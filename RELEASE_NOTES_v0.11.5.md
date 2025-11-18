# Release Notes v0.11.5

## Critical MCP Server Configuration Priority Fix

### 🐛 Bug Fix: Correct Configuration Priority Order

**Problem:**
The MCP server was checking `.env` files BEFORE `config.json`, causing it to initialize the wrong adapter when environment variables existed for multiple adapters.

**Symptoms:**
```
Required configuration key github_repo not found
Fatal error: GitHub adapter missing required configuration: repo
```

Even when `.mcp-ticketer/config.json` explicitly configured Linear adapter.

**Root Cause:**
- Configuration priority in `mcp_serve()` was incorrect (lines 2932-2951 in `src/mcp_ticketer/cli/main.py`)
- `.env` auto-detection had **higher priority** than project configuration file
- When `.env` or `.env.local` contained `GITHUB_*` variables (even if unused)
- Server would auto-detect GitHub adapter and override Linear from `config.json`
- Would fail with GitHub credential errors despite Linear being configured

**Solution:**
Fixed configuration priority order in `mcp_serve()` function:

**Before (Wrong):**
1. CLI argument
2. **`.env` files with auto-detection** ← **Too high priority!**
3. **`.mcp-ticketer/config.json`** ← **Should be higher!**
4. Default to aitrackdown

**After (Correct):**
1. CLI argument
2. **`.mcp-ticketer/config.json`** ← **Project config now wins!**
3. **`.env` files with auto-detection** ← **Now a fallback**
4. Default to aitrackdown

### Technical Details

**File Modified:** `src/mcp_ticketer/cli/main.py`
**Lines Changed:** 2932-2957 (26 lines)

The fix restructures the adapter selection logic to:
- Check project-specific configuration (`config.json`) first
- Use `.env` auto-detection only when no explicit config exists
- Preserve all existing functionality for CLI and defaults

### Impact

✅ **Project config file is now authoritative** - explicit configuration always takes precedence
✅ **`.env` auto-detection serves as fallback** - only used when config.json doesn't specify an adapter
✅ **Prevents adapter conflicts** - no more environment variable interference
✅ **Better user experience** - users' explicit configuration choices are always respected
✅ **Fixes MCP server crashes** - when multiple adapter env vars exist

### Testing

**Before fix:**
```bash
# With .mcp-ticketer/config.json specifying Linear
# And .env containing GITHUB_TOKEN, GITHUB_OWNER
mcp-ticketer mcp serve
# Result: Tries to use GitHub adapter (WRONG!)
# Error: "GitHub adapter missing required configuration: repo"
```

**After fix:**
```bash
# Same configuration
mcp-ticketer mcp serve
# Result: Uses Linear adapter from config.json (CORRECT!)
# Server starts successfully with Linear
```

**Test Scenarios Verified:**
- ✅ Config.json with Linear + .env with GitHub vars → Uses Linear (correct)
- ✅ Config.json with Linear, no .env → Uses Linear (correct)
- ✅ No config.json, no .env → Uses default aitrackdown (correct)
- ✅ CLI argument override still works (highest priority)
- ✅ CLI commands (`status`, `doctor`) unchanged

### Upgrade Instructions

```bash
# Using pip
pip install --upgrade mcp-ticketer

# Using pipx (recommended)
pipx upgrade mcp-ticketer

# Verify version
mcp-ticketer --version  # Should show 0.11.5
```

### Migration Notes

No configuration changes needed! This fix makes the system work as documented:

**Priority order** (as documented in `mcp serve --help`):
1. Command-line `--adapter` flag
2. Project-specific: `.mcp-ticketer/config.json`
3. Global: `~/.mcp-ticketer/config.json`
4. Auto-detection from `.env` files
5. Default: aitrackdown

If you were experiencing MCP server crashes due to adapter conflicts, this version fixes the issue automatically.

## Installation

```bash
# Fresh install
pip install mcp-ticketer==0.11.5

# Using pipx (recommended)
pipx install mcp-ticketer==0.11.5

# Upgrade existing installation
pip install --upgrade mcp-ticketer

# Verify installation
mcp-ticketer --version
mcp-ticketer doctor  # Run diagnostics
```

## Links

- **PyPI:** https://pypi.org/project/mcp-ticketer/0.11.5/
- **GitHub:** https://github.com/bobmatnyc/mcp-ticketer
- **Documentation:** https://github.com/bobmatnyc/mcp-ticketer/blob/main/README.md
- **Issue Tracker:** https://github.com/bobmatnyc/mcp-ticketer/issues

## Previous Releases

- **v0.11.4** - 1Password CLI Integration & Security Improvements
- **v0.11.3** - Additional 1Password features
- **v0.11.2** - Type annotations and formatting improvements
- **v0.11.1** - Bug fixes and stability improvements

---

🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)

Co-Authored-By: Claude <noreply@anthropic.com>
