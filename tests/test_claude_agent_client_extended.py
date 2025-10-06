"""Extended tests for ClaudeAgentClient to improve coverage."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.claude_agent_client import ClaudeAgentClient, _resolve_sdk_client_class


class TestClaudeAgentClientExtended:
    """Extended tests for ClaudeAgentClient coverage."""

    def test_resolve_sdk_client_class_success(self):
        """Test resolving Anthropic SDK client class."""
        with patch("importlib.import_module") as mock_import:
            mock_module = Mock()
            mock_module.Anthropic = Mock
            mock_import.return_value = mock_module

            client_class = _resolve_sdk_client_class()
            assert client_class == Mock

    def test_resolve_sdk_client_class_fallback(self):
        """Test fallback to stub when Anthropic SDK not available."""
        with patch("importlib.import_module", side_effect=ImportError()):
            client_class = _resolve_sdk_client_class()
            # Should return ClaudeSDKClient from fallback
            assert client_class.__name__ == "ClaudeSDKClient"

    def test_resolve_sdk_client_class_attribute_error(self):
        """Test fallback when Anthropic attribute missing."""
        with patch("importlib.import_module") as mock_import:
            mock_module = Mock(spec=[])  # No Anthropic attribute
            mock_import.return_value = mock_module

            with patch("importlib.import_module", side_effect=AttributeError()):
                client_class = _resolve_sdk_client_class()
                assert client_class.__name__ == "ClaudeSDKClient"

    def test_create_sdk_client_with_type_error_fallback(self):
        """Test SDK client creation falls back on TypeError."""
        mock_sdk_class = Mock()
        mock_sdk_class.side_effect = [TypeError("Invalid kwargs"), Mock()]

        with patch(
            "src.claude_agent_client._resolve_sdk_client_class", return_value=mock_sdk_class
        ):
            with patch("src.config.Config.get_claude_sdk_init_kwargs") as mock_kwargs:
                mock_kwargs.return_value = {
                    "api_key": "test-key",
                    "base_url": "https://api.test.com",
                    "default_headers": {"Authorization": "Bearer test"},
                    "extra_param": "should_be_removed",
                }

                client = ClaudeAgentClient()

                # Should call twice - first with all kwargs, then with minimal
                assert mock_sdk_class.call_count == 2

    def test_create_sdk_client_with_extra_headers(self):
        """Test SDK client creation with extra_headers instead of default_headers."""
        mock_sdk_class = Mock()

        # First call raises TypeError, second should work
        mock_sdk_class.side_effect = [
            TypeError("Invalid kwargs"),
            Mock()  # Success on second call
        ]

        with patch(
            "src.claude_agent_client._resolve_sdk_client_class", return_value=mock_sdk_class
        ):
            with patch("src.config.Config.get_claude_sdk_init_kwargs") as mock_kwargs:
                mock_kwargs.return_value = {
                    "api_key": "test-key",
                    "extra_headers": {"Custom": "Header"},
                }

                client = ClaudeAgentClient()

                # Verify second call used default_headers converted from extra_headers
                second_call_kwargs = mock_sdk_class.call_args_list[1][1]
                assert "default_headers" in second_call_kwargs
                assert second_call_kwargs["default_headers"]["Custom"] == "Header"

    def test_ensure_session_updates_prompt(self):
        """Test ensure_session updates system prompt when changed."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="original")

        client.ensure_session("updated prompt")
        assert client.system_prompt == "updated prompt"

    def test_ensure_session_no_update_when_same(self):
        """Test ensure_session doesn't update when prompt is same."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="same")

        client.ensure_session("same")
        assert client.system_prompt == "same"

    def test_ensure_session_no_update_when_none(self):
        """Test ensure_session doesn't update when instruction is None."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="original")

        client.ensure_session(None)
        assert client.system_prompt == "original"

    def test_chat_with_tools_api_error(self):
        """Test _chat_with_tools handles API errors."""
        mock_sdk = Mock()
        mock_sdk.messages.create.side_effect = Exception("API Error")

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        client.history.append({"role": "user", "content": "test"})

        with pytest.raises(Exception, match="API Error"):
            client._chat_with_tools()

    def test_chat_with_tools_max_turns(self):
        """Test _chat_with_tools stops after max turns."""
        mock_sdk = Mock()
        mock_response = Mock()
        mock_response.stop_reason = "tool_use"
        mock_response.content = []  # No tool use blocks
        mock_sdk.messages.create.return_value = mock_response

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        client.history.append({"role": "user", "content": "test"})

        with patch.object(
            client, "_handle_tool_use", return_value=None
        ):
            with patch.object(
                client, "_extract_text_from_message", return_value="response"
            ) as mock_extract:
                result = client._chat_with_tools()

                # Should eventually call extract_text_from_message
                mock_extract.assert_called()

    def test_get_mcp_tools_no_manager(self):
        """Test _get_mcp_tools returns empty list when no manager."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)

        tools = client._get_mcp_tools()
        assert tools == []

    def test_get_mcp_tools_with_error(self):
        """Test _get_mcp_tools handles errors gracefully."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_manager.get_tools_sync.side_effect = Exception("Tool fetch error")

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        tools = client._get_mcp_tools()
        assert tools == []

    def test_get_mcp_tools_without_input_schema(self):
        """Test _get_mcp_tools handles tools without inputSchema."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_manager.get_tools_sync.return_value = [
            {
                "name": "simple_tool",
                "description": "A simple tool",
                # No inputSchema
            }
        ]

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        tools = client._get_mcp_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "simple_tool"
        assert "input_schema" not in tools[0]

    def test_handle_tool_use_no_manager(self):
        """Test _handle_tool_use returns None when no manager."""
        mock_sdk = Mock()
        mock_response = Mock()

        client = ClaudeAgentClient(sdk_client=mock_sdk)

        result = client._handle_tool_use(mock_response)
        assert result is None

    def test_handle_tool_use_server_not_found(self):
        """Test _handle_tool_use handles server not found error."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_manager.find_best_server_for_tool_sync.return_value = None

        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "unknown_tool"
        mock_block.input = {}
        mock_block.id = "tool-123"

        mock_response = Mock()
        mock_response.content = [mock_block]

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        result = client._handle_tool_use(mock_response)

        assert len(result) == 1
        assert result[0]["type"] == "tool_result"
        assert result[0]["is_error"] is True
        assert "No server found" in result[0]["content"]

    def test_handle_tool_use_tool_execution_error(self):
        """Test _handle_tool_use handles tool execution errors."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_manager.find_best_server_for_tool_sync.return_value = "test-server"
        mock_manager.call_tool_sync.side_effect = Exception("Execution failed")

        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "failing_tool"
        mock_block.input = {"arg": "value"}
        mock_block.id = "tool-456"

        mock_response = Mock()
        mock_response.content = [mock_block]

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        result = client._handle_tool_use(mock_response)

        assert len(result) == 1
        assert result[0]["type"] == "tool_result"
        assert result[0]["is_error"] is True
        assert "Execution failed" in result[0]["content"]

    def test_handle_tool_use_result_without_content_attr(self):
        """Test _handle_tool_use handles result without content attribute."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_manager.find_best_server_for_tool_sync.return_value = "test-server"
        # Result is just a dict, no content attribute
        mock_manager.call_tool_sync.return_value = {"result": "success"}

        mock_block = Mock()
        mock_block.type = "tool_use"
        mock_block.name = "dict_tool"
        mock_block.input = {}
        mock_block.id = "tool-789"

        mock_response = Mock()
        mock_response.content = [mock_block]

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        result = client._handle_tool_use(mock_response)

        assert len(result) == 1
        assert result[0]["type"] == "tool_result"
        assert "result" in result[0]["content"]

    def test_handle_tool_use_no_tool_blocks(self):
        """Test _handle_tool_use with no tool_use blocks."""
        mock_sdk = Mock()
        mock_manager = Mock()

        mock_block = Mock()
        mock_block.type = "text"  # Not tool_use

        mock_response = Mock()
        mock_response.content = [mock_block]

        client = ClaudeAgentClient(sdk_client=mock_sdk, mcp_manager=mock_manager)

        result = client._handle_tool_use(mock_response)
        assert result is None  # No tool results

    def test_extract_text_from_message_dict_content(self):
        """Test _extract_text_from_message with dict content."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)

        mock_response = Mock()
        mock_response.content = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
            {"type": "other", "data": "ignored"},
        ]

        text = client._extract_text_from_message(mock_response)
        assert text == "Hello\nWorld"

    def test_extract_text_from_message_object_content(self):
        """Test _extract_text_from_message with object content."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)

        mock_block1 = Mock()
        mock_block1.type = "text"
        mock_block1.text = "First"

        mock_block2 = Mock()
        mock_block2.type = "text"
        mock_block2.text = "Second"

        mock_response = Mock()
        mock_response.content = [mock_block1, mock_block2]

        text = client._extract_text_from_message(mock_response)
        assert text == "First\nSecond"

    def test_extract_text_from_message_no_text_blocks(self):
        """Test _extract_text_from_message with no text blocks."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)

        mock_response = Mock()
        mock_response.content = [{"type": "image", "data": "..."}]

        text = client._extract_text_from_message(mock_response)
        # Should fall back to str(response)
        assert "Mock" in text or "object" in text

    def test_extract_text_from_message_non_list_content(self):
        """Test _extract_text_from_message with non-list content."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)

        mock_response = Mock()
        mock_response.content = "Just a string"

        text = client._extract_text_from_message(mock_response)
        # Should use str(response) not str(content)
        assert "Mock" in text or "object" in text

    def test_reset_session_with_new_prompt(self):
        """Test reset_session updates prompt and clears history."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="old")
        client.history = [{"role": "user", "content": "test"}]

        client.reset_session("new prompt")

        assert client.system_prompt == "new prompt"
        assert len(client.history) == 0

    def test_reset_session_keeps_old_prompt(self):
        """Test reset_session keeps old prompt if None provided."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="original")
        client.history = [{"role": "user", "content": "test"}]

        client.reset_session(None)

        assert client.system_prompt == "original"
        assert len(client.history) == 0

    def test_get_chat_history(self):
        """Test get_chat_history returns copy of history."""
        mock_sdk = Mock()
        client = ClaudeAgentClient(sdk_client=mock_sdk)
        client.history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        history = client.get_chat_history()

        assert history == client.history
        assert history is not client.history  # Should be a copy

    def test_close_with_close_method(self):
        """Test close calls SDK client's close method."""
        mock_sdk = Mock()
        mock_sdk.close = Mock()

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        client.close()

        mock_sdk.close.assert_called_once()

    def test_close_without_close_method(self):
        """Test close handles SDK client without close method."""
        mock_sdk = Mock(spec=[])  # No close method

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        # Should not raise
        client.close()

    def test_send_message_with_fallback(self):
        """Test send_message uses fallback when sessions attribute exists."""
        mock_sdk = Mock()
        mock_sdk.sessions = Mock()
        mock_sdk.sessions.send_message = Mock(return_value=Mock(output_text="Fallback response"))

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        response = client.send_message("Hello")

        assert response == "Fallback response"
        mock_sdk.sessions.send_message.assert_called_once()

    def test_send_with_fallback_no_output_text(self):
        """Test _send_with_fallback handles response without output_text."""
        mock_sdk = Mock()
        mock_response = Mock(spec=[])  # No output_text attribute
        # Mock the str() representation
        mock_response.__class__.__str__ = lambda self: "String response"
        mock_sdk.sessions.send_message.return_value = mock_response

        client = ClaudeAgentClient(sdk_client=mock_sdk)
        client._send_with_fallback("test")

        # Should add string representation to history
        assert client.history[-1]["role"] == "assistant"

    def test_chat_with_tools_with_system_prompt(self):
        """Test _chat_with_tools includes system prompt in params."""
        mock_sdk = Mock()
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(type="text", text="Response")]
        mock_sdk.messages.create.return_value = mock_response

        client = ClaudeAgentClient(sdk_client=mock_sdk, system_prompt="You are helpful")
        client.history.append({"role": "user", "content": "Hello"})

        with patch.object(client, "_extract_text_from_message", return_value="Response"):
            client._chat_with_tools()

            # Verify system prompt was included
            call_kwargs = mock_sdk.messages.create.call_args[1]
            assert call_kwargs["system"] == "You are helpful"

    def test_chat_with_tools_with_mcp_tools(self):
        """Test _chat_with_tools includes MCP tools when available."""
        mock_sdk = Mock()
        mock_manager = Mock()
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(type="text", text="Response")]
        mock_sdk.messages.create.return_value = mock_response

        client = ClaudeAgentClient(
            sdk_client=mock_sdk,
            mcp_manager=mock_manager
        )
        client.history.append({"role": "user", "content": "Hello"})

        with patch.object(
            client, "_get_mcp_tools", return_value=[{"name": "test_tool"}]
        ):
            with patch.object(client, "_extract_text_from_message", return_value="Response"):
                client._chat_with_tools()

                # Verify tools were included
                call_kwargs = mock_sdk.messages.create.call_args[1]
                assert "tools" in call_kwargs
                assert call_kwargs["tools"][0]["name"] == "test_tool"
