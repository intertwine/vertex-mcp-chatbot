"""Test OAuth URL encoding in MCP Manager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import pytest

from src.mcp_manager import MCPManager


class TestOAuthURLEncoding:
    """Test that OAuth authorization URLs are properly encoded."""

    @pytest.fixture
    def oauth_config_with_spaces(self):
        """Create a config with OAuth scopes containing spaces."""
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
                    "scope": "mcp:read mcp:write user:profile",  # Multiple scopes with spaces
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

    @pytest.mark.asyncio
    async def test_oauth_scope_encoding(self, oauth_config_with_spaces):
        """Test that OAuth scopes are properly URL-encoded."""
        manager = MCPManager(oauth_config_with_spaces)

        # Mark server as active
        manager._active_servers["oauth-server"] = oauth_config_with_spaces.servers[0]

        captured_url = None
        captured_state = None

        async def mock_handle_oauth_redirect(url):
            nonlocal captured_url, captured_state
            captured_url = url
            # Extract state from URL for use in callback
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            captured_state = params.get("state", [""])[0]
            return None

        async def mock_handle_oauth_callback():
            # Return a fake callback with the captured state
            return f"http://localhost:8080/callback?code=test&state={captured_state}"

        # Mock the OAuth flow methods
        manager._handle_oauth_redirect = mock_handle_oauth_redirect
        manager._handle_oauth_callback = mock_handle_oauth_callback
        manager._save_oauth_token = AsyncMock()

        # Mock httpx client for token exchange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(
            return_value={
                "access_token": "test-token",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Trigger the OAuth flow
            result = await manager._perform_oauth_flow(
                "oauth-server", oauth_config_with_spaces.servers[0]["auth"]
            )

        # Verify the URL was captured
        assert captured_url is not None, "OAuth redirect URL was not captured"

        # Parse the captured URL
        parsed = urlparse(captured_url)
        params = parse_qs(parsed.query)

        # Check that scope parameter exists and is properly encoded
        assert "scope" in params, "Scope parameter missing from URL"

        # The scope should be "mcp:read mcp:write user:profile"
        # parse_qs automatically decodes URL-encoded values
        actual_scope = params["scope"][0]
        expected_scope = "mcp:read mcp:write user:profile"

        assert actual_scope == expected_scope, (
            f"Scope not properly encoded. Expected: '{expected_scope}', "
            f"Got: '{actual_scope}'"
        )

        # Also verify the raw URL contains properly encoded spaces
        assert (
            "scope=mcp%3Aread%20mcp%3Awrite%20user%3Aprofile" in captured_url
        ), "URL should contain properly encoded scope with %20 for spaces"

    @pytest.mark.asyncio
    async def test_oauth_special_characters_encoding(self, oauth_config_with_spaces):
        """Test that special characters in OAuth parameters are properly encoded."""
        config = Mock()
        config.servers = [
            {
                "name": "special-oauth",
                "transport": "http",
                "url": "http://api.example.com/mcp",
                "auth": {
                    "type": "oauth",
                    "authorization_url": "https://auth.example.com/authorize",
                    "token_url": "https://auth.example.com/token",
                    "client_id": "client@with+special/chars",
                    "client_secret": "secret",
                    "scope": "read&write edit:user=admin",  # Special chars: & and =
                    "redirect_uri": "http://localhost:8080/callback?param=value",
                },
            }
        ]

        def get_server(name):
            for server in config.servers:
                if server["name"] == name:
                    return server
            return None

        config.get_server = get_server

        manager = MCPManager(config)
        manager._active_servers["special-oauth"] = config.servers[0]

        captured_url = None
        captured_state = None

        async def mock_handle_oauth_redirect(url):
            nonlocal captured_url, captured_state
            captured_url = url
            # Extract state from URL for use in callback
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            captured_state = params.get("state", [""])[0]
            return None

        async def mock_handle_oauth_callback():
            return f"http://localhost:8080/callback?code=test&state={captured_state}"

        manager._handle_oauth_redirect = mock_handle_oauth_redirect
        manager._handle_oauth_callback = mock_handle_oauth_callback
        manager._save_oauth_token = AsyncMock()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(
            return_value={"access_token": "test-token", "token_type": "bearer"}
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await manager._perform_oauth_flow(
                "special-oauth", config.servers[0]["auth"]
            )

        assert captured_url is not None

        # Check that special characters are properly encoded
        assert (
            "client_id=client%40with%2Bspecial%2Fchars" in captured_url
        ), "Client ID special characters should be encoded"
        assert (
            "scope=read%26write%20edit%3Auser%3Dadmin" in captured_url
        ), "Scope special characters should be encoded"
        assert (
            "redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback%3Fparam%3Dvalue"
            in captured_url
        ), "Redirect URI should be properly encoded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
