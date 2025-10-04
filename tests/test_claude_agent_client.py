"""Tests for the ClaudeAgentClient wrapper."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.claude_agent_client import ClaudeAgentClient


class TestClaudeAgentClient:
    """Unit tests covering core client behaviour."""

    def test_ensure_session_creates_agent_and_session(self):
        agent = SimpleNamespace(id="agent-123")
        session = SimpleNamespace(id="session-456")
        sdk_client = MagicMock()
        sdk_client.agents.create.return_value = agent
        sdk_client.sessions.create.return_value = session

        client = ClaudeAgentClient(sdk_client=sdk_client, model_name="claude-test")
        client.ensure_session("be helpful")

        sdk_client.agents.create.assert_called_once()
        sdk_client.sessions.create.assert_called_once_with(agent_id="agent-123")
        assert client.agent is agent
        assert client.session is session

    def test_send_message_records_history(self):
        agent = SimpleNamespace(id="agent-1")
        session = SimpleNamespace(id="session-1")
        response = SimpleNamespace(
            output_text="Hello there!",
            content=[SimpleNamespace(type="text", text="Hello there!")],
        )

        sdk_client = MagicMock()
        sdk_client.agents.create.return_value = agent
        sdk_client.sessions.create.return_value = session
        sdk_client.sessions.send_message.return_value = response

        client = ClaudeAgentClient(sdk_client=sdk_client)
        text = client.send_message("Hi")

        assert text == "Hello there!"
        assert client.history[-2:] == [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello there!"},
        ]

    def test_reset_session_recreates_agent(self):
        sdk_client = MagicMock()
        sdk_client.agents.create.side_effect = [
            SimpleNamespace(id="agent-old"),
            SimpleNamespace(id="agent-new"),
        ]
        sdk_client.sessions.create.side_effect = [
            SimpleNamespace(id="session-old"),
            SimpleNamespace(id="session-new"),
        ]

        client = ClaudeAgentClient(sdk_client=sdk_client)
        client.ensure_session("prompt one")
        assert client.agent.id == "agent-old"

        client.reset_session("prompt two")

        assert client.agent.id == "agent-new"
        assert client.session.id == "session-new"

    def test_extract_text_from_dict_response(self):
        sdk_client = MagicMock()
        sdk_client.agents.create.return_value = {"id": "agent"}
        sdk_client.sessions.create.return_value = {"id": "session"}
        sdk_client.sessions.send_message.return_value = {"output_text": "Hi"}

        client = ClaudeAgentClient(sdk_client=sdk_client)
        text = client.send_message("test")
        assert text == "Hi"

    @patch("src.claude_agent_client.Config.get_claude_sdk_init_kwargs", return_value={})
    def test_fallback_client_used_when_sdk_missing(self, mock_config_kwargs):
        with patch("src.claude_agent_client._resolve_sdk_client_class") as resolver:
            resolver.return_value = MagicMock()
            client = ClaudeAgentClient(model_name="test")
            resolver.assert_called_once()
            mock_config_kwargs.assert_called_once_with("test")
            assert client.model_name == "test"

    def test_create_sdk_client_uses_config_kwargs(self):
        sdk_instance = MagicMock()

        with (
            patch(
                "src.claude_agent_client._resolve_sdk_client_class",
                return_value=MagicMock(return_value=sdk_instance),
            ) as resolver,
            patch(
                "src.claude_agent_client.Config.get_claude_sdk_init_kwargs",
                return_value={"default_model": "claude-4.5-sonnet", "api_key": "token"},
            ) as config_kwargs,
        ):
            client = ClaudeAgentClient(model_name=None)
            resolver.assert_called_once()
            config_kwargs.assert_called_once_with("claude-4.5-sonnet")
            assert client._sdk_client is sdk_instance
