"""Client wrapper around the Claude Agent SDK."""

from __future__ import annotations

import importlib
import logging
from types import SimpleNamespace
from typing import Any, Dict, Iterable, List, Optional

from .config import Config

LOGGER = logging.getLogger(__name__)


def _resolve_sdk_client_class():
    """Return the Claude SDK client class, falling back to the local stub."""

    try:
        module = importlib.import_module("claude_sdk")
        return getattr(module, "ClaudeSDKClient")
    except (ImportError, AttributeError):
        from .claude_sdk_fallback import ClaudeSDKClient

        return ClaudeSDKClient


class ClaudeAgentClient:
    """High level helper for creating agents and chatting with Claude."""

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

        self.agent = None
        self.session = None
        self.history: List[Dict[str, str]] = []

    # ------------------------------------------------------------------
    # SDK helpers
    # ------------------------------------------------------------------
    def _create_sdk_client(self):
        cls = _resolve_sdk_client_class()
        init_kwargs = Config.get_claude_sdk_init_kwargs(self.model_name)

        try:
            return cls(**init_kwargs)
        except TypeError as exc:
            LOGGER.debug(
                "Claude SDK client rejected init kwargs %s; retrying without default model.",
                exc,
            )
            trimmed_kwargs = dict(init_kwargs)
            trimmed_kwargs.pop("default_model", None)
            return cls(**trimmed_kwargs)

    def ensure_session(self, system_instruction: Optional[str] = None) -> None:
        """Ensure both agent and session exist."""

        if system_instruction is not None and system_instruction != self.system_prompt:
            self.system_prompt = system_instruction
            self.agent = None
            self.session = None

        if self.agent is None:
            self.agent = self._create_agent(self.system_prompt)
            self.session = None

        if self.session is None:
            self.session = self._create_session(self.agent)

    def _create_agent(self, system_instruction: Optional[str]):
        payload = {
            "name": "Vertex MCP Claude Agent",
            "instructions": system_instruction,
            "default_model": self.model_name,
        }
        if self._mcp_servers:
            payload["mcp_servers"] = list(self._mcp_servers)

        agents = getattr(self._sdk_client, "agents", None)
        if agents and hasattr(agents, "create"):
            return agents.create(**payload)

        create_fn = getattr(self._sdk_client, "create_agent", None)
        if create_fn:
            return create_fn(**payload)

        raise RuntimeError("Claude SDK client does not expose an agent creation API")

    def _create_session(self, agent):
        agent_id = self._extract_id(agent)

        sessions = getattr(self._sdk_client, "sessions", None)
        if sessions and hasattr(sessions, "create"):
            return sessions.create(agent_id=agent_id)

        create_fn = getattr(self._sdk_client, "create_session", None)
        if create_fn:
            return create_fn(agent_id=agent_id)

        raise RuntimeError("Claude SDK client does not expose a session creation API")

    def _extract_id(self, obj: Any) -> str:
        if isinstance(obj, dict):
            return obj.get("id")
        return getattr(obj, "id")

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    def send_message(
        self,
        message: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        self.ensure_session(system_instruction)

        sessions = getattr(self._sdk_client, "sessions", None)
        payload = {
            "session_id": self._extract_id(self.session),
            "content": message,
        }

        if sessions and hasattr(sessions, "send_message"):
            response = sessions.send_message(**payload)
        elif sessions and hasattr(sessions, "create_message"):
            response = sessions.create_message(**payload)
        else:
            send_fn = getattr(self._sdk_client, "send_message", None)
            if not send_fn:
                raise RuntimeError(
                    "Claude SDK client does not expose a session messaging API"
                )
            response = send_fn(**payload)

        text = self._extract_text(response)
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": text})
        return text

    def _extract_text(self, response: Any) -> str:
        if hasattr(response, "output_text"):
            return response.output_text

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

        if isinstance(response, dict) and "output_text" in response:
            return response["output_text"]

        return str(response)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def reset_session(self, system_instruction: Optional[str] = None) -> None:
        self.system_prompt = system_instruction or self.system_prompt
        self.agent = None
        self.session = None
        self.ensure_session(self.system_prompt)

    def get_chat_history(self) -> List[Dict[str, str]]:
        return list(self.history)

    def close(self) -> None:
        close_fn = getattr(self._sdk_client, "close", None)
        if callable(close_fn):
            close_fn()


__all__ = ["ClaudeAgentClient", "_resolve_sdk_client_class"]
