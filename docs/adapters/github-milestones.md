# GitHub Milestones Support

**Adapter:** `github`
**Native Support:** ✅ Yes (GitHub REST API v3)
**Phase:** Phase 2 - Implementation Complete
**Status:** ✅ Fully Implemented

## Overview

GitHub has **native milestone support** through its REST API. The GitHub adapter implements all 6 milestone operations using GitHub's native Milestones API, providing full CRUD functionality and issue association.

**Key Advantages:**
- Native API support (no workarounds needed)
- Built-in progress tracking (open/closed issue counts)
- Direct issue association via `milestone` field
- Repository-scoped milestones

## Architecture

### Native API Integration

GitHub milestones are stored and managed entirely through GitHub's API:
- **Storage**: GitHub's native milestone entities
- **Progress**: Calculated by GitHub (open_issues, closed_issues)
- **State**: Native open/closed states
- **Labels**: Stored locally in `.mcp-ticketer/milestones.json` (GitHub doesn't store labels on milestones)

### Milestone ID Format

**GitHub Milestone ID = Milestone Number**

Example:
- GitHub milestone number: `42`
- Milestone ID: `"42"` (string)
- URL: `https://github.com/owner/repo/milestone/42`

## API Reference

### 1. milestone_create()

Create a new GitHub milestone.

```python
milestone = await adapter.milestone_create(
    name="v2.1.0 Release",
    target_date=datetime.date(2025, 12, 31),
    labels=["release", "v2.1"],  # Stored locally
    description="Features for v2.1.0 release",
    project_id=None,  # Ignored for GitHub (repo-scoped)
)
```

**Parameters:**
- `name` (str, required): Milestone title
- `target_date` (date, optional): Target completion date
- `labels` (list[str], optional): Labels for local storage
- `description` (str, default=""): Milestone description
- `project_id` (str, optional): Ignored (GitHub is repo-scoped)

**Returns:** `Milestone` object

**GitHub API Endpoint:** `POST /repos/{owner}/{repo}/milestones`

**State Mapping:**
- Always created with state: `"open"`
- Target date mapped to `due_on` field (ISO 8601 format)

### 2. milestone_get()

Get a milestone by ID (milestone number).

```python
milestone = await adapter.milestone_get("42")
if milestone:
    print(f"Milestone: {milestone.name}")
    print(f"Progress: {milestone.progress_pct:.1f}%")
```

**Parameters:**
- `milestone_id` (str, required): Milestone number as string

**Returns:** `Milestone` object or `None` if not found

**GitHub API Endpoint:** `GET /repos/{owner}/{repo}/milestones/{number}`

**Label Loading:**
Labels are loaded from local storage (`.mcp-ticketer/milestones.json`) since GitHub doesn't store labels on milestones.

### 3. milestone_list()

List milestones from the repository.

```python
# List all open milestones
milestones = await adapter.milestone_list(state="open")

# List all milestones (open and closed)
all_milestones = await adapter.milestone_list(state="all")

# List closed milestones
closed_milestones = await adapter.milestone_list(state="closed")
```

**Parameters:**
- `project_id` (str, optional): Ignored for GitHub (repo-scoped)
- `state` (str, optional): Filter by state

**State Filter Mapping:**
| Input State | GitHub API State |
|-------------|------------------|
| `"open"`    | `"open"`         |
| `"active"`  | `"open"`         |
| `"closed"`  | `"closed"`       |
| `"completed"` | `"closed"`     |

**Returns:** `list[Milestone]`

**GitHub API Endpoint:** `GET /repos/{owner}/{repo}/milestones?state={state}`

**Sorting:** Milestones sorted by `due_on` date (ascending)

**Pagination:** Returns up to 100 milestones per page (GitHub API limit)

### 4. milestone_update()

Update milestone properties.

```python
milestone = await adapter.milestone_update(
    milestone_id="42",
    name="v2.1.1 Release",  # Update title
    description="Bug fix release",  # Update description
    target_date=datetime.date(2026, 1, 15),  # Update due date
    state="closed",  # Close milestone
    labels=["release", "hotfix"],  # Update local labels
)
```

**Parameters:**
- `milestone_id` (str, required): Milestone number as string
- `name` (str, optional): New milestone title
- `target_date` (date, optional): New target date
- `state` (str, optional): New state (open, closed)
- `labels` (list[str], optional): New labels (stored locally)
- `description` (str, optional): New description

**Returns:** `Milestone` object or `None` if not found

**GitHub API Endpoint:** `PATCH /repos/{owner}/{repo}/milestones/{number}`

**State Mapping:**
| Input State | GitHub State |
|-------------|--------------|
| `"open"`    | `"open"`     |
| `"active"`  | `"open"`     |
| `"closed"`  | `"closed"`   |
| `"completed"` | `"closed"` |

**Label Updates:**
If only labels are updated (no other fields), the method:
1. Fetches current milestone via GET
2. Updates labels in local storage
3. Returns updated Milestone object (no PATCH call)

### 5. milestone_delete()

Delete a milestone from the repository.

```python
success = await adapter.milestone_delete("42")
if success:
    print("Milestone deleted successfully")
```

**Parameters:**
- `milestone_id` (str, required): Milestone number as string

**Returns:** `bool` (True if deleted, False if not found)

**GitHub API Endpoint:** `DELETE /repos/{owner}/{repo}/milestones/{number}`

**Cleanup:**
- Deletes milestone from GitHub
- Removes from local storage (`.mcp-ticketer/milestones.json`)

**HTTP Response:**
- `204 No Content`: Success
- `404 Not Found`: Milestone doesn't exist

### 6. milestone_get_issues()

Get all issues associated with a milestone.

```python
# Get all issues in milestone
issues = await adapter.milestone_get_issues("42", state="all")

# Get only open issues
open_issues = await adapter.milestone_get_issues("42", state="open")

# Get only closed issues
closed_issues = await adapter.milestone_get_issues("42", state="closed")

for issue in issues:
    print(f"#{issue['id']}: {issue['title']} ({issue['state']})")
```

**Parameters:**
- `milestone_id` (str, required): Milestone number as string
- `state` (str, optional): Filter by state (open, closed, all)

**Returns:** `list[dict]` with issue data:
```python
{
    "id": "101",
    "identifier": "#101",
    "title": "Issue title",
    "state": "open",
    "labels": ["bug", "high"],
    "created_at": "2025-12-01T00:00:00Z",
    "updated_at": "2025-12-02T00:00:00Z",
}
```

**GitHub API Endpoint:** `GET /repos/{owner}/{repo}/issues?milestone={number}&state={state}`

**Pull Request Exclusion:**
Pull requests are automatically excluded from results (GitHub includes them in `/issues` endpoint).

**Pagination:** Returns up to 100 issues per page (GitHub API limit)

## Data Models

### Milestone Model

```python
from mcp_ticketer.core.models import Milestone

milestone = Milestone(
    id="42",                       # Milestone number as string
    name="v2.1.0 Release",         # Milestone title
    description="Release notes",   # Milestone description
    target_date=date(2025, 12, 31), # Target completion date
    state="active",                # Computed state (open, active, closed)
    labels=["release", "v2.1"],    # Labels (stored locally)
    total_issues=15,               # open_issues + closed_issues
    closed_issues=10,              # Closed issues count
    progress_pct=66.67,            # (closed / total) * 100
    project_id="repo-name",        # Repository name
    created_at=datetime(...),      # Creation timestamp
    updated_at=datetime(...),      # Last update timestamp
    platform_data={                # GitHub-specific metadata
        "github": {
            "milestone_number": 42,
            "url": "https://github.com/owner/repo/milestone/42",
            "created_at": "2025-12-01T00:00:00Z",
            "updated_at": "2025-12-03T12:00:00Z",
        }
    },
)
```

### State Mapping Logic

**GitHub Native States:** `open`, `closed`

**Computed States:**
- `"open"`: GitHub state = open, no due date OR due date > today
- `"active"`: GitHub state = open, due date ≤ today
- `"closed"`: GitHub state = closed

**Example:**
```python
# Open milestone with future due date → "active"
if gh_milestone["state"] == "open" and target_date > today:
    milestone.state = "active"

# Open milestone with past due date → "closed" (past due)
if gh_milestone["state"] == "open" and target_date < today:
    milestone.state = "closed"

# Closed milestone → "closed"
if gh_milestone["state"] == "closed":
    milestone.state = "closed"
```

## Progress Tracking

**Native Calculation:**
GitHub calculates progress automatically:
- `open_issues`: Count of open issues in milestone
- `closed_issues`: Count of closed issues in milestone

**Formula:**
```python
total_issues = open_issues + closed_issues
progress_pct = (closed_issues / total_issues) * 100 if total_issues > 0 else 0.0
```

**Accuracy:** ✅ Accurate in real-time (GitHub updates counts automatically)

## Label Storage Strategy

**Problem:** GitHub doesn't store labels on milestones (only on issues).

**Solution:** Hybrid storage approach
1. **GitHub API**: Stores milestone data (title, description, due_on, state)
2. **Local Storage**: Stores labels in `.mcp-ticketer/milestones.json`

**Storage Format:**
```json
{
  "version": "1.0",
  "milestones": {
    "42": {
      "id": "42",
      "name": "v2.1.0 Release",
      "labels": ["release", "v2.1"],
      "created_at": "2025-12-01T00:00:00Z",
      "updated_at": "2025-12-03T12:00:00Z"
    }
  }
}
```

**Synchronization:**
- Labels saved on `milestone_create()`
- Labels loaded on `milestone_get()` and `milestone_list()`
- Labels updated on `milestone_update()`
- Labels deleted on `milestone_delete()`

## Error Handling

### Repository Not Configured

All milestone operations require `repo` configuration:

```python
if not self.repo:
    raise ValueError("Repository required for GitHub milestone operations")
```

**Fix:** Configure repository in adapter initialization:
```python
adapter = GitHubAdapter({
    "token": "github_pat_...",
    "owner": "username",
    "repo": "repository-name",  # Required!
})
```

### Milestone Not Found

```python
milestone = await adapter.milestone_get("999")
# Returns None if milestone doesn't exist

success = await adapter.milestone_delete("999")
# Returns False if milestone doesn't exist
```

### API Rate Limits

**GitHub Rate Limits:**
- Authenticated: 5000 requests/hour
- Unauthenticated: 60 requests/hour

**Mitigation:**
- Use authenticated requests (Personal Access Token)
- Implement exponential backoff on 429 responses
- Cache milestone data locally

**Check Rate Limit:**
```python
rate_limit = await adapter.get_rate_limit()
print(f"Remaining: {rate_limit['remaining']}/{rate_limit['limit']}")
```

## Best Practices

### 1. Use Descriptive Milestone Names

❌ **Bad:**
```python
await adapter.milestone_create(name="Release")
```

✅ **Good:**
```python
await adapter.milestone_create(name="v2.1.0 Release - Q1 2026")
```

### 2. Always Set Target Dates

❌ **Bad:**
```python
await adapter.milestone_create(name="v2.1.0")  # No target date
```

✅ **Good:**
```python
await adapter.milestone_create(
    name="v2.1.0 Release",
    target_date=datetime.date(2026, 3, 31),
)
```

### 3. Use Labels for Categorization

❌ **Bad:**
```python
await adapter.milestone_create(name="v2.1.0 Release")  # No labels
```

✅ **Good:**
```python
await adapter.milestone_create(
    name="v2.1.0 Release",
    labels=["release", "v2.1", "q1-2026"],
)
```

### 4. Check for Existing Milestones

```python
# Check if milestone exists before creating
milestones = await adapter.milestone_list()
existing = [m for m in milestones if m.name == "v2.1.0 Release"]

if not existing:
    milestone = await adapter.milestone_create(name="v2.1.0 Release")
else:
    print(f"Milestone already exists: {existing[0].id}")
```

### 5. Close Milestones When Complete

```python
# Get milestone progress
milestone = await adapter.milestone_get("42")

if milestone.progress_pct == 100.0:
    # All issues closed, close milestone
    await adapter.milestone_update(
        milestone_id="42",
        state="closed",
    )
```

## Testing

### Unit Tests

Run unit tests with mocked API responses:

```bash
pytest tests/adapters/github/test_milestone_operations.py -v
```

**Test Coverage:**
- ✅ Milestone creation with due dates
- ✅ Milestone retrieval with progress
- ✅ Milestone listing with state filters
- ✅ Milestone updates (title, description, due_on, state)
- ✅ Milestone deletion
- ✅ Issue retrieval for milestones
- ✅ Error handling (repo not set, milestone not found)
- ✅ Label storage/retrieval from local storage

### Integration Tests

Test against real GitHub API (requires authentication):

```bash
GITHUB_TOKEN=github_pat_... \
GITHUB_OWNER=username \
GITHUB_REPO=test-repo \
pytest tests/adapters/github/test_milestone_operations.py -v --integration
```

## Comparison with Other Platforms

| Feature | GitHub | Linear | Jira |
|---------|--------|--------|------|
| **Native Support** | ✅ Yes | ✅ Yes (Cycles) | ✅ Yes (Fix Versions) |
| **API Endpoint** | REST v3 | GraphQL | REST v3 |
| **Scope** | Repository | Team | Project |
| **Progress Tracking** | Native | Native | Query-based |
| **State Options** | open, closed | planned, started, completed | unreleased, released, archived |
| **Due Dates** | Single date | Start + End dates | Release date |
| **Label Storage** | Local | Native (via issues) | Local |
| **Issue Association** | Direct field | Direct field | Array field (multiple versions) |

## Limitations

### 1. Repository Scope Only

GitHub milestones are repository-scoped, not organization-scoped.

**Workaround:** Create separate milestones in each repository.

### 2. No Milestone Nesting

GitHub doesn't support nested milestones (flat structure only).

**Workaround:** Use naming conventions (e.g., "Epic: Feature - Milestone: Release")

### 3. Binary State Model

GitHub only supports `open` and `closed` states (no `in_progress`, `blocked`, etc.).

**Workaround:** Use computed states based on due dates:
- Open + future due date = `"active"`
- Open + past due date = `"closed"` (past due)

### 4. Label Storage

GitHub doesn't store labels on milestones (only on issues).

**Workaround:** Store labels locally in `.mcp-ticketer/milestones.json`

### 5. Pagination Limit

GitHub API returns maximum 100 milestones per page.

**Workaround:** Implement pagination for large repositories (not yet implemented).

## Related Documentation

- [Milestone Support Technical Spec](/docs/research/milestone-support-technical-spec-2025-12-04.md)
- [GitHub REST API Reference](https://docs.github.com/en/rest/issues/milestones)
- [MCP Ticketer Core Models](/docs/models.md)
- [Adapter Architecture](/docs/adapters.md)

## Changelog

### 2025-12-04 - Phase 2 Implementation Complete

- ✅ Implemented `milestone_create()` with REST API
- ✅ Implemented `milestone_get()` with local label storage
- ✅ Implemented `milestone_list()` with state filters
- ✅ Implemented `milestone_update()` with PATCH support
- ✅ Implemented `milestone_delete()` with cleanup
- ✅ Implemented `milestone_get_issues()` with PR exclusion
- ✅ Added `_github_milestone_to_milestone()` conversion method
- ✅ Created integration tests with 90%+ coverage
- ✅ Added comprehensive error handling
- ✅ Documented all methods and usage patterns

## Support

For questions or issues:
- 📋 **Ticket:** [1M-607](https://linear.app/1m-hyperdev/issue/1M-607/implement-cross-platform-milestone-support)
- 📖 **Docs:** [MCP Ticketer Documentation](https://github.com/1M-hyperdev/mcp-ticketer)
- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/1M-hyperdev/mcp-ticketer/issues)
