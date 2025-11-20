# GitHub Adapter - New Operations Quick Reference

## Quick Start

```python
from mcp_ticketer.adapters.github import GitHubAdapter

config = {
    "owner": "your-org",
    "repo": "your-repo",
    "token": "ghp_your_token"
}

adapter = GitHubAdapter(config)
```

---

## `list_issue_statuses()` - List Available Statuses

**Purpose:** Get all available issue statuses (native + extended).

**No parameters required** - returns constant data.

```python
# Get all statuses
statuses = await adapter.list_issue_statuses()

# Filter by type
native = [s for s in statuses if s['type'] == 'native']
extended = [s for s in statuses if s['type'] == 'extended']

# Example output
{
    "name": "in_progress",
    "type": "extended",
    "label": "in-progress",
    "description": "Issue is in progress (tracked via label)",
    "category": "in_progress"
}
```

**Use Cases:**
- Display available statuses in UI
- Validate status transitions
- Documentation generation

---

## `get_issue_status()` - Get Rich Issue Status

**Purpose:** Get comprehensive status information for a specific issue.

**Parameters:**
- `issue_number` (int): GitHub issue number

```python
# Get status for issue #123
status = await adapter.get_issue_status(123)

print(f"State: {status['state']}")           # 'open' or 'closed'
print(f"Extended: {status['extended_state']}")  # 'in_progress', etc.
print(f"Label: {status['status_label']}")    # 'in-progress' or None
print(f"Assignees: {status['metadata']['assignees']}")
print(f"Milestone: {status['metadata']['milestone']}")

# Example output
{
    "number": 123,
    "state": "open",
    "status_label": "in-progress",
    "extended_state": "in_progress",
    "state_reason": None,
    "labels": ["in-progress", "bug", "P1"],
    "metadata": {
        "title": "Fix authentication bug",
        "url": "https://github.com/...",
        "assignees": ["developer1"],
        "milestone": "v1.0",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "closed_at": None
    }
}
```

**Use Cases:**
- Status dashboards
- Workflow tracking
- Issue analytics
- State machine validation

**Errors:**
- `ValueError` if issue not found
- `ValueError` if credentials invalid

---

## `list_project_labels()` - List Labels

**Purpose:** List labels for entire repository or specific milestone.

**Parameters:**
- `milestone_number` (int, optional): Filter by milestone (None = all labels)

```python
# Get all repository labels
all_labels = await adapter.list_project_labels()

# Get labels used in milestone 5
milestone_labels = await adapter.list_project_labels(milestone_number=5)

# Labels are sorted by usage count (most used first)
for label in milestone_labels:
    print(f"{label['name']}: {label['usage_count']} issues")

# Example output
{
    "id": "bug",
    "name": "bug",
    "color": "d73a4a",
    "description": "Something isn't working",
    "usage_count": 12  # Only when filtered by milestone
}
```

**Use Cases:**
- Label analytics
- Milestone overview
- Tag suggestions
- Label management

**Behavior:**
- Without milestone: Returns all repository labels
- With milestone: Returns labels used by issues in that milestone
- Excludes pull requests from counting
- Sorted by usage frequency

---

## `list_cycles()` - List Project Iterations

**Purpose:** List GitHub Projects V2 iterations (sprints/cycles).

**Parameters:**
- `project_id` (str, **required**): Project V2 node ID (e.g., `PVT_kwDOABCD1234`)
- `limit` (int, default=50): Max iterations to return

```python
# List iterations for a project
iterations = await adapter.list_cycles(
    project_id="PVT_kwDOABCD1234",
    limit=10
)

for iteration in iterations:
    print(f"{iteration['title']}: {iteration['startDate']} - {iteration['endDate']}")
    print(f"  Duration: {iteration['duration']} days")

# Example output
{
    "id": "PVTI_lADOABCD01234",
    "title": "Sprint 1",
    "startDate": "2024-01-01T00:00:00Z",
    "duration": 14,
    "endDate": "2024-01-15T00:00:00Z"  # Calculated
}
```

**Finding Project ID:**

```graphql
# Using GitHub GraphQL Explorer
query {
  organization(login: "your-org") {
    projectV2(number: 1) {
      id  # Returns: PVT_kwDOABCD1234
      title
    }
  }
}
```

Or for user projects:
```graphql
query {
  user(login: "username") {
    projectV2(number: 1) {
      id
      title
    }
  }
}
```

**Use Cases:**
- Sprint planning
- Iteration management
- Timeline visualization
- Capacity planning

**Errors:**
- `ValueError` if `project_id` not provided
- `ValueError` if project not found
- `ValueError` if credentials invalid

---

## Complete Example

```python
import asyncio
from mcp_ticketer.adapters.github import GitHubAdapter

async def main():
    adapter = GitHubAdapter({
        "owner": "myorg",
        "repo": "myrepo",
        "token": "ghp_..."
    })

    # 1. See what statuses are available
    statuses = await adapter.list_issue_statuses()
    print(f"Available statuses: {[s['name'] for s in statuses]}")

    # 2. Check status of a specific issue
    status = await adapter.get_issue_status(42)
    print(f"Issue #42 is {status['extended_state']}")

    # 3. Get labels for milestone planning
    labels = await adapter.list_project_labels(milestone_number=5)
    print(f"Milestone 5 uses {len(labels)} labels")

    # 4. List current sprint iterations
    try:
        iterations = await adapter.list_cycles(
            project_id="PVT_kwDOABCD1234"
        )
        print(f"Found {len(iterations)} iterations")
    except ValueError as e:
        print(f"No project configured: {e}")

    await adapter.close()

asyncio.run(main())
```

---

## Common Patterns

### Status Workflow Tracking

```python
# Check if issue can transition to target state
status = await adapter.get_issue_status(issue_num)
available = await adapter.list_issue_statuses()

current = status['extended_state']
target = 'in_progress'

# Validate transition (use TicketState model)
from mcp_ticketer.core.models import TicketState
if TicketState(current).can_transition_to(TicketState(target)):
    # Update issue state
    await adapter.update(issue_num, {'state': TicketState(target)})
```

### Milestone Health Check

```python
# Get milestone overview
labels = await adapter.list_project_labels(milestone_number=5)

# Analyze label distribution
priority_labels = [l for l in labels if l['name'].startswith('P')]
state_labels = [l for l in labels if l['name'] in ['blocked', 'waiting']]

print(f"Blocked issues: {sum(l['usage_count'] for l in state_labels)}")
```

### Sprint Planning

```python
# Get active iterations
iterations = await adapter.list_cycles(project_id="PVT_...")

# Find current sprint
from datetime import datetime
now = datetime.now().isoformat()

current_sprint = next(
    (i for i in iterations
     if i['startDate'] <= now <= i['endDate']),
    None
)

if current_sprint:
    print(f"Current sprint: {current_sprint['title']}")
```

---

## Error Handling

All methods follow consistent error patterns:

```python
try:
    status = await adapter.get_issue_status(999)
except ValueError as e:
    if "not found" in str(e):
        print("Issue doesn't exist")
    elif "GITHUB_TOKEN" in str(e):
        print("Invalid credentials")
    else:
        print(f"Other error: {e}")
```

---

## Performance Tips

1. **Cache statuses:** `list_issue_statuses()` returns constant data - cache it
2. **Batch operations:** Fetch multiple issue statuses in parallel with `asyncio.gather()`
3. **Label caching:** Repository labels don't change often - cache for ~1 hour
4. **Project iterations:** Cache iterations for duration of sprint

```python
# Fetch multiple issue statuses in parallel
issues = [123, 124, 125]
statuses = await asyncio.gather(
    *[adapter.get_issue_status(num) for num in issues]
)
```

---

## GitHub API Limits

- `list_issue_statuses()`: No API calls (constant data)
- `get_issue_status()`: 1 REST API call per issue
- `list_project_labels()`: 1 REST API call (+ pagination if milestone has >100 issues)
- `list_cycles()`: 1 GraphQL call (counts against GraphQL limit, not REST)

**Rate Limits:**
- REST API: 5,000 requests/hour (authenticated)
- GraphQL API: 5,000 points/hour (separate limit)

---

## Comparison with Other Adapters

| Feature | GitHub | JIRA | Linear |
|---------|--------|------|--------|
| Cycles term | "Iterations" | "Sprints" | "Cycles" |
| Cycle ID | Node ID | Sprint ID | UUID |
| Status model | Binary + labels | Workflow states | State enum |
| Label scope | Repository | Project | Workspace |

---

## Migration from Old Patterns

### Before (Limited Status Info)
```python
issue = await adapter.read("123")
state = issue.state  # Just 'open' or 'closed'
```

### After (Rich Status Info)
```python
status = await adapter.get_issue_status(123)
state = status['extended_state']  # 'in_progress', 'blocked', etc.
labels = status['labels']
assignees = status['metadata']['assignees']
```

---

## See Also

- **Implementation:** `src/mcp_ticketer/adapters/github.py`
- **Tests:** `tests/adapters/test_github_new_operations.py`
- **Demo:** `examples/github_new_operations_demo.py`
- **Summary:** `GITHUB_NEW_OPERATIONS_SUMMARY.md`
