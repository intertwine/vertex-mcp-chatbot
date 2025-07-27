"""Tests for the main module."""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from main import main


class TestMain:
    """Test cases for the main function."""

    @patch("main.GeminiChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    def test_main_default_args(self, mock_parse_args, mock_chatbot_class):
        """Test main function with default arguments."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_parse_args.return_value = mock_args

        # Mock chatbot instance
        mock_chatbot = Mock()
        mock_chatbot_class.return_value = mock_chatbot

        main()

        mock_chatbot_class.assert_called_once_with(model_name=None)
        mock_chatbot.run.assert_called_once()

    @patch("main.GeminiChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    def test_main_custom_model(self, mock_parse_args, mock_chatbot_class):
        """Test main function with custom model argument."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = "gemini-1.5-pro"
        mock_parse_args.return_value = mock_args

        # Mock chatbot instance
        mock_chatbot = Mock()
        mock_chatbot_class.return_value = mock_chatbot

        main()

        mock_chatbot_class.assert_called_once_with(model_name="gemini-1.5-pro")
        mock_chatbot.run.assert_called_once()

    @patch("main.GeminiChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_keyboard_interrupt(
        self, mock_exit, mock_parse_args, mock_chatbot_class
    ):
        """Test main function handling KeyboardInterrupt."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_parse_args.return_value = mock_args

        # Mock chatbot to raise KeyboardInterrupt
        mock_chatbot = Mock()
        mock_chatbot.run.side_effect = KeyboardInterrupt()
        mock_chatbot_class.return_value = mock_chatbot

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\n\nExiting...")
        mock_exit.assert_called_once_with(0)

    @patch("main.GeminiChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_general_exception(
        self, mock_exit, mock_parse_args, mock_chatbot_class
    ):
        """Test main function handling general exceptions."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_parse_args.return_value = mock_args

        # Mock chatbot to raise general exception
        mock_chatbot = Mock()
        mock_chatbot.run.side_effect = Exception("Test error")
        mock_chatbot_class.return_value = mock_chatbot

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\nError: Test error", file=sys.stderr)
        mock_exit.assert_called_once_with(1)

    @patch("main.GeminiChatbot")
    @patch("main.argparse.ArgumentParser.parse_args")
    @patch("main.sys.exit")
    def test_main_chatbot_creation_exception(
        self, mock_exit, mock_parse_args, mock_chatbot_class
    ):
        """Test main function handling exception during chatbot creation."""
        # Mock command line arguments
        mock_args = Mock()
        mock_args.model = None
        mock_parse_args.return_value = mock_args

        # Mock chatbot class to raise exception during initialization
        mock_chatbot_class.side_effect = Exception("Initialization error")

        with patch("builtins.print") as mock_print:
            main()

        mock_print.assert_called_with("\nError: Initialization error", file=sys.stderr)
        mock_exit.assert_called_once_with(1)

    def test_argument_parser_setup(self):
        """Test that argument parser is set up correctly."""
        with patch("main.GeminiChatbot") as mock_chatbot_class:
            with patch("sys.argv", ["main.py", "--model", "gemini-1.5-pro"]):
                mock_chatbot = Mock()
                mock_chatbot_class.return_value = mock_chatbot

                main()

                mock_chatbot_class.assert_called_once_with(model_name="gemini-1.5-pro")

    def test_argument_parser_help_text(self):
        """Test that help text is properly configured."""
        # This test ensures the argument parser has the expected help configuration
        with patch("sys.argv", ["main.py", "--help"]):
            with pytest.raises(SystemExit):
                main()

    def test_argument_parser_default_model(self):
        """Test that default model argument works correctly."""
        with patch("main.GeminiChatbot") as mock_chatbot_class:
            with patch("sys.argv", ["main.py"]):
                mock_chatbot = Mock()
                mock_chatbot_class.return_value = mock_chatbot

                main()

                # Should be called with None when no model specified
                mock_chatbot_class.assert_called_once_with(model_name=None)
