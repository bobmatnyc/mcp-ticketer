# Release Notes v0.11.4

## Critical MCP Server Fix

### 🐛 Bug Fix: MCP Server Configuration Priority

**Problem:**
The MCP server was failing to connect when `.env` files contained environment variables for different adapters than the configured one.

**Symptoms:**
```
Required configuration key github_repo not found
Fatal error: GitHub adapter missing required configuration: repo
```

**Root Cause:**
- MCP server's configuration priority was incorrect
- Environment variable auto-detection had **higher priority** than project config file
- When `.env.local` contained `GITHUB_TOKEN` and `GITHUB_OWNER` (from other work)
- Server would auto-detect GitHub, override the Linear configuration
- Then fail because `GITHUB_REPO` was missing

**Solution:**
Changed configuration priority order in `main()`:

**Before (Wrong):**
1. Priority 1: .env files with auto-detection ← **Too high!**
2. Priority 2: `.mcp-ticketer/config.json`
3. Priority 3: Default to aitrackdown

**After (Correct):**
1. **Priority 1 (Highest): `.mcp-ticketer/config.json`** ← **Project config wins!**
2. Priority 2: .env files with auto-detection
3. Priority 3 (Lowest): Default to aitrackdown

### Impact

✅ **Project config file is now authoritative** - explicit configuration always wins
✅ **.env auto-detection only used as fallback** - when no config file exists
✅ **Prevents conflicts** - no more env var interference with configured adapters
✅ **Better UX** - users' explicit choices are always respected

### Testing

**Before fix:**
```bash
[MCP Server] Loaded environment from: .env.local
Required configuration key github_repo not found
[MCP Server] Fatal error: GitHub adapter missing required configuration
```

**After fix:**
```bash
[MCP Server] Loaded environment from: .env.local
[MCP Server] Using adapter from config: linear
[Server running successfully]
```

## Installation

```bash
# Upgrade
pip install --upgrade mcp-ticketer

# Fresh install
pip install mcp-ticketer==0.11.4

# Verify
mcp-ticketer --version  # Should show 0.11.4
```

## Links

- **PyPI:** https://pypi.org/project/mcp-ticketer/0.11.4/
- **GitHub:** (Release pending - GitHub experiencing 500 errors)
- **Documentation:** https://github.com/bobmatnyc/mcp-ticketer

## Previous Releases

- **v0.11.3** - 1Password CLI Integration & Bug Fixes
- **v0.11.2** - Type annotations and formatting improvements
- **v0.11.1** - Previous bug fixes

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
