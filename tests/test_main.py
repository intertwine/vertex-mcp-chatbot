"""Tests for the main module."""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from main import main


class TestMain:
    """Test cases for the main function."""

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    def test_main_default_args(
        self, mock_parse_args, mock_claude_chatbot_class, mock_gemini_chatbot_class
    ):
        """Test main function with default arguments."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_args.provider = "claude"
        mock_parse_args.return_value = mock_args

        # Mock chatbot instance
        mock_chatbot = Mock()
        mock_claude_chatbot_class.return_value = mock_chatbot

        main()

        mock_claude_chatbot_class.assert_called_once_with(model_name=None)
        mock_gemini_chatbot_class.assert_not_called()
        mock_chatbot.run.assert_called_once()

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    def test_main_custom_model(
        self, mock_parse_args, mock_claude_chatbot_class, mock_gemini_chatbot_class
    ):
        """Test main function with custom model argument."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = "claude-4-haiku"
        mock_args.provider = "claude"
        mock_parse_args.return_value = mock_args

        # Mock chatbot instance
        mock_chatbot = Mock()
        mock_claude_chatbot_class.return_value = mock_chatbot

        main()

        mock_claude_chatbot_class.assert_called_once_with(model_name="claude-4-haiku")
        mock_gemini_chatbot_class.assert_not_called()
        mock_chatbot.run.assert_called_once()

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_keyboard_interrupt(
        self,
        mock_exit,
        mock_parse_args,
        mock_claude_chatbot_class,
        mock_gemini_chatbot_class,
    ):
        """Test main function handling KeyboardInterrupt."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_args.provider = "claude"
        mock_parse_args.return_value = mock_args

        # Mock chatbot to raise KeyboardInterrupt
        mock_chatbot = Mock()
        mock_chatbot.run.side_effect = KeyboardInterrupt()
        mock_claude_chatbot_class.return_value = mock_chatbot

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\n\nExiting...")
        mock_exit.assert_called_once_with(0)
        mock_gemini_chatbot_class.assert_not_called()

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_general_exception(
        self,
        mock_exit,
        mock_parse_args,
        mock_claude_chatbot_class,
        mock_gemini_chatbot_class,
    ):
        """Test main function handling general exceptions."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_args.provider = "claude"
        mock_parse_args.return_value = mock_args

        # Mock chatbot to raise general exception
        mock_chatbot = Mock()
        mock_chatbot.run.side_effect = Exception("Test error")
        mock_claude_chatbot_class.return_value = mock_chatbot

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\nError: Test error", file=sys.stderr)
        mock_exit.assert_called_once_with(1)
        mock_gemini_chatbot_class.assert_not_called()

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_chatbot_creation_exception(
        self,
        mock_exit,
        mock_parse_args,
        mock_claude_chatbot_class,
        mock_gemini_chatbot_class,
    ):
        """Test main function handling exception during chatbot creation."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_args.provider = "claude"
        mock_parse_args.return_value = mock_args

        # Mock chatbot class to raise exception during initialization
        mock_claude_chatbot_class.side_effect = Exception("Initialization error")

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\nError: Initialization error", file=sys.stderr)
        mock_exit.assert_called_once_with(1)
        mock_gemini_chatbot_class.assert_not_called()

    @patch("main.GeminiChatbot")
    @patch("main.ClaudeAgentChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    def test_main_gemini_provider(
        self, mock_parse_args, mock_claude_chatbot_class, mock_gemini_chatbot_class
    ):
        """Test selecting the Gemini provider from the CLI."""
        mock_args = Mock()
        mock_args.model = "gemini-2.0-flash"
        mock_args.provider = "gemini"
        mock_parse_args.return_value = mock_args

        mock_gemini_instance = Mock()
        mock_gemini_chatbot_class.return_value = mock_gemini_instance

        main()

        mock_gemini_chatbot_class.assert_called_once_with(model_name="gemini-2.0-flash")
        mock_gemini_instance.run.assert_called_once()
        mock_claude_chatbot_class.assert_not_called()

    def test_argument_parser_setup(self):
        """Test that argument parser is set up correctly."""
        with patch("main.ClaudeAgentChatbot") as mock_claude_chatbot_class:
            with patch("main.GeminiChatbot") as mock_gemini_chatbot_class:
                with patch(
                    "sys.argv",
                    ["main.py", "--model", "claude-4-haiku", "--provider", "claude"],
                ):
                    mock_chatbot = Mock()
                    mock_claude_chatbot_class.return_value = mock_chatbot

                    main()

                    mock_claude_chatbot_class.assert_called_once_with(
                        model_name="claude-4-haiku"
                    )
                    mock_gemini_chatbot_class.assert_not_called()

    def test_argument_parser_help_text(self):
        """Test that help text is properly configured."""
        # This test ensures the argument parser has the expected help configuration
        with patch("sys.argv", ["main.py", "--help"]):
            with pytest.raises(SystemExit):
                main()

    def test_argument_parser_default_model(self):
        """Test that default model argument works correctly."""
        with patch("main.ClaudeAgentChatbot") as mock_claude_chatbot_class:
            with patch("main.GeminiChatbot") as mock_gemini_chatbot_class:
                with patch("sys.argv", ["main.py"]):
                    mock_chatbot = Mock()
                    mock_claude_chatbot_class.return_value = mock_chatbot

                    main()

                    # Should be called with None when no model specified
                    mock_claude_chatbot_class.assert_called_once_with(model_name=None)
                    mock_gemini_chatbot_class.assert_not_called()
