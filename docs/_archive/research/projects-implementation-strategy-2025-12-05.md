# Projects Implementation Strategy

**Strategy Date:** 2025-12-05
**Author:** Claude (Research Agent)
**Project:** mcp-ticketer - Unified Projects Abstraction

---

## Executive Summary

This document outlines a **phased implementation strategy** for adding unified Projects support to mcp-ticketer. The strategy balances:

- **Feature completeness**: Full project management across platforms
- **Backwards compatibility**: Existing Epic-based code continues to work
- **Risk mitigation**: Gradual rollout with fallback options
- **Developer experience**: Clear migration path and documentation

**Timeline:** 3 phases over 8-12 weeks
**Risk Level:** Low (non-breaking, additive changes)

---

## Phase 1: Foundation (Weeks 1-4)

### 1.1 Core Models and Types

**Goal**: Establish unified Project model and type system

**Tasks**:

1. **Add Project model** (`src/mcp_ticketer/core/models.py`):
   ```python
   # Add new models:
   - class ProjectState(str, Enum)
   - class ProjectVisibility(str, Enum)
   - class ProjectScope(str, Enum)
   - class Project(BaseModel)
   - class ProjectStatistics(BaseModel)
   ```

2. **Add ProjectOperations protocol** (`src/mcp_ticketer/core/adapter.py`):
   ```python
   @runtime_checkable
   class ProjectOperations(Protocol):
       async def list_projects(...) -> list[Project]: ...
       async def get_project(...) -> Project | None: ...
       async def create_project(...) -> Project: ...
       async def update_project(...) -> Project | None: ...
       async def delete_project(...) -> bool: ...
       async def get_project_issues(...) -> list[Task]: ...
       async def add_issue_to_project(...) -> bool: ...
       async def remove_issue_from_project(...) -> bool: ...
       async def get_project_statistics(...) -> ProjectStatistics: ...
   ```

3. **Add utility functions** (`src/mcp_ticketer/core/project_utils.py`):
   ```python
   # New file with utilities:
   - def epic_to_project(epic: Epic, platform: str) -> Project
   - def project_to_epic(project: Project) -> Epic  # backwards compat
   - def map_ticket_state_to_project_state(state: TicketState) -> ProjectState
   - def map_project_state_to_ticket_state(state: ProjectState) -> TicketState
   ```

**Testing**:
- Unit tests for Project model validation
- Unit tests for state mapping functions
- Type checking with mypy

**Deliverables**:
- ✅ Project models in core/models.py
- ✅ ProjectOperations protocol in core/adapter.py
- ✅ Utility functions in core/project_utils.py
- ✅ 100% test coverage for new code

**Estimated Effort**: 1-2 weeks

---

### 1.2 GitHub Projects V2 Support

**Goal**: Implement Projects V2 as primary project source for GitHub

**Tasks**:

1. **Add GraphQL queries** (`src/mcp_ticketer/adapters/github/queries.py`):
   ```python
   # Add new queries:
   LIST_ORG_PROJECTS_V2 = """..."""
   LIST_USER_PROJECTS_V2 = """..."""
   GET_PROJECT_V2 = """..."""
   GET_PROJECT_V2_ITEMS = """..."""
   CREATE_PROJECT_V2 = """..."""
   UPDATE_PROJECT_V2 = """..."""
   DELETE_PROJECT_V2 = """..."""
   ADD_PROJECT_V2_ITEM = """..."""
   REMOVE_PROJECT_V2_ITEM = """..."""
   GET_PROJECT_V2_FIELDS = """..."""
   ```

2. **Add mapper functions** (`src/mcp_ticketer/adapters/github/mappers.py`):
   ```python
   def map_github_project_v2_to_project(
       gh_project: dict[str, Any],
       owner_login: str
   ) -> Project: ...
   ```

3. **Implement GitHub adapter methods** (`src/mcp_ticketer/adapters/github/adapter.py`):
   ```python
   class GitHubAdapter(BaseAdapter, ProjectOperations):
       # Configuration
       use_projects_v2: bool  # Enable Projects V2 (default: False)
       github_owner_type: str  # "organization" or "user"

       # New methods
       async def list_projects(...) -> list[Project]: ...
       async def get_project(...) -> Project | None: ...
       async def create_project(...) -> Project: ...
       # ... (all ProjectOperations methods)

       # Internal helpers
       async def _get_project_node_id(self, project_id: str) -> str: ...
       async def _resolve_project_owner(self) -> dict[str, str]: ...
   ```

4. **Update configuration** (`src/mcp_ticketer/core/config.py`):
   ```python
   # Add GitHub config options:
   github_config_schema = {
       "use_projects_v2": {"type": "boolean", "default": False},
       "github_owner_type": {"type": "string", "enum": ["organization", "user"]},
       # ... existing fields
   }
   ```

**Testing**:
- Integration tests with real GitHub Projects V2 API
- Mock tests for GraphQL queries
- Test Projects V2 vs Milestones fallback

**Deliverables**:
- ✅ GitHub Projects V2 GraphQL queries
- ✅ Project V2 mapper functions
- ✅ GitHubAdapter implements ProjectOperations
- ✅ Configuration schema updated
- ✅ Integration tests passing

**Estimated Effort**: 2-3 weeks

---

## Phase 2: Platform Integration (Weeks 5-8)

### 2.1 Linear Projects Integration

**Goal**: Implement Linear Projects support using existing GraphQL API

**Tasks**:

1. **Review existing Linear implementation** (`src/mcp_ticketer/adapters/linear/adapter.py`):
   - ✅ Linear already has `get_project()` method
   - ✅ Project-to-Epic mapping exists
   - Need to add: `list_projects()`, `create_project()`, CRUD operations

2. **Implement ProjectOperations** (`src/mcp_ticketer/adapters/linear/adapter.py`):
   ```python
   class LinearAdapter(BaseAdapter, ProjectOperations):
       # Already exists: get_project()

       # Add new methods:
       async def list_projects(
           self, limit: int = 20, offset: int = 0, **filters
       ) -> list[Project]:
           # Use existing LIST_PROJECTS_QUERY
           ...

       async def create_project(
           self, name: str, description: str | None = None, **kwargs
       ) -> Project:
           # Use Linear's createProject mutation
           ...

       async def update_project(...) -> Project | None: ...
       async def delete_project(...) -> bool: ...  # archive in Linear
       async def get_project_issues(...) -> list[Task]: ...  # exists as _get_project_issues
       async def add_issue_to_project(...) -> bool: ...
       async def remove_issue_from_project(...) -> bool: ...
   ```

3. **Add Linear-specific queries** (`src/mcp_ticketer/adapters/linear/queries.py`):
   ```python
   # Add if missing:
   CREATE_PROJECT_MUTATION = """..."""
   UPDATE_PROJECT_MUTATION = """..."""
   ARCHIVE_PROJECT_MUTATION = """..."""
   ADD_ISSUE_TO_PROJECT_MUTATION = """..."""
   ```

**Testing**:
- Integration tests with Linear API
- Verify Linear project → Epic backwards compat
- Test project CRUD lifecycle

**Deliverables**:
- ✅ LinearAdapter implements ProjectOperations
- ✅ Linear-specific mutations added
- ✅ Integration tests passing

**Estimated Effort**: 1-2 weeks

---

### 2.2 JIRA Epics Integration

**Goal**: Map JIRA Epics to unified Project model

**Tasks**:

1. **Implement ProjectOperations** (`src/mcp_ticketer/adapters/jira/adapter.py`):
   ```python
   class JiraAdapter(BaseAdapter, ProjectOperations):
       # Reuse existing epic methods with new interface

       async def list_projects(...) -> list[Project]:
           # Delegate to list_epics(), convert to Project
           epics = await self.list_epics(...)
           return [epic_to_project(epic, "jira") for epic in epics]

       async def get_project(self, project_id: str) -> Project | None:
           epic = await self.get_epic(project_id)
           return epic_to_project(epic, "jira") if epic else None

       # Create/update/delete delegate to epic methods
       ...
   ```

2. **Update JQL queries** (`src/mcp_ticketer/adapters/jira/queries.py`):
   - Ensure epic queries support filtering by status, assignee, etc.

3. **Add JIRA-specific field handling**:
   - Handle custom epic fields (epic link, epic name, etc.)
   - Map JIRA status categories to ProjectState

**Testing**:
- Integration tests with JIRA Cloud/Server
- Test epic → project conversion
- Verify JQL query correctness

**Deliverables**:
- ✅ JiraAdapter implements ProjectOperations
- ✅ Epic-to-Project conversion working
- ✅ Integration tests passing

**Estimated Effort**: 1-2 weeks

---

### 2.3 Unified MCP Tools

**Goal**: Expose Projects via MCP server tools

**Tasks**:

1. **Add MCP project tools** (`src/mcp_ticketer/mcp/tools_projects.py`):
   ```python
   # New file with MCP tool definitions:

   @mcp.tool()
   async def project_list(
       adapter_name: str | None = None,
       state: str | None = None,
       limit: int = 20
   ) -> dict[str, Any]:
       """List projects from configured adapter."""
       ...

   @mcp.tool()
   async def project_get(
       project_id: str,
       adapter_name: str | None = None
   ) -> dict[str, Any]:
       """Get project by ID."""
       ...

   @mcp.tool()
   async def project_create(
       name: str,
       description: str | None = None,
       state: str = "planned",
       adapter_name: str | None = None
   ) -> dict[str, Any]:
       """Create new project."""
       ...

   @mcp.tool()
   async def project_update(
       project_id: str,
       adapter_name: str | None = None,
       **updates
   ) -> dict[str, Any]:
       """Update project."""
       ...

   @mcp.tool()
   async def project_add_issue(
       project_id: str,
       issue_id: str,
       adapter_name: str | None = None
   ) -> dict[str, Any]:
       """Add issue to project."""
       ...

   @mcp.tool()
   async def project_statistics(
       project_id: str,
       adapter_name: str | None = None
   ) -> dict[str, Any]:
       """Get project statistics."""
       ...
   ```

2. **Register tools in MCP server** (`src/mcp_ticketer/mcp/server.py`):
   ```python
   from .tools_projects import (
       project_list,
       project_get,
       project_create,
       project_update,
       project_add_issue,
       project_statistics
   )

   # Register in server initialization
   ```

3. **Update MCP documentation** (`docs/mcp-api-reference.md`):
   - Document all new project_* tools
   - Provide usage examples
   - Explain platform differences

**Testing**:
- MCP tool integration tests
- Test tool routing to correct adapter
- Verify error handling

**Deliverables**:
- ✅ MCP tools for project operations
- ✅ Tools registered in server
- ✅ Documentation updated
- ✅ Integration tests passing

**Estimated Effort**: 1 week

---

## Phase 3: Advanced Features (Weeks 9-12)

### 3.1 Custom Fields Support (GitHub Projects V2)

**Goal**: Support GitHub Projects V2 custom fields

**Tasks**:

1. **Implement field introspection**:
   ```python
   async def get_project_fields(
       self, project_id: str
   ) -> dict[str, ProjectField]:
       """Get all custom fields for a project."""
       # Query ProjectV2.fields
       # Cache field schemas
       ...

   async def update_project_item_field(
       self,
       project_id: str,
       item_id: str,
       field_name: str,
       value: Any
   ) -> bool:
       """Update custom field value."""
       # Resolve field name → field ID
       # Resolve field type and validate value
       # Execute updateProjectV2ItemFieldValue mutation
       ...
   ```

2. **Add field caching**:
   - Cache field schemas per project
   - Invalidate cache on field changes
   - Provide manual cache refresh method

**Testing**:
- Test each field type (text, number, date, select, iteration)
- Test field caching and invalidation
- Verify type validation

**Deliverables**:
- ✅ Custom field support for GitHub Projects V2
- ✅ Field caching implemented
- ✅ Tests for all field types

**Estimated Effort**: 1-2 weeks

---

### 3.2 Project Statistics and Analytics

**Goal**: Provide rich project analytics

**Tasks**:

1. **Implement statistics calculation**:
   ```python
   async def get_project_statistics(
       self, project_id: str
   ) -> ProjectStatistics:
       """Calculate comprehensive project statistics."""
       # Get all project issues
       # Count by state
       # Calculate velocity (if time tracking available)
       # Assess health score
       # Identify blockers
       ...
   ```

2. **Add health score algorithm**:
   ```python
   def calculate_health_score(stats: ProjectStatistics) -> int:
       """Calculate project health score (0-100)."""
       # Factors:
       # - Completion percentage
       # - Number of blockers
       # - Overdue items
       # - Recent activity
       # - In-progress vs open ratio
       ...
   ```

3. **Add MCP analytics tools**:
   ```python
   @mcp.tool()
   async def project_health_dashboard(
       project_id: str
   ) -> dict[str, Any]:
       """Get project health dashboard."""
       ...
   ```

**Testing**:
- Test statistics calculation accuracy
- Test health score algorithm
- Verify analytics tool output

**Deliverables**:
- ✅ Project statistics implementation
- ✅ Health score algorithm
- ✅ Analytics MCP tools
- ✅ Dashboard visualizations

**Estimated Effort**: 1-2 weeks

---

### 3.3 Migration Utilities

**Goal**: Provide tools to migrate from Epic to Project

**Tasks**:

1. **Create migration script** (`scripts/migrate_epic_to_project.py`):
   ```python
   async def migrate_adapter_to_projects(
       adapter_name: str,
       dry_run: bool = True
   ) -> dict[str, Any]:
       """Migrate adapter from Epic-based to Project-based."""
       # For each epic:
       # 1. Create equivalent project
       # 2. Migrate child issues
       # 3. Preserve metadata
       # 4. Update references
       ...
   ```

2. **Add CLI command** (`src/mcp_ticketer/cli/commands.py`):
   ```bash
   mcp-ticketer migrate epic-to-project --adapter github --dry-run
   ```

3. **Create migration guide** (`docs/MIGRATION_EPIC_TO_PROJECT.md`):
   - Step-by-step migration instructions
   - Rollback procedures
   - Common issues and solutions

**Testing**:
- Test migration with sample data
- Test dry-run mode
- Verify rollback capability

**Deliverables**:
- ✅ Migration script
- ✅ CLI command
- ✅ Migration guide
- ✅ Tested with sample data

**Estimated Effort**: 1 week

---

## Backwards Compatibility Strategy

### Maintaining Epic Support

**Approach**: Keep Epic model and methods, delegate to Project internally

```python
# In GitHubAdapter
async def get_epic(self, epic_id: str) -> Epic | None:
    """Get epic (delegates to project for Projects V2)."""
    if self.use_projects_v2:
        project = await self.get_project(epic_id)
        return project.to_epic() if project else None
    else:
        # Use milestone-based implementation
        milestone = await self.get_milestone(epic_id)
        return self._milestone_to_epic(milestone) if milestone else None


async def create_epic(self, title: str, **kwargs) -> Epic:
    """Create epic (delegates to project for Projects V2)."""
    if self.use_projects_v2:
        project = await self.create_project(name=title, **kwargs)
        return project.to_epic()
    else:
        # Use milestone-based implementation
        milestone = await self.create_milestone(title=title, **kwargs)
        return self._milestone_to_epic(milestone)
```

**Deprecation Timeline**:
- **Phase 1-2**: Epic methods work, no warnings
- **Phase 3**: Add deprecation warnings to Epic methods
- **v3.0 (future)**: Consider removing Epic methods (breaking change)

---

## Configuration Strategy

### Adapter Configuration

**GitHub Adapter**:
```yaml
adapters:
  github:
    api_key: ${GITHUB_TOKEN}
    owner: my-org
    repo: my-repo

    # Projects V2 configuration (new)
    use_projects_v2: true           # Enable Projects V2 (default: false)
    github_owner_type: organization # or "user"
    default_project_visibility: private  # or "public"

    # Legacy Milestones (backwards compat)
    # use_projects_v2: false (default)
```

**Linear Adapter**:
```yaml
adapters:
  linear:
    api_key: ${LINEAR_API_KEY}
    team_key: ENG

    # Projects are default in Linear (no flag needed)
```

**JIRA Adapter**:
```yaml
adapters:
  jira:
    base_url: https://company.atlassian.net
    email: user@company.com
    api_token: ${JIRA_API_TOKEN}
    project_key: PROJ

    # Epics map to Projects (no flag needed)
```

### Environment Variables

```bash
# GitHub
export GITHUB_TOKEN=ghp_...
export GITHUB_USE_PROJECTS_V2=true
export GITHUB_OWNER_TYPE=organization

# Linear
export LINEAR_API_KEY=lin_api_...

# JIRA
export JIRA_API_TOKEN=...
```

---

## Testing Strategy

### Unit Tests

**Coverage Requirements**: 90%+ for new code

**Test Files**:
```
tests/
  core/
    test_project_models.py       # Project model validation
    test_project_utils.py        # Conversion utilities
  adapters/
    test_github_projects_v2.py   # GitHub Projects V2
    test_linear_projects.py      # Linear Projects
    test_jira_projects.py        # JIRA Epics as Projects
  mcp/
    test_project_tools.py        # MCP tools
```

**Example Tests**:
```python
@pytest.mark.asyncio
async def test_github_create_project_v2():
    """Test creating GitHub Projects V2 project."""
    adapter = GitHubAdapter({"use_projects_v2": True, ...})

    project = await adapter.create_project(
        name="Test Project",
        description="Integration test",
        visibility=ProjectVisibility.PRIVATE
    )

    assert project.id is not None
    assert project.platform == "github"
    assert project.name == "Test Project"

    # Cleanup
    await adapter.delete_project(project.id)


@pytest.mark.asyncio
async def test_epic_to_project_backwards_compat():
    """Test Epic → Project conversion."""
    epic = Epic(
        id="epic-123",
        title="Auth System",
        state=TicketState.IN_PROGRESS
    )

    project = epic_to_project(epic, "linear")

    assert project.name == epic.title
    assert project.state == ProjectState.ACTIVE  # IN_PROGRESS → ACTIVE
    assert project.platform == "linear"
```

### Integration Tests

**Requirements**: Real API credentials for each platform

**Test Scenarios**:
1. Create project → Add issues → Get statistics → Delete project
2. List projects with various filters
3. Update project state and metadata
4. Cross-platform consistency (same operations on Linear/GitHub/JIRA)

**CI/CD**:
- Run unit tests on every commit
- Run integration tests nightly (requires API credentials)
- Skip integration tests on forks (no credentials)

---

## Documentation Strategy

### User Documentation

**Files to Create/Update**:

1. **`docs/projects-guide.md`**: Comprehensive project management guide
   - What are Projects in mcp-ticketer?
   - Platform comparison table
   - Usage examples
   - Best practices

2. **`docs/mcp-api-reference.md`**: Update with project tools
   - `project_list`
   - `project_get`
   - `project_create`
   - `project_update`
   - `project_add_issue`
   - `project_statistics`

3. **`docs/adapters/github.md`**: GitHub-specific docs
   - Projects V2 vs Milestones comparison
   - Custom fields guide
   - Iteration (sprint) support

4. **`docs/MIGRATION_EPIC_TO_PROJECT.md`**: Migration guide
   - Why migrate to Projects?
   - Step-by-step migration
   - Rollback procedures
   - FAQ

### Developer Documentation

**Files to Create/Update**:

1. **`docs/architecture/projects-design.md`**: Architecture documentation
   - Project model design
   - Platform mapping rationale
   - State machine diagrams

2. **`CONTRIBUTING.md`**: Update with project implementation guidelines
   - How to add project support to new adapter
   - Testing requirements
   - Code review checklist

---

## Risk Management

### Identified Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Breaking changes to Epic API** | Low | High | Maintain Epic methods, delegate to Project internally |
| **GitHub rate limits** | Medium | Medium | Implement caching, batch operations, retry logic |
| **Platform API changes** | Low | Medium | Monitor API changelogs, add version checks |
| **Performance degradation** | Low | Medium | Profile queries, optimize pagination, cache aggressively |
| **Data loss during migration** | Low | High | Require dry-run first, implement rollback, backup data |
| **Cross-platform inconsistencies** | Medium | Medium | Document platform differences, provide fallbacks |

### Mitigation Strategies

1. **Feature Flags**: Use `use_projects_v2` flag for gradual rollout
2. **Logging**: Comprehensive logging for debugging issues
3. **Monitoring**: Track API usage, errors, performance
4. **Rollback Plan**: Keep Epic methods working, allow disabling Projects
5. **User Communication**: Clear documentation, migration guide, deprecation warnings

---

## Success Criteria

### Phase 1 Success Metrics

✅ Project model implemented and tested
✅ GitHub Projects V2 support working
✅ All unit tests passing (90%+ coverage)
✅ Documentation updated

### Phase 2 Success Metrics

✅ Linear Projects support working
✅ JIRA Epics mapped to Projects
✅ MCP tools exposing project operations
✅ Integration tests passing on all platforms

### Phase 3 Success Metrics

✅ Custom fields support for GitHub Projects V2
✅ Project statistics and analytics working
✅ Migration utilities available
✅ User guide and migration docs published

### Overall Success

✅ Users can manage projects across Linear, GitHub, and JIRA
✅ No breaking changes to existing Epic-based code
✅ Performance acceptable (no significant degradation)
✅ Positive user feedback on new functionality

---

## Timeline Summary

| Phase | Duration | Key Deliverables | Dependencies |
|-------|----------|------------------|--------------|
| **Phase 1** | 3-4 weeks | Project models, GitHub Projects V2 | None |
| **Phase 2** | 3-4 weeks | Linear/JIRA integration, MCP tools | Phase 1 |
| **Phase 3** | 2-4 weeks | Custom fields, analytics, migration | Phase 2 |
| **Total** | **8-12 weeks** | Full project management support | - |

---

## Next Steps

### Immediate Actions (Week 1)

1. ✅ Review and approve this implementation strategy
2. ✅ Create GitHub issue/epic for Projects feature
3. ✅ Set up feature branch: `feature/unified-projects`
4. ✅ Add Project model to `core/models.py`
5. ✅ Add ProjectOperations protocol to `core/adapter.py`
6. ✅ Write initial unit tests
7. ✅ Create project board for tracking progress

### Week 2-4: GitHub Projects V2

1. Implement GraphQL queries
2. Add GitHub adapter project methods
3. Write integration tests
4. Update configuration schema
5. Document GitHub-specific features

### Week 5-8: Platform Integration

1. Implement Linear project support
2. Implement JIRA project support
3. Add MCP tools
4. Update documentation
5. Run cross-platform integration tests

### Week 9-12: Advanced Features

1. Add custom fields support
2. Implement project analytics
3. Create migration utilities
4. Finalize documentation
5. Release beta version

---

## Conclusion

This implementation strategy provides a **clear, phased approach** to adding unified Projects support to mcp-ticketer while:

✅ **Maintaining backwards compatibility** with Epic-based code
✅ **Minimizing risk** through gradual rollout and feature flags
✅ **Ensuring quality** with comprehensive testing and documentation
✅ **Providing value** at each phase with incremental deliverables

**Recommended Approval**: This strategy is ready for implementation with estimated timeline of 8-12 weeks.

---

**Related Documents:**
- [GitHub Projects V2 API Analysis](./github-projects-v2-api-analysis-2025-12-05.md)
- [Unified Projects Design](./unified-projects-design-2025-12-05.md)
- [Platform Mapping Document](./platform-concept-mapping-2025-12-05.md)
