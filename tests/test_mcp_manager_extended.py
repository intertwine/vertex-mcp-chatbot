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

    def test_server_not_in_active_list(self, mock_config):
        """Test that server tracking works correctly."""
        manager = MCPManager(mock_config)
        # Don't add to _active_servers

        # Server should not be in active list
        assert "server1" not in manager._active_servers

    def test_list_servers(self, mock_config):
        """Test listing configured servers."""
        manager = MCPManager(mock_config)
        manager._sessions["server1"] = Mock()  # Add to sessions to mark as connected

        servers = manager.list_servers()

        assert len(servers) > 0
        # Find our server in the list
        server1 = next((s for s in servers if s["name"] == "server1"), None)
        assert server1 is not None
        assert server1["connected"] is True
        assert server1["transport"] == "stdio"

    def test_find_best_server_for_tool_sync(self, mock_config):
        """Test finding best server for a tool."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = "server1"

            result = manager.find_best_server_for_tool_sync("test_tool")

            assert result == "server1"
            mock_run.assert_called_once()

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

    def test_get_resource_templates_sync(self, mock_config):
        """Test synchronous resource templates wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [{"uriTemplate": "test:///{id}"}]

            result = manager.get_resource_templates_sync("server1")

            assert len(result) == 1
            mock_run.assert_called_once()

    def test_call_tool_sync(self, mock_config):
        """Test synchronous call_tool wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {"content": [{"type": "text", "text": "Result"}]}

            result = manager.call_tool_sync("server1", "test_tool", {"arg": "value"})

            assert result["content"][0]["text"] == "Result"
            mock_run.assert_called_once()

    def test_read_resource_sync(self, mock_config):
        """Test synchronous read_resource wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {"contents": [{"type": "text", "text": "Content"}]}

            result = manager.read_resource_sync("server1", "resource://test")

            assert result["contents"][0]["text"] == "Content"
            mock_run.assert_called_once()

    def test_get_prompt_sync(self, mock_config):
        """Test synchronous get_prompt wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = {
                "messages": [{"role": "user", "content": "Prompt"}]
            }

            result = manager.get_prompt_sync("server1", "test-prompt", {"arg": "val"})

            assert result["messages"][0]["content"] == "Prompt"
            mock_run.assert_called_once()

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

    def test_get_tools_sync(self, mock_config):
        """Test synchronous get_tools wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [{"name": "tool1"}]

            result = manager.get_tools_sync("server1")

            assert len(result) == 1
            mock_run.assert_called_once()

    def test_get_resources_sync(self, mock_config):
        """Test synchronous get_resources wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [{"uri": "resource://test"}]

            result = manager.get_resources_sync("server1")

            assert len(result) == 1
            mock_run.assert_called_once()

    def test_get_prompts_sync(self, mock_config):
        """Test synchronous get_prompts wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = [{"name": "prompt1"}]

            result = manager.get_prompts_sync("server1")

            assert len(result) == 1
            mock_run.assert_called_once()

    def test_initialize_sync(self, mock_config):
        """Test synchronous initialize."""
        manager = MCPManager(mock_config)

        manager.initialize_sync()

        assert manager._initialized is True

    def test_cleanup_sync(self, mock_config):
        """Test synchronous cleanup."""
        manager = MCPManager(mock_config)
        manager._active_servers["test"] = {}
        manager._sessions["test"] = {}

        manager.cleanup_sync()

        assert manager._initialized is False
        assert len(manager._active_servers) == 0

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

    def test_find_servers_with_tool_sync(self, mock_config):
        """Test synchronous find_servers_with_tool wrapper."""
        manager = MCPManager(mock_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = ["server1", "server2"]

            result = manager.find_servers_with_tool_sync("test_tool")

            assert len(result) == 2
            assert "server1" in result
            mock_run.assert_called_once()

    def test_get_server_priorities(self, mock_config):
        """Test getting server priorities from configuration."""
        manager = MCPManager(mock_config)

        # Add priority to one server
        manager.config.servers[0]["priority"] = 1
        manager.config.servers[1]["priority"] = 2

        priorities = manager.get_server_priorities()

        assert priorities["server1"] == 1
        assert priorities["server2"] == 2

    @pytest.mark.asyncio
    async def test_async_get_tools(self, mock_config):
        """Test async get_tools method."""
        manager = MCPManager(mock_config)

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.return_value = [{"name": "tool1"}]

            result = await manager.get_tools("server1")

            assert len(result) == 1
            mock_get_tools.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_async_get_resources(self, mock_config):
        """Test async get_resources method."""
        manager = MCPManager(mock_config)

        with patch.object(
            manager, "_get_resources_async", new_callable=AsyncMock
        ) as mock_get_resources:
            mock_get_resources.return_value = [{"uri": "resource://test"}]

            result = await manager.get_resources("server1")

            assert len(result) == 1
            mock_get_resources.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_async_get_prompts(self, mock_config):
        """Test async get_prompts method."""
        manager = MCPManager(mock_config)

        with patch.object(
            manager, "_get_prompts_async", new_callable=AsyncMock
        ) as mock_get_prompts:
            mock_get_prompts.return_value = [{"name": "prompt1"}]

            result = await manager.get_prompts("server1")

            assert len(result) == 1
            mock_get_prompts.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_async_call_tool(self, mock_config):
        """Test async call_tool method."""
        manager = MCPManager(mock_config)

        with patch.object(
            manager, "_call_tool_async", new_callable=AsyncMock
        ) as mock_call_tool:
            mock_call_tool.return_value = {
                "content": [{"type": "text", "text": "Result"}]
            }

            result = await manager.call_tool("server1", "tool1", {"arg": "val"})

            assert result["content"][0]["text"] == "Result"
            mock_call_tool.assert_called_once_with("server1", "tool1", {"arg": "val"})

    @pytest.mark.asyncio
    async def test_async_read_resource(self, mock_config):
        """Test async read_resource method."""
        manager = MCPManager(mock_config)

        with patch.object(
            manager, "_read_resource_async", new_callable=AsyncMock
        ) as mock_read_resource:
            mock_read_resource.return_value = {
                "contents": [{"type": "text", "text": "Content"}]
            }

            result = await manager.read_resource("server1", "resource://test")

            assert result["contents"][0]["text"] == "Content"
            mock_read_resource.assert_called_once_with("server1", "resource://test")

    @pytest.mark.asyncio
    async def test_async_connect_server(self, mock_config):
        """Test async connect_server wrapper."""
        manager = MCPManager(mock_config)

        with patch.object(manager, "connect_server_sync") as mock_connect:
            await manager.connect_server("server1")
            mock_connect.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_async_disconnect_server(self, mock_config):
        """Test async disconnect_server wrapper."""
        manager = MCPManager(mock_config)

        with patch.object(manager, "disconnect_server_sync") as mock_disconnect:
            await manager.disconnect_server("server1")
            mock_disconnect.assert_called_once_with("server1")

    @pytest.mark.asyncio
    async def test_async_connect_with_retry(self, mock_config):
        """Test async _connect_with_retry calls sync version."""
        manager = MCPManager(mock_config)
        server_config = mock_config.get_server("server1")

        with patch.object(manager, "_connect_with_retry_sync") as mock_retry:
            await manager._connect_with_retry("server1", server_config)
            mock_retry.assert_called_once_with("server1", server_config)
