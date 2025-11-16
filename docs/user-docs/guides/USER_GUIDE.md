# MCP Ticketer User Guide

Complete guide to using MCP Ticketer for unified ticket management across different systems.

## Table of Contents

- [Installation and Setup](#installation-and-setup)
- [CLI Command Reference](#cli-command-reference)
- [Configuration Management](#configuration-management)
- [Adapter-Specific Setup](#adapter-specific-setup)
- [Common Workflows](#common-workflows)
- [Troubleshooting](#troubleshooting)
- [Frequently Asked Questions](#frequently-asked-questions)

## Installation and Setup

### System Requirements

- **Python 3.13+** (Required)
- Virtual environment (Highly recommended)
- Internet connection for external adapters (Linear, JIRA, GitHub)

### Installation Methods

#### Option 1: Install from PyPI (Recommended)

```bash
pip install mcp-ticketer
```

#### Option 2: Install from Source

```bash
git clone https://github.com/mcp-ticketer/mcp-ticketer.git
cd mcp-ticketer
python -m venv venv
source .venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

#### Option 3: Quick Install Script

```bash
curl -sSL https://raw.githubusercontent.com/mcp-ticketer/mcp-ticketer/main/install.sh | bash
```

### Verify Installation

```bash
mcp-ticket --version
mcp-ticket --help
```

## CLI Command Reference

### Global Options

All commands support these global options:

- `--help`: Show help message
- `--verbose`, `-v`: Enable verbose output
- `--quiet`, `-q`: Suppress non-error output
- `--config`: Specify custom config file path

### Initialization Commands

#### `init` - Initialize Configuration

Set up MCP Ticketer with your preferred ticket system.

```bash
mcp-ticket init [OPTIONS]
```

**Options:**
- `--adapter`, `-a`: Adapter type (`aitrackdown`, `linear`, `jira`, `github`)
- `--base-path`, `-p`: Base path for AITrackdown storage
- `--api-key`: API key for Linear or JIRA token
- `--team-id`: Linear team ID (required for Linear)
- `--jira-server`: JIRA server URL
- `--jira-email`: JIRA user email
- `--jira-project`: Default JIRA project key
- `--github-owner`: GitHub repository owner
- `--github-repo`: GitHub repository name
- `--github-token`: GitHub Personal Access Token

**Examples:**

```bash
# Initialize with AITrackdown (local file-based)
mcp-ticket init --adapter aitrackdown --base-path ./tickets

# Initialize with Linear
mcp-ticket init --adapter linear --team-id YOUR_TEAM_ID --api-key lin_api_xxxxx

# Initialize with JIRA
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com \
  --api-key your-api-token \
  --jira-project MYPROJ

# Initialize with GitHub Issues
mcp-ticket init --adapter github \
  --github-owner username \
  --github-repo repository \
  --github-token ghp_xxxxx
```

### Ticket Management Commands

#### `create` - Create New Ticket

Create a new task or issue in your ticket system.

```bash
mcp-ticket create TITLE [OPTIONS]
```

**Arguments:**
- `TITLE`: Ticket title (required)

**Options:**
- `--description`, `-d`: Detailed description
- `--priority`, `-p`: Priority level (`low`, `medium`, `high`, `critical`)
- `--tag`, `-t`: Add tags (can be used multiple times)
- `--assignee`, `-a`: Assign to user

**Examples:**

```bash
# Simple ticket
mcp-ticket create "Fix login bug"

# Detailed ticket with all options
mcp-ticket create "Implement user authentication" \
  --description "Add JWT-based authentication system" \
  --priority high \
  --tag backend \
  --tag security \
  --assignee john.doe
```

#### `list` - List Tickets

Display tickets with optional filtering.

```bash
mcp-ticket list [OPTIONS]
```

**Options:**
- `--state`, `-s`: Filter by state (`open`, `in_progress`, `ready`, etc.)
- `--priority`, `-p`: Filter by priority
- `--limit`, `-l`: Maximum number of tickets (default: 10)
- `--format`: Output format (`table`, `json`, `csv`)

**Examples:**

```bash
# List all open tickets
mcp-ticket list --state open

# List high priority tickets
mcp-ticket list --priority high --limit 20

# Export to JSON
mcp-ticket list --format json > tickets.json
```

#### `show` - Show Ticket Details

Display detailed information about a specific ticket.

```bash
mcp-ticket show TICKET_ID [OPTIONS]
```

**Arguments:**
- `TICKET_ID`: Ticket identifier

**Options:**
- `--comments`, `-c`: Include comments
- `--format`: Output format (`text`, `json`, `markdown`)

**Examples:**

```bash
# Show basic ticket info
mcp-ticket show TICKET-123

# Show ticket with comments
mcp-ticket show TICKET-123 --comments

# Export ticket to markdown
mcp-ticket show TICKET-123 --format markdown > ticket-123.md
```

#### `update` - Update Ticket

Modify ticket properties.

```bash
mcp-ticket update TICKET_ID [OPTIONS]
```

**Arguments:**
- `TICKET_ID`: Ticket identifier

**Options:**
- `--title`: New title
- `--description`, `-d`: New description
- `--priority`, `-p`: New priority
- `--assignee`, `-a`: New assignee

**Examples:**

```bash
# Update title and priority
mcp-ticket update TICKET-123 --title "Fix critical login bug" --priority critical

# Reassign ticket
mcp-ticket update TICKET-123 --assignee jane.doe

# Update description
mcp-ticket update TICKET-123 --description "Updated requirements based on user feedback"
```

#### `transition` - Change Ticket State

Move tickets through the workflow state machine.

```bash
mcp-ticket transition TICKET_ID STATE
```

**Arguments:**
- `TICKET_ID`: Ticket identifier
- `STATE`: Target state (`open`, `in_progress`, `ready`, `tested`, `done`, `closed`, `waiting`, `blocked`)

**Examples:**

```bash
# Start working on a ticket
mcp-ticket transition TICKET-123 in_progress

# Mark as ready for testing
mcp-ticket transition TICKET-123 ready

# Complete the ticket
mcp-ticket transition TICKET-123 done
```

#### `search` - Search Tickets

Advanced ticket search with multiple criteria.

```bash
mcp-ticket search [QUERY] [OPTIONS]
```

**Arguments:**
- `QUERY`: Text search query (optional)

**Options:**
- `--state`, `-s`: Filter by state
- `--priority`, `-p`: Filter by priority
- `--assignee`, `-a`: Filter by assignee
- `--tag`, `-t`: Filter by tag
- `--limit`, `-l`: Maximum results

**Examples:**

```bash
# Search by text
mcp-ticket search "authentication error"

# Complex search with filters
mcp-ticket search "login" --state open --priority high --assignee john.doe

# Find all blocked tickets
mcp-ticket search --state blocked

# Search by tag
mcp-ticket search --tag security --limit 50
```

### Utility Commands

#### `config` - Configuration Management

Manage MCP Ticketer configuration.

```bash
mcp-ticket config COMMAND [OPTIONS]
```

**Subcommands:**
- `show`: Display current configuration
- `test`: Test adapter connection
- `reset`: Reset configuration to defaults

**Examples:**

```bash
# Show current config
mcp-ticket config show

# Test connection
mcp-ticket config test

# Reset configuration
mcp-ticket config reset
```

#### `doctor` - Diagnostic Testing

Run comprehensive diagnostics on your MCP Ticketer setup.

```bash
mcp-ticketer doctor
```

**What it checks:**
- Adapter configuration validity
- Credential authentication
- Network connectivity
- Queue system health
- Recent error logs
- System dependencies

**Examples:**

```bash
# Run full diagnostics
mcp-ticketer doctor

# Alternative command (alias)
mcp-ticketer diagnose
```

**Note**: The `diagnose` command is still available as an alias for backward compatibility.

## Configuration Management

### Configuration File Location

MCP Ticketer stores configuration in:
- **Linux/macOS**: `~/.mcp-ticketer/config.json`
- **Windows**: `%USERPROFILE%\.mcp-ticketer\config.json`

### Configuration Structure

```json
{
  "adapter": "linear",
  "config": {
    "team_id": "your-team-id",
    "api_key": "lin_api_xxxxxxxxxxxxx"
  },
  "cache": {
    "ttl": 300,
    "max_size": 1000
  },
  "cli": {
    "default_limit": 10,
    "date_format": "YYYY-MM-DD HH:mm:ss"
  }
}
```

### Environment Variables

Environment variables take precedence over configuration file settings:

| Variable | Description | Example |
|----------|-------------|---------|
| `MCP_TICKETER_ADAPTER` | Default adapter | `linear` |
| `MCP_TICKETER_CONFIG_FILE` | Config file path | `/path/to/config.json` |
| `LINEAR_API_KEY` | Linear API key | `lin_api_xxxxxxxxxxxxx` |
| `LINEAR_TEAM_URL` | Linear team URL (easiest) | `https://linear.app/org/team/ENG/active` |
| `LINEAR_TEAM_KEY` | Linear team key | `ENG` |
| `LINEAR_TEAM_ID` | Linear team ID | `team-id` |
| `JIRA_SERVER` | JIRA server URL | `https://company.atlassian.net` |
| `JIRA_EMAIL` | JIRA user email | `user@company.com` |
| `JIRA_API_TOKEN` | JIRA API token | `your-api-token` |
| `JIRA_PROJECT_KEY` | Default JIRA project | `PROJ` |
| `GITHUB_OWNER` | GitHub repository owner | `username` |
| `GITHUB_REPO` | GitHub repository name | `repository` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_xxxxxxxxxxxxx` |

## Adapter-Specific Setup

### AITrackdown (Local File-Based)

Perfect for personal projects and offline work.

**Setup:**
```bash
mcp-ticket init --adapter aitrackdown --base-path ./my-tickets
```

**Features:**
- ✅ Offline operation
- ✅ Version control friendly
- ✅ No external dependencies
- ✅ Fast performance

**Configuration:**
```json
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".aitrackdown"
  }
}
```

### Linear

Modern project management for software teams.

**Setup:**
1. Get your Linear API key from [Linear Settings](https://linear.app/settings/api)
2. Get your team URL, key, or ID (see options below)
3. Initialize:

```bash
# Option 1: Using team URL (easiest - paste from browser)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active

# Option 2: Using team key
mcp-ticketer init --adapter linear --team-key ENG --api-key YOUR_API_KEY

# Option 3: Using team ID (advanced)
mcp-ticketer init --adapter linear --team-id YOUR_TEAM_ID --api-key YOUR_API_KEY
```

**Finding team information:**
- **Easiest**: Copy your Linear team's issues URL directly from your browser
- **Alternative**: Go to Linear Settings → Teams → Your Team → "Key" field

**Features:**
- ✅ Real-time sync
- ✅ Rich metadata support
- ✅ Team collaboration
- ✅ Custom fields

**Configuration:**
```json
{
  "adapter": "linear",
  "config": {
    "team_id": "your-team-id",
    "api_key": "lin_api_xxxxxxxxxxxxx"
  }
}
```

### JIRA

Enterprise project management and issue tracking.

**Setup:**
1. Generate API token at [Atlassian Account Settings](https://id.atlassian.com/manage/api-tokens)
2. Initialize:

```bash
mcp-ticket init --adapter jira \
  --jira-server https://company.atlassian.net \
  --jira-email your.email@company.com \
  --api-key your-api-token \
  --jira-project PROJ
```

**Features:**
- ✅ Enterprise features
- ✅ Complex workflows
- ✅ Extensive customization
- ✅ Advanced reporting

**Configuration:**
```json
{
  "adapter": "jira",
  "config": {
    "server": "https://company.atlassian.net",
    "email": "your.email@company.com",
    "api_token": "your-api-token",
    "project_key": "PROJ"
  }
}
```

### GitHub Issues

Native GitHub repository issue tracking.

**Setup:**
1. Create Personal Access Token at [GitHub Settings](https://github.com/settings/tokens/new)
2. Required scopes: `repo` (private repos) or `public_repo` (public repos)
3. Initialize:

```bash
mcp-ticket init --adapter github \
  --github-owner username \
  --github-repo repository \
  --github-token ghp_xxxxxxxxxxxxx
```

**Features:**
- ✅ GitHub integration
- ✅ Pull request linking
- ✅ Labels and milestones
- ✅ Project boards

**Configuration:**
```json
{
  "adapter": "github",
  "config": {
    "owner": "username",
    "repo": "repository-name",
    "token": "ghp_xxxxxxxxxxxxx"
  }
}
```

## Common Workflows

### Daily Ticket Management

```bash
# Check today's tickets
mcp-ticket list --state in_progress --limit 20

# Start working on a ticket
mcp-ticket transition TICKET-123 in_progress

# Update progress
mcp-ticket update TICKET-123 --description "Progress: implemented authentication logic"

# Mark as ready for review
mcp-ticket transition TICKET-123 ready
```

### Sprint Planning

```bash
# Create epic for new feature
mcp-ticket create "User Authentication System" \
  --description "Implement complete authentication system" \
  --priority high

# Create tasks under the epic
mcp-ticket create "Design authentication API" --tag backend --priority high
mcp-ticket create "Implement JWT tokens" --tag backend --priority medium
mcp-ticket create "Create login UI" --tag frontend --priority medium

# Review sprint backlog
mcp-ticket list --state open --priority high
```

### Bug Triage

```bash
# Find all open bugs
mcp-ticket search --tag bug --state open

# Prioritize critical bugs
mcp-ticket list --priority critical --state open

# Assign bug to developer
mcp-ticket update BUG-456 --assignee john.doe --priority high
```

### Release Management

```bash
# Find tickets ready for testing
mcp-ticket list --state ready

# Move tested tickets to done
mcp-ticket transition TICKET-123 tested
mcp-ticket transition TICKET-123 done

# Generate release notes
mcp-ticket search --state done --limit 50 --format markdown > release-notes.md
```

## Troubleshooting

### Common Issues

#### "Configuration not found" Error

**Problem**: MCP Ticketer can't find configuration file.

**Solution**:
```bash
# Initialize configuration
mcp-ticket init --adapter aitrackdown

# Or specify custom config location
export MCP_TICKETER_CONFIG_FILE=/path/to/config.json
```

#### "Authentication failed" Error

**Problem**: Invalid API credentials.

**Solutions**:

For Linear:
```bash
# Run diagnostics
mcp-ticketer doctor

# Check Linear API key
mcp-ticket config test

# Regenerate API key at https://linear.app/settings/api
# Reinitialize with team URL (easiest)
mcp-ticketer init --adapter linear --team-url https://linear.app/your-org/team/ENG/active
```

For JIRA:
```bash
# Verify JIRA credentials
curl -u email@company.com:api-token https://company.atlassian.net/rest/api/3/myself

# Update credentials
mcp-ticket init --adapter jira --jira-server URL --jira-email EMAIL --api-key TOKEN
```

For GitHub:
```bash
# Test GitHub token
curl -H "Authorization: token ghp_xxxxx" https://api.github.com/user

# Update token
mcp-ticket init --adapter github --github-owner OWNER --github-repo REPO --github-token TOKEN
```

#### "State transition not allowed" Error

**Problem**: Invalid state transition attempted.

**Solution**: Check valid state transitions:

```
OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
READY → TESTED, IN_PROGRESS, BLOCKED
TESTED → DONE, IN_PROGRESS
DONE → CLOSED
WAITING → OPEN, IN_PROGRESS, CLOSED
BLOCKED → OPEN, IN_PROGRESS, CLOSED
```

#### "Ticket not found" Error

**Problem**: Ticket ID doesn't exist or access denied.

**Solutions**:
```bash
# List available tickets
mcp-ticket list

# Search for the ticket
mcp-ticket search TICKET_ID

# Check permissions in the ticket system
```

### Performance Issues

#### Slow API responses

**Solutions**:
```bash
# Enable caching (if disabled)
export MCP_TICKETER_CACHE_TTL=300

# Reduce query limits
mcp-ticket list --limit 5

# Use more specific filters
mcp-ticket search "query" --state open --priority high
```

#### Memory usage

**Solutions**:
```bash
# Clear cache
rm -rf ~/.mcp-ticketer/cache

# Reduce cache size
export MCP_TICKETER_CACHE_MAX_SIZE=100
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Enable debug output
mcp-ticket --verbose list

# Enable trace logging
export MCP_TICKETER_LOG_LEVEL=DEBUG
mcp-ticket list
```

### Getting Help

If you encounter issues not covered here:

1. Check the [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
2. Enable debug mode and collect logs
3. Create a new issue with:
   - Command that failed
   - Full error message
   - System information (`python --version`, `pip list | grep mcp`)
   - Configuration (remove sensitive data)

## Frequently Asked Questions

### General Questions

**Q: Can I use multiple adapters simultaneously?**
A: Currently, MCP Ticketer supports one active adapter at a time. You can switch between adapters using `mcp-ticket init` with different configurations.

**Q: How do I migrate tickets between systems?**
A: See the [Migration Guide](MIGRATION_GUIDE.md) for detailed instructions on migrating data between different ticket systems.

**Q: Does MCP Ticketer work offline?**
A: Yes, with the AITrackdown adapter. Other adapters require internet connectivity to communicate with their respective services.

### Configuration Questions

**Q: Where are my tickets stored?**
A: This depends on the adapter:
- **AITrackdown**: Local files in the configured directory
- **Linear/JIRA/GitHub**: In their respective cloud services

**Q: Can I backup my configuration?**
A: Yes, copy the config file:
```bash
cp ~/.mcp-ticketer/config.json ~/config-backup.json
```

**Q: How do I use environment variables for sensitive data?**
A: Set environment variables instead of storing credentials in the config file:
```bash
export LINEAR_API_KEY="your-api-key"
export JIRA_API_TOKEN="your-token"
```

### Feature Questions

**Q: Can I create custom ticket types?**
A: MCP Ticketer uses a simplified model (Epic, Task, Comment). Custom types are stored as metadata and tags.

**Q: How do I handle ticket attachments?**
A: Attachments aren't directly supported in the universal model, but they're preserved in the original system and accessible through metadata.

**Q: Can I automate ticket operations?**
A: Yes! Use MCP Ticketer in scripts:
```bash
#!/bin/bash
# Create daily standup tickets
mcp-ticket create "Daily Standup $(date)" --tag standup --priority low
```

### Integration Questions

**Q: How do I integrate with CI/CD pipelines?**
A: Use MCP Ticketer commands in your pipeline scripts:
```yaml
- name: Create deployment ticket
  run: |
    mcp-ticket create "Deploy version ${{ github.ref }}" \
      --description "Automated deployment" \
      --tag deployment
```

**Q: Can I use this with AI assistants?**
A: Yes! Start the MCP server for AI tool integration:
```bash
mcp-ticket-server
```

**Q: How do I integrate with Slack or Teams?**
A: Integration bots are planned for v0.2.0. Currently, you can create custom scripts using the CLI commands.

### Performance Questions

**Q: How fast is MCP Ticketer?**
A: Performance varies by adapter:
- **AITrackdown**: Very fast (local files)
- **Linear**: Fast (optimized API usage)
- **GitHub**: Moderate (REST API limitations)
- **JIRA**: Varies (depends on server performance)

**Q: How much data can I handle?**
A: Tested with:
- 10,000+ tickets (AITrackdown)
- 5,000+ tickets (Linear)
- 2,000+ tickets (JIRA/GitHub with pagination)

**Q: Can I improve performance?**
A: Yes:
```bash
# Increase cache TTL
export MCP_TICKETER_CACHE_TTL=600

# Use specific filters
mcp-ticket list --state open --limit 10

# Enable compression for API calls
export MCP_TICKETER_COMPRESS=true
```

---

For more information, see:
- [Developer Guide](DEVELOPER_GUIDE.md) - Architecture and customization
- [API Reference](API_REFERENCE.md) - Complete API documentation
- [MCP Integration Guide](MCP_INTEGRATION.md) - AI tool integration
- [Configuration Guide](CONFIGURATION.md) - Advanced configuration options