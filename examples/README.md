# MCP Example Servers

This directory contains example MCP (Model Context Protocol) servers that demonstrate how to build and use MCP servers with the Gemini chatbot.

## Quick Start

### 1. Install Dependencies

The MCP package is already included in the project dependencies, so just ensure you have synced:

```bash
uv sync
```

### 2. Run the Example Servers

#### File System Server (stdio transport)

The filesystem server provides file operations through the stdio transport:

```bash
# Run from the project root directory
uv run python examples/mcp-servers/filesystem_server.py
```

This server provides:
- **Tools**: `list_files`, `read_file`, `write_file`, `create_directory`
- **Resources**: Exposes files as resources with `file:///` URIs
- **Prompts**: `analyze_directory`, `summarize_file`

#### Weather Server (stdio transport)

The weather server provides weather information through the stdio transport:

```bash
# Run the weather server
uv run python examples/mcp-servers/weather_server.py
```

This server provides:
- **Tools**: `get_weather`, `get_forecast`, `get_alerts`
- **Resources**: Weather data as `weather://` URIs
- **Prompts**: `weather_report`, `travel_weather`, `weather_comparison`

#### OAuth Servers (for authentication testing)

The OAuth servers demonstrate how to implement OAuth 2.0 authentication with MCP:

**OAuth Authorization Server**
```bash
# Run the authorization server (port 9000)
uv run python examples/mcp-servers/oauth_auth_server.py --port 9000
```

**OAuth Protected MCP Server**
```bash
# Run the protected MCP server (requires auth server running)
uv run python examples/mcp-servers/oauth_protected_server.py --transport stdio --auth-server http://localhost:9000
```

The OAuth servers provide:
- **Authorization Server**: OAuth 2.0 endpoints with PKCE support, test credentials (testuser/testpass)
- **Protected Server**: MCP server requiring OAuth tokens with tools like `get_user_profile`, `create_secure_note`
- **Discovery**: RFC 9728 compliant discovery endpoints for OAuth integration

### 3. Configure the Chatbot

Copy the example configuration to your project root:

```bash
cp examples/mcp_config.json mcp_config.json
```

Or create your own configuration:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "transport": "stdio",
      "command": ["python", "examples/mcp-servers/filesystem_server.py"]
    },
    {
      "name": "weather",
      "transport": "stdio",
      "command": ["python", "examples/mcp-servers/weather_server.py"]
    }
  ]
}
```

### 4. Connect and Use

Start the chatbot and connect to the servers:

```bash
# Start the chatbot
uv run main.py

# In the chatbot, connect to servers
You> /mcp connect filesystem
You> /mcp connect weather

# List available tools
You> /mcp tools

# Use the servers naturally in conversation
You> What files are in the current directory?
You> What's the weather like in London?
```

## Example Conversations

### File System Operations

```
You> Can you list all Python files in the examples directory?

Assistant> I'll list all Python files in the examples directory for you.

[Executing tool: list_files]
Found 2 Python files in examples/mcp-servers/:
- filesystem_server.py (11,234 bytes)
- weather_server.py (9,876 bytes)

You> Can you read and summarize the filesystem_server.py file?

Assistant> I'll read and summarize the filesystem_server.py file.

[Executing tool: read_file]
[Reading file content...]

The filesystem_server.py is an MCP server implementation that provides file system operations. Here's a summary:

**Main Features:**
- Provides 4 tools: list_files, read_file, write_file, and create_directory
- Uses stdio transport for communication
- Implements security checks to prevent access outside the base directory
- Exposes files as MCP resources with file:// URIs
- Includes 2 prompt templates for directory analysis and file summarization

**Key Components:**
1. FileSystemServer class that handles all MCP operations
2. Security validation on all paths to ensure they stay within base directory
3. MIME type detection based on file extensions
4. Resource discovery for common file types
5. Error handling with informative messages
```

### Weather Information

```
You> What's the weather forecast for Paris for the next 3 days?

Assistant> I'll get the weather forecast for Paris for the next 3 days.

[Executing tool: get_forecast]
Here's the 3-day forecast for Paris:

**Day 1 (2024-01-28)**
- Condition: Partly Cloudy
- High: 12°C, Low: 5°C
- Precipitation chance: 20%
- Wind: 15 km/h

**Day 2 (2024-01-29)**
- Condition: Rainy
- High: 10°C, Low: 4°C
- Precipitation chance: 80%
- Wind: 20 km/h

**Day 3 (2024-01-30)**
- Condition: Sunny
- High: 14°C, Low: 6°C
- Precipitation chance: 10%
- Wind: 10 km/h

Overall, expect some rain on Tuesday, but otherwise pleasant weather with temperatures ranging from 4-14°C.
```

### Using Resources

```
You> Can you analyze the file at file:///README.md?

Assistant> I'll analyze the README.md file for you.

[Reading resource: file:///README.md]
[Analyzing content...]

The README.md file is the main documentation for the MCP example servers. It contains:

1. **Structure**: Well-organized with clear sections for setup, usage, and examples
2. **Content**: Comprehensive guide covering installation, configuration, and usage
3. **Examples**: Practical examples showing real conversations with both servers
4. **Technical Details**: Lists all available tools, resources, and prompts for each server
```

### Using Prompts

```
You> /mcp prompt weather_comparison
Enter value for 'location1': London
Enter value for 'location2': New York

Assistant> I'll compare the weather between London and New York.

[Executing tool: get_weather for London]
[Executing tool: get_weather for New York]
[Executing tool: get_forecast for both locations]

**Weather Comparison: London vs New York**

**Current Conditions:**
- London: 8°C, Cloudy, 70% humidity
- New York: 2°C, Sunny, 45% humidity
- Temperature difference: London is 6°C warmer

**Better Weather:** London currently has milder temperatures, though it's cloudier...
```

## Server Details

### File System Server

**Configuration Options:**
- `FILE_SERVER_BASE_PATH`: Set the base directory for file operations (default: current directory)

**Security Features:**
- All paths are validated to ensure they remain within the base directory
- Prevents directory traversal attacks
- Safe for use with untrusted input

### Weather Server

**Notes:**
- Uses mock data for demonstration (not connected to real weather API)
- Demonstrates stdio transport for MCP
- Shows how to implement various data formats and prompt templates

## Testing the Example Servers

The example servers include comprehensive test suites to ensure they work correctly and serve as examples for testing your own MCP servers.

### Running Tests

**Test all example servers:**
```bash
# Run all example server tests
uv run python scripts/run_example_tests.py

# Run with verbose output
uv run python scripts/run_example_tests.py --verbose

# Run with coverage reporting
uv run python scripts/run_example_tests.py --coverage
```

**Test specific servers:**
```bash
# Test only filesystem server
uv run python scripts/run_example_tests.py --filesystem

# Test only weather server
uv run python scripts/run_example_tests.py --weather

# Check server health before testing
uv run python scripts/run_example_tests.py --check
```

**Using pytest directly:**
```bash
# Run filesystem server tests
uv run pytest tests/test_filesystem_server.py -v

# Run weather server tests
uv run pytest tests/test_weather_server.py -v

# Run both with coverage
uv run pytest tests/test_*_server.py --cov=examples/mcp-servers --cov-report=term-missing
```

### Test Coverage

**Filesystem Server Tests (44 tests):**
- ✅ Path validation and security (prevent directory traversal)
- ✅ File operations: list_files, read_file, write_file, create_directory
- ✅ Resource access patterns with file:// URIs
- ✅ Prompt templates: analyze_directory, summarize_file
- ✅ Error handling and edge cases
- ✅ MCP protocol compliance

**Weather Server Tests (39 tests):**
- ✅ Weather data tools: get_weather, get_forecast, get_alerts
- ✅ Resource access with weather:// URIs
- ✅ Prompt templates: weather_report, travel_weather, weather_comparison
- ✅ Data consistency and validation
- ✅ Error handling for invalid inputs
- ✅ MCP protocol compliance

**Integration Tests:**
- ✅ FastMCP server initialization
- ✅ Tool registration and discovery
- ✅ Resource registration and access
- ✅ Prompt template functionality
- ✅ Schema validation

### Test Development

When building your own MCP server, use these test patterns:

1. **Tool Testing**: Test each tool with valid inputs, edge cases, and error conditions
2. **Resource Testing**: Verify resource URIs return correct content and handle errors
3. **Prompt Testing**: Ensure prompt templates generate correct prompts with parameters
4. **Security Testing**: Test path validation, access controls, and input sanitization
5. **Integration Testing**: Verify MCP protocol compliance and server initialization

Example test structure:
```python
import pytest
from your_server import mcp, your_tool

class TestYourServer:
    @pytest.mark.asyncio
    async def test_your_tool_success(self):
        result = await your_tool("valid_input")
        assert result["success"] == True
    
    @pytest.mark.asyncio
    async def test_your_tool_error_handling(self):
        with pytest.raises(ValueError, match="Invalid input"):
            await your_tool("invalid_input")
    
    def test_server_has_tools(self):
        tools = mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        assert "your_tool" in tool_names
```

## Building Your Own MCP Server

Use these examples as templates for building your own MCP servers:

1. **Choose a transport**: stdio is the recommended transport for simplicity
2. **Define your tools**: What operations should the LLM be able to perform?
3. **Add resources**: What data should be accessible via URIs?
4. **Create prompts**: What complex workflows can you template?
5. **Implement handlers**: Use the MCP SDK to handle requests
6. **Test with chatbot**: Connect and verify functionality

For more details, see the [MCP User Guide](../docs/mcp-guide.md) and the official [MCP documentation](https://modelcontextprotocol.io).

## Troubleshooting

### Server Won't Start
- Check Python version (requires 3.10+)
- Ensure MCP package is installed: `uv pip install mcp`
- Check for port conflicts (weather server)

### Connection Failed
- Verify server is running before connecting
- Check configuration file syntax
- For stdio servers, ensure command path is correct
- The FastMCP framework handles transport details automatically

### Tools Not Working
- Check server logs for error messages
- Verify tool parameters are correct
- Ensure server has necessary permissions (file system access, etc.)

## Next Steps

1. Modify the example servers to add new capabilities
2. Create your own MCP server for your specific use case
3. Combine multiple servers for complex workflows
4. Share your servers with the community!