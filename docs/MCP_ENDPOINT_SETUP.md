# MCP Ticketer - Live MCP Endpoint Setup Guide

This document describes how to configure mcp-ticketer as a live MCP endpoint for local development and testing (dogfooding).

## Quick Start

The mcp-ticketer project is already configured to use itself as an MCP endpoint. Just ensure:

1. **Claude Code/Desktop is running** with MCP support
2. **Linear API credentials** are configured
3. **MCP server is enabled** in Claude settings

## Configuration Files

### 1. Claude Desktop MCP Configuration

**Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "/opt/homebrew/opt/python@3.13/bin/mcp-ticketer",
      "args": ["mcp"],
      "env": {
        "MCP_TICKETER_ADAPTER": "github",
        "GITHUB_TOKEN": "your_token_here"
      }
    }
  }
}
```

**Note**: This example shows GitHub adapter. For Linear (recommended for this project), configure credentials via mcp-ticketer config.

### 2. Project-Local MCP Configuration

**Location**: `.mcp/config.json` (in project root)

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/Users/masa/Projects/mcp-ticketer/.venv/bin/mcp-ticketer",
      "args": ["serve"],
      "cwd": "/Users/masa/Projects/mcp-ticketer",
      "env": {
        "PYTHONPATH": "/Users/masa/Projects/mcp-ticketer/src"
      }
    }
  }
}
```

**Benefits**:
- Uses local development version
- Changes take effect immediately
- Ideal for testing new features

### 3. Adapter Configuration

**Location**: `.mcp-ticketer/config.json` (in project root)

```json
{
  "default_adapter": "linear",
  "default_epic": "eac28953c267",
  "adapters": {
    "linear": {
      "adapter": "linear",
      "enabled": true,
      "team_key": "1M"
    }
  }
}
```

**Key Settings**:
- `default_adapter`: Primary platform (linear, github, jira)
- `default_epic`: Default project ID for operations
- `team_key`: Linear team identifier

## Linear Adapter Setup

### Option 1: Using macOS Keychain (Recommended)

```bash
# Store Linear API key securely
security add-generic-password \
  -a "$USER" \
  -s "mcp-ticketer-linear-api-key" \
  -w "lin_api_your_key_here"
```

### Option 2: Environment Variable

```bash
# Add to ~/.zshrc or ~/.bashrc
export LINEAR_API_KEY="lin_api_your_key_here"
export LINEAR_TEAM_KEY="1M"
```

### Option 3: Claude Desktop Config

Add to the `env` section of Claude Desktop config:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "env": {
        "LINEAR_API_KEY": "lin_api_your_key_here",
        "LINEAR_TEAM_KEY": "1M"
      }
    }
  }
}
```

## Getting Your Linear API Key

1. Go to [Linear Settings → API](https://linear.app/settings/api)
2. Click "Create new personal API key"
3. Give it a name (e.g., "mcp-ticketer development")
4. Select scopes: `read`, `write` (full access recommended)
5. Copy the generated key (starts with `lin_api_`)

## Testing the Setup

### 1. Verify Installation

```bash
# Check version
mcp-ticketer --version
# Should output: mcp-ticketer version 2.2.2

# Check config
mcp-ticketer config get
# Should show Linear adapter configured
```

### 2. Test Adapter Connection

```bash
# Test Linear adapter
mcp-ticketer config test linear
# Should output: ✅ Adapter healthy
```

### 3. Test MCP Tools (in Claude Code)

```python
# Get configuration
config(action="get")

# Test adapter
config(action="test", adapter_name="linear")

# Get session info
user_session(action="get_session_info")

# Search tickets in mcp-ticketer project
ticket_search(project_id="eac28953c267", limit=5)
```

## Default Project Configuration

**Project**: [mcp-ticketer Linear Project](https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues)

**Project ID**: `eac28953c267`

This project is configured as the default in:
1. `.mcp-ticketer/config.json` (as `default_epic`)
2. `CLAUDE.md` (project instructions)

All tickets should be created here unless explicitly specified otherwise.

## Common Use Cases

### 1. Create a Bug Report

```python
ticket(
    action="create",
    title="Fix: Error handling in ticket_update",
    description="API error when updating ticket description",
    priority="high",
    tags=["bug", "api-error"]
)
```

### 2. Search Open Issues

```python
ticket_search(
    project_id="eac28953c267",
    state="open",
    priority="high",
    limit=10
)
```

### 3. Get Your Assigned Tickets

```python
user_session(
    action="get_my_tickets",
    state="in_progress",
    limit=20
)
```

### 4. Update Ticket Status

```python
ticket(
    action="update",
    ticket_id="1M-XXX",
    state="done",
    priority="low"
)
```

### 5. Track Work on a Ticket

```python
# Associate current work with a ticket
attach_ticket(action="set", ticket_id="1M-XXX")

# Check current association
attach_ticket(action="status")
```

## Development Workflow (Dogfooding)

When developing mcp-ticketer, use the MCP tools to:

### 1. Issue Tracking
- Create tickets for bugs you encounter
- Track feature development progress
- Document technical debt

### 2. Testing New Features
- Test new MCP tools on real project data
- Verify adapter implementations work correctly
- Catch edge cases with live data

### 3. Example: Testing a New Feature

```python
# 1. Create ticket for the feature
ticket(
    action="create",
    title="Add support for ticket dependencies",
    description="Implement blocked_by/blocks relationships",
    priority="medium",
    tags=["feature", "enhancement"]
)
# Returns: {"ticket_id": "1M-XXX"}

# 2. Track work on this ticket
attach_ticket(action="set", ticket_id="1M-XXX")

# 3. Implement the feature...

# 4. Test the new feature
# (your new feature code here)

# 5. Mark complete
ticket(action="update", ticket_id="1M-XXX", state="done")
```

## Troubleshooting

### MCP Tools Not Available

**Check**:
1. Claude Desktop/Code is running
2. MCP server is configured in Claude settings
3. Restart Claude after config changes

**Verify**:
```bash
# Check if mcp-ticketer is in PATH
which mcp-ticketer

# Test direct execution
mcp-ticketer --version
```

### Linear API Errors

**Common Issues**:

1. **Invalid API Key**
   ```
   Error: Authentication failed
   ```
   - Verify key in Linear settings
   - Check key is not expired
   - Ensure key has correct scopes

2. **Team Not Found**
   ```
   Error: Team '1M' not found
   ```
   - Verify team key in Linear
   - Check you have access to team
   - Update config with correct team_key

3. **Project Not Found**
   ```
   Error: Project 'eac28953c267' not found
   ```
   - Verify project exists in Linear
   - Check project ID in URL
   - Ensure you have project access

### Configuration Not Loading

**Reset Configuration**:
```bash
# Backup current config
cp .mcp-ticketer/config.json .mcp-ticketer/config.json.backup

# Reset to defaults
rm .mcp-ticketer/config.json

# Reconfigure
mcp-ticketer config set linear_api_key YOUR_KEY
mcp-ticketer config set linear_team_key 1M
```

## Advanced Configuration

### Multiple Adapters

Configure multiple platforms simultaneously:

```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "adapter": "linear",
      "enabled": true,
      "team_key": "1M"
    },
    "github": {
      "adapter": "github",
      "enabled": true,
      "owner": "your-org",
      "repo": "mcp-ticketer"
    }
  }
}
```

### Custom Project Paths

For development/testing in different locations:

```bash
# Use specific project path
export MCP_TICKETER_PROJECT_PATH="/path/to/other/project"

# Or in Claude Desktop config
{
  "env": {
    "MCP_TICKETER_PROJECT_PATH": "/custom/path"
  }
}
```

### Debug Mode

Enable verbose logging:

```bash
# In Claude Desktop config
{
  "env": {
    "MCP_TICKETER_LOG_LEVEL": "DEBUG"
  }
}
```

Check logs:
```bash
# macOS
tail -f ~/Library/Logs/Claude/mcp-ticketer.log

# Or system log
log stream --predicate 'subsystem == "com.anthropic.claude"'
```

## Security Best Practices

### API Key Storage

**DO**:
- ✅ Use macOS Keychain for local development
- ✅ Use environment variables for CI/CD
- ✅ Rotate keys regularly
- ✅ Use scoped keys with minimal permissions

**DON'T**:
- ❌ Commit API keys to version control
- ❌ Share keys in chat/email
- ❌ Use personal keys in shared configs
- ❌ Grant broader permissions than needed

### Configuration Security

```bash
# Ensure config files have restricted permissions
chmod 600 .mcp-ticketer/config.json
chmod 600 .mcp-ticketer/session.json

# Add to .gitignore
echo ".mcp-ticketer/config.json" >> .gitignore
echo ".mcp-ticketer/session.json" >> .gitignore
```

## References

- [MCP Ticketer Documentation](../README.md)
- [Linear API Documentation](https://developers.linear.app/docs)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [Claude Desktop MCP Guide](https://claude.ai/docs/mcp)

## Support

**Issues**: Create a ticket in the [mcp-ticketer Linear project](https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues)

**Examples**:
```python
# Report a bug
ticket(
    action="create",
    title="Bug: Configuration not loading on startup",
    description="Steps to reproduce:\n1. ...\n2. ...",
    priority="high",
    tags=["bug", "config"]
)
```

---

**Last Updated**: December 5, 2025
**Version**: mcp-ticketer 2.2.2
**Status**: ✅ Verified and operational
