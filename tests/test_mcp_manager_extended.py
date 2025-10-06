"""Extended tests for MCP manager to improve coverage."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
    """Create a mock MCP configuration."""
    config = Mock()
    config.servers = [
        {
            "name": "server1",
            "transport": "stdio",
            "command": ["python", "server1.py"],
        },
        {
            "name": "server2",
            "transport": "stdio",
            "command": ["python", "server2.py"],
        },
    ]

    def get_server(name):
        for server in config.servers:
            if server["name"] == name:
                return server
        return None

    config.get_server = get_server
    return config


class TestMCPManagerExtended:
    """Extended test suite for MCP Manager coverage."""

    @pytest.mark.asyncio
    async def test_create_session_stdio(self, mock_config):
        """Test creating a stdio session."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        with patch("src.mcp_manager.stdio_client") as mock_stdio:
            # Mock the stdio client context manager
            mock_read = AsyncMock()
            mock_write = AsyncMock()
            mock_session = AsyncMock()
            mock_session.initialize = AsyncMock()
            mock_session.list_tools = AsyncMock(
                return_value=create_mock_list_tools_result([])
            )

            # Create async context manager mocks
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=(mock_read, mock_write)
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            with patch("src.mcp_manager.ClientSession") as mock_client_session:
                mock_client_session.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_client_session.return_value.__aexit__ = AsyncMock(
                    return_value=None
                )

                # Use the session
                async with manager._create_session("server1") as session:
                    assert session == mock_session
                    # Verify initialization was called
                    mock_session.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_http_with_basic_auth(self, mock_config):
        """Test creating an HTTP session with basic auth."""
        mock_config.servers.append(
            {
                "name": "auth-server",
                "transport": "http",
                "url": "http://localhost:8080",
                "auth": {
                    "type": "basic",
                    "username": "user",
                    "password": "pass",
                },
            }
        )

        manager = MCPManager(mock_config)
        manager._active_servers["auth-server"] = mock_config.get_server("auth-server")

        with patch("src.mcp_manager.streamablehttp_client") as mock_http:
            with patch("src.mcp_manager.httpx.BasicAuth") as mock_basic_auth:
                # Mock the HTTP client context manager
                mock_read = AsyncMock()
                mock_write = AsyncMock()
                mock_session = AsyncMock()
                mock_session.initialize = AsyncMock()

                mock_http.return_value.__aenter__ = AsyncMock(
                    return_value=(mock_read, mock_write, None)
                )
                mock_http.return_value.__aexit__ = AsyncMock(return_value=None)

                with patch("src.mcp_manager.ClientSession") as mock_client_session:
                    mock_client_session.return_value.__aenter__ = AsyncMock(
                        return_value=mock_session
                    )
                    mock_client_session.return_value.__aexit__ = AsyncMock(
                        return_value=None
                    )

                    # Use the session
                    async with manager._create_session("auth-server") as session:
                        assert session == mock_session
                        # Verify basic auth was created
                        mock_basic_auth.assert_called_once_with("user", "pass")

    @pytest.mark.asyncio
    async def test_create_session_sse_with_auth(self, mock_config):
        """Test creating an SSE session with authentication."""
        mock_config.servers.append(
            {
                "name": "sse-server",
                "transport": "sse",
                "url": "http://localhost:8081/sse",
                "auth": {
                    "type": "basic",
                    "username": "user",
                    "password": "pass",
                },
            }
        )

        manager = MCPManager(mock_config)
        manager._active_servers["sse-server"] = mock_config.get_server("sse-server")

        with patch("src.mcp_manager.sse_client") as mock_sse:
            with patch("src.mcp_manager.httpx.BasicAuth") as mock_basic_auth:
                # Mock the SSE client context manager
                mock_read = AsyncMock()
                mock_write = AsyncMock()
                mock_session = AsyncMock()
                mock_session.initialize = AsyncMock()

                mock_sse.return_value.__aenter__ = AsyncMock(
                    return_value=(mock_read, mock_write)
                )
                mock_sse.return_value.__aexit__ = AsyncMock(return_value=None)

                with patch("src.mcp_manager.ClientSession") as mock_client_session:
                    mock_client_session.return_value.__aenter__ = AsyncMock(
                        return_value=mock_session
                    )
                    mock_client_session.return_value.__aexit__ = AsyncMock(
                        return_value=None
                    )

                    # Use the session
                    async with manager._create_session("sse-server") as session:
                        assert session == mock_session
                        # Verify basic auth was created
                        mock_basic_auth.assert_called_once_with("user", "pass")

    @pytest.mark.asyncio
    async def test_create_session_unknown_transport(self, mock_config):
        """Test creating a session with unknown transport raises error."""
        mock_config.servers.append(
            {
                "name": "unknown-server",
                "transport": "websocket",  # Unknown transport
                "url": "ws://localhost:8080",
            }
        )

        manager = MCPManager(mock_config)
        manager._active_servers["unknown-server"] = mock_config.get_server(
            "unknown-server"
        )

        with pytest.raises(MCPManagerError, match="Unknown transport type: websocket"):
            async with manager._create_session("unknown-server"):
                pass

    @pytest.mark.asyncio
    async def test_get_resource_templates(self, mock_config):
        """Test getting resource templates from a server."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        expected_templates = [
            {
                "uriTemplate": "file:///{path}",
                "name": "File Template",
                "description": "Access files",
                "mimeType": "application/octet-stream",
                "server": "server1",
            }
        ]

        with patch.object(
            manager, "_get_resource_templates_async", new_callable=AsyncMock
        ) as mock_get_templates:
            mock_get_templates.return_value = expected_templates

            templates = await manager._get_resource_templates_async("server1")

            assert len(templates) == 1
            assert templates[0]["uriTemplate"] == "file:///{path}"

    @pytest.mark.asyncio
    async def test_broadcast_operation_list_tools(self, mock_config):
        """Test broadcast operation for listing tools."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")
        manager._active_servers["server2"] = mock_config.get_server("server2")

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.side_effect = [
                [{"name": "tool1", "server": "server1"}],
                [{"name": "tool2", "server": "server2"}],
            ]

            results = await manager.broadcast_operation("list_tools")

            assert len(results) == 2
            assert results[0][0] == "server1"
            assert results[0][1]["tools"][0]["name"] == "tool1"
            assert results[1][0] == "server2"
            assert results[1][1]["tools"][0]["name"] == "tool2"

    @pytest.mark.asyncio
    async def test_broadcast_operation_list_resources(self, mock_config):
        """Test broadcast operation for listing resources."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        with patch.object(
            manager, "_get_resources_async", new_callable=AsyncMock
        ) as mock_get_resources:
            mock_get_resources.return_value = [
                {"uri": "resource://test", "server": "server1"}
            ]

            results = await manager.broadcast_operation("list_resources")

            assert len(results) == 1
            assert results[0][0] == "server1"
            assert results[0][1][0]["uri"] == "resource://test"

    @pytest.mark.asyncio
    async def test_broadcast_operation_list_prompts(self, mock_config):
        """Test broadcast operation for listing prompts."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        with patch.object(
            manager, "_get_prompts_async", new_callable=AsyncMock
        ) as mock_get_prompts:
            mock_get_prompts.return_value = [{"name": "prompt1", "server": "server1"}]

            results = await manager.broadcast_operation("list_prompts")

            assert len(results) == 1
            assert results[0][0] == "server1"
            assert results[0][1][0]["name"] == "prompt1"

    @pytest.mark.asyncio
    async def test_broadcast_operation_unknown(self, mock_config):
        """Test broadcast operation with unknown operation."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        results = await manager.broadcast_operation("unknown_operation")

        # Should return None for unknown operations
        assert len(results) == 1
        assert results[0][1] is None

    @pytest.mark.asyncio
    async def test_broadcast_operation_with_failure(self, mock_config):
        """Test broadcast operation handles server failures."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")
        manager._active_servers["server2"] = mock_config.get_server("server2")

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            # First server succeeds, second fails
            mock_get_tools.side_effect = [
                [{"name": "tool1"}],
                Exception("Server error"),
            ]

            results = await manager.broadcast_operation("list_tools")

            assert len(results) == 2
            assert results[0][1]["tools"][0]["name"] == "tool1"
            assert results[1][1] is None  # Failed server returns None

    def test_broadcast_operation_sync(self, mock_config):
        """Test synchronous broadcast operation wrapper."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [("server1", {"tools": [{"name": "tool1"}]})]

            results = manager.broadcast_operation_sync("list_tools")

            assert len(results) == 1
            assert results[0][0] == "server1"
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_token_valid(self, mock_config):
        """Test OAuth token validation."""
        manager = MCPManager(mock_config)

        # Token without expiration should be valid
        token_no_expiry = {"access_token": "test"}
        assert manager._is_token_valid(token_no_expiry) is True

        # Token with future expiration should be valid
        future_expiry = datetime.now().timestamp() + 3600
        token_valid = {"access_token": "test", "expires_at": future_expiry}
        assert manager._is_token_valid(token_valid) is True

        # Token with past expiration should be invalid
        past_expiry = datetime.now().timestamp() - 3600
        token_expired = {"access_token": "test", "expires_at": past_expiry}
        assert manager._is_token_valid(token_expired) is False

    def test_get_retry_config_defaults(self, mock_config):
        """Test getting retry configuration with defaults."""
        manager = MCPManager(mock_config)

        server_config = {"name": "test", "transport": "stdio"}
        retry_config = manager._get_retry_config(server_config)

        assert retry_config["max_attempts"] == 3
        assert retry_config["initial_delay"] == 1.0
        assert retry_config["max_delay"] == 60.0
        assert retry_config["exponential_base"] == 2.0
        assert retry_config["jitter"] is True

    def test_get_retry_config_custom(self, mock_config):
        """Test getting retry configuration with custom values."""
        manager = MCPManager(mock_config)

        server_config = {
            "name": "test",
            "transport": "stdio",
            "retry": {
                "max_attempts": 5,
                "initial_delay": 2.0,
                "max_delay": 120.0,
            },
        }
        retry_config = manager._get_retry_config(server_config)

        assert retry_config["max_attempts"] == 5
        assert retry_config["initial_delay"] == 2.0
        assert retry_config["max_delay"] == 120.0
        assert retry_config["exponential_base"] == 2.0  # Default

    def test_calculate_backoff_delay(self, mock_config):
        """Test exponential backoff delay calculation."""
        manager = MCPManager(mock_config)

        # Test basic exponential backoff
        delay1 = manager._calculate_backoff_delay(0, 1.0, 2.0, 60.0, False)
        assert delay1 == 1.0

        delay2 = manager._calculate_backoff_delay(1, 1.0, 2.0, 60.0, False)
        assert delay2 == 2.0

        delay3 = manager._calculate_backoff_delay(2, 1.0, 2.0, 60.0, False)
        assert delay3 == 4.0

        # Test max delay cap
        delay_max = manager._calculate_backoff_delay(10, 1.0, 2.0, 60.0, False)
        assert delay_max == 60.0

        # Test with jitter (should be close to base but not exact)
        delay_jitter = manager._calculate_backoff_delay(1, 1.0, 2.0, 60.0, True)
        assert 1.0 <= delay_jitter <= 3.0  # 2.0 ± 50%

    @pytest.mark.asyncio
    async def test_async_method_wrappers(self, mock_config):
        """Test async method wrappers."""
        manager = MCPManager(mock_config)

        # Test initialize
        await manager.initialize()
        assert manager._initialized is True

        # Test cleanup
        manager._active_servers["test"] = {}
        manager._sessions["test"] = {}
        await manager.cleanup()
        assert manager._initialized is False
        assert len(manager._active_servers) == 0

        # Test connect_server (async wrapper)
        with patch.object(manager, "connect_server_sync") as mock_connect:
            await manager.connect_server("server1")
            mock_connect.assert_called_once_with("server1")

        # Test disconnect_server (async wrapper)
        with patch.object(manager, "disconnect_server_sync") as mock_disconnect:
            await manager.disconnect_server("server1")
            mock_disconnect.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_compatibility_safe_methods(self, mock_config):
        """Test compatibility safe methods."""
        manager = MCPManager(mock_config)

        # These should always return None
        result = await manager._get_tools_safe(None)
        assert result is None

        result = await manager._get_resources_safe(None)
        assert result is None

        result = await manager._get_prompts_safe(None)
        assert result is None

    def test_get_session_id(self, mock_config):
        """Test getting session ID (not implemented in simplified version)."""
        manager = MCPManager(mock_config)

        session_id = manager._get_session_id("test-server")
        assert session_id is None

    @pytest.mark.asyncio
    async def test_get_prompt_with_arguments(self, mock_config):
        """Test getting a prompt with arguments."""
        manager = MCPManager(mock_config)
        manager._active_servers["server1"] = mock_config.get_server("server1")

        expected_result = {
            "messages": [
                {
                    "role": "user",
                    "content": "Test prompt with arg: value",
                }
            ]
        }

        with patch.object(
            manager, "_get_prompt_async", new_callable=AsyncMock
        ) as mock_get_prompt:
            mock_get_prompt.return_value = expected_result

            result = await manager.get_prompt(
                "server1", "test-prompt", {"arg": "value"}
            )

            assert result["messages"][0]["content"] == "Test prompt with arg: value"
            mock_get_prompt.assert_called_once_with(
                "server1", "test-prompt", {"arg": "value"}
            )
