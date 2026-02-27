# Milestone Enhancement Implementation Plan

## Overview

This plan addresses GitHub issue #76 and adds comprehensive milestone support to mcp-ticketer:

1. **Issue #76**: Add `milestone_id` parameter to ticket create/update operations
2. **Enhancement**: Ensure milestone creation capability is robust across platforms

## Current State Analysis

### ✅ What Works
- Milestone creation via `milestone(action="create")` works for GitHub and Linear
- GitHub ticket creation can assign milestones via `parent_epic` workaround
- Linear ticket creation supports cycles via `metadata["linear"]["cycle_id"]` workaround
- Milestone CRUD operations (create/get/list/update/delete) fully implemented

### ❌ What's Missing
- **No `milestone_id` field on Task model**
- **No `milestone_id` parameter on `ticket()` tool**
- **GitHub ticket updates cannot change milestones**
- **Linear ticket create/update requires metadata workaround instead of direct milestone_id**
- **Jira milestone support completely unimplemented**

## Implementation Strategy

### Phase 1: Core Model & API Enhancement
**Files**: `core/models.py`, `mcp/server/tools/ticket_tools.py`

1. **Add `milestone_id` field to Task model**:
   ```python
   milestone_id: str | None = Field(None, description="Associated milestone ID")
   ```

2. **Update ticket() tool signature**:
   ```python
   async def ticket(
       action: Literal[...],
       milestone_id: str | None = None,  # NEW parameter
       ...
   )
   ```

3. **Update internal ticket functions**:
   - `ticket_create()`: Accept and pass milestone_id
   - `ticket_update()`: Accept milestone_id and add to updates dict

### Phase 2: GitHub Adapter Enhancement
**File**: `adapters/github/adapter.py`

1. **Enhance `create()` method**:
   - Priority: Check `task.milestone_id` first, fallback to `parent_epic`
   - Support both milestone ID (int) and milestone title (string)

2. **Fix `update()` method**:
   - Add milestone update support: `update_data["milestone"] = int(milestone_id)`
   - Handle milestone removal: `milestone_id = None` → `update_data["milestone"] = None`

### Phase 3: Linear Adapter Enhancement
**Files**: `adapters/linear/adapter.py`, `adapters/linear/mappers.py`

1. **Enhance `_create_task()` method**:
   - Priority: Check `task.milestone_id` first, fallback to `metadata["linear"]["cycle_id"]`
   - Add direct `issue_input["cycleId"] = milestone_id`

2. **Fix `update()` method**:
   - Handle `updates["milestone_id"]` → `update_input["cycleId"]`
   - Support cycle removal and cycle change

3. **Update mappers** (optional optimization):
   - `build_linear_issue_input()`: Direct milestone_id handling
   - `build_linear_issue_update_input()`: Direct milestone_id handling

### Phase 4: Validation & Testing
**Files**: `tests/unit/tools/test_ticket_tools.py`, adapter tests

1. **Unit tests for ticket tool**:
   - Test milestone_id parameter on create/update
   - Test None handling (milestone removal)

2. **Integration tests for adapters**:
   - GitHub: Test milestone assignment and updates
   - Linear: Test cycle assignment and updates
   - Validation of both ID and title formats

## Platform-Specific Considerations

### GitHub
- **Milestones**: Native concept, REST API `/repos/{owner}/{repo}/milestones`
- **ID format**: Integer milestone number (e.g., `1`, `2`, `3`)
- **Title support**: Can resolve milestone by title if ID fails
- **API calls**:
  - Create: `issue_data["milestone"] = int(milestone_id)`
  - Update: `update_data["milestone"] = int(milestone_id)`
  - Remove: `update_data["milestone"] = None`

### Linear
- **Milestones**: Called "Cycles", GraphQL API
- **ID format**: UUID string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`)
- **API calls**:
  - Create: `issue_input["cycleId"] = milestone_id`
  - Update: `update_input["cycleId"] = milestone_id`
  - Remove: `update_input["cycleId"] = None`

### Jira
- **Milestones**: Could map to "Fix Version" or "Sprint"
- **Status**: Currently NotImplemented (planned for v2.1.0)
- **Action**: Leave as-is, add TODO comments for future implementation

## API Examples After Implementation

### Creating a ticket with milestone
```python
# Using milestone ID
await ticket(
    action="create",
    title="Fix authentication bug",
    milestone_id="12"  # GitHub milestone number or Linear cycle UUID
)

# Using milestone title (GitHub fallback)
await ticket(
    action="create",
    title="Fix authentication bug",
    milestone_id="v2.4.0 Release"  # Will resolve to milestone ID
)
```

### Updating ticket milestone
```python
# Assign to milestone
await ticket(
    action="update",
    ticket_id="123",
    milestone_id="12"
)

# Remove from milestone
await ticket(
    action="update",
    ticket_id="123",
    milestone_id=None
)
```

### Creating milestones (already works)
```python
# GitHub milestone
await milestone(
    action="create",
    name="v2.4.0 Release",
    target_date="2024-03-15",
    description="Bug fixes and performance improvements"
)

# Linear cycle
await milestone(
    action="create",
    name="Sprint 23",
    target_date="2024-03-15"
)
```

## Implementation Priority

1. **High Priority** (Addresses Issue #76):
   - Phase 1: Core model and API changes
   - Phase 2: GitHub adapter milestone updates
   - Phase 3: Linear adapter direct milestone_id

2. **Medium Priority**:
   - Phase 4: Comprehensive testing
   - Documentation updates

3. **Low Priority** (Future):
   - Jira milestone implementation (v2.1.0)

## Backward Compatibility

- **`parent_epic` milestone assignment**: Keep working for GitHub
- **`metadata["linear"]["cycle_id"]`**: Keep working for Linear
- **New `milestone_id`**: Takes priority when both are provided
- **No breaking changes**: All existing workflows continue to work

## Success Criteria

✅ **Issue #76 Resolution**:
- `ticket(action="create", milestone_id="123")` works on GitHub/Linear
- `ticket(action="update", milestone_id="123")` works on GitHub/Linear
- `ticket(action="update", milestone_id=None)` removes milestones

✅ **Milestone Creation**:
- `milestone(action="create")` continues working robustly

✅ **Platform Compatibility**:
- GitHub: Integer milestone numbers + title fallback
- Linear: UUID cycle IDs
- Jira: Graceful NotImplemented (no regression)

✅ **Testing**:
- Unit tests cover new parameters
- Integration tests validate real adapter behavior
- Backward compatibility preserved