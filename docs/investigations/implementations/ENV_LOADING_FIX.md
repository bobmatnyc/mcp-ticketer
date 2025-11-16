# Environment Loading Timing Fix

## Problem
The `.env.local` file loading was happening at Python module import time, which occurred BEFORE the working directory was changed to the target project directory in `__main__.py`. This caused the MCP server to load environment variables from the wrong directory.

## Root Cause Analysis

### Execution Flow (Before Fix)
```
1. claude-code runs: python -m mcp_ticketer.mcp.server /Users/masa/Projects/claude-mpm
2. Python imports mcp_ticketer.mcp.server.__main__
3. __main__.py imports from .main (line 16) ← Triggers module load
4. main.py module-level code (lines 31-46): load_dotenv(Path.cwd() / ".env.local") ← WRONG directory!
5. THEN __main__.py changes directory (line 43) ← TOO LATE
```

### The Issue
- Module-level code runs during `import`, not during function execution
- `__main__.py` imports `main` before changing directories
- Environment variables were loaded from the directory where the command was executed, not the target project

## Solution

### Changes Made
1. **Removed** module-level `load_dotenv()` calls from `src/mcp_ticketer/mcp/server/main.py` (lines 31-46)
2. **Moved** environment loading INTO the `main()` async function (after logger initialization, line 1034)
3. **Added** clarifying comments explaining the timing
4. **Added** debug logging for better visibility

### Execution Flow (After Fix)
```
1. claude-code runs: python -m mcp_ticketer.mcp.server /Users/masa/Projects/claude-mpm
2. Python imports mcp_ticketer.mcp.server.__main__
3. __main__.py imports from .main (line 16) ← Module loads WITHOUT env loading
4. __main__.py changes directory (line 43) ← Sets correct working directory
5. __main__.py calls main() (line 50)
6. main() loads .env.local from Path.cwd() ← CORRECT directory!
```

## Testing

### Test Results
✅ Module import does not trigger environment loading
✅ Correct `.env.local` file is detected in target project directory
✅ Working directory is correctly set before `main()` executes

### Test Commands
```bash
# From mcp-ticketer directory
uv run python -m mcp_ticketer.mcp.server /Users/masa/Projects/claude-mpm

# Should output:
# [MCP Server] Working directory: /Users/masa/Projects/claude-mpm
# [MCP Server] Loaded environment from: /Users/masa/Projects/claude-mpm/.env.local
```

## Files Modified
- `src/mcp_ticketer/mcp/server/main.py`

## Impact
- **Before**: MCP server loaded `.env.local` from command execution directory
- **After**: MCP server loads `.env.local` from target project directory
- **Result**: Environment variables are now correctly loaded for the target project

## Success Criteria
- ✅ Server loads `.env.local` from target project directory, not from where command is executed
- ✅ MCP server successfully initializes when called by claude-code
- ✅ Debug logs show correct `.env.local` path being loaded
- ✅ No environment loading happens during module import

## Technical Details

### Why Module-Level Code is Problematic
Python executes module-level code immediately when the module is imported, before any function calls. This means:
- Module-level code in `main.py` runs when `__main__.py` imports it
- At that point, the working directory hasn't been changed yet
- Environment loading happens from the wrong directory

### Why Function-Level Code Works
By moving the environment loading into the `main()` function:
- Code only runs when `main()` is explicitly called
- `__main__.py` has already changed the working directory
- Environment loading happens from the correct target project directory

## Code Changes

### Before (lines 31-46, module level)
```python
# Load environment variables early (prioritize .env.local)
# Check for .env.local first (takes precedence)
env_local_file = Path.cwd() / ".env.local"
if env_local_file.exists():
    load_dotenv(env_local_file, override=True)
    sys.stderr.write(f"[MCP Server] Loaded environment from: {env_local_file}\n")
else:
    # Fall back to .env
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        sys.stderr.write(f"[MCP Server] Loaded environment from: {env_file}\n")
    else:
        # Try default dotenv loading (searches upward)
        load_dotenv(override=True)
        sys.stderr.write("[MCP Server] Loaded environment from default search path\n")
```

### After (inside main() function, around line 1034)
```python
# Load environment variables AFTER working directory has been set by __main__.py
# This ensures we load .env files from the target project directory, not from where the command is executed
env_local_file = Path.cwd() / ".env.local"
if env_local_file.exists():
    load_dotenv(env_local_file, override=True)
    sys.stderr.write(f"[MCP Server] Loaded environment from: {env_local_file}\n")
    logger.debug(f"Loaded environment from: {env_local_file}")
else:
    # Fall back to .env
    env_file = Path.cwd() / ".env"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        sys.stderr.write(f"[MCP Server] Loaded environment from: {env_file}\n")
        logger.debug(f"Loaded environment from: {env_file}")
    else:
        # Try default dotenv loading (searches upward)
        load_dotenv(override=True)
        sys.stderr.write("[MCP Server] Loaded environment from default search path\n")
        logger.debug("Loaded environment from default search path")
```

## LOC Impact
- **Net LOC**: 0 (moved code, not added)
- **Lines Removed**: 16 (module-level)
- **Lines Added**: 20 (function-level with debug logging)
- **Impact**: +4 LOC (due to additional debug logging)
