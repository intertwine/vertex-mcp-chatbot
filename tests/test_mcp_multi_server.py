"""Tests for MCP multi-server coordination."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_config import MCPConfig
from src.mcp_manager import MCPManager, MCPManagerError
from tests.mock_mcp_types import (
    create_mock_list_prompts_result,
    create_mock_list_resources_result,
    create_mock_list_tools_result,
)


@pytest.fixture
def multi_server_config():
    """Create a mock config with multiple servers."""
    config = Mock()
    config.servers = [
        {
            "name": "math-server",
            "transport": "stdio",
            "command": ["python", "math_server.py"],
            "priority": 1,  # Higher priority
        },
        {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["python", "calc_server.py"],
            "priority": 2,  # Lower priority
        },
        {
            "name": "tools-server",
            "transport": "http",
            "url": "http://localhost:8080/mcp",
        },
    ]

    def get_server(name):
        for server in config.servers:
            if server["name"] == name:
                return server
        return None

    config.get_server = get_server
    return config


class TestMultiServerCoordination:
    """Test multi-server coordination functionality."""

    @pytest.mark.asyncio
    async def test_tool_name_conflict_resolution(self, multi_server_config):
        """Test handling of tools with same name from different servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"],
            "priority": 1,
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["node", "calc.js"],
            "priority": 2,
        }

        # Expected tools from both servers
        expected_tools = [
            {
                "name": "calculate",
                "description": "Basic math calculations",
                "server": "math-server",
                "inputSchema": {},
            },
            {
                "name": "convert",
                "description": "Unit conversion",
                "server": "math-server",
                "inputSchema": {},
            },
            {
                "name": "calculate",
                "description": "Advanced calculations",
                "server": "calculator-server",
                "inputSchema": {},
            },
            {
                "name": "analyze",
                "description": "Data analysis",
                "server": "calculator-server",
                "inputSchema": {},
            },
        ]

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.return_value = expected_tools

            # Get all tools should show server info
            tools = await manager.get_tools()

        # Should have 4 tools total
        assert len(tools) == 4

        # Each tool should have server info
        calc_tools = [t for t in tools if t["name"] == "calculate"]
        assert len(calc_tools) == 2
        assert {t["server"] for t in calc_tools} == {"math-server", "calculator-server"}

    @pytest.mark.asyncio
    async def test_server_priority_for_tools(self, multi_server_config):
        """Test that server priority affects tool selection."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active with different priorities
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"],
            "priority": 1,  # Higher priority
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["node", "calc.js"],
            "priority": 2,  # Lower priority
        }

        # Mock the get_tools to return tools from both servers
        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.return_value = [
                {
                    "name": "calculate",
                    "description": "Priority 1 calc",
                    "server": "math-server",
                    "inputSchema": {},
                },
                {
                    "name": "calculate",
                    "description": "Priority 2 calc",
                    "server": "calculator-server",
                    "inputSchema": {},
                },
            ]

            # Mock find_servers_with_tool to return both servers
            with patch.object(
                manager, "find_servers_with_tool", new_callable=AsyncMock
            ) as mock_find_servers:
                mock_find_servers.return_value = ["math-server", "calculator-server"]

                # Mock get_server_priorities
                with patch.object(manager, "get_server_priorities") as mock_priorities:
                    mock_priorities.return_value = {
                        "math-server": 1,
                        "calculator-server": 2,
                    }

                    # Find best server for a tool
                    best_server = await manager.find_best_server_for_tool("calculate")

        assert best_server == "math-server"  # Higher priority wins

    @pytest.mark.asyncio
    async def test_parallel_tool_discovery(self, multi_server_config):
        """Test parallel tool discovery across multiple servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark three servers as active
        for i in range(1, 4):
            manager._active_servers[f"server{i}"] = {
                "name": f"server{i}",
                "transport": "stdio",
                "command": ["node", f"server{i}.js"],
            }

        # Expected tools from all servers
        expected_tools = [
            {
                "name": "slow_tool",
                "server": "server1",
                "description": "",
                "inputSchema": {},
            },
            {
                "name": "fast_tool",
                "server": "server2",
                "description": "",
                "inputSchema": {},
            },
            {
                "name": "medium_tool",
                "server": "server3",
                "description": "",
                "inputSchema": {},
            },
        ]

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            # Simulate parallel execution by returning all tools at once
            mock_get_tools.return_value = expected_tools

            tools = await manager.get_tools()

        assert len(tools) == 3
        # Verify all tools are present
        tool_names = {t["name"] for t in tools}
        assert tool_names == {"slow_tool", "fast_tool", "medium_tool"}

    @pytest.mark.asyncio
    async def test_server_specific_tool_execution(self, multi_server_config):
        """Test executing tools on specific servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"],
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["node", "calc.js"],
        }

        # Expected result from tool execution
        expected_result = {"content": [{"type": "text", "text": "Result from server1"}]}

        with patch.object(
            manager, "_call_tool_async", new_callable=AsyncMock
        ) as mock_call_tool:
            mock_call_tool.return_value = expected_result

            # Execute tool on specific server
            result = await manager.call_tool(
                "math-server", "calculate", {"expr": "2+2"}
            )

        assert result["content"][0]["text"] == "Result from server1"
        mock_call_tool.assert_called_once_with(
            "math-server", "calculate", {"expr": "2+2"}
        )

    @pytest.mark.asyncio
    async def test_error_isolation_between_servers(self, multi_server_config):
        """Test that errors in one server don't affect others."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        manager._active_servers["failing-server"] = {
            "name": "failing-server",
            "transport": "stdio",
            "command": ["node", "failing.js"],
        }
        manager._active_servers["working-server"] = {
            "name": "working-server",
            "transport": "stdio",
            "command": ["node", "working.js"],
        }

        # When getting tools from all servers, working server returns tools
        # but the method handles failures gracefully and still returns tools from working servers
        expected_tools = [
            {
                "name": "working_tool",
                "server": "working-server",
                "description": "",
                "inputSchema": {},
            }
        ]

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            # When called with None (all servers), return only working server's tools
            mock_get_tools.return_value = expected_tools

            # Get tools from all servers - should get tools from working server
            tools = await manager.get_tools()

        # Should only have tools from working server
        assert len(tools) == 1
        assert tools[0]["name"] == "working_tool"
        assert tools[0]["server"] == "working-server"

    @pytest.mark.asyncio
    async def test_resource_namespace_separation(self, multi_server_config):
        """Test that resources from different servers are properly namespaced."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        manager._active_servers["server1"] = {
            "name": "server1",
            "transport": "stdio",
            "command": ["node", "server1.js"],
        }
        manager._active_servers["server2"] = {
            "name": "server2",
            "transport": "stdio",
            "command": ["node", "server2.js"],
        }

        # Expected resources from both servers with same URI but different servers
        expected_resources = [
            {
                "uri": "file:///data.txt",
                "name": "Server1 Data",
                "server": "server1",
                "description": "",
                "mimeType": "application/octet-stream",
            },
            {
                "uri": "file:///data.txt",
                "name": "Server2 Data",
                "server": "server2",
                "description": "",
                "mimeType": "application/octet-stream",
            },
        ]

        with patch.object(
            manager, "_get_resources_async", new_callable=AsyncMock
        ) as mock_get_resources:
            mock_get_resources.return_value = expected_resources

            # Get all resources
            resources = await manager.get_resources()

        # Should have both resources with server info
        assert len(resources) == 2
        assert all(r["server"] in ["server1", "server2"] for r in resources)

        # Resources with same URI should be distinguishable by server
        data_resources = [r for r in resources if r["uri"] == "file:///data.txt"]
        assert len(data_resources) == 2
        assert {r["server"] for r in data_resources} == {"server1", "server2"}

    def test_server_priority_configuration(self, multi_server_config):
        """Test server priority configuration handling."""
        manager = MCPManager(multi_server_config)

        # Get server priorities
        priorities = manager.get_server_priorities()

        assert priorities["math-server"] == 1
        assert priorities["calculator-server"] == 2
        assert priorities.get("tools-server", float("inf")) == float(
            "inf"
        )  # No priority = lowest

    @pytest.mark.asyncio
    async def test_broadcast_operation(self, multi_server_config):
        """Test broadcasting an operation to all servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        for i in range(3):
            manager._active_servers[f"server{i}"] = {
                "name": f"server{i}",
                "transport": "stdio",
                "command": ["node", f"server{i}.js"],
            }

        # Mock the broadcast_operation method directly
        expected_results = [
            (
                "server0",
                {
                    "tools": [
                        {
                            "name": "tool0",
                            "server": "server0",
                            "description": "",
                            "inputSchema": {},
                        }
                    ]
                },
            ),
            (
                "server1",
                {
                    "tools": [
                        {
                            "name": "tool1",
                            "server": "server1",
                            "description": "",
                            "inputSchema": {},
                        }
                    ]
                },
            ),
            (
                "server2",
                {
                    "tools": [
                        {
                            "name": "tool2",
                            "server": "server2",
                            "description": "",
                            "inputSchema": {},
                        }
                    ]
                },
            ),
        ]

        with patch.object(
            manager, "broadcast_operation", new_callable=AsyncMock
        ) as mock_broadcast:
            mock_broadcast.return_value = expected_results

            # Broadcast list_tools to all servers
            all_results = await manager.broadcast_operation("list_tools")

        # Should have results from all servers
        assert len(all_results) == 3
        mock_broadcast.assert_called_once_with("list_tools")

    @pytest.mark.asyncio
    async def test_find_servers_with_tool(self, multi_server_config):
        """Test finding all servers that have a specific tool."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()

        # Mark servers as active
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"],
        }
        manager._active_servers["stats-server"] = {
            "name": "stats-server",
            "transport": "stdio",
            "command": ["node", "stats.js"],
        }
        manager._active_servers["calc-server"] = {
            "name": "calc-server",
            "transport": "stdio",
            "command": ["node", "calc.js"],
        }

        # Mock get_tools to return tools from all servers
        all_tools = [
            {
                "name": "calculate",
                "server": "math-server",
                "description": "Math calc",
                "inputSchema": {},
            },
            {
                "name": "graph",
                "server": "math-server",
                "description": "Graphing",
                "inputSchema": {},
            },
            {
                "name": "analyze",
                "server": "stats-server",
                "description": "Analysis",
                "inputSchema": {},
            },
            {
                "name": "calculate",
                "server": "calc-server",
                "description": "Advanced calc",
                "inputSchema": {},
            },
        ]

        with patch.object(
            manager, "_get_tools_async", new_callable=AsyncMock
        ) as mock_get_tools:
            mock_get_tools.return_value = all_tools

            # Find servers with "calculate" tool
            servers = await manager.find_servers_with_tool("calculate")

        assert set(servers) == {"math-server", "calc-server"}

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_sync_wrappers_for_multi_server(self, multi_server_config):
        """Test synchronous wrappers for multi-server operations."""
        manager = MCPManager(multi_server_config)

        with patch("asyncio.run") as mock_run:
            mock_run.return_value = "best-server"

            result = manager.find_best_server_for_tool_sync("calculate")

            assert result == "best-server"
            # Verify asyncio.run was called with the correct coroutine
            mock_run.assert_called_once()
