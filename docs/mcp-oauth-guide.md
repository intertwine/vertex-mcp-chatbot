# MCP OAuth Authentication Guide

This guide explains how to use the OAuth 2.0 authentication examples included with the MCP client implementation.

## Overview

The OAuth authentication system consists of two main components:

1. **OAuth Authorization Server** (`oauth_auth_server.py`) - Provides OAuth 2.0 authorization endpoints
2. **OAuth Protected MCP Server** (`oauth_protected_server.py`) - An MCP server that requires OAuth tokens for access

This implementation follows RFC 9728 (OAuth 2.0 for the Model Context Protocol) and demonstrates how to integrate OAuth 2.0 authentication with MCP servers.

## Features

### Authorization Server Features

- ✅ **OAuth 2.0 Authorization Code Flow** with PKCE (RFC 7636)
- ✅ **Token Introspection** (RFC 7662) 
- ✅ **Authorization Server Discovery** (RFC 8414)
- ✅ **Simple Web-based Login** with test credentials
- ✅ **In-memory Token Storage** (for testing)
- ✅ **CORS Support** for web clients
- ✅ **Security Features**: PKCE, state parameter, client validation

### Protected MCP Server Features

- ✅ **OAuth Token Validation** via introspection
- ✅ **Protected MCP Tools** requiring authentication
- ✅ **Protected MCP Resources** with user-specific data
- ✅ **Token Caching** to reduce introspection calls
- ✅ **Resource Server Discovery** (RFC 9728)
- ✅ **Both stdio and SSE transport** support

## Quick Start

### 1. Start the Authorization Server

The authorization server provides OAuth endpoints and handles user authentication:

```bash
# Start on default port 9000
uv run python examples/mcp-servers/oauth_auth_server.py

# Or specify a custom port
uv run python examples/mcp-servers/oauth_auth_server.py --port 9000 --host localhost
```

**Test Credentials:**
- Username: `testuser`
- Password: `testpass`
- Client ID: `mcp-test-client`
- Client Secret: `mcp-test-secret`

### 2. Start the Protected MCP Server

The protected server provides MCP tools that require OAuth authentication:

```bash
# Start with stdio transport (recommended for this example)
uv run python examples/mcp-servers/oauth_protected_server.py \
  --transport stdio \
  --auth-server http://localhost:9000

# Note: SSE transport is not fully supported in this example
# FastMCP's SSE implementation doesn't support custom port configuration
# For production OAuth servers, use a full HTTP server implementation
```

### 3. Configure the MCP Client

Update your `mcp_config.json` to include the OAuth protected server:

```json
{
  "servers": [
    {
      "name": "oauth-protected",
      "transport": "stdio",
      "command": ["uv", "run", "python", "examples/mcp-servers/oauth_protected_server.py", "--auth-server", "http://localhost:9000"],
      "auth": {
        "type": "oauth",
        "authorization_url": "http://localhost:9000/oauth/authorize",
        "token_url": "http://localhost:9000/oauth/token",
        "client_id": "mcp-test-client",
        "client_secret": "mcp-test-secret",
        "scope": "mcp:read mcp:write",
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
      }
    }
  ]
}
```

### 4. Connect and Test

Start the chatbot and connect to the OAuth protected server:

```bash
# Start the chatbot
uv run main.py

# Connect to the OAuth server (will trigger authentication flow)
You> /mcp connect oauth-protected

# The client will:
# 1. Open your browser to the authorization server
# 2. Display a login form (use testuser/testpass)
# 3. Show you the authorization code
# 4. Prompt you to paste the code back
# 5. Exchange the code for an access token
# 6. Store the token for future requests

# List available protected tools
You> /mcp tools oauth-protected

# Use the protected tools
You> Can you get my user profile information?
You> Create a secure note with title "Test" and content "Hello World"
You> List all my secure notes
You> What's my API usage this month?
```

## OAuth Flow Details

### Authorization Code Flow with PKCE

The implementation uses the OAuth 2.0 Authorization Code flow with PKCE (Proof Key for Code Exchange) for enhanced security:

1. **Authorization Request**: Client generates PKCE parameters and redirects user to authorization server
2. **User Authentication**: User authenticates with username/password on the authorization server
3. **Authorization Grant**: Server redirects back with authorization code
4. **Token Exchange**: Client exchanges authorization code + PKCE verifier for access token
5. **API Access**: Client uses access token to access protected MCP resources

### Security Features

- **PKCE (RFC 7636)**: Prevents authorization code interception attacks
- **State Parameter**: Protects against CSRF attacks
- **Client Authentication**: Validates client credentials during token exchange
- **Token Expiration**: Access tokens expire after 1 hour
- **Redirect URI Validation**: Prevents redirect attacks

## Available Tools and Resources

### Protected Tools

The OAuth protected server provides these authenticated tools:

#### `get_user_profile()`
Get the authenticated user's profile information including ID, email, name, and permissions.

```json
{
  "user_id": "testuser",
  "email": "testuser@example.com",
  "name": "Test User",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-28T10:30:00Z",
  "permissions": ["mcp:read", "mcp:write"]
}
```

#### `create_secure_note(content: str, title: str = "Untitled")`
Create a secure note stored with the user's identity.

**Parameters:**
- `content`: The note content (required)
- `title`: The note title (optional, defaults to "Untitled")

#### `list_secure_notes()`
List all secure notes for the authenticated user with previews.

#### `get_api_usage()`
Get API usage statistics for the authenticated user including request counts, token usage, and quota remaining.

### Protected Resources

#### `user://profile`
Returns the user's complete profile information and preferences.

#### `user://notes/{note_id}`
Returns individual note content by ID (e.g., `user://notes/note_1704067200`).

## Configuration Options

### Authorization Server Configuration

```bash
python examples/mcp-servers/oauth_auth_server.py --help
```

Options:
- `--port`: Port to run the server on (default: 9000)
- `--host`: Host to bind to (default: localhost)

### Protected MCP Server Configuration

```bash
python examples/mcp-servers/oauth_protected_server.py --help
```

Options:
- `--transport`: Transport method - stdio or sse (default: stdio)
- `--port`: Port for SSE transport (default: 8001)
- `--auth-server`: OAuth Authorization Server URL (default: http://localhost:9000)

### MCP Client Configuration

The client supports these OAuth configuration options in `mcp_config.json`:

```json
{
  "auth": {
    "type": "oauth",
    "authorization_url": "http://localhost:9000/oauth/authorize",
    "token_url": "http://localhost:9000/oauth/token",
    "client_id": "mcp-test-client",
    "client_secret": "mcp-test-secret",
    "scope": "mcp:read mcp:write",
    "redirect_uri": "urn:ietf:wg:oauth:2.0:oob"
  }
}
```

**Configuration Fields:**
- `authorization_url`: OAuth authorization endpoint
- `token_url`: OAuth token endpoint  
- `client_id`: OAuth client identifier
- `client_secret`: OAuth client secret
- `scope`: Requested OAuth scopes (space-separated)
- `redirect_uri`: OAuth redirect URI (use `urn:ietf:wg:oauth:2.0:oob` for manual code entry)

## Testing

### Running OAuth Server Tests

The OAuth implementation includes comprehensive tests:

```bash
# Run OAuth server tests
uv run pytest tests/test_oauth_servers.py -v

# Run with coverage
uv run pytest tests/test_oauth_servers.py --cov=examples/mcp-servers --cov-report=term-missing

# Run specific test classes
uv run pytest tests/test_oauth_servers.py::TestOAuthAuthServer -v
uv run pytest tests/test_oauth_servers.py::TestOAuthProtectedMCPServer -v
```

**Test Coverage:**
- Authorization server metadata endpoint
- Authorization code flow with PKCE
- Token exchange and validation
- Token introspection
- Error handling and security validations
- Protected MCP server token validation
- Discovery endpoints
- Integration testing

### Manual Testing

You can also test the OAuth flow manually:

```bash
# 1. Start the authorization server
uv run python examples/mcp-servers/oauth_auth_server.py &

# 2. Test discovery endpoint
curl http://localhost:9000/.well-known/oauth-authorization-server | jq

# 3. Test authorization (will return HTML login form)
curl "http://localhost:9000/oauth/authorize?client_id=mcp-test-client&redirect_uri=http://localhost:3000/callback&response_type=code&scope=mcp:read&code_challenge=test&code_challenge_method=S256"

# 4. Test token introspection
curl -X POST http://localhost:9000/oauth/introspect \
  -d "token=your-access-token" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

## Troubleshooting

### Common Issues

#### "Invalid client_id" Error
- Verify the client_id in your configuration matches "mcp-test-client"
- Check that the authorization server is running and accessible

#### "Invalid redirect_uri" Error  
- Ensure redirect_uri in config matches one of the allowed URIs
- For CLI usage, use `urn:ietf:wg:oauth:2.0:oob`

#### "Authentication required" Error
- Check that the authorization server is running
- Verify the auth_server URL in the protected server configuration
- Ensure you've completed the OAuth flow and have a valid token

#### Connection Refused
- Verify both servers are running on the expected ports
- Check firewall settings and port availability
- Ensure the auth_server URL is correct in the protected server config

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Token Storage

The authorization server stores tokens in memory, so tokens will be lost when the server restarts. For production use, implement persistent token storage.

## Production Considerations

⚠️ **Important**: These examples are for testing and development only. For production use:

1. **Use HTTPS**: All OAuth endpoints should use HTTPS in production
2. **Persistent Storage**: Replace in-memory storage with a database
3. **Real User Authentication**: Integrate with your identity provider
4. **Token Security**: Use JWT tokens with proper signing and validation
5. **Rate Limiting**: Implement rate limiting on all endpoints
6. **Audit Logging**: Log all authentication and authorization events
7. **Token Refresh**: Implement refresh tokens for long-lived sessions

## Further Reading

- [RFC 6749: OAuth 2.0 Authorization Framework](https://tools.ietf.org/html/rfc6749)
- [RFC 7636: PKCE for OAuth 2.0](https://tools.ietf.org/html/rfc7636)
- [RFC 7662: OAuth 2.0 Token Introspection](https://tools.ietf.org/html/rfc7662)
- [RFC 8414: OAuth 2.0 Authorization Server Metadata](https://tools.ietf.org/html/rfc8414)
- [RFC 9728: OAuth 2.0 for the Model Context Protocol](https://datatracker.ietf.org/doc/draft-ietf-oauth-mcp/)
- [MCP Official Documentation](https://modelcontextprotocol.io)

## Support

If you encounter issues with the OAuth implementation:

1. Check the troubleshooting section above
2. Review the test files for usage examples
3. Examine server logs for error details
4. Refer to the OAuth RFCs for protocol details