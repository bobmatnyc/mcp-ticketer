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
# Install latest version (recommended)
pip install mcp-ticketer

# Or install with specific adapters upfront (optional)
pip install mcp-ticketer[linear]    # For Linear support
pip install mcp-ticketer[jira]      # For JIRA support
pip install mcp-ticketer[github]    # For GitHub Issues support
pip install mcp-ticketer[all]       # For all adapters
```

**New in v0.15.0**: You don't need to install adapter-specific dependencies manually anymore! The `setup` command (Step 2) will automatically detect and offer to install missing adapter dependencies for you.

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

### Automatic Dependency Installation (v0.15.0+)

**New!** When you initialize an adapter, mcp-ticketer will automatically:
1. ✅ Detect if adapter-specific dependencies are missing
2. ✅ Prompt you to install them automatically
3. ✅ Install dependencies if you agree (or skip and show manual install command)
4. ✅ Validate the adapter configuration

**Example:**
```bash
$ mcp-ticketer setup

Initializing linear adapter...

⚠  Linear adapter requires additional dependencies
Required package: gql[httpx]

Install dependencies now? [Y/n]: y

Installing linear dependencies...
✓ Successfully installed linear dependencies
✓ Adapter configuration complete
```

### Option A: AI-Trackdown (Local Files - No API Keys Required)

**Best for**: Quick testing, local development, no external dependencies

```bash
# Initialize local file-based adapter
mcp-ticketer init --adapter aitrackdown

# Or using Make
make init-aitrackdown
```

**What it does**: Creates `.aitrackdown/` directory for local ticket storage.
**Dependencies**: None required (ready to use immediately!)

### Option B: Linear (Requires Linear Account)

**Best for**: Teams using Linear for project management

```bash
# Set environment variables
export LINEAR_API_KEY="lin_api_your_key_here"

# Option 1: Use team URL (easiest - paste from browser)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active

# Option 2: Use team key
export LINEAR_TEAM_KEY="ENG"
mcp-ticketer init --adapter linear --team-key $LINEAR_TEAM_KEY

# Option 3: Use team ID
export LINEAR_TEAM_ID="your_team_id"
mcp-ticketer init --adapter linear --team-id $LINEAR_TEAM_ID

# Or using Make
make init-linear
```

**Get API Key**: https://linear.app/settings/api

**Find Team Information**:
- **Easiest**: Copy your team's issues URL directly from your browser
- **Alternative**: Go to Linear Settings → Teams → Your Team → "Key" field (e.g., "ENG", "DESIGN")

**Supported URL formats**:
- `https://linear.app/your-org/team/ABC/active` (full issues page)
- `https://linear.app/your-org/team/ABC/` (team page)
- `https://linear.app/your-org/team/ABC` (short form)

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
export GITHUB_REPO_URL="https://github.com/owner/repository"

# Initialize GitHub adapter (preferred - uses repository URL)
mcp-ticketer init --adapter github --github-url $GITHUB_REPO_URL

# Legacy format still works
export GITHUB_REPO="owner/repository"
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

### Work with Attachments (AITrackdown only)

```bash
# Add a file attachment (via Python)
python -c "
import asyncio
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

async def main():
    adapter = AITrackdownAdapter({'base_path': '.aitrackdown'})
    attachment = await adapter.add_attachment(
        ticket_id='task-123',
        file_path='./specs/design.pdf',
        description='Final design document'
    )
    print(f'Attached: {attachment.filename}')

asyncio.run(main())
"

# List ticket attachments (via Python)
python -c "
import asyncio
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

async def main():
    adapter = AITrackdownAdapter({'base_path': '.aitrackdown'})
    attachments = await adapter.get_attachments('task-123')
    for att in attachments:
        print(f'{att.filename}: {att.size_bytes} bytes')

asyncio.run(main())
"

# Delete attachment (via Python)
python -c "
import asyncio
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

async def main():
    adapter = AITrackdownAdapter({'base_path': '.aitrackdown'})
    await adapter.delete_attachment('task-123', 'attachment_id')
    print('Attachment deleted')

asyncio.run(main())
"
```

**Note**: Attachment support is currently available for AITrackdown adapter. See [Attachments Guide](ATTACHMENTS.md) for detailed documentation.

---

## Step 5: Choose Your AI Client (1 minute)

### Which AI Client Should You Use?

MCP Ticketer supports **4 major AI clients**. Choose based on your needs:

| Client | Best For | Config Type | Setup Time |
|--------|----------|-------------|------------|
| **Claude Code** | Multi-project workflows | Project-level | < 1 min |
| **Claude Desktop** | Global AI assistant | Global-only | < 1 min |
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

### Auto-Detection (Easiest Method)

**The fastest way to set up any AI client:**

```bash
# See what AI platforms are detected on your system
mcp-ticketer install --auto-detect

# Interactive selection - choose from detected platforms
mcp-ticketer install

# Install for all detected platforms at once
mcp-ticketer install --all

# Preview what would be installed (safe to run)
mcp-ticketer install --all --dry-run
```

**What happens:**
1. ✅ **Auto-detects** all installed AI platforms on your system
2. ✅ **Shows status** of each platform (installed, configured, config path)
3. ✅ **Prompts for selection** or installs all at once
4. ✅ **Validates** platform is actually installed before configuring
5. ✅ **Configures** automatically with correct paths and settings

**Example output:**
```
Detected AI platforms:

Platform          Status        Scope          Config Path
────────────────────────────────────────────────────────────────────
Claude Code       ✓ Installed   Project-level  .claude/mcp.json
Claude Desktop    ✓ Installed   Global         ~/Library/.../claude_desktop_config.json
Gemini CLI        ✓ Installed   Project-level  .gemini/settings.json

Select platform (1-3, or 'q' to quit):
```

---

### Option A: Claude Code (Recommended)

**Best for**: Project-specific workflows, stable integration

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select "Claude Code" from the list

# Or install directly
mcp-ticketer install claude-code

# Configuration created at: .claude/mcp.json
```

**Use in Claude Code:**
- "Create a ticket for fixing the login bug"
- "List all open tickets with high priority"
- "Search for tickets related to authentication"
- "Update ticket TICK-123 to in_progress state"

---

### Option B: Claude Desktop

**Best for**: Global configuration across all projects

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select "Claude Desktop" from the list

# Or install directly
mcp-ticketer install claude-desktop

# Configuration created at: ~/Library/Application Support/Claude/claude_desktop_config.json
```

**Use in Claude Desktop:**
- Available globally across all conversations
- Same commands as Claude Code
- Restart Claude Desktop after installation

---

### Option C: Gemini CLI

**Best for**: Security features, Google AI users

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select "Gemini CLI" from the list

# Or install directly
mcp-ticketer install gemini

# Configuration created at: .gemini/settings.json
```

**Use in Gemini CLI:**
```bash
# Run gemini in project directory
gemini

# Tools automatically available
# Try: "Show me all open tickets"
```

---

### Option D: Codex CLI

**Best for**: Single-project users, TOML preferences

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select "Codex CLI" from the list

# Or install directly
mcp-ticketer install codex

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

### Option E: Auggie

**Best for**: Simple setup, lightweight usage

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select "Auggie" from the list

# Or install directly
mcp-ticketer install auggie

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
# Start MCP server in current directory (recommended)
mcp-ticketer mcp

# Start MCP server in specific directory
mcp-ticketer mcp --path /path/to/project

# Check MCP server status
mcp-ticketer mcp status
```

**Manual Configuration Pattern:**

All AI clients use the same reliable venv Python + module invocation pattern:

```json
{
  "command": "/path/to/venv/bin/python",
  "args": ["-m", "mcp_ticketer.mcp.server", "/absolute/path/to/project"],
  "env": {
    "MCP_TICKETER_ADAPTER": "aitrackdown",
    "PYTHONPATH": "/absolute/path/to/project"
  }
}
```

**Key Points:**
- **command**: Path to Python in your mcp-ticketer venv (auto-detected by install commands)
- **args**: Module invocation pattern `["-m", "mcp_ticketer.mcp.server", "<project_path>"]`
- **PYTHONPATH**: Set to project root for proper module resolution
- **Benefits**: More reliable than binary paths, works across all installation methods

**Finding your venv Python:**
```bash
# For pipx installations
ls ~/.local/pipx/venvs/mcp-ticketer/bin/python

# For pip installations in venv
ls .venv/bin/python

# For uv installations
ls .venv/bin/python
```

**See [AI Client Integration Guide](docs/AI_CLIENT_INTEGRATION.md) for detailed configuration.**

---

## Step 5.5: Optimize AI Queries with Compact Mode (v0.15.0+)

### Token Usage Optimization

When using MCP Ticketer with AI clients, you can significantly reduce token usage by using **compact mode** for ticket listings.

**Token Savings:**
- **Standard mode**: ~18,500 tokens for 100 tickets
- **Compact mode**: ~5,500 tokens for 100 tickets
- **Reduction**: **70% fewer tokens** = Query 3x more tickets!

### Using Compact Mode

**In your AI conversations (Claude Code, Claude Desktop, etc.):**

```
You: "List all open tickets in compact mode"
AI: *Uses compact=True parameter, returns 70% fewer tokens*

You: "Show me high priority tasks, use compact mode to save tokens"
AI: *Returns essential ticket fields only*

You: "Find all in-progress tickets assigned to me, compact format"
AI: *Efficient listing with minimal token usage*
```

### When to Use Compact Mode

**Use compact mode when you:**
- ✅ Need to see many tickets at once (>10)
- ✅ Want to filter/search across large ticket sets
- ✅ Are building dashboards or overviews
- ✅ Want to maximize your context window
- ✅ Don't need full descriptions and metadata

**Use standard mode when you:**
- ✅ Need complete ticket details
- ✅ Are viewing individual tickets
- ✅ Need descriptions, timestamps, and metadata
- ✅ Are listing < 10 tickets

### Fields Comparison

**Compact Mode (7 essential fields):**
- `id`, `title`, `state`, `priority`, `assignee`, `tags`, `parent_epic`

**Standard Mode (16 fields):**
- All compact fields + `description`, `created_at`, `updated_at`, `metadata`, `ticket_type`, `estimated_hours`, `actual_hours`, `children`, `parent_issue`

### Example AI Prompts

```
# Efficient queries with compact mode
"List all tickets in compact mode"
"Show high priority bugs using compact format"
"Find tickets assigned to john@example.com, compact view"
"Search for 'authentication' tickets, use compact mode to save tokens"

# When you need full details
"Show me the full details of TICK-123"
"List the 5 most recent tickets with descriptions"
```

**Pro Tip**: When working with large projects, always start with compact mode to get an overview, then request full details for specific tickets you want to investigate.

---

## Step 5.6: Configure Ticket Scoping for Multi-Team Projects (v1.1.6+)

### What is Ticket Scoping?

**Ticket scoping** helps you work more efficiently in large, multi-team environments by:
- 🎯 **Automatically filtering queries** to your team's tickets
- 🏃 **Reducing response time** for large organizations
- 💰 **Lowering token usage** by querying only relevant tickets
- ⚠️ **Preventing scope creep** with helpful warnings

**Best for**: Teams using Linear, JIRA, Asana, or GitHub with multiple teams/projects

### Quick Setup

#### Step 1: Set Your Default Team

```bash
# For Linear (find team ID from your team URL)
# URL: https://linear.app/my-org/team/ENG/active
# Team key: "ENG"

# Via MCP (in AI conversation)
"Set my default team to ENG"

# Or directly in configuration
echo '{"default_team": "your-team-id"}' >> ~/.mcp-ticketer/config.json
```

#### Step 2: Set Your Current Sprint/Cycle (Optional)

```bash
# Via MCP (in AI conversation)
"Set my default cycle to Sprint 23"

# Or directly in configuration
echo '{"default_cycle": "sprint-23-id"}' >> ~/.mcp-ticketer/config.json
```

### Platform-Specific Setup Examples

#### Linear Teams

```bash
# Find your team ID
# Method 1: From Linear URL (https://linear.app/my-org/team/ENG/active)
#   - Team key is "ENG"

# Method 2: Via MCP
"Configure ticket scoping for Linear team ENG"

# Example MCP conversation:
You: "Set my default team for Linear"
AI: "What's your team key or ID?"
You: "ENG"
AI: *Uses config_set_default_team to configure*
    "✓ Default team set to 'ENG'"
    "Your ticket queries will now scope to this team automatically"
```

#### JIRA Projects

```bash
# Find your project key (e.g., "PROJ" from URL)
# https://company.atlassian.net/browse/PROJ-123

# Via MCP
"Set my default JIRA project to PROJ"

# Set current sprint
"Set my default cycle to sprint 42"
```

#### GitHub Organizations

```bash
# Use your GitHub organization name
# Via MCP
"Set my default GitHub team to my-organization"
```

### Scope Warnings Help You Optimize

The system warns you about inefficient queries:

#### Large Unscoped Query Warning

```
⚠️  Large unscoped query: limit=100 with no filters.
    Consider using state, priority, or assignee filters.
    Tip: Configure default_team for automatic scoping.
```

**How to fix**:
```
# Before (triggers warning)
You: "List 100 tickets"

# After (no warning) - Option 1: Add filters
You: "List 100 in-progress tickets"

# After (no warning) - Option 2: Set scope
You: "Set my default team to ENG"
You: "List 100 tickets"  # Now scoped to team ENG
```

#### Unscoped Search Warning

```
⚠️  Unscoped search with no query or filters.
    This will search ALL tickets across all projects.
    Tip: Configure default_team for automatic scoping.
```

**How to fix**:
```
# Before (triggers warning)
You: "Search all tickets"

# After (no warning) - Add search query
You: "Search for authentication bug"

# After (no warning) - Set scope first
You: "Set my default team to ENG"
You: "Search all tickets"  # Now scoped to team ENG
```

### Real-World Workflow Examples

#### Starting a New Sprint

```
You: "Set my default cycle to Sprint 24"
AI: ✓ Default cycle set to 'Sprint 24'

You: "List all high priority tickets in compact mode"
AI: *Returns only Sprint 24 high priority tickets*
    *Uses 70% fewer tokens due to scope + compact mode*
```

#### Switching Teams

```
You: "Switch to backend team"
AI: "Setting default team to backend-team-id"
    ✓ Default team set to 'backend-team-id'

You: "Show my assigned tickets"
AI: *Returns only backend team tickets assigned to you*
```

#### Cross-Team Query

```
# Clear scope temporarily for org-wide query
You: "Show me all critical bugs across all teams"
AI: *Detects cross-team intent*
    *Queries without team filter*

You: "Now show me critical bugs for my team"
AI: *Uses default_team scope*
    *Returns only your team's critical bugs*
```

### Configuration via MCP Tools

All scoping configuration can be done through natural conversation:

```
# View current configuration
You: "What's my current ticket scope configuration?"
AI: *Uses config_get()*
    "Current configuration:"
    "- default_team: ENG"
    "- default_cycle: Sprint 24"
    "- default_project: PROJ-123"

# Update team
You: "Change my default team to Frontend"
AI: *Uses config_set_default_team()*
    "✓ Default team set to 'Frontend'"

# Update cycle
You: "Update my cycle to Sprint 25"
AI: *Uses config_set_default_cycle()*
    "✓ Default cycle set to 'Sprint 25'"

# Clear scope
You: "Clear my team scope"
AI: *Sets default_team to None*
    "✓ Team scope cleared"
```

### Best Practices

#### ✅ DO:
- Set `default_team` for multi-team platforms (Linear, JIRA, Asana)
- Update `default_cycle` at the start of each sprint
- Monitor warnings and adjust queries or scope
- Use scope to reduce token usage in AI interactions
- Clear scope when you need cross-team visibility

#### ❌ DON'T:
- Ignore scope warnings (they help you optimize!)
- Leave scope configured when switching projects
- Use scope on single-team platforms (unnecessary)
- Forget to update cycle when sprint changes

### Token & Performance Impact

**Before Scoping** (1000 tickets in organization):
- Query time: 2-5 seconds
- Tokens used: ~185 tokens/ticket × 100 results = 18,500 tokens
- Relevance: Mixed (includes other teams' tickets)

**After Scoping** (50 tickets in your team):
- Query time: 0.5-1 second (5x faster!)
- Tokens used: ~185 tokens/ticket × 50 results = 9,250 tokens (50% less!)
- Relevance: High (only your team's tickets)

**Scoping + Compact Mode**:
- Query time: 0.5-1 second
- Tokens used: ~55 tokens/ticket × 50 results = 2,750 tokens (85% less!)
- Relevance: High

### Migration for Existing Users

**All scoping features are optional and backwards compatible:**

- ✅ Existing configurations work without changes
- ✅ No action required if you don't need scoping
- ✅ Add when ready (incremental adoption)
- ✅ All tests pass (100% backward compatibility)

**When to adopt**:
- Multi-team environment with 100+ tickets
- Sprint-based workflow with cycles
- Want to optimize AI query performance
- Need better query relevance

---

### Removing MCP Configuration

When you need to remove mcp-ticketer from an AI platform:

```bash
# Remove from Claude Code (project-level)
mcp-ticketer remove claude-code

# Remove from Claude Desktop (global)
mcp-ticketer remove claude-desktop

# Remove from Auggie (alias: uninstall)
mcp-ticketer uninstall auggie

# Dry-run to preview removal without making changes
mcp-ticketer remove codex --dry-run
```

**Available removal commands:**
- `mcp-ticketer remove <platform>` - Remove MCP configuration
- `mcp-ticketer uninstall <platform>` - Alias for remove command

**Supported platforms:** claude-code, claude-desktop, auggie, gemini, codex

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
# Run diagnostics to check configuration
mcp-ticketer doctor

# Check configuration details
mcp-ticketer config-show

# Reinitialize adapter
mcp-ticketer init --adapter aitrackdown
```

### Issue: "Authentication failed"

**Solution**:
```bash
# Run diagnostics to test credentials
mcp-ticketer doctor

# Verify API keys
echo $LINEAR_API_KEY
echo $GITHUB_TOKEN
echo $JIRA_API_TOKEN

# Reinitialize with correct credentials (use team URL for Linear - easiest)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active
```

**Note**: The `doctor` command (formerly `diagnose`) provides comprehensive diagnostics including credential validation, network connectivity, and recent errors.

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

# Linear (choose team URL, team key, OR team ID)
export LINEAR_API_KEY=lin_api_xxx
export LINEAR_TEAM_URL=https://linear.app/your-org/team/ENG/active  # Easiest: paste from browser
# OR
export LINEAR_TEAM_KEY=ENG           # Alternative: short team identifier
# OR
export LINEAR_TEAM_ID=team_xxx       # Advanced: UUID-based team ID

# JIRA
export JIRA_SERVER=https://company.atlassian.net
export JIRA_EMAIL=user@example.com
export JIRA_API_TOKEN=your_token

# GitHub (preferred - URL format)
export GITHUB_TOKEN=ghp_xxx
export GITHUB_REPO_URL=https://github.com/owner/repo

# GitHub (legacy format - still supported)
export GITHUB_REPO=owner/repo

# Debug
export MCP_TICKETER_DEBUG=1
export MCP_TICKETER_LOG_LEVEL=DEBUG
```

**Linear Configuration Note**: LINEAR_TEAM_URL is now the easiest option - just paste your team's issues URL from your browser. Alternatively, LINEAR_TEAM_KEY can be found in Linear Settings → Teams → Your Team → "Key" field.

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
