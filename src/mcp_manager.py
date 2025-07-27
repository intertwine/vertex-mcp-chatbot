"""MCP client manager module."""

import asyncio
import logging
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
        headers = config.get("headers")
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
            # Add other auth types as needed

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
