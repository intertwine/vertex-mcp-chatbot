# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Full Model Context Protocol (MCP) client implementation
- Support for stdio, HTTP, and SSE transports
- OAuth 2.0 authentication support with PKCE
- Multi-server coordination with priority system
- Connection retry logic with exponential backoff
- Environment variable substitution in MCP configuration
- Scrollable output for long MCP listings
- Example MCP servers (filesystem and weather)
- Comprehensive documentation suite
- 316 tests with full coverage

### Changed
- Updated Python requirement to 3.10+ (required by MCP SDK)
- Improved error handling and user feedback
- Enhanced terminal UI with scrollable content

### Fixed
- Terminal compatibility issues with prompt_toolkit
- Async/sync compatibility in MCP operations
- Resource listing for static vs template resources
- Test side effects creating files in project directory

## [0.1.0] - 2025-01-28

### Added
- Initial release with basic Gemini chatbot functionality
- Interactive CLI interface with Rich terminal UI
- Gemini model integration via Google Vertex AI
- Markdown rendering for AI responses
- Conversation history persistence
- Command system with built-in commands
- Auto-suggestions from command history
- Multi-line input support
- Comprehensive test suite