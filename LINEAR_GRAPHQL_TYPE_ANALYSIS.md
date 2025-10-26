# Linear GraphQL Type Analysis

## Investigation Summary

**Date**: 2025-10-25
**Issue**: Conflicting GraphQL type requirements for `$teamId` parameter
**Status**: CRITICAL FINDING - v0.3.5 "fix" was INCORRECT

---

## The Problem

### Version History

1. **v0.3.4 and earlier**: Used `ID!` for `$teamId`
   - Error: `'Variable "$teamId" of type "ID!" used in position expecting type "String".'`

2. **v0.3.5**: Changed to `String!` for `$teamId`
   - Error: `'Variable "$teamId" of type "String!" used in position expecting type "ID".'`

### This proves: The "fix" in v0.3.5 was WRONG

---

## Evidence from Codebase

### Pattern 1: `team(id: $teamId)` - Direct Team Lookup

**Uses**: `String!` type

**Found in 5 locations, all using `String!`:**

1. `client.py:221` - GetTeam query
```graphql
query GetTeam($teamId: String!) {
    team(id: $teamId) { ... }
}
```

2. `adapter.py:228` - GetTeamLabels query
```graphql
query GetTeamLabels($teamId: String!) {
    team(id: $teamId) { ... }
}
```

3. `cli/linear_commands.py:275` - GetTeamById
```graphql
query GetTeamById($id: String!) {
    team(id: $id) { ... }
}
```

4. `cli/linear_commands.py:401` - GetTeamInfo
```graphql
query GetTeamInfo($id: String!) {
    team(id: $id) { ... }
}
```

**Conclusion**: `team(id:)` operation expects `String!` parameter

---

### Pattern 2: `teams(filter:)` - Team List with Filter

**Uses**: `String!` type in filter equality

**Found in 3 locations:**

1. `adapter.py:167` - GetTeamByKey
```graphql
query GetTeamByKey($key: String!) {
    teams(filter: { key: { eq: $key } }) { ... }
}
```

2. `cli/linear_commands.py:306` - GetTeamByKey
```graphql
query GetTeamByKey($key: String!) {
    teams(filter: { key: { eq: $key } }) { ... }
}
```

3. `cli/linear_commands.py:437` - GetTeamInfoByKey
```graphql
query GetTeamInfoByKey($key: String!) {
    teams(filter: { key: { eq: $key } }) { ... }
}
```

**Conclusion**: `teams(filter: { field: { eq: $var } })` expects `String!` parameter

---

### Pattern 3: `workflowStates(filter:)` - **THE PROBLEM QUERY**

**Currently uses**: `String!` type (as of v0.3.5)

**Location**: `queries.py:227-239`

```graphql
query WorkflowStates($teamId: String!) {
    workflowStates(filter: { team: { id: { eq: $teamId } } }) {
        nodes { ... }
    }
}
```

**Analysis of the operation:**
- Uses `workflowStates(filter:)` - list operation with filter
- Filter structure: `{ team: { id: { eq: $teamId } } }`
- Nested filter on team relationship's ID field

**Question**: Does the nested filter `team: { id: { eq: ... } }` expect:
- `String!` (like other filter operations)?
- `ID!` (because it's specifically an ID field)?

---

## Working Queries Analysis

### All `team(id:)` queries work with `String!`:
- ✅ `client.get_team_info()` - Works (200 OK)
- ✅ GetTeamById in CLI - Works
- ✅ GetTeamInfo in CLI - Works
- ✅ GetTeamLabels in adapter - **CRITICAL: This is the sister query to WORKFLOW_STATES_QUERY**

### GetTeamLabels Query (WORKS):
```graphql
query GetTeamLabels($teamId: String!) {
    team(id: $teamId) {
        labels { nodes { ... } }
    }
}
```
- Uses `String!` ✅
- Direct `team(id:)` lookup ✅
- Status: **WORKING**

### WORKFLOW_STATES_QUERY (FAILS in v0.3.5):
```graphql
query WorkflowStates($teamId: String!) {
    workflowStates(filter: { team: { id: { eq: $teamId } } }) {
        nodes { ... }
    }
}
```
- Uses `String!` ✅
- Indirect lookup via filter ❌
- Status: **FAILING** with "expecting type ID" error

---

## The Critical Difference

### GetTeamLabels (Works):
- **Operation**: `team(id: $teamId)`
- **Path**: Direct lookup on Team root query field
- **Type**: `String!` ✅

### WorkflowStates (Fails):
- **Operation**: `workflowStates(filter: { team: { id: { eq: $teamId } } })`
- **Path**: Filter on relationship field, then ID comparison
- **Type**: Currently `String!` ❌ - Error says expects `ID!`

---

## Hypothesis: Filter Context Matters

**Theory**: Linear's GraphQL schema may have different type requirements based on context:

1. **Root query fields** (like `team(id:)`) expect `String!`
2. **Filter equality comparisons on ID fields** expect `ID!`

**Why this makes sense:**
- GraphQL allows different type signatures for different operations
- Filters might use stricter type checking for ID fields
- The error message explicitly says "expecting type ID" for the filter case

---

## Test Evidence Needed

To confirm hypothesis, we need to test:

1. ✅ Does `team(id: $teamId)` work with `String!`? → YES (already confirmed)
2. ❓ Does `workflowStates(filter: { team: { id: { eq: $teamId } } })` work with `ID!`?
3. ❓ Does `workflowStates(filter: { team: { id: { eq: $teamId } } })` work with `String!`?

**Current status**:
- v0.3.4: Used `ID!` → Error "expecting String"
- v0.3.5: Uses `String!` → Error "expecting ID"

**This suggests**: Neither type works universally!

---

## Possible Root Causes

### 1. Type Mismatch in Variable Declaration vs. Usage
- Variable declared as `$teamId: String!`
- Filter expects `ID!` type
- Solution: Change variable type to `ID!` for WORKFLOW_STATES_QUERY

### 2. Linear Schema Changed Between Versions
- Older schema used `String!`
- Newer schema uses `ID!`
- Solution: Use the newer type

### 3. Different Queries Need Different Types
- Direct lookups: `String!`
- Filter comparisons: `ID!`
- Solution: Use appropriate type per query

---

## Recommended Next Steps

### 1. Check Linear GraphQL Schema Documentation
- Review official Linear API documentation
- Check schema for `workflowStates` query signature
- Verify expected type for filter team ID

### 2. Test with Linear GraphQL Playground
- Execute WORKFLOW_STATES_QUERY with `ID!`
- Execute WORKFLOW_STATES_QUERY with `String!`
- Determine which type actually works

### 3. Compare with Official Linear SDK
- Check Linear's official SDK implementation
- See what type they use for workflowStates queries

### 4. Check if teamId Format Matters
- Linear team IDs might have specific format requirements
- UUID vs string representation
- Test with actual team ID value

---

## Code Locations to Fix

### Primary Issue: `queries.py:228`
```python
# Current (v0.3.5) - FAILS
WORKFLOW_STATES_QUERY = """
    query WorkflowStates($teamId: String!) {
        workflowStates(filter: { team: { id: { eq: $teamId } } }) { ... }
    }
"""

# Proposed Fix Option 1: Use ID!
WORKFLOW_STATES_QUERY = """
    query WorkflowStates($teamId: ID!) {
        workflowStates(filter: { team: { id: { eq: $teamId } } }) { ... }
    }
"""
```

### Secondary Issue: `adapter.py:228`
GetTeamLabels might need similar fix if it fails in practice.

---

## Investigation Questions

1. ❓ What is the ACTUAL Linear GraphQL schema type for:
   - `team(id:)` parameter?
   - `workflowStates(filter: { team: { id: { eq: } } })` parameter?

2. ❓ Why did v0.3.4 fail with `ID!` if that's supposedly correct?

3. ❓ Are there two different fields named `id` with different types?
   - `Team.id` field type
   - `team(id:)` parameter type
   - Filter comparison type

4. ❓ Does Linear distinguish between:
   - Query parameter types
   - Filter comparison types
   - Field types

---

## Conclusion

**CRITICAL FINDING**: The v0.3.5 "fix" that changed `ID!` → `String!` was based on incomplete analysis.

**Evidence shows**:
- ✅ Direct `team(id:)` queries work with `String!`
- ❌ Filter `workflowStates(filter: { team: { id: { eq: } } })` fails with `String!`
- ❌ Same filter failed with `ID!` in v0.3.4

**This suggests**:
1. Two different queries have two different type requirements, OR
2. The actual problem is something OTHER than just the type declaration

**NEXT ACTION**: Need to examine the ACTUAL Linear GraphQL schema specification or test directly against Linear API to determine the correct types for each specific operation.

**DO NOT APPLY BLIND FIXES** - Need concrete evidence from Linear's schema or API testing.
