"""Interactive Gemini chatbot with rich UI."""

import sys
import os
from typing import Optional, Tuple, Dict, Any, List
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.buffer import Buffer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from io import StringIO
import re
import json
from .gemini_client import GeminiClient

# Try to import MCP components
try:
    from .mcp_config import MCPConfig
    from .mcp_manager import MCPManager

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class GeminiChatbot:
    """Interactive chatbot using Gemini model."""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the chatbot."""
        self.console = Console()
        self.client = None
        self.model_name = model_name
        self.mcp_manager = None

        # Create .chat directory if it doesn't exist
        self.chat_dir = ".chat"
        os.makedirs(self.chat_dir, exist_ok=True)
        self.history_file = os.path.join(self.chat_dir, "log.txt")

    def initialize(self):
        """Initialize the Gemini client and MCP manager."""
        try:
            self.console.print(
                "[bold blue]🚀 Initializing Gemini Chatbot...[/bold blue]"
            )
            self.client = GeminiClient(model_name=self.model_name)

            # Try to initialize MCP if available
            if MCP_AVAILABLE:
                try:
                    mcp_config = MCPConfig()
                    self.mcp_manager = MCPManager(mcp_config)
                    self.mcp_manager.initialize_sync()
                    self.console.print("[dim]MCP support enabled[/dim]")
                except Exception as e:
                    self.console.print(f"[dim]MCP not available: {e}[/dim]")
                    self.mcp_manager = None

            self.console.print("[bold green]✅ Chatbot ready![/bold green]")
            self.console.print(
                "[dim]Type '/help' for commands or '/quit' to exit[/dim]\n"
            )
        except Exception as e:
            self.console.print(f"[bold red]❌ Error: {e}[/bold red]")
            sys.exit(1)

    def cleanup(self):
        """Clean up resources before exit."""
        if self.mcp_manager:
            try:
                self.mcp_manager.cleanup_sync()
            except Exception:
                # Ignore cleanup errors
                pass

    def display_response(self, response: str):
        """Display the model's response with formatting and scrolling capability."""
        # First, render the response to a string buffer to measure its height
        temp_console = Console(file=StringIO(), width=self.console.size.width)
        md = Markdown(response)
        panel = Panel(
            md,
            title="[bold cyan]Gemini[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        temp_console.print(panel)
        rendered_content = temp_console.file.getvalue()

        # Count the number of lines in the rendered content
        content_lines = rendered_content.split("\n")
        terminal_height = self.console.size.height

        # If content fits in terminal, display normally
        if len(content_lines) <= terminal_height - 3:  # Leave space for prompt
            self.console.print(panel)
            self.console.print()
        else:
            # Use scrollable display for long content
            self._display_scrollable_content(
                rendered_content, "Gemini Response"
            )

    def _display_scrollable_content(self, rendered_content: str, title: str):
        """Display content in a scrollable interface."""
        lines = rendered_content.split("\n")

        # Create key bindings for scrolling
        kb = KeyBindings()

        @kb.add("q")
        @kb.add("escape")
        def _(event):
            "Exit the scrollable view"
            event.app.exit()

        @kb.add("up")
        @kb.add("k")
        def _(event):
            "Scroll up"
            buffer = event.app.layout.current_buffer
            if buffer.cursor_position > 0:
                # Move cursor up by finding the previous line start
                current_text = buffer.text
                current_pos = buffer.cursor_position
                prev_newline = current_text.rfind("\n", 0, current_pos - 1)
                if prev_newline == -1:
                    buffer.cursor_position = 0
                else:
                    prev_prev_newline = current_text.rfind(
                        "\n", 0, prev_newline - 1
                    )
                    buffer.cursor_position = (
                        prev_prev_newline + 1 if prev_prev_newline != -1 else 0
                    )

        @kb.add("down")
        @kb.add("j")
        def _(event):
            "Scroll down"
            buffer = event.app.layout.current_buffer
            current_text = buffer.text
            current_pos = buffer.cursor_position
            next_newline = current_text.find("\n", current_pos)
            if next_newline != -1:
                next_next_newline = current_text.find("\n", next_newline + 1)
                buffer.cursor_position = (
                    next_next_newline + 1
                    if next_next_newline != -1
                    else len(current_text)
                )

        @kb.add("home")
        @kb.add("g")
        def _(event):
            "Go to top"
            event.app.layout.current_buffer.cursor_position = 0

        @kb.add("end")
        @kb.add("G")
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
        root_container = HSplit(
            [
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
                    style="reverse",
                ),
            ]
        )

        # Add help text to the bottom window
        help_text = (
            "↑/↓ or j/k: scroll | Home/g: top | End/G: bottom | q/Esc: exit"
        )
        help_buffer = Buffer(document=Document(help_text), read_only=True)
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
        self.console.print(
            f"\n[dim]{title} is long. Opening scrollable view...[/dim]"
        )
        self.console.print(
            "[dim]Use arrow keys or j/k to scroll, q/Esc to exit[/dim]\n"
        )

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

# MCP Commands (if available)

- **/mcp connect <server>** - Connect to an MCP server
- **/mcp list** - List configured servers and connection status
- **/mcp resources** - List available resources from connected servers
- **/mcp prompts** - List available prompt templates
- **/mcp prompt <name> [args]** - Use a prompt template (e.g., /mcp prompt analyze_code language=python)
- **/mcp disconnect <server>** - Disconnect from an MCP server

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
        content_lines = rendered_content.split("\n")
        terminal_height = self.console.size.height

        # If content fits in terminal, display normally
        if len(content_lines) <= terminal_height - 3:  # Leave space for prompt
            self.console.print(history_content)
        else:
            # Use scrollable display for long history
            self._display_scrollable_content(
                rendered_content, "Conversation History"
            )

    def _build_history_content(self, history):
        """Build formatted history content as Rich markup."""
        from rich.text import Text

        content = Text()
        content.append("Conversation History:", style="bold")
        content.append("\n")

        for item in history:
            # Determine role from the item's role attribute or type
            if hasattr(item, "role"):
                role = "You" if item.role == "user" else "Gemini"
            else:
                # Fallback to alternating pattern
                role = (
                    "You"
                    if len(
                        [
                            h
                            for h in history[: history.index(item) + 1]
                            if getattr(h, "role", None) == "user"
                        ]
                    )
                    % 2
                    == 1
                    else "Gemini"
                )

            color = "green" if role == "You" else "cyan"
            content.append(f"\n{role}:", style=f"bold {color}")
            content.append("\n")

            # Extract text from parts
            if hasattr(item, "parts") and item.parts:
                text = (
                    item.parts[0].text
                    if hasattr(item.parts[0], "text")
                    else str(item.parts[0])
                )
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
        original_command = command
        command = command.lower().strip()

        if command in ["/quit", "/exit"]:
            return False
        elif command == "/help":
            self.display_help()
        elif command == "/clear":
            self.client.clear_chat()
            self.console.print("[green]✅ Chat history cleared[/green]")
        elif command == "/history":
            self.display_history()
        elif command == "/model":
            self.console.print(
                f"[bold]Current model:[/bold] {self.client.model_name}"
            )
        elif command == "/prune":
            self.prune_command_history()
        elif command.startswith("/mcp"):
            self.process_mcp_command(original_command)
        else:
            self.console.print(f"[red]Unknown command: {command}[/red]")
            self.console.print(
                "[dim]Type '/help' for available commands[/dim]"
            )

        return True

    def process_mcp_command(self, command: str):
        """Process MCP-related commands."""
        if not self.mcp_manager:
            self.console.print("[red]❌ MCP is not available[/red]")
            return

        parts = command.split()
        if len(parts) == 1:
            # Just "/mcp" - show usage
            self.console.print("[bold]MCP Commands:[/bold]")
            self.console.print("  /mcp connect <server> - Connect to a server")
            self.console.print("  /mcp list - List servers and status")
            self.console.print("  /mcp resources - List available resources")
            self.console.print(
                "  /mcp prompts - List available prompt templates"
            )
            self.console.print(
                "  /mcp prompt <name> [args] - Use a prompt template"
            )
            self.console.print(
                "  /mcp disconnect <server> - Disconnect from a server"
            )
            return

        subcommand = parts[1].lower()

        if subcommand == "list":
            self.mcp_list_servers()
        elif subcommand == "connect" and len(parts) > 2:
            server_name = parts[2]
            self.mcp_connect(server_name)
        elif subcommand == "disconnect" and len(parts) > 2:
            server_name = parts[2]
            self.mcp_disconnect(server_name)
        elif subcommand == "resources":
            self.mcp_list_resources()
        elif subcommand == "prompts":
            self.mcp_list_prompts()
        elif subcommand == "prompt" and len(parts) > 2:
            prompt_name = parts[2]
            # Parse any arguments after the prompt name
            args_str = " ".join(parts[3:]) if len(parts) > 3 else ""
            self.mcp_use_prompt(prompt_name, args_str)
        else:
            self.console.print(f"[red]Invalid MCP command: {command}[/red]")
            self.console.print("[dim]Type '/mcp' for usage[/dim]")

    def mcp_list_servers(self):
        """List MCP servers and their connection status."""
        servers = self.mcp_manager.list_servers()

        if not servers:
            self.console.print("[dim]No MCP servers configured[/dim]")
            return

        self.console.print("\n[bold]MCP Servers:[/bold]")
        for server in servers:
            status = (
                "✅ Connected" if server["connected"] else "⚪ Disconnected"
            )
            transport = server["transport"]
            self.console.print(
                f"  • {server['name']} ({transport}) - {status}"
            )
        self.console.print()

    def mcp_connect(self, server_name: str):
        """Connect to an MCP server."""
        try:
            self.mcp_manager.connect_server_sync(server_name)
            self.console.print(
                f"[green]✅ Connected to MCP server: {server_name}[/green]"
            )
        except Exception as e:
            self.console.print(f"[red]❌ Failed to connect: {e}[/red]")

    def mcp_disconnect(self, server_name: str):
        """Disconnect from an MCP server."""
        try:
            self.mcp_manager.disconnect_server_sync(server_name)
            self.console.print(
                f"[yellow]🔌 Disconnected from MCP server: {server_name}[/yellow]"
            )
        except Exception as e:
            self.console.print(f"[red]❌ Failed to disconnect: {e}[/red]")

    def mcp_list_resources(self):
        """List available MCP resources."""
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            self.console.print("[dim]No MCP servers connected[/dim]")
            return

        try:
            resources = self.mcp_manager.get_resources_sync()

            if not resources:
                self.console.print(
                    "[dim]No resources available from connected servers[/dim]"
                )
                return

            self.console.print("\n[bold]MCP Resources:[/bold]")
            for resource in resources:
                server = resource.get("server", "unknown")
                name = resource.get("name", "Unnamed")
                uri = resource.get("uri", "")
                desc = resource.get("description", "No description")
                mime = resource.get("mimeType", "unknown")

                self.console.print(f"\n• {name} (from {server})")
                self.console.print(f"  URI: {uri}")
                self.console.print(f"  Type: {mime}")
                self.console.print(f"  Description: {desc}")
            self.console.print()

        except Exception as e:
            self.console.print(f"[red]❌ Failed to list resources: {e}[/red]")

    def mcp_list_prompts(self):
        """List available MCP prompt templates."""
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            self.console.print("[dim]No MCP servers connected[/dim]")
            return

        try:
            prompts = self.mcp_manager.get_prompts_sync()

            if not prompts:
                self.console.print(
                    "[dim]No prompts available from connected servers[/dim]"
                )
                return

            self.console.print("\n[bold]MCP Prompt Templates:[/bold]")
            for prompt in prompts:
                server = prompt.get("server", "unknown")
                name = prompt.get("name", "Unnamed")
                desc = prompt.get("description", "No description")
                args = prompt.get("arguments", [])

                self.console.print(f"\n• {name} (from {server})")
                self.console.print(f"  Description: {desc}")

                if args:
                    self.console.print("  Arguments:")
                    for arg in args:
                        arg_name = arg.get("name", "unnamed")
                        arg_desc = arg.get("description", "")
                        required = arg.get("required", False)
                        req_text = " [required]" if required else " [optional]"
                        self.console.print(
                            f"    - {arg_name}{req_text}: {arg_desc}"
                        )
            self.console.print()

        except Exception as e:
            self.console.print(f"[red]❌ Failed to list prompts: {e}[/red]")

    def mcp_use_prompt(self, prompt_name: str, args_str: str):
        """Use an MCP prompt template."""
        # Find which server provides this prompt
        server_name = self._find_prompt_server(prompt_name)

        if not server_name:
            self.console.print(
                f"[red]Prompt '{prompt_name}' not found in connected servers[/red]"
            )
            return

        # Parse arguments
        arguments = self._parse_prompt_args(args_str)

        try:
            # Get the prompt with arguments
            with self.console.status(
                f"[dim]Loading prompt '{prompt_name}'...[/dim]"
            ):
                prompt_result = self.mcp_manager.get_prompt_sync(
                    server_name, prompt_name, arguments
                )

            # Format the prompt for Gemini
            prompt_text = self._format_prompt_for_gemini(prompt_result)

            # Process as a chat message
            self._process_chat_message(prompt_text)

        except Exception as e:
            self.console.print(f"[red]❌ Failed to use prompt: {e}[/red]")

    def prune_command_history(self):
        """Clear the local command history file with confirmation."""
        if not os.path.exists(self.history_file):
            self.console.print("[dim]No command history file found[/dim]")
            return

        # Show confirmation prompt
        self.console.print(
            "[yellow]⚠️  This will permanently delete your local command history.[/yellow]"
        )
        self.console.print(
            "[dim]This affects the up/down arrow command recall, not conversation history.[/dim]"
        )

        try:
            confirmation = (
                prompt("Are you sure? (y/N): ", default="n").lower().strip()
            )

            if confirmation in ["y", "yes"]:
                try:
                    os.remove(self.history_file)
                    self.console.print(
                        "[green]✅ Command history cleared[/green]"
                    )
                except OSError as e:
                    self.console.print(
                        f"[red]❌ Error clearing history: {e}[/red]"
                    )
            else:
                self.console.print("[dim]Command history preserved[/dim]")
        except KeyboardInterrupt:
            self.console.print("\n[dim]Command history preserved[/dim]")

    def _format_mcp_tools_context(self) -> str:
        """Format available MCP tools as context for Gemini."""
        if not self.mcp_manager:
            return ""

        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            return ""

        try:
            tools = self.mcp_manager.get_tools_sync()
            if not tools:
                return ""

            context = "\nAvailable MCP Tools:\n"
            for tool in tools:
                context += f"\n- Tool: {tool['name']} (from {tool.get('server', 'unknown')})\n"
                context += f"  Description: {tool.get('description', 'No description')}\n"

                # Add parameter information if available
                if (
                    "inputSchema" in tool
                    and "properties" in tool["inputSchema"]
                ):
                    context += "  Parameters:\n"
                    for param, schema in tool["inputSchema"][
                        "properties"
                    ].items():
                        required = param in tool["inputSchema"].get(
                            "required", []
                        )
                        req_text = " (required)" if required else " (optional)"
                        context += f"    - {param}: {schema.get('type', 'any')} - {schema.get('description', 'No description')}{req_text}\n"

            return context
        except Exception:
            return ""

    def _detect_tool_request(
        self, response: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Detect if Gemini's response indicates a tool should be called.

        Returns:
            Tuple of (tool_name, arguments) or (None, None) if no tool request detected.
        """
        # Pattern 1: "Let me use the X tool" or "I'll use the X tool"
        pattern1 = r"(?:Let me use|I'll use|I will use|Using) the (\w+) tool"

        # Pattern 2: "I need to use the X tool with"
        pattern2 = r"I need to use the (\w+) tool"

        # Check for tool mention
        tool_match = re.search(pattern1, response, re.IGNORECASE) or re.search(
            pattern2, response, re.IGNORECASE
        )

        if not tool_match:
            return None, None

        tool_name = tool_match.group(1)

        # Try to extract arguments from the response
        arguments = {}

        # Look for patterns like "for New York" or "with location New York"
        location_match = re.search(
            r"(?:for|with location|in) ([A-Z][A-Za-z\s]+)", response
        )
        if location_match:
            arguments["location"] = location_match.group(1).strip()

        # Look for numeric values pattern
        values_match = re.search(
            r"with values? (\d+(?:\s+and\s+\d+)*)", response
        )
        if values_match:
            values_text = values_match.group(1)
            values = [
                int(v.strip()) for v in re.split(r"\s+and\s+", values_text)
            ]
            arguments["values"] = values

        return tool_name, arguments if arguments else {}

    def _find_tool_server(self, tool_name: str) -> Optional[str]:
        """Find which server provides a specific tool."""
        if not self.mcp_manager:
            return None

        try:
            tools = self.mcp_manager.get_tools_sync()
            for tool in tools:
                if tool["name"] == tool_name:
                    return tool.get("server")
            return None
        except Exception:
            return None

    def _execute_mcp_tool(
        self, server_name: str, tool_name: str, arguments: dict
    ) -> str:
        """Execute an MCP tool and return formatted results."""
        try:
            result = self.mcp_manager.call_tool_sync(
                server_name, tool_name, arguments
            )

            # Extract text content from the result
            if "content" in result and isinstance(result["content"], list):
                text_parts = []
                for content in result["content"]:
                    if content.get("type") == "text":
                        text_parts.append(content.get("text", ""))
                return (
                    "\n".join(text_parts)
                    if text_parts
                    else "Tool executed successfully (no text output)"
                )

            return f"Tool result: {json.dumps(result)}"

        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"

    def _format_mcp_resources_context(self) -> str:
        """Format available MCP resources as context for Gemini."""
        if not self.mcp_manager:
            return ""

        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            return ""

        try:
            resources = self.mcp_manager.get_resources_sync()
            if not resources:
                return ""

            context = "\nAvailable MCP Resources:\n"
            for resource in resources:
                context += f"\n- Resource: {resource.get('name', 'Unnamed')} (from {resource.get('server', 'unknown')})\n"
                context += f"  URI: {resource.get('uri', '')}\n"
                context += f"  Description: {resource.get('description', 'No description')}\n"
                if "mimeType" in resource:
                    context += f"  Type: {resource['mimeType']}\n"

            return context
        except Exception:
            return ""

    def _detect_resource_reference(self, text: str) -> List[str]:
        """Detect resource URIs referenced in text.

        Returns:
            List of resource URIs found in the text.
        """
        import re

        # Pattern to match common resource URI schemes
        # Matches: file:///path, github:repo/file, db://table, etc.
        pattern = (
            r'(?:file://|github:|db://|https?://|resource://)[^\s,;"\'\?!]+'
        )

        matches = re.findall(pattern, text)
        return matches

    def _find_resource_server(self, resource_uri: str) -> Optional[str]:
        """Find which server provides a specific resource."""
        if not self.mcp_manager:
            return None

        try:
            resources = self.mcp_manager.get_resources_sync()
            for resource in resources:
                if resource.get("uri") == resource_uri:
                    return resource.get("server")
            return None
        except Exception:
            return None

    def _read_mcp_resource(self, server_name: str, resource_uri: str) -> str:
        """Read an MCP resource and return its content."""
        try:
            result = self.mcp_manager.read_resource_sync(
                server_name, resource_uri
            )

            # Extract content from the result
            if "contents" in result and isinstance(result["contents"], list):
                for content in result["contents"]:
                    # Handle text content
                    if "text" in content:
                        return content["text"]
                    # Handle binary content
                    elif "blob" in content:
                        mime_type = content.get("mimeType", "unknown")
                        return f"[Binary content: {mime_type}]"

            return f"Resource content: {json.dumps(result)}"

        except Exception as e:
            return f"Error reading resource '{resource_uri}': {str(e)}"

    def _find_prompt_server(self, prompt_name: str) -> Optional[str]:
        """Find which server provides a specific prompt."""
        if not self.mcp_manager:
            return None

        try:
            prompts = self.mcp_manager.get_prompts_sync()
            for prompt in prompts:
                if prompt.get("name") == prompt_name:
                    return prompt.get("server")
            return None
        except Exception:
            return None

    def _parse_prompt_args(self, args_str: str) -> Dict[str, Any]:
        """Parse prompt arguments from a string.

        Supports formats like:
        - arg1=value1 arg2=value2
        - name="John Doe" age=30
        """
        import shlex

        if not args_str.strip():
            return {}

        arguments = {}
        try:
            # Use shlex to handle quoted strings properly
            parts = shlex.split(args_str)
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    arguments[key] = value
        except Exception:
            # If parsing fails, return empty dict
            pass

        return arguments

    def _format_prompt_for_gemini(self, prompt_result: Dict[str, Any]) -> str:
        """Format MCP prompt messages for Gemini.

        Extracts user messages from the prompt result and formats them
        as a single message for Gemini.
        """
        messages = prompt_result.get("messages", [])

        # Extract text from user messages
        user_texts = []
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", {})
                if isinstance(content, dict) and content.get("type") == "text":
                    user_texts.append(content.get("text", ""))
                elif isinstance(content, str):
                    user_texts.append(content)

        # Join all user texts into a single message
        return "\n\n".join(user_texts) if user_texts else ""

    def _suggest_prompts_for_query(self, query: str) -> List[Dict[str, Any]]:
        """Suggest relevant prompts based on user query.

        Returns a list of prompts that might be relevant to the query.
        """
        if not self.mcp_manager:
            return []

        try:
            all_prompts = self.mcp_manager.get_prompts_sync()

            # Simple keyword matching for now
            query_lower = query.lower()
            relevant_prompts = []

            for prompt in all_prompts:
                name = prompt.get("name", "").lower()
                desc = prompt.get("description", "").lower()

                # Check if any keywords from the query appear in name or description
                keywords = [
                    "analyze",
                    "code",
                    "error",
                    "explain",
                    "summarize",
                    "help",
                ]
                for keyword in keywords:
                    if keyword in query_lower and (
                        keyword in name or keyword in desc
                    ):
                        relevant_prompts.append(prompt)
                        break

            return relevant_prompts[:3]  # Return top 3 suggestions

        except Exception:
            return []

    def _process_chat_message(self, user_input: str):
        """Process a chat message with potential MCP tool and resource integration."""
        # Check for resource references in the user input
        resource_refs = self._detect_resource_reference(user_input)
        resource_contents = {}

        # Read any referenced resources
        if resource_refs and self.mcp_manager:
            for resource_uri in resource_refs:
                server_name = self._find_resource_server(resource_uri)
                if server_name:
                    with self.console.status(
                        f"[dim]Reading {resource_uri}...[/dim]"
                    ):
                        content = self._read_mcp_resource(
                            server_name, resource_uri
                        )
                        resource_contents[resource_uri] = content

        # Get MCP contexts
        tools_context = self._format_mcp_tools_context()
        resources_context = self._format_mcp_resources_context()

        # Build the enhanced user message with resource contents
        enhanced_message = user_input
        if resource_contents:
            enhanced_message = (
                f"{user_input}\n\n--- Referenced Resources ---\n"
            )
            for uri, content in resource_contents.items():
                enhanced_message += f"\nContent of {uri}:\n{content}\n"

        # Build system instruction
        system_instruction = None
        if tools_context or resources_context:
            system_instruction = "You are a helpful assistant with access to external tools and resources via MCP (Model Context Protocol)."

            if tools_context:
                system_instruction += f"\n{tools_context}"
                system_instruction += "\nWhen a user asks for something that could benefit from using one of these tools, mention that you'll use the appropriate tool."

            if resources_context:
                system_instruction += f"\n{resources_context}"
                system_instruction += "\nThese resources can be accessed when the user references them by URI."

        # Get response from Gemini
        with self.console.status("[dim]Thinking...[/dim]"):
            response = self.client.send_message(
                enhanced_message, system_instruction
            )

        # Display initial response
        self.display_response(response)

        # Check if response indicates a tool should be called
        tool_name, arguments = self._detect_tool_request(response)

        if tool_name and self.mcp_manager:
            # Find which server provides this tool
            server_name = self._find_tool_server(tool_name)

            if server_name:
                # Execute the tool
                with self.console.status(
                    f"[dim]Executing {tool_name} tool...[/dim]"
                ):
                    tool_result = self._execute_mcp_tool(
                        server_name, tool_name, arguments
                    )

                # Send tool result back to Gemini for final response
                follow_up = f"The {tool_name} tool returned: {tool_result}\n\nPlease provide a natural response to the user based on this result."

                with self.console.status(
                    "[dim]Processing tool result...[/dim]"
                ):
                    final_response = self.client.send_message(follow_up)

                # Display final response
                self.display_response(final_response)
            else:
                self.console.print(
                    f"[yellow]Tool '{tool_name}' not found in connected servers[/yellow]"
                )

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
                    mouse_support=True,
                )

                # Skip empty input
                if not user_input.strip():
                    continue

                # Check for commands
                if user_input.strip().startswith("/"):
                    if not self.process_command(user_input):
                        break
                    continue

                # Process the message (handles both regular chat and MCP tools)
                self._process_chat_message(user_input)

            except KeyboardInterrupt:
                self.console.print(
                    "\n[yellow]Use '/quit' to exit properly[/yellow]"
                )
            except Exception as e:
                self.console.print(f"\n[bold red]Error: {e}[/bold red]")

        # Cleanup before exit
        self.cleanup()
        self.console.print("\n[bold blue]👋 Goodbye![/bold blue]")
