"""Test MCP manager functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig


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
    session.list_tools = AsyncMock(return_value={"tools": []})
    session.list_resources = AsyncMock(return_value={"resources": []})
    session.list_prompts = AsyncMock(return_value={"prompts": []})
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
            mock_config_class.return_value = MagicMock(servers=[])
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
        assert manager._exit_stack is not None

        # Test that calling initialize again doesn't create new stack
        first_stack = manager._exit_stack
        await manager.initialize()
        assert manager._exit_stack is first_stack

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_config):
        """Test manager cleanup."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock the exit stack aclose
        manager._exit_stack.aclose = AsyncMock()

        await manager.cleanup()

        manager._exit_stack.aclose.assert_called_once()
        assert manager._initialized is False
        assert len(manager._sessions) == 0
        assert len(manager._transports) == 0

    @pytest.mark.asyncio
    async def test_connect_stdio_server(self, mock_config, mock_client_session):
        """Test connecting to a stdio transport server."""
        manager = MCPManager(mock_config)

        with patch("src.mcp_manager.stdio_client"):
            with patch("src.mcp_manager.ClientSession"):
                # Mock the AsyncExitStack
                mock_exit_stack = AsyncMock()
                mock_exit_stack.enter_async_context = AsyncMock()

                # First call returns the stdio transport (read, write)
                mock_read, mock_write = AsyncMock(), AsyncMock()
                mock_exit_stack.enter_async_context.side_effect = [
                    (mock_read, mock_write),  # stdio_client result
                    mock_client_session,  # ClientSession result
                ]

                with patch(
                    "src.mcp_manager.AsyncExitStack",
                    return_value=mock_exit_stack,
                ):
                    await manager.initialize()
                    await manager.connect_server("test-stdio")

                assert "test-stdio" in manager._sessions
                assert manager._sessions["test-stdio"] == mock_client_session
                assert "test-stdio" in manager._transports
                mock_client_session.initialize.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.mcp_manager.HTTP_TRANSPORT_AVAILABLE", False)
    async def test_connect_http_server_not_available(self, mock_config):
        """Test connecting to HTTP transport server when httpx not available."""
        manager = MCPManager(mock_config)

        with pytest.raises(MCPManagerError, match="HTTP transport requires httpx"):
            await manager.connect_server("test-http")

    @pytest.mark.asyncio
    async def test_connect_nonexistent_server(self, mock_config):
        """Test connecting to a non-existent server."""
        manager = MCPManager(mock_config)

        with pytest.raises(MCPManagerError, match="Server 'nonexistent' not found"):
            await manager.connect_server("nonexistent")

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, mock_config, mock_client_session):
        """Test connecting to an already connected server."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        # Should not raise an error, just return existing session
        await manager.connect_server("test-stdio")
        assert manager._sessions["test-stdio"] == mock_client_session

    @pytest.mark.asyncio
    async def test_disconnect_server(self, mock_config, mock_client_session):
        """Test disconnecting from a server."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        await manager.disconnect_server("test-stdio")
        assert "test-stdio" not in manager._sessions

    @pytest.mark.asyncio
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
    async def test_get_tools_single_server(self, mock_config, mock_client_session):
        """Test getting tools from a specific server."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        mock_client_session.list_tools.return_value = {
            "tools": [
                {"name": "tool1", "description": "Test tool 1"},
                {"name": "tool2", "description": "Test tool 2"},
            ]
        }

        tools = await manager.get_tools("test-stdio")

        assert len(tools) == 2
        assert tools[0]["name"] == "tool1"
        mock_client_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tools_all_servers(self, mock_config):
        """Test getting tools from all connected servers."""
        manager = MCPManager(mock_config)

        # Create two mock sessions
        session1 = AsyncMock()
        session1.list_tools = AsyncMock(
            return_value={
                "tools": [{"name": "tool1", "description": "Tool from server 1"}]
            }
        )

        session2 = AsyncMock()
        session2.list_tools = AsyncMock(
            return_value={
                "tools": [{"name": "tool2", "description": "Tool from server 2"}]
            }
        )

        manager._sessions = {"server1": session1, "server2": session2}

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
    async def test_get_resources(self, mock_config, mock_client_session):
        """Test getting resources from servers."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        mock_client_session.list_resources.return_value = {
            "resources": [{"uri": "resource://test", "name": "Test Resource"}]
        }

        resources = await manager.get_resources("test-stdio")

        assert len(resources) == 1
        assert resources[0]["uri"] == "resource://test"

    @pytest.mark.asyncio
    async def test_get_prompts(self, mock_config, mock_client_session):
        """Test getting prompts from servers."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        mock_client_session.list_prompts.return_value = {
            "prompts": [{"name": "test-prompt", "description": "A test prompt"}]
        }

        prompts = await manager.get_prompts("test-stdio")

        assert len(prompts) == 1
        assert prompts[0]["name"] == "test-prompt"

    @pytest.mark.asyncio
    async def test_call_tool(self, mock_config, mock_client_session):
        """Test calling a tool on a server."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        mock_client_session.call_tool.return_value = {
            "content": [{"type": "text", "text": "Tool result"}]
        }

        result = await manager.call_tool("test-stdio", "tool1", {"arg": "value"})

        assert result["content"][0]["text"] == "Tool result"
        mock_client_session.call_tool.assert_called_once_with(
            "tool1", arguments={"arg": "value"}
        )

    @pytest.mark.asyncio
    async def test_read_resource(self, mock_config, mock_client_session):
        """Test reading a resource from a server."""
        manager = MCPManager(mock_config)
        manager._sessions["test-stdio"] = mock_client_session

        mock_client_session.read_resource.return_value = {
            "contents": [{"type": "text", "text": "Resource content"}]
        }

        result = await manager.read_resource("test-stdio", "resource://test")

        assert result["contents"][0]["text"] == "Resource content"
        mock_client_session.read_resource.assert_called_once_with("resource://test")

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
