# Linear Query Alternative Analysis

## CRITICAL DISCOVERY: We May Be Using the Wrong Query Entirely

### Current Approach (FAILING)
```graphql
query WorkflowStates($teamId: String!) {
    workflowStates(filter: { team: { id: { eq: $teamId } } }) {
        nodes { id name type position color }
    }
}
```

**Problem**: Type mismatch errors regardless of using `String!` or `ID!`

---

### Alternative Approach from Linear SDK

According to Linear's official documentation (from WebSearch), there's a **different pattern** for querying workflow states by team:

```graphql
query team_states(
  $id: String!
  $after: String
  $before: String
  $filter: WorkflowStateFilter
  $first: Int
  $includeArchived: Boolean
  $last: Int
  $orderBy: PaginationOrderBy
) {
  team(id: $id) {
    states(
      after: $after
      before: $before
      filter: $filter
      first: $first
      includeArchived: $includeArchived
      last: $last
      orderBy: $orderBy
    ) {
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

---

## Key Differences

### Current (Failing) Approach:
- ❌ Uses global `workflowStates` query
- ❌ Filters by team via nested filter: `filter: { team: { id: { eq: $teamId } } }`
- ❌ Type mismatch errors

### SDK Recommended Approach:
- ✅ Uses `team(id:)` query first
- ✅ Then accesses `states` field on Team object
- ✅ Uses `String!` type (confirmed working for `team(id:)` queries)
- ✅ Consistent with other working queries like GetTeamLabels

---

## Why This Makes Sense

### Pattern Analysis from Codebase

**Working Pattern** (used in 5+ places):
```graphql
query GetTeamLabels($teamId: String!) {
    team(id: $teamId) {
        labels { nodes { ... } }
    }
}
```

**Should Use Same Pattern**:
```graphql
query GetTeamWorkflowStates($teamId: String!) {
    team(id: $teamId) {
        states { nodes { ... } }
    }
}
```

---

## Evidence Supporting This Approach

1. **GetTeamLabels works** - Uses `team(id:).labels` pattern
2. **GetTeamInfo works** - Uses `team(id:)` lookup
3. **Linear SDK documentation** - Shows `team(id:).states` pattern
4. **Type consistency** - All `team(id:)` queries use `String!`

---

## Why Current Approach Might Be Problematic

### Theory: Filter Type Incompatibility

The global `workflowStates(filter:)` query might:
- Expect a different type for team ID in filter context
- Have schema changes between Linear API versions
- Not support the nested filter syntax we're using
- Be deprecated in favor of relationship-based queries

### The Linear API design philosophy seems to favor:
```
team(id:) → relationship fields (states, labels, members)
```

Rather than:
```
globalResource(filter: { team: { id: { eq: } } })
```

---

## Proposed Fix

### Replace WORKFLOW_STATES_QUERY in queries.py

**Current (Line 227-239)**:
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

**Proposed Replacement**:
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

---

## Impact Analysis

### Code Changes Required

1. **queries.py**: Update WORKFLOW_STATES_QUERY (shown above)

2. **adapter.py**: Update response parsing
   - Current: `result["workflowStates"]["nodes"]`
   - New: `result["team"]["states"]["nodes"]`

### Search for Usage

```bash
grep -r "workflowStates" src/mcp_ticketer/adapters/linear/
```

Expected locations:
- `queries.py` - Query definition
- `adapter.py` - Query usage and parsing
- Any other files that reference workflow states

---

## Testing Strategy

### 1. Verify Query Structure
- Ensure team.states field exists in Linear schema
- Confirm it returns WorkflowState nodes

### 2. Test with Actual Linear API
- Execute new query structure
- Verify 200 OK response
- Confirm data structure matches expectations

### 3. Integration Testing
- Run adapter initialization
- Verify workflow states load correctly
- Check state transitions work

---

## Additional Benefits

### Consistency
- Aligns with GetTeamLabels pattern
- Uses proven `team(id:)` approach
- Reduces query complexity

### Maintainability
- Easier to understand
- Follows Linear's recommended patterns
- Less likely to break with API changes

### Performance
- Potentially more efficient
- Direct relationship traversal vs global filter
- May have better caching characteristics

---

## Confidence Level

**HIGH** - This approach is likely correct because:

1. ✅ Matches Linear SDK documentation
2. ✅ Consistent with working queries in codebase
3. ✅ Uses proven `String!` type for team(id:)
4. ✅ Follows relationship-based query pattern
5. ✅ Aligns with GetTeamLabels (working sister query)

---

## Next Steps

1. **Update WORKFLOW_STATES_QUERY** to use `team(id:).states` pattern
2. **Update adapter.py** to parse new response structure
3. **Test against Linear API** to verify it works
4. **Update version** to 0.3.6 with correct fix
5. **Document** the correct pattern for future reference

---

## Lessons Learned

### Don't Assume Filter Syntax Works Universally

Just because you can write:
```graphql
globalResource(filter: { relationship: { field: { eq: $value } } })
```

Doesn't mean the GraphQL schema supports it. Always check:
- Schema documentation
- Official SDK usage
- Working examples in codebase

### Follow Established Patterns

When multiple queries use pattern A successfully, and one query using pattern B fails, **switch to pattern A**.

We had 5+ working examples of `team(id:).field` but tried to force `workflowStates(filter:)` to work.

---

## Conclusion

**ROOT CAUSE**: Using the wrong query pattern entirely
**FIX**: Switch from global filtered query to relationship-based query
**CONFIDENCE**: High - matches Linear SDK and working codebase patterns
**NEXT**: Implement and test the proposed fix
