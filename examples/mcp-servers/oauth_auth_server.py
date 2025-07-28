#!/usr/bin/env python3
"""
OAuth Authorization Server for MCP

A simple OAuth 2.0 Authorization Server implementation for testing MCP OAuth authentication.
This server provides the standard OAuth endpoints needed for the authorization code flow with PKCE.

Features:
- OAuth 2.0 Authorization Code flow with PKCE
- Token introspection endpoint
- Discovery endpoints for RFC 9728 compliance
- Simple credential-based authentication
- In-memory token storage (for testing only)

Usage:
    python oauth_auth_server.py [--port PORT]
"""

import base64
import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OAuthAuthServer:
    """OAuth 2.0 Authorization Server for MCP testing."""

    def __init__(self):
        self.app = FastAPI(
            title="MCP OAuth Authorization Server",
            description="OAuth 2.0 Authorization Server for testing MCP authentication",
            version="0.1.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # For testing only
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # In-memory storage (for testing only)
        self.clients = {
            "mcp-test-client": {
                "client_secret": "mcp-test-secret",
                "redirect_uris": [
                    "http://localhost:3000/callback",
                    "http://127.0.0.1:3000/callback",
                    "urn:ietf:wg:oauth:2.0:oob",
                ],
            }
        }

        self.authorization_codes = (
            {}
        )  # code -> {client_id, redirect_uri, user_id, code_challenge, scope, expires_at}
        self.access_tokens = {}  # token -> {client_id, user_id, scope, expires_at}

        # Test user credentials
        self.users = {"testuser": "testpass"}

        self._setup_routes()

    def _setup_routes(self):
        """Setup OAuth endpoints."""

        @self.app.get("/.well-known/oauth-authorization-server")
        async def authorization_server_metadata():
            """OAuth Authorization Server Metadata (RFC 8414)."""
            base_url = "http://localhost:9000"  # TODO: Make configurable
            return {
                "issuer": base_url,
                "authorization_endpoint": f"{base_url}/oauth/authorize",
                "token_endpoint": f"{base_url}/oauth/token",
                "introspection_endpoint": f"{base_url}/oauth/introspect",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256"],
                "scopes_supported": ["mcp:read", "mcp:write"],
                "token_endpoint_auth_methods_supported": [
                    "client_secret_post",
                    "client_secret_basic",
                ],
            }

        @self.app.get("/oauth/authorize")
        async def authorize(
            client_id: str = Query(...),
            redirect_uri: str = Query(...),
            response_type: str = Query(...),
            scope: str = Query(...),
            state: str = Query(None),
            code_challenge: str = Query(None),
            code_challenge_method: str = Query(None),
        ):
            """OAuth authorization endpoint."""

            # Validate client
            if client_id not in self.clients:
                raise HTTPException(status_code=400, detail="Invalid client_id")

            client = self.clients[client_id]
            if redirect_uri not in client["redirect_uris"]:
                raise HTTPException(status_code=400, detail="Invalid redirect_uri")

            if response_type != "code":
                raise HTTPException(status_code=400, detail="Unsupported response_type")

            # For PKCE, code_challenge is required
            if not code_challenge or code_challenge_method != "S256":
                raise HTTPException(
                    status_code=400,
                    detail="PKCE required: code_challenge with S256 method",
                )

            # Return login form
            login_form = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>MCP OAuth Login</title>
                <style>
                    body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }}
                    .form-group {{ margin-bottom: 15px; }}
                    label {{ display: block; margin-bottom: 5px; }}
                    input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
                    button {{ background: #007cba; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; }}
                    button:hover {{ background: #005a8b; }}
                    .info {{ background: #f0f8ff; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="info">
                    <h2>MCP OAuth Authorization</h2>
                    <p><strong>Client:</strong> {client_id}</p>
                    <p><strong>Scope:</strong> {scope}</p>
                    <p><strong>Redirect URI:</strong> {redirect_uri}</p>
                </div>

                <form method="post" action="/oauth/authorize">
                    <input type="hidden" name="client_id" value="{client_id}">
                    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                    <input type="hidden" name="response_type" value="{response_type}">
                    <input type="hidden" name="scope" value="{scope}">
                    <input type="hidden" name="state" value="{state or ''}">
                    <input type="hidden" name="code_challenge" value="{code_challenge}">
                    <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">

                    <div class="form-group">
                        <label for="username">Username:</label>
                        <input type="text" id="username" name="username" required placeholder="testuser">
                    </div>

                    <div class="form-group">
                        <label for="password">Password:</label>
                        <input type="password" id="password" name="password" required placeholder="testpass">
                    </div>

                    <button type="submit">Authorize</button>
                </form>

                <p><small>Test credentials: username=testuser, password=testpass</small></p>
            </body>
            </html>
            """
            return HTMLResponse(content=login_form)

        @self.app.post("/oauth/authorize")
        async def authorize_post(
            client_id: str = Form(...),
            redirect_uri: str = Form(...),
            response_type: str = Form(...),
            scope: str = Form(...),
            state: str = Form(None),
            code_challenge: str = Form(...),
            code_challenge_method: str = Form(...),
            username: str = Form(...),
            password: str = Form(...),
        ):
            """Handle authorization form submission."""

            # Authenticate user
            if username not in self.users or self.users[username] != password:
                raise HTTPException(status_code=401, detail="Invalid credentials")

            # Generate authorization code
            auth_code = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(minutes=10)

            self.authorization_codes[auth_code] = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "user_id": username,
                "code_challenge": code_challenge,
                "scope": scope,
                "expires_at": expires_at,
            }

            # Build redirect URL
            params = {"code": auth_code}
            if state:
                params["state"] = state

            redirect_url = f"{redirect_uri}?{urlencode(params)}"
            logger.info(f"Redirecting to: {redirect_url}")

            return RedirectResponse(url=redirect_url, status_code=302)

        @self.app.post("/oauth/token")
        async def token(
            grant_type: str = Form(...),
            code: str = Form(None),
            redirect_uri: str = Form(None),
            client_id: str = Form(None),
            client_secret: str = Form(None),
            code_verifier: str = Form(None),
        ):
            """OAuth token endpoint."""

            if grant_type != "authorization_code":
                raise HTTPException(status_code=400, detail="Unsupported grant_type")

            # Validate authorization code
            if code not in self.authorization_codes:
                raise HTTPException(
                    status_code=400, detail="Invalid authorization code"
                )

            auth_data = self.authorization_codes[code]

            # Check expiration
            if datetime.now() > auth_data["expires_at"]:
                del self.authorization_codes[code]
                raise HTTPException(
                    status_code=400, detail="Authorization code expired"
                )

            # Validate client
            if client_id != auth_data["client_id"]:
                raise HTTPException(status_code=400, detail="Client mismatch")

            if client_id not in self.clients:
                raise HTTPException(status_code=400, detail="Invalid client")

            client = self.clients[client_id]
            if client_secret != client["client_secret"]:
                raise HTTPException(
                    status_code=401, detail="Invalid client credentials"
                )

            # Validate redirect URI
            if redirect_uri != auth_data["redirect_uri"]:
                raise HTTPException(status_code=400, detail="Redirect URI mismatch")

            # Verify PKCE code verifier
            if not code_verifier:
                raise HTTPException(
                    status_code=400, detail="PKCE code_verifier required"
                )

            # Verify code challenge
            verifier_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            challenge = (
                base64.urlsafe_b64encode(verifier_hash).decode("utf-8").rstrip("=")
            )

            if challenge != auth_data["code_challenge"]:
                raise HTTPException(
                    status_code=400, detail="Invalid PKCE code_verifier"
                )

            # Generate access token
            access_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=1)

            self.access_tokens[access_token] = {
                "client_id": client_id,
                "user_id": auth_data["user_id"],
                "scope": auth_data["scope"],
                "expires_at": expires_at,
            }

            # Clean up authorization code
            del self.authorization_codes[code]

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": auth_data["scope"],
            }

        @self.app.post("/oauth/introspect")
        async def introspect(
            token: str = Form(...),
            client_id: str = Form(None),
            client_secret: str = Form(None),
        ):
            """OAuth token introspection endpoint (RFC 7662)."""

            # Validate client (optional for introspection)
            if client_id and client_id in self.clients:
                client = self.clients[client_id]
                if client_secret != client["client_secret"]:
                    raise HTTPException(
                        status_code=401, detail="Invalid client credentials"
                    )

            # Check if token exists and is valid
            if token not in self.access_tokens:
                return {"active": False}

            token_data = self.access_tokens[token]

            # Check expiration
            if datetime.now() > token_data["expires_at"]:
                del self.access_tokens[token]
                return {"active": False}

            return {
                "active": True,
                "client_id": token_data["client_id"],
                "username": token_data["user_id"],
                "scope": token_data["scope"],
                "exp": int(token_data["expires_at"].timestamp()),
            }

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {"status": "healthy", "service": "oauth-auth-server"}


def main():
    """Run the OAuth Authorization Server."""
    import argparse

    parser = argparse.ArgumentParser(description="MCP OAuth Authorization Server")
    parser.add_argument(
        "--port", type=int, default=9000, help="Port to run the server on"
    )
    parser.add_argument("--host", default="localhost", help="Host to bind to")

    args = parser.parse_args()

    server = OAuthAuthServer()

    logger.info(f"Starting OAuth Authorization Server on {args.host}:{args.port}")
    logger.info("Test client credentials:")
    logger.info("  Client ID: mcp-test-client")
    logger.info("  Client Secret: mcp-test-secret")
    logger.info("  User: testuser / testpass")

    uvicorn.run(server.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
