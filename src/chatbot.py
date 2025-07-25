"""Interactive Gemini chatbot with rich UI."""

import sys
import os
from typing import Optional
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from .gemini_client import GeminiClient


class GeminiChatbot:
    """Interactive chatbot using Gemini model."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize the chatbot."""
        self.console = Console()
        self.client = None
        self.model_name = model_name
        
        # Create .chat directory if it doesn't exist
        self.chat_dir = ".chat"
        os.makedirs(self.chat_dir, exist_ok=True)
        self.history_file = os.path.join(self.chat_dir, "log.txt")
        
    def initialize(self):
        """Initialize the Gemini client."""
        try:
            self.console.print("[bold blue]🚀 Initializing Gemini Chatbot...[/bold blue]")
            self.client = GeminiClient(model_name=self.model_name)
            self.console.print("[bold green]✅ Chatbot ready![/bold green]")
            self.console.print("[dim]Type '/help' for commands or '/quit' to exit[/dim]\n")
        except Exception as e:
            self.console.print(f"[bold red]❌ Error: {e}[/bold red]")
            sys.exit(1)
    
    def display_response(self, response: str):
        """Display the model's response with formatting."""
        # Use Markdown rendering for better formatting
        md = Markdown(response)
        panel = Panel(
            md,
            title="[bold cyan]Gemini[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()
    
    def display_help(self):
        """Display help information."""
        help_text = """
# Available Commands

- **/help** - Show this help message
- **/clear** - Clear the chat history and start fresh
- **/history** - Show the conversation history
- **/model** - Show current model information
- **/prune** - Clear local command history (with confirmation)
- **/quit** or **/exit** - Exit the chatbot

# Tips

- You can use multi-line input by pressing Shift+Enter
- Your chat history is saved between sessions
- Responses are formatted with Markdown for better readability
        """
        self.console.print(Markdown(help_text))
    
    def display_history(self):
        """Display the conversation history."""
        history = self.client.get_chat_history()
        if not history:
            self.console.print("[dim]No conversation history yet[/dim]")
            return
        
        self.console.print("[bold]Conversation History:[/bold]")
        for item in history:
            # Determine role from the item's role attribute or type
            if hasattr(item, 'role'):
                role = "You" if item.role == 'user' else "Gemini"
            else:
                # Fallback to alternating pattern
                role = "You" if len([h for h in history[:history.index(item)+1] if getattr(h, 'role', None) == 'user']) % 2 == 1 else "Gemini"
            
            color = "green" if role == "You" else "cyan"
            self.console.print(f"\n[bold {color}]{role}:[/bold {color}]")
            
            # Extract text from parts
            if hasattr(item, 'parts') and item.parts:
                text = item.parts[0].text if hasattr(item.parts[0], 'text') else str(item.parts[0])
                self.console.print(text)
            else:
                self.console.print(str(item))
    
    def process_command(self, command: str) -> bool:
        """
        Process special commands.
        
        Returns:
            True if should continue, False if should exit.
        """
        command = command.lower().strip()
        
        if command in ['/quit', '/exit']:
            return False
        elif command == '/help':
            self.display_help()
        elif command == '/clear':
            self.client.clear_chat()
            self.console.print("[green]✅ Chat history cleared[/green]")
        elif command == '/history':
            self.display_history()
        elif command == '/model':
            self.console.print(f"[bold]Current model:[/bold] {self.client.model_name}")
        elif command == '/prune':
            self.prune_command_history()
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print("[dim]Type '/help' for available commands[/dim]")
        
        return True
    
    def prune_command_history(self):
        """Clear the local command history file with confirmation."""
        if not os.path.exists(self.history_file):
            self.console.print("[dim]No command history file found[/dim]")
            return
        
        # Show confirmation prompt
        self.console.print("[yellow]⚠️  This will permanently delete your local command history.[/yellow]")
        self.console.print("[dim]This affects the up/down arrow command recall, not conversation history.[/dim]")
        
        try:
            confirmation = prompt(
                "Are you sure? (y/N): ",
                default="n"
            ).lower().strip()
            
            if confirmation in ['y', 'yes']:
                try:
                    os.remove(self.history_file)
                    self.console.print("[green]✅ Command history cleared[/green]")
                except OSError as e:
                    self.console.print(f"[red]❌ Error clearing history: {e}[/red]")
            else:
                self.console.print("[dim]Command history preserved[/dim]")
        except KeyboardInterrupt:
            self.console.print("\n[dim]Command history preserved[/dim]")
    
    def run(self):
        """Run the interactive chatbot."""
        self.initialize()
        
        # Create prompt session with history
        history = FileHistory(self.history_file)
        
        while True:
            try:
                # Get user input with rich prompt
                user_input = prompt(
                    "You> ",
                    history=history,
                    auto_suggest=AutoSuggestFromHistory(),
                    multiline=False,
                    mouse_support=True
                )
                
                # Skip empty input
                if not user_input.strip():
                    continue
                
                # Check for commands
                if user_input.strip().startswith('/'):
                    if not self.process_command(user_input):
                        break
                    continue
                
                # Send message to Gemini
                with self.console.status("[dim]Thinking...[/dim]"):
                    response = self.client.send_message(user_input)
                
                # Display response
                self.display_response(response)
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use '/quit' to exit properly[/yellow]")
            except Exception as e:
                self.console.print(f"\n[bold red]Error: {e}[/bold red]")
        
        self.console.print("\n[bold blue]👋 Goodbye![/bold blue]")
