# testing.mk - Testing infrastructure
# Part of mcp-ticketer modular Makefile architecture

##@ Testing

.PHONY: test
test: ## Run all tests
	@echo "Running tests..."
	pytest

.PHONY: test-parallel
test-parallel: ## Run tests in parallel (3-4x faster)
	@echo "Running tests in parallel ($(CPUS) CPUs)..."
	pytest -n $(CPUS) tests/

.PHONY: test-fast
test-fast: ## Run tests in parallel with fail-fast
	@echo "Running tests in parallel with fail-fast..."
	pytest -n $(CPUS) -x tests/

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest tests/unit/ -v

.PHONY: test-integration
test-integration: ## Run integration tests
	@echo "Running integration tests..."
	pytest tests/integration/ -v -m integration

.PHONY: test-e2e
test-e2e: ## Run end-to-end tests
	@echo "Running e2e tests..."
	pytest tests/e2e/ -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest --cov=mcp_ticketer --cov-report=html --cov-report=term-missing

.PHONY: test-coverage-parallel
test-coverage-parallel: ## Run tests with coverage in parallel
	@echo "Running tests with coverage in parallel..."
	pytest -n $(CPUS) --cov=mcp_ticketer --cov-report=html --cov-report=term-missing

.PHONY: test-watch
test-watch: ## Run tests in watch mode
	@echo "Running tests in watch mode..."
	pytest-watch

.PHONY: test-verbose
test-verbose: ## Run tests with verbose output
	@echo "Running tests with verbose output..."
	pytest -vv tests/

.PHONY: test-markers
test-markers: ## Show available test markers
	@echo "Available test markers:"
	@pytest --markers

##@ CI/CD Simulation

.PHONY: ci-test
ci-test: ## Simulate CI test pipeline
	@echo "Simulating CI test pipeline..."
	@$(MAKE) lint
	@$(MAKE) typecheck
	@$(MAKE) test-coverage
	@echo "CI test pipeline complete!"

.PHONY: ci-build
ci-build: ## Simulate CI build pipeline
	@echo "Simulating CI build pipeline..."
	@$(MAKE) clean
	@$(MAKE) build
	@echo "CI build pipeline complete!"

.PHONY: ci
ci: ci-test ci-build ## Simulate full CI pipeline
	@echo "Full CI pipeline complete!"
