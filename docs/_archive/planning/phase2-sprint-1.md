# Phase 2 Sprint 1: Low-Hanging Fruit

**Sprint Duration:** 2.5 days (Dec 2-6, 2025)
**Token Savings Target:** 5,644 tokens
**Risk Level:** Low
**Linear Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

---

## Sprint Goals

Sprint 1 focuses on **simple consolidations with immediate value** and minimal risk. These changes establish patterns for subsequent sprints while delivering measurable token savings quickly.

**Primary Objectives:**
1. Consolidate project_update tools (3 → 1)
2. Merge ticket_search tools (2 → 1)
3. Remove attachment/PR tools (4 tools)
4. Establish action-based patterns for Sprint 2/3
5. Achieve 5,644 tokens in savings

**Success Criteria:**
- All 9 tools consolidated/removed
- 33 tests passing with 100% coverage
- Documentation complete for all changes
- Token savings validated (≥ 5,644)
- Zero P0/P1 bugs discovered

---

## Sprint 1.1: project_update Consolidation

**Duration:** 2 days (Mon-Tue, Dec 2-3)
**Token Savings:** 1,500 tokens
**Risk:** Low

### Current State

**3 separate tools:**
```python
mcp__mcp-ticketer__project_update_create(project_id, body, health=None)
mcp__mcp-ticketer__project_update_list(project_id, limit=10)
mcp__mcp-ticketer__project_update_get(update_id)
```

**Token Cost:**
- project_update_create: ~550 tokens
- project_update_list: ~450 tokens
- project_update_get: ~500 tokens
- **Total:** 1,500 tokens

### Target State

**1 unified tool:**
```python
mcp__mcp-ticketer__project_update(
    action: str,  # "create" | "get" | "list"
    project_id: Optional[str] = None,
    update_id: Optional[str] = None,
    body: Optional[str] = None,
    health: Optional[str] = None,
    limit: int = 10
) -> Dict
```

**Token Cost:** ~600 tokens
**Savings:** 900 tokens

### Implementation Details

**Tool Signature:**

```python
from typing import Optional, Dict, Literal
from pydantic import BaseModel, validator

class ProjectUpdateInput(BaseModel):
    """Input schema for project_update tool."""

    action: Literal["create", "get", "list"]
    project_id: Optional[str] = None
    update_id: Optional[str] = None
    body: Optional[str] = None
    health: Optional[str] = None
    limit: int = 10

    @validator("action")
    def validate_action(cls, v):
        valid_actions = {"create", "get", "list"}
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v

    @validator("project_id")
    def validate_project_id(cls, v, values):
        action = values.get("action")
        if action in ["create", "list"] and not v:
            raise ValueError(f"project_id required for action={action}")
        return v

    @validator("update_id")
    def validate_update_id(cls, v, values):
        action = values.get("action")
        if action == "get" and not v:
            raise ValueError("update_id required for action=get")
        return v

    @validator("body")
    def validate_body(cls, v, values):
        action = values.get("action")
        if action == "create" and not v:
            raise ValueError("body required for action=create")
        return v


def project_update(
    action: str,
    project_id: Optional[str] = None,
    update_id: Optional[str] = None,
    body: Optional[str] = None,
    health: Optional[str] = None,
    limit: int = 10
) -> Dict:
    """
    Unified project update management tool.

    **Consolidates:**
    - project_update_create() → action="create"
    - project_update_get() → action="get"
    - project_update_list() → action="list"

    **Available Actions:**

    - **create**: Create a new project status update
      - Requires: project_id, body
      - Optional: health ("on_track" | "at_risk" | "off_track" | "complete")

    - **get**: Retrieve a specific project update
      - Requires: update_id

    - **list**: List project updates for a project
      - Requires: project_id
      - Optional: limit (default: 10, max: 50)

    **Parameters:**
    - action (str): REQUIRED. The action to perform.
    - project_id (str): Project identifier (UUID, slugId, or URL). Required for create/list.
    - update_id (str): Update identifier. Required for get.
    - body (str): Update content in Markdown. Required for create.
    - health (str): Health status. Optional for create.
    - limit (int): Max results to return. Optional for list (default: 10).

    **Returns:**
    Dict: Action-specific response with "status" field.

    **Examples:**

    Create update:
    >>> project_update(
    ...     action="create",
    ...     project_id="proj-123",
    ...     body="Sprint 5 completed. 18/20 stories done.",
    ...     health="on_track"
    ... )

    Get update:
    >>> project_update(action="get", update_id="update-456")

    List updates:
    >>> project_update(action="list", project_id="proj-123", limit=5)

    **Migration Guide:**

    Before (project_update_create):
    >>> project_update_create(project_id="proj-123", body="...", health="on_track")

    After:
    >>> project_update(action="create", project_id="proj-123", body="...", health="on_track")

    Before (project_update_get):
    >>> project_update_get(update_id="update-456")

    After:
    >>> project_update(action="get", update_id="update-456")

    Before (project_update_list):
    >>> project_update_list(project_id="proj-123", limit=5)

    After:
    >>> project_update(action="list", project_id="proj-123", limit=5)

    **See Also:**
    - docs/UPGRADING-v2.0.md for complete migration guide
    """

    # Validate input
    input_data = ProjectUpdateInput(
        action=action,
        project_id=project_id,
        update_id=update_id,
        body=body,
        health=health,
        limit=limit
    )

    # Route to action handler
    try:
        if action == "create":
            return _handle_create(input_data.project_id, input_data.body, input_data.health)
        elif action == "get":
            return _handle_get(input_data.update_id)
        elif action == "list":
            return _handle_list(input_data.project_id, input_data.limit)
    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e)
        }
```

**Action Handlers:**

```python
def _handle_create(project_id: str, body: str, health: Optional[str]) -> Dict:
    """Handle project update creation."""
    # Existing project_update_create logic
    from mcp_ticketer.tools.project_update import create_project_update

    return create_project_update(
        project_id=project_id,
        body=body,
        health=health
    )


def _handle_get(update_id: str) -> Dict:
    """Handle project update retrieval."""
    from mcp_ticketer.tools.project_update import get_project_update

    return get_project_update(update_id=update_id)


def _handle_list(project_id: str, limit: int) -> Dict:
    """Handle project update listing."""
    from mcp_ticketer.tools.project_update import list_project_updates

    return list_project_updates(project_id=project_id, limit=limit)
```

### Deprecation Strategy

**Old Tools (Deprecated in v1.5.0):**

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="project_update")
def project_update_create(project_id: str, body: str, health: Optional[str] = None) -> Dict:
    """
    DEPRECATED: Use project_update(action="create", ...) instead.

    This tool will be removed in v2.0.0. Migrate to the unified project_update tool.

    See: docs/UPGRADING-v2.0.md#project-update-consolidation
    """
    warnings.warn(
        "project_update_create is deprecated. Use project_update(action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return project_update(action="create", project_id=project_id, body=body, health=health)


@deprecated(version="1.5.0", removal="2.0.0", alternative="project_update")
def project_update_get(update_id: str) -> Dict:
    """
    DEPRECATED: Use project_update(action="get", ...) instead.

    This tool will be removed in v2.0.0. Migrate to the unified project_update tool.

    See: docs/UPGRADING-v2.0.md#project-update-consolidation
    """
    warnings.warn(
        "project_update_get is deprecated. Use project_update(action='get', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return project_update(action="get", update_id=update_id)


@deprecated(version="1.5.0", removal="2.0.0", alternative="project_update")
def project_update_list(project_id: str, limit: int = 10) -> Dict:
    """
    DEPRECATED: Use project_update(action="list", ...) instead.

    This tool will be removed in v2.0.0. Migrate to the unified project_update tool.

    See: docs/UPGRADING-v2.0.md#project-update-consolidation
    """
    warnings.warn(
        "project_update_list is deprecated. Use project_update(action='list', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return project_update(action="list", project_id=project_id, limit=limit)
```

### Test Plan

**Total Tests:** 15

**Unit Tests (5 per action):**
```python
def test_project_update_create_success():
    """Test successful project update creation."""
    result = project_update(
        action="create",
        project_id="proj-123",
        body="Sprint completed successfully",
        health="on_track"
    )
    assert result["status"] == "success"
    assert "update_id" in result


def test_project_update_create_missing_body():
    """Test create fails without body."""
    with pytest.raises(ValueError, match="body required"):
        project_update(action="create", project_id="proj-123")


def test_project_update_get_success():
    """Test successful update retrieval."""
    result = project_update(action="get", update_id="update-456")
    assert result["status"] == "success"
    assert result["update_id"] == "update-456"


def test_project_update_list_success():
    """Test successful update listing."""
    result = project_update(action="list", project_id="proj-123", limit=5)
    assert result["status"] == "success"
    assert len(result["updates"]) <= 5


def test_project_update_invalid_action():
    """Test invalid action raises error."""
    with pytest.raises(ValueError, match="action must be one of"):
        project_update(action="invalid", project_id="proj-123")
```

**Backward Compatibility Tests (6):**
```python
def test_project_update_create_backward_compat():
    """Test deprecated project_update_create still works."""
    with pytest.warns(DeprecationWarning):
        result = project_update_create(
            project_id="proj-123",
            body="Test update",
            health="on_track"
        )
    assert result["status"] == "success"


def test_project_update_get_backward_compat():
    """Test deprecated project_update_get still works."""
    with pytest.warns(DeprecationWarning):
        result = project_update_get(update_id="update-456")
    assert result["status"] == "success"


def test_project_update_list_backward_compat():
    """Test deprecated project_update_list still works."""
    with pytest.warns(DeprecationWarning):
        result = project_update_list(project_id="proj-123", limit=5)
    assert result["status"] == "success"


def test_deprecation_warning_message():
    """Test deprecation warning includes migration info."""
    with pytest.warns(DeprecationWarning, match="Use project_update"):
        project_update_create(project_id="proj-123", body="Test")


def test_deprecated_tools_identical_behavior():
    """Test deprecated tools produce identical results to new tool."""
    # Create update with new tool
    result_new = project_update(action="create", project_id="proj-123", body="Test")

    # Create update with old tool (ignoring warning)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result_old = project_update_create(project_id="proj-123", body="Test")

    # Compare responses (ignoring timestamps)
    assert result_new["status"] == result_old["status"]
```

**Integration Tests (4):**
```python
def test_project_update_full_lifecycle():
    """Test create → get → list workflow."""
    # Create update
    create_result = project_update(
        action="create",
        project_id="proj-123",
        body="Test update"
    )
    update_id = create_result["update_id"]

    # Get update
    get_result = project_update(action="get", update_id=update_id)
    assert get_result["body"] == "Test update"

    # List updates (should include created update)
    list_result = project_update(action="list", project_id="proj-123")
    update_ids = [u["update_id"] for u in list_result["updates"]]
    assert update_id in update_ids


def test_project_update_health_tracking():
    """Test health status transitions."""
    project_id = "proj-123"

    # Create on_track update
    project_update(action="create", project_id=project_id, body="All good", health="on_track")

    # Create at_risk update
    project_update(action="create", project_id=project_id, body="Some issues", health="at_risk")

    # List should show both
    result = project_update(action="list", project_id=project_id)
    healths = [u["health"] for u in result["updates"]]
    assert "on_track" in healths
    assert "at_risk" in healths
```

---

## Sprint 1.2: ticket_search Consolidation

**Duration:** 1 day (Wed, Dec 4)
**Token Savings:** 1,500 tokens
**Risk:** Low

### Current State

**2 separate tools:**
```python
mcp__mcp-ticketer__ticket_search(query, state, priority, tags, assignee, project_id, limit)
mcp__mcp-ticketer__ticket_search_hierarchy(query, project_id, include_children, max_depth)
```

**Token Cost:**
- ticket_search: ~700 tokens
- ticket_search_hierarchy: ~800 tokens
- **Total:** 1,500 tokens

### Target State

**1 unified tool:**
```python
mcp__mcp-ticketer__ticket_search(
    query: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 10,
    include_hierarchy: bool = False,  # NEW
    include_children: bool = True,
    max_depth: int = 3
) -> Dict
```

**Token Cost:** ~800 tokens
**Savings:** 700 tokens

### Implementation Details

**Tool Signature:**

```python
def ticket_search(
    query: Optional[str] = None,
    state: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    assignee: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 10,
    include_hierarchy: bool = False,
    include_children: bool = True,
    max_depth: int = 3
) -> Dict:
    """
    Search tickets with optional hierarchy information.

    **Consolidates:**
    - ticket_search() → Default behavior (include_hierarchy=False)
    - ticket_search_hierarchy() → Set include_hierarchy=True

    **Search Filters:**
    - query: Text search in title and description
    - state: Filter by workflow state
    - priority: Filter by priority level
    - tags: Filter by tags (AND logic)
    - assignee: Filter by assigned user
    - project_id: Scope to specific project

    **Hierarchy Options:**
    - include_hierarchy: Include parent/child relationships (default: False)
    - include_children: Include child tickets (default: True, requires include_hierarchy=True)
    - max_depth: Maximum hierarchy depth (default: 3, requires include_hierarchy=True)

    **Parameters:**
    - query (str): Text to search for in ticket titles and descriptions
    - state (str): Ticket state filter ("open", "in_progress", "done", etc.)
    - priority (str): Priority filter ("low", "medium", "high", "critical")
    - tags (List[str]): Tags filter (tickets must have all tags)
    - assignee (str): Assigned user ID or email
    - project_id (str): Project/epic ID (recommended for scoping)
    - limit (int): Maximum results to return (default: 10, max: 100)
    - include_hierarchy (bool): Include parent/child relationships (default: False)
    - include_children (bool): Include child tickets in hierarchy (default: True)
    - max_depth (int): Maximum hierarchy depth to traverse (default: 3)

    **Returns:**
    Dict: Search results with tickets array and count.

    **Examples:**

    Simple search:
    >>> ticket_search(query="authentication bug", state="open", limit=5)

    Search with hierarchy:
    >>> ticket_search(
    ...     query="oauth implementation",
    ...     project_id="proj-123",
    ...     include_hierarchy=True,
    ...     max_depth=2
    ... )

    **Migration Guide:**

    Before (ticket_search):
    >>> ticket_search(query="bug", state="open", limit=10)

    After (unchanged):
    >>> ticket_search(query="bug", state="open", limit=10)

    Before (ticket_search_hierarchy):
    >>> ticket_search_hierarchy(query="feature", project_id="proj-123", max_depth=2)

    After:
    >>> ticket_search(query="feature", project_id="proj-123", include_hierarchy=True, max_depth=2)

    **See Also:**
    - docs/UPGRADING-v2.0.md#ticket-search-consolidation
    """

    # Perform base search
    from mcp_ticketer.tools.ticket_search import search_tickets

    results = search_tickets(
        query=query,
        state=state,
        priority=priority,
        tags=tags,
        assignee=assignee,
        project_id=project_id,
        limit=limit
    )

    # Add hierarchy if requested
    if include_hierarchy:
        from mcp_ticketer.tools.hierarchy import enrich_with_hierarchy

        results["tickets"] = enrich_with_hierarchy(
            tickets=results["tickets"],
            include_children=include_children,
            max_depth=max_depth
        )

    return results
```

### Deprecation Strategy

**Old Tool (Deprecated in v1.5.0):**

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="ticket_search")
def ticket_search_hierarchy(
    query: str,
    project_id: Optional[str] = None,
    include_children: bool = True,
    max_depth: int = 3
) -> Dict:
    """
    DEPRECATED: Use ticket_search(include_hierarchy=True, ...) instead.

    This tool will be removed in v2.0.0. Migrate to the unified ticket_search tool.

    See: docs/UPGRADING-v2.0.md#ticket-search-consolidation
    """
    warnings.warn(
        "ticket_search_hierarchy is deprecated. Use ticket_search(include_hierarchy=True, ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return ticket_search(
        query=query,
        project_id=project_id,
        include_hierarchy=True,
        include_children=include_children,
        max_depth=max_depth
    )
```

### Test Plan

**Total Tests:** 8

**Unit Tests (4):**
```python
def test_ticket_search_basic():
    """Test basic search without hierarchy."""
    result = ticket_search(query="bug", state="open", limit=5)
    assert result["status"] == "success"
    assert len(result["tickets"]) <= 5
    assert "hierarchy" not in result["tickets"][0]


def test_ticket_search_with_hierarchy():
    """Test search with hierarchy enabled."""
    result = ticket_search(query="feature", include_hierarchy=True)
    assert result["status"] == "success"
    assert "parent" in result["tickets"][0] or "children" in result["tickets"][0]


def test_ticket_search_hierarchy_depth():
    """Test hierarchy respects max_depth."""
    result = ticket_search(query="epic", include_hierarchy=True, max_depth=2)
    # Verify no tickets have hierarchy deeper than 2 levels
    for ticket in result["tickets"]:
        if "children" in ticket:
            assert len(ticket["children"]) <= 2


def test_ticket_search_no_children():
    """Test hierarchy without children."""
    result = ticket_search(query="task", include_hierarchy=True, include_children=False)
    for ticket in result["tickets"]:
        assert "children" not in ticket
        assert "parent" in ticket or ticket.get("parent") is None
```

**Backward Compatibility Tests (4):**
```python
def test_ticket_search_hierarchy_backward_compat():
    """Test deprecated ticket_search_hierarchy still works."""
    with pytest.warns(DeprecationWarning):
        result = ticket_search_hierarchy(query="test", project_id="proj-123")
    assert result["status"] == "success"


def test_ticket_search_unchanged_behavior():
    """Test default ticket_search behavior unchanged."""
    # Old behavior (no hierarchy)
    result = ticket_search(query="bug", limit=5)

    # Should not include hierarchy by default
    assert "parent" not in result["tickets"][0]
    assert "children" not in result["tickets"][0]


def test_hierarchy_migration_equivalence():
    """Test old ticket_search_hierarchy equals new ticket_search."""
    query = "feature request"
    project_id = "proj-123"

    # Old tool
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result_old = ticket_search_hierarchy(query=query, project_id=project_id)

    # New tool
    result_new = ticket_search(query=query, project_id=project_id, include_hierarchy=True)

    # Should return same tickets
    assert len(result_old["tickets"]) == len(result_new["tickets"])
    assert result_old["tickets"][0]["id"] == result_new["tickets"][0]["id"]
```

---

## Sprint 1.3: Remove Attachment/PR Tools

**Duration:** 2 days (Thu-Fri, Dec 5-6)
**Token Savings:** 2,644 tokens (1,602 attachment + 1,042 PR)
**Risk:** Medium (requires user migration)

### Current State

**4 tools to remove:**
```python
mcp__mcp-ticketer__ticket_attach(ticket_id, file_path, description)
mcp__mcp-ticketer__ticket_attachments(ticket_id)
mcp__mcp-ticketer__ticket_create_pr(ticket_id, title, description, source_branch, target_branch)
mcp__mcp-ticketer__ticket_link_pr(ticket_id, pr_url)
```

**Token Cost:**
- ticket_attach: ~450 tokens
- ticket_attachments: ~400 tokens
- ticket_create_pr: ~550 tokens
- ticket_link_pr: ~492 tokens
- **Total:** 2,644 tokens (estimated - needs verification)

### Rationale for Removal

**Attachment Tools:**
- Functionality available in MCP filesystem server
- Users can attach files directly via filesystem operations
- Reduces duplication with existing MCP tooling

**PR Tools:**
- Functionality available in MCP GitHub server
- Users can create/link PRs via GitHub operations
- Reduces duplication with existing MCP tooling

### Migration Strategy

**Migration to Filesystem MCP:**

Before (ticket_attach):
```python
ticket_attach(
    ticket_id="TICKET-123",
    file_path="/path/to/report.pdf",
    description="Performance analysis report"
)
```

After (filesystem MCP + ticket comment):
```python
# 1. Copy file to ticket attachments directory
mcp__filesystem__write_file(
    path=f"./tickets/TICKET-123/attachments/report.pdf",
    content=open("/path/to/report.pdf", "rb").read()
)

# 2. Add comment with file reference
ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="Attached performance analysis report: ./tickets/TICKET-123/attachments/report.pdf"
)
```

**Migration to GitHub MCP:**

Before (ticket_create_pr):
```python
ticket_create_pr(
    ticket_id="TICKET-123",
    title="Fix authentication bug",
    description="Resolves TICKET-123",
    source_branch="fix/auth-bug",
    target_branch="main"
)
```

After (GitHub MCP + ticket comment):
```python
# 1. Create PR via GitHub MCP
pr = mcp__github__create_pull_request(
    owner="myorg",
    repo="myrepo",
    title="Fix authentication bug",
    head="fix/auth-bug",
    base="main",
    body="Resolves TICKET-123"
)

# 2. Link PR in ticket comment
ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text=f"Created PR: {pr['html_url']}"
)
```

### Deprecation Strategy

**Phase 1 (v1.5.0): Deprecation Warnings**

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="mcp_filesystem + ticket_comment")
def ticket_attach(ticket_id: str, file_path: str, description: str = "") -> Dict:
    """
    DEPRECATED: Use filesystem MCP + ticket_comment instead.

    This tool will be removed in v2.0.0.

    Migration:
    1. Use mcp__filesystem__write_file to copy file to project directory
    2. Use ticket_comment to reference file in ticket

    See: docs/UPGRADING-v2.0.md#attachment-migration
    """
    warnings.warn(
        "ticket_attach is deprecated. Use filesystem MCP + ticket_comment instead. "
        "See docs/UPGRADING-v2.0.md#attachment-migration",
        DeprecationWarning,
        stacklevel=2
    )
    # Still functional in v1.5.0
    return _legacy_attach_file(ticket_id, file_path, description)


@deprecated(version="1.5.0", removal="2.0.0", alternative="mcp_github + ticket_comment")
def ticket_create_pr(
    ticket_id: str,
    title: str,
    description: str = "",
    source_branch: Optional[str] = None,
    target_branch: str = "main"
) -> Dict:
    """
    DEPRECATED: Use GitHub MCP + ticket_comment instead.

    This tool will be removed in v2.0.0.

    Migration:
    1. Use mcp__github__create_pull_request to create PR
    2. Use ticket_comment to link PR in ticket

    See: docs/UPGRADING-v2.0.md#pr-migration
    """
    warnings.warn(
        "ticket_create_pr is deprecated. Use GitHub MCP + ticket_comment instead. "
        "See docs/UPGRADING-v2.0.md#pr-migration",
        DeprecationWarning,
        stacklevel=2
    )
    # Still functional in v1.5.0
    return _legacy_create_pr(ticket_id, title, description, source_branch, target_branch)
```

**Phase 2 (v2.0.0): Removal**

Tools completely removed from codebase.

### Documentation Requirements

**UPGRADING-v2.0.md Section:**

```markdown
## Attachment and PR Tool Migration

### Attachment Tools Removed

**Removed Tools:**
- `ticket_attach`
- `ticket_attachments`

**Migration Path:**

Use filesystem MCP server for file operations + ticket comments for references.

**Before:**
```python
ticket_attach(
    ticket_id="TICKET-123",
    file_path="/path/to/report.pdf",
    description="Performance report"
)
```

**After:**
```python
# 1. Organize files in project structure
mkdir -p ./docs/tickets/TICKET-123

# 2. Copy file via filesystem MCP
mcp__filesystem__write_file(
    path="./docs/tickets/TICKET-123/performance-report.pdf",
    content=open("/path/to/report.pdf", "rb").read()
)

# 3. Reference in ticket
ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text="Performance report attached: docs/tickets/TICKET-123/performance-report.pdf"
)
```

### PR Tools Removed

**Removed Tools:**
- `ticket_create_pr`
- `ticket_link_pr`

**Migration Path:**

Use GitHub MCP server for PR operations + ticket comments for linking.

**Before:**
```python
ticket_create_pr(
    ticket_id="TICKET-123",
    title="Fix bug",
    description="Resolves TICKET-123",
    source_branch="fix/bug",
    target_branch="main"
)
```

**After:**
```python
# 1. Create PR via GitHub MCP
pr = mcp__github__create_pull_request(
    owner="myorg",
    repo="myrepo",
    title="Fix bug",
    head="fix/bug",
    base="main",
    body="Resolves TICKET-123\n\nFixed the authentication bug by..."
)

# 2. Link in ticket
ticket_comment(
    ticket_id="TICKET-123",
    operation="add",
    text=f"PR created: {pr['html_url']}"
)
```

**Benefits:**
- Reduced duplication with MCP servers
- More flexible file management
- Direct GitHub integration
- Cleaner separation of concerns
```

### Test Plan

**Total Tests:** 10 (deprecation warnings only)

**Deprecation Warning Tests (8):**
```python
def test_ticket_attach_deprecation_warning():
    """Test ticket_attach emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Use filesystem MCP"):
        ticket_attach(ticket_id="TICKET-123", file_path="/tmp/test.pdf")


def test_ticket_attachments_deprecation_warning():
    """Test ticket_attachments emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Use filesystem MCP"):
        ticket_attachments(ticket_id="TICKET-123")


def test_ticket_create_pr_deprecation_warning():
    """Test ticket_create_pr emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Use GitHub MCP"):
        ticket_create_pr(ticket_id="TICKET-123", title="Test PR")


def test_ticket_link_pr_deprecation_warning():
    """Test ticket_link_pr emits deprecation warning."""
    with pytest.warns(DeprecationWarning, match="Use GitHub MCP"):
        ticket_link_pr(ticket_id="TICKET-123", pr_url="https://github.com/org/repo/pull/1")


def test_attachment_still_functional():
    """Test attachment tools still work in deprecated state."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = ticket_attach(ticket_id="TICKET-123", file_path="/tmp/test.pdf")
    assert result["status"] == "success"


def test_pr_still_functional():
    """Test PR tools still work in deprecated state."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = ticket_create_pr(ticket_id="TICKET-123", title="Test")
    assert result["status"] == "success"
```

**Migration Example Tests (2):**
```python
def test_attachment_migration_pattern():
    """Test filesystem MCP + comment pattern works."""
    ticket_id = "TICKET-123"

    # Write file via filesystem MCP
    file_path = f"./docs/tickets/{ticket_id}/test.pdf"
    mcp__filesystem__write_file(path=file_path, content=b"test content")

    # Add comment
    result = ticket_comment(
        ticket_id=ticket_id,
        operation="add",
        text=f"Attached file: {file_path}"
    )

    assert result["status"] == "success"


def test_pr_migration_pattern():
    """Test GitHub MCP + comment pattern works."""
    ticket_id = "TICKET-123"

    # Create PR via GitHub MCP (mocked)
    pr = {"html_url": "https://github.com/org/repo/pull/1"}

    # Link in ticket
    result = ticket_comment(
        ticket_id=ticket_id,
        operation="add",
        text=f"PR created: {pr['html_url']}"
    )

    assert result["status"] == "success"
```

---

## Sprint 1 Summary

### Deliverables Checklist

- [ ] **project_update consolidation complete**
  - [ ] Unified tool implemented
  - [ ] Action handlers functional
  - [ ] 15 tests passing
  - [ ] Deprecated tools emit warnings
  - [ ] Documentation updated

- [ ] **ticket_search consolidation complete**
  - [ ] include_hierarchy parameter added
  - [ ] 8 tests passing
  - [ ] Deprecated tool emits warnings
  - [ ] Documentation updated

- [ ] **Attachment/PR tools deprecated**
  - [ ] 10 tests passing (deprecation + migration)
  - [ ] Migration guide complete
  - [ ] Example patterns documented

- [ ] **Token savings validated**
  - [ ] Measured savings ≥ 5,644 tokens
  - [ ] MCP manifest updated
  - [ ] Token count documented

- [ ] **Documentation complete**
  - [ ] API docs updated
  - [ ] UPGRADING-v2.0.md sections added
  - [ ] Migration examples provided

### Success Metrics

**Quantitative:**
- Token savings: 5,644 tokens (target met)
- Test coverage: 100% maintained
- Tests written: 33 (all passing)
- Tools consolidated: 9

**Qualitative:**
- Action-based pattern established
- Clear migration paths documented
- Zero P0/P1 bugs discovered
- Ready for Sprint 2

### Risks and Mitigations

**Identified Risks:**
1. Users unaware of attachment/PR deprecation
   - **Mitigation:** Clear warnings, migration guide, 3-month window

2. ticket_search behavioral change
   - **Mitigation:** Default include_hierarchy=False maintains current behavior

3. project_update parameter validation too strict
   - **Mitigation:** Comprehensive tests, clear error messages

**Risk Status:** LOW (all risks mitigated)

---

## Next Steps

**Immediate (Sprint 1 completion):**
1. Merge Sprint 1 branch to main
2. Update CHANGELOG.md
3. Publish blog post announcing consolidation
4. Monitor for user feedback

**Sprint 2 Preparation:**
1. Review Sprint 1 patterns
2. Identify improvements for Sprint 2
3. Begin Sprint 2 design
4. Schedule Sprint 2 kickoff (Dec 9)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Next Review:** Sprint 1 completion (2025-12-06)
