# Linear Adapter: Milestone Support (Cycles)

**Implementation:** Ticket 1M-607 Phase 2 - Linear Adapter Integration
**Date:** 2025-12-04
**Status:** ✅ Implemented

## Overview

The Linear adapter implements milestone support using Linear's native **Cycles** feature. Cycles are time-boxed periods (similar to sprints) that group related issues together with start and end dates, making them a natural fit for the universal Milestone model.

## Linear Cycles → Milestone Mapping

| Linear Cycle Field | Milestone Field | Notes |
|-------------------|-----------------|-------|
| `id` | `id` | Cycle UUID |
| `name` | `name` | Cycle name |
| `description` | `description` | Cycle description |
| `endsAt` | `target_date` | End date maps to milestone target |
| `startsAt` | `platform_data.starts_at` | Start date stored in metadata |
| `completedAt` | `platform_data.completed_at` | Completion timestamp |
| `progress` (0.0-1.0) | `progress_pct` (0-100) | Converted to percentage |
| `issueCount` | `total_issues` | Total issues in cycle |
| `completedIssueCount` | `closed_issues` | Completed issues count |
| `team` | `platform_data.team` | Team information |

## State Determination

Milestone state is automatically calculated based on cycle dates:

```python
if completed_at:
    state = "completed"  # Cycle marked as complete
elif now > ends_at:
    state = "closed"     # Past due date without completion
elif starts_at <= now <= ends_at:
    state = "active"     # Currently in progress
else:
    state = "open"       # Before start date
```

### State Transitions

```
open → active → completed
  ↓       ↓
closed ← closed (past due)
```

- **open**: Cycle has not started yet (before `startsAt`)
- **active**: Cycle is in progress (between `startsAt` and `endsAt`)
- **completed**: Cycle has been marked complete (has `completedAt`)
- **closed**: Cycle passed end date without completion

## Date Requirements

Linear Cycles **require both start and end dates**:

- If `target_date` provided: `startsAt = now`, `endsAt = target_date`
- If no `target_date`: Default to 2-week cycle (`endsAt = now + 14 days`)

**Example:**
```python
# With target date
milestone = await adapter.milestone_create(
    name="v2.1.0 Release",
    target_date=datetime(2025, 12, 31, tzinfo=timezone.utc)
)
# Creates cycle: startsAt=now, endsAt=2025-12-31

# Without target date (default)
milestone = await adapter.milestone_create(
    name="Sprint 24"
)
# Creates cycle: startsAt=now, endsAt=now+14days
```

## Progress Calculation

Linear provides native progress tracking:

- **Linear Progress**: Float from 0.0 to 1.0
- **Milestone Progress**: Converted to 0-100 percentage
- **Calculation**: `progress_pct = cycle.progress * 100`

Progress is automatically calculated by Linear based on:
- Total issue count
- Completed issue count
- Issue state types (unstarted, started, completed)

## Supported Operations

### 1. Create Milestone (Cycle)

```python
milestone = await adapter.milestone_create(
    name="Q4 2025 Sprint",
    description="Final sprint of Q4",
    target_date=datetime(2025, 12, 15, tzinfo=timezone.utc),
    labels=["q4", "release"],  # Stored in metadata
    project_id="optional-project-id"
)
```

**GraphQL Mutation:** `cycleCreate`
**Returns:** Milestone object with Linear cycle data

### 2. Get Milestone

```python
milestone = await adapter.milestone_get("cycle-uuid-here")
```

**GraphQL Query:** `cycle(id: String!)`
**Returns:** Milestone object with calculated progress, or None if not found

### 3. List Milestones

```python
# List all milestones
milestones = await adapter.milestone_list()

# Filter by state
active_milestones = await adapter.milestone_list(state="active")
completed_milestones = await adapter.milestone_list(state="completed")
```

**GraphQL Query:** `team.cycles(first: Int!)`
**Returns:** List of Milestone objects
**Note:** `project_id` filter not used (Linear cycles are team-scoped)

### 4. Update Milestone

```python
updated = await adapter.milestone_update(
    milestone_id="cycle-uuid",
    name="Updated Cycle Name",
    description="New description",
    target_date=new_date,
    state="completed"  # Marks cycle as complete
)
```

**GraphQL Mutation:** `cycleUpdate`
**Returns:** Updated Milestone object, or None if not found

**State Update:**
- Setting `state="completed"` adds `completedAt` timestamp
- Other state values are ignored (state is date-based)

### 5. Delete Milestone (Archive)

```python
success = await adapter.milestone_delete("cycle-uuid")
```

**GraphQL Mutation:** `cycleArchive`
**Returns:** True if archived successfully, False otherwise

**Note:** Linear doesn't support permanent deletion, cycles are archived.

### 6. Get Issues in Milestone

```python
# Get all issues
issues = await adapter.milestone_get_issues("cycle-uuid")

# Filter by state
open_issues = await adapter.milestone_get_issues(
    "cycle-uuid",
    state="open"
)
```

**GraphQL Query:** `cycle.issues(first: Int!)`
**Returns:** List of Task objects

## API Limitations

### Rate Limits
- **1000 requests/hour** per user
- **20 requests/second** burst limit

### Pagination
- Maximum 50 cycles per query
- Use `after` cursor for pagination (not yet implemented)

### Scope
- Cycles are **team-scoped**, not workspace-scoped
- Each team has separate cycles
- Cannot span cycles across multiple teams

### Deletion
- Cycles cannot be permanently deleted
- `cycleArchive` mutation archives the cycle
- Archived cycles may still appear in queries

## Error Handling

### Common Errors

**1. Team ID Not Found**
```
ValueError: Cannot resolve team_id 'INVALID' to a valid Linear team UUID
```
**Solution:** Ensure `team_key` or `team_id` is correctly configured

**2. Invalid Date Format**
```
ValueError: Failed to create milestone: Invalid date format
```
**Solution:** Use timezone-aware datetime objects (`timezone.utc`)

**3. Cycle Not Found**
```
# Returns None instead of raising exception
milestone = await adapter.milestone_get("invalid-id")
assert milestone is None
```

**4. Unauthorized**
```
ValueError: Linear API connection failed
```
**Solution:** Check API key has proper permissions

## Platform-Specific Data

The `platform_data` field contains Linear-specific metadata:

```python
milestone.platform_data = {
    "linear": {
        "cycle_id": "cycle-uuid",
        "starts_at": "2025-12-01T00:00:00Z",
        "ends_at": "2025-12-15T23:59:59Z",
        "completed_at": None,  # or timestamp if completed
        "team": {
            "id": "team-uuid",
            "name": "Engineering"
        }
    }
}
```

## Best Practices

### 1. Always Use Timezone-Aware Dates
```python
from datetime import datetime, timezone

# ✅ Good
target_date = datetime.now(timezone.utc) + timedelta(days=14)

# ❌ Bad
target_date = datetime.now()  # Naive datetime
```

### 2. Check for None Returns
```python
milestone = await adapter.milestone_get(milestone_id)
if milestone is None:
    print("Milestone not found")
    return

# Safe to use milestone
print(f"Progress: {milestone.progress_pct}%")
```

### 3. Handle State Transitions
```python
# State is automatically calculated
milestone = await adapter.milestone_get(milestone_id)

if milestone.state == "active":
    print("Cycle is in progress")
elif milestone.state == "completed":
    print("Cycle completed!")
elif milestone.state == "closed":
    print("Cycle past due")
```

### 4. Use Labels for Metadata Only
```python
# Labels are stored in metadata, not used by Linear
milestone = await adapter.milestone_create(
    name="Sprint 24",
    labels=["sprint", "q4", "high-priority"]  # For app use only
)
```

## Testing

Run integration tests:

```bash
# Set environment variables
export LINEAR_API_KEY="lin_api_..."
export LINEAR_TEAM_ID="team-uuid-here"

# Run tests
pytest tests/adapters/test_linear_milestone_operations.py -v

# Run specific test
pytest tests/adapters/test_linear_milestone_operations.py::test_milestone_create_with_target_date -v
```

## Examples

### Example 1: Create Sprint Milestone
```python
from datetime import datetime, timedelta, timezone
from mcp_ticketer.core import AdapterRegistry

# Initialize adapter
config = {"api_key": "lin_api_...", "team_id": "team-uuid"}
adapter = AdapterRegistry.get_adapter("linear", config)
await adapter.initialize()

# Create 2-week sprint
sprint_end = datetime.now(timezone.utc) + timedelta(days=14)
milestone = await adapter.milestone_create(
    name="Sprint 24",
    description="Q4 2025 Sprint 24",
    target_date=sprint_end,
    labels=["sprint", "q4"]
)

print(f"Created: {milestone.name}")
print(f"State: {milestone.state}")
print(f"Target: {milestone.target_date}")
```

### Example 2: Track Milestone Progress
```python
# Get current progress
milestone = await adapter.milestone_get(milestone_id)

print(f"Milestone: {milestone.name}")
print(f"Progress: {milestone.progress_pct:.1f}%")
print(f"Issues: {milestone.closed_issues}/{milestone.total_issues}")
print(f"State: {milestone.state}")

# Get issues in milestone
issues = await adapter.milestone_get_issues(milestone_id)
for issue in issues:
    print(f"  - {issue.title} ({issue.state})")
```

### Example 3: Complete a Milestone
```python
# Mark milestone as completed
updated = await adapter.milestone_update(
    milestone_id,
    state="completed"
)

print(f"Milestone completed: {updated.name}")
print(f"Completion: {updated.platform_data['linear']['completed_at']}")
```

## Comparison with Other Adapters

| Feature | Linear (Cycles) | GitHub (Milestones) | Jira (Versions) |
|---------|----------------|---------------------|-----------------|
| Native Support | ✅ Yes | ✅ Yes | ✅ Yes |
| Start/End Dates | ✅ Required | ❌ Only end date | ❌ Only release date |
| Progress Tracking | ✅ Native | ✅ Native | ❌ Query-based |
| Deletion | ⚠️ Archive only | ✅ Permanent | ✅ Permanent |
| Scope | Team-level | Repository-level | Project-level |
| State Transitions | ✅ Date-based | ❌ Binary (open/closed) | ❌ Binary (released/unreleased) |

## Future Enhancements

Planned improvements for future versions:

1. **Pagination Support**: Handle >50 cycles with cursor-based pagination
2. **Batch Operations**: Create/update multiple milestones in one call
3. **Cross-Team Cycles**: Support for workspace-level milestones
4. **Burndown Charts**: Historical progress tracking
5. **Velocity Metrics**: Calculate team velocity across cycles

## Related Documentation

- [Milestone Model](/docs/models/milestone.md)
- [BaseAdapter Milestone Methods](/docs/adapters/base-adapter.md#milestone-operations)
- [Linear GraphQL API](https://studio.apollographql.com/public/Linear-API/variant/current/home)
- [Linear Cycles Documentation](https://linear.app/docs/cycles)

## Changelog

### 2025-12-04 - Initial Implementation
- ✅ Implemented all 6 milestone methods
- ✅ Added GraphQL queries for cycle operations
- ✅ Created comprehensive integration tests
- ✅ Documented API usage and limitations
- ✅ Added state transition logic
- ✅ Progress calculation with percentage conversion

**Related Ticket:** [1M-607](https://linear.app/1m-hyperdev/issue/1M-607/implement-cross-platform-milestone-support) - Phase 2: Linear Adapter Integration
