# MCP Installer Command Structure Fix - Complete

## Summary
Fixed critical bug in ALL MCP installer configurations where the command structure was using non-existent `mcp-ticketer` executable instead of the Python module pattern.

## Problem
All installer configurations were generating:
```json
{
    "command": "/path/to/venv/bin/mcp-ticketer",  // ← May not exist
    "args": ["mcp", "/project/path"]
}
```

This fails because the `mcp-ticketer` executable may not exist in arbitrary Python virtual environments.

## Solution
Updated all configurations to use Python module invocation pattern:
```json
{
    "command": "/path/to/venv/bin/python",  // ← Use Python directly
    "args": ["-m", "mcp_ticketer.mcp.server", "/project/path"]
}
```

This works regardless of where `mcp-ticketer` is installed, as long as the package is importable.

## Files Modified

### 1. `/src/mcp_ticketer/cli/mcp_configure.py`
**Function**: `create_mcp_server_config()`
- **Before**:
  ```python
  python_dir = Path(python_path).parent
  mcp_ticketer_cmd = str(python_dir / "mcp-ticketer")
  args = ["mcp"]
  config = {"command": mcp_ticketer_cmd, "args": args, ...}
  ```
- **After**:
  ```python
  args = ["-m", "mcp_ticketer.mcp.server"]
  config = {"command": python_path, "args": args, ...}
  ```
- **Print statement**: Updated from `"Command: mcp-ticketer mcp"` to `"Command: python -m mcp_ticketer.mcp.server"`

### 2. `/src/mcp_ticketer/cli/auggie_configure.py`
**Function**: `create_auggie_server_config()`
- Same changes as above
- Removed unused `python_dir` and `mcp_ticketer_cmd` construction
- Updated command to use `python_path` directly
- Changed args from `["mcp"]` to `["-m", "mcp_ticketer.mcp.server"]`
- Updated print statement

### 3. `/src/mcp_ticketer/cli/gemini_configure.py`
**Function**: `create_gemini_server_config()`
- Same changes as above
- Updated command to use `python_path` directly
- Changed args from `["mcp"]` to `["-m", "mcp_ticketer.mcp.server"]`
- Updated print statement

### 4. `/src/mcp_ticketer/cli/codex_configure.py`
**Function**: `create_codex_server_config()`
- Same changes as above
- Updated command to use `python_path` directly
- Changed args from `["mcp"]` to `["-m", "mcp_ticketer.mcp.server"]`
- Updated print statement

## Testing
All changes were verified with unit tests:
- ✅ Command uses Python executable path directly
- ✅ Args use `-m mcp_ticketer.mcp.server` pattern
- ✅ Configuration works with and without project path
- ✅ Pattern matches working implementation from `mcp-vector-search`

## Benefits
1. **Reliability**: Works regardless of installation method (pip, pipx, editable install)
2. **Portability**: No dependency on specific binary locations
3. **Consistency**: Matches established MCP server patterns
4. **Compatibility**: Works across all supported platforms (macOS, Linux, Windows)

## Impact
- **Claude Code**: ✅ Fixed
- **Claude Desktop**: ✅ Fixed
- **Gemini CLI**: ✅ Fixed
- **Codex CLI**: ✅ Fixed
- **Auggie CLI**: ✅ Fixed

## Migration
**For existing users**: No manual migration needed. The fix will apply automatically when they run:
- `mcp-ticketer mcp claude`
- `mcp-ticketer mcp gemini`
- `mcp-ticketer mcp codex`
- `mcp-ticketer mcp auggie`

The installer will regenerate the configuration with the correct Python module pattern.

## Related Pattern
This fix implements the same pattern used by `mcp-vector-search`:
```json
{
    "command": "/path/to/venv/bin/python",
    "args": ["-m", "mcp_vector_search.mcp.server", "/project/path"]
}
```

## Verification Commands
```bash
# Verify Python module is importable
python -m mcp_ticketer.mcp.server --help

# Test configuration generation
mcp-ticketer mcp claude  # Regenerates config with fix
```

## Future Considerations
- All future installer configurations should use this Python module pattern
- Document this as the canonical pattern for MCP server installations
- Consider adding validation to warn about old configuration format

---

**Status**: ✅ Complete
**Date**: 2025-10-28
**Impact**: Critical bug fix affecting all MCP platform integrations
