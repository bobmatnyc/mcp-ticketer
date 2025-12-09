# release.mk - Release automation with Twine
# Part of mcp-ticketer modular Makefile architecture
#
# PUBLISHING TOOLCHAIN:
# This module uses the modern Python publishing stack:
#   - build (PEP 517): Creates wheel and source distributions
#   - twine (PyPI upload): Securely uploads packages with validation
#
# PREREQUISITES:
# Ensure pyproject.toml includes in [project.optional-dependencies]:
#   dev = [
#       "build>=1.0.0",   # PEP 517 build tool
#       "twine>=5.0.0",   # PyPI publishing tool
#   ]
#
# CREDENTIALS:
# Twine supports multiple authentication methods:
#   1. .env.local file (loaded automatically):
#      TWINE_USERNAME=__token__
#      TWINE_PASSWORD=pypi-AgE...
#   2. ~/.pypirc file (standard)
#   3. Environment variables (CI/CD)
#
# WORKFLOW:
#   make release-patch  - Bump patch version, build, and publish
#   make release-minor  - Bump minor version, build, and publish
#   make release-major  - Bump major version, build, and publish
#
# For manual control:
#   make build         - Build packages only
#   make verify-dist   - Verify with Twine check
#   make publish-test  - Publish to TestPyPI
#   make publish-prod  - Publish to production PyPI

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
publish-test: check-release format lint test test-e2e build verify-dist ## Build and publish to TestPyPI
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
publish-prod: check-release format lint test test-e2e build verify-dist ## Build and publish to PyPI
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
verify-dist: ## Verify distribution packages with Twine
	@echo "Verifying distribution packages..."
	@if [ ! -d dist ]; then echo "Error: dist/ directory not found. Run 'make build' first."; exit 1; fi
	@echo "Packages in dist/:"
	@ls -lh dist/
	@echo "Running Twine validation checks..."
	@echo "  - Checking package metadata"
	@echo "  - Validating long_description rendering"
	@echo "  - Verifying required fields"
	@twine check dist/*
	@echo "✅ Distribution packages verified by Twine"

##@ Publishing Best Practices

.PHONY: publish-help
publish-help: ## Show Twine publishing best practices
	@echo "PyPI Publishing Best Practices with Twine:"
	@echo ""
	@echo "1. ALWAYS run verify-dist before publishing"
	@echo "   This catches common issues like broken long_description"
	@echo ""
	@echo "2. TEST on TestPyPI first"
	@echo "   make publish-test"
	@echo "   pip install --index-url https://test.pypi.org/simple/ mcp-ticketer"
	@echo ""
	@echo "3. Use API tokens (not passwords)"
	@echo "   Username: __token__"
	@echo "   Password: pypi-AgE... (from PyPI account settings)"
	@echo ""
	@echo "4. Store credentials securely"
	@echo "   - .env.local (git-ignored, project-specific)"
	@echo "   - ~/.pypirc (user-level, multiple projects)"
	@echo ""
	@echo "5. Never commit credentials to version control"
	@echo "   Add .env.local to .gitignore"

##@ Submodule Management

.PHONY: release-submodules
release-submodules: ## Check and release submodules with changes
	@echo "🔍 Checking submodules for changes..."
	@$(PYTHON) scripts/release_submodules.py $(TYPE)

##@ Full Release with Submodules

.PHONY: release-patch-full
release-patch-full: ## Release patch version with submodule check
	@echo "🚀 Releasing patch version with submodule check..."
	@$(MAKE) release-submodules TYPE=patch
	@echo "Proceeding with main release..."
	@$(MAKE) release-patch

.PHONY: release-minor-full
release-minor-full: ## Release minor version with submodule check
	@echo "🚀 Releasing minor version with submodule check..."
	@$(MAKE) release-submodules TYPE=minor
	@echo "Proceeding with main release..."
	@$(MAKE) release-minor

.PHONY: release-major-full
release-major-full: ## Release major version with submodule check
	@echo "🚀 Releasing major version with submodule check..."
	@$(MAKE) release-submodules TYPE=major
	@echo "Proceeding with main release..."
	@$(MAKE) release-major

##@ Homebrew Tap Management

.PHONY: update-homebrew-tap
update-homebrew-tap: ## Update Homebrew tap formula (requires VERSION)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION not specified"; \
		echo "Usage: make update-homebrew-tap VERSION=1.2.10"; \
		exit 1; \
	fi
	@echo "Updating Homebrew tap for version $(VERSION)..."
	@bash scripts/update_homebrew_tap.sh $(VERSION)

.PHONY: homebrew-tap-auto
homebrew-tap-auto: ## Auto-update Homebrew tap with current version
	@echo "Auto-updating Homebrew tap with current version..."
	@CURRENT_VERSION=$$($(PYTHON) scripts/manage_version.py get-version) && \
		bash scripts/update_homebrew_tap.sh $$CURRENT_VERSION

.PHONY: homebrew-tap-push
homebrew-tap-push: ## Update Homebrew tap and push automatically
	@echo "Auto-updating Homebrew tap with auto-push..."
	@CURRENT_VERSION=$$($(PYTHON) scripts/manage_version.py get-version) && \
		bash scripts/update_homebrew_tap.sh $$CURRENT_VERSION --push

##@ GitHub Release Management

.PHONY: github-release
github-release: ## Create GitHub release for current version
	@echo "Creating GitHub release..."
	@bash scripts/create_github_release.sh

.PHONY: github-release-version
github-release-version: ## Create GitHub release for specific version (requires VERSION)
	@if [ -z "$(VERSION)" ]; then \
		echo "Error: VERSION not specified"; \
		echo "Usage: make github-release-version VERSION=2.2.11"; \
		exit 1; \
	fi
	@echo "Creating GitHub release for version $(VERSION)..."
	@bash scripts/create_github_release.sh v$(VERSION)

##@ Full Release Automation

.PHONY: release-full-patch
release-full-patch: ## Complete patch release (PyPI + GitHub + Homebrew)
	@echo "🚀 Starting full patch release workflow..."
	@bash scripts/release_full.sh patch

.PHONY: release-full-minor
release-full-minor: ## Complete minor release (PyPI + GitHub + Homebrew)
	@echo "🚀 Starting full minor release workflow..."
	@bash scripts/release_full.sh minor

.PHONY: release-full-major
release-full-major: ## Complete major release (PyPI + GitHub + Homebrew)
	@echo "🚀 Starting full major release workflow..."
	@bash scripts/release_full.sh major

.PHONY: release-pypi
release-pypi: ## Publish to PyPI (alias for publish-prod)
	@$(MAKE) publish-prod

##@ Release Verification

.PHONY: verify-release
verify-release: ## Verify package is installable from PyPI
	@echo "Verifying package installation from PyPI..."
	@CURRENT_VERSION=$$($(PYTHON) scripts/manage_version.py get-version) && \
		echo "Current version: $$CURRENT_VERSION" && \
		echo "Checking if version exists on PyPI..." && \
		$(PYTHON) -m pip index versions mcp-ticketer | grep "$$CURRENT_VERSION" && \
		echo "✅ Version $$CURRENT_VERSION found on PyPI"
