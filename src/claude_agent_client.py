"""Client wrapper around the Anthropic SDK for Claude via Vertex AI."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Iterable, List, Optional

from .config import Config

LOGGER = logging.getLogger(__name__)


def _resolve_sdk_client_class():
    """Return the Anthropic client class, falling back to the local stub."""

    try:
        module = importlib.import_module("anthropic")
        return getattr(module, "Anthropic")
    except (ImportError, AttributeError):
        from .claude_sdk_fallback import ClaudeSDKClient

        return ClaudeSDKClient


class ClaudeAgentClient:
    """High level helper for chatting with Claude via Vertex AI using the Anthropic SDK."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        sdk_client=None,
        mcp_servers: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> None:
        self.model_name = model_name or Config.get_default_claude_model()
        self.system_prompt = system_prompt
        self._sdk_client = sdk_client or self._create_sdk_client()
        self._mcp_servers = list(mcp_servers or [])
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # SDK helpers
    # ------------------------------------------------------------------
    def _create_sdk_client(self):
        cls = _resolve_sdk_client_class()
        init_kwargs = Config.get_claude_sdk_init_kwargs(self.model_name)

        # Remove parameters that Anthropic SDK doesn't accept
        init_kwargs.pop("default_model", None)

        try:
            return cls(**init_kwargs)
        except TypeError as exc:
            LOGGER.warning(
                "Failed to initialize Anthropic client with kwargs %s: %s",
                init_kwargs.keys(), exc
            )
            # Try with minimal kwargs
            minimal_kwargs = {}
            if "api_key" in init_kwargs:
                minimal_kwargs["api_key"] = init_kwargs["api_key"]
            if "base_url" in init_kwargs:
                minimal_kwargs["base_url"] = init_kwargs["base_url"]
            if "default_headers" in init_kwargs:
                minimal_kwargs["default_headers"] = init_kwargs["default_headers"]
            elif "extra_headers" in init_kwargs:
                minimal_kwargs["default_headers"] = init_kwargs["extra_headers"]

            return cls(**minimal_kwargs)

    def ensure_session(self, system_instruction: Optional[str] = None) -> None:
        """Update system prompt if changed."""
        if system_instruction is not None and system_instruction != self.system_prompt:
            self.system_prompt = system_instruction

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    def send_message(
        self,
        message: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Send a message to Claude and get a response.

        Uses the Anthropic Messages API, maintaining conversation history.
        """
        self.ensure_session(system_instruction)

        # Add the new user message to history
        self.history.append({"role": "user", "content": message})

        # Check if we're using the fallback stub
        if hasattr(self._sdk_client, "sessions"):
            # Using fallback stub
            return self._send_with_fallback(message)

        # Using real Anthropic SDK
        try:
            # Build messages list from history
            messages = [{"role": msg["role"], "content": msg["content"]}
                       for msg in self.history]

            # Prepare API call parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 4096,
            }

            if self.system_prompt:
                params["system"] = self.system_prompt

            # Call the Messages API
            response = self._sdk_client.messages.create(**params)

            # Extract text from response
            text = self._extract_text_from_message(response)

            # Add assistant response to history
            self.history.append({"role": "assistant", "content": text})

            return text

        except Exception as exc:
            LOGGER.error("Error calling Claude API: %s", exc)
            raise

    def _send_with_fallback(self, message: str) -> str:
        """Send message using fallback stub."""
        session_id = "fallback-session"
        response = self._sdk_client.sessions.send_message(
            session_id=session_id,
            content=message
        )
        text = getattr(response, "output_text", str(response))
        self.history.append({"role": "assistant", "content": text})
        return text

    def _extract_text_from_message(self, response: Any) -> str:
        """Extract text from Anthropic Messages API response."""
        content = getattr(response, "content", None)
        if isinstance(content, list):
            texts: List[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                else:
                    if getattr(block, "type", "") == "text":
                        texts.append(getattr(block, "text", ""))
            if texts:
                return "\n".join(texts)

        return str(response)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def reset_session(self, system_instruction: Optional[str] = None) -> None:
        """Clear conversation history and optionally update system prompt."""
        self.system_prompt = system_instruction or self.system_prompt
        self.history.clear()

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return list(self.history)

    def close(self) -> None:
        """Close the SDK client if it has a close method."""
        close_fn = getattr(self._sdk_client, "close", None)
        if callable(close_fn):
            close_fn()


__all__ = ["ClaudeAgentClient", "_resolve_sdk_client_class"]
