# Makefile for Vertex MCP Chatbot
# All targets use uv for dependency management and execution

# Default target
.PHONY: help
help:
	@echo "Vertex MCP Chatbot - Available make targets:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  make install         - Install project dependencies with uv sync"
	@echo "  make install-dev     - Install project with dev dependencies"
	@echo "  make activate        - Show how to activate the virtual environment"
	@echo "  make setup-env       - Copy .env.example to .env (if not exists)"
	@echo "  make auth            - Authenticate with Google Cloud"
	@echo ""
	@echo "Running the Chatbot:"
	@echo "  make run             - Run the chatbot with Claude (quiet MCP logging)"
	@echo "  make run-claude      - Run with Claude Sonnet 4.5 (quiet MCP logging)"
	@echo "  make run-opus        - Run with Claude Opus 4.1 (quiet MCP logging)"
	@echo "  make run-haiku       - Run with Claude Haiku 4.5 (quiet MCP logging)"
	@echo "  make run-gemini      - Run with Gemini 2.5 Flash (quiet MCP logging)"
	@echo "  make run-gemini-pro  - Run with Gemini 2.5 Pro (quiet MCP logging)"
	@echo "  make run-verbose     - Run with Claude and verbose MCP logging"
	@echo "  make run-debug       - Run with Claude and debug-level logging"
	@echo ""
	@echo "Testing:"
	@echo "  make test            - Run all tests"
	@echo "  make test-v          - Run tests with verbose output"
	@echo "  make test-cov        - Run tests with coverage report"
	@echo "  make test-unit       - Run only unit tests"
	@echo "  make test-int        - Run only integration tests"
	@echo "  make test-examples   - Run example server tests"
	@echo "  make test-examples-v - Run example server tests (verbose)"
	@echo "  make test-examples-cov - Run example server tests with coverage"
	@echo "  make test-filesystem - Run only filesystem server tests"
	@echo "  make test-weather    - Run only weather server tests"
	@echo "  make server-check    - Check example server health"
	@echo ""
	@echo "Development:"
	@echo "  make format          - Format code with black and isort"
	@echo "  make lint            - Run linting with flake8"
	@echo "  make pre-commit      - Install pre-commit hooks"
	@echo "  make pre-commit-run  - Run all pre-commit hooks manually"
	@echo "  make clean           - Clean up Python cache files"
	@echo "  make clean-all       - Clean cache and remove .venv"
	@echo ""
	@echo "Dependency Management:"
	@echo "  make add             - Add a dependency (use PKG=package-name)"
	@echo "  make add-dev         - Add a dev dependency (use PKG=package-name)"
	@echo "  make sync            - Sync dependencies from pyproject.toml"
	@echo "  make lock            - Update the lock file"
	@echo "  make show            - Show current dependencies"
	@echo ""

# Setup and Installation targets
.PHONY: install
install:
	uv sync

.PHONY: install-dev
install-dev:
	uv sync --extra dev

.PHONY: activate
activate:
	@echo "To activate the virtual environment manually, run:"
	@echo "  source .venv/bin/activate"
	@echo ""
	@echo "Note: When using 'uv run', the environment is automatically activated."

.PHONY: setup-env
setup-env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env file from .env.example"; \
		echo "Please edit .env to set your project settings:"; \
		echo "  GOOGLE_CLOUD_PROJECT='your-gcp-project-id'"; \
		echo "  GOOGLE_CLOUD_LOCATION='your-gcp-location'"; \
	else \
		echo ".env file already exists"; \
	fi

.PHONY: auth
auth:
	gcloud auth application-default login

# Running the Chatbot targets
.PHONY: run
run:
	uv run main.py --quiet-mcp

.PHONY: run-claude
run-claude:
	uv run main.py --quiet-mcp

.PHONY: run-opus
run-opus:
	uv run main.py --model claude-opus-4-1-20250805 --quiet-mcp

.PHONY: run-haiku
run-haiku:
	uv run main.py --model claude-haiku-4-5 --quiet-mcp

.PHONY: run-gemini
run-gemini:
	uv run main.py --provider gemini --quiet-mcp

.PHONY: run-gemini-pro
run-gemini-pro:
	uv run main.py --provider gemini --model gemini-2.5-pro --quiet-mcp

.PHONY: run-verbose
run-verbose:
	uv run main.py --log-level INFO

.PHONY: run-debug
run-debug:
	uv run main.py --log-level DEBUG

# Testing targets
.PHONY: test
test:
	uv run pytest tests/ -v

.PHONY: test-v
test-v:
	uv run python scripts/run_tests.py --verbose

.PHONY: test-cov
test-cov:
	uv run python scripts/run_tests.py --coverage

.PHONY: test-unit
test-unit:
	uv run python scripts/run_tests.py --unit

.PHONY: test-int
test-int:
	uv run python scripts/run_tests.py --integration

.PHONY: test-examples
test-examples:
	uv run python scripts/run_example_tests.py

.PHONY: test-examples-v
test-examples-v:
	uv run python scripts/run_example_tests.py --verbose

.PHONY: test-examples-cov
test-examples-cov:
	uv run python scripts/run_example_tests.py --coverage

.PHONY: test-filesystem
test-filesystem:
	uv run python scripts/run_example_tests.py --filesystem

.PHONY: test-weather
test-weather:
	uv run python scripts/run_example_tests.py --weather

.PHONY: server-check
server-check:
	uv run python scripts/run_example_tests.py --check

# Development targets
.PHONY: format
format:
	uv run black src/ tests/
	uv run isort src/ tests/

.PHONY: lint
lint:
	uv run flake8 src/ tests/

.PHONY: pre-commit
pre-commit:
	uv run pre-commit install

.PHONY: pre-commit-run
pre-commit-run:
	uv run pre-commit run --all-files

.PHONY: clean
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true

.PHONY: clean-all
clean-all: clean
	rm -rf .venv

# Dependency Management targets
.PHONY: add
add:
	@if [ -z "$(PKG)" ]; then \
		echo "Usage: make add PKG=package-name"; \
		exit 1; \
	fi
	uv add $(PKG)
	uv sync

.PHONY: add-dev
add-dev:
	@if [ -z "$(PKG)" ]; then \
		echo "Usage: make add-dev PKG=package-name"; \
		exit 1; \
	fi
	uv add --dev $(PKG)
	uv sync --extra dev

.PHONY: sync
sync:
	uv sync

.PHONY: lock
lock:
	uv lock

.PHONY: show
show:
	uv pip list

# Quick setup target for new users
.PHONY: setup
setup: install setup-env
	@echo ""
	@echo "Setup complete! Next steps:"
	@echo "1. Edit .env file with your GCP project settings"
	@echo "2. Run 'make auth' to authenticate with Google Cloud"
	@echo "3. Run 'make run' to start the chatbot"

# Development setup target
.PHONY: dev-setup
dev-setup: install-dev pre-commit setup-env
	@echo ""
	@echo "Development environment setup complete!"
	@echo "Pre-commit hooks installed."
	@echo "Run 'make test' to verify everything is working."
