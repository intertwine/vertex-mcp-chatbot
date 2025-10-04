"""Tests for the ClaudeAgentChatbot REPL."""

from unittest.mock import MagicMock, patch

from src.claude_agent_chatbot import ClaudeAgentChatbot


class TestClaudeAgentChatbot:
    """Unit tests that exercise command handling and messaging."""

    @patch("src.claude_agent_chatbot.MCPConfig")
    @patch("src.claude_agent_chatbot.ClaudeAgentClient")
    def test_initialize_bootstraps_client(
        self, mock_client_class, mock_mcp_config
    ):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_config = MagicMock()
        mock_config.servers = [{"name": "test", "transport": "stdio"}]
        mock_mcp_config.return_value = mock_config

        chatbot = ClaudeAgentChatbot(model_name="claude", system_prompt="be nice")
        chatbot.console = MagicMock()
        chatbot.initialize()

        mock_client_class.assert_called_once_with(
            model_name="claude",
            system_prompt="be nice",
            sdk_client=None,
            mcp_servers=mock_config.servers,
        )
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
