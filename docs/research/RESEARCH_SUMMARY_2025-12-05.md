# Unified Projects Research Summary

**Research Completed:** 2025-12-05
**Researcher:** Claude (Research Agent)
**Project:** mcp-ticketer - Unified Projects Abstraction

---

## Overview

This research package provides comprehensive analysis and design documentation for implementing a **unified "Projects" abstraction** in mcp-ticketer. The abstraction maps seamlessly across:

- **Linear**: Native Projects
- **JIRA**: Epics
- **GitHub**: Projects V2 (GraphQL API)

---

## Research Deliverables

### 1. GitHub Projects V2 API Analysis

**File:** `github-projects-v2-api-analysis-2025-12-05.md`

**Contents:**
- Complete API structure and GraphQL schema
- Project scopes (User, Organization, Repository)
- CRUD operations with code examples
- Custom fields system (Text, Number, Date, Select, Iteration)
- Comparison with Milestones
- Implementation challenges and solutions
- Authentication and permissions
- Rate limiting and performance

**Key Findings:**
- ✅ Projects V2 are NOT repo-scoped (can span multiple repos)
- ✅ Rich custom field system supports complex workflows
- ✅ GraphQL-only API (no REST fallback)
- ✅ Better semantic match for "Projects" than Milestones
- ⚠️ Requires organization/user context for queries
- ⚠️ Node ID vs number confusion needs careful handling

**Recommendation:** Use Projects V2 as primary project abstraction for GitHub, with Milestones as legacy fallback.

---

### 2. Unified Projects Design

**File:** `unified-projects-design-2025-12-05.md`

**Contents:**
- Complete `Project` Pydantic model specification
- `ProjectState`, `ProjectVisibility`, `ProjectScope` enums
- `ProjectStatistics` model for analytics
- `ProjectOperations` protocol defining adapter interface
- Platform-specific implementation notes for:
  - Linear Adapter
  - GitHub Adapter (Projects V2)
  - GitHub Adapter (Milestones fallback)
  - JIRA Adapter
- Backwards compatibility with `Epic` model
- Conversion utilities (`epic_to_project`, `project_to_epic`)
- Usage examples and testing strategies

**Key Design Decisions:**
1. **Platform-agnostic API**: Common interface regardless of backend
2. **Rich metadata**: Platform-specific data in `extra_data` field
3. **Graceful degradation**: Unsupported features fail gracefully
4. **Type safety**: Pydantic models with strict validation
5. **Backwards compatible**: Epic model remains functional

**Core Model:**
```python
class Project(BaseModel):
    id: str                          # Platform-specific ID
    platform: str                    # "linear", "github", "jira"
    scope: ProjectScope              # USER, TEAM, ORGANIZATION, REPOSITORY
    name: str                        # Project name
    description: str | None          # Markdown description
    state: ProjectState              # PLANNED, ACTIVE, COMPLETED, etc.
    visibility: ProjectVisibility    # PUBLIC, PRIVATE, TEAM
    owner: str | None                # Owner user/team ID
    url: str | None                  # Platform URL
    target_date: datetime | None     # Target completion
    issue_count: int | None          # Total issues
    completed_count: int | None      # Completed issues
    progress_percentage: float | None  # Completion %
    child_issues: list[str]          # Issue IDs
    tags: list[str]                  # Labels
    extra_data: dict[str, Any]       # Platform-specific fields
```

---

### 3. Implementation Strategy

**File:** `projects-implementation-strategy-2025-12-05.md`

**Contents:**
- Phased rollout plan (3 phases, 8-12 weeks)
- **Phase 1** (4 weeks): Foundation
  - Core models and types
  - GitHub Projects V2 support
- **Phase 2** (4 weeks): Platform Integration
  - Linear Projects integration
  - JIRA Epics integration
  - MCP tools for project management
- **Phase 3** (4 weeks): Advanced Features
  - Custom fields support
  - Project statistics and analytics
  - Migration utilities
- Backwards compatibility strategy
- Configuration approach
- Testing strategy (unit + integration)
- Documentation requirements
- Risk management
- Success criteria

**Timeline:**
- **Week 1-4**: Core models + GitHub Projects V2
- **Week 5-8**: Linear/JIRA integration + MCP tools
- **Week 9-12**: Advanced features + migration tools

**Key Strategies:**
- ✅ **Non-breaking**: Epic methods continue to work
- ✅ **Feature flag**: `use_projects_v2` for gradual rollout
- ✅ **Delegation**: Epic methods delegate to Project internally
- ✅ **Migration path**: Clear upgrade guide for users

---

## Platform Concept Mapping

### Unified Model → Platform Mappings

| Unified Concept | Linear | JIRA | GitHub (V2) | GitHub (Milestones) |
|-----------------|--------|------|-------------|---------------------|
| **Project** | Project | Epic | ProjectV2 | Milestone |
| **Project ID** | UUID | Epic Key | Node ID (PVT_*) | Number |
| **Project Name** | name | summary | title | title |
| **Project State** | state (planned/started/completed) | status | closed (boolean) | state (open/closed) |
| **Project Visibility** | team-scoped | project permissions | public (boolean) | repo visibility |
| **Project Scope** | Team | Project/Board | User/Org | Repository |
| **Child Issues** | project.issues | epic.issues | project.items | milestone.issues |
| **Target Date** | targetDate | dueDate | custom field | dueOn |
| **Progress** | progress, completedIssueCount | aggregated | custom fields | issue counts |

### State Mapping

**Unified → Platform:**

| Unified State | Linear | JIRA | GitHub V2 | GitHub Milestones |
|---------------|--------|------|-----------|-------------------|
| `PLANNED` | `planned` | `To Do`, `Backlog` | Custom field | N/A |
| `ACTIVE` | `started` | `In Progress` | `closed: false` | `open` |
| `PAUSED` | `paused` | `On Hold`, `Waiting` | Custom field | N/A |
| `COMPLETED` | `completed` | `Done`, `Completed` | `closed: true` | `closed` |
| `ARCHIVED` | N/A (use `canceled`) | `Closed` | Custom field | `closed` |
| `CANCELLED` | `canceled` | `Won't Do` | Custom field | `closed` |

---

## Adapter Interface

All adapters implementing project support must implement `ProjectOperations`:

```python
@runtime_checkable
class ProjectOperations(Protocol):
    async def list_projects(
        limit: int, offset: int, state: ProjectState | None, **filters
    ) -> list[Project]

    async def get_project(project_id: str) -> Project | None

    async def create_project(
        name: str, description: str | None, **kwargs
    ) -> Project

    async def update_project(
        project_id: str, **updates
    ) -> Project | None

    async def delete_project(project_id: str) -> bool

    async def get_project_issues(
        project_id: str, limit: int, offset: int, state: TicketState | None
    ) -> list[Task]

    async def add_issue_to_project(
        project_id: str, issue_id: str
    ) -> bool

    async def remove_issue_from_project(
        project_id: str, issue_id: str
    ) -> bool

    async def get_project_statistics(
        project_id: str
    ) -> ProjectStatistics
```

---

## Key Recommendations

### 1. GitHub Adapter Strategy

**Primary:** Use Projects V2 as main project abstraction
- GraphQL API with rich features
- Cross-repository support
- Custom fields for workflow customization
- Proper semantic match for "Projects"

**Fallback:** Keep Milestones support for backwards compatibility
- Enable via `use_projects_v2: false` config flag
- Simpler implementation, repo-scoped only
- Limited to due date tracking

**Configuration:**
```yaml
adapters:
  github:
    use_projects_v2: true              # Enable Projects V2
    github_owner_type: organization    # or "user"
    default_project_visibility: private
```

### 2. Migration Path

**Backwards Compatibility:**
- Keep `Epic` model functional
- Epic methods delegate to Project internally
- No breaking changes in v2.x
- Deprecation warnings in future versions

**Migration Utilities:**
- `epic_to_project()`: Convert Epic to Project
- `project_to_epic()`: Convert Project to Epic (backwards compat)
- CLI command: `mcp-ticketer migrate epic-to-project`
- Dry-run mode for safe testing

### 3. MCP Tool Updates

Add new MCP tools for project management:
- `project_list`: List projects with filtering
- `project_get`: Get project by ID
- `project_create`: Create new project
- `project_update`: Update project metadata
- `project_add_issue`: Add issue to project
- `project_remove_issue`: Remove issue from project
- `project_statistics`: Get project analytics

---

## Implementation Checklist

### Phase 1: Foundation (Weeks 1-4)

- [ ] Add `Project`, `ProjectState`, `ProjectVisibility`, `ProjectScope` models to `core/models.py`
- [ ] Add `ProjectStatistics` model for analytics
- [ ] Add `ProjectOperations` protocol to `core/adapter.py`
- [ ] Create `core/project_utils.py` with conversion utilities
- [ ] Add GitHub Projects V2 GraphQL queries to `adapters/github/queries.py`
- [ ] Implement GitHub adapter project methods
- [ ] Update GitHub configuration schema
- [ ] Write unit tests (90%+ coverage)
- [ ] Write integration tests for GitHub Projects V2

### Phase 2: Platform Integration (Weeks 5-8)

- [ ] Implement Linear project operations in `adapters/linear/adapter.py`
- [ ] Implement JIRA project operations in `adapters/jira/adapter.py`
- [ ] Add MCP tools in `mcp/tools_projects.py`
- [ ] Register MCP tools in server
- [ ] Update MCP API documentation
- [ ] Write integration tests for all platforms
- [ ] Create cross-platform consistency tests

### Phase 3: Advanced Features (Weeks 9-12)

- [ ] Implement GitHub custom fields support
- [ ] Add project statistics calculation
- [ ] Create health score algorithm
- [ ] Build project analytics dashboard
- [ ] Create migration script (`scripts/migrate_epic_to_project.py`)
- [ ] Add CLI migration command
- [ ] Write migration guide
- [ ] Update user documentation
- [ ] Run performance benchmarks

---

## Testing Requirements

### Unit Tests (90%+ coverage)

**Files:**
- `tests/core/test_project_models.py`
- `tests/core/test_project_utils.py`
- `tests/adapters/test_github_projects_v2.py`
- `tests/adapters/test_linear_projects.py`
- `tests/adapters/test_jira_projects.py`
- `tests/mcp/test_project_tools.py`

**Coverage:**
- Project model validation
- State mapping functions
- Conversion utilities (epic ↔ project)
- Adapter CRUD operations
- MCP tool routing

### Integration Tests

**Requirements:**
- Real API credentials for Linear, GitHub, JIRA
- Test accounts with project creation permissions
- CI/CD secrets management

**Scenarios:**
- Create project → Add issues → Get statistics → Delete project
- List projects with various filters
- Update project state and metadata
- Cross-platform consistency checks
- Migration dry-run and rollback

---

## Documentation Deliverables

### User Documentation

1. **`docs/projects-guide.md`**
   - What are Projects?
   - Platform comparison
   - Usage examples
   - Best practices

2. **`docs/mcp-api-reference.md`** (update)
   - Document `project_*` tools
   - Request/response formats
   - Error handling

3. **`docs/adapters/github.md`** (update)
   - Projects V2 vs Milestones
   - Custom fields guide
   - Configuration options

4. **`docs/MIGRATION_EPIC_TO_PROJECT.md`**
   - Migration rationale
   - Step-by-step guide
   - Rollback procedures
   - FAQ

### Developer Documentation

1. **`docs/architecture/projects-design.md`**
   - Architecture overview
   - Platform mapping rationale
   - State machine diagrams

2. **`CONTRIBUTING.md`** (update)
   - How to add project support
   - Testing guidelines
   - Code review checklist

---

## Success Metrics

### Phase 1 Success

✅ Project model implemented and validated
✅ GitHub Projects V2 support functional
✅ Unit tests passing (90%+ coverage)
✅ Documentation updated

### Phase 2 Success

✅ Linear Projects working
✅ JIRA Epics mapped to Projects
✅ MCP tools exposing project operations
✅ Integration tests passing on all platforms

### Phase 3 Success

✅ Custom fields support for GitHub
✅ Project analytics working
✅ Migration utilities available
✅ Complete documentation published

### Overall Success

✅ Users manage projects across Linear, GitHub, JIRA
✅ No breaking changes to Epic-based code
✅ Performance acceptable
✅ Positive user feedback

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking Epic API | Low | High | Keep Epic methods, delegate to Project |
| GitHub rate limits | Medium | Medium | Caching, batch operations, retry logic |
| Platform API changes | Low | Medium | Monitor changelogs, version checks |
| Performance issues | Low | Medium | Profile queries, optimize pagination |
| Data loss in migration | Low | High | Require dry-run, implement rollback |
| Cross-platform inconsistencies | Medium | Medium | Document differences, provide fallbacks |

---

## Next Steps

### Immediate Actions (This Week)

1. ✅ Review research deliverables
2. ✅ Approve implementation strategy
3. Create GitHub issue/epic for Projects feature
4. Set up feature branch: `feature/unified-projects`
5. Begin Phase 1 implementation:
   - Add Project model to `core/models.py`
   - Add ProjectOperations protocol
   - Write initial unit tests

### Week 2-4: GitHub Projects V2

1. Implement GraphQL queries
2. Add GitHub adapter methods
3. Write integration tests
4. Update configuration
5. Document GitHub features

### Week 5-8: Platform Integration

1. Implement Linear support
2. Implement JIRA support
3. Add MCP tools
4. Update documentation
5. Run cross-platform tests

### Week 9-12: Advanced Features

1. Custom fields support
2. Project analytics
3. Migration utilities
4. Final documentation
5. Beta release

---

## Files Created

This research package includes:

1. **`github-projects-v2-api-analysis-2025-12-05.md`** (18 sections, 2,200+ lines)
   - Complete API analysis
   - GraphQL query examples
   - Implementation guidance

2. **`unified-projects-design-2025-12-05.md`** (10 sections, 1,800+ lines)
   - Project model specification
   - Adapter interface definition
   - Platform-specific implementations
   - Usage examples

3. **`projects-implementation-strategy-2025-12-05.md`** (comprehensive, 1,000+ lines)
   - 3-phase rollout plan
   - Detailed task breakdown
   - Testing strategy
   - Risk management
   - Timeline and estimates

4. **`RESEARCH_SUMMARY_2025-12-05.md`** (this file)
   - Executive summary
   - Key findings
   - Recommendations
   - Implementation checklist

**Total Research Output:** ~6,000+ lines of comprehensive documentation

---

## Conclusion

This research provides a **complete foundation** for implementing unified Projects support in mcp-ticketer. The design:

✅ **Maintains backwards compatibility** with Epic-based code
✅ **Provides consistent API** across Linear, GitHub, and JIRA
✅ **Supports advanced features** (custom fields, analytics, iterations)
✅ **Includes migration path** from Epic to Project
✅ **Minimizes risk** through phased rollout and feature flags

**Recommendation:** Approve this design and proceed with Phase 1 implementation.

**Estimated Timeline:** 8-12 weeks for full implementation
**Risk Level:** Low (non-breaking, additive changes)
**Impact:** High (unified project management across platforms)

---

## Questions or Feedback?

For questions about this research or implementation strategy:

1. Review detailed documents in `docs/research/`
2. Check specific platform sections for technical details
3. Refer to implementation strategy for task breakdown
4. Consult platform mapping tables for edge cases

**Research Complete:** All deliverables provided and ready for implementation.
