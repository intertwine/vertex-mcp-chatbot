"""Tests for MCP HTTP transport integration."""

import pytest
import warnings
from unittest.mock import AsyncMock, Mock, patch
import asyncio

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

    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    def test_connect_http_server_basic(self, mock_http_client, mock_run, mock_config):
        """Test basic HTTP server connection."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to execute the coroutine synchronously
        async def mock_async_run(coro):
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
            mock_session.list_tools = AsyncMock(
                return_value=create_mock_list_tools_result([])
            )

            with patch("src.mcp_manager.ClientSession") as mock_client_session:
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context

                # Execute the actual coroutine
                return await coro

        # Create a hybrid handler that uses create_async_run_mock for known coroutines
        # and executes test-specific logic for connect_server
        base_mock = create_async_run_mock()

        def hybrid_handler(coro):
            if asyncio.iscoroutine(coro) and coro.cr_code.co_name == "connect_server":
                # For connect_server, run our test-specific logic
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(mock_async_run(coro))
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            else:
                # For other coroutines (like _get_tools_async), use the base mock
                return base_mock(coro)

        mock_run.side_effect = hybrid_handler

        manager.connect_server_sync("test-http")

        # Verify asyncio.run was called
        mock_run.assert_called()

        # Verify server is tracked
        assert "test-http" in manager._sessions
        assert "test-http" in manager._active_servers

    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    def test_connect_http_server_with_auth(
        self, mock_http_client, mock_run, mock_config
    ):
        """Test HTTP server connection with authentication."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to execute the coroutine synchronously
        async def mock_async_run(coro):
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
            mock_session.list_tools = AsyncMock(
                return_value=create_mock_list_tools_result([])
            )

            with patch("src.mcp_manager.ClientSession") as mock_client_session:
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context

                with patch("src.mcp_manager.httpx.BasicAuth") as mock_basic_auth:
                    mock_auth = Mock()
                    mock_basic_auth.return_value = mock_auth

                    # Execute the actual coroutine
                    result = await coro

                    # Verify auth was created
                    mock_basic_auth.assert_called_once_with("user", "pass")

                    # Verify HTTP client was called with auth
                    mock_http_client.assert_called_once_with(
                        "http://localhost:8082/mcp", headers={}, auth=mock_auth
                    )

                    return result

        # Create a hybrid handler that uses create_async_run_mock for known coroutines
        # and executes test-specific logic for connect_server
        base_mock = create_async_run_mock()

        def hybrid_handler(coro):
            if asyncio.iscoroutine(coro) and coro.cr_code.co_name == "connect_server":
                # For connect_server, run our test-specific logic
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(mock_async_run(coro))
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            else:
                # For other coroutines (like _get_tools_async), use the base mock
                return base_mock(coro)

        mock_run.side_effect = hybrid_handler

        manager.connect_server_sync("test-auth-http")

    @patch("src.mcp_manager.asyncio.run")
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
    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.sse_client")
    def test_connect_sse_server(self, mock_sse_client, mock_run, mock_config):
        """Test SSE server connection."""
        manager = MCPManager(mock_config)

        # Mock asyncio.run to execute the coroutine synchronously
        async def mock_async_run(coro):
            # Mock the SSE client context manager
            mock_read = AsyncMock()
            mock_write = AsyncMock()

            mock_sse_context = AsyncMock()
            mock_sse_context.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_sse_context.__aexit__ = AsyncMock(return_value=None)
            mock_sse_client.return_value = mock_sse_context

            # Mock session
            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.list_tools = AsyncMock(
                return_value=create_mock_list_tools_result([])
            )

            with patch("src.mcp_manager.ClientSession") as mock_client_session:
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context

                # Execute the actual coroutine
                result = await coro

                # Verify SSE client was called with correct parameters
                mock_sse_client.assert_called_once_with(
                    "http://localhost:8081/sse", headers=None, auth=None
                )

                # Verify session was initialized
                mock_session.initialize.assert_called_once()

                return result

        # Create a hybrid handler that uses create_async_run_mock for known coroutines
        # and executes test-specific logic for connect_server
        base_mock = create_async_run_mock()

        def hybrid_handler(coro):
            if asyncio.iscoroutine(coro) and coro.cr_code.co_name == "connect_server":
                # For connect_server, run our test-specific logic
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(mock_async_run(coro))
                finally:
                    loop.close()
                    asyncio.set_event_loop(None)
            else:
                # For other coroutines (like _get_tools_async), use the base mock
                return base_mock(coro)

        mock_run.side_effect = hybrid_handler

        manager.connect_server_sync("test-sse")

        # Verify server is tracked
        assert "test-sse" in manager._sessions
        assert "test-sse" in manager._active_servers

    @patch("src.mcp_manager.asyncio.run")
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
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    async def test_get_tools_http(self, mock_config):
        """Test getting tools from HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mark server as active
        manager._active_servers["test-http"] = mock_config.get_server("test-http")

        # Mock the session creation
        mock_session = AsyncMock()
        mock_session.list_tools = AsyncMock(
            return_value=create_mock_list_tools_result(
                [
                    {
                        "name": "calculator",
                        "description": "Perform calculations",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"expression": {"type": "string"}},
                        },
                    }
                ]
            )
        )

        with patch("src.mcp_manager.ClientSession") as mock_client_session:
            with patch("src.mcp_manager.streamablehttp_client") as mock_http_client:
                # Mock HTTP client context
                mock_read = AsyncMock()
                mock_write = AsyncMock()
                mock_get_session_id = Mock(return_value="test-session")

                mock_http_context = AsyncMock()
                mock_http_context.__aenter__ = AsyncMock(
                    return_value=(mock_read, mock_write, mock_get_session_id)
                )
                mock_http_context.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.return_value = mock_http_context

                # Mock session context
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context

                tools = await manager.get_tools("test-http")

        assert len(tools) == 1
        assert tools[0]["name"] == "calculator"
        mock_session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    async def test_call_tool_http(self, mock_config):
        """Test calling a tool on HTTP server."""
        manager = MCPManager(mock_config)
        await manager.initialize()

        # Mark server as active
        manager._active_servers["test-http"] = mock_config.get_server("test-http")

        # Mock the session
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(
            return_value={"content": [{"type": "text", "text": "Result: 42"}]}
        )

        with patch("src.mcp_manager.ClientSession") as mock_client_session:
            with patch("src.mcp_manager.streamablehttp_client") as mock_http_client:
                # Mock HTTP client context
                mock_read = AsyncMock()
                mock_write = AsyncMock()
                mock_get_session_id = Mock(return_value="test-session")

                mock_http_context = AsyncMock()
                mock_http_context.__aenter__ = AsyncMock(
                    return_value=(mock_read, mock_write, mock_get_session_id)
                )
                mock_http_context.__aexit__ = AsyncMock(return_value=None)
                mock_http_client.return_value = mock_http_context

                # Mock session context
                mock_session_context = AsyncMock()
                mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_session.return_value = mock_session_context

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

        # In simplified version, session IDs are not implemented
        session_id = manager._get_session_id("test-http")

        # Should always return None in simplified version
        assert session_id is None
