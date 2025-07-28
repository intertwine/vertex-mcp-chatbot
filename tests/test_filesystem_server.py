"""
Tests for the filesystem MCP server example.

These tests verify that the filesystem_server.py example server correctly
implements MCP protocol features including tools, resources, and prompts.
"""

import pytest
import asyncio
import tempfile
import os
import json
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch, AsyncMock
import sys

# Add examples directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "examples" / "mcp-servers"))

from filesystem_server import (
    mcp,
    validate_path,
    get_mime_type,
    list_files,
    read_file,
    write_file,
    create_directory,
    read_resource,
    analyze_directory,
    summarize_file,
    BASE_PATH
)


class TestFilesystemServer:
    """Test filesystem MCP server functionality."""

    def setup_method(self):
        """Set up test environment."""
        # Create test files in current directory for testing
        self.create_test_files()

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up test files
        self.cleanup_test_files()

    def create_test_files(self):
        """Create test files and directories."""
        # Create test files in current directory
        Path("test.txt").write_text("Hello, World!")
        Path("test.json").write_text('{"key": "value"}')
        Path("test.py").write_text("print('Hello')")
        
        # Create subdirectory with files
        subdir = Path("test_subdir")
        subdir.mkdir(exist_ok=True)
        (subdir / "nested.txt").write_text("Nested file content")
        
        # Create empty directory
        Path("test_empty_dir").mkdir(exist_ok=True)
    
    def cleanup_test_files(self):
        """Clean up test files and directories."""
        import shutil
        # Clean up test files
        test_files = [
            "test.txt", "test.json", "test.py", "new_file.txt", 
            "empty.txt", "restricted.txt"
        ]
        for file in test_files:
            try:
                # Restore permissions in case they were changed
                file_path = Path(file)
                if file_path.exists():
                    file_path.chmod(0o644)
                    file_path.unlink()
            except (FileNotFoundError, OSError):
                pass
        
        # Clean up test directories
        test_dirs = [
            "test_subdir", "test_empty_dir", "new_directory", 
            "new_dir", "level1"
        ]
        for dir_name in test_dirs:
            try:
                shutil.rmtree(dir_name)
            except (FileNotFoundError, OSError):
                pass


class TestValidatePath(TestFilesystemServer):
    """Test path validation functionality."""

    def test_validate_path_safe(self):
        """Test path validation with safe paths."""
        result = validate_path("test.txt")
        assert result is not None
        assert result.name == "test.txt"

    def test_validate_path_subdirectory(self):
        """Test path validation with subdirectory paths."""
        result = validate_path("test_subdir/nested.txt")
        assert result is not None
        assert result.name == "nested.txt"

    def test_validate_path_unsafe_relative(self):
        """Test path validation rejects unsafe relative paths."""
        result = validate_path("../../../etc/passwd")
        assert result is None

    def test_validate_path_unsafe_absolute(self):
        """Test path validation rejects absolute paths outside base."""
        result = validate_path("/etc/passwd")
        assert result is None

    def test_validate_path_current_directory(self):
        """Test path validation with current directory."""
        result = validate_path(".")
        assert result is not None
        assert result == BASE_PATH


class TestGetMimeType:
    """Test MIME type detection."""

    def test_get_mime_type_known_extensions(self):
        """Test MIME type detection for known extensions."""
        assert get_mime_type(".txt") == "text/plain"
        assert get_mime_type(".json") == "application/json"
        assert get_mime_type(".py") == "text/x-python"
        assert get_mime_type(".js") == "text/javascript"
        assert get_mime_type(".html") == "text/html"
        assert get_mime_type(".css") == "text/css"
        assert get_mime_type(".md") == "text/markdown"
        assert get_mime_type(".xml") == "text/xml"
        assert get_mime_type(".yaml") == "text/yaml"
        assert get_mime_type(".yml") == "text/yaml"

    def test_get_mime_type_case_insensitive(self):
        """Test MIME type detection is case insensitive."""
        assert get_mime_type(".TXT") == "text/plain"
        assert get_mime_type(".JSON") == "application/json"
        assert get_mime_type(".Py") == "text/x-python"

    def test_get_mime_type_unknown_extension(self):
        """Test MIME type detection for unknown extensions."""
        assert get_mime_type(".xyz") == "text/plain"
        assert get_mime_type(".unknown") == "text/plain"
        assert get_mime_type("") == "text/plain"


class TestListFilesTool(TestFilesystemServer):
    """Test list_files tool."""

    @pytest.mark.asyncio
    async def test_list_files_current_directory(self):
        """Test listing files in current directory."""
        result = await list_files(".")
        
        assert result["directory"] == "."
        assert result["count"] >= 3  # At least test.txt, test.json, test.py
        
        # Check that files are present
        file_names = [f["name"] for f in result["files"]]
        assert "test.txt" in file_names
        assert "test.json" in file_names
        assert "test.py" in file_names

    @pytest.mark.asyncio
    async def test_list_files_subdirectory(self):
        """Test listing files in subdirectory."""
        result = await list_files("test_subdir")
        
        assert result["directory"] == "test_subdir"
        assert result["count"] == 1
        assert result["files"][0]["name"] == "nested.txt"

    @pytest.mark.asyncio
    async def test_list_files_with_pattern(self):
        """Test listing files with glob pattern."""
        result = await list_files(".", "*.txt")
        
        file_names = [f["name"] for f in result["files"]]
        assert "test.txt" in file_names
        assert "test.json" not in file_names
        assert "test.py" not in file_names

    @pytest.mark.asyncio
    async def test_list_files_empty_directory(self):
        """Test listing files in empty directory."""
        result = await list_files("test_empty_dir")
        
        assert result["directory"] == "test_empty_dir"
        assert result["count"] == 0
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_list_files_nonexistent_directory(self):
        """Test listing files in nonexistent directory."""
        with pytest.raises(ValueError, match="Directory not found"):
            await list_files("nonexistent")

    @pytest.mark.asyncio
    async def test_list_files_not_directory(self):
        """Test listing files on a file path."""
        with pytest.raises(ValueError, match="Not a directory"):
            await list_files("test.txt")

    @pytest.mark.asyncio
    async def test_list_files_path_traversal(self):
        """Test listing files with path traversal attempt."""
        with pytest.raises(ValueError, match="Access denied"):
            await list_files("../../../etc")


class TestReadFileTool(TestFilesystemServer):
    """Test read_file tool."""

    @pytest.mark.asyncio
    async def test_read_file_success(self):
        """Test reading a file successfully."""
        result = await read_file("test.txt")
        assert result == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_file_json(self):
        """Test reading JSON file."""
        result = await read_file("test.json")
        assert result == '{"key": "value"}'

    @pytest.mark.asyncio
    async def test_read_file_subdirectory(self):
        """Test reading file in subdirectory."""
        result = await read_file("test_subdir/nested.txt")
        assert result == "Nested file content"

    @pytest.mark.asyncio
    async def test_read_file_nonexistent(self):
        """Test reading nonexistent file."""
        with pytest.raises(ValueError, match="File not found"):
            await read_file("nonexistent.txt")

    @pytest.mark.asyncio
    async def test_read_file_directory(self):
        """Test reading a directory path."""
        with pytest.raises(ValueError, match="Not a file"):
            await read_file("test_subdir")

    @pytest.mark.asyncio
    async def test_read_file_path_traversal(self):
        """Test reading file with path traversal attempt."""
        with pytest.raises(ValueError, match="Access denied"):
            await read_file("../../../etc/passwd")


class TestWriteFileTool(TestFilesystemServer):
    """Test write_file tool."""

    @pytest.mark.asyncio
    async def test_write_file_new(self):
        """Test writing a new file."""
        content = "New file content"
        result = await write_file("new_file.txt", content)
        
        assert "Successfully wrote" in result
        assert "16 bytes" in result  # "New file content" is 16 bytes
        
        # Verify file was created
        assert Path("new_file.txt").exists()
        assert Path("new_file.txt").read_text() == content

    @pytest.mark.asyncio
    async def test_write_file_overwrite(self):
        """Test overwriting existing file."""
        content = "Overwritten content"
        result = await write_file("test.txt", content)
        
        assert "Successfully wrote" in result
        
        # Verify file was overwritten
        assert Path("test.txt").read_text() == content

    @pytest.mark.asyncio
    async def test_write_file_create_directories(self):
        """Test writing file with automatic directory creation."""
        content = "Content in new directory"
        result = await write_file("new_dir/new_file.txt", content)
        
        assert "Successfully wrote" in result
        
        # Verify directories and file were created
        file_path = Path("new_dir") / "new_file.txt"
        assert file_path.exists()
        assert file_path.read_text() == content

    @pytest.mark.asyncio
    async def test_write_file_path_traversal(self):
        """Test writing file with path traversal attempt."""
        with pytest.raises(ValueError, match="Access denied"):
            await write_file("../../../tmp/malicious.txt", "content")

    @pytest.mark.asyncio
    async def test_write_file_empty_content(self):
        """Test writing file with empty content."""
        result = await write_file("empty.txt", "")
        
        assert "Successfully wrote 0 bytes" in result
        assert Path("empty.txt").exists()
        assert Path("empty.txt").read_text() == ""


class TestCreateDirectoryTool(TestFilesystemServer):
    """Test create_directory tool."""

    @pytest.mark.asyncio
    async def test_create_directory_new(self):
        """Test creating a new directory."""
        result = await create_directory("new_directory")
        
        assert "Successfully created" in result
        assert Path("new_directory").exists()
        assert Path("new_directory").is_dir()

    @pytest.mark.asyncio
    async def test_create_directory_nested(self):
        """Test creating nested directories."""
        result = await create_directory("level1/level2/level3")
        
        assert "Successfully created" in result
        nested_path = Path("level1") / "level2" / "level3"
        assert nested_path.exists()
        assert nested_path.is_dir()

    @pytest.mark.asyncio
    async def test_create_directory_existing(self):
        """Test creating directory that already exists."""
        result = await create_directory("test_subdir")
        
        assert "Successfully created" in result
        assert Path("test_subdir").exists()

    @pytest.mark.asyncio
    async def test_create_directory_path_traversal(self):
        """Test creating directory with path traversal attempt."""
        with pytest.raises(ValueError, match="Access denied"):
            await create_directory("../../../tmp/malicious_dir")


class TestReadResource(TestFilesystemServer):
    """Test read_resource function."""

    def test_read_resource_success(self):
        """Test reading a file resource successfully."""
        # Note: This test will initially fail due to the bug in read_resource
        # The function calls undefined sanitize_path() and is_path_allowed()
        with patch('filesystem_server.sanitize_path') as mock_sanitize, \
             patch('filesystem_server.is_path_allowed') as mock_is_allowed:
            
            mock_sanitize.return_value = "test.txt"
            mock_is_allowed.return_value = True
            
            result = read_resource("test.txt")
            assert result == "Hello, World!"

    def test_read_resource_access_denied(self):
        """Test reading resource with access denied."""
        with patch('filesystem_server.sanitize_path') as mock_sanitize, \
             patch('filesystem_server.is_path_allowed') as mock_is_allowed:
            
            mock_sanitize.return_value = "../../../etc/passwd"
            mock_is_allowed.return_value = False
            
            result = read_resource("../../../etc/passwd")
            assert "Error: Access denied" in result

    def test_read_resource_file_not_found(self):
        """Test reading nonexistent file resource."""
        with patch('filesystem_server.sanitize_path') as mock_sanitize, \
             patch('filesystem_server.is_path_allowed') as mock_is_allowed:
            
            mock_sanitize.return_value = "nonexistent.txt"
            mock_is_allowed.return_value = True
            
            result = read_resource("nonexistent.txt")
            assert "Error: File not found" in result

    def test_read_resource_not_file(self):
        """Test reading directory as resource."""
        with patch('filesystem_server.sanitize_path') as mock_sanitize, \
             patch('filesystem_server.is_path_allowed') as mock_is_allowed:
            
            mock_sanitize.return_value = "subdir"
            mock_is_allowed.return_value = True
            
            result = read_resource("subdir")
            assert "Error: Not a file" in result


class TestPrompts(TestFilesystemServer):
    """Test prompt templates."""

    @pytest.mark.asyncio
    async def test_analyze_directory_prompt(self):
        """Test analyze_directory prompt template."""
        result = await analyze_directory(".")
        
        assert "analyze the directory" in result
        assert "Total number of files" in result
        assert "File type distribution" in result
        assert "list_files tool" in result

    @pytest.mark.asyncio
    async def test_analyze_directory_prompt_custom_dir(self):
        """Test analyze_directory prompt with custom directory."""
        result = await analyze_directory("subdir")
        
        assert "analyze the directory 'subdir'" in result

    @pytest.mark.asyncio
    async def test_summarize_file_prompt(self):
        """Test summarize_file prompt template."""
        result = await summarize_file("test.txt")
        
        assert "read the file at 'test.txt'" in result
        assert "Maximum length: 100 words" in result
        assert "read_file tool" in result

    @pytest.mark.asyncio
    async def test_summarize_file_prompt_custom_length(self):
        """Test summarize_file prompt with custom max length."""
        result = await summarize_file("test.txt", 50)
        
        assert "Maximum length: 50 words" in result


class TestMCPServerIntegration(TestFilesystemServer):
    """Test MCP server integration."""

    @pytest.mark.asyncio
    async def test_server_has_tools(self):
        """Test that server has expected tools."""
        tools = await mcp.list_tools()
        tool_names = [tool.name for tool in tools]
        
        expected_tools = ["list_files", "read_file", "write_file", "create_directory"]
        for tool in expected_tools:
            assert tool in tool_names

    @pytest.mark.asyncio
    async def test_server_has_resources(self):
        """Test that server has expected resources."""
        resources = await mcp.list_resources()
        # Filesystem server has resource patterns defined but may return empty list
        # This is expected behavior for FastMCP with template resources
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_server_has_prompts(self):
        """Test that server has expected prompts."""
        prompts = await mcp.list_prompts()
        prompt_names = [prompt.name for prompt in prompts]
        
        expected_prompts = ["analyze_directory", "summarize_file"]
        for prompt in expected_prompts:
            assert prompt in prompt_names

    @pytest.mark.asyncio
    async def test_tool_schemas(self):
        """Test that tools have proper schemas."""
        tools = await mcp.list_tools()
        
        for tool in tools:
            assert tool.name is not None
            assert tool.description is not None
            assert hasattr(tool, 'inputSchema')


class TestErrorHandling(TestFilesystemServer):
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # Create a file with no read permissions (if possible)
        restricted_file = Path("restricted.txt")
        restricted_file.write_text("restricted content")
        
        # Try to make it unreadable (may not work on all systems)
        try:
            restricted_file.chmod(0o000)
            
            # This should raise an error
            with pytest.raises(ValueError, match="Error reading file"):
                await read_file("restricted.txt")
                
        except OSError:
            # If we can't change permissions, skip this test
            pytest.skip("Cannot modify file permissions on this system")
        finally:
            # Restore permissions for cleanup
            try:
                restricted_file.chmod(0o644)
            except OSError:
                pass

    @pytest.mark.asyncio 
    async def test_disk_full_simulation(self):
        """Test handling of disk full errors during write."""
        # Mock write_text to raise OSError (disk full)
        with patch.object(Path, 'write_text', side_effect=OSError("No space left on device")):
            with pytest.raises(ValueError, match="Error writing file"):
                await write_file("test_disk_full.txt", "content")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])