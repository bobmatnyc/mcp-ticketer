# Claude Code Native CLI Support

## Overview

mcp-ticketer now supports Claude Code's native `claude mcp add` command for seamless MCP server installation. The installer automatically detects Claude CLI availability and uses the best method for your system.

## What's New

- **Auto-Detection**: Installer automatically detects Claude CLI availability
- **Native Command**: Uses `claude mcp add` when available for validated configuration
- **Graceful Fallback**: Falls back to JSON configuration if CLI is not available
- **Zero Breaking Changes**: Fully backward compatible with existing installations

## How It Works

### With Claude CLI Installed

When Claude CLI is detected, the installer uses:

```bash
claude mcp add --scope local --transport stdio \
  --env LINEAR_API_KEY=*** \
  --env LINEAR_TEAM_ID=*** \
  --env MCP_TICKETER_ADAPTER=linear \
  mcp-ticketer -- mcp-ticketer mcp --path /path/to/project
```

**Benefits**:
- ✅ Validated by Claude's built-in validation
- ✅ Better error messages
- ✅ Automatic restart prompts
- ✅ Consistent with Claude's native tooling
- ✅ Simpler command structure

### Without Claude CLI

Falls back to legacy JSON configuration:
- Writes directly to `~/.config/claude/mcp.json` or `~/.claude.json`
- Works on all systems
- Same functionality as before
- No manual intervention required

## Installation Methods

### Method 1: Auto-Detected (Recommended)

```bash
mcp-ticketer install --platform claude-code
```

The installer auto-detects your environment and uses the best method:

| CLI Available | Method Used | Config Location |
|---------------|-------------|-----------------|
| Yes | Native `claude mcp add` | Claude CLI managed |
| No | JSON configuration | `~/.config/claude/mcp.json` |

### Method 2: Manual Native CLI

If you have Claude CLI installed, you can configure manually:

```bash
claude mcp add --scope local --transport stdio \
  --env LINEAR_API_KEY=your_key \
  --env LINEAR_TEAM_ID=your_team \
  mcp-ticketer -- mcp-ticketer mcp --path $(pwd)
```

**Benefits**:
- Direct control over configuration
- Claude validates the setup
- Better error messages
- Automatic Claude restart prompts

### Method 3: Manual JSON (Legacy)

For systems without Claude CLI, manual JSON configuration still works:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["mcp", "--path", "/path/to/project"],
      "env": {
        "LINEAR_API_KEY": "your_key",
        "LINEAR_TEAM_ID": "your_team",
        "MCP_TICKETER_ADAPTER": "linear"
      }
    }
  }
}
```

**Note**: This is the fallback method, fully supported but less preferred.

## Environment Variables

The native command automatically passes all configured environment variables based on your adapter:

### Linear Adapter

```bash
--env LINEAR_API_KEY=your_key \
--env LINEAR_TEAM_ID=your_team \
--env MCP_TICKETER_ADAPTER=linear
```

### GitHub Adapter

```bash
--env GITHUB_TOKEN=your_token \
--env GITHUB_OWNER=owner \
--env GITHUB_REPO=repo \
--env MCP_TICKETER_ADAPTER=github
```

### JIRA Adapter

```bash
--env JIRA_API_TOKEN=your_token \
--env JIRA_EMAIL=your_email \
--env JIRA_URL=https://company.atlassian.net \
--env MCP_TICKETER_ADAPTER=jira
```

## Scope Options

### Local (Project-Specific) - Default

```bash
claude mcp add --scope local ...
```

- Configuration stored in project-local Claude settings
- Only available when working in this project
- **Recommended** for project-specific ticket tracking
- This is the default when using `mcp-ticketer install --platform claude-code`

### User (Global)

```bash
claude mcp add --scope user ...
```

- Available across all projects
- Stored in user's global Claude configuration
- Use for cross-project ticket management
- Equivalent to Claude Desktop configuration

## Troubleshooting

### "Claude CLI not found"

**Symptom**: Installer says "Claude CLI not found in PATH"

**Solution**:
- Install Claude CLI from https://docs.claude.ai/cli
- Installer will automatically fall back to JSON configuration
- No action required if fallback method works

### "Permission denied"

**Symptom**: Error running `claude` command

**Solution**:
```bash
# Check if claude is executable
which claude
chmod +x $(which claude)

# Or reinstall Claude CLI
```

### "Command timed out"

**Symptom**: Claude CLI took >30s to respond

**Possible Causes**:
- Network connectivity issues
- Claude CLI needs update
- System resource constraints

**Solution**:
```bash
# Update Claude CLI
brew upgrade claude  # macOS
# or check https://docs.claude.ai/cli for latest version

# Check connectivity
curl -I https://api.anthropic.com
```

### "Already configured" Error

**Symptom**: `claude mcp add` reports server already exists

**Solution**:
```bash
# Option 1: Remove and re-add
claude mcp remove mcp-ticketer
mcp-ticketer install --platform claude-code

# Option 2: Force overwrite
# (Not yet supported in automatic installer, coming soon)
```

### Sensitive Credential Warnings

**Symptom**: Warning about sensitive credentials in console output

**Expected Behavior**: The installer masks sensitive values (API keys, tokens) in console output with `***` for security.

**Example Output**:
```
Command:
  claude mcp add --scope local --transport stdio --env LINEAR_API_KEY=*** ...
```

This is intentional security behavior - actual values are passed to Claude CLI but masked in user-visible output.

## Migration

**No migration needed!** The feature is:
- ✅ Fully backward compatible
- ✅ Auto-detecting
- ✅ Non-breaking

Existing JSON configurations continue to work unchanged. Users on systems without Claude CLI automatically use the fallback method.

## Configuration Comparison

### Native CLI Configuration Result

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "mcp-ticketer",
      "args": ["mcp", "--path", "/path/to/project"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "xyz",
        "LINEAR_TEAM_ID": "abc"
      }
    }
  }
}
```

### Legacy JSON Configuration Result

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "/path/to/venv/bin/mcp-ticketer",
      "args": ["mcp", "--path", "/path/to/project"],
      "env": {
        "MCP_TICKETER_ADAPTER": "linear",
        "LINEAR_API_KEY": "xyz",
        "LINEAR_TEAM_ID": "abc",
        "PYTHONPATH": "/path/to/project"
      }
    }
  }
}
```

**Key Differences**:
1. Native uses `mcp-ticketer` (assumes it's in PATH)
2. Legacy uses full path to venv binary
3. Native managed by Claude CLI (validated)
4. Legacy managed by mcp-ticketer (no validation)

Both configurations are functionally equivalent and work identically.

## FAQ

**Q: Do I need Claude CLI?**
A: No, it's optional. The installer automatically falls back to JSON configuration if Claude CLI is unavailable. However, Claude CLI is recommended for better validation and error handling.

**Q: Will my existing configuration break?**
A: No. Existing JSON configurations continue to work unchanged. This feature only affects new installations.

**Q: Can I force JSON configuration even if CLI is available?**
A: Currently, the installer automatically chooses the best method. To use JSON configuration manually, edit `~/.config/claude/mcp.json` directly.

**Q: Which method is better?**
A: Native CLI is recommended when available because:
- Claude validates the configuration
- Better error messages
- Automatic restart prompts
- Future-proof

However, both methods produce identical working configurations.

**Q: How do I install Claude CLI?**
A: Visit https://docs.claude.ai/cli for installation instructions. For macOS users with Homebrew:
```bash
brew install claude
```

**Q: What if Claude CLI is available but the command fails?**
A: The installer automatically falls back to JSON configuration and logs the error. You'll still get a working configuration.

**Q: Can I use different scopes for different projects?**
A: Yes! Use `--scope local` (project-specific) or `--scope user` (global) when manually configuring with `claude mcp add`.

## Implementation Details

For technical details about the implementation, see:
- Research document: [docs/research/claude-code-native-mcp-setup-2025-11-30.md](/Users/masa/Projects/mcp-ticketer/docs/research/claude-code-native-mcp-setup-2025-11-30.md)
- Implementation commit: `6af6014`
- Source code: `src/mcp_ticketer/cli/mcp_configure.py`

## Testing Coverage

The native CLI support includes comprehensive test coverage:
- ✅ 15 test cases covering all scenarios
- ✅ CLI detection and availability checking
- ✅ Command construction for all adapters
- ✅ Fallback behavior when CLI unavailable
- ✅ Error handling and timeout scenarios
- ✅ Sensitive credential masking

## Related Documentation

- [Installation Guide](../user-docs/installation/INSTALLATION.md)
- [Configuration Reference](../user-docs/configuration/CONFIGURATION.md)
- [Troubleshooting Guide](../user-docs/troubleshooting/TROUBLESHOOTING.md)
- [MCP Setup Documentation](../SETUP_COMMAND.md)

---

**Version**: 1.4.0+
**Date**: 2025-11-30
**Commit**: 6af6014
**Status**: ✅ Implemented and Tested
