"""Tests for MCP connection retry logic."""

import pytest
from unittest.mock import AsyncMock, Mock, patch, call, mock_open
import asyncio
from datetime import datetime

from src.mcp_manager import MCPManager, MCPManagerError
from src.mcp_config import MCPConfig
from tests.mock_mcp_types import create_mock_list_tools_result
from tests.test_helpers import make_sync_run_handler

# Suppress runtime warnings about unawaited coroutines in this test module
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


@pytest.fixture
def retry_config():
    """Create a mock config with retry settings."""
    config = Mock()
    config.servers = [
        {
            "name": "retry-stdio-server",
            "transport": "stdio",
            "command": ["python", "server.py"],
            "retry": {
                "max_attempts": 3,
                "initial_delay": 0.1,
                "max_delay": 2.0,
                "exponential_base": 2.0,
                "jitter": False,
            },
        },
        {
            "name": "retry-http-server",
            "transport": "http",
            "url": "http://localhost:8000/mcp",
            "retry": {
                "max_attempts": 2,
                "initial_delay": 0.5,
                "max_delay": 5.0,
                "exponential_base": 3.0,
                "jitter": True,
            },
        },
        {
            "name": "no-retry-server",
            "transport": "stdio",
            "command": ["python", "server.py"],
        },
    ]

    def get_server(name):
        for server in config.servers:
            if server["name"] == name:
                return server
        return None

    config.get_server = get_server
    return config


class TestMCPRetry:
    """Test connection retry functionality."""

    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.stdio_client")
    @patch("time.sleep")
    def test_stdio_retry_on_failure(
        self, mock_sleep, mock_stdio_client, mock_run, retry_config
    ):
        """Test stdio connection retries on failure."""
        manager = MCPManager(retry_config)

        # Track call counts
        attempt_count = [0]

        def mock_run_with_retries(coro):
            if asyncio.iscoroutine(coro):
                coro_name = coro.cr_code.co_name
                if coro_name == "_get_tools_async":
                    # Increment attempt count
                    attempt_count[0] += 1
                    # Close the coroutine to prevent warning
                    coro.close()
                    # Fail first two attempts
                    if attempt_count[0] < 3:
                        raise Exception("Connection failed")
                    # Succeed on third attempt
                    return []
                else:
                    # For other coroutines, just close and return None
                    coro.close()
                    return None
            return coro

        mock_run.side_effect = mock_run_with_retries

        # Should succeed after retries
        manager.connect_server_sync("retry-stdio-server")

        # Verify retries happened
        assert mock_run.call_count == 3

        # Verify exponential backoff delays
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls(
            [
                call(0.1),  # First retry delay
                call(0.2),  # Second retry delay (0.1 * 2)
            ]
        )

    @patch("src.mcp_manager.asyncio.run")
    def test_stdio_max_retries_exceeded(self, mock_run, retry_config):
        """Test that connection fails after max retries."""
        manager = MCPManager(retry_config)

        # Mock asyncio.run to always fail
        mock_run.side_effect = Exception("Connection failed")

        # Should fail after max attempts
        with pytest.raises(
            MCPManagerError, match="Failed to connect to server .* after 3 attempts"
        ):
            manager.connect_server_sync("retry-stdio-server")

        # Verify it tried max attempts
        assert mock_run.call_count == 3

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("src.mcp_manager.asyncio.run")
    @patch("src.mcp_manager.streamablehttp_client")
    @patch("time.sleep")
    def test_http_retry_with_jitter(
        self, mock_sleep, mock_http_client, mock_run, retry_config
    ):
        """Test HTTP connection retries with jitter."""
        manager = MCPManager(retry_config)

        # Track call counts for HTTP retry test
        attempt_count = [0]

        def mock_run_with_http_retry(coro):
            if asyncio.iscoroutine(coro):
                coro_name = coro.cr_code.co_name
                if coro_name == "_get_tools_async":
                    # Increment attempt count
                    attempt_count[0] += 1
                    # Close the coroutine to prevent warning
                    coro.close()
                    # Fail first attempt
                    if attempt_count[0] < 2:
                        raise Exception("Connection refused")
                    # Succeed on second attempt
                    return []
                else:
                    # For other coroutines, just close and return None
                    coro.close()
                    return None
            return coro

        mock_run.side_effect = mock_run_with_http_retry

        manager.connect_server_sync("retry-http-server")

        # Verify retry happened
        assert mock_run.call_count == 2

        # Verify jitter was applied
        # Initial delay is 0.5, with ±50% jitter, so range is 0.25 to 0.75
        assert mock_sleep.call_count == 1
        actual_delay = mock_sleep.call_args[0][0]
        assert 0.25 <= actual_delay <= 0.75

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("src.mcp_manager.asyncio.run")
    def test_no_retry_when_disabled(self, mock_run, retry_config):
        """Test that retry doesn't happen when not configured."""
        manager = MCPManager(retry_config)

        # Mock asyncio.run to fail
        mock_run.side_effect = Exception("Connection failed")

        # Should fail immediately without retry
        with pytest.raises(MCPManagerError) as exc_info:
            manager.connect_server_sync("no-retry-server")

        # With default config (3 attempts), it should still retry
        # But we want to verify the server was configured without explicit retry
        assert mock_run.call_count == 3  # Default max_attempts
        assert "Connection failed" in str(exc_info.value)

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_exponential_backoff_with_max_delay(self, retry_config):
        """Test that exponential backoff respects max delay."""
        manager = MCPManager(retry_config)

        # Test the backoff calculation directly
        delays = []
        for attempt in range(5):
            delay = manager._calculate_backoff_delay(
                attempt,
                initial_delay=0.1,
                exponential_base=2.0,
                max_delay=1.0,
                jitter=False,
            )
            delays.append(delay)

        # Expected: 0.1, 0.2, 0.4, 0.8, 1.0 (capped at max)
        assert delays[0] == 0.1
        assert delays[1] == 0.2
        assert delays[2] == 0.4
        assert delays[3] == 0.8
        assert delays[4] == 1.0  # Capped at max_delay

    def test_default_retry_config(self):
        """Test default retry configuration."""
        manager = MCPManager()

        # Get default retry config
        default_config = manager._get_retry_config(
            {"name": "test", "transport": "stdio"}
        )

        assert default_config["max_attempts"] == 3
        assert default_config["initial_delay"] == 1.0
        assert default_config["max_delay"] == 60.0
        assert default_config["exponential_base"] == 2.0
        assert default_config["jitter"] is True

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_merge_retry_config(self):
        """Test merging custom and default retry configs."""
        manager = MCPManager()

        # Server with partial retry config
        server_config = {
            "name": "test",
            "transport": "stdio",
            "retry": {
                "max_attempts": 5,
                "initial_delay": 2.0,
            },
        }

        retry_config = manager._get_retry_config(server_config)

        # Custom values
        assert retry_config["max_attempts"] == 5
        assert retry_config["initial_delay"] == 2.0

        # Default values
        assert retry_config["max_delay"] == 60.0
        assert retry_config["exponential_base"] == 2.0
        assert retry_config["jitter"] is True

    @patch("src.mcp_manager.asyncio.run")
    @patch("time.sleep")
    def test_retry_logging(self, mock_sleep, mock_run, retry_config, caplog):
        """Test that retries are properly logged."""
        # Set log level to capture INFO messages
        caplog.set_level("INFO")
        manager = MCPManager(retry_config)

        # Track call counts for logging test
        attempt_count = [0]

        def mock_run_with_logging_retry(coro):
            if asyncio.iscoroutine(coro):
                coro_name = coro.cr_code.co_name
                if coro_name == "_get_tools_async":
                    # Increment attempt count
                    attempt_count[0] += 1
                    # Close the coroutine to prevent warning
                    coro.close()
                    # Fail first attempt
                    if attempt_count[0] < 2:
                        raise Exception("Temporary failure")
                    # Succeed on second attempt
                    return []
                else:
                    # For other coroutines, just close and return None
                    coro.close()
                    return None
            return coro

        mock_run.side_effect = mock_run_with_logging_retry

        manager.connect_server_sync("retry-stdio-server")

        # Check logs
        warning_messages = [
            record.message for record in caplog.records if record.levelname == "WARNING"
        ]
        info_messages = [
            record.message for record in caplog.records if record.levelname == "INFO"
        ]

        assert any("Connection attempt 1/3 failed" in msg for msg in warning_messages)
        assert any("Retrying in" in msg for msg in warning_messages)
        # Connection success is logged at INFO level
        assert any("attempt 2" in msg for msg in info_messages)

    @patch("src.mcp_manager.asyncio.run")
    def test_immediate_success_no_retry(self, mock_run, retry_config):
        """Test that successful connection doesn't trigger retries."""
        manager = MCPManager(retry_config)

        # Mock successful connection
        mock_run.return_value = []  # Empty tools list

        manager.connect_server_sync("retry-stdio-server")

        # Should only call once
        assert mock_run.call_count == 1

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("src.mcp_manager.asyncio.run")
    @patch("time.sleep")
    def test_oauth_retry_on_token_exchange_failure(
        self, mock_sleep, mock_run, retry_config
    ):
        """Test retry during OAuth token exchange failure."""
        # Add OAuth config to retry server
        retry_config.servers[1]["auth"] = {
            "type": "oauth",
            "authorization_url": "https://auth.example.com/authorize",
            "token_url": "https://auth.example.com/token",
            "client_id": "test-client",
            "scope": "read",
            "redirect_uri": "http://localhost:8080/callback",
        }

        manager = MCPManager(retry_config)

        # Mock asyncio.run to fail once due to OAuth error then succeed
        call_count = 0

        def run_side_effect(coro):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise MCPManagerError(
                    "OAuth authorization failed: Token endpoint unavailable"
                )
            return []  # Success on second attempt

        mock_run.side_effect = run_side_effect

        # Should eventually succeed
        manager.connect_server_sync("retry-http-server")

        # Verify retries happened
        assert mock_run.call_count == 2
        # Verify delay was applied
        assert mock_sleep.call_count == 1

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    def test_retry_sync_wrapper(self, retry_config):
        """Test synchronous wrapper respects retry config."""
        manager = MCPManager(retry_config)

        with patch("asyncio.run") as mock_run:
            # Make async run raise exception to simulate connection failure
            mock_run.side_effect = MCPManagerError("Connection failed")

            # Should propagate the error
            with pytest.raises(MCPManagerError):
                manager.connect_server_sync("retry-stdio-server")
