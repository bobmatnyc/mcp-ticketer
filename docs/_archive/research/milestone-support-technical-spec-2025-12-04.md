# Cross-Platform Milestone Support - Technical Specification

**Research Date:** 2025-12-04
**Ticket:** [1M-607](https://linear.app/1m-hyperdev/issue/1M-607/implement-cross-platform-milestone-support)
**Status:** Implementation Planning
**Priority:** High - Essential for sprint/release planning

## Executive Summary

This document provides a comprehensive technical specification for implementing cross-platform milestone support in mcp-ticketer. Milestones are defined as **collections of labels with target dates that group related issues**. The implementation will support GitHub's native milestones while providing label-based fallback mechanisms for Linear and Jira.

**Key Findings:**
- GitHub has native milestone support via REST/GraphQL API (already partially implemented)
- Linear uses Cycles (similar concept) with GraphQL API support
- Jira uses Fix Versions and Sprints for milestone-like functionality
- Unified abstraction layer required to normalize these different concepts
- Storage strategy: Platform-native where available, local metadata for label-based platforms

**Implementation Complexity:** Medium (5-6 days)
- Phase 1: Data model and core infrastructure (1 day)
- Phase 2: GitHub adapter enhancement (1 day)
- Phase 3: Linear adapter with Cycles support (2 days)
- Phase 4: MCP tools and API (1 day)
- Phase 5: Jira adapter support (1 day)

---

## 1. Architecture Analysis

### 1.1 Current Adapter Pattern

The mcp-ticketer project follows a clean adapter pattern with clear separation of concerns:

**Core Components:**
```
src/mcp_ticketer/
├── core/
│   ├── models.py              # Pydantic data models (Epic, Task, Comment)
│   ├── adapter.py             # BaseAdapter abstract class
│   └── project_config.py      # Configuration management
├── adapters/
│   ├── github.py              # GitHub REST/GraphQL adapter (has milestone support)
│   ├── linear/                # Linear GraphQL adapter (modularized)
│   │   ├── adapter.py
│   │   ├── queries.py         # GraphQL queries (has cycle queries)
│   │   ├── mappers.py
│   │   └── types.py
│   ├── jira.py                # Jira REST adapter (has sprint support)
│   └── asana/
└── mcp/server/tools/          # MCP tool definitions (17 tool modules)
    ├── ticket_tools.py        # Unified ticket() interface
    ├── hierarchy_tools.py     # hierarchy() for epics/issues/tasks
    └── ...
```

**Key Architectural Patterns:**
1. **Unified Interface:** All adapters implement `BaseAdapter[T]` abstract class
2. **Pydantic Models:** Type-safe data models with validation (Epic, Task, Comment, Attachment, ProjectUpdate)
3. **MCP Tool Consolidation:** v2.0.0 consolidated tools into unified interfaces (ticket, hierarchy, label, config)
4. **Async Operations:** All adapter methods are async for performance
5. **Platform-Specific Extensions:** Adapters store platform metadata in `metadata` dict field

### 1.2 Existing Milestone-Like Features

**GitHub Adapter (src/mcp_ticketer/adapters/github.py):**
```python
# Lines 73-79: Milestone data extracted in GraphQL
milestone {
    id
    number
    title
    state
    description
}

# Lines 313-343: Milestone-to-Epic conversion
def _milestone_to_epic(self, milestone: dict[str, Any]) -> Epic:
    """Convert GitHub milestone to Epic model."""
    return Epic(
        id=str(milestone["number"]),
        title=milestone["title"],
        description=milestone.get("description", ""),
        state=TicketState.OPEN if milestone["state"] == "open" else TicketState.CLOSED,
        metadata={
            "github": {
                "number": milestone["number"],
                "url": milestone.get("html_url"),
                "open_issues": milestone.get("open_issues", 0),
                "closed_issues": milestone.get("closed_issues", 0),
            }
        }
    )

# Lines 1043-1089: Full milestone CRUD operations
async def create_milestone(self, epic: Epic) -> Epic
async def get_milestone(self, milestone_number: int) -> Epic | None
async def list_milestones(self, state: str = "open", ...) -> list[Epic]
async def update_milestone(self, milestone_number: int, updates: dict) -> Epic
# Note: delete_milestone integrated into delete_epic (lines 1092-1145)
```

**Linear Adapter (src/mcp_ticketer/adapters/linear/queries.py):**
```python
# Lines 311-312: Cycle query support exists
cycles(filter: $filter, orderBy: createdAt) {
    nodes { ... }
}

# Lines 413: Project iterations query
cycles(first: $first, after: $after) {
    nodes { ... }
}
```

**Jira Adapter (src/mcp_ticketer/adapters/jira.py):**
```python
# Lines 925-1257: Sprint support exists
async def get_sprints(self, board_id: int, ...)
    """Get active sprints for a board (requires JIRA Software)."""

# Also supports Fix Versions (lines 483):
"fix_versions": fields.get("fixVersions", [])
```

**Current Limitation:** These platform-specific features are not unified into a cross-platform abstraction. GitHub milestones are mapped to Epics, but Linear Cycles and Jira Sprints are not exposed through the universal interface.

---

## 2. Platform-Specific Implementations

### 2.1 GitHub Milestones

**API Support:** Native milestone feature via REST API v3 and GraphQL API v4

**Data Structure:**
```json
{
  "id": 1234567,
  "node_id": "MI_kwDOAbc123",
  "number": 5,
  "title": "v2.1.0 Release",
  "description": "Features for v2.1.0 release",
  "state": "open",  // or "closed"
  "open_issues": 8,
  "closed_issues": 12,
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-02-20T15:30:00Z",
  "due_on": "2025-03-31T23:59:59Z",  // Target date
  "html_url": "https://github.com/owner/repo/milestone/5"
}
```

**Key Features:**
- Native progress tracking (open_issues, closed_issues)
- Due date field maps directly to target_date
- State: open/closed
- Markdown description support
- Filter issues by milestone in API: `?milestone=5`

**GraphQL Query:**
```graphql
query GetMilestones($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    milestones(first: 50, states: [OPEN, CLOSED]) {
      nodes {
        id
        number
        title
        description
        state
        dueOn
        progressPercentage
        issues(first: 100) {
          totalCount
        }
      }
    }
  }
}
```

**Implementation Status:** ✅ **Mostly Complete**
- CRUD operations exist (create, read, list, update, delete)
- Mapped to Epic model
- Progress calculation available
- **Gap:** Not exposed as unified "milestone" interface

### 2.2 Linear Cycles

**API Support:** Native Cycle feature via GraphQL API

**Data Structure (GraphQL Schema):**
```graphql
type Cycle {
  id: ID!
  name: String!
  description: String
  startsAt: DateTime!
  endsAt: DateTime!
  completedAt: DateTime
  progress: Float!  # 0.0 to 1.0

  issues(filter: IssueFilter): IssueConnection!

  team: Team!
  project: Project
}
```

**Key Features:**
- Start and end dates (similar to sprints)
- Built-in progress calculation
- Team-scoped (each team has separate cycles)
- Issues can be assigned to cycles
- Active/completed state based on dates
- Can be associated with projects (epics)

**GraphQL Query:**
```graphql
query GetCycles($teamId: String!, $filter: CycleFilter) {
  team(id: $teamId) {
    cycles(filter: $filter, orderBy: createdAt) {
      nodes {
        id
        name
        description
        startsAt
        endsAt
        completedAt
        progress
        completedIssueCount
        issueCount
        completedScopeHistory
        scopeHistory
        issues(first: 100) {
          nodes {
            id
            title
            state { name }
          }
        }
      }
    }
  }
}
```

**Issue Assignment:**
```graphql
mutation AssignIssueToCycle($issueId: ID!, $cycleId: ID!) {
  issueUpdate(id: $issueId, input: { cycleId: $cycleId }) {
    issue {
      id
      cycle { id name }
    }
  }
}
```

**Implementation Status:** 🟡 **Partial Support**
- Cycle queries exist in queries.py (lines 146, 311, 413)
- Not exposed through adapter public methods
- Not mapped to universal model
- **Gap:** Need to create Cycle ↔ Milestone mapping layer

**Mapping Strategy:**
```python
# Map Linear Cycle to unified Milestone model
Linear Cycle          → Milestone
├── id                → id (UUID)
├── name              → name
├── description       → description
├── endsAt            → target_date
├── progress          → progress_pct
├── issueCount        → total_issues
├── completedCount    → closed_issues
└── issues.nodes[]    → labels (extract common labels)
```

**Challenge:** Linear Cycles don't use labels for grouping; they have explicit issue assignment. We'll need to:
1. Store cycle-to-milestone mapping locally (.mcp-ticketer/milestones.json)
2. Query issues by cycle ID, not labels
3. Optionally tag issues with milestone labels for consistency

### 2.3 Jira Versions and Sprints

**API Support:** Two mechanisms available

**Option 1: Fix Versions (Simpler, Always Available)**
```json
{
  "id": "10001",
  "name": "v2.1.0",
  "description": "Version 2.1.0 Release",
  "archived": false,
  "released": false,
  "releaseDate": "2025-03-31",
  "project": "PROJ",
  "projectId": 10000
}
```

**REST Endpoints:**
```
GET  /rest/api/3/project/{projectIdOrKey}/versions
POST /rest/api/3/version
GET  /rest/api/3/version/{id}
PUT  /rest/api/3/version/{id}
```

**Query Issues by Fix Version:**
```
GET /rest/api/3/search?jql=fixVersion="v2.1.0" AND project=PROJ
```

**Option 2: Sprints (Requires Jira Software)**
```json
{
  "id": 123,
  "name": "Sprint 24",
  "state": "active",  // future, active, closed
  "startDate": "2025-02-01T00:00:00.000Z",
  "endDate": "2025-02-14T23:59:59.999Z",
  "completeDate": null,
  "goal": "Complete authentication features",
  "originBoardId": 84
}
```

**REST Endpoints:**
```
GET /rest/agile/1.0/board/{boardId}/sprint
GET /rest/agile/1.0/sprint/{sprintId}
GET /rest/agile/1.0/sprint/{sprintId}/issue
```

**Implementation Status:** 🟡 **Partial Support**
- Sprint queries exist (lines 925-1257)
- Fix Versions extracted in issue metadata (line 483)
- Not unified into milestone interface
- **Gap:** Need to choose primary mechanism and map to Milestone model

**Recommended Approach:** Use Fix Versions as primary mechanism
- Available in all Jira editions (Core, Software, Service Desk)
- Simpler API (no board dependencies)
- Better aligns with "release milestone" concept
- Sprints can be secondary/optional enhancement

**Mapping Strategy:**
```python
# Map Jira Fix Version to Milestone
Fix Version           → Milestone
├── id                → id
├── name              → name
├── description       → description
├── releaseDate       → target_date
├── released          → state (done/open)
└── project           → project_id

# Query issues: JQL filter by fixVersion
# Labels: Extract from issues in version
```

---

## 3. Unified Milestone Data Model

### 3.1 Core Model Definition

**Location:** `src/mcp_ticketer/core/models.py` (add new model)

```python
from datetime import date
from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class Milestone(BaseModel):
    """Unified milestone model across all platforms.

    Represents a collection of related issues with a target completion date.
    Maps to platform-specific concepts:
    - GitHub: Native Milestones
    - Linear: Cycles
    - Jira: Fix Versions (or Sprints)
    - Generic: Label groups with local storage
    """

    model_config = ConfigDict(use_enum_values=True)

    # Core fields (universal)
    id: str = Field(..., description="Unique identifier (platform-specific or generated)")
    name: str = Field(..., min_length=1, description="Milestone name/title")
    description: str | None = Field(None, description="Milestone description")
    target_date: date | None = Field(None, description="Target completion date")
    state: str = Field("open", description="Milestone state: open, active, completed, closed")

    # Association mechanism (platform-dependent)
    labels: list[str] = Field(
        default_factory=list,
        description="Labels defining this milestone (for label-based platforms)"
    )

    # Progress tracking (calculated)
    total_issues: int = Field(0, description="Total issues in milestone")
    closed_issues: int = Field(0, description="Completed issues count")
    progress_pct: float = Field(0.0, ge=0.0, le=100.0, description="Completion percentage")

    # Platform-specific data
    project_id: str | None = Field(None, description="Parent project/epic ID")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Platform-specific metadata (URLs, platform IDs, etc.)"
    )

    @property
    def is_completed(self) -> bool:
        """Check if milestone is completed."""
        return self.state in ("completed", "closed", "done")

    @property
    def is_active(self) -> bool:
        """Check if milestone is currently active."""
        return self.state in ("open", "active", "in_progress")

    def calculate_progress(self) -> float:
        """Calculate progress percentage from issue counts."""
        if self.total_issues == 0:
            return 0.0
        return (self.closed_issues / self.total_issues) * 100.0

    def update_progress(self, total: int, closed: int) -> None:
        """Update progress tracking fields."""
        self.total_issues = total
        self.closed_issues = closed
        self.progress_pct = self.calculate_progress()


class MilestoneFilter(BaseModel):
    """Filter criteria for milestone queries."""

    state: str | None = Field(None, description="Filter by state")
    project_id: str | None = Field(None, description="Filter by project")
    active_only: bool = Field(False, description="Only return active milestones")
    include_completed: bool = Field(False, description="Include completed milestones")
    limit: int = Field(50, gt=0, le=200, description="Maximum results")
```

### 3.2 State Mapping

**Unified States:**
- `open` - Not yet started or planned
- `active` - Currently in progress
- `completed` - All work done, target met
- `closed` - Archived/finalized

**Platform Mappings:**
```python
MILESTONE_STATE_MAPPING = {
    "github": {
        "open": "open",
        "active": "open",      # GitHub only has open/closed
        "completed": "closed",
        "closed": "closed"
    },
    "linear": {
        "open": "planned",     # Before start date
        "active": "started",   # Between start and end date
        "completed": "completed",
        "closed": "completed"
    },
    "jira": {
        "open": "unreleased",
        "active": "unreleased",
        "completed": "released",
        "closed": "archived"
    }
}
```

### 3.3 Storage Strategy

**Hybrid Approach: Platform-Native + Local Metadata**

**1. GitHub: Pure Platform Storage**
```python
# Use native milestone API
# No local storage needed
# Milestone ID = milestone number (e.g., "5")
```

**2. Linear: Platform Storage + Local Mapping**
```python
# Use native Cycle API for storage
# Local mapping: .mcp-ticketer/milestones.json
{
  "linear_milestones": {
    "cycle-abc123": {
      "milestone_id": "milestone-uuid",
      "milestone_name": "v2.1.0",
      "cycle_id": "abc123",
      "labels": ["v2.1", "release"],  # Optional consistency labels
      "created_at": "2025-02-01T00:00:00Z"
    }
  }
}
```

**3. Jira: Platform Storage (Fix Versions) + Local Mapping**
```python
# Use Fix Version API for storage
# Local mapping for metadata
{
  "jira_milestones": {
    "10001": {
      "milestone_id": "10001",
      "milestone_name": "v2.1.0",
      "version_id": "10001",
      "labels": ["2.1", "release"],
      "created_at": "2025-02-01T00:00:00Z"
    }
  }
}
```

**4. Generic/Fallback: Pure Local Storage**
```python
# For platforms without native milestone support
{
  "milestones": {
    "milestone-uuid-1": {
      "id": "milestone-uuid-1",
      "name": "v2.1.0 Release",
      "labels": ["v2.1", "release", "high-priority"],
      "target_date": "2025-03-31",
      "state": "open",
      "project_id": "project-123"
    }
  }
}
```

**Storage Location:** `.mcp-ticketer/milestones.json` (project-specific)

**Migration from Ticket Description:**
- Initially stored as mentioned: local JSON file
- This allows milestone metadata even when platforms don't support it natively
- For GitHub/Linear/Jira, local file acts as secondary index

---

## 4. MCP Tool Interface Design

### 4.1 Unified Milestone Tool

**Design Decision:** Follow v2.0.0 pattern of consolidated tools

**Tool Function:**
```python
@mcp.tool()
async def milestone(
    action: Literal[
        "create", "get", "list", "update", "delete",
        "add_issue", "remove_issue", "get_issues", "progress"
    ],
    milestone_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    target_date: str | None = None,  # ISO format: YYYY-MM-DD
    state: str | None = None,
    labels: list[str] | None = None,
    project_id: str | None = None,
    issue_id: str | None = None,
    limit: int = 50,
    include_completed: bool = False,
) -> dict[str, Any]:
    """Unified milestone management tool.

    Supports operations:
    - create: Create new milestone
    - get: Retrieve milestone details
    - list: List milestones (filterable)
    - update: Update milestone properties
    - delete: Delete milestone
    - add_issue: Associate issue with milestone
    - remove_issue: Remove issue from milestone
    - get_issues: List issues in milestone
    - progress: Get progress summary

    Args:
        action: Operation to perform
        milestone_id: Milestone identifier (required for get/update/delete/progress)
        name: Milestone name (required for create)
        description: Milestone description
        target_date: Target completion date (ISO format)
        state: Milestone state (open, active, completed, closed)
        labels: Label list (for label-based platforms)
        project_id: Parent project/epic ID
        issue_id: Issue ID (for add_issue/remove_issue)
        limit: Maximum results (for list/get_issues)
        include_completed: Include completed milestones in list

    Returns:
        Operation result with status and data

    Examples:
        # Create milestone
        await milestone(
            action="create",
            name="v2.1.0 Release",
            target_date="2025-03-31",
            labels=["v2.1", "release"]
        )

        # List active milestones
        await milestone(action="list", state="active")

        # Get progress
        await milestone(action="progress", milestone_id="milestone-123")

        # Add issue to milestone
        await milestone(
            action="add_issue",
            milestone_id="milestone-123",
            issue_id="PROJ-456"
        )
    """
```

### 4.2 Integration with Existing Tools

**ticket_search Enhancement:**
```python
@mcp.tool()
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    project_id: str | None = None,
    milestone_id: str | None = None,  # NEW: Filter by milestone
    limit: int = 10,
    include_hierarchy: bool = False,
) -> dict[str, Any]:
    """Search tickets with optional milestone filter."""
```

**ticket Enhancement (for create/update):**
```python
@mcp.tool()
async def ticket(
    action: str,
    ticket_id: str | None = None,
    title: str | None = None,
    description: str | None = None,
    milestone_id: str | None = None,  # NEW: Associate with milestone
    # ... existing parameters
) -> dict[str, Any]:
    """Unified ticket management with milestone support."""
```

**hierarchy Enhancement:**
```python
# Milestones can act as Epic-level grouping
# Option: Allow milestone_id as alternative to parent_epic
await hierarchy(
    entity_type="issue",
    action="create",
    title="Implement OAuth",
    milestone_id="milestone-123",  # Alternative to parent_epic
    # Or use milestone as filter in list
)
```

### 4.3 Response Format

**Standard Response Structure:**
```json
{
  "status": "success",
  "action": "create",
  "milestone": {
    "id": "milestone-123",
    "name": "v2.1.0 Release",
    "description": "Features for version 2.1.0",
    "target_date": "2025-03-31",
    "state": "active",
    "total_issues": 15,
    "closed_issues": 7,
    "progress_pct": 46.67,
    "labels": ["v2.1", "release"],
    "project_id": "project-abc",
    "created_at": "2025-02-01T10:00:00Z",
    "updated_at": "2025-02-15T14:30:00Z",
    "metadata": {
      "github": {
        "number": 5,
        "url": "https://github.com/owner/repo/milestone/5"
      }
    }
  },
  "adapter": "github",
  "adapter_name": "GitHub"
}
```

**Progress Response:**
```json
{
  "status": "success",
  "action": "progress",
  "milestone_id": "milestone-123",
  "milestone_name": "v2.1.0 Release",
  "progress": {
    "total_issues": 15,
    "closed_issues": 7,
    "open_issues": 8,
    "progress_pct": 46.67,
    "by_priority": {
      "critical": {"total": 2, "closed": 1},
      "high": {"total": 5, "closed": 3},
      "medium": {"total": 6, "closed": 3},
      "low": {"total": 2, "closed": 0}
    },
    "by_state": {
      "open": 3,
      "in_progress": 5,
      "ready": 2,
      "done": 5,
      "blocked": 0
    },
    "target_date": "2025-03-31",
    "days_remaining": 45,
    "on_track": true
  }
}
```

---

## 5. Adapter Implementation Strategy

### 5.1 BaseAdapter Extension

**Add abstract methods to BaseAdapter:**
```python
# src/mcp_ticketer/core/adapter.py

from .models import Milestone, MilestoneFilter

class BaseAdapter(ABC, Generic[T]):
    """Base adapter with milestone support."""

    # Existing methods...

    # Milestone operations (optional implementation)
    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create milestone. Raise NotImplementedError if unsupported."""
        raise NotImplementedError(
            f"{self.adapter_type} adapter does not support milestone creation"
        )

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get milestone by ID. Return None if not found or unsupported."""
        raise NotImplementedError(
            f"{self.adapter_type} adapter does not support milestones"
        )

    async def list_milestones(
        self, filters: MilestoneFilter | None = None
    ) -> list[Milestone]:
        """List milestones. Return empty list if unsupported."""
        return []

    async def update_milestone(
        self, milestone_id: str, updates: dict[str, Any]
    ) -> Milestone | None:
        """Update milestone. Raise NotImplementedError if unsupported."""
        raise NotImplementedError(
            f"{self.adapter_type} adapter does not support milestone updates"
        )

    async def delete_milestone(self, milestone_id: str) -> bool:
        """Delete milestone. Return False if unsupported."""
        return False

    async def add_issue_to_milestone(
        self, milestone_id: str, issue_id: str
    ) -> bool:
        """Add issue to milestone. Return False if unsupported."""
        return False

    async def remove_issue_from_milestone(
        self, milestone_id: str, issue_id: str
    ) -> bool:
        """Remove issue from milestone. Return False if unsupported."""
        return False

    async def get_milestone_issues(
        self, milestone_id: str, limit: int = 100
    ) -> list[Task]:
        """Get issues in milestone. Return empty list if unsupported."""
        return []

    async def get_milestone_progress(
        self, milestone_id: str
    ) -> dict[str, Any]:
        """Get milestone progress summary."""
        milestone = await self.get_milestone(milestone_id)
        if not milestone:
            return {"error": "Milestone not found"}

        issues = await self.get_milestone_issues(milestone_id)

        total = len(issues)
        closed = sum(1 for issue in issues if issue.state == TicketState.DONE)

        return {
            "total_issues": total,
            "closed_issues": closed,
            "open_issues": total - closed,
            "progress_pct": (closed / total * 100) if total > 0 else 0,
            "target_date": milestone.target_date,
            "state": milestone.state,
        }
```

### 5.2 GitHub Adapter Enhancement

**Status:** Mostly complete, needs unification

**Implementation:**
```python
# src/mcp_ticketer/adapters/github.py

class GitHubAdapter(BaseAdapter[Task]):
    """GitHub adapter with native milestone support."""

    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create GitHub milestone."""
        milestone_data = {
            "title": milestone.name,
            "description": milestone.description or "",
            "state": "open" if milestone.state == "open" else "closed",
        }

        if milestone.target_date:
            # GitHub expects ISO 8601 timestamp
            milestone_data["due_on"] = f"{milestone.target_date}T23:59:59Z"

        response = await self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/milestones",
            json=milestone_data
        )

        gh_milestone = response.json()
        return self._github_milestone_to_milestone(gh_milestone)

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get GitHub milestone by number."""
        try:
            milestone_number = int(milestone_id)
            response = await self._make_request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
            )
            gh_milestone = response.json()
            return self._github_milestone_to_milestone(gh_milestone)
        except (ValueError, httpx.HTTPError):
            return None

    async def list_milestones(
        self, filters: MilestoneFilter | None = None
    ) -> list[Milestone]:
        """List GitHub milestones."""
        params = {}

        if filters:
            if filters.state:
                params["state"] = "open" if filters.state == "open" else "closed"
            params["per_page"] = min(filters.limit, 100)

        response = await self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/milestones",
            params=params
        )

        milestones = [
            self._github_milestone_to_milestone(gh_ms)
            for gh_ms in response.json()
        ]

        # Apply additional filters
        if filters:
            if filters.active_only:
                milestones = [m for m in milestones if m.is_active]
            if not filters.include_completed:
                milestones = [m for m in milestones if not m.is_completed]

        return milestones

    async def update_milestone(
        self, milestone_id: str, updates: dict[str, Any]
    ) -> Milestone | None:
        """Update GitHub milestone."""
        milestone_number = int(milestone_id)

        # Map updates to GitHub fields
        gh_updates = {}
        if "name" in updates:
            gh_updates["title"] = updates["name"]
        if "description" in updates:
            gh_updates["description"] = updates["description"]
        if "state" in updates:
            gh_updates["state"] = "open" if updates["state"] == "open" else "closed"
        if "target_date" in updates:
            gh_updates["due_on"] = f"{updates['target_date']}T23:59:59Z"

        response = await self._make_request(
            "PATCH",
            f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}",
            json=gh_updates
        )

        return self._github_milestone_to_milestone(response.json())

    async def add_issue_to_milestone(
        self, milestone_id: str, issue_id: str
    ) -> bool:
        """Add issue to GitHub milestone."""
        try:
            milestone_number = int(milestone_id)
            issue_number = int(issue_id)

            await self._make_request(
                "PATCH",
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
                json={"milestone": milestone_number}
            )
            return True
        except (ValueError, httpx.HTTPError):
            return False

    async def get_milestone_issues(
        self, milestone_id: str, limit: int = 100
    ) -> list[Task]:
        """Get issues in GitHub milestone."""
        milestone_number = int(milestone_id)

        params = {
            "milestone": str(milestone_number),
            "state": "all",
            "per_page": min(limit, 100)
        }

        response = await self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/issues",
            params=params
        )

        return [
            self._issue_to_task(issue)
            for issue in response.json()
            if "pull_request" not in issue  # Exclude PRs
        ]

    def _github_milestone_to_milestone(
        self, gh_milestone: dict[str, Any]
    ) -> Milestone:
        """Convert GitHub milestone to Milestone model."""
        target_date = None
        if gh_milestone.get("due_on"):
            target_date = datetime.fromisoformat(
                gh_milestone["due_on"].replace("Z", "+00:00")
            ).date()

        return Milestone(
            id=str(gh_milestone["number"]),
            name=gh_milestone["title"],
            description=gh_milestone.get("description", ""),
            target_date=target_date,
            state="open" if gh_milestone["state"] == "open" else "closed",
            total_issues=gh_milestone.get("open_issues", 0) + gh_milestone.get("closed_issues", 0),
            closed_issues=gh_milestone.get("closed_issues", 0),
            created_at=datetime.fromisoformat(
                gh_milestone["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                gh_milestone["updated_at"].replace("Z", "+00:00")
            ),
            metadata={
                "github": {
                    "number": gh_milestone["number"],
                    "node_id": gh_milestone.get("node_id"),
                    "url": gh_milestone.get("html_url"),
                }
            }
        )
```

**Effort Estimate:** 0.5 days (refactoring existing code)

### 5.3 Linear Adapter Implementation

**Strategy:** Map Cycles to Milestones

**Implementation:**
```python
# src/mcp_ticketer/adapters/linear/adapter.py

from ...core.models import Milestone, MilestoneFilter

class LinearAdapter(BaseAdapter[Task]):
    """Linear adapter with Cycle-based milestone support."""

    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create Linear cycle as milestone."""
        # Calculate start date (30 days before target)
        start_date = milestone.target_date - timedelta(days=30) if milestone.target_date else datetime.now()
        end_date = milestone.target_date or datetime.now() + timedelta(days=30)

        mutation = gql("""
            mutation CreateCycle($input: CycleCreateInput!) {
                cycleCreate(input: $input) {
                    success
                    cycle {
                        id
                        name
                        description
                        startsAt
                        endsAt
                        progress
                        issueCount
                        completedIssueCount
                    }
                }
            }
        """)

        variables = {
            "input": {
                "teamId": self.team_id,
                "name": milestone.name,
                "description": milestone.description or "",
                "startsAt": start_date.isoformat(),
                "endsAt": end_date.isoformat(),
            }
        }

        result = await self.client.execute(mutation, variable_values=variables)
        cycle = result["cycleCreate"]["cycle"]

        return self._linear_cycle_to_milestone(cycle)

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get Linear cycle by ID."""
        query = gql("""
            query GetCycle($id: String!) {
                cycle(id: $id) {
                    id
                    name
                    description
                    startsAt
                    endsAt
                    completedAt
                    progress
                    issueCount
                    completedIssueCount
                    issues(first: 100) {
                        nodes {
                            id
                            title
                            state { name type }
                        }
                    }
                }
            }
        """)

        try:
            result = await self.client.execute(query, variable_values={"id": milestone_id})
            if result.get("cycle"):
                return self._linear_cycle_to_milestone(result["cycle"])
        except Exception as e:
            logger.error(f"Failed to get Linear cycle: {e}")

        return None

    async def list_milestones(
        self, filters: MilestoneFilter | None = None
    ) -> list[Milestone]:
        """List Linear cycles as milestones."""
        query = gql("""
            query ListCycles($teamId: String!, $first: Int!) {
                team(id: $teamId) {
                    cycles(first: $first, orderBy: createdAt) {
                        nodes {
                            id
                            name
                            description
                            startsAt
                            endsAt
                            completedAt
                            progress
                            issueCount
                            completedIssueCount
                        }
                    }
                }
            }
        """)

        limit = filters.limit if filters else 50
        variables = {"teamId": self.team_id, "first": min(limit, 100)}

        result = await self.client.execute(query, variable_values=variables)
        cycles = result["team"]["cycles"]["nodes"]

        milestones = [self._linear_cycle_to_milestone(cycle) for cycle in cycles]

        # Apply filters
        if filters:
            if filters.state:
                milestones = [m for m in milestones if m.state == filters.state]
            if filters.active_only:
                milestones = [m for m in milestones if m.is_active]
            if not filters.include_completed:
                milestones = [m for m in milestones if not m.is_completed]

        return milestones

    async def add_issue_to_milestone(
        self, milestone_id: str, issue_id: str
    ) -> bool:
        """Add issue to Linear cycle."""
        mutation = gql("""
            mutation UpdateIssue($id: String!, $cycleId: String!) {
                issueUpdate(id: $id, input: { cycleId: $cycleId }) {
                    success
                    issue {
                        id
                        cycle { id name }
                    }
                }
            }
        """)

        try:
            result = await self.client.execute(
                mutation,
                variable_values={"id": issue_id, "cycleId": milestone_id}
            )
            return result["issueUpdate"]["success"]
        except Exception as e:
            logger.error(f"Failed to add issue to cycle: {e}")
            return False

    async def get_milestone_issues(
        self, milestone_id: str, limit: int = 100
    ) -> list[Task]:
        """Get issues in Linear cycle."""
        query = gql("""
            query GetCycleIssues($cycleId: String!, $first: Int!) {
                cycle(id: $cycleId) {
                    issues(first: $first) {
                        nodes {
                            id
                            identifier
                            title
                            description
                            state { name type }
                            priority
                            assignee { email name }
                            labels { nodes { name } }
                            createdAt
                            updatedAt
                        }
                    }
                }
            }
        """)

        result = await self.client.execute(
            query,
            variable_values={"cycleId": milestone_id, "first": min(limit, 100)}
        )

        issues = result["cycle"]["issues"]["nodes"]
        return [map_linear_issue_to_task(issue) for issue in issues]

    def _linear_cycle_to_milestone(self, cycle: dict[str, Any]) -> Milestone:
        """Convert Linear cycle to Milestone model."""
        # Determine state from dates
        now = datetime.now(timezone.utc)
        start = datetime.fromisoformat(cycle["startsAt"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(cycle["endsAt"].replace("Z", "+00:00"))
        completed = cycle.get("completedAt")

        if completed:
            state = "completed"
        elif now < start:
            state = "open"
        elif start <= now <= end:
            state = "active"
        else:
            state = "closed"

        return Milestone(
            id=cycle["id"],
            name=cycle["name"],
            description=cycle.get("description", ""),
            target_date=end.date(),
            state=state,
            total_issues=cycle.get("issueCount", 0),
            closed_issues=cycle.get("completedIssueCount", 0),
            progress_pct=cycle.get("progress", 0.0) * 100,
            metadata={
                "linear": {
                    "cycle_id": cycle["id"],
                    "starts_at": cycle["startsAt"],
                    "ends_at": cycle["endsAt"],
                    "completed_at": completed,
                }
            }
        )
```

**Effort Estimate:** 2 days (new implementation)

### 5.4 Jira Adapter Implementation

**Strategy:** Use Fix Versions as primary mechanism

**Implementation:**
```python
# src/mcp_ticketer/adapters/jira.py

class JiraAdapter(BaseAdapter[Task]):
    """Jira adapter with Fix Version-based milestone support."""

    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create Jira fix version as milestone."""
        version_data = {
            "name": milestone.name,
            "description": milestone.description or "",
            "project": self.project_key,
            "archived": False,
            "released": milestone.state == "completed",
        }

        if milestone.target_date:
            version_data["releaseDate"] = milestone.target_date.isoformat()

        response = await self._make_request(
            "POST",
            "/rest/api/3/version",
            json=version_data
        )

        version = response.json()
        return self._jira_version_to_milestone(version)

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get Jira fix version by ID."""
        try:
            response = await self._make_request(
                "GET",
                f"/rest/api/3/version/{milestone_id}"
            )
            version = response.json()
            return self._jira_version_to_milestone(version)
        except httpx.HTTPError:
            return None

    async def list_milestones(
        self, filters: MilestoneFilter | None = None
    ) -> list[Milestone]:
        """List Jira fix versions as milestones."""
        response = await self._make_request(
            "GET",
            f"/rest/api/3/project/{self.project_key}/versions"
        )

        versions = response.json()
        milestones = [self._jira_version_to_milestone(v) for v in versions]

        # Apply filters
        if filters:
            if filters.state:
                milestones = [m for m in milestones if m.state == filters.state]
            if not filters.include_completed:
                milestones = [m for m in milestones if not m.is_completed]

        return milestones

    async def add_issue_to_milestone(
        self, milestone_id: str, issue_id: str
    ) -> bool:
        """Add issue to Jira fix version."""
        try:
            await self._make_request(
                "PUT",
                f"/rest/api/3/issue/{issue_id}",
                json={
                    "fields": {
                        "fixVersions": [{"id": milestone_id}]
                    }
                }
            )
            return True
        except httpx.HTTPError:
            return False

    async def get_milestone_issues(
        self, milestone_id: str, limit: int = 100
    ) -> list[Task]:
        """Get issues in Jira fix version."""
        # Get version name first
        version = await self.get_milestone(milestone_id)
        if not version:
            return []

        # Query issues by JQL
        jql = f'fixVersion="{version.name}" AND project={self.project_key}'
        params = {
            "jql": jql,
            "maxResults": min(limit, 100),
            "fields": "*all"
        }

        response = await self._make_request(
            "GET",
            "/rest/api/3/search",
            params=params
        )

        issues = response.json().get("issues", [])
        return [self._issue_to_task(issue) for issue in issues]

    def _jira_version_to_milestone(self, version: dict[str, Any]) -> Milestone:
        """Convert Jira fix version to Milestone model."""
        target_date = None
        if version.get("releaseDate"):
            target_date = datetime.fromisoformat(version["releaseDate"]).date()

        state = "completed" if version.get("released") else "open"
        if version.get("archived"):
            state = "closed"

        return Milestone(
            id=version["id"],
            name=version["name"],
            description=version.get("description", ""),
            target_date=target_date,
            state=state,
            project_id=version.get("projectId"),
            metadata={
                "jira": {
                    "version_id": version["id"],
                    "project": version.get("project"),
                    "archived": version.get("archived", False),
                    "released": version.get("released", False),
                }
            }
        )
```

**Effort Estimate:** 1 day (similar pattern to GitHub)

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure (1 day)

**Files to Create/Modify:**
- `src/mcp_ticketer/core/models.py` - Add `Milestone` and `MilestoneFilter` models
- `src/mcp_ticketer/core/adapter.py` - Add milestone abstract methods to `BaseAdapter`
- `src/mcp_ticketer/core/milestone_manager.py` - NEW: Local storage manager

**Tasks:**
1. Define `Milestone` Pydantic model with validation
2. Define `MilestoneFilter` for query operations
3. Add abstract milestone methods to `BaseAdapter`
4. Create `MilestoneManager` class for local JSON storage
5. Add milestone state mapping constants
6. Write unit tests for models

**Deliverables:**
- ✅ Milestone data models
- ✅ Local storage infrastructure
- ✅ Unit tests passing

**Acceptance Criteria:**
- Models validate correctly (Pydantic validation)
- Local storage can save/load milestones
- BaseAdapter defines interface contract

### Phase 2: GitHub Adapter Enhancement (1 day)

**Files to Modify:**
- `src/mcp_ticketer/adapters/github.py`

**Tasks:**
1. Refactor existing milestone methods to use new `Milestone` model
2. Implement `create_milestone` (refactor existing)
3. Implement `get_milestone` (refactor existing)
4. Implement `list_milestones` (refactor existing)
5. Implement `update_milestone` (refactor existing)
6. Implement `delete_milestone` (already exists)
7. Implement `add_issue_to_milestone` (NEW)
8. Implement `remove_issue_from_milestone` (NEW)
9. Implement `get_milestone_issues` (NEW)
10. Implement `get_milestone_progress` (NEW)
11. Write integration tests

**Deliverables:**
- ✅ GitHub milestone operations unified
- ✅ Full CRUD support
- ✅ Issue association methods
- ✅ Integration tests passing

**Acceptance Criteria:**
- All milestone operations work with GitHub API
- Progress calculation accurate
- Tests cover happy path and error cases

### Phase 3: Linear Adapter Implementation (2 days)

**Files to Modify:**
- `src/mcp_ticketer/adapters/linear/adapter.py`
- `src/mcp_ticketer/adapters/linear/queries.py`
- `src/mcp_ticketer/adapters/linear/mappers.py`

**Tasks:**
1. Add cycle queries to `queries.py` (expand existing)
2. Implement `_linear_cycle_to_milestone` mapper
3. Implement `create_milestone` (create cycle)
4. Implement `get_milestone` (query cycle)
5. Implement `list_milestones` (list cycles)
6. Implement `update_milestone` (update cycle)
7. Implement `delete_milestone` (archive cycle)
8. Implement `add_issue_to_milestone` (assign issue to cycle)
9. Implement `remove_issue_from_milestone` (remove cycle assignment)
10. Implement `get_milestone_issues` (query cycle issues)
11. Implement `get_milestone_progress` (calculate from cycle data)
12. Handle date-based state transitions (open → active → completed)
13. Write integration tests

**Deliverables:**
- ✅ Linear Cycle ↔ Milestone mapping
- ✅ Full CRUD support for cycles
- ✅ Date-based state management
- ✅ Integration tests passing

**Acceptance Criteria:**
- Cycles map correctly to milestones
- State transitions based on dates work
- Progress calculation matches Linear's native progress
- Tests cover all operations

**Technical Notes:**
- Linear cycles have explicit start/end dates (unlike GitHub milestones)
- Need to calculate state: open (before start), active (in range), completed (after end)
- Linear tracks progress natively (0.0 to 1.0 float)

### Phase 4: MCP Tools and API (1 day)

**Files to Create/Modify:**
- `src/mcp_ticketer/mcp/server/tools/milestone_tools.py` - NEW
- `src/mcp_ticketer/mcp/server/tools/ticket_tools.py` - Modify
- `src/mcp_ticketer/mcp/server/tools/search_tools.py` - Modify

**Tasks:**
1. Create `milestone_tools.py` with unified `milestone()` tool
2. Implement action routing (create, get, list, update, delete, add_issue, remove_issue, get_issues, progress)
3. Add `milestone_id` parameter to `ticket()` tool
4. Add `milestone_id` filter to `ticket_search()` tool
5. Implement adapter routing (detect platform, call appropriate adapter)
6. Add error handling and validation
7. Write MCP tool tests
8. Update tool documentation

**Deliverables:**
- ✅ Unified `milestone()` MCP tool
- ✅ Integration with existing ticket tools
- ✅ Comprehensive error handling
- ✅ Tool documentation

**Acceptance Criteria:**
- All milestone operations accessible via MCP
- Ticket tools support milestone filtering
- Error messages clear and actionable
- Documentation complete

### Phase 5: Jira Adapter Implementation (1 day)

**Files to Modify:**
- `src/mcp_ticketer/adapters/jira.py`

**Tasks:**
1. Implement `_jira_version_to_milestone` mapper
2. Implement `create_milestone` (create fix version)
3. Implement `get_milestone` (get fix version)
4. Implement `list_milestones` (list fix versions)
5. Implement `update_milestone` (update fix version)
6. Implement `delete_milestone` (archive fix version)
7. Implement `add_issue_to_milestone` (set fixVersion field)
8. Implement `remove_issue_from_milestone` (clear fixVersion)
9. Implement `get_milestone_issues` (JQL query)
10. Write integration tests

**Deliverables:**
- ✅ Jira Fix Version ↔ Milestone mapping
- ✅ Full CRUD support
- ✅ JQL-based issue queries
- ✅ Integration tests passing

**Acceptance Criteria:**
- Fix versions map correctly to milestones
- All operations work with Jira API
- JQL queries return correct results
- Tests cover all operations

### Phase 6: Testing and Documentation (Optional, if time permits)

**Tasks:**
1. Write end-to-end tests across all adapters
2. Update API documentation
3. Write user guide with examples
4. Create migration guide for existing users
5. Performance testing (especially for large milestone queries)

**Deliverables:**
- ✅ Comprehensive test suite
- ✅ Updated documentation
- ✅ User guide with examples

---

## 7. Technical Constraints and Risks

### 7.1 Platform Limitations

**GitHub:**
- ✅ Native milestone support (no limitations)
- ⚠️ Milestone is repository-scoped (not organization-scoped)
- ⚠️ Cannot nest milestones (flat structure)
- ⚠️ 100 milestones per query (pagination required for large repos)

**Linear:**
- ✅ Native Cycle support
- ⚠️ Cycles are team-scoped (not workspace-scoped)
- ⚠️ Start/end dates required (cannot create open-ended milestone)
- ⚠️ Progress calculated by Linear (may differ from our calculation)
- ⚠️ Cycle deletion = archive (not permanent delete)

**Jira:**
- ✅ Fix Versions available in all editions
- ⚠️ Project-scoped (not cross-project)
- ⚠️ No native progress calculation (must query issues)
- ⚠️ JQL query complexity for large projects
- ⚠️ Sprints require Jira Software (not available in Core/Service Desk)

### 7.2 Data Consistency Risks

**Issue Association:**
- GitHub: Direct `milestone` field on issue
- Linear: Direct `cycleId` field on issue
- Jira: Array field `fixVersions[]` (can have multiple versions)

**Risk:** Jira allows multiple fix versions per issue, but our model assumes single milestone
**Mitigation:** Store additional fix versions in metadata, primary milestone in `milestone_id`

**Label Consistency:**
- User definition mentions "list of labels with target dates"
- But GitHub/Linear/Jira don't use labels for milestone grouping
- They use direct associations

**Risk:** Confusion between label-based grouping and platform-native associations
**Mitigation:**
- Store optional `labels` field in Milestone model for metadata
- Document that labels are informational, not functional
- For label-based platforms (future), use labels as primary mechanism

### 7.3 Performance Considerations

**Milestone Progress Calculation:**
- GitHub: Native progress (open_issues, closed_issues) - ✅ Fast
- Linear: Native progress (float 0.0-1.0) - ✅ Fast
- Jira: Requires JQL query to count issues - ⚠️ Slower for large projects

**Mitigation:**
- Cache progress results with TTL (5 minutes)
- Provide `refresh=True` parameter to force recalculation
- Add `skip_progress=True` option for list operations

**Issue Queries:**
- GitHub: 100 issues per page (pagination required)
- Linear: 100 issues per query (pagination supported)
- Jira: 100 issues per query (JQL maxResults)

**Mitigation:**
- Implement pagination for all adapters
- Add `limit` parameter (default: 50, max: 200)
- Warn user if results truncated

### 7.4 API Rate Limits

**GitHub:**
- Authenticated: 5000 requests/hour
- GraphQL: 5000 points/hour (complex queries cost more)

**Linear:**
- Rate limit: 1000 requests/hour per user
- Burst limit: 20 requests/second

**Jira:**
- Cloud: Rate limits vary by plan (typically 100-10000 req/hour)
- Server: No rate limits (self-hosted)

**Mitigation:**
- Implement request caching (5 minute TTL)
- Batch operations where possible
- Provide clear error messages on rate limit errors

### 7.5 Backward Compatibility

**Existing Code:**
- GitHub adapter already has `create_milestone`, `get_milestone`, etc.
- These currently return `Epic` objects
- New implementation returns `Milestone` objects

**Risk:** Breaking existing integrations

**Mitigation:**
1. Keep existing `_milestone_to_epic()` method for Epic hierarchy support
2. Add new `_milestone_to_milestone()` for milestone API
3. Deprecate Epic-based milestone methods with warnings
4. Provide migration guide for users

**Breaking Changes:**
- Response format changes from Epic to Milestone
- New required fields (target_date, progress_pct)
- State mapping changes (open/closed → open/active/completed/closed)

**Recommendation:** Introduce as v2.1.0 (minor version bump) with deprecation warnings

---

## 8. Dependencies and Prerequisites

### 8.1 External Dependencies

**No new external dependencies required** ✅

**Existing dependencies sufficient:**
- `httpx` - HTTP client (already used)
- `pydantic` - Data validation (already used)
- `gql` - GraphQL client for Linear (already used)

### 8.2 Internal Dependencies

**Must exist before implementation:**
1. ✅ BaseAdapter abstract class (already exists)
2. ✅ Pydantic models infrastructure (already exists)
3. ✅ MCP tool framework (already exists)
4. ✅ Adapter registry system (already exists)
5. ✅ Configuration management (already exists)

**Nice to have (can implement in parallel):**
- Label management system (for label-based milestone grouping)
- Progress tracking analytics
- Milestone burndown charts (future enhancement)

### 8.3 Configuration Requirements

**New configuration options:**
```json
{
  "milestones": {
    "enabled": true,
    "storage_path": ".mcp-ticketer/milestones.json",
    "cache_ttl": 300,  // 5 minutes
    "default_duration_days": 30,  // For Linear cycle creation
    "progress_calculation": "native"  // or "query"
  }
}
```

**Adapter-specific config (no changes needed):**
- GitHub: Existing auth sufficient
- Linear: Existing auth sufficient
- Jira: Existing auth sufficient

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Models (test_models.py):**
```python
def test_milestone_creation():
    """Test Milestone model validation."""

def test_milestone_progress_calculation():
    """Test progress calculation logic."""

def test_milestone_state_validation():
    """Test state enum validation."""
```

**Adapters (test_adapter_*.py):**
```python
@pytest.mark.asyncio
async def test_github_create_milestone():
    """Test GitHub milestone creation."""

@pytest.mark.asyncio
async def test_linear_cycle_to_milestone_mapping():
    """Test Linear Cycle → Milestone conversion."""

@pytest.mark.asyncio
async def test_jira_version_to_milestone_mapping():
    """Test Jira Fix Version → Milestone conversion."""
```

### 9.2 Integration Tests

**MCP Tools (test_milestone_tools.py):**
```python
@pytest.mark.integration
async def test_milestone_create_via_mcp():
    """Test milestone creation via MCP tool."""

@pytest.mark.integration
async def test_milestone_add_issue():
    """Test adding issue to milestone via MCP."""

@pytest.mark.integration
async def test_milestone_progress_query():
    """Test milestone progress calculation."""
```

### 9.3 End-to-End Tests

**Cross-Platform (test_e2e_milestones.py):**
```python
@pytest.mark.e2e
@pytest.mark.parametrize("adapter", ["github", "linear", "jira"])
async def test_milestone_lifecycle(adapter):
    """Test full milestone lifecycle across adapters."""
    # 1. Create milestone
    # 2. Add issues
    # 3. Update milestone
    # 4. Query progress
    # 5. Delete milestone
```

### 9.4 Performance Tests

**Load Testing:**
```python
@pytest.mark.performance
async def test_milestone_list_performance():
    """Test listing 100+ milestones."""

@pytest.mark.performance
async def test_milestone_progress_large_project():
    """Test progress calculation with 500+ issues."""
```

### 9.5 Test Coverage Goals

- **Unit Tests:** 90%+ coverage
- **Integration Tests:** All MCP tools covered
- **E2E Tests:** Happy path for each adapter
- **Performance Tests:** Critical operations benchmarked

---

## 10. Documentation Requirements

### 10.1 API Documentation

**Files to Update:**
- `docs/mcp-api-reference.md` - Add milestone tool documentation
- `docs/adapters/github.md` - Document GitHub milestone support
- `docs/adapters/linear.md` - Document Linear Cycle support
- `docs/adapters/jira.md` - Document Jira Fix Version support

**Content:**
```markdown
## Milestone Management

### milestone() Tool

Unified milestone management across all platforms.

**Actions:**
- create: Create new milestone
- get: Retrieve milestone details
- list: List milestones with filters
- update: Update milestone properties
- delete: Delete milestone
- add_issue: Associate issue with milestone
- remove_issue: Remove issue from milestone
- get_issues: List issues in milestone
- progress: Get progress summary

**Examples:**
[Include code examples for each action]

**Platform Support:**
| Platform | Native Support | Implementation |
|----------|----------------|----------------|
| GitHub   | ✅ Yes         | Milestones API |
| Linear   | ✅ Yes         | Cycles API     |
| Jira     | ✅ Yes         | Fix Versions   |
| Asana    | ⏳ Planned     | Projects API   |
```

### 10.2 User Guide

**New Document:** `docs/guides/milestones.md`

**Content:**
- What are milestones?
- Creating and managing milestones
- Adding issues to milestones
- Tracking milestone progress
- Platform-specific considerations
- Best practices
- Common workflows

### 10.3 Migration Guide

**New Document:** `docs/UPGRADING-v2.1.md`

**Content:**
- Breaking changes from v2.0
- Deprecated methods
- Migration examples
- FAQ

---

## 11. Future Enhancements

### 11.1 Phase 2 Features (Post-MVP)

**Milestone Templates:**
```python
# Predefined milestone templates
templates = {
    "sprint": {
        "duration_days": 14,
        "labels": ["sprint"],
        "auto_close": True
    },
    "release": {
        "duration_days": 90,
        "labels": ["release"],
        "require_approval": True
    }
}
```

**Milestone Dependencies:**
```python
# Milestone A must complete before Milestone B
milestone.dependencies = ["milestone-123"]
```

**Burndown Charts:**
```python
# Get daily progress history
milestone_burndown = await adapter.get_milestone_burndown(milestone_id)
# Returns: [(date, remaining_issues), ...]
```

**Auto-Transition:**
```python
# Automatically move milestone from open → active → completed based on dates
milestone.auto_transition = True
```

### 11.2 Advanced Features

**Cross-Project Milestones:**
```python
# Create milestone spanning multiple projects
milestone.project_ids = ["project-1", "project-2", "project-3"]
```

**Milestone Roadmap:**
```python
# Generate roadmap view of all milestones
roadmap = await adapter.get_milestone_roadmap(
    start_date="2025-01-01",
    end_date="2025-12-31"
)
```

**Smart Labels:**
```python
# Automatically suggest labels for milestone based on issues
suggested_labels = await adapter.suggest_milestone_labels(milestone_id)
```

### 11.3 Platform Expansions

**Asana:**
- Use Projects API for milestone support
- Map projects to milestones

**Notion:**
- Use Database API with date properties
- Custom milestone views

**Trello:**
- Use Lists or Labels for milestone grouping
- Custom fields for target dates

---

## 12. Conclusion and Recommendations

### 12.1 Implementation Priority

**Must Have (v2.1.0):**
1. ✅ Phase 1: Core infrastructure and data models
2. ✅ Phase 2: GitHub adapter enhancement
3. ✅ Phase 3: Linear adapter implementation
4. ✅ Phase 4: MCP tools and API

**Should Have (v2.1.0):**
5. ✅ Phase 5: Jira adapter implementation
6. ✅ Unit and integration tests
7. ✅ Basic documentation

**Nice to Have (v2.2.0):**
8. ⏳ Performance optimization
9. ⏳ Advanced features (templates, dependencies)
10. ⏳ Comprehensive user guide

### 12.2 Technical Recommendations

**Storage Strategy:**
- ✅ Use platform-native storage where available (GitHub, Linear, Jira)
- ✅ Local JSON only for metadata and label-based fallback
- ✅ Avoid duplicating platform data locally

**State Management:**
- ✅ Unified state enum (open, active, completed, closed)
- ✅ Platform-specific state mapping
- ✅ Date-based state transitions for Linear

**Progress Calculation:**
- ✅ Use native progress when available (GitHub, Linear)
- ⚠️ Query-based calculation for Jira (cache results)
- ✅ Provide both real-time and cached options

**Label Usage:**
- ℹ️ Labels are informational metadata, not functional requirement
- ℹ️ Document that platforms use native associations, not labels
- ✅ Support label-based grouping for future platforms

### 12.3 Success Metrics

**Functional:**
- ✅ All CRUD operations work across 3 platforms (GitHub, Linear, Jira)
- ✅ Progress calculation accurate within 1%
- ✅ Milestone-issue association works bidirectionally
- ✅ Query performance <2 seconds for milestones with <100 issues

**Technical:**
- ✅ 90%+ test coverage
- ✅ Zero breaking changes for existing Epic-based code
- ✅ API rate limits respected (no 429 errors)
- ✅ Clear error messages for all failure cases

**User Experience:**
- ✅ Consistent MCP tool interface across platforms
- ✅ Comprehensive documentation with examples
- ✅ Migration path for existing users
- ✅ Performance acceptable for typical use cases

### 12.4 Risk Mitigation Summary

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API rate limits | High | Medium | Caching, batch operations |
| Jira multiple fix versions | Medium | Low | Store primary in model, others in metadata |
| Label confusion | Medium | Medium | Clear documentation, examples |
| Performance (large projects) | High | Medium | Pagination, caching, async queries |
| Breaking changes | High | Low | Deprecation warnings, migration guide |

### 12.5 Go/No-Go Recommendation

**Recommendation: ✅ GO**

**Justification:**
1. ✅ Clear user need (sprint/release planning)
2. ✅ Platform support exists (GitHub, Linear, Jira all have native features)
3. ✅ Architecture supports extension (BaseAdapter pattern)
4. ✅ Reasonable implementation effort (5-6 days)
5. ✅ No blocking technical constraints
6. ✅ Backward compatibility achievable
7. ✅ Clear success criteria

**Recommended Approach:**
- Start with Phase 1-4 (core + GitHub + Linear + MCP tools)
- Release as v2.1.0-beta for early testing
- Add Jira support in v2.1.0 final release
- Plan advanced features for v2.2.0

**Next Steps:**
1. Get stakeholder approval for technical approach
2. Create detailed task breakdown in Linear
3. Assign developers to Phase 1-2
4. Begin implementation with unit tests
5. Iterate with code reviews after each phase

---

## Appendix A: Code Examples

### A.1 Creating a Milestone

```python
# Via MCP tool
result = await milestone(
    action="create",
    name="v2.1.0 Release",
    description="Features for version 2.1.0",
    target_date="2025-03-31",
    labels=["v2.1", "release", "high-priority"],
    project_id="project-abc123"
)

# Via adapter directly (GitHub)
from mcp_ticketer.core.models import Milestone
from mcp_ticketer.adapters.github import GitHubAdapter

adapter = GitHubAdapter(config)
milestone = Milestone(
    name="v2.1.0 Release",
    description="Features for version 2.1.0",
    target_date=date(2025, 3, 31),
    state="open"
)
created = await adapter.create_milestone(milestone)
print(f"Created milestone: {created.id}")
```

### A.2 Querying Milestone Progress

```python
# Via MCP tool
result = await milestone(
    action="progress",
    milestone_id="milestone-123"
)

print(f"Progress: {result['progress']['progress_pct']:.1f}%")
print(f"Issues: {result['progress']['closed_issues']}/{result['progress']['total_issues']}")

# Via adapter
progress = await adapter.get_milestone_progress("milestone-123")
print(f"On track: {progress.get('on_track', False)}")
```

### A.3 Adding Issues to Milestone

```python
# Via MCP tool
result = await milestone(
    action="add_issue",
    milestone_id="milestone-123",
    issue_id="PROJ-456"
)

# Bulk add via ticket_bulk
await ticket_bulk(
    action="update",
    updates=[
        {"ticket_id": "PROJ-456", "milestone_id": "milestone-123"},
        {"ticket_id": "PROJ-457", "milestone_id": "milestone-123"},
        {"ticket_id": "PROJ-458", "milestone_id": "milestone-123"},
    ]
)
```

### A.4 Listing Milestones

```python
# Via MCP tool - active milestones only
result = await milestone(
    action="list",
    state="active",
    project_id="project-abc",
    limit=20
)

for ms in result["milestones"]:
    print(f"{ms['name']}: {ms['progress_pct']:.0f}% ({ms['closed_issues']}/{ms['total_issues']})")
```

### A.5 Searching Tickets by Milestone

```python
# Via ticket_search with milestone filter
result = await ticket_search(
    milestone_id="milestone-123",
    state="open",
    priority="high",
    limit=50
)

print(f"Found {len(result['tickets'])} high-priority open issues in milestone")
```

---

## Appendix B: Platform API References

### B.1 GitHub Milestones API

**REST API v3:**
- Docs: https://docs.github.com/en/rest/issues/milestones
- Endpoints:
  - `GET /repos/{owner}/{repo}/milestones`
  - `POST /repos/{owner}/{repo}/milestones`
  - `GET /repos/{owner}/{repo}/milestones/{milestone_number}`
  - `PATCH /repos/{owner}/{repo}/milestones/{milestone_number}`
  - `DELETE /repos/{owner}/{repo}/milestones/{milestone_number}`

**GraphQL API v4:**
- Schema: https://docs.github.com/en/graphql/reference/objects#milestone
- Fields: id, number, title, description, dueOn, state, progressPercentage

### B.2 Linear Cycles API

**GraphQL API:**
- Docs: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- Cycle Schema: https://studio.apollographql.com/public/Linear-API/variant/current/schema/reference/objects/Cycle
- Mutations:
  - `cycleCreate(input: CycleCreateInput!)`
  - `cycleUpdate(id: String!, input: CycleUpdateInput!)`
  - `cycleArchive(id: String!)`
  - `issueUpdate(id: String!, input: { cycleId: String })`

### B.3 Jira Versions API

**REST API v3:**
- Docs: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-project-versions/
- Endpoints:
  - `GET /rest/api/3/project/{projectIdOrKey}/versions`
  - `POST /rest/api/3/version`
  - `GET /rest/api/3/version/{id}`
  - `PUT /rest/api/3/version/{id}`
  - `DELETE /rest/api/3/version/{id}`

**Jira Software Sprints API:**
- Docs: https://developer.atlassian.com/cloud/jira/software/rest/api-group-sprint/
- Endpoints:
  - `GET /rest/agile/1.0/board/{boardId}/sprint`
  - `GET /rest/agile/1.0/sprint/{sprintId}`

---

## Appendix C: Memory Usage Statistics

**Files Analyzed:**
- `src/mcp_ticketer/core/models.py` (533 lines) - Read fully
- `src/mcp_ticketer/adapters/github.py` (2043 lines) - Sampled 200 lines + grep patterns
- `src/mcp_ticketer/adapters/linear/adapter.py` (200 lines sampled) - Strategic reading
- `src/mcp_ticketer/mcp/server/tools/ticket_tools.py` (150 lines sampled) - Pattern extraction
- `src/mcp_ticketer/core/project_config.py` (150 lines sampled) - Configuration review
- `src/mcp_ticketer/core/adapter.py` (150 lines sampled) - Interface analysis

**Total Files Read:** 6 strategic samples + 4 grep operations
**Memory-Efficient Techniques Used:**
- ✅ Grep pattern matching for milestone detection (avoided full file reading)
- ✅ Limited line reading (150-200 lines max per file)
- ✅ Used existing knowledge of MCP architecture from previous sessions
- ✅ Focused on interface definitions, not implementation details

**Research Methodology:**
- Discovery phase: Used grep to locate milestone-related code
- Analysis phase: Strategic sampling of key adapter files
- Pattern extraction: Identified common patterns without full reading
- Synthesis: Compiled findings into comprehensive specification

---

**End of Technical Specification**

**Document Metadata:**
- **Version:** 1.0
- **Last Updated:** 2025-12-04
- **Author:** Research Agent (Claude)
- **Review Status:** Ready for Implementation
- **Ticket:** 1M-607
