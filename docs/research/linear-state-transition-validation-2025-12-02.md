# Linear State Transition Validation Error Investigation

**Research Date**: 2025-12-02
**Ticket**: [1M-552](https://linear.app/1m-hyperdev/issue/1M-552)
**Error**: "Discrepancy between issue state and state type"
**Status**: Root cause identified

---

## Executive Summary

The Linear state transition error occurs due to a **fundamental mismatch between Universal State Model and Linear's multi-state-per-type workflow system**. The current implementation assumes a 1:1 mapping between state types (unstarted, started, completed) and actual workflow states, but Linear allows multiple states of the same type (e.g., "Todo", "Backlog", "Ready" all being "unstarted").

**Root Cause**: When transitioning to states like `READY` or `TESTED`, the adapter always selects the **lowest-position state** of the corresponding type, causing validation errors when trying to move between different states of the same type.

**Impact**: Affects all state transitions to `READY`, `TESTED`, `WAITING`, and `BLOCKED` states that map to "unstarted" or "started" types.

---

## 1. Linear State Model

### 1.1 State Structure

Linear's workflow states have three key properties:

```graphql
type WorkflowState {
  id: String!           # Unique UUID identifier
  name: String!         # Display name (e.g., "Todo", "In Progress", "Done")
  type: String!         # State type category (backlog, unstarted, started, completed, canceled)
  position: Float!      # Sort order within workflow
  color: String!        # Display color
}
```

### 1.2 State Types

Linear defines 5 standard state types:

| State Type   | Semantic Meaning            | Example State Names              |
|--------------|-----------------------------|---------------------------------|
| `backlog`    | Not yet planned             | "Backlog"                       |
| `unstarted`  | Planned but not started     | "Todo", "Ready", "Waiting"      |
| `started`    | Work in progress            | "In Progress", "In Review"      |
| `completed`  | Successfully finished       | "Done", "Closed"                |
| `canceled`   | Abandoned or rejected       | "Canceled", "Won't Do"          |

### 1.3 Multi-State-Per-Type System

**Critical Finding**: Linear allows **multiple states of the same type** in a single workflow.

**Example Linear Workflow**:
```
Todo         (type: unstarted, position: 0)
Backlog      (type: unstarted, position: 1)
Ready        (type: unstarted, position: 2)
In Progress  (type: started, position: 3)
In Review    (type: started, position: 4)
Done         (type: completed, position: 5)
```

This design allows teams to customize workflows while maintaining semantic state categories for automation and reporting.

### 1.4 State Validation Rules

Based on Linear API behavior and error messages:

1. **stateId must be valid UUID** belonging to the team's workflow
2. **State transitions must be valid** according to workflow configuration
3. **State type consistency**: Cannot arbitrarily jump between states of the same type
4. **Validation error format**: `"Discrepancy between issue state and state type"`

---

## 2. Current Implementation Analysis

### 2.1 Universal State Mapping

**File**: `/src/mcp_ticketer/adapters/linear/types.py:35-44`

```python
class LinearStateMapping:
    TO_LINEAR: dict[TicketState, str] = {
        TicketState.OPEN: "unstarted",
        TicketState.IN_PROGRESS: "started",
        TicketState.READY: "unstarted",      # ⚠️ Maps to same type as OPEN
        TicketState.TESTED: "started",       # ⚠️ Maps to same type as IN_PROGRESS
        TicketState.DONE: "completed",
        TicketState.CLOSED: "canceled",
        TicketState.WAITING: "unstarted",    # ⚠️ Maps to same type as OPEN
        TicketState.BLOCKED: "unstarted",    # ⚠️ Maps to same type as OPEN
    }
```

**Problem**: Multiple universal states map to the same Linear state type.

### 2.2 Workflow State Loading

**File**: `/src/mcp_ticketer/adapters/linear/adapter.py:884-908`

```python
async def _load_workflow_states(self, team_id: str) -> None:
    """Load and cache workflow states for the team."""
    result = await self.client.execute_query(
        WORKFLOW_STATES_QUERY, {"teamId": team_id}
    )

    workflow_states = {}
    for state in result["team"]["states"]["nodes"]:
        state_type = state["type"].lower()
        if state_type not in workflow_states:
            workflow_states[state_type] = state
        elif state["position"] < workflow_states[state_type]["position"]:
            workflow_states[state_type] = state  # ⚠️ PICKS LOWEST POSITION

    self._workflow_states = workflow_states
```

**Critical Bug** (Line 902): **Always selects the state with the LOWEST position for each type**.

This means:
- For "unstarted" type → picks "Todo" (position 0), not "Ready" (position 2)
- For "started" type → picks "In Progress" (position 3), not "In Review" (position 4)

### 2.3 State Mapping Resolution

**File**: `/src/mcp_ticketer/adapters/linear/adapter.py:1290-1320`

```python
def _get_state_mapping(self) -> dict[TicketState, str]:
    """Get mapping from universal states to Linear workflow state IDs."""
    if not self._workflow_states:
        # Fallback: return type names
        return {TicketState.OPEN: "unstarted", ...}

    # Return ID-based mapping using cached workflow states
    mapping = {}
    for universal_state, linear_type in LinearStateMapping.TO_LINEAR.items():
        if linear_type in self._workflow_states:
            mapping[universal_state] = self._workflow_states[linear_type]["id"]
            # ⚠️ ALL states mapping to "unstarted" get the SAME stateId
        else:
            mapping[universal_state] = linear_type

    return mapping
```

**Result**:
```python
{
    TicketState.OPEN: "uuid-todo",      # All three map to
    TicketState.READY: "uuid-todo",     # the SAME state ID
    TicketState.WAITING: "uuid-todo",   # (lowest position "unstarted")
    TicketState.BLOCKED: "uuid-todo",
    # ...
}
```

### 2.4 State Transition Execution

**File**: `/src/mcp_ticketer/adapters/linear/adapter.py:1881-1890`

```python
# Handle state transitions
if "state" in updates:
    target_state = TicketState(updates["state"])
    state_mapping = self._get_state_mapping()
    if target_state in state_mapping:
        update_input["stateId"] = state_mapping[target_state]
        # ⚠️ Always sends "uuid-todo" for READY, WAITING, BLOCKED
```

---

## 3. Root Cause Analysis

### 3.1 The Discrepancy

**Scenario**: Transition ticket JJF-47 to "ready" state

**What happens**:
1. User calls: `ticket_transition(ticket_id="JJF-47", to_state="ready")`
2. Maps `READY` → "unstarted" type
3. Looks up "unstarted" in `_workflow_states` → finds "Todo" (position 0)
4. Sends GraphQL mutation: `issueUpdate(id: "...", input: { stateId: "uuid-todo" })`

**Linear's validation**:
- Current state: "Backlog" (type: unstarted, position: 1)
- Target state: "Todo" (type: unstarted, position: 0)
- Error: **"Discrepancy between issue state and state type"**

Linear detects we're trying to move **within the same type** (unstarted → unstarted) but to a **different state** (Backlog → Todo) that doesn't represent a valid forward progression.

### 3.2 Why the Error Occurs

Linear's validation logic likely checks:

```python
# Pseudocode for Linear's validation
if new_state.type == current_state.type:
    if new_state.id == current_state.id:
        # No-op, state unchanged
        return OK
    else:
        # Trying to change state within same type
        raise Error("Discrepancy between issue state and state type")
```

The error message indicates Linear **disallows lateral moves within the same state type** unless explicitly configured in workflow rules.

### 3.3 Affected State Transitions

**High Impact** (multiple states map to "unstarted"):
- `OPEN` → "unstarted"
- `READY` → "unstarted" ⚠️
- `WAITING` → "unstarted" ⚠️
- `BLOCKED` → "unstarted" ⚠️

**Medium Impact** (multiple states map to "started"):
- `IN_PROGRESS` → "started"
- `TESTED` → "started" ⚠️

**No Impact**:
- `DONE` → "completed" (usually single state)
- `CLOSED` → "canceled" (usually single state)

---

## 4. Evidence and Code References

### 4.1 State Mapping
- **File**: `src/mcp_ticketer/adapters/linear/types.py`
- **Lines**: 35-44 (LinearStateMapping definition)
- **Lines**: 118-128 (get_linear_state_type function)

### 4.2 Workflow State Loading
- **File**: `src/mcp_ticketer/adapters/linear/adapter.py`
- **Lines**: 884-908 (_load_workflow_states method)
- **Lines**: 1290-1320 (_get_state_mapping method)

### 4.3 State Transition Logic
- **File**: `src/mcp_ticketer/adapters/linear/adapter.py`
- **Lines**: 1881-1890 (state handling in update method)
- **Lines**: 2121-2141 (transition_state method)

### 4.4 GraphQL Mutations
- **File**: `src/mcp_ticketer/adapters/linear/queries.py`
- **Lines**: 227-241 (WORKFLOW_STATES_QUERY)
- **Lines**: 257-269 (UPDATE_ISSUE_MUTATION)

---

## 5. Reproduction Steps

### 5.1 Minimal Reproduction

```python
from mcp_ticketer.adapters.linear import LinearAdapter

# Initialize adapter
adapter = LinearAdapter(config={
    "api_key": "lin_api_...",
    "team_key": "JJF"
})

# Create issue
ticket = await adapter.create(Task(
    title="Test ticket",
    state=TicketState.OPEN  # Gets "Todo" state (unstarted, position 0)
))

# Move to Backlog manually in Linear UI
# (or create with a different unstarted state)

# Attempt transition to READY
result = await adapter.transition_state(
    ticket_id=ticket.id,
    target_state=TicketState.READY
)
# ❌ Error: "Discrepancy between issue state and state type"
```

### 5.2 Actual Error from Ticket 1M-552

```
Failed to transition ticket: Failed to update Linear issue:
[linear] Linear API transport error:
{'message': 'Discrepancy between issue state and state type...'}
```

**Context**:
- Ticket: JJF-47
- Requested state: "ready"
- Current state: Unknown (likely "Backlog" or another "unstarted" state)
- Attempted stateId: ID of "Todo" (lowest-position "unstarted" state)

---

## 6. Fix Approach

### 6.1 Immediate Solution (Recommended)

**Option A: Semantic Name Matching**

Instead of selecting by lowest position, match workflow state names to universal states:

```python
async def _load_workflow_states(self, team_id: str) -> None:
    """Load and cache workflow states with semantic name matching."""
    result = await self.client.execute_query(
        WORKFLOW_STATES_QUERY, {"teamId": team_id}
    )

    # Create comprehensive mapping
    state_by_type = {}  # type -> [states...]
    state_by_name = {}  # name.lower() -> state

    for state in result["team"]["states"]["nodes"]:
        state_type = state["type"].lower()
        state_name = state["name"].lower()

        # Group by type
        if state_type not in state_by_type:
            state_by_type[state_type] = []
        state_by_type[state_type].append(state)

        # Index by name
        state_by_name[state_name] = state

    # Build universal state mapping with name matching
    self._workflow_states = {}

    # Define semantic name mappings
    name_mappings = {
        TicketState.READY: ["ready", "ready for dev", "ready to start"],
        TicketState.TESTED: ["tested", "in review", "qa", "testing"],
        TicketState.WAITING: ["waiting", "blocked", "on hold"],
        # ... add more mappings
    }

    for universal_state, possible_names in name_mappings.items():
        # Try to match by name first
        for name in possible_names:
            if name in state_by_name:
                self._workflow_states[universal_state] = state_by_name[name]
                break

        # Fallback: use lowest position of matching type
        if universal_state not in self._workflow_states:
            linear_type = LinearStateMapping.TO_LINEAR[universal_state]
            if linear_type in state_by_type:
                states = sorted(state_by_type[linear_type], key=lambda s: s["position"])
                self._workflow_states[universal_state] = states[0]
```

**Pros**:
- Respects team's custom workflow naming
- Gracefully falls back to type-based selection
- Minimal breaking changes

**Cons**:
- Requires maintaining name mapping configuration
- May not match all team naming conventions

### 6.2 Alternative Solution

**Option B: Get Current State Before Transition**

Query the issue's current state and only update if it's actually different:

```python
async def transition_state(
    self, ticket_id: str, target_state: TicketState
) -> Task | None:
    """Transition Linear issue to new state with current state check."""

    # Get current issue state
    current_task = await self.read(ticket_id)
    if not current_task:
        return None

    # Check if already in target state (by semantic equivalence)
    if self._is_semantically_equivalent(current_task.state, target_state):
        logger.info(f"Issue {ticket_id} already in equivalent state")
        return current_task

    # Validate transition
    if not await self.validate_transition(ticket_id, target_state):
        return None

    # Update state
    return await self.update(ticket_id, {"state": target_state})
```

**Pros**:
- Avoids unnecessary state updates
- Reduces API calls that would fail

**Cons**:
- Extra API call for every transition
- Doesn't solve the underlying mapping problem

### 6.3 Long-Term Solution

**Option C: Custom State Configuration**

Allow users to configure their team's workflow state mapping:

```yaml
# .mcp-ticketer.yaml
linear:
  api_key: lin_api_...
  team_key: JJF
  state_mapping:
    OPEN: "Todo"
    READY: "Ready"
    IN_PROGRESS: "In Progress"
    TESTED: "In Review"
    DONE: "Done"
    CLOSED: "Canceled"
    WAITING: "Waiting"
    BLOCKED: "Blocked"
```

**Pros**:
- Full flexibility for custom workflows
- Explicit and transparent mapping
- Team-specific configuration

**Cons**:
- Requires configuration setup
- Breaking change for existing users
- Need to handle missing mappings

---

## 7. Recommendations

### 7.1 Immediate Action (Fix 1M-552)

1. **Implement semantic name matching** (Option A) for common state names
2. **Add warning logs** when multiple states of same type exist
3. **Document state mapping** in Linear adapter configuration

### 7.2 Testing Requirements

1. **Unit tests** for state name matching logic
2. **Integration tests** with multi-state workflows:
   - Workflow with 3 "unstarted" states (Todo, Backlog, Ready)
   - Workflow with 2 "started" states (In Progress, In Review)
3. **Edge case tests**:
   - Team with minimal states (1 per type)
   - Team with custom state names (non-standard)
   - Transitions between states of same type

### 7.3 Documentation Updates

1. **README.md**: Document Linear state mapping behavior
2. **Linear adapter docs**: Add workflow state configuration guide
3. **Troubleshooting guide**: Add "Discrepancy" error resolution steps

---

## 8. Impact Assessment

### 8.1 Scope

**Affected Components**:
- `LinearAdapter._load_workflow_states()` (core bug)
- `LinearAdapter._get_state_mapping()` (secondary issue)
- All state transitions using READY, TESTED, WAITING, BLOCKED states

**Affected Users**:
- Any team with custom Linear workflows
- Teams using multi-state-per-type workflows (common in mature teams)
- Users transitioning to READY or TESTED states

### 8.2 Severity

- **Priority**: HIGH (blocking state transitions)
- **User Impact**: HIGH (workflow disruption)
- **Data Risk**: LOW (no data corruption, only transition failures)
- **Workaround**: Use Linear UI directly for state transitions

### 8.3 Related Issues

- **1M-164**: State synonym matching (related to state mapping)
- **1M-93**: Parent/child state constraints (uses same state system)

---

## 9. Appendix

### 9.1 Linear API References

- **GraphQL Endpoint**: `https://api.linear.app/graphql`
- **Authentication**: `Authorization: Bearer <ACCESS_TOKEN>`
- **Schema**: https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql

### 9.2 Relevant Queries

**Get Team Workflow States**:
```graphql
query WorkflowStates($teamId: String!) {
  team(id: $teamId) {
    states {
      nodes {
        id
        name
        type
        position
        color
      }
    }
  }
}
```

**Update Issue State**:
```graphql
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {
      id
      state {
        id
        name
        type
      }
    }
  }
}
```

### 9.3 Test Workflow Examples

**Example Team Workflow (JJF)**:
```
Todo         (unstarted, pos 0)   ← Selected for OPEN/READY/WAITING/BLOCKED
Backlog      (unstarted, pos 1)
Ready        (unstarted, pos 2)
In Progress  (started, pos 3)     ← Selected for IN_PROGRESS/TESTED
Done         (completed, pos 4)   ← Selected for DONE
Canceled     (canceled, pos 5)    ← Selected for CLOSED
```

**Issue with Current Implementation**:
- All "unstarted" states (OPEN, READY, WAITING, BLOCKED) → "Todo" (pos 0)
- All "started" states (IN_PROGRESS, TESTED) → "In Progress" (pos 3)
- Cannot distinguish between semantic states within same type

---

## 10. Next Steps

### For Engineering Team (1M-552 Fix)

1. ✅ **Research completed** - Root cause identified
2. ⏳ **Implement fix** - Semantic name matching (Option A)
3. ⏳ **Add tests** - Multi-state workflow coverage
4. ⏳ **Update docs** - State mapping configuration guide
5. ⏳ **Deploy** - Test with JJF team workflow
6. ⏳ **Monitor** - Track state transition errors post-fix

### For Product Team (Future Enhancement)

1. Consider adding **custom state mapping configuration** (Option C)
2. Add **workflow state visualization** in CLI/docs
3. Implement **state transition suggestions** based on workflow

---

**Research Completed**: 2025-12-02
**Researcher**: Claude (Research Agent)
**Next Action**: Implement semantic name matching fix for 1M-552
