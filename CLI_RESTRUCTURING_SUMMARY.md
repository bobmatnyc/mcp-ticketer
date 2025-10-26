# CLI Restructuring Summary

## Overview

The MCP Ticketer CLI has been restructured to follow the kuzu-memory pattern, with a clear hierarchy of commands organized into logical groups. This restructuring improves discoverability, reduces clutter at the top level, and provides a more intuitive user experience.

## New Command Structure

```
mcp-ticketer
│
├── Top-Level Commands (System Management)
│   ├── init                    # Initialize/setup project
│   ├── setup                   # Alias for init
│   ├── install                 # Alias for init
│   ├── status (alias: health)  # Quick health check
│   ├── health (alias: status)  # Quick health check
│   ├── doctor (alias: diagnose) # Comprehensive diagnostics
│   ├── diagnose (alias: doctor) # Comprehensive diagnostics
│   ├── configure               # Configuration wizard
│   ├── set                     # Set adapter configuration
│   ├── migrate-config          # Migrate config format
│   └── serve                   # Start MCP server
│
├── ticket                      # Ticket operations (NEW GROUP)
│   ├── create                  # Create ticket
│   ├── list                    # List tickets
│   ├── show                    # Show ticket details
│   ├── update                  # Update ticket
│   ├── transition              # Change ticket state
│   ├── search                  # Search tickets
│   ├── comment                 # Add comment
│   └── check                   # Check queued operation
│
├── mcp                         # MCP client configuration
│   ├── claude                  # Configure Claude Code/Desktop
│   ├── gemini                  # Configure Gemini CLI
│   ├── codex                   # Configure Codex CLI
│   └── auggie                  # Configure Auggie CLI
│
├── platform                    # Platform-specific commands (NEW GROUP)
│   ├── linear
│   │   ├── workspaces          # List workspaces
│   │   ├── teams               # List teams
│   │   ├── configure           # Configure Linear adapter
│   │   └── info                # Show team info
│   ├── jira                    # Placeholder for future
│   │   ├── projects            # (Placeholder)
│   │   └── configure           # (Placeholder)
│   ├── github                  # Placeholder for future
│   │   ├── repos               # (Placeholder)
│   │   └── configure           # (Placeholder)
│   └── aitrackdown             # Placeholder for future
│       ├── info                # (Placeholder)
│       └── configure           # (Placeholder)
│
├── queue                       # Queue management
│   └── worker
│       ├── start
│       ├── stop
│       ├── status
│       └── restart
│
└── discover                    # Environment discovery
    └── ...
```

## Key Changes

### 1. New Command Groups

#### `ticket` Group
All ticket-related operations have been consolidated under the `ticket` command group:

**Before:**
```bash
mcp-ticketer create "My ticket"
mcp-ticketer list
mcp-ticketer show TICKET-123
```

**After:**
```bash
mcp-ticketer ticket create "My ticket"
mcp-ticketer ticket list
mcp-ticketer ticket show TICKET-123
```

#### `platform` Group
Platform-specific commands are now organized under the `platform` group:

**Before:**
```bash
mcp-ticketer linear teams
mcp-ticketer linear configure --team-id ABC123
```

**After:**
```bash
mcp-ticketer platform linear teams
mcp-ticketer platform linear configure --team-id ABC123
```

### 2. Command Aliases

The following command aliases have been added for convenience:

- `status` ↔ `health` - System health check
- `diagnose` ↔ `doctor` - Comprehensive diagnostics

**Examples:**
```bash
mcp-ticketer status       # Same as: mcp-ticketer health
mcp-ticketer doctor       # Same as: mcp-ticketer diagnose
```

### 3. Backward Compatibility

All old top-level ticket commands are still available but are marked as **deprecated** and **hidden**. When used, they will display a deprecation warning and redirect users to the new command structure:

```bash
$ mcp-ticketer create "My ticket"
⚠️  This command is deprecated. Use 'mcp-ticketer ticket create' instead.
```

The deprecated commands include:
- `create` → `ticket create`
- `list` → `ticket list`
- `show` → `ticket show`
- `update` → `ticket update`
- `transition` → `ticket transition`
- `search` → `ticket search`
- `comment` → `ticket comment`
- `check` → `ticket check`

### 4. Platform Placeholders

Placeholder command groups have been added for future platform integrations:
- **JIRA** - `mcp-ticketer platform jira`
- **GitHub** - `mcp-ticketer platform github`
- **AITrackdown** - `mcp-ticketer platform aitrackdown`

These placeholders provide helpful messages directing users to use the generic ticket commands until platform-specific features are implemented.

## File Changes

### New Files Created

1. **`src/mcp_ticketer/cli/ticket_commands.py`**
   - Contains all ticket management commands
   - Includes configuration functions (load_config, save_config, get_adapter)
   - Self-contained to avoid circular imports

2. **`src/mcp_ticketer/cli/platform_commands.py`**
   - Platform command group orchestration
   - Imports and registers Linear commands
   - Placeholder apps for JIRA, GitHub, and AITrackdown

### Modified Files

1. **`src/mcp_ticketer/cli/main.py`**
   - Added imports for new command groups
   - Registered `ticket` and `platform` command groups
   - Deprecated old top-level ticket commands
   - Added command aliases (status/health, diagnose/doctor)
   - Removed direct `linear_app` registration (now under platform)

2. **`src/mcp_ticketer/cli/linear_commands.py`**
   - No changes required (works as-is under platform group)

## Migration Guide

### For End Users

#### Updating Scripts
If you have scripts using the old commands, they will continue to work but will show deprecation warnings. Update them to use the new structure:

**Old scripts:**
```bash
#!/bin/bash
mcp-ticketer create "Bug in login"
mcp-ticketer list --state todo
mcp-ticketer linear teams
```

**Updated scripts:**
```bash
#!/bin/bash
mcp-ticketer ticket create "Bug in login"
mcp-ticketer ticket list --state todo
mcp-ticketer platform linear teams
```

#### Using Aliases
Take advantage of the new aliases for brevity:

```bash
# Instead of: mcp-ticketer diagnose
mcp-ticketer doctor

# Instead of: mcp-ticketer health
mcp-ticketer status
```

### For Developers

#### Adding New Platform Commands

To add commands for a new platform (e.g., JIRA), follow this pattern:

1. Create the command module (e.g., `jira_commands.py`)
2. Import it in `platform_commands.py`
3. Replace the placeholder app with your real implementation

**Example:**
```python
# In src/mcp_ticketer/cli/jira_commands.py
import typer

app = typer.Typer(name="jira", help="JIRA workspace and project management")

@app.command("projects")
def list_projects():
    """List JIRA projects."""
    # Implementation here
    pass

# In src/mcp_ticketer/cli/platform_commands.py
from .jira_commands import app as jira_app

# Replace the placeholder:
# jira_app = typer.Typer(...)  # OLD
# with:
# from .jira_commands import app as jira_app  # NEW
```

## Testing

All new command structures have been tested and verified:

✅ `mcp-ticketer --help` - Shows new command groups
✅ `mcp-ticketer ticket --help` - Shows ticket subcommands
✅ `mcp-ticketer platform --help` - Shows platform groups
✅ `mcp-ticketer platform linear --help` - Shows Linear commands
✅ `mcp-ticketer status` / `mcp-ticketer health` - Aliases work
✅ `mcp-ticketer doctor` / `mcp-ticketer diagnose` - Aliases work
✅ Old commands show deprecation warnings

## Benefits

1. **Better Organization** - Commands are logically grouped by function
2. **Cleaner Top Level** - Reduced clutter at the main help level
3. **Improved Discoverability** - Users can explore commands by category
4. **Future-Proof** - Easy to add new platforms without polluting the top level
5. **Backward Compatible** - Existing scripts continue to work (with warnings)
6. **Consistent Pattern** - Follows established CLI patterns (kuzu-memory style)
7. **Alias Convenience** - Common operations have intuitive aliases

## Next Steps

1. ✅ Implement restructuring
2. ✅ Add deprecation warnings
3. ✅ Test all command paths
4. 📝 Update documentation (in progress)
5. 🔄 Deprecation cycle (6-12 months before removing old commands)
6. 🚀 Implement platform-specific commands for JIRA and GitHub

---

**Version:** 1.0.0
**Date:** October 26, 2025
**Author:** Generated via Claude Code MPM
