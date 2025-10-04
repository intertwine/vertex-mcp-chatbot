# Vertex MCP Chatbot

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org)
[![MCP](https://img.shields.io/badge/MCP-blue.svg)](https://modelcontextprotocol.io)
[![Python SDK](https://img.shields.io/badge/Python%20SDK-green.svg)](https://github.com/modelcontextprotocol/python-sdk)
[![Specification](https://img.shields.io/badge/specification-gray.svg)](https://spec.modelcontextprotocol.io/specification/)
[![Documentation](https://img.shields.io/badge/documentation-purple.svg)](https://modelcontextprotocol.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An interactive command-line chatbot powered by Anthropic's Claude via Google Cloud Vertex AI. The terminal experience is backed by the Claude Agent SDK so you inherit native MCP (Model Context Protocol) tool handling, structured responses, and stateful sessions out of the box. Gemini utilities and helpers remain available for experimentation—launch them with a single flag—but the primary REPL now speaks directly to Claude 4.5 Sonnet by default.

## Features

- 🤖 **Interactive Chat Interface**: Clean, intuitive terminal UI with rich formatting
- 🧠 **Claude Agent SDK**: Launches a full Claude agent with MCP servers, session history, and tool orchestration managed by Anthropic's runtime
- 📝 **Markdown Support**: Responses are rendered with proper markdown formatting
- 📜 **Scrollable Content**: Long responses and conversation history automatically become scrollable with intuitive navigation controls
- 💾 **Persistent History**: Conversation history saved between sessions on disk
- 🎨 **Rich Terminal UI**: Colorful, well-formatted output using Rich library
- 🔧 **Provider & Model Selection**: Choose between the Claude Agent SDK or the legacy Gemini REPL and override individual model identifiers with simple CLI flags
- 🔌 **MCP Integration**: Claude's built-in MCP support is automatically wired up using your local `mcp_config.json`

### MCP Features

The chatbot includes comprehensive MCP (Model Context Protocol) support:

- ✅ **Tool Execution**: Claude automatically uses MCP tools during conversations
- ✅ **Resource Access**: Read files, APIs, and other resources via URIs
- ✅ **Prompt Templates**: Use pre-defined templates for common tasks
- ✅ **Multiple Transports**: stdio, HTTP, and SSE protocols supported
- ✅ **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- ✅ **Authentication**: OAuth 2.0, Basic Auth, and custom headers
- ✅ **Reliability**: Automatic retry with exponential backoff
- ✅ **Priority System**: Smart conflict resolution when servers offer similar tools

## Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) package manager installed
- Access to Google Cloud Vertex AI with Anthropic Claude enabled (MCP-capable regions)
- Google Cloud CLI (`gcloud`) installed and authenticated

## Installation

1. Clone this repository:
```bash
git clone https://github.com/intertwine/vertex-mcp-chatbot.git
cd vertex-mcp-chatbot
```

2. Install dependencies with uv (creates virtual environment automatically):
```bash
uv sync
```

3. (OPTIONAL) Activate the virtual environment manually:
```bash
source .venv/bin/activate
```
> **Note**: When using `uv run`, the virtual environment is automatically activated, so manual activation is typically not required.

4. Authenticate with Google Cloud (Application Default Credentials):
```bash
gcloud auth application-default login
```

5. (REQUIRED) Set up environment variables:
```bash
cp .env.example .env
```

You must edit `.env` to override default project settings:
```bash
GOOGLE_CLOUD_PROJECT='your-gcp-project-id'
GOOGLE_CLOUD_LOCATION='us-east1'
```

## Usage

### Basic Usage

Start the chatbot with the default model (`claude-4.5-sonnet`):
```bash
uv run main.py
```

### Using Different Models

Start with a different Claude model:
```bash
uv run main.py --model claude-4-haiku
```

### Switching between Claude and Gemini

The Claude Agent SDK currently supports only Anthropic models—Gemini models cannot be loaded through the SDK even on Vertex AI. If you need to chat with Gemini, switch back to the legacy Gemini REPL using the `--provider` flag:

```bash
uv run main.py --provider gemini
```

You can still supply a `--model` override, which is forwarded to the Gemini client. Omitting `--provider` keeps the default Claude 4.5 Sonnet agent experience.

### Configuring Claude via Vertex AI

The CLI automatically attempts to run Claude through Google Cloud Vertex AI using Application Default Credentials. To customise the behaviour, set any of the following environment variables before launching the REPL (they can be stored in `.env`):

- `CLAUDE_VERTEX_ENABLED` – set to `false` to fall back to the public Anthropic API (requires `ANTHROPIC_API_KEY`)
- `CLAUDE_VERTEX_PROJECT` – override the GCP project used for billing (`GOOGLE_CLOUD_PROJECT` is used otherwise)
- `CLAUDE_VERTEX_LOCATION` – override the Vertex region (defaults to `GOOGLE_CLOUD_LOCATION` or `us-east1`)
- `CLAUDE_VERTEX_BASE_URL` – fully override the Vertex endpoint if you need to point at a proxy
- `CLAUDE_MODEL` – override the default Claude model name (`claude-4.5-sonnet`)
- `CLAUDE_API_VERSION` – override the Anthropic API version header sent to the SDK

See [docs/claude-agent.md](docs/claude-agent.md) for an end-to-end walkthrough that covers authentication, MCP configuration, and troubleshooting tips when connecting Claude through Vertex AI, plus guidance on when to prefer the legacy Gemini provider.

### MCP Configuration

To use MCP features, create an `mcp_config.json` file in the project root. See the [MCP User Guide](docs/mcp-guide.md) for detailed configuration instructions and examples.

### Scrollable Content

When responses or content are too long for your terminal, the chatbot automatically switches to a scrollable view:

**Navigation Controls:**
- **↑/↓** or **j/k** - Scroll up/down line by line
- **Home/g** - Jump to the top of the content
- **End/G** - Jump to the bottom of the content
- **q/Esc** - Exit scrollable view and return to chat

**Features:**
- Automatically detects when content exceeds terminal height
- Works for:
  - LLM responses
  - `/history` command
  - `/mcp tools` listings
  - `/mcp resources` listings
  - `/mcp prompts` listings
- Preserves all markdown formatting and styling
- Short content displays normally (no change in experience)

### Available Commands

While chatting, you can use these commands:

- `/help` - Show available commands and tips
- `/clear` - Clear the chat history and start fresh (resets the Claude session)
- `/history` - Display the full conversation history with markdown rendering
- `/system <prompt>` - Update the system instruction and restart the Claude agent
- `/quit` - Exit the chatbot

**MCP Commands** (when MCP is available):
- `/mcp connect <server>` - Connect to an MCP server from your config
- `/mcp list` - Show configured servers and their connection status
- `/mcp disconnect <server>` - Disconnect from an MCP server
- `/mcp tools` - Show available tools from all connected servers
- `/mcp resources` - Show available resources from all connected servers
- `/mcp prompts` - List available prompt templates from all connected servers
- `/mcp prompt <name>` - Use a specific prompt template

### MCP Tool Integration

When MCP servers are connected, their tools become automatically available during conversations. Claude will intelligently use these tools when appropriate to help answer your questions or perform tasks. You don't need to use special syntax - just chat naturally and Claude will:

- Recognize when a tool would be helpful
- Execute the appropriate tool with the right parameters
- Include the tool results in its response

For example, if you have a weather MCP server connected and ask "What's the weather like?", Claude will automatically use the weather tool to get current conditions.

### MCP Resource Integration

MCP resources are automatically read when you reference them by URI in your messages. This allows you to seamlessly include external data in your conversations with Claude:

- **Automatic Detection**: When you include a resource URI in your message, it's automatically detected
- **Transparent Reading**: The resource content is fetched and included in the context sent to Claude
- **Multiple Resources**: You can reference multiple resources in a single message
- **Standard URI Format**: Use standard URIs like `file:///path/to/data.json` or `http://example.com/api/data`

**Example:**
```
You> Can you analyze the data in file:///home/user/sales_report.csv?

[The chatbot automatically reads the CSV file and includes its content in the prompt to Claude,
who can then analyze and discuss the data]
```

### MCP Prompt Templates

MCP servers can provide prompt templates that help structure interactions for specific tasks. These templates make it easy to perform complex operations with consistent formatting:

- **List Templates**: Use `/mcp prompts` to see all available templates
- **Use a Template**: Use `/mcp prompt <template_name>` to apply a template
- **Interactive Arguments**: The chatbot will prompt you for any required template arguments
- **Seamless Processing**: Filled templates are sent directly to Claude for processing

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

[The template is filled with your values and sent to Claude, who provides
a detailed analysis of the function based on the structured prompt]
```

### Example Session

```
🚀 Starting Claude Agent REPL...
✅ Ready!

You> What is machine learning?

╭─ Claude ─────────────────────────────────────────────╮
│                                                      │
│  Machine learning (ML) is a branch of artificial     │
│  intelligence focused on building systems that can   │
│  learn from data and improve their performance over  │
│  time without being explicitly programmed for every  │
│  scenario...                                         │
│                                                      │
╰──────────────────────────────────────────────────────╯

You> /system You are a patient tutor for high-school students.
System prompt updated.

You> Explain overfitting in one paragraph.

╭─ Claude ─────────────────────────────────────────────╮
│                                                      │
│  Overfitting happens when a model memorises the      │
│  training data instead of learning the underlying    │
│  patterns, so it performs well on the data it has    │
│  seen but poorly on new examples. A simple way to    │
│  picture it is a student who only studies past exam  │
│  answers: they may ace the practice questions yet    │
│  struggle when the real test words things slightly   │
│  differently.                                        │
│                                                      │
╰──────────────────────────────────────────────────────╯

You> /quit

👋 Goodbye!
```

## MCP Configuration

### Basic Configuration

Create an `mcp_config.json` file in the project root:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "transport": "stdio",
      "command": ["python", "examples/mcp-servers/filesystem_server.py"]
    },
    {
      "name": "weather-api",
      "transport": "http",
      "url": "http://localhost:8080/mcp",
      "auth": {
        "type": "basic",
        "username": "user",
        "password": "pass"
      }
    }
  ]
}
```

### Environment Variables

The MCP configuration supports environment variable substitution using `${VAR_NAME}` syntax. Variables are automatically loaded from your `.env` file:

```bash
# .env file
API_KEY=your-secret-key
OAUTH_CLIENT_SECRET=your-oauth-secret
```

```json
{
  "servers": [
    {
      "name": "api-server",
      "transport": "http",
      "url": "https://api.example.com",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  ]
}
```

You can also provide default values with `${VAR_NAME:-default}` syntax.

### Advanced Configuration Options

#### OAuth 2.0 Authentication

```json
{
  "name": "github-api",
  "transport": "http",
  "url": "https://api.github.com/mcp",
  "auth": {
    "type": "oauth",
    "authorization_url": "https://github.com/login/oauth/authorize",
    "token_url": "https://github.com/login/oauth/access_token",
    "client_id": "your-client-id",
    "client_secret": "${OAUTH_CLIENT_SECRET}",
    "scope": "repo read:user",
    "redirect_uri": "http://localhost:8080/callback"
  }
}
```

#### Connection Retry Configuration

```json
{
  "name": "flaky-server",
  "transport": "stdio",
  "command": ["node", "server.js"],
  "retry": {
    "max_attempts": 5,
    "initial_delay": 1.0,
    "max_delay": 30.0,
    "exponential_base": 2.0,
    "jitter": true
  }
}
```

#### Server Priority

When multiple servers offer similar tools, use priority to control which server is preferred:

```json
{
  "servers": [
    {
      "name": "primary-calc",
      "transport": "stdio",
      "command": ["python", "calc_server.py"],
      "priority": 1
    },
    {
      "name": "backup-calc",
      "transport": "http",
      "url": "http://backup.example.com/mcp",
      "priority": 2
    }
  ]
}
```

### Example MCP Servers

The project includes example MCP servers in `examples/mcp-servers/`:

- **filesystem_server.py**: File operations (list, read, write)
- **weather_server.py**: Weather data and forecasts

See [examples/README.md](examples/README.md) for detailed setup instructions.

## Project Structure

```
vertex-mcp-chatbot/
├── main.py              # Entry point
├── pyproject.toml       # Python project configuration and dependencies
├── pytest.ini          # Pytest configuration
├── scripts/
│   ├── run_tests.py         # Custom test runner script
│   └── run_example_tests.py # Example server test runner
├── .env.example        # Example environment file
├── .gitignore          # Git ignore rules
├── README.md           # This file
├── mcp_config.json.example # Example MCP server configuration
├── docs/
│   ├── claude-agent.md # Claude Agent SDK + Vertex AI walkthrough
│   └── mcp-guide.md    # Comprehensive MCP user guide
├── src/
│   ├── __init__.py     # Package init
│   ├── claude_agent_chatbot.py # Claude Agent REPL (default CLI)
│   ├── claude_agent_client.py  # Claude SDK helper / session manager
│   ├── claude_sdk_fallback.py  # Local stub used in tests when SDK is unavailable
│   ├── config.py       # Configuration management for Claude + Gemini helpers
│   ├── gemini_client.py # Legacy Gemini/Vertex AI client wrapper (still used in tests)
│   ├── chatbot.py      # Legacy Gemini chatbot implementation
│   ├── mcp_config.py   # MCP configuration handling
│   └── mcp_manager.py  # MCP client management
└── tests/
    ├── __init__.py     # Test package init
    ├── conftest.py     # Pytest fixtures and configuration
    ├── test_config.py  # Configuration tests
    ├── test_gemini_client.py # Gemini client tests
    ├── test_chatbot.py # Legacy Gemini chatbot functionality tests
    ├── test_claude_agent_chatbot.py # Claude REPL behaviour
    ├── test_claude_agent_client.py # Claude client helper tests
    ├── test_main.py    # Main entry point tests
    ├── test_integration.py # Integration tests
    ├── test_mcp_config.py # MCP configuration tests
    ├── test_mcp_manager.py # MCP manager tests
    ├── test_mcp_http_transport.py # HTTP/SSE transport tests
    ├── test_mcp_multi_server.py # Multi-server coordination tests
    ├── test_mcp_oauth.py # OAuth authentication tests
    └── test_mcp_retry.py # Connection retry tests
```

## Configuration

The application uses the following configuration (can be modified in `src/config.py`):

- **Project ID**: `your-gcp-project-id` (override in `.env` via `GOOGLE_CLOUD_PROJECT`)
- **Location**: `your-gcp-location` (override in `.env` via `GOOGLE_CLOUD_LOCATION`)
- **Default Claude Model**: `claude-4.5-sonnet` (change via `CLAUDE_MODEL`)
- **Anthropic API Version**: `2025-02-19` (set `CLAUDE_API_VERSION` to override)
- **Max History Length**: 10 conversation turns

## Troubleshooting

### "Failed to start Claude Agent REPL"

Make sure you've:
1. Authenticated with Google Cloud: `gcloud auth application-default login`
2. Enabled the Vertex AI API and Anthropic publisher access for your project/region
3. Granted the `Vertex AI User` role to the identity running the CLI
4. Installed dependencies (`uv sync` or `pip install -e .`) so `google-auth` is available

### "Unable to refresh Google credentials"

Check that:
1. ADC credentials are active (`gcloud auth application-default login` or service account JSON)
2. The `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` values match your deployment
3. The executing user/service account has billing enabled for the project
4. You are targeting a region that exposes Claude through Vertex AI

### Falling back to the public Anthropic API

If Vertex access is unavailable you can still run the REPL by setting `CLAUDE_VERTEX_ENABLED=false` and exporting `ANTHROPIC_API_KEY`. The helper automatically reconfigures the Claude SDK to use the public endpoint and keeps MCP tooling enabled.

## Testing

This project includes a comprehensive test suite with 190+ tests covering all functionality, including example MCP servers.

### Running Tests

**Quick test run:**
```bash
# Install dev dependencies (includes pytest-cov for coverage)
uv sync --extra dev

# Run all tests (including example servers)
uv run pytest tests/ -v
```

**Using the custom test runner:**
```bash
# Run all tests
uv run python scripts/run_tests.py

# Run with verbose output
uv run python scripts/run_tests.py --verbose

# Run with coverage report
uv run python scripts/run_tests.py --coverage

# Run only unit tests
uv run python scripts/run_tests.py --unit

# Run only integration tests
uv run python scripts/run_tests.py --integration

# Run specific test files
uv run python scripts/run_tests.py tests/test_config.py tests/test_main.py
```

**Example MCP Server Tests:**
```bash
# Run all example server tests
uv run python scripts/run_example_tests.py

# Run with verbose output
uv run python scripts/run_example_tests.py --verbose

# Run with coverage
uv run python scripts/run_example_tests.py --coverage

# Run only filesystem server tests
uv run python scripts/run_example_tests.py --filesystem

# Run only weather server tests
uv run python scripts/run_example_tests.py --weather

# Check server health
uv run python scripts/run_example_tests.py --check
```

### Test Categories

**Unit Tests:**
- `test_config.py` - Configuration management (6 tests)
- `test_claude_agent_client.py` - Claude Agent client helper (6 tests)
- `test_claude_agent_chatbot.py` - Claude REPL commands and history (7 tests)
- `test_gemini_client.py` - Gemini API client functionality (11 tests)
- `test_chatbot.py` - Interactive chatbot features (23 tests)
- `test_main.py` - Main entry point and CLI (8 tests)

**MCP Framework Tests:**
- `test_mcp_manager.py` - MCP client management (25+ tests)
- `test_mcp_config.py` - MCP configuration handling (15+ tests)
- `test_mcp_http_transport.py` - HTTP/SSE transport tests (20+ tests)
- `test_mcp_multi_server.py` - Multi-server coordination (15+ tests)
- `test_mcp_oauth.py` - OAuth authentication (20+ tests)
- `test_mcp_retry.py` - Connection retry logic (10+ tests)

**Example Server Tests:**
- `test_filesystem_server.py` - Filesystem MCP server (44 tests)
- `test_weather_server.py` - Weather MCP server (39 tests)

**Integration Tests:**
- `test_integration.py` - Full system integration scenarios

### Test Coverage

The test suite covers:
- ✅ **Configuration**: Environment variables, defaults, static methods
- ✅ **Claude Agent**: Session lifecycle management, MCP registration, command handling
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

## Documentation

- 📚 **[Documentation Index](docs/README.md)** - Complete documentation overview
- 🤖 **[Claude Agent Guide](docs/claude-agent.md)** - Configure the Claude Agent SDK on Vertex AI
- 📖 **[MCP User Guide](docs/mcp-guide.md)** - Comprehensive guide to using MCP features
- ⚙️ **[MCP Configuration Reference](docs/mcp-config-reference.md)** - Detailed configuration options
- 🔧 **[MCP API Reference](docs/mcp-api.md)** - Technical API documentation
- 🔍 **[MCP Troubleshooting](docs/mcp-troubleshooting.md)** - Solutions to common problems
- 🚀 **[Example MCP Servers](examples/README.md)** - Ready-to-use example servers
- 🏗️ **[Implementation Details](plans/implement-mcp-client.md)** - Technical implementation notes

## Development

To extend or modify the chatbot:

### Architecture
1. **`ClaudeAgentClient`** (`src/claude_agent_client.py`) - Creates Claude agents/sessions and sends messages
2. **`ClaudeAgentChatbot`** (`src/claude_agent_chatbot.py`) - Terminal UI that wraps the Claude Agent SDK
3. **`Config`** (`src/config.py`) - Centralised configuration management for Claude and Gemini helpers
4. **`main.py`** - Entry point and CLI argument handling
5. **Legacy Gemini modules** (`src/gemini_client.py`, `src/chatbot.py`) - Retained for backwards compatibility and tests

### Adding New Features
1. **New Commands**: Extend `ClaudeAgentChatbot.handle_command` for CLI additions
2. **Model Parameters**: Modify settings in the `Config` class
3. **API Features**: Add helpers to `ClaudeAgentClient` (or the fallback stub) for advanced SDK usage
4. **UI Enhancements**: Update rendering helpers in `ClaudeAgentChatbot`

### Development Workflow
```bash
# Install dev dependencies
uv sync --extra dev

# Install pre-commit hooks (one-time setup)
uv run pre-commit install

# Run tests during development
uv run pytest tests/ -v --tb=short

# Run tests with coverage
uv run python scripts/run_tests.py --coverage

# Format code manually (or let pre-commit do it automatically)
uv run black src/ tests/
uv run isort src/ tests/

# Run all pre-commit hooks manually
uv run pre-commit run --all-files

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

MIT License. See [LICENSE](LICENSE) for details.
