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

### MCP Server Configuration Pattern

**MCP Ticketer uses a reliable venv Python + module invocation pattern:**

```json
{
  "command": "/path/to/venv/bin/python",
  "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"],
  "env": {
    "PYTHONPATH": "/project/path"
  }
}
```

**Why this pattern?**
1. **Reliability**: Direct venv Python invocation avoids binary wrapper issues
2. **Consistency**: Matches proven mcp-vector-search approach
3. **Compatibility**: Works across pipx, pip, and uv installations
4. **Error Clarity**: Python module errors are more informative
5. **Automatic**: `mcp-ticketer install <platform>` detects paths automatically

**How it works:**
- The `install` commands automatically detect your mcp-ticketer venv Python
- Module invocation (`-m mcp_ticketer.mcp.server`) is more reliable than binary paths
- Project path argument enables project-specific configurations
- PYTHONPATH ensures proper module resolution

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

## Platform Auto-Detection

### Overview

MCP Ticketer includes intelligent platform detection that automatically discovers which AI clients are installed on your system. This simplifies setup by eliminating guesswork and ensuring correct configuration.

### Auto-Detection Features

**What it detects:**
- ✅ Installed AI platforms (Claude Code, Claude Desktop, Gemini CLI, Codex CLI, Auggie)
- ✅ Configuration file locations (project-level and global)
- ✅ Platform availability and status
- ✅ Configuration scope (project vs. global)

**Benefits:**
- 🚀 **Faster setup**: No need to remember platform-specific commands
- ✅ **Validation**: Confirms platform is installed before attempting configuration
- 🎯 **Accuracy**: Uses correct paths and settings for your system
- 🔄 **Batch install**: Configure multiple platforms at once

### Auto-Detection Commands

#### Show Detected Platforms

```bash
# Display all detected AI platforms
mcp-ticketer install --auto-detect
```

**Example output:**
```
Detected AI platforms:

Platform          Status        Scope          Config Path
────────────────────────────────────────────────────────────────────
Claude Code       ✓ Installed   Project-level  .claude/mcp.json
Claude Desktop    ✓ Installed   Global         ~/Library/.../claude_desktop_config.json
Gemini CLI        ✓ Installed   Project-level  .gemini/settings.json
Codex CLI         ⚠ Not found   Global         ~/.codex/config.toml
Auggie            ⚠ Not found   Global         ~/.augment/settings.json

3 platform(s) detected and ready for installation.
```

#### Interactive Installation

```bash
# Auto-detect and prompt for platform selection
mcp-ticketer install
```

**Example interaction:**
```
Detected AI platforms:

  1. Claude Code (Project-level)
  2. Claude Desktop (Global)
  3. Gemini CLI (Project-level)

Enter the number of the platform to configure, or 'q' to quit:
Select platform: 1

✓ Installing MCP configuration for Claude Code...
✓ Configuration saved to .claude/mcp.json
```

#### Install All Platforms

```bash
# Install for all detected platforms at once
mcp-ticketer install --all

# Preview what would be installed (safe to run)
mcp-ticketer install --all --dry-run
```

**Example output (dry-run):**
```
DRY RUN - The following platforms would be configured:

  ✓ Claude Code (Project-level)
  ✓ Claude Desktop (Global)
  ✓ Gemini CLI (Project-level)

Would configure 3 platform(s)
```

**Example output (actual install):**
```
Installing for 3 detected platform(s)...

✓ Claude Code configured (.claude/mcp.json)
✓ Claude Desktop configured (~/Library/.../claude_desktop_config.json)
✓ Gemini CLI configured (.gemini/settings.json)

Successfully configured 3 platform(s).
```

### Platform Validation

When installing for a specific platform, auto-detection validates that the platform is actually installed:

```bash
# If platform is not detected
mcp-ticketer install codex
```

**Output if not installed:**
```
⚠ Platform 'codex' not detected on this system.
Run 'mcp-ticketer install --auto-detect' to see detected platforms.

Do you want to proceed with installation anyway? [y/N]:
```

This prevents configuration errors and provides helpful feedback.

### How Auto-Detection Works

**Detection methods:**
1. **Binary checks**: Looks for AI client executables in PATH
2. **Config file checks**: Searches for existing configuration files
3. **Platform-specific detection**:
   - **Claude Code**: Checks for `.claude/` directory or `claude` binary
   - **Claude Desktop**: Checks for config directory in user's Application Support
   - **Gemini CLI**: Checks for `gemini` binary or `.gemini/` directory
   - **Codex CLI**: Checks for `codex` binary or `~/.codex/` directory
   - **Auggie**: Checks for `auggie` binary or `~/.augment/` directory

**Scope determination:**
- **Project-level**: Platforms that support per-project configuration (Claude Code, Gemini CLI)
- **Global**: Platforms that only support system-wide configuration (Claude Desktop, Codex CLI, Auggie)

### Best Practices

1. **Always check detection first**: Run `--auto-detect` before manual installation
   ```bash
   mcp-ticketer install --auto-detect
   ```

2. **Use interactive mode for single platform**: Let auto-detection guide you
   ```bash
   mcp-ticketer install  # Interactive selection
   ```

3. **Use --all for team setups**: Configure all platforms at once
   ```bash
   mcp-ticketer install --all --dry-run  # Preview first
   mcp-ticketer install --all            # Then install
   ```

4. **Verify platform is installed**: Auto-detection will warn if platform isn't found
   ```bash
   # If you see "not detected", install the platform first
   # For example:
   brew install gemini-cli  # Install the AI client
   mcp-ticketer install gemini  # Then configure it
   ```

### Troubleshooting Auto-Detection

#### Platform Not Detected

**Symptom**: Platform you installed doesn't appear in `--auto-detect` output.

**Solutions**:
```bash
# 1. Verify platform is in PATH
which claude
which gemini
which codex
which auggie

# 2. Check if binary is accessible
claude --version
gemini --version

# 3. Try manual installation (will prompt if not detected)
mcp-ticketer install <platform-name>
```

#### Wrong Configuration Path

**Symptom**: Auto-detection shows incorrect config path.

**Solution**: Use `--path` flag to specify project directory:
```bash
mcp-ticketer install --path /path/to/project
```

#### Multiple Platforms Not Showing

**Symptom**: Only some platforms detected, but you have more installed.

**Solution**: Check installation methods and paths:
```bash
# Check each platform individually
mcp-ticketer install claude-code    # Will show if detected
mcp-ticketer install gemini         # Will show if detected
```

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

# 2. Auto-detect and install (RECOMMENDED)
mcp-ticketer install --auto-detect   # Show all detected AI platforms
mcp-ticketer install                 # Interactive: auto-detect and prompt
mcp-ticketer install --all           # Install for all detected platforms

# 3. Or install for specific platform
mcp-ticketer install claude-code     # Claude Code (project-level, recommended)
mcp-ticketer install claude-desktop  # Claude Desktop (global)
mcp-ticketer install gemini          # Gemini CLI
mcp-ticketer install codex           # Codex CLI
mcp-ticketer install auggie          # Auggie
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
mcp-ticketer init --adapter github --github-url https://github.com/owner/repo
```

#### Step 3: Configure MCP Integration

```bash
# Auto-detect and install (recommended)
mcp-ticketer install  # Select Claude Code from the list

# Or install directly
mcp-ticketer install claude-code    # Project-level (recommended for Claude Code)
mcp-ticketer install claude-desktop # Global configuration (for Claude Desktop)

# Preview changes without applying them
mcp-ticketer install claude-code --dry-run
```

#### Step 4: Verify Configuration

**Claude Code supports two configuration file locations with automatic detection:**

**Option 1: Global MCP Configuration** (Recommended - checked first)
```
~/.config/claude/mcp.json
```

**Option 2: Project-Specific Configuration** (Legacy - fallback)
```
~/.claude.json
```

**Configuration Priority:**
- New location (`~/.config/claude/mcp.json`) is checked first
- Falls back to old location (`~/.claude.json`) if new location doesn't exist
- Both formats are fully supported with backward compatibility
- The `mcp-ticketer install claude-code` command automatically detects and uses the correct location

---

**Example Configuration (Global - `~/.config/claude/mcp.json`):**

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "your_key_here",
        "LINEAR_TEAM_ID": "your_team_id"
      }
    }
  }
}
```

**Structure:**
- **Flat format**: `{"mcpServers": {...}}`
- **No project path**: Global MCP servers available to all projects
- **Environment-based config**: Adapter settings in `env` section

---

**Example Configuration (Project-Specific - `~/.claude.json`):**

```json
{
  "projects": {
    "/absolute/path/to/project": {
      "mcpServers": {
        "mcp-ticketer": {
          "command": "/path/to/venv/bin/python",
          "args": ["-m", "mcp_ticketer.mcp.server", "/absolute/path/to/project"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/project",
            "MCP_TICKETER_ADAPTER": "aitrackdown",
            "MCP_TICKETER_BASE_PATH": "/absolute/path/to/project/.aitrackdown"
          }
        }
      }
    }
  }
}
```

**Structure:**
- **Nested format**: `{"projects": {"<path>": {"mcpServers": {...}}}}`
- **Project path required**: Each project has its own MCP server configuration
- **PYTHONPATH needed**: Project path must be in environment for module resolution

---

**Configuration Pattern Explained:**
- **command**: Path to Python in your mcp-ticketer venv (auto-detected by `install` command)
- **args**: `["-m", "mcp_ticketer.mcp.server", "<project_path>"]` - module invocation pattern
- **PYTHONPATH**: Project path for proper module resolution (project-specific config only)
- **Benefits**: More reliable, better error messages, works across all installation methods

**Migration Path:**
- Existing `~/.claude.json` configurations continue to work
- New installations default to `~/.config/claude/mcp.json`
- No action required - both formats are automatically detected and supported

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
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "your-api-key",
        "LINEAR_TEAM_ID": "your-team-id",
        "MCP_TICKETER_LOG_LEVEL": "DEBUG",
        "PYTHONPATH": "/project/path"
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
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"],
      "env": {
        "MCP_TICKETER_ADAPTER": "jira",
        "JIRA_SERVER": "https://company.atlassian.net",
        "PYTHONPATH": "/project/path"
      }
    },
    "mcp-ticketer-github": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"],
      "env": {
        "MCP_TICKETER_ADAPTER": "github",
        "GITHUB_REPO_URL": "https://github.com/owner/repo",
        "GITHUB_TOKEN": "ghp_xxxxxxxxxxxxx",
        "PYTHONPATH": "/project/path"
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
# Auto-detect and install (recommended)
mcp-ticketer install  # Select Gemini CLI from the list

# Or install directly
mcp-ticketer install gemini

# Preview changes without applying them
mcp-ticketer install gemini --dry-run
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
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server", "/Users/username/projects/my-project"],
      "env": {
        "PYTHONPATH": "/Users/username/projects/my-project",
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/username/projects/my-project/.aitrackdown"
      },
      "timeout": 15000,
      "trust": false
    }
  }
}
```

**Note**: The venv Python path is automatically detected by `mcp-ticketer install gemini`.

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
# Auto-detect and install (recommended)
mcp-ticketer install  # Select Codex CLI from the list

# Or install directly
mcp-ticketer install codex

# Preview changes without applying them
mcp-ticketer install codex --dry-run
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
command = "/path/to/venv/bin/python"
args = ["-m", "mcp_ticketer.mcp.server", "/Users/username/projects/my-project"]

[mcp_servers.mcp-ticketer.env]
PYTHONPATH = "/Users/username/projects/my-project"
MCP_TICKETER_ADAPTER = "aitrackdown"
MCP_TICKETER_BASE_PATH = "/Users/username/projects/my-project/.aitrackdown"
```

**Note**: The venv Python path is automatically detected and configured by `mcp-ticketer install codex`.

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
# Auto-detect and install (recommended)
mcp-ticketer install  # Select Auggie from the list

# Or install directly
mcp-ticketer install auggie

# Preview changes without applying them
mcp-ticketer install auggie --dry-run
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
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "mcp_ticketer.mcp.server"],
      "env": {
        "MCP_TICKETER_ADAPTER": "aitrackdown",
        "MCP_TICKETER_BASE_PATH": "/Users/username/.mcp-ticketer/.aitrackdown"
      }
    }
  }
}
```

**Note**: The venv Python path is automatically detected by `mcp-ticketer install auggie`. Since Auggie uses global configuration, project path arguments are typically omitted.

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

5. **Use Compact Mode for Large Listings** (v0.15.0+)
   ```
   # In AI conversations
   "List all open tickets in compact mode"
   "Show high priority tasks using compact format"

   # Saves 70% tokens (~18,500 → ~5,500 for 100 tickets)
   ```

---

### Token Optimization with Compact Mode (v0.15.0+)

The `ticket_list` MCP tool now supports compact mode for significant token savings when working with AI clients.

#### Token Usage Comparison

| Scenario | Standard Mode | Compact Mode | Savings |
|----------|--------------|--------------|---------|
| 10 tickets | ~1,850 tokens | ~550 tokens | 70% |
| 50 tickets | ~9,250 tokens | ~2,750 tokens | 70% |
| 100 tickets | ~18,500 tokens | ~5,500 tokens | 70% |

#### When to Use Compact Mode

**Use `compact=True` when:**
- ✅ Building ticket dashboards or overviews
- ✅ Filtering/searching across many tickets (>10)
- ✅ Working within token-limited contexts
- ✅ Optimizing AI agent response times
- ✅ Need to query 3x more tickets in same context window

**Use `compact=False` (default) when:**
- ✅ Need full ticket details (descriptions, metadata)
- ✅ Processing individual tickets
- ✅ Listing < 10 tickets
- ✅ Displaying ticket content to users

#### Example AI Prompts

**Efficient queries with compact mode:**
```
"List all open tickets in compact mode"
"Show high priority bugs using compact format"
"Find tickets assigned to john@example.com, compact view"
"Search for 'authentication' issues, use compact mode to save tokens"
```

**When you need full details:**
```
"Show me the full details of TICK-123"
"List the 5 most recent tickets with descriptions"
"Display all critical bugs with complete information"
```

#### Fields Comparison

**Compact Mode (7 fields):**
- `id`, `title`, `state`, `priority`, `assignee`, `tags`, `parent_epic`

**Standard Mode (16 fields):**
- All compact fields plus: `description`, `created_at`, `updated_at`, `metadata`, `ticket_type`, `estimated_hours`, `actual_hours`, `children`, `parent_issue`

#### Best Practices

1. **Start with Compact Mode**
   - Use compact mode for initial ticket discovery
   - Request full details only for specific tickets of interest
   - Maximizes context window efficiency

2. **Combine with Filters**
   - Apply state/priority/assignee filters
   - Use compact mode to review filtered results
   - Reduces token usage while maintaining useful information

3. **Large Project Workflows**
   ```
   # Step 1: Overview with compact mode (saves tokens)
   "List all open tickets in compact mode"

   # Step 2: Focus on specific tickets
   "Show me full details for TICK-123 and TICK-456"

   # Step 3: Bulk operations on filtered set
   "Show all high priority bugs in compact format"
   ```

4. **Context Window Management**
   - Compact mode allows querying 3x more tickets
   - Especially useful for large projects (100+ tickets)
   - Prevents context overflow while maintaining visibility

---

## Troubleshooting

### Using the Doctor Command

Before diving into specific issues, always start with the diagnostic tool:

```bash
# Run comprehensive diagnostics
mcp-ticketer doctor
```

The `doctor` command checks:
- ✅ Adapter configuration validity
- ✅ Credential authentication
- ✅ Network connectivity
- ✅ Queue system health
- ✅ Recent error logs
- ✅ System dependencies

**Note**: The `diagnose` command is still available as an alias for backward compatibility.

### Common Issues

#### 1. "Command not found: mcp-ticketer"

**Symptom:** AI client cannot find the mcp-ticketer binary.

**Solution:**
```bash
# Find the binary path
which mcp-ticketer

# Reinstall configuration
mcp-ticketer remove claude-code
mcp-ticketer install claude-code
```

#### 2. "Adapter not configured"

**Symptom:** MCP server starts but adapter is not initialized.

**Solution:**
```bash
# Run diagnostics first
mcp-ticketer doctor

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

# Reinstall configuration
mcp-ticketer remove gemini
mcp-ticketer install gemini
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
# Start MCP server in current directory
mcp-ticketer mcp

# Start MCP server in specific directory
mcp-ticketer mcp --path /path/to/project

# Check MCP server status
mcp-ticketer mcp status
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

# 2. Install Gemini CLI configuration
mcp-ticketer install gemini

# 3. Both clients can now use the same adapter
# No data migration required
```

#### From Global to Project-Level (Codex/Auggie → Claude/Gemini)

```bash
# 1. Create project-specific adapter config
cd /path/to/project
mcp-ticketer init --adapter aitrackdown

# 2. Install configuration for new client
mcp-ticketer install claude-code  # or: mcp-ticketer install gemini

# 3. Migrate tickets (optional)
# Copy tickets from global storage to project storage
cp -r ~/.mcp-ticketer/.aitrackdown/* .aitrackdown/
```

#### From Project-Level to Global (Claude/Gemini → Codex/Auggie)

```bash
# 1. Copy project config to global
mkdir -p ~/.mcp-ticketer
cp .mcp-ticketer/config.json ~/.mcp-ticketer/

# 2. Install configuration for global client
mcp-ticketer install codex  # or: mcp-ticketer install auggie

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
mcp-ticketer remove codex
mcp-ticketer install codex
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
