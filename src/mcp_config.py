"""MCP configuration management module."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional


class MCPConfigError(Exception):
    """Exception raised for MCP configuration errors."""

    pass


class MCPConfig:
    """Manages MCP server configurations."""

    VALID_TRANSPORTS = {"stdio", "http", "sse"}

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize MCP configuration.

        Args:
            config_path: Path to configuration file. If not provided,
                        defaults to mcp_config.json in current directory.
        """
        self.config_path = config_path or Path("mcp_config.json")
        self.servers: List[Dict[str, Any]] = []
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            # Missing config file is not an error - just use empty config
            self.servers = []
            return

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise MCPConfigError(f"Invalid JSON in config file: {e}")

        # Get servers list, default to empty if not present
        self.servers = data.get("servers", [])

        # Validate all server configurations
        for server in self.servers:
            self._validate_server_config(server)

    def _validate_server_config(self, server: Dict[str, Any]) -> None:
        """Validate a single server configuration.

        Args:
            server: Server configuration dictionary

        Raises:
            MCPConfigError: If configuration is invalid
        """
        # Check required fields
        if "name" not in server:
            raise MCPConfigError(
                "Server configuration missing required field: name"
            )

        if "transport" not in server:
            raise MCPConfigError(
                f"Server '{server.get('name', 'unnamed')}' missing required field: transport"
            )

        transport = server["transport"]

        # Validate transport type
        if transport not in self.VALID_TRANSPORTS:
            raise MCPConfigError(
                f"Invalid transport '{transport}' for server '{server['name']}'. "
                f"Valid transports are: {', '.join(self.VALID_TRANSPORTS)}"
            )

        # Validate transport-specific fields
        if transport == "stdio":
            if "command" not in server:
                raise MCPConfigError(
                    f"Server '{server['name']}' with stdio transport missing required field: command"
                )
            if not isinstance(server["command"], list):
                raise MCPConfigError(
                    f"Server '{server['name']}' command must be a list"
                )

        elif transport in ("http", "sse"):
            if "url" not in server:
                raise MCPConfigError(
                    f"Server '{server['name']}' with {transport} transport missing required field: url"
                )

    def get_server(self, name: str) -> Optional[Dict[str, Any]]:
        """Get server configuration by name.

        Args:
            name: Server name to look up

        Returns:
            Server configuration dict if found, None otherwise
        """
        for server in self.servers:
            if server.get("name") == name:
                return server
        return None

    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
