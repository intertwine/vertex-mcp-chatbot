"""Configuration helpers for Gemini and Claude integrations."""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

from dotenv import load_dotenv

try:  # pragma: no cover - optional dependency resolved at runtime
    from google.auth import default as google_auth_default
    from google.auth.transport.requests import Request as GoogleAuthRequest
except ImportError:  # pragma: no cover - optional dependency resolved at runtime
    google_auth_default = None
    GoogleAuthRequest = None

# Load environment variables
load_dotenv()

LOGGER = logging.getLogger(__name__)


class Config:
    """Configuration settings for the Vertex MCP chatbot."""

    # ------------------------------------------------------------------
    # GCP and model defaults
    # ------------------------------------------------------------------
    PROJECT_ID = "your-gcp-project-id"
    LOCATION = "your-gcp-location"

    DEFAULT_MODEL = "gemini-2.5-flash"

    CLAUDE_DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929")
    CLAUDE_API_VERSION = os.getenv("CLAUDE_API_VERSION", "2023-06-01")
    CLAUDE_VERTEX_API_VERSION = os.getenv("CLAUDE_VERTEX_API_VERSION", "v1")
    CLAUDE_VERTEX_ENABLED = os.getenv("CLAUDE_VERTEX_ENABLED", "true")

    MAX_HISTORY_LENGTH = 10  # Number of conversation turns to keep in memory

    # ------------------------------------------------------------------
    # Core GCP helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_project_id() -> str:
        """Return the Google Cloud project ID from environment or config."""

        return os.getenv("GOOGLE_CLOUD_PROJECT", Config.PROJECT_ID)

    @staticmethod
    def get_location() -> str:
        """Return the Google Cloud location from environment or config."""

        return os.getenv("GOOGLE_CLOUD_LOCATION", Config.LOCATION)

    # ------------------------------------------------------------------
    # Claude helpers
    # ------------------------------------------------------------------
    @staticmethod
    def get_default_claude_model() -> str:
        """Return the default Claude model to use for the agent SDK."""

        return os.getenv("CLAUDE_MODEL", Config.CLAUDE_DEFAULT_MODEL)

    @staticmethod
    def get_anthropic_api_key() -> Optional[str]:
        """Return the Anthropic API key if one is configured."""

        return os.getenv("ANTHROPIC_API_KEY")

    @staticmethod
    def should_use_vertex_for_claude() -> bool:
        """Return True if Claude requests should attempt to use Vertex AI."""

        value = os.getenv("CLAUDE_VERTEX_ENABLED", Config.CLAUDE_VERTEX_ENABLED)
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def get_claude_vertex_project(default_project: Optional[str] = None) -> str:
        """Return the project used for Vertex Claude requests."""

        return (
            os.getenv("CLAUDE_VERTEX_PROJECT")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or default_project
            or Config.get_project_id()
        )

    @staticmethod
    def get_claude_vertex_location() -> str:
        """Return the region used for Vertex Claude requests."""

        return (
            os.getenv("CLAUDE_VERTEX_LOCATION")
            or os.getenv("GOOGLE_CLOUD_LOCATION")
            or Config.LOCATION
        )

    @staticmethod
    def get_claude_vertex_base_url(
        project: Optional[str] = None, location: Optional[str] = None
    ) -> str:
        """Return the Vertex base URL for Anthropic endpoints."""

        override = os.getenv("CLAUDE_VERTEX_BASE_URL")
        if override:
            return override.rstrip("/")

        project_id = project or Config.get_claude_vertex_project()
        location_id = location or Config.get_claude_vertex_location()
        api_version = Config.CLAUDE_VERTEX_API_VERSION.strip("/")
        return (
            f"https://{location_id}-aiplatform.googleapis.com/"
            f"{api_version}/projects/{project_id}/locations/{location_id}/publishers/anthropic"
        )

    @staticmethod
    def get_claude_vertex_sdk_kwargs() -> Dict[str, object]:
        """Return initialization kwargs for the Claude SDK when using Vertex.

        The function attempts to acquire an OAuth access token using Application
        Default Credentials. If this fails (for example when credentials are not
        configured) an empty dict is returned so that the SDK can fall back to
        the public Anthropic API using an API key.
        """

        if not Config.should_use_vertex_for_claude():
            return {}

        if google_auth_default is None or GoogleAuthRequest is None:
            LOGGER.debug(
                "Google authentication libraries are unavailable; skipping Vertex Claude configuration."
            )
            return {}

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]

        try:
            credentials, detected_project = google_auth_default(scopes=scopes)
        except Exception as exc:  # pragma: no cover - depends on local env
            LOGGER.debug(
                "Unable to load Google credentials for Vertex Claude integration: %s",
                exc,
            )
            return {}

        project_id = Config.get_claude_vertex_project(detected_project)
        location = Config.get_claude_vertex_location()

        try:
            credentials.refresh(GoogleAuthRequest())
        except Exception as exc:  # pragma: no cover - depends on local env
            LOGGER.debug(
                "Unable to refresh Google credentials for Vertex Claude integration: %s",
                exc,
            )
            return {}

        token = getattr(credentials, "token", None)
        if not token:
            LOGGER.debug(
                "Google credentials refresh returned an empty token; skipping Vertex Claude configuration."
            )
            return {}

        base_url = Config.get_claude_vertex_base_url(project_id, location)

        headers = {
            "Authorization": f"Bearer {token}",
            "x-goog-user-project": project_id,
        }

        return {
            "base_url": base_url,
            "api_key": token,
            "default_headers": headers,
        }

    @staticmethod
    def get_claude_sdk_init_kwargs(
        default_model: Optional[str] = None,
    ) -> Dict[str, object]:
        """Return keyword arguments for initializing the Claude SDK client."""

        kwargs: Dict[str, object] = {}

        vertex_kwargs = Config.get_claude_vertex_sdk_kwargs()
        if vertex_kwargs:
            # Avoid mutating the dict returned from the helper.
            kwargs.update(vertex_kwargs)

        api_key = Config.get_anthropic_api_key()
        if api_key and "api_key" not in kwargs:
            kwargs["api_key"] = api_key

        model_name = default_model or Config.get_default_claude_model()
        if model_name:
            kwargs.setdefault("default_model", model_name)

        # Use default_headers for Anthropic SDK (not extra_headers)
        headers = dict(kwargs.get("default_headers", {}))
        if "anthropic-version" not in headers:
            headers["anthropic-version"] = Config.CLAUDE_API_VERSION
        if headers:
            kwargs["default_headers"] = headers

        return kwargs
