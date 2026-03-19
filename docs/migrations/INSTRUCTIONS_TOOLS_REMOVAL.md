# Migration Guide: Instructions Tools Removed from MCP Server

**Version:** v1.5.0
**Ticket:** 1M-484
**Phase:** Phase 2 Sprint 2.3

## Overview

The following MCP tools have been removed from the MCP server and are now available exclusively via the CLI. This reduces token overhead per request and keeps the MCP interface focused on ticket management operations.

## Removed MCP Tools

| Tool | Token Cost | Replacement |
|------|-----------|-------------|
| `instructions_get` | 750 tokens | `aitrackdown instructions show` |
| `instructions_set` | 800 tokens | `aitrackdown instructions add` / `aitrackdown instructions update` |
| `instructions_reset` | 740 tokens | `aitrackdown instructions delete` |
| `instructions_validate` | 710 tokens | (validation runs automatically) |

**Total token savings per session:** 3,000 tokens

## Why This Change?

Instructions management is a setup/configuration concern, not a per-ticket operation. Keeping these tools in the MCP server added 3,000 tokens of overhead to every session. Moving them to the CLI reduces bloat and lets the MCP server focus on its core purpose.

The tools still exist in the codebase (`mcp_ticketer.mcp.server.tools.instruction_tools`) and are fully functional — they are simply not registered with the MCP server.

## CLI Alternatives

Use the `aitrackdown instructions` CLI commands instead:

```bash
# View current instructions
aitrackdown instructions show

# Add new instructions
aitrackdown instructions add "Your instruction text"

# Update existing instructions
aitrackdown instructions update <id> "Updated text"

# Delete instructions
aitrackdown instructions delete <id>

# Show instructions file path
aitrackdown instructions path

# Open instructions in editor
aitrackdown instructions edit
```

## Filesystem and MCP Access

If you previously used the MCP tools to manage instructions from within an AI session, use the filesystem MCP tools instead to read/write the instructions file directly. The path can be found with `aitrackdown instructions path`.

Example using filesystem mcp:
```
Read the instructions file at the path returned by `aitrackdown instructions path`
```

## Affected Files

- `src/mcp_ticketer/mcp/server/tools/instruction_tools.py` — tools still exist, not registered
- `src/mcp_ticketer/mcp/server/__init__.py` — registration removed
- `src/mcp_ticketer/cli/instruction_commands.py` — CLI commands (unchanged)

## Rollback

If you need the MCP tools temporarily, re-register them in `server_sdk`:

```python
from mcp_ticketer.mcp.server.tools.instruction_tools import (
    instructions_get,
    instructions_set,
    instructions_reset,
    instructions_validate,
)
```
