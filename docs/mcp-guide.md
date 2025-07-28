# MCP (Model Context Protocol) User Guide

This guide provides comprehensive documentation for using MCP features in the Gemini chatbot.

## Table of Contents

1. [Introduction to MCP](#introduction-to-mcp)
2. [Getting Started](#getting-started)
3. [Server Configuration Reference](#server-configuration-reference)
4. [Using MCP Features](#using-mcp-features)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Topics](#advanced-topics)

## Introduction to MCP

### What is MCP?

The Model Context Protocol (MCP) is an open standard that enables Large Language Models (LLMs) to securely access external tools, data sources, and computational resources. It provides a unified way for AI assistants to interact with various services and APIs.

### Why Use MCP with the Gemini Chatbot?

MCP integration enhances the Gemini chatbot with:

- **Dynamic Tool Access**: Execute external tools and scripts during conversations
- **Data Integration**: Access files, databases, and APIs seamlessly
- **Prompt Templates**: Use pre-defined prompts for common tasks
- **Extensibility**: Connect to any MCP-compliant server

### Key Benefits

1. **No Code Changes Required**: Add new capabilities by connecting to MCP servers
2. **Security**: Controlled access to resources with authentication support
3. **Flexibility**: Mix and match servers for different functionalities
4. **Natural Integration**: Tools and resources work seamlessly in conversations

## Getting Started

### Prerequisites

- Python 3.10 or higher
- The Gemini chatbot installed and configured
- MCP servers to connect to (or use example servers)

### Basic Setup

1. **Create Configuration File**

   Create an `mcp_config.json` file in the chatbot directory:

   ```json
   {
     "servers": [
       {
         "name": "my-first-server",
         "transport": "stdio",
         "command": ["python", "path/to/mcp_server.py"]
       }
     ]
   }
   ```

2. **Start the Chatbot**

   ```bash
   uv run main.py
   ```

3. **Connect to the Server**

   ```
   You: /mcp connect my-first-server
   Assistant: Connected to MCP server 'my-first-server'
   ```

### Your First MCP Interaction

Once connected, the chatbot automatically discovers available tools:

```
You: What tools are available?
Assistant: I can see you have access to these MCP tools:
- calculate: Performs mathematical calculations
- read_file: Reads content from files
- web_search: Searches the web for information

You: Can you calculate 15% of 200?
Assistant: I'll calculate 15% of 200 for you.

[Executing tool: calculate]
15% of 200 is 30.
```

## Server Configuration Reference

### Configuration File Structure

The `mcp_config.json` file contains an array of server configurations:

```json
{
  "servers": [
    {
      "name": "server-name",
      "transport": "stdio|http|sse",
      "priority": 1,
      "retry": { ... },
      "auth": { ... },
      ...transport-specific fields
    }
  ]
}
```

### Transport Types

#### stdio Transport

For local MCP servers that communicate via standard input/output:

```json
{
  "name": "local-tools",
  "transport": "stdio",
  "command": ["python", "mcp_server.py"],
  "args": ["--verbose"],
  "env": {
    "API_KEY": "your-key"
  }
}
```

Fields:
- `command`: Command to execute (required)
- `args`: Additional arguments (optional)
- `env`: Environment variables (optional)

#### HTTP Transport

For servers accessible via HTTP endpoints:

```json
{
  "name": "api-server",
  "transport": "http",
  "url": "https://api.example.com/mcp",
  "headers": {
    "X-API-Key": "your-api-key"
  }
}
```

Fields:
- `url`: HTTP endpoint URL (required)
- `headers`: Custom headers (optional)

#### SSE Transport (Deprecated)

For servers using Server-Sent Events:

```json
{
  "name": "sse-server",
  "transport": "sse",
  "url": "https://sse.example.com/events"
}
```

Note: SSE transport is deprecated. Use HTTP transport with streaming instead.

### Authentication Options

#### Basic Authentication

```json
{
  "name": "secure-server",
  "transport": "http",
  "url": "https://api.example.com/mcp",
  "auth": {
    "type": "basic",
    "username": "your-username",
    "password": "your-password"
  }
}
```

#### OAuth 2.0

```json
{
  "name": "oauth-server",
  "transport": "http",
  "url": "https://api.example.com/mcp",
  "auth": {
    "type": "oauth",
    "authorization_url": "https://auth.example.com/oauth/authorize",
    "token_url": "https://auth.example.com/oauth/token",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "scope": "read write",
    "redirect_uri": "http://localhost:8080/callback"
  }
}
```

OAuth fields:
- `authorization_url`: OAuth authorization endpoint
- `token_url`: OAuth token exchange endpoint
- `client_id`: OAuth client identifier
- `client_secret`: OAuth client secret (optional for public clients)
- `scope`: Requested permissions
- `redirect_uri`: Callback URL for authorization

### Retry Configuration

Configure automatic retry for unreliable connections:

```json
{
  "name": "unreliable-server",
  "transport": "http",
  "url": "http://flaky-server.example.com/mcp",
  "retry": {
    "max_attempts": 5,
    "initial_delay": 2.0,
    "max_delay": 30.0,
    "exponential_base": 2.0,
    "jitter": true
  }
}
```

Retry fields:
- `max_attempts`: Maximum connection attempts (default: 3)
- `initial_delay`: Initial retry delay in seconds (default: 1.0)
- `max_delay`: Maximum retry delay in seconds (default: 60.0)
- `exponential_base`: Backoff multiplier (default: 2.0)
- `jitter`: Add randomization to delays (default: true)

### Server Priority

When multiple servers provide the same tool, use priority to control selection:

```json
{
  "name": "primary-tools",
  "transport": "stdio",
  "command": ["python", "primary_server.py"],
  "priority": 1
},
{
  "name": "backup-tools",
  "transport": "http",
  "url": "http://backup.example.com/mcp",
  "priority": 2
}
```

Lower numbers = higher priority. Server with priority 1 will be preferred over priority 2.

## Using MCP Features

### MCP Commands

The chatbot provides several commands for managing MCP connections:

#### /mcp connect <server-name>

Connect to an MCP server defined in your configuration:

```
You: /mcp connect local-tools
Assistant: Connected to MCP server 'local-tools'
```

#### /mcp list

Show all configured servers and their connection status:

```
You: /mcp list
Assistant: MCP Servers:
• local-tools [Connected]
• api-server [Not connected]
• database-server [Not connected]
```

#### /mcp disconnect <server-name>

Disconnect from a connected server:

```
You: /mcp disconnect local-tools
Assistant: Disconnected from MCP server 'local-tools'
```

#### /mcp tools

List all available tools from connected servers:

```
You: /mcp tools
Assistant: Available MCP Tools:

From server 'local-tools':
• calculate - Performs mathematical calculations
• read_file - Reads content from files

From server 'api-server':
• web_search - Searches the web for information
• weather - Gets current weather data
```

#### /mcp resources

List all available resources from connected servers:

```
You: /mcp resources
Assistant: Available MCP Resources:

From server 'local-tools':
• file:///data/config.json - Application configuration
• file:///data/users.csv - User database

From server 'api-server':
• https://api.example.com/status - API status information
```

#### /mcp prompts

List all available prompt templates:

```
You: /mcp prompts
Assistant: Available MCP Prompts:

From server 'local-tools':
• code_review - Template for code review requests
• bug_report - Template for bug report generation
```

#### /mcp prompt <prompt-name>

Use a specific prompt template:

```
You: /mcp prompt code_review
Assistant: Please provide values for the following arguments:
- language: python
- file_path: src/main.py

[Executing prompt template...]
```

### Natural Tool Execution

Tools are automatically available in conversations without special syntax:

```
You: Can you check the weather in San Francisco?
Assistant: I'll check the weather in San Francisco for you.

[Executing tool: weather]
The current weather in San Francisco is 68°F (20°C) with partly cloudy skies.
```

### Resource Embedding

Reference resources by their URI to include them in your conversation:

```
You: Can you analyze the data in file:///data/sales.csv?
Assistant: I'll read and analyze the sales data for you.

[Reading resource: file:///data/sales.csv]
Based on the sales data, I can see that Q4 showed a 15% increase...
```

### Using Prompt Templates

Prompt templates help standardize common requests:

```
You: /mcp prompt bug_report
Assistant: Please provide values for the following arguments:
- description: Login button not responding
- steps_to_reproduce: 1. Go to login page 2. Click login button
- expected_behavior: Should submit form
- actual_behavior: Nothing happens

[Generating bug report...]
```

## Troubleshooting

### Common Issues

#### Connection Failed

**Problem**: Cannot connect to MCP server

**Solutions**:
1. Check server configuration in `mcp_config.json`
2. Verify the server command/URL is correct
3. Ensure the server is running (for stdio servers)
4. Check network connectivity (for HTTP/SSE servers)
5. Review retry configuration for flaky connections

#### Authentication Errors

**Problem**: OAuth or Basic Auth failing

**Solutions**:
1. Verify credentials are correct
2. Check OAuth redirect URI matches configuration
3. Ensure tokens haven't expired
4. Try deleting `.mcp_tokens/` directory to force re-authentication

#### Tool Execution Failures

**Problem**: Tools fail to execute or return errors

**Solutions**:
1. Check tool parameters are correct
2. Verify server has necessary permissions
3. Review server logs for detailed error messages
4. Ensure tool is still available with `/mcp tools`

#### Resource Access Issues

**Problem**: Cannot read resources

**Solutions**:
1. Verify resource URI is correct
2. Check server has access to the resource
3. Ensure proper authentication for protected resources
4. Try accessing resource directly on server first

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
export MCP_DEBUG=true
uv run main.py
```

### Server Logs

For stdio servers, check the server's output:

```bash
# Run server directly to see logs
python mcp_server.py --verbose
```

## Advanced Topics

### Architecture Notes

The MCP implementation uses a simplified on-demand session architecture:

1. **No Persistent Sessions**: MCP sessions are created when needed and closed after use
2. **Stateless Operations**: Each tool call, resource read, or prompt execution is independent
3. **Automatic Cleanup**: Resources are properly released after each operation
4. **Thread Safety**: Safe for concurrent operations

This design ensures reliability and prevents resource leaks while maintaining full MCP functionality.

### Multi-Server Coordination

When multiple servers provide the same tools, the chatbot automatically handles:

- **Conflict Resolution**: Uses server priority to select which server to use
- **Failover**: Falls back to lower priority servers if higher priority fails
- **Load Distribution**: Can distribute requests across servers
- **Tool Discovery**: The `/mcp tools` command shows which server provides each tool

### Custom Headers and Authentication

Add custom headers for API authentication:

```json
{
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}",
    "X-Custom-Header": "value"
  }
}
```

### Environment Variables

Use environment variables in configuration:

```json
{
  "command": ["python", "server.py"],
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "DEBUG": "true"
  }
}
```

### Resource Templates

Some resources accept parameters (resource templates). These are discovered with `/mcp resources` and can be used with specific arguments:

```
You: Show me the logs for yesterday using file:///logs/2024-01-27
Assistant: I'll read the log file for that date.

[Reading resource: file:///logs/2024-01-27]
[Log content displayed...]
```

### Performance Optimization

1. **Connection Pooling**: HTTP transport reuses connections
2. **Parallel Discovery**: Tool/resource discovery happens in parallel
3. **Caching**: Server capabilities cached during session
4. **Retry Strategy**: Configure retry for optimal performance
5. **On-Demand Sessions**: MCP sessions created only when needed

### Security Best Practices

1. **Never commit credentials**: Keep `mcp_config.json` out of version control
2. **Use environment variables**: For sensitive values
3. **Limit server access**: Only connect to trusted MCP servers
4. **Review permissions**: Understand what each server can access
5. **Token storage**: OAuth tokens stored in `.mcp_tokens/` with restricted permissions

## Related Documentation

- 📚 **[Documentation Index](README.md)** - Overview of all documentation
- ⚙️ **[Configuration Reference](mcp-config-reference.md)** - Detailed configuration options
- 🔧 **[API Documentation](mcp-api.md)** - Technical API reference
- 🔍 **[Troubleshooting Guide](mcp-troubleshooting.md)** - Solutions to common problems
- 🚀 **[Example Servers](../examples/README.md)** - Working example implementations

## Next Steps

1. **Explore Example Servers**: Try the example MCP servers included with the chatbot
2. **Build Your Own**: Create custom MCP servers for your specific needs
3. **Share Configurations**: Exchange server configurations with your team
4. **Contribute**: Help improve the MCP ecosystem

For more information about the Model Context Protocol, visit the [official MCP documentation](https://modelcontextprotocol.io).