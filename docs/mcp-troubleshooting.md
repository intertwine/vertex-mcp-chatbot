# MCP Troubleshooting Guide

This guide helps resolve common issues with MCP server connections and operations.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Authentication Problems](#authentication-problems)
3. [Tool Execution Errors](#tool-execution-errors)
4. [Resource Access Issues](#resource-access-issues)
5. [Performance Problems](#performance-problems)
6. [Debugging Techniques](#debugging-techniques)

## Connection Issues

### Server Won't Connect

**Symptoms:**
- "Failed to connect to server" error
- Connection timeout
- Server appears as "Not connected" in `/mcp list`

**Solutions:**

1. **Check Server Configuration**
   ```json
   {
     "name": "my-server",
     "transport": "stdio",
     "command": ["python", "server.py"]  // Verify path is correct
   }
   ```

2. **Verify Server is Runnable**
   ```bash
   # Test the server command directly
   python server.py
   ```

3. **Check Python Version**
   ```bash
   python --version  # Must be 3.10 or higher
   ```

4. **Review Server Logs**
   - stdio servers: Check terminal output
   - HTTP servers: Check server logs
   - Enable debug mode: `export MCP_DEBUG=true`

### Connection Keeps Dropping

**Symptoms:**
- Server disconnects randomly
- "Connection reset" errors
- Need to reconnect frequently

**Solutions:**

1. **Configure Retry Settings**
   ```json
   {
     "retry": {
       "max_attempts": 5,
       "initial_delay": 2.0,
       "max_delay": 30.0,
       "jitter": true
     }
   }
   ```

2. **Check Network Stability**
   - For HTTP servers, test with curl: `curl -v http://server-url/mcp`
   - Check firewall rules
   - Verify proxy settings

3. **Increase Timeouts**
   - Some servers may need longer initialization time
   - Add delays in retry configuration

### "Server not found in configuration"

**Cause:** Server name doesn't match configuration

**Solution:**
1. List configured servers: `/mcp list`
2. Check exact server name in `mcp_config.json`
3. Server names are case-sensitive

## Authentication Problems

### OAuth Authorization Failed

**Symptoms:**
- "OAuth authorization failed" error
- Redirect URI mismatch
- Invalid client credentials

**Solutions:**

1. **Verify OAuth Configuration**
   ```json
   {
     "auth": {
       "type": "oauth",
       "client_id": "your-client-id",        // Check this
       "client_secret": "${CLIENT_SECRET}",  // Check env var
       "redirect_uri": "http://localhost:8080/callback"  // Must match exactly
     }
   }
   ```

2. **Check Environment Variables**
   ```bash
   echo $CLIENT_SECRET  # Should show value
   ```

3. **Validate Redirect URI**
   - Must match exactly what's configured in OAuth provider
   - Include port number if specified
   - Use exact protocol (http vs https)

4. **Clear Token Cache**
   ```bash
   rm -rf .mcp_tokens/
   ```

### Basic Auth Failing

**Symptoms:**
- 401 Unauthorized errors
- "Invalid credentials" messages

**Solutions:**

1. **Check Credentials**
   ```json
   {
     "auth": {
       "type": "basic",
       "username": "user",
       "password": "${PASSWORD}"  // Check env var
     }
   }
   ```

2. **Test with curl**
   ```bash
   curl -u username:password http://server/mcp
   ```

### Token Expired

**Symptoms:**
- Worked before, now failing
- 401 errors after some time

**Solutions:**

1. **Delete Cached Token**
   ```bash
   rm .mcp_tokens/server-name.json
   ```

2. **Reconnect to Server**
   ```
   /mcp disconnect server-name
   /mcp connect server-name
   ```

## Tool Execution Errors

### Tool Not Found

**Symptoms:**
- "Tool 'x' not found" error
- Tool doesn't appear in `/mcp tools`

**Solutions:**

1. **Verify Server Connection**
   ```
   /mcp list  # Check server is connected
   /mcp tools  # List available tools
   ```

2. **Check Tool Name**
   - Tool names are case-sensitive
   - Use exact name from `/mcp tools`

3. **Verify Server Provides Tool**
   - Some tools may be conditionally available
   - Check server documentation

### Tool Execution Fails

**Symptoms:**
- Tool found but execution errors
- Invalid parameters errors
- Unexpected results

**Solutions:**

1. **Check Parameter Schema**
   ```
   /mcp tools  # Shows parameter requirements
   ```

2. **Validate Input Types**
   - Numbers vs strings
   - Required vs optional parameters
   - Proper JSON formatting

3. **Review Server Permissions**
   - File system tools need access permissions
   - Network tools need connectivity
   - Check server error logs

### Tool Timeout

**Symptoms:**
- Tool execution hangs
- Timeout errors

**Solutions:**

1. **Check Server Performance**
   - Is server overloaded?
   - Network latency issues?

2. **Optimize Tool Parameters**
   - Reduce data size if possible
   - Use pagination for large results

## Resource Access Issues

### Resource Not Found

**Symptoms:**
- "Resource not found" errors
- URI not recognized

**Solutions:**

1. **Verify Resource URI**
   ```
   /mcp resources  # List available resources
   ```

2. **Check URI Format**
   - Correct scheme: `file://`, `http://`, etc.
   - Proper encoding for special characters
   - Absolute vs relative paths

3. **Verify Server Has Access**
   - File resources: Check file permissions
   - Network resources: Check connectivity

### Resource Access Denied

**Symptoms:**
- Permission denied errors
- 403 Forbidden responses

**Solutions:**

1. **Check Server Permissions**
   - File system: User running server needs read access
   - API resources: Verify authentication

2. **Review Security Settings**
   - Some servers restrict path access
   - Check server configuration for allowed paths

## Performance Problems

### Slow Tool Execution

**Symptoms:**
- Tools take long time to complete
- UI feels unresponsive

**Solutions:**

1. **Profile Server Performance**
   - Check server resource usage
   - Monitor network latency

2. **Optimize Queries**
   - Request only needed data
   - Use filters when available

3. **Consider Caching**
   - Some servers support result caching
   - Check server documentation

### High Memory Usage

**Symptoms:**
- Chatbot using excessive memory
- System becomes slow

**Solutions:**

1. **Limit Connected Servers**
   - Disconnect unused servers
   - Connect only when needed

2. **Monitor Resource Sizes**
   - Large resources consume memory
   - Consider streaming for large data

## Debugging Techniques

### Enable Debug Logging

```bash
# Enable MCP debug mode
export MCP_DEBUG=true
uv run main.py

# Enable Python logging
export PYTHONUNBUFFERED=1
export PYTHONASYNCIODEBUG=1
```

### Test Server Directly

```bash
# Test stdio server
echo '{"method": "initialize"}' | python server.py

# Test HTTP server
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "list_tools"}'
```

### Check Configuration

```python
# Validate configuration
from src.mcp_config import MCPConfig

config = MCPConfig("mcp_config.json")
for server in config.servers:
    print(f"Server: {server['name']} ({server['transport']})")
```

### Monitor Network Traffic

```bash
# For HTTP servers
tcpdump -i any -s 0 -A 'tcp port 8080'

# Using mitmproxy
mitmproxy -p 8888
# Configure server to use proxy
```

### Common Log Locations

- **Chatbot Logs**: Terminal output
- **Server Logs**: Depends on server implementation
- **OAuth Tokens**: `.mcp_tokens/*.json`
- **Python Errors**: stderr output

## Error Message Reference

### MCPManagerError

| Error | Cause | Solution |
|-------|-------|----------|
| "Server 'x' not found" | Invalid server name | Check name in config |
| "Failed to connect after N attempts" | Connection issues | Check server is running |
| "No active servers" | No servers connected | Use `/mcp connect` |
| "Tool 'x' not found on server" | Invalid tool name | List tools with `/mcp tools` |

### Authentication Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "OAuth configuration missing required fields" | Invalid OAuth config | Check all required fields |
| "Authorization code not received" | User cancelled OAuth | Retry authorization |
| "Token refresh failed" | Refresh token expired | Re-authenticate |

### Transport Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "stdio transport error" | Server crashed | Check server logs |
| "HTTP 404 Not Found" | Wrong URL | Verify endpoint URL |
| "Connection refused" | Server not running | Start server first |

## Getting Help

1. **Check Server Documentation**
   - Each MCP server has its own requirements
   - Review server-specific setup instructions

2. **Enable Debug Mode**
   ```bash
   export MCP_DEBUG=true
   ```

3. **Review Examples**
   - See `examples/mcp-servers/` for working examples
   - Compare with your configuration

4. **File an Issue**
   - Include configuration (without secrets)
   - Include error messages
   - Include debug logs if possible