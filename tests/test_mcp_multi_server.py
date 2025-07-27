"""Tests for MCP multi-server coordination."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig


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
        
        # Mock two servers with conflicting tool names
        session1 = AsyncMock()
        session1.list_tools = AsyncMock(return_value={
            "tools": [
                {"name": "calculate", "description": "Basic math calculations"},
                {"name": "convert", "description": "Unit conversion"},
            ]
        })
        
        session2 = AsyncMock()
        session2.list_tools = AsyncMock(return_value={
            "tools": [
                {"name": "calculate", "description": "Advanced calculations"},
                {"name": "analyze", "description": "Data analysis"},
            ]
        })
        
        manager._sessions = {
            "math-server": session1,
            "calculator-server": session2,
        }
        
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
        
        # Mock servers with conflicting tools
        session1 = AsyncMock()
        session1.list_tools = AsyncMock(return_value={
            "tools": [{"name": "calculate", "description": "Priority 1 calc"}]
        })
        
        session2 = AsyncMock()
        session2.list_tools = AsyncMock(return_value={
            "tools": [{"name": "calculate", "description": "Priority 2 calc"}]
        })
        
        manager._sessions = {
            "math-server": session1,  # priority 1
            "calculator-server": session2,  # priority 2
        }
        
        # Find best server for a tool
        best_server = await manager.find_best_server_for_tool("calculate")
        
        assert best_server == "math-server"  # Higher priority wins

    @pytest.mark.asyncio
    async def test_parallel_tool_discovery(self, multi_server_config):
        """Test parallel tool discovery across multiple servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock three sessions with different response times
        async def slow_list_tools():
            await asyncio.sleep(0.1)
            return {"tools": [{"name": "slow_tool"}]}
        
        async def fast_list_tools():
            return {"tools": [{"name": "fast_tool"}]}
        
        async def medium_list_tools():
            await asyncio.sleep(0.05)
            return {"tools": [{"name": "medium_tool"}]}
        
        session1 = AsyncMock()
        session1.list_tools = slow_list_tools
        
        session2 = AsyncMock()
        session2.list_tools = fast_list_tools
        
        session3 = AsyncMock()
        session3.list_tools = medium_list_tools
        
        manager._sessions = {
            "server1": session1,
            "server2": session2,
            "server3": session3,
        }
        
        # Should complete in ~0.1s (not 0.15s if sequential)
        import time
        start = time.time()
        tools = await manager.get_tools()
        duration = time.time() - start
        
        assert len(tools) == 3
        assert duration < 0.12  # Should be parallel, not sequential

    @pytest.mark.asyncio
    async def test_server_specific_tool_execution(self, multi_server_config):
        """Test executing tools on specific servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock sessions
        session1 = AsyncMock()
        session1.call_tool = AsyncMock(return_value={
            "content": [{"type": "text", "text": "Result from server1"}]
        })
        
        session2 = AsyncMock()
        session2.call_tool = AsyncMock(return_value={
            "content": [{"type": "text", "text": "Result from server2"}]
        })
        
        manager._sessions = {
            "math-server": session1,
            "calculator-server": session2,
        }
        
        # Execute tool on specific server
        result = await manager.call_tool("math-server", "calculate", {"expr": "2+2"})
        
        assert result["content"][0]["text"] == "Result from server1"
        session1.call_tool.assert_called_once_with("calculate", arguments={"expr": "2+2"})
        session2.call_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_isolation_between_servers(self, multi_server_config):
        """Test that errors in one server don't affect others."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock one failing and one successful server
        failing_session = AsyncMock()
        failing_session.list_tools = AsyncMock(side_effect=Exception("Server error"))
        
        working_session = AsyncMock()
        working_session.list_tools = AsyncMock(return_value={
            "tools": [{"name": "working_tool"}]
        })
        
        manager._sessions = {
            "failing-server": failing_session,
            "working-server": working_session,
        }
        
        # Should still get tools from working server
        tools = await manager.get_tools()
        
        assert len(tools) == 1
        assert tools[0]["name"] == "working_tool"
        assert tools[0]["server"] == "working-server"

    @pytest.mark.asyncio
    async def test_resource_namespace_separation(self, multi_server_config):
        """Test that resources from different servers are properly namespaced."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock servers with resources
        session1 = AsyncMock()
        session1.list_resources = AsyncMock(return_value={
            "resources": [
                {"uri": "file:///data.txt", "name": "Server1 Data"},
            ]
        })
        
        session2 = AsyncMock()
        session2.list_resources = AsyncMock(return_value={
            "resources": [
                {"uri": "file:///data.txt", "name": "Server2 Data"},  # Same URI
            ]
        })
        
        manager._sessions = {
            "server1": session1,
            "server2": session2,
        }
        
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
        assert priorities.get("tools-server", float('inf')) == float('inf')  # No priority = lowest

    @pytest.mark.asyncio
    async def test_broadcast_operation(self, multi_server_config):
        """Test broadcasting an operation to all servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock sessions
        results = []
        for i in range(3):
            session = AsyncMock()
            session.list_tools = AsyncMock(return_value={
                "tools": [{"name": f"tool{i}"}]
            })
            manager._sessions[f"server{i}"] = session
            results.append(session)
        
        # Broadcast list_tools to all servers
        all_results = await manager.broadcast_operation("list_tools")
        
        # Should have results from all servers
        assert len(all_results) == 3
        for session in results:
            session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_servers_with_tool(self, multi_server_config):
        """Test finding all servers that have a specific tool."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mock servers with different tools
        session1 = AsyncMock()
        session1.list_tools = AsyncMock(return_value={
            "tools": [
                {"name": "calculate", "description": "Math calc"},
                {"name": "graph", "description": "Graphing"},
            ]
        })
        
        session2 = AsyncMock()
        session2.list_tools = AsyncMock(return_value={
            "tools": [
                {"name": "analyze", "description": "Analysis"},
            ]
        })
        
        session3 = AsyncMock()
        session3.list_tools = AsyncMock(return_value={
            "tools": [
                {"name": "calculate", "description": "Advanced calc"},
            ]
        })
        
        manager._sessions = {
            "math-server": session1,
            "stats-server": session2,
            "calc-server": session3,
        }
        
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