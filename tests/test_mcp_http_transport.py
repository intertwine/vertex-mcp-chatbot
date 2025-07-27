"""Tests for MCP HTTP transport integration."""

import pytest
import warnings
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig


@pytest.fixture
def mock_config():
    """Create a mock MCP configuration with HTTP/SSE servers."""
    config = Mock()
    config.servers = [
        {
            "name": "test-http",
            "transport": "http",
            "url": "http://localhost:8080/mcp",
            "headers": {"Authorization": "Bearer test-token"},
        },
        {
            "name": "test-sse",
            "transport": "sse",
            "url": "http://localhost:8081/sse",
        },
        {
            "name": "test-auth-http",
            "transport": "http",
            "url": "http://localhost:8082/mcp",
            "auth": {
                "type": "basic",
                "username": "user",
                "password": "pass",
            },
        },
    ]

    def get_server(name):
        for server in config.servers:
            if server["name"] == name:
                return server
        return None

    config.get_server = get_server
    return config


class TestHTTPTransport:
    """Test HTTP transport functionality."""

    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    async def test_connect_http_server_basic(self, mock_http_client, mock_config):
        """Test basic HTTP server connection."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock the HTTP client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock(return_value="test-session-123")

        mock_http_context = AsyncMock()
        mock_http_context.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write, mock_get_session_id)
        )
        mock_http_context.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.return_value = mock_http_context

        # Mock session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        with patch("src.mcp_manager.ClientSession") as mock_client_session:
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_session.return_value = mock_session_context

            await manager.connect_server("test-http")

        # Verify HTTP client was called with correct parameters
        mock_http_client.assert_called_once_with(
            "http://localhost:8080/mcp",
            headers={"Authorization": "Bearer test-token"},
            auth=None,
        )

        # Verify session was initialized
        mock_session.initialize.assert_called_once()

        # Verify server is tracked
        assert "test-http" in manager._sessions
        assert manager._sessions["test-http"] == mock_session
        assert "test-http" in manager._transports

    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    async def test_connect_http_server_with_auth(self, mock_http_client, mock_config):
        """Test HTTP server connection with authentication."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock the HTTP client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock(return_value=None)

        mock_http_context = AsyncMock()
        mock_http_context.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write, mock_get_session_id)
        )
        mock_http_context.__aexit__ = AsyncMock(return_value=None)
        mock_http_client.return_value = mock_http_context

        # Mock session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        with patch("src.mcp_manager.ClientSession") as mock_client_session:
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_session.return_value = mock_session_context

            with patch("src.mcp_manager.httpx.BasicAuth") as mock_basic_auth:
                mock_auth = Mock()
                mock_basic_auth.return_value = mock_auth

                await manager.connect_server("test-auth-http")

        # Verify auth was created
        mock_basic_auth.assert_called_once_with("user", "pass")

        # Verify HTTP client was called with auth
        mock_http_client.assert_called_once_with(
            "http://localhost:8082/mcp", headers=None, auth=mock_auth
        )

    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    async def test_connect_http_server_failure(self, mock_http_client, mock_config):
        """Test HTTP server connection failure."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock HTTP client to raise exception
        mock_http_client.side_effect = Exception("Connection failed")

        with pytest.raises(
            MCPManagerError, match="Failed to connect to server 'test-http'"
        ):
            await manager.connect_server("test-http")

        # Verify server is not tracked
        assert "test-http" not in manager._sessions
        assert "test-http" not in manager._transports

    def test_connect_http_server_sync(self, mock_config):
        """Test synchronous HTTP server connection."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            manager.connect_server_sync("test-http")

            # Verify asyncio.run was called with the correct coroutine
            mock_run.assert_called_once()
            args = mock_run.call_args[0]
            assert len(args) == 1
            # The argument should be a coroutine for connect_server
            assert hasattr(args[0], "__await__")


class TestSSETransport:
    """Test SSE transport functionality."""

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("src.mcp_manager.sse_client")
    async def test_connect_sse_server(self, mock_sse_client, mock_config):
        """Test SSE server connection."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock the SSE client context manager
        mock_read = AsyncMock()
        mock_write = AsyncMock()

        mock_sse_context = AsyncMock()
        mock_sse_context.__aenter__ = AsyncMock(return_value=(mock_read, mock_write))
        mock_sse_context.__aexit__ = AsyncMock(return_value=None)
        mock_sse_client.return_value = mock_sse_context

        # Mock session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        with patch("src.mcp_manager.ClientSession") as mock_client_session:
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_session.return_value = mock_session_context

            await manager.connect_server("test-sse")

        # Verify SSE client was called with correct parameters
        mock_sse_client.assert_called_once_with(
            "http://localhost:8081/sse", headers=None, auth=None
        )

        # Verify session was initialized
        mock_session.initialize.assert_called_once()

        # Verify server is tracked
        assert "test-sse" in manager._sessions
        assert manager._sessions["test-sse"] == mock_session
        assert "test-sse" in manager._transports

    @pytest.mark.asyncio
    @patch("src.mcp_manager.sse_client")
    async def test_connect_sse_server_failure(self, mock_sse_client, mock_config):
        """Test SSE server connection failure."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock SSE client to raise exception
        mock_sse_client.side_effect = Exception("SSE connection failed")

        with pytest.raises(
            MCPManagerError, match="Failed to connect to server 'test-sse'"
        ):
            await manager.connect_server("test-sse")

        # Verify server is not tracked
        assert "test-sse" not in manager._sessions
        assert "test-sse" not in manager._transports


class TestHTTPOperations:
    """Test operations over HTTP transport."""

    @pytest.mark.asyncio
    async def test_get_tools_http(self, mock_config):
        """Test getting tools from HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock an existing HTTP session
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(
            return_value={
                "tools": [
                    {
                        "name": "calculator",
                        "description": "Perform calculations",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                        },
                    }
                ]
            }
        )
        manager._sessions["test-http"] = mock_session

        tools = await manager.get_tools("test-http")

        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_tool_http(self, mock_config):
        """Test calling a tool on HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock an existing HTTP session
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "Result: 42"}]}
        )
        manager._sessions["test-http"] = mock_session

        result = await manager.call_tool(
            "test-http", "calculator", {"expression": "21 * 2"}
        )

        assert result["content"][0]["text"] == "Result: 42"
        mock_session.call_tool.assert_called_once_with(
            "calculator", arguments={"expression": "21 * 2"}
        )

    @pytest.mark.asyncio
    async def test_get_session_id_callback(self, mock_config):
        """Test session ID callback functionality."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mock session ID callback
        mock_get_session_id = Mock(return_value="session-abc-123")
        manager._session_id_callbacks["test-http"] = mock_get_session_id

        session_id = manager._get_session_id("test-http")

        assert session_id == "session-abc-123"
        mock_get_session_id.assert_called_once()
