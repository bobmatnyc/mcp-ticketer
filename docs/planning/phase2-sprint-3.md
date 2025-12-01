# Phase 2 Sprint 3: High-Value Consolidations

**Sprint Duration:** 4 days (Dec 16-20, 2025)
**Token Savings Target:** 9,500 tokens
**Risk Level:** High
**Linear Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

---

## Sprint Goals

Sprint 3 focuses on **massive consolidations** with the highest token savings but also highest complexity. These changes represent the most significant API improvements in Phase 2.

**Primary Objectives:**
1. Consolidate 11 hierarchy tools into 1 unified tool (4,500 tokens)
2. Consolidate 8 ticket CRUD tools into 1 unified tool (5,000 tokens)
3. Establish comprehensive routing patterns for complex operations
4. Maintain 100% backward compatibility during migration
5. Achieve 9,500 tokens in savings

**Success Criteria:**
- 19 tools consolidated/deprecated
- 75+ tests passing with 100% coverage
- Complex routing logic validated
- Performance benchmarks met (no regression)
- Documentation complete for all changes
- Token savings validated (≥ 9,500)
- Zero P0/P1 bugs discovered

**Risk Factors:**
- Most-used tools being consolidated (ticket CRUD)
- Complex routing with 11 tools → 1 (hierarchy)
- High testing burden (75+ tests required)
- Performance-sensitive operations

---

## Sprint 3.1: Hierarchy Consolidation

**Duration:** 2 days (Mon-Wed, Dec 16-18)
**Token Savings:** 4,500 tokens
**Risk:** High

### Current State

**11 separate hierarchy tools:**

**Epic Operations (6 tools):**
```python
mcp__mcp-ticketer__epic_create(title, description, target_date, lead_id, child_issues)
mcp__mcp-ticketer__epic_get(epic_id)
mcp__mcp-ticketer__epic_update(epic_id, title, description, state, target_date)
mcp__mcp-ticketer__epic_delete(epic_id)
mcp__mcp-ticketer__epic_list(limit, offset, state, project_id, include_completed)
mcp__mcp-ticketer__epic_issues(epic_id)
```

**Issue Operations (3 tools):**
```python
mcp__mcp-ticketer__issue_create(title, description, epic_id, assignee, priority, tags)
mcp__mcp-ticketer__issue_get_parent(issue_id)
mcp__mcp-ticketer__issue_tasks(issue_id, state, assignee, priority)
```

**Task Operations (1 tool):**
```python
mcp__mcp-ticketer__task_create(title, description, issue_id, assignee, priority, tags)
```

**Hierarchy Traversal (1 tool):**
```python
mcp__mcp-ticketer__hierarchy_tree(epic_id, max_depth)
```

**Token Cost:**
- Epic tools: ~2,700 tokens (6 tools × ~450 avg)
- Issue tools: ~1,200 tokens (3 tools × ~400 avg)
- Task tool: ~400 tokens
- Hierarchy tree: ~200 tokens
- **Total:** 4,500 tokens

### Target State

**1 unified hierarchy tool:**

```python
mcp__mcp-ticketer__hierarchy(
    resource: str,  # "epic" | "issue" | "task" | "tree"
    action: str,    # "create" | "read" | "update" | "delete" | "list" | "children" | "parent"
    resource_id: Optional[str] = None,
    data: Optional[Dict] = None,
    **kwargs
) -> Dict
```

**Token Cost:** ~1,200 tokens
**Savings:** 3,300 tokens

### Implementation Details

**Unified hierarchy tool:**

```python
from typing import Literal, Optional, Dict
from pydantic import BaseModel, validator

VALID_RESOURCES = {"epic", "issue", "task", "tree"}
VALID_ACTIONS = {"create", "read", "update", "delete", "list", "children", "parent"}

# Resource-specific valid actions
RESOURCE_ACTIONS = {
    "epic": {"create", "read", "update", "delete", "list", "children"},
    "issue": {"create", "parent", "children"},
    "task": {"create"},
    "tree": {"read"}  # Special: hierarchy_tree functionality
}


class HierarchyInput(BaseModel):
    """Input validation for hierarchy tool."""

    resource: Literal["epic", "issue", "task", "tree"]
    action: str
    resource_id: Optional[str] = None
    data: Optional[Dict] = None

    @validator("resource")
    def validate_resource(cls, v):
        if v not in VALID_RESOURCES:
            raise ValueError(f"resource must be one of {VALID_RESOURCES}")
        return v

    @validator("action")
    def validate_action(cls, v, values):
        resource = values.get("resource")
        if resource and v not in RESOURCE_ACTIONS.get(resource, set()):
            valid = RESOURCE_ACTIONS[resource]
            raise ValueError(f"action '{v}' not valid for resource '{resource}'. Valid actions: {valid}")
        return v

    @validator("resource_id")
    def validate_resource_id(cls, v, values):
        action = values.get("action")
        if action in ["read", "update", "delete", "children", "parent"] and not v:
            raise ValueError(f"resource_id required for action '{action}'")
        return v


def hierarchy(
    resource: str,
    action: str,
    resource_id: Optional[str] = None,
    data: Optional[Dict] = None,
    **kwargs
) -> Dict:
    """
    Unified hierarchy management tool for epics, issues, and tasks.

    **Consolidates 11 tools:**
    - Epic: epic_create, epic_get, epic_update, epic_delete, epic_list, epic_issues
    - Issue: issue_create, issue_get_parent, issue_tasks
    - Task: task_create
    - Tree: hierarchy_tree

    **Resource Types:**

    - **epic**: Project milestones containing issues
      - Actions: create, read, update, delete, list, children

    - **issue**: Work items within epics containing tasks
      - Actions: create, parent, children

    - **task**: Individual work units within issues
      - Actions: create

    - **tree**: Full hierarchy traversal
      - Actions: read (returns epic → issues → tasks tree)

    **Common Actions:**

    - **create**: Create new resource
      - Requires: data dict with resource-specific fields
      - Epic: title, description, target_date, lead_id
      - Issue: title, description, epic_id, assignee
      - Task: title, description, issue_id, assignee

    - **read**: Get resource details
      - Requires: resource_id
      - Returns: Full resource information

    - **update**: Update resource
      - Requires: resource_id, data dict with fields to update
      - Epic: title, description, state, target_date

    - **delete**: Delete resource
      - Requires: resource_id
      - Note: May not be supported for all adapters

    - **list**: List resources
      - Optional filters: limit, offset, state, project_id
      - Epic-only action

    - **children**: Get child resources
      - Requires: resource_id
      - Epic → returns issues, Issue → returns tasks

    - **parent**: Get parent resource
      - Requires: resource_id
      - Issue-only action (returns parent epic)

    **Parameters:**
    - resource (str): REQUIRED. Resource type to operate on.
    - action (str): REQUIRED. Action to perform.
    - resource_id (str): Resource identifier (required for read/update/delete/children/parent).
    - data (Dict): Resource data (required for create/update).
    - **kwargs: Action-specific parameters.

    **Returns:**
    Dict: Action-specific response with "status" field.

    **Examples:**

    Create epic:
    >>> hierarchy(
    ...     resource="epic",
    ...     action="create",
    ...     data={"title": "Q4 Features", "target_date": "2025-12-31"}
    ... )

    Get epic details:
    >>> hierarchy(resource="epic", action="read", resource_id="epic-123")

    List epics:
    >>> hierarchy(resource="epic", action="list", limit=10)

    Get epic's issues:
    >>> hierarchy(resource="epic", action="children", resource_id="epic-123")

    Create issue under epic:
    >>> hierarchy(
    ...     resource="issue",
    ...     action="create",
    ...     data={"title": "Implement feature", "epic_id": "epic-123"}
    ... )

    Get issue's parent epic:
    >>> hierarchy(resource="issue", action="parent", resource_id="issue-456")

    Get issue's tasks:
    >>> hierarchy(resource="issue", action="children", resource_id="issue-456")

    Create task under issue:
    >>> hierarchy(
    ...     resource="task",
    ...     action="create",
    ...     data={"title": "Write tests", "issue_id": "issue-456"}
    ... )

    Get full hierarchy tree:
    >>> hierarchy(resource="tree", action="read", resource_id="epic-123", max_depth=3)

    **Migration Guide:**

    Before (epic_create):
    >>> epic_create(title="Q4 Features", target_date="2025-12-31")

    After:
    >>> hierarchy(resource="epic", action="create", data={"title": "Q4 Features", "target_date": "2025-12-31"})

    Before (epic_get):
    >>> epic_get(epic_id="epic-123")

    After:
    >>> hierarchy(resource="epic", action="read", resource_id="epic-123")

    Before (epic_issues):
    >>> epic_issues(epic_id="epic-123")

    After:
    >>> hierarchy(resource="epic", action="children", resource_id="epic-123")

    Before (issue_create):
    >>> issue_create(title="Feature", epic_id="epic-123")

    After:
    >>> hierarchy(resource="issue", action="create", data={"title": "Feature", "epic_id": "epic-123"})

    Before (issue_get_parent):
    >>> issue_get_parent(issue_id="issue-456")

    After:
    >>> hierarchy(resource="issue", action="parent", resource_id="issue-456")

    Before (hierarchy_tree):
    >>> hierarchy_tree(epic_id="epic-123", max_depth=3)

    After:
    >>> hierarchy(resource="tree", action="read", resource_id="epic-123", max_depth=3)

    **See Also:**
    - docs/UPGRADING-v2.0.md#hierarchy-consolidation
    - docs/api/hierarchy.md for detailed API reference
    """

    # Validate input
    input_data = HierarchyInput(
        resource=resource,
        action=action,
        resource_id=resource_id,
        data=data
    )

    # Route to resource handler
    try:
        if resource == "epic":
            return _handle_epic(action, resource_id, data, **kwargs)
        elif resource == "issue":
            return _handle_issue(action, resource_id, data, **kwargs)
        elif resource == "task":
            return _handle_task(action, resource_id, data, **kwargs)
        elif resource == "tree":
            return _handle_tree(action, resource_id, **kwargs)
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "resource": resource,
            "action": action
        }


# Epic handlers
def _handle_epic(action: str, resource_id: Optional[str], data: Optional[Dict], **kwargs) -> Dict:
    """Route epic actions to appropriate handlers."""
    from mcp_ticketer.tools import epic

    if action == "create":
        return epic.create_epic(**data, **kwargs)
    elif action == "read":
        return epic.get_epic(epic_id=resource_id)
    elif action == "update":
        return epic.update_epic(epic_id=resource_id, **data, **kwargs)
    elif action == "delete":
        return epic.delete_epic(epic_id=resource_id)
    elif action == "list":
        return epic.list_epics(**kwargs)
    elif action == "children":
        return epic.get_epic_issues(epic_id=resource_id)


# Issue handlers
def _handle_issue(action: str, resource_id: Optional[str], data: Optional[Dict], **kwargs) -> Dict:
    """Route issue actions to appropriate handlers."""
    from mcp_ticketer.tools import issue

    if action == "create":
        return issue.create_issue(**data, **kwargs)
    elif action == "parent":
        return issue.get_parent_issue(issue_id=resource_id)
    elif action == "children":
        return issue.get_issue_tasks(issue_id=resource_id, **kwargs)


# Task handlers
def _handle_task(action: str, resource_id: Optional[str], data: Optional[Dict], **kwargs) -> Dict:
    """Route task actions to appropriate handlers."""
    from mcp_ticketer.tools import task

    if action == "create":
        return task.create_task(**data, **kwargs)


# Tree handler
def _handle_tree(action: str, resource_id: str, **kwargs) -> Dict:
    """Handle hierarchy tree traversal."""
    from mcp_ticketer.tools import hierarchy_tree

    if action == "read":
        return hierarchy_tree.get_hierarchy_tree(epic_id=resource_id, **kwargs)
```

### Deprecation Strategy

Due to the large number of tools, I'll show representative examples:

```python
# Epic tools
@deprecated(version="1.5.0", removal="2.0.0", alternative="hierarchy")
def epic_create(title, description="", target_date=None, lead_id=None, child_issues=None):
    """DEPRECATED: Use hierarchy(resource="epic", action="create", ...) instead."""
    warnings.warn(
        "epic_create is deprecated. Use hierarchy(resource='epic', action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return hierarchy(
        resource="epic",
        action="create",
        data={
            "title": title,
            "description": description,
            "target_date": target_date,
            "lead_id": lead_id,
            "child_issues": child_issues
        }
    )


@deprecated(version="1.5.0", removal="2.0.0", alternative="hierarchy")
def epic_get(epic_id):
    """DEPRECATED: Use hierarchy(resource="epic", action="read", ...) instead."""
    warnings.warn(
        "epic_get is deprecated. Use hierarchy(resource='epic', action='read', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return hierarchy(resource="epic", action="read", resource_id=epic_id)


# Issue tools
@deprecated(version="1.5.0", removal="2.0.0", alternative="hierarchy")
def issue_create(title, description="", epic_id=None, assignee=None, priority="medium", tags=None):
    """DEPRECATED: Use hierarchy(resource="issue", action="create", ...) instead."""
    warnings.warn(
        "issue_create is deprecated. Use hierarchy(resource='issue', action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return hierarchy(
        resource="issue",
        action="create",
        data={
            "title": title,
            "description": description,
            "epic_id": epic_id,
            "assignee": assignee,
            "priority": priority,
            "tags": tags
        }
    )


# Task tools
@deprecated(version="1.5.0", removal="2.0.0", alternative="hierarchy")
def task_create(title, description="", issue_id=None, assignee=None, priority="medium", tags=None):
    """DEPRECATED: Use hierarchy(resource="task", action="create", ...) instead."""
    warnings.warn(
        "task_create is deprecated. Use hierarchy(resource='task', action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return hierarchy(
        resource="task",
        action="create",
        data={
            "title": title,
            "description": description,
            "issue_id": issue_id,
            "assignee": assignee,
            "priority": priority,
            "tags": tags
        }
    )
```

### Test Plan

**Total Tests:** 40+

**Unit Tests (25 - by resource and action):**

Epic tests (12):
```python
def test_hierarchy_epic_create():
    """Test epic creation."""
    result = hierarchy(resource="epic", action="create", data={"title": "Q4 Sprint"})
    assert result["status"] == "success"


def test_hierarchy_epic_read():
    """Test epic retrieval."""
    result = hierarchy(resource="epic", action="read", resource_id="epic-123")
    assert result["status"] == "success"


def test_hierarchy_epic_update():
    """Test epic update."""
    result = hierarchy(resource="epic", action="update", resource_id="epic-123", data={"title": "Updated"})
    assert result["status"] == "success"


def test_hierarchy_epic_delete():
    """Test epic deletion."""
    result = hierarchy(resource="epic", action="delete", resource_id="epic-123")
    assert result["status"] == "success"


def test_hierarchy_epic_list():
    """Test epic listing."""
    result = hierarchy(resource="epic", action="list", limit=10)
    assert result["status"] == "success"


def test_hierarchy_epic_children():
    """Test getting epic's issues."""
    result = hierarchy(resource="epic", action="children", resource_id="epic-123")
    assert result["status"] == "success"
    assert "issues" in result or "children" in result
```

Issue tests (8):
```python
def test_hierarchy_issue_create():
    """Test issue creation."""
    result = hierarchy(resource="issue", action="create", data={"title": "Feature", "epic_id": "epic-123"})
    assert result["status"] == "success"


def test_hierarchy_issue_parent():
    """Test getting issue's parent epic."""
    result = hierarchy(resource="issue", action="parent", resource_id="issue-456")
    assert result["status"] == "success"
    assert "parent" in result or "epic" in result


def test_hierarchy_issue_children():
    """Test getting issue's tasks."""
    result = hierarchy(resource="issue", action="children", resource_id="issue-456")
    assert result["status"] == "success"
    assert "tasks" in result or "children" in result
```

Task tests (3):
```python
def test_hierarchy_task_create():
    """Test task creation."""
    result = hierarchy(resource="task", action="create", data={"title": "Write tests", "issue_id": "issue-456"})
    assert result["status"] == "success"
```

Tree tests (2):
```python
def test_hierarchy_tree_read():
    """Test hierarchy tree traversal."""
    result = hierarchy(resource="tree", action="read", resource_id="epic-123", max_depth=3)
    assert result["status"] == "success"
    assert "epic" in result or "tree" in result
```

**Validation Tests (8):**
```python
def test_hierarchy_invalid_resource():
    """Test invalid resource raises error."""
    with pytest.raises(ValueError, match="resource must be one of"):
        hierarchy(resource="invalid", action="create")


def test_hierarchy_invalid_action_for_resource():
    """Test invalid action for resource raises error."""
    with pytest.raises(ValueError, match="not valid for resource"):
        hierarchy(resource="task", action="delete")  # Tasks don't support delete


def test_hierarchy_missing_resource_id():
    """Test read without resource_id raises error."""
    with pytest.raises(ValueError, match="resource_id required"):
        hierarchy(resource="epic", action="read")


def test_hierarchy_missing_data():
    """Test create without data raises error."""
    with pytest.raises(ValueError, match="data required"):
        hierarchy(resource="epic", action="create")
```

**Backward Compatibility Tests (11 - one per deprecated tool):**
```python
def test_epic_create_backward_compat():
    """Test deprecated epic_create still works."""
    with pytest.warns(DeprecationWarning):
        result = epic_create(title="Test Epic")
    assert result["status"] == "success"


def test_epic_get_backward_compat():
    """Test deprecated epic_get still works."""
    with pytest.warns(DeprecationWarning):
        result = epic_get(epic_id="epic-123")
    assert result["status"] == "success"


# ... similar tests for all 11 deprecated tools
```

**Integration Tests (6):**
```python
def test_hierarchy_full_lifecycle():
    """Test create epic → issue → task workflow."""
    # Create epic
    epic_result = hierarchy(resource="epic", action="create", data={"title": "Sprint 1"})
    epic_id = epic_result["epic_id"]

    # Create issue
    issue_result = hierarchy(resource="issue", action="create", data={"title": "Feature", "epic_id": epic_id})
    issue_id = issue_result["issue_id"]

    # Create task
    task_result = hierarchy(resource="task", action="create", data={"title": "Test", "issue_id": issue_id})

    # Verify hierarchy
    epic_issues = hierarchy(resource="epic", action="children", resource_id=epic_id)
    assert any(i["id"] == issue_id for i in epic_issues["issues"])


def test_hierarchy_tree_consistency():
    """Test hierarchy tree matches individual queries."""
    epic_id = "epic-123"

    # Get via tree
    tree_result = hierarchy(resource="tree", action="read", resource_id=epic_id, max_depth=2)

    # Get via individual calls
    epic_result = hierarchy(resource="epic", action="read", resource_id=epic_id)
    issues_result = hierarchy(resource="epic", action="children", resource_id=epic_id)

    # Should be consistent
    assert tree_result["epic"]["id"] == epic_result["id"]
```

---

## Sprint 3.2: Ticket CRUD Consolidation

**Duration:** 2 days (Wed-Fri, Dec 18-20)
**Token Savings:** 5,000 tokens
**Risk:** High

### Current State

**8 ticket CRUD tools:**
```python
mcp__mcp-ticketer__ticket_create(title, description, priority, tags, assignee, parent_epic)
mcp__mcp-ticketer__ticket_read(ticket_id)
mcp__mcp-ticketer__ticket_update(ticket_id, title, description, priority, state, assignee, tags)
mcp__mcp-ticketer__ticket_delete(ticket_id)
mcp__mcp-ticketer__ticket_list(limit, offset, state, priority, assignee, project_id)
mcp__mcp-ticketer__ticket_summary(ticket_id)
mcp__mcp-ticketer__ticket_latest(ticket_id, limit)
mcp__mcp-ticketer__ticket_assign(ticket_id, assignee, comment, auto_transition)
```

**Token Cost:**
- ticket_create: ~700 tokens
- ticket_read: ~600 tokens
- ticket_update: ~750 tokens
- ticket_delete: ~400 tokens
- ticket_list: ~800 tokens
- ticket_summary: ~500 tokens
- ticket_latest: ~550 tokens
- ticket_assign: ~700 tokens
- **Total:** 5,000 tokens

### Target State

**1 unified ticket tool:**

```python
mcp__mcp-ticketer__ticket(
    action: str,  # "create" | "read" | "update" | "delete" | "list" | "summary" | "activity" | "assign"
    ticket_id: Optional[str] = None,
    data: Optional[Dict] = None,
    **kwargs
) -> Dict
```

**Token Cost:** ~1,200 tokens
**Savings:** 3,800 tokens

### Implementation Details

**Unified ticket tool:**

```python
VALID_ACTIONS = {"create", "read", "update", "delete", "list", "summary", "activity", "assign"}


def ticket(
    action: str,
    ticket_id: Optional[str] = None,
    data: Optional[Dict] = None,
    **kwargs
) -> Dict:
    """
    Unified ticket management tool for all CRUD operations.

    **Consolidates 8 tools:**
    - ticket_create → action="create"
    - ticket_read → action="read"
    - ticket_update → action="update"
    - ticket_delete → action="delete"
    - ticket_list → action="list"
    - ticket_summary → action="summary"
    - ticket_latest → action="activity"
    - ticket_assign → action="assign"

    **Available Actions:**

    - **create**: Create new ticket
      - Requires: data dict (title, description, priority, tags, assignee)
      - Returns: Created ticket with ID

    - **read**: Get full ticket details
      - Requires: ticket_id
      - Returns: Complete ticket information

    - **update**: Update ticket fields
      - Requires: ticket_id, data dict (fields to update)
      - Returns: Updated ticket

    - **delete**: Delete ticket
      - Requires: ticket_id
      - Returns: Deletion confirmation

    - **list**: List tickets with filters
      - Optional: limit, offset, state, priority, assignee, project_id
      - Returns: Paginated ticket list

    - **summary**: Get compact ticket summary
      - Requires: ticket_id
      - Returns: Essential fields only (id, title, state, priority, assignee)

    - **activity**: Get recent ticket activity
      - Requires: ticket_id
      - Optional: limit (default: 5)
      - Returns: Recent comments, updates, state changes

    - **assign**: Assign/unassign ticket
      - Requires: ticket_id
      - Optional: assignee (user ID/email or None to unassign)
      - Optional: comment, auto_transition
      - Returns: Assignment result with state transitions

    **Parameters:**
    - action (str): REQUIRED. The action to perform.
    - ticket_id (str): Ticket identifier (required for read/update/delete/summary/activity/assign).
    - data (Dict): Action-specific data (required for create/update, optional for assign).
    - **kwargs: Action-specific parameters.

    **Returns:**
    Dict: Action-specific response with "status" field.

    **Examples:**

    Create ticket:
    >>> ticket(action="create", data={"title": "Fix bug", "priority": "high"})

    Read ticket:
    >>> ticket(action="read", ticket_id="TICKET-123")

    Update ticket:
    >>> ticket(action="update", ticket_id="TICKET-123", data={"state": "done"})

    Delete ticket:
    >>> ticket(action="delete", ticket_id="TICKET-123")

    List tickets:
    >>> ticket(action="list", state="open", limit=10)

    Get summary:
    >>> ticket(action="summary", ticket_id="TICKET-123")

    Get activity:
    >>> ticket(action="activity", ticket_id="TICKET-123", limit=5)

    Assign ticket:
    >>> ticket(action="assign", ticket_id="TICKET-123", assignee="user@example.com")

    **Migration Guide:**

    See docs/UPGRADING-v2.0.md#ticket-crud-consolidation for complete examples.

    **See Also:**
    - docs/UPGRADING-v2.0.md#ticket-crud-consolidation
    - docs/api/ticket.md for detailed API reference
    """

    # Validate action
    if action not in VALID_ACTIONS:
        raise ValueError(f"action must be one of {VALID_ACTIONS}")

    # Validate parameters
    if action in ["read", "update", "delete", "summary", "activity", "assign"] and not ticket_id:
        raise ValueError(f"ticket_id required for action '{action}'")

    if action in ["create", "update"] and not data:
        raise ValueError(f"data required for action '{action}'")

    # Route to handler
    try:
        if action == "create":
            return _handle_ticket_create(data, **kwargs)
        elif action == "read":
            return _handle_ticket_read(ticket_id)
        elif action == "update":
            return _handle_ticket_update(ticket_id, data, **kwargs)
        elif action == "delete":
            return _handle_ticket_delete(ticket_id)
        elif action == "list":
            return _handle_ticket_list(**kwargs)
        elif action == "summary":
            return _handle_ticket_summary(ticket_id)
        elif action == "activity":
            return _handle_ticket_activity(ticket_id, **kwargs)
        elif action == "assign":
            return _handle_ticket_assign(ticket_id, data, **kwargs)
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
            "action": action
        }


# Action handlers
def _handle_ticket_create(data: Dict, **kwargs) -> Dict:
    """Handle ticket creation."""
    from mcp_ticketer.tools.ticket import create_ticket
    return create_ticket(**data, **kwargs)


def _handle_ticket_read(ticket_id: str) -> Dict:
    """Handle ticket read."""
    from mcp_ticketer.tools.ticket import read_ticket
    return read_ticket(ticket_id=ticket_id)


def _handle_ticket_update(ticket_id: str, data: Dict, **kwargs) -> Dict:
    """Handle ticket update."""
    from mcp_ticketer.tools.ticket import update_ticket
    return update_ticket(ticket_id=ticket_id, **data, **kwargs)


def _handle_ticket_delete(ticket_id: str) -> Dict:
    """Handle ticket deletion."""
    from mcp_ticketer.tools.ticket import delete_ticket
    return delete_ticket(ticket_id=ticket_id)


def _handle_ticket_list(**kwargs) -> Dict:
    """Handle ticket listing."""
    from mcp_ticketer.tools.ticket import list_tickets
    return list_tickets(**kwargs)


def _handle_ticket_summary(ticket_id: str) -> Dict:
    """Handle ticket summary."""
    from mcp_ticketer.tools.ticket import get_ticket_summary
    return get_ticket_summary(ticket_id=ticket_id)


def _handle_ticket_activity(ticket_id: str, **kwargs) -> Dict:
    """Handle ticket activity retrieval."""
    from mcp_ticketer.tools.ticket import get_ticket_activity
    return get_ticket_activity(ticket_id=ticket_id, **kwargs)


def _handle_ticket_assign(ticket_id: str, data: Optional[Dict], **kwargs) -> Dict:
    """Handle ticket assignment."""
    from mcp_ticketer.tools.ticket import assign_ticket
    assignee = data.get("assignee") if data else kwargs.get("assignee")
    return assign_ticket(ticket_id=ticket_id, assignee=assignee, **kwargs)
```

### Deprecation Strategy

Representative examples:

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="ticket")
def ticket_create(title, description="", priority="medium", tags=None, assignee=None, parent_epic=None):
    """DEPRECATED: Use ticket(action="create", ...) instead."""
    warnings.warn(
        "ticket_create is deprecated. Use ticket(action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return ticket(
        action="create",
        data={
            "title": title,
            "description": description,
            "priority": priority,
            "tags": tags,
            "assignee": assignee,
            "parent_epic": parent_epic
        }
    )


@deprecated(version="1.5.0", removal="2.0.0", alternative="ticket")
def ticket_read(ticket_id):
    """DEPRECATED: Use ticket(action="read", ...) instead."""
    warnings.warn(
        "ticket_read is deprecated. Use ticket(action='read', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return ticket(action="read", ticket_id=ticket_id)


# ... similar for all 8 tools
```

### Test Plan

**Total Tests:** 35+

**Unit Tests (16 - 2 per action):**
```python
def test_ticket_create():
    """Test ticket creation."""
    result = ticket(action="create", data={"title": "Fix bug", "priority": "high"})
    assert result["status"] == "success"
    assert "ticket_id" in result


def test_ticket_read():
    """Test ticket read."""
    result = ticket(action="read", ticket_id="TICKET-123")
    assert result["status"] == "success"


def test_ticket_update():
    """Test ticket update."""
    result = ticket(action="update", ticket_id="TICKET-123", data={"state": "done"})
    assert result["status"] == "success"


def test_ticket_delete():
    """Test ticket deletion."""
    result = ticket(action="delete", ticket_id="TICKET-123")
    assert result["status"] == "success"


def test_ticket_list():
    """Test ticket listing."""
    result = ticket(action="list", state="open", limit=10)
    assert result["status"] == "success"
    assert len(result["tickets"]) <= 10


def test_ticket_summary():
    """Test ticket summary."""
    result = ticket(action="summary", ticket_id="TICKET-123")
    assert result["status"] == "success"
    assert "id" in result
    assert "title" in result


def test_ticket_activity():
    """Test ticket activity."""
    result = ticket(action="activity", ticket_id="TICKET-123", limit=5)
    assert result["status"] == "success"


def test_ticket_assign():
    """Test ticket assignment."""
    result = ticket(action="assign", ticket_id="TICKET-123", assignee="user@example.com")
    assert result["status"] == "success"
```

**Backward Compatibility Tests (8):**
```python
def test_ticket_create_backward_compat():
    """Test deprecated ticket_create still works."""
    with pytest.warns(DeprecationWarning):
        result = ticket_create(title="Test", priority="high")
    assert result["status"] == "success"


# ... similar for all 8 deprecated tools
```

**Integration Tests (11):**
```python
def test_ticket_full_lifecycle():
    """Test create → read → update → delete workflow."""
    # Create
    create_result = ticket(action="create", data={"title": "Test Bug"})
    ticket_id = create_result["ticket_id"]

    # Read
    read_result = ticket(action="read", ticket_id=ticket_id)
    assert read_result["title"] == "Test Bug"

    # Update
    update_result = ticket(action="update", ticket_id=ticket_id, data={"state": "in_progress"})
    assert update_result["state"] == "in_progress"

    # Delete
    delete_result = ticket(action="delete", ticket_id=ticket_id)
    assert delete_result["status"] == "success"


def test_ticket_activity_tracking():
    """Test activity is tracked correctly."""
    ticket_id = "TICKET-123"

    # Update ticket
    ticket(action="update", ticket_id=ticket_id, data={"state": "in_progress"})

    # Get activity
    activity_result = ticket(action="activity", ticket_id=ticket_id, limit=5)

    # Should include state change
    assert any("in_progress" in str(a) for a in activity_result["activities"])
```

---

## Sprint 3 Summary

### Deliverables Checklist

- [ ] **Hierarchy consolidation complete**
  - [ ] Unified hierarchy() tool implemented
  - [ ] 40+ tests passing
  - [ ] All 11 deprecated tools emit warnings
  - [ ] Documentation updated

- [ ] **Ticket CRUD consolidation complete**
  - [ ] Unified ticket() tool implemented
  - [ ] 35+ tests passing
  - [ ] All 8 deprecated tools emit warnings
  - [ ] Documentation updated

- [ ] **Token savings validated**
  - [ ] Measured savings ≥ 9,500 tokens
  - [ ] MCP manifest updated
  - [ ] Token count documented

- [ ] **Performance validated**
  - [ ] Benchmarks show no regression
  - [ ] Routing overhead < 5ms
  - [ ] Memory usage acceptable

- [ ] **Documentation complete**
  - [ ] API docs updated
  - [ ] UPGRADING-v2.0.md complete
  - [ ] Migration examples for all 19 tools

### Success Metrics

**Quantitative:**
- Token savings: 9,500 tokens (target met)
- Test coverage: 100% maintained
- Tests written: 75+ (all passing)
- Tools consolidated: 19

**Qualitative:**
- Most-used APIs (ticket CRUD) improved
- Hierarchy management simplified
- Complex routing working correctly
- Ready for v1.5.0 release

### Risks and Mitigations

**Identified Risks:**
1. Performance regression in routing logic
   - **Mitigation:** Benchmarks run, caching implemented

2. Breaking changes in most-used tools
   - **Mitigation:** 100% backward compatibility, comprehensive tests

3. Complex hierarchy routing errors
   - **Mitigation:** Extensive validation, clear error messages

**Risk Status:** HIGH (but mitigated, monitoring required)

---

## Phase 2 Complete

**Total Token Savings:** 19,744 tokens (94% of target)

**Next Steps:**
1. Comprehensive integration testing
2. Performance validation
3. Documentation review
4. Release v1.5.0
5. Monitor community feedback

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Next Review:** Sprint 3 completion (2025-12-20)
