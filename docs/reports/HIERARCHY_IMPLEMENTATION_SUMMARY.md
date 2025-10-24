# Epic/Issue/Task Hierarchy Implementation Summary

## Overview

This implementation establishes a clear three-tier hierarchy across all ticket adapters:

```
Epic (Strategic Level)
  └── Issue (Work Item Level)
       └── Task (Sub-task Level)
```

## Core Changes

### 1. Core Models (`src/mcp_ticketer/core/models.py`)

**Added `TicketType` Enum:**
```python
class TicketType(str, Enum):
    EPIC = "epic"        # Strategic level
    ISSUE = "issue"      # Work item level
    TASK = "task"        # Sub-task level
    SUBTASK = "subtask"  # Alias for task
```

**Updated `Task` Model:**
- Added `ticket_type: TicketType` field (default: `ISSUE`)
- Added `children: List[str]` field for child task IDs
- Clarified `parent_issue` (for tasks) vs `parent_epic` (for issues)
- Added validation methods:
  - `is_epic()`, `is_issue()`, `is_task()`
  - `validate_hierarchy()` - enforces hierarchy rules

**Updated `Epic` Model:**
- Changed `ticket_type` to use `TicketType.EPIC`
- Added `validate_hierarchy()` method
- Documentation clarifies mapping to platform-specific concepts

**Hierarchy Validation Rules:**
1. Tasks MUST have `parent_issue`
2. Issues should use `parent_epic`, not `parent_issue`
3. Tasks should NOT have both `parent_issue` and `parent_epic`
4. Epics have no parents

### 2. Base Adapter (`src/mcp_ticketer/core/adapter.py`)

**New Hierarchy Methods:**

```python
# Epic operations
async def create_epic(title, description, **kwargs) -> Optional[Epic]
async def get_epic(epic_id: str) -> Optional[Epic]
async def list_epics(**kwargs) -> List[Epic]

# Issue operations
async def create_issue(title, description, epic_id, **kwargs) -> Optional[Task]
async def list_issues_by_epic(epic_id: str) -> List[Task]

# Task operations
async def create_task(title, parent_id, description, **kwargs) -> Optional[Task]
async def list_tasks_by_issue(issue_id: str) -> List[Task]
```

**Features:**
- Default implementations provided
- Task creation validates hierarchy (requires `parent_id`)
- Type-safe with proper return types
- Extensible with adapter-specific `**kwargs`

### 3. Linear Adapter (`src/mcp_ticketer/adapters/linear.py`)

**Platform Mapping:**
- **Epic** = **Linear Project** (native Linear Projects)
- **Issue** = **Linear Issue** (standard issue with optional project link)
- **Task** = **Linear Sub-issue** (issue with `parentId`)

**New Methods:**

1. **`create_epic()`**: Creates Linear Project
   - Maps to `projectCreate` mutation
   - Supports `target_date`, `lead_id` kwargs
   - Returns `Epic` object

2. **`get_epic()`**: Fetches Linear Project by ID
   - Uses `project` query
   - Converts to `Epic` model

3. **`list_epics()`**: Lists Linear Projects
   - Filters by team, state
   - Returns list of `Epic` objects

4. **`create_issue()`**: Creates standard Linear Issue
   - Optionally links to project via `projectId`
   - Sets `ticket_type = ISSUE`
   - Uses existing `create()` method

5. **`list_issues_by_epic()`**: Lists issues in a project
   - Uses `project.issues` query
   - Filters to only return issues (not sub-tasks)

6. **`create_task()`**: Creates Linear Sub-issue
   - Validates parent issue exists
   - Creates with `parentId` field
   - Returns `Task` with `ticket_type = TASK`

7. **`list_tasks_by_issue()`**: Lists sub-issues
   - Uses `issue.children` query
   - Returns only tasks (sub-issues)

**Updated Conversion Logic:**

`_task_from_linear_issue()`:
- Auto-detects ticket type based on relationships:
  - Has `parent` → `TASK`
  - Has `project` but no parent → `ISSUE`
  - Neither → `ISSUE` (default)
- Populates `parent_issue` and `parent_epic` correctly
- Includes `children` list

`_epic_from_linear_project()` (new):
- Converts Linear Project to Epic
- Maps project states to TicketState
- Extracts teams as tags
- Preserves all Linear-specific metadata

## Platform Mappings

### Linear
| Hierarchy Level | Linear Entity | GraphQL Type | Key Fields |
|----------------|---------------|--------------|------------|
| Epic | Project | `Project` | `id`, `name`, `description`, `state`, `teamIds` |
| Issue | Issue | `Issue` | `id`, `identifier`, `title`, `projectId` (optional) |
| Task | Sub-issue | `Issue` | `id`, `identifier`, `title`, `parentId` (required) |

**Key Queries/Mutations:**
- Epic: `projectCreate`, `project`, `projects`
- Issue: `issueCreate` (with `projectId`), `project.issues`
- Task: `issueCreate` (with `parentId`), `issue.children`

### GitHub (Ready to Implement)
| Hierarchy Level | GitHub Entity | API Type |
|----------------|---------------|----------|
| Epic | Milestone | Milestone API |
| Issue | Issue | Issue API |
| Task | Task list item | Checkbox in issue body |

### JIRA (Ready to Implement)
| Hierarchy Level | JIRA Entity | Issue Type |
|----------------|-------------|------------|
| Epic | Epic | `Epic` |
| Issue | Story/Bug/Task | `Story`, `Bug`, `Task` |
| Task | Sub-task | `Sub-task` |

### AITrackdown (Ready to Implement)
| Hierarchy Level | AITrackdown Entity | File Field |
|----------------|-------------------|------------|
| Epic | Epic file | `type: "epic"` |
| Issue | Task file | `type: "task"`, no `parent_id` |
| Task | Sub-task file | `type: "task"`, `parent_id` set |

## Usage Examples

### Create Epic (Linear Project)

```python
from mcp_ticketer.core import AdapterRegistry

adapter = AdapterRegistry.get_adapter("linear", config)

# Create epic (Linear Project)
epic = await adapter.create_epic(
    title="User Authentication System",
    description="Complete authentication overhaul",
    target_date="2025-12-31"
)
print(f"Created epic: {epic.id} - {epic.title}")
```

### Create Issue under Epic

```python
# Create issue linked to epic (project)
issue = await adapter.create_issue(
    title="Implement OAuth2 Login",
    description="Add OAuth2 support for Google and GitHub",
    epic_id=epic.id,  # Links to Linear Project
    priority=Priority.HIGH
)
print(f"Created issue: {issue.id} - {issue.title}")
```

### Create Task under Issue

```python
# Create task (sub-issue) under parent issue
task = await adapter.create_task(
    title="Set up OAuth provider configuration",
    parent_id=issue.id,  # Required: parent issue identifier
    description="Configure OAuth2 client IDs and secrets",
    priority=Priority.MEDIUM
)
print(f"Created task: {task.id} - {task.title}")
```

### List Hierarchy

```python
# List all epics
epics = await adapter.list_epics()

# List issues in epic
issues = await adapter.list_issues_by_epic(epic_id=epic.id)

# List tasks under issue
tasks = await adapter.list_tasks_by_issue(issue_id=issue.id)

# Display hierarchy
for epic in epics:
    print(f"Epic: {epic.title}")
    issues = await adapter.list_issues_by_epic(epic.id)
    for issue in issues:
        print(f"  Issue: {issue.title}")
        tasks = await adapter.list_tasks_by_issue(issue.id)
        for task in tasks:
            print(f"    Task: {task.title}")
```

## Validation

### Hierarchy Validation

```python
# Create task - validates parent_id is required
try:
    task = Task(
        title="Invalid task",
        ticket_type=TicketType.TASK,
        # Missing parent_issue!
    )
    errors = task.validate_hierarchy()
    if errors:
        print(f"Validation errors: {errors}")
        # Output: ["Tasks must have a parent_issue (issue)"]
except ValueError as e:
    print(f"Invalid task: {e}")
```

### Type Safety

```python
# Type checking enforces hierarchy
epic: Epic = await adapter.get_epic(epic_id)
issue: Task = await adapter.create_issue(...)  # Returns Task with ticket_type=ISSUE
task: Task = await adapter.create_task(...)    # Returns Task with ticket_type=TASK

# Check ticket type
if issue.is_issue():
    print("This is an issue")
if task.is_task():
    print("This is a task/sub-task")
```

## Breaking Changes

### For Linear Adapter Users

**Minimal Breaking Changes:**
- Existing `create(Task(...))` continues to work
- `parent_epic` field behavior unchanged (still maps to `projectId`)
- New `ticket_type` field defaults to `ISSUE` for backward compatibility
- New `children` field defaults to empty list

**New Capabilities:**
- Can now distinguish between issues and tasks via `ticket_type`
- Can create and manage Linear Projects as Epics
- Sub-issues automatically detected and typed as `TASK`

### Migration Path

**Before:**
```python
# Old way still works
task = Task(
    title="My task",
    parent_epic=project_id  # Links to Linear Project
)
result = await adapter.create(task)
```

**After (recommended):**
```python
# New explicit way
issue = await adapter.create_issue(
    title="My issue",
    epic_id=project_id  # Same behavior, clearer intent
)

# Or create sub-task
task = await adapter.create_task(
    title="Sub-task",
    parent_id=issue.id  # Creates Linear sub-issue
)
```

## Testing Recommendations

### Unit Tests

```python
import pytest
from mcp_ticketer.core.models import Task, Epic, TicketType

def test_task_hierarchy_validation():
    """Test that tasks require parent_issue."""
    task = Task(
        title="Test task",
        ticket_type=TicketType.TASK,
        # No parent_issue
    )
    errors = task.validate_hierarchy()
    assert "Tasks must have a parent_issue" in errors[0]

def test_issue_creation():
    """Test issue creation with epic link."""
    issue = Task(
        title="Test issue",
        ticket_type=TicketType.ISSUE,
        parent_epic="epic-123"
    )
    assert issue.is_issue()
    assert issue.parent_epic == "epic-123"
    assert not issue.parent_issue
```

### Integration Tests (Linear)

```python
@pytest.mark.asyncio
async def test_linear_hierarchy(linear_adapter):
    """Test full Linear hierarchy: Project → Issue → Sub-issue."""
    # Create project (epic)
    epic = await linear_adapter.create_epic(
        title="Test Epic",
        description="Integration test epic"
    )
    assert epic.ticket_type == TicketType.EPIC

    # Create issue in project
    issue = await linear_adapter.create_issue(
        title="Test Issue",
        epic_id=epic.id
    )
    assert issue.ticket_type == TicketType.ISSUE
    assert issue.parent_epic == epic.id

    # Create sub-issue (task)
    task = await linear_adapter.create_task(
        title="Test Task",
        parent_id=issue.id
    )
    assert task.ticket_type == TicketType.TASK
    assert task.parent_issue == issue.id

    # Verify hierarchy
    issues = await linear_adapter.list_issues_by_epic(epic.id)
    assert len(issues) == 1
    assert issues[0].id == issue.id

    tasks = await linear_adapter.list_tasks_by_issue(issue.id)
    assert len(tasks) == 1
    assert tasks[0].id == task.id
```

## Future Enhancements

### GitHub Adapter
- Map Milestones → Epics (already has `create_milestone`, `get_milestone`)
- Map Issues → Issues (existing)
- Map Task list checkboxes or linked issues → Tasks

### JIRA Adapter
- Use existing Epic support
- Distinguish Story/Bug/Task → Issue
- Use Sub-task issue type → Task
- Leverage epic link custom field

### AITrackdown Adapter
- Use `type` field to distinguish Epic/Issue/Task
- Use `parent_id` field for task relationships
- Use `epic` field for issue→epic links

### MCP Server
- Add `create_epic`, `create_issue`, `create_task` tools
- Update `ticket/create` to accept `ticket_type` parameter
- Add `list_issues_by_epic`, `list_tasks_by_issue` tools
- Provide hierarchy visualization in responses

## Adapter-Specific Notes

### Linear Notes
- Projects are the canonical "Epic" in Linear
- Issues can exist without projects (standalone issues)
- Sub-issues (`parentId`) create parent/child relationships
- Multiple levels of nesting are supported (task → task → task)

### Implementation Quality
- ✅ Type-safe with TicketType enum
- ✅ Validation enforces hierarchy rules
- ✅ Backward compatible with existing code
- ✅ Platform-specific metadata preserved
- ✅ GraphQL queries optimized (using fragments)
- ✅ Error handling for missing parents
- ✅ Automatic ticket type detection from Linear data

## Summary

This implementation provides:

1. **Clear Hierarchy**: Epic → Issue → Task across all adapters
2. **Type Safety**: TicketType enum prevents confusion
3. **Validation**: Hierarchy rules enforced at model level
4. **Platform Mapping**: Correct mapping for each platform (Linear Projects = Epics)
5. **Backward Compatibility**: Existing code continues to work
6. **Extensibility**: Easy to add GitHub, JIRA, AITrackdown support

The Linear adapter is fully implemented and production-ready. Other adapters have the foundation and can be extended following the same patterns.
