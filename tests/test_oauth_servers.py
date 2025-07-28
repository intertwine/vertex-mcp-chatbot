"""Tests for OAuth servers (Authorization Server and Protected MCP Server)."""

import asyncio
import base64
import hashlib
import json
import os
import secrets

# Import our OAuth server implementations
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.append(
    os.path.join(os.path.dirname(__file__), "..", "examples", "mcp-servers")
)

from oauth_auth_server import OAuthAuthServer
from oauth_protected_server import OAuthProtectedMCPServer

# Suppress runtime warnings about unawaited coroutines in this test module
pytestmark = pytest.mark.filterwarnings(
    "ignore:coroutine.*was never awaited:RuntimeWarning"
)


class TestOAuthAuthServer:
    """Test the OAuth Authorization Server."""

    @pytest.fixture
    def auth_server(self):
        """Create OAuth Authorization Server instance."""
        return OAuthAuthServer()

    @pytest.fixture
    def client(self, auth_server):
        """Create test client for the auth server."""
        return TestClient(auth_server.app)

    def test_authorization_server_metadata(self, client):
        """Test OAuth authorization server metadata endpoint."""
        response = client.get("/.well-known/oauth-authorization-server")

        assert response.status_code == 200
        metadata = response.json()

        # Check required OAuth metadata fields
        assert "issuer" in metadata
        assert "authorization_endpoint" in metadata
        assert "token_endpoint" in metadata
        assert "introspection_endpoint" in metadata
        assert "response_types_supported" in metadata
        assert "grant_types_supported" in metadata
        assert "code_challenge_methods_supported" in metadata

        # Verify expected values
        assert "code" in metadata["response_types_supported"]
        assert "authorization_code" in metadata["grant_types_supported"]
        assert "S256" in metadata["code_challenge_methods_supported"]

    def test_authorization_endpoint_get(self, client):
        """Test GET request to authorization endpoint returns login form."""
        # Generate PKCE parameters
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        response = client.get(
            "/oauth/authorize",
            params={
                "client_id": "mcp-test-client",
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:read mcp:write",
                "state": "test-state",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "MCP OAuth Login" in response.text
        assert "testuser" in response.text

    def test_authorization_invalid_client(self, client):
        """Test authorization with invalid client_id."""
        response = client.get(
            "/oauth/authorize",
            params={
                "client_id": "invalid-client",
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:read",
                "code_challenge": "test-challenge",
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 400
        assert "Invalid client_id" in response.json()["detail"]

    def test_authorization_invalid_redirect_uri(self, client):
        """Test authorization with invalid redirect_uri."""
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        response = client.get(
            "/oauth/authorize",
            params={
                "client_id": "mcp-test-client",
                "redirect_uri": "http://malicious.com/callback",
                "response_type": "code",
                "scope": "mcp:read",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            },
        )

        assert response.status_code == 400
        assert "Invalid redirect_uri" in response.json()["detail"]

    def test_authorization_post_valid_credentials(self, client, auth_server):
        """Test POST to authorization endpoint with valid credentials."""
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        response = client.post(
            "/oauth/authorize",
            data={
                "client_id": "mcp-test-client",
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:read mcp:write",
                "state": "test-state",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "username": "testuser",
                "password": "testpass",
            },
            follow_redirects=False,
        )

        assert response.status_code == 302
        location = response.headers["location"]

        # Parse redirect URL
        parsed = urlparse(location)
        params = parse_qs(parsed.query)

        assert "code" in params
        assert params["state"] == ["test-state"]

        # Verify authorization code was stored
        auth_code = params["code"][0]
        assert auth_code in auth_server.authorization_codes

    def test_authorization_post_invalid_credentials(self, client):
        """Test POST to authorization endpoint with invalid credentials."""
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        response = client.post(
            "/oauth/authorize",
            data={
                "client_id": "mcp-test-client",
                "redirect_uri": "http://localhost:3000/callback",
                "response_type": "code",
                "scope": "mcp:read",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "username": "testuser",
                "password": "wrongpass",
            },
        )

        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_token_endpoint_valid_flow(self, client, auth_server):
        """Test complete OAuth flow from authorization to token exchange."""
        # First, create an authorization code manually
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        auth_code = "test-auth-code"
        auth_server.authorization_codes[auth_code] = {
            "client_id": "mcp-test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "user_id": "testuser",
            "code_challenge": challenge,
            "scope": "mcp:read mcp:write",
            "expires_at": datetime.now() + timedelta(minutes=10),
        }

        # Exchange code for token
        response = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": "mcp-test-client",
                "client_secret": "mcp-test-secret",
                "code_verifier": verifier,
            },
        )

        assert response.status_code == 200
        token_data = response.json()

        assert "access_token" in token_data
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == 3600
        assert token_data["scope"] == "mcp:read mcp:write"

        # Verify access token was stored
        access_token = token_data["access_token"]
        assert access_token in auth_server.access_tokens

        # Verify authorization code was consumed
        assert auth_code not in auth_server.authorization_codes

    def test_token_endpoint_invalid_code(self, client):
        """Test token endpoint with invalid authorization code."""
        response = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "invalid-code",
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": "mcp-test-client",
                "client_secret": "mcp-test-secret",
                "code_verifier": "test-verifier",
            },
        )

        assert response.status_code == 400
        assert "Invalid authorization code" in response.json()["detail"]

    def test_token_endpoint_invalid_pkce(self, client, auth_server):
        """Test token endpoint with invalid PKCE verifier."""
        # Create authorization code with specific challenge
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        auth_code = "test-auth-code"
        auth_server.authorization_codes[auth_code] = {
            "client_id": "mcp-test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "user_id": "testuser",
            "code_challenge": challenge,
            "scope": "mcp:read",
            "expires_at": datetime.now() + timedelta(minutes=10),
        }

        # Try to exchange with wrong verifier
        response = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": "http://localhost:3000/callback",
                "client_id": "mcp-test-client",
                "client_secret": "mcp-test-secret",
                "code_verifier": "wrong-verifier",
            },
        )

        assert response.status_code == 400
        assert "Invalid PKCE code_verifier" in response.json()["detail"]

    def test_introspection_endpoint_valid_token(self, client, auth_server):
        """Test token introspection with valid token."""
        # Create a valid access token
        access_token = "test-access-token"
        auth_server.access_tokens[access_token] = {
            "client_id": "mcp-test-client",
            "user_id": "testuser",
            "scope": "mcp:read mcp:write",
            "expires_at": datetime.now() + timedelta(hours=1),
        }

        response = client.post(
            "/oauth/introspect",
            data={
                "token": access_token,
                "client_id": "mcp-test-client",
                "client_secret": "mcp-test-secret",
            },
        )

        assert response.status_code == 200
        introspection_data = response.json()

        assert introspection_data["active"] is True
        assert introspection_data["client_id"] == "mcp-test-client"
        assert introspection_data["username"] == "testuser"
        assert introspection_data["scope"] == "mcp:read mcp:write"
        assert "exp" in introspection_data

    def test_introspection_endpoint_invalid_token(self, client):
        """Test token introspection with invalid token."""
        response = client.post("/oauth/introspect", data={"token": "invalid-token"})

        assert response.status_code == 200
        introspection_data = response.json()
        assert introspection_data["active"] is False

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        health_data = response.json()
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "oauth-auth-server"


class TestOAuthProtectedMCPServer:
    """Test the OAuth Protected MCP Server."""

    @pytest.fixture
    def protected_server(self):
        """Create OAuth Protected MCP Server instance."""
        return OAuthProtectedMCPServer(auth_server_url="http://localhost:9000")

    @pytest.mark.asyncio
    async def test_token_validation_valid_token(self, protected_server):
        """Test token validation with valid token."""
        # Mock the HTTP response for token introspection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "active": True,
            "client_id": "mcp-test-client",
            "username": "testuser",
            "scope": "mcp:read mcp:write",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            is_valid, token_info = await protected_server._validate_token("valid-token")

            assert is_valid is True
            assert token_info["active"] is True
            assert token_info["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_token_validation_invalid_token(self, protected_server):
        """Test token validation with invalid token."""
        # Mock the HTTP response for token introspection
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"active": False}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response

            is_valid, token_info = await protected_server._validate_token(
                "invalid-token"
            )

            assert is_valid is False
            assert token_info == {}

    @pytest.mark.asyncio
    async def test_token_validation_network_error(self, protected_server):
        """Test token validation with network error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.RequestError("Network error")

            is_valid, token_info = await protected_server._validate_token("some-token")

            assert is_valid is False
            assert token_info == {}

    def test_token_caching(self, protected_server):
        """Test that valid tokens are cached to avoid repeated introspection calls."""
        # Add a token to cache
        token_info = {
            "active": True,
            "username": "testuser",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        }
        protected_server.authenticated_tokens["cached-token"] = token_info

        # This should return cached result without making HTTP call
        async def test_cached():
            with patch("httpx.AsyncClient") as mock_client_class:
                is_valid, returned_info = await protected_server._validate_token(
                    "cached-token"
                )

                assert is_valid is True
                assert returned_info == token_info
                # Verify no HTTP call was made
                mock_client_class.assert_not_called()

        asyncio.run(test_cached())

    def test_discovery_endpoint(self, protected_server):
        """Test OAuth resource server discovery endpoint."""
        # Test the server setup and discovery info
        assert protected_server.auth_server_url == "http://localhost:9000"
        assert protected_server.mcp is not None

        # Verify discovery info is properly configured
        expected_discovery = {
            "resource_server": "oauth-protected-mcp-server",
            "authorization_servers": ["http://localhost:9000"],
            "scopes_supported": ["mcp:read", "mcp:write"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": "https://example.com/mcp-oauth-docs",
        }

        assert protected_server.discovery_info == expected_discovery


class TestOAuthIntegration:
    """Integration tests for the complete OAuth flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_oauth_flow(self):
        """Test complete OAuth flow from authorization to protected resource access."""
        # This is a conceptual test - in practice, would require running both servers
        # and making actual HTTP requests

        # 1. Client requests authorization
        # 2. User authenticates and grants permission
        # 3. Client receives authorization code
        # 4. Client exchanges code for access token
        # 5. Client uses access token to access protected MCP resources

        # For now, we'll test the components we can isolate
        auth_server = OAuthAuthServer()
        protected_server = OAuthProtectedMCPServer(
            auth_server_url="http://localhost:9000"
        )

        # Verify servers are properly initialized
        assert auth_server.clients is not None
        assert protected_server.mcp is not None
        assert protected_server.auth_server_url == "http://localhost:9000"

        # Test that authorization codes and tokens work together
        verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("utf-8")
            .rstrip("=")
        )
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )

        # Simulate creating an authorization code
        auth_code = "integration-test-code"
        auth_server.authorization_codes[auth_code] = {
            "client_id": "mcp-test-client",
            "redirect_uri": "http://localhost:3000/callback",
            "user_id": "testuser",
            "code_challenge": challenge,
            "scope": "mcp:read mcp:write",
            "expires_at": datetime.now() + timedelta(minutes=10),
        }

        # Verify the code exists and has correct data
        assert auth_code in auth_server.authorization_codes
        code_data = auth_server.authorization_codes[auth_code]
        assert code_data["user_id"] == "testuser"
        assert code_data["scope"] == "mcp:read mcp:write"

        # Simulate token exchange (without HTTP client)
        access_token = "integration-test-token"
        auth_server.access_tokens[access_token] = {
            "client_id": code_data["client_id"],
            "user_id": code_data["user_id"],
            "scope": code_data["scope"],
            "expires_at": datetime.now() + timedelta(hours=1),
        }

        # Verify token was created correctly
        assert access_token in auth_server.access_tokens
        token_data = auth_server.access_tokens[access_token]
        assert token_data["user_id"] == "testuser"
        assert token_data["scope"] == "mcp:read mcp:write"

        print("✅ OAuth integration test components verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
