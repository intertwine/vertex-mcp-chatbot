# MCP API Documentation

This document provides technical details about the MCP implementation in the Gemini chatbot.

## Table of Contents

1. [MCPManager Class](#mcpmanager-class)
2. [MCPConfig Class](#mcpconfig-class)
3. [API Methods](#api-methods)
4. [Data Types](#data-types)
5. [Error Handling](#error-handling)

## MCPManager Class

The `MCPManager` class (`src/mcp_manager.py`) is the core component that manages MCP server connections and operations.

### Initialization

```python
from src.mcp_manager import MCPManager
from src.mcp_config import MCPConfig

# Initialize with configuration
config = MCPConfig("mcp_config.json")
manager = MCPManager(config)

# Initialize without configuration (uses default mcp_config.json)
manager = MCPManager()
```

### Key Attributes

- `config`: MCPConfig instance
- `_active_servers`: Dict of currently connected servers
- `_sessions`: Dict tracking server session status
- `_initialized`: Boolean indicating initialization state

## MCPConfig Class

The `MCPConfig` class (`src/mcp_config.py`) handles loading and validating MCP server configurations.

### Configuration Schema

```python
{
    "servers": [
        {
            "name": str,           # Required: Unique server identifier
            "transport": str,      # Required: "stdio", "http", or "sse"
            "priority": int,       # Optional: Server priority (default: 1)
            "retry": {            # Optional: Retry configuration
                "max_attempts": int,
                "initial_delay": float,
                "max_delay": float,
                "exponential_base": float,
                "jitter": bool
            },
            # Transport-specific fields...
        }
    ]
}
```

## API Methods

### Connection Management

#### connect_server_sync(server_name: str) -> None
Connect to an MCP server synchronously.

```python
manager.connect_server_sync("my-server")
```

**Raises:**
- `MCPManagerError`: If server not found or connection fails

#### disconnect_server_sync(server_name: str) -> None
Disconnect from an MCP server.

```python
manager.disconnect_server_sync("my-server")
```

#### list_servers() -> List[Dict[str, Any]]
Get all configured servers with their connection status.

```python
servers = manager.list_servers()
# Returns: [{"name": "server1", "connected": True}, ...]
```

### Tool Operations

#### get_tools_sync(server_name: Optional[str] = None) -> List[Dict[str, Any]]
Get available tools from connected servers.

```python
# Get tools from all servers
all_tools = manager.get_tools_sync()

# Get tools from specific server
server_tools = manager.get_tools_sync("my-server")
```

**Returns:** List of tool definitions with schema

#### call_tool_sync(server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]
Execute a tool on a specific server.

```python
result = manager.call_tool_sync(
    "my-server",
    "calculate",
    {"expression": "2 + 2"}
)
```

**Returns:** Tool execution result

#### find_best_server_for_tool_sync(tool_name: str) -> Optional[str]
Find the best server to execute a tool based on priority.

```python
server = manager.find_best_server_for_tool_sync("calculate")
if server:
    result = manager.call_tool_sync(server, "calculate", {...})
```

### Resource Operations

#### list_resources_sync(server_name: Optional[str] = None) -> List[Dict[str, Any]]
List available resources from servers.

```python
# Get all resources
resources = manager.list_resources_sync()

# Get resources from specific server
server_resources = manager.list_resources_sync("my-server")
```

#### get_resource_templates_sync(server_name: Optional[str] = None) -> List[Dict[str, Any]]
List resource templates (parameterized resources).

```python
templates = manager.get_resource_templates_sync()
# Returns templates like "file:///logs/{date}"
```

#### read_resource_sync(server_name: str, uri: str) -> Dict[str, Any]
Read a resource by URI.

```python
content = manager.read_resource_sync(
    "my-server",
    "file:///data/report.json"
)
```

**Returns:** Resource content with MIME type

#### find_server_with_resource_sync(uri: str) -> Optional[str]
Find which server can provide a resource.

```python
server = manager.find_server_with_resource_sync("file:///data.csv")
if server:
    content = manager.read_resource_sync(server, "file:///data.csv")
```

### Prompt Operations

#### list_prompts_sync(server_name: Optional[str] = None) -> List[Dict[str, Any]]
List available prompt templates.

```python
prompts = manager.list_prompts_sync()
```

#### get_prompt_sync(server_name: str, prompt_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]
Execute a prompt template with arguments.

```python
result = manager.get_prompt_sync(
    "my-server",
    "code_review",
    {
        "file_path": "main.py",
        "focus": "security"
    }
)
```

### Multi-Server Operations

#### broadcast_operation_sync(operation: str, *args, **kwargs) -> Dict[str, Any]
Execute an operation across all connected servers.

```python
# Get tools from all servers
results = manager.broadcast_operation_sync("list_tools")
```

## Data Types

### Tool Definition
```python
{
    "name": str,
    "description": str,
    "inputSchema": {
        "type": "object",
        "properties": {...},
        "required": [...]
    }
}
```

### Resource Definition
```python
{
    "uri": str,
    "name": str,
    "description": str,
    "mimeType": str
}
```

### Prompt Definition
```python
{
    "name": str,
    "description": str,
    "arguments": [
        {
            "name": str,
            "description": str,
            "required": bool
        }
    ]
}
```

## Error Handling

### MCPManagerError
Base exception for all MCP-related errors.

```python
from src.mcp_manager import MCPManagerError

try:
    manager.connect_server_sync("server")
except MCPManagerError as e:
    print(f"MCP Error: {e}")
```

### Common Error Scenarios

1. **Server Not Found**
   ```python
   MCPManagerError: Server 'unknown' not found in configuration
   ```

2. **Connection Failed**
   ```python
   MCPManagerError: Failed to connect to server 'server' after 3 attempts
   ```

3. **Tool Not Found**
   ```python
   MCPManagerError: Tool 'unknown_tool' not found on server 'server'
   ```

4. **Authentication Failed**
   ```python
   MCPManagerError: OAuth authorization failed: Invalid client credentials
   ```

## Usage Examples

### Basic Tool Execution
```python
# Initialize manager
manager = MCPManager()

# Connect to server
manager.connect_server_sync("calculator")

# Execute tool
result = manager.call_tool_sync(
    "calculator",
    "evaluate",
    {"expression": "sqrt(16) + 3^2"}
)
print(result)  # {"result": 13.0}
```

### Resource Reading with Auto-Discovery
```python
# Find server that has the resource
uri = "file:///config/settings.json"
server = manager.find_server_with_resource_sync(uri)

if server:
    # Read the resource
    content = manager.read_resource_sync(server, uri)
    print(content["text"])  # JSON content
```

### Using Prompt Templates
```python
# List available prompts
prompts = manager.list_prompts_sync("code-analyzer")

# Use a prompt
result = manager.get_prompt_sync(
    "code-analyzer",
    "review_function",
    {
        "function_name": "process_data",
        "language": "python"
    }
)
print(result["messages"][0]["content"]["text"])
```

### Multi-Server Tool Discovery
```python
# Connect to multiple servers
manager.connect_server_sync("server1")
manager.connect_server_sync("server2")

# Get all tools
tools = manager.get_tools_sync()

# Find best server for a tool
server = manager.find_best_server_for_tool_sync("calculate")
```

## Thread Safety

The MCPManager is designed to be thread-safe for read operations. However, connection management (connect/disconnect) should be synchronized in multi-threaded environments.

## Performance Considerations

1. **Session Management**: Sessions are created on-demand and closed after use
2. **No Connection Pooling**: Each operation creates a new session
3. **Parallel Operations**: Multi-server operations use asyncio.gather()
4. **Retry Logic**: Configurable exponential backoff for failed connections

## Integration with Chatbot

The chatbot (`src/chatbot.py`) integrates MCPManager through:

1. **Automatic Tool Detection**: Tools are discovered and made available to Gemini
2. **Resource Embedding**: URIs in messages trigger automatic resource reading
3. **Prompt Commands**: `/mcp prompt` command uses the prompt API
4. **System Instructions**: Available tools/resources included in Gemini context
