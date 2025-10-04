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
        self.client = ClaudeAgentClient(
            model_name=self.model_name,
            system_prompt=self.system_prompt,
            sdk_client=self._sdk_client,
            mcp_servers=servers,
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
        if command == "/quit":
            return True

        self.console.print(
            "[yellow]Unknown command. Type /help to see available commands.[/yellow]"
        )
        return False

    def _display_help(self) -> None:
        self.console.print(
            Panel(
                """[bold]Available commands[/bold]:
/help      Show this message
/history   Display the current chat history
/system    Update the system prompt for subsequent replies
/clear     Clear chat history and start a new Claude session
/quit      Exit the program""",
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


__all__ = ["ClaudeAgentChatbot"]
