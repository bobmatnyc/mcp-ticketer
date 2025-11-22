# docs.mk - Documentation build and management
# Part of mcp-ticketer modular Makefile architecture

##@ Documentation

.PHONY: docs
docs: ## Build documentation
	@echo "Building documentation..."
	cd $(DOCS_DIR) && make html
	@echo "Documentation built! Open docs/_build/html/index.html"

.PHONY: docs-serve
docs-serve: docs ## Build and serve documentation locally
	@echo "Serving documentation at http://localhost:8000"
	@echo "Press Ctrl+C to stop server"
	cd $(DOCS_DIR)/_build/html && $(PYTHON) -m http.server 8000

.PHONY: docs-open
docs-open: docs ## Build and open documentation in browser
	@echo "Opening documentation in browser..."
	$(OPEN_CMD) $(DOCS_DIR)/_build/html/index.html

.PHONY: docs-clean
docs-clean: ## Clean documentation build
	@echo "Cleaning documentation..."
	cd $(DOCS_DIR) && make clean

.PHONY: docs-rebuild
docs-rebuild: docs-clean docs ## Clean and rebuild documentation
	@echo "Documentation rebuilt!"

.PHONY: docs-check-links
docs-check-links: ## Check for broken links in documentation
	@echo "Checking documentation links..."
	cd $(DOCS_DIR) && make linkcheck
