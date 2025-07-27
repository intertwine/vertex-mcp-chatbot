"""Tests for scrollable response functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from src.chatbot import GeminiChatbot


class TestScrollableResponse:
    """Test cases for the scrollable response display functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chatbot = GeminiChatbot()
        self.chatbot.console = Mock()
        # Mock console size
        self.chatbot.console.size = Mock()
        self.chatbot.console.size.width = 80
        self.chatbot.console.size.height = 24

    def test_short_response_displays_normally(self):
        """Test that short responses are displayed normally without scrolling."""
        short_response = "This is a short response."

        with patch("src.chatbot.Console") as mock_console_class:
            # Mock the temporary console used for measuring content
            mock_temp_console = Mock()
            mock_temp_console.file = StringIO("Short content\nLine 2\n")
            mock_console_class.return_value = mock_temp_console

            self.chatbot.display_response(short_response)

            # Should print normally, not call scrollable display
            assert self.chatbot.console.print.call_count >= 1

    def test_long_response_triggers_scrollable_display(self):
        """Test that long responses trigger the scrollable display."""
        # Create a response that will be longer than terminal height
        long_response = "This is a very long response.\n" * 30

        with patch("src.chatbot.Console") as mock_console_class:
            # Mock the temporary console to return many lines
            mock_temp_console = Mock()
            long_content = "\n".join([f"Line {i}" for i in range(30)])
            mock_temp_console.file = StringIO(long_content)
            mock_console_class.return_value = mock_temp_console

            with patch.object(
                self.chatbot, "_display_scrollable_content"
            ) as mock_scrollable:
                self.chatbot.display_response(long_response)

                # Should call scrollable display
                mock_scrollable.assert_called_once()

    @patch("src.chatbot.Application")
    def test_scrollable_response_creates_application(self, mock_app_class):
        """Test that scrollable response creates a prompt_toolkit Application."""
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        rendered_content = "Line 1\nLine 2\nLine 3\n"
        original_response = "Original response"

        self.chatbot._display_scrollable_content(rendered_content, "Test Title")

        # Should create and run an application
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()

    @patch("src.chatbot.Application")
    def test_scrollable_response_handles_keyboard_interrupt(self, mock_app_class):
        """Test that scrollable response handles KeyboardInterrupt gracefully."""
        mock_app = Mock()
        mock_app.run.side_effect = KeyboardInterrupt()
        mock_app_class.return_value = mock_app

        rendered_content = "Line 1\nLine 2\nLine 3\n"
        original_response = "Original response"

        # Should not raise exception
        self.chatbot._display_scrollable_content(rendered_content, "Test Title")

        # Should still print return message
        assert self.chatbot.console.print.call_count >= 1

    @patch("src.chatbot.KeyBindings")
    @patch("src.chatbot.Application")
    def test_scrollable_response_key_bindings(self, mock_app_class, mock_kb_class):
        """Test that scrollable response sets up proper key bindings."""
        mock_kb = Mock()
        mock_kb_class.return_value = mock_kb
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        rendered_content = "Line 1\nLine 2\nLine 3\n"
        original_response = "Original response"

        self.chatbot._display_scrollable_content(rendered_content, "Test Title")

        # Should create key bindings
        mock_kb_class.assert_called_once()

        # Should register key bindings (check that add was called multiple times)
        assert mock_kb.add.call_count >= 5  # q, escape, up, down, etc.

    def test_content_height_calculation(self):
        """Test that content height is calculated correctly."""
        # Test with content that should fit
        with patch("src.chatbot.Console") as mock_console_class:
            mock_temp_console = Mock()
            short_content = "Line 1\nLine 2\nLine 3\n"  # 4 lines including empty
            mock_temp_console.file = StringIO(short_content)
            mock_console_class.return_value = mock_temp_console

            with patch.object(
                self.chatbot, "_display_scrollable_content"
            ) as mock_scrollable:
                self.chatbot.display_response("Short response")

                # Should not call scrollable display for short content
                mock_scrollable.assert_not_called()

    def test_terminal_size_adaptation(self):
        """Test that the display adapts to different terminal sizes."""
        # Test with small terminal
        self.chatbot.console.size.height = 10

        with patch("src.chatbot.Console") as mock_console_class:
            mock_temp_console = Mock()
            # Content that would be long for small terminal
            medium_content = "\n".join([f"Line {i}" for i in range(15)])
            mock_temp_console.file = StringIO(medium_content)
            mock_console_class.return_value = mock_temp_console

            with patch.object(
                self.chatbot, "_display_scrollable_content"
            ) as mock_scrollable:
                self.chatbot.display_response("Medium response")

                # Should call scrollable display for small terminal
                mock_scrollable.assert_called_once()

    @patch("prompt_toolkit.document.Document")
    @patch("src.chatbot.Buffer")
    @patch("src.chatbot.Application")
    def test_buffer_creation_and_content(
        self, mock_app_class, mock_buffer_class, mock_document_class
    ):
        """Test that buffer is created with correct content."""
        mock_buffer = Mock()
        mock_buffer_class.return_value = mock_buffer
        mock_app = Mock()
        mock_app_class.return_value = mock_app
        mock_document = Mock()
        mock_document_class.return_value = mock_document

        rendered_content = "Test content\nLine 2\nLine 3\n"
        original_response = "Original"

        self.chatbot._display_scrollable_content(rendered_content, "Test Title")

        # Should create buffer with document
        mock_buffer_class.assert_called()
        # Check that Document was called with the rendered content (may be called multiple times)
        document_calls = [
            call.args[0] for call in mock_document_class.call_args_list if call.args
        ]
        assert (
            rendered_content in document_calls
        ), f"Expected {rendered_content} in Document calls: {document_calls}"

    def test_help_text_display(self):
        """Test that help text is displayed to user."""
        with patch("src.chatbot.Application") as mock_app_class:
            mock_app = Mock()
            mock_app_class.return_value = mock_app

            rendered_content = "Test content"
            original_response = "Original"

            self.chatbot._display_scrollable_content(rendered_content, "Test Title")

            # Should print help messages
            print_calls = [
                call.args[0] for call in self.chatbot.console.print.call_args_list
            ]
            help_messages = [
                call
                for call in print_calls
                if "scroll" in call.lower() or "arrow" in call.lower()
            ]
            assert len(help_messages) >= 1


class TestScrollableResponseIntegration:
    """Integration tests for scrollable response functionality."""

    @patch("src.chatbot.GeminiClient")
    def test_end_to_end_scrollable_flow(self, mock_gemini_client):
        """Test the complete flow from response to scrollable display."""
        # Setup
        mock_client = Mock()
        mock_gemini_client.return_value = mock_client

        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.console.size = Mock()
        chatbot.console.size.width = 80
        chatbot.console.size.height = 10  # Small height to trigger scrolling

        # Create a long response that will trigger scrolling
        long_response = (
            "# Long Response\n\n"
            + "This is a very long line of text. " * 20
            + "\n\n"
            + "Another paragraph. " * 15
        )

        with patch("src.chatbot.Console") as mock_console_class:
            # Mock temp console to return many lines
            mock_temp_console = Mock()
            long_content = "\n".join([f"Line {i}" for i in range(20)])
            mock_temp_console.file = StringIO(long_content)
            mock_console_class.return_value = mock_temp_console

            with patch("src.chatbot.Application") as mock_app_class:
                mock_app = Mock()
                mock_app_class.return_value = mock_app

                # Test the display
                chatbot.display_response(long_response)

                # Should create and run scrollable application
                mock_app_class.assert_called_once()
                mock_app.run.assert_called_once()

                # Should print help text
                assert chatbot.console.print.call_count >= 2


class TestScrollableHistory:
    """Test cases for the scrollable history display functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.chatbot = GeminiChatbot()
        self.chatbot.console = Mock()
        self.chatbot.console.size = Mock()
        self.chatbot.console.size.width = 80
        self.chatbot.console.size.height = 24

        # Mock client
        self.chatbot.client = Mock()

    def test_empty_history_displays_normally(self):
        """Test that empty history displays a simple message."""
        self.chatbot.client.get_chat_history.return_value = []

        self.chatbot.display_history()

        # Should print empty history message
        self.chatbot.console.print.assert_called_with(
            "[dim]No conversation history yet[/dim]"
        )

    def test_short_history_displays_normally(self):
        """Test that short history displays normally without scrolling."""
        # Create mock history items
        mock_item1 = Mock()
        mock_item1.role = "user"
        mock_item1.parts = [Mock()]
        mock_item1.parts[0].text = "Hello"

        mock_item2 = Mock()
        mock_item2.role = "assistant"
        mock_item2.parts = [Mock()]
        mock_item2.parts[0].text = "Hi there!"

        self.chatbot.client.get_chat_history.return_value = [
            mock_item1,
            mock_item2,
        ]

        with patch("src.chatbot.Console") as mock_console_class:
            mock_temp_console = Mock()
            mock_temp_console.file = StringIO("Short history\nLine 2\n")
            mock_console_class.return_value = mock_temp_console

            self.chatbot.display_history()

            # Should print normally, not call scrollable display
            assert self.chatbot.console.print.call_count >= 1

    def test_long_history_triggers_scrollable_display(self):
        """Test that long history triggers scrollable display."""
        # Create many mock history items
        history_items = []
        for i in range(20):
            mock_item = Mock()
            mock_item.role = "user" if i % 2 == 0 else "assistant"
            mock_item.parts = [Mock()]
            mock_item.parts[0].text = f"Message {i}"
            history_items.append(mock_item)

        self.chatbot.client.get_chat_history.return_value = history_items

        with patch("src.chatbot.Console") as mock_console_class:
            mock_temp_console = Mock()
            # Create long content that will trigger scrolling
            long_content = "\n".join([f"Line {i}" for i in range(30)])
            mock_temp_console.file = StringIO(long_content)
            mock_console_class.return_value = mock_temp_console

            with patch.object(
                self.chatbot, "_display_scrollable_content"
            ) as mock_scrollable:
                self.chatbot.display_history()

                # Should call scrollable display
                mock_scrollable.assert_called_once_with(
                    long_content, "Conversation History"
                )

    def test_build_history_content(self):
        """Test that history content is built correctly."""
        # Create mock history items
        mock_item1 = Mock()
        mock_item1.role = "user"
        mock_item1.parts = [Mock()]
        mock_item1.parts[0].text = "Hello"

        mock_item2 = Mock()
        mock_item2.role = "assistant"
        mock_item2.parts = [Mock()]
        mock_item2.parts[0].text = "Hi there!"

        history = [mock_item1, mock_item2]

        content = self.chatbot._build_history_content(history)

        # Should return Rich Text object
        from rich.text import Text

        assert isinstance(content, Text)

        # Should contain the conversation content
        content_str = str(content)
        assert "Conversation History:" in content_str

    def test_history_with_no_parts(self):
        """Test history items that don't have parts attribute."""
        mock_item = Mock()
        mock_item.role = "user"
        # No parts attribute
        del mock_item.parts

        history = [mock_item]

        content = self.chatbot._build_history_content(history)

        # Should handle items without parts gracefully
        from rich.text import Text

        assert isinstance(content, Text)

    def test_history_role_fallback(self):
        """Test history items that don't have role attribute."""
        mock_item1 = Mock()
        # No role attribute
        del mock_item1.role
        mock_item1.parts = [Mock()]
        mock_item1.parts[0].text = "Test message"

        mock_item2 = Mock()
        del mock_item2.role
        mock_item2.parts = [Mock()]
        mock_item2.parts[0].text = "Response message"

        history = [mock_item1, mock_item2]

        content = self.chatbot._build_history_content(history)

        # Should handle items without role using fallback logic
        from rich.text import Text

        assert isinstance(content, Text)
