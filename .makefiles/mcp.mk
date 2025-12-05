# mcp.mk - mcp-ticketer-specific targets
# Part of mcp-ticketer modular Makefile architecture

##@ Development

.PHONY: dev
dev: ## Run in development mode (start MCP server)
	@echo "Starting MCP Ticketer server..."
	mcp-ticketer-server

.PHONY: cli
cli: ## Run CLI in interactive mode
	@echo "MCP Ticketer CLI ready. Use 'mcp-ticketer --help' for commands"
	mcp-ticketer

.PHONY: dev-setup
dev-setup: install-dev ## Setup complete development environment
	@echo "Installing additional dev dependencies..."
	$(PIP) install pytest-xdist pytest-watch
	@echo "Development environment ready!"

##@ Adapter Management

.PHONY: init-aitrackdown
init-aitrackdown: ## Initialize AI-Trackdown adapter
	@echo "Initializing AI-Trackdown adapter..."
	mcp-ticketer init --adapter aitrackdown

.PHONY: init-linear
init-linear: ## Initialize Linear adapter (requires LINEAR_API_KEY, LINEAR_TEAM_ID)
	@echo "Initializing Linear adapter..."
	@if [ -z "$$LINEAR_API_KEY" ]; then echo "Error: LINEAR_API_KEY not set"; exit 1; fi
	@if [ -z "$$LINEAR_TEAM_ID" ]; then echo "Error: LINEAR_TEAM_ID not set"; exit 1; fi
	mcp-ticketer init --adapter linear --team-id $$LINEAR_TEAM_ID

.PHONY: init-jira
init-jira: ## Initialize JIRA adapter (requires JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN)
	@echo "Initializing JIRA adapter..."
	@if [ -z "$$JIRA_SERVER" ]; then echo "Error: JIRA_SERVER not set"; exit 1; fi
	@if [ -z "$$JIRA_EMAIL" ]; then echo "Error: JIRA_EMAIL not set"; exit 1; fi
	@if [ -z "$$JIRA_API_TOKEN" ]; then echo "Error: JIRA_API_TOKEN not set"; exit 1; fi
	mcp-ticketer init --adapter jira --jira-server $$JIRA_SERVER --jira-email $$JIRA_EMAIL

.PHONY: init-github
init-github: ## Initialize GitHub adapter (requires GITHUB_TOKEN, GITHUB_REPO)
	@echo "Initializing GitHub adapter..."
	@if [ -z "$$GITHUB_TOKEN" ]; then echo "Error: GITHUB_TOKEN not set"; exit 1; fi
	@if [ -z "$$GITHUB_REPO" ]; then echo "Error: GITHUB_REPO not set"; exit 1; fi
	mcp-ticketer init --adapter github --repo $$GITHUB_REPO

##@ Adapter Testing

.PHONY: test-adapters
test-adapters: ## Run adapter-specific tests
	@echo "Running adapter tests..."
	pytest tests/adapters/ -v

.PHONY: test-linear
test-linear: ## Test Linear adapter
	@echo "Testing Linear adapter..."
	pytest tests/adapters/linear/ -v

.PHONY: test-github
test-github: ## Test GitHub adapter
	@echo "Testing GitHub adapter..."
	pytest tests/adapters/test_github.py -v

.PHONY: test-jira
test-jira: ## Test JIRA adapter
	@echo "Testing JIRA adapter..."
	pytest tests/adapters/test_jira.py -v

.PHONY: test-aitrackdown
test-aitrackdown: ## Test AI-Trackdown adapter
	@echo "Testing AI-Trackdown adapter..."
	pytest tests/adapters/test_aitrackdown.py -v

##@ MCP Server Testing

.PHONY: mcp-server-test
mcp-server-test: ## Test MCP server functionality
	@echo "Testing MCP server..."
	pytest tests/mcp/ -v

.PHONY: test-mcp-tools
test-mcp-tools: ## Test MCP tool definitions
	@echo "Testing MCP tools..."
	pytest tests/mcp/test_tools.py -v

##@ MCP Server Installation

.PHONY: install-mcp-server
install-mcp-server: ## Install mcp-ticketer as MCP server (auto-detect platform)
	@echo "Installing mcp-ticketer as MCP server..."
	mcp-ticketer install-mcp-server

.PHONY: install-mcp-server-global
install-mcp-server-global: ## Install mcp-ticketer as MCP server globally
	@echo "Installing mcp-ticketer globally..."
	mcp-ticketer install-mcp-server --scope global

.PHONY: install-mcp-server-dry-run
install-mcp-server-dry-run: ## Preview MCP server installation without applying
	@echo "Previewing MCP server installation..."
	mcp-ticketer install-mcp-server --dry-run

.PHONY: list-mcp-servers
list-mcp-servers: ## List installed MCP servers on detected platform
	@echo "Listing MCP servers..."
	mcp-ticketer list-mcp-servers

.PHONY: uninstall-mcp-server
uninstall-mcp-server: ## Uninstall mcp-ticketer MCP server
	@echo "Uninstalling mcp-ticketer MCP server..."
	mcp-ticketer uninstall-mcp-server

##@ Quick Operations

.PHONY: create
create: ## Create a new ticket (usage: make create TITLE="..." DESC="..." PRIORITY="high")
	@if [ -z "$(TITLE)" ]; then echo "Error: TITLE required. Usage: make create TITLE='...'"; exit 1; fi
	@mcp-ticketer create "$(TITLE)" $${DESC:+--description "$$DESC"} $${PRIORITY:+--priority "$$PRIORITY"}

.PHONY: list
list: ## List tickets (usage: make list STATE="open" LIMIT=10)
	@mcp-ticketer list $${STATE:+--state "$$STATE"} $${LIMIT:+--limit "$$LIMIT"}

.PHONY: search
search: ## Search tickets (usage: make search QUERY="bug")
	@if [ -z "$(QUERY)" ]; then echo "Error: QUERY required. Usage: make search QUERY='...'"; exit 1; fi
	@mcp-ticketer search "$(QUERY)"
