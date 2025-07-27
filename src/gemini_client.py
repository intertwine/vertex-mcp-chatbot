"""Gemini client for interacting with Google Gen AI."""

from typing import Optional, List
from google import genai
from google.genai import types
from .config import Config


class GeminiClient:
    """Client for interacting with Gemini models via Google Gen AI."""

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the Gemini client.

        Args:
            model_name: Name of the model to use. Defaults to Config.DEFAULT_MODEL.
        """
        self.model_name = model_name or Config.DEFAULT_MODEL
        self._initialize_client()
        self.chat_session = None

    def _initialize_client(self):
        """Initialize Google Gen AI client with Application Default Credentials."""
        try:
            # Initialize client with Vertex AI using Application Default Credentials
            self.client = genai.Client(
                vertexai=True,
                project=Config.get_project_id(),
                location=Config.get_location(),
            )
            print("✅ Google Gen AI client initialized successfully")
            print(f"✅ Model '{self.model_name}' ready")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Google Gen AI client: {e}")

    def start_chat(self, system_instruction: Optional[str] = None):
        """Start a new chat session.

        Args:
            system_instruction: Optional system instruction to guide the model.
        """
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction

        self.chat_session = self.client.chats.create(
            model=self.model_name, config=config
        )
        return self.chat_session

    def send_message(
        self, message: str, system_instruction: Optional[str] = None
    ) -> str:
        """
        Send a message to the chat session.

        Args:
            message: The message to send.
            system_instruction: Optional system instruction for new sessions.

        Returns:
            The response text from the model.
        """
        if not self.chat_session:
            self.start_chat(system_instruction)

        try:
            response = self.chat_session.send_message(message)
            return response.text
        except Exception as e:
            raise RuntimeError(f"Failed to send message: {e}")

    def get_chat_history(self) -> List:
        """Get the current chat history."""
        if not self.chat_session:
            return []
        try:
            return self.chat_session.get_history()
        except Exception:
            return []

    def clear_chat(self):
        """Clear the current chat session."""
        self.chat_session = None
