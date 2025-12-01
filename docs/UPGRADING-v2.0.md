# Upgrading to mcp-ticketer v2.0

**Version:** 2.0.0 (Breaking Changes)
**Release Date:** 2026-03-27 (projected)
**Deprecation Start:** v1.5.0 (2025-12-27)
**Deprecation Period:** 3 months

---

## Overview

mcp-ticketer v2.0 introduces **major API consolidations** that reduce tool count from 52 to 21 tools while improving consistency and developer experience. This guide helps you migrate from deprecated tools to the new unified interfaces.

**Key Changes:**
- **19,744 tokens saved** (40% reduction in context usage)
- **37 tools consolidated** into 10 unified tools
- **Action-based patterns** for consistency
- **Backward compatibility maintained** in v1.5.0-v1.8.0

**Timeline:**
- **v1.5.0 (Dec 2025):** Deprecation warnings begin
- **v1.6.0-v1.8.0 (Jan-Mar 2026):** Deprecation period
- **v2.0.0 (Mar 2026):** Deprecated tools removed

---

## Migration Strategy

### Recommended Approach

1. **Upgrade to v1.5.0 first**
   ```bash
   pip install --upgrade mcp-ticketer==1.5.0
   ```

2. **Run migration checker**
   ```bash
   mcp-ticketer migrate --check
   ```

3. **Fix deprecation warnings**
   - Review tool usage
   - Update to new unified tools
   - Test thoroughly

4. **Upgrade to v2.0.0**
   ```bash
   pip install --upgrade mcp-ticketer>=2.0.0
   ```

### Migration Checker

The migration checker scans your codebase for deprecated tool usage:

```bash
$ mcp-ticketer migrate --check

Scanning for deprecated MCP tool usage...

Found 23 deprecated tool calls:

  project_update_create (5 occurrences)
  → Migrate to: project_update(action="create", ...)
    - src/workflows/project.py:45
    - src/workflows/project.py:78
    - src/workflows/sprint.py:12
    - tests/test_project.py:23
    - tests/test_project.py:89

  ticket_read (8 occurrences)
  → Migrate to: ticket(action="read", ...)
    - src/ticket_utils.py:34
    - src/ticket_utils.py:67
    ...

Run 'mcp-ticketer migrate --apply' to auto-migrate (experimental)
Run 'mcp-ticketer migrate --help' for more options
```

---

## Consolidated Tools Reference

| Old Tools | New Unified Tool | Section |
|-----------|-----------------|---------|
| project_update_create, project_update_get, project_update_list | project_update | [Project Updates](#project-updates) |
| ticket_search, ticket_search_hierarchy | ticket_search | [Ticket Search](#ticket-search) |
| ticket_attach, ticket_attachments | [Removed] | [Attachments](#attachments-removed) |
| ticket_create_pr, ticket_link_pr | [Removed] | [Pull Requests](#pull-requests-removed) |
| ticket_bulk_create, ticket_bulk_update | ticket_create, ticket_update | [Bulk Operations](#bulk-operations) |
| get_my_tickets, attach_ticket, get_session_info | user | [User/Session](#user-session-management) |
| epic_create, epic_get, epic_update, epic_delete, epic_list, epic_issues | hierarchy | [Hierarchy](#hierarchy-management) |
| issue_create, issue_get_parent, issue_tasks | hierarchy | [Hierarchy](#hierarchy-management) |
| task_create | hierarchy | [Hierarchy](#hierarchy-management) |
| hierarchy_tree | hierarchy | [Hierarchy](#hierarchy-management) |
| ticket_create, ticket_read, ticket_update, ticket_delete, ticket_list, ticket_summary, ticket_latest, ticket_assign | ticket | [Ticket CRUD](#ticket-crud) |

---

## Project Updates

**Changed:** 3 tools → 1 unified tool

### Before (v1.x)

```python
# Create project update
mcp__mcp-ticketer__project_update_create(
    project_id="proj-123",
    body="Sprint 5 completed. 18/20 stories done.",
    health="on_track"
)

# Get project update
mcp__mcp-ticketer__project_update_get(update_id="update-456")

# List project updates
mcp__mcp-ticketer__project_update_list(project_id="proj-123", limit=10)
```

### After (v2.0)

```python
# Create project update
mcp__mcp-ticketer__project_update(
    action="create",
    project_id="proj-123",
    body="Sprint 5 completed. 18/20 stories done.",
    health="on_track"
)

# Get project update
mcp__mcp-ticketer__project_update(
    action="get",
    update_id="update-456"
)

# List project updates
mcp__mcp-ticketer__project_update(
    action="list",
    project_id="proj-123",
    limit=10
)
```

**Migration Pattern:**
- Add `action="create"|"get"|"list"` parameter
- Keep all other parameters unchanged
- Response format identical

---

## Ticket Search

**Changed:** 2 tools → 1 unified tool

### Before (v1.x)

```python
# Basic search
mcp__mcp-ticketer__ticket_search(
    query="authentication bug",
    state="open",
    limit=10
)

# Search with hierarchy
mcp__mcp-ticketer__ticket_search_hierarchy(
    query="oauth implementation",
    project_id="proj-123",
    max_depth=2
)
```

### After (v2.0)

```python
# Basic search (unchanged)
mcp__mcp-ticketer__ticket_search(
    query="authentication bug",
    state="open",
    limit=10
)

# Search with hierarchy (add include_hierarchy=True)
mcp__mcp-ticketer__ticket_search(
    query="oauth implementation",
    project_id="proj-123",
    include_hierarchy=True,
    max_depth=2
)
```

**Migration Pattern:**
- Basic search: No changes required
- Hierarchy search: Add `include_hierarchy=True`
- Default `include_hierarchy=False` maintains current behavior

---

## Attachments (Removed)

**Removed:** ticket_attach, ticket_attachments (v1.5.0)

**Rationale:** Functionality available in MCP filesystem server

**Migration Guide:** See [docs/migrations/ATTACHMENT_PR_REMOVAL.md](migrations/ATTACHMENT_PR_REMOVAL.md) for comprehensive examples and patterns.

### Before (v1.x)

```python
# Attach file to ticket
mcp__mcp-ticketer__ticket_attach(
    ticket_id="TICKET-123",
    file_path="/path/to/report.pdf",
    description="Performance analysis"
)

# List attachments
mcp__mcp-ticketer__ticket_attachments(ticket_id="TICKET-123")
```

### After (v2.0)

```python
# Use filesystem MCP + ticket comment

# 1. Organize files in project structure
# mkdir -p ./docs/tickets/TICKET-123

# 2. Copy file via filesystem MCP
mcp__filesystem__write_file(
    path="./docs/tickets/TICKET-123/performance-report.pdf",
    content=open("/path/to/report.pdf", "rb").read()
)

# 3. Reference in ticket
mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="Performance report attached: docs/tickets/TICKET-123/performance-report.pdf"
)

# 4. List "attachments" via filesystem
files = mcp__filesystem__list_directory(path="./docs/tickets/TICKET-123")
```

**Benefits:**
- Direct filesystem access (more flexible)
- No duplication with MCP filesystem server
- Better file management

**CLI Availability:**
These tools remain available via CLI:
```bash
aitrackdown attach TICKET-123 /path/to/file.pdf
aitrackdown attachments TICKET-123
```

**Migration Checklist:**
- [ ] Identify all ticket_attach usage
- [ ] Create docs/tickets/{ticket_id}/ directory structure
- [ ] Update code to use filesystem MCP
- [ ] Add ticket comments referencing files
- [ ] Test file access

---

## Pull Requests (Removed)

**Removed:** ticket_create_pr, ticket_link_pr (v1.5.0)

**Rationale:** Functionality available in MCP GitHub server

**Migration Guide:** See [docs/migrations/ATTACHMENT_PR_REMOVAL.md](migrations/ATTACHMENT_PR_REMOVAL.md) for comprehensive examples and patterns.

### Before (v1.x)

```python
# Create PR for ticket
mcp__mcp-ticketer__ticket_create_pr(
    ticket_id="TICKET-123",
    title="Fix authentication bug",
    description="Resolves TICKET-123",
    source_branch="fix/auth-bug",
    target_branch="main"
)

# Link existing PR
mcp__mcp-ticketer__ticket_link_pr(
    ticket_id="TICKET-123",
    pr_url="https://github.com/org/repo/pull/42"
)
```

### After (v2.0)

```python
# Use GitHub MCP + ticket comment

# 1. Create PR via GitHub MCP
pr = mcp__github__create_pull_request(
    owner="myorg",
    repo="myrepo",
    title="Fix authentication bug",
    head="fix/auth-bug",
    base="main",
    body="""
Resolves TICKET-123

## Changes
- Fixed JWT validation
- Added token refresh mechanism
- Updated tests

## Testing
- All tests passing
- Manual testing complete
    """
)

# 2. Link PR in ticket
mcp__mcp-ticketer__ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text=f"Pull Request: {pr['html_url']}"
)

# 3. Optional: Update ticket state
mcp__mcp-ticketer__ticket_update(
    ticket_id="TICKET-123",
    state="in_review"
)
```

**Benefits:**
- Direct GitHub integration
- More PR control (reviewers, labels, etc.)
- Consistent with GitHub workflow

**CLI Availability:**
These tools remain available via CLI:
```bash
aitrackdown pr create TICKET-123 --branch fix/auth
aitrackdown pr link TICKET-123 https://github.com/org/repo/pull/42
```

**Migration Checklist:**
- [ ] Identify all ticket_create_pr/ticket_link_pr usage
- [ ] Update code to use GitHub MCP
- [ ] Add ticket comments linking PRs
- [ ] Test PR creation workflow

---

## Bulk Operations

**Changed:** Merged into standard operations

### Before (v1.x)

```python
# Bulk create
mcp__mcp-ticketer__ticket_bulk_create(
    tickets=[
        {"title": "Bug 1", "priority": "high"},
        {"title": "Bug 2", "priority": "medium"},
        {"title": "Bug 3", "priority": "low"}
    ]
)

# Bulk update
mcp__mcp-ticketer__ticket_bulk_update(
    updates=[
        {"ticket_id": "TICKET-123", "state": "done"},
        {"ticket_id": "TICKET-124", "state": "done"},
        {"ticket_id": "TICKET-125", "priority": "high"}
    ]
)
```

### After (v2.0)

```python
# Create handles both single and bulk automatically

# Single ticket (dict)
mcp__mcp-ticketer__ticket_create(
    data={"title": "Bug 1", "priority": "high"}
)

# Bulk tickets (array of dicts)
mcp__mcp-ticketer__ticket_create(
    data=[
        {"title": "Bug 1", "priority": "high"},
        {"title": "Bug 2", "priority": "medium"},
        {"title": "Bug 3", "priority": "low"}
    ]
)

# Update handles both single and bulk automatically

# Single update (dict)
mcp__mcp-ticketer__ticket_update(
    data={"ticket_id": "TICKET-123", "state": "done"}
)

# Bulk updates (array of dicts)
mcp__mcp-ticketer__ticket_update(
    data=[
        {"ticket_id": "TICKET-123", "state": "done"},
        {"ticket_id": "TICKET-124", "state": "done"},
        {"ticket_id": "TICKET-125", "priority": "high"}
    ]
)
```

**Response Format:**

Single operation:
```python
{
    "status": "success",
    "ticket": {"id": "TICKET-123", ...}
}
```

Bulk operation:
```python
{
    "status": "success",  # or "partial" if some failed
    "results": [
        {"index": 0, "status": "success", "ticket": {...}},
        {"index": 1, "status": "success", "ticket": {...}},
        {"index": 2, "status": "error", "error": "..."}
    ],
    "succeeded": 2,
    "failed": 1,
    "total": 3
}
```

**Migration Pattern:**
- Replace `ticket_bulk_create(tickets=[...])` with `ticket_create(data=[...])`
- Replace `ticket_bulk_update(updates=[...])` with `ticket_update(data=[...])`
- Response format matches input (single → single, bulk → bulk)

---

## User/Session Management

**Changed:** 3 tools → 1 unified tool

### Before (v1.x)

```python
# Get my tickets
mcp__mcp-ticketer__get_my_tickets(
    state="in_progress",
    project_id="proj-123",
    limit=10
)

# Attach session to ticket
mcp__mcp-ticketer__attach_ticket(
    action="set",
    ticket_id="TICKET-123"
)

# Clear session attachment
mcp__mcp-ticketer__attach_ticket(action="clear")

# Get session info
mcp__mcp-ticketer__get_session_info()
```

### After (v2.0)

```python
# Get my tickets
mcp__mcp-ticketer__user(
    action="get_tickets",
    state="in_progress",
    project_id="proj-123",
    limit=10
)

# Attach session to ticket
mcp__mcp-ticketer__user(
    action="attach_ticket",
    ticket_id="TICKET-123"
)

# Detach session from ticket
mcp__mcp-ticketer__user(action="detach_ticket")

# Get session info
mcp__mcp-ticketer__user(action="session_info")
```

**Migration Pattern:**
- `get_my_tickets(...)` → `user(action="get_tickets", ...)`
- `attach_ticket(action="set", ...)` → `user(action="attach_ticket", ...)`
- `attach_ticket(action="clear")` → `user(action="detach_ticket")`
- `get_session_info()` → `user(action="session_info")`

---

## Hierarchy Management

**Changed:** 11 tools → 1 unified tool

This is the most significant consolidation in v2.0.

### Before (v1.x)

```python
# Epic operations
mcp__mcp-ticketer__epic_create(title="Q4 Features", target_date="2025-12-31")
mcp__mcp-ticketer__epic_get(epic_id="epic-123")
mcp__mcp-ticketer__epic_update(epic_id="epic-123", state="active")
mcp__mcp-ticketer__epic_delete(epic_id="epic-123")
mcp__mcp-ticketer__epic_list(limit=10)
mcp__mcp-ticketer__epic_issues(epic_id="epic-123")

# Issue operations
mcp__mcp-ticketer__issue_create(title="Feature", epic_id="epic-123")
mcp__mcp-ticketer__issue_get_parent(issue_id="issue-456")
mcp__mcp-ticketer__issue_tasks(issue_id="issue-456")

# Task operations
mcp__mcp-ticketer__task_create(title="Write tests", issue_id="issue-456")

# Hierarchy traversal
mcp__mcp-ticketer__hierarchy_tree(epic_id="epic-123", max_depth=3)
```

### After (v2.0)

```python
# Epic operations
mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="create",
    data={"title": "Q4 Features", "target_date": "2025-12-31"}
)

mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="read",
    resource_id="epic-123"
)

mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="update",
    resource_id="epic-123",
    data={"state": "active"}
)

mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="delete",
    resource_id="epic-123"
)

mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="list",
    limit=10
)

mcp__mcp-ticketer__hierarchy(
    resource="epic",
    action="children",  # Replaces epic_issues
    resource_id="epic-123"
)

# Issue operations
mcp__mcp-ticketer__hierarchy(
    resource="issue",
    action="create",
    data={"title": "Feature", "epic_id": "epic-123"}
)

mcp__mcp-ticketer__hierarchy(
    resource="issue",
    action="parent",  # Replaces issue_get_parent
    resource_id="issue-456"
)

mcp__mcp-ticketer__hierarchy(
    resource="issue",
    action="children",  # Replaces issue_tasks
    resource_id="issue-456"
)

# Task operations
mcp__mcp-ticketer__hierarchy(
    resource="task",
    action="create",
    data={"title": "Write tests", "issue_id": "issue-456"}
)

# Hierarchy traversal
mcp__mcp-ticketer__hierarchy(
    resource="tree",
    action="read",
    resource_id="epic-123",
    max_depth=3
)
```

**Resource-Action Matrix:**

| Resource | Available Actions |
|----------|------------------|
| epic | create, read, update, delete, list, children |
| issue | create, parent, children |
| task | create |
| tree | read |

**Migration Pattern:**

1. Identify resource type (epic/issue/task/tree)
2. Identify action (create/read/update/delete/list/children/parent)
3. Map parameters:
   - `{resource}_id` → `resource_id`
   - Data fields → `data` dict
   - Filters → keep as kwargs

**Common Migrations:**

```python
# Epic create
epic_create(title="Sprint 1", description="Q1 Sprint")
→ hierarchy(resource="epic", action="create", data={"title": "Sprint 1", "description": "Q1 Sprint"})

# Epic get
epic_get(epic_id="epic-123")
→ hierarchy(resource="epic", action="read", resource_id="epic-123")

# Epic issues
epic_issues(epic_id="epic-123")
→ hierarchy(resource="epic", action="children", resource_id="epic-123")

# Issue create
issue_create(title="Feature", epic_id="epic-123")
→ hierarchy(resource="issue", action="create", data={"title": "Feature", "epic_id": "epic-123"})

# Issue parent
issue_get_parent(issue_id="issue-456")
→ hierarchy(resource="issue", action="parent", resource_id="issue-456")

# Issue tasks
issue_tasks(issue_id="issue-456", state="open")
→ hierarchy(resource="issue", action="children", resource_id="issue-456", state="open")

# Task create
task_create(title="Test", issue_id="issue-456")
→ hierarchy(resource="task", action="create", data={"title": "Test", "issue_id": "issue-456"})

# Hierarchy tree
hierarchy_tree(epic_id="epic-123", max_depth=3)
→ hierarchy(resource="tree", action="read", resource_id="epic-123", max_depth=3)
```

---

## Ticket CRUD

**Changed:** 8 tools → 1 unified tool

This affects the most commonly used tools.

### Before (v1.x)

```python
# Create ticket
mcp__mcp-ticketer__ticket_create(
    title="Fix bug",
    description="User can't login",
    priority="high",
    tags=["bug", "auth"],
    assignee="dev@example.com"
)

# Read ticket
mcp__mcp-ticketer__ticket_read(ticket_id="TICKET-123")

# Update ticket
mcp__mcp-ticketer__ticket_update(
    ticket_id="TICKET-123",
    state="in_progress",
    priority="critical"
)

# Delete ticket
mcp__mcp-ticketer__ticket_delete(ticket_id="TICKET-123")

# List tickets
mcp__mcp-ticketer__ticket_list(
    state="open",
    priority="high",
    limit=20
)

# Get ticket summary
mcp__mcp-ticketer__ticket_summary(ticket_id="TICKET-123")

# Get ticket activity
mcp__mcp-ticketer__ticket_latest(ticket_id="TICKET-123", limit=5)

# Assign ticket
mcp__mcp-ticketer__ticket_assign(
    ticket_id="TICKET-123",
    assignee="dev@example.com",
    auto_transition=True
)
```

### After (v2.0)

```python
# Create ticket
mcp__mcp-ticketer__ticket(
    action="create",
    data={
        "title": "Fix bug",
        "description": "User can't login",
        "priority": "high",
        "tags": ["bug", "auth"],
        "assignee": "dev@example.com"
    }
)

# Read ticket
mcp__mcp-ticketer__ticket(
    action="read",
    ticket_id="TICKET-123"
)

# Update ticket
mcp__mcp-ticketer__ticket(
    action="update",
    ticket_id="TICKET-123",
    data={
        "state": "in_progress",
        "priority": "critical"
    }
)

# Delete ticket
mcp__mcp-ticketer__ticket(
    action="delete",
    ticket_id="TICKET-123"
)

# List tickets
mcp__mcp-ticketer__ticket(
    action="list",
    state="open",
    priority="high",
    limit=20
)

# Get ticket summary
mcp__mcp-ticketer__ticket(
    action="summary",
    ticket_id="TICKET-123"
)

# Get ticket activity
mcp__mcp-ticketer__ticket(
    action="activity",
    ticket_id="TICKET-123",
    limit=5
)

# Assign ticket
mcp__mcp-ticketer__ticket(
    action="assign",
    ticket_id="TICKET-123",
    assignee="dev@example.com",
    auto_transition=True
)
```

**Migration Pattern:**

| Old Tool | New Action | Notes |
|----------|-----------|-------|
| ticket_create | action="create" | Parameters → data dict |
| ticket_read | action="read" | No changes to parameters |
| ticket_update | action="update" | Update fields → data dict |
| ticket_delete | action="delete" | No changes to parameters |
| ticket_list | action="list" | No changes to parameters |
| ticket_summary | action="summary" | No changes to parameters |
| ticket_latest | action="activity" | Renamed for clarity |
| ticket_assign | action="assign" | No changes to parameters |

---

## Testing Your Migration

### Unit Tests

Update your unit tests to use new tool signatures:

**Before:**
```python
def test_create_ticket():
    result = ticket_create(title="Test", priority="high")
    assert result["status"] == "success"
```

**After:**
```python
def test_create_ticket():
    result = ticket(action="create", data={"title": "Test", "priority": "high"})
    assert result["status"] == "success"
```

### Integration Tests

Test complete workflows with new tools:

```python
def test_ticket_lifecycle():
    """Test create → read → update → delete workflow."""

    # Create
    create_result = ticket(action="create", data={"title": "Test Bug"})
    ticket_id = create_result["ticket_id"]

    # Read
    read_result = ticket(action="read", ticket_id=ticket_id)
    assert read_result["title"] == "Test Bug"

    # Update
    update_result = ticket(action="update", ticket_id=ticket_id, data={"state": "done"})
    assert update_result["state"] == "done"

    # Delete
    delete_result = ticket(action="delete", ticket_id=ticket_id)
    assert delete_result["status"] == "success"
```

---

## Common Migration Patterns

### Pattern 1: Simple Tool Rename

**Before:** `tool_name(params)`
**After:** `unified_tool(action="action_name", params)`

```python
# Before
epic_get(epic_id="epic-123")

# After
hierarchy(resource="epic", action="read", resource_id="epic-123")
```

### Pattern 2: Parameters to Data Dict

**Before:** `tool(param1=value1, param2=value2)`
**After:** `unified_tool(action="action", data={"param1": value1, "param2": value2})`

```python
# Before
ticket_create(title="Bug", priority="high", assignee="dev@example.com")

# After
ticket(action="create", data={
    "title": "Bug",
    "priority": "high",
    "assignee": "dev@example.com"
})
```

### Pattern 3: Remove Tool + Use Alternative

**Before:** `removed_tool(params)`
**After:** `alternative_mcp_tool(params) + ticket_comment(...)`

```python
# Before
ticket_attach(ticket_id="TICKET-123", file_path="/path/to/file.pdf")

# After
mcp__filesystem__write_file(path="./docs/tickets/TICKET-123/file.pdf", ...)
ticket_comment(ticket_id="TICKET-123", operation="add", text="Attached: file.pdf")
```

---

## Troubleshooting

### Deprecation Warning Not Showing

**Problem:** Not seeing deprecation warnings in v1.5.0+

**Solution:**
```python
import warnings
warnings.simplefilter("always", DeprecationWarning)
```

### Tool Not Found Error

**Problem:** `AttributeError: tool 'ticket_create' not found` in v2.0+

**Solution:** Tool was removed. Use unified tool:
```python
# Old (removed)
ticket_create(title="Bug")

# New
ticket(action="create", data={"title": "Bug"})
```

### Response Format Changed

**Problem:** Response structure different in v2.0

**Solution:** Check if using bulk operations. Response format matches input:
- Single input (dict) → single response
- Bulk input (list) → bulk response with results array

### Performance Regression

**Problem:** Slower response times after migration

**Solution:**
1. Check routing overhead (should be < 5ms)
2. Review parameter validation
3. Report issue on GitHub

---

## Getting Help

### Resources

- **Documentation:** [docs/api/](https://github.com/yourusername/mcp-ticketer/tree/main/docs/api)
- **GitHub Issues:** [Report migration issues](https://github.com/yourusername/mcp-ticketer/issues)
- **Migration Tool:** `mcp-ticketer migrate --help`

### Community Support

- Open GitHub issue with `[Migration]` tag
- Include code examples (before/after)
- Provide error messages and stack traces

### Professional Support

Contact: support@mcp-ticketer.dev (if available)

---

## Appendix: Complete Tool Mapping

| v1.x Tool | v2.0 Equivalent | Notes |
|-----------|----------------|-------|
| project_update_create | project_update(action="create") | |
| project_update_get | project_update(action="get") | |
| project_update_list | project_update(action="list") | |
| ticket_search | ticket_search | No change |
| ticket_search_hierarchy | ticket_search(include_hierarchy=True) | Add parameter |
| ticket_attach | [Removed] Use filesystem MCP | See Attachments section |
| ticket_attachments | [Removed] Use filesystem MCP | See Attachments section |
| ticket_create_pr | [Removed] Use GitHub MCP | See PR section |
| ticket_link_pr | [Removed] Use GitHub MCP | See PR section |
| ticket_bulk_create | ticket_create(data=[...]) | Array input |
| ticket_bulk_update | ticket_update(data=[...]) | Array input |
| get_my_tickets | user(action="get_tickets") | |
| attach_ticket | user(action="attach_ticket"/"detach_ticket") | |
| get_session_info | user(action="session_info") | |
| epic_create | hierarchy(resource="epic", action="create") | |
| epic_get | hierarchy(resource="epic", action="read") | |
| epic_update | hierarchy(resource="epic", action="update") | |
| epic_delete | hierarchy(resource="epic", action="delete") | |
| epic_list | hierarchy(resource="epic", action="list") | |
| epic_issues | hierarchy(resource="epic", action="children") | |
| issue_create | hierarchy(resource="issue", action="create") | |
| issue_get_parent | hierarchy(resource="issue", action="parent") | |
| issue_tasks | hierarchy(resource="issue", action="children") | |
| task_create | hierarchy(resource="task", action="create") | |
| hierarchy_tree | hierarchy(resource="tree", action="read") | |
| ticket_create | ticket(action="create") | |
| ticket_read | ticket(action="read") | |
| ticket_update | ticket(action="update") | |
| ticket_delete | ticket(action="delete") | |
| ticket_list | ticket(action="list") | |
| ticket_summary | ticket(action="summary") | |
| ticket_latest | ticket(action="activity") | Renamed |
| ticket_assign | ticket(action="assign") | |

---

**Document Version:** 1.0 (Draft)
**Last Updated:** 2025-12-01
**Next Review:** After v1.5.0 release
