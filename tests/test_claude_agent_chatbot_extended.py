"""Extended tests for ClaudeAgentChatbot to improve coverage."""

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from src.claude_agent_chatbot import ClaudeAgentChatbot
from src.mcp_config import MCPConfigError


class TestClaudeAgentChatbotExtended:
    """Extended tests for ClaudeAgentChatbot coverage."""

    def test_initialize_with_existing_client(self):
        """Test that initialize doesn't reinitialize if client exists."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()

        chatbot.initialize()

        # Client shouldn't be recreated
        chatbot.client.ensure_session.assert_not_called()

    @patch("src.claude_agent_chatbot.MCP_AVAILABLE", True)
    @patch("src.claude_agent_chatbot.MCPConfig")
    @patch("src.claude_agent_chatbot.MCPManager")
    @patch("src.claude_agent_chatbot.ClaudeAgentClient")
    def test_initialize_with_mcp_config_error(
        self, mock_client_class, mock_manager_class, mock_config_class
    ):
        """Test initialization handles MCPConfigError gracefully."""
        mock_config_class.side_effect = MCPConfigError("Config file not found")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.initialize()

        # Should still create client with empty servers
        assert chatbot.client is not None
        chatbot.console.print.assert_any_call(
            "[yellow]⚠️ Unable to load MCP configuration: Config file not found[/yellow]"
        )

    @patch("src.claude_agent_chatbot.MCP_AVAILABLE", True)
    @patch("src.claude_agent_chatbot.MCPManager")
    @patch("src.claude_agent_chatbot.ClaudeAgentClient")
    def test_initialize_with_mcp_manager_error(
        self, mock_client_class, mock_manager_class
    ):
        """Test initialization handles MCP manager initialization errors."""
        mock_manager_class.side_effect = Exception("MCP init failed")

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        chatbot = ClaudeAgentChatbot(mcp_config=MagicMock(servers=[]))
        chatbot.console = MagicMock()
        chatbot.initialize()

        # Should still create client, MCP manager should be None
        assert chatbot.client is not None
        assert chatbot.mcp_manager is None
        chatbot.console.print.assert_any_call(
            "[dim]MCP initialization warning: MCP init failed[/dim]"
        )

    def test_help_command_without_mcp(self):
        """Test /help command without MCP manager."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = None

        result = chatbot.handle_command("/help")

        assert result is False
        # Verify help text was displayed
        assert chatbot.console.print.called

    def test_help_command_with_mcp(self):
        """Test /help command with MCP manager."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()

        result = chatbot.handle_command("/help")

        assert result is False
        # Verify help text was displayed
        assert chatbot.console.print.called

    def test_history_command_empty(self):
        """Test /history command with no history."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.history = []

        result = chatbot.handle_command("/history")

        assert result is False
        chatbot.console.print.assert_called_with(
            "[dim]No conversation history yet.[/dim]"
        )

    def test_system_command_no_argument(self):
        """Test /system command without argument."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()

        result = chatbot.handle_command("/system")

        assert result is False
        chatbot.console.print.assert_called_with(
            "[yellow]Usage: /system <new system prompt text>[/yellow]"
        )

    def test_system_command_empty_argument(self):
        """Test /system command with empty argument."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()

        result = chatbot.handle_command("/system   ")

        assert result is False
        chatbot.console.print.assert_called_with(
            "[yellow]Usage: /system <new system prompt text>[/yellow]"
        )

    def test_quit_command(self):
        """Test /quit command returns True to exit."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()

        result = chatbot.handle_command("/quit")

        assert result is True

    def test_mcp_command_shows_usage(self):
        """Test /mcp command alone shows usage."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()

        chatbot.handle_command("/mcp")

        # Should show MCP command list
        calls = chatbot.console.print.call_args_list
        output = " ".join(str(c) for c in calls)
        assert "MCP Commands" in output
        assert "connect" in output
        assert "list" in output

    def test_mcp_list_servers_empty(self):
        """Test /mcp list with no servers configured."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = []

        chatbot._mcp_list_servers()

        chatbot.console.print.assert_called_with("[dim]No MCP servers configured[/dim]")

    def test_mcp_connect_error(self):
        """Test /mcp connect handles errors."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.connect_server_sync.side_effect = Exception("Connection failed")

        chatbot._mcp_connect("test-server")

        chatbot.console.print.assert_called_with(
            "[red]❌ Failed to connect: Connection failed[/red]"
        )

    def test_mcp_disconnect_error(self):
        """Test /mcp disconnect handles errors."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.disconnect_server_sync.side_effect = Exception("Disconnect failed")

        chatbot._mcp_disconnect("test-server")

        chatbot.console.print.assert_called_with(
            "[red]❌ Failed to disconnect: Disconnect failed[/red]"
        )

    def test_mcp_list_tools_no_connected_servers(self):
        """Test /mcp tools with no connected servers."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": False}
        ]

        chatbot._mcp_list_tools()

        chatbot.console.print.assert_called_with("[dim]No MCP servers connected[/dim]")

    def test_mcp_list_tools_no_tools(self):
        """Test /mcp tools when server has no tools."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_tools_sync.return_value = []

        chatbot._mcp_list_tools()

        # Should still print headers but no tools
        chatbot.console.print.assert_any_call("\n[bold]Available MCP Tools:[/bold]")

    def test_mcp_list_resources_no_connected_servers(self):
        """Test /mcp resources with no connected servers."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = []

        chatbot._mcp_list_resources()

        chatbot.console.print.assert_called_with("[dim]No MCP servers connected[/dim]")

    def test_mcp_list_resources_with_resources(self):
        """Test /mcp resources displays resources correctly."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_resources_sync.return_value = [
            {"uri": "file:///test.txt", "description": "Test file"}
        ]

        chatbot._mcp_list_resources()

        calls = chatbot.console.print.call_args_list
        output = " ".join(str(c) for c in calls)
        assert "file:///test.txt" in output
        assert "Test file" in output

    def test_mcp_list_prompts_no_connected_servers(self):
        """Test /mcp prompts with no connected servers."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = []

        chatbot._mcp_list_prompts()

        chatbot.console.print.assert_called_with("[dim]No MCP servers connected[/dim]")

    def test_mcp_list_prompts_with_prompts(self):
        """Test /mcp prompts displays prompts correctly."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_prompts_sync.return_value = [
            {"name": "test-prompt", "description": "Test prompt template"}
        ]

        chatbot._mcp_list_prompts()

        calls = chatbot.console.print.call_args_list
        output = " ".join(str(c) for c in calls)
        assert "test-prompt" in output
        assert "Test prompt template" in output

    def test_mcp_use_prompt_not_found(self):
        """Test /mcp prompt with non-existent prompt."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_prompts_sync.return_value = []

        chatbot._mcp_use_prompt("nonexistent", "")

        chatbot.console.print.assert_called_with(
            "[red]❌ Prompt not found: nonexistent[/red]"
        )

    def test_mcp_use_prompt_with_args(self):
        """Test /mcp prompt with arguments."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_prompts_sync.return_value = [
            {"name": "test-prompt", "description": "Test"}
        ]
        chatbot.mcp_manager.get_prompt_sync.return_value = {
            "messages": [
                {"role": "user", "content": "Prompt content with args"}
            ]
        }

        chatbot._mcp_use_prompt("test-prompt", "key=value foo=bar")

        # Verify prompt was retrieved with parsed arguments
        chatbot.mcp_manager.get_prompt_sync.assert_called_with(
            "server1", "test-prompt", {"key": "value", "foo": "bar"}
        )
        # Verify content was displayed
        assert chatbot.console.print.called

    def test_mcp_use_prompt_non_string_content(self):
        """Test /mcp prompt with non-string content (should skip)."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True}
        ]
        chatbot.mcp_manager.get_prompts_sync.return_value = [
            {"name": "test-prompt", "description": "Test"}
        ]
        chatbot.mcp_manager.get_prompt_sync.return_value = {
            "messages": [
                {"role": "user", "content": {"type": "image", "data": "..."}}
            ]
        }

        chatbot._mcp_use_prompt("test-prompt", "")

        # Should not display non-string content
        # Only the result return should happen
        assert chatbot.console.print.call_count == 0

    def test_mcp_invalid_subcommand(self):
        """Test /mcp with invalid subcommand."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.mcp_manager = MagicMock()

        chatbot.handle_command("/mcp invalid")

        calls = chatbot.console.print.call_args_list
        output = " ".join(str(c) for c in calls)
        assert "Invalid MCP command" in output

    def test_chat_once_without_client(self):
        """Test _chat_once raises error when client not initialized."""
        chatbot = ClaudeAgentChatbot()
        chatbot.client = None

        with pytest.raises(RuntimeError, match="Claude client is not initialized"):
            chatbot._chat_once("Hello")

    def test_record_turn_file_error(self):
        """Test _record_turn handles file write errors gracefully."""
        chatbot = ClaudeAgentChatbot()

        with patch("builtins.open", side_effect=OSError("File error")):
            # Should not raise, just skip file writing
            chatbot._record_turn("user", "test message")

        # History should still be recorded in memory
        assert chatbot.history[-1] == {"role": "user", "content": "test message"}

    @patch("src.claude_agent_chatbot.prompt")
    def test_run_keyboard_interrupt(self, mock_prompt):
        """Test run handles KeyboardInterrupt gracefully."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.initialize = MagicMock()
        chatbot.mcp_manager = MagicMock()

        mock_prompt.side_effect = KeyboardInterrupt()

        chatbot.run()

        chatbot.console.print.assert_any_call("\n[dim]Exiting...[/dim]")
        chatbot.client.close.assert_called_once()
        chatbot.mcp_manager.cleanup_sync.assert_called_once()

    @patch("src.claude_agent_chatbot.prompt")
    def test_run_empty_input(self, mock_prompt):
        """Test run handles empty input correctly."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.initialize = MagicMock()

        # Provide empty strings then quit
        mock_prompt.side_effect = ["", "   ", "/quit"]

        chatbot.run()

        # Should skip empty inputs and not call _chat_once
        chatbot.client.send_message.assert_not_called()

    @patch("src.claude_agent_chatbot.prompt")
    def test_run_chat_error(self, mock_prompt):
        """Test run handles chat errors gracefully."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.client.send_message.side_effect = Exception("Chat error")
        chatbot.initialize = MagicMock()

        mock_prompt.side_effect = ["Hello", "/quit"]

        chatbot.run()

        # Error should be displayed
        chatbot.console.print.assert_any_call("[bold red]Error: Chat error[/bold red]")

    @patch("src.claude_agent_chatbot.prompt")
    def test_run_without_mcp_manager(self, mock_prompt):
        """Test run without MCP manager doesn't crash on cleanup."""
        chatbot = ClaudeAgentChatbot()
        chatbot.console = MagicMock()
        chatbot.client = MagicMock()
        chatbot.initialize = MagicMock()
        chatbot.mcp_manager = None

        mock_prompt.side_effect = ["/quit"]

        chatbot.run()

        # Should not crash, just skip MCP cleanup
        chatbot.client.close.assert_called_once()
