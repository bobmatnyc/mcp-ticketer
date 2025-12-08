# Asana Priority and Status Testing - Comprehensive Report

**Test Date**: 2025-11-15
**Target Ticket**: 1211956047964390
**Project**: 1211955750346310
**URL**: https://app.asana.com/0/1211955750346310/1211956047964390

---

## Executive Summary

**CRITICAL FINDINGS:**

1. **Priority Setting Works** - Via direct API calls, custom fields can be set successfully
2. **Status Custom Field Works** - Via direct API calls, Status field can be updated
3. **Adapter Has Bugs** - The `AsanaAdapter.update()` method does NOT handle custom fields properly
4. **Mapping is Incomplete** - Priority and Status updates via adapter are ignored

**Current Status of Ticket:**
- **Priority**: High (successfully set via direct API)
- **State**: Open (completed=false)
- **Status Custom Field**: "Off track" (successfully set via direct API)

---

## Phase 1: Custom Fields Investigation

### Project Custom Fields Discovered

The Asana project has TWO custom fields configured:

#### 1. Priority Field
- **Name**: Priority
- **Type**: enum
- **GID**: 1211955750346315
- **Options**:
  - Low (GID: 1211955750346316)
  - Medium (GID: 1211955750346317)
  - High (GID: 1211955750346318)

#### 2. Status Field
- **Name**: Status
- **Type**: enum
- **GID**: 1211955750346320
- **Options**:
  - On track (GID: 1211955750346321)
  - At risk (GID: 1211955750346322)
  - Off track (GID: 1211955750346323)

### Workspace Custom Fields
- No additional workspace-level custom fields found
- All custom fields are project-specific

---

## Phase 2: Priority Setting Tests

### TEST 1: Update via adapter.update() ❌ FAILED
```python
updated = await adapter.update(TASK_ID, {"priority": "high"})
print(f"Result: {updated.priority}")  # Output: medium
```

**Result**: FAILED
- Priority parameter is IGNORED by adapter.update()
- No custom field is updated
- Priority remains at previous value (medium)

**Root Cause**: The `AsanaAdapter.update()` method (line 499-566 in adapter.py) does NOT handle the `priority` parameter. It only handles:
- title
- description
- state (mapped to completed)
- assignee
- due_on/due_at
- tags

### TEST 2: Direct API with Custom Fields ✅ SUCCESS
```python
result = await adapter.client.put(
    f"/tasks/{TASK_ID}",
    {
        "custom_fields": {
            "1211955750346315": "1211955750346318"  # Priority: High
        }
    }
)
```

**Result**: SUCCESS
- Priority custom field successfully updated to "High"
- Verified in raw API response
- Change is permanent and visible in Asana UI

**Evidence**:
```json
{
  "enum_value": {
    "gid": "1211955750346318",
    "name": "High",
    "color": "purple"
  },
  "display_value": "High"
}
```

### TEST 3: Multiple Priority Values ❌ ADAPTER BUG
```python
for priority_val in ["low", "medium", "high", "critical"]:
    updated = await adapter.update(TASK_ID, {"priority": priority_val})
    print(f"Set '{priority_val}': result = {updated.priority}")
```

**Result**: ALL FAILED
- All calls returned "high" (the previously set value via direct API)
- Adapter.update() does not modify custom fields
- Reading works (mapper correctly reads custom fields)
- Writing is broken (update method ignores priority)

---

## Phase 3: Status Setting Tests

### TEST 1: Completion Boolean ✅ SUCCESS
```python
# Mark incomplete
await adapter.client.put(f"/tasks/{TASK_ID}", {"completed": False})
# Verify: completed = False ✅

# Mark complete
await adapter.client.put(f"/tasks/{TASK_ID}", {"completed": True})
# Verify: completed = True ✅

# Mark incomplete again
await adapter.client.put(f"/tasks/{TASK_ID}", {"completed": False})
# Verify: completed = False ✅
```

**Result**: SUCCESS
- Asana's `completed` boolean works perfectly
- This controls DONE/OPEN states
- No issues with completion toggling

### TEST 2: Status Custom Field ✅ SUCCESS
```python
status_options = ["On track", "At risk", "Off track"]
for status_option in status_options:
    await adapter.client.put(
        f"/tasks/{TASK_ID}",
        {
            "custom_fields": {
                "1211955750346320": status_option_gid
            }
        }
    )
```

**Result**: SUCCESS
- All three Status options successfully set
- Custom field updates work via direct API
- Final state: "Off track" (GID: 1211955750346323)

**Evidence**:
```json
{
  "enum_value": {
    "gid": "1211955750346323",
    "name": "Off track",
    "color": "red"
  },
  "display_value": "Off track"
}
```

### TEST 3: Adapter transition_state() ⚠️ PARTIAL SUCCESS
```python
states = [TicketState.IN_PROGRESS, TicketState.READY, TicketState.DONE, TicketState.OPEN]
for state in states:
    updated = await adapter.transition_state(TASK_ID, state)
    print(f"Target: {state.value}, Result: {updated.state}")
```

**Results**:
- IN_PROGRESS → OPEN ❌ (should stay IN_PROGRESS)
- READY → OPEN ❌ (should stay READY)
- DONE → DONE ✅ (correctly sets completed=true)
- OPEN → OPEN ✅ (correctly sets completed=false)

**Root Cause**:
- Asana only has `completed` boolean (true/false)
- Adapter maps DONE/CLOSED → true, everything else → false
- Status custom field is NOT USED by adapter for state transitions
- All non-completed states map to OPEN when read back

---

## Phase 4: Root Cause Analysis

### Issue 1: Priority Setting Ignored

**Location**: `/src/mcp_ticketer/adapters/asana/adapter.py:499-566`

**Problem**: The `update()` method does not handle `priority` parameter.

**Current Code**:
```python
async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
    update_data: dict[str, Any] = {}

    if "title" in updates:
        update_data["name"] = updates["title"]

    if "description" in updates:
        update_data["notes"] = updates["description"]

    if "state" in updates:
        state = updates["state"]
        # ... maps to completed boolean
        update_data["completed"] = map_state_to_asana(state)

    # ⚠️ NO HANDLING OF "priority" parameter!
    # Custom fields are never set!
```

**Missing Logic**:
```python
if "priority" in updates:
    # Need to:
    # 1. Map priority to Asana priority value
    # 2. Get priority field GID (stored in self._priority_field_gid)
    # 3. Resolve priority option GID from field
    # 4. Update custom_fields in update_data
    pass  # Currently not implemented
```

### Issue 2: Status Custom Field Ignored

**Location**: Same as above

**Problem**: The adapter never uses the Status custom field for state transitions.

**Current Behavior**:
- State transitions only modify `completed` boolean
- Status custom field is read during mapping but never written
- Fine-grained states (IN_PROGRESS, READY, TESTED) are lost

**Expected Behavior**:
- Should use Status custom field if it exists
- Map universal states to Status field options
- Fall back to completed boolean for DONE/OPEN

### Issue 3: Custom Field Resolution Missing

**Location**: `/src/mcp_ticketer/adapters/asana/adapter.py:191-211`

**Current Implementation**:
```python
async def _load_custom_fields(self) -> None:
    """Load custom fields for the workspace (specifically Priority field)."""
    # Only loads workspace-level custom fields
    # Does NOT load project-specific custom fields
    # Only stores _priority_field_gid (workspace level)
```

**Problem**:
- Priority and Status fields in the test project are PROJECT-LEVEL
- Adapter only looks for WORKSPACE-LEVEL custom fields
- `self._priority_field_gid` is None for project-level fields
- Even if it found the field, update() doesn't use it

---

## Recommendations

### CRITICAL: Fix Priority Setting

**Priority**: HIGH
**Complexity**: MEDIUM
**Impact**: Priority setting currently doesn't work at all

**Required Changes**:

1. **Load project-specific custom fields**:
```python
async def _load_project_custom_fields(self, project_gid: str) -> dict[str, str]:
    """Load custom fields for a specific project.

    Returns:
        Dict mapping field names (lowercase) to field GIDs
    """
    project = await self.client.get(
        f"/projects/{project_gid}",
        params={"opt_fields": "custom_field_settings.custom_field"}
    )

    field_map = {}
    for setting in project.get('custom_field_settings', []):
        field = setting.get('custom_field', {})
        field_name = field.get('name', '').lower()
        field_map[field_name] = field

    return field_map
```

2. **Add priority handling to update()**:
```python
# In update() method, add:
if "priority" in updates:
    priority = updates["priority"]
    if isinstance(priority, str):
        from ...core.models import Priority
        priority = Priority(priority)

    # Get task's projects to load custom fields
    task = await self.client.get(f"/tasks/{ticket_id}")
    projects = task.get("projects", [])

    if projects:
        # Load custom fields for first project
        project_fields = await self._load_project_custom_fields(projects[0]["gid"])

        if "priority" in project_fields:
            priority_field = project_fields["priority"]

            # Find matching option
            priority_name = map_priority_to_asana(priority)
            for option in priority_field.get("enum_options", []):
                if option["name"].lower() == priority_name.lower():
                    if "custom_fields" not in update_data:
                        update_data["custom_fields"] = {}
                    update_data["custom_fields"][priority_field["gid"]] = option["gid"]
                    break
```

### MEDIUM: Enhanced Status Handling

**Priority**: MEDIUM
**Complexity**: MEDIUM
**Impact**: Would enable fine-grained state tracking

**Required Changes**:

1. **Detect Status custom field**:
```python
# In _load_project_custom_fields or similar
self._status_field_gid = None
for field_name, field in project_fields.items():
    if "status" in field_name:
        self._status_field_gid = field["gid"]
        self._status_field_options = {
            opt["name"].lower(): opt["gid"]
            for opt in field.get("enum_options", [])
        }
```

2. **Map states to Status options**:
```python
# In update() for state transitions:
if "state" in updates and self._status_field_gid:
    state = updates["state"]
    # Try to map to Status field first
    status_mapping = {
        TicketState.IN_PROGRESS: "at risk",  # or custom mapping
        TicketState.READY: "on track",
        TicketState.DONE: None,  # Use completed=true
    }

    status_name = status_mapping.get(state)
    if status_name and status_name in self._status_field_options:
        if "custom_fields" not in update_data:
            update_data["custom_fields"] = {}
        update_data["custom_fields"][self._status_field_gid] = \
            self._status_field_options[status_name]
```

### LOW: Improve State Mapping

**Priority**: LOW
**Complexity**: LOW
**Impact**: Better state preservation on read

**Required Changes**:

1. **Use Status field during read**:
```python
# In map_asana_task_to_task (mappers.py):
# Check Status custom field first
custom_state_name = None
for field in custom_fields:
    if field.get("name", "").lower() == "status" and field.get("enum_value"):
        custom_state_name = field["enum_value"].get("name")
        break

# Pass to map_state_from_asana
state = map_state_from_asana(completed, custom_state_name)
```

2. **This would allow reading states like**:
- "At risk" → IN_PROGRESS
- "On track" → READY
- etc.

---

## Verification in Asana UI

After running all tests, the ticket at https://app.asana.com/0/1211955750346310/1211956047964390 should show:

✅ **Priority**: High (purple indicator)
✅ **Status**: Off track (red indicator)
✅ **Completed**: False (task is open)

**Screenshot Evidence Needed**:
- User should verify Priority field shows "High" in Asana UI
- User should verify Status field shows "Off track" in Asana UI
- User should verify task is not marked as complete

---

## Test Results Summary

| Test | Method | Result | Evidence |
|------|--------|--------|----------|
| Custom Fields Discovery | API | ✅ SUCCESS | Found Priority and Status fields |
| Priority via adapter.update() | Adapter | ❌ FAILED | Parameter ignored |
| Priority via direct API | API | ✅ SUCCESS | Custom field updated |
| Status completion toggle | API | ✅ SUCCESS | Boolean works |
| Status custom field | API | ✅ SUCCESS | Field updated |
| State transitions (DONE) | Adapter | ✅ SUCCESS | Completed=true |
| State transitions (others) | Adapter | ⚠️ PARTIAL | Maps to OPEN |

---

## Code Locations

**Files Requiring Changes**:

1. `/src/mcp_ticketer/adapters/asana/adapter.py`
   - Line 191-211: `_load_custom_fields()` - needs project-level support
   - Line 499-566: `update()` - needs priority/status handling

2. `/src/mcp_ticketer/adapters/asana/mappers.py`
   - Line 74-148: `map_asana_task_to_task()` - could use Status field for better state mapping

3. `/src/mcp_ticketer/adapters/asana/types.py`
   - Line 111-141: `map_state_from_asana()` - already supports custom_state parameter, just needs to be called

---

## Conclusion

**The Asana API works perfectly**. Priority and Status can be set via custom fields using direct API calls.

**The AsanaAdapter has bugs**:
1. Priority updates are completely ignored
2. Status custom fields are not used for state transitions
3. Custom field resolution only checks workspace level, not project level

**Next Steps**:
1. Fix `update()` method to handle priority parameter
2. Load project-level custom fields during initialization
3. Optionally enhance state mapping to use Status custom field
4. Add tests for custom field updates

**Workaround**:
Until adapter is fixed, users can:
- Set priority/status via direct Asana API calls
- Read priority/status correctly (mapper works)
- Use completed boolean for DONE/OPEN states
