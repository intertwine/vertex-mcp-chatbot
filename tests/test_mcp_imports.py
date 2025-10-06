"""Test MCP package imports and availability."""

import pytest

# Suppress runtime warnings about unawaited coroutines during import
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


def test_mcp_package_import():
    """Test that the MCP package can be imported."""
    try:
        import mcp

        assert mcp is not None
    except ImportError as e:
        pytest.fail(f"MCP package is not installed: {e}")


def test_mcp_client_session_import():
    """Test that ClientSession can be imported from MCP."""
    try:
        from mcp import ClientSession

        assert ClientSession is not None
    except ImportError as e:
        pytest.fail(f"Cannot import ClientSession from MCP: {e}")


def test_mcp_stdio_server_parameters_import():
    """Test that StdioServerParameters can be imported from MCP."""
    try:
        from mcp import StdioServerParameters

        assert StdioServerParameters is not None
    except ImportError as e:
        pytest.fail(f"Cannot import StdioServerParameters from MCP: {e}")


def test_mcp_stdio_client_import():
    """Test that stdio_client can be imported from MCP client."""
    try:
        from mcp.client.stdio import stdio_client

        assert stdio_client is not None
    except ImportError as e:
        pytest.fail(f"Cannot import stdio_client from MCP: {e}")
