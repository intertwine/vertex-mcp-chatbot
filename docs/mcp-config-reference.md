# MCP Configuration Reference

Complete reference for configuring MCP servers in the Gemini chatbot.

## Configuration File

The MCP configuration is stored in `mcp_config.json` in the project root directory.

### Basic Structure

```json
{
  "servers": [
    {
      "name": "server-name",
      "transport": "stdio|http|sse",
      // ... transport-specific configuration
    }
  ]
}
```

## Common Server Options

All server types support these options:

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Unique identifier for the server |
| `transport` | string | Yes | - | Transport type: "stdio", "http", or "sse" |
| `priority` | integer | No | 1 | Server priority for tool conflict resolution (lower = higher priority) |
| `retry` | object | No | See below | Connection retry configuration |

## Transport-Specific Options

### stdio Transport

For local servers that communicate via standard input/output.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `command` | array | Yes | - | Command to execute (e.g., `["python", "server.py"]`) |
| `args` | array | No | [] | Additional command-line arguments |
| `env` | object | No | {} | Environment variables to set |
| `cwd` | string | No | Current dir | Working directory for the command |

**Example:**
```json
{
  "name": "local-tools",
  "transport": "stdio",
  "command": ["python", "mcp_server.py"],
  "args": ["--verbose", "--port", "8080"],
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "DEBUG": "true"
  },
  "cwd": "/path/to/server"
}
```

### HTTP Transport

For servers accessible via HTTP endpoints.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | HTTP endpoint URL |
| `headers` | object | No | {} | Custom HTTP headers |
| `auth` | object | No | - | Authentication configuration |

**Example:**
```json
{
  "name": "api-server",
  "transport": "http",
  "url": "https://api.example.com/mcp",
  "headers": {
    "X-API-Key": "${API_KEY}",
    "User-Agent": "Gemini-MCP-Client/1.0"
  }
}
```

### SSE Transport (Deprecated)

For servers using Server-Sent Events. Note: SSE transport is deprecated; use HTTP instead.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | Yes | - | SSE endpoint URL |
| `headers` | object | No | {} | Custom HTTP headers |

## Authentication Options

### Basic Authentication

For HTTP/SSE transports with basic auth.

```json
{
  "auth": {
    "type": "basic",
    "username": "your-username",
    "password": "${PASSWORD}"
  }
}
```

### OAuth 2.0 Authentication

For HTTP/SSE transports with OAuth 2.0.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "oauth" |
| `authorization_url` | string | Yes | - | OAuth authorization endpoint |
| `token_url` | string | Yes | - | OAuth token exchange endpoint |
| `client_id` | string | Yes | - | OAuth client identifier |
| `client_secret` | string | No | - | OAuth client secret (for confidential clients) |
| `scope` | string | Yes | - | Space-separated list of scopes |
| `redirect_uri` | string | Yes | - | Callback URL for authorization |
| `pkce` | boolean | No | true | Use PKCE for enhanced security |

**Example:**
```json
{
  "auth": {
    "type": "oauth",
    "authorization_url": "https://github.com/login/oauth/authorize",
    "token_url": "https://github.com/login/oauth/access_token",
    "client_id": "abc123",
    "client_secret": "${GITHUB_CLIENT_SECRET}",
    "scope": "repo read:user",
    "redirect_uri": "http://localhost:8080/callback"
  }
}
```

### Custom Headers Authentication

For API key or token-based auth via headers.

```json
{
  "headers": {
    "Authorization": "Bearer ${API_TOKEN}",
    "X-API-Key": "${API_KEY}"
  }
}
```

## Retry Configuration

Configure automatic retry for unreliable connections.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `max_attempts` | integer | No | 3 | Maximum number of connection attempts |
| `initial_delay` | float | No | 1.0 | Initial retry delay in seconds |
| `max_delay` | float | No | 60.0 | Maximum retry delay in seconds |
| `exponential_base` | float | No | 2.0 | Exponential backoff multiplier |
| `jitter` | boolean | No | true | Add randomization to retry delays |

**Example:**
```json
{
  "retry": {
    "max_attempts": 5,
    "initial_delay": 2.0,
    "max_delay": 30.0,
    "exponential_base": 2.0,
    "jitter": true
  }
}
```

## Environment Variables

Configuration values can reference environment variables using `${VAR_NAME}` syntax. Environment variables are automatically loaded from your `.env` file if present.

### Basic Substitution

```json
{
  "command": ["python", "server.py"],
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "DATABASE_URL": "${DATABASE_URL}"
  },
  "headers": {
    "Authorization": "Bearer ${ACCESS_TOKEN}"
  }
}
```

### Default Values

Use `${VAR_NAME:-default}` syntax to provide default values when environment variables are not set:

```json
{
  "env": {
    "DEBUG": "${DEBUG:-false}",
    "PORT": "${PORT:-8080}",
    "LOG_LEVEL": "${LOG_LEVEL:-info}"
  }
}
```

### Escaped Variables

To include literal `${...}` in your configuration without substitution, use one of these escape methods:

```json
{
  "message": "\\${NOT_A_VARIABLE}",    // Results in: ${NOT_A_VARIABLE}
  "pattern": "$${ALSO_NOT_A_VAR}"      // Results in: ${ALSO_NOT_A_VAR}
}
```

### Loading from .env Files

The chatbot automatically loads environment variables from `.env` files in your project root:

```bash
# .env file
MY_API_KEY=secret123
OAUTH_CLIENT_ID=my-client-id
OAUTH_CLIENT_SECRET=my-client-secret
```

### Substitution Scope

Environment variable substitution works in:
- String values at any nesting level
- Array elements (if they are strings)
- Object property values (if they are strings)

Non-string values (numbers, booleans, null) are not affected by substitution.

### Error Handling

If a referenced environment variable is not found and no default is provided, the configuration will fail to load with a clear error message:

```
MCPConfigError: Environment variable 'MISSING_VAR' not found in configuration value: ${MISSING_VAR}
```

## Complete Examples

### Local Development Server

```json
{
  "servers": [
    {
      "name": "dev-tools",
      "transport": "stdio",
      "command": ["python", "-m", "mcp_server"],
      "args": ["--dev"],
      "env": {
        "PYTHONPATH": ".",
        "DEBUG": "true"
      },
      "priority": 1
    }
  ]
}
```

### Production API Server

```json
{
  "servers": [
    {
      "name": "prod-api",
      "transport": "http",
      "url": "https://api.company.com/mcp/v1",
      "auth": {
        "type": "oauth",
        "authorization_url": "https://auth.company.com/oauth/authorize",
        "token_url": "https://auth.company.com/oauth/token",
        "client_id": "gemini-chatbot",
        "client_secret": "${OAUTH_CLIENT_SECRET}",
        "scope": "mcp.read mcp.write",
        "redirect_uri": "http://localhost:8080/oauth/callback"
      },
      "retry": {
        "max_attempts": 5,
        "initial_delay": 1.0,
        "max_delay": 10.0
      },
      "priority": 1
    }
  ]
}
```

### Multi-Server Setup

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
      "auth": {
        "type": "basic",
        "username": "user",
        "password": "${BACKUP_PASSWORD}"
      },
      "retry": {
        "max_attempts": 10
      },
      "priority": 2
    },
    {
      "name": "file-server",
      "transport": "stdio",
      "command": ["node", "file_server.js"],
      "env": {
        "BASE_PATH": "/data"
      }
    }
  ]
}
```

## Configuration Validation

The configuration is validated when loaded. Common validation errors:

1. **Missing required fields**
   ```
   MCPConfigError: Server 'my-server' missing required field 'transport'
   ```

2. **Invalid transport type**
   ```
   MCPConfigError: Invalid transport 'websocket' for server 'my-server'
   ```

3. **Duplicate server names**
   ```
   MCPConfigError: Duplicate server name: 'calculator'
   ```

4. **Missing OAuth fields**
   ```
   MCPConfigError: OAuth configuration missing required field 'client_id'
   ```

## Best Practices

1. **Use Environment Variables**: Never hardcode sensitive values
   ```json
   "password": "${DB_PASSWORD}"  // Good
   "password": "secret123"       // Bad
   ```

2. **Set Appropriate Timeouts**: Configure retry for network reliability
   ```json
   "retry": {
     "max_attempts": 5,
     "initial_delay": 1.0
   }
   ```

3. **Use Priority**: Control server selection for tools
   ```json
   "priority": 1  // Primary server
   "priority": 2  // Backup server
   ```

4. **Descriptive Names**: Use clear, meaningful server names
   ```json
   "name": "github-api"     // Good
   "name": "server1"        // Bad
   ```

5. **Minimal Permissions**: Request only necessary OAuth scopes
   ```json
   "scope": "read:user"     // Good
   "scope": "admin"         // Avoid if not needed
   ```

## Token Storage

OAuth tokens are automatically stored in `.mcp_tokens/` directory:

```
.mcp_tokens/
├── github-api.json
└── google-drive.json
```

Token files contain:
- Access token
- Token type
- Expiration time
- Refresh token (if available)

## Security Considerations

1. **Git Ignore**: Add to `.gitignore`:
   ```
   mcp_config.json
   .mcp_tokens/
   ```

2. **File Permissions**: Tokens are saved with restricted permissions (owner read/write only)

3. **Token Refresh**: Expired tokens are automatically refreshed when possible

4. **PKCE**: OAuth flows use PKCE by default for enhanced security
