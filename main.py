#!/usr/bin/env python3
"""Main entry point for the Vertex MCP chatbot CLI."""

import argparse
import logging
import sys

from src.chatbot import GeminiChatbot
from src.claude_agent_chatbot import ClaudeAgentChatbot


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Interactive Claude or Gemini REPL powered by Vertex AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                             # Start Claude Agent with default model (claude-4.5-sonnet)
  %(prog)s --model claude-4-haiku       # Override the Claude model
  %(prog)s --provider gemini            # Launch the legacy Gemini REPL
  %(prog)s --quiet-mcp                  # Start with suppressed MCP server logging
  %(prog)s --log-level DEBUG            # Show detailed MCP debug information
        """,
    )

    parser.add_argument(
        "--provider",
        choices=("claude", "gemini"),
        default="claude",
        help=(
            "Model provider to use: 'claude' for the Claude Agent SDK (default) "
            "or 'gemini' for the legacy Gemini chatbot"
        ),
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=(
            "Model identifier to use. Defaults to claude-4.5-sonnet when using "
            "the Claude provider or the Gemini client default when using Gemini"
        ),
    )

    parser.add_argument(
        "--quiet-mcp",
        action="store_true",
        help="Suppress MCP server info logging during tool calls",
    )

    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="WARNING",
        help="Set the logging level for MCP operations (default: WARNING)",
    )

    args = parser.parse_args()

    # Configure logging based on arguments
    if args.quiet_mcp:
        # Suppress all MCP-related logging
        logging.getLogger("src.mcp_manager").setLevel(logging.ERROR)
        logging.getLogger("src.claude_agent_client").setLevel(logging.ERROR)
        logging.getLogger("src.config").setLevel(logging.ERROR)
        logging.getLogger("src.chatbot").setLevel(logging.ERROR)
    else:
        # Set the requested log level for MCP modules
        log_level = getattr(logging, args.log_level)
        logging.getLogger("src.mcp_manager").setLevel(log_level)
        logging.getLogger("src.claude_agent_client").setLevel(log_level)
        logging.getLogger("src.config").setLevel(log_level)
        logging.getLogger("src.chatbot").setLevel(log_level)

    try:
        if args.provider == "gemini":
            chatbot = GeminiChatbot(model_name=args.model, quiet_mcp=args.quiet_mcp)
        else:
            chatbot = ClaudeAgentChatbot(
                model_name=args.model, quiet_mcp=args.quiet_mcp
            )
        chatbot.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
