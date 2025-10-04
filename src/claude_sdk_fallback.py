"""Fallback implementation of the Claude Agent SDK for local testing."""

from __future__ import annotations

import itertools
from types import SimpleNamespace
from typing import Optional


class _Agents:
    def __init__(self, default_model: Optional[str] = None) -> None:
        self._ids = itertools.count(1)
        self._default_model = default_model

    def create(self, **kwargs):
        payload = dict(kwargs)
        payload.setdefault("default_model", self._default_model)
        return SimpleNamespace(id=f"agent-{next(self._ids)}", **payload)


class _Sessions:
    def __init__(self) -> None:
        self._ids = itertools.count(1)
        self._store = {}

    def create(self, agent_id: str, **kwargs):
        session_id = f"session-{next(self._ids)}"
        session = {"id": session_id, "agent_id": agent_id, "history": []}
        self._store[session_id] = session
        return SimpleNamespace(**session)

    def send_message(self, session_id: str, content: str, **kwargs):
        session = self._store[session_id]
        session["history"].append({"role": "user", "content": content})
        text = f"Echo: {content}"
        session["history"].append({"role": "assistant", "content": text})
        return SimpleNamespace(
            id=f"message-{len(session['history'])}",
            output_text=text,
            content=[SimpleNamespace(type="text", text=text)],
        )


class ClaudeSDKClient:
    """Minimal stub with the public API we rely on."""

    def __init__(self, **kwargs) -> None:
        self.default_model = kwargs.get("default_model")
        self.base_url = kwargs.get("base_url")
        self.extra_headers = kwargs.get("extra_headers", {})
        self.agents = _Agents(self.default_model)
        self.sessions = _Sessions()

    def create_agent(self, **kwargs):
        """Compatibility helper matching anticipated SDK surface."""

        return self.agents.create(**kwargs)

    def create_session(self, **kwargs):
        agent_id = kwargs.get("agent_id")
        return self.sessions.create(agent_id=agent_id)

    def send_message(self, **kwargs):
        return self.sessions.send_message(**kwargs)

    def close(self) -> None:  # pragma: no cover - provided for API parity
        return None


__all__ = ["ClaudeSDKClient"]

