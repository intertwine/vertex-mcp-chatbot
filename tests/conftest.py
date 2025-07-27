"""Pytest configuration and fixtures for the test suite."""

import pytest
import os
import tempfile
from unittest.mock import Mock, AsyncMock, patch
from src.config import Config


@pytest.fixture
def mock_console():
    """Fixture providing a mocked Rich console."""
    return Mock()


@pytest.fixture
def mock_gemini_client():
    """Fixture providing a mocked GeminiClient."""
    client = Mock()
    client.model_name = Config.DEFAULT_MODEL
    client.chat_session = None
    client.send_message.return_value = "Mocked response"
    client.get_chat_history.return_value = []
    return client


@pytest.fixture
def mock_genai_client():
    """Fixture providing a mocked genai.Client."""
    with patch("src.gemini_client.genai.Client") as mock_client:
        mock_instance = Mock()
        mock_chat_session = Mock()
        mock_response = Mock()
        mock_response.text = "Test response"

        mock_instance.chats.create.return_value = mock_chat_session
        mock_chat_session.send_message.return_value = mock_response
        mock_chat_session.get_history.return_value = []
        mock_client.return_value = mock_instance

        yield mock_client


@pytest.fixture
def temp_chat_dir():
    """Fixture providing a temporary chat directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        chat_dir = os.path.join(temp_dir, ".chat")
        os.makedirs(chat_dir, exist_ok=True)
        yield chat_dir


@pytest.fixture
def mock_config_env():
    """Fixture for mocking environment variables used by Config."""
    with patch.dict(
        os.environ,
        {
            "GOOGLE_CLOUD_PROJECT": "test-project-123",
            "GOOGLE_CLOUD_LOCATION": "us-west1",
        },
    ):
        yield


@pytest.fixture
def sample_chat_history():
    """Fixture providing sample chat history data."""
    user_message = Mock()
    user_message.role = "user"
    user_message.parts = [Mock()]
    user_message.parts[0].text = "What is artificial intelligence?"

    assistant_message = Mock()
    assistant_message.role = "assistant"
    assistant_message.parts = [Mock()]
    assistant_message.parts[0].text = (
        "Artificial intelligence (AI) refers to..."
    )

    return [user_message, assistant_message]


@pytest.fixture(autouse=True)
def mock_makedirs():
    """Auto-use fixture to mock os.makedirs in all tests."""
    with patch("os.makedirs"):
        yield


@pytest.fixture
def mock_file_operations():
    """Fixture for mocking file operations."""
    with (
        patch("os.path.exists") as mock_exists,
        patch("os.remove") as mock_remove,
        patch("builtins.open") as mock_open,
    ):

        mock_exists.return_value = True
        yield {"exists": mock_exists, "remove": mock_remove, "open": mock_open}


# Pytest markers
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


# MCP-specific fixtures


@pytest.fixture
def mock_mcp_config():
    """Fixture providing a mock MCP configuration."""
    config = Mock()
    config.servers = [
        {
            "name": "test-server",
            "transport": "stdio",
            "command": ["python", "server.py"],
        },
        {
            "name": "http-server",
            "transport": "http",
            "url": "http://localhost:8000",
        },
    ]
    config.get_server = Mock(
        side_effect=lambda name: next(
            (s for s in config.servers if s["name"] == name), None
        )
    )
    return config


@pytest.fixture
def mock_mcp_session():
    """Fixture providing a mock MCP client session."""
    session = AsyncMock()
    session.initialize = AsyncMock()
    session.list_tools = AsyncMock(return_value={"tools": []})
    session.list_resources = AsyncMock(return_value={"resources": []})
    session.list_prompts = AsyncMock(return_value={"prompts": []})
    session.call_tool = AsyncMock()
    session.read_resource = AsyncMock()
    return session


@pytest.fixture
def mock_mcp_manager():
    """Fixture providing a mock MCP manager."""
    manager = Mock()
    manager.config = Mock(servers=[])
    manager.list_servers = Mock(return_value=[])
    manager.connect_server_sync = Mock()
    manager.disconnect_server_sync = Mock()
    manager.get_tools_sync = Mock(return_value=[])
    manager.get_resources_sync = Mock(return_value=[])
    manager.get_prompts_sync = Mock(return_value=[])
    manager.call_tool_sync = Mock()
    manager.read_resource_sync = Mock()
    return manager
