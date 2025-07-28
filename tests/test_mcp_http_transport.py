"""Tests for MCP HTTP transport integration."""

import asyncio
import warnings
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_config import MCPConfig
from src.mcp_manager import MCPManager, MCPManagerError
from tests.mock_mcp_types import (
    create_mock_list_prompts_result,
    create_mock_list_resources_result,
    create_mock_list_tools_result,
)
from tests.test_async_utils import create_async_run_mock

# Suppress runtime warnings about unawaited coroutines in this test module
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


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

    @patch("asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    def test_connect_http_server_basic(self, mock_http_client, mock_run, mock_config):
        """Test basic HTTP server connection."""
        manager = MCPManager(mock_config)

        # Use the simple async run mock that doesn't actually run async code
        mock_run.side_effect = create_async_run_mock(
            {"_get_tools_async": lambda: []}  # Return empty tools list
        )

        # We don't need to mock the HTTP client details since asyncio.run is mocked
        # The connection will succeed because _get_tools_async returns successfully

        manager.connect_server_sync("test-http")

        # Verify asyncio.run was called
        mock_run.assert_called()

        # Verify server is tracked
        assert "test-http" in manager._sessions
        assert "test-http" in manager._active_servers

    @patch("asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    @patch("src.mcp_manager.httpx.BasicAuth")
    def test_connect_http_server_with_auth(
        self, mock_basic_auth, mock_http_client, mock_run, mock_config
    ):
        """Test HTTP server connection with authentication."""
        manager = MCPManager(mock_config)

        # Use the simple async run mock
        mock_run.side_effect = create_async_run_mock(
            {"_get_tools_async": lambda: []}  # Return empty tools list
        )

        # Mock the auth
        mock_auth = Mock()
        mock_basic_auth.return_value = mock_auth

        manager.connect_server_sync("test-auth-http")

        # Verify asyncio.run was called
        mock_run.assert_called()

        # Server should be tracked
        assert "test-auth-http" in manager._sessions

    @patch("asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    def test_connect_http_server_failure(self, mock_http_client, mock_run, mock_config):
        """Test HTTP server connection failure."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to raise exception
        mock_run.side_effect = Exception("Connection failed")

        with pytest.raises(
            MCPManagerError, match="Failed to connect to server 'test-http'"
        ):
            manager.connect_server_sync("test-http")

        # Verify server is not tracked
        assert "test-http" not in manager._sessions
        assert "test-http" not in manager._active_servers

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_connect_http_server_sync(self, mock_config):
        """Test synchronous HTTP server connection."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run", create_async_run_mock()):
            # Mark server as active for test
            manager._active_servers["test-http"] = mock_config.servers[0]
            manager.connect_server_sync("test-http")

            # Verify server was processed successfully
            assert "test-http" in manager._active_servers


class TestSSETransport:
    """Test SSE transport functionality."""

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("asyncio.run")
    @patch("src.mcp_manager.sse_client")
    def test_connect_sse_server(self, mock_sse_client, mock_run, mock_config):
        """Test SSE server connection."""
        manager = MCPManager(mock_config)

        # Use the simple async run mock
        mock_run.side_effect = create_async_run_mock(
            {"_get_tools_async": lambda: []}  # Return empty tools list
        )

        manager.connect_server_sync("test-sse")

        # Verify server is tracked
        assert "test-sse" in manager._sessions
        assert "test-sse" in manager._active_servers

    @patch("asyncio.run")
    @patch("src.mcp_manager.sse_client")
    def test_connect_sse_server_failure(self, mock_sse_client, mock_run, mock_config):
        """Test SSE server connection failure."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to raise exception
        mock_run.side_effect = Exception("SSE connection failed")

        with pytest.raises(
            MCPManagerError, match="Failed to connect to server 'test-sse'"
        ):
            manager.connect_server_sync("test-sse")

        # Verify server is not tracked
        assert "test-sse" not in manager._sessions
        assert "test-sse" not in manager._active_servers


class TestHTTPOperations:
    """Test operations over HTTP transport."""

    @pytest.mark.asyncio
    async def test_get_tools_http(self, mock_config):
        """Test getting tools from HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mark server as active
        manager._active_servers["test-http"] = mock_config.get_server("test-http")

        # Create the expected tool result
        expected_tools = [
            {
                "name": "calculator",
                "description": "Perform calculations",
                "inputSchema": {
                    "type": "object",
                    "properties": {"expression": {"type": "string"}},
                },
                "server": "test-http",
            }
        ]

        # Patch the _get_tools_async method directly
        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.return_value = expected_tools

            tools = await manager.get_tools("test-http")

            assert len(tools) == 1
            assert tools[0]["name"] == "calculator"
            assert tools[0]["server"] == "test-http"
            mock_get_tools.assert_called_once_with("test-http")

    @pytest.mark.asyncio
    async def test_call_tool_http(self, mock_config):
        """Test calling a tool on HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mark server as active
        manager._active_servers["test-http"] = mock_config.get_server("test-http")

        # Expected result
        expected_result = {"content": [{"type": "text", "text": "Result: 42"}]}

        # Patch the _call_tool_async method directly
        with patch.object(
            manager, "_call_tool_async", new_callable=AsyncMock
        ) as mock_call_tool:
            mock_call_tool.return_value = expected_result

            result = await manager.call_tool(
                "test-http", "calculator", {"expression": "21 * 2"}
            )

            assert result["content"][0]["text"] == "Result: 42"
            mock_call_tool.assert_called_once_with(
                "test-http", "calculator", {"expression": "21 * 2"}
            )

    @pytest.mark.asyncio
    async def test_get_session_id_callback(self, mock_config):
        """Test session ID callback functionality."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # In simplified version, session IDs are not implemented
        session_id = manager._get_session_id("test-http")

        # Should always return None in simplified version
        assert session_id is None
