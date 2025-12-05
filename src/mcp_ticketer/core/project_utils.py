"""Utilities for project conversion and backwards compatibility.

This module provides conversion functions between the legacy Epic model and
the new Project model, ensuring backward compatibility during the migration
to unified project support.

The conversions maintain semantic equivalence while mapping between the
simpler Epic structure and the richer Project model with additional fields
for visibility, scope, ownership, and statistics.

Example:
    >>> from mcp_ticketer.core.models import Epic, Priority
    >>> from mcp_ticketer.core.project_utils import epic_to_project
    >>>
    >>> epic = Epic(
    ...     epic_id="epic-123",
    ...     title="User Authentication",
    ...     priority=Priority.HIGH
    ... )
    >>> project = epic_to_project(epic)
    >>> print(project.scope)  # ProjectScope.TEAM (default)

"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Epic, Project

from .models import ProjectScope, ProjectState, TicketState


def epic_to_project(epic: Epic) -> Project:
    """Convert Epic model to Project model for backwards compatibility.

    Maps legacy Epic fields to the new Project structure with sensible defaults
    for new fields not present in Epic.

    Field Mappings:
        - epic.id -> project.id
        - epic.id -> project.platform_id
        - epic.title -> project.name
        - epic.description -> project.description
        - epic.state -> project.state (via state mapping)
        - epic.url -> project.url
        - epic.created_at -> project.created_at
        - epic.updated_at -> project.updated_at
        - epic.target_date -> project.target_date
        - epic.child_issues -> project.child_issues

    New fields receive defaults:
        - scope: ProjectScope.TEAM (epics are team-level by convention)
        - visibility: ProjectVisibility.TEAM
        - platform: Extracted from epic.metadata or "unknown"

    Args:
        epic: Epic instance to convert

    Returns:
        Project instance with equivalent data

    Example:
        >>> epic = Epic(
        ...     epic_id="linear-epic-123",
        ...     title="Q4 Features",
        ...     state="in_progress",
        ...     child_issues=["issue-1", "issue-2"]
        ... )
        >>> project = epic_to_project(epic)
        >>> project.name == epic.title
        True
        >>> project.scope == ProjectScope.TEAM
        True

    """
    from .models import Project, ProjectVisibility

    # Extract platform from metadata if available
    platform = epic.metadata.get("platform", "unknown") if epic.metadata else "unknown"

    # Map epic state to project state
    state = _map_epic_state_to_project(epic.state)

    return Project(
        id=epic.id or "",
        platform=platform,
        platform_id=epic.id or "",
        scope=ProjectScope.TEAM,  # Default for epics
        name=epic.title,
        description=epic.description,
        state=state,
        visibility=ProjectVisibility.TEAM,  # Default visibility
        url=getattr(epic.metadata, "url", None) if epic.metadata else None,
        created_at=epic.created_at,
        updated_at=epic.updated_at,
        target_date=(
            getattr(epic.metadata, "target_date", None) if epic.metadata else None
        ),
        completed_at=(
            getattr(epic.metadata, "completed_at", None) if epic.metadata else None
        ),
        child_issues=epic.child_issues or [],
        extra_data={"original_type": "epic", **epic.metadata} if epic.metadata else {},
    )


def project_to_epic(project: Project) -> Epic:
    """Convert Project model back to Epic for backwards compatibility.

    Maps Project fields back to the simpler Epic structure, preserving data
    in metadata where Epic doesn't have direct field equivalents.

    Field Mappings:
        - project.id -> epic.id
        - project.name -> epic.title
        - project.description -> epic.description
        - project.state -> epic.state (via state mapping)
        - project.child_issues -> epic.child_issues

    Additional project data stored in metadata:
        - platform, scope, visibility, ownership fields
        - Stored under metadata["project_data"]

    Args:
        project: Project instance to convert

    Returns:
        Epic instance with equivalent core data

    Example:
        >>> from .models import ProjectScope, ProjectState
        >>> project = Project(
        ...     id="proj-123",
        ...     platform="linear",
        ...     platform_id="abc123",
        ...     scope=ProjectScope.TEAM,
        ...     name="Q4 Features",
        ...     state=ProjectState.ACTIVE
        ... )
        >>> epic = project_to_epic(project)
        >>> epic.title == project.name
        True
        >>> epic.metadata["project_data"]["platform"] == "linear"
        True

    """
    from .models import Epic

    # Map project state back to epic state string
    state = _map_project_state_to_epic(project.state)

    # Build metadata with project-specific data
    metadata = {
        "platform": project.platform,
        "url": project.url,
        "target_date": project.target_date,
        "completed_at": project.completed_at,
        "project_data": {
            "scope": project.scope,
            "visibility": project.visibility,
            "owner_id": project.owner_id,
            "owner_name": project.owner_name,
            "team_id": project.team_id,
            "team_name": project.team_name,
            "platform_id": project.platform_id,
        },
        **project.extra_data,
    }

    return Epic(
        id=project.id,
        title=project.name,
        description=project.description,
        state=state,
        created_at=project.created_at,
        updated_at=project.updated_at,
        child_issues=project.child_issues,
        metadata=metadata,
    )


def _map_epic_state_to_project(epic_state: str | None) -> ProjectState:
    """Map epic state string to ProjectState enum.

    Provides flexible mapping from various platform-specific epic states
    to the standardized ProjectState values.

    State Mappings:
        - "planned", "backlog" -> PLANNED
        - "in_progress", "active", "started" -> ACTIVE
        - "completed", "done" -> COMPLETED
        - "archived" -> ARCHIVED
        - "cancelled", "canceled" -> CANCELLED

    Args:
        epic_state: Epic state string (case-insensitive)

    Returns:
        Corresponding ProjectState, defaults to PLANNED if unknown

    Example:
        >>> _map_epic_state_to_project("in_progress")
        <ProjectState.ACTIVE: 'active'>
        >>> _map_epic_state_to_project("Done")
        <ProjectState.COMPLETED: 'completed'>
        >>> _map_epic_state_to_project(None)
        <ProjectState.PLANNED: 'planned'>

    """
    if not epic_state:
        return ProjectState.PLANNED

    # Normalize to lowercase for case-insensitive matching
    normalized = epic_state.lower().strip()

    # State mapping dictionary
    mapping = {
        # Planned states
        "planned": ProjectState.PLANNED,
        "backlog": ProjectState.PLANNED,
        "todo": ProjectState.PLANNED,
        # Active states
        "in_progress": ProjectState.ACTIVE,
        "active": ProjectState.ACTIVE,
        "started": ProjectState.ACTIVE,
        "in progress": ProjectState.ACTIVE,
        # Completed states
        "completed": ProjectState.COMPLETED,
        "done": ProjectState.COMPLETED,
        "finished": ProjectState.COMPLETED,
        # Archived states
        "archived": ProjectState.ARCHIVED,
        "archive": ProjectState.ARCHIVED,
        # Cancelled states
        "cancelled": ProjectState.CANCELLED,
        "canceled": ProjectState.CANCELLED,
        "dropped": ProjectState.CANCELLED,
    }

    return mapping.get(normalized, ProjectState.PLANNED)


def _map_project_state_to_epic(project_state: ProjectState | str) -> TicketState:
    """Map ProjectState back to TicketState enum for Epic.

    Converts ProjectState enum values to TicketState enum values
    suitable for Epic model which uses TicketState.

    Args:
        project_state: ProjectState enum or string value

    Returns:
        TicketState enum value compatible with Epic model

    Example:
        >>> _map_project_state_to_epic(ProjectState.ACTIVE)
        <TicketState.IN_PROGRESS: 'in_progress'>
        >>> _map_project_state_to_epic(ProjectState.COMPLETED)
        <TicketState.DONE: 'done'>

    """
    # Handle both enum and string inputs
    if isinstance(project_state, str):
        try:
            project_state = ProjectState(project_state)
        except ValueError:
            # If invalid string, return default
            return TicketState.OPEN

    # Map ProjectState to TicketState
    mapping = {
        ProjectState.PLANNED: TicketState.OPEN,
        ProjectState.ACTIVE: TicketState.IN_PROGRESS,
        ProjectState.COMPLETED: TicketState.DONE,
        ProjectState.ARCHIVED: TicketState.CLOSED,
        ProjectState.CANCELLED: TicketState.CLOSED,
    }

    return mapping.get(project_state, TicketState.OPEN)
