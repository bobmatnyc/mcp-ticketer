# MCP Tools Consolidation Analysis

**Research Date:** 2025-12-27
**Researcher:** Claude Code (Research Agent)
**Project:** mcp-ticketer
**Objective:** Identify consolidation opportunities to reduce token usage from 23,869 tokens

---

## Executive Summary

**Current State:** 20 MCP tools consuming ~23,869 tokens
**Proposed State:** 14 tools (6 consolidations) saving ~6,200-8,500 tokens (26-36% reduction)
**Already Consolidated:** 6 tools (ticket, config, hierarchy, label, milestone, project_update)

### Key Findings

1. **High Priority Consolidations (estimated 4,800-6,500 tokens saved)**
   - Workflow tools consolidation: 2,400-3,200 tokens
   - Attachment tools consolidation: 1,200-1,600 tokens
   - Project tools consolidation: 1,200-1,700 tokens

2. **Medium Priority Consolidations (estimated 1,400-2,000 tokens saved)**
   - Deprecated tool removal: 800-1,200 tokens
   - Comment into ticket: 600-800 tokens

3. **Already Well-Optimized**
   - ticket (unified CRUD)
   - config (consolidated from 16 tools)
   - hierarchy (epics/issues/tasks)
   - label (unified label management)
   - milestone (milestone CRUD)
   - project_update (action-based routing)

---

## Current Tool Inventory

### File Structure
**Location:** `/Users/masa/Projects/mcp-ticketer/src/mcp_ticketer/mcp/server/tools/`

| File | Lines | Tools | Status |
|------|-------|-------|--------|
| config_tools.py | 1,627 | config | ✅ Consolidated (from 16 tools) |
| ticket_tools.py | 1,413 | ticket | ✅ Consolidated (CRUD) |
| label_tools.py | 942 | label | ✅ Consolidated (7 actions) |
| hierarchy_tools.py | 942 | hierarchy | ✅ Consolidated (epics/issues/tasks) |
| analysis_tools.py | 854 | ticket_analyze | ✅ Consolidated (5 actions) |
| project_update_tools.py | 473 | project_update | ✅ Consolidated (3 actions) |
| user_ticket_tools.py | 364 | get_available_transitions, ticket_transition | ⚠️ CONSOLIDATE |
| milestone_tools.py | 338 | milestone | ✅ Consolidated (6 actions) |
| bulk_tools.py | 330 | ticket_bulk | ✅ Consolidated (2 actions) |
| search_tools.py | 318 | ticket_search, ticket_search_hierarchy | ⚠️ REMOVE DEPRECATED |
| session_tools.py | 308 | user_session, attach_ticket | ⚠️ CONSOLIDATE |
| instruction_tools.py | 295 | (4 non-MCP helpers) | ℹ️ No MCP tools |
| attachment_tools.py | 226 | ticket_attach, ticket_attachments | ⚠️ CONSOLIDATE |
| diagnostic_tools.py | 211 | system_diagnostics, check_adapter_health | ⚠️ CONSOLIDATE |
| project_status_tools.py | 158 | project_status | ⚠️ CONSOLIDATE |
| comment_tools.py | 152 | ticket_comment | ⚠️ MERGE INTO TICKET |
| pr_tools.py | 150 | (2 non-MCP helpers) | ℹ️ No MCP tools |

**Total:** 9,170 lines of code
**Active MCP Tools:** 20

---

## Complete Tool List with Recommendations

### Already Consolidated Tools (Keep As-Is)

1. **ticket** (ticket_tools.py) - ✅ EXCELLENT
   - Actions: create, get, update, delete, list, summary, get_activity, assign
   - Consolidates 8 former tools
   - **Keep unchanged**

2. **config** (config_tools.py) - ✅ EXCELLENT
   - Actions: get, set, set_project_from_url, validate, test, list_adapters, get_requirements, setup_wizard
   - Consolidates 16 former tools
   - Token savings: ~7,200 tokens (90% reduction)
   - **Keep unchanged**

3. **hierarchy** (hierarchy_tools.py) - ✅ EXCELLENT
   - Entity types: epic, issue, task
   - Actions: create, get, list, update, delete, get_children, get_parent, get_tree
   - Consolidates 11 former tools
   - **Keep unchanged**

4. **label** (label_tools.py) - ✅ EXCELLENT
   - Actions: list, normalize, find_duplicates, suggest_merge, merge, rename, cleanup_report
   - Consolidates 7 former tools
   - **Keep unchanged**

5. **milestone** (milestone_tools.py) - ✅ EXCELLENT
   - Actions: create, get, list, update, delete, get_issues
   - Consolidates 6 former tools
   - **Keep unchanged**

6. **ticket_analyze** (analysis_tools.py) - ✅ EXCELLENT
   - Actions: find_similar, find_stale, find_orphaned, cleanup_report
   - Consolidates 5 former tools
   - **Keep unchanged**

7. **ticket_bulk** (bulk_tools.py) - ✅ GOOD
   - Actions: create, update
   - **Keep unchanged**

8. **project_update** (project_update_tools.py) - ✅ EXCELLENT
   - Actions: create, get, list
   - Consolidates 3 former tools
   - Token savings: ~1,100 tokens (69% reduction)
   - **Keep unchanged**

9. **ticket_search** (search_tools.py) - ✅ GOOD (with deprecation)
   - Consolidates ticket_search + ticket_search_hierarchy
   - include_hierarchy parameter for backward compatibility
   - **Keep unchanged, remove deprecated sibling**

10. **user_session** (session_tools.py) - ✅ GOOD
    - Actions: get_my_tickets, get_session_info
    - Consolidates 2 former tools
    - **Propose merge with attach_ticket**

### Tools to Consolidate

#### HIGH PRIORITY CONSOLIDATIONS

**1. WORKFLOW CONSOLIDATION** (user_ticket_tools.py)
- **Current:** 2 separate tools
  - get_available_transitions (55 lines)
  - ticket_transition (237 lines)
- **Total:** 364 lines, ~2,400-3,200 tokens
- **Proposed:** Single `workflow` tool with actions
  ```python
  workflow(action="get_transitions", ticket_id)
  workflow(action="transition", ticket_id, to_state, comment, auto_confirm)
  ```
- **Token Savings:** ~1,200-1,600 tokens (50% reduction)
- **Effort:** Low (similar pattern to existing consolidated tools)

**2. ATTACHMENT CONSOLIDATION** (attachment_tools.py)
- **Current:** 2 separate tools
  - ticket_attach (129 lines)
  - ticket_attachments (81 lines)
- **Total:** 226 lines, ~1,500-2,000 tokens
- **Proposed:** Single `attachment` tool with actions
  ```python
  attachment(action="attach", ticket_id, file_path, description)
  attachment(action="list", ticket_id)
  ```
- **Token Savings:** ~750-1,000 tokens (50% reduction)
- **Effort:** Low (straightforward action routing)

**3. PROJECT CONSOLIDATION** (project_status_tools.py + project_update_tools.py)
- **Current:** 2 separate tools
  - project_status (158 lines)
  - project_update (473 lines, already consolidated)
- **Total:** 631 lines, ~2,400-3,400 tokens
- **Proposed:** Single `project` tool with actions
  ```python
  project(action="status", project_id)
  project(action="create_update", project_id, body, health)
  project(action="get_update", update_id)
  project(action="list_updates", project_id, limit)
  ```
- **Token Savings:** ~1,200-1,700 tokens (50% reduction)
- **Effort:** Medium (project_update already has good action routing, add status action)
- **Alternative:** Keep separate but rename project_update → project (less disruptive)

#### MEDIUM PRIORITY CONSOLIDATIONS

**4. REMOVE DEPRECATED TOOL** (search_tools.py)
- **Current:** ticket_search_hierarchy (DEPRECATED in 1M-606)
- **Lines:** ~50 lines wrapper
- **Token Cost:** ~800-1,200 tokens
- **Action:** REMOVE entirely (functionality in ticket_search with include_hierarchy=True)
- **Token Savings:** ~800-1,200 tokens (100% reduction)
- **Effort:** Minimal (already deprecated, just delete)

**5. COMMENT CONSOLIDATION INTO TICKET** (comment_tools.py)
- **Current:** ticket_comment (152 lines, separate tool)
- **Token Cost:** ~1,000-1,200 tokens
- **Proposed:** Merge into `ticket` tool as new actions
  ```python
  ticket(action="add_comment", ticket_id, text)
  ticket(action="list_comments", ticket_id, limit, offset)
  ```
- **Token Savings:** ~600-800 tokens (50-60% reduction)
- **Effort:** Medium (requires updating ticket tool with comment actions)
- **Trade-off:** Increases ticket tool complexity, but improves cohesion

**6. SESSION CONSOLIDATION** (session_tools.py)
- **Current:** 2 separate tools
  - user_session (actions: get_my_tickets, get_session_info) - already consolidated
  - attach_ticket (standalone)
- **Lines:** attach_ticket ~118 lines
- **Token Cost:** attach_ticket ~800-1,000 tokens
- **Proposed:** Merge attach_ticket into user_session as new action
  ```python
  user_session(action="attach_ticket", ticket_id)
  user_session(action="detach_ticket")
  user_session(action="get_my_tickets", state, project_id, limit)
  user_session(action="get_session_info")
  ```
- **Token Savings:** ~400-600 tokens (50% reduction)
- **Effort:** Low (user_session already has action routing)

#### LOW PRIORITY (OPTIONAL)

**7. DIAGNOSTIC CONSOLIDATION** (diagnostic_tools.py)
- **Current:** 2 separate tools
  - system_diagnostics (99 lines)
  - check_adapter_health (97 lines)
- **Total:** 211 lines, ~1,400-1,800 tokens
- **Proposed:** Single `diagnostics` tool
  ```python
  diagnostics(action="system", simple)
  diagnostics(action="adapter", adapter_name)
  ```
- **Token Savings:** ~700-900 tokens (50% reduction)
- **Effort:** Low
- **Priority:** Low (diagnostic tools less frequently used)

---

## Consolidation Recommendations Summary

### Recommended Consolidations (Prioritized)

| Priority | Consolidation | Current Tools | New Tool | Est. Savings | Effort |
|----------|---------------|---------------|----------|--------------|--------|
| 1 (REMOVE) | Deprecated search | ticket_search_hierarchy | (delete) | 800-1,200 | Minimal |
| 2 (HIGH) | Workflow | get_available_transitions, ticket_transition | workflow | 1,200-1,600 | Low |
| 3 (HIGH) | Attachment | ticket_attach, ticket_attachments | attachment | 750-1,000 | Low |
| 4 (HIGH) | Project | project_status, project_update | project | 1,200-1,700 | Medium |
| 5 (MEDIUM) | Session | user_session, attach_ticket | user_session (expanded) | 400-600 | Low |
| 6 (MEDIUM) | Comment | ticket_comment | ticket (expanded) | 600-800 | Medium |
| 7 (LOW) | Diagnostics | system_diagnostics, check_adapter_health | diagnostics | 700-900 | Low |

### Total Token Savings

**Conservative Estimate:**
- Remove deprecated: 800 tokens
- Workflow: 1,200 tokens
- Attachment: 750 tokens
- Project: 1,200 tokens
- Session: 400 tokens
- Comment: 600 tokens
- **Total: ~5,000 tokens (21% reduction)**

**Optimistic Estimate:**
- Remove deprecated: 1,200 tokens
- Workflow: 1,600 tokens
- Attachment: 1,000 tokens
- Project: 1,700 tokens
- Session: 600 tokens
- Comment: 800 tokens
- Diagnostics: 900 tokens
- **Total: ~7,800 tokens (33% reduction)**

**Final Tool Count:**
- Current: 20 tools
- After consolidation: 13-14 tools (depending on diagnostics)
- Reduction: 6-7 tools (30-35% reduction)

---

## Implementation Plan

### Phase 1: Quick Wins (Est. 2,000-2,400 tokens)
1. **Remove ticket_search_hierarchy** (DEPRECATED)
   - File: search_tools.py
   - Action: Delete @mcp.tool() decorator and function
   - Testing: Verify ticket_search(include_hierarchy=True) works
   - Time: 1 hour

2. **Consolidate workflow tools**
   - File: user_ticket_tools.py
   - Create: workflow(action, ticket_id, to_state, comment, auto_confirm)
   - Actions: get_transitions, transition
   - Testing: Test state machine validation, semantic matching
   - Time: 3-4 hours

### Phase 2: Medium Impact (Est. 1,950-2,700 tokens)
3. **Consolidate attachment tools**
   - File: attachment_tools.py
   - Create: attachment(action, ticket_id, file_path, description)
   - Actions: attach, list
   - Testing: Test Linear upload, adapter fallbacks
   - Time: 2-3 hours

4. **Consolidate project tools**
   - Files: project_status_tools.py, project_update_tools.py
   - Option A: Merge into single project() tool
   - Option B: Rename project_update → project, add status action
   - Actions: status, create_update, get_update, list_updates
   - Testing: Test status analysis, update creation
   - Time: 4-5 hours

### Phase 3: Refinement (Est. 1,000-1,400 tokens)
5. **Merge attach_ticket into user_session**
   - File: session_tools.py
   - Add actions: attach_ticket, detach_ticket
   - Testing: Test session persistence, opt-out
   - Time: 2-3 hours

6. **Merge ticket_comment into ticket**
   - Files: comment_tools.py, ticket_tools.py
   - Add actions to ticket: add_comment, list_comments
   - Testing: Test URL routing, pagination
   - Time: 3-4 hours

### Phase 4: Optional (Est. 700-900 tokens)
7. **Consolidate diagnostics tools**
   - File: diagnostic_tools.py
   - Create: diagnostics(action, simple, adapter_name)
   - Actions: system, adapter
   - Testing: Test full/simple diagnostics, adapter health
   - Time: 2-3 hours

---

## Code Examples

### Workflow Consolidation Pattern

**Before:**
```python
@mcp.tool()
async def get_available_transitions(ticket_id: str) -> dict[str, Any]:
    ...

@mcp.tool()
async def ticket_transition(ticket_id, to_state, comment, auto_confirm) -> dict[str, Any]:
    ...
```

**After:**
```python
@mcp.tool()
async def workflow(
    action: Literal["get_transitions", "transition"],
    ticket_id: str,
    to_state: str | None = None,
    comment: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """Unified workflow management for ticket state transitions.

    Args:
        action: Operation - "get_transitions" or "transition"
        ticket_id: Ticket ID (required)
        to_state: Target state (required for transition)
        comment: Optional comment (for transition)
        auto_confirm: Auto-confirm medium confidence matches (default: True)
    """
    if action == "get_transitions":
        return await _handle_get_transitions(ticket_id)
    elif action == "transition":
        if not to_state:
            return {"status": "error", "error": "to_state required for transition action"}
        return await _handle_transition(ticket_id, to_state, comment, auto_confirm)
    else:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be 'get_transitions' or 'transition'",
        }
```

### Attachment Consolidation Pattern

**Before:**
```python
@mcp.tool()
async def ticket_attach(ticket_id, file_path, description) -> dict[str, Any]:
    ...

@mcp.tool()
async def ticket_attachments(ticket_id) -> dict[str, Any]:
    ...
```

**After:**
```python
@mcp.tool()
async def attachment(
    action: Literal["attach", "list"],
    ticket_id: str,
    file_path: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Unified attachment management for tickets.

    Args:
        action: Operation - "attach" or "list"
        ticket_id: Ticket ID (required)
        file_path: Path to file (required for attach)
        description: File description (optional for attach)
    """
    if action == "attach":
        if not file_path:
            return {"status": "error", "error": "file_path required for attach action"}
        return await _handle_attach(ticket_id, file_path, description)
    elif action == "list":
        return await _handle_list_attachments(ticket_id)
    else:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be 'attach' or 'list'",
        }
```

### Project Consolidation Pattern

**Option A: Full Consolidation**
```python
@mcp.tool()
async def project(
    action: Literal["status", "create_update", "get_update", "list_updates"],
    project_id: str | None = None,
    update_id: str | None = None,
    body: str | None = None,
    health: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Unified project management for status and updates.

    Actions:
        - status: Analyze project health and generate work plan
        - create_update: Create project status update
        - get_update: Get specific update by ID
        - list_updates: List updates for project
    """
    if action == "status":
        return await _handle_project_status(project_id)
    elif action == "create_update":
        return await _handle_create_update(project_id, body, health)
    elif action == "get_update":
        return await _handle_get_update(update_id)
    elif action == "list_updates":
        return await _handle_list_updates(project_id, limit)
    else:
        return {"status": "error", "error": f"Invalid action '{action}'"}
```

**Option B: Rename and Extend (Less Disruptive)**
```python
# Rename project_update → project
# Add status action to existing action list

@mcp.tool()
async def project(
    action: Literal["status", "create_update", "get_update", "list_updates"],
    # ... rest of parameters
) -> dict[str, Any]:
    """Unified project management (formerly project_update + project_status)."""
    if action == "status":
        # Move logic from project_status here
        ...
    # Keep existing update actions
    ...
```

---

## Migration Guide for Users

### Deprecated Tool Removals

**ticket_search_hierarchy** → Use `ticket_search(include_hierarchy=True)`
```python
# OLD (deprecated)
await ticket_search_hierarchy(query="feature", project_id="proj-123")

# NEW (use this)
await ticket_search(query="feature", project_id="proj-123", include_hierarchy=True)
```

### Workflow Tools

**get_available_transitions** → `workflow(action="get_transitions")`
```python
# OLD
await get_available_transitions(ticket_id="PROJ-123")

# NEW
await workflow(action="get_transitions", ticket_id="PROJ-123")
```

**ticket_transition** → `workflow(action="transition")`
```python
# OLD
await ticket_transition(ticket_id="PROJ-123", to_state="in_progress", comment="Starting work")

# NEW
await workflow(action="transition", ticket_id="PROJ-123", to_state="in_progress", comment="Starting work")
```

### Attachment Tools

**ticket_attach** → `attachment(action="attach")`
```python
# OLD
await ticket_attach(ticket_id="PROJ-123", file_path="/path/to/file.pdf", description="Report")

# NEW
await attachment(action="attach", ticket_id="PROJ-123", file_path="/path/to/file.pdf", description="Report")
```

**ticket_attachments** → `attachment(action="list")`
```python
# OLD
await ticket_attachments(ticket_id="PROJ-123")

# NEW
await attachment(action="list", ticket_id="PROJ-123")
```

### Project Tools

**project_status** → `project(action="status")`
```python
# OLD
await project_status(project_id="proj-123")

# NEW
await project(action="status", project_id="proj-123")
```

**project_update (create)** → `project(action="create_update")`
```python
# OLD
await project_update(action="create", project_id="proj-123", body="Sprint complete", health="on_track")

# NEW
await project(action="create_update", project_id="proj-123", body="Sprint complete", health="on_track")
```

### Session Tools

**attach_ticket** → `user_session(action="attach_ticket")`
```python
# OLD
await attach_ticket(action="set", ticket_id="PROJ-123")

# NEW
await user_session(action="attach_ticket", ticket_id="PROJ-123")
```

### Comment Tools

**ticket_comment** → `ticket(action="add_comment")` or `ticket(action="list_comments")`
```python
# OLD
await ticket_comment(ticket_id="PROJ-123", operation="add", text="Great work!")

# NEW
await ticket(action="add_comment", ticket_id="PROJ-123", text="Great work!")

# OLD
await ticket_comment(ticket_id="PROJ-123", operation="list", limit=10)

# NEW
await ticket(action="list_comments", ticket_id="PROJ-123", limit=10)
```

---

## Testing Strategy

### Unit Tests to Create/Update

1. **Workflow Tool Tests**
   - test_workflow_get_transitions()
   - test_workflow_transition_valid()
   - test_workflow_transition_invalid()
   - test_workflow_semantic_matching()
   - test_workflow_auto_confirm()

2. **Attachment Tool Tests**
   - test_attachment_attach_success()
   - test_attachment_attach_file_not_found()
   - test_attachment_list_success()
   - test_attachment_adapter_fallback()

3. **Project Tool Tests**
   - test_project_status_analysis()
   - test_project_create_update()
   - test_project_get_update()
   - test_project_list_updates()

4. **Session Tool Tests** (extend existing)
   - test_user_session_attach_ticket()
   - test_user_session_detach_ticket()
   - test_user_session_get_my_tickets()
   - test_user_session_get_session_info()

5. **Ticket Tool Tests** (extend existing)
   - test_ticket_add_comment()
   - test_ticket_list_comments()
   - test_ticket_comment_pagination()

### Integration Tests

- E2E workflow: Create ticket → Transition states → Attach file → Add comment
- Multi-adapter tests for URL routing in comments
- Session persistence across tool calls
- Project status → Create update → List updates flow

---

## Risk Assessment

### Low Risk
- ✅ Remove ticket_search_hierarchy (already deprecated)
- ✅ Consolidate workflow tools (self-contained)
- ✅ Consolidate attachment tools (straightforward)

### Medium Risk
- ⚠️ Consolidate project tools (affects PM workflows)
- ⚠️ Merge attach_ticket into user_session (session state sensitive)

### Higher Risk
- ⚠️ Merge ticket_comment into ticket (large tool, complex routing)
  - Mitigation: Extensive testing, gradual rollout

### Breaking Changes
All consolidations introduce breaking changes requiring migration:
- Update client code using old tool names
- Update documentation and examples
- Deprecation warnings before removal
- Version bump: 2.2.x → 2.3.0 or 3.0.0

---

## Success Metrics

### Quantitative
- Token usage reduction: 21-33% (5,000-7,800 tokens)
- Tool count reduction: 30-35% (6-7 fewer tools)
- Lines of code: Slight reduction or neutral
- Test coverage: Maintain >80% coverage

### Qualitative
- Improved developer experience (fewer tools to learn)
- Consistent action-based patterns across all tools
- Easier maintenance (less code duplication)
- Better discoverability (related operations grouped)

---

## Alternative Approaches Considered

### 1. Keep All Tools Separate
**Pros:** No breaking changes, simple
**Cons:** High token usage, scattered functionality
**Verdict:** ❌ Not recommended (doesn't solve the problem)

### 2. Mega-Consolidation (Single "mcp_ticketer" Tool)
**Pros:** Ultimate token reduction
**Cons:** Too complex, poor UX, hard to maintain
**Verdict:** ❌ Not recommended (over-optimization)

### 3. Gradual Consolidation (Recommended)
**Pros:** Controlled risk, incremental improvement
**Cons:** Takes longer, requires migration path
**Verdict:** ✅ **RECOMMENDED** (balanced approach)

### 4. Parameter-Based Routing Instead of Actions
**Example:** `workflow(get_transitions=True, ticket_id=...)`
**Pros:** Slightly fewer parameters
**Cons:** Harder to validate, less clear intent
**Verdict:** ❌ Not recommended (action-based is clearer)

---

## Related Tickets and Documentation

### Relevant Tickets
- 1M-606: ticket_search consolidation (completed)
- 1M-484: Phase 2 Sprint 1.1 - project_update consolidation (completed)
- 1M-487: Phase 3 Sprint 3.4 - project tools consolidation (in progress)
- 1M-238: Add project updates support (completed)

### Documentation to Update
- `docs/mcp-api-reference.md` - Tool API documentation
- `docs/ticket-workflows.md` - Workflow state transitions
- `README.md` - Quick start examples
- `UPGRADING-v2.0.md` - Migration guide (create if doesn't exist)

---

## Conclusion

The mcp-ticketer codebase has already implemented excellent consolidation patterns with tools like `config` (16→1), `ticket` (8→1), and `hierarchy` (11→1). The remaining consolidation opportunities follow these proven patterns.

**Recommended Approach:**
1. **Phase 1 (Quick Wins):** Remove deprecated + consolidate workflow tools → 2,000-2,400 tokens
2. **Phase 2 (Medium Impact):** Consolidate attachment + project tools → 1,950-2,700 tokens
3. **Phase 3 (Refinement):** Session + comment consolidations → 1,000-1,400 tokens
4. **Phase 4 (Optional):** Diagnostics consolidation → 700-900 tokens

**Total Impact:** 5,650-7,400 tokens saved (24-31% reduction) with 13-14 final tools (vs. 20 current).

The action-based routing pattern is well-established in the codebase and proven to work effectively. All proposed consolidations follow this same pattern, reducing implementation risk.

---

**Next Steps:**
1. Review this analysis with project maintainers
2. Create implementation tickets for each consolidation
3. Start with Phase 1 (low risk, high impact)
4. Gather user feedback after each phase
5. Adjust plan based on real-world usage patterns
