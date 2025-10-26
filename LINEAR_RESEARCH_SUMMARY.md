# Linear GraphQL Type Investigation - Research Summary

**Investigation Date**: 2025-10-25
**Researcher**: Claude (Research Agent)
**Issue**: Linear adapter GraphQL type errors in v0.3.5

---

## Executive Summary

**CRITICAL FINDING**: The v0.3.5 "fix" was incorrect. However, the root cause is **not a simple type mismatch** - we're likely using the **wrong GraphQL query pattern entirely**.

**Recommended Solution**: Switch from global `workflowStates(filter:)` query to relationship-based `team(id:).states` query to match Linear SDK patterns and working codebase examples.

---

## Investigation Background

### Problem Statement

User reported that v0.3.5 now shows OPPOSITE error from v0.3.4:

- **v0.3.4**: Used `$teamId: ID!` → Error: "expecting type String"
- **v0.3.5**: Uses `$teamId: String!` → Error: "expecting type ID"

This ping-pong behavior indicates the "fix" in v0.3.5 was based on incomplete analysis.

---

## Research Methodology

### 1. Codebase Pattern Analysis

**Tools Used**: Grep, Read, pattern matching

**Searched For**:
- All GraphQL queries using `team` parameter
- All queries using `workflowStates`
- All queries using `team(id:)` pattern
- All queries using filter syntax

**Files Analyzed**:
- `src/mcp_ticketer/adapters/linear/queries.py` (query definitions)
- `src/mcp_ticketer/adapters/linear/client.py` (GraphQL client)
- `src/mcp_ticketer/adapters/linear/adapter.py` (query usage)
- `src/mcp_ticketer/cli/linear_commands.py` (CLI queries)
- `tests/adapters/linear/test_queries.py` (test validations)

### 2. Linear API Documentation Research

**Sources Checked**:
- Linear Developers documentation (linear.app/developers)
- Linear GraphQL API filtering guide
- Linear SDK GitHub repository
- Apollo Studio schema reference

**Key Finding**: WebSearch revealed Linear SDK uses `team(id:).states` pattern, NOT `workflowStates(filter:)`.

### 3. Working vs Failing Query Comparison

Systematically compared:
- Queries that work (200 OK)
- Queries that fail (400 Bad Request)
- Type declarations for each
- Query patterns used

---

## Key Findings

### Finding 1: Pattern Consistency in Working Queries

**ALL working team-related queries use the same pattern:**

```graphql
query QueryName($teamId: String!) {
    team(id: $teamId) {
        someField { ... }
    }
}
```

**Evidence (5+ working queries)**:

1. `client.py:221` - GetTeam
2. `adapter.py:228` - GetTeamLabels
3. `cli/linear_commands.py:275` - GetTeamById
4. `cli/linear_commands.py:401` - GetTeamInfo
5. `cli/linear_commands.py:437` - GetTeamInfoByKey (via teams filter)

**Common characteristics**:
- ✅ All use `String!` type for team ID
- ✅ All use direct `team(id:)` lookup OR `teams(filter:)`
- ✅ All successfully return 200 OK
- ✅ All work in production

### Finding 2: The Failing Query Uses Different Pattern

**WORKFLOW_STATES_QUERY (queries.py:227-239)**:

```graphql
query WorkflowStates($teamId: String!) {
    workflowStates(filter: { team: { id: { eq: $teamId } } }) {
        nodes { ... }
    }
}
```

**Unique characteristics**:
- ❌ Uses global `workflowStates` query (not team-based)
- ❌ Uses nested filter syntax: `filter: { team: { id: { eq: } } }`
- ❌ Fails with type errors regardless of `String!` or `ID!`
- ❌ No other query in codebase uses this pattern

### Finding 3: Sister Query Comparison

**GetTeamLabels (WORKS)** vs **WorkflowStates (FAILS)** - Both fetch team sub-resources:

| Aspect | GetTeamLabels (✅ Works) | WorkflowStates (❌ Fails) |
|--------|-------------------------|---------------------------|
| Pattern | `team(id:).labels` | `workflowStates(filter: { team: ... })` |
| Type | `String!` | `String!` (v0.3.5) |
| Query Style | Relationship-based | Global + filter |
| Status | 200 OK | 400 Bad Request |
| Usage | Production-ready | Failing |

**Conclusion**: Both queries have identical goals (fetch team sub-resources), but different approaches. The working one uses relationship traversal.

### Finding 4: Linear SDK Pattern

**From WebSearch results**, Linear's official SDK documentation shows:

```graphql
query team_states($id: String!) {
  team(id: $id) {
    states {
      nodes { id name type position color }
    }
  }
}
```

**This matches**:
- ✅ The working GetTeamLabels pattern
- ✅ Uses `String!` type
- ✅ Relationship-based query
- ✅ Simple, direct traversal

**This contradicts**:
- ❌ Our current `workflowStates(filter:)` approach
- ❌ Nested filter syntax
- ❌ Global query + filter pattern

---

## Root Cause Analysis

### The Real Problem

**It's not a type mismatch - it's the wrong query structure.**

**Evidence**:
1. Changing `ID!` ↔ `String!` just swaps error messages
2. No combination of types makes the filter-based query work
3. Linear SDK shows different approach
4. All working queries use relationship pattern

### Why Filter Approach Fails

**Possible reasons**:

1. **Schema Design**: Linear's GraphQL schema may not support nested team ID filters in the way we're using them

2. **Type Context Sensitivity**: Filter equality comparisons on relationship IDs might require different types than direct lookups

3. **API Evolution**: The `workflowStates(filter:)` approach may be deprecated or never fully supported

4. **Complexity**: Nested filter syntax `{ team: { id: { eq: } } }` might have type resolution issues in Linear's schema

---

## Recommended Solution

### Replace Query Pattern

**Current (queries.py:227-239)**:
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

**Recommended**:
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

### Update Response Parsing

**Current (adapter.py:208)**:
```python
for state in result["workflowStates"]["nodes"]:
```

**Recommended**:
```python
for state in result["team"]["states"]["nodes"]:
```

---

## Implementation Details

### Files to Modify

1. **src/mcp_ticketer/adapters/linear/queries.py**
   - Line 227-239: Update WORKFLOW_STATES_QUERY

2. **src/mcp_ticketer/adapters/linear/adapter.py**
   - Line 208: Update response parsing path

### Testing Requirements

1. **Unit Tests**: Update test expectations in `tests/adapters/linear/test_queries.py`
   - Line 179: Update query structure assertion
   - Line 181-182: Update filter assertion (or remove)

2. **Integration Tests**: Verify against actual Linear API
   - Test workflow state loading
   - Test state transitions
   - Test adapter initialization

3. **Regression Tests**: Ensure no breaking changes
   - GetTeamLabels still works
   - Other team queries unaffected
   - State mapping logic unchanged

---

## Confidence Assessment

### High Confidence (90%+)

**Reasons**:

1. ✅ **Pattern Match**: Aligns with 5+ working queries in codebase
2. ✅ **SDK Alignment**: Matches Linear's official SDK pattern
3. ✅ **Simplicity**: Simpler query structure, easier to maintain
4. ✅ **Sister Query**: Identical to working GetTeamLabels pattern
5. ✅ **Type Consistency**: Uses proven `String!` type for `team(id:)`

**Risk Factors**:

1. ⚠️ **Untested**: Haven't executed new query against Linear API yet
2. ⚠️ **Schema Assumption**: Assuming `team.states` field exists
3. ⚠️ **Response Structure**: Need to verify nodes structure matches

---

## Next Steps for Implementation

### 1. Pre-Implementation Verification (Optional but Recommended)

Test new query structure against Linear GraphQL playground:
```graphql
query {
  team(id: "ACTUAL_TEAM_ID") {
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

### 2. Code Changes

1. Update `WORKFLOW_STATES_QUERY` in queries.py
2. Update response parsing in adapter.py
3. Update test assertions if needed

### 3. Testing

1. Run unit tests: `make test-unit`
2. Run Linear adapter tests specifically
3. Test against live Linear API
4. Verify state loading works
5. Test state transitions

### 4. Version & Release

1. Update version to 0.3.6
2. Update CHANGELOG.md with correct fix
3. Document the pattern change
4. Publish corrected version

---

## Supporting Documentation

### Additional Analysis Files

1. **LINEAR_GRAPHQL_TYPE_ANALYSIS.md**: Detailed type investigation
2. **LINEAR_QUERY_ALTERNATIVE_ANALYSIS.md**: Query pattern comparison
3. This summary: **LINEAR_RESEARCH_SUMMARY.md**

### Code References

**Working Patterns**:
- `client.py:209-235` - get_team_info() using team(id:)
- `adapter.py:220-248` - _load_team_labels() using team(id:).labels

**Failing Pattern**:
- `queries.py:227-239` - WORKFLOW_STATES_QUERY using workflowStates(filter:)
- `adapter.py:195-218` - _load_workflow_states() parsing

**Test Coverage**:
- `tests/adapters/linear/test_queries.py:177-188` - Tests for WORKFLOW_STATES_QUERY

---

## Memory Updates

### Lessons Learned for Future Reference

1. **Pattern Over Type**: When debugging GraphQL queries, check query pattern BEFORE focusing on types

2. **Follow Working Examples**: If 5+ queries use pattern A successfully, and 1 query using pattern B fails, switch to pattern A

3. **Don't Ping-Pong**: If changing a type just swaps error messages, the type isn't the real problem

4. **Check Official SDKs**: Official SDK patterns are usually the most reliable guide

5. **Sister Queries**: When two queries have similar goals (like fetching team sub-resources), they should use similar patterns

### Linear GraphQL Best Practices

1. **Team-Related Queries**: Use `team(id:).field` pattern, not global queries with team filters
2. **Team ID Type**: Use `String!` for `team(id:)` parameter
3. **Relationship Traversal**: Prefer direct field access over complex filters
4. **Query Simplicity**: Simpler queries = fewer schema issues

---

## Conclusion

**ROOT CAUSE**: Wrong GraphQL query pattern - using global filtered query instead of relationship-based query

**SOLUTION**: Switch to `team(id:).states` pattern matching Linear SDK and working codebase examples

**CONFIDENCE**: High (90%+) - Strong evidence from multiple sources

**IMPACT**: Low-risk change with high likelihood of fixing the issue

**NEXT ACTION**: Implement query pattern change and test against Linear API

---

## Appendix: Query Pattern Reference

### ✅ RECOMMENDED Pattern (Relationship-Based)

```graphql
# Pattern: team(id:) → field → nodes
query GetTeamResource($teamId: String!) {
    team(id: $teamId) {
        resourceField {
            nodes { ... }
        }
    }
}
```

**Examples**:
- `team(id:).labels.nodes` - Get team labels
- `team(id:).states.nodes` - Get workflow states
- `team(id:).members.nodes` - Get team members

### ❌ AVOID Pattern (Global Filter-Based)

```graphql
# Pattern: globalResource(filter:) with nested team ID
query GetFilteredResource($teamId: String!) {
    globalResources(filter: { team: { id: { eq: $teamId } } }) {
        nodes { ... }
    }
}
```

**Problems**:
- Type mismatches
- Schema complexity
- Potential deprecation
- Not found in Linear SDK
