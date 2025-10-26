# Linear GraphQL Query Pattern Comparison

**Visual Guide**: Side-by-side comparison of query patterns

---

## Pattern 1: Relationship-Based (✅ WORKING)

### Used By: GetTeamLabels

```graphql
query GetTeamLabels($teamId: String!) {
    team(id: $teamId) {
        labels {
            nodes {
                id
                name
                color
                description
            }
        }
    }
}
```

**Characteristics**:
- ✅ Direct relationship traversal
- ✅ Simple query structure
- ✅ Uses `String!` type
- ✅ Returns: `{team: {labels: {nodes: [...]}}}`
- ✅ Status: **200 OK**

**Usage**: `adapter.py:220-248`
```python
async def _load_team_labels(self, team_id: str) -> None:
    query = """query GetTeamLabels($teamId: String!) { ... }"""
    result = await self.client.execute_query(query, {"teamId": team_id})
    self._labels_cache = result["team"]["labels"]["nodes"]
```

---

## Pattern 2: Global Filter-Based (❌ FAILING)

### Used By: WorkflowStates (CURRENT)

```graphql
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
```

**Characteristics**:
- ❌ Global query with nested filter
- ❌ Complex filter syntax
- ❌ Type confusion (fails with both `String!` and `ID!`)
- ❌ Returns: Would be `{workflowStates: {nodes: [...]}}`
- ❌ Status: **400 Bad Request**

**Usage**: `adapter.py:195-218`
```python
async def _load_workflow_states(self, team_id: str) -> None:
    result = await self.client.execute_query(
        WORKFLOW_STATES_QUERY, {"teamId": team_id}
    )
    workflow_states = {}
    for state in result["workflowStates"]["nodes"]:  # ❌ Fails here
        # ...
```

---

## Pattern 3: Relationship-Based (✅ PROPOSED FIX)

### Proposed For: WorkflowStates (NEW)

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

**Characteristics**:
- ✅ Direct relationship traversal (same as GetTeamLabels)
- ✅ Simple query structure
- ✅ Uses `String!` type (proven to work)
- ✅ Returns: `{team: {states: {nodes: [...]}}}`
- ✅ Expected Status: **200 OK**

**Usage**: `adapter.py:195-218` (updated)
```python
async def _load_workflow_states(self, team_id: str) -> None:
    result = await self.client.execute_query(
        WORKFLOW_STATES_QUERY, {"teamId": team_id}
    )
    workflow_states = {}
    for state in result["team"]["states"]["nodes"]:  # ✅ Should work
        # ...
```

---

## Side-by-Side: Labels vs States

### GetTeamLabels (✅ Works)
```
team(id: $teamId)
  └── labels
       └── nodes[]
            ├── id
            ├── name
            ├── color
            └── description
```

### WorkflowStates (❌ Current - Fails)
```
workflowStates(filter: {team: {id: {eq: $teamId}}})
  └── nodes[]
       ├── id
       ├── name
       ├── type
       ├── position
       └── color
```

### WorkflowStates (✅ Proposed - Should Work)
```
team(id: $teamId)
  └── states
       └── nodes[]
            ├── id
            ├── name
            ├── type
            ├── position
            └── color
```

**Observation**: Proposed pattern is **structurally identical** to working GetTeamLabels pattern.

---

## Query Pattern Decision Tree

```
Need team-specific resource?
│
├─ YES → Use team(id:).field pattern
│   │
│   ├─ Need labels? → team(id:).labels
│   ├─ Need states? → team(id:).states
│   ├─ Need members? → team(id:).members
│   └─ Need projects? → team(id:).projects
│
└─ NO → Use direct resource query
    │
    ├─ Single resource by ID? → resource(id: $id)
    ├─ Filter by non-team field? → resources(filter: {field: {eq: $value}})
    └─ List all? → resources(first: $limit)
```

**For workflow states**: Answer is **YES** (team-specific) → Use `team(id:).states`

---

## Type Usage Patterns

### Pattern: team(id:) - Direct Lookup

```graphql
query($teamId: String!)  ← Use String!
team(id: $teamId)        ← Accepts String!
```

**Evidence**: 5+ working queries all use `String!`

### Pattern: teams(filter:) - List with Filter

```graphql
query($key: String!)                     ← Use String!
teams(filter: {key: {eq: $key}})        ← Accepts String!
```

**Evidence**: 3 working queries use `String!`

### Pattern: workflowStates(filter:) - Global Filter

```graphql
query($teamId: ???)  ← Unknown what type works!
workflowStates(filter: {team: {id: {eq: $teamId}}})  ← Type confusion
```

**Evidence**:
- Fails with `String!` (v0.3.5)
- Fails with `ID!` (v0.3.4)
- **Solution**: Don't use this pattern!

---

## All Working Team Queries (Reference)

### 1. GetTeam (client.py:221)
```graphql
query GetTeam($teamId: String!) {
    team(id: $teamId) { id name key description }
}
```
✅ Works

### 2. GetTeamLabels (adapter.py:228)
```graphql
query GetTeamLabels($teamId: String!) {
    team(id: $teamId) {
        labels { nodes { id name color description } }
    }
}
```
✅ Works

### 3. GetTeamById (cli/linear_commands.py:275)
```graphql
query GetTeamById($id: String!) {
    team(id: $id) { id key name organization { ... } }
}
```
✅ Works

### 4. GetTeamInfo (cli/linear_commands.py:401)
```graphql
query GetTeamInfo($id: String!) {
    team(id: $id) { id key name description ... }
}
```
✅ Works

### 5. GetTeamByKey (adapter.py:167)
```graphql
query GetTeamByKey($key: String!) {
    teams(filter: {key: {eq: $key}}) { nodes { id name key } }
}
```
✅ Works

---

## Pattern Recommendation Matrix

| Resource Type | Recommended Pattern | Type | Example |
|---------------|-------------------|------|---------|
| Team info | `team(id:)` | `String!` | `team(id: $id) { name }` |
| Team labels | `team(id:).labels` | `String!` | `team(id: $id) { labels { nodes {...} } }` |
| Team states | `team(id:).states` | `String!` | `team(id: $id) { states { nodes {...} } }` |
| Team members | `team(id:).members` | `String!` | `team(id: $id) { members { nodes {...} } }` |
| Teams by key | `teams(filter:)` | `String!` | `teams(filter: {key: {eq: $key}})` |

**❌ AVOID**: `globalResource(filter: {team: {id: {eq: $id}}})`

---

## Linear SDK Confirmation

From Linear's official SDK (via WebSearch results):

```graphql
query team_states(
  $id: String!
  $filter: WorkflowStateFilter
  $first: Int
  # ... other pagination params
) {
  team(id: $id) {
    states(
      filter: $filter
      first: $first
      # ... other pagination args
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

**Confirms**:
- ✅ Use `team(id:).states` pattern
- ✅ Use `String!` for team ID
- ✅ Can add additional filters via `WorkflowStateFilter` if needed
- ✅ Supports pagination

---

## Migration Guide

### Step 1: Update Query Definition

**File**: `src/mcp_ticketer/adapters/linear/queries.py`

```diff
  WORKFLOW_STATES_QUERY = """
      query WorkflowStates($teamId: String!) {
-         workflowStates(filter: { team: { id: { eq: $teamId } } }) {
+         team(id: $teamId) {
+             states {
-             nodes {
+                 nodes {
-                 id
-                 name
-                 type
-                 position
-                 color
+                     id
+                     name
+                     type
+                     position
+                     color
+                 }
-             }
+             }
          }
      }
  """
```

### Step 2: Update Response Parser

**File**: `src/mcp_ticketer/adapters/linear/adapter.py`

```diff
  async def _load_workflow_states(self, team_id: str) -> None:
      try:
          result = await self.client.execute_query(
              WORKFLOW_STATES_QUERY, {"teamId": team_id}
          )

          workflow_states = {}
-         for state in result["workflowStates"]["nodes"]:
+         for state in result["team"]["states"]["nodes"]:
              state_type = state["type"].lower()
              if state_type not in workflow_states:
                  workflow_states[state_type] = state
```

### Step 3: Update Tests

**File**: `tests/adapters/linear/test_queries.py`

```diff
  def test_workflow_states_query_structure(self):
      """Test WORKFLOW_STATES_QUERY structure."""
      assert "query WorkflowStates($teamId: String!)" in WORKFLOW_STATES_QUERY
-     assert (
-         "workflowStates(filter: { team: { id: { eq: $teamId } } })"
-         in WORKFLOW_STATES_QUERY
-     )
+     assert "team(id: $teamId)" in WORKFLOW_STATES_QUERY
+     assert "states" in WORKFLOW_STATES_QUERY
      assert "nodes" in WORKFLOW_STATES_QUERY
```

---

## Verification Checklist

After implementing the fix:

- [ ] Query structure matches GetTeamLabels pattern
- [ ] Response parsing path is `result["team"]["states"]["nodes"]`
- [ ] Type is `String!` for `$teamId` parameter
- [ ] Unit tests pass
- [ ] Integration tests pass (if available)
- [ ] Manual test against Linear API succeeds
- [ ] Workflow states load correctly during adapter init
- [ ] State transitions work correctly

---

## Expected Outcome

### Before Fix (v0.3.5)
```
→ Execute WORKFLOW_STATES_QUERY
← 400 Bad Request
  Error: Variable "$teamId" of type "String!" used in position expecting type "ID".
```

### After Fix (v0.3.6)
```
→ Execute WORKFLOW_STATES_QUERY (new pattern)
← 200 OK
  {
    "team": {
      "states": {
        "nodes": [
          {"id": "...", "name": "Todo", "type": "unstarted", ...},
          {"id": "...", "name": "In Progress", "type": "started", ...},
          ...
        ]
      }
    }
  }
```

---

## Conclusion

**Use relationship-based queries for team resources:**
- ✅ `team(id:).states` not `workflowStates(filter:)`
- ✅ `team(id:).labels` not `issueLabels(filter:)`
- ✅ `team(id:).members` not `users(filter:)`

**This pattern**:
- Works consistently across codebase
- Aligns with Linear SDK best practices
- Avoids GraphQL type complications
- Maintains query simplicity

**IMPLEMENT THIS FIX** → v0.3.6
