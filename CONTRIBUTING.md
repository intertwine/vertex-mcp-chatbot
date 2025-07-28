# Contributing to Vertex MCP Chatbot

Thank you for your interest in contributing to the Vertex MCP Chatbot! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Issues

- Check if the issue already exists in the [issue tracker](https://github.com/intertwine/vertex-mcp-chatbot/issues)
- Use the issue templates when creating new issues
- Provide as much detail as possible, including:
  - Steps to reproduce
  - Expected behavior
  - Actual behavior
  - Environment details (OS, Python version, etc.)

### Submitting Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Set up your development environment**:
   ```bash
   # Install uv if you haven't already
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Clone your fork
   git clone https://github.com/intertwine/vertex-mcp-chatbot.git
   cd vertex-mcp-chatbot

   # Install dependencies
   uv sync --all-extras --dev

   # Install pre-commit hooks
   uv run pre-commit install
   ```

3. **Make your changes**:
   - Write clean, documented code
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting**:
   ```bash
   # Run all tests
   uv run pytest -xvs

   # Run black formatter
   uv run black .

   # Run example server tests
   uv run python scripts/run_example_tests.py
   ```

5. **Commit your changes**:
   - Use clear, descriptive commit messages
   - Reference issue numbers when applicable (e.g., "Fix #123: Add feature X")

6. **Push to your fork** and submit a pull request

### Development Guidelines

#### Code Style

- We use [Black](https://github.com/psf/black) for code formatting (automatically applied via pre-commit)
- We use [isort](https://github.com/PyCQA/isort) for import sorting (automatically applied via pre-commit)
- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write descriptive docstrings for all public functions and classes
- Pre-commit hooks will automatically format your code on commit

#### Testing

- All new features must include tests
- Maintain or increase code coverage
- Tests should be isolated and not depend on external services
- Use mocks for external dependencies

#### Documentation

- Update README.md for user-facing changes
- Update technical documentation in the docs/ directory
- Include docstrings for all public APIs
- Add examples for complex features

### MCP Server Development

If you're contributing an MCP server:

1. Place it in `examples/mcp-servers/`
2. Use the FastMCP framework when possible
3. Include comprehensive tests
4. Document all tools, resources, and prompts
5. Add security measures (input validation, path restrictions, etc.)
6. Update the examples README with usage instructions

### Areas for Contribution

- **MCP Servers**: Create new example servers or enhance existing ones
- **Transport Support**: Improve HTTP/SSE/WebSocket implementations
- **Documentation**: Improve guides, add tutorials, fix typos
- **Testing**: Increase test coverage, add edge case tests
- **Performance**: Optimize slow operations, reduce memory usage
- **Features**: Implement items from the "Future Enhancements" section

## Questions?

Feel free to open an issue for any questions about contributing!
