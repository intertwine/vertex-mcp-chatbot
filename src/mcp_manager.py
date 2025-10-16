"""Simplified MCP client manager that uses asyncio.run for each operation."""

import asyncio
import logging
import os
import random
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import HTTP/SSE transports
try:
    import httpx
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client

    HTTP_TRANSPORT_AVAILABLE = True
except ImportError:
    HTTP_TRANSPORT_AVAILABLE = False

# Import OAuth support
try:
    import base64
    import hashlib
    import json
    import secrets
    import webbrowser
    from datetime import datetime, timedelta
    from urllib.parse import parse_qs, quote, urlparse

    from rich.console import Console

    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

from .mcp_config import MCPConfig

logger = logging.getLogger(__name__)


class MCPManagerError(Exception):
    """Exception raised for MCP manager errors."""

    pass


class MCPManager:
    """Simplified MCP client manager that creates sessions on demand."""

    def __init__(self, config: Optional[MCPConfig] = None, quiet_mode: bool = False):
        """Initialize MCP manager.

        Args:
            config: MCP configuration. If not provided, will create default.
            quiet_mode: If True, suppress subprocess output from MCP servers.
        """
        self.config = config or MCPConfig()
        self._active_servers: Dict[str, Dict[str, Any]] = {}  # Track server configs
        self._quiet_mode = quiet_mode
        # Add these for compatibility with tests
        self._sessions = {}  # Mock sessions tracking
        self._transports = {}
        self._session_id_callbacks = {}
        self._oauth_tokens = {}
        self._oauth_console = Console() if OAUTH_AVAILABLE else None
        self._exit_stack = None
        self._initialized = False

    def connect_server_sync(self, server_name: str) -> None:
        """Mark a server as active for connection.

        Args:
            server_name: Name of the server to connect to
        """
        server_config = self.config.get_server(server_name)
        if not server_config:
            raise MCPManagerError(f"Server '{server_name}' not found in configuration")

        # Use retry logic
        self._connect_with_retry_sync(server_name, server_config)

    def _connect_with_retry_sync(
        self, server_name: str, server_config: Dict[str, Any]
    ) -> None:
        """Connect with retry logic (synchronous version)."""
        retry_config = self._get_retry_config(server_config)
        max_attempts = retry_config["max_attempts"]

        last_error = None

        for attempt in range(max_attempts):
            try:
                # Log attempt
                if attempt > 0:
                    logger.info(
                        f"Connection attempt {attempt + 1}/{max_attempts} for {server_name}"
                    )

                # Mark as active
                self._active_servers[server_name] = server_config
                self._sessions[server_name] = True

                # Test connection by getting tools
                asyncio.run(self._get_tools_async(server_name))

                # Success!
                if attempt > 0:
                    logger.info(
                        f"Connection successful on attempt {attempt + 1} for {server_name}"
                    )
                logger.info(f"Server '{server_name}' connected successfully")
                return

            except Exception as e:
                last_error = e

                # Remove from active servers
                self._active_servers.pop(server_name, None)
                self._sessions.pop(server_name, None)

                # Don't retry if this is the last attempt
                if attempt >= max_attempts - 1:
                    break

                # Calculate backoff delay
                delay = self._calculate_backoff_delay(
                    attempt,
                    retry_config["initial_delay"],
                    retry_config["exponential_base"],
                    retry_config["max_delay"],
                    retry_config["jitter"],
                )

                logger.warning(
                    f"Connection attempt {attempt + 1}/{max_attempts} failed for "
                    f"{server_name}: {e}. Retrying in {delay:.1f}s..."
                )

                # Wait before retry
                import time

                time.sleep(delay)

        # All attempts failed
        raise MCPManagerError(
            f"Failed to connect to server '{server_name}' after {max_attempts} "
            f"attempts: {last_error}"
        )

    def disconnect_server_sync(self, server_name: str) -> None:
        """Mark a server as inactive.

        Args:
            server_name: Name of the server to disconnect from
        """
        self._active_servers.pop(server_name, None)
        self._sessions.pop(server_name, None)
        self._transports.pop(server_name, None)
        self._session_id_callbacks.pop(server_name, None)
        logger.info(f"Server '{server_name}' marked as inactive")

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all configured servers with their connection status.

        Returns:
            List of server info with name, transport, and connection status
        """
        servers = []
        for server in self.config.servers:
            server_info = server.copy()
            server_info["connected"] = server["name"] in self._sessions
            servers.append(server_info)
        return servers

    @asynccontextmanager
    async def _create_session(self, server_name: str):
        """Create a temporary session for a server operation.

        Args:
            server_name: Name of the server

        Yields:
            ClientSession instance
        """
        if server_name not in self._active_servers:
            raise MCPManagerError(f"Server '{server_name}' is not connected")

        server_config = self._active_servers[server_name]
        transport = server_config["transport"]

        if transport == "stdio":
            command = server_config["command"]
            server_params = StdioServerParameters(
                command=command[0], args=command[1:] if len(command) > 1 else None
            )

            # Use a null error log if in quiet mode to suppress subprocess output
            if self._quiet_mode:
                # Open /dev/null (Unix) or nul (Windows) for writing
                null_device = "nul" if sys.platform == "win32" else "/dev/null"
                with open(null_device, "w") as null_file:
                    async with stdio_client(server_params, errlog=null_file) as (
                        read,
                        write,
                    ):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            yield session
            else:
                async with stdio_client(server_params, errlog=sys.stderr) as (
                    read,
                    write,
                ):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        yield session

        elif transport == "http":
            if not HTTP_TRANSPORT_AVAILABLE:
                raise MCPManagerError(
                    "HTTP transport requires httpx. Install with: pip install httpx httpx-sse"
                )

            url = server_config["url"]
            headers = server_config.get("headers", {})
            auth = None

            # Handle authentication
            auth_config = server_config.get("auth")
            if auth_config:
                auth_type = auth_config.get("type")
                if auth_type == "basic":
                    username = auth_config.get("username")
                    password = auth_config.get("password")
                    if username and password:
                        auth = httpx.BasicAuth(username, password)
                elif auth_type == "oauth" and OAUTH_AVAILABLE:
                    # Handle OAuth authentication
                    token = await self._handle_oauth_auth(server_name, auth_config)
                    if token:
                        headers = headers.copy()
                        headers["Authorization"] = f"Bearer {token['access_token']}"
                        self._oauth_tokens[server_name] = token

            async with streamablehttp_client(url, headers=headers, auth=auth) as (
                read,
                write,
                _,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        elif transport == "sse":
            if not HTTP_TRANSPORT_AVAILABLE:
                raise MCPManagerError(
                    "SSE transport requires httpx. Install with: pip install httpx httpx-sse"
                )

            url = server_config["url"]
            headers = server_config.get("headers")
            auth = None

            # Handle authentication (same as HTTP)
            auth_config = server_config.get("auth")
            if auth_config:
                auth_type = auth_config.get("type")
                if auth_type == "basic":
                    username = auth_config.get("username")
                    password = auth_config.get("password")
                    if username and password:
                        auth = httpx.BasicAuth(username, password)

            async with sse_client(url, headers=headers, auth=auth) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        else:
            raise MCPManagerError(f"Unknown transport type: {transport}")

    async def _get_tools_async(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available tools from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of tool definitions
        """
        if server_name:
            async with self._create_session(server_name) as session:
                result = await session.list_tools()
                tools = result.tools if hasattr(result, "tools") else []

                tool_dicts = []
                for tool in tools:
                    tool_dict = {
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema,
                        "server": server_name,
                    }
                    tool_dicts.append(tool_dict)
                return tool_dicts
        else:
            # Get tools from all active servers
            all_tools = []
            for server_name in self._active_servers:
                try:
                    tools = await self._get_tools_async(server_name)
                    all_tools.extend(tools)
                except Exception as e:
                    logger.warning(f"Failed to get tools from {server_name}: {e}")
            return all_tools

    async def _get_resources_async(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available resources from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of resource definitions
        """
        if server_name:
            async with self._create_session(server_name) as session:
                result = await session.list_resources()
                logger.debug(f"Resource result from {server_name}: {result}")
                resources = result.resources if hasattr(result, "resources") else []
                logger.debug(f"Resources extracted: {len(resources)} resources")

                resource_dicts = []
                for resource in resources:
                    logger.debug(f"Processing resource: {resource}")
                    resource_dict = {
                        "uri": str(resource.uri) if resource.uri else "",
                        "name": resource.name or "",
                        "description": resource.description or "",
                        "mimeType": resource.mimeType or "application/octet-stream",
                        "server": server_name,
                    }
                    resource_dicts.append(resource_dict)
                logger.debug(
                    f"Returning {len(resource_dicts)} resources from {server_name}"
                )
                return resource_dicts
        else:
            # Get resources from all active servers
            all_resources = []
            for server_name in self._active_servers:
                try:
                    resources = await self._get_resources_async(server_name)
                    all_resources.extend(resources)
                except Exception as e:
                    logger.warning(f"Failed to get resources from {server_name}: {e}")
            return all_resources

    async def _get_prompts_async(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available prompts from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of prompt definitions
        """
        if server_name:
            async with self._create_session(server_name) as session:
                result = await session.list_prompts()
                prompts = result.prompts if hasattr(result, "prompts") else []

                prompt_dicts = []
                for prompt in prompts:
                    prompt_dict = {
                        "name": prompt.name,
                        "description": prompt.description or "",
                        "arguments": [
                            {
                                "name": arg.name,
                                "description": arg.description or "",
                                "required": arg.required,
                            }
                            for arg in (prompt.arguments or [])
                        ],
                        "server": server_name,
                    }
                    prompt_dicts.append(prompt_dict)
                return prompt_dicts
        else:
            # Get prompts from all active servers
            all_prompts = []
            for server_name in self._active_servers:
                try:
                    prompts = await self._get_prompts_async(server_name)
                    all_prompts.extend(prompts)
                except Exception as e:
                    logger.warning(f"Failed to get prompts from {server_name}: {e}")
            return all_prompts

    async def _call_tool_async(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a specific server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        async with self._create_session(server_name) as session:
            return await session.call_tool(tool_name, arguments=arguments)

    async def _read_resource_async(
        self, server_name: str, resource_uri: str
    ) -> Dict[str, Any]:
        """Read a resource from a specific server.

        Args:
            server_name: Name of the server
            resource_uri: URI of the resource to read

        Returns:
            Resource content
        """
        async with self._create_session(server_name) as session:
            return await session.read_resource(resource_uri)

    async def _get_prompt_async(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Get a specific prompt from a server.

        Args:
            server_name: Name of the server
            prompt_name: Name of the prompt to get
            arguments: Optional arguments for the prompt

        Returns:
            Prompt result with messages
        """
        async with self._create_session(server_name) as session:
            return await session.get_prompt(prompt_name, arguments=arguments or {})

    async def _get_resource_templates_async(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available resource templates from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of resource template definitions
        """
        if server_name:
            async with self._create_session(server_name) as session:
                result = await session.list_resource_templates()
                logger.debug(f"Resource templates result from {server_name}: {result}")
                templates = (
                    result.resourceTemplates
                    if hasattr(result, "resourceTemplates")
                    else []
                )
                logger.debug(f"Templates extracted: {len(templates)} templates")

                template_dicts = []
                for template in templates:
                    logger.debug(f"Processing template: {template}")
                    template_dict = {
                        "uriTemplate": (
                            str(template.uriTemplate)
                            if hasattr(template, "uriTemplate")
                            else ""
                        ),
                        "name": template.name or "",
                        "description": template.description or "",
                        "mimeType": (
                            template.mimeType or "application/octet-stream"
                            if hasattr(template, "mimeType")
                            else "application/octet-stream"
                        ),
                        "server": server_name,
                    }
                    template_dicts.append(template_dict)
                logger.debug(
                    f"Returning {len(template_dicts)} templates from {server_name}"
                )
                return template_dicts
        else:
            # Get templates from all active servers
            all_templates = []
            for server_name in self._active_servers:
                try:
                    templates = await self._get_resource_templates_async(server_name)
                    all_templates.extend(templates)
                except Exception as e:
                    logger.warning(
                        f"Failed to get resource templates from {server_name}: {e}"
                    )
            return all_templates

    # Synchronous wrapper methods

    def get_tools_sync(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_tools."""
        return asyncio.run(self._get_tools_async(server_name))

    def get_resources_sync(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_resources."""
        return asyncio.run(self._get_resources_async(server_name))

    def get_prompts_sync(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_prompts."""
        return asyncio.run(self._get_prompts_async(server_name))

    def call_tool_sync(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous wrapper for call_tool."""
        return asyncio.run(self._call_tool_async(server_name, tool_name, arguments))

    def read_resource_sync(self, server_name: str, resource_uri: str) -> Dict[str, Any]:
        """Synchronous wrapper for read_resource."""
        return asyncio.run(self._read_resource_async(server_name, resource_uri))

    def get_prompt_sync(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for get_prompt."""
        return asyncio.run(self._get_prompt_async(server_name, prompt_name, arguments))

    def get_resource_templates_sync(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_resource_templates."""
        return asyncio.run(self._get_resource_templates_async(server_name))

    # Compatibility methods for existing code

    def initialize_sync(self) -> None:
        """No-op for compatibility."""
        self._initialized = True

    def cleanup_sync(self) -> None:
        """No-op for compatibility."""
        self._initialized = False
        self._active_servers.clear()
        self._sessions.clear()
        self._transports.clear()
        self._session_id_callbacks.clear()

    # Multi-server coordination methods

    async def find_best_server_for_tool(self, tool_name: str) -> Optional[str]:
        """Find the best server for a specific tool based on priority.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Name of the best server, or None if tool not found
        """
        servers_with_tool = await self.find_servers_with_tool(tool_name)
        if not servers_with_tool:
            return None

        # Get server priorities
        priorities = self.get_server_priorities()

        # Sort servers by priority (lower number = higher priority)
        sorted_servers = sorted(
            servers_with_tool, key=lambda s: priorities.get(s, float("inf"))
        )

        return sorted_servers[0] if sorted_servers else None

    async def find_servers_with_tool(self, tool_name: str) -> List[str]:
        """Find all servers that have a specific tool.

        Args:
            tool_name: Name of the tool to find

        Returns:
            List of server names that have the tool
        """
        servers_with_tool = []

        # Get tools from all servers
        all_tools = await self._get_tools_async()

        # Find unique servers that have this tool
        for tool in all_tools:
            if tool["name"] == tool_name and tool["server"] not in servers_with_tool:
                servers_with_tool.append(tool["server"])

        return servers_with_tool

    def get_server_priorities(self) -> Dict[str, int]:
        """Get server priorities from configuration.

        Returns:
            Dictionary mapping server names to priority values
        """
        priorities = {}
        for server in self.config.servers:
            if "priority" in server:
                priorities[server["name"]] = server["priority"]
        return priorities

    # Sync wrappers for multi-server operations

    def find_best_server_for_tool_sync(self, tool_name: str) -> Optional[str]:
        """Synchronous wrapper for find_best_server_for_tool.

        This implementation is safe to call whether or not an event loop is running.
        If a loop is already running (e.g., inside pytest-asyncio), we execute the
        coroutine in a dedicated background thread with its own event loop to avoid
        creating an un-awaited coroutine and to prevent RuntimeError from
        asyncio.run().
        """
        try:
            # If this doesn't raise, we're in a running event loop.
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop: create and manage a private event loop explicitly.
            coro = self.find_best_server_for_tool(tool_name)
            loop = asyncio.new_event_loop()
            try:
                # Prefer asyncio.run for compatibility with tests that patch it,
                # but manage the loop ourselves to avoid nested-loop issues.
                return asyncio.run(coro)
            finally:
                # Ensure the coroutine object is closed to avoid 'never awaited' warnings
                try:
                    coro.close()
                except Exception:
                    pass
                # Clean up any event loop we may have created above (none in this branch)
                try:
                    asyncio.set_event_loop(None)
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
        else:
            # Running event loop detected; execute in a separate thread with its own loop.
            import threading

            result: Dict[str, Optional[str]] = {"value": None}
            error: Dict[str, BaseException] = {}

            def _runner():
                inner_loop = asyncio.new_event_loop()
                try:
                    asyncio.set_event_loop(inner_loop)
                    result["value"] = inner_loop.run_until_complete(
                        self.find_best_server_for_tool(tool_name)
                    )
                except BaseException as e:  # propagate later in caller thread
                    error["err"] = e
                finally:
                    try:
                        asyncio.set_event_loop(None)
                    finally:
                        inner_loop.close()

            t = threading.Thread(target=_runner, daemon=True)
            t.start()
            t.join()

            if "err" in error:
                raise error["err"]
            return result["value"]

    def find_servers_with_tool_sync(self, tool_name: str) -> List[str]:
        """Synchronous wrapper for find_servers_with_tool."""
        return asyncio.run(self.find_servers_with_tool(tool_name))

    # OAuth authentication methods

    async def _handle_oauth_auth(
        self, server_name: str, auth_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Handle OAuth authentication for a server.

        Args:
            server_name: Name of the server
            auth_config: OAuth configuration

        Returns:
            Token data if successful, None otherwise
        """
        # Validate OAuth configuration
        required_fields = [
            "authorization_url",
            "token_url",
            "client_id",
            "scope",
            "redirect_uri",
        ]
        if not all(field in auth_config for field in required_fields):
            raise MCPManagerError(
                f"OAuth configuration missing required fields: {required_fields}"
            )

        # Try to load existing token
        token = await self._load_oauth_token(server_name)
        if token and self._is_token_valid(token):
            return token

        # Need new authorization
        return await self._perform_oauth_flow(server_name, auth_config)

    async def _perform_oauth_flow(
        self, server_name: str, auth_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Perform the OAuth authorization flow.

        Args:
            server_name: Name of the server
            auth_config: OAuth configuration

        Returns:
            Token data if successful, None otherwise
        """
        if not OAUTH_AVAILABLE or not HTTP_TRANSPORT_AVAILABLE:
            raise MCPManagerError(
                "OAuth support not available. Install required dependencies."
            )

        # Generate PKCE parameters
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        # Generate state for CSRF protection
        state = secrets.token_urlsafe(16)

        # Build authorization URL
        auth_params = {
            "client_id": auth_config["client_id"],
            "redirect_uri": auth_config["redirect_uri"],
            "response_type": "code",
            "scope": auth_config["scope"],
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }

        # Create the authorization URL
        auth_url = auth_config["authorization_url"]
        if "?" in auth_url:
            auth_url += "&"
        else:
            auth_url += "?"
        # Properly URL-encode each parameter value
        encoded_params = [
            f"{k}={quote(str(v), safe='')}" for k, v in auth_params.items()
        ]
        auth_url += "&".join(encoded_params)

        # Display the URL to the user
        await self._handle_oauth_redirect(auth_url)

        # Get the callback URL from user
        callback_url = await self._handle_oauth_callback()

        # Parse the callback URL
        parsed = urlparse(callback_url)
        params = parse_qs(parsed.query)

        # Verify state
        if params.get("state", [None])[0] != state:
            raise MCPManagerError("OAuth state mismatch - possible CSRF attack")

        # Get the authorization code
        code = params.get("code", [None])[0]
        if not code:
            error = params.get("error", ["unknown"])[0]
            raise MCPManagerError(f"OAuth authorization failed: {error}")

        # Exchange code for token
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": auth_config["redirect_uri"],
            "client_id": auth_config["client_id"],
            "code_verifier": verifier,
        }

        # Add client secret if provided (confidential client)
        if "client_secret" in auth_config:
            token_data["client_secret"] = auth_config["client_secret"]

        # Make token request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                auth_config["token_url"],
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise MCPManagerError(f"Token exchange failed: {response.text}")

            token = response.json()
            await self._save_oauth_token(server_name, token)
            return token

    async def _handle_oauth_redirect(self, url: str) -> Optional[str]:
        """Handle OAuth redirect by displaying URL to user.

        Args:
            url: Authorization URL

        Returns:
            None (manual handling)
        """
        if self._oauth_console:
            self._oauth_console.print(
                f"\n[bold blue]OAuth Authorization Required[/bold blue]"
            )
            self._oauth_console.print(
                f"Please visit this URL to authorize the application:"
            )
            self._oauth_console.print(f"[link]{url}[/link]\n")
        return None

    async def _handle_oauth_callback(self) -> str:
        """Handle OAuth callback by prompting for the callback URL.

        Returns:
            The callback URL entered by the user
        """
        if self._oauth_console:
            self._oauth_console.print(
                "[yellow]After authorizing, paste the full callback URL here:[/yellow]"
            )
        return input("Callback URL: ")

    def _get_token_storage_path(self, server_name: str) -> str:
        """Get the token storage file path for a server.

        Args:
            server_name: Name of the server

        Returns:
            Path to the token file
        """
        return os.path.join(".mcp_tokens", f"{server_name}.json")

    async def _save_oauth_token(
        self, server_name: str, token_data: Dict[str, Any]
    ) -> None:
        """Save OAuth token to file.

        Args:
            server_name: Name of the server
            token_data: Token data to save
        """
        # Calculate expiration time
        if "expires_in" in token_data:
            expires_at = datetime.now().timestamp() + token_data["expires_in"]
            token_data["expires_at"] = expires_at

        # Ensure directory exists
        os.makedirs(".mcp_tokens", exist_ok=True)

        # Save token
        path = self._get_token_storage_path(server_name)
        with open(path, "w") as f:
            json.dump(token_data, f)

    async def _load_oauth_token(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Load OAuth token from file.

        Args:
            server_name: Name of the server

        Returns:
            Token data if found and valid, None otherwise
        """
        path = self._get_token_storage_path(server_name)
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load token for {server_name}: {e}")
            return None

    def _is_token_valid(self, token: Dict[str, Any]) -> bool:
        """Check if a token is still valid.

        Args:
            token: Token data

        Returns:
            True if token is valid, False otherwise
        """
        if "expires_at" not in token:
            return True  # No expiration

        # Check if expired (with 5 minute buffer)
        expires_at = token["expires_at"]
        return datetime.now().timestamp() < (expires_at - 300)

    # Connection retry methods

    def _get_retry_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Get retry configuration for a server.

        Args:
            server_config: Server configuration

        Returns:
            Retry configuration with defaults
        """
        default_retry = {
            "max_attempts": 3,
            "initial_delay": 1.0,
            "max_delay": 60.0,
            "exponential_base": 2.0,
            "jitter": True,
        }

        # Get server-specific retry config
        server_retry = server_config.get("retry", {})

        # Merge with defaults
        retry_config = default_retry.copy()
        retry_config.update(server_retry)

        return retry_config

    def _calculate_backoff_delay(
        self,
        attempt: int,
        initial_delay: float,
        exponential_base: float,
        max_delay: float,
        jitter: bool,
    ) -> float:
        """Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-based)
            initial_delay: Initial delay in seconds
            exponential_base: Base for exponential calculation
            max_delay: Maximum delay in seconds
            jitter: Whether to add random jitter

        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = initial_delay * (exponential_base**attempt)

        # Cap at max delay
        delay = min(delay, max_delay)

        # Add jitter if enabled (±50% of delay)
        if jitter:
            jitter_range = delay * 0.5
            delay = delay + (random.random() - 0.5) * jitter_range

        return max(delay, 0)  # Ensure non-negative

    # Async versions for compatibility

    async def initialize(self) -> None:
        """Initialize the manager (no-op for compatibility)."""
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up all connections and resources."""
        self._initialized = False
        self._active_servers.clear()
        self._sessions.clear()
        self._transports.clear()
        self._session_id_callbacks.clear()

    async def connect_server(self, server_name: str) -> None:
        """Connect to an MCP server (async wrapper)."""
        self.connect_server_sync(server_name)

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from an MCP server (async wrapper)."""
        self.disconnect_server_sync(server_name)

    async def get_tools(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available tools from server(s)."""
        return await self._get_tools_async(server_name)

    async def get_resources(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available resources from server(s)."""
        return await self._get_resources_async(server_name)

    async def get_prompts(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available prompts from server(s)."""
        return await self._get_prompts_async(server_name)

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a specific server."""
        return await self._call_tool_async(server_name, tool_name, arguments)

    async def read_resource(
        self, server_name: str, resource_uri: str
    ) -> Dict[str, Any]:
        """Read a resource from a specific server."""
        return await self._read_resource_async(server_name, resource_uri)

    async def get_prompt(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Get a specific prompt from a server."""
        return await self._get_prompt_async(server_name, prompt_name, arguments)

    # Additional async methods for compatibility

    async def _get_tools_safe(self, session) -> Optional[Any]:
        """Compatibility method - not used in simplified version."""
        return None

    async def _get_resources_safe(self, session) -> Optional[Any]:
        """Compatibility method - not used in simplified version."""
        return None

    async def _get_prompts_safe(self, session) -> Optional[Any]:
        """Compatibility method - not used in simplified version."""
        return None

    async def broadcast_operation(
        self, operation: str, *args, **kwargs
    ) -> List[Tuple[str, Any]]:
        """Broadcast an operation to all connected servers."""
        results = []
        for server_name in self._active_servers:
            try:
                if operation == "list_tools":
                    result = await self._get_tools_async(server_name)
                elif operation == "list_resources":
                    result = await self._get_resources_async(server_name)
                elif operation == "list_prompts":
                    result = await self._get_prompts_async(server_name)
                else:
                    result = None
                results.append(
                    (
                        server_name,
                        {"tools": result} if operation == "list_tools" else result,
                    )
                )
            except Exception as e:
                logger.warning(f"Operation {operation} failed for {server_name}: {e}")
                results.append((server_name, None))
        return results

    def broadcast_operation_sync(
        self, operation: str, *args, **kwargs
    ) -> List[Tuple[str, Any]]:
        """Synchronous wrapper for broadcast_operation."""
        return asyncio.run(self.broadcast_operation(operation, *args, **kwargs))

    def _get_session_id(self, server_name: str) -> Optional[str]:
        """Get the session ID for an HTTP server (not implemented in simplified version)."""
        return None

    # Async versions for retry (not used in simplified version)

    async def _connect_with_retry(
        self, server_name: str, server_config: Dict[str, Any]
    ) -> None:
        """Async version of retry (calls sync version)."""
        self._connect_with_retry_sync(server_name, server_config)
