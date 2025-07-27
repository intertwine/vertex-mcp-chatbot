# Expel Vertex AI Chatbot

An interactive command-line chatbot powered by Google's Gemini LLM via Vertex AI. This application provides a rich terminal interface for conversing with Gemini models, complete with markdown rendering, conversation history, and various utility commands.

## Features

- 🤖 **Interactive Chat Interface**: Clean, intuitive terminal UI with rich formatting
- 📝 **Markdown Support**: Responses are rendered with proper markdown formatting
- 📜 **Scrollable Content**: Long responses and conversation history automatically become scrollable with intuitive navigation controls
- 💾 **Persistent History**: Conversation history saved between sessions
- 🎨 **Rich Terminal UI**: Colorful, well-formatted output using Rich library
- 🔧 **Multiple Models**: Support for different Gemini models (flash, pro)
- 📋 **Command System**: Built-in commands for managing your chat session
- 🔌 **MCP Tool Integration**: When MCP servers are connected, their tools are automatically available to Gemini during conversations

> **Note**: Model Context Protocol (MCP) integration is in active development. Currently supports:
> - ✅ Tool execution during conversations
> - ✅ Resource reading and embedding
> - ✅ Prompt template usage
> - ✅ HTTP/SSE transport (in addition to stdio)
> - 🚧 Multi-server coordination (coming soon)

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager installed
- Access to Google Cloud Vertex AI with Gemini models
- Google Cloud CLI (`gcloud`) installed and authenticated

## Installation

1. Clone this repository:
```bash
git clone https://github.com/expel-io/vertex-ai-chatbot.git
cd vertex-ai-chatbot
```

2. Install dependencies with uv (creates virtual environment automatically):
```bash
uv sync
```

3. (Optional) Activate the virtual environment manually if needed:
```bash
source .venv/bin/activate
```
> **Note**: When using `uv run`, the virtual environment is automatically activated, so manual activation is typically not required.

4. Authenticate with Google Cloud (Application Default Credentials):
```bash
gcloud auth application-default login
```

5. (Optional) Set up environment variables:
```bash
cp .env.example .env
```

You can optionally edit `.env` to override default project settings:
```bash
# GOOGLE_CLOUD_PROJECT='expel-engineering-prod'
# GOOGLE_CLOUD_LOCATION='us-central1'
```

## Usage

### Basic Usage

Start the chatbot with the default model (gemini-2.5-flash):
```bash
uv run main.py
```

### Using Different Models

Start with a different model:
```bash
uv run main.py --model gemini-2.5-pro
```

### Scrollable Content

When responses or conversation history are too long for your terminal, the chatbot automatically switches to a scrollable view:

**Navigation Controls:**
- **↑/↓** or **j/k** - Scroll up/down line by line
- **Home/g** - Jump to the top of the content
- **End/G** - Jump to the bottom of the content
- **q/Esc** - Exit scrollable view and return to chat

**Features:**
- Automatically detects when content exceeds terminal height
- Works for both LLM responses and `/history` command
- Preserves all markdown formatting and styling
- Short content displays normally (no change in experience)

### Available Commands

While chatting, you can use these commands:

- `/help` - Show available commands and tips
- `/clear` - Clear the chat history and start fresh
- `/history` - Display the full conversation history
- `/model` - Show which Gemini model you're using
- `/prune` - Clear local command history (with confirmation)
- `/quit` or `/exit` - Exit the chatbot

**MCP Commands** (when MCP is available):
- `/mcp connect <server>` - Connect to an MCP server from your config
- `/mcp list` - Show configured servers and their connection status
- `/mcp disconnect <server>` - Disconnect from an MCP server
- `/mcp resources` - Show available resources from all connected servers
- `/mcp prompts` - List available prompt templates from all connected servers
- `/mcp prompt <name>` - Use a specific prompt template

### MCP Tool Integration

When MCP servers are connected, their tools become automatically available during conversations. Gemini will intelligently use these tools when appropriate to help answer your questions or perform tasks. You don't need to use special syntax - just chat naturally and Gemini will:

- Recognize when a tool would be helpful
- Execute the appropriate tool with the right parameters
- Include the tool results in its response

For example, if you have a weather MCP server connected and ask "What's the weather like?", Gemini will automatically use the weather tool to get current conditions.

### MCP Resource Integration

MCP resources are automatically read when you reference them by URI in your messages. This allows you to seamlessly include external data in your conversations:

- **Automatic Detection**: When you include a resource URI in your message, it's automatically detected
- **Transparent Reading**: The resource content is fetched and included in the context sent to Gemini
- **Multiple Resources**: You can reference multiple resources in a single message
- **Standard URI Format**: Use standard URIs like `file:///path/to/data.json` or `http://example.com/api/data`

**Example:**
```
You> Can you analyze the data in file:///home/user/sales_report.csv?

[The chatbot automatically reads the CSV file and includes its content in the prompt to Gemini, 
who can then analyze and discuss the data]
```

### MCP Prompt Templates

MCP servers can provide prompt templates that help structure interactions for specific tasks. These templates make it easy to perform complex operations with consistent formatting:

- **List Templates**: Use `/mcp prompts` to see all available templates
- **Use a Template**: Use `/mcp prompt <template_name>` to apply a template
- **Interactive Arguments**: The chatbot will prompt you for any required template arguments
- **Seamless Processing**: Filled templates are sent directly to Gemini for processing

**Example:**
```
You> /mcp prompts
Available prompts from code-analyzer:
  - analyze_function: Analyze a function for complexity and suggest improvements
  - review_pr: Review pull request changes and provide feedback
  - explain_code: Explain how a piece of code works in simple terms

You> /mcp prompt analyze_function
Enter value for 'function_name': calculateTotalPrice
Enter value for 'context': This function processes shopping cart items

[The template is filled with your values and sent to Gemini, who provides
a detailed analysis of the function based on the structured prompt]
```

### Example Session

```
🚀 Initializing Gemini Chatbot...
✅ Vertex AI initialized successfully
✅ Model 'gemini-2.5-flash' ready
✅ Chatbot ready!
Type '/help' for commands or '/quit' to exit

You> What is machine learning?

╭─ Gemini ─────────────────────────────────────────────╮
│                                                      │
│  Machine learning (ML) is a type of artificial       │
│  intelligence (AI) that allows software              │
│  applications to become more accurate in             │
│  predicting outcomes without being explicitly        │
│  programmed to do so...                              │
│                                                      │
╰──────────────────────────────────────────────────────╯

You> /model
Current model: gemini-2.5-flash

You> /quit

👋 Goodbye!
```

## Project Structure

```
vertex-ai-chatbot/
├── main.py              # Entry point
├── pyproject.toml       # Python project configuration and dependencies
├── pytest.ini          # Pytest configuration
├── run_tests.py         # Custom test runner script
├── .env.example        # Example environment file
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── src/
│   ├── __init__.py     # Package init
│   ├── config.py       # Configuration management
│   ├── gemini_client.py # Gemini/Vertex AI client wrapper
│   └── chatbot.py      # Interactive chatbot implementation
└── tests/
    ├── __init__.py     # Test package init
    ├── conftest.py     # Pytest fixtures and configuration
    ├── test_config.py  # Configuration tests
    ├── test_gemini_client.py # Gemini client tests
    ├── test_chatbot.py # Chatbot functionality tests
    ├── test_main.py    # Main entry point tests
    └── test_integration.py # Integration tests
```

## Configuration

The application uses the following configuration (can be modified in `src/config.py`):

- **Project ID**: `expel-engineering-prod`
- **Location**: `us-central1`
- **Default Model**: `gemini-2.5-flash`
- **Max History Length**: 10 conversation turns

## Troubleshooting

### "Failed to initialize Google Gen AI client"

Make sure you've:
1. Authenticated with Google Cloud: `gcloud auth application-default login`
2. Your account has access to the specified Google Cloud project
3. Vertex AI API is enabled in your project
4. Your account has the necessary permissions (Vertex AI User role)

### "Authentication Error"

Check that:
1. You've run `gcloud auth application-default login` successfully
2. The project ID in the config matches your GCP project
3. Gemini models are available in your specified region
4. Your Google Cloud account has billing enabled

### Connection Issues

Ensure:
1. You have an active internet connection
2. No firewall/proxy blocking access to Google Cloud
3. Your service account is active and not expired

## Testing

This project includes a comprehensive test suite with 55+ tests covering all functionality.

### Running Tests

**Quick test run:**
```bash
# Install dev dependencies
uv sync --extra dev

# Run all tests
uv run pytest tests/ -v
```

**Using the custom test runner:**
```bash
# Run all tests
uv run python run_tests.py

# Run with verbose output
uv run python run_tests.py --verbose

# Run with coverage report
uv run python run_tests.py --coverage

# Run only unit tests
uv run python run_tests.py --unit

# Run only integration tests
uv run python run_tests.py --integration

# Run specific test files
uv run python run_tests.py tests/test_config.py tests/test_main.py
```

### Test Categories

**Unit Tests:**
- `test_config.py` - Configuration management (6 tests)
- `test_gemini_client.py` - Gemini API client functionality (11 tests)
- `test_chatbot.py` - Interactive chatbot features (23 tests)
- `test_main.py` - Main entry point and CLI (8 tests)

**Integration Tests:**
- `test_integration.py` - Full system integration scenarios

### Test Coverage

The test suite covers:
- ✅ **Configuration**: Environment variables, defaults, static methods
- ✅ **API Client**: Initialization, chat sessions, message handling, error cases
- ✅ **Chatbot UI**: Commands, history, display formatting, input validation
- ✅ **CLI Interface**: Argument parsing, exception handling, lifecycle management
- ✅ **Integration**: End-to-end workflows, component interactions
- ✅ **Error Handling**: Network failures, API errors, user interrupts

### Test Features

- **Comprehensive mocking** - No external API calls during testing
- **No hanging tests** - Properly handles infinite loops and user input
- **Fixtures and utilities** - Reusable test components in `conftest.py`
- **Multiple test runners** - Standard pytest and custom runner with options
- **CI/CD ready** - Configured for automated testing pipelines

## Development

To extend or modify the chatbot:

### Architecture
1. **`GeminiClient`** (`src/gemini_client.py`) - Handles all Vertex AI interactions
2. **`GeminiChatbot`** (`src/chatbot.py`) - Manages UI and user interaction
3. **`Config`** (`src/config.py`) - Centralized configuration management
4. **`main.py`** - Entry point and CLI argument handling

### Adding New Features
1. **New Commands**: Extend the `process_command` method in `GeminiChatbot`
2. **Model Parameters**: Modify settings in the `Config` class
3. **API Features**: Add methods to `GeminiClient` class
4. **UI Enhancements**: Update display methods in `GeminiChatbot`

### Development Workflow
```bash
# Install dev dependencies
uv sync --extra dev

# Run tests during development
uv run pytest tests/ -v --tb=short

# Run tests with coverage
uv run python run_tests.py --coverage

# Format code
uv run black src/ tests/
uv run isort src/ tests/

# Lint code
uv run flake8 src/ tests/
```

### Writing Tests
When adding new functionality:
1. Add unit tests for individual methods/functions
2. Add integration tests for feature workflows
3. Use the fixtures in `tests/conftest.py` for common mocking
4. Follow the existing test patterns and naming conventions
5. Ensure tests don't make external API calls

## Security Notes

- Never commit your `.env` file or service account credentials
- The `.gitignore` file is configured to exclude sensitive files
- Store your service account JSON securely
- Consider using Google Cloud Secret Manager for production deployments

## License

This project is for internal Expel use. Please follow company guidelines for code usage and distribution.
