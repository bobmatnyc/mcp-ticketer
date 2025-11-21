# New Features Guide: Hierarchy Navigation & Ticket Assignment

**Version**: 1.0.6 (Unreleased)
**Features**: Linear Issues 1M-93, 1M-94
**Date**: 2025-11-21

---

## Overview

This guide covers three new powerful features added to MCP Ticketer:

1. **Parent Issue Lookup** (`issue_get_parent`) - Navigate hierarchy upward
2. **Enhanced Sub-Issue Filtering** (`issue_tasks`) - Filter child tasks by state, assignee, priority
3. **Ticket Assignment Tool** (`ticket_assign`) - Dedicated assignment with audit trail

These features enhance hierarchy navigation, team collaboration, and ticket organization workflows.

---

## Table of Contents

- [Parent Issue Lookup](#parent-issue-lookup)
- [Enhanced Sub-Issue Filtering](#enhanced-sub-issue-filtering)
- [Ticket Assignment Tool](#ticket-assignment-tool)
- [Common Use Cases](#common-use-cases)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Parent Issue Lookup

### Overview

The `issue_get_parent()` tool allows you to find the parent issue of any sub-issue. This is useful for:
- Understanding task context
- Navigating hierarchy upward
- Tracking work organization
- Building hierarchy visualizations

### MCP Tool Usage

```python
# Get parent of a sub-issue
await issue_get_parent(issue_id="ENG-842")
```

**Response Structure:**
```json
{
  "status": "completed",
  "parent": {
    "id": "abc-123",
    "identifier": "ENG-840",
    "title": "Implement hierarchy features",
    "state": "in_progress",
    "priority": "high",
    "assignee": "john@example.com",
    "description": "Add parent lookup and filtering",
    "created_at": "2025-11-15T10:00:00Z",
    "updated_at": "2025-11-20T15:30:00Z"
  },
  "adapter": "linear",
  "adapter_name": "Linear"
}
```

### Edge Cases

#### 1. Top-Level Issue (No Parent)
```python
await issue_get_parent(issue_id="ENG-840")
```
Response:
```json
{
  "status": "completed",
  "parent": null,
  "adapter": "linear"
}
```

#### 2. Invalid Issue ID
```python
await issue_get_parent(issue_id="INVALID-999")
```
Response:
```json
{
  "status": "error",
  "error": "Ticket INVALID-999 not found"
}
```

#### 3. Parent Not Found
If issue has `parent_issue` field but parent doesn't exist:
```json
{
  "status": "error",
  "error": "Parent issue abc-999 not found"
}
```

### Use Cases

#### Use Case 1: Context Lookup
When viewing a sub-task, quickly understand its parent context:
```python
# User viewing ENG-842
parent = await issue_get_parent(issue_id="ENG-842")
if parent["parent"]:
    print(f"This task is part of: {parent['parent']['title']}")
    print(f"Parent status: {parent['parent']['state']}")
```

#### Use Case 2: Hierarchy Traversal
Build a breadcrumb trail from child to root:
```python
async def get_breadcrumb_trail(issue_id: str) -> list:
    """Get full path from issue to root."""
    trail = []
    current_id = issue_id

    while current_id:
        result = await issue_get_parent(issue_id=current_id)
        if result["parent"]:
            trail.append({
                "id": result["parent"]["identifier"],
                "title": result["parent"]["title"]
            })
            current_id = result["parent"]["id"]
        else:
            break

    return list(reversed(trail))

# Example output:
# [
#   {"id": "ENG-100", "title": "Q4 Features"},
#   {"id": "ENG-840", "title": "Hierarchy Implementation"},
#   {"id": "ENG-842", "title": "Parent Lookup"}
# ]
```

#### Use Case 3: Validation
Verify issue belongs to correct parent:
```python
async def validate_issue_parent(issue_id: str, expected_parent_id: str) -> bool:
    """Verify issue is under correct parent."""
    result = await issue_get_parent(issue_id=issue_id)
    if result["status"] != "completed" or not result["parent"]:
        return False
    return result["parent"]["identifier"] == expected_parent_id
```

---

## Enhanced Sub-Issue Filtering

### Overview

The enhanced `issue_tasks()` tool allows filtering child tasks by state, assignee, and priority. This is useful for:
- Finding tasks by status
- Viewing team member workload
- Identifying high-priority blockers
- Generating filtered reports

### MCP Tool Usage

#### Basic Usage (Unchanged)
```python
# Get all child tasks (backward compatible)
await issue_tasks(issue_id="ENG-840")
```

#### Filter by State
```python
# Get only in-progress tasks
await issue_tasks(
    issue_id="ENG-840",
    state="in_progress"
)
```

#### Filter by Assignee
```python
# Get tasks assigned to specific user
await issue_tasks(
    issue_id="ENG-840",
    assignee="john@example.com"
)

# Case-insensitive partial match
await issue_tasks(
    issue_id="ENG-840",
    assignee="john"  # Matches "john@example.com"
)
```

#### Filter by Priority
```python
# Get high-priority tasks
await issue_tasks(
    issue_id="ENG-840",
    priority="high"
)
```

#### Multiple Filters (AND Logic)
```python
# Get high-priority, in-progress tasks assigned to John
await issue_tasks(
    issue_id="ENG-840",
    state="in_progress",
    assignee="john@example.com",
    priority="high"
)
```

### Response Structure

```json
{
  "status": "completed",
  "tasks": [
    {
      "id": "def-456",
      "identifier": "ENG-841",
      "title": "Add filtering support",
      "state": "in_progress",
      "priority": "high",
      "assignee": "john@example.com",
      "parent_issue": "ENG-840",
      ...
    },
    {
      "id": "ghi-789",
      "identifier": "ENG-843",
      "title": "Write tests",
      "state": "in_progress",
      "priority": "medium",
      "assignee": "john@example.com",
      ...
    }
  ],
  "count": 2,
  "filters_applied": {
    "state": "in_progress",
    "assignee": "john@example.com"
  },
  "adapter": "linear",
  "adapter_name": "Linear"
}
```

### Filter Options

#### State Filter
Valid values:
- `open` - Not yet started
- `in_progress` - Currently being worked on
- `ready` - Ready for review/testing
- `tested` - Testing complete
- `done` - Work complete
- `closed` - Issue closed
- `waiting` - Waiting on dependencies
- `blocked` - Blocked by impediments

#### Assignee Filter
- User ID (adapter-specific)
- Email address (case-insensitive)
- Partial matches supported
- Examples: `"user@example.com"`, `"user"`, `"USER@EXAMPLE.COM"`

#### Priority Filter
Valid values:
- `low` - Low priority
- `medium` - Normal priority
- `high` - High priority
- `critical` - Critical/urgent

### Use Cases

#### Use Case 1: Team Dashboard
Show each team member's active work:
```python
async def get_team_dashboard(epic_id: str, team_members: list[str]):
    """Generate dashboard showing each member's work."""
    dashboard = {}

    for member in team_members:
        result = await issue_tasks(
            issue_id=epic_id,
            assignee=member,
            state="in_progress"
        )
        dashboard[member] = {
            "active_tasks": result["count"],
            "tasks": [t["title"] for t in result["tasks"]]
        }

    return dashboard

# Example output:
# {
#   "john@example.com": {
#     "active_tasks": 3,
#     "tasks": ["Add filtering", "Write tests", "Update docs"]
#   },
#   "jane@example.com": {
#     "active_tasks": 2,
#     "tasks": ["Code review", "Deploy changes"]
#   }
# }
```

#### Use Case 2: Blocker Identification
Find all blocked high-priority tasks:
```python
async def find_critical_blockers(epic_id: str):
    """Find critical blocked tasks that need attention."""
    result = await issue_tasks(
        issue_id=epic_id,
        state="blocked",
        priority="critical"
    )

    return {
        "count": result["count"],
        "blockers": [
            {
                "id": task["identifier"],
                "title": task["title"],
                "assignee": task["assignee"]
            }
            for task in result["tasks"]
        ]
    }
```

#### Use Case 3: Sprint Planning
Get unassigned tasks ready for sprint assignment:
```python
async def get_available_work(epic_id: str):
    """Find tasks ready to be assigned."""
    result = await issue_tasks(
        issue_id=epic_id,
        state="open",
        assignee=None  # Unassigned tasks
    )

    # Sort by priority
    tasks_by_priority = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": []
    }

    for task in result["tasks"]:
        priority = task["priority"]
        tasks_by_priority[priority].append(task)

    return tasks_by_priority
```

#### Use Case 4: Progress Tracking
Calculate epic completion percentage:
```python
async def calculate_epic_progress(epic_id: str):
    """Calculate percentage of work completed."""
    # Get all tasks
    all_tasks = await issue_tasks(issue_id=epic_id)
    total = all_tasks["count"]

    # Get done tasks
    done_tasks = await issue_tasks(issue_id=epic_id, state="done")
    completed = done_tasks["count"]

    # Get in-progress tasks
    active_tasks = await issue_tasks(issue_id=epic_id, state="in_progress")
    in_progress = active_tasks["count"]

    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "percentage": (completed / total * 100) if total > 0 else 0
    }
```

---

## Ticket Assignment Tool

### Overview

The `ticket_assign()` tool provides dedicated assignment functionality with:
- URL support for multiple platforms
- Audit trail via comments
- Previous/new assignee tracking
- Unassignment capability

### MCP Tool Usage

#### Basic Assignment
```python
# Assign by ticket ID
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="user@example.com"
)
```

#### Assignment with Comment
```python
# Add explanation for assignment
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="user@example.com",
    comment="Taking ownership - have relevant experience"
)
```

#### Assignment via URL
```python
# Use full ticket URL (multi-platform)
await ticket_assign(
    ticket_id="https://linear.app/team/issue/ENG-840",
    assignee="john@example.com",
    comment="Reassigning to John"
)
```

#### Unassignment
```python
# Remove assignee
await ticket_assign(
    ticket_id="PROJ-123",
    assignee=None,
    comment="Moving back to backlog"
)
```

#### Reassignment
```python
# Change assignee with explanation
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="jane@example.com",
    comment="Reassigning to Jane who has domain expertise"
)
```

### Response Structure

```json
{
  "status": "completed",
  "ticket": {
    "id": "abc-123",
    "identifier": "PROJ-123",
    "title": "Fix authentication bug",
    "state": "in_progress",
    "assignee": "user@example.com",
    ...
  },
  "previous_assignee": "john@example.com",
  "new_assignee": "user@example.com",
  "comment_added": true,
  "adapter": "linear",
  "adapter_name": "Linear",
  "routed_from_url": false
}
```

### URL Support

The tool automatically detects platform from URLs:

#### Linear URLs
```python
ticket_assign(
    ticket_id="https://linear.app/company/issue/ENG-123",
    assignee="user@example.com"
)
```

#### GitHub URLs
```python
ticket_assign(
    ticket_id="https://github.com/owner/repo/issues/456",
    assignee="username"
)
```

#### JIRA URLs
```python
ticket_assign(
    ticket_id="https://company.atlassian.net/browse/PROJ-789",
    assignee="user@company.com"
)
```

#### Asana URLs
```python
ticket_assign(
    ticket_id="https://app.asana.com/0/1234567890/9876543210",
    assignee="user@example.com"
)
```

### User Resolution by Platform

Each platform has different user identifier formats:

| Platform | User Format | Examples |
|----------|-------------|----------|
| **Linear** | User ID (UUID) or email | `"550e8400-e29b-41d4-a716-446655440000"`, `"user@example.com"` |
| **GitHub** | Username | `"octocat"`, `"username"` |
| **JIRA** | Account ID or email | `"5b10a2844c20165700ede21g"`, `"user@company.com"` |
| **Asana** | User GID or email | `"1234567890123"`, `"user@example.com"` |

### Use Cases

#### Use Case 1: Workload Balancing
Reassign tickets to balance team workload:
```python
async def balance_workload(epic_id: str, team_members: dict):
    """Distribute work evenly across team."""
    # Get unassigned tasks
    unassigned = await issue_tasks(epic_id=epic_id, assignee=None, state="open")

    # Sort team by current workload
    sorted_team = sorted(
        team_members.items(),
        key=lambda x: x[1]["current_tickets"]
    )

    # Assign tasks round-robin
    for i, task in enumerate(unassigned["tasks"]):
        assignee_email = sorted_team[i % len(sorted_team)][0]

        await ticket_assign(
            ticket_id=task["identifier"],
            assignee=assignee_email,
            comment=f"Auto-assigned for workload balance"
        )
```

#### Use Case 2: Skill-Based Assignment
Assign based on expertise tags:
```python
async def assign_by_expertise(task_id: str, required_skills: list[str]):
    """Assign to team member with required skills."""
    # Find team members with required skills
    team_db = get_team_database()
    candidates = team_db.find_by_skills(required_skills)

    if candidates:
        # Assign to least busy qualified person
        assignee = min(candidates, key=lambda x: x["workload"])

        await ticket_assign(
            ticket_id=task_id,
            assignee=assignee["email"],
            comment=f"Assigned based on expertise in: {', '.join(required_skills)}"
        )
```

#### Use Case 3: Automatic Escalation
Reassign stale tickets to manager:
```python
async def escalate_stale_tickets(epic_id: str, days_threshold: int, manager_email: str):
    """Escalate tickets with no progress."""
    from datetime import datetime, timedelta

    # Get all in-progress tasks
    tasks = await issue_tasks(epic_id=epic_id, state="in_progress")

    cutoff_date = datetime.now() - timedelta(days=days_threshold)

    for task in tasks["tasks"]:
        updated_at = datetime.fromisoformat(task["updated_at"])

        if updated_at < cutoff_date:
            await ticket_assign(
                ticket_id=task["identifier"],
                assignee=manager_email,
                comment=f"Escalated: No updates in {days_threshold} days"
            )
```

#### Use Case 4: URL-Based Workflows
Handle tickets from different platforms:
```python
async def handle_cross_platform_assignment(ticket_urls: list[str], assignee: str):
    """Assign tickets from multiple platforms."""
    results = []

    for url in ticket_urls:
        result = await ticket_assign(
            ticket_id=url,  # URL automatically routed to correct adapter
            assignee=assignee,
            comment="Bulk assignment from cross-platform workflow"
        )

        results.append({
            "url": url,
            "success": result["status"] == "completed",
            "platform": result.get("adapter_name", "unknown")
        })

    return results

# Example:
# urls = [
#     "https://linear.app/team/issue/ENG-1",
#     "https://github.com/org/repo/issues/42",
#     "https://company.atlassian.net/browse/PROJ-7"
# ]
# handle_cross_platform_assignment(urls, "john@example.com")
```

---

## Common Use Cases

### Scenario 1: Sprint Planning Dashboard

Build a comprehensive sprint planning view:

```python
async def generate_sprint_dashboard(epic_id: str):
    """Generate complete sprint planning dashboard."""

    # 1. Get all tasks
    all_tasks = await issue_tasks(issue_id=epic_id)

    # 2. Break down by status
    open_tasks = await issue_tasks(epic_id=epic_id, state="open")
    in_progress = await issue_tasks(epic_id=epic_id, state="in_progress")
    blocked = await issue_tasks(epic_id=epic_id, state="blocked")
    done_tasks = await issue_tasks(epic_id=epic_id, state="done")

    # 3. Get high-priority items
    high_priority = await issue_tasks(epic_id=epic_id, priority="high")
    critical = await issue_tasks(epic_id=epic_id, priority="critical")

    # 4. Team workload
    team_emails = ["john@ex.com", "jane@ex.com", "bob@ex.com"]
    workload = {}
    for email in team_emails:
        active = await issue_tasks(epic_id=epic_id, assignee=email, state="in_progress")
        workload[email] = active["count"]

    return {
        "total_tasks": all_tasks["count"],
        "open": open_tasks["count"],
        "in_progress": in_progress["count"],
        "blocked": blocked["count"],
        "done": done_tasks["count"],
        "completion_pct": (done_tasks["count"] / all_tasks["count"] * 100) if all_tasks["count"] > 0 else 0,
        "high_priority_count": high_priority["count"],
        "critical_count": critical["count"],
        "team_workload": workload
    }
```

### Scenario 2: Automated Triage System

Automatically assign new tickets based on rules:

```python
async def auto_triage_tickets(epic_id: str, triage_rules: dict):
    """Automatically assign tickets based on rules."""

    # Get unassigned open tickets
    unassigned = await issue_tasks(
        issue_id=epic_id,
        state="open",
        assignee=None
    )

    for task in unassigned["tasks"]:
        # Determine assignee based on rules
        assignee = None
        comment = ""

        # Rule 1: Critical priority → team lead
        if task["priority"] == "critical":
            assignee = triage_rules["team_lead"]
            comment = "Auto-assigned to team lead (critical priority)"

        # Rule 2: Backend tag → backend specialist
        elif "backend" in task.get("tags", []):
            assignee = triage_rules["backend_specialist"]
            comment = "Auto-assigned to backend specialist"

        # Rule 3: Bug tag → QA engineer
        elif "bug" in task.get("tags", []):
            assignee = triage_rules["qa_engineer"]
            comment = "Auto-assigned to QA engineer (bug report)"

        # Rule 4: Default → round-robin
        else:
            assignee = triage_rules["default_assignee"]
            comment = "Auto-assigned via round-robin"

        if assignee:
            await ticket_assign(
                ticket_id=task["identifier"],
                assignee=assignee,
                comment=comment
            )
```

### Scenario 3: Hierarchy Explorer

Build an interactive hierarchy explorer:

```python
async def explore_hierarchy(issue_id: str, max_depth: int = 3):
    """Explore full hierarchy around an issue."""

    # Get parent chain
    parents = []
    current_id = issue_id

    while current_id and len(parents) < max_depth:
        parent_result = await issue_get_parent(issue_id=current_id)
        if parent_result["parent"]:
            parents.append(parent_result["parent"])
            current_id = parent_result["parent"]["id"]
        else:
            break

    # Get children
    children_result = await issue_tasks(issue_id=issue_id)
    children = children_result["tasks"]

    # Get siblings (parent's other children)
    siblings = []
    if parents:
        parent_id = parents[0]["id"]
        siblings_result = await issue_tasks(issue_id=parent_id)
        siblings = [
            t for t in siblings_result["tasks"]
            if t["id"] != issue_id
        ]

    return {
        "ancestors": list(reversed(parents)),
        "current": issue_id,
        "children": children,
        "siblings": siblings
    }
```

---

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
async def safe_parent_lookup(issue_id: str):
    """Safely get parent with error handling."""
    try:
        result = await issue_get_parent(issue_id=issue_id)

        if result["status"] == "error":
            logger.error(f"Failed to get parent: {result['error']}")
            return None

        return result["parent"]

    except Exception as e:
        logger.exception(f"Unexpected error getting parent: {e}")
        return None
```

### 2. Filter Validation

Validate filter values before use:

```python
VALID_STATES = ["open", "in_progress", "ready", "tested", "done", "closed", "waiting", "blocked"]
VALID_PRIORITIES = ["low", "medium", "high", "critical"]

async def filtered_tasks_safe(issue_id: str, state: str = None, priority: str = None):
    """Get filtered tasks with validation."""
    # Validate filters
    if state and state not in VALID_STATES:
        raise ValueError(f"Invalid state: {state}. Must be one of {VALID_STATES}")

    if priority and priority not in VALID_PRIORITIES:
        raise ValueError(f"Invalid priority: {priority}. Must be one of {VALID_PRIORITIES}")

    return await issue_tasks(
        issue_id=issue_id,
        state=state,
        priority=priority
    )
```

### 3. Assignment Comments

Always provide meaningful comments:

```python
# ✅ Good: Clear explanation
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="user@example.com",
    comment="Reassigning to Sarah who has experience with this codebase"
)

# ❌ Bad: No context
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="user@example.com"
)

# ✅ Good: Audit trail
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="manager@example.com",
    comment="Escalated: No response from assignee for 5 days"
)
```

### 4. Batch Operations

Use efficient patterns for batch operations:

```python
async def batch_filter_tasks(epic_id: str, filters: list[dict]):
    """Efficiently run multiple filters."""
    results = {}

    # Run filters in parallel
    import asyncio

    tasks = []
    for filter_spec in filters:
        task = issue_tasks(
            issue_id=epic_id,
            state=filter_spec.get("state"),
            assignee=filter_spec.get("assignee"),
            priority=filter_spec.get("priority")
        )
        tasks.append(task)

    # Wait for all
    responses = await asyncio.gather(*tasks)

    # Build results
    for filter_spec, response in zip(filters, responses):
        key = f"{filter_spec.get('state', 'all')}_{filter_spec.get('assignee', 'all')}"
        results[key] = response["count"]

    return results
```

### 5. URL vs ID Decision

Choose the right input format:

```python
# Use IDs when working within single platform
await ticket_assign(
    ticket_id="PROJ-123",  # Simple ID
    assignee="user@example.com"
)

# Use URLs when:
# - Accepting user input (copy-paste from browser)
# - Cross-platform workflows
# - Building integrations
await ticket_assign(
    ticket_id="https://linear.app/team/issue/ENG-840",  # Full URL
    assignee="user@example.com"
)
```

---

## Troubleshooting

### Issue: Parent not found

**Symptom**: `issue_get_parent` returns error "Parent issue not found"

**Causes**:
1. Parent was deleted
2. Parent moved to different team/project
3. Data inconsistency

**Solution**:
```python
result = await issue_get_parent(issue_id="ENG-842")
if result["status"] == "error":
    if "not found" in result["error"]:
        # Handle missing parent
        logger.warning(f"Orphaned issue: {issue_id}")
        # Optionally reassign to new parent
```

### Issue: Filter returns no results

**Symptom**: `issue_tasks` with filters returns empty list

**Debugging**:
```python
# 1. Verify parent has children
all_tasks = await issue_tasks(issue_id="ENG-840")
print(f"Total children: {all_tasks['count']}")

# 2. Check filter values are valid
result = await issue_tasks(
    issue_id="ENG-840",
    state="in_progress"  # Verify exact state value
)
print(f"In-progress tasks: {result['count']}")

# 3. Try filters individually
by_state = await issue_tasks(issue_id="ENG-840", state="in_progress")
by_assignee = await issue_tasks(issue_id="ENG-840", assignee="john@example.com")
by_priority = await issue_tasks(issue_id="ENG-840", priority="high")

# 4. Check combined filters
combined = await issue_tasks(
    issue_id="ENG-840",
    state="in_progress",
    assignee="john@example.com",
    priority="high"
)
```

### Issue: Assignment fails with URL

**Symptom**: `ticket_assign` with URL returns error

**Debugging**:
```python
# 1. Verify URL format
url = "https://linear.app/team/issue/ENG-840"
print(f"Platform detected: {detect_platform(url)}")

# 2. Check adapter is configured
config = load_config()
print(f"Available adapters: {config.keys()}")

# 3. Test with plain ID first
result = await ticket_assign(
    ticket_id="ENG-840",  # Use ID instead of URL
    assignee="user@example.com"
)

# 4. Verify multi-platform setup
# See docs on configuring multi-platform routing
```

### Issue: Case sensitivity in assignee filter

**Symptom**: Filter doesn't match expected assignee

**Solution**: The assignee filter is case-insensitive and supports partial matches:

```python
# All of these will match "John.Doe@Example.com"
await issue_tasks(issue_id="ENG-840", assignee="john")
await issue_tasks(issue_id="ENG-840", assignee="JOHN")
await issue_tasks(issue_id="ENG-840", assignee="john.doe")
await issue_tasks(issue_id="ENG-840", assignee="@example.com")

# For exact match, retrieve and filter manually:
result = await issue_tasks(issue_id="ENG-840")
exact_matches = [
    t for t in result["tasks"]
    if t["assignee"] == "exact.email@example.com"
]
```

---

## Migration Notes

### From `ticket_update` to `ticket_assign`

**Before** (using generic update):
```python
await ticket_update(
    ticket_id="PROJ-123",
    updates={"assignee": "user@example.com"}
)
```

**After** (using dedicated assignment):
```python
await ticket_assign(
    ticket_id="PROJ-123",
    assignee="user@example.com",
    comment="Assignment with audit trail"
)
```

**Benefits of migration**:
- ✅ Previous assignee tracking
- ✅ Audit trail via comments
- ✅ URL support
- ✅ Clearer intent

### Backward Compatibility

All new features are fully backward compatible:

```python
# Old code continues to work
tasks = await issue_tasks(issue_id="ENG-840")

# New filtering is opt-in
filtered_tasks = await issue_tasks(
    issue_id="ENG-840",
    state="in_progress"  # New parameter
)
```

---

## Additional Resources

- **API Reference**: See [API_REFERENCE.md](developer-docs/api/API_REFERENCE.md) for complete tool signatures
- **Implementation Details**: See [IMPLEMENTATION_SUMMARY_1M-93.md](../IMPLEMENTATION_SUMMARY_1M-93.md)
- **Test Reports**: See [TEST_REPORT_LINEAR_1M-93.md](../TEST_REPORT_LINEAR_1M-93.md)
- **Release Notes**: See [CHANGELOG.md](../CHANGELOG.md)

---

## Feedback

Have questions or suggestions? Please:
- Open an issue on GitHub
- Refer to Linear issues 1M-93 and 1M-94
- Check the troubleshooting section above

---

**Last Updated**: 2025-11-21
**Version**: 1.0.6 (Unreleased)
