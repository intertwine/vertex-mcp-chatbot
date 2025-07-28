"""Tests for the gemini_client module."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.config import Config
from src.gemini_client import GeminiClient


class TestGeminiClient:
    """Test cases for the GeminiClient class."""

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_init_with_default_model(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test initialization with default model."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()

        assert client.model_name == Config.DEFAULT_MODEL
        assert client.chat_session is None
        mock_genai_client.assert_called_once_with(
            vertexai=True, project="test-project", location="us-central1"
        )

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_init_with_custom_model(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test initialization with custom model."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        custom_model = "gemini-1.5-pro"
        client = GeminiClient(model_name=custom_model)

        assert client.model_name == custom_model

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_initialize_client_failure(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test client initialization failure."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_genai_client.side_effect = Exception("API Error")

        with pytest.raises(
            RuntimeError, match="Failed to initialize Google Gen AI client"
        ):
            GeminiClient()

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_start_chat(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test starting a chat session."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        result = client.start_chat()

        assert client.chat_session == mock_chat_session
        assert result == mock_chat_session
        mock_client_instance.chats.create.assert_called_once_with(
            model=Config.DEFAULT_MODEL, config={}
        )

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_send_message_new_session(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test sending a message when no chat session exists."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Hello! How can I help you?"

        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_chat_session.send_message.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        response = client.send_message("Hello")

        assert response == "Hello! How can I help you?"
        assert client.chat_session == mock_chat_session
        mock_chat_session.send_message.assert_called_once_with("Hello")

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_send_message_existing_session(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test sending a message with existing chat session."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Response text"

        mock_chat_session.send_message.return_value = mock_response
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        client.chat_session = mock_chat_session  # Set existing session

        response = client.send_message("Test message")

        assert response == "Response text"
        mock_chat_session.send_message.assert_called_once_with("Test message")
        # Should not create a new session
        mock_client_instance.chats.create.assert_not_called()

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_send_message_failure(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test send_message failure handling."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_chat_session.send_message.side_effect = Exception("API Error")

        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()

        with pytest.raises(RuntimeError, match="Failed to send message"):
            client.send_message("Hello")

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_get_chat_history_no_session(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test getting chat history when no session exists."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        history = client.get_chat_history()

        assert history == []

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_get_chat_history_with_session(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test getting chat history with existing session."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_history = ["message1", "message2"]
        mock_chat_session.get_history.return_value = mock_history
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        client.chat_session = mock_chat_session

        history = client.get_chat_history()

        assert history == mock_history
        mock_chat_session.get_history.assert_called_once()

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_get_chat_history_exception(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test getting chat history when an exception occurs."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_chat_session.get_history.side_effect = Exception("History error")
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        client.chat_session = mock_chat_session

        history = client.get_chat_history()

        assert history == []

    @patch("src.gemini_client.genai.Client")
    @patch("src.gemini_client.Config.get_project_id")
    @patch("src.gemini_client.Config.get_location")
    def test_clear_chat(
        self, mock_get_location, mock_get_project_id, mock_genai_client
    ):
        """Test clearing chat session."""
        mock_get_project_id.return_value = "test-project"
        mock_get_location.return_value = "us-central1"
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        client.chat_session = mock_chat_session

        client.clear_chat()

        assert client.chat_session is None
