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

    def test_get_token_storage_path(self):
        """Test getting token storage path."""
        manager = MCPManager()

        path = manager._get_token_storage_path("my-server")
        assert path == ".mcp_tokens/my-server.json"

    def test_oauth_constants_available(self):
        """Test that OAuth-related constants exist."""
        # Just verify the module has the expected constants
        import src.mcp_manager

        assert hasattr(src.mcp_manager, "OAUTH_AVAILABLE")
        assert hasattr(src.mcp_manager, "HTTP_TRANSPORT_AVAILABLE")

    @pytest.mark.asyncio
    async def test_is_token_expired(self):
        """Test token expiration checking."""
        manager = MCPManager()

        # Token without expiration should be valid
        token_no_expiry = {"access_token": "test"}
        assert manager._is_token_valid(token_no_expiry) is True

        # Token with future expiration should be valid
        future_expiry = datetime.now().timestamp() + 3600
        token_valid = {"access_token": "test", "expires_at": future_expiry}
        assert manager._is_token_valid(token_valid) is True

        # Token with past expiration should be invalid
        past_expiry = datetime.now().timestamp() - 3600
        token_expired = {"access_token": "test", "expires_at": past_expiry}
        assert manager._is_token_valid(token_expired) is False
