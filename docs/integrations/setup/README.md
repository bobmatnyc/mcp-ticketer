# Platform Setup Guides

Step-by-step setup guides for integrating MCP Ticketer with different platforms.

## 📚 Contents

### Ticket System Platforms

- **[Linear Setup](LINEAR_SETUP.md)** - Configure Linear integration
  - API key generation
  - Team and workspace setup
  - Testing connection
  - Common issues

- **[JIRA Setup](JIRA_SETUP.md)** - Configure JIRA integration
  - API token creation
  - Project configuration
  - Authentication setup
  - Troubleshooting

### AI Client Platforms

- **[Claude Desktop Setup](CLAUDE_DESKTOP_SETUP.md)** - Set up MCP for Claude Desktop
  - MCP server installation
  - Claude Desktop configuration
  - Testing integration
  - Common issues

- **[Codex Integration](CODEX_INTEGRATION.md)** - Integrate with Codex
  - Codex configuration
  - MCP setup
  - Usage examples

## 🚀 Quick Setup

### Choose Your Platform

**For Ticket Systems**:
1. **Linear**: [Linear Setup Guide](LINEAR_SETUP.md)
2. **JIRA**: [JIRA Setup Guide](JIRA_SETUP.md)
3. **GitHub**: Use GitHub API token (see [Configuration](../../user-docs/getting-started/CONFIGURATION.md))
4. **AITrackdown**: No external setup needed (local storage)

**For AI Clients**:
1. **Claude Desktop**: [Claude Desktop Setup](CLAUDE_DESKTOP_SETUP.md)
2. **Codex**: [Codex Integration](CODEX_INTEGRATION.md)

### General Setup Flow

1. **Install MCP Ticketer**:
   ```bash
   pip install mcp-ticketer
   ```

2. **Choose Platform**: Select your ticket system and AI client

3. **Follow Platform Guide**: Complete platform-specific setup

4. **Test Connection**: Verify integration works

See: [Quick Start Guide](../../user-docs/getting-started/QUICK_START.md)

## 📖 Setup by Platform

### Linear
**What you need**:
- Linear workspace
- API key with appropriate permissions
- Team ID (optional)

**Setup time**: ~5 minutes

**Guide**: [Linear Setup](LINEAR_SETUP.md)

### JIRA
**What you need**:
- JIRA instance (Cloud or Server)
- API token
- Project key

**Setup time**: ~10 minutes

**Guide**: [JIRA Setup](JIRA_SETUP.md)

### Claude Desktop
**What you need**:
- Claude Desktop installed
- MCP Ticketer configured
- Ticket system API credentials

**Setup time**: ~10 minutes

**Guide**: [Claude Desktop Setup](CLAUDE_DESKTOP_SETUP.md)

### Codex
**What you need**:
- Codex account
- MCP server running
- Configuration file

**Setup time**: ~10 minutes

**Guide**: [Codex Integration](CODEX_INTEGRATION.md)

## 🔧 Configuration

After completing platform setup, configure MCP Ticketer:

```bash
# Interactive setup
mcp-ticketer setup

# Or use environment variables
export LINEAR_API_KEY="your-api-key"
export LINEAR_TEAM_ID="your-team-id"
```

See: [Configuration Guide](../../user-docs/getting-started/CONFIGURATION.md)

## 📋 Related Documentation

- **[Configuration Guide](../../user-docs/getting-started/CONFIGURATION.md)** - Complete configuration reference
- **[Quick Start](../../user-docs/getting-started/QUICK_START.md)** - Getting started guide
- **[AI Client Integration](../AI_CLIENT_INTEGRATION.md)** - General AI integration
- **[Troubleshooting](../../user-docs/troubleshooting/TROUBLESHOOTING.md)** - Common issues

## 🆘 Getting Help

### Setup Issues
- Check: Platform-specific troubleshooting in each guide
- Review: [Troubleshooting Guide](../../user-docs/troubleshooting/TROUBLESHOOTING.md)
- Search: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- Ask: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)

### Platform-Specific Help
- **Linear**: [Linear API Documentation](https://developers.linear.app/)
- **JIRA**: [JIRA API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- **GitHub**: [GitHub API Documentation](https://docs.github.com/en/rest)

---

[← Back to Integration Guides](../README.md)
