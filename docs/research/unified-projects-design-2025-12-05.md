# Unified Projects Abstraction Design

**Design Date:** 2025-12-05
**Designer:** Claude (Research Agent)
**Project:** mcp-ticketer - Cross-Platform Project Management

---

## Executive Summary

This document defines a **unified "Projects" abstraction** for mcp-ticketer that maps naturally across Linear, JIRA, and GitHub platforms. The design provides a consistent API for project management while respecting platform-specific capabilities and constraints.

**Key Design Principles:**
1. **Platform-agnostic API**: Common interface regardless of backend
2. **Rich metadata preservation**: Platform-specific data accessible via `extra_data`
3. **Graceful degradation**: Unsupported features fail gracefully
4. **Type safety**: Pydantic models with strict validation
5. **Extensibility**: Easy to add new platforms without breaking changes

---

## 1. Unified Project Model

### 1.1 Core Project Model

```python
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ProjectState(str, Enum):
    """Universal project states across platforms.

    Platform Mappings:
    - Linear: PLANNED → planned, ACTIVE → started, COMPLETED → completed, ARCHIVED → canceled
    - GitHub: ACTIVE → open, COMPLETED → closed, ARCHIVED → closed
    - JIRA: ACTIVE → active, COMPLETED → done, ARCHIVED → archived
    """

    PLANNED = "planned"      # Not yet started
    ACTIVE = "active"        # Currently in progress
    PAUSED = "paused"        # Temporarily paused
    COMPLETED = "completed"  # Successfully finished
    ARCHIVED = "archived"    # Closed/archived
    CANCELLED = "cancelled"  # Cancelled/abandoned


class ProjectVisibility(str, Enum):
    """Project visibility/access control.

    Platform Support:
    - Linear: PUBLIC, PRIVATE (team-scoped)
    - GitHub: PUBLIC, PRIVATE (org/user-scoped)
    - JIRA: PUBLIC, PRIVATE (project-scoped permissions)
    """

    PUBLIC = "public"    # Visible to all
    PRIVATE = "private"  # Restricted access
    TEAM = "team"        # Team members only (Linear-specific)


class ProjectScope(str, Enum):
    """Scope of project (where it lives).

    Used to understand project context and multi-repo support.
    """

    USER = "user"              # Personal project (GitHub, Linear)
    TEAM = "team"              # Team project (Linear, JIRA)
    ORGANIZATION = "organization"  # Org-wide (GitHub, JIRA)
    REPOSITORY = "repository"  # Repo-specific (GitHub Milestones fallback)


class Project(BaseModel):
    """Unified project model across all platforms.

    This model provides a consistent interface for project management
    across Linear (Projects), JIRA (Epics), and GitHub (Projects V2).

    The model uses Pydantic for validation and type safety, ensuring
    consistent behavior regardless of the underlying platform.

    Attributes:
        id: Unique platform-specific identifier (UUID for Linear, node ID for GitHub, key for JIRA)
        platform_id: Original ID from platform (preserved for direct API access)
        platform: Source platform ("linear", "github", "jira")
        scope: Where the project lives (user, team, org, repo)

        name: Project name/title (required)
        description: Detailed project description (markdown supported)
        state: Current project state (planned, active, completed, etc.)
        visibility: Access control (public, private, team)

        owner: User/team who owns the project
        lead_id: Project lead/manager user ID
        url: Platform-specific project URL

        # Dates
        start_date: Project start date (optional)
        target_date: Target completion date (optional)
        created_at: When project was created
        updated_at: When project was last modified
        completed_at: When project was completed (if applicable)

        # Progress tracking
        issue_count: Total number of issues in project
        completed_count: Number of completed issues
        in_progress_count: Number of in-progress issues
        progress_percentage: Completion percentage (0-100)

        # Relationships
        child_issues: List of issue IDs belonging to this project
        tags: Labels/tags for categorization

        # Platform-specific data
        extra_data: Dictionary for platform-specific fields not in core model

    Example:
        >>> project = Project(
        ...     id="proj-123",
        ...     platform="linear",
        ...     name="Authentication System Overhaul",
        ...     description="Complete rewrite of auth",
        ...     state=ProjectState.ACTIVE,
        ...     target_date=date(2025, 12, 31)
        ... )
        >>> print(f"{project.name}: {project.progress_percentage}% complete")

    Platform Mapping Examples:
        # Linear Project
        Project(
            id="02d15669-7351-4451-9719-807576c16049",
            platform="linear",
            scope=ProjectScope.TEAM,
            name="Q4 2025 Goals",
            state=ProjectState.ACTIVE,
            visibility=ProjectVisibility.TEAM,
            extra_data={
                "slugId": "q4-2025",
                "icon": "🎯",
                "color": "#4EA7FC"
            }
        )

        # GitHub Projects V2
        Project(
            id="PVT_kwDOABcdefgh",
            platform="github",
            scope=ProjectScope.ORGANIZATION,
            name="Product Roadmap",
            state=ProjectState.ACTIVE,
            visibility=ProjectVisibility.PUBLIC,
            extra_data={
                "number": 5,
                "owner_login": "my-org",
                "owner_type": "Organization"
            }
        )

        # JIRA Epic
        Project(
            id="PROJ-123",
            platform="jira",
            scope=ProjectScope.TEAM,
            name="User Onboarding Flow",
            state=ProjectState.ACTIVE,
            visibility=ProjectVisibility.PRIVATE,
            extra_data={
                "key": "PROJ-123",
                "project_key": "PROJ",
                "epic_link_field": "customfield_10014"
            }
        )
    """

    # Identity
    id: str = Field(..., description="Unique identifier (platform-specific format)")
    platform_id: str = Field(..., description="Original platform ID (for direct API calls)")
    platform: str = Field(..., description="Source platform: linear, github, jira")
    scope: ProjectScope = Field(..., description="Project scope (user, team, org, repo)")

    # Core fields
    name: str = Field(..., min_length=1, description="Project name/title")
    description: str | None = Field(None, description="Detailed description (supports markdown)")
    state: ProjectState = Field(ProjectState.ACTIVE, description="Current project state")
    visibility: ProjectVisibility = Field(ProjectVisibility.PRIVATE, description="Access control")

    # Ownership
    owner: str | None = Field(None, description="Owner user ID or team ID")
    lead_id: str | None = Field(None, description="Project lead/manager user ID")

    # URLs
    url: str | None = Field(None, description="Platform-specific project URL")

    # Dates
    start_date: datetime | None = Field(None, description="Project start date")
    target_date: datetime | None = Field(None, description="Target completion date")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")
    completed_at: datetime | None = Field(None, description="Completion timestamp")

    # Progress tracking
    issue_count: int | None = Field(None, ge=0, description="Total number of issues")
    completed_count: int | None = Field(None, ge=0, description="Number of completed issues")
    in_progress_count: int | None = Field(None, ge=0, description="Number of in-progress issues")
    progress_percentage: float | None = Field(None, ge=0, le=100, description="Completion percentage")

    # Relationships
    child_issues: list[str] = Field(default_factory=list, description="Issue IDs in this project")
    tags: list[str] = Field(default_factory=list, description="Tags/labels for categorization")

    # Platform-specific data
    extra_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific fields and metadata"
    )

    def calculate_progress(self) -> float:
        """Calculate progress percentage from issue counts.

        Returns:
            Progress percentage (0-100), or 0 if no issues

        Example:
            >>> project.issue_count = 10
            >>> project.completed_count = 7
            >>> project.calculate_progress()
            70.0
        """
        if not self.issue_count or self.issue_count == 0:
            return 0.0

        completed = self.completed_count or 0
        return (completed / self.issue_count) * 100

    def is_overdue(self) -> bool:
        """Check if project is past its target date.

        Returns:
            True if target_date is in the past and project not completed

        Example:
            >>> project.target_date = datetime(2024, 1, 1)
            >>> project.state = ProjectState.ACTIVE
            >>> project.is_overdue()
            True
        """
        if not self.target_date:
            return False

        if self.state in [ProjectState.COMPLETED, ProjectState.ARCHIVED, ProjectState.CANCELLED]:
            return False

        return datetime.now() > self.target_date

    def to_epic(self) -> Epic:
        """Convert Project to Epic model for backwards compatibility.

        Returns:
            Epic model with project data mapped to epic fields

        Note:
            This is for backwards compatibility with existing Epic-based APIs.
            New code should use Project model directly.
        """
        from ...core.models import Epic, TicketState

        # Map ProjectState to TicketState
        state_mapping = {
            ProjectState.PLANNED: TicketState.OPEN,
            ProjectState.ACTIVE: TicketState.IN_PROGRESS,
            ProjectState.PAUSED: TicketState.WAITING,
            ProjectState.COMPLETED: TicketState.DONE,
            ProjectState.ARCHIVED: TicketState.CLOSED,
            ProjectState.CANCELLED: TicketState.CLOSED,
        }

        return Epic(
            id=self.id,
            title=self.name,
            description=self.description or "",
            state=state_mapping.get(self.state, TicketState.OPEN),
            child_issues=self.child_issues,
            tags=self.tags,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata={
                "platform": self.platform,
                "project_scope": self.scope.value,
                "project_visibility": self.visibility.value,
                "project_url": self.url,
                "target_date": self.target_date.isoformat() if self.target_date else None,
                **self.extra_data
            }
        )
```

### 1.2 Project Statistics Model

```python
class ProjectStatistics(BaseModel):
    """Detailed statistics for project progress tracking.

    Provides comprehensive metrics for project health and progress monitoring.
    Useful for dashboards, reporting, and project status updates.

    Attributes:
        project_id: ID of the project these stats belong to

        # Issue counts by state
        total_issues: Total number of issues
        open_issues: Issues not yet started
        in_progress_issues: Issues being worked on
        ready_issues: Issues ready for review/testing
        completed_issues: Issues marked as done
        blocked_issues: Issues currently blocked
        cancelled_issues: Issues cancelled/won't do

        # Progress metrics
        completion_percentage: Overall completion (0-100)
        velocity: Average issues completed per time period
        estimated_completion_date: Projected completion based on velocity

        # Time tracking
        total_time_spent: Total time logged (hours)
        average_time_per_issue: Average completion time

        # Health indicators
        health_score: Project health (0-100, higher is better)
        risk_level: LOW, MEDIUM, HIGH, CRITICAL
        blockers_count: Number of blocking issues

    Example:
        >>> stats = ProjectStatistics(
        ...     project_id="proj-123",
        ...     total_issues=50,
        ...     completed_issues=35,
        ...     in_progress_issues=10,
        ...     blocked_issues=2
        ... )
        >>> print(f"Health: {stats.health_score}/100")
        >>> print(f"Risk: {stats.risk_level}")
    """

    project_id: str = Field(..., description="Project identifier")

    # Issue counts by state
    total_issues: int = Field(0, ge=0, description="Total number of issues")
    open_issues: int = Field(0, ge=0, description="Open/not started issues")
    in_progress_issues: int = Field(0, ge=0, description="Issues being worked on")
    ready_issues: int = Field(0, ge=0, description="Issues ready for review")
    completed_issues: int = Field(0, ge=0, description="Completed issues")
    blocked_issues: int = Field(0, ge=0, description="Blocked issues")
    cancelled_issues: int = Field(0, ge=0, description="Cancelled issues")

    # Progress metrics
    completion_percentage: float = Field(0.0, ge=0, le=100, description="Completion %")
    velocity: float | None = Field(None, description="Issues completed per sprint/week")
    estimated_completion_date: datetime | None = Field(None, description="Projected completion")

    # Time tracking (optional, platform-dependent)
    total_time_spent: float | None = Field(None, ge=0, description="Total hours logged")
    average_time_per_issue: float | None = Field(None, ge=0, description="Average hours per issue")

    # Health indicators
    health_score: int = Field(100, ge=0, le=100, description="Project health (0-100)")
    risk_level: str = Field("LOW", description="LOW, MEDIUM, HIGH, CRITICAL")
    blockers_count: int = Field(0, ge=0, description="Number of blocking issues")

    # Metadata
    last_calculated: datetime = Field(default_factory=datetime.now, description="When stats were calculated")
```

---

## 2. Platform Mapping Documentation

### 2.1 Concept Mapping Table

| Unified Concept | Linear | JIRA | GitHub (Projects V2) | GitHub (Milestones) |
|-----------------|--------|------|---------------------|---------------------|
| **Project** | Project | Epic | ProjectV2 | Milestone (fallback) |
| **Project ID** | UUID | Epic Key | Node ID (PVT_*) | Number |
| **Project Name** | name | summary | title | title |
| **Project Description** | description | description | shortDescription/readme | description |
| **Project State** | state (planned/started/completed/canceled) | status | closed (boolean) | state (open/closed) |
| **Project Visibility** | team-scoped (no public option) | project permissions | public (boolean) | repo visibility |
| **Project Scope** | Team | Project/Board | User/Organization | Repository |
| **Project URL** | Linear app URL | JIRA web URL | GitHub project URL | Milestone URL |
| **Child Issues** | project.issues | epic.issues | project.items | milestone.issues |
| **Progress Tracking** | progress, completedIssueCount | aggregated from issues | custom fields | issue counts |
| **Target Date** | targetDate | dueDate | custom date field | dueOn |
| **Start Date** | startDate | startDate | custom date field | N/A |
| **Project Lead** | lead | epicOwner | N/A (use custom field) | N/A |

### 2.2 State Mapping

#### Linear → Unified

| Linear State | Unified State | Notes |
|--------------|---------------|-------|
| `planned` | `PLANNED` | Project planned but not started |
| `started` | `ACTIVE` | Project in progress |
| `paused` | `PAUSED` | Temporarily paused (if supported) |
| `completed` | `COMPLETED` | Successfully finished |
| `canceled` | `CANCELLED` | Cancelled/abandoned |

#### JIRA → Unified

| JIRA Status | Unified State | Notes |
|-------------|---------------|-------|
| `To Do`, `Backlog` | `PLANNED` | Not yet started |
| `In Progress`, `In Development` | `ACTIVE` | Currently being worked on |
| `On Hold`, `Waiting` | `PAUSED` | Temporarily paused |
| `Done`, `Completed` | `COMPLETED` | Successfully finished |
| `Closed`, `Resolved` | `ARCHIVED` | Closed/archived |
| `Cancelled`, `Won't Do` | `CANCELLED` | Cancelled |

#### GitHub Projects V2 → Unified

| GitHub State | Unified State | Notes |
|--------------|---------------|-------|
| `closed: false` | `ACTIVE` | Open project (default) |
| `closed: true` | `COMPLETED` | Closed project |
| Custom "Status" field: "Planned" | `PLANNED` | Via custom single-select field |
| Custom "Status" field: "Paused" | `PAUSED` | Via custom single-select field |
| Custom "Status" field: "Archived" | `ARCHIVED` | Via custom single-select field |

#### GitHub Milestones → Unified (Fallback)

| Milestone State | Unified State | Notes |
|-----------------|---------------|-------|
| `open` | `ACTIVE` | Open milestone |
| `closed` | `COMPLETED` | Closed milestone |

### 2.3 Visibility Mapping

| Platform | Public | Private | Team |
|----------|--------|---------|------|
| **Linear** | ❌ No public projects | ✅ Default (team-scoped) | ✅ Team-only access |
| **GitHub Projects V2** | ✅ `public: true` | ✅ `public: false` | ⚠️ Map to `private` |
| **JIRA** | ✅ Project permissions | ✅ Restricted permissions | ✅ Team/group permissions |

---

## 3. Adapter Interface Definition

### 3.1 Base Adapter Project Operations

All adapters implementing project support must implement the `ProjectOperations` protocol:

```python
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProjectOperations(Protocol):
    """Protocol defining project operations that all adapters must support.

    This protocol ensures consistent project management across platforms.
    Adapters can implement this protocol to provide project functionality.

    Example:
        >>> class MyAdapter(BaseAdapter, ProjectOperations):
        ...     async def list_projects(self, **filters) -> list[Project]:
        ...         # Implementation
        ...         pass
    """

    async def list_projects(
        self,
        limit: int = 20,
        offset: int = 0,
        state: ProjectState | None = None,
        **filters: Any
    ) -> list[Project]:
        """List projects with optional filtering.

        Args:
            limit: Maximum number of projects to return
            offset: Pagination offset
            state: Filter by project state (PLANNED, ACTIVE, etc.)
            **filters: Platform-specific filters

        Returns:
            List of Project objects

        Example:
            >>> projects = await adapter.list_projects(
            ...     limit=50,
            ...     state=ProjectState.ACTIVE
            ... )
        """
        ...

    async def get_project(self, project_id: str) -> Project | None:
        """Get project by ID.

        Args:
            project_id: Project identifier (platform-specific format)

        Returns:
            Project object or None if not found

        Example:
            >>> project = await adapter.get_project("proj-123")
            >>> if project:
            ...     print(f"Project: {project.name}")
        """
        ...

    async def create_project(
        self,
        name: str,
        description: str | None = None,
        state: ProjectState = ProjectState.PLANNED,
        visibility: ProjectVisibility = ProjectVisibility.PRIVATE,
        **kwargs: Any
    ) -> Project:
        """Create new project.

        Args:
            name: Project name/title (required)
            description: Optional project description
            state: Initial project state (default: PLANNED)
            visibility: Access control (default: PRIVATE)
            **kwargs: Platform-specific options

        Returns:
            Created Project object

        Raises:
            ValueError: If required fields missing or invalid

        Example:
            >>> project = await adapter.create_project(
            ...     name="Q1 2025 Goals",
            ...     description="Strategic goals for Q1",
            ...     visibility=ProjectVisibility.TEAM,
            ...     target_date=date(2025, 3, 31)
            ... )
        """
        ...

    async def update_project(
        self,
        project_id: str,
        **updates: Any
    ) -> Project | None:
        """Update project metadata.

        Args:
            project_id: Project identifier
            **updates: Fields to update (name, description, state, etc.)

        Returns:
            Updated Project object or None if not found

        Example:
            >>> updated = await adapter.update_project(
            ...     "proj-123",
            ...     state=ProjectState.COMPLETED,
            ...     completed_at=datetime.now()
            ... )
        """
        ...

    async def delete_project(self, project_id: str) -> bool:
        """Delete or archive project.

        Args:
            project_id: Project identifier

        Returns:
            True if successfully deleted, False otherwise

        Note:
            Some platforms may archive instead of delete.

        Example:
            >>> success = await adapter.delete_project("proj-123")
            >>> if success:
            ...     print("Project deleted")
        """
        ...

    async def get_project_issues(
        self,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
        state: TicketState | None = None
    ) -> list[Task]:
        """Get all issues in project.

        Args:
            project_id: Project identifier
            limit: Maximum issues to return
            offset: Pagination offset
            state: Filter by issue state (optional)

        Returns:
            List of Task objects

        Example:
            >>> issues = await adapter.get_project_issues(
            ...     "proj-123",
            ...     state=TicketState.IN_PROGRESS
            ... )
        """
        ...

    async def add_issue_to_project(
        self,
        project_id: str,
        issue_id: str
    ) -> bool:
        """Add issue to project.

        Args:
            project_id: Project identifier
            issue_id: Issue identifier

        Returns:
            True if successfully added, False otherwise

        Note:
            Idempotent - returns True if issue already in project

        Example:
            >>> success = await adapter.add_issue_to_project(
            ...     "proj-123",
            ...     "ISSUE-456"
            ... )
        """
        ...

    async def remove_issue_from_project(
        self,
        project_id: str,
        issue_id: str
    ) -> bool:
        """Remove issue from project.

        Args:
            project_id: Project identifier
            issue_id: Issue identifier

        Returns:
            True if successfully removed, False otherwise

        Example:
            >>> success = await adapter.remove_issue_from_project(
            ...     "proj-123",
            ...     "ISSUE-456"
            ... )
        """
        ...

    async def get_project_statistics(
        self,
        project_id: str
    ) -> ProjectStatistics:
        """Get detailed project statistics.

        Args:
            project_id: Project identifier

        Returns:
            ProjectStatistics object with counts, progress, health metrics

        Example:
            >>> stats = await adapter.get_project_statistics("proj-123")
            >>> print(f"Completion: {stats.completion_percentage}%")
            >>> print(f"Blocked: {stats.blocked_issues}")
        """
        ...
```

### 3.2 Optional Advanced Operations

```python
class AdvancedProjectOperations(Protocol):
    """Optional advanced project operations for platforms that support them."""

    async def archive_project(self, project_id: str) -> bool:
        """Archive project (soft delete).

        Preserves project data but marks as archived.
        Supported by: Linear, JIRA
        Not supported by: GitHub (use delete_project instead)
        """
        ...

    async def restore_project(self, project_id: str) -> Project | None:
        """Restore archived project.

        Supported by: Linear, JIRA
        Not supported by: GitHub
        """
        ...

    async def move_project(
        self,
        project_id: str,
        target_team_id: str
    ) -> Project | None:
        """Move project to different team/organization.

        Supported by: Linear, JIRA
        Not supported by: GitHub (projects are org/user-scoped)
        """
        ...

    async def get_project_roadmap(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """Get project roadmap/timeline.

        Returns timeline view with milestones, sprints, deliverables.
        Supported by: Linear, JIRA (with Advanced Roadmaps)
        Not supported by: GitHub (no native roadmap feature)
        """
        ...
```

---

## 4. Platform-Specific Implementation Notes

### 4.1 Linear Adapter

**Strengths:**
- Native Project entity with rich metadata
- Team-scoped projects with clear ownership
- Built-in progress tracking
- First-class project support in GraphQL API

**Implementation:**
```python
# Linear projects map 1:1 to unified Project model
async def get_project(self, project_id: str) -> Project | None:
    """Get Linear project by ID."""
    query = gql("""
    query GetProject($id: String!) {
      project(id: $id) {
        id
        name
        description
        state
        startDate
        targetDate
        progress
        completedIssueCount
        issueCount
        lead { id, name }
        teams { nodes { id, name } }
        url
      }
    }
    """)

    result = await self.client.execute(query, {"id": project_id})
    if not result or "project" not in result:
        return None

    project_data = result["project"]

    return Project(
        id=project_data["id"],
        platform_id=project_data["id"],
        platform="linear",
        scope=ProjectScope.TEAM,
        name=project_data["name"],
        description=project_data.get("description"),
        state=self._map_linear_state(project_data["state"]),
        visibility=ProjectVisibility.TEAM,  # Linear projects are team-scoped
        lead_id=project_data.get("lead", {}).get("id"),
        url=project_data.get("url"),
        start_date=project_data.get("startDate"),
        target_date=project_data.get("targetDate"),
        issue_count=project_data.get("issueCount"),
        completed_count=project_data.get("completedIssueCount"),
        progress_percentage=project_data.get("progress"),
        extra_data={
            "teams": [team["id"] for team in project_data.get("teams", {}).get("nodes", [])]
        }
    )
```

### 4.2 GitHub Adapter (Projects V2)

**Strengths:**
- Rich custom field system
- Cross-repository support
- Public/private visibility control
- Powerful GraphQL API

**Challenges:**
- Node ID vs number confusion
- Requires owner context (org/user login)
- Custom fields need dynamic resolution

**Implementation:**
```python
async def get_project(self, project_id: str) -> Project | None:
    """Get GitHub Projects V2 project by ID."""

    # Determine if project_id is node ID or number
    if project_id.startswith("PVT_"):
        # Direct node ID lookup
        query = """
        query GetProject($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
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
                ... on Organization { login }
                ... on User { login }
              }
            }
          }
        }
        """
        variables = {"projectId": project_id}
    else:
        # Project number lookup (requires owner)
        query = """
        query GetProject($org: String!, $number: Int!) {
          organization(login: $org) {
            projectV2(number: $number) {
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
            }
          }
        }
        """
        variables = {"org": self.owner, "number": int(project_id)}

    result = await self._graphql_request(query, variables)

    # Extract project data
    project_data = result.get("node") or result.get("organization", {}).get("projectV2")
    if not project_data:
        return None

    # Get item counts
    items_query = """
    query GetItemCounts($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          items {
            totalCount
          }
        }
      }
    }
    """
    items_result = await self._graphql_request(items_query, {"projectId": project_data["id"]})
    total_items = items_result["node"]["items"]["totalCount"]

    return Project(
        id=project_data["id"],
        platform_id=str(project_data["number"]),
        platform="github",
        scope=ProjectScope.ORGANIZATION,  # Detect from owner type
        name=project_data["title"],
        description=project_data.get("shortDescription") or project_data.get("readme"),
        state=ProjectState.COMPLETED if project_data.get("closed") else ProjectState.ACTIVE,
        visibility=ProjectVisibility.PUBLIC if project_data.get("public") else ProjectVisibility.PRIVATE,
        url=project_data.get("url"),
        created_at=project_data.get("createdAt"),
        updated_at=project_data.get("updatedAt"),
        issue_count=total_items,
        extra_data={
            "number": project_data["number"],
            "owner_login": project_data.get("owner", {}).get("login"),
            "readme": project_data.get("readme")
        }
    )
```

### 4.3 GitHub Adapter (Milestones Fallback)

**For backwards compatibility:**

```python
async def get_project_milestone(self, milestone_number: int) -> Project | None:
    """Get GitHub milestone as Project (fallback/legacy)."""

    response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
    )

    if response.status_code == 404:
        return None

    response.raise_for_status()
    milestone = response.json()

    # Get issues in milestone for counts
    issues_response = await self.client.get(
        f"/repos/{self.owner}/{self.repo}/issues",
        params={"milestone": str(milestone_number), "state": "all"}
    )
    issues = issues_response.json()
    closed_count = sum(1 for issue in issues if issue["state"] == "closed")

    return Project(
        id=f"milestone-{milestone['number']}",
        platform_id=str(milestone["number"]),
        platform="github",
        scope=ProjectScope.REPOSITORY,  # Milestones are repo-scoped
        name=milestone["title"],
        description=milestone.get("description"),
        state=ProjectState.COMPLETED if milestone["state"] == "closed" else ProjectState.ACTIVE,
        visibility=ProjectVisibility.PRIVATE,  # Inherit repo visibility
        url=milestone["html_url"],
        target_date=milestone.get("due_on"),
        created_at=milestone["created_at"],
        updated_at=milestone["updated_at"],
        completed_at=milestone.get("closed_at"),
        issue_count=milestone.get("open_issues", 0) + milestone.get("closed_issues", 0),
        completed_count=closed_count,
        extra_data={
            "number": milestone["number"],
            "open_issues": milestone.get("open_issues"),
            "closed_issues": milestone.get("closed_issues"),
            "creator": milestone.get("creator", {}).get("login")
        }
    )
```

### 4.4 JIRA Adapter

**Strengths:**
- Mature epic/story hierarchy
- Rich field customization
- Powerful JQL queries
- Enterprise-grade permissions

**Challenges:**
- Epic field varies by instance (customfield_10014, etc.)
- REST API pagination complexity
- Complex permission models

**Implementation:**
```python
async def get_project(self, project_id: str) -> Project | None:
    """Get JIRA Epic as Project."""

    # Get epic details
    response = await self.client.get(f"/rest/api/3/issue/{project_id}")

    if response.status_code == 404:
        return None

    response.raise_for_status()
    epic = response.json()

    # Verify it's an epic
    if epic.get("fields", {}).get("issuetype", {}).get("name") != "Epic":
        return None

    # Get epic's child issues via JQL
    jql = f'"Epic Link" = {project_id}'
    search_response = await self.client.get(
        "/rest/api/3/search",
        params={"jql": jql, "maxResults": 0}  # Just get count
    )
    search_result = search_response.json()
    total_issues = search_result.get("total", 0)

    # Count completed issues
    jql_completed = f'"Epic Link" = {project_id} AND status in (Done, Closed, Resolved)'
    completed_response = await self.client.get(
        "/rest/api/3/search",
        params={"jql": jql_completed, "maxResults": 0}
    )
    completed_count = completed_response.json().get("total", 0)

    fields = epic["fields"]

    return Project(
        id=epic["key"],
        platform_id=epic["id"],
        platform="jira",
        scope=ProjectScope.TEAM,
        name=fields.get("summary", ""),
        description=fields.get("description"),
        state=self._map_jira_status(fields.get("status", {}).get("name")),
        visibility=ProjectVisibility.PRIVATE,  # Determine from project permissions
        url=f"{self.base_url}/browse/{epic['key']}",
        target_date=fields.get("duedate"),
        created_at=fields.get("created"),
        updated_at=fields.get("updated"),
        issue_count=total_issues,
        completed_count=completed_count,
        extra_data={
            "project_key": epic["fields"].get("project", {}).get("key"),
            "epic_link_field": self.epic_link_field,
            "status_category": fields.get("status", {}).get("statusCategory", {}).get("name")
        }
    )
```

---

## 5. Migration and Backwards Compatibility

### 5.1 Gradual Migration Strategy

**Phase 1: Add Project Support Alongside Epic**
- Implement `ProjectOperations` in all adapters
- Keep existing `Epic` model and methods
- Add `project.to_epic()` conversion method

**Phase 2: Deprecate Epic-centric Methods**
- Mark `create_epic()`, `get_epic()`, etc. as deprecated
- Recommend `create_project()`, `get_project()` instead
- Maintain full backwards compatibility

**Phase 3: Unified API Default**
- New code uses Project by default
- Legacy code continues to work via Epic
- Documentation emphasizes Project model

**Phase 4: Optional Epic Removal**
- After 6-12 months, consider removing Epic entirely
- Provide migration utilities
- Breaking change in next major version

### 5.2 Conversion Utilities

```python
def epic_to_project(epic: Epic, platform: str) -> Project:
    """Convert Epic to Project for unified API.

    Args:
        epic: Epic object to convert
        platform: Source platform (linear, github, jira)

    Returns:
        Project object with epic data

    Example:
        >>> epic = await adapter.get_epic("EPIC-123")
        >>> project = epic_to_project(epic, "jira")
    """
    return Project(
        id=epic.id,
        platform_id=epic.id,
        platform=platform,
        scope=ProjectScope.TEAM,  # Default assumption
        name=epic.title,
        description=epic.description,
        state=_ticket_state_to_project_state(epic.state),
        child_issues=epic.child_issues,
        tags=epic.tags,
        created_at=epic.created_at,
        updated_at=epic.updated_at,
        extra_data=epic.metadata
    )


def _ticket_state_to_project_state(state: TicketState) -> ProjectState:
    """Map TicketState to ProjectState."""
    mapping = {
        TicketState.OPEN: ProjectState.PLANNED,
        TicketState.IN_PROGRESS: ProjectState.ACTIVE,
        TicketState.READY: ProjectState.ACTIVE,
        TicketState.TESTED: ProjectState.ACTIVE,
        TicketState.DONE: ProjectState.COMPLETED,
        TicketState.WAITING: ProjectState.PAUSED,
        TicketState.BLOCKED: ProjectState.PAUSED,
        TicketState.CLOSED: ProjectState.ARCHIVED,
    }
    return mapping.get(state, ProjectState.ACTIVE)
```

---

## 6. Usage Examples

### Example 1: List Active Projects Across Platforms

```python
# Works identically regardless of platform
async def list_active_projects(adapter: BaseAdapter) -> list[Project]:
    """List all active projects."""

    if not isinstance(adapter, ProjectOperations):
        raise TypeError(f"Adapter {adapter} does not support projects")

    projects = await adapter.list_projects(
        state=ProjectState.ACTIVE,
        limit=50
    )

    return sorted(projects, key=lambda p: p.updated_at or datetime.min, reverse=True)
```

### Example 2: Create Project with Issues

```python
async def create_project_with_issues(
    adapter: BaseAdapter,
    name: str,
    description: str,
    issue_ids: list[str]
) -> Project:
    """Create project and add issues to it."""

    # Create project
    project = await adapter.create_project(
        name=name,
        description=description,
        state=ProjectState.ACTIVE
    )

    # Add issues
    for issue_id in issue_ids:
        await adapter.add_issue_to_project(project.id, issue_id)

    # Refresh to get updated counts
    return await adapter.get_project(project.id)
```

### Example 3: Project Health Dashboard

```python
async def get_project_health(adapter: BaseAdapter, project_id: str) -> dict[str, Any]:
    """Get project health metrics."""

    project = await adapter.get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    stats = await adapter.get_project_statistics(project_id)

    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "state": project.state.value,
            "progress": project.progress_percentage or 0
        },
        "health": {
            "score": stats.health_score,
            "risk": stats.risk_level,
            "blockers": stats.blockers_count
        },
        "progress": {
            "total": stats.total_issues,
            "completed": stats.completed_issues,
            "in_progress": stats.in_progress_issues,
            "blocked": stats.blocked_issues
        },
        "timeline": {
            "start_date": project.start_date,
            "target_date": project.target_date,
            "is_overdue": project.is_overdue(),
            "estimated_completion": stats.estimated_completion_date
        }
    }
```

---

## 7. Testing Strategy

### Unit Tests

```python
@pytest.mark.asyncio
async def test_get_project_linear():
    """Test getting Linear project."""
    adapter = LinearAdapter(config)

    project = await adapter.get_project("proj-uuid")

    assert project is not None
    assert project.platform == "linear"
    assert project.scope == ProjectScope.TEAM
    assert isinstance(project.state, ProjectState)


@pytest.mark.asyncio
async def test_get_project_github_projects_v2():
    """Test getting GitHub Projects V2 project."""
    adapter = GitHubAdapter({"use_projects_v2": True, ...})

    project = await adapter.get_project("PVT_kwDOABcdefgh")

    assert project is not None
    assert project.platform == "github"
    assert project.scope in [ProjectScope.ORGANIZATION, ProjectScope.USER]


@pytest.mark.asyncio
async def test_project_to_epic_conversion():
    """Test Project to Epic backwards compatibility."""
    project = Project(
        id="proj-123",
        platform="linear",
        name="Test Project",
        state=ProjectState.ACTIVE
    )

    epic = project.to_epic()

    assert epic.title == project.name
    assert epic.state == TicketState.IN_PROGRESS  # ACTIVE → IN_PROGRESS
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_crud_lifecycle():
    """Test full project CRUD lifecycle."""
    adapter = get_test_adapter()

    # Create
    project = await adapter.create_project(
        name="Integration Test Project",
        description="Testing project operations"
    )
    assert project.id is not None

    # Read
    fetched = await adapter.get_project(project.id)
    assert fetched.name == "Integration Test Project"

    # Update
    updated = await adapter.update_project(
        project.id,
        state=ProjectState.ACTIVE,
        description="Updated description"
    )
    assert updated.state == ProjectState.ACTIVE

    # Delete
    success = await adapter.delete_project(project.id)
    assert success is True

    # Verify deleted
    deleted = await adapter.get_project(project.id)
    assert deleted is None
```

---

## 8. Documentation Requirements

### API Documentation

- Complete docstrings for all Project methods
- Usage examples for common workflows
- Platform-specific notes and limitations
- Migration guide from Epic to Project

### User Guide

- "Working with Projects" tutorial
- Platform comparison table
- Best practices for cross-platform projects
- Troubleshooting common issues

---

## 9. Future Enhancements

### Roadmap Features

1. **Project Templates**: Predefined project structures
2. **Project Cloning**: Duplicate project with issues
3. **Cross-Platform Sync**: Sync projects across adapters
4. **Project Archives**: Historical project data export
5. **Project Analytics**: Advanced metrics and insights
6. **Multi-Project Views**: Aggregate multiple projects
7. **Project Dependencies**: Track inter-project dependencies

---

## 10. Conclusion

This unified Projects abstraction provides:

✅ **Consistent API** across Linear, JIRA, and GitHub
✅ **Rich metadata** with platform-specific extensibility
✅ **Type safety** via Pydantic models
✅ **Backwards compatibility** with existing Epic-based code
✅ **Graceful degradation** for unsupported features

**Next Steps:**
1. Implement `Project` model in `core/models.py`
2. Add `ProjectOperations` protocol in `core/adapter.py`
3. Implement project methods in each adapter
4. Update tests and documentation
5. Provide migration utilities

---

**Related Documents:**
- [GitHub Projects V2 API Analysis](./github-projects-v2-api-analysis-2025-12-05.md)
- [Platform Mapping Document](./platform-concept-mapping-2025-12-05.md)
- [Implementation Strategy](./projects-implementation-strategy-2025-12-05.md)
