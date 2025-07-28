"""Tests for scrollable output functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from rich.console import Console

from src.chatbot import GeminiChatbot


class TestScrollableOutput:
    """Test scrollable output for various content types."""

    @pytest.fixture
    def chatbot(self):
        """Create a test chatbot instance."""
        with patch("src.chatbot.GeminiClient"):
            bot = GeminiChatbot()
            bot.console = Mock(spec=Console)
            bot.console.size = Mock(width=80, height=24)
            bot.client = Mock()  # Mock the client
            return bot

    def test_display_content_short(self, chatbot):
        """Test that short content displays normally without scrolling."""
        # Short content that fits in terminal
        content = (
            "This is a short message\nWith just a few lines\nThat fits in the terminal"
        )

        with patch.object(chatbot, "_display_scrollable_content") as mock_scroll:
            chatbot.display_content(content, "Test Title")

            # Should not use scrollable display
            mock_scroll.assert_not_called()
            # Should print normally
            chatbot.console.print.assert_called()

    def test_display_content_long(self, chatbot):
        """Test that long content uses scrollable display."""
        # Create content longer than terminal height
        long_content = "\n".join([f"Line {i}" for i in range(50)])

        with patch.object(chatbot, "_display_scrollable_content") as mock_scroll:
            chatbot.display_content(long_content, "Test Title")

            # Should use scrollable display
            mock_scroll.assert_called_once()
            assert "Test Title" in mock_scroll.call_args[0][1]

    def test_mcp_list_tools_scrollable(self, chatbot):
        """Test that long tool listings become scrollable."""
        # Mock MCP manager with many tools
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True, "transport": "stdio"}
        ]

        # Create many tools to exceed terminal height
        tools = []
        for i in range(30):
            tools.append(
                {
                    "name": f"tool_{i}",
                    "server": "server1",
                    "description": f"This is a description for tool {i} that is somewhat long to simulate real tool descriptions",
                }
            )

        chatbot.mcp_manager.get_tools_sync.return_value = tools

        with patch.object(chatbot, "display_content") as mock_display:
            chatbot.mcp_list_tools()

            # Should call display_content with the formatted tool list
            mock_display.assert_called_once()
            content = mock_display.call_args[0][0]
            title = mock_display.call_args[0][1]

            assert "MCP Tools" in title
            assert "tool_0" in content
            assert "tool_29" in content

    def test_mcp_list_resources_scrollable(self, chatbot):
        """Test that long resource listings become scrollable."""
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True, "transport": "stdio"}
        ]

        # Create many resources
        resources = []
        for i in range(25):
            resources.append(
                {
                    "server": "server1",
                    "uri": f"file:///path/to/resource_{i}.txt",
                    "mimeType": "text/plain",
                    "description": f"Resource {i} description",
                }
            )

        chatbot.mcp_manager.get_resources_sync.return_value = resources
        chatbot.mcp_manager.get_resource_templates_sync.return_value = []

        with patch.object(chatbot, "display_content") as mock_display:
            chatbot.mcp_list_resources()

            mock_display.assert_called_once()
            content = mock_display.call_args[0][0]
            title = mock_display.call_args[0][1]

            assert "MCP Resources" in title
            assert "resource_0.txt" in content

    def test_mcp_list_prompts_scrollable(self, chatbot):
        """Test that long prompt listings become scrollable."""
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True, "transport": "stdio"}
        ]

        # Create many prompts
        prompts = []
        for i in range(20):
            prompts.append(
                {
                    "server": "server1",
                    "name": f"prompt_{i}",
                    "description": f"This is prompt {i} for various tasks",
                    "arguments": [
                        {"name": "arg1", "description": "First argument"},
                        {"name": "arg2", "description": "Second argument"},
                    ],
                }
            )

        chatbot.mcp_manager.get_prompts_sync.return_value = prompts

        with patch.object(chatbot, "display_content") as mock_display:
            chatbot.mcp_list_prompts()

            mock_display.assert_called_once()
            content = mock_display.call_args[0][0]
            title = mock_display.call_args[0][1]

            assert "MCP Prompt Templates" in title
            assert "prompt_0" in content
            assert "arg1" in content

    def test_display_content_with_panel(self, chatbot):
        """Test display_content with panel formatting."""
        content = "Test content"

        with patch.object(chatbot, "_display_scrollable_content") as mock_scroll:
            chatbot.display_content(content, "Test Title", use_panel=True)

            # Should handle panel formatting
            chatbot.console.print.assert_called()

    def test_display_content_height_calculation(self, chatbot):
        """Test that content height is calculated correctly."""
        # Mock console for rendering
        temp_console = Mock(spec=Console)
        temp_console.size = Mock(width=80, height=24)
        temp_console.file = StringIO()

        # Write some multi-line content to the StringIO
        test_output = "\n".join(["Line"] * 30)
        temp_console.print = Mock(
            side_effect=lambda x: temp_console.file.write(test_output)
        )
        temp_console.file.getvalue = Mock(return_value=test_output)

        with patch("src.chatbot.Console", return_value=temp_console):
            # Content with known line count
            content = "\n".join(["Line"] * 30)

            with patch.object(chatbot, "_display_scrollable_content") as mock_scroll:
                chatbot.display_content(content, "Test")

                # Should trigger scrollable display for 30 lines on 24-line terminal
                mock_scroll.assert_called_once()

    def test_mcp_tool_with_conflicts_display(self, chatbot):
        """Test display of tools with conflicts from multiple servers."""
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True, "transport": "stdio"},
            {"name": "server2", "connected": True, "transport": "http"},
        ]

        # Tools with same name from different servers
        tools = [
            {"name": "search", "server": "server1", "description": "Search files"},
            {"name": "search", "server": "server2", "description": "Search web"},
            {"name": "unique_tool", "server": "server1", "description": "Unique tool"},
        ]

        chatbot.mcp_manager.get_tools_sync.return_value = tools
        chatbot.mcp_manager.get_server_priorities.return_value = {
            "server1": 1,
            "server2": 2,
        }

        with patch.object(chatbot, "display_content") as mock_display:
            chatbot.mcp_list_tools()

            mock_display.assert_called_once()
            content = mock_display.call_args[0][0]

            # Should show conflict information
            assert "multiple servers" in content
            assert "server1" in content
            assert "server2" in content

    def test_empty_listings_no_scroll(self, chatbot):
        """Test that empty listings don't trigger scrollable display."""
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers.return_value = [
            {"name": "server1", "connected": True, "transport": "stdio"}
        ]
        chatbot.mcp_manager.get_tools_sync.return_value = []

        with patch.object(chatbot, "_display_scrollable_content") as mock_scroll:
            chatbot.mcp_list_tools()

            # Should not use scrollable display for empty content
            mock_scroll.assert_not_called()
            # Should show "no tools" message
            chatbot.console.print.assert_called()

    def test_display_content_error_handling(self, chatbot):
        """Test error handling in display_content."""
        # Test with None content
        chatbot.display_content(None, "Test")
        chatbot.console.print.assert_called()

        # Test with rendering error
        with patch("src.chatbot.Console") as mock_console_class:
            mock_console_class.side_effect = Exception("Render error")

            # Should fall back to simple print
            chatbot.display_content("Content", "Title")
            chatbot.console.print.assert_called()
