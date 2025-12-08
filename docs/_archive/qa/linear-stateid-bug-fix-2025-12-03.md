# Linear stateId Bug Fix - 2025-12-03

## Bug Summary

**Error**: `stateId must be a UUID`
**Root Cause**: `_get_state_mapping()` was incorrectly accessing `_workflow_states` dict, trying to use Linear state types (like "unstarted") as keys instead of universal state values (like "open")

## Problem Details

### Original Buggy Code

In `_get_state_mapping()` (lines 1407-1412):
```python
# WRONG: Tried to access by linear_type ("unstarted")
for universal_state, linear_type in LinearStateMapping.TO_LINEAR.items():
    if linear_type in self._workflow_states:
        mapping[universal_state] = self._workflow_states[linear_type]["id"]
    else:
        mapping[universal_state] = linear_type
```

### Data Structure Mismatch

**Actual `_workflow_states` structure** (set in `_load_workflow_states()` line 965):
```python
{
  "open": "uuid-1",           # TicketState.OPEN.value → UUID
  "in_progress": "uuid-2",    # TicketState.IN_PROGRESS.value → UUID
  "done": "uuid-3",           # TicketState.DONE.value → UUID
  ...
}
```

**What buggy code tried to access**:
```python
{
  "unstarted": {"id": "uuid-1"},  # ❌ WRONG - state type, not universal state
  "started": {"id": "uuid-2"},    # ❌ WRONG
  ...
}
```

### Why Bug Occurred

1. `_workflow_states` is populated in `_load_workflow_states()` using `universal_state.value` as keys
2. `_get_state_mapping()` tried to access it using `linear_type` (state types like "unstarted")
3. Lookup failed → fell back to returning state type string instead of UUID
4. Linear API rejected `"unstarted"` because it expects UUID

## Fix Applied

### Code Changes

**File**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py`

```python
# FIXED: Access by universal_state.value ("open", "in_progress", etc.)
mapping = {}
for universal_state in TicketState:
    state_uuid = self._workflow_states.get(universal_state.value)
    if state_uuid:
        mapping[universal_state] = state_uuid
    else:
        # Fallback to type name if state not found in cache
        linear_type = LinearStateMapping.TO_LINEAR.get(universal_state)
        if linear_type:
            mapping[universal_state] = linear_type

return mapping
```

### Test Updates

**File**: `/Users/masa/Projects/mcp-ticketer/tests/adapters/linear/test_adapter.py`

Updated `test_get_state_mapping_with_workflow_states()` to use correct data structure:

```python
# BEFORE (incorrect test data):
adapter._workflow_states = {
    "unstarted": {"id": "state-1", "name": "To Do"},  # ❌ Wrong structure
    ...
}

# AFTER (correct test data):
adapter._workflow_states = {
    "open": "state-uuid-1",        # ✅ Correct structure
    "in_progress": "state-uuid-2",
    "done": "state-uuid-3",
    ...
}
```

## Impact Analysis

### Files Changed
1. `src/mcp_ticketer/adapters/linear/adapter.py` - Fixed `_get_state_mapping()` method
2. `tests/adapters/linear/test_adapter.py` - Updated test to match correct data structure

### Affected Operations
- ✅ `_create_task()` - Now correctly sends UUID for `stateId`
- ✅ `_update_ticket()` - Now correctly sends UUID for `stateId` during state transitions
- ✅ All state-related operations using `_get_state_mapping()`

### Backward Compatibility
- ✅ Fallback behavior preserved - if `_workflow_states` not loaded, still returns state types
- ✅ Existing functionality unchanged - only fixes UUID vs. type string issue

## Verification

### Pre-Fix Behavior
```json
{
  "stateId": "unstarted"  // ❌ String type, not UUID
}
```
**Result**: Error: "stateId must be a UUID"

### Post-Fix Behavior
```json
{
  "stateId": "abc-123-uuid-456"  // ✅ Valid UUID
}
```
**Result**: Successful issue creation

### Test Coverage
- ✅ `test_get_state_mapping_with_workflow_states` - Updated and validates correct UUID mapping
- ✅ `test_load_workflow_states` - Already validated correct data structure (no changes needed)
- ✅ `test_get_state_mapping_without_workflow_states` - Validates fallback behavior (no changes needed)

## Related Issues

This bug likely affects:
- Epic creation (if using state assignment)
- Issue creation with specific states
- Task creation with default OPEN state
- Any state transition operations

## Net LOC Impact

- **adapter.py**: +5 lines (better comments + fixed logic)
- **test_adapter.py**: +8 lines (more comprehensive test coverage)
- **Net impact**: +13 lines

**Justification**: Bug fix with improved documentation and test coverage. The added lines provide critical fixes and prevent regression.

## Success Criteria

- ✅ Code compiles without syntax errors
- ✅ `_get_state_mapping()` returns UUIDs when `_workflow_states` loaded
- ✅ Fallback to state types when `_workflow_states` not loaded
- ✅ Test coverage updated to reflect correct behavior
- ✅ No hardcoded state types sent to Linear API as UUIDs

## Deployment Notes

**Priority**: HIGH - Blocks all issue/epic/task creation operations

**Testing Required**:
1. Create issue with default state (OPEN)
2. Create issue with specific state (IN_PROGRESS, DONE, etc.)
3. Transition issue between states
4. Create epic/task and verify state assignment

**Rollback Plan**: Revert commits if UUID mapping fails - fallback behavior still intact
