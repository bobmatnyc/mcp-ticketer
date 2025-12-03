# Migration Guide: v2.0.1 → v2.0.2

## Overview

Version 2.0.2 is a **patch release** with bug fixes and performance improvements. All changes are **backward compatible** with no breaking changes.

**Release Type**: Patch
**Breaking Changes**: None
**Migration Complexity**: Low (automatic fixes + optional opt-ins)

---

## What's New

### Automatic Fixes (No Action Required)

These issues are now resolved automatically:

✅ **Linear State Transitions** (1M-552)
   - Fixed: State transitions work for all workflow configurations
   - Impact: READY, TESTED, WAITING, BLOCKED states now work correctly
   - Action: None - automatic semantic name matching implemented

✅ **Epic Listing Pagination** (1M-553)
   - Fixed: Epic listing operations no longer fail with GraphQL errors
   - Impact: Teams with large numbers of epics can now list all projects
   - Action: None - pagination parameters added to GraphQL query

✅ **MCP Installer Reliability** (1M-579)
   - Fixed: Installer detects installation method and configures appropriately
   - Impact: All installation methods (pipx, uv, pip, poetry) now work reliably
   - Action: None - automatic PATH detection with fallback

### Optional Performance Improvements

#### Compact List Output (Opt-in Feature)

**What**: New `compact=True` parameter reduces token usage by 77.5%

**Why**: Enables AI agents to work with 4x more tickets within the same token budget

**Example**:
```python
# Old way (still works)
tickets = adapter.list(limit=20)  # Full format

# New way (opt-in for token savings)
tickets = adapter.list(limit=20, compact=True)  # Compact format
```

**Performance**:
- 50 items full format: 31,082 characters (~7,770 tokens)
- 50 items compact format: 6,982 characters (~1,745 tokens)
- Token reduction: 77.5%

**When to Use**:
- ✅ AI agent applications with token limits
- ✅ Bulk ticket processing workflows
- ✅ Dashboard/overview displays
- ❌ Use full format when you need complete ticket details

**Backward Compatibility**: Default is `compact=False`, so existing code works unchanged.

---

## Breaking Changes

**None** - All changes are backward compatible.

---

## Upgrade Instructions

### Step 1: Upgrade Package

```bash
# Via pipx (recommended)
pipx upgrade mcp-ticketer

# Via uv
uv tool upgrade mcp-ticketer

# Via pip
pip install --upgrade mcp-ticketer
```

### Step 2: Verify Installation

```bash
mcp-ticketer --version
# Should show: 2.0.2
```

### Step 3: Test (Optional)

```bash
# Test basic functionality
mcp-ticketer config get

# Test Linear adapter (if configured)
mcp-ticketer list --limit 5
```

---

## Optional: Enable Compact Mode

If you want to benefit from the 77.5% token reduction, update your code to use compact mode:

### Python API

```python
from mcp_ticketer import TicketManager

manager = TicketManager(adapter="linear")

# Enable compact mode for list operations
tickets = manager.list(limit=20, compact=True)

# Enable compact mode for epic listing
epics = manager.list_epics(limit=10, compact=True)
```

### MCP Tools (AI Agents)

Compact mode is automatically available in MCP tools:

```json
{
  "tool": "ticket",
  "action": "list",
  "limit": 20,
  "compact": true
}
```

---

## Optional: Configure PATH (For Better UX)

While not required, adding `mcp-ticketer` to your PATH provides better Claude Desktop integration:

### For pipx Users

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

### Verify PATH

```bash
which mcp-ticketer
# Should show: /Users/username/.local/bin/mcp-ticketer (or similar)
```

**Note**: Without PATH configuration, mcp-ticketer still works using legacy mode with full paths.

---

## What Changed Under the Hood

### State Transition Logic (1M-552)
- Added semantic name matching for Linear workflow states
- Fallback to type-based matching for backward compatibility
- No configuration changes required

### GraphQL Queries (1M-553)
- Added pagination parameters to `LIST_PROJECTS_QUERY`
- Supports cursor-based iteration for large result sets
- No API changes for end users

### Compact Output Format (1M-554)
- New `to_compact_dict()` method in `LinearMappers`
- Reduces output to essential fields: id, title, state, priority
- Full format remains default for backward compatibility

### Installer PATH Detection (1M-579)
- Added `is_mcp_ticketer_in_path()` validation
- Automatic fallback to legacy mode when PATH not configured
- Decision matrix ensures reliable operation across all installation methods

---

## Rollback Instructions

If you need to rollback to v2.0.1:

```bash
# Via pipx
pipx install mcp-ticketer==2.0.1

# Via uv
uv tool install mcp-ticketer==2.0.1

# Via pip
pip install mcp-ticketer==2.0.1
```

**Note**: Rollback should not be necessary - all changes are backward compatible and well-tested (346 tests passing).

---

## Support

- **GitHub Issues**: https://github.com/mcp-ticketer/mcp-ticketer/issues
- **Linear Project**: https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues
- **Documentation**: https://mcp-ticketer.readthedocs.io

---

## Related Documentation

- [CHANGELOG.md](../CHANGELOG.md) - Detailed technical changes
- [RELEASE-v2.0.2.md](RELEASE-v2.0.2.md) - Release notes summary
- [README.md](../README.md) - General documentation
