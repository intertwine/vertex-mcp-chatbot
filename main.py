#!/usr/bin/env python3
"""Main entry point for the Vertex MCP chatbot CLI."""

import argparse
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

    args = parser.parse_args()

    try:
        if args.provider == "gemini":
            chatbot = GeminiChatbot(model_name=args.model)
        else:
            chatbot = ClaudeAgentChatbot(model_name=args.model)
        chatbot.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
