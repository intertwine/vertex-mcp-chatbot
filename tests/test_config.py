"""Tests for the config module."""

import os
from unittest.mock import patch

import pytest

from src.config import Config


class TestConfig:
    """Test cases for the Config class."""

    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        assert Config.PROJECT_ID == "your-gcp-project-id"
        assert Config.LOCATION == "your-gcp-location"
        assert Config.DEFAULT_MODEL == "gemini-2.5-flash"
        assert Config.CLAUDE_DEFAULT_MODEL == "claude-4.5-sonnet"
        assert Config.CLAUDE_API_VERSION == "2025-02-19"
        assert Config.MAX_HISTORY_LENGTH == 10

    def test_get_project_id_default(self):
        """Test get_project_id returns default when no env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove GOOGLE_CLOUD_PROJECT if it exists
            if "GOOGLE_CLOUD_PROJECT" in os.environ:
                del os.environ["GOOGLE_CLOUD_PROJECT"]

            project_id = Config.get_project_id()
            assert project_id == Config.PROJECT_ID

    def test_get_project_id_from_env(self):
        """Test get_project_id returns environment variable when set."""
        test_project_id = "test-project-123"
        with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": test_project_id}):
            project_id = Config.get_project_id()
            assert project_id == test_project_id

    def test_get_location_default(self):
        """Test get_location returns default when no env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove GOOGLE_CLOUD_LOCATION if it exists
            if "GOOGLE_CLOUD_LOCATION" in os.environ:
                del os.environ["GOOGLE_CLOUD_LOCATION"]

            location = Config.get_location()
            assert location == Config.LOCATION

    def test_get_location_from_env(self):
        """Test get_location returns environment variable when set."""
        test_location = "us-west1"
        with patch.dict(os.environ, {"GOOGLE_CLOUD_LOCATION": test_location}):
            location = Config.get_location()
            assert location == test_location

    def test_should_use_vertex_for_claude(self):
        with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "false"}):
            assert Config.should_use_vertex_for_claude() is False
        with patch.dict(os.environ, {"CLAUDE_VERTEX_ENABLED": "TRUE"}):
            assert Config.should_use_vertex_for_claude() is True

    def test_get_claude_vertex_project_prefers_env(self):
        with patch.dict(
            os.environ,
            {
                "CLAUDE_VERTEX_PROJECT": "vertex-project",
                "GOOGLE_CLOUD_PROJECT": "gcp-project",
            },
        ):
            assert Config.get_claude_vertex_project() == "vertex-project"

        with patch.dict(
            os.environ,
            {"GOOGLE_CLOUD_PROJECT": "gcp-project"},
            clear=True,
        ):
            assert Config.get_claude_vertex_project() == "gcp-project"

    def test_get_claude_sdk_init_kwargs_merges_headers(self):
        with patch(
            "src.config.Config.get_claude_vertex_sdk_kwargs",
            return_value={"extra_headers": {"Authorization": "Bearer token"}},
        ):
            kwargs = Config.get_claude_sdk_init_kwargs("claude-vertex")
            assert kwargs["default_model"] == "claude-vertex"
            assert kwargs["extra_headers"]["Authorization"] == "Bearer token"
            assert kwargs["extra_headers"]["Anthropic-Version"] == Config.CLAUDE_API_VERSION

    def test_config_is_static(self):
        """Test that Config methods are static and can be called without instantiation."""
        # Should be able to call without creating an instance
        project_id = Config.get_project_id()
        location = Config.get_location()

        assert isinstance(project_id, str)
        assert isinstance(location, str)
