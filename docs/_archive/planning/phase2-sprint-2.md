# Phase 2 Sprint 2: Medium Complexity Consolidations

**Sprint Duration:** 2.5 days (Dec 9-13, 2025)
**Token Savings Target:** 4,600 tokens
**Risk Level:** Medium
**Linear Ticket:** [1M-484](https://linear.app/1m-hyperdev/issue/1M-484)

---

## Sprint Goals

Sprint 2 focuses on **merging related operations** with moderate complexity. These consolidations improve API consistency while handling both single-item and bulk operations seamlessly.

**Primary Objectives:**
1. Merge bulk operations into standard operations
2. Consolidate user/session ticket tools
3. Verify instructions consolidation (may already be complete)
4. Support single AND bulk patterns uniformly
5. Achieve 4,600 tokens in savings

**Success Criteria:**
- 5 tools consolidated/deprecated
- 22 tests passing with 100% coverage
- Single/bulk operations work seamlessly
- Documentation complete for all changes
- Token savings validated (≥ 4,600)
- Zero P0/P1 bugs discovered

---

## Sprint 2.1: Bulk Operations Merge

**Duration:** 2 days (Mon-Tue, Dec 9-10)
**Token Savings:** 1,300 tokens
**Risk:** Medium

### Current State

**2 dedicated bulk tools:**
```python
mcp__mcp-ticketer__ticket_bulk_create(tickets: List[Dict]) -> Dict
mcp__mcp-ticketer__ticket_bulk_update(updates: List[Dict]) -> Dict
```

**Token Cost:**
- ticket_bulk_create: ~650 tokens
- ticket_bulk_update: ~650 tokens
- **Total:** 1,300 tokens

### Target State

**Enhance existing tools to accept single OR array:**

```python
# ticket_create and ticket_update automatically handle bulk
mcp__mcp-ticketer__ticket_create(
    data: Union[Dict, List[Dict]],  # Single object OR array
    **kwargs
) -> Dict

mcp__mcp-ticketer__ticket_update(
    data: Union[Dict, List[Dict]],  # Single object OR array
    **kwargs
) -> Dict
```

**Token Savings:** ~1,300 tokens (bulk tools removed)

### Implementation Details

**Enhanced ticket_create:**

```python
from typing import Union, List, Dict
from pydantic import BaseModel, validator

class TicketData(BaseModel):
    """Single ticket data."""
    title: str
    description: str = ""
    priority: str = "medium"
    tags: Optional[List[str]] = None
    assignee: Optional[str] = None


def ticket_create(
    data: Union[Dict, List[Dict]],
    **kwargs
) -> Dict:
    """
    Create one or more tickets.

    **Supports Bulk Operations:**
    - Pass single dict for single ticket
    - Pass list of dicts for bulk creation

    **Parameters:**
    - data (Dict | List[Dict]): Ticket data (single or array)
      - title (str): REQUIRED for each ticket
      - description (str): Optional description
      - priority (str): Optional priority (default: "medium")
      - tags (List[str]): Optional tags
      - assignee (str): Optional assignee

    **Returns:**
    Dict: Response with "status" and results:
      - Single: {"status": "success", "ticket": {...}}
      - Bulk: {"status": "success", "results": [...], "succeeded": N, "failed": M}

    **Examples:**

    Single ticket:
    >>> ticket_create(data={"title": "Fix bug", "priority": "high"})
    {"status": "success", "ticket": {"id": "TICKET-123", ...}}

    Bulk tickets:
    >>> ticket_create(data=[
    ...     {"title": "Bug 1", "priority": "high"},
    ...     {"title": "Bug 2", "priority": "medium"}
    ... ])
    {"status": "success", "results": [...], "succeeded": 2, "failed": 0}

    **Migration Guide:**

    Before (ticket_bulk_create):
    >>> ticket_bulk_create(tickets=[
    ...     {"title": "Bug 1"},
    ...     {"title": "Bug 2"}
    ... ])

    After (ticket_create with array):
    >>> ticket_create(data=[
    ...     {"title": "Bug 1"},
    ...     {"title": "Bug 2"}
    ... ])

    **See Also:**
    - docs/UPGRADING-v2.0.md#bulk-operations-merge
    """

    # Detect single vs bulk
    is_bulk = isinstance(data, list)

    if is_bulk:
        return _handle_bulk_create(data, **kwargs)
    else:
        return _handle_single_create(data, **kwargs)


def _handle_single_create(ticket_data: Dict, **kwargs) -> Dict:
    """Handle single ticket creation."""
    # Validate ticket data
    validated = TicketData(**ticket_data)

    # Create ticket (existing logic)
    from mcp_ticketer.tools.ticket import create_ticket

    result = create_ticket(
        title=validated.title,
        description=validated.description,
        priority=validated.priority,
        tags=validated.tags,
        assignee=validated.assignee,
        **kwargs
    )

    return {
        "status": "success",
        "ticket": result
    }


def _handle_bulk_create(tickets: List[Dict], **kwargs) -> Dict:
    """Handle bulk ticket creation."""
    results = []
    succeeded = 0
    failed = 0

    for i, ticket_data in enumerate(tickets):
        try:
            result = _handle_single_create(ticket_data, **kwargs)
            results.append({
                "index": i,
                "status": "success",
                "ticket": result["ticket"]
            })
            succeeded += 1
        except Exception as e:
            results.append({
                "index": i,
                "status": "error",
                "error": str(e),
                "ticket_data": ticket_data
            })
            failed += 1

    return {
        "status": "success" if failed == 0 else "partial",
        "results": results,
        "succeeded": succeeded,
        "failed": failed,
        "total": len(tickets)
    }
```

**Enhanced ticket_update:**

```python
def ticket_update(
    data: Union[Dict, List[Dict]],
    **kwargs
) -> Dict:
    """
    Update one or more tickets.

    **Supports Bulk Operations:**
    - Pass single dict for single ticket update
    - Pass list of dicts for bulk updates

    **Parameters:**
    - data (Dict | List[Dict]): Update data (single or array)
      - ticket_id (str): REQUIRED for each update
      - title (str): Optional new title
      - description (str): Optional new description
      - priority (str): Optional new priority
      - state (str): Optional new state
      - assignee (str): Optional new assignee

    **Returns:**
    Dict: Response with "status" and results (format matches input)

    **Examples:**

    Single update:
    >>> ticket_update(data={"ticket_id": "TICKET-123", "state": "done"})

    Bulk updates:
    >>> ticket_update(data=[
    ...     {"ticket_id": "TICKET-123", "state": "done"},
    ...     {"ticket_id": "TICKET-124", "priority": "high"}
    ... ])

    **Migration Guide:**

    Before (ticket_bulk_update):
    >>> ticket_bulk_update(updates=[
    ...     {"ticket_id": "TICKET-123", "state": "done"},
    ...     {"ticket_id": "TICKET-124", "state": "done"}
    ... ])

    After (ticket_update with array):
    >>> ticket_update(data=[
    ...     {"ticket_id": "TICKET-123", "state": "done"},
    ...     {"ticket_id": "TICKET-124", "state": "done"}
    ... ])
    """

    # Detect single vs bulk
    is_bulk = isinstance(data, list)

    if is_bulk:
        return _handle_bulk_update(data, **kwargs)
    else:
        return _handle_single_update(data, **kwargs)


def _handle_single_update(update_data: Dict, **kwargs) -> Dict:
    """Handle single ticket update."""
    ticket_id = update_data.get("ticket_id")
    if not ticket_id:
        raise ValueError("ticket_id required for update")

    # Update ticket (existing logic)
    from mcp_ticketer.tools.ticket import update_ticket

    result = update_ticket(ticket_id=ticket_id, **update_data, **kwargs)

    return {
        "status": "success",
        "ticket": result
    }


def _handle_bulk_update(updates: List[Dict], **kwargs) -> Dict:
    """Handle bulk ticket updates."""
    results = []
    succeeded = 0
    failed = 0

    for i, update_data in enumerate(updates):
        try:
            result = _handle_single_update(update_data, **kwargs)
            results.append({
                "index": i,
                "status": "success",
                "ticket": result["ticket"]
            })
            succeeded += 1
        except Exception as e:
            results.append({
                "index": i,
                "status": "error",
                "error": str(e),
                "update_data": update_data
            })
            failed += 1

    return {
        "status": "success" if failed == 0 else "partial",
        "results": results,
        "succeeded": succeeded,
        "failed": failed,
        "total": len(updates)
    }
```

### Deprecation Strategy

**Old Tools (Deprecated in v1.5.0):**

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="ticket_create")
def ticket_bulk_create(tickets: List[Dict]) -> Dict:
    """
    DEPRECATED: Use ticket_create(data=[...]) instead.

    This tool will be removed in v2.0.0. Migrate to ticket_create with array input.

    See: docs/UPGRADING-v2.0.md#bulk-operations-merge
    """
    warnings.warn(
        "ticket_bulk_create is deprecated. Use ticket_create(data=[...]) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return ticket_create(data=tickets)


@deprecated(version="1.5.0", removal="2.0.0", alternative="ticket_update")
def ticket_bulk_update(updates: List[Dict]) -> Dict:
    """
    DEPRECATED: Use ticket_update(data=[...]) instead.

    This tool will be removed in v2.0.0. Migrate to ticket_update with array input.

    See: docs/UPGRADING-v2.0.md#bulk-operations-merge
    """
    warnings.warn(
        "ticket_bulk_update is deprecated. Use ticket_update(data=[...]) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return ticket_update(data=updates)
```

### Test Plan

**Total Tests:** 12

**Unit Tests (8):**
```python
def test_ticket_create_single():
    """Test single ticket creation."""
    result = ticket_create(data={"title": "Test Bug", "priority": "high"})
    assert result["status"] == "success"
    assert "ticket" in result
    assert result["ticket"]["title"] == "Test Bug"


def test_ticket_create_bulk():
    """Test bulk ticket creation."""
    result = ticket_create(data=[
        {"title": "Bug 1", "priority": "high"},
        {"title": "Bug 2", "priority": "medium"}
    ])
    assert result["status"] == "success"
    assert result["succeeded"] == 2
    assert result["failed"] == 0
    assert len(result["results"]) == 2


def test_ticket_create_bulk_partial_failure():
    """Test bulk creation with some failures."""
    result = ticket_create(data=[
        {"title": "Valid Bug"},
        {"description": "Missing title"},  # Invalid
        {"title": "Another Valid Bug"}
    ])
    assert result["status"] == "partial"
    assert result["succeeded"] == 2
    assert result["failed"] == 1


def test_ticket_update_single():
    """Test single ticket update."""
    result = ticket_update(data={"ticket_id": "TICKET-123", "state": "done"})
    assert result["status"] == "success"
    assert "ticket" in result


def test_ticket_update_bulk():
    """Test bulk ticket updates."""
    result = ticket_update(data=[
        {"ticket_id": "TICKET-123", "state": "done"},
        {"ticket_id": "TICKET-124", "priority": "high"}
    ])
    assert result["status"] == "success"
    assert result["succeeded"] == 2


def test_bulk_response_format_consistency():
    """Test bulk responses have consistent format."""
    result = ticket_create(data=[{"title": "Test"}])
    assert "results" in result
    assert "succeeded" in result
    assert "failed" in result
    assert "total" in result
    assert result["total"] == 1
```

**Backward Compatibility Tests (4):**
```python
def test_ticket_bulk_create_backward_compat():
    """Test deprecated ticket_bulk_create still works."""
    with pytest.warns(DeprecationWarning):
        result = ticket_bulk_create(tickets=[{"title": "Test"}])
    assert result["status"] == "success"


def test_ticket_bulk_update_backward_compat():
    """Test deprecated ticket_bulk_update still works."""
    with pytest.warns(DeprecationWarning):
        result = ticket_bulk_update(updates=[{"ticket_id": "TICKET-123", "state": "done"}])
    assert result["status"] == "success"


def test_bulk_migration_equivalence():
    """Test old bulk tools equal new tools with arrays."""
    tickets = [{"title": "Bug 1"}, {"title": "Bug 2"}]

    # Old tool
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result_old = ticket_bulk_create(tickets=tickets)

    # New tool
    result_new = ticket_create(data=tickets)

    # Should return same structure
    assert result_old["succeeded"] == result_new["succeeded"]
    assert len(result_old["results"]) == len(result_new["results"])
```

---

## Sprint 2.2: User/Session Ticket Consolidation

**Duration:** 1.5 days (Wed-Thu, Dec 11-12)
**Token Savings:** 1,800 tokens
**Risk:** Medium

### Current State

**3 user-related ticket tools:**
```python
mcp__mcp-ticketer__get_my_tickets(state, project_id, limit) -> Dict
mcp__mcp-ticketer__attach_ticket(action, ticket_id) -> Dict
mcp__mcp-ticketer__get_session_info() -> Dict
```

**Token Cost:**
- get_my_tickets: ~600 tokens
- attach_ticket: ~600 tokens
- get_session_info: ~600 tokens
- **Total:** 1,800 tokens

### Target State

**1 unified user tool:**

```python
mcp__mcp-ticketer__user(
    action: str,  # "get_tickets" | "attach_ticket" | "detach_ticket" | "session_info"
    ticket_id: Optional[str] = None,
    state: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 10
) -> Dict
```

**Token Cost:** ~700 tokens
**Savings:** 1,100 tokens

### Implementation Details

**Unified user tool:**

```python
def user(
    action: str,
    ticket_id: Optional[str] = None,
    state: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 10
) -> Dict:
    """
    Unified user and session management tool.

    **Consolidates:**
    - get_my_tickets() → action="get_tickets"
    - attach_ticket() → action="attach_ticket"
    - get_session_info() → action="session_info"

    **Available Actions:**

    - **get_tickets**: Get tickets assigned to current user
      - Optional: state, project_id, limit

    - **attach_ticket**: Associate current session with a ticket
      - Requires: ticket_id

    - **detach_ticket**: Remove session ticket association
      - No parameters required

    - **session_info**: Get current session information
      - No parameters required

    **Parameters:**
    - action (str): REQUIRED. The action to perform.
    - ticket_id (str): Ticket ID (required for attach_ticket)
    - state (str): Filter by state (optional for get_tickets)
    - project_id (str): Filter by project (optional for get_tickets)
    - limit (int): Max results (optional for get_tickets, default: 10)

    **Returns:**
    Dict: Action-specific response with "status" field.

    **Examples:**

    Get my tickets:
    >>> user(action="get_tickets", state="in_progress", limit=5)

    Attach to ticket:
    >>> user(action="attach_ticket", ticket_id="TICKET-123")

    Get session info:
    >>> user(action="session_info")

    **Migration Guide:**

    Before (get_my_tickets):
    >>> get_my_tickets(state="open", project_id="proj-123", limit=10)

    After:
    >>> user(action="get_tickets", state="open", project_id="proj-123", limit=10)

    Before (attach_ticket):
    >>> attach_ticket(action="set", ticket_id="TICKET-123")

    After:
    >>> user(action="attach_ticket", ticket_id="TICKET-123")

    Before (get_session_info):
    >>> get_session_info()

    After:
    >>> user(action="session_info")

    **See Also:**
    - docs/UPGRADING-v2.0.md#user-session-consolidation
    """

    # Validate action
    valid_actions = {"get_tickets", "attach_ticket", "detach_ticket", "session_info"}
    if action not in valid_actions:
        raise ValueError(f"action must be one of {valid_actions}")

    # Route to handler
    if action == "get_tickets":
        return _handle_get_my_tickets(state, project_id, limit)
    elif action == "attach_ticket":
        if not ticket_id:
            raise ValueError("ticket_id required for attach_ticket")
        return _handle_attach_ticket(ticket_id)
    elif action == "detach_ticket":
        return _handle_detach_ticket()
    elif action == "session_info":
        return _handle_session_info()


def _handle_get_my_tickets(state, project_id, limit) -> Dict:
    """Get tickets assigned to current user."""
    from mcp_ticketer.tools.user_tickets import get_user_tickets

    return get_user_tickets(state=state, project_id=project_id, limit=limit)


def _handle_attach_ticket(ticket_id: str) -> Dict:
    """Attach session to ticket."""
    from mcp_ticketer.session import attach_ticket_to_session

    attach_ticket_to_session(ticket_id)
    return {
        "status": "success",
        "message": f"Session attached to {ticket_id}",
        "ticket_id": ticket_id
    }


def _handle_detach_ticket() -> Dict:
    """Detach session from ticket."""
    from mcp_ticketer.session import detach_ticket_from_session

    detach_ticket_from_session()
    return {
        "status": "success",
        "message": "Session detached from ticket"
    }


def _handle_session_info() -> Dict:
    """Get session information."""
    from mcp_ticketer.session import get_session_info

    return get_session_info()
```

### Deprecation Strategy

**Old Tools (Deprecated in v1.5.0):**

```python
@deprecated(version="1.5.0", removal="2.0.0", alternative="user")
def get_my_tickets(state=None, project_id=None, limit=10) -> Dict:
    """
    DEPRECATED: Use user(action="get_tickets", ...) instead.

    See: docs/UPGRADING-v2.0.md#user-session-consolidation
    """
    warnings.warn(
        "get_my_tickets is deprecated. Use user(action='get_tickets', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return user(action="get_tickets", state=state, project_id=project_id, limit=limit)


@deprecated(version="1.5.0", removal="2.0.0", alternative="user")
def attach_ticket(action: str, ticket_id: Optional[str] = None) -> Dict:
    """
    DEPRECATED: Use user(action="attach_ticket"|"detach_ticket", ...) instead.

    See: docs/UPGRADING-v2.0.md#user-session-consolidation
    """
    warnings.warn(
        "attach_ticket is deprecated. Use user(action='attach_ticket'|'detach_ticket', ...) instead.",
        DeprecationWarning,
        stacklevel=2
    )

    if action == "set":
        return user(action="attach_ticket", ticket_id=ticket_id)
    elif action == "clear":
        return user(action="detach_ticket")
    elif action == "status":
        return user(action="session_info")
    else:
        raise ValueError(f"Unknown action: {action}")


@deprecated(version="1.5.0", removal="2.0.0", alternative="user")
def get_session_info() -> Dict:
    """
    DEPRECATED: Use user(action="session_info") instead.

    See: docs/UPGRADING-v2.0.md#user-session-consolidation
    """
    warnings.warn(
        "get_session_info is deprecated. Use user(action='session_info') instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return user(action="session_info")
```

### Test Plan

**Total Tests:** 10

**Unit Tests (6):**
```python
def test_user_get_tickets():
    """Test get_tickets action."""
    result = user(action="get_tickets", state="open", limit=5)
    assert result["status"] == "success"
    assert len(result["tickets"]) <= 5


def test_user_attach_ticket():
    """Test attach_ticket action."""
    result = user(action="attach_ticket", ticket_id="TICKET-123")
    assert result["status"] == "success"
    assert result["ticket_id"] == "TICKET-123"


def test_user_detach_ticket():
    """Test detach_ticket action."""
    result = user(action="detach_ticket")
    assert result["status"] == "success"


def test_user_session_info():
    """Test session_info action."""
    result = user(action="session_info")
    assert result["status"] == "success"
    assert "session_id" in result


def test_user_attach_requires_ticket_id():
    """Test attach_ticket requires ticket_id."""
    with pytest.raises(ValueError, match="ticket_id required"):
        user(action="attach_ticket")


def test_user_invalid_action():
    """Test invalid action raises error."""
    with pytest.raises(ValueError, match="action must be one of"):
        user(action="invalid_action")
```

**Backward Compatibility Tests (4):**
```python
def test_get_my_tickets_backward_compat():
    """Test deprecated get_my_tickets still works."""
    with pytest.warns(DeprecationWarning):
        result = get_my_tickets(state="open", limit=5)
    assert result["status"] == "success"


def test_attach_ticket_backward_compat():
    """Test deprecated attach_ticket still works."""
    with pytest.warns(DeprecationWarning):
        result = attach_ticket(action="set", ticket_id="TICKET-123")
    assert result["status"] == "success"


def test_get_session_info_backward_compat():
    """Test deprecated get_session_info still works."""
    with pytest.warns(DeprecationWarning):
        result = get_session_info()
    assert result["status"] == "success"


def test_user_migration_equivalence():
    """Test old tools equal new user tool."""
    # Old get_my_tickets
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result_old = get_my_tickets(state="open")

    # New user tool
    result_new = user(action="get_tickets", state="open")

    # Should return same tickets
    assert len(result_old["tickets"]) == len(result_new["tickets"])
```

---

## Sprint 2.3: Instructions Consolidation Verification

**Duration:** 0.5 days (Fri, Dec 13)
**Token Savings:** 1,500 tokens (verify if already complete)
**Risk:** Low

### Verification Tasks

**Check Current State:**

1. **Verify tools removed from MCP:**
   ```bash
   grep -r "instructions_" src/mcp_ticketer/mcp/tools/
   ```

2. **Check internal API still exists:**
   ```bash
   grep -r "def instructions_" src/mcp_ticketer/
   ```

3. **Verify token savings:**
   - Count tokens in old tool definitions
   - Confirm removal from MCP manifest

**Expected Outcome:**

Instructions tools were already removed from MCP in Phase 1, but internal Python API remains for direct usage. Sprint 2.3 verifies this is complete.

**If Already Complete:**
- Document verification
- Add to CHANGELOG
- Update token savings (already counted)

**If Not Complete:**
- Remove remaining MCP tool definitions
- Deprecate tools (if needed)
- Add tests for deprecation warnings

---

## Sprint 2 Summary

### Deliverables Checklist

- [ ] **Bulk operations merged**
  - [ ] ticket_create handles single/array
  - [ ] ticket_update handles single/array
  - [ ] 12 tests passing
  - [ ] Deprecated bulk tools emit warnings
  - [ ] Documentation updated

- [ ] **User/session tools consolidated**
  - [ ] Unified user() tool implemented
  - [ ] 10 tests passing
  - [ ] Deprecated tools emit warnings
  - [ ] Documentation updated

- [ ] **Instructions verification complete**
  - [ ] Removal confirmed
  - [ ] Token savings validated
  - [ ] Documentation updated

- [ ] **Token savings validated**
  - [ ] Measured savings ≥ 4,600 tokens
  - [ ] MCP manifest updated
  - [ ] Token count documented

- [ ] **Documentation complete**
  - [ ] API docs updated
  - [ ] UPGRADING-v2.0.md sections added
  - [ ] Migration examples provided

### Success Metrics

**Quantitative:**
- Token savings: 4,600 tokens (target met)
- Test coverage: 100% maintained
- Tests written: 22 (all passing)
- Tools consolidated: 5

**Qualitative:**
- Single/bulk pattern established
- User experience improved (fewer tools)
- Session management simplified
- Ready for Sprint 3

### Risks and Mitigations

**Identified Risks:**
1. Bulk operations break existing single-item usage
   - **Mitigation:** Auto-detect single vs array, maintain backward compatibility

2. Session state lost during migration
   - **Mitigation:** Database-backed sessions, no in-memory state

3. User confusion about attach_ticket action mapping
   - **Mitigation:** Clear migration guide, deprecation warnings

**Risk Status:** MEDIUM (all risks mitigated, monitoring required)

---

## Next Steps

**Immediate (Sprint 2 completion):**
1. Merge Sprint 2 branch to main
2. Update CHANGELOG.md
3. Monitor for user feedback on bulk operations
4. Publish updated migration guide

**Sprint 3 Preparation:**
1. Review Sprint 1+2 patterns
2. Design complex hierarchy routing
3. Plan ticket CRUD consolidation
4. Schedule Sprint 3 kickoff (Dec 16)

---

**Document Version:** 1.0
**Last Updated:** 2025-12-01
**Next Review:** Sprint 2 completion (2025-12-13)
