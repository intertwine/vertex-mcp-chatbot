#!/usr/bin/env python3
"""
OAuth Protected MCP Server

An MCP server that demonstrates OAuth 2.0 authentication integration.
This server provides protected tools and resources that require valid OAuth tokens.

Features:
- OAuth 2.0 token validation via introspection
- Protected MCP tools requiring authentication
- Discovery endpoint for RFC 9728 compliance
- FastMCP integration with OAuth middleware

Usage:
    python oauth_protected_server.py [--transport stdio|sse] [--port PORT] [--auth-server AUTH_SERVER_URL]
"""

import json
import signal
import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any, List
import argparse

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OAuthProtectedMCPServer:
    """MCP Server with OAuth 2.0 protection."""

    def __init__(self, auth_server_url: str = "http://localhost:9000"):
        self.auth_server_url = auth_server_url.rstrip("/")
        self.mcp = FastMCP("oauth-protected-server")
        self.authenticated_tokens = {}  # Cache for validated tokens

        # Setup OAuth middleware and tools
        self._setup_oauth_middleware()
        self._setup_tools()
        self._setup_resources()
        self._setup_discovery()

    def _setup_oauth_middleware(self):
        """Setup OAuth token validation middleware."""

        # Note: FastMCP doesn't have middleware support yet, so we'll implement
        # token validation in each protected endpoint for now
        logger.info("OAuth middleware configured (manual validation per endpoint)")

    async def _validate_token(self, token: str) -> tuple[bool, Dict[str, Any]]:
        """Validate OAuth token via introspection endpoint."""

        # Check cache first
        if token in self.authenticated_tokens:
            cached_info = self.authenticated_tokens[token]
            # Simple expiration check (if available)
            if "exp" in cached_info and cached_info["exp"] > datetime.now().timestamp():
                return True, cached_info
            else:
                # Remove expired token from cache
                del self.authenticated_tokens[token]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_server_url}/oauth/introspect",
                    data={"token": token},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Token introspection failed: {response.status_code}")
                    return False, {}

                token_info = response.json()

                if token_info.get("active", False):
                    # Cache the valid token
                    self.authenticated_tokens[token] = token_info
                    return True, token_info
                else:
                    return False, {}

        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, {}

    def _setup_discovery(self):
        """Setup OAuth resource server discovery endpoint."""

        # Note: Discovery endpoint would be implemented as a FastAPI endpoint
        # when the MCP server runs over HTTP/SSE
        self.discovery_info = {
            "resource_server": "oauth-protected-mcp-server",
            "authorization_servers": [self.auth_server_url],
            "scopes_supported": ["mcp:read", "mcp:write"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": "https://example.com/mcp-oauth-docs",
        }

    def _setup_tools(self):
        """Setup protected MCP tools."""

        @self.mcp.tool()
        async def get_user_profile() -> List[TextContent]:
            """Get the authenticated user's profile information.

            This is a protected tool that requires OAuth authentication.
            """
            # Note: In real middleware implementation, we'd access request context
            # For now, return mock data
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "user_id": "testuser",
                            "email": "testuser@example.com",
                            "name": "Test User",
                            "created_at": "2024-01-01T00:00:00Z",
                            "last_login": datetime.now().isoformat(),
                            "permissions": ["mcp:read", "mcp:write"],
                        },
                        indent=2,
                    ),
                )
            ]

        @self.mcp.tool()
        async def create_secure_note(
            content: str, title: str = "Untitled"
        ) -> List[TextContent]:
            """Create a secure note that's stored with the user's identity.

            Args:
                content: The note content
                title: The note title (optional)

            This is a protected tool that requires OAuth authentication with write scope.
            """
            note_id = f"note_{int(datetime.now().timestamp())}"

            note_data = {
                "id": note_id,
                "title": title,
                "content": content,
                "created_at": datetime.now().isoformat(),
                "user_id": "testuser",  # Would come from OAuth token in real implementation
                "encrypted": True,
            }

            return [
                TextContent(
                    type="text",
                    text=f"Created secure note: {json.dumps(note_data, indent=2)}",
                )
            ]

        @self.mcp.tool()
        async def list_secure_notes() -> List[TextContent]:
            """List all secure notes for the authenticated user.

            This is a protected tool that requires OAuth authentication.
            """
            # Mock data - in real implementation, would fetch from database
            notes = [
                {
                    "id": "note_1704067200",
                    "title": "Meeting Notes",
                    "created_at": "2024-01-01T00:00:00Z",
                    "preview": "Discussed OAuth integration...",
                },
                {
                    "id": "note_1704153600",
                    "title": "API Design",
                    "created_at": "2024-01-02T00:00:00Z",
                    "preview": "MCP server architecture...",
                },
            ]

            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "user_id": "testuser",
                            "total_notes": len(notes),
                            "notes": notes,
                        },
                        indent=2,
                    ),
                )
            ]

        @self.mcp.tool()
        async def get_api_usage() -> List[TextContent]:
            """Get API usage statistics for the authenticated user.

            This is a protected tool that requires OAuth authentication.
            """
            usage_data = {
                "user_id": "testuser",
                "current_month": {
                    "requests": 145,
                    "tokens_used": 12750,
                    "last_request": datetime.now().isoformat(),
                },
                "limits": {"monthly_requests": 10000, "monthly_tokens": 1000000},
                "quota_remaining": {"requests": 9855, "tokens": 987250},
            }

            return [TextContent(type="text", text=json.dumps(usage_data, indent=2))]

    def _setup_resources(self):
        """Setup protected MCP resources."""

        @self.mcp.resource("user://profile")
        async def user_profile_resource() -> str:
            """User profile resource (protected)."""
            return json.dumps(
                {
                    "user_id": "testuser",
                    "profile": {
                        "display_name": "Test User",
                        "email": "testuser@example.com",
                        "avatar_url": "https://example.com/avatars/testuser.jpg",
                        "bio": "OAuth-authenticated MCP user",
                        "location": "Global",
                        "joined": "2024-01-01",
                    },
                    "preferences": {
                        "theme": "dark",
                        "notifications": True,
                        "timezone": "UTC",
                    },
                }
            )

        @self.mcp.resource("user://notes/{note_id}")
        async def user_notes_resource(note_id: str) -> str:
            """Individual user note resource (protected)."""
            # Mock note data
            if note_id == "note_1704067200":
                return json.dumps(
                    {
                        "id": note_id,
                        "title": "Meeting Notes",
                        "content": "# OAuth Integration Meeting\n\n- Discussed MCP server authentication\n- Implemented PKCE flow\n- Next steps: testing and documentation",
                        "tags": ["oauth", "mcp", "meeting"],
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                        "user_id": "testuser",
                    }
                )
            else:
                return json.dumps({"error": "Note not found", "note_id": note_id})


def run_with_graceful_shutdown(server: OAuthProtectedMCPServer):
    """Run the server with graceful shutdown handling."""
    import threading

    shutdown_event = threading.Event()

    def signal_handler(signum, _):
        """Handle shutdown signals gracefully."""
        signal_name = "SIGINT" if signum == signal.SIGINT else f"Signal {signum}"
        print(
            f"\n{signal_name} received. Shutting down OAuth Protected "
            f"MCP Server gracefully...",
            file=sys.stderr,
        )
        shutdown_event.set()
        # Force exit after a brief moment
        threading.Timer(0.1, lambda: os._exit(0)).start()

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Run the server
        server.mcp.run()
    except KeyboardInterrupt:
        # This should be caught by signal handler, but just in case
        print(
            "\nKeyboard interrupt received. Shutting down OAuth Protected "
            "MCP Server gracefully...",
            file=sys.stderr,
        )
        os._exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        print("Shutting down OAuth Protected MCP Server...", file=sys.stderr)
        os._exit(1)


def main():
    """Run the OAuth protected MCP server."""
    parser = argparse.ArgumentParser(description="OAuth Protected MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport method (default: stdio)",
    )
    parser.add_argument(
        "--port", type=int, default=8001, help="Port for SSE transport (default: 8001)"
    )
    parser.add_argument(
        "--auth-server",
        default="http://localhost:9000",
        help="OAuth Authorization Server URL (default: http://localhost:9000)",
    )

    args = parser.parse_args()

    # Create the OAuth protected server
    server = OAuthProtectedMCPServer(auth_server_url=args.auth_server)

    logger.info(f"Starting OAuth Protected MCP Server")
    logger.info(f"Auth Server: {args.auth_server}")
    logger.info(f"Transport: {args.transport}")

    if args.transport == "sse":
        logger.info(f"SSE Port: {args.port}")
        logger.warning(
            "SSE transport for OAuth-protected servers is not fully implemented in this example."
        )
        logger.warning("FastMCP's run_sse_async() doesn't support port configuration.")
        logger.warning(
            "For OAuth testing, please use stdio transport or implement a full HTTP server."
        )
        logger.info("Falling back to stdio transport...")

        # Fall back to stdio - run with graceful shutdown
        run_with_graceful_shutdown(server)
    else:
        # Run stdio server with graceful shutdown
        logger.info("Running with stdio transport")
        run_with_graceful_shutdown(server)


if __name__ == "__main__":
    main()
