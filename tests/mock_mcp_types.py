"""Mock MCP SDK types for testing."""

from typing import List, Dict, Any, Optional
from unittest.mock import MagicMock


class MockTool:
    """Mock Tool object that matches MCP SDK structure."""

    def __init__(
        self,
        name: str,
        description: str = "",
        inputSchema: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema or {"type": "object"}


class MockResource:
    """Mock Resource object that matches MCP SDK structure."""

    def __init__(
        self,
        uri: str,
        name: str,
        description: str = "",
        mimeType: str = "application/octet-stream",
    ):
        self.uri = uri
        self.name = name
        self.description = description
        self.mimeType = mimeType


class MockPromptArgument:
    """Mock PromptArgument object that matches MCP SDK structure."""

    def __init__(self, name: str, description: str = "", required: bool = True):
        self.name = name
        self.description = description
        self.required = required


class MockPrompt:
    """Mock Prompt object that matches MCP SDK structure."""

    def __init__(
        self,
        name: str,
        description: str = "",
        arguments: Optional[List[MockPromptArgument]] = None,
    ):
        self.name = name
        self.description = description
        self.arguments = arguments or []


class MockListToolsResult:
    """Mock ListToolsResult object that matches MCP SDK structure."""

    def __init__(self, tools: List[MockTool]):
        self.tools = tools


class MockListResourcesResult:
    """Mock ListResourcesResult object that matches MCP SDK structure."""

    def __init__(self, resources: List[MockResource]):
        self.resources = resources


class MockListPromptsResult:
    """Mock ListPromptsResult object that matches MCP SDK structure."""

    def __init__(self, prompts: List[MockPrompt]):
        self.prompts = prompts


def create_mock_list_tools_result(
    tools_data: List[Dict[str, Any]],
) -> MockListToolsResult:
    """Create a mock ListToolsResult from tool data dictionaries."""
    tools = []
    for tool_data in tools_data:
        tool = MockTool(
            name=tool_data["name"],
            description=tool_data.get("description", ""),
            inputSchema=tool_data.get("inputSchema", {"type": "object"}),
        )
        tools.append(tool)
    return MockListToolsResult(tools)


def create_mock_list_resources_result(
    resources_data: List[Dict[str, Any]],
) -> MockListResourcesResult:
    """Create a mock ListResourcesResult from resource data dictionaries."""
    resources = []
    for resource_data in resources_data:
        resource = MockResource(
            uri=resource_data["uri"],
            name=resource_data["name"],
            description=resource_data.get("description", ""),
            mimeType=resource_data.get("mimeType", "application/octet-stream"),
        )
        resources.append(resource)
    return MockListResourcesResult(resources)


def create_mock_list_prompts_result(
    prompts_data: List[Dict[str, Any]],
) -> MockListPromptsResult:
    """Create a mock ListPromptsResult from prompt data dictionaries."""
    prompts = []
    for prompt_data in prompts_data:
        # Convert argument data to MockPromptArgument objects
        arguments = []
        for arg_data in prompt_data.get("arguments", []):
            arg = MockPromptArgument(
                name=arg_data["name"],
                description=arg_data.get("description", ""),
                required=arg_data.get("required", True),
            )
            arguments.append(arg)

        prompt = MockPrompt(
            name=prompt_data["name"],
            description=prompt_data.get("description", ""),
            arguments=arguments,
        )
        prompts.append(prompt)
    return MockListPromptsResult(prompts)
