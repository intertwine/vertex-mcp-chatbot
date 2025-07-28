"""Tests for MCP multi-server coordination."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig
from tests.mock_mcp_types import (
    create_mock_list_tools_result,
    create_mock_list_resources_result,
    create_mock_list_prompts_result,
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
            "priority": 1
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio", 
            "command": ["node", "calc.js"],
            "priority": 2
        }
        
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
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([
                            {"name": "calculate", "description": "Basic math calculations"},
                            {"name": "convert", "description": "Unit conversion"},
                        ]))
                    else:
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([
                            {"name": "calculate", "description": "Advanced calculations"},
                            {"name": "analyze", "description": "Data analysis"},
                        ]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
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
            "priority": 1  # Higher priority
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["node", "calc.js"],
            "priority": 2  # Lower priority
        }
        
        call_count = 0
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create sessions
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    if call_count == 0:
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": "calculate", "description": "Priority 1 calc"}]))
                    else:
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": "calculate", "description": "Priority 2 calc"}]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
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
                "command": ["node", f"server{i}.js"]
            }
        
        call_count = 0
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create sessions with different response times
                async def slow_list_tools():
                    await asyncio.sleep(0.1)
                    return create_mock_list_tools_result([{"name": "slow_tool"}])
                
                async def fast_list_tools():
                    return create_mock_list_tools_result([{"name": "fast_tool"}])
                
                async def medium_list_tools():
                    await asyncio.sleep(0.05)
                    return create_mock_list_tools_result([{"name": "medium_tool"}])
                
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    if call_count == 0:
                        session.list_tools = slow_list_tools
                    elif call_count == 1:
                        session.list_tools = fast_list_tools
                    else:
                        session.list_tools = medium_list_tools
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
                # Should complete in ~0.1s (not 0.15s if sequential)
                import time
                start = time.time()
                tools = await manager.get_tools()
                duration = time.time() - start
        
        assert len(tools) == 3
        assert duration < 0.2  # Should be parallel, not sequential

    @pytest.mark.asyncio
    async def test_server_specific_tool_execution(self, multi_server_config):
        """Test executing tools on specific servers."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mark servers as active
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"]
        }
        manager._active_servers["calculator-server"] = {
            "name": "calculator-server",
            "transport": "stdio",
            "command": ["node", "calc.js"]
        }
        
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create session that returns expected result
                session = AsyncMock()
                session.call_tool = AsyncMock(return_value={
                    "content": [{"type": "text", "text": "Result from server1"}]
                })
                
                context = AsyncMock()
                context.__aenter__ = AsyncMock(return_value=session)
                context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = context
                
                # Execute tool on specific server
                result = await manager.call_tool("math-server", "calculate", {"expr": "2+2"})
        
        assert result["content"][0]["text"] == "Result from server1"
        session.call_tool.assert_called_once_with("calculate", arguments={"expr": "2+2"})

    @pytest.mark.asyncio
    async def test_error_isolation_between_servers(self, multi_server_config):
        """Test that errors in one server don't affect others."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mark servers as active
        manager._active_servers["failing-server"] = {
            "name": "failing-server",
            "transport": "stdio",
            "command": ["node", "failing.js"]
        }
        manager._active_servers["working-server"] = {
            "name": "working-server",
            "transport": "stdio",
            "command": ["node", "working.js"]
        }
        
        # Mock the session creation
        call_count = 0
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create sessions with different behaviors
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    if call_count == 0:
                        # First server fails
                        session.list_tools = AsyncMock(side_effect=Exception("Server error"))
                    else:
                        # Second server works
                        session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": "working_tool"}]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
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
        
        # Mark servers as active
        manager._active_servers["server1"] = {
            "name": "server1",
            "transport": "stdio",
            "command": ["node", "server1.js"]
        }
        manager._active_servers["server2"] = {
            "name": "server2",
            "transport": "stdio",
            "command": ["node", "server2.js"]
        }
        
        # Mock the session creation for each server
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
                        session.list_resources = AsyncMock(return_value=create_mock_list_resources_result([
                            {"uri": "file:///data.txt", "name": "Server1 Data"},
                        ]))
                    else:
                        session.list_resources = AsyncMock(return_value=create_mock_list_resources_result([
                            {"uri": "file:///data.txt", "name": "Server2 Data"},  # Same URI
                        ]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
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
        
        # Mark servers as active
        for i in range(3):
            manager._active_servers[f"server{i}"] = {
                "name": f"server{i}",
                "transport": "stdio",
                "command": ["node", f"server{i}.js"]
            }
        
        # Mock the session creation
        call_count = 0
        sessions = []
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create sessions
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    session.list_tools = AsyncMock(return_value=create_mock_list_tools_result([{"name": f"tool{call_count}"}]))
                    sessions.append(session)
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
                # Broadcast list_tools to all servers
                all_results = await manager.broadcast_operation("list_tools")
        
        # Should have results from all servers
        assert len(all_results) == 3
        for session in sessions:
            session.list_tools.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_servers_with_tool(self, multi_server_config):
        """Test finding all servers that have a specific tool."""
        manager = MCPManager(multi_server_config)
        await manager.initialize()
        
        # Mark servers as active
        manager._active_servers["math-server"] = {
            "name": "math-server",
            "transport": "stdio",
            "command": ["node", "math.js"]
        }
        manager._active_servers["stats-server"] = {
            "name": "stats-server",
            "transport": "stdio",
            "command": ["node", "stats.js"]
        }
        manager._active_servers["calc-server"] = {
            "name": "calc-server",
            "transport": "stdio",
            "command": ["node", "calc.js"]
        }
        
        # Mock the session creation
        call_count = 0
        server_tools = {
            0: [{"name": "calculate", "description": "Math calc"}, {"name": "graph", "description": "Graphing"}],
            1: [{"name": "analyze", "description": "Analysis"}],
            2: [{"name": "calculate", "description": "Advanced calc"}]
        }
        
        with patch("src.mcp_manager.ClientSession") as mock_client_class:
            with patch("src.mcp_manager.stdio_client") as mock_stdio:
                # Setup stdio transport
                mock_stdio.return_value.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock()))
                mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Create sessions
                def create_session(*args, **kwargs):
                    nonlocal call_count
                    session = AsyncMock()
                    session.list_tools = AsyncMock(return_value=create_mock_list_tools_result(server_tools[call_count]))
                    call_count += 1
                    
                    context = AsyncMock()
                    context.__aenter__ = AsyncMock(return_value=session)
                    context.__aexit__ = AsyncMock(return_value=None)
                    return context
                
                mock_client_class.side_effect = create_session
                
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