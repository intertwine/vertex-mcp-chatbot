"""Integration tests for the chatbot system."""

from io import StringIO
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.chatbot import GeminiChatbot
from src.config import Config
from src.gemini_client import GeminiClient


class TestIntegration:
    """Integration test cases for the complete chatbot system."""

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_chatbot_gemini_client_integration(self, mock_makedirs, mock_genai_client):
        """Test integration between GeminiChatbot and GeminiClient."""
        # Mock the genai client
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you today?"

        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_chat_session.send_message.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        # Create chatbot and initialize
        chatbot = GeminiChatbot(model_name="gemini-2.5-flash")
        chatbot.console = Mock()  # Mock console to avoid output

        # Initialize the chatbot (this creates the GeminiClient)
        chatbot.initialize()

        # Verify the client was created with correct model
        assert chatbot.client is not None
        assert chatbot.client.model_name == "gemini-2.5-flash"

        # Test sending a message through the full stack
        response = chatbot.client.send_message("Hello")

        assert response == "Hello! How can I help you today?"
        mock_chat_session.send_message.assert_called_once_with("Hello")

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_config_integration(self, mock_makedirs, mock_genai_client):
        """Test that Config values are properly used throughout the system."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # Test with default model from config
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.initialize()

        # Verify the client uses the default model from Config
        assert chatbot.client.model_name == Config.DEFAULT_MODEL

        # Verify the genai client was initialized with config values
        mock_genai_client.assert_called_with(
            vertexai=True,
            project=Config.get_project_id(),
            location=Config.get_location(),
        )

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_chat_history_integration(self, mock_makedirs, mock_genai_client):
        """Test chat history functionality across the system."""
        # Mock the genai client and chat session
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.chats.create.return_value = mock_chat_session

        # Mock chat history
        mock_history_item1 = Mock()
        mock_history_item1.role = "user"
        mock_history_item1.parts = [Mock()]
        mock_history_item1.parts[0].text = "What is AI?"

        mock_history_item2 = Mock()
        mock_history_item2.role = "assistant"
        mock_history_item2.parts = [Mock()]
        mock_history_item2.parts[0].text = "AI stands for Artificial Intelligence..."

        mock_chat_session.get_history.return_value = [
            mock_history_item1,
            mock_history_item2,
        ]

        # Create and initialize chatbot
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.console.size = Mock()
        chatbot.console.size.width = 80
        chatbot.console.size.height = 24
        chatbot.initialize()

        # Test getting history through the full stack
        history = chatbot.client.get_chat_history()
        # Note: Since we're mocking, we need to set up the mock properly
        chatbot.client.chat_session = mock_chat_session
        history = chatbot.client.get_chat_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[1].role == "assistant"

        # Test displaying history
        with patch("src.chatbot.Console") as mock_console_class:
            mock_temp_console = Mock()
            mock_temp_console.file = StringIO("Short history\nLine 2\n")
            mock_console_class.return_value = mock_temp_console

            chatbot.display_history()

        # Verify console was called to display the history
        assert chatbot.console.print.call_count >= 1

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_command_processing_integration(self, mock_makedirs, mock_genai_client):
        """Test command processing with real client interactions."""
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_genai_client.return_value = mock_client_instance
        mock_client_instance.chats.create.return_value = mock_chat_session

        # Create and initialize chatbot
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.initialize()

        # Test /clear command
        result = chatbot.process_command("/clear")
        assert result is True
        # Verify that clear_chat was called (it's a method, not a mock)
        assert chatbot.client.chat_session is None

        # Test /model command
        result = chatbot.process_command("/model")
        assert result is True
        # Should display the current model name
        model_calls = [
            call
            for call in chatbot.console.print.call_args_list
            if "Current model:" in str(call)
        ]
        assert len(model_calls) > 0

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_error_handling_integration(self, mock_makedirs, mock_genai_client):
        """Test error handling across the integrated system."""
        # Test client initialization failure
        mock_genai_client.side_effect = Exception("Authentication failed")

        chatbot = GeminiChatbot()
        chatbot.console = Mock()

        with patch("src.chatbot.sys.exit") as mock_exit:
            chatbot.initialize()
            mock_exit.assert_called_once_with(1)

        # Test message sending failure
        mock_genai_client.side_effect = None  # Reset the side effect
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_chat_session.send_message.side_effect = Exception(
            "API rate limit exceeded"
        )
        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        chatbot2 = GeminiChatbot()
        chatbot2.console = Mock()
        chatbot2.initialize()

        # Should raise RuntimeError with descriptive message
        with pytest.raises(RuntimeError, match="Failed to send message"):
            chatbot2.client.send_message("Hello")

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_model_switching_integration(self, mock_makedirs, mock_genai_client):
        """Test that different models can be used correctly."""
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        # Test with different models
        models_to_test = [
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ]

        for model in models_to_test:
            chatbot = GeminiChatbot(model_name=model)
            chatbot.console = Mock()
            chatbot.initialize()

            assert chatbot.client.model_name == model

            # Verify the client was initialized with the correct model
            assert chatbot.model_name == model

    @patch("src.gemini_client.genai.Client")
    @patch("src.chatbot.os.makedirs")
    def test_session_lifecycle_integration(self, mock_makedirs, mock_genai_client):
        """Test the complete session lifecycle."""
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"

        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_chat_session.send_message.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        # Create and initialize chatbot
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.console.size = Mock()
        chatbot.console.size.width = 80
        chatbot.console.size.height = 24
        chatbot.initialize()

        # Initially no chat session
        assert chatbot.client.chat_session is None

        # Send first message (should create session)
        response = chatbot.client.send_message("Hello")
        assert chatbot.client.chat_session is not None
        assert response == "Test response"

        # Send second message (should use existing session)
        mock_client_instance.chats.create.reset_mock()  # Reset call count
        response2 = chatbot.client.send_message("How are you?")

        # Should not create a new session
        mock_client_instance.chats.create.assert_not_called()
        assert response2 == "Test response"

        # Clear chat (should reset session)
        chatbot.client.clear_chat()
        assert chatbot.client.chat_session is None
