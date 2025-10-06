"""Tests for the ClaudeAgentChatbot REPL."""

from unittest.mock import MagicMock, patch

from src.claude_agent_chatbot import ClaudeAgentChatbot


class TestClaudeAgentChatbot:
    """Unit tests that exercise command handling and messaging."""

    @patch("src.claude_agent_chatbot.MCP_AVAILABLE", False)
    @patch("src.claude_agent_chatbot.MCPConfig")
    @patch("src.claude_agent_chatbot.ClaudeAgentClient")
    def test_initialize_bootstraps_client(self, mock_client_class, mock_mcp_config):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_config = MagicMock()
        mock_config.servers = [{"name": "test", "transport": "stdio"}]
        mock_mcp_config.return_value = mock_config

        chatbot = ClaudeAgentChatbot(model_name="claude", system_prompt="be nice")
        chatbot.console = MagicMock()
        chatbot.initialize()

        # Check that client was created with correct parameters
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["model_name"] == "claude"
        assert call_kwargs["system_prompt"] == "be nice"
        assert call_kwargs["mcp_servers"] == mock_config.servers

        mock_client.ensure_session.assert_called_once_with("be nice")

    def test_handle_unknown_command(self):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        result = chatbot.handle_command("/does-not-exist")
        assert result is False
        chatbot.console.print.assert_called()

    def test_system_prompt_command_updates_prompt(self):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()

        chatbot.handle_command("/system You are a tutor")

        chatbot.client.reset_session.assert_called_once_with(
            system_instruction="You are a tutor"
        )

    def test_clear_command_resets_history(self):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.history = [{"role": "user", "content": "Hello"}]

        chatbot.handle_command("/clear")

        assert chatbot.history == []
        chatbot.client.reset_session.assert_called_once()

    def test_display_history_renders_messages(self):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]

        chatbot.handle_command("/history")
        assert chatbot.console.print.call_count == 2

    def test_chat_once_records_turn(self):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.client.send_message.return_value = "Echo"

        chatbot._chat_once("Test")

        assert chatbot.history[-2:] == [
            {"role": "user", "content": "Test"},
            {"role": "assistant", "content": "Echo"},
        ]

    @patch("src.claude_agent_chatbot.prompt")
    def test_run_handles_quit_command(self, mock_prompt):
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.initialize = MagicMock()

        mock_prompt.side_effect = ["/quit"]

        chatbot.run()

        chatbot.initialize.assert_called_once()
        chatbot.client.close.assert_called_once()

    def test_mcp_list_command(self):
        """Test /mcp list command displays servers."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "filesystem", "transport": "stdio", "connected": True},
            {"name": "weather", "transport": "http", "connected": False},
        ]

        chatbot.handle_command("/mcp list")

        chatbot.console.print.assert_called()
        # Verify it shows both servers
        call_args = str(chatbot.console.print.call_args_list)
        assert "filesystem" in call_args
        assert "weather" in call_args

    def test_mcp_connect_command(self):
        """Test /mcp connect <server> command."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()

        chatbot.handle_command("/mcp connect test-server")

        chatbot.mcp_manager.connect_server_sync.assert_called_once_with("test-server")
        chatbot.console.print.assert_called()

    def test_mcp_disconnect_command(self):
        """Test /mcp disconnect <server> command."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()

        chatbot.handle_command("/mcp disconnect test-server")

        chatbot.mcp_manager.disconnect_server_sync.assert_called_once_with(
            "test-server"
        )
        chatbot.console.print.assert_called()

    def test_mcp_tools_command(self):
        """Test /mcp tools command lists available tools."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "filesystem", "connected": True}
        ]
        chatbot.mcp_manager.get_tools_sync.return_value = [
            {"name": "list_files", "description": "List files"}
        ]

        chatbot.handle_command("/mcp tools")

        chatbot.mcp_manager.get_tools_sync.assert_called_once_with("filesystem")
        chatbot.console.print.assert_called()

    def test_mcp_command_without_manager(self):
        """Test /mcp commands show error when MCP not available."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = None

        chatbot.handle_command("/mcp list")

        # Should show error message
        chatbot.console.print.assert_called()
        call_arg = str(chatbot.console.print.call_args)
        assert "not available" in call_arg.lower()

    @patch("src.claude_agent_chatbot.MCPConfig")
    @patch("src.claude_agent_chatbot.MCP_AVAILABLE", True)
    @patch("src.claude_agent_chatbot.MCPManager")
    @patch("src.claude_agent_chatbot.ClaudeAgentClient")
    def test_initialize_with_mcp_manager(
        self, mock_client_class, mock_manager_class, mock_config_class
    ):
        """Test that MCP manager is initialized and passed to client."""
        mock_config = MagicMock()
        mock_config.servers = []
        mock_config_class.return_value = mock_config

        mock_manager = MagicMock()
        mock_manager_class.return_value = mock_manager

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.initialize()

        # Verify MCP manager was created and initialized
        mock_manager_class.assert_called_once_with(mock_config)
        mock_manager.initialize_sync.assert_called_once()

        # Verify client received the MCP manager
        assert mock_client_class.call_args[1]["mcp_manager"] == mock_manager
