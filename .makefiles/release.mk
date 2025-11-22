# release.mk - Release automation
# Part of mcp-ticketer modular Makefile architecture

##@ Version Management

.PHONY: version
version: ## Show current version
	@$(PYTHON) scripts/manage_version.py get-version

.PHONY: version-bump-patch
version-bump-patch: ## Bump patch version (0.0.X)
	@echo "Bumping patch version..."
	@$(PYTHON) scripts/manage_version.py bump patch --git-commit --git-tag

.PHONY: version-bump-minor
version-bump-minor: ## Bump minor version (0.X.0)
	@echo "Bumping minor version..."
	@$(PYTHON) scripts/manage_version.py bump minor --git-commit --git-tag

.PHONY: version-bump-major
version-bump-major: ## Bump major version (X.0.0)
	@echo "Bumping major version..."
	@$(PYTHON) scripts/manage_version.py bump major --git-commit --git-tag

.PHONY: check-release
check-release: ## Validate release readiness
	@echo "Validating release readiness..."
	@$(PYTHON) scripts/manage_version.py check-release

##@ Building & Publishing

.PHONY: build
build: clean-build ## Build distribution packages
	@echo "Building distribution..."
	$(PYTHON) -m build
	@$(PYTHON) scripts/manage_version.py track-build
	@echo "Build complete! Packages in dist/"

.PHONY: build-metadata
build-metadata: ## Generate build metadata
	@echo "Generating build metadata..."
	@echo "Build Time: $$(date -u +"%Y-%m-%dT%H:%M:%SZ")" > BUILD_INFO
	@echo "Git Commit: $$(git rev-parse HEAD 2>/dev/null || echo 'unknown')" >> BUILD_INFO
	@echo "Version: $(VERSION)" >> BUILD_INFO
	@echo "OS: $(OS)" >> BUILD_INFO
	@echo "Python: $$($(PYTHON) --version)" >> BUILD_INFO
	@cat BUILD_INFO

.PHONY: safe-release-build
safe-release-build: pre-publish build ## Build release with quality gate
	@echo "✅ Safe release build complete"

.PHONY: publish-test
publish-test: check-release format lint test test-e2e build ## Build and publish to TestPyPI
	@echo "Publishing to TestPyPI..."
	@if [ -f .env.local ]; then \
		echo "Loading PyPI credentials from .env.local..."; \
		export $$(grep -E '^(TWINE_USERNAME|TWINE_PASSWORD)=' .env.local | xargs) && \
		twine upload --repository testpypi dist/*; \
	else \
		echo "No .env.local found, using default credentials (~/.pypirc or environment)..."; \
		twine upload --repository testpypi dist/*; \
	fi
	@echo "Published to TestPyPI!"

.PHONY: publish-prod
publish-prod: check-release format lint test test-e2e build ## Build and publish to PyPI
	@echo "Publishing to PyPI..."
	@if [ -f .env.local ]; then \
		echo "Loading PyPI credentials from .env.local..."; \
		export $$(grep -E '^(TWINE_USERNAME|TWINE_PASSWORD)=' .env.local | xargs) && \
		twine upload dist/*; \
	else \
		echo "No .env.local found, using default credentials (~/.pypirc or environment)..."; \
		twine upload dist/*; \
	fi
	@echo "Published successfully!"

.PHONY: publish
publish: publish-prod ## Alias for publish-prod

##@ Full Release Workflow

.PHONY: release-patch
release-patch: version-bump-patch build publish-prod ## Release new patch version (X.Y.Z+1)
	@echo "✅ Patch release complete!"
	@$(PYTHON) scripts/manage_version.py get-version

.PHONY: release-minor
release-minor: version-bump-minor build publish-prod ## Release new minor version (X.Y+1.0)
	@echo "✅ Minor release complete!"
	@$(PYTHON) scripts/manage_version.py get-version

.PHONY: release-major
release-major: version-bump-major build publish-prod ## Release new major version (X+1.0.0)
	@echo "✅ Major release complete!"
	@$(PYTHON) scripts/manage_version.py get-version

##@ Release Verification

.PHONY: verify-dist
verify-dist: ## Verify distribution packages
	@echo "Verifying distribution packages..."
	@if [ ! -d dist ]; then echo "Error: dist/ directory not found. Run 'make build' first."; exit 1; fi
	@echo "Packages in dist/:"
	@ls -lh dist/
	@echo "Checking package integrity..."
	@twine check dist/*
	@echo "✅ Distribution packages verified"
