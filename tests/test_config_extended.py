"""Extended tests for config.py to improve coverage."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.config import Config


class TestConfigExtended:
    """Extended tests for Config class coverage."""

    def test_get_default_claude_model(self):
        """Test getting default Claude model."""
        with patch.dict(os.environ, {}, clear=True):
            model = Config.get_default_claude_model()
            assert model == Config.CLAUDE_DEFAULT_MODEL

        with patch.dict(os.environ, {"CLAUDE_MODEL": "custom-model"}):
            model = Config.get_default_claude_model()
            assert model == "custom-model"

    def test_get_anthropic_api_key(self):
        """Test getting Anthropic API key."""
        with patch.dict(os.environ, {}, clear=True):
            api_key = Config.get_anthropic_api_key()
            assert api_key is None

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"}):
            api_key = Config.get_anthropic_api_key()
            assert api_key == "test-key-123"

    def test_should_use_vertex_for_claude_various_values(self):
        """Test should_use_vertex_for_claude with various boolean values."""
        # Test false values
        for false_val in ["0", "false", "False", "FALSE", "no", "NO", "off", "OFF"]:
            with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": false_val}):
                assert Config.should_use_vertex_for_claude() is False

        # Test true values
        for true_val in ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON"]:
            with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": true_val}):
                assert Config.should_use_vertex_for_claude() is True

        # Test with whitespace
        with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "  false  "}):
            assert Config.should_use_vertex_for_claude() is False

    def test_get_claude_vertex_project_fallback_chain(self):
        """Test the fallback chain for Claude Vertex project."""
        # Test with all env vars unset, uses default
        with patch.dict(os.environ, {}, clear=True):
            project = Config.get_claude_vertex_project()
            assert project == Config.PROJECT_ID

        # Test with default_project parameter
        with patch.dict(os.environ, {}, clear=True):
            project = Config.get_claude_vertex_project("custom-default")
            assert project == "custom-default"

        # Test CLAUDE_VERTEX_PROJECT takes precedence
        with patch.dict(
            os.environ,
            {
                "CLAUDE_VERTEX_PROJECT": "vertex-proj",
                "GOOGLE_CLOUD_PROJECT": "gcp-proj",
            },
        ):
            project = Config.get_claude_vertex_project("default-proj")
            assert project == "vertex-proj"

        # Test GOOGLE_CLOUD_PROJECT is second priority
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "gcp-proj"}):
            project = Config.get_claude_vertex_project("default-proj")
            assert project == "gcp-proj"

        # Test default_project is third priority
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Config, "get_project_id", return_value="config-proj"):
                project = Config.get_claude_vertex_project("default-proj")
                assert project == "default-proj"

    def test_get_claude_vertex_location_fallback_chain(self):
        """Test the fallback chain for Claude Vertex location."""
        # Test with all env vars unset, uses default
        with patch.dict(os.environ, {}, clear=True):
            location = Config.get_claude_vertex_location()
            assert location == Config.LOCATION

        # Test CLAUDE_VERTEX_LOCATION takes precedence
        with patch.dict(
            os.environ,
            {
                "CLAUDE_VERTEX_LOCATION": "us-west1",
                "GOOGLE_CLOUD_LOCATION": "us-east1",
            },
        ):
            location = Config.get_claude_vertex_location()
            assert location == "us-west1"

        # Test GOOGLE_CLOUD_LOCATION is second priority
        with patch.dict(os.environ, {"GOOGLE_CLOUD_LOCATION": "us-east1"}):
            location = Config.get_claude_vertex_location()
            assert location == "us-east1"

    def test_get_claude_vertex_base_url_override(self):
        """Test Claude Vertex base URL with override."""
        with patch.dict(os.environ, {"CLAUDE_VERTEX_BASE_URL": "https://custom.api.com/"}):
            base_url = Config.get_claude_vertex_base_url()
            assert base_url == "https://custom.api.com"  # Trailing slash removed

    def test_get_claude_vertex_base_url_default(self):
        """Test Claude Vertex base URL default construction."""
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(Config, "get_claude_vertex_project", return_value="test-proj"):
                with patch.object(Config, "get_claude_vertex_location", return_value="us-central1"):
                    base_url = Config.get_claude_vertex_base_url()
                    assert "us-central1-aiplatform.googleapis.com" in base_url
                    assert "test-proj" in base_url
                    assert "anthropic" in base_url
                    assert "/v1/" in base_url

    def test_get_claude_vertex_base_url_with_params(self):
        """Test Claude Vertex base URL with explicit parameters."""
        base_url = Config.get_claude_vertex_base_url(
            project="explicit-proj",
            location="europe-west1"
        )
        assert "europe-west1-aiplatform.googleapis.com" in base_url
        assert "explicit-proj" in base_url

    def test_get_claude_vertex_sdk_kwargs_disabled(self):
        """Test Claude Vertex SDK kwargs when disabled."""
        with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "false"}):
            kwargs = Config.get_claude_vertex_sdk_kwargs()
            assert kwargs == {}

    def test_get_claude_vertex_sdk_kwargs_no_google_auth(self):
        """Test Claude Vertex SDK kwargs when Google auth is unavailable."""
        with patch("src.config.google_auth_default", None):
            with patch("src.config.GoogleAuthRequest", None):
                kwargs = Config.get_claude_vertex_sdk_kwargs()
                assert kwargs == {}

    def test_get_claude_vertex_sdk_kwargs_auth_failure(self):
        """Test Claude Vertex SDK kwargs when auth fails."""
        mock_auth = Mock()
        mock_auth.side_effect = Exception("Auth failed")

        with patch("src.config.google_auth_default", mock_auth):
            with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "true"}):
                kwargs = Config.get_claude_vertex_sdk_kwargs()
                assert kwargs == {}

    def test_get_claude_vertex_sdk_kwargs_refresh_failure(self):
        """Test Claude Vertex SDK kwargs when credential refresh fails."""
        mock_credentials = Mock()
        mock_credentials.refresh.side_effect = Exception("Refresh failed")

        mock_auth = Mock(return_value=(mock_credentials, "test-project"))

        with patch("src.config.google_auth_default", mock_auth):
            with patch("src.config.GoogleAuthRequest", Mock()):
                with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "true"}):
                    kwargs = Config.get_claude_vertex_sdk_kwargs()
                    assert kwargs == {}

    def test_get_claude_vertex_sdk_kwargs_empty_token(self):
        """Test Claude Vertex SDK kwargs when token is empty."""
        mock_credentials = Mock()
        mock_credentials.token = None
        mock_credentials.refresh = Mock()

        mock_auth = Mock(return_value=(mock_credentials, "test-project"))

        with patch("src.config.google_auth_default", mock_auth):
            with patch("src.config.GoogleAuthRequest", Mock()):
                with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "true"}):
                    kwargs = Config.get_claude_vertex_sdk_kwargs()
                    assert kwargs == {}

    def test_get_claude_vertex_sdk_kwargs_success(self):
        """Test Claude Vertex SDK kwargs with successful auth."""
        mock_credentials = Mock()
        mock_credentials.token = "test-access-token"
        mock_credentials.refresh = Mock()

        mock_auth = Mock(return_value=(mock_credentials, "detected-project"))

        with patch("src.config.google_auth_default", mock_auth):
            with patch("src.config.GoogleAuthRequest", Mock()):
                with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "true"}):
                    with patch.object(
                        Config, "get_claude_vertex_project", return_value="final-project"
                    ):
                        with patch.object(
                            Config, "get_claude_vertex_location", return_value="us-east1"
                        ):
                            kwargs = Config.get_claude_vertex_sdk_kwargs()

                            assert "base_url" in kwargs
                            assert "api_key" in kwargs
                            assert kwargs["api_key"] == "test-access-token"
                            assert "default_headers" in kwargs
                            assert kwargs["default_headers"]["Authorization"] == "Bearer test-access-token"
                            assert kwargs["default_headers"]["x-goog-user-project"] == "final-project"

    def test_get_claude_sdk_init_kwargs_with_vertex(self):
        """Test Claude SDK init kwargs when using Vertex."""
        mock_vertex_kwargs = {
            "base_url": "https://vertex.api.com",
            "api_key": "vertex-token",
            "default_headers": {"Authorization": "Bearer vertex-token"}
        }

        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value=mock_vertex_kwargs):
            kwargs = Config.get_claude_sdk_init_kwargs("custom-model")

            assert kwargs["base_url"] == "https://vertex.api.com"
            assert kwargs["api_key"] == "vertex-token"
            assert kwargs["default_model"] == "custom-model"
            assert kwargs["default_headers"]["Authorization"] == "Bearer vertex-token"
            assert kwargs["default_headers"]["anthropic-version"] == Config.CLAUDE_API_VERSION

    def test_get_claude_sdk_init_kwargs_with_api_key(self):
        """Test Claude SDK init kwargs with API key."""
        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value={}):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "api-key-123"}):
                kwargs = Config.get_claude_sdk_init_kwargs()

                assert kwargs["api_key"] == "api-key-123"
                assert kwargs["default_model"] == Config.CLAUDE_DEFAULT_MODEL
                assert "anthropic-version" in kwargs["default_headers"]

    def test_get_claude_sdk_init_kwargs_vertex_takes_precedence(self):
        """Test that Vertex API key takes precedence over Anthropic API key."""
        mock_vertex_kwargs = {
            "api_key": "vertex-token"
        }

        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value=mock_vertex_kwargs):
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-key"}):
                kwargs = Config.get_claude_sdk_init_kwargs()

                # Vertex token should be used, not Anthropic key
                assert kwargs["api_key"] == "vertex-token"

    def test_get_claude_sdk_init_kwargs_preserves_existing_headers(self):
        """Test that existing headers in vertex kwargs are preserved."""
        mock_vertex_kwargs = {
            "default_headers": {
                "Authorization": "Bearer token",
                "x-custom-header": "custom-value"
            }
        }

        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value=mock_vertex_kwargs):
            kwargs = Config.get_claude_sdk_init_kwargs()

            assert kwargs["default_headers"]["Authorization"] == "Bearer token"
            assert kwargs["default_headers"]["x-custom-header"] == "custom-value"
            assert kwargs["default_headers"]["anthropic-version"] == Config.CLAUDE_API_VERSION

    def test_get_claude_sdk_init_kwargs_no_model_override(self):
        """Test default model is used when no override provided."""
        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value={}):
            with patch.dict(os.environ, {"CLAUDE_MODEL": "env-model"}):
                kwargs = Config.get_claude_sdk_init_kwargs()
                assert kwargs["default_model"] == "env-model"

    def test_get_claude_sdk_init_kwargs_model_parameter_precedence(self):
        """Test that model parameter takes precedence over env var."""
        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value={}):
            with patch.dict(os.environ, {"CLAUDE_MODEL": "env-model"}):
                kwargs = Config.get_claude_sdk_init_kwargs("param-model")
                assert kwargs["default_model"] == "param-model"

    def test_get_claude_sdk_init_kwargs_empty_headers(self):
        """Test that headers are created even when vertex kwargs is empty."""
        with patch.object(Config, "get_claude_vertex_sdk_kwargs", return_value={}):
            with patch.dict(os.environ, {}, clear=True):
                kwargs = Config.get_claude_sdk_init_kwargs()

                assert "default_headers" in kwargs
                assert kwargs["default_headers"]["anthropic-version"] == Config.CLAUDE_API_VERSION
