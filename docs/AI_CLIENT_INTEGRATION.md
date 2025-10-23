# AI Client Integration Guide

**Version**: 0.1.24
**Last Updated**: 2025-10-24

Complete guide to integrating MCP Ticketer with AI clients via the Model Context Protocol (MCP).

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Comparison](#quick-comparison)
3. [Claude Code Integration](#claude-code-integration)
4. [Gemini CLI Integration](#gemini-cli-integration)
5. [Codex CLI Integration](#codex-cli-integration)
6. [Auggie Integration](#auggie-integration)
7. [Feature Comparison Matrix](#feature-comparison-matrix)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Migration Guide](#migration-guide)

---

## Overview

### What is MCP?

The **Model Context Protocol (MCP)** is a standardized protocol that enables AI assistants to interact with external tools and services. MCP Ticketer implements MCP to provide universal ticket management capabilities to AI clients.

### Supported AI Clients

MCP Ticketer supports **4 major AI clients** with varying levels of integration:

| Client | Developer | Project-Level | Config Format | Status |
|--------|-----------|---------------|---------------|--------|
| **Claude Code** | Anthropic | ✅ Yes | JSON | Stable |
| **Gemini CLI** | Google | ✅ Yes | JSON | Stable |
| **Codex CLI** | Third-party | ❌ Global only | TOML | Beta |
| **Auggie** | Augment Code | ❌ Global only | JSON | Emerging |

### Prerequisites

Before integrating with any AI client, ensure you have:

1. **Python 3.9+** installed
2. **mcp-ticketer** installed: `pip install mcp-ticketer`
3. **Adapter configured**: Run `mcp-ticketer init --adapter <adapter>`
4. **AI client** installed and configured

---

## Quick Comparison

### Configuration Scope

```
┌─────────────────────────────────────────────────────────────┐
│                     Configuration Scope                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  PROJECT-LEVEL (Recommended)                                │
│  ✅ Claude Code (.claude/mcp.json)                          │
│  ✅ Gemini CLI (.gemini/settings.json)                      │
│                                                              │
│  GLOBAL-ONLY                                                │
│  ⚠️  Codex CLI (~/.codex/config.toml)                       │
│  ⚠️  Auggie (~/.augment/settings.json)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Quick Setup Commands

```bash
# 1. Install and initialize (REQUIRED for all clients)
pip install mcp-ticketer
mcp-ticketer init --adapter aitrackdown

# 2. Configure your AI client (choose ONE)
mcp-ticketer mcp claude  # Claude Code (recommended)
mcp-ticketer mcp gemini  # Gemini CLI
mcp-ticketer mcp codex   # Codex CLI
mcp-ticketer mcp auggie  # Auggie
```

---

## Claude Code Integration

### Overview

Claude Code (Anthropic) provides **native MCP support** with excellent project-level configuration.

**Strengths:**
- ✅ Project-level and global configuration support
- ✅ JSON configuration format (familiar and readable)
- ✅ Hot reload (no restart required)
- ✅ Native integration from Anthropic
- ✅ Stable and well-documented

**Limitations:**
- ⚠️ Manual .gitignore management for project configs
- ⚠️ Basic security options

---

### Setup Instructions

#### Step 1: Prerequisites

```bash
# Ensure Claude Code is installed
claude --version

# Install mcp-ticketer
pip install mcp-ticketer

# Verify installation
mcp-ticketer --version
```

#### Step 2: Initialize Adapter

```bash
# Initialize with local file-based adapter (no API keys needed)
mcp-ticketer init --adapter aitrackdown

# Or initialize with external service
mcp-ticketer init --adapter linear --team-id YOUR_TEAM_ID
mcp-ticketer init --adapter jira --jira-server https://company.atlassian.net
mcp-ticketer init --adapter github --repo owner/repo
```

#### Step 3: Configure MCP Integration

```bash
# Project-level configuration (recommended)
mcp-ticketer mcp claude

# Global configuration (Claude Desktop)
mcp-ticketer mcp claude --global

# Force overwrite existing configuration
mcp-ticketer mcp claude --force
```

#### Step 4: Verify Configuration

**Project-level config location:**
```
.claude/mcp.json
```

**Global config locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

**Example configuration (.claude/mcp.json):**

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/usr/local/bin/mcp-ticketer",
      "args": ["serve"],
      "cwd": "/Users/username/projects/my-project",
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/username/projects/my-project/.aitrackdown"
      }
    }
  }
}
```

#### Step 5: Use in Claude Code

1. Open Claude Code
2. Start a conversation
3. MCP tools are automatically available
4. Try: "Create a ticket to fix the login bug"

---

### Advanced Configuration

#### Custom Environment Variables

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "your-api-key",
        "LINEAR_TEAM_ID": "your-team-id",
        "MCP_TICKETER_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

#### Multiple Adapters

```json
{
  "mcpServers": {
    "mcp-ticketer-jira": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "jira",
        "JIRA_SERVER": "https://company.atlassian.net"
      }
    },
    "mcp-ticketer-github": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "github",
        "GITHUB_REPO": "owner/repo"
      }
    }
  }
}
```

---

## Gemini CLI Integration

### Overview

Gemini CLI (Google) provides **excellent project-level MCP support** with additional security features.

**Strengths:**
- ✅ Project-level and user-level configuration support
- ✅ JSON configuration format
- ✅ Automatic .gitignore management
- ✅ Security: trust settings for MCP servers
- ✅ 15-second timeout for operations
- ✅ Hot reload (no restart required)

**Limitations:**
- ⚠️ Newer, less documentation available
- ⚠️ Requires Gemini API access

---

### Setup Instructions

#### Step 1: Prerequisites

```bash
# Ensure Gemini CLI is installed
gemini --version

# Install mcp-ticketer
pip install mcp-ticketer
```

#### Step 2: Initialize Adapter

```bash
# Initialize adapter (same as Claude Code)
mcp-ticketer init --adapter aitrackdown
```

#### Step 3: Configure MCP Integration

```bash
# Project-level configuration (recommended)
mcp-ticketer mcp gemini --scope project

# User-level configuration (global)
mcp-ticketer mcp gemini --scope user

# Force overwrite
mcp-ticketer mcp gemini --scope project --force
```

#### Step 4: Verify Configuration

**Project-level config:**
```
.gemini/settings.json
```

**User-level config:**
```
~/.gemini/settings.json
```

**Example configuration (.gemini/settings.json):**

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/usr/local/bin/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "PYTHONPATH": "/Users/username/projects/my-project/src",
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/username/projects/my-project/.aitrackdown"
      },
      "timeout": 15000,
      "trust": false
    }
  }
}
```

#### Step 5: Use in Gemini CLI

1. Navigate to your project directory
2. Run `gemini` command
3. MCP tools automatically available
4. Try: "List all open tickets"

---

### Security Features

#### Trust Settings

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "trust": false  // Default: don't trust automatically
    }
  }
}
```

**Trust levels:**
- `false`: Requires explicit approval for each operation (secure)
- `true`: Automatically trusts all operations (convenient)

#### Timeout Configuration

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "timeout": 15000  // 15 seconds (default)
    }
  }
}
```

---

## Codex CLI Integration

### Overview

Codex CLI provides MCP support but **ONLY supports global configuration**.

**Strengths:**
- ✅ Simple global setup
- ✅ TOML configuration format (if you prefer TOML)
- ✅ Works across all directories once configured

**Limitations:**
- ❌ No project-level configuration support
- ❌ Global configuration affects all projects
- ⚠️ Requires restart after configuration changes
- ⚠️ Different config format (TOML vs JSON)
- ⚠️ Beta status, less stable

---

### Setup Instructions

#### Step 1: Prerequisites

```bash
# Ensure Codex CLI is installed
codex --version

# Install mcp-ticketer
pip install mcp-ticketer
```

#### Step 2: Initialize Adapter

```bash
# Initialize adapter
mcp-ticketer init --adapter aitrackdown
```

#### Step 3: Configure MCP Integration

```bash
# Configure Codex (global-only)
mcp-ticketer mcp codex

# Force overwrite
mcp-ticketer mcp codex --force
```

⚠️ **IMPORTANT:** Codex CLI does NOT support project-level configuration.

#### Step 4: Restart Codex CLI

```bash
# Codex requires restart to pick up configuration changes
# Exit Codex and restart
```

#### Step 5: Verify Configuration

**Global config location:**
```
~/.codex/config.toml
```

**Example configuration (~/.codex/config.toml):**

```toml
[mcp_servers.mcp-ticketer]
command = "/usr/local/bin/mcp-ticketer"
args = ["serve"]

[mcp_servers.mcp-ticketer.env]
PYTHONPATH = "/Users/username/projects/my-project/src"
MCP_TICKETER_ADAPTER = "aitrackdown"
MCP_TICKETER_BASE_PATH = "/Users/username/projects/my-project/.aitrackdown"
```

#### Step 6: Use in Codex CLI

1. Run `codex` from any directory
2. MCP tools globally available
3. Try: "Search tickets for authentication"

---

### Global Configuration Implications

⚠️ **Important considerations:**

1. **Single Configuration**: One configuration applies to all projects
2. **Path Dependencies**: Absolute paths may not work across projects
3. **Restart Required**: Must restart Codex after any config change
4. **Security**: Global access may not be suitable for sensitive projects

**Best for:**
- Single-project workflows
- Non-sensitive projects
- Users who prefer global tool access

---

## Auggie Integration

### Overview

Auggie (Augment Code) provides MCP support with **global configuration only**.

**Strengths:**
- ✅ Simple setup
- ✅ JSON configuration format
- ✅ Lightweight and fast

**Limitations:**
- ❌ No project-level configuration support
- ❌ Global configuration affects all projects
- ⚠️ Emerging tool, limited documentation
- ⚠️ May require restart

---

### Setup Instructions

#### Step 1: Prerequisites

```bash
# Ensure Auggie is installed
auggie --version

# Install mcp-ticketer
pip install mcp-ticketer
```

#### Step 2: Initialize Adapter

```bash
# Initialize adapter
mcp-ticketer init --adapter aitrackdown
```

#### Step 3: Configure MCP Integration

```bash
# Configure Auggie (global-only)
mcp-ticketer mcp auggie

# Force overwrite
mcp-ticketer mcp auggie --force
```

#### Step 4: Restart Auggie

```bash
# Auggie may require restart
# Exit and restart the application
```

#### Step 5: Verify Configuration

**Global config location:**
```
~/.augment/settings.json
```

**Example configuration (~/.augment/settings.json):**

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/usr/local/bin/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/username/.mcp-ticketer/.aitrackdown"
      }
    }
  }
}
```

#### Step 6: Use in Auggie

1. Open Auggie
2. MCP tools globally available
3. Try: "Show me ticket TASK-123"

---

### Global Storage Consideration

Since Auggie only supports global configuration, it's recommended to use:

```bash
# Global storage location for tickets
~/.mcp-ticketer/.aitrackdown/
```

This ensures tickets are accessible across all projects when using Auggie.

---

## Feature Comparison Matrix

### Configuration Support

| Feature | Claude Code | Gemini CLI | Codex CLI | Auggie |
|---------|-------------|------------|-----------|--------|
| **Project-level config** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Global config** | ✅ Yes | ✅ Yes | ✅ Only option | ✅ Only option |
| **Config format** | JSON | JSON | TOML | JSON |
| **Config location** | `.claude/` or global | `.gemini/` or `~/.gemini/` | `~/.codex/` | `~/.augment/` |
| **Hot reload** | ✅ Yes | ✅ Yes | ❌ Requires restart | ⚠️ May require restart |

### Security & Features

| Feature | Claude Code | Gemini CLI | Codex CLI | Auggie |
|---------|-------------|------------|-----------|--------|
| **Trust settings** | ⚠️ Basic | ✅ Advanced | ⚠️ Basic | ⚠️ Basic |
| **Timeout config** | ⚠️ Basic | ✅ Configurable | ⚠️ Basic | ⚠️ Basic |
| **Working directory** | ✅ Supported | ✅ Supported | ⚠️ Global only | ⚠️ Global only |
| **Auto .gitignore** | ❌ Manual | ✅ Automatic | N/A | N/A |
| **Environment vars** | ✅ Full | ✅ Full | ✅ Full | ✅ Full |

### Maturity & Support

| Aspect | Claude Code | Gemini CLI | Codex CLI | Auggie |
|--------|-------------|------------|-----------|--------|
| **Maturity** | ✅ Stable | ✅ Stable | ⚠️ Beta | ⚠️ Emerging |
| **Documentation** | ✅ Excellent | ✅ Good | ⚠️ Limited | ⚠️ Limited |
| **Community** | ✅ Large | ✅ Growing | ⚠️ Small | ⚠️ Small |
| **Official support** | ✅ Anthropic | ✅ Google | ⚠️ Community | ⚠️ Startup |

---

## Best Practices

### Choosing the Right Client

#### Use Claude Code if:
- ✅ You work on multiple projects
- ✅ You need project-specific ticket systems
- ✅ You prefer stable, well-documented tools
- ✅ You want native Anthropic integration

#### Use Gemini CLI if:
- ✅ You work on multiple projects
- ✅ You need security features (trust settings)
- ✅ You prefer Google's AI models
- ✅ You want automatic .gitignore management

#### Use Codex CLI if:
- ⚠️ You primarily work on one project
- ⚠️ You prefer TOML configuration
- ⚠️ You're comfortable with global configuration
- ⚠️ You don't mind restarting the CLI

#### Use Auggie if:
- ⚠️ You work on a single project
- ⚠️ You want the simplest setup
- ⚠️ You're comfortable with emerging tools
- ⚠️ You prefer lightweight solutions

---

### Security Best Practices

1. **Use Project-Level Configuration** (when available)
   - Isolates credentials per project
   - Reduces risk of credential leakage
   - Easier to manage access

2. **Never Commit Credentials**
   ```bash
   # Always add to .gitignore
   echo ".claude/" >> .gitignore
   echo ".gemini/" >> .gitignore
   echo ".mcp-ticketer/" >> .gitignore
   ```

3. **Use Environment Variables**
   ```json
   {
     "env": {
       "LINEAR_API_KEY": "${LINEAR_API_KEY}",
       "GITHUB_TOKEN": "${GITHUB_TOKEN}"
     }
   }
   ```

4. **Minimize Trust** (Gemini CLI)
   ```json
   {
     "trust": false  // Require approval for operations
   }
   ```

5. **Regular Audits**
   ```bash
   # Review configurations periodically
   cat .claude/mcp.json
   cat .gemini/settings.json
   cat ~/.codex/config.toml
   cat ~/.augment/settings.json
   ```

---

### Performance Optimization

1. **Use Caching**
   ```bash
   # Enable caching in adapter config
   mcp-ticketer init --adapter aitrackdown --cache-ttl 300
   ```

2. **Set Appropriate Timeouts** (Gemini CLI)
   ```json
   {
     "timeout": 15000  // 15 seconds
   }
   ```

3. **Optimize Working Directory**
   ```json
   {
     "cwd": "/absolute/path/to/project"  // Use absolute paths
   }
   ```

4. **Limit Log Verbosity**
   ```json
   {
     "env": {
       "MCP_TICKETER_LOG_LEVEL": "WARNING"  // Reduce logging
     }
   }
   ```

---

## Troubleshooting

### Common Issues

#### 1. "Command not found: mcp-ticketer"

**Symptom:** AI client cannot find the mcp-ticketer binary.

**Solution:**
```bash
# Find the binary path
which mcp-ticketer

# Update config with absolute path
mcp-ticketer mcp claude --force
```

#### 2. "Adapter not configured"

**Symptom:** MCP server starts but adapter is not initialized.

**Solution:**
```bash
# Check configuration
mcp-ticketer config-show

# Reinitialize adapter
mcp-ticketer init --adapter aitrackdown
```

#### 3. "Permission denied"

**Symptom:** MCP server cannot access ticket storage.

**Solution:**
```bash
# Check permissions
ls -la .aitrackdown/

# Fix permissions
chmod -R u+rw .aitrackdown/
```

#### 4. "Configuration not detected" (Gemini CLI)

**Symptom:** Gemini CLI doesn't detect project-level config.

**Solution:**
```bash
# Verify config exists
cat .gemini/settings.json

# Verify .gitignore
cat .gitignore | grep .gemini

# Reconfigure
mcp-ticketer mcp gemini --scope project --force
```

#### 5. "Server not responding" (Codex CLI)

**Symptom:** MCP server doesn't respond after configuration.

**Solution:**
```bash
# Restart Codex CLI (REQUIRED)
# Exit and restart the application

# Verify config
cat ~/.codex/config.toml
```

---

### Debugging

#### Enable Debug Logging

```json
{
  "env": {
    "MCP_TICKETER_DEBUG": "1",
    "MCP_TICKETER_LOG_LEVEL": "DEBUG"
  }
}
```

#### Test MCP Server Manually

```bash
# Start server manually
mcp-ticketer serve

# Check if server starts without errors
# Press Ctrl+C to stop
```

#### Verify Configuration

```bash
# Validate JSON configuration
cat .claude/mcp.json | python -m json.tool

# Validate TOML configuration (Codex)
python -c "import tomli; print(tomli.load(open('~/.codex/config.toml', 'rb')))"
```

---

## Migration Guide

### Migrating Between Clients

#### From Claude Code to Gemini CLI

```bash
# 1. Your adapter config is already compatible
# No changes needed to .mcp-ticketer/config.json

# 2. Configure Gemini CLI
mcp-ticketer mcp gemini --scope project

# 3. Both clients can now use the same adapter
# No data migration required
```

#### From Global to Project-Level (Codex/Auggie → Claude/Gemini)

```bash
# 1. Create project-specific adapter config
cd /path/to/project
mcp-ticketer init --adapter aitrackdown

# 2. Configure new client
mcp-ticketer mcp claude  # or: mcp-ticketer mcp gemini

# 3. Migrate tickets (optional)
# Copy tickets from global storage to project storage
cp -r ~/.mcp-ticketer/.aitrackdown/* .aitrackdown/
```

#### From Project-Level to Global (Claude/Gemini → Codex/Auggie)

```bash
# 1. Copy project config to global
mkdir -p ~/.mcp-ticketer
cp .mcp-ticketer/config.json ~/.mcp-ticketer/

# 2. Configure global client
mcp-ticketer mcp codex  # or: mcp-ticketer mcp auggie

# 3. Update paths in global config
# Edit ~/.codex/config.toml or ~/.augment/settings.json
# Use global paths: ~/.mcp-ticketer/.aitrackdown
```

---

### Configuration Migration

#### JSON to TOML (Claude/Gemini → Codex)

**Input (JSON):**
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown"
      }
    }
  }
}
```

**Output (TOML):**
```toml
[mcp_servers.mcp-ticketer]
command = "/path/to/mcp-ticketer"
args = ["serve"]

[mcp_servers.mcp-ticketer.env]
MCP_TICKETER_ADAPTER = "aitrackdown"
```

**Conversion script:**
```bash
# Use mcp-ticketer's built-in conversion
mcp-ticketer mcp codex --force
```

---

## Additional Resources

### Documentation Links

- **Main Documentation**: [README.md](../README.md)
- **Quick Start Guide**: [QUICK_START.md](../QUICK_START.md)
- **Claude Instructions**: [CLAUDE.md](../CLAUDE.md)
- **Developer Guide**: [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)

### External Resources

- **MCP Protocol**: https://github.com/anthropics/model-context-protocol
- **Claude Code**: https://claude.ai/
- **Gemini CLI**: https://ai.google.dev/
- **Codex CLI**: (Check official documentation)
- **Auggie**: https://augmentcode.com/

### Support

- **Issues**: [GitHub Issues](https://github.com/mcp-ticketer/mcp-ticketer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/mcp-ticketer/mcp-ticketer/discussions)
- **Email**: support@mcp-ticketer.io

---

## Version History

- **0.1.23** (2025-10-23): Added multi-client MCP integration support
  - Added Gemini CLI support with project-level configuration
  - Added Codex CLI support (global-only)
  - Added Auggie support (global-only)
  - Enhanced security features for Gemini CLI
  - Improved configuration commands and documentation

- **0.1.11** (2025-10-22): Initial MCP integration
  - Claude Code/Desktop support
  - Basic MCP server implementation

---

**Last Updated**: 2025-10-23
**Maintained by**: MCP Ticketer Team
