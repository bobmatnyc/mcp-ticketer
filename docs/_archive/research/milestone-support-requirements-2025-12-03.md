# Milestone Support Requirements for mcp-ticketer

**Research Date**: 2025-12-03
**Researcher**: Claude (Research Agent)
**Objective**: Design comprehensive milestone support for mcp-ticketer CLI and MCP integration
**Linear Project**: [mcp-ticketer](https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/issues)

---

## Executive Summary

This research investigates Linear's ProjectMilestone API capabilities and designs a complete implementation plan for milestone support in mcp-ticketer. Key findings:

1. **Linear API Support**: Linear has native `ProjectMilestone` type with full CRUD operations via GraphQL
2. **Current State**: GitHub adapter has complete milestone support; Linear adapter has zero milestone code
3. **Architecture**: Milestones are project-scoped entities that group issues (parallel to project, not hierarchical)
4. **Implementation Scope**: ~800-1,200 LOC across adapter, CLI, and MCP layers
5. **Timeline Estimate**: 2-3 days for complete implementation and testing

**Critical Finding**: Milestones in Linear are **sub-entities of projects**, not top-level hierarchy items like Epics. This is different from GitHub where milestones ARE the epic equivalent.

---

## 1. Linear API ProjectMilestone Capabilities

### 1.1 GraphQL Type Definition

Based on Linear's GraphQL schema and documentation:

```graphql
type ProjectMilestone {
  id: ID!
  name: String!
  description: String
  sortOrder: Float!
  targetDate: TimelessDate
  progress: Float!
  status: String
  documentContent: String
  createdAt: DateTime!
  updatedAt: DateTime!
  project: Project!
}
```

### 1.2 Key Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | UUID | Yes | Unique identifier |
| `name` | String | Yes | Milestone name |
| `description` | String | No | Markdown description |
| `targetDate` | Date | No | Planned completion date (YYYY-MM-DD) |
| `progress` | Float | Auto | Calculated % of completed issues (0.0-1.0) |
| `status` | String | Auto | Current status |
| `sortOrder` | Float | Auto | Order within project |
| `project` | Project | Yes | Parent project (required relationship) |
| `createdAt` | DateTime | Auto | Creation timestamp |
| `updatedAt` | DateTime | Auto | Last modification timestamp |

### 1.3 Available Mutations

Linear provides standard CRUD mutations:

```graphql
# Create milestone
mutation ProjectMilestoneCreate {
  projectMilestoneCreate(input: ProjectMilestoneCreateInput!) {
    success
    projectMilestone {
      id
      name
      description
      targetDate
      progress
      project { id name }
    }
  }
}

# Update milestone
mutation ProjectMilestoneUpdate {
  projectMilestoneUpdate(id: String!, input: ProjectMilestoneUpdateInput!) {
    success
    projectMilestone {
      id
      name
      # ... fields
    }
  }
}

# Delete milestone
mutation ProjectMilestoneDelete {
  projectMilestoneDelete(id: String!) {
    success
  }
}
```

### 1.4 Input Types

**ProjectMilestoneCreateInput**:
```graphql
input ProjectMilestoneCreateInput {
  projectId: String!      # Required: parent project UUID
  name: String!           # Required: milestone name
  description: String     # Optional: markdown description
  targetDate: TimelessDate  # Optional: YYYY-MM-DD format
  sortOrder: Float        # Optional: custom ordering
}
```

**ProjectMilestoneUpdateInput**:
```graphql
input ProjectMilestoneUpdateInput {
  name: String
  description: String
  targetDate: TimelessDate
  sortOrder: Float
}
```

### 1.5 Queries

```graphql
# Get single milestone
query ProjectMilestone($id: String!) {
  projectMilestone(id: $id) {
    id
    name
    description
    targetDate
    progress
    project { id name }
  }
}

# List milestones for a project
query ProjectMilestones($projectId: String!, $first: Int) {
  project(id: $projectId) {
    projectMilestones(first: $first) {
      nodes {
        id
        name
        targetDate
        progress
      }
    }
  }
}
```

### 1.6 Issue Association

Issues link to milestones via `projectMilestoneId` field:

```graphql
mutation IssueUpdate {
  issueUpdate(id: $issueId, input: {
    projectMilestoneId: $milestoneId  # UUID of milestone
  }) {
    success
    issue {
      id
      projectMilestone {
        id
        name
      }
    }
  }
}
```

---

## 2. Current mcp-ticketer Implementation Analysis

### 2.1 GitHub Adapter (Existing Milestone Support)

**Location**: `src/mcp_ticketer/adapters/github.py`

**Key Methods** (COMPREHENSIVE):
- `_milestone_to_epic(milestone: dict) -> Epic` - Maps GitHub milestones to Epic model
- `create_milestone(epic: Epic) -> Epic` - Creates new milestone
- `get_milestone(milestone_number: int) -> Epic | None` - Fetches milestone
- `list_milestones(state: str, limit: int, offset: int) -> list[Epic]` - Lists milestones
- `update_milestone(milestone_number: int, updates: dict) -> Epic | None` - Updates milestone
- `delete_epic(epic_id: str) -> bool` - Deletes milestone (named delete_epic for consistency)
- `add_attachment_reference_to_milestone(...)` - Attaches files to milestone description

**Pattern**: GitHub treats milestones as Epic equivalents (top-level hierarchy)

### 2.2 Linear Adapter (NO Milestone Support)

**Location**: `src/mcp_ticketer/adapters/linear/adapter.py`

**Milestone Code**: **ZERO** - No milestone-related methods exist

**Relevant Patterns from Epic (Project) Implementation**:
- `_create_epic(epic: Epic) -> Epic` - Uses `projectCreate` mutation (lines 1740-1826)
- `update_epic(epic_id: str, updates: dict) -> Epic | None` - Uses `projectUpdate` mutation (lines 1828+)
- `get_epic(epic_id: str, include_issues: bool) -> Epic | None` - Fetches project details (line 492+)
- `list_epics(...)` - Lists projects with filters (line 3180+)

**Key Insight**: Linear adapter already has robust project (epic) management that can serve as template for milestone implementation.

### 2.3 Core Models

**Location**: `src/mcp_ticketer/core/models.py`

**Epic Model** (lines 243-273):
```python
class Epic(BaseTicket):
    """Epic - highest level container for strategic work initiatives.

    Platform Mappings:
    - Linear: Projects (with issues as children)
    - JIRA: Epics (with stories/tasks as children)
    - GitHub: Milestones (with issues as children)
    """

    ticket_type: TicketType = Field(default=TicketType.EPIC, frozen=True)
    child_issues: list[str] = Field(default_factory=list)
```

**Milestone Model**: **DOES NOT EXIST** - Needs to be created

### 2.4 CLI Commands

**Location**: `src/mcp_ticketer/cli/`

**Existing Epic Commands**: **NONE** - No CLI commands for epic/project management exist
**Milestone Commands**: **NONE** - No CLI commands for milestone management exist

**Ticket Commands** (`src/mcp_ticketer/cli/ticket_commands.py`): Exists but doesn't cover epics/milestones

### 2.5 MCP Tools

**Location**: `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py`

**Existing Pattern** (v2.0.0):
```python
@mcp.tool()
async def hierarchy(
    entity_type: Literal["epic", "issue", "task"],
    action: Literal["create", "get", "list", "update", "delete",
                    "get_children", "get_parent", "get_tree"],
    # ... parameters
) -> dict[str, Any]:
    """Unified hierarchy management tool."""
```

**Milestone Support**: **NONE** - `entity_type` does not include "milestone"

---

## 3. Architecture Design

### 3.1 Milestone Hierarchy Position

**CRITICAL DECISION**: Milestones are **NOT** part of the Epic→Issue→Task hierarchy.

**Correct Model**:
```
Project (Epic)
├── Milestone 1
│   └── Issues (attached via projectMilestoneId)
├── Milestone 2
│   └── Issues
└── Issues (no milestone)
```

**Key Differences**:

| Platform | Epic Equivalent | Milestone |
|----------|----------------|-----------|
| **Linear** | Project | ProjectMilestone (child of Project) |
| **GitHub** | Milestone | N/A (Milestone IS the epic) |
| **JIRA** | Epic | Version/FixVersion (similar to milestone) |

**Design Implications**:
1. Milestones are **project-scoped entities**, not independent top-level items
2. Issues link to milestones via `projectMilestoneId` field (optional)
3. Milestones must have a parent `projectId` (required)
4. Cannot create milestones without an active project context

### 3.2 Data Model Design

**New Model** (to add to `core/models.py`):

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Milestone:
    """Project milestone - represents a stage or phase within a project.

    Milestones are project-scoped entities that group issues to track progress
    toward specific goals or deadlines. They are distinct from epics/projects.

    Platform Mappings:
    - Linear: ProjectMilestone (child of Project)
    - GitHub: Not applicable (GitHub milestones ARE epics in our model)
    - JIRA: Version or FixVersion

    Key Characteristics:
    - Must belong to a parent project (required relationship)
    - Issues can optionally link to milestone via projectMilestoneId
    - Progress is auto-calculated based on completed issues
    - Cannot exist independently (always project-scoped)

    Attributes:
        id: Unique milestone identifier (UUID for Linear)
        name: Milestone name/title (required)
        description: Detailed description in markdown format
        project_id: Parent project UUID (required)
        target_date: Planned completion date (optional, ISO format YYYY-MM-DD)
        progress: Completion percentage (0.0-1.0, auto-calculated)
        status: Current status (e.g., "active", "completed", "archived")
        sort_order: Display order within project (float for flexibility)
        created_at: Creation timestamp
        updated_at: Last modification timestamp
        metadata: Platform-specific additional data

    Example:
        >>> milestone = Milestone(
        ...     name="Beta Release",
        ...     description="Complete features for beta launch",
        ...     project_id="eac28953-c267-4e9d-8f9b-123456789012",
        ...     target_date="2025-03-15"
        ... )
    """

    # Core identification
    id: str
    name: str
    project_id: str  # Required: parent project UUID

    # Content
    description: str = ""

    # Dates and progress
    target_date: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0 (auto-calculated)

    # Status and ordering
    status: str = "active"  # active, completed, archived
    sort_order: float = 0.0

    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Platform-specific metadata
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert milestone to dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "project_id": self.project_id,
            "description": self.description,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "progress": self.progress,
            "status": self.status,
            "sort_order": self.sort_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata,
        }
```

### 3.3 Adapter Interface Extension

**Add to BaseAdapter** (`core/adapter.py`):

```python
class BaseAdapter:
    # ... existing methods

    # Milestone operations
    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create a new milestone within a project."""
        raise NotImplementedError("create_milestone not implemented")

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Retrieve milestone by ID."""
        raise NotImplementedError("get_milestone not implemented")

    async def update_milestone(
        self, milestone_id: str, updates: dict[str, Any]
    ) -> Milestone | None:
        """Update milestone fields."""
        raise NotImplementedError("update_milestone not implemented")

    async def delete_milestone(self, milestone_id: str) -> bool:
        """Delete milestone."""
        raise NotImplementedError("delete_milestone not implemented")

    async def list_milestones(
        self, project_id: str, limit: int = 20, offset: int = 0
    ) -> list[Milestone]:
        """List milestones for a project."""
        raise NotImplementedError("list_milestones not implemented")

    async def attach_issues_to_milestone(
        self, milestone_id: str, issue_ids: list[str]
    ) -> bool:
        """Attach multiple issues to a milestone."""
        raise NotImplementedError("attach_issues_to_milestone not implemented")
```

---

## 4. CLI Command Design

### 4.1 Command Structure

Following existing patterns from `mcp-ticketer ticket` and `mcp-ticketer platform`:

**Proposed Top-Level Command**:
```bash
mcp-ticketer milestone [OPTIONS] COMMAND [ARGS...]
```

**Alternative** (if we extend platform commands):
```bash
mcp-ticketer platform linear milestone [OPTIONS] COMMAND [ARGS...]
```

**Recommendation**: Use **top-level `milestone` command** for consistency with `ticket`, `project-update`, etc.

### 4.2 Subcommands

```bash
# Create milestone
mcp-ticketer milestone create <NAME> \
  --project <PROJECT_ID> \
  --description "Milestone description" \
  --date 2025-03-15 \
  --order 1.0

# Update milestone
mcp-ticketer milestone update <MILESTONE_ID> \
  --name "Updated Name" \
  --description "New description" \
  --date 2025-04-01 \
  --status completed

# Set/change date (convenience command)
mcp-ticketer milestone set-date <MILESTONE_ID> --date 2025-02-01

# Attach issues to milestone
mcp-ticketer milestone attach <MILESTONE_ID> \
  --issues ISSUE-123,ISSUE-456,ISSUE-789

# Detach issues from milestone
mcp-ticketer milestone detach <MILESTONE_ID> \
  --issues ISSUE-123

# List milestones in project
mcp-ticketer milestone list \
  --project <PROJECT_ID> \
  --limit 20 \
  --status active

# Get milestone details
mcp-ticketer milestone get <MILESTONE_ID> \
  --include-issues

# Delete milestone
mcp-ticketer milestone delete <MILESTONE_ID> \
  --confirm
```

### 4.3 Implementation File

**Location**: `src/mcp_ticketer/cli/milestone_commands.py`

**Structure** (following `ticket_commands.py` pattern):

```python
"""CLI commands for milestone management."""

import asyncio
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..core.adapter import get_adapter_instance
from ..core.models import Milestone
from ..core.project_config import ConfigResolver

console = Console()


@click.group()
def milestone():
    """Milestone management operations."""
    pass


@milestone.command()
@click.argument("name")
@click.option("--project", "-p", required=True, help="Project ID")
@click.option("--description", "-d", default="", help="Milestone description")
@click.option("--date", "-t", help="Target date (YYYY-MM-DD)")
@click.option("--order", type=float, default=0.0, help="Sort order")
def create(name: str, project: str, description: str, date: Optional[str], order: float):
    """Create a new milestone."""
    async def _create():
        adapter = await get_adapter_instance()

        # Parse target date if provided
        target_date = None
        if date:
            target_date = datetime.fromisoformat(date)

        # Create milestone object
        milestone = Milestone(
            id="",  # Will be generated by adapter
            name=name,
            project_id=project,
            description=description,
            target_date=target_date,
            sort_order=order,
        )

        # Create via adapter
        created = await adapter.create_milestone(milestone)

        console.print(f"[green]✓[/green] Created milestone: {created.id}")
        console.print(f"  Name: {created.name}")
        console.print(f"  Project: {created.project_id}")
        if created.target_date:
            console.print(f"  Target: {created.target_date.date()}")

    asyncio.run(_create())


@milestone.command()
@click.argument("milestone_id")
@click.option("--name", "-n", help="New milestone name")
@click.option("--description", "-d", help="New description")
@click.option("--date", "-t", help="New target date (YYYY-MM-DD)")
@click.option("--status", help="Milestone status")
def update(milestone_id: str, name: Optional[str], description: Optional[str],
           date: Optional[str], status: Optional[str]):
    """Update milestone fields."""
    async def _update():
        adapter = await get_adapter_instance()

        # Build updates dict
        updates = {}
        if name:
            updates["name"] = name
        if description:
            updates["description"] = description
        if date:
            updates["target_date"] = datetime.fromisoformat(date)
        if status:
            updates["status"] = status

        # Update via adapter
        updated = await adapter.update_milestone(milestone_id, updates)

        if updated:
            console.print(f"[green]✓[/green] Updated milestone: {updated.id}")
        else:
            console.print(f"[red]✗[/red] Milestone not found: {milestone_id}")

    asyncio.run(_update())


@milestone.command()
@click.argument("milestone_id")
@click.option("--issues", "-i", required=True, help="Comma-separated issue IDs")
def attach(milestone_id: str, issues: str):
    """Attach issues to milestone."""
    async def _attach():
        adapter = await get_adapter_instance()
        issue_ids = [i.strip() for i in issues.split(",")]

        success = await adapter.attach_issues_to_milestone(milestone_id, issue_ids)

        if success:
            console.print(f"[green]✓[/green] Attached {len(issue_ids)} issues to milestone")
        else:
            console.print(f"[red]✗[/red] Failed to attach issues")

    asyncio.run(_attach())


@milestone.command()
@click.option("--project", "-p", required=True, help="Project ID")
@click.option("--limit", "-l", type=int, default=20, help="Max results")
@click.option("--status", help="Filter by status")
def list(project: str, limit: int, status: Optional[str]):
    """List milestones in project."""
    async def _list():
        adapter = await get_adapter_instance()
        milestones = await adapter.list_milestones(project, limit=limit)

        if status:
            milestones = [m for m in milestones if m.status == status]

        table = Table(title=f"Milestones in {project}")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Target Date", style="yellow")
        table.add_column("Progress", style="green")
        table.add_column("Status", style="blue")

        for m in milestones:
            table.add_row(
                m.id,
                m.name,
                m.target_date.date().isoformat() if m.target_date else "-",
                f"{m.progress * 100:.0f}%",
                m.status,
            )

        console.print(table)

    asyncio.run(_list())


# ... additional commands (get, delete, set-date)
```

**Register in main CLI** (`src/mcp_ticketer/cli/main.py`):

```python
from .milestone_commands import milestone

app.add_command(milestone)
```

---

## 5. MCP Tool Design

### 5.1 Unified Tool Pattern

Following v2.0.0 consolidated tool pattern (like `hierarchy()`, `config()`, `ticket()`):

**Location**: `src/mcp_ticketer/mcp/server/tools/milestone_tools.py`

**Tool Signature**:

```python
@mcp.tool()
async def milestone(
    action: Literal["create", "get", "update", "delete", "list",
                    "attach_issues", "detach_issues", "set_date"],
    milestone_id: Optional[str] = None,
    name: Optional[str] = None,
    description: str = "",
    project_id: Optional[str] = None,
    target_date: Optional[str] = None,  # ISO format YYYY-MM-DD
    status: Optional[str] = None,
    sort_order: Optional[float] = None,
    issue_ids: Optional[list[str]] = None,  # For attach/detach
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Unified milestone management tool.

    This tool provides complete milestone lifecycle management within projects:
    - Create milestones with optional target dates
    - Update milestone properties (name, description, date, status)
    - List milestones within a project
    - Attach/detach issues to track milestone progress
    - Delete milestones when no longer needed

    **IMPORTANT**: Milestones are project-scoped entities in Linear.
    You MUST provide a project_id when creating milestones.

    Actions:
    - create: Create new milestone (requires: name, project_id)
    - get: Get milestone details (requires: milestone_id)
    - update: Update milestone fields (requires: milestone_id)
    - delete: Delete milestone (requires: milestone_id)
    - list: List milestones in project (requires: project_id)
    - attach_issues: Link issues to milestone (requires: milestone_id, issue_ids)
    - detach_issues: Unlink issues from milestone (requires: milestone_id, issue_ids)
    - set_date: Set/update target date (convenience action, requires: milestone_id, target_date)

    Args:
        action: Operation to perform
        milestone_id: Milestone UUID (for get/update/delete/attach/detach)
        name: Milestone name (for create/update)
        description: Markdown description (for create/update)
        project_id: Parent project UUID (REQUIRED for create/list)
        target_date: Target completion date in ISO format YYYY-MM-DD
        status: Milestone status (active, completed, archived)
        sort_order: Display order within project (float)
        issue_ids: List of issue IDs to attach/detach
        limit: Maximum results for list (default: 20, max: 100)
        offset: Pagination offset for list

    Returns:
        dict: Operation results with status, data, and metadata
            - status: "success" or "error"
            - data: Milestone object(s) or operation result
            - metadata: Adapter info, counts, etc.

    Examples:
        # Create milestone
        await milestone(
            action="create",
            name="Beta Release",
            description="Complete features for beta",
            project_id="eac28953-c267-4e9d-8f9b-123456789012",
            target_date="2025-03-15"
        )

        # Update milestone
        await milestone(
            action="update",
            milestone_id="milestone-uuid",
            name="Updated Beta Release",
            target_date="2025-04-01"
        )

        # List milestones
        await milestone(
            action="list",
            project_id="eac28953-c267-4e9d-8f9b-123456789012",
            limit=10
        )

        # Attach issues
        await milestone(
            action="attach_issues",
            milestone_id="milestone-uuid",
            issue_ids=["1M-123", "1M-456", "1M-789"]
        )

        # Set date (convenience)
        await milestone(
            action="set_date",
            milestone_id="milestone-uuid",
            target_date="2025-05-01"
        )

    Migration from old tools (if any existed):
        N/A - This is a new tool, no previous milestone tools existed

    Token Savings:
        N/A - First implementation, no consolidation metrics

    See: docs/mcp-api-reference.md#milestone-response-format
    """
    # Implementation here
    pass
```

### 5.2 Implementation Structure

```python
async def milestone(action: str, **kwargs) -> dict[str, Any]:
    """Implementation."""

    # Route to action handlers
    if action == "create":
        return await _milestone_create(**kwargs)
    elif action == "get":
        return await _milestone_get(**kwargs)
    elif action == "update":
        return await _milestone_update(**kwargs)
    elif action == "delete":
        return await _milestone_delete(**kwargs)
    elif action == "list":
        return await _milestone_list(**kwargs)
    elif action == "attach_issues":
        return await _milestone_attach_issues(**kwargs)
    elif action == "detach_issues":
        return await _milestone_detach_issues(**kwargs)
    elif action == "set_date":
        return await _milestone_set_date(**kwargs)
    else:
        raise ValueError(f"Invalid action: {action}")


async def _milestone_create(
    name: str,
    project_id: str,
    description: str = "",
    target_date: Optional[str] = None,
    sort_order: float = 0.0,
    **kwargs,
) -> dict[str, Any]:
    """Create milestone handler."""
    adapter = await get_adapter()

    # Validate required parameters
    if not name:
        return {"status": "error", "error": "name is required"}
    if not project_id:
        return {"status": "error", "error": "project_id is required"}

    # Parse target date
    target_dt = None
    if target_date:
        try:
            target_dt = datetime.fromisoformat(target_date)
        except ValueError as e:
            return {"status": "error", "error": f"Invalid date format: {e}"}

    # Create milestone
    milestone = Milestone(
        id="",  # Generated by adapter
        name=name,
        project_id=project_id,
        description=description,
        target_date=target_dt,
        sort_order=sort_order,
    )

    try:
        created = await adapter.create_milestone(milestone)
        return {
            "status": "success",
            "data": created.to_dict(),
            "metadata": {
                "adapter": adapter.adapter_type,
                "milestone_id": created.id,
            },
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ... additional action handlers
```

### 5.3 Response Format

**Standard Response Schema**:

```typescript
interface MilestoneResponse {
  status: "success" | "error";
  data?: Milestone | Milestone[] | boolean;
  error?: string;
  metadata?: {
    adapter: string;
    milestone_id?: string;
    count?: number;
    project_id?: string;
  };
}

interface Milestone {
  id: string;
  name: string;
  project_id: string;
  description: string;
  target_date: string | null;  // ISO format
  progress: number;  // 0.0 to 1.0
  status: string;
  sort_order: number;
  created_at: string;  // ISO format
  updated_at: string;  // ISO format
  metadata: Record<string, any>;
}
```

---

## 6. Linear Adapter Integration

### 6.1 Implementation Overview

**Location**: `src/mcp_ticketer/adapters/linear/adapter.py`

**Methods to Implement** (~400 LOC):

```python
class LinearAdapter(BaseAdapter):
    # ... existing methods

    async def create_milestone(self, milestone: Milestone) -> Milestone:
        """Create Linear project milestone."""
        # Implementation

    async def get_milestone(self, milestone_id: str) -> Milestone | None:
        """Get Linear project milestone by ID."""
        # Implementation

    async def update_milestone(
        self, milestone_id: str, updates: dict[str, Any]
    ) -> Milestone | None:
        """Update Linear project milestone."""
        # Implementation

    async def delete_milestone(self, milestone_id: str) -> bool:
        """Delete Linear project milestone."""
        # Implementation

    async def list_milestones(
        self, project_id: str, limit: int = 20, offset: int = 0
    ) -> list[Milestone]:
        """List Linear project milestones."""
        # Implementation

    async def attach_issues_to_milestone(
        self, milestone_id: str, issue_ids: list[str]
    ) -> bool:
        """Attach issues to Linear milestone."""
        # Implementation
```

### 6.2 GraphQL Queries to Add

**Location**: `src/mcp_ticketer/adapters/linear/queries.py`

```python
# Milestone fragment
PROJECT_MILESTONE_FRAGMENT = """
    fragment ProjectMilestoneFields on ProjectMilestone {
        id
        name
        description
        targetDate
        progress
        status
        sortOrder
        createdAt
        updatedAt
        project {
            id
            name
            slugId
        }
    }
"""

# Create mutation
CREATE_PROJECT_MILESTONE_MUTATION = (
    PROJECT_MILESTONE_FRAGMENT
    + """
    mutation ProjectMilestoneCreate($input: ProjectMilestoneCreateInput!) {
        projectMilestoneCreate(input: $input) {
            success
            projectMilestone {
                ...ProjectMilestoneFields
            }
        }
    }
"""
)

# Update mutation
UPDATE_PROJECT_MILESTONE_MUTATION = (
    PROJECT_MILESTONE_FRAGMENT
    + """
    mutation ProjectMilestoneUpdate($id: String!, $input: ProjectMilestoneUpdateInput!) {
        projectMilestoneUpdate(id: $id, input: $input) {
            success
            projectMilestone {
                ...ProjectMilestoneFields
            }
        }
    }
"""
)

# Delete mutation
DELETE_PROJECT_MILESTONE_MUTATION = """
    mutation ProjectMilestoneDelete($id: String!) {
        projectMilestoneDelete(id: $id) {
            success
        }
    }
"""

# Get query
GET_PROJECT_MILESTONE_QUERY = (
    PROJECT_MILESTONE_FRAGMENT
    + """
    query ProjectMilestone($id: String!) {
        projectMilestone(id: $id) {
            ...ProjectMilestoneFields
        }
    }
"""
)

# List query
LIST_PROJECT_MILESTONES_QUERY = (
    PROJECT_MILESTONE_FRAGMENT
    + """
    query ProjectMilestones($projectId: String!, $first: Int!, $after: String) {
        project(id: $projectId) {
            id
            name
            projectMilestones(first: $first, after: $after) {
                nodes {
                    ...ProjectMilestoneFields
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
"""
)
```

### 6.3 Mapper Functions

**Location**: `src/mcp_ticketer/adapters/linear/mappers.py`

```python
def map_linear_milestone_to_model(milestone_data: dict[str, Any]) -> Milestone:
    """Convert Linear ProjectMilestone data to Milestone model.

    Args:
        milestone_data: Raw ProjectMilestone data from Linear GraphQL API

    Returns:
        Milestone model instance
    """
    # Parse dates
    created_at = None
    if created := milestone_data.get("createdAt"):
        created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))

    updated_at = None
    if updated := milestone_data.get("updatedAt"):
        updated_at = datetime.fromisoformat(updated.replace("Z", "+00:00"))

    target_date = None
    if target := milestone_data.get("targetDate"):
        target_date = datetime.fromisoformat(target)

    # Extract project ID
    project = milestone_data.get("project", {})
    project_id = project.get("id", "")

    return Milestone(
        id=milestone_data["id"],
        name=milestone_data["name"],
        project_id=project_id,
        description=milestone_data.get("description", ""),
        target_date=target_date,
        progress=milestone_data.get("progress", 0.0),
        status=milestone_data.get("status", "active"),
        sort_order=milestone_data.get("sortOrder", 0.0),
        created_at=created_at,
        updated_at=updated_at,
        metadata={
            "linear": {
                "project_name": project.get("name"),
                "project_slug": project.get("slugId"),
            }
        },
    )
```

### 6.4 Example Implementation: create_milestone

```python
async def create_milestone(self, milestone: Milestone) -> Milestone:
    """Create a Linear project milestone.

    Args:
        milestone: Milestone object with name, project_id, and optional fields

    Returns:
        Created milestone with Linear-generated ID

    Raises:
        ValueError: If project_id is missing or invalid
    """
    # Validate project_id
    if not milestone.project_id:
        raise ValueError("project_id is required to create a milestone")

    # Validate project exists
    project = await self.get_epic(milestone.project_id, include_issues=False)
    if not project:
        raise ValueError(f"Project '{milestone.project_id}' not found")

    # Build mutation input
    milestone_input = {
        "projectId": milestone.project_id,
        "name": milestone.name,
    }

    if milestone.description:
        milestone_input["description"] = milestone.description

    if milestone.target_date:
        # Linear expects ISO date format (YYYY-MM-DD)
        milestone_input["targetDate"] = milestone.target_date.date().isoformat()

    if milestone.sort_order:
        milestone_input["sortOrder"] = milestone.sort_order

    # Execute mutation
    try:
        result = await self.client.execute_mutation(
            CREATE_PROJECT_MILESTONE_MUTATION,
            {"input": milestone_input}
        )

        if not result["projectMilestoneCreate"]["success"]:
            raise ValueError("Failed to create Linear project milestone")

        created_data = result["projectMilestoneCreate"]["projectMilestone"]
        return map_linear_milestone_to_model(created_data)

    except Exception as e:
        raise ValueError(f"Failed to create milestone: {e}") from e
```

### 6.5 Issue Attachment Implementation

```python
async def attach_issues_to_milestone(
    self, milestone_id: str, issue_ids: list[str]
) -> bool:
    """Attach multiple issues to a Linear milestone.

    This updates each issue's projectMilestoneId field to link them
    to the specified milestone.

    Args:
        milestone_id: UUID of the milestone
        issue_ids: List of issue identifiers (UUID or identifier like "1M-123")

    Returns:
        True if all issues were successfully attached, False otherwise

    Example:
        >>> await adapter.attach_issues_to_milestone(
        ...     "milestone-uuid",
        ...     ["1M-123", "1M-456", "1M-789"]
        ... )
        True
    """
    # Validate milestone exists
    milestone = await self.get_milestone(milestone_id)
    if not milestone:
        raise ValueError(f"Milestone '{milestone_id}' not found")

    # Update each issue
    success_count = 0
    for issue_id in issue_ids:
        try:
            # Resolve issue ID to UUID if necessary
            issue_uuid = await self._resolve_issue_id(issue_id)

            # Update issue with milestone ID
            update_result = await self.update_issue(issue_uuid, {
                "projectMilestoneId": milestone_id
            })

            if update_result:
                success_count += 1

        except Exception as e:
            logging.getLogger(__name__).warning(
                f"Failed to attach issue {issue_id} to milestone: {e}"
            )

    return success_count == len(issue_ids)
```

---

## 7. Implementation Plan

### 7.1 Files to Create/Modify

**New Files** (4):
1. `src/mcp_ticketer/cli/milestone_commands.py` (~300 LOC)
2. `src/mcp_ticketer/mcp/server/tools/milestone_tools.py` (~400 LOC)
3. `docs/milestone-user-guide.md` (~200 lines documentation)
4. `tests/test_milestone_*.py` (~400 LOC tests)

**Modified Files** (6):
1. `src/mcp_ticketer/core/models.py` (~80 LOC addition for Milestone class)
2. `src/mcp_ticketer/core/adapter.py` (~50 LOC for interface methods)
3. `src/mcp_ticketer/adapters/linear/adapter.py` (~400 LOC for implementation)
4. `src/mcp_ticketer/adapters/linear/queries.py` (~150 LOC for GraphQL queries)
5. `src/mcp_ticketer/adapters/linear/mappers.py` (~60 LOC for mapper)
6. `src/mcp_ticketer/cli/main.py` (~5 LOC to register command)

**Total Estimated LOC**: 800-1,200 LOC (excluding tests and docs)

### 7.2 Implementation Phases

**Phase 1: Core Models and Adapter Interface** (4 hours)
- [ ] Add `Milestone` dataclass to `core/models.py`
- [ ] Add milestone methods to `BaseAdapter` interface
- [ ] Add GraphQL queries to `linear/queries.py`
- [ ] Add mapper function to `linear/mappers.py`
- [ ] Unit tests for models and mappers

**Phase 2: Linear Adapter Implementation** (8 hours)
- [ ] Implement `create_milestone()`
- [ ] Implement `get_milestone()`
- [ ] Implement `update_milestone()`
- [ ] Implement `delete_milestone()`
- [ ] Implement `list_milestones()`
- [ ] Implement `attach_issues_to_milestone()`
- [ ] Integration tests with Linear API (use test workspace)

**Phase 3: MCP Tool Implementation** (4 hours)
- [ ] Create `milestone_tools.py` with unified `milestone()` tool
- [ ] Implement all action handlers (create, get, update, delete, list, attach, detach, set_date)
- [ ] Add response formatting and error handling
- [ ] Register tool in MCP server
- [ ] MCP tool tests

**Phase 4: CLI Commands** (6 hours)
- [ ] Create `milestone_commands.py` with Click commands
- [ ] Implement `create`, `update`, `list`, `get`, `delete` commands
- [ ] Implement `attach`, `detach`, `set-date` commands
- [ ] Add rich formatting for output tables
- [ ] Register commands in main CLI
- [ ] CLI integration tests

**Phase 5: Documentation and Testing** (4 hours)
- [ ] Write user guide (`docs/milestone-user-guide.md`)
- [ ] Update `docs/mcp-api-reference.md` with milestone tool
- [ ] Add examples to documentation
- [ ] End-to-end testing with real Linear workspace
- [ ] Update CHANGELOG.md

**Total Estimated Time**: 26 hours (~3 days for single developer)

### 7.3 Testing Requirements

**Unit Tests**:
- Milestone model serialization/deserialization
- Mapper functions (Linear → Milestone)
- GraphQL query construction

**Integration Tests**:
- Linear API create/update/delete operations
- Issue attachment via projectMilestoneId
- Error handling (invalid project_id, missing fields)

**MCP Tool Tests**:
- Action routing
- Parameter validation
- Response formatting

**CLI Tests**:
- Command parsing and validation
- Output formatting
- Error messaging

**End-to-End Tests**:
- Create milestone → attach issues → verify in Linear UI
- Update milestone date → verify via API
- Delete milestone → verify cleanup

### 7.4 Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|---------|------------|
| Linear API changes | Low | High | Pin to stable API version, monitor Linear changelog |
| UUID validation issues | Medium | Medium | Reuse existing `_validate_linear_uuid()` from adapter |
| Date parsing errors | Medium | Low | Use ISO format consistently, add validation |
| Project resolution failures | Medium | Medium | Validate project_id before creating milestone |
| Issue attachment race conditions | Low | Low | Use sequential updates, add retry logic |

---

## 8. Timeline Estimate

**Conservative Estimate**: 2-3 days (16-24 hours)

**Breakdown**:
- **Day 1 (8h)**: Phase 1 (models) + Phase 2 (adapter implementation)
- **Day 2 (8h)**: Phase 3 (MCP tool) + Phase 4 (CLI commands)
- **Day 3 (4-8h)**: Phase 5 (documentation, testing, polish)

**Fast-Track Estimate**: 1.5 days (12-16 hours) if skipping extensive documentation

---

## 9. Success Criteria

**Functional Requirements**:
- ✅ Create milestones within Linear projects via CLI and MCP
- ✅ Update milestone properties (name, description, date, status)
- ✅ List milestones for a given project
- ✅ Attach issues to milestones
- ✅ Delete milestones
- ✅ Set/change milestone target dates

**Quality Requirements**:
- ✅ 100% test coverage for new code
- ✅ Type hints on all functions
- ✅ Comprehensive error handling
- ✅ Rich CLI output with tables and colors
- ✅ Clear MCP tool documentation

**Integration Requirements**:
- ✅ Works with existing Linear adapter infrastructure
- ✅ Follows v2.0.0 unified tool pattern
- ✅ Compatible with existing project (epic) workflows
- ✅ Validates project_id before milestone operations

---

## 10. Example Usage Scenarios

### Scenario 1: Create Beta Release Milestone

**CLI**:
```bash
# Create milestone for Q1 Beta release
mcp-ticketer milestone create "Q1 Beta Release" \
  --project eac28953-c267-4e9d-8f9b-123456789012 \
  --description "Complete features for beta launch" \
  --date 2025-03-15

# Output:
# ✓ Created milestone: a1b2c3d4-e5f6-7890-abcd-ef1234567890
#   Name: Q1 Beta Release
#   Project: eac28953-c267-4e9d-8f9b-123456789012
#   Target: 2025-03-15
```

**MCP Tool**:
```python
result = await milestone(
    action="create",
    name="Q1 Beta Release",
    description="Complete features for beta launch",
    project_id="eac28953-c267-4e9d-8f9b-123456789012",
    target_date="2025-03-15"
)

# Result:
# {
#   "status": "success",
#   "data": {
#     "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#     "name": "Q1 Beta Release",
#     "project_id": "eac28953-c267-4e9d-8f9b-123456789012",
#     "description": "Complete features for beta launch",
#     "target_date": "2025-03-15",
#     "progress": 0.0,
#     "status": "active"
#   }
# }
```

### Scenario 2: Track Milestone Progress

**CLI**:
```bash
# Attach issues to milestone
mcp-ticketer milestone attach a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --issues 1M-123,1M-456,1M-789

# Output:
# ✓ Attached 3 issues to milestone

# Check progress
mcp-ticketer milestone get a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Output:
# Milestone: Q1 Beta Release
# ┌──────────┬────────────────────────────────────────┐
# │ Field    │ Value                                  │
# ├──────────┼────────────────────────────────────────┤
# │ ID       │ a1b2c3d4-e5f6-7890-abcd-ef1234567890   │
# │ Project  │ MCP Ticketer                           │
# │ Target   │ 2025-03-15                             │
# │ Progress │ 33% (1/3 issues completed)             │
# │ Status   │ active                                 │
# └──────────┴────────────────────────────────────────┘
```

**MCP Tool**:
```python
# Attach issues
await milestone(
    action="attach_issues",
    milestone_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    issue_ids=["1M-123", "1M-456", "1M-789"]
)

# Get progress
result = await milestone(
    action="get",
    milestone_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
)

# Result shows progress: 0.33 (33% complete)
```

### Scenario 3: Adjust Release Date

**CLI**:
```bash
# Push back release date
mcp-ticketer milestone set-date a1b2c3d4-e5f6-7890-abcd-ef1234567890 \
  --date 2025-04-01

# Output:
# ✓ Updated milestone target date: 2025-04-01
```

**MCP Tool**:
```python
# Convenience action
await milestone(
    action="set_date",
    milestone_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    target_date="2025-04-01"
)

# Or via update action
await milestone(
    action="update",
    milestone_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    target_date="2025-04-01",
    status="delayed"  # Optional: update status too
)
```

---

## 11. Key Insights and Recommendations

### 11.1 Critical Architectural Decisions

**Decision 1: Milestones are NOT top-level hierarchy entities**
- **Rationale**: In Linear, ProjectMilestones are sub-entities of Projects, not independent
- **Impact**: Milestones require parent `project_id` (cannot exist independently)
- **Implementation**: Validate project exists before creating milestone

**Decision 2: Do NOT extend Epic→Issue→Task hierarchy to include milestones**
- **Rationale**: Milestones are orthogonal to hierarchy (issues can belong to milestone AND have parent/children)
- **Impact**: Keep milestone operations separate from `hierarchy()` tool
- **Implementation**: Create dedicated `milestone()` tool, do not add to hierarchy tool

**Decision 3: Follow v2.0.0 unified tool pattern**
- **Rationale**: Consistency with existing codebase (hierarchy, config, ticket tools)
- **Impact**: Single `milestone()` function with action routing
- **Implementation**: 8 actions (create, get, update, delete, list, attach_issues, detach_issues, set_date)

### 11.2 Implementation Priorities

**High Priority** (Must Have):
1. Create milestone with project_id and target_date
2. List milestones in a project
3. Attach issues to milestone
4. Update milestone target_date

**Medium Priority** (Should Have):
1. Delete milestone
2. Detach issues from milestone
3. Update milestone status
4. Get single milestone details

**Low Priority** (Nice to Have):
1. Bulk issue attachment
2. Milestone sorting/reordering
3. Milestone progress calculation
4. Export milestone report

### 11.3 Technical Recommendations

**Recommendation 1: Reuse existing project resolution logic**
- Use `_resolve_project_id()` from Linear adapter
- Validates project UUID format
- Handles both UUID and slug-shortid formats

**Recommendation 2: Implement issue attachment as batch operation**
- Single GraphQL mutation per issue (no bulk mutation available)
- Use sequential updates with error collection
- Return success count and failed issue list

**Recommendation 3: Add comprehensive date validation**
- Accept ISO format YYYY-MM-DD
- Convert to Linear's `TimelessDate` type
- Validate date is in future (optional warning)

**Recommendation 4: Leverage existing error handling patterns**
- Reuse `AdapterError`, `ValidationError` from core
- Follow existing try/except patterns from epic operations
- Provide clear error messages with actionable fixes

### 11.4 Documentation Requirements

**User-Facing Documentation**:
- `docs/milestone-user-guide.md` - Complete user guide with examples
- `docs/mcp-api-reference.md` - MCP tool reference (add milestone section)
- `README.md` - Update features list to include milestone support

**Developer Documentation**:
- Inline docstrings on all new functions
- GraphQL query documentation
- Architecture decision records (ADRs) for key decisions

**Examples and Tutorials**:
- CLI usage examples for common workflows
- MCP tool usage examples with code snippets
- Video walkthrough (optional, future)

---

## 12. Future Enhancements

**Phase 2 Features** (Post-Launch):
1. **Milestone Templates**: Pre-defined milestone sets for common project types
2. **Bulk Operations**: Attach multiple issues with single CLI command
3. **Milestone Reports**: Generate progress reports with issue breakdowns
4. **Deadline Alerts**: CLI warnings for approaching milestone dates
5. **Milestone Dependencies**: Track dependencies between milestones
6. **Gantt Chart Export**: Export milestone timeline to visualization tools

**Multi-Platform Support**:
- JIRA adapter: Map to FixVersion/Version entities
- GitHub adapter: **NOT APPLICABLE** (GitHub milestones ARE epics in our model)
- Aitrackdown adapter: File-based milestone tracking

---

## 13. Appendix

### A. GraphQL Schema Reference

**Linear ProjectMilestone Type** (from Linear API v2025):
```graphql
type ProjectMilestone implements Node {
  id: ID!
  name: String!
  description: String
  documentContent: String
  sortOrder: Float!
  targetDate: TimelessDate
  progress: Float!
  status: String
  createdAt: DateTime!
  updatedAt: DateTime!
  archivedAt: DateTime

  project: Project!
  issues(
    filter: IssueFilter
    first: Int
    after: String
  ): IssueConnection!
}

input ProjectMilestoneCreateInput {
  projectId: String!
  name: String!
  description: String
  targetDate: TimelessDate
  sortOrder: Float
}

input ProjectMilestoneUpdateInput {
  name: String
  description: String
  targetDate: TimelessDate
  sortOrder: Float
}
```

### B. Related GitHub Issues

**Related Linear Issues** (to be created):
- `1M-XXX`: Add milestone support to Linear adapter
- `1M-XXX`: Add milestone CLI commands
- `1M-XXX`: Add milestone MCP tool
- `1M-XXX`: Update documentation for milestone support

### C. Research Artifacts

**Files Analyzed**:
- `src/mcp_ticketer/adapters/github.py` - GitHub milestone implementation (reference)
- `src/mcp_ticketer/adapters/linear/adapter.py` - Linear epic implementation (template)
- `src/mcp_ticketer/adapters/linear/queries.py` - GraphQL query patterns
- `src/mcp_ticketer/core/models.py` - Data model patterns
- `src/mcp_ticketer/mcp/server/tools/hierarchy_tools.py` - MCP tool patterns
- `src/mcp_ticketer/cli/ticket_commands.py` - CLI command patterns

**Memory Usage Statistics**:
- Files read: 6 (using strategic sampling)
- Grep operations: 12 (pattern-based discovery)
- WebSearch queries: 2 (Linear API documentation)
- Total token usage: ~76,000 tokens (well within memory limits)

---

## 14. Conclusion

This research provides a comprehensive blueprint for implementing milestone support in mcp-ticketer. The Linear API provides robust ProjectMilestone capabilities that map cleanly to our architecture. By following existing patterns from the GitHub adapter and v2.0.0 unified tools, we can deliver a consistent, high-quality milestone feature in 2-3 days of development time.

**Key Takeaways**:
1. Linear has full ProjectMilestone API support - no blockers
2. Implementation follows established patterns - low risk
3. Milestones are project-scoped, not hierarchical - important distinction
4. Unified tool pattern ensures consistency with v2.0.0 architecture
5. Estimated 800-1,200 LOC across adapter, CLI, and MCP layers

**Next Steps**:
1. Create Linear tickets for each implementation phase
2. Set up test Linear workspace for development
3. Begin Phase 1: Core models and adapter interface
4. Follow implementation plan sequentially through Phase 5

---

**Research completed**: 2025-12-03
**Researcher**: Claude (Research Agent)
**Status**: ✅ COMPLETE - Ready for implementation
