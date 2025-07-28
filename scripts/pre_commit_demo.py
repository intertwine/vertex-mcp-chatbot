#!/usr/bin/env python3
"""Script to demonstrate pre-commit hooks."""

import sys
from pathlib import Path


def main():
    """Main function to show pre-commit in action."""
    print("Pre-commit hooks are now configured!")
    print("\nWhen you commit changes, the following hooks will run automatically:")
    print("1. trailing-whitespace - removes trailing whitespace")
    print("2. end-of-file-fixer - ensures files end with a newline")
    print("3. check-yaml/json/toml - validates configuration files")
    print("4. black - formats Python code")
    print("5. isort - sorts imports")
    print("6. flake8 - checks for style violations")
    print("\nTo run hooks manually: uv run pre-commit run --all-files")
    print("To skip hooks temporarily: git commit --no-verify")


if __name__ == "__main__":
    main()
