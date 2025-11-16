# MCP Configuration Fix for Claude Code

## Summary

Fixed the MCP installer (`src/mcp_ticketer/cli/mcp_configure.py`) to write configuration to the correct location for Claude Code.

## Problem

The installer was writing to `.claude/settings.local.json`, but Claude Code actually reads from `~/.claude.json` under project-specific paths: `.projects["/absolute/path/to/project"].mcpServers["server-name"]`

## Solution

Updated three key functions to support the correct Claude Code configuration structure:

### 1. `find_claude_mcp_config()` (lines 79-113)

**Changed**: For Claude Code (not Desktop), now returns `~/.claude.json` instead of `.claude/settings.local.json`

```python
# Before:
config_path = Path.cwd() / ".claude" / "settings.local.json"

# After:
config_path = Path.home() / ".claude.json"
```

### 2. `load_claude_mcp_config()` (lines 116-147)

**Enhanced**: Added `is_claude_code` parameter to return appropriate structure

- Claude Code: Returns `{"projects": {}}` for empty configs
- Claude Desktop: Returns `{"mcpServers": {}}` for empty configs
- Added JSON parsing error handling with graceful fallback
- Handles empty files correctly

```python
def load_claude_mcp_config(config_path: Path, is_claude_code: bool = False) -> dict:
    """Load existing Claude MCP configuration or return empty structure."""
    if config_path.exists():
        try:
            content = f.read().strip()
            if not content:
                return {"projects": {}} if is_claude_code else {"mcpServers": {}}
            return json.loads(content)
        except json.JSONDecodeError as e:
            # Handle invalid JSON gracefully
            return {"projects": {}} if is_claude_code else {"mcpServers": {}}

    return {"projects": {}} if is_claude_code else {"mcpServers": {}}
```

### 3. `configure_claude_mcp()` (lines 316-478)

**Refactored**: Now writes to both primary and legacy locations

#### Primary Configuration (Claude Code)

Writes to `~/.claude.json` with project-specific structure:

```json
{
  "projects": {
    "/absolute/path/to/project": {
      "mcpServers": {
        "mcp-ticketer": {
          "type": "stdio",
          "command": "/path/to/venv/bin/mcp-ticketer",
          "args": ["mcp", "/absolute/path/to/project"],
          "env": {
            "PYTHONPATH": "/absolute/path/to/project",
            "MCP_TICKETER_ADAPTER": "linear",
            "LINEAR_API_KEY": "...",
            "LINEAR_TEAM_ID": "...",
            "LINEAR_TEAM_KEY": "..."
          }
        }
      }
    }
  }
}
```

#### Secondary Configuration (Backward Compatibility)

Also writes to `.claude/mcp.local.json` for older Claude Code versions:

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "/path/to/venv/bin/mcp-ticketer",
      "args": ["mcp", "/absolute/path/to/project"],
      "env": { ... }
    }
  }
}
```

#### Key Implementation Details

1. **Absolute Paths**: Uses `Path.cwd().resolve()` for absolute project paths
2. **Structure Creation**: Ensures nested structure exists before writing:
   - `.projects` → `.projects[project_path]` → `.projects[project_path].mcpServers`
3. **Duplicate Detection**: Checks correct location based on platform:
   - Claude Code: `.projects[path].mcpServers["mcp-ticketer"]`
   - Claude Desktop: `.mcpServers["mcp-ticketer"]`
4. **Error Handling**: Legacy config writes are non-fatal (warns but continues)

### 4. `remove_claude_mcp()` (lines 256-355)

**Updated**: Now removes from both primary and legacy locations

- Removes from `~/.claude.json` project-specific path
- Cleans up empty structures (mcpServers, project entry)
- Also removes from `.claude/mcp.local.json` if it exists
- Shows appropriate messaging for Claude Code vs Desktop

## Configuration Structure Comparison

### Claude Desktop (Global)

```json
{
  "mcpServers": {
    "mcp-ticketer": { ... }
  }
}
```

**Location**:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Claude Code (Project-Specific)

```json
{
  "projects": {
    "/absolute/project/path": {
      "mcpServers": {
        "mcp-ticketer": { ... }
      }
    }
  }
}
```

**Location**: `~/.claude.json`

## Testing

Created comprehensive test script (`test_mcp_configure_fix.py`) verifying:

✅ Correct config path detection (`~/.claude.json` for Claude Code)
✅ Projects structure for Claude Code configs
✅ mcpServers structure for Claude Desktop configs
✅ Empty config initialization
✅ Invalid JSON handling with graceful fallback
✅ Save/load roundtrip correctness
✅ Expected configuration structure

All tests pass successfully.

## Error Handling

1. **JSON Parse Errors**: Warns and creates new config (non-fatal)
2. **Empty Files**: Handles gracefully with appropriate default structure
3. **Legacy Config Failures**: Warns but continues (non-fatal for backward compatibility)
4. **Missing Directories**: Creates parent directories as needed

## Backward Compatibility

- **Primary**: Uses new `~/.claude.json` structure (current Claude Code)
- **Legacy**: Also writes to `.claude/mcp.local.json` (older versions)
- **Desktop**: Unchanged behavior for Claude Desktop users

## Command Usage

```bash
# Configure for Claude Code (project-specific)
mcp-ticketer mcp install

# Configure for Claude Desktop (global)
mcp-ticketer mcp install --global

# Force overwrite existing config
mcp-ticketer mcp install --force

# Remove from Claude Code
mcp-ticketer mcp uninstall

# Remove from Claude Desktop
mcp-ticketer mcp uninstall --global
```

## Verification

After installation, verify configuration:

```bash
# Claude Code config
cat ~/.claude.json | python -m json.tool

# Legacy config
cat .claude/mcp.local.json | python -m json.tool
```

Expected output shows:
- `"type": "stdio"` field present
- Absolute project path in args
- Environment variables properly set
- Command points to correct mcp-ticketer executable

## Migration Notes

Users upgrading from older versions will automatically get:
1. New configuration written to `~/.claude.json`
2. Legacy configuration maintained in `.claude/mcp.local.json`
3. No manual migration needed - installer handles both

## Related Files

- `src/mcp_ticketer/cli/mcp_configure.py` - Main implementation
- `test_mcp_configure_fix.py` - Verification tests (can be deleted after review)
- `MCP_CONFIGURE_FIX.md` - This documentation (can be deleted after review)
