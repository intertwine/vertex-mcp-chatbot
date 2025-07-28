"""Common test fixtures for MCP tests."""

import pytest
from unittest.mock import patch


@pytest.fixture
def mock_get_tools_async():
    """Mock _get_tools_async to avoid coroutine warnings during connection tests."""
    with patch("src.mcp_manager.MCPManager._get_tools_async") as mock:
        # Make it a regular function that returns empty list
        mock.return_value = []
        yield mock
