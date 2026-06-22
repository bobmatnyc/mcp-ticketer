"""Data mappers for converting between Plane and mcp-ticketer models."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from ...core.models import (
    Comment,
    Epic,
    Milestone,
    Task,
    TicketState,
    TicketType,
)
from .types import (
    GROUP_TO_STATE,
    PlaneStateGroup,
    map_priority_from_plane,
    refine_state_from_name,
)

logger = logging.getLogger(__name__)


def parse_plane_datetime(date_str: str | None) -> datetime | None:
    """Parse a Plane datetime / date string into a datetime.

    Plane returns ISO 8601 timestamps (e.g. "2024-11-15T10:30:00.000000Z") and
    plain dates (e.g. "2024-11-15") for ``target_date``.

    Args:
        date_str: ISO 8601 datetime/date string, or None.

    Returns:
        Parsed datetime, or None on failure.

    """
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        logger.warning("Failed to parse Plane datetime '%s'", date_str)
        return None


def map_plane_issue_to_task(
    issue: dict[str, Any],
    state_by_id: dict[str, dict[str, Any]] | None = None,
) -> Task:
    """Map a Plane issue payload to a universal Task.

    The ticket type is derived from the presence of a parent: an issue with a
    ``parent`` is a sub-issue (TASK), otherwise it is a standard ISSUE.

    Args:
        issue: Plane issue payload.
        state_by_id: Optional mapping of state UUID -> state record, used to
            resolve the issue's universal state from its state group and name.

    Returns:
        Task model instance.

    """
    parent_id = issue.get("parent")
    ticket_type = TicketType.TASK if parent_id else TicketType.ISSUE

    state = _resolve_issue_state(issue, state_by_id)
    priority = map_priority_from_plane(issue.get("priority"))

    assignees = issue.get("assignees") or []
    assignee = assignees[0] if assignees else None

    labels = issue.get("labels") or []

    return Task(
        id=issue.get("id"),
        title=issue.get("name", ""),
        description=issue.get("description_html") or issue.get("description_stripped"),
        state=state,
        priority=priority,
        tags=[str(label) for label in labels],
        assignee=assignee,
        ticket_type=ticket_type,
        parent_issue=parent_id if ticket_type == TicketType.TASK else None,
        parent_epic=issue.get("project") if ticket_type == TicketType.ISSUE else None,
        milestone_id=issue.get("module"),
        created_at=parse_plane_datetime(issue.get("created_at")),
        updated_at=parse_plane_datetime(issue.get("updated_at")),
        metadata={
            "plane_id": issue.get("id"),
            "plane_sequence_id": issue.get("sequence_id"),
            "plane_project": issue.get("project"),
            "plane_workspace": issue.get("workspace"),
            "plane_state_id": issue.get("state"),
            "plane_priority": issue.get("priority"),
            "plane_target_date": issue.get("target_date"),
            "plane_assignees": assignees,
            "plane_labels": labels,
            "plane_parent": parent_id,
        },
    )


def _resolve_issue_state(
    issue: dict[str, Any],
    state_by_id: dict[str, dict[str, Any]] | None,
) -> TicketState:
    """Resolve an issue's universal state from its Plane state record.

    Args:
        issue: Plane issue payload.
        state_by_id: Optional mapping of state UUID -> state record.

    Returns:
        Universal ticket state (defaults to OPEN when unknown).

    """
    state_id = issue.get("state")
    if not state_id or not state_by_id:
        return TicketState.OPEN

    state_record = state_by_id.get(state_id)
    if not state_record:
        return TicketState.OPEN

    group = state_record.get("group", "")
    name = state_record.get("name")

    try:
        base_state = GROUP_TO_STATE[PlaneStateGroup(group)]
    except ValueError:
        return TicketState.OPEN

    return refine_state_from_name(base_state, name)


def map_task_to_plane_issue(
    task: Task,
    state_id: str | None = None,
    assignee_ids: list[str] | None = None,
    label_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a Plane issue create/update payload from a Task.

    Args:
        task: Task model instance.
        state_id: Resolved Plane state UUID (optional).
        assignee_ids: Resolved Plane assignee UUIDs (optional).
        label_ids: Resolved Plane label UUIDs (optional).

    Returns:
        Plane issue payload for create/update.

    """
    from .types import map_priority_to_plane

    payload: dict[str, Any] = {"name": task.title}

    if task.description is not None:
        payload["description_html"] = task.description

    payload["priority"] = map_priority_to_plane(task.priority)

    if state_id:
        payload["state"] = state_id

    if assignee_ids is not None:
        payload["assignees"] = assignee_ids

    if label_ids is not None:
        payload["labels"] = label_ids

    if task.parent_issue:
        payload["parent"] = task.parent_issue

    target_date = task.metadata.get("plane_target_date")
    if target_date:
        payload["target_date"] = target_date

    return payload


def map_plane_comment_to_comment(comment: dict[str, Any], issue_id: str) -> Comment:
    """Map a Plane issue comment to a universal Comment.

    Args:
        comment: Plane comment payload.
        issue_id: Parent issue UUID.

    Returns:
        Comment model instance.

    """
    return Comment(
        id=comment.get("id"),
        ticket_id=issue_id,
        author=comment.get("actor") or comment.get("created_by"),
        content=comment.get("comment_html") or comment.get("comment_stripped") or "",
        created_at=parse_plane_datetime(comment.get("created_at")),
        metadata={
            "plane_id": comment.get("id"),
            "plane_actor": comment.get("actor"),
            "plane_created_by": comment.get("created_by"),
        },
    )


def map_plane_module_to_milestone(module: dict[str, Any]) -> Milestone:
    """Map a Plane module to a universal Milestone.

    Plane modules are the closest native concept to a milestone: a named
    grouping of issues with optional start/target dates and a status.

    Args:
        module: Plane module payload.

    Returns:
        Milestone model instance.

    """
    total = module.get("total_issues")
    completed = module.get("completed_issues")
    progress = 0.0
    if isinstance(total, int) and total > 0 and isinstance(completed, int):
        progress = round((completed / total) * 100.0, 1)

    return Milestone(
        id=module.get("id"),
        name=module.get("name", ""),
        target_date=parse_plane_datetime(module.get("target_date")),
        state=_map_module_status(module.get("status")),
        description=module.get("description") or "",
        total_issues=total if isinstance(total, int) else 0,
        closed_issues=completed if isinstance(completed, int) else 0,
        progress_pct=progress,
        project_id=module.get("project"),
        created_at=parse_plane_datetime(module.get("created_at")),
        updated_at=parse_plane_datetime(module.get("updated_at")),
        platform_data={
            "plane_id": module.get("id"),
            "plane_status": module.get("status"),
            "plane_start_date": module.get("start_date"),
            "plane_target_date": module.get("target_date"),
            "plane_project": module.get("project"),
            "plane_workspace": module.get("workspace"),
        },
    )


# Plane module status -> universal milestone state.
_MODULE_STATUS_TO_STATE = {
    "backlog": "open",
    "planned": "open",
    "in-progress": "active",
    "paused": "active",
    "completed": "completed",
    "cancelled": "closed",
}


def _map_module_status(status: str | None) -> str:
    """Map a Plane module status to a universal milestone state.

    Args:
        status: Plane module status string.

    Returns:
        Universal milestone state (open/active/completed/closed).

    """
    if not status:
        return "open"
    return _MODULE_STATUS_TO_STATE.get(status.lower(), "open")


def map_plane_project_to_epic(project: dict[str, Any]) -> Epic:
    """Map a Plane project payload to an Epic.

    Plane projects are the top-level container, so they map to the universal
    Epic concept (used by ``project_list`` / ``get_epic``).

    Args:
        project: Plane project payload.

    Returns:
        Epic model instance.

    """
    return Epic(
        id=project.get("id"),
        title=project.get("name", ""),
        description=project.get("description"),
        state=TicketState.OPEN,
        created_at=parse_plane_datetime(project.get("created_at")),
        updated_at=parse_plane_datetime(project.get("updated_at")),
        metadata={
            "plane_id": project.get("id"),
            "plane_identifier": project.get("identifier"),
            "plane_workspace": project.get("workspace"),
        },
    )
