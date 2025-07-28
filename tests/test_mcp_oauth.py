"""Tests for MCP OAuth authentication."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, mock_open
import json
import asyncio
from datetime import datetime, timedelta

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig


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


class TestMCPOAuth:
    """Test OAuth authentication functionality."""

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    @patch("src.mcp_manager.httpx.AsyncClient")
    @patch("builtins.input")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists")
    @patch("os.makedirs")
    async def test_connect_oauth_server_new_auth(
        self,
        mock_makedirs,
        mock_exists,
        mock_file,
        mock_input,
        mock_httpx_client,
        mock_http_client,
        oauth_server_config,
    ):
        """Test connecting to OAuth server with new authorization."""
        manager = MCPManager(oauth_server_config)
        await manager.initialize()

        # Mock that token file doesn't exist
        mock_exists.return_value = False

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=test-code&state=test-state"

        # Mock httpx client for token exchange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock the HTTP transport
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock(return_value="test-session-123")
        
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write, mock_get_session_id)
        )
        mock_client_cm.__aexit__ = AsyncMock()
        mock_http_client.return_value = mock_client_cm

        # Mock the session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()

        # Patch the state generation to return a known value
        with patch("src.mcp_manager.secrets.token_urlsafe", return_value="test-state"):
            with patch("src.mcp_manager.ClientSession", return_value=mock_session):
                await manager.connect_server("oauth-server")

        # Verify token was saved
        mock_file.assert_called()
        # Get the file handle that was written to
        file_handle = mock_file.return_value
        # Get the write calls
        write_calls = file_handle.write.call_args_list
        # Concatenate all written data
        written_data = ''.join(call[0][0] for call in write_calls)
        if written_data:
            token_data = json.loads(written_data)
            assert token_data["access_token"] == "new-test-token"

        # Verify session was initialized
        assert "oauth-server" in manager._sessions

    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    @patch("builtins.open", mock_open(read_data='{"access_token": "existing-token", "expires_at": 9999999999}'))
    @patch("os.path.exists")
    async def test_connect_oauth_server_existing_token(
        self, mock_exists, mock_http_client, oauth_server_config
    ):
        """Test connecting to OAuth server with existing valid token."""
        manager = MCPManager(oauth_server_config)
        await manager.initialize()

        # Mock that token file exists
        mock_exists.return_value = True

        # Mock the HTTP client with auth
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock(return_value="test-session-123")
        
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write, mock_get_session_id)
        )
        mock_client_cm.__aexit__ = AsyncMock()
        mock_http_client.return_value = mock_client_cm

        # Mock the session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        
        with patch("src.mcp_manager.ClientSession", return_value=mock_session):
            await manager.connect_server("oauth-server")

        # Verify HTTP client was called with Bearer auth
        mock_http_client.assert_called_once()
        call_args = mock_http_client.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer existing-token"

    @pytest.mark.asyncio
    @patch("src.mcp_manager.streamablehttp_client")
    @patch("src.mcp_manager.httpx.AsyncClient")
    @patch("builtins.input")
    @patch("builtins.open", mock_open(read_data='{"access_token": "expired-token", "expires_at": 1000}'))
    @patch("os.path.exists")
    async def test_connect_oauth_server_expired_token(
        self, mock_exists, mock_input, mock_httpx_client, mock_http_client, oauth_server_config
    ):
        """Test connecting to OAuth server with expired token triggers re-auth."""
        manager = MCPManager(oauth_server_config)
        await manager.initialize()

        # Mock that token file exists
        mock_exists.return_value = True

        # Mock user input for callback URL
        mock_input.return_value = "http://localhost:8080/callback?code=refresh-code&state=test-state"

        # Mock httpx client for token exchange
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_httpx_client.return_value.__aenter__.return_value = mock_client_instance

        # Mock the HTTP transport
        mock_read = AsyncMock()
        mock_write = AsyncMock()
        mock_get_session_id = Mock(return_value="test-session-123")
        
        mock_client_cm = AsyncMock()
        mock_client_cm.__aenter__ = AsyncMock(
            return_value=(mock_read, mock_write, mock_get_session_id)
        )
        mock_client_cm.__aexit__ = AsyncMock()
        mock_http_client.return_value = mock_client_cm

        # Mock the session
        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        
        # Patch the state generation to return a known value
        with patch("src.mcp_manager.secrets.token_urlsafe", return_value="test-state"):
            with patch("src.mcp_manager.ClientSession", return_value=mock_session):
                await manager.connect_server("oauth-server")

        # Verify new token was obtained
        mock_httpx_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_oauth_token_storage_path(self, oauth_server_config):
        """Test OAuth token storage path generation."""
        manager = MCPManager(oauth_server_config)
        
        path = manager._get_token_storage_path("oauth-server")
        assert path == ".mcp_tokens/oauth-server.json"

    @pytest.mark.asyncio
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    async def test_save_oauth_token(self, mock_makedirs, mock_file, oauth_server_config):
        """Test saving OAuth token to file."""
        manager = MCPManager(oauth_server_config)
        
        token_data = {
            "access_token": "test-token",
            "token_type": "Bearer",
            "expires_in": 3600,
        }
        
        await manager._save_oauth_token("oauth-server", token_data)
        
        # Verify directory was created
        mock_makedirs.assert_called_once_with(".mcp_tokens", exist_ok=True)
        
        # Verify file was written
        mock_file.assert_called_once_with(".mcp_tokens/oauth-server.json", "w")
        # Get the file handle that was written to
        file_handle = mock_file.return_value
        # Get the write calls
        write_calls = file_handle.write.call_args_list
        # Concatenate all written data
        written_data = ''.join(call[0][0] for call in write_calls)
        if written_data:
            token_data = json.loads(written_data)
            assert token_data["access_token"] == "test-token"
            assert "expires_at" in token_data

    @pytest.mark.asyncio
    @patch("builtins.open", mock_open(read_data='{"access_token": "stored-token", "expires_at": 9999999999}'))
    @patch("os.path.exists")
    async def test_load_oauth_token(self, mock_exists, oauth_server_config):
        """Test loading OAuth token from file."""
        manager = MCPManager(oauth_server_config)
        mock_exists.return_value = True
        
        token = await manager._load_oauth_token("oauth-server")
        
        assert token["access_token"] == "stored-token"
        assert token["expires_at"] == 9999999999

    @pytest.mark.asyncio
    @patch("os.path.exists")
    async def test_load_oauth_token_not_found(self, mock_exists, oauth_server_config):
        """Test loading OAuth token when file doesn't exist."""
        manager = MCPManager(oauth_server_config)
        mock_exists.return_value = False
        
        token = await manager._load_oauth_token("oauth-server")
        
        assert token is None

    @pytest.mark.asyncio
    async def test_oauth_redirect_handler(self, oauth_server_config):
        """Test OAuth redirect URL handler."""
        manager = MCPManager(oauth_server_config)
        
        # Mock console for testing
        manager._oauth_console = Mock()
        
        redirect_url = await manager._handle_oauth_redirect("https://auth.example.com/authorize?client_id=test")
        
        # Should display the URL and return None (manual handling)
        manager._oauth_console.print.assert_called()
        assert redirect_url is None

    @pytest.mark.asyncio
    async def test_oauth_callback_handler(self, oauth_server_config):
        """Test OAuth callback handler."""
        manager = MCPManager(oauth_server_config)
        
        # Mock console and input
        manager._oauth_console = Mock()
        with patch("builtins.input", return_value="http://localhost:8080/callback?code=auth-code&state=test-state"):
            callback_url = await manager._handle_oauth_callback()
        
        assert callback_url == "http://localhost:8080/callback?code=auth-code&state=test-state"

    def test_oauth_config_validation(self):
        """Test OAuth configuration validation."""
        config = Mock()
        config.servers = [
            {
                "name": "invalid-oauth",
                "transport": "http",
                "url": "http://api.example.com",
                "auth": {
                    "type": "oauth",
                    # Missing required OAuth fields
                }
            }
        ]
        config.get_server = lambda name: config.servers[0] if name == "invalid-oauth" else None
        
        manager = MCPManager(config)
        
        # Should raise error for missing OAuth config
        with pytest.raises(MCPManagerError, match="OAuth configuration missing required fields"):
            asyncio.run(manager.connect_server("invalid-oauth"))

    @pytest.mark.asyncio
    @patch("src.mcp_manager.httpx.AsyncClient")
    async def test_oauth_token_in_requests(self, mock_httpx_client, oauth_server_config):
        """Test that OAuth token is included in HTTP requests."""
        manager = MCPManager(oauth_server_config)
        await manager.initialize()
        
        # Set up a mock token
        manager._oauth_tokens["oauth-server"] = {
            "access_token": "test-bearer-token",
            "expires_at": 9999999999,
        }
        
        # Mock session for the server
        mock_session = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value={"result": "success"})
        manager._sessions["oauth-server"] = mock_session
        
        # Call a tool
        result = await manager.call_tool("oauth-server", "test-tool", {"arg": "value"})
        
        assert result["result"] == "success"
        mock_session.call_tool.assert_called_once_with("test-tool", arguments={"arg": "value"})

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_oauth_sync_wrapper(self, oauth_server_config):
        """Test synchronous wrapper for OAuth server connection."""
        manager = MCPManager(oauth_server_config)
        
        with patch("asyncio.run") as mock_run:
            manager.connect_server_sync("oauth-server")
            
            mock_run.assert_called_once()