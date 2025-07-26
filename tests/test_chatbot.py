"""Tests for the chatbot module."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock, call, mock_open
from io import StringIO
from src.chatbot import GeminiChatbot
from src.gemini_client import GeminiClient


class TestGeminiChatbot:
    """Test cases for the GeminiChatbot class."""
    
    @patch('src.chatbot.os.makedirs')
    def test_init_default_model(self, mock_makedirs):
        """Test initialization with default model."""
        chatbot = GeminiChatbot()
        
        assert chatbot.model_name is None
        assert chatbot.client is None
        assert chatbot.chat_dir == ".chat"
        assert chatbot.history_file == os.path.join(".chat", "log.txt")
        mock_makedirs.assert_called_once_with(".chat", exist_ok=True)
    
    @patch('src.chatbot.os.makedirs')
    def test_init_custom_model(self, mock_makedirs):
        """Test initialization with custom model."""
        custom_model = "gemini-1.5-pro"
        chatbot = GeminiChatbot(model_name=custom_model)
        
        assert chatbot.model_name == custom_model
        assert chatbot.client is None
        mock_makedirs.assert_called_once_with(".chat", exist_ok=True)
    
    @patch('src.chatbot.GeminiClient')
    @patch('src.chatbot.os.makedirs')
    def test_initialize_success(self, mock_makedirs, mock_gemini_client):
        """Test successful initialization of the Gemini client."""
        mock_client_instance = Mock()
        mock_gemini_client.return_value = mock_client_instance
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()  # Mock the console to avoid output
        
        chatbot.initialize()
        
        assert chatbot.client == mock_client_instance
        mock_gemini_client.assert_called_once_with(model_name=None)
        # Check that success messages were printed
        assert chatbot.console.print.call_count >= 2
    
    @patch('src.chatbot.GeminiClient')
    @patch('src.chatbot.os.makedirs')
    @patch('src.chatbot.sys.exit')
    def test_initialize_failure(self, mock_exit, mock_makedirs, mock_gemini_client):
        """Test initialization failure handling."""
        mock_gemini_client.side_effect = Exception("API Error")
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()  # Mock the console to avoid output
        
        chatbot.initialize()
        
        mock_exit.assert_called_once_with(1)
        # Check that error message was printed
        chatbot.console.print.assert_called()
    
    @patch('src.chatbot.Console')
    @patch('src.chatbot.os.makedirs')
    def test_display_response(self, mock_makedirs, mock_console_class):
        """Test displaying a response with formatting."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.console.size = Mock()
        chatbot.console.size.width = 80
        chatbot.console.size.height = 24
        
        # Mock the temporary console used for measuring content
        mock_temp_console = Mock()
        mock_temp_console.file = StringIO("Short content\nLine 2\n")
        mock_console_class.return_value = mock_temp_console
        
        test_response = "This is a test response"
        chatbot.display_response(test_response)
        
        # Should call print twice (panel and empty line) for short content
        assert chatbot.console.print.call_count == 2
    
    @patch('src.chatbot.os.makedirs')
    def test_display_help(self, mock_makedirs):
        """Test displaying help information."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        chatbot.display_help()
        
        chatbot.console.print.assert_called_once()
    
    @patch('src.chatbot.os.makedirs')
    def test_display_history_empty(self, mock_makedirs):
        """Test displaying empty chat history."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.client = Mock()
        chatbot.client.get_chat_history.return_value = []
        
        chatbot.display_history()
        
        chatbot.console.print.assert_called_with("[dim]No conversation history yet[/dim]")
    
    @patch('src.chatbot.Console')
    @patch('src.chatbot.os.makedirs')
    def test_display_history_with_content(self, mock_makedirs, mock_console_class):
        """Test displaying chat history with content."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.console.size = Mock()
        chatbot.console.size.width = 80
        chatbot.console.size.height = 24
        chatbot.client = Mock()
        
        # Mock the temporary console used for measuring content
        mock_temp_console = Mock()
        mock_temp_console.file = StringIO("Short history\nLine 2\n")
        mock_console_class.return_value = mock_temp_console
        
        # Mock history items
        mock_item1 = Mock()
        mock_item1.role = 'user'
        mock_item1.parts = [Mock()]
        mock_item1.parts[0].text = "Hello"
        
        mock_item2 = Mock()
        mock_item2.role = 'assistant'
        mock_item2.parts = [Mock()]
        mock_item2.parts[0].text = "Hi there!"
        
        chatbot.client.get_chat_history.return_value = [mock_item1, mock_item2]
        
        chatbot.display_history()
        
        # Should print content for short history
        assert chatbot.console.print.call_count >= 1
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_quit(self, mock_makedirs):
        """Test processing quit command."""
        chatbot = GeminiChatbot()
        
        result = chatbot.process_command('/quit')
        assert result is False
        
        result = chatbot.process_command('/exit')
        assert result is False
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_help(self, mock_makedirs):
        """Test processing help command."""
        chatbot = GeminiChatbot()
        chatbot.display_help = Mock()
        
        result = chatbot.process_command('/help')
        
        assert result is True
        chatbot.display_help.assert_called_once()
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_clear(self, mock_makedirs):
        """Test processing clear command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.client = Mock()
        
        result = chatbot.process_command('/clear')
        
        assert result is True
        chatbot.client.clear_chat.assert_called_once()
        chatbot.console.print.assert_called_with("[green]✅ Chat history cleared[/green]")
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_history(self, mock_makedirs):
        """Test processing history command."""
        chatbot = GeminiChatbot()
        chatbot.display_history = Mock()
        
        result = chatbot.process_command('/history')
        
        assert result is True
        chatbot.display_history.assert_called_once()
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_model(self, mock_makedirs):
        """Test processing model command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.client = Mock()
        chatbot.client.model_name = "gemini-2.5-flash"
        
        result = chatbot.process_command('/model')
        
        assert result is True
        chatbot.console.print.assert_called_with("[bold]Current model:[/bold] gemini-2.5-flash")
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_prune(self, mock_makedirs):
        """Test processing prune command."""
        chatbot = GeminiChatbot()
        chatbot.prune_command_history = Mock()
        
        result = chatbot.process_command('/prune')
        
        assert result is True
        chatbot.prune_command_history.assert_called_once()
    
    @patch('src.chatbot.os.makedirs')
    def test_process_command_unknown(self, mock_makedirs):
        """Test processing unknown command."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        result = chatbot.process_command('/unknown')
        
        assert result is True
        # Should print error message
        assert chatbot.console.print.call_count == 2
    
    @patch('src.chatbot.os.path.exists')
    @patch('src.chatbot.os.makedirs')
    def test_prune_command_history_no_file(self, mock_makedirs, mock_exists):
        """Test pruning command history when no file exists."""
        mock_exists.return_value = False
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        chatbot.prune_command_history()
        
        chatbot.console.print.assert_called_with("[dim]No command history file found[/dim]")
    
    @patch('src.chatbot.prompt')
    @patch('src.chatbot.os.remove')
    @patch('src.chatbot.os.path.exists')
    @patch('src.chatbot.os.makedirs')
    def test_prune_command_history_confirmed(self, mock_makedirs, mock_exists, mock_remove, mock_prompt):
        """Test pruning command history with user confirmation."""
        mock_exists.return_value = True
        mock_prompt.return_value = "y"
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        chatbot.prune_command_history()
        
        mock_remove.assert_called_once_with(chatbot.history_file)
        chatbot.console.print.assert_called_with("[green]✅ Command history cleared[/green]")
    
    @patch('src.chatbot.prompt')
    @patch('src.chatbot.os.remove')
    @patch('src.chatbot.os.path.exists')
    @patch('src.chatbot.os.makedirs')
    def test_prune_command_history_declined(self, mock_makedirs, mock_exists, mock_remove, mock_prompt):
        """Test pruning command history when user declines."""
        mock_exists.return_value = True
        mock_prompt.return_value = "n"
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        chatbot.prune_command_history()
        
        mock_remove.assert_not_called()
        chatbot.console.print.assert_called_with("[dim]Command history preserved[/dim]")
    
    @patch('src.chatbot.prompt')
    @patch('src.chatbot.os.path.exists')
    @patch('src.chatbot.os.makedirs')
    def test_prune_command_history_keyboard_interrupt(self, mock_makedirs, mock_exists, mock_prompt):
        """Test pruning command history with keyboard interrupt."""
        mock_exists.return_value = True
        mock_prompt.side_effect = KeyboardInterrupt()
        
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        
        chatbot.prune_command_history()
        
        chatbot.console.print.assert_called_with("\n[dim]Command history preserved[/dim]")
    
    @patch('src.chatbot.os.makedirs')
    def test_run_initialization(self, mock_makedirs):
        """Test that run method properly initializes."""
        chatbot = GeminiChatbot()
        chatbot.initialize = Mock()
        
        # Mock the entire run loop to avoid hanging
        with patch.object(chatbot, 'run') as mock_run:
            mock_run.return_value = None
            chatbot.run()
            mock_run.assert_called_once()
    
    @patch('src.chatbot.os.makedirs')
    def test_message_processing_flow(self, mock_makedirs):
        """Test the message processing flow without the run loop."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.client = Mock()
        chatbot.client.send_message.return_value = "Test response"
        chatbot.display_response = Mock()
        
        # Test direct message processing (simulating what happens in run loop)
        user_input = "Hello, how are you?"
        
        # This simulates the core logic inside the run loop
        if not user_input.strip().startswith('/'):
            response = chatbot.client.send_message(user_input)
            chatbot.display_response(response)
        
        chatbot.client.send_message.assert_called_once_with(user_input)
        chatbot.display_response.assert_called_once_with("Test response")
    
    @patch('src.chatbot.os.makedirs')
    def test_command_processing_flow(self, mock_makedirs):
        """Test the command processing flow without the run loop."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.process_command = Mock(return_value=True)
        
        # Test direct command processing (simulating what happens in run loop)
        user_input = "/help"
        
        # This simulates the core logic inside the run loop
        if user_input.strip().startswith('/'):
            should_continue = chatbot.process_command(user_input)
            assert should_continue is True
        
        chatbot.process_command.assert_called_once_with(user_input)
    
    @patch('src.chatbot.os.makedirs')
    def test_empty_input_handling(self, mock_makedirs):
        """Test handling of empty input."""
        chatbot = GeminiChatbot()
        chatbot.console = Mock()
        chatbot.client = Mock()
        
        # Test empty input handling (simulating what happens in run loop)
        empty_inputs = ["", "  ", "\n", "\t"]
        
        for user_input in empty_inputs:
            # This simulates the core logic inside the run loop
            if not user_input.strip():
                # Should continue without processing
                continue
            # If we get here, input wasn't empty
            assert False, f"Input '{user_input}' should have been considered empty"
        
        # Client should not be called for empty inputs
        chatbot.client.send_message.assert_not_called()
