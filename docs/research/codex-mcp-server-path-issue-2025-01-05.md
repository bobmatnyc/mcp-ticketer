# Codex MCP Server Configuration Path Issue

**Date**: 2025-01-05
**Status**: Root Cause Identified
**Severity**: High (Blocks Codex Integration)

## Summary

Codex CLI shows no MCP servers configured (`codex.list_mcp_resources({})` returns empty) despite `mcp-ticketer install codex` completing successfully. Root cause: incorrect CLI path construction in `codex_configure.py`.

## Investigation

### 1. Configuration File Status

**Location**: `~/.codex/config.toml`
**Status**: ✅ EXISTS with mcp-ticketer configured

```toml
[mcp_servers.mcp-ticketer]
command = "/opt/homebrew/opt/python@3.11/bin/mcp-ticketer"
args = [
    "mcp",
    "--path",
    "/Users/masa/Projects/mcp-ticketer",
]
```

### 2. Path Validation

**Configured Command**: `/opt/homebrew/opt/python@3.11/bin/mcp-ticketer`
**Exists**: ❌ NO - File does not exist

**Actual CLI Location**: `/opt/homebrew/bin/mcp-ticketer`
**Exists**: ✅ YES - Working CLI

### 3. Root Cause Analysis

**File**: `src/mcp_ticketer/cli/codex_configure.py` (lines 104-107)

```python
# Get mcp-ticketer CLI path from Python path
# If python_path is /path/to/venv/bin/python, CLI is /path/to/venv/bin/mcp-ticketer
python_dir = Path(python_path).parent
cli_path = str(python_dir / "mcp-ticketer")
```

**Problem Flow**:

1. `get_mcp_ticketer_python()` reads shebang from `/opt/homebrew/bin/mcp-ticketer`:
   ```
   #!/opt/homebrew/opt/python@3.11/bin/python3.11
   ```

2. Returns: `/opt/homebrew/opt/python@3.11/bin/python3.11`

3. `codex_configure.py` constructs CLI path:
   ```python
   python_dir = Path("/opt/homebrew/opt/python@3.11/bin/python3.11").parent
   # python_dir = "/opt/homebrew/opt/python@3.11/bin"

   cli_path = str(python_dir / "mcp-ticketer")
   # cli_path = "/opt/homebrew/opt/python@3.11/bin/mcp-ticketer"
   ```

4. **BUT**: `mcp-ticketer` is actually at `/opt/homebrew/bin/mcp-ticketer`, not in the Python directory!

### 4. Why This Happens

**Homebrew Installation Structure**:
- Python binaries: `/opt/homebrew/opt/python@3.11/bin/python3.11`
- pip-installed scripts: `/opt/homebrew/bin/mcp-ticketer`
- The script directory is NOT the same as the Python directory

**Incorrect Assumption**:
The code assumes that if Python is at `/path/to/bin/python`, then mcp-ticketer CLI is at `/path/to/bin/mcp-ticketer`. This is true for pipx virtual environments but NOT for Homebrew installations.

### 5. Verification

```bash
# Config path (doesn't exist)
$ test -f /opt/homebrew/opt/python@3.11/bin/mcp-ticketer
# Returns: Does NOT exist

# Actual path (exists and works)
$ test -f /opt/homebrew/bin/mcp-ticketer
# Returns: Exists

$ /opt/homebrew/bin/mcp-ticketer --help
# Returns: Works correctly
```

## Impact

**Severity**: High
**Affected**: Codex CLI integration with Homebrew-installed mcp-ticketer

**Symptoms**:
- `mcp-ticketer install codex` completes without error
- Config file is created with incorrect CLI path
- Codex cannot launch MCP server (command not found)
- `codex.list_mcp_resources({})` returns empty (no resources available)
- No error message to user about failed MCP server startup

## Solution Options

### Option 1: Use `shutil.which()` to Find CLI (Recommended)

**Approach**: Use `shutil.which("mcp-ticketer")` to get the actual CLI path instead of constructing it from Python path.

**Pros**:
- Works across all installation methods (Homebrew, pipx, pip, etc.)
- Uses the actual PATH resolution that will be used at runtime
- Simple, reliable, proven approach

**Cons**:
- None significant

**Implementation**:

```python
def create_codex_server_config(
    python_path: str, project_config: dict, project_path: str | None = None
) -> dict[str, Any]:
    """Create Codex MCP server configuration for mcp-ticketer."""

    # Use shutil.which to find the actual CLI path (works across all install methods)
    cli_path = shutil.which("mcp-ticketer")
    if not cli_path:
        raise FileNotFoundError(
            "mcp-ticketer CLI not found in PATH. "
            "Ensure mcp-ticketer is installed and available."
        )

    # Build CLI arguments
    args = ["mcp"]
    if project_path:
        args.extend(["--path", project_path])

    config: dict[str, Any] = {
        "command": cli_path,
        "args": args,
    }

    return config
```

### Option 2: Check Multiple Locations

**Approach**: Try multiple common paths and use the first that exists.

**Pros**:
- Explicit fallback chain
- Can handle edge cases

**Cons**:
- More complex
- May miss valid installations in non-standard locations
- Maintenance burden (need to update for new package managers)

**Implementation**:

```python
def find_cli_path(python_path: str) -> str:
    """Find mcp-ticketer CLI path by checking common locations."""

    # Try 1: Same directory as Python (pipx, venv)
    python_dir = Path(python_path).parent
    cli_path = python_dir / "mcp-ticketer"
    if cli_path.exists():
        return str(cli_path)

    # Try 2: shutil.which (PATH resolution)
    which_path = shutil.which("mcp-ticketer")
    if which_path:
        return which_path

    # Try 3: Common Homebrew location
    homebrew_path = Path("/opt/homebrew/bin/mcp-ticketer")
    if homebrew_path.exists():
        return str(homebrew_path)

    raise FileNotFoundError("mcp-ticketer CLI not found")
```

### Option 3: Use Python Module Invocation (Legacy)

**Approach**: Use `python -m mcp_ticketer.cli.main mcp` instead of CLI command.

**Pros**:
- Always works if mcp-ticketer is importable
- No path resolution needed

**Cons**:
- Longer command
- Less clean than CLI invocation
- May have different behavior than CLI

**NOT RECOMMENDED**: The code already migrated away from Python module invocation to CLI for good reasons.

## Recommended Fix

**Use Option 1: `shutil.which()` to find CLI**

### Changes Required

**File**: `src/mcp_ticketer/cli/codex_configure.py`

**Lines to Change**: 104-107

**Before**:
```python
# Get mcp-ticketer CLI path from Python path
# If python_path is /path/to/venv/bin/python, CLI is /path/to/venv/bin/mcp-ticketer
python_dir = Path(python_path).parent
cli_path = str(python_dir / "mcp-ticketer")
```

**After**:
```python
# Use shutil.which to find the actual CLI path (works across all install methods)
import shutil
cli_path = shutil.which("mcp-ticketer")
if not cli_path:
    raise FileNotFoundError(
        "mcp-ticketer CLI not found in PATH. "
        "Ensure mcp-ticketer is installed and available."
    )
```

**Additional Changes**:
- Add `import shutil` at top of file (may already exist)
- Add validation error message if CLI not found
- Update docstring to reflect new approach

### Testing Plan

1. **Test Homebrew Installation**:
   ```bash
   # Install via Homebrew Python
   pip3 install mcp-ticketer
   mcp-ticketer install codex
   # Verify config has correct path: /opt/homebrew/bin/mcp-ticketer
   ```

2. **Test pipx Installation**:
   ```bash
   # Install via pipx
   pipx install mcp-ticketer
   mcp-ticketer install codex
   # Verify config has correct path: ~/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer
   ```

3. **Test venv Installation**:
   ```bash
   # Install in project venv
   python -m venv .venv
   source .venv/bin/activate
   pip install mcp-ticketer
   mcp-ticketer install codex
   # Verify config has correct path: ./.venv/bin/mcp-ticketer
   ```

4. **Test Codex Integration**:
   ```bash
   # After fix, verify MCP server works
   codex
   # In Codex, run:
   codex.list_mcp_resources({})
   # Should return mcp-ticketer resources
   ```

## Related Issues

**CRITICAL**: This issue affects ALL platform configuration modules!

**Affected Files** (same pattern in all):
- ✅ `codex_configure.py` (lines 105-106)
- ✅ `auggie_configure.py` (lines 147-148)
- ✅ `cursor_configure.py` (lines 105-106)
- ✅ `gemini_configure.py` (lines 148-149)
- ✅ `mcp_configure.py` (lines 531-532, 1023-1024 - TWO instances!)

**Impact**: ALL platform integrations will fail with Homebrew-installed mcp-ticketer:
- Codex CLI
- Auggie
- Cursor
- Gemini CLI
- Generic MCP configuration

**Pattern in All Files**:
```python
python_dir = Path(python_path).parent
cli_path = str(python_dir / "mcp-ticketer")
```

**Required Fix**: Replace pattern in ALL files with `shutil.which("mcp-ticketer")`

## Additional Notes

### Why `get_mcp_ticketer_python()` Exists

The Python detection function is still useful for:
- Validation that mcp-ticketer is importable
- Getting the correct Python for module invocation (if needed)
- Supporting project-local venv detection

However, for CLI path resolution, `shutil.which()` is the correct approach.

### Homebrew vs pipx Differences

**pipx**:
- Python: `~/.local/pipx/venvs/mcp-ticketer/bin/python`
- CLI: `~/.local/pipx/venvs/mcp-ticketer/bin/mcp-ticketer`
- Same directory ✅

**Homebrew**:
- Python: `/opt/homebrew/opt/python@3.11/bin/python3.11`
- CLI: `/opt/homebrew/bin/mcp-ticketer` (different directory!)
- Different directory ❌

**pip (system/venv)**:
- Python: `/path/to/venv/bin/python`
- CLI: `/path/to/venv/bin/mcp-ticketer`
- Same directory ✅

The current code works for pipx and venv but fails for Homebrew.

## Action Items

**Priority: CRITICAL** - Blocks all platform integrations on Homebrew

### Required Fixes (All Files)
- [ ] Fix `codex_configure.py` lines 105-106 to use `shutil.which()`
- [ ] Fix `auggie_configure.py` lines 147-148 to use `shutil.which()`
- [ ] Fix `cursor_configure.py` lines 105-106 to use `shutil.which()`
- [ ] Fix `gemini_configure.py` lines 148-149 to use `shutil.which()`
- [ ] Fix `mcp_configure.py` lines 531-532 AND 1023-1024 (TWO instances!)

### Testing
- [ ] Add test coverage for Homebrew installation
- [ ] Add test coverage for pipx installation
- [ ] Add test coverage for venv installation
- [ ] Test each platform integration after fix

### Documentation
- [ ] Update documentation about supported installation methods
- [ ] Add troubleshooting guide for path issues
- [ ] Document differences between Homebrew/pipx/venv installations

### Code Quality
- [ ] Extract CLI path resolution into shared utility function (DRY principle)
- [ ] Add validation that CLI path exists and is executable
- [ ] Add better error messages when CLI not found

## Tags

`#bug` `#codex` `#configuration` `#homebrew` `#cli-path` `#mcp-server`
