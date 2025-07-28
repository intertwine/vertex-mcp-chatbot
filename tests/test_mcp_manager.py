"""Test MCP manager functionality."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig
from tests.mock_mcp_types import (
    create_mock_list_tools_result,
    create_mock_list_resources_result,
    create_mock_list_prompts_result,
)
from tests.test_async_utils import create_async_run_mock


@pytest.fixture
def mock_config():
    """Create a mock MCP configuration."""
    config = MagicMock(spec=MCPConfig)
    config.servers = [
        {
            "name": "test-stdio",
            "transport": "stdio",
            "command": ["python", "server.py"],
        },
        {
            "name": "test-http",
            "transport": "http",
            "url": "http://localhost:8000",
        },
    ]
    config.get_server.side_effect = lambda name: next(
        (s for s in config.servers if s["name"] == name), None
    )
    return config


@pytest.fixture
def mock_client_session():
    """Create a mock MCP client session."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([]))
    session.list_resources = AsyncMock(return_value=create_mock_list_resources_result([]))
    session.list_prompts = AsyncMock(return_value=create_mock_list_prompts_result([]))
    session.call_tool = AsyncMock()
    session.read_resource = AsyncMock()
    return session


class TestMCPManager:
    """Test suite for MCP Manager."""

    def test_init_with_config(self, mock_config):
        """Test initialization with configuration."""
        manager = MCPManager(mock_config)
        assert manager.config == mock_config
        assert manager._sessions == {}
        assert manager._transports == {}
        assert manager._exit_stack is None
        assert manager._initialized is False

    def test_init_without_config(self):
        """Test initialization without configuration."""
        with patch("src.mcp_manager.MCPConfig") as mock_config_class:
            # Use a regular Mock instead of MagicMock to avoid coroutine issues
            mock_config = Mock()
            mock_config.servers = []
            mock_config_class.return_value = mock_config
            manager = MCPManager()
            assert manager.config is not None
            assert manager._sessions == {}
            assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self, mock_config):
        """Test manager initialization."""
        manager = MCPManager(mock_config)

        await manager.initialize()
        assert manager._initialized is True
        
        # In simplified architecture, _exit_stack is not used
        # Test that calling initialize again is idempotent
        await manager.initialize()
        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_config):
        """Test manager cleanup."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Add some mock connections
        manager._active_servers["test-server"] = mock_config.servers[0]
        manager._sessions["test-server"] = True

        await manager.cleanup()

        # In simplified architecture, cleanup clears all state
        assert manager._initialized is False
        assert len(manager._active_servers) == 0
        assert len(manager._sessions) == 0
        assert len(manager._transports) == 0

    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.stdio_client")
    def test_connect_stdio_server(self, mock_stdio_client, mock_run, mock_config):
        """Test connecting to a stdio transport server."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to execute the coroutine synchronously
        async def mock_async_run(coro):
            # Mock stdio client context
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            
            mock_stdio_context = AsyncMock()
            mock_stdio_context.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
            mock_stdio_context.__aexit__ = AsyncMock(return_value=None)
            mock_stdio_client.return_value = mock_stdio_context
            
            # Mock session
            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([]))
            
            with patch("src.mcp_manager.ClientSession") as mock_client_session:
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context
                
                # Execute the actual coroutine
                return await coro
        
        mock_run.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(mock_async_run(coro))
        
        manager.connect_server_sync("test-stdio")
        
        # Verify server is tracked
        assert "test-stdio" in manager._sessions
        assert "test-stdio" in manager._active_servers

    @patch("src.mcp_manager.HTTP_TRANSPORT_AVAILABLE", False)
    def test_connect_http_server_not_available(self, mock_config):
        """Test connecting to HTTP transport server when httpx not available."""
        manager = MCPManager(mock_config)

        with pytest.raises(MCPManagerError, match="HTTP transport requires httpx"):
            manager.connect_server_sync("test-http")

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server(self, mock_config):
        """Test connecting to a non-existent server."""
        manager = MCPManager(mock_config)

        with pytest.raises(MCPManagerError, match="Server 'nonexistent' not found"):
            await manager.connect_server("nonexistent")

    @patch("src.mcp_manager.asyncio.run")
    def test_connect_already_connected(self, mock_run, mock_config, mock_client_session):
        """Test connecting to an already connected server."""
        manager = MCPManager(mock_config)
        # Mark server as already active
        manager._active_servers["test-stdio"] = mock_config.servers[0]
        manager._sessions["test-stdio"] = mock_client_session

        # Mock asyncio.run for the test connection
        mock_run.return_value = []  # Empty tools list

        # Should not raise an error, just update existing session
        manager.connect_server_sync("test-stdio")
        assert "test-stdio" in manager._sessions

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_disconnect_server(self, mock_config, mock_client_session):
        """Test disconnecting from a server."""
        manager = MCPManager(mock_config)
        manager._active_servers["test-stdio"] = mock_config.servers[0]
        manager._sessions["test-stdio"] = mock_client_session

        with patch("asyncio.run", create_async_run_mock()):
            manager.disconnect_server_sync("test-stdio")
        assert "test-stdio" not in manager._sessions
        assert "test-stdio" not in manager._active_servers

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    async def test_disconnect_nonexistent_server(self, mock_config):
        """Test disconnecting from a non-connected server."""
        manager = MCPManager(mock_config)

        # Should not raise an error
        await manager.disconnect_server("nonexistent")

    def test_list_servers(self, mock_config, mock_client_session):
        """Test listing all configured servers with their status."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        servers = manager.list_servers()

        assert len(servers) == 2
        assert servers[0]["name"] == "test-stdio"
        assert servers[0]["connected"] is True
        assert servers[1]["name"] == "test-http"
        assert servers[1]["connected"] is False

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    async def test_get_tools_single_server(self, mock_config):
        """Test getting tools from a specific server."""
        manager = MCPManager(mock_config)
        # Mark server as active
        manager._active_servers["test-stdio"] = mock_config.servers[0]

        # Mock the session creation
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio client
                mock_stdio_context = AsyncMock()
                mock_stdio_context.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio_context.__aexit__ = AsyncMock(return_value=None)
                mock_stdio.return_value = mock_stdio_context
                
                # Setup session
                mock_session = AsyncMock()
                mock_session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([
                    {"name": "tool1", "description": "Test tool 1"},
                    {"name": "tool2", "description": "Test tool 2"},
                ]))
                
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_session_context
                
                tools = await manager.get_tools("test-stdio")

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tools_all_servers(self, mock_config):
        """Test getting tools from all connected servers."""
        manager = MCPManager(mock_config)

        # Mark two servers as active
        manager._active_servers["server1"] = {"name": "server1", "transport": "stdio", "command": ["node", "s1.js"]}
        manager._active_servers["server2"] = {"name": "server2", "transport": "stdio", "command": ["node", "s2.js"]}

        call_count = 0
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create different sessions for each server
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    if call_count == 0:
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": "tool1", "description": "Tool from server 1"}]))
                    else:
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": "tool2", "description": "Tool from server 2"}]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
                tools = await manager.get_tools()

        assert len(tools) == 2
        assert any(t["name"] == "tool1" for t in tools)
        assert any(t["name"] == "tool2" for t in tools)
        assert any(t.get("server") == "server1" for t in tools)
        assert any(t.get("server") == "server2" for t in tools)

    @pytest.mark.asyncio
    async def test_get_tools_disconnected_server(self, mock_config):
        """Test getting tools from a disconnected server."""
        manager = MCPManager(mock_config)

        with pytest.raises(
            MCPManagerError, match="Server 'test-stdio' is not connected"
        ):
            await manager.get_tools("test-stdio")

    @pytest.mark.asyncio
    async def test_get_resources(self, mock_config):
        """Test getting resources from servers."""
        manager = MCPManager(mock_config)
        # Mark server as active
        manager._active_servers["test-stdio"] = mock_config.servers[0]

        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio client
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Setup session
                mock_session = AsyncMock()
                mock_session.list_resources = AsyncMock(return_value=create_mock_list_resources_result([
                    {"uri": "resource://test", "name": "Test Resource"}
                ]))
                
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_session_context
                
                resources = await manager.get_resources("test-stdio")

        assert len(resources) == 1
        assert resources[0]["uri"] == "resource://test"

    @pytest.mark.asyncio
    async def test_get_prompts(self, mock_config):
        """Test getting prompts from servers."""
        manager = MCPManager(mock_config)
        # Mark server as active
        manager._active_servers["test-stdio"] = mock_config.servers[0]

        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio client
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Setup session
                mock_session = AsyncMock()
                mock_session.list_prompts = AsyncMock(return_value=create_mock_list_prompts_result([
                    {"name": "test-prompt", "description": "A test prompt"}
                ]))
                
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_session_context
                
                prompts = await manager.get_prompts("test-stdio")

        assert len(prompts) == 1
        assert prompts[0]["name"] == "test-prompt"

    @pytest.mark.asyncio
    async def test_call_tool(self, mock_config):
        """Test calling a tool on a server."""
        manager = MCPManager(mock_config)
        # Mark server as active
        manager._active_servers["test-stdio"] = mock_config.servers[0]

        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio client
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Setup session
                mock_session = AsyncMock()
                mock_session.call_tool = AsyncMock(return_value={
                    "content": [{"type": "text", "text": "Tool result"}]
                })
                
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_session_context
                
                result = await manager.call_tool("test-stdio", "tool1", {"arg": "value"})

        assert result["content"][0]["text"] == "Tool result"
        mock_session.call_tool.assert_called_once_with(
            "tool1", arguments={"arg": "value"}
        )

    @pytest.mark.asyncio
    async def test_read_resource(self, mock_config):
        """Test reading a resource from a server."""
        manager = MCPManager(mock_config)
        # Mark server as active
        manager._active_servers["test-stdio"] = mock_config.servers[0]

        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio client
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Setup session
                mock_session = AsyncMock()
                mock_session.read_resource = AsyncMock(return_value={
                    "contents": [{"type": "text", "text": "Resource content"}]
                })
                
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_session_context
                
                result = await manager.read_resource("test-stdio", "resource://test")

        assert result["contents"][0]["text"] == "Resource content"
        mock_session.read_resource.assert_called_once_with("resource://test")

    def test_get_sync_wrapper_methods(self, mock_config):
        """Test that sync wrapper methods exist for async operations."""
        manager = MCPManager(mock_config)

        # Check that sync wrappers exist
        assert hasattr(manager, "initialize_sync")
        assert hasattr(manager, "cleanup_sync")
        assert hasattr(manager, "connect_server_sync")
        assert hasattr(manager, "disconnect_server_sync")
        assert hasattr(manager, "get_tools_sync")
        assert hasattr(manager, "get_resources_sync")
        assert hasattr(manager, "get_prompts_sync")
        assert hasattr(manager, "call_tool_sync")
        assert hasattr(manager, "read_resource_sync")
