.PHONY: help venv install install-browsers clean clean-cache clean-sessions clean-all run run-headless run-new-session run-fast run-slow lint format format-check build publish publish-test install-editable

# Python interpreter
PYTHON := python3
VENV := venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PYTHON_VENV := $(BIN)/python

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@echo "Virtual environment created at $(VENV)"
	@echo "Run 'source $(VENV)/bin/activate' to activate it"

install: venv ## Install dependencies in virtual environment
	@echo "Installing dependencies..."
	@$(PIP) install --upgrade pip
	@$(PIP) install -e ".[yaml]"
	@echo "Dependencies installed successfully"
	@echo "Don't forget to run 'make install-browsers' to install Playwright browsers"

install-browsers: ## Install Playwright browser binaries
	@echo "Installing Playwright browsers..."
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@$(PYTHON_VENV) -m playwright install
	@echo "Playwright browsers installed successfully"

run: ## Run the main script (default query)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@$(PYTHON_VENV) main.py

lint: ## Check code style with pylint (if installed)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Linting code..."
	@if $(PIP) list | grep -q pylint; then \
		$(PYTHON_VENV) -m pylint main.py modules/*.py; \
	else \
		echo "pylint not installed. Run 'make install-dev' first"; \
	fi

format: ## Format code with black (if installed)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Formatting code..."
	@if $(PIP) list | grep -q black; then \
		$(PYTHON_VENV) -m black main.py modules/; \
	else \
		echo "black not installed. Run 'make install-dev' first"; \
	fi

format-check: ## Check code formatting without modifying (useful for CI)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Checking code formatting..."
	@if $(PIP) list | grep -q black; then \
		$(PYTHON_VENV) -m black --check --diff main.py modules/; \
	else \
		echo "black not installed. Run 'make install-dev' first"; \
	fi

clean-cache: ## Clean Python cache files
	@echo "Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.pyd" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf build/ dist/ .eggs/ 2>/dev/null || true
	@echo "Python cache cleaned"

clean-sessions: ## Clean up browser session data
	@echo "Cleaning session data..."
	@rm -rf sessions/
	@rm -f captcha_log.json
	@rm -f debug_*.png
	@rm -f *.log
	@echo "Session data cleaned"

clean: clean-cache clean-sessions ## Clean cache and session data (keep venv)
	@echo "Cleanup complete (virtual environment preserved)"

clean-all: clean ## Remove everything including virtual environment
	@echo "Removing virtual environment..."
	@rm -rf $(VENV)
	@echo "Complete cleanup done"

setup: install install-browsers ## Complete setup: create venv, install deps and browsers
	@echo "Setup complete! Run 'source $(VENV)/bin/activate' to activate the environment"

# Development tools (optional dependencies)
install-dev: install ## Install development dependencies
	@echo "Installing development dependencies..."
	@$(PIP) install -e ".[dev]"
	@$(PIP) install build twine
	@echo "Development dependencies installed"

install-editable: ## Install package in editable mode
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Installing package in editable mode..."
	@$(PIP) install -e .
	@echo "Package installed in editable mode"

# Package building and publishing
build: clean ## Build distribution packages
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Building distribution packages..."
	@$(PIP) install --upgrade build
	@$(PYTHON_VENV) -m build
	@echo "Build complete! Packages in dist/"
	@ls -lh dist/

publish-test: build ## Publish to TestPyPI (for testing)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "Publishing to TestPyPI..."
	@$(PIP) install --upgrade twine
	@$(PYTHON_VENV) -m twine upload --repository testpypi dist/*
	@echo "Published to TestPyPI!"
	@echo "Install with: pip install --index-url https://test.pypi.org/simple/ google-search-resource"

publish: build ## Publish to PyPI (production)
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	@echo "WARNING: This will publish to PyPI (production)!"
	@echo "Make sure you have:"
	@echo "  1. Updated version in pyproject.toml"
	@echo "  2. Committed and tagged the release"
	@echo "  3. Pushed to repository"
	@echo ""
	@read -p "Continue? (y/N) " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(PIP) install --upgrade twine
	@$(PYTHON_VENV) -m twine upload dist/*
	@echo "Published to PyPI!"
	@echo "Install with: pip install google-search-resource"


