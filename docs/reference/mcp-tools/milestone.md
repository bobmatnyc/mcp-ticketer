# Milestone MCP Tool

**Tool Name:** `milestone`
**Version:** 2.0.0
**Related Ticket:** [1M-607 - Add milestone support (Phase 3)](https://linear.app/1m-hyperdev/issue/1M-607)

## Overview

The `milestone()` tool provides unified milestone management for cross-platform ticket tracking. A milestone is defined as **a list of labels with target dates, into which issues can be grouped**.

This tool supports:
- Creating and managing milestones across platforms (Linear, GitHub, JIRA)
- Progress tracking with automatic calculation
- Issue association via labels
- Milestone-based filtering for ticket searches

## Architecture

### Unified Tool Pattern

Following the established pattern from `ticket()` and `hierarchy()` tools, `milestone()` provides a single interface for all milestone operations:

```python
milestone(action="create|get|list|update|delete|get_issues", ...)
```

### Platform Mappings

| Platform | Milestone Type | Progress Tracking | Label Support |
|----------|---------------|-------------------|---------------|
| **Linear** | Milestones | Native | Full support |
| **GitHub** | Milestones | Native | Full support |
| **JIRA** | Versions/Releases | Manual | Via labels |
| **Asana** | Projects with dates | Workaround | Via tags |

## Actions

### 1. Create Milestone

Create a new milestone with labels and target date.

**Signature:**
```python
await milestone(
    action="create",
    name: str,                    # Required
    target_date: str | None,       # ISO format: YYYY-MM-DD
    labels: list[str] | None,      # Labels defining scope
    description: str = "",
    project_id: str | None = None
)
```

**Example:**
```python
result = await milestone(
    action="create",
    name="v2.1.0 Release",
    target_date="2025-12-31",
    labels=["v2.1", "release", "q4"],
    description="Q4 2025 major release",
    project_id="proj-123"
)
```

**Response:**
```json
{
  "status": "completed",
  "message": "Milestone 'v2.1.0 Release' created successfully",
  "milestone": {
    "id": "milestone-abc123",
    "name": "v2.1.0 Release",
    "target_date": "2025-12-31T00:00:00",
    "state": "open",
    "description": "Q4 2025 major release",
    "labels": ["v2.1", "release", "q4"],
    "total_issues": 0,
    "closed_issues": 0,
    "progress_pct": 0.0,
    "project_id": "proj-123"
  },
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear",
    "milestone_id": "milestone-abc123"
  }
}
```

**Errors:**
- `name is required for create action`
- `Invalid date format 'XXX'. Use ISO format: YYYY-MM-DD`

---

### 2. Get Milestone

Retrieve milestone by ID with calculated progress.

**Signature:**
```python
await milestone(
    action="get",
    milestone_id: str  # Required
)
```

**Example:**
```python
result = await milestone(
    action="get",
    milestone_id="milestone-abc123"
)
```

**Response:**
```json
{
  "status": "completed",
  "milestone": {
    "id": "milestone-abc123",
    "name": "v2.1.0 Release",
    "target_date": "2025-12-31T00:00:00",
    "state": "active",
    "labels": ["v2.1", "release"],
    "total_issues": 15,
    "closed_issues": 8,
    "progress_pct": 53.3,
    "project_id": "proj-123"
  },
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear",
    "milestone_id": "milestone-abc123"
  }
}
```

**Progress Calculation:**
- `progress_pct = (closed_issues / total_issues) * 100`
- Issues counted by matching milestone labels
- Closed state determined by platform-specific rules

**Errors:**
- `milestone_id is required for get action`
- `Milestone 'XXX' not found`

---

### 3. List Milestones

List all milestones with optional filtering.

**Signature:**
```python
await milestone(
    action="list",
    project_id: str | None = None,  # Filter by project
    state: str | None = None        # Filter by state
)
```

**Example:**
```python
# List all active milestones
result = await milestone(
    action="list",
    state="active"
)

# List milestones in specific project
result = await milestone(
    action="list",
    project_id="proj-123"
)
```

**Response:**
```json
{
  "status": "completed",
  "message": "Found 3 milestone(s)",
  "milestones": [
    {
      "id": "milestone-abc123",
      "name": "v2.1.0 Release",
      "state": "active",
      "progress_pct": 53.3
    },
    {
      "id": "milestone-def456",
      "name": "v2.2.0 Release",
      "state": "open",
      "progress_pct": 0.0
    }
  ],
  "count": 3,
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear"
  }
}
```

**State Values:**
- `open`: Not started
- `active`: In progress
- `completed`: Finished
- `closed`: Canceled or archived

---

### 4. Update Milestone

Update milestone properties.

**Signature:**
```python
await milestone(
    action="update",
    milestone_id: str,           # Required
    name: str | None = None,
    target_date: str | None = None,
    state: str | None = None,
    labels: list[str] | None = None,
    description: str | None = None
)
```

**Example:**
```python
# Mark milestone as completed
result = await milestone(
    action="update",
    milestone_id="milestone-abc123",
    state="completed"
)

# Update target date and labels
result = await milestone(
    action="update",
    milestone_id="milestone-abc123",
    target_date="2026-01-15",
    labels=["v2.1", "release", "q1-2026"]
)
```

**Response:**
```json
{
  "status": "completed",
  "message": "Milestone 'milestone-abc123' updated successfully",
  "milestone": {
    "id": "milestone-abc123",
    "name": "v2.1.0 Release",
    "state": "completed",
    "target_date": "2026-01-15T00:00:00",
    "labels": ["v2.1", "release", "q1-2026"]
  },
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear",
    "milestone_id": "milestone-abc123"
  }
}
```

**Errors:**
- `milestone_id is required for update action`
- `Failed to update milestone 'XXX'`
- `Invalid date format 'XXX'. Use ISO format: YYYY-MM-DD`

---

### 5. Delete Milestone

Delete a milestone.

**Signature:**
```python
await milestone(
    action="delete",
    milestone_id: str  # Required
)
```

**Example:**
```python
result = await milestone(
    action="delete",
    milestone_id="milestone-abc123"
)
```

**Response:**
```json
{
  "status": "completed",
  "message": "Milestone 'milestone-abc123' deleted successfully",
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear",
    "milestone_id": "milestone-abc123"
  }
}
```

**Errors:**
- `milestone_id is required for delete action`
- `Failed to delete milestone 'XXX'`

**Note:** Deleting a milestone does NOT delete its associated issues. Issues remain but lose milestone association.

---

### 6. Get Issues in Milestone

Retrieve all issues associated with a milestone.

**Signature:**
```python
await milestone(
    action="get_issues",
    milestone_id: str,           # Required
    state: str | None = None     # Filter by issue state
)
```

**Example:**
```python
# Get all issues in milestone
result = await milestone(
    action="get_issues",
    milestone_id="milestone-abc123"
)

# Get only open issues
result = await milestone(
    action="get_issues",
    milestone_id="milestone-abc123",
    state="open"
)
```

**Response:**
```json
{
  "status": "completed",
  "message": "Found 15 issue(s) in milestone",
  "issues": [
    {
      "id": "issue-1",
      "title": "Implement OAuth2",
      "state": "in_progress",
      "priority": "high",
      "labels": ["v2.1", "authentication"]
    },
    {
      "id": "issue-2",
      "title": "Add API rate limiting",
      "state": "open",
      "priority": "medium",
      "labels": ["v2.1", "api"]
    }
  ],
  "count": 15,
  "metadata": {
    "adapter": "linear",
    "adapter_name": "Linear",
    "milestone_id": "milestone-abc123"
  }
}
```

**Errors:**
- `milestone_id is required for get_issues action`

---

## Integration with ticket_search

The `ticket_search()` tool supports milestone filtering via the `milestone_id` parameter.

**Example:**
```python
# Search for open bugs in a milestone
result = await ticket_search(
    query="authentication",
    milestone_id="milestone-abc123",
    state="open",
    tags=["bug"],
    limit=20
)
```

**Behavior:**
1. Execute standard search with all filters
2. Get issues in milestone via `adapter.milestone_get_issues()`
3. Filter search results to only include milestone issues
4. Return filtered results

**Note:** If milestone filtering fails, search continues with unfiltered results and logs a warning.

---

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `Invalid action` | Action not in valid list | Use: create, get, list, update, delete, get_issues |
| `milestone_id is required` | Missing required ID | Provide milestone_id parameter |
| `name is required` | Missing name for create | Provide name parameter |
| `Invalid date format` | Date not ISO format | Use format: YYYY-MM-DD |
| `Milestone 'XXX' not found` | ID doesn't exist | Verify milestone exists with list action |
| `Failed to update/delete` | Adapter operation failed | Check adapter logs, verify permissions |

### Exception Handling

All exceptions are caught and returned as error responses:

```json
{
  "status": "error",
  "error": "Milestone operation failed: <exception message>",
  "action": "get",
  "milestone_id": "milestone-abc123"
}
```

---

## Usage Patterns

### Creating Release Milestones

```python
# 1. Create milestone for release
milestone_result = await milestone(
    action="create",
    name="v2.1.0 Release",
    target_date="2025-12-31",
    labels=["v2.1", "release"],
    description="Q4 2025 release with OAuth2 and API improvements"
)

milestone_id = milestone_result["milestone"]["id"]

# 2. Tag issues with milestone labels
await ticket(
    action="update",
    ticket_id="issue-123",
    tags=["v2.1", "release"]  # Matches milestone labels
)

# 3. Track progress
progress = await milestone(
    action="get",
    milestone_id=milestone_id
)
print(f"Release progress: {progress['milestone']['progress_pct']}%")

# 4. List remaining work
open_issues = await milestone(
    action="get_issues",
    milestone_id=milestone_id,
    state="open"
)
```

### Sprint Planning

```python
# Create sprint milestone
sprint = await milestone(
    action="create",
    name="Sprint 42",
    target_date="2025-12-15",
    labels=["sprint-42"],
    project_id="proj-123"
)

# Find candidate issues
candidates = await ticket_search(
    project_id="proj-123",
    state="open",
    priority="high",
    limit=50
)

# Tag issues for sprint
for issue in candidates["tickets"][:10]:  # Take top 10
    await ticket(
        action="update",
        ticket_id=issue["id"],
        tags=issue.get("tags", []) + ["sprint-42"]
    )

# Daily standup: Check sprint progress
sprint_status = await milestone(
    action="get",
    milestone_id=sprint["milestone"]["id"]
)
```

### Release Retrospective

```python
# Get completed milestone
milestone_data = await milestone(
    action="get",
    milestone_id="milestone-v2.0.0"
)

# Analyze completed work
completed_issues = await milestone(
    action="get_issues",
    milestone_id="milestone-v2.0.0",
    state="done"
)

# Check for carryover work
incomplete = await milestone(
    action="get_issues",
    milestone_id="milestone-v2.0.0",
    state="open"
)

# Move incomplete to next milestone
for issue in incomplete["issues"]:
    await ticket(
        action="update",
        ticket_id=issue["id"],
        tags=["v2.1", "release"]  # Next milestone labels
    )

# Archive old milestone
await milestone(
    action="update",
    milestone_id="milestone-v2.0.0",
    state="closed"
)
```

---

## Best Practices

### Label Naming Conventions

Use consistent label naming for milestones:

```python
# ✅ GOOD: Version-based labels
labels=["v2.1", "release"]

# ✅ GOOD: Sprint-based labels
labels=["sprint-42", "q4-2025"]

# ✅ GOOD: Date-based labels
labels=["dec-2025", "release"]

# ❌ BAD: Inconsistent naming
labels=["v2.1", "V2.1-Release", "version_2_1"]
```

### Progress Tracking

1. **Set realistic target dates**: Leave buffer for unexpected delays
2. **Review progress regularly**: Check milestone progress in daily standups
3. **Update states promptly**: Mark milestones as active/completed accurately
4. **Handle scope creep**: Update milestone labels if scope changes

### Multi-Platform Usage

When working across platforms:

```python
# Check which adapter is active
config = await config(action="get")
current_adapter = config["data"]["adapter"]

# Platform-specific milestone handling
if current_adapter == "linear":
    # Linear: Full milestone support
    result = await milestone(action="create", ...)
elif current_adapter == "github":
    # GitHub: Native milestone support
    result = await milestone(action="create", ...)
elif current_adapter == "jira":
    # JIRA: Use versions as milestones
    result = await milestone(action="create", ...)
```

---

## Performance Considerations

### Progress Calculation

Progress is calculated on-demand by counting issues:

```python
# Efficient: Get progress for single milestone
milestone_data = await milestone(action="get", milestone_id="xyz")

# Less efficient: List all milestones (calculates progress for each)
all_milestones = await milestone(action="list")
```

### Issue Filtering

When filtering by milestone in search:

```python
# Two API calls required:
# 1. adapter.search() - Find matching tickets
# 2. adapter.milestone_get_issues() - Get milestone issues
# 3. Filter results client-side

result = await ticket_search(
    milestone_id="xyz",
    query="authentication"
)
```

**Optimization:** Use milestone-specific state filters to reduce result set:

```python
# Better: Filter by state at milestone level
result = await ticket_search(
    milestone_id="xyz",
    state="open",  # Passed to milestone_get_issues()
    query="authentication"
)
```

---

## See Also

- [Milestone Technical Specification](/docs/research/milestone-support-technical-spec-2025-12-04.md)
- [MCP API Reference](/docs/mcp-api-reference.md)
- [Ticket Tool Documentation](/docs/mcp-tools/ticket.md)
- [Hierarchy Tool Documentation](/docs/mcp-tools/hierarchy.md)

---

**Implementation:** Phase 3 of 1M-607 (MCP Tools Integration)
**Status:** Complete
**Version:** 2.0.0
**Last Updated:** 2025-12-04
