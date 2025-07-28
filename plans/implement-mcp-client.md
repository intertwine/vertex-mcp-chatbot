# MCP Client Implementation Plan

> **Note**: For detailed implementation log, see [implement-mcp-client-detailed.md](./implement-mcp-client-detailed.md)

## Overview
Modify the Gemini chatbot to act as an MCP (Model Context Protocol) client, enabling connection to MCP servers for tools, resources, and prompts.

## Implementation Phases

### Phase 1: Core MCP Infrastructure ✅ COMPLETE
- Created `src/mcp_config.py` - Configuration loading from JSON
- Created `src/mcp_manager.py` - MCP client session management with AsyncExitStack pattern
- Added basic `/mcp` commands (connect, list, disconnect)
- Updated Python to 3.10+ (MCP requirement)
- 116 tests passing

### Phase 2: Integration with Chat Flow ✅ COMPLETE
- **Increment 1**: Tool execution - Natural language tool detection and execution
- **Increment 2**: Resource embedding - Automatic URI detection and content inclusion
- **Increment 3**: Prompt templates - Template listing and usage with argument parsing
- Gemini now aware of MCP tools/resources via system instructions
- 145 tests passing

### Phase 3: Advanced Features ✅ COMPLETE
- **Increment 1**: HTTP/SSE transport ✅ COMPLETE
  - Implemented streamablehttp_client and sse_client support
  - Basic Auth and custom headers
  - Session ID management for HTTP
  - 154 tests passing
- **Increment 2**: Multi-server coordination ✅ COMPLETE
  - Server priority system for tool conflict resolution
  - Parallel operations with asyncio.gather()
  - Error isolation between servers
  - `/mcp tools` command shows conflicts and priorities
  - 164 tests passing
- **Increment 3**: OAuth authentication ✅ COMPLETE
  - OAuth 2.0 authorization code flow with PKCE
  - Token storage and automatic refresh
  - Support for confidential and public clients
  - Interactive authorization flow
  - 176 tests passing
- **Increment 4**: Connection retry logic ✅ COMPLETE
  - Exponential backoff with configurable parameters
  - Jitter to prevent thundering herd
  - Per-server retry configuration
  - Clear retry attempt logging
  - 187 tests passing

### Phase 4: Polish and Documentation (TODO)
- Comprehensive user documentation
- Example MCP servers
- Performance optimization

## Key Architecture Decisions
1. **AsyncExitStack Pattern**: Following official SDK for connection lifecycle
2. **Optional MCP Support**: Graceful fallback when MCP not available
3. **Natural Language Integration**: No special syntax for tool calls
4. **Sync/Async Bridge**: Using asyncio.run() for sync wrapper methods
5. **Transport Abstraction**: Unified interface for stdio/HTTP/SSE

## Current Status (2025-01-28)
- ✅ Phase 1: Core infrastructure complete
- ✅ Phase 2: Chat flow integration complete
- ✅ Phase 3: Advanced features complete
  - All transports (stdio, HTTP, SSE) supported
  - Multi-server coordination with priorities
  - OAuth 2.0 authentication
  - Connection retry with exponential backoff
- All 187 tests passing

## Next Steps
1. Phase 4: Polish and documentation
2. Create example MCP servers for testing
3. Comprehensive user guide with tutorials
4. Performance optimization and caching

## Important Notes
- Uses MCP Python SDK (requires Python 3.10+)
- Project uses `uv` package manager, not pip
- All phases follow TDD approach: tests first, then implementation
- Documentation updates required after each increment