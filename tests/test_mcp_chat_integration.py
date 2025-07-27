"""Tests for MCP integration with chat flow."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.chatbot import GeminiChatbot
from src.gemini_client import GeminiClient


class TestMCPChatIntegration:
    """Test MCP tool integration in chat conversations."""

    @patch("src.chatbot.os.makedirs")
    def test_format_tools_for_context(self, mock_makedirs):
        """Test formatting MCP tools for Gemini context."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[
                {
                    "name": "test-server",
                    "connected": True,
                    "transport": "stdio",
                }
            ]
        )
        chatbot.mcp_manager.get_tools_sync = Mock(
            return_value=[
                {
                    "name": "get_weather",
                    "description": "Get current weather for a location",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name",
                            }
                        },
                        "required": ["location"],
                    },
                    "server": "test-server",
                }
            ]
        )

        tools_context = chatbot._format_mcp_tools_context()

        assert "Available MCP Tools:" in tools_context
        assert "get_weather" in tools_context
        assert "Get current weather for a location" in tools_context
        assert "location" in tools_context
        assert "test-server" in tools_context

    @patch("src.chatbot.os.makedirs")
    def test_format_tools_no_mcp(self, mock_makedirs):
        """Test formatting tools when MCP is not available."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = None

        tools_context = chatbot._format_mcp_tools_context()

        assert tools_context == ""

    @patch("src.chatbot.os.makedirs")
    def test_format_tools_no_connected_servers(self, mock_makedirs):
        """Test formatting tools when no servers are connected."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(return_value=[])

        tools_context = chatbot._format_mcp_tools_context()

        assert tools_context == ""

    @patch("src.chatbot.os.makedirs")
    def test_detect_tool_request_in_response(self, mock_makedirs):
        """Test detecting tool requests in Gemini responses."""
        chatbot = GeminiChatbot()

        # Test various response patterns
        assert chatbot._detect_tool_request(
            "I'll check the weather for you. Let me use the get_weather tool for New York."
        ) == ("get_weather", {"location": "New York"})

        assert chatbot._detect_tool_request(
            "I need to use the calculate_sum tool with values 5 and 10."
        ) == ("calculate_sum", {"values": [5, 10]})

        assert chatbot._detect_tool_request(
            "This is a normal response without tool calls."
        ) == (None, None)

    @patch("src.chatbot.os.makedirs")
    def test_execute_mcp_tool(self, mock_makedirs):
        """Test executing an MCP tool and getting results."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.call_tool_sync = Mock(
            return_value={
                "content": [
                    {
                        "type": "text",
                        "text": "Weather in New York: 72°F, sunny",
                    }
                ]
            }
        )

        result = chatbot._execute_mcp_tool(
            "test-server", "get_weather", {"location": "New York"}
        )

        assert result == "Weather in New York: 72°F, sunny"
        chatbot.mcp_manager.call_tool_sync.assert_called_once_with(
            "test-server", "get_weather", {"location": "New York"}
        )

    @patch("src.chatbot.os.makedirs")
    def test_execute_mcp_tool_error(self, mock_makedirs):
        """Test handling errors during tool execution."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.call_tool_sync = Mock(
            side_effect=Exception("Tool execution failed")
        )

        result = chatbot._execute_mcp_tool(
            "test-server", "get_weather", {"location": "New York"}
        )

        assert "Error executing tool" in result
        assert "Tool execution failed" in result

    @patch("src.chatbot.os.makedirs")
    def test_process_message_with_tool_call(self, mock_makedirs):
        """Test processing a message that triggers a tool call."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        # Mock the status context manager
        status_mock = Mock()
        status_mock.__enter__ = Mock(return_value=status_mock)
        status_mock.__exit__ = Mock(return_value=None)
        chatbot.console.status = Mock(return_value=status_mock)

        chatbot.client = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.display_response = Mock()

        # Mock MCP manager methods
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[
                {
                    "name": "test-server",
                    "connected": True,
                    "transport": "stdio",
                }
            ]
        )
        chatbot.mcp_manager.get_tools_sync = Mock(
            return_value=[
                {
                    "name": "get_weather",
                    "description": "Get weather",
                    "server": "test-server",
                }
            ]
        )

        # Mock the Gemini response that requests a tool
        chatbot.client.send_message = Mock(
            return_value="I'll check the weather for you. Let me use the get_weather tool for New York."
        )

        # Mock tool execution
        chatbot.mcp_manager.call_tool_sync = Mock(
            return_value={
                "content": [
                    {
                        "type": "text",
                        "text": "Weather in New York: 72°F, sunny",
                    }
                ]
            }
        )

        # Process message
        chatbot._process_chat_message("What's the weather in New York?")

        # Verify tool was executed
        chatbot.mcp_manager.call_tool_sync.assert_called_once_with(
            "test-server", "get_weather", {"location": "New York"}
        )

        # Verify follow-up message was sent with tool result
        assert chatbot.client.send_message.call_count == 2
        second_call_args = chatbot.client.send_message.call_args_list[1][0][0]
        assert "Weather in New York: 72°F, sunny" in second_call_args

    @patch("src.chatbot.os.makedirs")
    def test_find_tool_server(self, mock_makedirs):
        """Test finding which server provides a specific tool."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.get_tools_sync = Mock(
            return_value=[
                {"name": "get_weather", "server": "weather-server"},
                {"name": "calculate", "server": "math-server"},
            ]
        )

        assert chatbot._find_tool_server("get_weather") == "weather-server"
        assert chatbot._find_tool_server("calculate") == "math-server"
        assert chatbot._find_tool_server("unknown_tool") is None
