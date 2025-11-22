# quality.mk - Code quality checks
# Part of mcp-ticketer modular Makefile architecture

##@ Code Quality

.PHONY: lint
lint: ## Run all linters (ruff, mypy)
	@echo "Running linters..."
	ruff check src tests
	mypy src

.PHONY: lint-fix
lint-fix: ## Run linters with auto-fix
	@echo "Running linters with auto-fix..."
	ruff check --fix src tests
	@echo "Linting complete!"

.PHONY: format
format: ## Format code (black, ruff for imports)
	@echo "Formatting code..."
	ruff check --select I --fix src tests
	black src tests
	@echo "Code formatted!"

.PHONY: format-check
format-check: ## Check code formatting without modifying
	@echo "Checking code formatting..."
	black --check src tests
	isort --check src tests

.PHONY: typecheck
typecheck: ## Run type checking with mypy
	@echo "Type checking..."
	mypy src

.PHONY: quality
quality: format lint test ## Run all quality checks (format + lint + test)
	@echo "All quality checks complete!"

.PHONY: pre-commit
pre-commit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

.PHONY: pre-publish
pre-publish: format lint typecheck ## Pre-publication quality gate
	@echo "✅ All pre-publish quality checks passed"

##@ Security & Auditing

.PHONY: security-check
security-check: ## Run security checks
	@echo "Running security checks..."
	bandit -r src/
	safety check

.PHONY: audit
audit: ## Run comprehensive audit (security + quality)
	@echo "Running comprehensive audit..."
	@$(MAKE) security-check
	@$(MAKE) quality
	@echo "Audit complete!"
