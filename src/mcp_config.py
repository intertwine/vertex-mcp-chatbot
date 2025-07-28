"""MCP configuration management module."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


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

        # Perform environment variable substitution
        self.servers = self._substitute_env_vars(self.servers)

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
            raise MCPConfigError("Server configuration missing required field: name")

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

    def _substitute_env_vars(self, obj: Any) -> Any:
        """Recursively substitute environment variables in configuration.

        Args:
            obj: Configuration object (dict, list, or primitive)

        Returns:
            Object with environment variables substituted

        Raises:
            MCPConfigError: If a referenced environment variable is not found
        """
        if isinstance(obj, str):
            return self._substitute_string(obj)
        elif isinstance(obj, dict):
            return {key: self._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(item) for item in obj]
        else:
            # For non-string primitives (int, float, bool, None), return as-is
            return obj

    def _substitute_string(self, value: str) -> str:
        """Substitute environment variables in a string.

        Supports:
        - ${VAR_NAME} - Simple substitution
        - ${VAR_NAME:-default} - Substitution with default value
        - \\${VAR_NAME} or $${VAR_NAME} - Escaped, not substituted

        Args:
            value: String potentially containing environment variables

        Returns:
            String with environment variables substituted

        Raises:
            MCPConfigError: If a referenced environment variable is not found
        """
        # Handle escaped dollar signs
        value = value.replace("\\$", "\x00")  # Temporary placeholder
        value = value.replace("$$", "\x00")  # Alternative escape syntax

        # Pattern to match ${VAR_NAME} or ${VAR_NAME:-default}
        pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"

        def replacer(match):
            var_name = match.group(1)
            default_value = match.group(2)

            # Get the environment variable value
            env_value = os.environ.get(var_name)

            if env_value is None:
                if default_value is not None:
                    return default_value
                else:
                    raise MCPConfigError(
                        f"Environment variable '{var_name}' not found in configuration value: {value}"
                    )

            return env_value

        # Perform substitution
        result = re.sub(pattern, replacer, value)

        # Restore escaped dollar signs
        result = result.replace("\x00", "$")

        return result
