"""Interactive chatbot powered by the Claude Agent SDK."""

from __future__ import annotations

import os
import sys
from typing import List, Optional

from prompt_toolkit import prompt
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from .claude_agent_client import ClaudeAgentClient
from .mcp_config import MCPConfig, MCPConfigError

# MCP support (optional)
try:
    from .mcp_manager import MCPManager

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


class ClaudeAgentChatbot:
    """Terminal user interface that drives the Claude Agent SDK."""

    HISTORY_DIR = ".claude"
    HISTORY_FILE = "history.txt"

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        sdk_client=None,
        mcp_config: Optional[MCPConfig] = None,
    ) -> None:
        self.console = Console()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self._sdk_client = sdk_client
        self._mcp_config = mcp_config
        self.client: Optional[ClaudeAgentClient] = None
        self.history: List[dict] = []
        self.mcp_manager: Optional["MCPManager"] = None

        os.makedirs(self.HISTORY_DIR, exist_ok=True)
        self._history_path = os.path.join(self.HISTORY_DIR, self.HISTORY_FILE)

    def initialize(self) -> None:
        """Load MCP configuration and boot the Claude Agent client."""

        if self.client is not None:
            return

        servers = []
        config = self._mcp_config
        if config is None:
            try:
                config = MCPConfig()
            except MCPConfigError as error:
                self.console.print(
                    f"[yellow]⚠️ Unable to load MCP configuration: {error}[/yellow]"
                )
            else:
                servers = config.servers
        else:
            servers = config.servers

        self.console.print("[bold blue]🚀 Starting Claude Agent REPL...[/bold blue]")

        # Try to initialize MCP first if available
        if MCP_AVAILABLE:
            try:
                if config is None:
                    config = MCPConfig()
                self.mcp_manager = MCPManager(config)
                self.mcp_manager.initialize_sync()
                self.console.print("[dim]MCP support enabled[/dim]")
            except Exception as e:
                self.console.print(f"[dim]MCP initialization warning: {e}[/dim]")
                self.mcp_manager = None

        # Create client with MCP manager
        self.client = ClaudeAgentClient(
            model_name=self.model_name,
            system_prompt=self.system_prompt,
            sdk_client=self._sdk_client,
            mcp_servers=servers,
            mcp_manager=self.mcp_manager,
        )
        self.client.ensure_session(self.system_prompt)

        self.console.print("[bold green]✅ Ready![/bold green]")
        self.console.print("[dim]Type /help for a list of commands.[/dim]\n")

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------
    def handle_command(self, command: str) -> bool:
        """Handle special slash commands.

        Returns True when the REPL should exit.
        """

        if command == "/help":
            self._display_help()
            return False
        if command == "/history":
            self._display_history()
            return False
        if command.startswith("/system"):
            return self._update_system_prompt(command)
        if command == "/clear":
            self._clear_history()
            return False
        if command.startswith("/mcp"):
            self._process_mcp_command(command)
            return False
        if command == "/quit":
            return True

        self.console.print(
            "[yellow]Unknown command. Type /help to see available commands.[/yellow]"
        )
        return False

    def _display_help(self) -> None:
        help_text = """[bold]Available commands[/bold]:
/help      Show this message
/history   Display the current chat history
/system    Update the system prompt for subsequent replies
/clear     Clear chat history and start a new Claude session
/quit      Exit the program"""

        if self.mcp_manager:
            help_text += """

[bold]MCP commands[/bold]:
/mcp       Show MCP command usage
/mcp list  List configured MCP servers"""

        self.console.print(
            Panel(
                help_text,
                title="Claude Agent Commands",
                border_style="cyan",
            )
        )

    def _display_history(self) -> None:
        if not self.history:
            self.console.print("[dim]No conversation history yet.[/dim]")
            return

        for turn in self.history:
            role = turn["role"].capitalize()
            text = turn["content"]
            style = "bold green" if role == "Assistant" else "bold blue"
            self.console.print(Panel(Markdown(text), title=role, border_style=style))

    def _update_system_prompt(self, command: str) -> bool:
        parts = command.split(" ", 1)
        if len(parts) == 1 or not parts[1].strip():
            self.console.print(
                "[yellow]Usage: /system <new system prompt text>[/yellow]"
            )
            return False

        new_prompt = parts[1].strip()
        self.system_prompt = new_prompt
        if self.client:
            self.client.reset_session(system_instruction=new_prompt)
        self.console.print("[green]System prompt updated.[/green]")
        return False

    def _clear_history(self) -> None:
        self.history.clear()
        if self.client:
            self.client.reset_session(system_instruction=self.system_prompt)
        self.console.print("[dim]Conversation cleared.[/dim]")

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------
    def _render_response(self, text: str) -> None:
        panel = Panel(
            Markdown(text),
            title="Claude",
            border_style="magenta",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def _record_turn(self, role: str, message: str) -> None:
        self.history.append({"role": role, "content": message})

        try:
            with open(self._history_path, "a", encoding="utf-8") as history_file:
                history_file.write(f"{role}: {message}\n")
        except OSError:
            # Persisting history is best-effort only.
            pass

    def _chat_once(self, user_message: str) -> None:
        if not self.client:
            raise RuntimeError("Claude client is not initialized")

        self._record_turn("user", user_message)
        response_text = self.client.send_message(
            user_message, system_instruction=self.system_prompt
        )
        self._record_turn("assistant", response_text)
        self._render_response(response_text)

    # ------------------------------------------------------------------
    # MCP command handling
    # ------------------------------------------------------------------
    def _process_mcp_command(self, command: str) -> None:
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
            self.console.print("  /mcp tools - List available tools")
            self.console.print("  /mcp resources - List available resources")
            self.console.print("  /mcp prompts - List available prompt templates")
            self.console.print("  /mcp prompt <name> [args] - Use a prompt template")
            self.console.print("  /mcp disconnect <server> - Disconnect from a server")
            return

        subcommand = parts[1].lower()

        if subcommand == "list":
            self._mcp_list_servers()
        elif subcommand == "connect" and len(parts) > 2:
            self._mcp_connect(parts[2])
        elif subcommand == "disconnect" and len(parts) > 2:
            self._mcp_disconnect(parts[2])
        elif subcommand == "tools":
            self._mcp_list_tools()
        elif subcommand == "resources":
            self._mcp_list_resources()
        elif subcommand == "prompts":
            self._mcp_list_prompts()
        elif subcommand == "prompt" and len(parts) > 2:
            args_str = " ".join(parts[3:]) if len(parts) > 3 else ""
            self._mcp_use_prompt(parts[2], args_str)
        else:
            self.console.print(f"[red]Invalid MCP command: {command}[/red]")
            self.console.print("[dim]Type '/mcp' for usage[/dim]")

    def _mcp_list_servers(self) -> None:
        """List MCP servers and their connection status."""
        servers = self.mcp_manager.list_servers()

        if not servers:
            self.console.print("[dim]No MCP servers configured[/dim]")
            return

        self.console.print("\n[bold]MCP Servers:[/bold]")
        for server in servers:
            status = "✅ Connected" if server["connected"] else "⚪ Disconnected"
            transport = server["transport"]
            self.console.print(f"  • {server['name']} ({transport}) - {status}")
        self.console.print()

    def _mcp_connect(self, server_name: str) -> None:
        """Connect to an MCP server."""
        try:
            self.mcp_manager.connect_server_sync(server_name)
            self.console.print(
                f"[green]✅ Connected to MCP server: {server_name}[/green]"
            )
        except Exception as e:
            self.console.print(f"[red]❌ Failed to connect: {e}[/red]")

    def _mcp_disconnect(self, server_name: str) -> None:
        """Disconnect from an MCP server."""
        try:
            self.mcp_manager.disconnect_server_sync(server_name)
            self.console.print(
                f"[yellow]🔌 Disconnected from MCP server: {server_name}[/yellow]"
            )
        except Exception as e:
            self.console.print(f"[red]❌ Failed to disconnect: {e}[/red]")

    def _mcp_list_tools(self) -> None:
        """List available MCP tools from all connected servers."""
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            self.console.print("[dim]No MCP servers connected[/dim]")
            return

        self.console.print("\n[bold]Available MCP Tools:[/bold]")
        for server in connected_servers:
            tools = self.mcp_manager.get_tools_sync(server["name"])
            if tools:
                self.console.print(f"\n  [bold]{server['name']}:[/bold]")
                for tool in tools:
                    self.console.print(
                        f"    • {tool['name']}: {tool.get('description', 'No description')}"
                    )
        self.console.print()

    def _mcp_list_resources(self) -> None:
        """List available MCP resources."""
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            self.console.print("[dim]No MCP servers connected[/dim]")
            return

        self.console.print("\n[bold]Available MCP Resources:[/bold]")
        for server in connected_servers:
            resources = self.mcp_manager.get_resources_sync(server["name"])
            if resources:
                self.console.print(f"\n  [bold]{server['name']}:[/bold]")
                for resource in resources:
                    self.console.print(
                        f"    • {resource['uri']}: {resource.get('description', 'No description')}"
                    )
        self.console.print()

    def _mcp_list_prompts(self) -> None:
        """List available MCP prompt templates."""
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        if not connected_servers:
            self.console.print("[dim]No MCP servers connected[/dim]")
            return

        self.console.print("\n[bold]Available MCP Prompts:[/bold]")
        for server in connected_servers:
            prompts = self.mcp_manager.get_prompts_sync(server["name"])
            if prompts:
                self.console.print(f"\n  [bold]{server['name']}:[/bold]")
                for prompt in prompts:
                    self.console.print(
                        f"    • {prompt['name']}: {prompt.get('description', 'No description')}"
                    )
        self.console.print()

    def _mcp_use_prompt(self, prompt_name: str, args_str: str) -> None:
        """Use an MCP prompt template."""
        # Find which server provides this prompt
        servers = self.mcp_manager.list_servers()
        connected_servers = [s for s in servers if s["connected"]]

        for server in connected_servers:
            prompts = self.mcp_manager.get_prompts_sync(server["name"])
            for prompt in prompts:
                if prompt["name"] == prompt_name:
                    # Parse arguments
                    args = {}
                    if args_str:
                        for arg in args_str.split():
                            if "=" in arg:
                                key, value = arg.split("=", 1)
                                args[key] = value

                    # Get the prompt
                    result = self.mcp_manager.get_prompt_sync(
                        server["name"], prompt_name, args
                    )
                    if result and "messages" in result:
                        for message in result["messages"]:
                            if message.get("role") == "user":
                                content = message.get("content")
                                if isinstance(content, str):
                                    self.console.print(
                                        Panel(content, title=f"Prompt: {prompt_name}")
                                    )
                    return

        self.console.print(f"[red]❌ Prompt not found: {prompt_name}[/red]")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            self.initialize()
        except Exception as exc:  # pragma: no cover - displayed to user
            self.console.print(f"[bold red]Failed to start chatbot: {exc}[/bold red]")
            raise

        history = FileHistory(self._history_path)
        while True:
            try:
                user_input = prompt(
                    "You > ",
                    history=history,
                    auto_suggest=AutoSuggestFromHistory(),
                )
            except KeyboardInterrupt:
                self.console.print("\n[dim]Exiting...[/dim]")
                break

            if not user_input:
                continue

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.startswith("/"):
                should_exit = self.handle_command(user_input)
                if should_exit:
                    break
                continue

            try:
                self._chat_once(user_input)
            except Exception as exc:  # pragma: no cover - displayed to user
                self.console.print(f"[bold red]Error: {exc}[/bold red]")

        if self.client:
            self.client.close()

        if self.mcp_manager:
            self.mcp_manager.cleanup_sync()


__all__ = ["ClaudeAgentChatbot"]
