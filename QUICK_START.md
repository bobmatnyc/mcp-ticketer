# QUICK_START.md - MCP Ticketer 5-Minute Setup

**Get up and running with MCP Ticketer in 5 minutes or less.**

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.9+** installed (`python --version`)
- **pip** package manager (`pip --version`)
- **git** for version control (optional but recommended)
- **5 minutes** of your time

---

## Step 1: Install (1 minute)

### For End Users (PyPI)

```bash
# Install latest version
pip install mcp-ticketer

# Or install with specific adapters
pip install mcp-ticketer[linear]    # For Linear support
pip install mcp-ticketer[jira]      # For JIRA support
pip install mcp-ticketer[github]    # For GitHub Issues support
pip install mcp-ticketer[all]       # For all adapters
```

### For Developers (Source)

```bash
# Clone repository
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer

# Install in development mode
make install-dev

# Or manually
pip install -e ".[dev,test,docs,all]"
```

**Verify Installation**:
```bash
mcp-ticketer --version
# Output: mcp-ticketer version 0.1.11
```

---

## Step 2: Initialize (1 minute)

Choose ONE adapter to start with:

### Option A: AI-Trackdown (Local Files - No API Keys Required)

**Best for**: Quick testing, local development, no external dependencies

```bash
# Initialize local file-based adapter
mcp-ticketer init --adapter aitrackdown

# Or using Make
make init-aitrackdown
```

**What it does**: Creates `.aitrackdown/` directory for local ticket storage.

### Option B: Linear (Requires Linear Account)

**Best for**: Teams using Linear for project management

```bash
# Set environment variables
export LINEAR_API_KEY="lin_api_your_key_here"
export LINEAR_TEAM_ID="your_team_id"

# Initialize Linear adapter
mcp-ticketer init --adapter linear --team-id $LINEAR_TEAM_ID

# Or using Make
make init-linear
```

**Get API Key**: https://linear.app/settings/api

### Option C: JIRA (Requires JIRA Account)

**Best for**: Teams using JIRA/Atlassian products

```bash
# Set environment variables
export JIRA_SERVER="https://your-domain.atlassian.net"
export JIRA_EMAIL="your-email@example.com"
export JIRA_API_TOKEN="your_jira_api_token"

# Initialize JIRA adapter
mcp-ticketer init --adapter jira \
  --jira-server $JIRA_SERVER \
  --jira-email $JIRA_EMAIL

# Or using Make
make init-jira
```

**Get API Token**: https://id.atlassian.com/manage-profile/security/api-tokens

### Option D: GitHub Issues (Requires GitHub Account)

**Best for**: Projects using GitHub for issue tracking

```bash
# Set environment variables
export GITHUB_TOKEN="ghp_your_token_here"
export GITHUB_REPO="owner/repository"

# Initialize GitHub adapter
mcp-ticketer init --adapter github --repo $GITHUB_REPO

# Or using Make
make init-github
```

**Get Token**: https://github.com/settings/tokens/new (needs `repo` scope)

---

## Step 3: Create Your First Ticket (1 minute)

### Create a Ticket

```bash
# Simple ticket
mcp-ticketer create "Fix login bug"

# Ticket with details
mcp-ticketer create "Implement user search" \
  --description "Add search functionality to user directory" \
  --priority high \
  --assignee john.doe \
  --tags feature,frontend

# Using Make
make create TITLE="Fix login bug" DESC="Users cannot authenticate" PRIORITY="high"
```

**Output**:
```
Created ticket: TICK-123
Title: Fix login bug
State: open
Priority: high
```

### List Tickets

```bash
# List all open tickets
mcp-ticketer list --state open

# List with limit
mcp-ticketer list --state open --limit 20

# Using Make
make list STATE="open" LIMIT=20
```

**Output**:
```
┌──────────┬─────────────────┬────────────┬──────────┐
│ ID       │ Title           │ State      │ Priority │
├──────────┼─────────────────┼────────────┼──────────┤
│ TICK-123 │ Fix login bug   │ open       │ high     │
│ TICK-124 │ Add user search │ in_progress│ medium   │
└──────────┴─────────────────┴────────────┴──────────┘
```

---

## Step 4: Manage Tickets (1 minute)

### View Ticket Details

```bash
# Show ticket with comments
mcp-ticketer show TICK-123 --comments

# Or use read command
mcp-ticketer read TICK-123
```

### Update Ticket

```bash
# Update priority
mcp-ticketer update TICK-123 --priority critical

# Update assignee
mcp-ticketer update TICK-123 --assignee jane.smith

# Update multiple fields
mcp-ticketer update TICK-123 \
  --priority high \
  --assignee john.doe \
  --tags bug,urgent
```

### Transition State

```bash
# Move to in_progress
mcp-ticketer transition TICK-123 in_progress

# Move to done
mcp-ticketer transition TICK-123 done

# Close ticket
mcp-ticketer transition TICK-123 closed
```

### Add Comments

```bash
# Add comment
mcp-ticketer comment TICK-123 "Fixed the authentication issue"

# View comments
mcp-ticketer show TICK-123 --comments
```

### Search Tickets

```bash
# Search by text
mcp-ticketer search "login bug"

# Search with filters
mcp-ticketer search "authentication" --state open --priority high

# Using Make
make search QUERY="login bug"
```

---

## Step 5: Choose Your AI Client (1 minute)

### Which AI Client Should You Use?

MCP Ticketer supports **4 major AI clients**. Choose based on your needs:

| Client | Best For | Config Type | Setup Time |
|--------|----------|-------------|------------|
| **Claude Code** | Multi-project workflows | Project-level | < 1 min |
| **Gemini CLI** | Security-conscious teams | Project-level | < 1 min |
| **Codex CLI** | Single-project users | Global-only | < 2 min |
| **Auggie** | Simplicity seekers | Global-only | < 1 min |

**Decision Tree:**
```
Do you work on multiple projects?
├─ Yes → Use Claude Code or Gemini CLI (project-level)
└─ No  → Use Codex CLI or Auggie (global)

Do you need advanced security features?
├─ Yes → Use Gemini CLI (trust settings)
└─ No  → Use Claude Code (simpler setup)

Do you prefer TOML config?
├─ Yes → Use Codex CLI
└─ No  → Use any other client (JSON)
```

---

### Option A: Claude Code (Recommended)

**Best for**: Project-specific workflows, stable integration

```bash
# Configure MCP integration (THE ONLY WAY)
mcp-ticketer mcp claude

# Configuration created at: .claude/mcp.json
# Or for global: ~/Library/Application Support/Claude/claude_desktop_config.json
```

**Use in Claude Code:**
- "Create a ticket for fixing the login bug"
- "List all open tickets with high priority"
- "Search for tickets related to authentication"
- "Update ticket TICK-123 to in_progress state"

---

### Option B: Gemini CLI

**Best for**: Security features, Google AI users

```bash
# Configure for project-level (recommended)
mcp-ticketer mcp gemini --scope project

# Or configure globally
mcp-ticketer mcp gemini --scope user

# Configuration created at:
# Project: .gemini/settings.json
# Global: ~/.gemini/settings.json
```

**Use in Gemini CLI:**
```bash
# Run gemini in project directory
gemini

# Tools automatically available
# Try: "Show me all open tickets"
```

---

### Option C: Codex CLI

**Best for**: Single-project users, TOML preferences

```bash
# Configure Codex (global-only)
mcp-ticketer mcp codex

# Configuration created at: ~/.codex/config.toml

# ⚠️ IMPORTANT: Restart Codex CLI (required)
```

**Use in Codex CLI:**
```bash
# Run codex from any directory
codex

# Tools globally available
# Try: "Search tickets for login issues"
```

---

### Option D: Auggie

**Best for**: Simple setup, lightweight usage

```bash
# Configure Auggie (global-only)
mcp-ticketer mcp auggie

# Configuration created at: ~/.augment/settings.json

# May need to restart Auggie
```

**Use in Auggie:**
```bash
# Open Auggie
auggie

# Tools globally available
# Try: "Create a high-priority ticket"
```

---

### Manual MCP Server Setup (Advanced)

If you prefer manual configuration or troubleshooting:

```bash
# Start server manually (listens on stdio)
mcp-ticketer serve

# Test server
# Press Ctrl+C to stop
```

**See [AI Client Integration Guide](docs/AI_CLIENT_INTEGRATION.md) for detailed configuration.**

---

## Common Commands Quick Reference

```bash
# Setup
make install-dev              # Install for development
make init-aitrackdown         # Initialize local adapter

# Ticket Operations
make create TITLE="..."       # Create ticket
make list STATE="open"        # List tickets
make search QUERY="..."       # Search tickets

# Development
make test                     # Run all tests
make format                   # Format code
make lint-fix                 # Fix linting issues
make quality                  # Run all quality checks

# Building
make build                    # Build package
make docs                     # Build documentation
make docs-serve               # Serve docs locally

# Help
make help                     # Show all Make targets
mcp-ticketer --help           # Show CLI help
```

---

## Next Steps

### For End Users

1. **Read the User Guide**: `docs/USER_GUIDE.md`
2. **Configure your adapter**: See adapter-specific guides
   - JIRA: `JIRA_SETUP.md`
   - Linear: `LINEAR_SETUP.md`
   - GitHub: `docs/adapters/github.md`
3. **Integrate with Claude**: See `CLAUDE_DESKTOP_SETUP.md`

### For Developers

1. **Read CLAUDE.md**: Complete AI agent guide
2. **Explore CODE_STRUCTURE.md**: Architecture overview
3. **Read DEVELOPER_GUIDE.md**: Comprehensive developer documentation
4. **Review CONTRIBUTING.md**: Contribution guidelines
5. **Run tests**: `make test-coverage`
6. **Build docs**: `make docs-serve`

### For Contributors

1. **Fork the repository**: https://github.com/mcp-ticketer/mcp-ticketer
2. **Create a feature branch**: `git checkout -b feature/your-feature`
3. **Make changes**: Follow code quality standards
4. **Run quality checks**: `make quality`
5. **Submit PR**: `gh pr create --title "Your Feature" --body "Description"`

---

## Troubleshooting

### Issue: "Command not found: mcp-ticketer"

**Solution**:
```bash
# Ensure package is installed
pip install mcp-ticketer

# Check if in PATH
which mcp-ticketer

# Reinstall if needed
pip uninstall mcp-ticketer
pip install mcp-ticketer
```

### Issue: "Adapter not configured"

**Solution**:
```bash
# Check configuration
mcp-ticketer config-show

# Reinitialize adapter
mcp-ticketer init --adapter aitrackdown
```

### Issue: "Authentication failed"

**Solution**:
```bash
# Verify API keys
echo $LINEAR_API_KEY
echo $GITHUB_TOKEN
echo $JIRA_API_TOKEN

# Reinitialize with correct credentials
mcp-ticketer init --adapter linear --team-id YOUR_TEAM_ID
```

### Issue: "Import errors after installation"

**Solution**:
```bash
# Clean and reinstall
make clean
make install-dev

# Or manually
pip uninstall mcp-ticketer
pip install -e ".[all,dev]"
```

### Issue: "Tests failing"

**Solution**:
```bash
# Run specific test
pytest tests/unit/test_models.py -v

# Check test environment
make check-env

# Clean and rerun
make clean
make test
```

### Get More Help

- **Documentation**: See `docs/` folder
- **Issues**: https://github.com/mcp-ticketer/mcp-ticketer/issues
- **Discussions**: https://github.com/mcp-ticketer/mcp-ticketer/discussions
- **Discord**: [Join our community](https://discord.gg/mcp-ticketer)
- **Email**: support@mcp-ticketer.io

---

## Configuration Files

### Config Location

- **macOS/Linux**: `~/.mcp-ticketer/config.json`
- **Windows**: `%USERPROFILE%\.mcp-ticketer\config.json`

### Example Config

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "your_team_id",
    "api_key": "your_api_key"
  },
  "cache": {
    "enabled": true,
    "ttl": 300
  }
}
```

### Environment Variables

```bash
# Adapter Selection
export MCP_TICKETER_ADAPTER=linear

# Linear
export LINEAR_API_KEY=lin_api_xxx
export LINEAR_TEAM_ID=team_xxx

# JIRA
export JIRA_SERVER=https://company.atlassian.net
export JIRA_EMAIL=user@example.com
export JIRA_API_TOKEN=your_token

# GitHub
export GITHUB_TOKEN=ghp_xxx
export GITHUB_REPO=owner/repo

# Debug
export MCP_TICKETER_DEBUG=1
export MCP_TICKETER_LOG_LEVEL=DEBUG
```

---

## Success Checklist

- [ ] Python 3.9+ installed
- [ ] mcp-ticketer installed (`pip install mcp-ticketer`)
- [ ] Adapter initialized (aitrackdown, linear, jira, or github)
- [ ] First ticket created successfully
- [ ] Tickets can be listed and searched
- [ ] AI client configured (Claude Code, Gemini CLI, Codex CLI, or Auggie) - optional
- [ ] MCP integration tested (optional)
- [ ] Configuration saved in `.mcp-ticketer/config.json`

**Congratulations! You're now ready to use MCP Ticketer.**

For advanced usage, see:
- **docs/AI_CLIENT_INTEGRATION.md** - Comprehensive AI client integration guide
- **CLAUDE.md** - Comprehensive AI agent instructions
- **docs/USER_GUIDE.md** - Complete user guide
- **docs/DEVELOPER_GUIDE.md** - Developer documentation
- **CODE_STRUCTURE.md** - Architecture overview

---

**Quick Start Complete! Time to build something awesome. 🚀**
