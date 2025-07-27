"""Tests for Gemini client MCP-related functionality."""

import pytest
from unittest.mock import Mock, patch
from src.gemini_client import GeminiClient


class TestGeminiClientMCP:
    """Test MCP-related features in Gemini client."""

    @patch("src.gemini_client.genai.Client")
    def test_start_chat_with_system_instruction(self, mock_genai_client):
        """Test starting chat with system instruction."""
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        system_instruction = (
            "You are a helpful assistant with access to tools."
        )

        session = client.start_chat(system_instruction)

        assert session == mock_chat_session
        mock_client_instance.chats.create.assert_called_once_with(
            model="gemini-2.5-flash",
            config={"system_instruction": system_instruction},
        )

    @patch("src.gemini_client.genai.Client")
    def test_start_chat_without_system_instruction(self, mock_genai_client):
        """Test starting chat without system instruction."""
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()

        session = client.start_chat()

        assert session == mock_chat_session
        mock_client_instance.chats.create.assert_called_once_with(
            model="gemini-2.5-flash", config={}
        )

    @patch("src.gemini_client.genai.Client")
    def test_send_message_with_system_instruction(self, mock_genai_client):
        """Test sending message with system instruction for new session."""
        mock_client_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"
        mock_chat_session.send_message.return_value = mock_response
        mock_client_instance.chats.create.return_value = mock_chat_session
        mock_genai_client.return_value = mock_client_instance

        client = GeminiClient()
        assert client.chat_session is None

        system_instruction = "You have access to tools."
        response = client.send_message("Hello", system_instruction)

        assert response == "Test response"
        mock_client_instance.chats.create.assert_called_once_with(
            model="gemini-2.5-flash",
            config={"system_instruction": system_instruction},
        )
        mock_chat_session.send_message.assert_called_once_with("Hello")
