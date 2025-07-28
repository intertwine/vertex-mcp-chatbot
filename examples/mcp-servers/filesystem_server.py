#!/usr/bin/env python3
"""
File System MCP Server

A simple MCP server that provides file system operations through stdio transport.
This server demonstrates basic MCP concepts including tools, resources, and prompts.

Usage:
    python filesystem_server.py
"""

import os
import signal
import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("filesystem-server")

# Get base path from environment or use current directory
BASE_PATH = Path(os.environ.get("FILE_SERVER_BASE_PATH", ".")).resolve()


def validate_path(path: str) -> Optional[Path]:
    """Validate that path is within base directory."""
    target_path = (BASE_PATH / path).resolve()
    if not str(target_path).startswith(str(BASE_PATH)):
        return None
    return target_path


def get_mime_type(suffix: str) -> str:
    """Get MIME type from file extension."""
    mime_types = {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".json": "application/json",
        ".py": "text/x-python",
        ".js": "text/javascript",
        ".html": "text/html",
        ".css": "text/css",
        ".xml": "text/xml",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
    }
    return mime_types.get(suffix.lower(), "text/plain")


def sanitize_path(path: str) -> str:
    """Sanitize path by removing dangerous components."""
    # Remove leading slashes and resolve relative components
    try:
        return str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        # If path can't be resolved relative to cwd, just use the path as-is
        return path


def is_path_allowed(path: Path) -> bool:
    """Check if path is allowed (within base directory)."""
    try:
        path.resolve().relative_to(BASE_PATH.resolve())
        return True
    except ValueError:
        return False


@mcp.tool()
async def list_files(directory: str = ".", pattern: str = "*") -> dict:
    """
    List files in a directory.
    
    Args:
        directory: Directory path relative to base directory
        pattern: Glob pattern to filter files (e.g., '*.txt')
    
    Returns:
        Dictionary with directory info and list of files
    """
    target_path = validate_path(directory)
    if not target_path:
        raise ValueError("Access denied: Path outside base directory")
    
    if not target_path.exists():
        raise ValueError(f"Directory not found: {directory}")
    
    if not target_path.is_dir():
        raise ValueError(f"Not a directory: {directory}")
    
    # List files matching pattern
    files = []
    for item in target_path.glob(pattern):
        if item.is_file():
            files.append({
                "name": item.name,
                "size": item.stat().st_size,
                "modified": item.stat().st_mtime
            })
    
    return {
        "directory": str(directory),
        "files": files,
        "count": len(files)
    }


@mcp.tool()
async def read_file(path: str) -> str:
    """
    Read the contents of a file.
    
    Args:
        path: File path relative to base directory
    
    Returns:
        File contents as string
    """
    target_path = validate_path(path)
    if not target_path:
        raise ValueError("Access denied: Path outside base directory")
    
    if not target_path.exists():
        raise ValueError(f"File not found: {path}")
    
    if not target_path.is_file():
        raise ValueError(f"Not a file: {path}")
    
    try:
        return target_path.read_text(encoding='utf-8')
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")


@mcp.tool()
async def write_file(path: str, content: str) -> str:
    """
    Write content to a file.
    
    Args:
        path: File path relative to base directory
        content: Content to write to the file
    
    Returns:
        Success message
    """
    target_path = validate_path(path)
    if not target_path:
        raise ValueError("Access denied: Path outside base directory")
    
    try:
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write content
        target_path.write_text(content, encoding='utf-8')
        
        return f"Successfully wrote {len(content)} bytes to {path}"
    except Exception as e:
        raise ValueError(f"Error writing file: {str(e)}")


@mcp.tool()
async def create_directory(path: str) -> str:
    """
    Create a new directory.
    
    Args:
        path: Directory path relative to base directory
    
    Returns:
        Success message
    """
    target_path = validate_path(path)
    if not target_path:
        raise ValueError("Access denied: Path outside base directory")
    
    try:
        target_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created directory: {path}"
    except Exception as e:
        raise ValueError(f"Error creating directory: {str(e)}")


# Resources - expose some files as resources
@mcp.resource("file:///{path}")
def read_resource(path: str) -> str:
    """
    Read a file resource.
    
    Args:
        path: File path relative to base directory
    
    Returns:
        File contents
    """
    # For sync resource, read file directly
    safe_path = sanitize_path(path)
    full_path = BASE_PATH / safe_path
    
    # Security check
    if not is_path_allowed(full_path):
        return f"Error: Access denied - path outside base directory"
    
    # Check if file exists
    if not full_path.exists():
        return f"Error: File not found: {path}"
    
    # Check if it's a file
    if not full_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        # Read the file
        return full_path.read_text(encoding='utf-8')
    except Exception as e:
        return f"Error reading file: {str(e)}"


# Prompts
@mcp.prompt()
async def analyze_directory(directory: str = ".") -> str:
    """
    Analyze the structure and contents of a directory.
    
    Args:
        directory: Directory path to analyze
    
    Returns:
        Prompt text for directory analysis
    """
    return f"""Please analyze the directory '{directory}' and provide:
1. Total number of files and subdirectories
2. File type distribution (by extension)
3. Total size of all files
4. Most recently modified files
5. Any notable patterns or observations

Use the list_files tool to explore the directory structure."""


@mcp.prompt()
async def summarize_file(file_path: str, max_length: int = 100) -> str:
    """
    Summarize the contents of a file.
    
    Args:
        file_path: Path to the file to summarize
        max_length: Maximum length of summary in words
    
    Returns:
        Prompt text for file summarization
    """
    return f"""Please read the file at '{file_path}' and provide a concise summary.

Requirements:
- Maximum length: {max_length} words
- Include the main purpose or content of the file
- Highlight any key sections or important information
- Note the file type and structure

Use the read_file tool to access the file contents."""


def run_with_graceful_shutdown():
    """Run the server with graceful shutdown handling."""
    import threading
    shutdown_event = threading.Event()
    
    def signal_handler(signum, _):
        """Handle shutdown signals gracefully."""
        signal_name = ("SIGINT" if signum == signal.SIGINT 
                      else f"Signal {signum}")
        print(f"\n{signal_name} received. Shutting down File System "
              f"MCP Server gracefully...", file=sys.stderr)
        shutdown_event.set()
        # Force exit after a brief moment
        threading.Timer(0.1, lambda: os._exit(0)).start()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the server
        mcp.run()
    except KeyboardInterrupt:
        # This should be caught by signal handler, but just in case
        print("\nKeyboard interrupt received. Shutting down File System "
              "MCP Server gracefully...", file=sys.stderr)
        os._exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        print("Shutting down File System MCP Server...", file=sys.stderr)
        os._exit(1)


if __name__ == "__main__":
    # Simple startup message without Ctrl+C instruction
    print("Starting File System MCP Server", file=sys.stderr)
    print(f"Base path: {BASE_PATH}", file=sys.stderr)
    
    # Run with graceful shutdown handling
    run_with_graceful_shutdown()
