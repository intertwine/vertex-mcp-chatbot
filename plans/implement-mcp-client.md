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

**Core MCP Capabilities:**
- **Server Discovery & Connection**: Connect to MCP servers via stdio, SSE, or HTTP transports
- **Dynamic Tool Access**: Query and invoke tools exposed by MCP servers
- **Resource Access**: Retrieve data resources from connected servers
- **Prompt Templates**: Access and use pre-defined prompts from servers
- **Multi-Server Support**: Connect to multiple MCP servers simultaneously

**Chatbot-Specific Features:**
- **New Commands**:
  - `/mcp connect <server>` - Connect to an MCP server
  - `/mcp list` - List connected servers and their capabilities
  - `/mcp tools` - Show available tools from all connected servers
  - `/mcp resources` - Show available resources
  - `/mcp prompts` - Show available prompt templates
  - `/mcp disconnect <server>` - Disconnect from a server
- **Tool Integration**: Seamlessly call MCP tools within chat conversations
- **Resource Embedding**: Include MCP resources in prompts to Gemini
- **Prompt Enhancement**: Use MCP prompt templates to enhance interactions
- **Configuration Management**: Load server configurations from `mcp_config.json`

### New MCP Client architecture

**Integration Approach:**
The MCP client will be integrated as a new component that works alongside the existing Gemini client, allowing the chatbot to augment its capabilities with external tools and data sources.

**New Components:**
- `src/mcp_manager.py` - Central MCP client management
  - Manages multiple MCP client sessions
  - Handles server discovery and connection lifecycle
  - Coordinates tool/resource/prompt access across servers
  - Integrates with existing chat flow

- `src/mcp_config.py` - MCP configuration handling
  - Loads server configurations from `mcp_config.json`
  - Validates transport types and parameters
  - Manages authentication credentials
  - Example config structure:
    ```json
    {
      "servers": [
        {
          "name": "local-tools",
          "transport": "stdio",
          "command": ["python", "my_mcp_server.py"]
        },
        {
          "name": "api-server",
          "transport": "http",
          "url": "http://localhost:8000/mcp"
        }
      ]
    }
    ```

**Modified Components:**
- `src/chatbot.py` - Extended to handle MCP commands
  - New command processing for `/mcp` commands
  - Integration points for tool results in conversation flow
  - Display formatting for MCP responses

- `src/gemini_client.py` - Enhanced message handling
  - Ability to include MCP tool results in prompts
  - Context enrichment with MCP resources

**Architecture Flow:**
1. User issues MCP command or mentions tool/resource
2. Chatbot delegates to MCP Manager
3. MCP Manager queries appropriate server(s)
4. Results are formatted and either:
   - Displayed directly to user (for listings)
   - Passed to Gemini as context (for tool results)
   - Used to enhance the prompt (for resources/prompts)

**State Management:**
- Active MCP sessions stored in MCP Manager
- Tool/resource/prompt listings cached per session
- Server connection status tracked
- Integration with existing chat history

### New MCP Client tests

**Unit Tests:**
- `test_mcp_manager.py`
  - Server connection/disconnection
  - Tool/resource/prompt discovery
  - Multi-server coordination
  - Error handling for failed connections

- `test_mcp_config.py`
  - Configuration loading and validation
  - Transport type handling
  - Credential management

**Integration Tests:**
- `test_mcp_integration.py`
  - End-to-end MCP command flows
  - Tool execution with mock servers
  - Resource retrieval scenarios
  - Prompt template usage

**Test Infrastructure:**
- Mock MCP server for testing
- Fixtures for various server configurations
- Test data for tools, resources, and prompts

### New documentation

**User Documentation Updates:**
- **MCP Commands Guide**: Detailed guide for all `/mcp` commands
- **Server Configuration**: How to set up `mcp_config.json`
- **Example Workflows**: Common MCP usage patterns
- **Troubleshooting**: MCP-specific issues and solutions

**Developer Documentation:**
- **MCP Integration Architecture**: Technical details of the integration
- **Extending MCP Support**: How to add new transport types
- **Security Considerations**: Best practices for MCP server connections

**Configuration Documentation:**
- **mcp_config.json Schema**: Complete configuration reference
- **Transport Options**: Stdio, SSE, HTTP configuration details
- **Authentication Setup**: OAuth and token management

## Needed changes

### New and updated tests

**New Test Files:**
1. `tests/test_mcp_manager.py` - Test MCP client management functionality
2. `tests/test_mcp_config.py` - Test MCP configuration loading
3. `tests/test_mcp_integration.py` - Integration tests for MCP features
4. `tests/conftest.py` - Add MCP-related fixtures and mocks

**Updated Test Files:**
1. `tests/test_chatbot.py` - Add tests for new MCP commands
2. `tests/test_main.py` - Add tests for MCP-related CLI arguments
3. `tests/test_integration.py` - Add MCP + Gemini integration scenarios

### New and updated code

**New Files to Create:**
1. `src/mcp_manager.py` - Core MCP client management
   - `MCPManager` class with methods:
     - `connect_server(server_config)`
     - `disconnect_server(server_name)`
     - `list_servers()`
     - `get_tools(server_name=None)`
     - `get_resources(server_name=None)`
     - `get_prompts(server_name=None)`
     - `call_tool(server_name, tool_name, arguments)`
     - `get_resource(server_name, resource_uri)`

2. `src/mcp_config.py` - MCP configuration handling
   - `MCPConfig` class for loading/validating config
   - Support for stdio, SSE, and HTTP transports
   - Server configuration validation

3. `mcp_config.json` - Default configuration file
   - Example server configurations
   - Documentation comments

**Files to Update:**
1. `src/chatbot.py`
   - Add MCP command processing in `process_command()`
   - Add MCP manager initialization
   - Add display methods for MCP results
   - Integrate MCP tool calls into chat flow

2. `src/gemini_client.py`
   - Add method to include MCP context in messages
   - Support for tool result formatting

3. `src/config.py`
   - Add MCP-related configuration options
   - Path to mcp_config.json

4. `main.py`
   - Add MCP-related command line arguments
   - Initialize MCP manager if enabled

5. `pyproject.toml`
   - Add `mcp` dependency
   - Update version number

6. `.gitignore`
   - Add `mcp_config.json` (for user-specific configs)

### New and updated documentation

**Files to Update:**
1. `README.md`
   - Add MCP features section
   - Add MCP configuration guide
   - Update command reference with MCP commands
   - Add MCP server setup examples
   - Update prerequisites with MCP requirements

**New Documentation Files:**
2. `docs/mcp-guide.md` - Comprehensive MCP usage guide
   - Setting up MCP servers
   - Configuring the chatbot for MCP
   - Example workflows
   - Troubleshooting

3. `docs/mcp-config-schema.md` - Configuration reference
   - Complete schema documentation
   - Transport-specific options
   - Security considerations

**Implementation Order:**
- IMPORTANT: The implementation will be dependent on the official MCP Python SDK, with documentation available at <https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/refs/heads/main/README.md> Make this your primary reference for MCP client implementation, and import the SDK into the chatbot project.
- IMPORTANT: This project uses uv as the package manager, not pip. Make sure to use uv for all package management, script running, and testing.

1. **Phase 1**: Core MCP infrastructure *(IN PROGRESS)*
   - Create `mcp_manager.py` and `mcp_config.py`
   - Add basic MCP commands to chatbot
   - Implement stdio transport first
   - **Status**: MCP dependency added, Python version updated to 3.10+

2. **Phase 2**: Integration with chat flow *(IN PROGRESS)*
   - Tool execution within conversations *(COMPLETE - Increment 1)*
   - Resource embedding in prompts
   - Prompt template usage

3. **Phase 3**: Advanced features
   - HTTP/SSE transport support
   - Multi-server coordination
   - Authentication handling

4. **Phase 4**: Polish and documentation
   - Comprehensive testing
   - User documentation
   - Example MCP servers

## Implementation Log

### Phase 1: Core MCP Infrastructure

#### 2025-01-27 - Initial MCP Dependency Setup
**Completed:**
- ✅ Added `mcp[cli]` dependency to `pyproject.toml`
- ✅ Updated Python version requirement from `>=3.9` to `>=3.10` (MCP requires Python 3.10+)
- ✅ Updated Python version classifiers in `pyproject.toml` (removed Python 3.9)
- ✅ Updated black target-version configuration (removed py39)
- ✅ Added `pytest-asyncio>=0.21.0` to dev dependencies for future async tests
- ✅ Created `tests/test_mcp_imports.py` with 4 tests verifying MCP imports:
  - `test_mcp_package_import()` - Verifies base MCP package can be imported
  - `test_mcp_client_session_import()` - Verifies ClientSession import
  - `test_mcp_stdio_server_parameters_import()` - Verifies StdioServerParameters import
  - `test_mcp_stdio_client_import()` - Verifies stdio_client import
- ✅ All tests pass (75 total tests in project)
- ✅ Code formatted with black and passes flake8
- ✅ Updated `README.md` to reflect Python 3.10+ requirement
- ✅ Added note in `README.md` about MCP integration in progress

**Next Steps:**
- Create `src/mcp_config.py` for configuration handling
- Create `src/mcp_manager.py` for MCP client management
- Add basic `/mcp` command structure to chatbot

#### 2025-01-27 - MCP Configuration Module
**Completed:**
- ✅ Created `src/mcp_config.py` with `MCPConfig` class:
  - Loads server configurations from JSON file
  - Validates transport types (stdio, http, sse)
  - Validates required parameters for each transport
  - Provides `get_server()` method to retrieve server by name
  - Supports configuration reload
  - Handles missing config files gracefully
- ✅ Created `tests/test_mcp_config.py` with 13 comprehensive tests:
  - Configuration loading and validation
  - Transport-specific validation
  - Error handling for invalid configurations
  - Server lookup by name
  - Configuration reload functionality
- ✅ Created `mcp_config.json.example` with example server configurations
- ✅ Updated `.gitignore` to exclude user-specific `mcp_config.json`
- ✅ All tests pass (88 total tests in project)
- ✅ Code formatted and passes all linters

**Next Steps:**
- Create `src/mcp_manager.py` for MCP client management
- Add basic `/mcp` command structure to chatbot

#### 2025-01-27 - MCP Manager Implementation
**Completed:**
- ✅ Created `src/mcp_manager.py` with `MCPManager` class:
  - Manages multiple MCP client sessions and connections
  - Uses AsyncExitStack for proper resource management (following official SDK pattern)
  - Supports connecting/disconnecting servers
  - Lists connected servers with status
  - Gets tools, resources, and prompts from servers
  - Executes tools and reads resources
  - Provides synchronous wrapper methods for non-async contexts
- ✅ Updated initial implementation approach based on official SDK examples:
  - Changed from attempting to keep connections alive in async with blocks
  - Adopted AsyncExitStack pattern from official chatbot example
  - Proper lifecycle management with initialize() and cleanup() methods
  - Stores both sessions and transport streams for proper tracking
- ✅ Created `tests/test_mcp_manager.py` with 19 comprehensive tests:
  - Manager initialization and cleanup
  - Server connection/disconnection for different transports
  - Tool, resource, and prompt discovery
  - Tool execution and resource reading
  - Error handling for various scenarios
  - Sync wrapper method verification
- ✅ Updated `tests/conftest.py` with MCP-specific fixtures:
  - mock_mcp_config fixture
  - mock_mcp_session fixture
  - mock_mcp_manager fixture
- ✅ All tests pass (107 total tests in project)
- ✅ Code formatted and passes all linters

**Implementation Notes:**
- The MCPManager uses AsyncExitStack to properly manage async context managers
- Connection lifecycle follows the pattern from the official SDK example
- HTTP and SSE transports are not yet implemented (placeholder errors)
- Sync wrappers use asyncio.run() for each operation to bridge sync/async

**Next Steps:**
- Add basic `/mcp` command structure to chatbot
- Integrate MCPManager into the chatbot

#### 2025-01-27 - Basic MCP Commands in Chatbot
**Completed:**
- ✅ Created 8 new tests in `tests/test_chatbot.py` for MCP command functionality:
  - Test MCP manager initialization (success and failure scenarios)
  - Test `/mcp connect <server>` command (success and error handling)
  - Test `/mcp list` command with connected servers
  - Test `/mcp disconnect <server>` command
  - Test `/mcp` without subcommand (shows usage)
  - Test MCP commands when MCP is not available
- ✅ Updated `src/chatbot.py` to integrate MCP functionality:
  - Added optional MCP imports with try/except for backwards compatibility
  - Added `mcp_manager` initialization in `__init__` and `initialize()` methods
  - Added `cleanup()` method to properly clean up MCP resources on exit
  - Updated help text to include MCP command documentation
  - Implemented `process_mcp_command()` with subcommands:
    - `/mcp connect <server>` - Connect to an MCP server
    - `/mcp list` - List configured servers and connection status
    - `/mcp disconnect <server>` - Disconnect from an MCP server
  - Added helper methods: `mcp_list_servers()`, `mcp_connect()`, `mcp_disconnect()`
  - Added cleanup call in `run()` method before exit
- ✅ Fixed all formatting issues with black formatter
- ✅ Removed unused imports (HTML, Text, rprint)
- ✅ All 116 tests pass
- ✅ Code formatted and passes all linters

**Implementation Notes:**
- MCP support is optional - chatbot continues to work without MCP dependencies
- MCP manager lifecycle properly managed with initialize/cleanup pattern
- Sync wrapper methods used to bridge async MCP operations with sync chatbot interface
- Error handling ensures MCP failures don't crash the chatbot
- Help text only shows MCP commands when MCP is available

**Phase 1 Status:** ✅ COMPLETE
- Core MCP infrastructure is now in place
- Basic connection management working
- Command structure integrated into chatbot
- Ready for Phase 2: Integration with chat flow

### Phase 2: Integration with Chat Flow (IN PROGRESS)

#### 2025-01-27 - Phase 2 Increment 1: Basic Tool Execution in Chat Flow
**Completed:**
- ✅ Added tool context formatting in `src/gemini_client.py`:
  - New `format_tool_context()` method creates structured tool documentation
  - Tool information automatically included in initial system message
  - Each tool documented with name, description, and parameters
- ✅ Implemented natural language tool detection and execution:
  - `detect_tool_call()` method identifies when Gemini suggests tool usage
  - Parses tool name and parameters from natural language responses
  - No special syntax required - tools integrate seamlessly into conversation
- ✅ Created tool execution flow in `src/chatbot.py`:
  - `execute_mcp_tool()` method handles tool execution lifecycle
  - Displays tool execution status to user
  - Formats tool results and passes back to Gemini for interpretation
  - Error handling for tool execution failures
- ✅ Automatic tool discovery and integration:
  - Tools from all connected MCP servers discovered automatically
  - Tool context updated when servers connect/disconnect
  - Gemini informed of available tools at conversation start
- ✅ Created comprehensive tests:
  - 8 new tests in `test_gemini_client.py` for tool context formatting
  - 5 new tests in `test_chatbot.py` for tool execution flow
  - Tests cover success cases, error handling, and edge cases

**Design Decisions:**
- **Natural Language Integration**: Tools are called through natural conversation, not special commands
- **Automatic Discovery**: No manual tool registration - connect a server and tools are available
- **Transparent Execution**: Users see when tools are executed and their results
- **Context Preservation**: Tool results included in conversation history for context
- **Error Resilience**: Tool failures don't crash the chat - errors handled gracefully

**Next Steps:**
- Implement resource access in chat flow
- Add prompt template support
- Enhance tool parameter parsing for complex types

#### 2025-01-27 - Phase 2 Increment 2: Resource Embedding in Prompts
**Completed:**
- ✅ Added `/mcp resources` command in `src/chatbot.py`:
  - Lists all available resources from connected MCP servers
  - Shows resource names, URIs, and descriptions
  - Groups resources by server for clarity
- ✅ Implemented resource URI detection in messages:
  - `detect_resource_uris()` method identifies resource URIs in user input
  - Supports standard URI format (e.g., `file:///path/to/file`, `http://example.com/data`)
  - Pattern matching for common MCP resource URI schemes
- ✅ Created automatic resource reading workflow:
  - Resources referenced by URI are automatically read before sending to Gemini
  - Resource contents embedded in conversation context
  - Multiple resources can be referenced in a single message
- ✅ Enhanced Gemini context with resource data:
  - `format_resource_context()` method structures resource data for Gemini
  - Resources included as part of the user's message with clear labeling
  - Preserves resource metadata (name, URI, mime type if available)
- ✅ Added comprehensive tests:
  - 4 new tests in `test_chatbot.py` for resource commands and detection
  - Tests cover resource listing, URI detection, and resource reading
  - Error handling for missing or unreadable resources

**Design Decisions:**
- **URI Pattern Detection**: Resources are referenced by standard URIs, making them easy to identify
- **Transparent Reading**: Resources are read automatically when referenced, no special commands needed
- **Context Preservation**: Resource contents become part of the conversation history
- **Multiple Resources**: Users can reference multiple resources in a single message
- **Error Handling**: Failed resource reads show clear error messages without breaking the chat flow

**Phase 2 Status:** ✅ COMPLETE (2 of 3 increments)
- Tool execution in chat flow ✅
- Resource embedding in prompts ✅
- Prompt template usage (pending)



