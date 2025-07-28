# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please follow these steps:

1. **DO NOT** open a public issue
2. Email the details to the project maintainer (see CODE_OF_CONDUCT.md for contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Security Considerations

When using this chatbot with MCP servers:

### Authentication
- Store sensitive credentials in environment variables, not in code
- Use `.env` files for local development (never commit these)
- OAuth tokens are stored in `.mcp_tokens/` - ensure this directory is gitignored

### MCP Server Security
- Always validate input in MCP servers
- Implement path restrictions for filesystem operations
- Use authentication for production MCP servers
- Limit tool permissions to what's necessary

### Network Security
- Use HTTPS for HTTP/SSE transports in production
- Verify SSL certificates
- Be cautious with self-signed certificates

### Example Server Notes
The example servers in `examples/mcp-servers/` are for demonstration only:
- The filesystem server has basic path validation but should be enhanced for production
- The weather server uses mock data and is safe
- The OAuth servers use test credentials - replace for production use

## Best Practices

1. **Environment Variables**: Use `${VAR_NAME}` syntax in MCP config for secrets
2. **File Permissions**: Restrict access to `.mcp_tokens/` and `.env` files
3. **Input Validation**: Always validate and sanitize user input in MCP servers
4. **Least Privilege**: Grant minimal necessary permissions to MCP tools
5. **Audit Logging**: Log MCP tool usage for security monitoring