# Implement MCP Client

This plan outlines detailed steps to modify the chatbot to enable it to act as an MCP client. Client configuration will be stored in an mcp_config.json file.

## Current Chatbot Overview

### Current features

- **Interactive CLI interface** with rich terminal UI using Rich library
- **Gemini model integration** via Google Vertex AI (supports gemini-2.5-flash, gemini-2.5-pro)
- **Markdown rendering** for AI responses with proper formatting
- **Scrollable content** for long responses with keyboard navigation (arrow keys, j/k, Home/End, q to exit)
- **Conversation history** persistence between sessions with `/history` command
- **Command system** with built-in commands:
  - `/help` - Show available commands and tips
  - `/clear` - Clear the chat history
  - `/history` - Display full conversation history
  - `/model` - Show current model information
  - `/prune` - Clear local command history
  - `/quit` or `/exit` - Exit the chatbot
- **Auto-suggestions** from command history using prompt_toolkit
- **Multi-line input** support with Shift+Enter
- **Error handling** for authentication, network, and API failures

### Current architecture

**Core Components:**
- `main.py` - Entry point with CLI argument parsing (--model flag)
- `src/config.py` - Configuration management with environment variable support
  - Default project: expel-engineering-prod
  - Default location: us-central1
  - Default model: gemini-2.5-flash
  - Max history length: 10 conversation turns
- `src/gemini_client.py` - Gemini/Vertex AI client wrapper
  - Uses google-genai library with vertexai=True
  - Manages chat sessions and message history
  - Application Default Credentials authentication
- `src/chatbot.py` - Interactive chatbot implementation
  - Rich console for UI rendering
  - prompt_toolkit for input handling
  - Scrollable view implementation for long content
  - Command processing and history management

**Dependencies:**
- google-genai>=1.27.0 (Vertex AI integration)
- python-dotenv>=1.1.1 (environment variables)
- rich>=14.1.0 (terminal UI)
- prompt-toolkit>=3.0.51 (interactive prompts)

**State Management:**
- Chat history stored in memory during session
- Command history persisted in `.chat/log.txt`
- No persistent conversation storage between sessions

### Current tests

**Test Infrastructure:**
- pytest-based test suite with 55+ tests
- Custom test runner (`run_tests.py`) with options for coverage, verbosity, unit/integration filtering
- Comprehensive mocking to avoid external API calls
- Test fixtures in `conftest.py` for reusable components

**Test Coverage:**
- `test_config.py` - Configuration management tests (6 tests)
  - Default values, environment variable handling
- `test_gemini_client.py` - Gemini API client tests (11 tests)
  - Initialization, chat sessions, message handling, error cases
- `test_chatbot.py` - Interactive chatbot tests (23 tests)
  - Commands, history, display formatting, input validation
- `test_main.py` - Main entry point tests (8 tests)
  - Argument parsing, exception handling, lifecycle management
- `test_scrollable_response.py` - Scrollable content tests
- `test_integration.py` - Full system integration tests
  - End-to-end workflows, component interactions

**Test Features:**
- No hanging tests (properly handles infinite loops)
- CI/CD ready configuration
- 80% minimum coverage requirement
- Separate unit and integration test markers

### Current documentation

**User Documentation:**
- Comprehensive README.md with:
  - Feature overview and prerequisites
  - Installation instructions (using uv package manager)
  - Usage examples and command reference
  - Scrollable content navigation guide
  - Project structure overview
  - Configuration options
  - Troubleshooting guide
  - Testing instructions

**Code Documentation:**
- Module-level docstrings in all Python files
- Function/method docstrings with parameter descriptions
- Inline comments for complex logic
- Type hints for function parameters (partial coverage)

## New MCP Client features

### New MCP Client architecture

### New MCP Client tests

### New documentation

## Needed changes

### New and updated tests

### New and updated code

### New and updated documentation



