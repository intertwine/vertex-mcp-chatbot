"""Simplified OAuth tests for MCP."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.mcp_manager import MCPManager
from tests.test_async_utils import create_async_run_mock


@pytest.fixture
def oauth_server_config():
    """Create a mock config with OAuth authentication."""
    config = Mock()
    config.servers = [
        {
            "name": "oauth-server",
            "transport": "http",
            "url": "http://api.example.com/mcp",
            "auth": {
                "type": "oauth",
                "authorization_url": "https://auth.example.com/authorize",
                "token_url": "https://auth.example.com/token",
                "client_id": "test-client",
                "client_secret": "test-secret",
                "scope": "read write",
                "redirect_uri": "http://localhost:8080/callback",
            },
        }
    ]

    def get_server(name):
        for server in config.servers:
            if server["name"] == name:
                return server
        return None

    config.get_server = get_server
    return config


class TestOAuthSimplified:
    """Simplified OAuth tests that don't execute actual flows."""

    def test_connect_oauth_server(self, oauth_server_config):
        """Test basic OAuth server connection."""
        manager = MCPManager(oauth_server_config)

        with patch("asyncio.run") as mock_run:
            mock_run.side_effect = create_async_run_mock(
                {"_get_tools_async": lambda: []}
            )

            manager.connect_server_sync("oauth-server")

        assert "oauth-server" in manager._active_servers
        assert "oauth-server" in manager._sessions

    @pytest.mark.asyncio
    async def test_oauth_methods_exist(self, oauth_server_config):
        """Test that OAuth methods exist."""
        manager = MCPManager(oauth_server_config)

        # Verify OAuth methods exist
        assert hasattr(manager, "_handle_oauth_auth")
        assert hasattr(manager, "_save_oauth_token")
        assert hasattr(manager, "_load_oauth_token")
        assert hasattr(manager, "_is_token_valid")
