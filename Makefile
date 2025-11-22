# Makefile - Main entry point for mcp-ticketer build system
#
# This Makefile uses a modular architecture with specialized modules in .makefiles/
# Each module handles a specific aspect of the build system:
#   - common.mk: Infrastructure and environment detection
#   - quality.mk: Code quality checks (Ruff, MyPy, Black, isort)
#   - testing.mk: Testing infrastructure (pytest, coverage, parallel execution)
#   - release.mk: Release automation (versioning, building, publishing)
#   - docs.mk: Documentation build and management
#   - mcp.mk: mcp-ticketer-specific targets
#
# Architecture inspired by python-project-template with mcp-ticketer adaptations.

.PHONY: help
.DEFAULT_GOAL := help

# Include all modules (order matters for variable dependencies)
include .makefiles/common.mk
include .makefiles/quality.mk
include .makefiles/testing.mk
include .makefiles/release.mk
include .makefiles/docs.mk
include .makefiles/mcp.mk

##@ Help

help: ## Display this help message
	@echo ""
	@echo "╔════════════════════════════════════════════════════════════════╗"
	@echo "║           mcp-ticketer Modular Build System                   ║"
	@echo "╚════════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; section=""} \
		/^##@/ { section=substr($$0, 5); printf "\n\033[1m%s\033[0m\n", section; next } \
		/^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2 } \
	' $(MAKEFILE_LIST)
	@echo ""
	@echo "For more details, see .makefiles/README.md"
	@echo ""
	@echo "Quick Start:"
	@echo "  make setup           # Setup development environment"
	@echo "  make test            # Run tests"
	@echo "  make test-parallel   # Run tests in parallel (faster)"
	@echo "  make lint            # Run linters"
	@echo "  make format          # Format code"
	@echo ""

.PHONY: modules
modules: ## Show loaded modules and their paths
	@echo "Loaded Makefile Modules:"
	@echo "  common.mk:   $(PROJECT_ROOT)/.makefiles/common.mk"
	@echo "  quality.mk:  $(PROJECT_ROOT)/.makefiles/quality.mk"
	@echo "  testing.mk:  $(PROJECT_ROOT)/.makefiles/testing.mk"
	@echo "  release.mk:  $(PROJECT_ROOT)/.makefiles/release.mk"
	@echo "  docs.mk:     $(PROJECT_ROOT)/.makefiles/docs.mk"
	@echo "  mcp.mk:      $(PROJECT_ROOT)/.makefiles/mcp.mk"
