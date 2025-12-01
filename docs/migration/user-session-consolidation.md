# User Session Tool Consolidation - Migration Guide

**Sprint**: Phase 2 Sprint 2.2
**Date**: 2025-12-01
**Status**: Completed
**Ticket**: [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

## Overview

This guide covers the consolidation of `get_my_tickets` and `get_session_info` into a single unified `user_session()` tool, following the established consolidation pattern from Sprint 2.1.

## What Changed

### Before (Deprecated in v1.5.0, removed in v2.0.0)

Two separate tools:
```python
# Get user's tickets
result = await get_my_tickets(state="open", limit=20)

# Get session information
result = await get_session_info()
```

### After (Available in v1.5.0+)

Single unified tool with action parameter:
```python
# Get user's tickets
result = await user_session(
    action="get_my_tickets",
    state="open",
    limit=20
)

# Get session information
result = await user_session(
    action="get_session_info"
)
```

## Token Savings

**Analysis Results**:
- **Before**: 479 tokens (2 separate tools)
- **After**: 388 tokens (1 unified tool)
- **Savings**: 91 tokens (19.0% reduction)
- **Tool Count**: Reduced by 50% (2 → 1)

## Migration Examples

### Example 1: Get My Tickets

**Before**:
```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import get_my_tickets

# Simple query
tickets = await get_my_tickets(state="open", limit=10)

# With project filter
tickets = await get_my_tickets(
    state="in_progress",
    project_id="PROJ-123",
    limit=20
)
```

**After**:
```python
from mcp_ticketer.mcp.server.tools.session_tools import user_session

# Simple query
tickets = await user_session(
    action="get_my_tickets",
    state="open",
    limit=10
)

# With project filter
tickets = await user_session(
    action="get_my_tickets",
    state="in_progress",
    project_id="PROJ-123",
    limit=20
)
```

### Example 2: Get Session Info

**Before**:
```python
from mcp_ticketer.mcp.server.tools.session_tools import get_session_info

session = await get_session_info()
print(f"Session ID: {session['session_id']}")
print(f"Current Ticket: {session['current_ticket']}")
```

**After**:
```python
from mcp_ticketer.mcp.server.tools.session_tools import user_session

session = await user_session(action="get_session_info")
print(f"Session ID: {session['session_id']}")
print(f"Current Ticket: {session['current_ticket']}")
```

### Example 3: Error Handling

**Before**:
```python
try:
    tickets = await get_my_tickets(state="open")
    if tickets["status"] == "error":
        print(f"Error: {tickets['error']}")
except Exception as e:
    print(f"Exception: {e}")
```

**After**:
```python
try:
    tickets = await user_session(action="get_my_tickets", state="open")
    if tickets["status"] == "error":
        print(f"Error: {tickets['error']}")
except Exception as e:
    print(f"Exception: {e}")
```

## Backward Compatibility

### Deprecation Timeline

- **v1.5.0**: `user_session()` introduced, old tools deprecated with warnings
- **v1.6.0 - v1.9.x**: Old tools continue to work with deprecation warnings
- **v2.0.0**: Old tools removed, only `user_session()` available

### Current Behavior (v1.5.0+)

Both old and new tools work, but old tools emit deprecation warnings:

```python
# This still works but emits warning
result = await get_my_tickets(state="open")
# DeprecationWarning: get_my_tickets is deprecated.
# Use user_session(action='get_my_tickets', ...) instead.
# This function will be removed in version 2.0.0.
```

### Suppressing Warnings (Temporary)

If you need to suppress warnings during migration:

```python
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    result = await get_my_tickets(state="open")
```

## API Reference

### user_session()

```python
async def user_session(
    action: Literal["get_my_tickets", "get_session_info"],
    state: str | None = None,
    project_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]
```

**Parameters**:
- `action` (required): Operation to perform
  - `"get_my_tickets"`: Get tickets assigned to default user
  - `"get_session_info"`: Get current session information
- `state` (optional): Filter tickets by state (for `get_my_tickets` only)
- `project_id` (optional): Filter tickets by project (for `get_my_tickets` only)
- `limit` (optional): Maximum tickets to return (default: 10, max: 100, for `get_my_tickets` only)

**Returns**:
- Operation-specific response dictionary
- Always includes `"status"` field (`"completed"` or `"error"`)

**Raises**:
- Returns error response (not exception) for invalid actions

### Action: get_my_tickets

**Response Format**:
```json
{
  "status": "completed",
  "adapter": "linear",
  "adapter_name": "Linear",
  "tickets": [
    {
      "id": "TEST-100",
      "title": "Bug Fix",
      "state": "open",
      "priority": "high",
      ...
    }
  ],
  "count": 1,
  "user": "test@example.com",
  "state_filter": "open",
  "limit": 10
}
```

**Requirements**:
- Requires `default_user` configured (use `config_set_default_user()`)
- Requires `project_id` parameter OR `default_project` configured

### Action: get_session_info

**Response Format**:
```json
{
  "success": true,
  "session_id": "abc-123",
  "current_ticket": "PROJ-123",
  "opted_out": false,
  "last_activity": "2025-01-19T20:00:00",
  "session_timeout_minutes": 30
}
```

## Testing

### Test Coverage

**File**: `tests/mcp/test_unified_user_session.py`

**Test Statistics**:
- **Total Tests**: 14
- **Pass Rate**: 100%
- **Test Classes**: 4
  - `TestUnifiedUserSession`: 8 tests
  - `TestDeprecationWarnings`: 2 tests
  - `TestBackwardCompatibility`: 2 tests
  - `TestIntegration`: 2 tests

**Test Coverage**:
- ✅ Unified tool with `get_my_tickets` action
- ✅ Unified tool with `get_session_info` action
- ✅ Invalid action handling
- ✅ Parameter forwarding (state, project_id, limit)
- ✅ Limit validation and clamping
- ✅ Configuration requirements (default_user, default_project)
- ✅ Error handling for both actions
- ✅ Deprecation warnings on original tools
- ✅ Backward compatibility maintained
- ✅ Integration workflows

### Running Tests

```bash
# Run all user_session tests
pytest tests/mcp/test_unified_user_session.py -v

# Run specific test class
pytest tests/mcp/test_unified_user_session.py::TestUnifiedUserSession -v

# Run with deprecation warnings visible
pytest tests/mcp/test_unified_user_session.py -v -W default::DeprecationWarning
```

## Implementation Details

### Files Modified

1. **`src/mcp_ticketer/mcp/server/tools/session_tools.py`**
   - Added unified `user_session()` tool
   - Added deprecation warning to `get_session_info()`
   - Updated module docstring

2. **`src/mcp_ticketer/mcp/server/tools/user_ticket_tools.py`**
   - Added deprecation warning to `get_my_tickets()`
   - Updated module docstring

3. **`tests/mcp/test_unified_user_session.py`** (NEW)
   - Comprehensive test suite with 14 tests

### Line Counts

```
session_tools.py:           278 lines (+76 for unified tool)
user_ticket_tools.py:       491 lines (+26 for deprecation)
test_unified_user_session:  423 lines (new file)
```

### Design Decisions

1. **Routing Pattern**: Follows exact pattern from `ticket_bulk()` consolidation
2. **Error Handling**: Returns error dict instead of raising exceptions
3. **Parameter Forwarding**: All parameters forwarded to underlying implementations
4. **Deprecation Strategy**: Warnings with version info, 2-release deprecation cycle
5. **Testing Strategy**: Comprehensive coverage including edge cases and integration

## Benefits

### For Users
- **Simplified API**: Single entry point for user/session operations
- **Better Discoverability**: Easier to find related functionality
- **Consistent Interface**: Matches pattern from other consolidated tools
- **Backward Compatible**: No breaking changes until v2.0.0

### For System
- **Token Efficiency**: 19.0% reduction in tool definition tokens
- **Reduced Complexity**: 50% fewer tools to maintain
- **Consistent Pattern**: Follows established consolidation approach
- **Better Organization**: Related functionality grouped together

## Troubleshooting

### Common Issues

**Issue**: Deprecation warning when using old tools
```
DeprecationWarning: get_my_tickets is deprecated...
```
**Solution**: Migrate to `user_session(action="get_my_tickets", ...)`

---

**Issue**: Invalid action error
```json
{"status": "error", "error": "Invalid action 'get_tickets'..."}
```
**Solution**: Use valid action: `"get_my_tickets"` or `"get_session_info"`

---

**Issue**: Missing project configuration
```json
{"status": "error", "error": "project_id required..."}
```
**Solution**: Provide `project_id` parameter or configure default:
```python
await config_set_default_project(project_id="YOUR-PROJECT")
```

## Support

For issues or questions:
- **Documentation**: See `docs/mcp-api-reference.md`
- **Tests**: Reference `tests/mcp/test_unified_user_session.py`
- **Ticket**: [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

## Related Documentation

- [MCP API Reference](../mcp-api-reference.md)
- [Bulk Operations Consolidation](./bulk-operations-consolidation.md) (Sprint 2.1)
- [Phase 2 Consolidation Plan](../architecture/phase-2-consolidation.md)
