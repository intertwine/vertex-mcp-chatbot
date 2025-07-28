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

### Phase 4: Polish and Documentation ✅ MOSTLY COMPLETE
- **Increment 1**: Example MCP Servers ✅ COMPLETE
  - Created examples/mcp-servers/ directory
  - Implemented filesystem server (stdio) using FastMCP
  - Implemented weather server (stdio) using FastMCP
  - Created example mcp_config.json
  - Added examples README with quickstart guide
- **Increment 2**: Critical Bug Fixes and Improvements ✅ COMPLETE
  - Fixed MCP tool detection for Gemini's "MCP Tool Call: tool_name(args)" format
  - Fixed Pydantic object handling (CallToolResult, resources, prompts)
  - Simplified MCP manager to use on-demand sessions (avoiding async context issues)
  - Fixed terminal compatibility issues (errno 22 with prompt_toolkit)
  - Added session management when MCP servers connect/disconnect
  - Fixed multi-server tool handling and system instruction updates
  - Fixed resource listing (static resources vs resource templates)
  - Fixed prompt result handling for Pydantic GetPromptResult objects
- **Increment 3**: Test Updates ✅ COMPLETE (189/189 tests passing, 0 warnings)
  - ✅ Updated all MCP manager tests for simplified architecture
  - ✅ Updated all HTTP transport tests for new patterns
  - ✅ Fixed multi-server coordination tests
  - ✅ Updated tests to handle Pydantic objects instead of dicts
  - ✅ Fixed async/sync compatibility issues in tests
  - ✅ Fixed OAuth authentication tests
  - ✅ Fixed retry logic tests
  - ✅ Fixed resource handling tests
  - ✅ Fixed coroutine warning issues with proper mocking
  - ✅ Created test utilities for async handling (test_async_utils.py)
  - ✅ Added simplified OAuth tests (test_mcp_oauth_simplified.py)
  - ✅ Suppressed all remaining coroutine warnings with pytest filters
- **Increment 4**: Documentation Updates (TODO)
  - Update user documentation with examples
  - Update API documentation
  - Update README with current features

## Key Architecture Decisions
1. **AsyncExitStack Pattern**: Following official SDK for connection lifecycle
2. **Optional MCP Support**: Graceful fallback when MCP not available
3. **Natural Language Integration**: No special syntax for tool calls
4. **Sync/Async Bridge**: Using asyncio.run() for sync wrapper methods
5. **Transport Abstraction**: Unified interface for stdio/HTTP/SSE
6. **On-Demand Sessions**: Create MCP sessions per operation (simplified from persistent)
7. **Pydantic Object Handling**: MCP SDK returns Pydantic objects, not dicts
8. **Resource Templates**: Parameterized resources use list_resource_templates()
9. **Session Refresh**: Clear Gemini chat when MCP servers change

## Current Status (2025-01-28)
- ✅ Phase 1: Core infrastructure complete
- ✅ Phase 2: Chat flow integration complete
- ✅ Phase 3: Advanced features complete
  - All transports (stdio, HTTP, SSE) supported
  - Multi-server coordination with priorities
  - OAuth 2.0 authentication
  - Connection retry with exponential backoff
- ✅ Phase 4 Increment 1 & 2: Example servers and critical fixes complete
  - FastMCP-based example servers working
  - All major MCP features (tools, resources, prompts) functional
  - Gemini integration fully operational
- ✅ Phase 4 Increment 3: Test updates COMPLETE (189/189 tests passing, 0 warnings)
  - Major test suite refactoring for simplified architecture complete
  - All tests updated for Pydantic object handling
  - Async/sync compatibility issues resolved
  - Event loop isolation fixed to prevent test conflicts
  - Coroutine warning issues resolved with proper mocking patterns
  - Test utilities created for consistent async handling
  - All pytest warnings suppressed with targeted filters

## Next Steps
2. **Phase 4 Increment 4**: Documentation updates
   - Update user documentation with working examples
   - Update API documentation
   - Update README with current features
3. Performance optimization and caching (future)
4. Additional example servers (future)

## Important Notes
- Uses MCP Python SDK (requires Python 3.10+)
- Project uses `uv` package manager, not pip
- All phases follow TDD approach: tests first, then implementation
- Documentation updates required after each increment
- Test event loop isolation: Tests that mock `asyncio.run()` create new event loops to avoid conflicts