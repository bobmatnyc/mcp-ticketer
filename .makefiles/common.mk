# common.mk - Infrastructure and environment detection
# Part of mcp-ticketer modular Makefile architecture

##@ Environment Information

# OS Detection
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
	OS := linux
	OPEN_CMD := xdg-open
endif
ifeq ($(UNAME_S),Darwin)
	OS := macos
	OPEN_CMD := open
endif
ifeq ($(findstring MINGW,$(UNAME_S)),MINGW)
	OS := windows
	OPEN_CMD := start
endif

# Python executable detection
PYTHON := $(shell command -v python3 2> /dev/null || command -v python 2> /dev/null)
PIP := $(PYTHON) -m pip

# Project paths
PROJECT_ROOT := $(shell pwd)
SRC_DIR := $(PROJECT_ROOT)/src
TESTS_DIR := $(PROJECT_ROOT)/tests
DOCS_DIR := $(PROJECT_ROOT)/docs

# Version detection
VERSION := $(shell $(PYTHON) -c 'from src.mcp_ticketer.__version__ import __version__; print(__version__)' 2>/dev/null || echo "unknown")

# CPU count for parallel operations
CPUS := $(shell $(PYTHON) -c 'import multiprocessing; print(multiprocessing.cpu_count())' 2>/dev/null || echo 4)

##@ Setup & Installation

.PHONY: install
install: ## Install package and dependencies
	@echo "Installing mcp-ticketer..."
	$(PIP) install -e .

.PHONY: install-dev
install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	$(PIP) install -e ".[dev,test,docs,all]"
	pre-commit install

.PHONY: install-all
install-all: ## Install with all adapters (jira, linear, github)
	@echo "Installing with all adapters..."
	$(PIP) install -e ".[all,dev,test,docs]"

.PHONY: setup
setup: install-dev ## Complete development setup (alias for install-dev)
	@echo "Development environment ready!"

##@ Environment Management

.PHONY: info
info: ## Show project information
	@echo "==================================="
	@echo "mcp-ticketer Project Information"
	@echo "==================================="
	@echo "Version:      $(VERSION)"
	@echo "OS:           $(OS)"
	@echo "Python:       $(shell $(PYTHON) --version)"
	@echo "CPU Cores:    $(CPUS)"
	@echo "Project Root: $(PROJECT_ROOT)"
	@echo "Virtual Env:  $${VIRTUAL_ENV:-Not activated}"
	@echo "==================================="

.PHONY: check-env
check-env: ## Check required environment variables
	@echo "Checking environment variables..."
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version)"
	@echo "Virtual environment: $${VIRTUAL_ENV:-Not activated}"
	@if command -v mcp-ticketer >/dev/null 2>&1; then echo "mcp-ticketer: Installed"; else echo "mcp-ticketer: Not installed"; fi

.PHONY: venv
venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

.PHONY: activate
activate: ## Show activation command
	@echo "To activate virtual environment, run:"
	@echo "  source venv/bin/activate  # On macOS/Linux"
	@echo "  venv\\Scripts\\activate    # On Windows"

##@ Maintenance

.PHONY: update-deps
update-deps: ## Update all dependencies
	@echo "Updating dependencies..."
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install --upgrade -e ".[all,dev,test,docs]"
	@echo "Dependencies updated!"

.PHONY: clean-build
clean-build: ## Clean build artifacts only
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info

.PHONY: clean
clean: clean-build ## Clean build artifacts and cache
	@echo "Cleaning cache..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
	@echo "Clean complete!"
