# Implementation Summary: MCP Configuration Fix

## Files Modified

### 1. `src/mcp_ticketer/cli/mcp_configure.py`

#### Changes Made:

##### A. `find_claude_mcp_config()` - Lines 79-113
**Change**: Updated Claude Code config path

```python
# OLD (line 111):
config_path = Path.cwd() / ".claude" / "settings.local.json"

# NEW (line 111):
config_path = Path.home() / ".claude.json"
```

**Impact**: Claude Code now uses `~/.claude.json` instead of project-local `.claude/settings.local.json`

---

##### B. `load_claude_mcp_config()` - Lines 116-147
**Changes**: Added parameter and error handling

```python
# OLD signature:
def load_claude_mcp_config(config_path: Path) -> dict:

# NEW signature:
def load_claude_mcp_config(config_path: Path, is_claude_code: bool = False) -> dict:
```

**Added**:
1. JSON parsing error handling (lines 128-141)
2. Empty file handling (lines 131-133)
3. Conditional default structure based on `is_claude_code` parameter
4. Warning messages for invalid JSON

**Impact**: Robust handling of corrupt or empty config files

---

##### C. `configure_claude_mcp()` - Lines 316-478
**Major Refactor**: Added project-specific path handling

**Key Changes**:

1. **Line 361**: Updated console message from "project-level" to "Claude Code"

2. **Line 365**: Added "Primary config" label for clarity

3. **Lines 367-368**: Get absolute project path
   ```python
   absolute_project_path = str(Path.cwd().resolve()) if not global_config else None
   ```

4. **Lines 370-372**: Load config with appropriate structure
   ```python
   is_claude_code = not global_config
   mcp_config = load_claude_mcp_config(mcp_config_path, is_claude_code=is_claude_code)
   ```

5. **Lines 374-428**: Enhanced duplicate detection
   - Claude Code: Check `.projects[path].mcpServers["mcp-ticketer"]`
   - Claude Desktop: Check `.mcpServers["mcp-ticketer"]`

6. **Lines 445-440**: Write to project-specific structure
   ```python
   if is_claude_code:
       if absolute_project_path:
           # Ensure projects structure exists
           if "projects" not in mcp_config:
               mcp_config["projects"] = {}

           # Ensure project entry exists
           if absolute_project_path not in mcp_config["projects"]:
               mcp_config["projects"][absolute_project_path] = {}

           # Ensure mcpServers exists
           if "mcpServers" not in mcp_config["projects"][absolute_project_path]:
               mcp_config["projects"][absolute_project_path]["mcpServers"] = {}

           # Add mcp-ticketer configuration
           mcp_config["projects"][absolute_project_path]["mcpServers"]["mcp-ticketer"] = server_config
   ```

7. **Lines 424-440**: Add backward-compatible legacy config
   ```python
   legacy_config_path = Path.cwd() / ".claude" / "mcp.local.json"
   # Write to legacy location (non-fatal if fails)
   ```

**Impact**: Correct project-specific configuration for Claude Code

---

##### D. `remove_claude_mcp()` - Lines 256-355
**Updated**: Remove from both primary and legacy locations

**Key Changes**:

1. **Line 265**: Updated message to "Claude Code"

2. **Line 269**: Added "Primary config" label

3. **Lines 271-272**: Get absolute project path

4. **Lines 280-282**: Load with appropriate structure

5. **Lines 284-294**: Check correct location based on platform

6. **Lines 310-333**: Remove from both locations
   ```python
   if is_claude_code and absolute_project_path:
       # Remove from ~/.claude.json
       del mcp_config["projects"][absolute_project_path]["mcpServers"]["mcp-ticketer"]

       # Clean up empty structures
       if not mcp_config["projects"][absolute_project_path]["mcpServers"]:
           del mcp_config["projects"][absolute_project_path]["mcpServers"]
       if not mcp_config["projects"][absolute_project_path]:
           del mcp_config["projects"][absolute_project_path]

       # Also remove from legacy location
       legacy_config_path = Path.cwd() / ".claude" / "mcp.local.json"
       if legacy_config_path.exists():
           # Remove from legacy (non-fatal)
   ```

**Impact**: Complete cleanup of all configuration files

---

## Configuration Structure Changes

### Before (Incorrect)

**Location**: `.claude/settings.local.json`

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",
      "args": ["mcp"]
    }
  }
}
```

**Problem**: Claude Code doesn't read from this location

### After (Correct)

**Primary Location**: `~/.claude.json`

```json
{
  "projects": {
    "/Users/masa/Projects/mcp-ticketer": {
      "mcpServers": {
        "mcp-ticketer": {
          "type": "stdio",
          "command": "/Users/masa/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer",
          "args": ["mcp", "/Users/masa/Projects/mcp-ticketer"],
          "env": {
            "PYTHONPATH": "/Users/masa/Projects/mcp-ticketer",
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

**Secondary Location**: `.claude/mcp.local.json` (backward compatibility)

```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "type": "stdio",
      "command": "/Users/masa/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer",
      "args": ["mcp", "/Users/masa/Projects/mcp-ticketer"],
      "env": { ... }
    }
  }
}
```

---

## Key Improvements

1. ✅ **Correct Location**: Uses `~/.claude.json` (actual Claude Code config)
2. ✅ **Project-Specific**: Uses absolute paths as keys in `.projects`
3. ✅ **Type Field**: Includes `"type": "stdio"` (required)
4. ✅ **Absolute Paths**: All paths are absolute, not relative
5. ✅ **Error Handling**: Graceful handling of invalid JSON, empty files
6. ✅ **Backward Compatibility**: Maintains legacy config for older versions
7. ✅ **Cleanup**: Removes empty structures to keep config clean
8. ✅ **Clear Messaging**: Updated console output to distinguish Claude Code vs Desktop

---

## Testing

### Test Coverage

Created `test_mcp_configure_fix.py` with 7 tests:

1. ✅ Config path detection (`~/.claude.json`)
2. ✅ Projects structure loading
3. ✅ Empty config initialization (Claude Code)
4. ✅ Empty config initialization (Claude Desktop)
5. ✅ Invalid JSON handling
6. ✅ Save/load roundtrip
7. ✅ Expected structure validation

All tests pass successfully.

### Manual Verification

```bash
# Run installer
mcp-ticketer mcp install

# Check primary config
cat ~/.claude.json | python -m json.tool

# Check legacy config
cat .claude/mcp.local.json | python -m json.tool

# Verify structure
jq '.projects | keys[]' ~/.claude.json  # Should show absolute project path
```

---

## Lines of Code Impact

**Net LOC Delta**: +135 lines (added functionality for proper structure handling)

**Breakdown**:
- `find_claude_mcp_config`: +1 line (changed path)
- `load_claude_mcp_config`: +31 lines (error handling, parameter)
- `configure_claude_mcp`: +80 lines (project structure, legacy config)
- `remove_claude_mcp`: +23 lines (project structure cleanup)

**Justification**: Necessary complexity for correct Claude Code integration

---

## Migration Path

### For Existing Users

No manual migration needed. Next time they run `mcp-ticketer mcp install`:

1. New config written to `~/.claude.json` (correct location)
2. Legacy config updated in `.claude/mcp.local.json` (backward compat)
3. Restart Claude Code → MCP server works

### For New Users

Just works™ - installer creates correct structure from scratch.

---

## Verification Checklist

- [x] Config written to `~/.claude.json` (not `.claude/settings.local.json`)
- [x] Uses `.projects[absolute_path].mcpServers` structure
- [x] Includes `"type": "stdio"` field
- [x] All paths are absolute
- [x] Environment variables properly included
- [x] Legacy config written for backward compatibility
- [x] Removal cleans up both locations
- [x] Error handling for invalid JSON
- [x] Tests pass
- [x] Console output is clear and accurate

---

## Remaining Work

None - implementation is complete and tested.

### Optional Cleanup (Post-Merge)

- Delete `test_mcp_configure_fix.py` (temporary test file)
- Delete `MCP_CONFIGURE_FIX.md` (detailed explanation)
- Delete `IMPLEMENTATION_SUMMARY.md` (this file)
- Update user documentation to mention `~/.claude.json` location
