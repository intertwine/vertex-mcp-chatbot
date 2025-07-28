#!/usr/bin/env python3
"""
Test runner for MCP example servers.

This script runs tests specifically for the example MCP servers
(filesystem_server.py and weather_server.py) to ensure they work correctly.

Usage:
    python run_example_tests.py [options]
    
    # Run all example server tests
    python run_example_tests.py
    
    # Run with verbose output
    python run_example_tests.py --verbose
    
    # Run with coverage
    python run_example_tests.py --coverage
    
    # Run only filesystem server tests
    python run_example_tests.py --filesystem
    
    # Run only weather server tests
    python run_example_tests.py --weather
    
    # Run with custom pytest options
    python run_example_tests.py --pytest-args "-x --tb=short"
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run tests for MCP example servers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests with verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    
    parser.add_argument(
        "--filesystem",
        action="store_true",
        help="Run only filesystem server tests"
    )
    
    parser.add_argument(
        "--weather",
        action="store_true",
        help="Run only weather server tests"
    )
    
    parser.add_argument(
        "--pytest-args",
        type=str,
        help="Additional pytest arguments (in quotes)"
    )
    
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help="Skip dependency check"
    )
    
    args = parser.parse_args()
    
    # Determine which tests to run
    test_files = []
    if args.filesystem and not args.weather:
        test_files = ["tests/test_filesystem_server.py"]
    elif args.weather and not args.filesystem:
        test_files = ["tests/test_weather_server.py"]
    else:
        # Run both by default
        test_files = [
            "tests/test_filesystem_server.py",
            "tests/test_weather_server.py"
        ]
    
    # Check dependencies unless skipped
    if not args.no_deps:
        if not check_dependencies():
            return 1
    
    # Build pytest command
    cmd = ["uv", "run", "pytest"]
    
    # Add test files
    cmd.extend(test_files)
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend([
            "--cov=examples/mcp-servers",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov/examples"
        ])
    
    # Add custom pytest arguments
    if args.pytest_args:
        cmd.extend(args.pytest_args.split())
    
    # Display command being run
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    # Run tests
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        return 130
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def check_dependencies():
    """Check that required dependencies are available."""
    print("Checking dependencies...")
    
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: 'uv' is not available. Please install uv package manager.")
        return False
    
    # Check if example servers exist
    project_root = Path(__file__).parent.parent  # Go up one level from scripts/
    filesystem_server = project_root / "examples" / "mcp-servers" / "filesystem_server.py"
    weather_server = project_root / "examples" / "mcp-servers" / "weather_server.py"
    
    if not filesystem_server.exists():
        print(f"Error: {filesystem_server} not found")
        return False
        
    if not weather_server.exists():
        print(f"Error: {weather_server} not found")
        return False
    
    # Check test files exist
    test_filesystem = project_root / "tests" / "test_filesystem_server.py"
    test_weather = project_root / "tests" / "test_weather_server.py"
    
    if not test_filesystem.exists():
        print(f"Error: {test_filesystem} not found")
        return False
        
    if not test_weather.exists():
        print(f"Error: {test_weather} not found")
        return False
    
    print("✅ All dependencies found")
    return True


def check_servers():
    """Check that example servers can be imported and initialized."""
    print("Checking example servers...")
    
    project_root = Path(__file__).parent.parent  # Go up one level from scripts/
    
    # Test filesystem server import
    try:
        sys.path.insert(0, str(project_root / "examples" / "mcp-servers"))
        import filesystem_server
        print("✅ filesystem_server.py imports successfully")
        
        # Check that FastMCP server is initialized
        assert filesystem_server.mcp is not None, "FastMCP server not initialized"
        print("✅ filesystem_server FastMCP instance created")
        
    except Exception as e:
        print(f"❌ Error with filesystem_server.py: {e}")
        return False
    
    # Test weather server import
    try:
        import weather_server
        print("✅ weather_server.py imports successfully")
        
        # Check that FastMCP server is initialized
        assert weather_server.mcp is not None, "FastMCP server not initialized"
        print("✅ weather_server FastMCP instance created")
        
    except Exception as e:
        print(f"❌ Error with weather_server.py: {e}")
        return False
    
    return True


def run_quick_test():
    """Run a quick smoke test of the example servers."""
    print("Running quick smoke test...")
    
    try:
        # Import and test basic functionality
        project_root = Path(__file__).parent.parent  # Go up one level from scripts/
        sys.path.insert(0, str(project_root / "examples" / "mcp-servers"))
        
        import filesystem_server
        import weather_server
        
        # Test basic functions
        print("Testing filesystem server functions...")
        assert callable(filesystem_server.validate_path)
        assert callable(filesystem_server.get_mime_type)
        print("✅ Filesystem server functions accessible")
        
        print("Testing weather server functions...")
        assert len(weather_server.WEATHER_CONDITIONS) > 0
        print("✅ Weather server constants available")
        
        print("✅ Quick smoke test passed")
        return True
        
    except Exception as e:
        print(f"❌ Quick smoke test failed: {e}")
        return False


def show_test_summary():
    """Show a summary of available tests."""
    print("\nExample Server Test Summary:")
    print("=" * 40)
    print("📁 Filesystem Server Tests:")
    print("  • Path validation and security")
    print("  • File operations (list, read, write)")
    print("  • Directory creation")
    print("  • Resource access patterns")
    print("  • Prompt templates")
    print("  • MCP protocol compliance")
    print()
    print("🌤️  Weather Server Tests:")
    print("  • Weather data retrieval")
    print("  • Forecast generation")
    print("  • Weather alerts")
    print("  • Resource URIs")
    print("  • Prompt templates")
    print("  • Data consistency")
    print()
    print("🔧 Integration Tests:")
    print("  • FastMCP server initialization")
    print("  • Tool registration")
    print("  • Resource registration")
    print("  • Prompt registration")
    print("  • Error handling")


if __name__ == "__main__":
    # Special handling for --help to show test summary
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        parser = argparse.ArgumentParser(description="Run tests for MCP example servers")
        parser.print_help()
        show_test_summary()
        sys.exit(0)
    
    # Special command to check servers
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        print("Checking example servers...")
        if check_dependencies() and check_servers() and run_quick_test():
            print("\n✅ All checks passed! Example servers are ready for testing.")
            sys.exit(0)
        else:
            print("\n❌ Some checks failed. See output above.")
            sys.exit(1)
    
    # Special command to show summary
    if len(sys.argv) > 1 and sys.argv[1] == "--summary":
        show_test_summary()
        sys.exit(0)
    
    # Run main test runner
    sys.exit(main())