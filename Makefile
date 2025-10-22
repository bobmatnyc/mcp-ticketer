# MCP Ticketer Makefile
# Single-path commands for all operations

.PHONY: help install dev test lint format quality build clean publish docs serve

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup & Installation

install: ## Install package and dependencies
	@echo "Installing mcp-ticketer..."
	pip install -e .

install-dev: ## Install development dependencies
	@echo "Installing development dependencies..."
	pip install -e ".[dev,test,docs,all]"
	pre-commit install

install-all: ## Install with all adapters (jira, linear, github)
	@echo "Installing with all adapters..."
	pip install -e ".[all,dev,test,docs]"

setup: install-dev ## Complete development setup (alias for install-dev)
	@echo "Development environment ready!"

##@ Development

dev: ## Run in development mode (start MCP server)
	@echo "Starting MCP Ticketer server..."
	mcp-ticketer-server

cli: ## Run CLI in interactive mode
	@echo "MCP Ticketer CLI ready. Use 'mcp-ticketer --help' for commands"
	mcp-ticketer

##@ Testing

test: ## Run all tests
	@echo "Running tests..."
	pytest

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest tests/unit/ -v

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	pytest tests/integration/ -v -m integration

test-e2e: ## Run end-to-end tests
	@echo "Running e2e tests..."
	pytest tests/e2e/ -v

test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest --cov=mcp_ticketer --cov-report=html --cov-report=term-missing

test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	pytest-watch

##@ Code Quality

lint: ## Run all linters (ruff, mypy)
	@echo "Running linters..."
	ruff check src tests
	mypy src

lint-fix: ## Run linters with auto-fix
	@echo "Running linters with auto-fix..."
	ruff check --fix src tests
	@echo "Linting complete!"

format: ## Format code (black, isort)
	@echo "Formatting code..."
	black src tests
	isort src tests
	@echo "Code formatted!"

typecheck: ## Run type checking with mypy
	@echo "Type checking..."
	mypy src

quality: format lint test ## Run all quality checks (format + lint + test)
	@echo "All quality checks complete!"

pre-commit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

##@ Building & Publishing

clean-build: ## Clean build artifacts only
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ *.egg-info

clean: clean-build ## Clean build artifacts and cache
	@echo "Cleaning cache..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf htmlcov/ .coverage
	@echo "Clean complete!"

build: clean-build ## Build distribution packages
	@echo "Building distribution..."
	python3 -m build
	@python3 scripts/manage_version.py track-build
	@echo "Build complete! Packages in dist/"

publish-test: check-release build ## Build and publish to TestPyPI
	@echo "Publishing to TestPyPI..."
	twine upload --repository testpypi dist/*
	@echo "Published to TestPyPI!"

publish-prod: check-release build ## Build and publish to PyPI
	@echo "Publishing to PyPI..."
	twine upload dist/*
	@echo "Published successfully!"

publish: publish-prod ## Alias for publish-prod

##@ Full Release Workflow

release-patch: version-bump-patch build publish-prod ## Release new patch version (X.Y.Z+1)
	@echo "✅ Patch release complete!"
	@python3 scripts/manage_version.py get-version

release-minor: version-bump-minor build publish-prod ## Release new minor version (X.Y+1.0)
	@echo "✅ Minor release complete!"
	@python3 scripts/manage_version.py get-version

release-major: version-bump-major build publish-prod ## Release new major version (X+1.0.0)
	@echo "✅ Major release complete!"
	@python3 scripts/manage_version.py get-version

##@ Documentation

docs: ## Build documentation
	@echo "Building documentation..."
	cd docs && make html
	@echo "Documentation built! Open docs/_build/html/index.html"

docs-serve: docs ## Build and serve documentation locally
	@echo "Serving documentation at http://localhost:8000"
	cd docs/_build/html && python -m http.server 8000

docs-clean: ## Clean documentation build
	@echo "Cleaning documentation..."
	cd docs && make clean

##@ Version Management

version: ## Show current version
	@python3 scripts/manage_version.py get-version

version-bump-patch: ## Bump patch version (0.0.X)
	@echo "Bumping patch version..."
	@python3 scripts/manage_version.py bump patch --git-commit --git-tag

version-bump-minor: ## Bump minor version (0.X.0)
	@echo "Bumping minor version..."
	@python3 scripts/manage_version.py bump minor --git-commit --git-tag

version-bump-major: ## Bump major version (X.0.0)
	@echo "Bumping major version..."
	@python3 scripts/manage_version.py bump major --git-commit --git-tag

check-release: ## Validate release readiness
	@echo "Validating release readiness..."
	@python3 scripts/manage_version.py check-release

##@ Adapter Management

init-aitrackdown: ## Initialize AI-Trackdown adapter
	@echo "Initializing AI-Trackdown adapter..."
	mcp-ticketer init --adapter aitrackdown

init-linear: ## Initialize Linear adapter (requires LINEAR_API_KEY, LINEAR_TEAM_ID)
	@echo "Initializing Linear adapter..."
	@if [ -z "$$LINEAR_API_KEY" ]; then echo "Error: LINEAR_API_KEY not set"; exit 1; fi
	@if [ -z "$$LINEAR_TEAM_ID" ]; then echo "Error: LINEAR_TEAM_ID not set"; exit 1; fi
	mcp-ticketer init --adapter linear --team-id $$LINEAR_TEAM_ID

init-jira: ## Initialize JIRA adapter (requires JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN)
	@echo "Initializing JIRA adapter..."
	@if [ -z "$$JIRA_SERVER" ]; then echo "Error: JIRA_SERVER not set"; exit 1; fi
	@if [ -z "$$JIRA_EMAIL" ]; then echo "Error: JIRA_EMAIL not set"; exit 1; fi
	@if [ -z "$$JIRA_API_TOKEN" ]; then echo "Error: JIRA_API_TOKEN not set"; exit 1; fi
	mcp-ticketer init --adapter jira --jira-server $$JIRA_SERVER --jira-email $$JIRA_EMAIL

init-github: ## Initialize GitHub adapter (requires GITHUB_TOKEN, GITHUB_REPO)
	@echo "Initializing GitHub adapter..."
	@if [ -z "$$GITHUB_TOKEN" ]; then echo "Error: GITHUB_TOKEN not set"; exit 1; fi
	@if [ -z "$$GITHUB_REPO" ]; then echo "Error: GITHUB_REPO not set"; exit 1; fi
	mcp-ticketer init --adapter github --repo $$GITHUB_REPO

##@ Quick Operations

create: ## Create a new ticket (usage: make create TITLE="..." DESC="..." PRIORITY="high")
	@if [ -z "$(TITLE)" ]; then echo "Error: TITLE required. Usage: make create TITLE='...'"; exit 1; fi
	@mcp-ticketer create "$(TITLE)" $${DESC:+--description "$$DESC"} $${PRIORITY:+--priority "$$PRIORITY"}

list: ## List tickets (usage: make list STATE="open" LIMIT=10)
	@mcp-ticketer list $${STATE:+--state "$$STATE"} $${LIMIT:+--limit "$$LIMIT"}

search: ## Search tickets (usage: make search QUERY="bug")
	@if [ -z "$(QUERY)" ]; then echo "Error: QUERY required. Usage: make search QUERY='...'"; exit 1; fi
	@mcp-ticketer search "$(QUERY)"

##@ Environment

check-env: ## Check required environment variables
	@echo "Checking environment variables..."
	@echo "Python version: $$(python --version)"
	@echo "Pip version: $$(pip --version)"
	@echo "Virtual environment: $${VIRTUAL_ENV:-Not activated}"
	@if command -v mcp-ticketer >/dev/null 2>&1; then echo "mcp-ticketer: Installed"; else echo "mcp-ticketer: Not installed"; fi

venv: ## Create virtual environment
	@echo "Creating virtual environment..."
	python -m venv venv
	@echo "Virtual environment created. Activate with: source venv/bin/activate"

activate: ## Show activation command
	@echo "To activate virtual environment, run:"
	@echo "  source venv/bin/activate  # On macOS/Linux"
	@echo "  venv\\Scripts\\activate    # On Windows"

##@ Maintenance

update-deps: ## Update all dependencies
	@echo "Updating dependencies..."
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -e ".[all,dev,test,docs]"
	@echo "Dependencies updated!"

security-check: ## Run security checks
	@echo "Running security checks..."
	bandit -r src/
	safety check

audit: ## Run comprehensive audit (security + quality)
	@echo "Running comprehensive audit..."
	@make security-check
	@make quality
	@echo "Audit complete!"

##@ CI/CD Simulation

ci-test: ## Simulate CI test pipeline
	@echo "Simulating CI test pipeline..."
	@make lint
	@make typecheck
	@make test-coverage
	@echo "CI test pipeline complete!"

ci-build: ## Simulate CI build pipeline
	@echo "Simulating CI build pipeline..."
	@make clean
	@make build
	@echo "CI build pipeline complete!"

ci: ci-test ci-build ## Simulate full CI pipeline
	@echo "Full CI pipeline complete!"
