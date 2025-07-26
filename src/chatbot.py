"""Interactive Gemini chatbot with rich UI."""

import sys
import os
from typing import Optional
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from io import StringIO
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
        """Display the model's response with formatting and scrolling capability."""
        # First, render the response to a string buffer to measure its height
        temp_console = Console(file=StringIO(), width=self.console.size.width)
        md = Markdown(response)
        panel = Panel(
            md,
            title="[bold cyan]Gemini[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        temp_console.print(panel)
        rendered_content = temp_console.file.getvalue()
        
        # Count the number of lines in the rendered content
        content_lines = rendered_content.split('\n')
        terminal_height = self.console.size.height
        
        # If content fits in terminal, display normally
        if len(content_lines) <= terminal_height - 3:  # Leave space for prompt
            self.console.print(panel)
            self.console.print()
        else:
            # Use scrollable display for long content
            self._display_scrollable_content(rendered_content, "Gemini Response")
    
    def _display_scrollable_content(self, rendered_content: str, title: str):
        """Display content in a scrollable interface."""
        lines = rendered_content.split('\n')
        
        # Create key bindings for scrolling
        kb = KeyBindings()
        
        @kb.add('q')
        @kb.add('escape')
        def _(event):
            "Exit the scrollable view"
            event.app.exit()
        
        @kb.add('up')
        @kb.add('k')
        def _(event):
            "Scroll up"
            buffer = event.app.layout.current_buffer
            if buffer.cursor_position > 0:
                # Move cursor up by finding the previous line start
                current_text = buffer.text
                current_pos = buffer.cursor_position
                prev_newline = current_text.rfind('\n', 0, current_pos - 1)
                if prev_newline == -1:
                    buffer.cursor_position = 0
                else:
                    prev_prev_newline = current_text.rfind('\n', 0, prev_newline - 1)
                    buffer.cursor_position = prev_prev_newline + 1 if prev_prev_newline != -1 else 0
        
        @kb.add('down')
        @kb.add('j')
        def _(event):
            "Scroll down"
            buffer = event.app.layout.current_buffer
            current_text = buffer.text
            current_pos = buffer.cursor_position
            next_newline = current_text.find('\n', current_pos)
            if next_newline != -1:
                next_next_newline = current_text.find('\n', next_newline + 1)
                buffer.cursor_position = next_next_newline + 1 if next_next_newline != -1 else len(current_text)
        
        @kb.add('home')
        @kb.add('g')
        def _(event):
            "Go to top"
            event.app.layout.current_buffer.cursor_position = 0
        
        @kb.add('end')
        @kb.add('G')
        def _(event):
            "Go to bottom"
            buffer = event.app.layout.current_buffer
            buffer.cursor_position = len(buffer.text)
        
        # Create buffer with the content
        from prompt_toolkit.document import Document
        buffer = Buffer(
            document=Document(rendered_content),
            read_only=True,
        )
        
        # Create the layout
        root_container = HSplit([
            Window(
                content=BufferControl(buffer=buffer),
                height=None,
                wrap_lines=True,
            ),
            Window(
                content=BufferControl(
                    buffer=Buffer(
                        document=None,
                        read_only=True,
                    )
                ),
                height=1,
                style='reverse',
            ),
        ])
        
        # Add help text to the bottom window
        help_text = "↑/↓ or j/k: scroll | Home/g: top | End/G: bottom | q/Esc: exit"
        help_buffer = Buffer(
            document=Document(help_text),
            read_only=True
        )
        root_container.children[1].content.buffer = help_buffer
        
        layout = Layout(root_container)
        
        # Create and run the application
        app = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            mouse_support=True,
        )
        
        content_type = title.lower()
        self.console.print(f"\n[dim]{title} is long. Opening scrollable view...[/dim]")
        self.console.print("[dim]Use arrow keys or j/k to scroll, q/Esc to exit[/dim]\n")
        
        try:
            app.run()
        except KeyboardInterrupt:
            pass
        
        self.console.print("[dim]Returned to chat[/dim]\n")
    
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
        """Display the conversation history with scrolling capability."""
        history = self.client.get_chat_history()
        if not history:
            self.console.print("[dim]No conversation history yet[/dim]")
            return
        
        # Build the history content as a string first
        history_content = self._build_history_content(history)
        
        # Render to measure height
        temp_console = Console(file=StringIO(), width=self.console.size.width)
        temp_console.print(history_content)
        rendered_content = temp_console.file.getvalue()
        
        # Count lines and check if scrolling is needed
        content_lines = rendered_content.split('\n')
        terminal_height = self.console.size.height
        
        # If content fits in terminal, display normally
        if len(content_lines) <= terminal_height - 3:  # Leave space for prompt
            self.console.print(history_content)
        else:
            # Use scrollable display for long history
            self._display_scrollable_content(rendered_content, "Conversation History")
    
    def _build_history_content(self, history):
        """Build formatted history content as Rich markup."""
        from rich.text import Text
        
        content = Text()
        content.append("Conversation History:", style="bold")
        content.append("\n")
        
        for item in history:
            # Determine role from the item's role attribute or type
            if hasattr(item, 'role'):
                role = "You" if item.role == 'user' else "Gemini"
            else:
                # Fallback to alternating pattern
                role = "You" if len([h for h in history[:history.index(item)+1] if getattr(h, 'role', None) == 'user']) % 2 == 1 else "Gemini"
            
            color = "green" if role == "You" else "cyan"
            content.append(f"\n{role}:", style=f"bold {color}")
            content.append("\n")
            
            # Extract text from parts
            if hasattr(item, 'parts') and item.parts:
                text = item.parts[0].text if hasattr(item.parts[0], 'text') else str(item.parts[0])
                content.append(text)
            else:
                content.append(str(item))
            content.append("\n")
        
        return content
    
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
