# Linear Adapter Filtering Issues Analysis

**Research Date**: 2025-11-24
**Researcher**: Research Agent
**Status**: Analysis Complete

---

## Executive Summary

This analysis investigates two critical filtering bugs in the Linear adapter:

1. **Bug 1 - State Mapping Issue**: Tickets with Linear state "ToDo" are NOT returned when querying for `state="open"`, resulting in incomplete search results.
2. **Bug 2 - Missing Project/Epic Filter**: The `search()` method lacks support for project/epic filtering, making it impossible to filter tickets by Linear view or project context.

**Impact**: Both bugs prevent accurate filtering of Linear tickets, resulting in incomplete or irrelevant search results for users.

---

## Bug 1: State Mapping Issue - "ToDo" Not Mapped to "open"

### Root Cause

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/types.py`

The Linear adapter uses a state type mapping system that converts universal `TicketState` enums to Linear's workflow state types. The current mapping is:

```python
# types.py lines 46-52
FROM_LINEAR: dict[str, TicketState] = {
    "backlog": TicketState.OPEN,
    "unstarted": TicketState.OPEN,
    "started": TicketState.IN_PROGRESS,
    "completed": TicketState.DONE,
    "canceled": TicketState.CLOSED,
}
```

**The Problem**: Linear has TWO types of "open" states:
- `"backlog"` - Pre-prioritized items
- `"unstarted"` - Ready-to-work items (including "ToDo", "To Do", "Backlog", etc.)

When users query for `state="open"`, the adapter converts this to Linear state type `"unstarted"`:

```python
# types.py lines 35-44
TO_LINEAR: dict[TicketState, str] = {
    TicketState.OPEN: "unstarted",
    # ...
}
```

This filtering happens in the `search()` method:

```python
# adapter.py lines 1810-1812
if query.state:
    state_type = get_linear_state_type(query.state)  # Returns "unstarted" for OPEN
    issue_filter["state"] = {"type": {"eq": state_type}}  # Filters by type="unstarted"
```

**However**, the reverse mapping (`get_universal_state()`) maps BOTH "unstarted" AND "backlog" to `TicketState.OPEN`:

```python
# types.py lines 46-48
FROM_LINEAR: dict[str, TicketState] = {
    "backlog": TicketState.OPEN,
    "unstarted": TicketState.OPEN,
}
```

This creates a **logical inconsistency**:
- When **filtering**, `state="open"` only matches Linear `type="unstarted"`
- When **reading**, both `type="unstarted"` AND `type="backlog"` are mapped to `TicketState.OPEN`

### Evidence

User reported:
```
Query: ticket_search(query: "epstein island", state: "open", limit: 100)
Result: Multiple tickets with state "ToDo" exist but are NOT returned
```

Expected behavior: All tickets with Linear states that map to `TicketState.OPEN` should be returned, including:
- `type="unstarted"` with name="ToDo"
- `type="backlog"` with any name

### State Name vs State Type Confusion

Linear has a two-level state system:
1. **State Type** (technical): `"backlog"`, `"unstarted"`, `"started"`, `"completed"`, `"canceled"`
2. **State Name** (user-facing): `"ToDo"`, `"In Progress"`, `"Done"`, etc. (customizable)

The adapter currently:
- **Filters by state type** (e.g., `type="unstarted"`)
- **Maps using state type** (ignoring state name)

However, the recent fix (1M-164) added synonym matching for state names:

```python
# types.py lines 131-187
def get_universal_state(linear_state_type: str, state_name: str | None = None) -> TicketState:
    """Convert Linear workflow state type to universal TicketState with synonym matching."""

    # First try exact type match
    if linear_state_type in LinearStateMapping.FROM_LINEAR:
        return LinearStateMapping.FROM_LINEAR[linear_state_type]

    # If no exact match and state_name provided, try synonym matching
    if state_name:
        state_name_lower = state_name.lower().strip()

        # Check for "done/closed" synonyms
        closed_synonyms = ["done", "closed", "cancelled", ...]
        if any(synonym in state_name_lower for synonym in closed_synonyms):
            return TicketState.DONE if state_name_lower == "done" else TicketState.CLOSED

        # Default: everything else is OPEN (including "ToDo", "Backlog", "To Do", etc.)
        return TicketState.OPEN
```

**The issue**: This synonym matching only applies when **reading** tickets, not when **filtering**. The filter still uses state type mapping only.

### Fix Recommendations

**Option 1: Expand State Filter to Multiple Types (RECOMMENDED)**

When filtering for `state="open"`, include BOTH `"unstarted"` AND `"backlog"` types:

```python
# adapter.py search() method - PROPOSED FIX
if query.state:
    state_type = get_linear_state_type(query.state)

    # OPEN state should match BOTH unstarted AND backlog
    if query.state == TicketState.OPEN:
        issue_filter["state"] = {"type": {"in": ["unstarted", "backlog"]}}
    else:
        issue_filter["state"] = {"type": {"eq": state_type}}
```

**Benefits**:
- Preserves existing behavior for other states
- Matches the semantic expectation that "open" includes all not-yet-started work
- Aligns filtering with reading logic (both map to OPEN)

**Option 2: Use State Name Synonym Matching in Filters**

Query Linear for all states, then filter client-side using synonym matching. This would make filtering consistent with reading but requires fetching more data.

**NOT RECOMMENDED**: More expensive, less efficient.

**Option 3: Change Mapping to Only Use "unstarted"**

Remove `"backlog"` from the `FROM_LINEAR` mapping, treating it as a separate state. This would be a **breaking change** that affects existing users who rely on backlog items being treated as "open".

---

## Bug 2: Missing Project/Epic Filter in search()

### Root Cause

**Location**: `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/adapters/linear/adapter.py` lines 1780-1844

The `search()` method builds a comprehensive issue filter but **does NOT include project/epic filtering**:

```python
# adapter.py lines 1800-1830
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    # Build comprehensive issue filter
    issue_filter = {"team": {"id": {"eq": team_id}}}

    # Text search
    if query.query:
        issue_filter["title"] = {"containsIgnoreCase": query.query}

    # State filter
    if query.state:
        state_type = get_linear_state_type(query.state)
        issue_filter["state"] = {"type": {"eq": state_type}}

    # Priority filter
    if query.priority:
        linear_priority = get_linear_priority(query.priority)
        issue_filter["priority"] = {"eq": linear_priority}

    # Assignee filter
    if query.assignee:
        user_id = await self._get_user_id(query.assignee)
        if user_id:
            issue_filter["assignee"] = {"id": {"eq": user_id}}

    # Tags filter (labels in Linear)
    if query.tags:
        issue_filter["labels"] = {"some": {"name": {"in": query.tags}}}

    # Exclude archived by default
    issue_filter["archivedAt"] = {"null": True}

    # MISSING: No project/epic filter support!
```

**The Problem**: The `SearchQuery` model (in `core/models.py` lines 419-428) does NOT include a `project` or `parent_epic` field:

```python
class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str | None = Field(None, description="Text search query")
    state: TicketState | None = Field(None, description="Filter by state")
    priority: Priority | None = Field(None, description="Filter by priority")
    tags: list[str] | None = Field(None, description="Filter by tags")
    assignee: str | None = Field(None, description="Filter by assignee")
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")

    # MISSING: No project/epic field!
```

### Evidence

User reported:
```
User requests tickets from specific Linear view:
https://linear.app/1m-hyperdev/view/mcp-skills-issues-0d0359fabcf9

System returns tickets NOT in that project/epic
```

The user expected filtering by project/epic context, but the `search()` method has no mechanism to apply this filter.

### Existing Project Filter Infrastructure

The adapter DOES have project filtering infrastructure in the `build_issue_filter()` helper:

```python
# types.py lines 190-266
def build_issue_filter(
    state: TicketState | None = None,
    assignee_id: str | None = None,
    priority: Priority | None = None,
    team_id: str | None = None,
    project_id: str | None = None,  # <-- PROJECT FILTER EXISTS!
    parent_id: str | None = None,
    labels: list[str] | None = None,
    # ...
) -> dict[str, Any]:
    # ...

    # Project filter
    if project_id:
        issue_filter["project"] = {"id": {"eq": project_id}}  # <-- Filter implementation
```

However, the `search()` method doesn't use `build_issue_filter()` - it builds the filter manually and omits project filtering.

### Fix Recommendations

**Option 1: Add project Field to SearchQuery (RECOMMENDED)**

Extend the `SearchQuery` model to include project/epic filtering:

```python
# core/models.py - PROPOSED FIX
class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str | None = Field(None, description="Text search query")
    state: TicketState | None = Field(None, description="Filter by state")
    priority: Priority | None = Field(None, description="Filter by priority")
    tags: list[str] | None = Field(None, description="Filter by tags")
    assignee: str | None = Field(None, description="Filter by assignee")
    project: str | None = Field(None, description="Filter by project/epic")  # NEW
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
```

Then update the `search()` method to use this field:

```python
# adapter.py search() - PROPOSED FIX
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    # ...existing filter building...

    # Project/Epic filter (NEW)
    if query.project:
        project_id = await self._resolve_project_id(query.project)
        if project_id:
            issue_filter["project"] = {"id": {"eq": project_id}}

    # ...rest of method...
```

**Benefits**:
- Consistent with existing filter patterns
- Uses existing `_resolve_project_id()` infrastructure (supports slugs, names, UUIDs)
- Enables filtering by project/epic in searches

**Option 2: Refactor search() to Use build_issue_filter()**

Replace manual filter building with the existing `build_issue_filter()` helper:

```python
# adapter.py search() - ALTERNATIVE FIX
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    await self.initialize()
    team_id = await self._ensure_team_id()

    # Resolve project ID if provided
    project_id = None
    if query.project:
        project_id = await self._resolve_project_id(query.project)

    # Resolve assignee ID if provided
    assignee_id = None
    if query.assignee:
        assignee_id = await self._get_user_id(query.assignee)

    # Use existing build_issue_filter helper
    issue_filter = build_issue_filter(
        team_id=team_id,
        state=query.state,
        priority=query.priority,
        assignee_id=assignee_id,
        project_id=project_id,  # NEW
        labels=query.tags,
        include_archived=False,
    )

    # Add text search
    if query.query:
        issue_filter["title"] = {"containsIgnoreCase": query.query}

    # Execute query
    result = await self.client.execute_query(
        SEARCH_ISSUES_QUERY, {"filter": issue_filter, "first": query.limit}
    )
    # ...
```

**Benefits**:
- Reduces code duplication
- Uses battle-tested filter builder
- More maintainable

---

## Bug 3: Assignee Filter Working Correctly (No Issue Found)

### Analysis

The assignee filter in the `search()` method is properly implemented:

```python
# adapter.py lines 1820-1823
if query.assignee:
    user_id = await self._get_user_id(query.assignee)
    if user_id:
        issue_filter["assignee"] = {"id": {"eq": user_id}}
```

The `_get_user_id()` method (lines 1069-1113) handles:
- Email lookup (most specific)
- Display name search
- Name matching
- User ID passthrough

**Conclusion**: Assignee filtering is working as designed. No bug found.

---

## Priority Recommendations

### Immediate (Critical)

1. **Fix Bug 1 - State Mapping**: Expand "open" state filter to include both `"unstarted"` and `"backlog"` types
   - **Effort**: Low (5-10 lines of code)
   - **Impact**: High (fixes incomplete search results)
   - **Risk**: Low (preserves existing behavior for other states)

### High Priority

2. **Fix Bug 2 - Project Filtering**: Add `project` field to `SearchQuery` and implement filtering
   - **Effort**: Medium (requires core model change + adapter logic)
   - **Impact**: High (enables project/epic-scoped searches)
   - **Risk**: Low (additive change, doesn't break existing code)

---

## Implementation Notes

### Testing Recommendations

For Bug 1 (State Mapping):
```python
# Test that state="open" returns BOTH unstarted and backlog tickets
async def test_open_state_includes_backlog_and_unstarted():
    # Create ticket with type="backlog"
    # Create ticket with type="unstarted"
    # Search with state="open"
    # Assert both tickets returned
```

For Bug 2 (Project Filtering):
```python
# Test that project filter limits results to project's tickets
async def test_search_filters_by_project():
    # Create project
    # Create ticket in project
    # Create ticket NOT in project
    # Search with project=project_id
    # Assert only project ticket returned
```

### Backward Compatibility

Both fixes are **backward compatible**:
- Bug 1: Expands results (users get MORE tickets, not fewer)
- Bug 2: Adds optional filter (doesn't change behavior when not used)

---

## Code Locations

### Bug 1 - State Mapping
- **State type mapping**: `src/mcp_ticketer/adapters/linear/types.py` lines 31-52
- **State filter logic**: `src/mcp_ticketer/adapters/linear/adapter.py` lines 1810-1812
- **State synonym matching**: `src/mcp_ticketer/adapters/linear/types.py` lines 131-187

### Bug 2 - Project Filtering
- **SearchQuery model**: `src/mcp_ticketer/core/models.py` lines 419-428
- **search() method**: `src/mcp_ticketer/adapters/linear/adapter.py` lines 1780-1844
- **build_issue_filter() helper**: `src/mcp_ticketer/adapters/linear/types.py` lines 190-266
- **Project ID resolution**: `src/mcp_ticketer/adapters/linear/adapter.py` lines 475-632

---

## References

- Linear API Documentation: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- Linear Workflow States: https://linear.app/docs/workflow-states
- Ticket 1M-164: State synonym matching implementation (recently completed)

---

## Appendix: State Type vs State Name Reference

| Linear State Type | Common State Names | Universal State | Included in "open" Filter? |
|-------------------|-------------------|-----------------|---------------------------|
| `backlog`         | "Backlog"         | `OPEN`          | ❌ NO (Bug!) |
| `unstarted`       | "ToDo", "To Do"   | `OPEN`          | ✅ YES |
| `started`         | "In Progress"     | `IN_PROGRESS`   | N/A |
| `completed`       | "Done"            | `DONE`          | N/A |
| `canceled`        | "Canceled"        | `CLOSED`        | N/A |

**Key Insight**: Users expect `state="open"` to match ALL "not yet started" tickets, including both `backlog` and `unstarted` types. The current implementation only matches `unstarted`, causing incomplete results.
