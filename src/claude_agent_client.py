"""Client wrapper around the Anthropic SDK for Claude via Vertex AI."""

from __future__ import annotations

import importlib
import logging
from typing import Any, Dict, Iterable, List, Optional

from .config import Config

LOGGER = logging.getLogger(__name__)


def _resolve_sdk_client_class():
    """Return the Anthropic client class, falling back to the local stub."""

    try:
        module = importlib.import_module("anthropic")
        return getattr(module, "Anthropic")
    except (ImportError, AttributeError):
        from .claude_sdk_fallback import ClaudeSDKClient

        return ClaudeSDKClient


class ClaudeAgentClient:
    """High level helper for chatting with Claude via Vertex AI using the Anthropic SDK."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        sdk_client=None,
        mcp_servers: Optional[Iterable[Dict[str, Any]]] = None,
        mcp_manager=None,
    ) -> None:
        self.model_name = model_name or Config.get_default_claude_model()
        self.system_prompt = system_prompt
        self._sdk_client = sdk_client or self._create_sdk_client()
        self._mcp_servers = list(mcp_servers or [])
        self._mcp_manager = mcp_manager
        self.history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # SDK helpers
    # ------------------------------------------------------------------
    def _create_sdk_client(self):
        cls = _resolve_sdk_client_class()
        init_kwargs = Config.get_claude_sdk_init_kwargs(self.model_name)

        # Remove parameters that Anthropic SDK doesn't accept
        init_kwargs.pop("default_model", None)

        try:
            return cls(**init_kwargs)
        except TypeError as exc:
            LOGGER.warning(
                "Failed to initialize Anthropic client with kwargs %s: %s",
                init_kwargs.keys(),
                exc,
            )
            # Try with minimal kwargs
            minimal_kwargs = {}
            if "api_key" in init_kwargs:
                minimal_kwargs["api_key"] = init_kwargs["api_key"]
            if "base_url" in init_kwargs:
                minimal_kwargs["base_url"] = init_kwargs["base_url"]
            if "default_headers" in init_kwargs:
                minimal_kwargs["default_headers"] = init_kwargs["default_headers"]
            elif "extra_headers" in init_kwargs:
                minimal_kwargs["default_headers"] = init_kwargs["extra_headers"]

            return cls(**minimal_kwargs)

    def ensure_session(self, system_instruction: Optional[str] = None) -> None:
        """Update system prompt if changed."""
        if system_instruction is not None and system_instruction != self.system_prompt:
            self.system_prompt = system_instruction

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------
    def send_message(
        self,
        message: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Send a message to Claude and get a response.

        Uses the Anthropic Messages API, maintaining conversation history.
        Supports tool calling via MCP if manager is provided.
        """
        self.ensure_session(system_instruction)

        # Add the new user message to history
        self.history.append({"role": "user", "content": message})

        # Check if we're using the fallback stub
        if hasattr(self._sdk_client, "sessions"):
            # Using fallback stub
            return self._send_with_fallback(message)

        # Using real Anthropic SDK - may need multiple turns for tool use
        return self._chat_with_tools()

    def _chat_with_tools(self) -> str:
        """Handle conversation with tool calling support."""
        max_turns = 10  # Prevent infinite loops
        turn_count = 0

        while turn_count < max_turns:
            turn_count += 1

            # Build messages list from history
            messages = [
                {"role": msg["role"], "content": msg["content"]} for msg in self.history
            ]

            # Prepare API call parameters
            params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": 4096,
            }

            if self.system_prompt:
                params["system"] = self.system_prompt

            # Add MCP tools if available
            if self._mcp_manager:
                tools = self._get_mcp_tools()
                if tools:
                    params["tools"] = tools

            try:
                # Call the Messages API
                response = self._sdk_client.messages.create(**params)

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Handle tool calls and continue conversation
                    tool_results = self._handle_tool_use(response)
                    if tool_results is None:
                        # No tools were executed, return the response
                        break
                    # Continue loop to send tool results back to Claude
                    continue
                else:
                    # Normal response, extract and return text
                    text = self._extract_text_from_message(response)
                    self.history.append(
                        {"role": "assistant", "content": response.content}
                    )
                    return text

            except Exception as exc:
                LOGGER.error("Error calling Claude API: %s", exc)
                raise

        # If we hit max turns, return the last response
        return self._extract_text_from_message(response)

    def _send_with_fallback(self, message: str) -> str:
        """Send message using fallback stub."""
        session_id = "fallback-session"
        response = self._sdk_client.sessions.send_message(
            session_id=session_id, content=message
        )
        text = getattr(response, "output_text", str(response))
        self.history.append({"role": "assistant", "content": text})
        return text

    def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """Get all available MCP tools in Anthropic SDK format."""
        if not self._mcp_manager:
            return []

        try:
            # Get tools from all connected servers
            mcp_tools = self._mcp_manager.get_tools_sync()

            # Convert to Anthropic tool format
            anthropic_tools = []
            for tool in mcp_tools:
                anthropic_tool = {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                }

                # Add input schema if available
                if "inputSchema" in tool:
                    anthropic_tool["input_schema"] = tool["inputSchema"]

                anthropic_tools.append(anthropic_tool)

            return anthropic_tools
        except Exception as exc:
            LOGGER.warning("Failed to get MCP tools: %s", exc)
            return []

    def _handle_tool_use(self, response: Any) -> Optional[List[Dict[str, Any]]]:
        """Handle tool use requests from Claude."""
        if not self._mcp_manager:
            return None

        # Add assistant response with tool use to history
        self.history.append({"role": "assistant", "content": response.content})

        # Extract tool use blocks and execute them
        tool_results = []
        for block in response.content:
            if getattr(block, "type", "") == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_use_id = block.id

                try:
                    # Find which server has this tool
                    server_name = self._mcp_manager.find_best_server_for_tool_sync(
                        tool_name
                    )
                    if not server_name:
                        raise Exception(f"No server found with tool: {tool_name}")

                    # Call the tool
                    result = self._mcp_manager.call_tool_sync(
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments=tool_input,
                    )

                    # Extract content from MCP result
                    content_text = ""
                    if hasattr(result, "content"):
                        for content_item in result.content:
                            if hasattr(content_item, "text"):
                                content_text += content_item.text
                    else:
                        content_text = str(result)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": content_text,
                        }
                    )
                except Exception as exc:
                    LOGGER.error("Tool execution failed for %s: %s", tool_name, exc)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "is_error": True,
                            "content": f"Error: {str(exc)}",
                        }
                    )

        if tool_results:
            # Add tool results to history as a user message
            self.history.append({"role": "user", "content": tool_results})
            return tool_results

        return None

    def _extract_text_from_message(self, response: Any) -> str:
        """Extract text from Anthropic Messages API response."""
        content = getattr(response, "content", None)
        if isinstance(content, list):
            texts: List[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                else:
                    if getattr(block, "type", "") == "text":
                        texts.append(getattr(block, "text", ""))
            if texts:
                return "\n".join(texts)

        return str(response)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------
    def reset_session(self, system_instruction: Optional[str] = None) -> None:
        """Clear conversation history and optionally update system prompt."""
        self.system_prompt = system_instruction or self.system_prompt
        self.history.clear()

    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the current conversation history."""
        return list(self.history)

    def close(self) -> None:
        """Close the SDK client if it has a close method."""
        close_fn = getattr(self._sdk_client, "close", None)
        if callable(close_fn):
            close_fn()


__all__ = ["ClaudeAgentClient", "_resolve_sdk_client_class"]
