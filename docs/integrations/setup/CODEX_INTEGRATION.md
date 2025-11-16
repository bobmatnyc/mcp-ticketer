# Codex CLI Integration for MCP Ticketer

## Overview

This document describes the Codex CLI integration for mcp-ticketer, which allows the Codex AI assistant to interact with mcp-ticketer through the Model Context Protocol (MCP).

**Important**: Codex CLI only supports **global configuration** at `~/.codex/config.toml`. Unlike Claude Code and Gemini CLI, there is no project-level configuration support.

## Quick Start

### 1. Prerequisites

- mcp-ticketer installed (`pip install mcp-ticketer` or `make install-dev`)
- Project configured with `.mcp-ticketer/config.json` (run `mcp-ticketer init`)

### 2. Configure Codex CLI

```bash
# Option 1: Auto-detect (recommended)
mcp-ticketer install  # Select Codex CLI from detected platforms

# Option 2: Install directly
mcp-ticketer install codex

# Preview changes before applying
mcp-ticketer install codex --dry-run
```

### 3. Restart Codex CLI

**Important**: You must restart Codex CLI after configuration changes.

### 4. Verify Configuration

Check `~/.codex/config.toml`:

```toml
[mcp_servers.mcp-ticketer]
command = "/path/to/mcp-ticketer"
args = ["serve"]

[mcp_servers.mcp-ticketer.env]
PYTHONPATH = "/path/to/src"
MCP_TICKETER_ADAPTER = "aitrackdown"
MCP_TICKETER_BASE_PATH = "/path/to/.aitrackdown"
```

## Configuration Details

### File Locations

- **Codex Config**: `~/.codex/config.toml` (global only)
- **MCP Ticketer Config**: `.mcp-ticketer/config.json` (project-local)

### Configuration Scope

| CLI Tool | Scope Options | Config Location |
|----------|---------------|-----------------|
| Claude Code | Project, Global | `.mcp/config.json` or `~/Library/Application Support/Claude/` |
| Gemini CLI | Project, User | `.gemini/settings.json` or `~/.gemini/settings.json` |
| **Codex CLI** | **Global only** | **`~/.codex/config.toml`** |

### Environment Variables

The configuration automatically includes environment variables based on your adapter:

**AITrackdown (Local)**:
- `MCP_TICKETER_ADAPTER=aitrackdown`
- `MCP_TICKETER_BASE_PATH=/path/to/.aitrackdown`

**Linear**:
- `MCP_TICKETER_ADAPTER=linear`
- `LINEAR_API_KEY=your_api_key`
- `LINEAR_TEAM_ID=your_team_id`

**GitHub**:
- `MCP_TICKETER_ADAPTER=github`
- `GITHUB_TOKEN=your_token`
- `GITHUB_OWNER=owner`
- `GITHUB_REPO=repo`

**JIRA**:
- `MCP_TICKETER_ADAPTER=jira`
- `JIRA_API_TOKEN=your_token`
- `JIRA_EMAIL=your_email`
- `JIRA_SERVER=https://your-domain.atlassian.net`
- `JIRA_PROJECT_KEY=PROJECT`

## TOML Structure

### Key Differences from JSON-based CLIs

Codex uses TOML format with specific naming conventions:

```toml
# Codex uses underscore: mcp_servers (not camelCase mcpServers)
[mcp_servers.mcp-ticketer]
command = "/usr/local/bin/mcp-ticketer"
args = ["serve"]

# Environment variables in nested section
[mcp_servers.mcp-ticketer.env]
PYTHONPATH = "/path/to/src"
MCP_TICKETER_ADAPTER = "aitrackdown"
```

Compare to Claude Code JSON:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/usr/local/bin/mcp-ticketer",
      "args": ["serve"],
      "env": {
        "PYTHONPATH": "/path/to/src",
        "MCP_TICKETER_ADAPTER": "aitrackdown"
      }
    }
  }
}
```

## CLI Command Reference

```bash
# Install Codex CLI configuration
mcp-ticketer install codex [OPTIONS]

# Options:
#   --dry-run      Preview changes without making them
#   --help         Show help message

# Examples:
mcp-ticketer install codex                # Install globally
mcp-ticketer install codex --dry-run      # Preview changes
mcp-ticketer install codex --help         # Show help

# Remove configuration
mcp-ticketer remove codex                 # Remove configuration
mcp-ticketer uninstall codex              # Alias for remove
```

## Troubleshooting

### Configuration Not Taking Effect

**Problem**: Changes to config.toml not reflected in Codex CLI

**Solution**: Restart Codex CLI. Configuration changes require a restart.

### Wrong Adapter Active

**Problem**: Codex using wrong ticket adapter

**Solution**: Check `.mcp-ticketer/config.json` in your project:

```bash
# Show current configuration
mcp-ticketer configure --show

# Set different adapter
mcp-ticketer configure --adapter linear
```

Then reinstall Codex configuration:

```bash
mcp-ticketer remove codex        # Remove old config
mcp-ticketer install codex       # Install new config
```

### Binary Not Found

**Problem**: "Could not find mcp-ticketer binary"

**Solution**: Ensure mcp-ticketer is installed and in PATH:

```bash
# Check installation
which mcp-ticketer

# Install if missing
pip install mcp-ticketer

# Or for development
make install-dev
```

### Configuration Path Issues

**Problem**: TOML file has incorrect paths

**Solution**: Run configuration from your project directory:

```bash
cd /path/to/your/project
mcp-ticketer remove codex
mcp-ticketer install codex
```

## Implementation Details

### File Structure

```
src/mcp_ticketer/cli/
├── codex_configure.py    # Codex CLI configuration module
├── mcp_configure.py      # Claude Code configuration (JSON)
├── gemini_configure.py   # Gemini CLI configuration (JSON)
└── main.py              # CLI commands including 'codex' command
```

### Dependencies

Added to `pyproject.toml`:

```toml
dependencies = [
    # ... existing dependencies ...
    "tomli>=2.0.0; python_version<'3.11'",  # TOML reading (Python <3.11)
    "tomli-w>=1.0.0",                       # TOML writing (all versions)
]
```

### Key Functions

**`codex_configure.py`**:

- `find_codex_config()`: Returns `~/.codex/config.toml` path
- `load_codex_config(config_path)`: Loads existing TOML or empty structure
- `save_codex_config(config_path, config)`: Writes TOML with formatting
- `create_codex_server_config(binary_path, project_config, cwd)`: Creates server config
- `configure_codex_mcp(force)`: Main configuration function

## Testing

### Manual Test

```bash
# 1. Install configuration
mcp-ticketer install codex

# 2. Check TOML file
cat ~/.codex/config.toml

# 3. Test removal
mcp-ticketer remove codex --dry-run

# 4. Reinstall
mcp-ticketer install codex
```

### Automated Test

Run the included test script:

```bash
python3 test_codex_config.py
```

Expected output:

```
✓ Created test TOML file: /tmp/...
✓ TOML format validation passed
✓ Structure validation passed
✓ Value validation passed

✅ All tests passed!
```

## Comparison with Other CLIs

| Feature | Claude Code | Gemini CLI | Codex CLI |
|---------|-------------|------------|-----------|
| **Config Format** | JSON | JSON | **TOML** |
| **Config Location** | Project or Global | Project or User | **Global only** |
| **Key Name** | mcpServers | mcpServers | **mcp_servers** |
| **Scope Flag** | `--global` | `--scope user/project` | **None (global only)** |
| **Restart Required** | Yes | No | **Yes** |
| **Nested Env** | Yes | Yes | Yes |
| **Project Support** | Yes | Yes | **No** |

## Security Considerations

### Global Configuration Implications

Since Codex only supports global configuration:

1. **API Keys**: Environment variables (including API keys) are in global config
2. **Path References**: Configuration includes absolute paths from configuration time
3. **Multi-Project**: Same configuration used across all projects

### Best Practices

1. **Protect config.toml**: Ensure `~/.codex/config.toml` has appropriate permissions
2. **Avoid Hardcoded Secrets**: Use environment variables where possible
3. **Reconfigure Per Project**: Run `mcp-ticketer remove codex && mcp-ticketer install codex` when switching projects
4. **Review Configuration**: Periodically audit `~/.codex/config.toml`

## Future Enhancements

- [ ] Support for multiple adapters in single config
- [ ] Environment variable templating
- [ ] Automatic path resolution
- [ ] Configuration validation command
- [ ] Migration tool from JSON to TOML

## References

- [Codex CLI Documentation](https://github.com/your-org/codex-cli)
- [MCP Protocol Specification](https://modelcontextprotocol.io/)
- [TOML Specification](https://toml.io/en/)
- [mcp-ticketer Documentation](https://github.com/mcp-ticketer/mcp-ticketer)

## Support

For issues or questions:

1. Check troubleshooting section above
2. Review `~/.codex/config.toml` for correctness
3. Test with `mcp-ticketer install codex --dry-run`
4. File issue at https://github.com/mcp-ticketer/mcp-ticketer/issues
