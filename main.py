#!/usr/bin/env python3
"""Main entry point for the Gemini chatbot."""

import argparse
import sys

from src.chatbot import GeminiChatbot


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Interactive Gemini chatbot powered by Vertex AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Start with default model (gemini-2.5-flash)
  %(prog)s --model gemini-1.5-pro  # Use Gemini Pro model
        """,
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Gemini model to use (default: gemini-2.5-flash)",
    )

    args = parser.parse_args()

    try:
        chatbot = GeminiChatbot(model_name=args.model)
        chatbot.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
