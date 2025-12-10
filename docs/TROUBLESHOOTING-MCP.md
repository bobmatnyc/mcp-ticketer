# MCP Troubleshooting Guide

Quick guide to resolve common MCP integration issues with mcp-ticketer.

## Quick Diagnostics

Run these commands to identify the issue:

```bash
# 1. Verify mcp-ticketer is installed
which mcp-ticketer
# Expected: /path/to/bin/mcp-ticketer

# 2. Check version
mcp-ticketer --version
# Expected: mcp-ticketer version X.Y.Z

# 3. Test server startup
mcp-ticketer mcp serve
# Press Ctrl+D to stop
# Expected: "Starting MCP SDK server with [adapter] adapter"

# 4. Check configuration
mcp-ticketer config get
# Expected: Shows adapter configuration

# 5. Check MCP status
mcp-ticketer mcp status
# Expected: Shows Claude Code/Desktop configuration status
```

## Common Issues and Solutions

### Issue 1: "mcp-ticketer: command not found"

**Symptom:** Claude Code/Desktop can't find mcp-ticketer command

**Cause:** Binary not in PATH or not installed

**Solution:**

```bash
# Option 1: Install globally with pipx (recommended)
pipx install mcp-ticketer

# Option 2: Install with pip
pip install mcp-ticketer

# Option 3: Install from source
git clone https://github.com/your-org/mcp-ticketer
cd mcp-ticketer
pip install -e .

# Then find the absolute path
which mcp-ticketer
# Use this path in .mcp/config.json
```

Update `.mcp/config.json` with absolute path:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/Users/you/.local/bin/mcp-ticketer",  // Absolute path
      "args": ["serve"],
      "cwd": "/path/to/your/project"
    }
  }
}
```

### Issue 2: "No tools available from mcp-ticketer"

**Symptom:** MCP server starts but no tools show up in Claude Code/Desktop

**Cause:** Usually wrong subcommand or missing `serve` argument

**Solution:**

Check `.mcp/config.json`:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["serve"],  // ✅ Must include "serve"
      "cwd": "/path/to/project"
    }
  }
}
```

**Common mistakes:**
```json
// ❌ Wrong - missing serve
"args": ["mcp"]

// ❌ Wrong - typo
"args": ["server"]

// ✅ Correct
"args": ["serve"]
```

### Issue 3: "Adapter not configured" error

**Symptom:** Server starts but crashes when trying to use tools

**Cause:** Missing `.mcp-ticketer/config.json` in project

**Solution:**

```bash
cd /path/to/your/project

# Initialize configuration
mcp-ticketer init

# Follow the prompts to configure your adapter (Linear, GitHub, Jira, etc.)
```

Or create manually:

```json
// .mcp-ticketer/config.json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "api_key": "lin_api_...",
      "team_key": "ENG"
    }
  }
}
```

### Issue 4: Authentication failures

**Symptom:** "Unauthorized" or "Invalid token" errors

**Cause:** Missing or invalid adapter credentials

**Solution:**

Create `.env.local` in project root:

```bash
# For Linear
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_KEY=ENG

# For GitHub
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=your-org
GITHUB_REPO=your-repo

# For Jira
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=you@example.com
JIRA_API_TOKEN=...
JIRA_PROJECT_KEY=PROJ
```

**Verify credentials:**
```bash
mcp-ticketer config test --adapter linear
```

### Issue 5: Wrong working directory

**Symptom:** Server can't find configuration files

**Cause:** `cwd` in `.mcp/config.json` points to wrong directory

**Solution:**

Update `.mcp/config.json`:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["serve"],
      "cwd": "/absolute/path/to/project"  // ✅ Use absolute path
    }
  }
}
```

**Verify cwd is correct:**
- Must contain `.mcp-ticketer/config.json` or `.env.local`
- Should be the root of your project

### Issue 6: Server starts but immediately crashes

**Symptom:** No error message visible in Claude Code/Desktop

**Cause:** Unhandled exception during initialization

**Solution:**

Test server manually to see error output:
```bash
cd /path/to/project
mcp-ticketer mcp serve 2>&1 | tee mcp-debug.log
# Press Ctrl+D to stop

# Check the log
cat mcp-debug.log
```

Common causes:
- Invalid JSON in `.mcp-ticketer/config.json`
- Missing required adapter credentials
- Network connectivity issues

### Issue 7: Tools work locally but not in Claude Code/Desktop

**Symptom:** `mcp-ticketer mcp serve` works when run manually, but not via Claude Code

**Cause:** Environment variables not passed to MCP server

**Solution:**

Add environment variables to `.mcp/config.json`:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["serve"],
      "cwd": "/path/to/project",
      "env": {
        "LINEAR_API_KEY": "lin_api_...",
        "LINEAR_TEAM_KEY": "ENG",
        "PYTHONPATH": "/path/to/project/src"
      }
    }
  }
}
```

**Better approach:** Use `.env.local` in project (loaded automatically)

## Verification Checklist

Before asking for support, verify:

- [ ] `which mcp-ticketer` returns a valid path
- [ ] `mcp-ticketer --version` shows version number
- [ ] `mcp-ticketer mcp serve` starts without errors
- [ ] `.mcp-ticketer/config.json` exists in project root
- [ ] `.mcp/config.json` has correct `command`, `args`, and `cwd`
- [ ] Adapter credentials are valid (test with `mcp-ticketer config test`)
- [ ] `mcp-ticketer mcp status` shows correct configuration

## Debug Mode

Enable verbose logging:

```bash
# Set environment variable
export MCP_TICKETER_DEBUG=1
mcp-ticketer mcp serve
```

Add to `.mcp/config.json`:
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["serve"],
      "cwd": "/path/to/project",
      "env": {
        "MCP_TICKETER_DEBUG": "1"
      }
    }
  }
}
```

## Getting Help

If issues persist:

1. **Run diagnostics:**
   ```bash
   mcp-ticketer doctor
   ```

2. **Collect information:**
   - mcp-ticketer version: `mcp-ticketer --version`
   - Installation method: pipx, pip, or source
   - Platform: macOS, Linux, Windows
   - Claude Code/Desktop version
   - `.mcp/config.json` (remove sensitive credentials)
   - Error messages from `mcp-debug.log`

3. **Open an issue:**
   - GitHub: https://github.com/your-org/mcp-ticketer/issues
   - Include diagnostic output and logs
   - Describe expected vs. actual behavior

## Quick Reference: Valid Configuration

**Minimal working configuration:**

```json
// .mcp/config.json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/Users/you/.local/bin/mcp-ticketer",
      "args": ["serve"],
      "cwd": "/Users/you/projects/my-project"
    }
  }
}
```

```json
// /Users/you/projects/my-project/.mcp-ticketer/config.json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": {
      "api_key": "lin_api_...",
      "team_key": "ENG"
    }
  }
}
```

**Or using environment variables:**

```bash
# /Users/you/projects/my-project/.env.local
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_KEY=ENG
```

```json
// .mcp/config.json (simplified)
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["serve"],
      "cwd": "/Users/you/projects/my-project"
    }
  }
}
```

## Related Documentation

- [Installation Guide](docs/INSTALLATION.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [MCP Integration](docs/MCP-INTEGRATION.md)
- [API Reference](docs/mcp-api-reference.md)
