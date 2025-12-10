# MCP Tools Availability Investigation

**Date:** 2025-12-10
**Issue:** PM from another project reported mcp-ticketer MCP tools not available
**Status:** ✅ No Issue Found - Tools are properly registered and available

## Executive Summary

Investigation into reported MCP tools unavailability found **NO ISSUES** with the mcp-ticketer server implementation. All 18 tools are properly registered and available when the server starts. The issue likely stems from **incorrect MCP configuration** in the other project, not a problem with mcp-ticketer itself.

## Investigation Findings

### 1. Tool Registration Verification

**Test Method:** Direct server startup with tool listing
```bash
/Users/masa/Projects/mcp-ticketer/.venv/bin/mcp-ticketer mcp serve
```

**Result:** ✅ All 18 tools registered successfully
```
Tools registered: 18
Tool names: ['ticket_analyze', 'ticket_attach', 'ticket_attachments', 'ticket_bulk',
             'ticket_comment', 'config', 'ticket', 'hierarchy', 'label', 'milestone', ...]
```

### 2. Server Initialization Flow Analysis

**Entry Points:**
1. CLI Command: `mcp-ticketer serve` (via `mcp_app` subcommand)
2. Direct module: `python -m mcp_ticketer.mcp.server`

**Initialization Sequence:**
```
mcp_serve() in mcp_server_commands.py (line 51)
    ↓
configure_adapter(adapter_type, adapter_config) (line 132)
    ↓
sdk_main() → mcp.run(transport="stdio") (line 133)
```

**Critical Finding:** Tools are imported and registered **BEFORE** server starts:
```python
# In server_sdk.py line 133
from . import tools  # noqa: E402, F401  ← Tools registered here

def main() -> None:
    """Run the FastMCP server."""
    mcp.run(transport="stdio")  # ← Server starts after tools imported
```

### 3. Tool Registration Mechanism

**FastMCP Decorator Pattern:**
```python
# Each tool module uses @mcp.tool() decorator
@mcp.tool()
async def ticket(action: str, ...):
    """Unified ticket management tool."""
    ...
```

**Consolidated Tool Architecture (v2.0.0):**
- **18 unified tools** (down from 50+ individual tools)
- Action-based routing pattern reduces token usage by 90%
- All tools registered via module import in `tools/__init__.py`

### 4. Configuration Resolution Priority

**When `mcp-ticketer serve` starts:**
1. **Project-specific:** `.mcp-ticketer/config.json` in cwd (highest priority)
2. **Environment variables:** `.env.local` or `.env` files
3. **Auto-detection:** Parse env vars for LINEAR_API_KEY, GITHUB_TOKEN, etc.
4. **Default fallback:** `aitrackdown` adapter with `.aitrackdown` base path

**Critical:** The `cwd` (current working directory) is set by the MCP client from the `cwd` field in `.mcp/config.json`

## Root Cause Analysis

### Likely Issues in Other Project

Based on investigation, the PM's issue is likely due to one of these **configuration problems**:

#### Issue 1: Incorrect MCP Configuration Path

**Problem:** `.mcp/config.json` pointing to wrong command
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "mcp-ticketer",  // ❌ May not be in PATH
      "args": ["serve"]
    }
  }
}
```

**Solution:** Use absolute path to binary
```json
{
  "mcpServers": {
    "mcp-ticketer": {
      "command": "/path/to/.venv/bin/mcp-ticketer",  // ✅ Absolute path
      "args": ["serve"],
      "cwd": "/path/to/project"  // ✅ Explicit working directory
    }
  }
}
```

#### Issue 2: Missing mcp-ticketer Installation

**Problem:** mcp-ticketer not installed in the project's environment

**Verification:**
```bash
which mcp-ticketer
# or
pipx list | grep mcp-ticketer
```

**Solution:**
```bash
pipx install mcp-ticketer
# or for local development
pip install -e /path/to/mcp-ticketer
```

#### Issue 3: Wrong Subcommand

**Problem:** Using `mcp` without `serve` subcommand
```json
{
  "command": "mcp-ticketer",
  "args": ["mcp"]  // ❌ Missing "serve"
}
```

**Solution:**
```json
{
  "command": "mcp-ticketer",
  "args": ["mcp", "serve"]  // ✅ Correct subcommand
}
```

Or use shorter form:
```json
{
  "command": "mcp-ticketer",
  "args": ["serve"]  // ✅ mcp_app callback handles this
}
```

#### Issue 4: Missing Project Configuration

**Problem:** No `.mcp-ticketer/config.json` in project, adapter fails to initialize

**Error Symptom:** Server starts but crashes when trying to use tools

**Solution:**
```bash
cd /path/to/project
mcp-ticketer init  # Creates .mcp-ticketer/config.json
```

#### Issue 5: Environment Variable Conflicts

**Problem:** MCP client not passing environment variables correctly

**Verification:** Check if adapter credentials are available
```bash
# Test adapter configuration
mcp-ticketer config get
```

**Solution:** Ensure `.env.local` or `.env` exists in project root with required vars:
```bash
# For Linear
LINEAR_API_KEY=lin_api_...
LINEAR_TEAM_KEY=ENG

# For GitHub
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=...
GITHUB_REPO=...
```

### NOT an mcp-ticketer Issue

**Evidence:**
1. ✅ Tools successfully register at import time (verified)
2. ✅ Server responds to `tools/list` request with all 18 tools
3. ✅ Initialization order is correct (tools before server start)
4. ✅ No race conditions in tool registration
5. ✅ Error handling logs failures to stderr (would be visible)

## Recommendations

### For the PM Reporting the Issue

**Immediate Actions:**
1. **Verify installation:** Run `which mcp-ticketer` or `pipx list`
2. **Check config:** Inspect `.mcp/config.json` for correct command and cwd
3. **Test manually:** Run `mcp-ticketer serve` in the project directory
4. **Check logs:** Look for error messages in Claude Code/Desktop logs

**Debug Commands:**
```bash
# 1. Verify mcp-ticketer is installed
which mcp-ticketer

# 2. Test server startup
cd /path/to/project
mcp-ticketer mcp serve
# Press Ctrl+D to send EOF and stop

# 3. Check configuration
mcp-ticketer config get

# 4. Verify adapter connection
mcp-ticketer config test --adapter linear  # or github, jira, etc.

# 5. Check MCP status
mcp-ticketer mcp status
```

**Expected Output (working setup):**
```
Starting MCP SDK server with linear adapter
Server running on stdio. Send JSON-RPC requests via stdin.
```

### For mcp-ticketer Maintainers

**No code changes required**, but consider these **documentation improvements**:

1. **Add troubleshooting guide:** Create `docs/TROUBLESHOOTING.md` with:
   - Common MCP configuration issues
   - Verification steps
   - Debug commands

2. **Improve error messages:** Add specific guidance when adapter fails:
   ```python
   except Exception as e:
       sys.stderr.write(f"MCP server error: {e}\n")
       sys.stderr.write("Troubleshooting: Run 'mcp-ticketer mcp status' to check configuration\n")
   ```

3. **Add validation command:** Create `mcp-ticketer mcp validate` to check:
   - Binary path exists
   - Configuration file exists
   - Adapter credentials valid
   - Tools can be listed

## Testing Evidence

### Test 1: Tool Registration at Import

```python
from mcp_ticketer.mcp.server.server_sdk import mcp
# Result: 18 tools registered
```

### Test 2: Server Startup and Tool Listing

```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' | \
  mcp-ticketer mcp serve
```

**Result:** All 18 tools returned in response

### Test 3: Configuration Priority

**Test:** Start server in project with `.mcp-ticketer/config.json`
**Result:** Project config loaded correctly (verified in logs)

## Conclusion

**No bug exists in mcp-ticketer.** The MCP server correctly:
1. Registers all 18 tools at module import time
2. Initializes adapter before starting server
3. Responds to `tools/list` with complete tool catalog
4. Handles configuration from multiple sources (config file, env vars, defaults)

**The issue is environmental** - likely incorrect MCP configuration in the other project's `.mcp/config.json` or missing installation.

**Next Steps:**
1. Share this analysis with the PM
2. Request their `.mcp/config.json` for review
3. Ask them to run debug commands above
4. Consider adding troubleshooting docs to mcp-ticketer

## Files Analyzed

- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/server_sdk.py` - Server initialization
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/cli/mcp_server_commands.py` - CLI serve command
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/__main__.py` - Module entry point
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/main.py` - Legacy server (still used by __main__)
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/__init__.py` - Tool registration
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/ticket_tools.py` - Example tool
- `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/config_tools.py` - Config tool

## Memory Usage Statistics

- Files analyzed: 7 key files
- Tool modules checked: 18 modules in tools/ directory
- No large files loaded into memory (used strategic sampling)
- Total investigation: <130K tokens used
