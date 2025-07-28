"""MCP client manager module."""

import asyncio
import logging
import random
from contextlib import AsyncExitStack
from typing import Dict, List, Any, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Import HTTP/SSE transports
try:
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.sse import sse_client
    import httpx

    HTTP_TRANSPORT_AVAILABLE = True
except ImportError:
    HTTP_TRANSPORT_AVAILABLE = False

# Import OAuth support
try:
    from rich.console import Console
    import json
    import os
    from datetime import datetime, timedelta
    import webbrowser
    from urllib.parse import urlparse, parse_qs
    import secrets
    import base64
    import hashlib

    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False

from .mcp_config import MCPConfig

logger = logging.getLogger(__name__)


class MCPManagerError(Exception):
    """Exception raised for MCP manager errors."""

    pass


class MCPManager:
    """Manages MCP client connections and operations."""

    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize MCP manager.

        Args:
            config: MCP configuration. If not provided, will create default.
        """
        self.config = config or MCPConfig()
        self._sessions: Dict[str, ClientSession] = {}
        self._transports: Dict[str, Tuple[Any, Any]] = {}  # Store (read, write) streams
        self._session_id_callbacks: Dict[str, Any] = {}  # For HTTP transport
        self._oauth_tokens: Dict[str, Dict[str, Any]] = {}  # OAuth tokens by server
        self._oauth_console = Console() if OAUTH_AVAILABLE else None
        self._exit_stack: Optional[AsyncExitStack] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the manager with exit stack for resource management."""
        if self._initialized:
            return

        self._exit_stack = AsyncExitStack()
        self._initialized = True

    async def cleanup(self) -> None:
        """Clean up all connections and resources."""
        if self._exit_stack:
            await self._exit_stack.aclose()

        self._sessions.clear()
        self._transports.clear()
        self._initialized = False

    async def connect_server(self, server_name: str) -> None:
        """Connect to an MCP server.

        Args:
            server_name: Name of the server to connect to

        Raises:
            MCPManagerError: If server not found or connection fails
        """
        if not self._initialized:
            await self.initialize()

        # Check if already connected
        if server_name in self._sessions:
            return

        # Get server configuration
        server_config = self.config.get_server(server_name)
        if not server_config:
            raise MCPManagerError(f"Server '{server_name}' not found in configuration")

        # Use retry logic for connection
        await self._connect_with_retry(server_name, server_config)

    async def _connect_stdio_server(
        self, server_name: str, config: Dict[str, Any]
    ) -> None:
        """Connect to a stdio transport server.

        Args:
            server_name: Name of the server
            config: Server configuration
        """
        if not self._exit_stack:
            raise MCPManagerError("Manager not initialized")

        command = config["command"]
        server_params = StdioServerParameters(
            command=command[0], args=command[1:] if len(command) > 1 else None
        )

        try:
            # Create the stdio transport
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport

            # Create the client session
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Initialize the session
            await session.initialize()

            # Store the session and transport
            self._sessions[server_name] = session
            self._transports[server_name] = (read, write)

        except Exception as e:
            raise MCPManagerError(f"Failed to connect to server '{server_name}': {e}")

    async def _connect_http_server(
        self, server_name: str, config: Dict[str, Any]
    ) -> None:
        """Connect to an HTTP transport server.

        Args:
            server_name: Name of the server
            config: Server configuration
        """
        if not self._exit_stack:
            raise MCPManagerError("Manager not initialized")

        url = config["url"]
        headers = config.get("headers", {})
        auth = None

        # Handle authentication
        auth_config = config.get("auth")
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

        try:
            # Create the HTTP transport
            http_transport = await self._exit_stack.enter_async_context(
                streamablehttp_client(url, headers=headers, auth=auth)
            )
            read, write, get_session_id = http_transport

            # Create the client session
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Initialize the session
            await session.initialize()

            # Store the session, transport, and session ID callback
            self._sessions[server_name] = session
            self._transports[server_name] = (read, write)
            self._session_id_callbacks[server_name] = get_session_id

        except Exception as e:
            raise MCPManagerError(f"Failed to connect to server '{server_name}': {e}")

    async def _connect_sse_server(
        self, server_name: str, config: Dict[str, Any]
    ) -> None:
        """Connect to an SSE transport server.

        Args:
            server_name: Name of the server
            config: Server configuration
        """
        if not self._exit_stack:
            raise MCPManagerError("Manager not initialized")

        url = config["url"]
        headers = config.get("headers")
        auth = None

        # Handle authentication (same as HTTP)
        auth_config = config.get("auth")
        if auth_config:
            auth_type = auth_config.get("type")
            if auth_type == "basic":
                username = auth_config.get("username")
                password = auth_config.get("password")
                if username and password:
                    auth = httpx.BasicAuth(username, password)

        try:
            # Create the SSE transport
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(url, headers=headers, auth=auth)
            )
            read, write = sse_transport

            # Create the client session
            session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            # Initialize the session
            await session.initialize()

            # Store the session and transport
            self._sessions[server_name] = session
            self._transports[server_name] = (read, write)

        except Exception as e:
            raise MCPManagerError(f"Failed to connect to server '{server_name}': {e}")

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from an MCP server.

        Args:
            server_name: Name of the server to disconnect from
        """
        # Remove from our tracking
        # Note: Actual cleanup happens via AsyncExitStack on cleanup()
        self._sessions.pop(server_name, None)
        self._transports.pop(server_name, None)
        self._session_id_callbacks.pop(server_name, None)

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

    async def get_tools(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available tools from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of tool definitions

        Raises:
            MCPManagerError: If specified server is not connected
        """
        if server_name:
            if server_name not in self._sessions:
                raise MCPManagerError(f"Server '{server_name}' is not connected")

            session = self._sessions[server_name]
            result = await session.list_tools()
            tools = result.get("tools", [])
            # Add server name to each tool
            for tool in tools:
                tool["server"] = server_name
            return tools
        else:
            # Get tools from all connected servers in parallel
            tasks = []
            server_names = []
            
            for name, session in self._sessions.items():
                tasks.append(self._get_tools_safe(session))
                server_names.append(name)
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks)
            
            # Combine results with server names
            all_tools = []
            for server_name, result in zip(server_names, results):
                if result is not None:
                    tools = result.get("tools", [])
                    # Add server name to each tool
                    for tool in tools:
                        tool["server"] = server_name
                    all_tools.extend(tools)
            
            return all_tools
    
    async def _get_tools_safe(self, session: ClientSession) -> Optional[Dict[str, Any]]:
        """Safely get tools from a session, returning None on error."""
        try:
            return await session.list_tools()
        except Exception as e:
            # Log error but don't propagate - error isolation
            logger.warning(f"Failed to get tools from server: {e}")
            return None

    async def get_resources(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available resources from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of resource definitions

        Raises:
            MCPManagerError: If specified server is not connected
        """
        if server_name:
            if server_name not in self._sessions:
                raise MCPManagerError(f"Server '{server_name}' is not connected")

            session = self._sessions[server_name]
            result = await session.list_resources()
            return result.get("resources", [])
        else:
            # Get resources from all connected servers in parallel
            tasks = []
            server_names = []
            
            for name, session in self._sessions.items():
                tasks.append(self._get_resources_safe(session))
                server_names.append(name)
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks)
            
            # Combine results with server names
            all_resources = []
            for server_name, result in zip(server_names, results):
                if result is not None:
                    resources = result.get("resources", [])
                    # Add server name to each resource
                    for resource in resources:
                        resource["server"] = server_name
                    all_resources.extend(resources)
            
            return all_resources
    
    async def _get_resources_safe(self, session: ClientSession) -> Optional[Dict[str, Any]]:
        """Safely get resources from a session, returning None on error."""
        try:
            return await session.list_resources()
        except Exception as e:
            # Log error but don't propagate - error isolation
            logger.warning(f"Failed to get resources from server: {e}")
            return None

    async def get_prompts(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available prompts from server(s).

        Args:
            server_name: Specific server name, or None for all servers

        Returns:
            List of prompt definitions

        Raises:
            MCPManagerError: If specified server is not connected
        """
        if server_name:
            if server_name not in self._sessions:
                raise MCPManagerError(f"Server '{server_name}' is not connected")

            session = self._sessions[server_name]
            result = await session.list_prompts()
            return result.get("prompts", [])
        else:
            # Get prompts from all connected servers in parallel
            tasks = []
            server_names = []
            
            for name, session in self._sessions.items():
                tasks.append(self._get_prompts_safe(session))
                server_names.append(name)
            
            # Execute all tasks in parallel
            results = await asyncio.gather(*tasks)
            
            # Combine results with server names
            all_prompts = []
            for server_name, result in zip(server_names, results):
                if result is not None:
                    prompts = result.get("prompts", [])
                    # Add server name to each prompt
                    for prompt in prompts:
                        prompt["server"] = server_name
                    all_prompts.extend(prompts)
            
            return all_prompts
    
    async def _get_prompts_safe(self, session: ClientSession) -> Optional[Dict[str, Any]]:
        """Safely get prompts from a session, returning None on error."""
        try:
            return await session.list_prompts()
        except Exception as e:
            # Log error but don't propagate - error isolation
            logger.warning(f"Failed to get prompts from server: {e}")
            return None

    async def call_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call a tool on a specific server.

        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPManagerError: If server is not connected
        """
        if server_name not in self._sessions:
            raise MCPManagerError(f"Server '{server_name}' is not connected")

        session = self._sessions[server_name]
        return await session.call_tool(tool_name, arguments=arguments)

    async def read_resource(
        self, server_name: str, resource_uri: str
    ) -> Dict[str, Any]:
        """Read a resource from a specific server.

        Args:
            server_name: Name of the server
            resource_uri: URI of the resource to read

        Returns:
            Resource content

        Raises:
            MCPManagerError: If server is not connected
        """
        if server_name not in self._sessions:
            raise MCPManagerError(f"Server '{server_name}' is not connected")

        session = self._sessions[server_name]
        return await session.read_resource(resource_uri)

    async def get_prompt(
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

        Raises:
            MCPManagerError: If server is not connected
        """
        if server_name not in self._sessions:
            raise MCPManagerError(f"Server '{server_name}' is not connected")

        session = self._sessions[server_name]
        return await session.get_prompt(prompt_name, arguments=arguments or {})

    # Synchronous wrapper methods for use in non-async context
    # These create a new event loop for each operation

    def initialize_sync(self) -> None:
        """Synchronous wrapper for initialize."""
        asyncio.run(self.initialize())

    def cleanup_sync(self) -> None:
        """Synchronous wrapper for cleanup."""
        asyncio.run(self.cleanup())

    def connect_server_sync(self, server_name: str) -> None:
        """Synchronous wrapper for connect_server."""
        asyncio.run(self.connect_server(server_name))

    def disconnect_server_sync(self, server_name: str) -> None:
        """Synchronous wrapper for disconnect_server."""
        asyncio.run(self.disconnect_server(server_name))

    def get_tools_sync(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_tools."""
        return asyncio.run(self.get_tools(server_name))

    def get_resources_sync(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_resources."""
        return asyncio.run(self.get_resources(server_name))

    def get_prompts_sync(
        self, server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for get_prompts."""
        return asyncio.run(self.get_prompts(server_name))

    def call_tool_sync(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synchronous wrapper for call_tool."""
        return asyncio.run(self.call_tool(server_name, tool_name, arguments))

    def read_resource_sync(self, server_name: str, resource_uri: str) -> Dict[str, Any]:
        """Synchronous wrapper for read_resource."""
        return asyncio.run(self.read_resource(server_name, resource_uri))

    def get_prompt_sync(
        self,
        server_name: str,
        prompt_name: str,
        arguments: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for get_prompt."""
        return asyncio.run(self.get_prompt(server_name, prompt_name, arguments))

    def _get_session_id(self, server_name: str) -> Optional[str]:
        """Get the session ID for an HTTP server.

        Args:
            server_name: Name of the server

        Returns:
            Session ID if available, None otherwise
        """
        callback = self._session_id_callbacks.get(server_name)
        if callback:
            return callback()
        return None

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
            servers_with_tool,
            key=lambda s: priorities.get(s, float("inf"))
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
        all_tools = await self.get_tools()
        
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

    async def broadcast_operation(
        self, operation: str, *args, **kwargs
    ) -> List[Tuple[str, Any]]:
        """Broadcast an operation to all connected servers.

        Args:
            operation: Name of the operation to perform
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            List of (server_name, result) tuples
        """
        tasks = []
        server_names = []
        
        for name, session in self._sessions.items():
            if hasattr(session, operation):
                method = getattr(session, operation)
                tasks.append(self._safe_call(method, *args, **kwargs))
                server_names.append(name)
        
        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks)
        
        # Combine results with server names
        return list(zip(server_names, results))

    async def _safe_call(self, method, *args, **kwargs) -> Any:
        """Safely call a method, returning None on error."""
        try:
            return await method(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Operation failed: {e}")
            return None

    # Sync wrappers for multi-server operations

    def find_best_server_for_tool_sync(self, tool_name: str) -> Optional[str]:
        """Synchronous wrapper for find_best_server_for_tool."""
        return asyncio.run(self.find_best_server_for_tool(tool_name))

    def find_servers_with_tool_sync(self, tool_name: str) -> List[str]:
        """Synchronous wrapper for find_servers_with_tool."""
        return asyncio.run(self.find_servers_with_tool(tool_name))

    def broadcast_operation_sync(
        self, operation: str, *args, **kwargs
    ) -> List[Tuple[str, Any]]:
        """Synchronous wrapper for broadcast_operation."""
        return asyncio.run(self.broadcast_operation(operation, *args, **kwargs))

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
            raise MCPManagerError("OAuth support not available. Install required dependencies.")

        # Generate PKCE parameters
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')
        
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
        auth_url += "&".join(f"{k}={v}" for k, v in auth_params.items())
        
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
            self._oauth_console.print(f"\n[bold blue]OAuth Authorization Required[/bold blue]")
            self._oauth_console.print(f"Please visit this URL to authorize the application:")
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
        delay = initial_delay * (exponential_base ** attempt)

        # Cap at max delay
        delay = min(delay, max_delay)

        # Add jitter if enabled (±50% of delay)
        if jitter:
            jitter_range = delay * 0.5
            delay = delay + (random.random() - 0.5) * jitter_range

        return max(delay, 0)  # Ensure non-negative

    async def _connect_with_retry(
        self, server_name: str, server_config: Dict[str, Any]
    ) -> None:
        """Connect to a server with retry logic.

        Args:
            server_name: Name of the server
            server_config: Server configuration

        Raises:
            MCPManagerError: If connection fails after all retries
        """
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
                
                # Try to connect based on transport type
                transport = server_config["transport"]
                if transport == "stdio":
                    await self._connect_stdio_server(server_name, server_config)
                elif transport == "http":
                    if not HTTP_TRANSPORT_AVAILABLE:
                        raise MCPManagerError(
                            "HTTP transport requires httpx. Install with: pip install httpx httpx-sse"
                        )
                    await self._connect_http_server(server_name, server_config)
                elif transport == "sse":
                    if not HTTP_TRANSPORT_AVAILABLE:
                        raise MCPManagerError(
                            "SSE transport requires httpx. Install with: pip install httpx httpx-sse"
                        )
                    await self._connect_sse_server(server_name, server_config)
                else:
                    raise MCPManagerError(f"Unknown transport type: {transport}")
                
                # Success!
                if attempt > 0:
                    logger.info(
                        f"Connection successful on attempt {attempt + 1} for {server_name}"
                    )
                return
                
            except Exception as e:
                last_error = e
                
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
                await asyncio.sleep(delay)
        
        # All attempts failed
        raise MCPManagerError(
            f"Failed to connect to server '{server_name}' after {max_attempts} "
            f"attempts: {last_error}"
        )
