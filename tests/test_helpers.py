"""Test helpers for handling async code in tests."""

import asyncio
from typing import Any, Callable, TypeVar, Coroutine

T = TypeVar("T")


def make_sync_run_handler(custom_handlers: dict[str, Callable] = None):
    """Create a sync_run handler that properly handles all coroutines.

    Args:
        custom_handlers: Dict mapping coroutine names to sync handlers

    Returns:
        A function that can be used as a side_effect for mocking asyncio.run
    """
    custom_handlers = custom_handlers or {}

    def sync_run(coro: Coroutine[Any, Any, T]) -> T:
        """Execute a coroutine synchronously with proper event loop handling."""
        # Create a new event loop just for this execution
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Check if we have a custom handler for this coroutine
            if asyncio.iscoroutine(coro):
                coro_name = coro.cr_code.co_name
                if coro_name in custom_handlers:
                    # Close the coroutine to prevent warning
                    coro.close()
                    return custom_handlers[coro_name]()

            # Otherwise, run the coroutine normally
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            asyncio.set_event_loop(None)

    return sync_run
