"""Utilities for handling async code in tests."""

import asyncio
from typing import Any, Callable, Dict, Optional
from unittest.mock import Mock, AsyncMock


def create_async_run_mock(handlers: Optional[Dict[str, Callable]] = None) -> Mock:
    """Create a mock for asyncio.run that properly handles coroutines.
    
    This mock:
    1. Properly closes coroutines to prevent warnings
    2. Returns appropriate values based on the coroutine name
    3. Can be customized with specific handlers
    
    Args:
        handlers: Optional dict mapping coroutine names to return values or callables
        
    Returns:
        A mock that can be used as side_effect for patching asyncio.run
    """
    handlers = handlers or {}
    
    # Default handlers for common MCP methods
    default_handlers = {
        '_get_tools_async': lambda: [],
        'find_best_server_for_tool': lambda: None,
        'connect_server': lambda: None,
        'disconnect_server': lambda: None,
        'call_tool': lambda: {"result": "success"},
        'get_resource': lambda: {"contents": "test content"},
        'list_resources': lambda: [],
        'get_resource_templates': lambda: [],
        'list_tools': lambda: [],
    }
    
    # Merge user handlers with defaults
    all_handlers = {**default_handlers, **handlers}
    
    def async_run_side_effect(coro):
        """Handle coroutine execution."""
        if asyncio.iscoroutine(coro):
            coro_name = coro.cr_code.co_name
            
            # Check if we have a handler for this coroutine
            if coro_name in all_handlers:
                # Close the coroutine to prevent warning
                coro.close()
                
                handler = all_handlers[coro_name]
                if callable(handler):
                    return handler()
                else:
                    return handler
            
            # For unhandled coroutines, run them in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        
        # If not a coroutine, just return it
        return coro
    
    mock = Mock(side_effect=async_run_side_effect)
    return mock


def create_session_mock(tools=None, resources=None):
    """Create a mock MCP session with common functionality."""
    mock_session = AsyncMock()
    mock_session.initialize = AsyncMock()
    mock_session.list_tools = AsyncMock(
        return_value={"tools": tools or []}
    )
    mock_session.list_resources = AsyncMock(
        return_value={"resources": resources or []}
    )
    mock_session.call_tool = AsyncMock(
        return_value={"result": "success"}
    )
    
    # Create session context manager
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_context.__aexit__ = AsyncMock(return_value=None)
    
    return mock_session_context