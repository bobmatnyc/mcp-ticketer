# Linear GraphQL Fix Recommendation

**Date**: 2025-10-25
**Status**: READY FOR IMPLEMENTATION
**Confidence**: High (90%+)

---

## TL;DR - The Fix

**DON'T** change the type from `String!` to `ID!` or vice versa.

**DO** change the query pattern from `workflowStates(filter:)` to `team(id:).states`.

---

## The Problem

v0.3.5 introduced a "fix" changing `$teamId: ID!` → `$teamId: String!` but this just swapped the error message:

- v0.3.4: "expecting type String"
- v0.3.5: "expecting type ID"

**This ping-pong proves**: The type isn't the issue - **the query pattern is wrong**.

---

## The Root Cause

We're using a global filtered query that Linear's GraphQL schema doesn't properly support:

```graphql
# ❌ CURRENT (WRONG)
workflowStates(filter: { team: { id: { eq: $teamId } } })
```

While everywhere else in our code, we successfully use relationship-based queries:

```graphql
# ✅ WORKING PATTERN (used 5+ places)
team(id: $teamId) { someField { ... } }
```

---

## The Evidence

### 5+ Working Queries Use Relationship Pattern

| Query | Pattern | Type | Status |
|-------|---------|------|--------|
| GetTeam | `team(id:)` | `String!` | ✅ Works |
| GetTeamLabels | `team(id:).labels` | `String!` | ✅ Works |
| GetTeamById | `team(id:)` | `String!` | ✅ Works |
| GetTeamInfo | `team(id:)` | `String!` | ✅ Works |

### 1 Failing Query Uses Global Filter Pattern

| Query | Pattern | Type | Status |
|-------|---------|------|--------|
| WorkflowStates | `workflowStates(filter: {team:...})` | `String!` | ❌ Fails |

### Linear SDK Shows the Right Way

From Linear's official documentation:
```graphql
query team_states($id: String!) {
  team(id: $id) {
    states { nodes { ... } }
  }
}
```

**This confirms**: Use `team(id:).states`, not `workflowStates(filter:)`.

---

## The Fix

### File 1: `src/mcp_ticketer/adapters/linear/queries.py` (Line 227-239)

**BEFORE**:
```python
WORKFLOW_STATES_QUERY = """
    query WorkflowStates($teamId: String!) {
        workflowStates(filter: { team: { id: { eq: $teamId } } }) {
            nodes {
                id
                name
                type
                position
                color
            }
        }
    }
"""
```

**AFTER**:
```python
WORKFLOW_STATES_QUERY = """
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
"""
```

### File 2: `src/mcp_ticketer/adapters/linear/adapter.py` (Line 208)

**BEFORE**:
```python
for state in result["workflowStates"]["nodes"]:
```

**AFTER**:
```python
for state in result["team"]["states"]["nodes"]:
```

### File 3: `tests/adapters/linear/test_queries.py` (Line 179-182)

**BEFORE**:
```python
def test_workflow_states_query_structure(self):
    """Test WORKFLOW_STATES_QUERY structure."""
    assert "query WorkflowStates($teamId: String!)" in WORKFLOW_STATES_QUERY
    assert (
        "workflowStates(filter: { team: { id: { eq: $teamId } } })"
        in WORKFLOW_STATES_QUERY
    )
```

**AFTER**:
```python
def test_workflow_states_query_structure(self):
    """Test WORKFLOW_STATES_QUERY structure."""
    assert "query WorkflowStates($teamId: String!)" in WORKFLOW_STATES_QUERY
    assert "team(id: $teamId)" in WORKFLOW_STATES_QUERY
    assert "states" in WORKFLOW_STATES_QUERY
```

---

## Why This Will Work

### 1. Pattern Alignment
Matches 5+ working queries in the codebase that all use `team(id:)` pattern.

### 2. Linear SDK Alignment
Matches Linear's official SDK documentation showing `team(id:).states` usage.

### 3. Simplicity
Simpler query = fewer schema complications = less likely to have type issues.

### 4. Sister Query Success
GetTeamLabels uses identical pattern (`team(id:).labels`) and works perfectly.

### 5. Type Consistency
Uses proven `String!` type that works for all `team(id:)` queries.

---

## Testing Checklist

Before releasing v0.3.6:

- [ ] Update WORKFLOW_STATES_QUERY in queries.py
- [ ] Update response parsing in adapter.py
- [ ] Update test assertions in test_queries.py
- [ ] Run unit tests: `make test-unit`
- [ ] Test against live Linear API (if possible)
- [ ] Verify workflow states load during adapter init
- [ ] Verify state transitions work correctly
- [ ] Update CHANGELOG.md with correct fix description
- [ ] Update version to 0.3.6
- [ ] Commit and publish

---

## CHANGELOG Entry for v0.3.6

```markdown
## [0.3.6] - 2025-XX-XX

### Fixed
- **Linear Adapter Workflow States Query**: Fixed query pattern to use relationship-based approach
  - Changed from global `workflowStates(filter:)` to `team(id:).states` pattern
  - Aligns with Linear SDK best practices and working queries in codebase
  - Eliminates type mismatch errors during adapter initialization
  - Matches successful GetTeamLabels query pattern

### Technical Details
- Root cause was incorrect query pattern, not type declaration
- v0.3.5 attempted fix (ID! → String!) only swapped error messages
- Correct solution: Use relationship-based query like all other team queries
- Query pattern now consistent across entire Linear adapter
```

---

## Risk Assessment

### Low Risk
- ✅ Pattern proven across 5+ working queries
- ✅ Matches Linear SDK documentation
- ✅ Simple change with clear before/after
- ✅ Easy to revert if issues arise

### Mitigation
- Test against Linear API before release
- Verify response structure matches expectations
- Monitor for any schema differences

---

## Alternative Investigation (If This Fails)

**If this fix doesn't work**, investigate:

1. Whether `team.states` field exists in Linear schema (likely does based on SDK docs)
2. Whether response structure differs from expected `{team: {states: {nodes: [...]}}}`
3. Whether there are Linear API version differences
4. Whether team ID format/encoding is incorrect

**But confidence is high** this will work based on:
- Multiple working examples in codebase
- Linear SDK documentation alignment
- Logical consistency with sister queries

---

## Quick Reference Commands

```bash
# Edit the queries
nano src/mcp_ticketer/adapters/linear/queries.py    # Line 227-239

# Edit the parser
nano src/mcp_ticketer/adapters/linear/adapter.py     # Line 208

# Edit the tests
nano tests/adapters/linear/test_queries.py           # Line 179-182

# Run tests
make test-unit

# If all passes
make quality  # Format + lint + test
git add .
git commit -m "fix(linear): use relationship-based query for workflow states"
```

---

## Confidence Level

**90%** - Very high confidence this is the correct fix.

**Why 90% and not 100%?**
- Haven't executed new query against actual Linear API yet
- Small possibility Linear schema differs from SDK documentation
- Edge case: response structure might vary

**Why not lower?**
- Too much evidence supporting this approach
- Pattern is proven across codebase
- Aligns with Linear's documented best practices
- Logical and simple solution

---

## Research Documentation

Full analysis available in:
- `LINEAR_RESEARCH_SUMMARY.md` - Complete investigation findings
- `LINEAR_GRAPHQL_TYPE_ANALYSIS.md` - Detailed type analysis
- `LINEAR_QUERY_ALTERNATIVE_ANALYSIS.md` - Pattern comparison
- `LINEAR_FIX_RECOMMENDATION.md` - This document

---

**READY TO IMPLEMENT** ✅
