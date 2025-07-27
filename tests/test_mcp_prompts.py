"""Tests for MCP prompt template handling in chatbot."""

import pytest
from unittest.mock import Mock, patch
from src.chatbot import GeminiChatbot


class TestMCPPrompts:
    """Test MCP prompt template integration."""

    @patch("src.chatbot.os.makedirs")
    def test_mcp_prompts_command(self, mock_makedirs):
        """Test /mcp prompts command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[{"name": "test-server", "connected": True}]
        )
        chatbot.mcp_manager.get_prompts_sync = Mock(
            return_value=[
                {
                    "name": "analyze_code",
                    "description": "Analyze code for best practices",
                    "arguments": [
                        {
                            "name": "language",
                            "description": "Programming language",
                            "required": True,
                        },
                        {
                            "name": "focus",
                            "description": "Specific aspect to focus on",
                            "required": False,
                        },
                    ],
                    "server": "dev-server",
                },
                {
                    "name": "summarize",
                    "description": "Create a summary of content",
                    "arguments": [
                        {
                            "name": "style",
                            "description": "Summary style (brief, detailed)",
                            "required": False,
                        }
                    ],
                    "server": "docs-server",
                },
            ]
        )

        result = chatbot.process_command("/mcp prompts")

        assert result is True
        # Should print header and prompts
        assert chatbot.console.print.call_count >= 3
        # Verify prompt details are shown
        call_args = [
            str(call) for call in chatbot.console.print.call_args_list
        ]
        assert any("analyze_code" in str(arg) for arg in call_args)
        assert any(
            "Analyze code for best practices" in str(arg) for arg in call_args
        )

    @patch("src.chatbot.os.makedirs")
    def test_mcp_prompts_no_servers(self, mock_makedirs):
        """Test /mcp prompts when no servers connected."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(return_value=[])

        result = chatbot.process_command("/mcp prompts")

        assert result is True
        chatbot.console.print.assert_called_with(
            "[dim]No MCP servers connected[/dim]"
        )

    @patch("src.chatbot.os.makedirs")
    def test_mcp_prompts_no_prompts(self, mock_makedirs):
        """Test /mcp prompts when servers have no prompts."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[{"name": "test-server", "connected": True}]
        )
        chatbot.mcp_manager.get_prompts_sync = Mock(return_value=[])

        result = chatbot.process_command("/mcp prompts")

        assert result is True
        chatbot.console.print.assert_called_with(
            "[dim]No prompts available from connected servers[/dim]"
        )

    @patch("src.chatbot.os.makedirs")
    def test_mcp_prompt_use_command(self, mock_makedirs):
        """Test /mcp prompt <name> command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        # Mock status context manager
        status_mock = Mock()
        status_mock.__enter__ = Mock(return_value=status_mock)
        status_mock.__exit__ = Mock(return_value=None)
        chatbot.console.status = Mock(return_value=status_mock)

        chatbot.client = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.display_response = Mock()

        # Mock prompt availability
        chatbot.mcp_manager.get_prompts_sync = Mock(
            return_value=[
                {
                    "name": "analyze_code",
                    "description": "Analyze code for best practices",
                    "arguments": [
                        {
                            "name": "language",
                            "description": "Programming language",
                            "required": True,
                        }
                    ],
                    "server": "dev-server",
                }
            ]
        )

        # Mock get_prompt call
        chatbot.mcp_manager.get_prompt_sync = Mock(
            return_value={
                "description": "Analyze code for best practices",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": "Please analyze the Python code for best practices, focusing on code style, efficiency, and potential bugs.",
                        },
                    }
                ],
            }
        )

        # Mock Gemini response
        chatbot.client.send_message = Mock(
            return_value="I'll analyze the Python code for best practices..."
        )

        result = chatbot.process_command(
            "/mcp prompt analyze_code language=python"
        )

        assert result is True
        chatbot.mcp_manager.get_prompt_sync.assert_called_once_with(
            "dev-server", "analyze_code", {"language": "python"}
        )

    @patch("src.chatbot.os.makedirs")
    def test_mcp_prompt_not_found(self, mock_makedirs):
        """Test /mcp prompt with non-existent prompt."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.get_prompts_sync = Mock(return_value=[])

        result = chatbot.process_command("/mcp prompt nonexistent")

        assert result is True
        chatbot.console.print.assert_called_with(
            "[red]Prompt 'nonexistent' not found in connected servers[/red]"
        )

    @patch("src.chatbot.os.makedirs")
    def test_find_prompt_server(self, mock_makedirs):
        """Test finding which server provides a prompt."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.get_prompts_sync = Mock(
            return_value=[
                {"name": "analyze", "server": "server1"},
                {"name": "summarize", "server": "server2"},
            ]
        )

        assert chatbot._find_prompt_server("analyze") == "server1"
        assert chatbot._find_prompt_server("summarize") == "server2"
        assert chatbot._find_prompt_server("unknown") is None

    @patch("src.chatbot.os.makedirs")
    def test_parse_prompt_args(self, mock_makedirs):
        """Test parsing prompt arguments from command."""
        chatbot = GeminiChatbot()

        # Test various argument formats
        assert chatbot._parse_prompt_args("arg1=value1 arg2=value2") == {
            "arg1": "value1",
            "arg2": "value2",
        }

        assert chatbot._parse_prompt_args('name="John Doe" age=30') == {
            "name": "John Doe",
            "age": "30",
        }

        assert chatbot._parse_prompt_args("style=brief") == {"style": "brief"}

        assert chatbot._parse_prompt_args("") == {}

    @patch("src.chatbot.os.makedirs")
    def test_format_prompt_for_gemini(self, mock_makedirs):
        """Test formatting MCP prompt messages for Gemini."""
        chatbot = GeminiChatbot()

        prompt_result = {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Analyze this code for best practices",
                    },
                },
                {
                    "role": "assistant",
                    "content": {
                        "type": "text",
                        "text": "I'll analyze the code...",
                    },
                },
            ]
        }

        formatted = chatbot._format_prompt_for_gemini(prompt_result)

        assert "Analyze this code for best practices" in formatted
        # Should only include user messages for now
        assert "I'll analyze the code..." not in formatted

    @patch("src.chatbot.os.makedirs")
    def test_suggest_prompts_for_query(self, mock_makedirs):
        """Test suggesting relevant prompts based on user query."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.get_prompts_sync = Mock(
            return_value=[
                {
                    "name": "analyze_code",
                    "description": "Analyze code for best practices",
                    "server": "dev-server",
                },
                {
                    "name": "explain_error",
                    "description": "Explain error messages and provide solutions",
                    "server": "dev-server",
                },
                {
                    "name": "summarize_docs",
                    "description": "Summarize documentation",
                    "server": "docs-server",
                },
            ]
        )

        # Should suggest code-related prompts
        suggestions = chatbot._suggest_prompts_for_query(
            "Can you analyze my Python code?"
        )
        assert any(p["name"] == "analyze_code" for p in suggestions)

        # Should suggest error-related prompts
        suggestions = chatbot._suggest_prompts_for_query(
            "I'm getting an error message"
        )
        assert any(p["name"] == "explain_error" for p in suggestions)

        # Should return empty for unrelated queries
        suggestions = chatbot._suggest_prompts_for_query("What's the weather?")
        assert len(suggestions) == 0
