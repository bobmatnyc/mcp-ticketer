# MCP-Ticketer Workflow State Handling Fix Analysis

**Research Date:** 2025-11-28
**Ticket:** 1M-215
**Title:** Fix MCP-Ticketer workflow state handling in automation scripts
**Priority:** High
**Researcher:** Claude (Research Agent)
**Status:** Research Complete

---

## Executive Summary

This research analyzes workflow state handling issues in MCP-Ticketer automation scripts and provides comprehensive guidance for implementing direct MCP function calls. The investigation reveals that:

1. **Current workflow scripts use comment-based workflow tracking** - They do NOT attempt to change ticket states programmatically
2. **The ticket's problem description appears to be based on incorrect assumptions** - No "execute_auggie_with_context()" usage exists in the codebase
3. **MCP-Ticketer already provides robust state transition tools** - The `ticket_transition` MCP function with semantic state matching and validation
4. **Linear state mapping is well-documented and implemented** - Clear mapping between universal states (OPEN, IN_PROGRESS, etc.) and Linear's workflow states

**Key Finding:** The mentioned "smart-ticket-processor-*.sh" scripts **do not exist** in the codebase. The actual workflow scripts (`ops/scripts/linear/workflow.py`) deliberately **do not** perform state transitions, only comment-based workflow tracking.

---

## 1. Current State Analysis

### 1.1 Actual Workflow Script Implementation

**File:** `/Users/masa/Projects/mcp-ticketer/ops/scripts/linear/workflow.py`

The existing workflow script provides:
- Ticket creation (bugs, features, tasks)
- Comment management
- Workflow shortcuts via **comments only**

**Critical Finding:** The workflow shortcuts **intentionally do NOT change ticket states**:

```python
@app.command("start-work")
def start_work(ticket_id: str):
    """Mark ticket as started and add 'Starting work' comment.

    Note: State transitions are managed through Linear's web interface.
    This command only adds a comment to indicate work has started.
    """
    async def _start_work(adapter: LinearAdapter):
        comment_obj = Comment(
            ticket_id=ticket_id,
            content="🚀 Starting work on this ticket",
        )
        await adapter.add_comment(comment_obj)
        console.print(f"[green]✓[/green] Started work on {ticket_id}")
        console.print(
            "[dim]Note: Update status manually in Linear web interface[/dim]"
        )
```

**Similar pattern for:**
- `ready-review`: Adds "✅ Ready for review" comment
- `deployed`: Adds "🚀 Deployed to {environment}" comment

### 1.2 Why Scripts Avoid State Transitions

From `ops/scripts/linear/README.md` (lines 119-132):

> ⚠️ **State transitions are NOT automatically updated** in Linear. This is by design due to Linear's custom workflow states per team.
>
> **Rationale:** Linear teams have custom workflow states (e.g., "In Review", "Testing", "QA"). The universal state mapping cannot accurately represent these team-specific states, so manual status updates ensure correct workflow tracking.

**Design Decision:** Comment-based workflow tracking chosen to avoid assumptions about team-specific Linear workflow configurations.

### 1.3 Non-Existent Files

The ticket mentions:
- `ops/shared/scripts/monitoring/smart-ticket-processor-production.sh`
- `ops/shared/scripts/monitoring/smart-ticket-processor-staging.sh`
- `ops/shared/scripts/monitoring/smart-ticket-processor-test.sh`

**Research Finding:** These files **do not exist** in the codebase. Search results:

```bash
find /Users/masa/Projects/mcp-ticketer -name "*smart-ticket-processor*"
# No results

find /Users/masa/Projects/mcp-ticketer -name "*processor*.sh"
# No results

grep -r "execute_auggie_with_context" /Users/masa/Projects/mcp-ticketer
# Found in documentation/changelogs only, not in code
```

**Actual ops/ structure:**
```
ops/
└── scripts/
    └── linear/
        ├── practical-workflow.sh  (bash wrapper)
        ├── workflow.py            (Python CLI)
        └── README.md
```

### 1.4 No "execute_auggie_with_context" Usage

**Search Results:** This function is mentioned in:
- Documentation files (AI_CLIENT_INTEGRATION.md, QUICK_START.md)
- Changelogs and archived docs
- CLI setup commands (auggie_configure.py)

**BUT:** No actual automation scripts use this pattern. The function is part of **Auggie integration setup**, not automation workflows.

---

## 2. Linear State Mapping

### 2.1 Universal States to Linear States

**Source:** `src/mcp_ticketer/adapters/linear/types.py` (lines 31-52)

```python
class LinearStateMapping:
    """Mapping between universal TicketState and Linear workflow state types."""

    # Linear workflow state types
    TO_LINEAR: dict[TicketState, str] = {
        TicketState.OPEN: "unstarted",
        TicketState.IN_PROGRESS: "started",
        TicketState.READY: "unstarted",      # No direct equivalent
        TicketState.TESTED: "started",       # No direct equivalent
        TicketState.DONE: "completed",
        TicketState.CLOSED: "canceled",
        TicketState.WAITING: "unstarted",
        TicketState.BLOCKED: "unstarted",
    }

    FROM_LINEAR: dict[str, TicketState] = {
        "backlog": TicketState.OPEN,
        "unstarted": TicketState.OPEN,
        "started": TicketState.IN_PROGRESS,
        "completed": TicketState.DONE,
        "canceled": TicketState.CLOSED,
    }
```

### 2.2 Linear Workflow State Types

**Canonical Linear States** (from GraphQL API, `LinearWorkflowStateType` enum):

1. **backlog** - Work in backlog, not yet prioritized
2. **unstarted** - Work prioritized but not started
3. **started** - Work actively in progress
4. **completed** - Work finished and accepted
5. **canceled** - Work canceled or won't do

### 2.3 State Name Synonym Mapping

**Source:** `src/mcp_ticketer/adapters/linear/types.py` (lines 131-211)

Linear teams can customize **state names** while using standard **state types**. The adapter handles this with synonym matching:

```python
def get_universal_state(linear_state_type: str, state_name: str | None = None) -> TicketState:
    """Convert Linear workflow state type to universal TicketState with synonym matching.

    Synonym Matching Rules:
    - "Done", "Closed", "Cancelled", "Completed", "Won't Do" → CLOSED
    - "In Progress", "Working", "Active", "Started", "Doing" → IN_PROGRESS
    - "Review", "In Review", "Testing", "QA", "Ready for Review" → READY
    - Everything else → OPEN
    """
```

**Examples of team-specific states:**
- "ToDo" (state name) + "unstarted" (state type) → `TicketState.OPEN`
- "In Review" (state name) + "started" (state type) → `TicketState.READY`
- "Testing" (state name) + "started" (state type) → `TicketState.READY`

### 2.4 Complete State Mapping Table

| Universal State | Linear State Type | Common Linear State Names | Notes |
|----------------|-------------------|---------------------------|-------|
| `OPEN` | `unstarted` | "ToDo", "Backlog", "To Do", "Triage" | Not yet started |
| `IN_PROGRESS` | `started` | "In Progress", "Working", "In Dev", "Doing" | Actively working |
| `READY` | `started` or `unstarted` | "In Review", "PR Ready", "Testing", "QA" | Ready for review/test |
| `TESTED` | `started` | "QA Done", "Verified", "Approved" | Testing complete |
| `DONE` | `completed` | "Done", "Finished", "Delivered" | Work accepted |
| `CLOSED` | `canceled` | "Closed", "Cancelled", "Won't Do", "Rejected" | Archived/rejected |
| `WAITING` | `unstarted` | "Waiting", "On Hold", "Paused" | Blocked externally |
| `BLOCKED` | `unstarted` | "Blocked", "Stuck", "Impediment" | Cannot proceed |

---

## 3. MCP Ticket Transition Function Analysis

### 3.1 Function Signature

**Source:** `src/mcp_ticketer/mcp/server/tools/user_ticket_tools.py` (lines 264-525)

```python
@mcp.tool()
async def ticket_transition(
    ticket_id: str,
    to_state: str,
    comment: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """Move ticket through workflow with validation and optional comment.

    Supports natural language state inputs with semantic matching.

    Args:
        ticket_id: Unique identifier of the ticket to transition
        to_state: Target state (supports natural language!)
            Examples: "working on it", "needs review", "finished", "review"
        comment: Optional comment explaining the transition reason
        auto_confirm: Auto-apply high confidence matches (default: True)

    Returns:
        Dictionary containing:
        - status: "completed", "needs_confirmation", or "error"
        - ticket: Updated ticket object with new state (if completed)
        - previous_state: State before transition
        - new_state: State after transition
        - matched_state: Matched state from input (if semantic match used)
        - confidence: Confidence score (0.0-1.0) for semantic matches
        - original_input: Original user input
        - suggestions: Alternative matches (for ambiguous inputs)
        - comment_added: Whether a comment was added
        - error: Error details (if failed)
    """
```

### 3.2 Natural Language Support

**Semantic State Matcher** - Accepts natural phrases:

| Natural Language Input | Matched State | Confidence |
|------------------------|---------------|------------|
| "working on it" | `IN_PROGRESS` | 0.95 |
| "needs review" | `READY` | 0.95 |
| "pr ready" | `READY` | 0.95 |
| "finished" | `DONE` | 0.95 |
| "qa done" | `TESTED` | 0.95 |
| "blocked" | `BLOCKED` | 0.95 |
| "on hold" | `WAITING` | 0.95 |
| "won't do" | `CLOSED` | 0.95 |

**Typo Tolerance:**
- "reviw" → `READY` (0.80 confidence)
- "doen" → `DONE` (0.80 confidence)
- "bloked" → `BLOCKED` (0.85 confidence)

### 3.3 Validation and Error Handling

**Two-Layer Validation:**

1. **Workflow Validation** - Checks state machine rules:
   ```python
   # Source: core/models.py TicketState.can_transition_to()
   OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
   IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
   READY → TESTED, IN_PROGRESS, BLOCKED
   TESTED → DONE, IN_PROGRESS
   DONE → CLOSED
   WAITING → OPEN, IN_PROGRESS, CLOSED
   BLOCKED → OPEN, IN_PROGRESS, CLOSED
   CLOSED → (no transitions, terminal state)
   ```

2. **Parent/Child Constraint Validation** - Ensures parent issues stay ≥ child completion level:
   ```python
   # Source: core/adapter.py validate_transition() (lines 312-370)
   async def validate_transition(ticket_id: str, target_state: TicketState) -> bool:
       # Check workflow transition validity
       if not current_state.can_transition_to(target_state):
           return False

       # Check parent/child state constraint
       if ticket has children:
           max_child_level = max(child.state.completion_level() for child in children)
           if target_state.completion_level() < max_child_level:
               return False  # Cannot move parent behind children

       return True
   ```

**Error Response Examples:**

```python
# Invalid workflow transition
{
    "status": "error",
    "error": "Invalid transition from 'open' to 'done'",
    "reason": "workflow_violation",
    "valid_transitions": ["in_progress", "waiting", "blocked", "closed"],
    "message": "Cannot transition from open to done. Valid transitions: in_progress, waiting, blocked, closed"
}

# Parent/child constraint violation
{
    "status": "error",
    "error": "Cannot transition to 'open': parent issue has children in higher completion states",
    "reason": "parent_constraint_violation",
    "max_child_state": "in_progress",
    "message": "Cannot transition to open: parent issue has children in higher completion states (max child state: in_progress). Please update child states first."
}

# Ambiguous input
{
    "status": "ambiguous",
    "matched_state": "ready",
    "confidence": 0.65,
    "suggestions": [
        {"state": "ready", "confidence": 0.65, "description": "Work complete, ready for review or testing"},
        {"state": "closed", "confidence": 0.55, "description": "Ticket closed or archived (final state)"}
    ]
}
```

### 3.4 Usage Examples

**Basic Transition:**
```python
result = await ticket_transition(
    ticket_id="BTA-123",
    to_state="in_progress",
    comment="Started implementation"
)
# Returns:
# {
#     "status": "completed",
#     "ticket": {...},
#     "previous_state": "open",
#     "new_state": "in_progress",
#     "comment_added": True
# }
```

**Natural Language:**
```python
result = await ticket_transition(
    ticket_id="BTA-123",
    to_state="working on it",
    comment="Beginning feature work"
)
# Semantic matcher maps "working on it" → IN_PROGRESS
```

**Error Handling:**
```python
result = await ticket_transition(
    ticket_id="BTA-123",
    to_state="done"  # Invalid from OPEN
)
if result["status"] == "error":
    print(f"Transition failed: {result['message']}")
    print(f"Valid options: {result['valid_transitions']}")
```

---

## 4. Best Practices for State Transitions

### 4.1 Recommended Workflow

**Step 1: Check Available Transitions**
```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import get_available_transitions

# Get valid next states
transitions = await get_available_transitions("BTA-123")
print(transitions)
# {
#     "status": "completed",
#     "current_state": "open",
#     "available_transitions": ["in_progress", "waiting", "blocked", "closed"],
#     "transition_descriptions": {
#         "in_progress": "Begin active work on ticket",
#         "waiting": "Pause work while waiting for external dependency",
#         ...
#     }
# }
```

**Step 2: Perform Transition with Validation**
```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import ticket_transition

# Transition with comment
result = await ticket_transition(
    ticket_id="BTA-123",
    to_state="in_progress",
    comment="Started work on authentication feature"
)

if result["status"] == "completed":
    print(f"✓ Transitioned from {result['previous_state']} to {result['new_state']}")
else:
    print(f"✗ Error: {result['error']}")
```

### 4.2 State Validation Before Transition

**Always validate before attempting transition:**

```python
async def safe_transition(ticket_id: str, target_state: str, comment: str = None):
    """Safely transition ticket with validation."""
    # Get adapter
    from mcp_ticketer.mcp.server.server_sdk import get_adapter
    from mcp_ticketer.core.models import TicketState

    adapter = get_adapter()

    # Read current ticket
    ticket = await adapter.read(ticket_id)
    if not ticket:
        return {"status": "error", "error": f"Ticket {ticket_id} not found"}

    # Resolve target state (handles natural language)
    target = adapter.resolve_state(target_state)

    # Validate transition
    is_valid = await adapter.validate_transition(ticket_id, target)
    if not is_valid:
        # Get valid options
        current = ticket.state
        valid = TicketState.valid_transitions().get(current, [])
        return {
            "status": "error",
            "error": f"Invalid transition from {current.value} to {target.value}",
            "valid_transitions": [s.value for s in valid]
        }

    # Perform transition
    return await ticket_transition(ticket_id, target_state, comment)
```

### 4.3 Handling Custom Linear State Names

**Teams with custom states** (e.g., "In QA", "Code Review"):

```python
# Option 1: Use universal state names (always works)
await ticket_transition(ticket_id="BTA-123", to_state="ready")

# Option 2: Use semantic matching with team-specific names
await ticket_transition(ticket_id="BTA-123", to_state="in qa")
# Semantic matcher: "in qa" → READY (via synonym matching)

# Option 3: Use natural language
await ticket_transition(ticket_id="BTA-123", to_state="needs code review")
# Semantic matcher: "needs code review" → READY
```

### 4.4 Error Recovery Patterns

```python
async def robust_transition(ticket_id: str, to_state: str, comment: str = None):
    """Transition with fallback and retry logic."""
    result = await ticket_transition(ticket_id, to_state, comment)

    if result["status"] == "ambiguous":
        # Low confidence - ask user to clarify
        print(f"Ambiguous state '{to_state}'. Did you mean:")
        for suggestion in result["suggestions"]:
            print(f"  - {suggestion['state']}: {suggestion['description']}")

        # Use top suggestion if confidence > 0.70
        if result["confidence"] > 0.70:
            print(f"Using top match: {result['matched_state']}")
            return await ticket_transition(
                ticket_id,
                result["matched_state"],  # Use resolved state
                comment,
                auto_confirm=True
            )

    elif result["status"] == "error":
        if result.get("reason") == "parent_constraint_violation":
            # Handle parent/child constraint
            print(f"Cannot transition: child issues prevent this state change")
            print(f"Max child state: {result['max_child_state']}")
            print("Fix child states first, then retry")

        elif result.get("reason") == "workflow_violation":
            # Handle workflow violation
            print(f"Invalid transition. Valid options:")
            for state in result["valid_transitions"]:
                print(f"  - {state}")

    return result
```

---

## 5. Recommended Fix Approach

### 5.1 Problem Reframing

**Original Ticket Claims:**
1. Scripts use `execute_auggie_with_context()` to change states
2. Scripts assume states like "ToDo", "In Progress", "In Review"
3. Need direct MCP-ticketer transition function calls

**Actual Situation:**
1. No such scripts exist in the codebase
2. Existing scripts deliberately avoid state transitions
3. MCP-ticketer already provides robust transition tools

**Recommended Action:** Clarify ticket scope with stakeholders:
- Are new automation scripts needed?
- Should existing comment-based scripts be enhanced?
- Is there external automation (outside this repo) that needs fixing?

### 5.2 If New Automation Scripts Are Needed

**Create state-aware automation scripts:**

**File:** `ops/scripts/linear/automated-transitions.py`

```python
#!/usr/bin/env python3
"""Automated Linear ticket state transitions via MCP-Ticketer.

This script demonstrates direct MCP function usage for state transitions
with proper validation and error handling.
"""

import asyncio
import sys
from pathlib import Path

# Add project src to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import TicketState


async def transition_ticket(
    adapter: LinearAdapter,
    ticket_id: str,
    target_state: str,
    comment: str = None
):
    """Transition ticket using MCP-ticketer validation.

    Args:
        adapter: Initialized LinearAdapter instance
        ticket_id: Ticket identifier (e.g., "BTA-123")
        target_state: Target state (universal or natural language)
        comment: Optional transition comment

    Returns:
        Transition result dictionary
    """
    # Read current ticket
    ticket = await adapter.read(ticket_id)
    if not ticket:
        return {
            "status": "error",
            "error": f"Ticket {ticket_id} not found"
        }

    current_state = ticket.state
    print(f"Current state: {current_state.value}")

    # Resolve target state (handles natural language)
    try:
        resolved_state = adapter.resolve_state(target_state)
        print(f"Target state: {resolved_state.value}")
    except Exception as e:
        return {
            "status": "error",
            "error": f"Invalid state '{target_state}': {e}"
        }

    # Validate transition
    is_valid = await adapter.validate_transition(ticket_id, resolved_state)
    if not is_valid:
        valid_transitions = TicketState.valid_transitions().get(current_state, [])
        return {
            "status": "error",
            "error": f"Invalid transition from {current_state.value} to {resolved_state.value}",
            "valid_transitions": [s.value for s in valid_transitions],
            "message": f"Valid transitions: {', '.join(s.value for s in valid_transitions)}"
        }

    # Perform transition
    updated = await adapter.update(ticket_id, {"state": resolved_state})
    if not updated:
        return {
            "status": "error",
            "error": f"Failed to update ticket {ticket_id}"
        }

    # Add comment if provided
    comment_added = False
    if comment:
        try:
            from mcp_ticketer.core.models import Comment
            comment_obj = Comment(ticket_id=ticket_id, content=comment)
            await adapter.add_comment(comment_obj)
            comment_added = True
        except Exception as e:
            print(f"Warning: Failed to add comment: {e}")

    return {
        "status": "completed",
        "ticket_id": ticket_id,
        "previous_state": current_state.value,
        "new_state": resolved_state.value,
        "comment_added": comment_added
    }


async def main():
    """Example usage of automated transitions."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Configure adapter
    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_key": os.getenv("LINEAR_TEAM_KEY")
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    try:
        # Example: Start work on ticket
        result = await transition_ticket(
            adapter,
            ticket_id="BTA-123",
            target_state="in_progress",
            comment="🚀 Automated transition: Work started"
        )

        print(f"\n{'='*50}")
        print(f"Status: {result['status']}")
        if result['status'] == 'completed':
            print(f"✓ Transitioned {result['ticket_id']}")
            print(f"  From: {result['previous_state']}")
            print(f"  To: {result['new_state']}")
            if result['comment_added']:
                print(f"  Comment: Added")
        else:
            print(f"✗ Error: {result['error']}")
            if 'valid_transitions' in result:
                print(f"  Valid: {result['valid_transitions']}")
        print(f"{'='*50}\n")

    finally:
        await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 5.3 Migration Strategy

**If external scripts need updating:**

**Before (Hypothetical Auggie approach):**
```bash
# Unreliable indirect approach
execute_auggie_with_context "Change ticket BTA-123 to In Progress"
```

**After (Direct MCP approach):**
```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import ticket_transition

# Direct, validated transition
result = await ticket_transition(
    ticket_id="BTA-123",
    to_state="in_progress",
    comment="Automated state change"
)

if result["status"] != "completed":
    print(f"Error: {result['error']}")
    sys.exit(1)
```

### 5.4 Testing Strategy

**Unit Tests:**
```python
import pytest
from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import TicketState

@pytest.mark.asyncio
async def test_transition_validation():
    """Test state transition validation."""
    adapter = LinearAdapter(test_config)
    await adapter.initialize()

    # Create test ticket in OPEN state
    ticket = await adapter.create(Task(title="Test", state=TicketState.OPEN))

    # Valid transition: OPEN → IN_PROGRESS
    is_valid = await adapter.validate_transition(ticket.id, TicketState.IN_PROGRESS)
    assert is_valid is True

    # Invalid transition: OPEN → DONE
    is_valid = await adapter.validate_transition(ticket.id, TicketState.DONE)
    assert is_valid is False

    await adapter.close()

@pytest.mark.asyncio
async def test_semantic_state_matching():
    """Test natural language state resolution."""
    adapter = LinearAdapter(test_config)

    # Natural language → Universal state
    state = adapter.resolve_state("working on it")
    assert state == TicketState.IN_PROGRESS

    state = adapter.resolve_state("needs review")
    assert state == TicketState.READY

    state = adapter.resolve_state("finished")
    assert state == TicketState.DONE
```

**Integration Tests:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_workflow_transition():
    """Test complete workflow: OPEN → IN_PROGRESS → READY → DONE."""
    from mcp_ticketer.mcp.server.tools.user_ticket_tools import ticket_transition

    # Create ticket
    adapter = get_adapter()
    ticket = await adapter.create(Task(title="Integration Test"))
    ticket_id = ticket.id

    # Transition 1: OPEN → IN_PROGRESS
    result = await ticket_transition(
        ticket_id=ticket_id,
        to_state="working on it",
        comment="Started work"
    )
    assert result["status"] == "completed"
    assert result["new_state"] == "in_progress"

    # Transition 2: IN_PROGRESS → READY
    result = await ticket_transition(
        ticket_id=ticket_id,
        to_state="needs review",
        comment="PR created"
    )
    assert result["status"] == "completed"
    assert result["new_state"] == "ready"

    # Transition 3: READY → DONE (via TESTED)
    result = await ticket_transition(ticket_id, "tested")
    assert result["status"] == "completed"

    result = await ticket_transition(ticket_id, "done")
    assert result["status"] == "completed"
    assert result["new_state"] == "done"
```

---

## 6. Documentation References

### 6.1 Key Files

**State Transition Implementation:**
- `src/mcp_ticketer/mcp/server/tools/user_ticket_tools.py` - `ticket_transition()` and `get_available_transitions()`
- `src/mcp_ticketer/core/adapter.py` - `validate_transition()` base implementation
- `src/mcp_ticketer/core/models.py` - `TicketState` enum and workflow rules

**Linear Adapter:**
- `src/mcp_ticketer/adapters/linear/adapter.py` - LinearAdapter implementation
- `src/mcp_ticketer/adapters/linear/types.py` - State mapping (`LinearStateMapping`)
- `src/mcp_ticketer/adapters/linear/mappers.py` - Data transformation

**Semantic Matching:**
- `src/mcp_ticketer/core/state_matcher.py` - Natural language state resolution
- `docs/user-docs/guides/SEMANTIC_STATE_TRANSITIONS.md` - Complete guide

**Existing Workflow Scripts:**
- `ops/scripts/linear/workflow.py` - Comment-based workflow tracking
- `ops/scripts/linear/README.md` - Usage documentation

### 6.2 Related Documentation

**User Guides:**
- `docs/user-docs/guides/config_and_user_tools.md` - MCP tools reference
- `docs/user-docs/guides/SEMANTIC_STATE_TRANSITIONS.md` - Natural language states

**Developer Docs:**
- `docs/developer-docs/getting-started/CODE_STRUCTURE.md` - Architecture overview
- `docs/developer-docs/adapters/LINEAR.md` - Linear adapter details

**Architecture:**
- `docs/architecture/MCP_INTEGRATION.md` - MCP server design
- `docs/architecture/DESIGN.md` - Overall system design

---

## 7. Conclusions and Recommendations

### 7.1 Key Findings

1. **No broken automation scripts exist** - The mentioned files don't exist in the codebase
2. **Existing workflow scripts work as designed** - Comment-based tracking is intentional
3. **MCP-Ticketer provides complete state transition tools** - `ticket_transition()` with validation
4. **Linear state mapping is well-implemented** - Clear mapping with synonym support
5. **Natural language support is robust** - Semantic matching handles team-specific state names

### 7.2 Recommended Actions

**Immediate:**
1. **Clarify ticket scope** with ticket author - Identify what actually needs fixing
2. **Check for external automation** - Are there scripts outside this repo?
3. **Review Linear configuration** - Verify team-specific state names

**If New Features Needed:**
1. **Create automated transition scripts** using examples in Section 5.2
2. **Add comprehensive tests** following patterns in Section 5.4
3. **Document state mapping** for specific Linear teams

**If Existing Scripts Need Enhancement:**
1. **Add optional state transition mode** to `workflow.py`
2. **Keep comment-based mode** as default (safer for custom workflows)
3. **Add `--update-state` flag** for explicit state transitions

### 7.3 Next Steps for Engineer

**Before Implementation:**
1. Confirm ticket scope - What scripts need fixing?
2. Identify Linear team state configurations
3. Determine if automation is in-repo or external

**Implementation Checklist:**
- [ ] Use `ticket_transition()` MCP function directly
- [ ] Add `get_available_transitions()` validation before transitions
- [ ] Handle errors with `status` field checks
- [ ] Use universal state names (`open`, `in_progress`, etc.) or natural language
- [ ] Add comments explaining transitions
- [ ] Test against actual Linear team workflow states
- [ ] Validate parent/child state constraints

**Testing Checklist:**
- [ ] Test all workflow state transitions
- [ ] Test invalid transitions (expect errors)
- [ ] Test natural language inputs
- [ ] Test parent/child constraint scenarios
- [ ] Test error recovery patterns
- [ ] Verify Linear API state updates

### 7.4 Risk Assessment

**Low Risk:**
- Using `ticket_transition()` - Well-tested, production-ready
- Universal state names - Reliable mapping to Linear
- Validation logic - Prevents invalid transitions

**Medium Risk:**
- Team-specific state names - May need synonym mapping updates
- Parent/child constraints - Complex scenarios need thorough testing

**High Risk:**
- Bypassing validation - Never update states without `validate_transition()`
- Assuming state names - Always use semantic matching or universal names

---

## Appendix A: Complete Linear State Reference

### Universal States

```python
class TicketState(str, Enum):
    OPEN = "open"              # Initial, not started
    IN_PROGRESS = "in_progress"  # Actively working
    READY = "ready"             # Ready for review/test
    TESTED = "tested"           # Testing complete
    DONE = "done"               # Work accepted
    WAITING = "waiting"         # Waiting for dependency
    BLOCKED = "blocked"         # Blocked by impediment
    CLOSED = "closed"           # Archived/canceled
```

### Workflow Transitions

```
OPEN:
  → in_progress, waiting, blocked, closed

IN_PROGRESS:
  → ready, waiting, blocked, open

READY:
  → tested, in_progress, blocked

TESTED:
  → done, in_progress

DONE:
  → closed

WAITING:
  → open, in_progress, closed

BLOCKED:
  → open, in_progress, closed

CLOSED:
  → (terminal state, no transitions)
```

### Completion Levels

```python
OPEN: 0          # Not started
BLOCKED: 1       # Blocked
WAITING: 2       # Waiting
IN_PROGRESS: 3   # In progress
READY: 4         # Ready for review
TESTED: 5        # Tested
DONE: 6          # Complete
CLOSED: 7        # Archived
```

---

## Appendix B: Code Examples

### Example 1: Simple State Transition

```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import ticket_transition

async def start_work(ticket_id: str):
    """Start work on a ticket."""
    result = await ticket_transition(
        ticket_id=ticket_id,
        to_state="in_progress",
        comment="Started implementation"
    )

    if result["status"] == "completed":
        print(f"✓ Started work on {ticket_id}")
    else:
        print(f"✗ Error: {result['error']}")

    return result
```

### Example 2: Full Workflow Automation

```python
async def complete_workflow(ticket_id: str):
    """Complete full development workflow."""

    # 1. Start work
    await ticket_transition(ticket_id, "in_progress", "Started development")

    # 2. Ready for review
    await ticket_transition(ticket_id, "ready", "PR created: #123")

    # 3. Testing
    await ticket_transition(ticket_id, "tested", "All tests passing")

    # 4. Complete
    result = await ticket_transition(ticket_id, "done", "Merged and deployed")

    return result
```

### Example 3: Validation Before Transition

```python
from mcp_ticketer.mcp.server.tools.user_ticket_tools import (
    get_available_transitions,
    ticket_transition
)

async def safe_transition(ticket_id: str, target_state: str):
    """Transition with validation."""

    # Check available transitions
    transitions = await get_available_transitions(ticket_id)

    if transitions["status"] == "error":
        return transitions

    # Verify target is valid
    if target_state not in transitions["available_transitions"]:
        return {
            "status": "error",
            "error": f"Invalid transition to {target_state}",
            "valid_options": transitions["available_transitions"]
        }

    # Perform transition
    return await ticket_transition(ticket_id, target_state)
```

---

**End of Research Document**

**Next Actions:**
1. Attach this research to ticket 1M-215
2. Clarify ticket scope with stakeholders
3. Determine if implementation is needed
4. Follow recommended fix approach if proceeding
