"""Tests for MCP resource handling in chatbot."""

from unittest.mock import Mock, patch

import pytest

from src.chatbot import GeminiChatbot


class TestMCPResources:
    """Test MCP resource integration."""

    @patch("src.chatbot.os.makedirs")
    def test_mcp_resources_command(self, mock_makedirs):
        """Test /mcp resources command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[
                {"name": "docs-server", "connected": True},
                {"name": "github-server", "connected": True},
            ]
        )
        chatbot.mcp_manager.get_resources_sync = Mock(
            return_value=[
                {
                    "uri": "file:///docs/api.md",
                    "name": "API Documentation",
                    "description": "REST API documentation",
                    "mimeType": "text/markdown",
                    "server": "docs-server",
                },
                {
                    "uri": "github:myrepo/README.md",
                    "name": "Project README",
                    "description": "Main project documentation",
                    "server": "github-server",
                },
            ]
        )
        chatbot.mcp_manager.get_resource_templates_sync = Mock(return_value=[])

        with patch.object(chatbot, "display_content") as mock_display:
            result = chatbot.process_command("/mcp resources")

            assert result is True
            # Should call display_content once
            mock_display.assert_called_once()
            content = mock_display.call_args[0][0]
            # Verify resource details are in the content
            assert "API Documentation" in content
            assert "file:///docs/api.md" in content

    @patch("src.chatbot.os.makedirs")
    def test_mcp_resources_no_servers(self, mock_makedirs):
        """Test /mcp resources when no servers connected."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(return_value=[])

        result = chatbot.process_command("/mcp resources")

        assert result is True
        chatbot.console.print.assert_called_with("[dim]No MCP servers connected[/dim]")

    @patch("src.chatbot.os.makedirs")
    def test_mcp_resources_no_resources(self, mock_makedirs):
        """Test /mcp resources when servers have no resources."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[{"name": "test-server", "connected": True}]
        )
        chatbot.mcp_manager.get_resources_sync = Mock(return_value=[])
        chatbot.mcp_manager.get_resource_templates_sync = Mock(return_value=[])

        result = chatbot.process_command("/mcp resources")

        assert result is True
        chatbot.console.print.assert_called_with(
            "[dim]No resources available from connected servers[/dim]"
        )

    @patch("src.chatbot.os.makedirs")
    def test_format_resources_context(self, mock_makedirs):
        """Test formatting resources for Gemini context."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[{"name": "test-server", "connected": True}]
        )
        chatbot.mcp_manager.get_resources_sync = Mock(
            return_value=[
                {
                    "uri": "file:///data/config.json",
                    "name": "Configuration",
                    "description": "App configuration file",
                    "mimeType": "application/json",
                    "server": "test-server",
                }
            ]
        )

        context = chatbot._format_mcp_resources_context()

        assert "Available MCP Resources:" in context
        assert "Configuration" in context
        assert "file:///data/config.json" in context
        assert "App configuration file" in context

    @patch("src.chatbot.os.makedirs")
    def test_detect_resource_reference(self, mock_makedirs):
        """Test detecting resource references in user messages."""
        chatbot = GeminiChatbot()

        # Test various patterns
        assert chatbot._detect_resource_reference(
            "Can you analyze the file:///docs/api.md?"
        ) == ["file:///docs/api.md"]

        assert chatbot._detect_resource_reference(
            "Please check github:myrepo/README.md for details"
        ) == ["github:myrepo/README.md"]

        assert chatbot._detect_resource_reference(
            "Compare file:///a.txt with file:///b.txt"
        ) == ["file:///a.txt", "file:///b.txt"]

        assert chatbot._detect_resource_reference("This is a normal message") == []

    @pytest.mark.filterwarnings("ignore:coroutine.*was never awaited:RuntimeWarning")
    @patch("src.chatbot.os.makedirs")
    def test_read_mcp_resource(self, mock_makedirs):
        """Test reading an MCP resource."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.read_resource_sync = Mock(
            return_value={
                "contents": [
                    {
                        "uri": "file:///docs/api.md",
                        "mimeType": "text/markdown",
                        "text": "# API Documentation\n\nGET /users - List all users",
                    }
                ]
            }
        )

        content = chatbot._read_mcp_resource("docs-server", "file:///docs/api.md")

        assert content == "# API Documentation\n\nGET /users - List all users"
        chatbot.mcp_manager.read_resource_sync.assert_called_once_with(
            "docs-server", "file:///docs/api.md"
        )

    @patch("src.chatbot.os.makedirs")
    def test_read_mcp_resource_binary(self, mock_makedirs):
        """Test reading a binary MCP resource."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.read_resource_sync = Mock(
            return_value={
                "contents": [
                    {
                        "uri": "file:///image.png",
                        "mimeType": "image/png",
                        "blob": "base64encodeddata",
                    }
                ]
            }
        )

        content = chatbot._read_mcp_resource("server", "file:///image.png")

        assert content == "[Binary content: image/png]"

    @patch("src.chatbot.os.makedirs")
    def test_find_resource_server(self, mock_makedirs):
        """Test finding which server provides a resource."""
        chatbot = GeminiChatbot()
        chatbot.mcp_manager = Mock()
        chatbot.mcp_manager.get_resources_sync = Mock(
            return_value=[
                {"uri": "file:///a.txt", "server": "server1"},
                {"uri": "file:///b.txt", "server": "server2"},
            ]
        )

        assert chatbot._find_resource_server("file:///a.txt") == "server1"
        assert chatbot._find_resource_server("file:///b.txt") == "server2"
        assert chatbot._find_resource_server("file:///c.txt") is None

    @patch("src.chatbot.os.makedirs")
    def test_process_message_with_resource(self, mock_makedirs):
        """Test processing a message that references a resource."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        # Mock status context manager
        status_mock = Mock()
        status_mock.__enter__ = Mock(return_value=status_mock)
        status_mock.__exit__ = Mock(return_value=None)
        chatbot.console.status = Mock(return_value=status_mock)

        chatbot.client = Mock()
        chatbot.mcp_manager = Mock()
        chatbot.display_response = Mock()

        # Mock resource availability
        chatbot.mcp_manager.list_servers = Mock(
            return_value=[{"name": "docs-server", "connected": True}]
        )
        chatbot.mcp_manager.get_resources_sync = Mock(
            return_value=[
                {
                    "uri": "file:///docs/api.md",
                    "name": "API Documentation",
                    "server": "docs-server",
                }
            ]
        )
        chatbot.mcp_manager.read_resource_sync = Mock(
            return_value={
                "contents": [
                    {
                        "uri": "file:///docs/api.md",
                        "mimeType": "text/markdown",
                        "text": "# API Documentation\n\nGET /users",
                    }
                ]
            }
        )

        # Mock Gemini response
        chatbot.client.send_message = Mock(
            return_value="Based on the API documentation, the /users endpoint returns a list of users."
        )

        # Process message with resource reference
        chatbot._process_chat_message("What does file:///docs/api.md say about users?")

        # Verify resource was read
        chatbot.mcp_manager.read_resource_sync.assert_called_once_with(
            "docs-server", "file:///docs/api.md"
        )

        # Verify resource content was included in prompt
        first_call = chatbot.client.send_message.call_args_list[0]
        assert "# API Documentation" in first_call[0][0]
        assert "What does file:///docs/api.md say about users?" in first_call[0][0]
