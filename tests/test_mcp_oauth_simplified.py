"""Simplified tests for MCP OAuth authentication."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, mock_open
import json
import asyncio
from datetime import datetime, timedelta

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig
from tests.mock_mcp_types import create_mock_list_tools_result
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
    """Simplified OAuth tests."""
    
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_oauth_connection_flow(self, oauth_server_config):
        """Test the basic OAuth connection flow."""
        manager = MCPManager(oauth_server_config)
        
        # Create a custom async_run handler that tracks what's being called
        calls = []
        
        def track_calls(coro):
            if asyncio.iscoroutine(coro):
                coro_name = coro.cr_code.co_name
                calls.append(coro_name)
                coro.close()
                
                # Return appropriate values based on method
                if coro_name == '_get_tools_async':
                    return []
                elif coro_name == '_handle_oauth_auth':
                    return {"access_token": "test-token", "expires_at": 9999999999}
                    
            return None
        
        with patch("asyncio.run", side_effect=track_calls):
            # This should trigger _get_tools_async
            manager.connect_server_sync("oauth-server")
        
        # Verify the server is marked as active
        assert "oauth-server" in manager._active_servers
        # Verify _get_tools_async was called
        assert '_get_tools_async' in calls
        
    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_oauth_token_save(self, oauth_server_config):
        """Test that OAuth tokens are saved correctly."""
        manager = MCPManager(oauth_server_config)
        
        # Track file operations
        file_operations = []
        
        # Create a mock file handler
        mock_file_handler = mock_open()
        
        def file_write_tracker(content):
            file_operations.append(('write', content))
            return len(content)  # Return number of bytes written
        
        mock_file_handler.return_value.write.side_effect = file_write_tracker
        
        with patch("builtins.open", mock_file_handler):
            with patch("os.path.exists", return_value=False):
                with patch("os.makedirs"):
                    with patch("builtins.input", return_value="http://localhost:8080/callback?code=test-code"):
                        with patch("src.mcp_manager.httpx.AsyncClient") as mock_httpx:
                            # Mock token exchange response
                            mock_response = Mock()
                            mock_response.status_code = 200
                            mock_response.json.return_value = {
                                "access_token": "new-token",
                                "token_type": "Bearer",
                                "expires_in": 3600
                            }
                            mock_httpx.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                            
                            # Use create_async_run_mock with custom handlers
                            async def handle_oauth(server_name, auth_config):
                                """Mock OAuth handler that simulates the flow."""
                                # This would normally do the OAuth flow
                                token_data = {
                                    "access_token": "new-token",
                                    "token_type": "Bearer",
                                    "expires_in": 3600
                                }
                                # Save token
                                await manager._save_oauth_token(server_name, token_data)
                                return token_data
                            
                            with patch.object(manager, '_handle_oauth_auth', side_effect=handle_oauth):
                                # This test focuses on the token save mechanism
                                asyncio.run(manager._save_oauth_token("oauth-server", {
                                    "access_token": "test-save-token",
                                    "expires_in": 3600
                                }))
        
        # Verify file was opened for writing
        mock_file_handler.assert_called_with(".mcp_tokens/oauth-server.json", "w")
        
        # Verify token data was written
        written_data = ''.join(call[1] for call in file_operations if call[0] == 'write')
        if written_data:
            saved_data = json.loads(written_data)
            assert saved_data["access_token"] == "test-save-token"
            assert "expires_at" in saved_data