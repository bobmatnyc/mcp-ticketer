# Project Filtering Gap Analysis

**Research Date**: 2025-11-29
**Researcher**: Research Agent (Claude Sonnet 4.5)
**Issue**: User reports tickets from other projects appearing in searches
**Requirement**: ALL search/list operations MUST require project|epic ID parameter (foundational enforcement)

---

## Executive Summary

### Critical Finding
**Project filtering is NOT enforced at the foundational level in search/list operations.** While the `SearchQuery` model includes an optional `project` field, **NO MCP tools currently require or default project filtering**, allowing searches to span ALL projects across the entire workspace.

### Impact
- Users see irrelevant tickets from other projects in search results
- No scoping boundary enforced at the API/MCP tool level
- Default behavior returns tickets from ALL projects (Linear teams, GitHub repos, JIRA projects)

### Root Cause
1. **SearchQuery.project field is optional** (line 530: `project: str | None = Field(None, ...)`)
2. **MCP tools don't pass project parameter to SearchQuery** (ticket_search, ticket_list)
3. **Adapters only filter by project IF provided** (not by default)
4. **No enforcement mechanism** at core level to require project context

---

## Analysis Findings

### 1. MCP Tools Performing Search/List Operations

#### 1.1 Core Search/List Tools (NO PROJECT FILTERING)

| Tool | File | Project Filter? | Required? | Behavior |
|------|------|----------------|-----------|----------|
| `ticket_search()` | `search_tools.py:15` | ❌ No | ❌ Optional | Searches ALL projects |
| `ticket_list()` | `ticket_tools.py:614` | ❌ No | ❌ Optional | Lists ALL projects |
| `epic_list()` | `hierarchy_tools.py:138` | ❌ No | ❌ Optional | Lists ALL epics |
| `ticket_search_hierarchy()` | `search_tools.py:105` | ❌ No | ❌ Optional | Searches ALL projects |

**Key Evidence**:
```python
# ticket_search() - NO project parameter
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    # Creates SearchQuery without project
    search_query = SearchQuery(
        query=query,
        state=state_enum,
        priority=priority_enum,
        tags=tags,
        assignee=assignee,
        limit=min(limit, 100),
    )
```

**Warning in Code** (line 44-49):
```python
# Add warning for unscoped searches
if not query and not (state or priority or tags or assignee):
    logging.warning(
        "Unscoped search with no query or filters. "
        "This will search ALL tickets across all projects. "
        "Tip: Configure default_project or default_team for automatic scoping."
    )
```

This warning **proves the system knows searches are cross-project** but only warns—doesn't enforce.

#### 1.2 Single Issue Lookup (Correctly Excludes Project Requirement)

| Tool | File | Project Filter? | Reason |
|------|------|----------------|--------|
| `ticket_read()` | `ticket_tools.py:46` | ✅ N/A (by design) | Issue ID is globally unique |
| `ticket_summary()` | `ticket_tools.py:716` | ✅ N/A (by design) | Issue ID is globally unique |
| `ticket_latest()` | `ticket_tools.py:788` | ✅ N/A (by design) | Issue ID is globally unique |

These tools correctly don't require project filtering because they operate on unique issue IDs.

---

### 2. SearchQuery Model Analysis

**Location**: `src/mcp_ticketer/core/models.py:522-532`

```python
class SearchQuery(BaseModel):
    """Search query parameters."""

    query: str | None = Field(None, description="Text search query")
    state: TicketState | None = Field(None, description="Filter by state")
    priority: Priority | None = Field(None, description="Filter by priority")
    tags: list[str] | None = Field(None, description="Filter by tags")
    assignee: str | None = Field(None, description="Filter by assignee")
    project: str | None = Field(None, description="Filter by project/epic ID or name")  # ❌ OPTIONAL
    limit: int = Field(10, gt=0, le=100, description="Maximum results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
```

**Gap**: `project` field is **optional** (default: `None`), allowing searches without project scoping.

---

### 3. Adapter Implementation Analysis

#### 3.1 Linear Adapter

**Location**: `src/mcp_ticketer/adapters/linear/adapter.py:1808-1885`

**List Method** (line 1740):
```python
async def list(
    self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
) -> builtins.list[Task]:
    # Always filters by team_id
    team_id = await self._ensure_team_id()
    issue_filter = build_issue_filter(
        team_id=team_id,  # ✅ Team scoping enforced
        state=filters.get("state") if filters else None,
        priority=filters.get("priority") if filters else None,
    )
```

**Search Method** (line 1808):
```python
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    team_id = await self._ensure_team_id()
    issue_filter = {"team": {"id": {"eq": team_id}}}  # ✅ Team scoping enforced

    # Project filter (Bug fix: Add support for filtering by project/epic)
    if query.project:  # ⚠️ Only filters IF provided
        project_id = await self._resolve_project_id(query.project)
        if project_id:
            issue_filter["project"] = {"id": {"eq": project_id}}
```

**Linear Behavior**:
- ✅ **Team-level scoping IS enforced** (searches within configured team)
- ⚠️ **Project-level scoping is optional** (only if `query.project` provided)
- **Impact**: User sees ALL tickets in their Linear team, not just their project

#### 3.2 GitHub Adapter

**Location**: `src/mcp_ticketer/adapters/github.py:796-915`

**List Method** (line 796):
```python
async def list(
    self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
) -> list[Task]:
    # Scoped to configured repo ONLY
    response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/issues", params=params
    )
```

**Search Method** (line 861):
```python
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    # Build GitHub search query
    search_parts = [f"repo:{self.owner}/{self.repo}", "is:issue"]  # ✅ Repo scoping enforced
```

**GitHub Behavior**:
- ✅ **Repo-level scoping IS enforced** (adapter configured for single repo)
- ✅ **Cannot search across multiple repos** (adapter limitation)
- **Impact**: No cross-project issue IF each project has separate adapter config

#### 3.3 JIRA Adapter

**Location**: `src/mcp_ticketer/adapters/jira.py:669-758`

**List Method** (line 669):
```python
async def list(
    self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
) -> list[Epic | Task]:
    jql_parts = []

    if self.project_key:  # ⚠️ Only filters IF configured
        jql_parts.append(f"project = {self.project_key}")
```

**Search Method** (line 710):
```python
async def search(self, query: SearchQuery) -> builtins.list[Epic | Task]:
    jql_parts = []

    if self.project_key:  # ⚠️ Only filters IF configured
        jql_parts.append(f"project = {self.project_key}")
```

**JIRA Behavior**:
- ⚠️ **Project scoping is optional** (only if `self.project_key` configured)
- ❌ **No enforcement if project_key not set** (searches ALL accessible projects)
- **Impact**: User with multi-project access sees tickets from ALL projects

#### 3.4 AiTrackDown Adapter (File-Based)

**Location**: `src/mcp_ticketer/adapters/aitrackdown.py:439-518`

**List Method** (line 439):
```python
async def list(
    self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
) -> list[Task]:
    # Reads ALL ticket files from tickets_dir
    ticket_files = sorted(self.tickets_dir.glob("*.json"))
```

**Search Method** (line 485):
```python
async def search(self, query: SearchQuery) -> builtins.list[Task]:
    # Filters after loading ALL tasks
    all_tasks = await self.list(limit=100, filters=filters)
```

**AiTrackDown Behavior**:
- ❌ **No project filtering** (file-based, no project concept)
- **Impact**: Returns all tickets in local directory

---

### 4. Configuration Analysis

#### 4.1 Project-Level Defaults

**Location**: `src/mcp_ticketer/core/project_config.py:169-192`

```python
@dataclass
class TicketerConfig:
    default_adapter: str = "aitrackdown"
    default_user: str | None = None
    default_project: str | None = None  # ⚠️ Optional, not enforced
    default_epic: str | None = None     # ⚠️ Alias for default_project
    default_team: str | None = None
    default_tags: list[str] | None = None
```

**Gap**: `default_project` is optional and **NOT automatically applied** in search/list operations.

#### 4.2 Usage in ticket_create (Contrast)

**Location**: `src/mcp_ticketer/mcp/server/tools/ticket_tools.py:206-224`

```python
# Apply configuration defaults if values not provided
config = resolver.load_project_config() or TicketerConfig()

# Priority 2: Use configured default
if config.default_project or config.default_epic:
    final_parent_epic = config.default_project or config.default_epic
    logging.debug(f"Using default epic from config: {final_parent_epic}")
```

**Key Observation**: `ticket_create()` DOES apply `default_project` from config, but **search/list tools DO NOT**.

---

## Gap Summary

### Current Behavior (Problematic)

```python
# User searches without project context
ticket_search(query="bug", priority="high")
# ❌ Returns tickets from ALL projects in workspace

ticket_list(state="open", limit=50)
# ❌ Returns tickets from ALL projects in workspace

epic_list(limit=10)
# ❌ Returns ALL epics/projects (no filtering)
```

### Desired Behavior (Required)

```python
# User MUST provide project context
ticket_search(query="bug", priority="high", project_id="PROJ-123")
# ✅ Returns only tickets from PROJ-123

ticket_list(state="open", limit=50, project_id="PROJ-123")
# ✅ Returns only tickets from PROJ-123

# OR: Use configured default
config_set_default_project(project_id="PROJ-123")
ticket_search(query="bug")
# ✅ Uses default_project from config automatically
```

---

## Recommendations for Engineer

### Option 1: Make project_id Required (Strictest)

**Pros**:
- Explicit, no ambiguity
- Prevents accidental cross-project searches
- Forces users to be intentional

**Cons**:
- Breaking change for existing users
- Requires migration of all tool calls

**Implementation**:
1. Add `project_id: str` parameter to all search/list tools
2. Make it required (no default value)
3. Remove `None` from `SearchQuery.project` field
4. Update documentation

**Code Locations**:
- `src/mcp_ticketer/mcp/server/tools/search_tools.py:15` - `ticket_search()`
- `src/mcp_ticketer/mcp/server/tools/ticket_tools.py:614` - `ticket_list()`
- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py:138` - `epic_list()`
- `src/mcp_ticketer/core/models.py:530` - `SearchQuery.project` field

### Option 2: Require project_id OR default_project (Recommended)

**Pros**:
- Explicit when needed, convenient when configured
- Backward compatible with configuration
- Allows per-call override

**Cons**:
- Requires validation logic in each tool
- Users must configure default_project or pass explicitly

**Implementation**:
1. Add `project_id: str | None = None` parameter to all search/list tools
2. In each tool, check:
   ```python
   config = resolver.load_project_config()
   final_project = project_id or config.default_project

   if not final_project:
       return {
           "status": "error",
           "error": "project_id is required. Provide project_id parameter or set default_project via config_set_default_project()"
       }
   ```
3. Pass `final_project` to `SearchQuery(project=final_project)`

**Code Locations** (same as Option 1, plus):
- Add validation logic in each tool function
- Update `SearchQuery` instantiation to always pass `project` parameter

### Option 3: Make default_project Mandatory in Configuration (Hybrid)

**Pros**:
- Configuration-driven (set once, use everywhere)
- No breaking changes to tool signatures
- Aligns with existing `ticket_create()` behavior

**Cons**:
- Requires configuration step (may be forgotten)
- Less flexible for multi-project workflows
- Requires adapter support for applying defaults

**Implementation**:
1. In search/list tools, load config and apply `default_project`:
   ```python
   config = resolver.load_project_config()
   if not config.default_project:
       return {
           "status": "error",
           "error": "No default_project configured. Use config_set_default_project() first."
       }

   search_query = SearchQuery(
       project=config.default_project,  # Apply default
       ...
   )
   ```
2. Allow explicit `project_id` parameter to override default

**Code Locations**:
- Modify all search/list tool functions to load and apply config defaults

---

## Adapter-Specific Considerations

### Linear
- Already enforces **team-level** scoping (✅ good)
- Needs **project-level** scoping within team
- Code location: `src/mcp_ticketer/adapters/linear/adapter.py:1859-1864`

### GitHub
- Already enforces **repo-level** scoping (✅ good)
- No cross-repo search capability
- Consider: Is repo == project? (probably yes for GitHub)

### JIRA
- **Critical**: Optional `project_key` allows cross-project searches
- Must enforce `project_key` requirement in configuration
- Code location: `src/mcp_ticketer/adapters/jira.py:675-677`

### AiTrackDown
- File-based, no project concept
- May need to add project metadata to ticket files
- Code location: `src/mcp_ticketer/adapters/aitrackdown.py:439-518`

---

## Implementation Roadmap

### Phase 1: Enforce at MCP Tool Level (Immediate)
1. Add `project_id` parameter to search/list tools
2. Validate `project_id or config.default_project` is present
3. Return error if neither provided
4. Pass to `SearchQuery(project=final_project)`

### Phase 2: Ensure Adapter Compliance (Critical)
1. **Linear**: Verify project filtering works in search (line 1859-1864)
2. **JIRA**: Make `project_key` required in adapter config
3. **GitHub**: Document repo == project assumption
4. **AiTrackDown**: Consider adding project field to ticket schema

### Phase 3: Documentation and Migration (User-Facing)
1. Update tool docstrings with project_id requirement
2. Add migration guide for existing users
3. Add examples showing project_id usage
4. Update error messages with helpful guidance

---

## Testing Requirements

### Test Cases Needed

```python
# Test 1: Reject search without project_id
result = await ticket_search(query="bug")
assert result["status"] == "error"
assert "project_id" in result["error"]

# Test 2: Accept search with explicit project_id
result = await ticket_search(query="bug", project_id="PROJ-123")
assert result["status"] == "completed"

# Test 3: Accept search with default_project configured
config_set_default_project(project_id="PROJ-123")
result = await ticket_search(query="bug")
assert result["status"] == "completed"

# Test 4: Explicit project_id overrides default
config_set_default_project(project_id="PROJ-123")
result = await ticket_search(query="bug", project_id="PROJ-456")
assert result["tickets"][0]["parent_epic"] == "PROJ-456"

# Test 5: Single issue lookup works without project_id
result = await ticket_read(ticket_id="PROJ-123-456")
assert result["status"] == "completed"
```

---

## Risk Assessment

### Breaking Changes
- **High Impact**: Existing scripts/workflows using search/list without project_id will fail
- **Mitigation**: Provide migration guide, clear error messages with instructions

### Performance
- **Low Impact**: Adding project filtering should improve performance (smaller result sets)

### User Experience
- **Medium Impact**: Requires additional parameter or configuration step
- **Mitigation**: Make error messages helpful, provide examples

---

## Files Requiring Modification

### Core Models
- `src/mcp_ticketer/core/models.py:530` - `SearchQuery.project` field (make non-optional or validate)

### MCP Tools
- `src/mcp_ticketer/mcp/server/tools/search_tools.py:15` - `ticket_search()`
- `src/mcp_ticketer/mcp/server/tools/search_tools.py:105` - `ticket_search_hierarchy()`
- `src/mcp_ticketer/mcp/server/tools/ticket_tools.py:614` - `ticket_list()`
- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py:138` - `epic_list()`

### Adapters (Verification/Enforcement)
- `src/mcp_ticketer/adapters/linear/adapter.py:1808-1885` - Verify project filtering
- `src/mcp_ticketer/adapters/jira.py:669-758` - Enforce project_key requirement
- `src/mcp_ticketer/adapters/github.py:796-915` - Document repo scoping
- `src/mcp_ticketer/adapters/aitrackdown.py:439-518` - Consider project support

### Configuration
- `src/mcp_ticketer/core/project_config.py:186` - Document default_project usage
- `src/mcp_ticketer/mcp/server/tools/config_tools.py` - Ensure default_project tools exist

---

## Next Steps for Engineer

1. **Choose Enforcement Strategy**: Option 1 (strict), Option 2 (recommended), or Option 3 (hybrid)
2. **Implement Validation**: Add project_id parameter and validation to all search/list tools
3. **Update Adapters**: Ensure adapters respect project filtering when provided
4. **Add Tests**: Implement test cases listed above
5. **Update Documentation**: Add examples and migration guide
6. **Release Notes**: Document breaking changes and migration path

---

## Appendix A: Complete Tool Inventory

| Tool | Type | Project Filter? | Action Required |
|------|------|----------------|-----------------|
| `ticket_create()` | Create | ✅ Uses default | ✅ Already correct |
| `ticket_read()` | Read | ✅ N/A (by ID) | ✅ Already correct |
| `ticket_update()` | Update | ✅ N/A (by ID) | ✅ Already correct |
| `ticket_delete()` | Delete | ✅ N/A (by ID) | ✅ Already correct |
| `ticket_search()` | Search | ❌ No | ⚠️ **NEEDS FIX** |
| `ticket_list()` | List | ❌ No | ⚠️ **NEEDS FIX** |
| `ticket_search_hierarchy()` | Search | ❌ No | ⚠️ **NEEDS FIX** |
| `epic_list()` | List | ❌ No | ⚠️ **NEEDS FIX** |
| `epic_create()` | Create | ✅ N/A | ✅ Already correct |
| `epic_read()` | Read | ✅ N/A (by ID) | ✅ Already correct |
| `epic_issues()` | List | ✅ Scoped to epic | ✅ Already correct |
| `issue_tasks()` | List | ✅ Scoped to issue | ✅ Already correct |
| `get_my_tickets()` | List | ❌ No | ⚠️ **NEEDS FIX** |
| `ticket_summary()` | Read | ✅ N/A (by ID) | ✅ Already correct |
| `ticket_latest()` | Read | ✅ N/A (by ID) | ✅ Already correct |

**4 Tools Require Project Filtering**: `ticket_search()`, `ticket_list()`, `ticket_search_hierarchy()`, `epic_list()`, `get_my_tickets()`

---

## Appendix B: Code Snippets for Implementation

### Before (Current - Problematic)
```python
@mcp.tool()
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    adapter = get_adapter()
    search_query = SearchQuery(
        query=query,
        state=state_enum,
        priority=priority_enum,
        tags=tags,
        assignee=assignee,
        limit=min(limit, 100),
    )
    results = await adapter.search(search_query)
```

### After (Recommended Fix - Option 2)
```python
@mcp.tool()
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    project_id: str | None = None,  # ✅ Added
    limit: int = 10,
) -> dict[str, Any]:
    adapter = get_adapter()

    # ✅ Validate project context
    resolver = ConfigResolver(project_path=Path.cwd())
    config = resolver.load_project_config() or TicketerConfig()
    final_project = project_id or config.default_project

    if not final_project:
        return {
            "status": "error",
            "error": (
                "project_id is required for search operations. "
                "Provide project_id parameter or set default: "
                "config_set_default_project(project_id='PROJ-123')"
            ),
        }

    # ✅ Always include project in search
    search_query = SearchQuery(
        query=query,
        state=state_enum,
        priority=priority_enum,
        tags=tags,
        assignee=assignee,
        project=final_project,  # ✅ Enforced
        limit=min(limit, 100),
    )
    results = await adapter.search(search_query)
```

---

## Conclusion

The current implementation allows search/list operations to span ALL projects in a workspace due to missing project-level enforcement at the MCP tool and adapter levels. While some adapters (GitHub, Linear) enforce team/repo-level scoping, **project-level filtering within those scopes is optional**.

**Recommended Action**: Implement **Option 2** (require project_id OR default_project) to enforce foundational project scoping while maintaining flexibility through configuration.

**Priority**: **HIGH** - This is a correctness and usability issue affecting all multi-project users.

**Estimated Effort**: 2-3 hours for implementation + testing + documentation.

---

**End of Research Report**
