"""Additional OAuth tests for MCPManager to improve coverage."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock, mock_open, patch

import pytest

from src.mcp_manager import MCPManager, MCPManagerError

# Suppress runtime warnings about unawaited coroutines in this test module
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


@pytest.fixture
def oauth_config():
    """Create OAuth server configuration."""
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


class TestOAuthCoverage:
    """Additional OAuth tests for coverage."""

    @pytest.mark.asyncio
    async def test_handle_oauth_auth_missing_fields(self, oauth_config):
        """Test OAuth auth with missing required fields."""
        manager = MCPManager(oauth_config)

        incomplete_auth = {
            "type": "oauth",
            "client_id": "test",
            # Missing other required fields
        }

        with pytest.raises(
            MCPManagerError, match="OAuth configuration missing required fields"
        ):
            await manager._handle_oauth_auth("oauth-server", incomplete_auth)

    @pytest.mark.asyncio
    async def test_load_oauth_token_file_not_exists(self):
        """Test loading OAuth token when file doesn't exist."""
        manager = MCPManager()

        with patch("os.path.exists", return_value=False):
            token = await manager._load_oauth_token("nonexistent-server")
            assert token is None

    @pytest.mark.asyncio
    async def test_load_oauth_token_json_error(self):
        """Test loading OAuth token with JSON parse error."""
        manager = MCPManager()

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json")):
                token = await manager._load_oauth_token("test-server")
                assert token is None

    @pytest.mark.asyncio
    async def test_save_oauth_token_creates_directory(self):
        """Test saving OAuth token creates directory."""
        manager = MCPManager()

        token_data = {"access_token": "test-token", "expires_in": 3600}

        with patch("os.makedirs") as mock_makedirs:
            with patch("builtins.open", mock_open()) as mock_file:
                await manager._save_oauth_token("test-server", token_data)

                # Verify directory creation
                mock_makedirs.assert_called_once_with(".mcp_tokens", exist_ok=True)
                # Verify file was opened
                mock_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_oauth_redirect(self):
        """Test OAuth redirect handler."""
        manager = MCPManager()

        # Should not raise, returns None
        result = await manager._handle_oauth_redirect(
            "https://auth.example.com/authorize"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_handle_oauth_callback(self):
        """Test OAuth callback handler."""
        manager = MCPManager()

        with patch("builtins.input", return_value="http://localhost/callback?code=123"):
            result = await manager._handle_oauth_callback()
            assert result == "http://localhost/callback?code=123"

    def test_get_token_storage_path(self):
        """Test getting token storage path."""
        manager = MCPManager()

        path = manager._get_token_storage_path("my-server")
        assert path == ".mcp_tokens/my-server.json"

    @pytest.mark.asyncio
    async def test_perform_oauth_flow_no_dependencies(self):
        """Test OAuth flow when dependencies not available."""
        manager = MCPManager()

        with patch("src.mcp_manager.OAUTH_AVAILABLE", False):
            with pytest.raises(MCPManagerError, match="OAuth support not available"):
                await manager._perform_oauth_flow(
                    "test-server",
                    {
                        "authorization_url": "https://auth.example.com",
                        "token_url": "https://token.example.com",
                        "client_id": "test",
                        "scope": "read",
                        "redirect_uri": "http://localhost/callback",
                    },
                )

    @pytest.mark.asyncio
    async def test_perform_oauth_flow_no_http_transport(self):
        """Test OAuth flow when HTTP transport not available."""
        manager = MCPManager()

        with patch("src.mcp_manager.HTTP_TRANSPORT_AVAILABLE", False):
            with pytest.raises(MCPManagerError, match="OAuth support not available"):
                await manager._perform_oauth_flow(
                    "test-server",
                    {
                        "authorization_url": "https://auth.example.com",
                        "token_url": "https://token.example.com",
                        "client_id": "test",
                        "scope": "read",
                        "redirect_uri": "http://localhost/callback",
                    },
                )

    @pytest.mark.asyncio
    async def test_perform_oauth_flow_state_mismatch(self):
        """Test OAuth flow with state mismatch."""
        manager = MCPManager()

        auth_config = {
            "authorization_url": "https://auth.example.com/authorize",
            "token_url": "https://token.example.com/token",
            "client_id": "test-client",
            "scope": "read write",
            "redirect_uri": "http://localhost:8080/callback",
        }

        with patch.object(manager, "_handle_oauth_redirect"):
            with patch.object(
                manager,
                "_handle_oauth_callback",
                return_value="http://localhost:8080/callback?code=123&state=wrong",
            ):
                with pytest.raises(MCPManagerError, match="OAuth state mismatch"):
                    await manager._perform_oauth_flow("test-server", auth_config)

    @pytest.mark.asyncio
    async def test_perform_oauth_flow_no_code(self):
        """Test OAuth flow when no code in callback."""
        manager = MCPManager()

        auth_config = {
            "authorization_url": "https://auth.example.com/authorize",
            "token_url": "https://token.example.com/token",
            "client_id": "test-client",
            "scope": "read write",
            "redirect_uri": "http://localhost:8080/callback",
        }

        # First mock secrets to get a known state value
        with patch("src.mcp_manager.secrets.token_urlsafe", return_value="KNOWN_STATE"):
            with patch.object(manager, "_handle_oauth_redirect"):
                # Return callback with matching state but no code
                with patch.object(
                    manager,
                    "_handle_oauth_callback",
                    return_value="http://localhost:8080/callback?error=access_denied&state=KNOWN_STATE",
                ):
                    with pytest.raises(
                        MCPManagerError, match="OAuth authorization failed"
                    ):
                        await manager._perform_oauth_flow("test-server", auth_config)
