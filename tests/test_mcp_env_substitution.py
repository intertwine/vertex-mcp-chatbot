"""Tests for environment variable substitution in MCP configuration."""

import json
import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.mcp_config import MCPConfig, MCPConfigError


class TestEnvironmentVariableSubstitution:
    """Test environment variable substitution in MCP configuration."""

    def test_simple_env_substitution(self, tmp_path):
        """Test basic environment variable substitution."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                    "env": {"API_KEY": "${TEST_API_KEY}", "DEBUG": "true"},
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(os.environ, {"TEST_API_KEY": "secret123"}):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["env"]["API_KEY"] == "secret123"
            assert server["env"]["DEBUG"] == "true"

    def test_multiple_env_substitutions(self, tmp_path):
        """Test multiple environment variable substitutions in one value."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "${PROTOCOL}://${HOST}:${PORT}/mcp",
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(
            os.environ, {"PROTOCOL": "https", "HOST": "api.example.com", "PORT": "8443"}
        ):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["url"] == "https://api.example.com:8443/mcp"

    def test_env_substitution_in_headers(self, tmp_path):
        """Test environment variable substitution in headers."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "https://api.example.com",
                    "headers": {
                        "Authorization": "Bearer ${ACCESS_TOKEN}",
                        "X-API-Key": "${API_KEY}",
                    },
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(os.environ, {"ACCESS_TOKEN": "token123", "API_KEY": "key456"}):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["headers"]["Authorization"] == "Bearer token123"
            assert server["headers"]["X-API-Key"] == "key456"

    def test_env_substitution_in_auth(self, tmp_path):
        """Test environment variable substitution in authentication."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "https://api.example.com",
                    "auth": {
                        "type": "basic",
                        "username": "${API_USER}",
                        "password": "${API_PASSWORD}",
                    },
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(
            os.environ, {"API_USER": "testuser", "API_PASSWORD": "testpass"}
        ):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["auth"]["username"] == "testuser"
            assert server["auth"]["password"] == "testpass"

    def test_oauth_env_substitution(self, tmp_path):
        """Test environment variable substitution in OAuth configuration."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "https://api.example.com",
                    "auth": {
                        "type": "oauth",
                        "authorization_url": "${OAUTH_AUTH_URL}",
                        "token_url": "${OAUTH_TOKEN_URL}",
                        "client_id": "${OAUTH_CLIENT_ID}",
                        "client_secret": "${OAUTH_CLIENT_SECRET}",
                        "scope": "read write",
                    },
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(
            os.environ,
            {
                "OAUTH_AUTH_URL": "https://auth.example.com/authorize",
                "OAUTH_TOKEN_URL": "https://auth.example.com/token",
                "OAUTH_CLIENT_ID": "client123",
                "OAUTH_CLIENT_SECRET": "secret456",
            },
        ):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert (
                server["auth"]["authorization_url"]
                == "https://auth.example.com/authorize"
            )
            assert server["auth"]["token_url"] == "https://auth.example.com/token"
            assert server["auth"]["client_id"] == "client123"
            assert server["auth"]["client_secret"] == "secret456"

    def test_missing_env_variable_error(self, tmp_path):
        """Test error handling for missing environment variables."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                    "env": {"API_KEY": "${MISSING_VAR}"},
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)

        assert "MISSING_VAR" in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_env_substitution_with_defaults(self, tmp_path):
        """Test environment variable substitution with default values."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                    "env": {
                        "API_KEY": "${API_KEY:-default_key}",
                        "DEBUG": "${DEBUG:-false}",
                    },
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        # Test with env var present (clear DEBUG to test default)
        with patch.dict(os.environ, {"API_KEY": "real_key"}, clear=True):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")
            assert server["env"]["API_KEY"] == "real_key"
            assert server["env"]["DEBUG"] == "false"  # Uses default

        # Test with env var missing (uses default)
        with patch.dict(os.environ, {}, clear=True):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")
            assert server["env"]["API_KEY"] == "default_key"
            assert server["env"]["DEBUG"] == "false"

    def test_env_substitution_in_nested_objects(self, tmp_path):
        """Test environment variable substitution in deeply nested objects."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "https://api.example.com",
                    "retry": {"max_attempts": 3, "initial_delay": 1.0},
                    "custom": {"nested": {"value": "${NESTED_VALUE}"}},
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(os.environ, {"NESTED_VALUE": "deeply_nested"}):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["custom"]["nested"]["value"] == "deeply_nested"

    def test_env_substitution_in_arrays(self, tmp_path):
        """Test environment variable substitution in array values."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["${PYTHON_BIN}", "${SCRIPT_PATH}"],
                    "args": ["--api-key", "${API_KEY}", "--port", "${PORT}"],
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        with patch.dict(
            os.environ,
            {
                "PYTHON_BIN": "/usr/bin/python3",
                "SCRIPT_PATH": "/app/server.py",
                "API_KEY": "key123",
                "PORT": "8080",
            },
        ):
            config = MCPConfig(config_file)
            server = config.get_server("test-server")

            assert server["command"] == ["/usr/bin/python3", "/app/server.py"]
            assert server["args"] == ["--api-key", "key123", "--port", "8080"]

    def test_no_substitution_for_non_strings(self, tmp_path):
        """Test that non-string values are not affected by substitution."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "http",
                    "url": "https://api.example.com",
                    "priority": 1,
                    "retry": {"max_attempts": 5, "jitter": True, "initial_delay": 1.5},
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        config = MCPConfig(config_file)
        server = config.get_server("test-server")

        # Numeric and boolean values should remain unchanged
        assert server["priority"] == 1
        assert server["retry"]["max_attempts"] == 5
        assert server["retry"]["jitter"] is True
        assert server["retry"]["initial_delay"] == 1.5

    def test_escaped_dollar_sign(self, tmp_path):
        """Test that escaped dollar signs are preserved."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["echo"],
                    "args": ["\\${NOT_A_VAR}", "$${ALSO_NOT_A_VAR}"],
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        config = MCPConfig(config_file)
        server = config.get_server("test-server")

        # Escaped patterns should be preserved (with escape removed)
        assert server["args"][0] == "${NOT_A_VAR}"
        assert server["args"][1] == "${ALSO_NOT_A_VAR}"

    def test_env_from_dotenv_file(self, tmp_path, monkeypatch):
        """Test that environment variables from .env file are used."""
        # Create a .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DOTENV_API_KEY=from_dotenv_file\nDOTENV_SECRET=secret_value\n"
        )

        # Change to the temp directory
        monkeypatch.chdir(tmp_path)

        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                    "env": {
                        "API_KEY": "${DOTENV_API_KEY}",
                        "SECRET": "${DOTENV_SECRET}",
                    },
                }
            ]
        }

        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        # Since load_dotenv is called in config.py at module level,
        # we need to ensure the environment is set up properly
        from dotenv import load_dotenv

        load_dotenv(env_file)

        config = MCPConfig(config_file)
        server = config.get_server("test-server")

        assert server["env"]["API_KEY"] == "from_dotenv_file"
        assert server["env"]["SECRET"] == "secret_value"
