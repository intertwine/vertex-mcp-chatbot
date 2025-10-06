"""Tests for the ClaudeAgentClient wrapper."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.claude_agent_client import ClaudeAgentClient


class TestClaudeAgentClient:
    """Unit tests covering core client behaviour with Anthropic SDK."""

    def test_send_message_basic_flow(self):
        """Test basic message sending without tools."""
        response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Hello there!")],
            stop_reason="end_turn",
        )

        sdk_client = MagicMock(spec=["messages"])
        sdk_client.messages.create.return_value = response

        client = ClaudeAgentClient(sdk_client=sdk_client, model_name="claude-test")
        text = client.send_message("Hi")

        assert text == "Hello there!"
        assert len(client.history) == 2
        assert client.history[0] == {"role": "user", "content": "Hi"}
        assert client.history[1]["role"] == "assistant"

    def test_send_message_with_system_prompt(self):
        """Test that system prompt is passed to API."""
        response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Response")],
            stop_reason="end_turn",
        )

        sdk_client = MagicMock(spec=["messages"])
        sdk_client.messages.create.return_value = response

        client = ClaudeAgentClient(
            sdk_client=sdk_client,
            system_prompt="Be helpful",
        )
        client.send_message("Hi")

        # Verify system prompt was passed
        call_kwargs = sdk_client.messages.create.call_args[1]
        assert call_kwargs["system"] == "Be helpful"

    def test_get_mcp_tools_without_manager(self):
        """Test that no tools are returned when no MCP manager."""
        sdk_client = MagicMock()
        client = ClaudeAgentClient(sdk_client=sdk_client)

        tools = client._get_mcp_tools()
        assert tools == []

    def test_get_mcp_tools_with_manager(self):
        """Test MCP tools are converted to Anthropic format."""
        mcp_tools = [
            {
                "name": "list_files",
                "description": "List files in directory",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            }
        ]

        mcp_manager = MagicMock()
        mcp_manager.get_tools_sync.return_value = mcp_tools

        sdk_client = MagicMock()
        client = ClaudeAgentClient(sdk_client=sdk_client, mcp_manager=mcp_manager)

        tools = client._get_mcp_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "list_files"
        assert tools[0]["description"] == "List files in directory"
        assert "input_schema" in tools[0]

    def test_tool_calling_flow(self):
        """Test complete tool calling flow."""
        # First response: Claude wants to use a tool
        tool_use_response = SimpleNamespace(
            content=[
                SimpleNamespace(type="text", text="Let me check that"),
                SimpleNamespace(
                    type="tool_use",
                    name="list_files",
                    input={"directory": "."},
                    id="tool_123",
                ),
            ],
            stop_reason="tool_use",
        )

        # Second response: Claude responds with tool results
        final_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Here are the files...")],
            stop_reason="end_turn",
        )

        sdk_client = MagicMock(spec=["messages"])
        sdk_client.messages.create.side_effect = [tool_use_response, final_response]

        # Mock MCP manager
        mcp_manager = MagicMock()
        mcp_manager.get_tools_sync.return_value = [
            {"name": "list_files", "description": "List files"}
        ]
        mcp_manager.find_best_server_for_tool_sync.return_value = "filesystem"
        mcp_manager.call_tool_sync.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="file1.txt\nfile2.txt")]
        )

        client = ClaudeAgentClient(sdk_client=sdk_client, mcp_manager=mcp_manager)
        text = client.send_message("List files")

        # Verify tool was called
        mcp_manager.call_tool_sync.assert_called_once_with(
            server_name="filesystem",
            tool_name="list_files",
            arguments={"directory": "."},
        )

        # Verify we got the final response
        assert text == "Here are the files..."

    def test_tool_calling_error_handling(self):
        """Test that tool errors are handled gracefully."""
        tool_use_response = SimpleNamespace(
            content=[
                SimpleNamespace(
                    type="tool_use",
                    name="broken_tool",
                    input={},
                    id="tool_456",
                ),
            ],
            stop_reason="tool_use",
        )

        final_response = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Tool failed")],
            stop_reason="end_turn",
        )

        sdk_client = MagicMock(spec=["messages"])
        sdk_client.messages.create.side_effect = [tool_use_response, final_response]

        mcp_manager = MagicMock()
        mcp_manager.get_tools_sync.return_value = [
            {"name": "broken_tool", "description": "Broken"}
        ]
        mcp_manager.find_best_server_for_tool_sync.return_value = "server"
        mcp_manager.call_tool_sync.side_effect = Exception("Tool execution failed")

        client = ClaudeAgentClient(sdk_client=sdk_client, mcp_manager=mcp_manager)
        text = client.send_message("Use broken tool")

        # Should still return a response even though tool failed
        assert text == "Tool failed"

    def test_reset_session_clears_history(self):
        """Test that reset_session clears conversation history."""
        sdk_client = MagicMock()
        client = ClaudeAgentClient(sdk_client=sdk_client)

        client.history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
        ]

        client.reset_session()

        assert len(client.history) == 0

    def test_fallback_stub_is_used_when_no_sdk(self):
        """Test that fallback stub works when Anthropic SDK not available."""
        # Create a mock that looks like the fallback stub
        fallback_client = MagicMock()
        fallback_client.sessions.send_message.return_value = SimpleNamespace(
            output_text="Echo: test"
        )

        client = ClaudeAgentClient(sdk_client=fallback_client)
        text = client.send_message("test")

        assert text == "Echo: test"
        fallback_client.sessions.send_message.assert_called_once()

    @patch("src.claude_agent_client.Config.get_claude_sdk_init_kwargs")
    @patch("src.claude_agent_client._resolve_sdk_client_class")
    def test_sdk_initialization_with_config(self, mock_resolver, mock_config):
        """Test SDK client initialization uses config."""
        mock_config.return_value = {
            "api_key": "test-key",
            "base_url": "https://test.com",
            "default_model": "claude-test",
        }
        mock_sdk_class = MagicMock()
        mock_resolver.return_value = mock_sdk_class

        client = ClaudeAgentClient(model_name="claude-test")

        mock_config.assert_called_once_with("claude-test")
        # Verify default_model is removed before passing to Anthropic SDK
        call_kwargs = mock_sdk_class.call_args[1]
        assert "default_model" not in call_kwargs

    def test_multiple_tool_calls_in_sequence(self):
        """Test handling multiple sequential tool calls."""
        # Response 1: First tool use
        response1 = SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", name="tool1", input={}, id="t1")],
            stop_reason="tool_use",
        )

        # Response 2: Second tool use
        response2 = SimpleNamespace(
            content=[SimpleNamespace(type="tool_use", name="tool2", input={}, id="t2")],
            stop_reason="tool_use",
        )

        # Response 3: Final answer
        response3 = SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Done!")],
            stop_reason="end_turn",
        )

        sdk_client = MagicMock(spec=["messages"])
        sdk_client.messages.create.side_effect = [response1, response2, response3]

        mcp_manager = MagicMock()
        mcp_manager.get_tools_sync.return_value = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"},
        ]
        mcp_manager.find_best_server_for_tool_sync.return_value = "server"
        mcp_manager.call_tool_sync.return_value = SimpleNamespace(
            content=[SimpleNamespace(text="result")]
        )

        client = ClaudeAgentClient(sdk_client=sdk_client, mcp_manager=mcp_manager)
        text = client.send_message("Do task")

        # Should have called both tools
        assert mcp_manager.call_tool_sync.call_count == 2
        assert text == "Done!"
