"""Test MCP configuration loading and validation."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.mcp_config import MCPConfig, MCPConfigError


class TestMCPConfig:
    """Test suite for MCP configuration management."""

    def test_load_valid_config(self, tmp_path):
        """Test loading a valid configuration file."""
        config_data = {
            "servers": [
                {
                    "name": "test-server",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                }
            ]
        }
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        config = MCPConfig(config_file)
        assert len(config.servers) == 1
        assert config.servers[0]["name"] == "test-server"
        assert config.servers[0]["transport"] == "stdio"
        assert config.servers[0]["command"] == ["python", "server.py"]

    def test_load_multiple_servers(self, tmp_path):
        """Test loading configuration with multiple servers."""
        config_data = {
            "servers": [
                {
                    "name": "stdio-server",
                    "transport": "stdio",
                    "command": ["node", "server.js"],
                },
                {
                    "name": "http-server",
                    "transport": "http",
                    "url": "http://localhost:8000/mcp",
                },
            ]
        }
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text(json.dumps(config_data))

        config = MCPConfig(config_file)
        assert len(config.servers) == 2
        assert config.servers[0]["name"] == "stdio-server"
        assert config.servers[1]["name"] == "http-server"

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        config = MCPConfig(Path("nonexistent.json"))
        assert config.servers == []

    def test_empty_config_file(self, tmp_path):
        """Test handling of empty configuration file."""
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text("{}")

        config = MCPConfig(config_file)
        assert config.servers == []

    def test_invalid_json(self, tmp_path):
        """Test handling of invalid JSON in config file."""
        config_file = tmp_path / "mcp_config.json"
        config_file.write_text("invalid json {")

        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)
        assert "Invalid JSON" in str(exc_info.value)

    def test_validate_stdio_transport(self, tmp_path):
        """Test validation of stdio transport configuration."""
        # Valid stdio config
        valid_config = {
            "servers": [
                {
                    "name": "test",
                    "transport": "stdio",
                    "command": ["python", "server.py"],
                }
            ]
        }
        config_file = tmp_path / "valid.json"
        config_file.write_text(json.dumps(valid_config))
        MCPConfig(config_file)  # Should not raise

        # Invalid stdio config - missing command
        invalid_config = {"servers": [{"name": "test", "transport": "stdio"}]}
        config_file = tmp_path / "invalid.json"
        config_file.write_text(json.dumps(invalid_config))
        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)
        assert "command" in str(exc_info.value)

    def test_validate_http_transport(self, tmp_path):
        """Test validation of HTTP transport configuration."""
        # Valid HTTP config
        valid_config = {
            "servers": [
                {
                    "name": "test",
                    "transport": "http",
                    "url": "http://localhost:8000",
                }
            ]
        }
        config_file = tmp_path / "valid.json"
        config_file.write_text(json.dumps(valid_config))
        MCPConfig(config_file)  # Should not raise

        # Invalid HTTP config - missing url
        invalid_config = {"servers": [{"name": "test", "transport": "http"}]}
        config_file = tmp_path / "invalid.json"
        config_file.write_text(json.dumps(invalid_config))
        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)
        assert "url" in str(exc_info.value)

    def test_validate_sse_transport(self, tmp_path):
        """Test validation of SSE transport configuration."""
        # Valid SSE config
        valid_config = {
            "servers": [
                {
                    "name": "test",
                    "transport": "sse",
                    "url": "http://localhost:8000/events",
                }
            ]
        }
        config_file = tmp_path / "valid.json"
        config_file.write_text(json.dumps(valid_config))
        MCPConfig(config_file)  # Should not raise

    def test_invalid_transport_type(self, tmp_path):
        """Test handling of invalid transport type."""
        config_data = {
            "servers": [
                {
                    "name": "test",
                    "transport": "invalid_transport",
                    "url": "http://localhost:8000",
                }
            ]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)
        assert "Invalid transport" in str(exc_info.value)

    def test_missing_server_name(self, tmp_path):
        """Test handling of server without name."""
        config_data = {
            "servers": [{"transport": "stdio", "command": ["python", "server.py"]}]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        with pytest.raises(MCPConfigError) as exc_info:
            MCPConfig(config_file)
        assert "name" in str(exc_info.value)

    def test_get_server_by_name(self, tmp_path):
        """Test retrieving server configuration by name."""
        config_data = {
            "servers": [
                {
                    "name": "server1",
                    "transport": "stdio",
                    "command": ["python", "server1.py"],
                },
                {
                    "name": "server2",
                    "transport": "http",
                    "url": "http://localhost:8000",
                },
            ]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))

        config = MCPConfig(config_file)

        server1 = config.get_server("server1")
        assert server1 is not None
        assert server1["name"] == "server1"
        assert server1["transport"] == "stdio"

        server2 = config.get_server("server2")
        assert server2 is not None
        assert server2["name"] == "server2"
        assert server2["transport"] == "http"

        server3 = config.get_server("nonexistent")
        assert server3 is None

    def test_default_config_path(self):
        """Test that default config path is used when none provided."""
        with patch("pathlib.Path.exists", return_value=False):
            config = MCPConfig()
            assert config.servers == []

    def test_reload_config(self, tmp_path):
        """Test reloading configuration from file."""
        config_file = tmp_path / "mcp_config.json"
        initial_config = {
            "servers": [{"name": "test1", "transport": "stdio", "command": ["cmd1"]}]
        }
        config_file.write_text(json.dumps(initial_config))

        config = MCPConfig(config_file)
        assert len(config.servers) == 1
        assert config.servers[0]["name"] == "test1"

        # Update the file
        updated_config = {
            "servers": [
                {
                    "name": "test2",
                    "transport": "http",
                    "url": "http://localhost",
                }
            ]
        }
        config_file.write_text(json.dumps(updated_config))

        # Reload
        config.reload()
        assert len(config.servers) == 1
        assert config.servers[0]["name"] == "test2"
