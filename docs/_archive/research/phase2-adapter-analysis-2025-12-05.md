# Phase 2: Adapter Interface Analysis for GitHub Projects V2

**Analysis Date:** 2025-12-05
**Analyst:** Claude (Research Agent)
**Project:** mcp-ticketer - GitHub Projects V2 Integration
**Phase:** Phase 2 - Adapter Implementation Planning

---

## Executive Summary

This analysis reviews the current adapter architecture and provides concrete recommendations for adding GitHub Projects V2 support to mcp-ticketer. The analysis shows that **Phase 1 core models are complete and committed**, providing a solid foundation for Phase 2 adapter implementation.

**Key Findings:**

✅ **Phase 1 Complete**: `Project`, `ProjectState`, `ProjectScope`, `ProjectStatistics` models are implemented in `core/models.py`
✅ **Adapter Interface Ready**: `BaseAdapter` already has project operation stubs (lines 759-980) with `NotImplementedError` defaults
✅ **GitHub Adapter Extensible**: Clean GraphQL-based architecture with modular design (queries, mappers, types)
✅ **Minimal API Changes Needed**: Can implement project support without breaking existing Epic-based APIs

**Recommendation**: Proceed with **Option 1: Implement ProjectV2 methods directly in GitHubAdapter** (detailed below).

---

## 1. Current Adapter Architecture

### 1.1 BaseAdapter Interface (Core)

**Location:** `src/mcp_ticketer/core/adapter.py`

**Key Findings:**

1. **Project Operations Already Defined** (lines 759-980):
   - `project_list(scope, state, limit, offset) -> list[Project]`
   - `project_get(project_id) -> Project | None`
   - `project_create(name, description, state, target_date, **kwargs) -> Project`
   - `project_update(project_id, **updates) -> Project | None`
   - `project_delete(project_id) -> bool`
   - `project_get_issues(project_id, state) -> list[Task]`
   - `project_add_issue(project_id, issue_id) -> bool`
   - `project_remove_issue(project_id, issue_id) -> bool`
   - `project_get_statistics(project_id) -> ProjectStatistics`

2. **Default Behavior**: All methods raise `NotImplementedError` with helpful message:
   ```python
   raise NotImplementedError(
       f"{self.__class__.__name__} does not support project operations. "
       "Use Epic operations for this adapter."
   )
   ```

3. **Epic Operations Coexist** (lines 385-551):
   - `create_epic()`, `get_epic()`, `list_epics()`
   - `create_issue()`, `list_issues_by_epic()`
   - Epic-based hierarchy is **NOT deprecated** yet

**Implication**: We can implement project operations **without removing Epic support**, maintaining full backwards compatibility.

---

### 1.2 Core Models (Phase 1 Complete)

**Location:** `src/mcp_ticketer/core/models.py`

**Implemented Models:**

```python
class ProjectState(str, Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"

class ProjectVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    TEAM = "team"

class ProjectScope(str, Enum):
    USER = "user"
    TEAM = "team"
    ORGANIZATION = "organization"
    REPOSITORY = "repository"

class Project(BaseModel):
    # Core identification
    id: str
    platform: str
    platform_id: str
    scope: ProjectScope

    # Basic information
    name: str
    description: str | None
    state: ProjectState
    visibility: ProjectVisibility

    # Ownership
    owner_id: str | None
    owner_name: str | None
    team_id: str | None
    team_name: str | None

    # URLs and dates
    url: str | None
    created_at: datetime | None
    updated_at: datetime | None
    start_date: datetime | None
    target_date: datetime | None
    completed_at: datetime | None

    # Progress tracking
    child_issues: list[str]
    issue_count: int | None
    completed_count: int | None
    in_progress_count: int | None
    progress_percentage: float | None

    # Platform-specific
    extra_data: dict[str, Any]

    # Methods
    def calculate_progress(self) -> float

class ProjectStatistics(BaseModel):
    project_id: str
    total_issues: int
    completed_issues: int
    in_progress_issues: int
    open_issues: int
    blocked_issues: int
    progress_percentage: float
    velocity: float | None
    estimated_completion: datetime | None
```

**Status**: ✅ **All models ready for use**. No changes needed.

---

### 1.3 GitHub Adapter Architecture

**Location:** `src/mcp_ticketer/adapters/github/`

**File Structure:**
```
github/
├── adapter.py        # Main adapter implementation
├── client.py         # HTTP/GraphQL client wrapper
├── queries.py        # GraphQL query strings
├── mappers.py        # Data transformation functions
├── types.py          # Type definitions and mappings
└── __init__.py
```

**Key Characteristics:**

1. **GraphQL-First Design**:
   - Uses GitHub GraphQL API v4 for most operations
   - REST API v3 for mutations (create/update/delete)
   - Fragment-based query composition (see `queries.py` lines 29-91)

2. **Modular Architecture**:
   - **Queries**: Centralized in `queries.py` (lines 249-322 have preliminary ProjectV2 queries)
   - **Mappers**: Data transformations in `mappers.py` (e.g., `map_github_milestone_to_epic`)
   - **Types**: State/priority mappings in `types.py`

3. **Current Projects V2 Support**:
   - ✅ Queries defined: `GET_PROJECT_ITERATIONS`, `GET_PROJECT_ITEMS` (lines 249-322)
   - ❌ No ProjectV2 list/create/update/delete queries yet
   - ❌ No ProjectV2 mappers yet
   - ❌ No ProjectV2 adapter methods implemented

4. **Configuration Support**:
   - `use_projects_v2: bool` flag already exists (line 97)
   - Currently unused (no code paths check this flag)

---

## 2. Implementation Options Analysis

### Option 1: Implement ProjectV2 Methods Directly in GitHubAdapter ⭐ **RECOMMENDED**

**Approach:**
- Add project_* methods to `GitHubAdapter` class
- Override base class `NotImplementedError` stubs
- Use existing GraphQL infrastructure
- Respect `use_projects_v2` config flag

**Pros:**
- ✅ Minimal code changes (add methods, no refactoring)
- ✅ Leverages existing GraphQL client
- ✅ No breaking changes to API
- ✅ Easy to test incrementally
- ✅ Follows existing adapter pattern (see `milestone_*` methods)

**Cons:**
- ⚠️ `GitHubAdapter` class will be large (~1500+ lines)
- ⚠️ Two project systems in one adapter (Milestones vs ProjectV2)

**Implementation Estimate:** 2-3 days for core CRUD operations

---

### Option 2: Create ProjectAdapter Mixin/Protocol

**Approach:**
- Define `ProjectOperations` protocol in `core/adapter.py`
- Create `GitHubProjectV2Mixin` class
- Compose `GitHubAdapter` with mixin

**Pros:**
- ✅ Better separation of concerns
- ✅ Reusable across adapters (Linear, JIRA can use same protocol)
- ✅ Easier to test in isolation

**Cons:**
- ❌ Requires refactoring `BaseAdapter`
- ❌ More complex class hierarchy
- ❌ Python multiple inheritance can be tricky
- ❌ Delays Phase 2 implementation

**Implementation Estimate:** 4-5 days (includes refactoring)

---

### Option 3: Separate GitHubProjectsV2Adapter

**Approach:**
- Create new adapter class: `GitHubProjectsV2Adapter`
- User chooses: `adapter: github` (milestones) or `adapter: github-projects-v2` (ProjectV2)
- Complete separation

**Pros:**
- ✅ Clean separation of concerns
- ✅ No conditional logic in single adapter
- ✅ Easy to maintain independently

**Cons:**
- ❌ Duplicate code between adapters (90% shared)
- ❌ Confusing for users ("which GitHub adapter?")
- ❌ Breaks existing configs
- ❌ Two adapters to maintain for GitHub

**Implementation Estimate:** 5-7 days (includes code duplication)

---

## 3. Recommended Approach: Option 1 (Direct Implementation)

### 3.1 Required Methods (Minimal Set for Phase 2)

**Priority 1: Core CRUD Operations**

```python
class GitHubAdapter(BaseAdapter[Task]):

    # --- Project V2 Operations (NEW) ---

    async def project_list(
        self,
        scope: ProjectScope | None = None,
        state: ProjectState | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Project]:
        """List GitHub Projects V2.

        Maps to:
        - organization(login).projectsV2 (if scope == ORGANIZATION)
        - user(login).projectsV2 (if scope == USER)
        - Defaults to org projects based on config

        Implementation:
        1. Check use_projects_v2 config flag
        2. Query organization/user projects via GraphQL
        3. Map ProjectV2 nodes to Project model
        4. Filter by state if provided
        5. Handle pagination with cursors
        """
        pass

    async def project_get(self, project_id: str) -> Project | None:
        """Get GitHub ProjectV2 by ID or number.

        Accepts:
        - Node ID: "PVT_kwDOABcdefgh" (direct lookup)
        - Project number: "5" (requires owner context)

        Implementation:
        1. Detect ID format (node ID vs number)
        2. Query via node(id) or organization.projectV2(number)
        3. Get project metadata + item counts
        4. Map to Project model
        """
        pass

    async def project_create(
        self,
        name: str,
        description: str | None = None,
        state: ProjectState = ProjectState.PLANNED,
        target_date: datetime | None = None,
        **kwargs: Any,
    ) -> Project:
        """Create new GitHub ProjectV2.

        GraphQL Mutation:
        - createProjectV2(input: {ownerId, title})
        - Returns: ProjectV2 with id, number, url

        Implementation:
        1. Get owner ID (org or user)
        2. Execute createProjectV2 mutation
        3. Map result to Project model
        4. Optionally set custom fields (description via readme)
        """
        pass

    async def project_get_issues(
        self, project_id: str, state: TicketState | None = None
    ) -> list[Task]:
        """Get issues in GitHub ProjectV2.

        GraphQL Query:
        - node(id).items(first: 100) { content { ... on Issue } }

        Implementation:
        1. Query project items via GET_PROJECT_ITEMS
        2. Filter by content type (ISSUE only, skip PR/DRAFT_ISSUE)
        3. Map Issue nodes to Task models
        4. Filter by state if provided
        """
        pass

    async def project_add_issue(
        self, project_id: str, issue_id: str
    ) -> bool:
        """Add issue to GitHub ProjectV2.

        GraphQL Mutation:
        - addProjectV2ItemById(input: {projectId, contentId})

        Implementation:
        1. Get issue node ID from issue_id
        2. Execute addProjectV2ItemById mutation
        3. Return True if successful (idempotent)

        Note: GitHub requires node ID, not issue number
        """
        pass

    async def project_remove_issue(
        self, project_id: str, issue_id: str
    ) -> bool:
        """Remove issue from GitHub ProjectV2.

        GraphQL Mutation:
        - deleteProjectV2Item(input: {projectId, itemId})

        Implementation:
        1. Query project items to find itemId for issue
        2. Execute deleteProjectV2Item mutation
        3. Return True if successful

        Note: Requires project item ID, not issue ID
        """
        pass
```

**Priority 2: Statistics and Updates**

```python
    async def project_update(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        state: ProjectState | None = None,
        **kwargs: Any,
    ) -> Project | None:
        """Update GitHub ProjectV2 metadata.

        GraphQL Mutation:
        - updateProjectV2(input: {projectId, title, shortDescription, closed})

        Implementation:
        1. Map ProjectState to closed boolean
        2. Execute updateProjectV2 mutation
        3. Return updated Project model
        """
        pass

    async def project_delete(self, project_id: str) -> bool:
        """Delete GitHub ProjectV2.

        GraphQL Mutation:
        - deleteProjectV2(input: {projectId})

        Implementation:
        1. Execute deleteProjectV2 mutation
        2. Return True if successful

        Warning: Permanent deletion, no archive option
        """
        pass

    async def project_get_statistics(
        self, project_id: str
    ) -> ProjectStatistics:
        """Calculate GitHub ProjectV2 statistics.

        Implementation:
        1. Get all project items
        2. Count by state (open, in_progress, done, etc.)
        3. Calculate progress percentage
        4. Return ProjectStatistics model

        Note: GitHub doesn't provide aggregated stats, must calculate
        """
        pass
```

---

### 3.2 Required GraphQL Queries

**Add to `queries.py`:**

```python
# --- Projects V2 Core Queries (NEW) ---

PROJECT_V2_FRAGMENT = """
    fragment ProjectV2Fields on ProjectV2 {
        id
        number
        title
        shortDescription
        readme
        public
        closed
        url
        createdAt
        updatedAt
        owner {
            ... on Organization { login, id }
            ... on User { login, id }
        }
    }
"""

LIST_ORG_PROJECTS_V2 = PROJECT_V2_FRAGMENT + """
    query ListOrgProjects($org: String!, $first: Int!, $after: String) {
        organization(login: $org) {
            projectsV2(first: $first, after: $after, orderBy: {field: UPDATED_AT, direction: DESC}) {
                totalCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ...ProjectV2Fields
                }
            }
        }
    }
"""

GET_PROJECT_V2_BY_NUMBER = PROJECT_V2_FRAGMENT + """
    query GetProjectByNumber($org: String!, $number: Int!) {
        organization(login: $org) {
            projectV2(number: $number) {
                ...ProjectV2Fields
                items {
                    totalCount
                }
            }
        }
    }
"""

GET_PROJECT_V2_BY_ID = PROJECT_V2_FRAGMENT + """
    query GetProjectById($projectId: ID!) {
        node(id: $projectId) {
            ... on ProjectV2 {
                ...ProjectV2Fields
                items {
                    totalCount
                }
            }
        }
    }
"""

# Mutations

CREATE_PROJECT_V2 = """
    mutation CreateProject($ownerId: ID!, $title: String!) {
        createProjectV2(input: {
            ownerId: $ownerId
            title: $title
        }) {
            projectV2 {
                id
                number
                title
                url
            }
        }
    }
"""

UPDATE_PROJECT_V2 = """
    mutation UpdateProject(
        $projectId: ID!,
        $title: String,
        $shortDescription: String,
        $public: Boolean,
        $closed: Boolean
    ) {
        updateProjectV2(input: {
            projectId: $projectId
            title: $title
            shortDescription: $shortDescription
            public: $public
            closed: $closed
        }) {
            projectV2 {
                id
                title
                shortDescription
                public
                closed
            }
        }
    }
"""

DELETE_PROJECT_V2 = """
    mutation DeleteProject($projectId: ID!) {
        deleteProjectV2(input: {
            projectId: $projectId
        }) {
            projectV2 {
                id
            }
        }
    }
"""

ADD_ISSUE_TO_PROJECT_V2 = """
    mutation AddIssueToProject($projectId: ID!, $contentId: ID!) {
        addProjectV2ItemById(input: {
            projectId: $projectId
            contentId: $contentId
        }) {
            item {
                id
                content {
                    ... on Issue {
                        number
                        title
                    }
                }
            }
        }
    }
"""

REMOVE_ISSUE_FROM_PROJECT_V2 = """
    mutation RemoveIssueFromProject($projectId: ID!, $itemId: ID!) {
        deleteProjectV2Item(input: {
            projectId: $projectId
            itemId: $itemId
        }) {
            deletedItemId
        }
    }
"""
```

---

### 3.3 Required Mapper Functions

**Add to `mappers.py`:**

```python
def map_github_projectv2_to_project(
    project_data: dict[str, Any],
    platform: str = "github"
) -> Project:
    """Convert GitHub ProjectV2 GraphQL response to Project model.

    Args:
        project_data: ProjectV2 node from GraphQL response
        platform: Platform identifier (default: "github")

    Returns:
        Project model with mapped fields

    Example GraphQL Response:
        {
            "id": "PVT_kwDOABcdefgh",
            "number": 5,
            "title": "Product Roadmap",
            "shortDescription": "Q4 2025 roadmap",
            "readme": "## Overview\n...",
            "public": true,
            "closed": false,
            "url": "https://github.com/orgs/my-org/projects/5",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-12-05T12:00:00Z",
            "owner": {
                "login": "my-org",
                "id": "MDEyOk9yZ2FuaXphdGlvbjEyMzQ1"
            },
            "items": {
                "totalCount": 42
            }
        }
    """
    from ...core.models import (
        Project,
        ProjectScope,
        ProjectState,
        ProjectVisibility,
    )

    # Determine scope from owner type
    owner_type = project_data.get("owner", {}).get("__typename", "Organization")
    scope = ProjectScope.ORGANIZATION if owner_type == "Organization" else ProjectScope.USER

    # Map closed boolean to ProjectState
    state = ProjectState.COMPLETED if project_data.get("closed") else ProjectState.ACTIVE

    # Map public boolean to ProjectVisibility
    visibility = ProjectVisibility.PUBLIC if project_data.get("public") else ProjectVisibility.PRIVATE

    return Project(
        id=project_data["id"],
        platform=platform,
        platform_id=str(project_data["number"]),
        scope=scope,
        name=project_data["title"],
        description=project_data.get("shortDescription") or project_data.get("readme"),
        state=state,
        visibility=visibility,
        url=project_data.get("url"),
        created_at=project_data.get("createdAt"),
        updated_at=project_data.get("updatedAt"),
        owner_id=project_data.get("owner", {}).get("id"),
        owner_name=project_data.get("owner", {}).get("login"),
        issue_count=project_data.get("items", {}).get("totalCount"),
        extra_data={
            "number": project_data["number"],
            "owner_login": project_data.get("owner", {}).get("login"),
            "owner_type": owner_type,
            "readme": project_data.get("readme"),
        }
    )


def calculate_project_statistics(
    project: Project,
    issues: list[Task]
) -> ProjectStatistics:
    """Calculate ProjectStatistics from Project and its issues.

    Args:
        project: Project model
        issues: List of issues in the project

    Returns:
        ProjectStatistics with calculated metrics
    """
    from ...core.models import ProjectStatistics, TicketState

    total = len(issues)
    completed = sum(1 for issue in issues if issue.state == TicketState.DONE)
    in_progress = sum(1 for issue in issues if issue.state == TicketState.IN_PROGRESS)
    open_issues = sum(1 for issue in issues if issue.state == TicketState.OPEN)
    blocked = sum(1 for issue in issues if issue.state == TicketState.BLOCKED)

    progress_pct = (completed / total * 100) if total > 0 else 0.0

    return ProjectStatistics(
        project_id=project.id,
        total_issues=total,
        completed_issues=completed,
        in_progress_issues=in_progress,
        open_issues=open_issues,
        blocked_issues=blocked,
        progress_percentage=progress_pct,
    )
```

---

### 3.4 Configuration Requirements

**Update `.env.local` / config:**

```bash
# GitHub Projects V2 Configuration
GITHUB_USE_PROJECTS_V2=true           # Enable Projects V2 (default: false)
GITHUB_OWNER_TYPE=organization        # "organization" or "user" (default: org)
GITHUB_OWNER=my-org                   # Org or user login (required)

# GitHub Repository (existing, for issues)
GITHUB_REPO=my-repo                   # Repository name (required)
GITHUB_TOKEN=ghp_xxxxx                # PAT with repo + project scopes (required)
```

**Required Token Scopes:**
- `repo` (for issues, PRs)
- `project` (read/write Projects V2)
- `read:project` (minimum for read-only)

---

## 4. Implementation Challenges and Solutions

### Challenge 1: Node ID vs Number Confusion

**Problem**: GitHub ProjectV2 uses:
- **Node ID**: `PVT_kwDOABcdefgh` (global, works everywhere)
- **Project Number**: `5` (requires owner context)

**Solution**:
```python
async def project_get(self, project_id: str) -> Project | None:
    """Auto-detect ID format and query appropriately."""

    if project_id.startswith("PVT_"):
        # Use node(id) query
        query = GET_PROJECT_V2_BY_ID
        variables = {"projectId": project_id}
    else:
        # Use organization.projectV2(number) query
        query = GET_PROJECT_V2_BY_NUMBER
        variables = {"org": self.owner, "number": int(project_id)}

    result = await self._graphql_request(query, variables)
    # ...
```

---

### Challenge 2: Owner Context Required

**Problem**: All ProjectV2 queries require organization/user login.

**Solution**:
```python
def __init__(self, config: dict[str, Any]):
    # ...existing code...

    # Get owner type (org or user)
    self.owner_type = config.get("github_owner_type", "organization")

    # Validate owner is set
    if self.use_projects_v2 and not self.owner:
        raise ValueError(
            "GitHub Projects V2 requires 'github_owner' configuration. "
            "Set GITHUB_OWNER in .env.local or config."
        )
```

---

### Challenge 3: Item ID vs Issue ID Distinction

**Problem**: ProjectV2 items have separate IDs from their underlying issues.

**Solution**: Maintain internal mapping:
```python
async def _get_project_item_id(
    self, project_id: str, issue_number: int
) -> str | None:
    """Find project item ID for an issue.

    Required for removing issues from projects.
    """
    query = GET_PROJECT_ITEMS
    variables = {"projectId": project_id, "first": 100, "after": None}

    result = await self._graphql_request(query, variables)
    items = result["node"]["items"]["nodes"]

    for item in items:
        if item["content"]["number"] == issue_number:
            return item["id"]

    return None
```

---

### Challenge 4: Custom Fields Management

**Problem**: ProjectV2 custom fields require dynamic field resolution.

**Out of Scope for Phase 2**: Custom fields are advanced feature.

**Phase 3 Enhancement**: Add field introspection and value updates.

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Test file:** `tests/adapters/github/test_github_projectsv2.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp_ticketer.adapters.github import GitHubAdapter
from mcp_ticketer.core.models import Project, ProjectState, ProjectScope

@pytest.fixture
def github_adapter():
    """Create GitHub adapter with Projects V2 enabled."""
    config = {
        "token": "ghp_test_token",
        "owner": "test-org",
        "repo": "test-repo",
        "use_projects_v2": True,
        "github_owner_type": "organization"
    }
    return GitHubAdapter(config)


@pytest.mark.asyncio
async def test_project_list_organization(github_adapter, mocker):
    """Test listing organization projects."""

    # Mock GraphQL response
    mock_response = {
        "organization": {
            "projectsV2": {
                "totalCount": 2,
                "nodes": [
                    {
                        "id": "PVT_kwDOABcdefgh",
                        "number": 5,
                        "title": "Product Roadmap",
                        "shortDescription": "Q4 2025",
                        "public": True,
                        "closed": False,
                        "url": "https://github.com/orgs/test-org/projects/5",
                        "createdAt": "2025-01-01T00:00:00Z",
                        "updatedAt": "2025-12-05T12:00:00Z",
                        "owner": {"login": "test-org", "id": "ORG123"}
                    }
                ]
            }
        }
    }

    mocker.patch.object(
        github_adapter,
        "_graphql_request",
        return_value=mock_response
    )

    # Execute
    projects = await github_adapter.project_list(limit=10)

    # Assertions
    assert len(projects) == 1
    assert projects[0].platform == "github"
    assert projects[0].scope == ProjectScope.ORGANIZATION
    assert projects[0].name == "Product Roadmap"
    assert projects[0].state == ProjectState.ACTIVE
    assert projects[0].extra_data["number"] == 5


@pytest.mark.asyncio
async def test_project_get_by_node_id(github_adapter, mocker):
    """Test getting project by node ID."""

    mock_response = {
        "node": {
            "id": "PVT_kwDOABcdefgh",
            "number": 5,
            "title": "Test Project",
            "closed": False,
            # ... other fields ...
        }
    }

    mocker.patch.object(
        github_adapter,
        "_graphql_request",
        return_value=mock_response
    )

    project = await github_adapter.project_get("PVT_kwDOABcdefgh")

    assert project is not None
    assert project.id == "PVT_kwDOABcdefgh"
    assert project.name == "Test Project"


@pytest.mark.asyncio
async def test_project_create(github_adapter, mocker):
    """Test creating new project."""

    # Mock owner ID lookup
    mocker.patch.object(
        github_adapter,
        "_get_owner_id",
        return_value="ORG123"
    )

    # Mock project creation
    mock_response = {
        "createProjectV2": {
            "projectV2": {
                "id": "PVT_new123",
                "number": 6,
                "title": "New Project",
                "url": "https://github.com/orgs/test-org/projects/6"
            }
        }
    }

    mocker.patch.object(
        github_adapter,
        "_graphql_request",
        return_value=mock_response
    )

    project = await github_adapter.project_create(
        name="New Project",
        description="Test project"
    )

    assert project.id == "PVT_new123"
    assert project.name == "New Project"
    assert project.extra_data["number"] == 6
```

---

### 5.2 Integration Tests

**Test against real GitHub API:**

```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("GITHUB_TOKEN"), reason="No GitHub token")
@pytest.mark.asyncio
async def test_project_crud_lifecycle():
    """Test full CRUD lifecycle with real API."""

    config = {
        "token": os.getenv("GITHUB_TOKEN"),
        "owner": os.getenv("GITHUB_OWNER"),
        "repo": os.getenv("GITHUB_REPO"),
        "use_projects_v2": True,
    }

    adapter = GitHubAdapter(config)

    try:
        # Create
        project = await adapter.project_create(
            name="Integration Test Project",
            description="Testing ProjectV2 API"
        )
        assert project.id is not None
        project_id = project.id

        # Read
        fetched = await adapter.project_get(project_id)
        assert fetched.name == "Integration Test Project"

        # Update
        updated = await adapter.project_update(
            project_id,
            name="Updated Test Project"
        )
        assert updated.name == "Updated Test Project"

        # List
        projects = await adapter.project_list(limit=10)
        assert any(p.id == project_id for p in projects)

    finally:
        # Cleanup: Delete test project
        if project_id:
            await adapter.project_delete(project_id)
```

---

## 6. Migration Path and Backwards Compatibility

### 6.1 Dual Support Strategy

**Keep both Epic and Project APIs working:**

```python
# Epic API (existing, unchanged)
epic = await adapter.get_epic("milestone-123")  # Works with Milestones
issue = await adapter.create_issue(title="Fix bug", epic_id="milestone-123")

# Project API (new, Projects V2)
project = await adapter.project_get("PVT_kwDOABcdefgh")  # Works with ProjectV2
await adapter.project_add_issue(project.id, issue.id)
```

**Configuration determines behavior:**

```python
# .env.local
GITHUB_USE_PROJECTS_V2=false  # Use Milestones (default, backwards compatible)
GITHUB_USE_PROJECTS_V2=true   # Use Projects V2 (new feature)
```

---

### 6.2 Deprecation Timeline (Future)

**Phase 2** (Current):
- ✅ Implement Projects V2 support
- ✅ Keep Epic/Milestone API unchanged
- ✅ No deprecation warnings

**Phase 3** (6 months later):
- ⚠️ Add deprecation warnings to Epic API
- 📖 Update docs to recommend Projects V2
- 🔧 Provide migration guide

**Phase 4** (12+ months later):
- ❌ Consider removing Epic API (breaking change)
- 📦 Release as next major version (v3.0.0)

---

## 7. Potential Issues and Risks

### Risk 1: GraphQL API Rate Limits

**Issue**: Projects V2 queries can be expensive (5-10 points per query).

**Mitigation**:
- Implement cursor-based pagination (not offset)
- Cache project metadata with TTL (5 minutes)
- Use compact queries (request only needed fields)

---

### Risk 2: Node ID Resolution Complexity

**Issue**: Users expect numeric IDs, GitHub returns node IDs.

**Mitigation**:
- Accept both formats in all methods
- Store `extra_data["number"]` for display
- Document ID format clearly

---

### Risk 3: Owner Context Dependency

**Issue**: All queries need organization/user login.

**Mitigation**:
- Validate `github_owner` in `__init__`
- Provide clear error messages
- Auto-detect owner from authenticated user (viewer query)

---

### Risk 4: Custom Fields Complexity

**Issue**: Custom fields require dynamic schema introspection.

**Mitigation**:
- **Phase 2**: Ignore custom fields entirely
- **Phase 3**: Add optional custom field support
- Document limitations clearly

---

## 8. Implementation Checklist

### Phase 2.1: Core Models and Queries (Week 1)

- [ ] Add ProjectV2 GraphQL queries to `queries.py`
  - [ ] `LIST_ORG_PROJECTS_V2`
  - [ ] `GET_PROJECT_V2_BY_ID`
  - [ ] `GET_PROJECT_V2_BY_NUMBER`
  - [ ] `CREATE_PROJECT_V2`
  - [ ] `UPDATE_PROJECT_V2`
  - [ ] `DELETE_PROJECT_V2`
  - [ ] `ADD_ISSUE_TO_PROJECT_V2`
  - [ ] `REMOVE_ISSUE_FROM_PROJECT_V2`

- [ ] Add mapper functions to `mappers.py`
  - [ ] `map_github_projectv2_to_project()`
  - [ ] `calculate_project_statistics()`

- [ ] Add unit tests for queries and mappers
  - [ ] Test ProjectV2 fragment composition
  - [ ] Test mapper with various inputs

---

### Phase 2.2: Adapter Implementation (Week 2)

- [ ] Implement `project_list()` in `GitHubAdapter`
  - [ ] Support `scope` filtering (org vs user)
  - [ ] Support `state` filtering
  - [ ] Handle pagination with cursors
  - [ ] Add unit tests

- [ ] Implement `project_get()` in `GitHubAdapter`
  - [ ] Auto-detect node ID vs number
  - [ ] Query via appropriate GraphQL query
  - [ ] Map to Project model
  - [ ] Add unit tests

- [ ] Implement `project_create()` in `GitHubAdapter`
  - [ ] Get owner ID
  - [ ] Execute createProjectV2 mutation
  - [ ] Handle errors gracefully
  - [ ] Add unit tests

---

### Phase 2.3: Issue Operations (Week 3)

- [ ] Implement `project_get_issues()` in `GitHubAdapter`
  - [ ] Query project items
  - [ ] Filter by content type (ISSUE only)
  - [ ] Map to Task models
  - [ ] Add unit tests

- [ ] Implement `project_add_issue()` in `GitHubAdapter`
  - [ ] Convert issue number to node ID
  - [ ] Execute addProjectV2ItemById mutation
  - [ ] Handle idempotency
  - [ ] Add unit tests

- [ ] Implement `project_remove_issue()` in `GitHubAdapter`
  - [ ] Query to find item ID
  - [ ] Execute deleteProjectV2Item mutation
  - [ ] Add unit tests

---

### Phase 2.4: Statistics and Updates (Week 4)

- [ ] Implement `project_update()` in `GitHubAdapter`
  - [ ] Map ProjectState to closed boolean
  - [ ] Execute updateProjectV2 mutation
  - [ ] Add unit tests

- [ ] Implement `project_delete()` in `GitHubAdapter`
  - [ ] Execute deleteProjectV2 mutation
  - [ ] Add unit tests

- [ ] Implement `project_get_statistics()` in `GitHubAdapter`
  - [ ] Get all issues in project
  - [ ] Calculate state counts
  - [ ] Return ProjectStatistics model
  - [ ] Add unit tests

---

### Phase 2.5: Integration Testing and Docs (Week 5)

- [ ] Integration tests with real API
  - [ ] CRUD lifecycle test
  - [ ] Issue operations test
  - [ ] Error handling test

- [ ] Documentation
  - [ ] Update `docs/adapters/github.md` with Projects V2 section
  - [ ] Add configuration guide
  - [ ] Add migration guide from Milestones
  - [ ] Add troubleshooting section

- [ ] Code review and refinement
  - [ ] Ensure error messages are helpful
  - [ ] Validate token scopes
  - [ ] Performance testing

---

## 9. Success Criteria

**Phase 2 is complete when:**

✅ All 9 project methods implemented in `GitHubAdapter`
✅ All GraphQL queries and mappers tested
✅ Integration tests pass with real GitHub API
✅ Configuration documented clearly
✅ Error handling is robust and helpful
✅ Backwards compatibility maintained (Epic API still works)
✅ No breaking changes to existing code

---

## 10. Next Steps for Engineer

**Immediate Actions:**

1. **Review this analysis document** - Ensure understanding of architecture
2. **Set up GitHub test organization** - For integration testing
3. **Create feature branch** - `feature/phase2-github-projects-v2`
4. **Start with queries.py** - Add ProjectV2 GraphQL queries first
5. **Implement incrementally** - One method at a time with tests

**Recommended Order:**

1. Week 1: Queries + Mappers + Unit Tests
2. Week 2: `project_list()` + `project_get()` + `project_create()`
3. Week 3: `project_get_issues()` + `project_add_issue()` + `project_remove_issue()`
4. Week 4: `project_update()` + `project_delete()` + `project_get_statistics()`
5. Week 5: Integration tests + Documentation

---

## 11. References

**Research Documents:**
- [GitHub Projects V2 API Analysis](./github-projects-v2-api-analysis-2025-12-05.md) - Detailed API research
- [Unified Projects Design](./unified-projects-design-2025-12-05.md) - Architecture design
- [Phase 1 Implementation Summary](../phase1-implementation-summary.md) - Core models implementation

**GitHub Documentation:**
- [Projects V2 API Reference](https://docs.github.com/en/graphql/reference/objects#projectv2)
- [Projects V2 Mutations](https://docs.github.com/en/graphql/reference/mutations#project-mutations)
- [GraphQL Explorer](https://docs.github.com/en/graphql/overview/explorer)

---

## Conclusion

**Phase 2 is ready to begin.** The adapter architecture is well-designed for extension, Phase 1 models are complete, and this analysis provides a clear implementation path. The recommended approach (Option 1: Direct Implementation) minimizes risk, maintains backwards compatibility, and delivers GitHub Projects V2 support in ~4-5 weeks.

**Key Decision**: Implement `project_*` methods directly in `GitHubAdapter` using existing GraphQL infrastructure, following the same pattern as `milestone_*` methods.

**No Blockers Identified**: All dependencies resolved, core models committed, adapter interface ready.

