# Project-Level Configuration Guide

Complete guide to the new project-level configuration system with hierarchical resolution, environment variable support, and hybrid mode.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration Hierarchy](#configuration-hierarchy)
- [Configuration Wizard](#configuration-wizard)
- [Environment Variables](#environment-variables)
- [Hybrid Mode](#hybrid-mode)
- [Migration](#migration)
- [Examples](#examples)

## Quick Start

### Interactive Configuration

```bash
# Run the configuration wizard
mcp-ticketer configure

# Show current configuration
mcp-ticketer configure --show
```

### Direct Configuration

```bash
# Set adapter directly
mcp-ticketer configure --adapter linear --api-key lin_xxx --team-id team-abc

# Set global config
mcp-ticketer configure --adapter linear --api-key lin_xxx --global
```

## Configuration Hierarchy

Configuration is resolved with the following precedence (highest to lowest):

1. **CLI Flags** - `--adapter`, `--api-key`, etc.
2. **Environment Variables** - `MCP_TICKETER_*` and adapter-specific vars
3. **Project Config** - `.mcp-ticketer/config.json` in project root
4. **Global Config** - `~/.mcp-ticketer/config.json`

## Configuration Wizard

Run `mcp-ticketer configure` to launch the interactive wizard.

### Single Adapter Mode

1. Select ticketing system (Linear, JIRA, GitHub, AITrackdown)
2. Enter credentials
3. Choose scope (global or project-specific)

### Hybrid Mode

1. Select 2+ adapters
2. Configure each adapter
3. Choose primary adapter
4. Select sync strategy

## Environment Variables

### Global

- `MCP_TICKETER_ADAPTER` - Override default adapter
- `MCP_TICKETER_API_KEY` - Generic API key
- `MCP_TICKETER_HYBRID_MODE` - Enable hybrid mode (`true`/`false`)
- `MCP_TICKETER_HYBRID_ADAPTERS` - Comma-separated list (e.g., `linear,github`)

### Linear

- `LINEAR_API_KEY` - Linear API key (https://linear.app/settings/api)
- `MCP_TICKETER_LINEAR_API_KEY` - Scoped Linear API key
- `MCP_TICKETER_LINEAR_TEAM_ID` - Team ID

### GitHub

- `GITHUB_TOKEN` - GitHub PAT (https://github.com/settings/tokens/new)
- `MCP_TICKETER_GITHUB_TOKEN` - Scoped GitHub PAT  
- `MCP_TICKETER_GITHUB_OWNER` - Repository owner
- `MCP_TICKETER_GITHUB_REPO` - Repository name

### JIRA

- `JIRA_SERVER` - JIRA server URL
- `JIRA_EMAIL` - User email
- `JIRA_API_TOKEN` - API token (https://id.atlassian.com/manage/api-tokens)
- `MCP_TICKETER_JIRA_*` - Scoped variants

### AITrackdown

- `MCP_TICKETER_AITRACKDOWN_BASE_PATH` - Base path (defaults to `.aitrackdown`)

## Hybrid Mode

Sync tickets across multiple platforms.

### Configuration

```json
{
  "default_adapter": "linear",
  "adapters": {
    "linear": { "adapter": "linear", "api_key": "lin_xxx" },
    "github": { "adapter": "github", "token": "ghp_xxx" }
  },
  "hybrid_mode": {
    "enabled": true,
    "adapters": ["linear", "github"],
    "primary_adapter": "linear",
    "sync_strategy": "primary_source"
  }
}
```

### Sync Strategies

- **primary_source**: One-way sync (primary → others)
- **bidirectional**: Two-way sync
- **mirror**: Clone tickets independently

## Migration

```bash
# Dry run
mcp-ticketer migrate-config --dry-run

# Apply migration
mcp-ticketer migrate-config
```

## Examples

See [CONFIGURATION.md](CONFIGURATION.md) for complete examples and troubleshooting.
