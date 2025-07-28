#!/usr/bin/env python3
"""Test runner script for the Vertex AI Chatbot project."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False):
    """
    Run tests with various options.

    Args:
        test_type: Type of tests to run ("all", "unit", "integration", "specific")
        verbose: Whether to run in verbose mode
        coverage: Whether to generate coverage report
    """
    # Base pytest command
    cmd = ["python", "-m", "pytest"]

    # Add verbosity
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")

    # Add coverage if requested
    if coverage:
        cmd.extend(
            [
                "--cov=src",
                "--cov-report=html",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
            ]
        )

    # Add test selection based on type
    if test_type == "unit":
        cmd.extend(["-m", "not integration"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "specific":
        # This will be handled by the caller passing specific test files
        pass
    # For "all", we don't add any filters

    # Add test directory
    cmd.append("tests/")

    print(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Error: pytest not found. Please install it with:")
        print("pip install pytest")
        if coverage:
            print("pip install pytest-cov")
        return 1


def main():
    """Main function for the test runner."""
    parser = argparse.ArgumentParser(
        description="Run tests for the Vertex AI Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s --unit                   # Run only unit tests
  %(prog)s --integration            # Run only integration tests
  %(prog)s --coverage               # Run with coverage report
  %(prog)s --verbose --coverage     # Verbose output with coverage
        """,
    )

    parser.add_argument("--unit", action="store_true", help="Run only unit tests")

    parser.add_argument(
        "--integration", action="store_true", help="Run only integration tests"
    )

    parser.add_argument(
        "--coverage", action="store_true", help="Generate coverage report"
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    parser.add_argument("test_files", nargs="*", help="Specific test files to run")

    args = parser.parse_args()

    # Determine test type
    if args.unit:
        test_type = "unit"
    elif args.integration:
        test_type = "integration"
    elif args.test_files:
        test_type = "specific"
        # Override the pytest command to run specific files
        cmd = ["python", "-m", "pytest"]
        if args.verbose:
            cmd.append("-v")
        if args.coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term-missing"])
        cmd.extend(args.test_files)

        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=False)
        return result.returncode
    else:
        test_type = "all"

    return run_tests(test_type, args.verbose, args.coverage)


if __name__ == "__main__":
    sys.exit(main())
