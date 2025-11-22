"""Data mappers for converting between Asana and mcp-ticketer models."""

import logging
from datetime import datetime
from typing import Any

from ...core.models import (
    Attachment,
    Comment,
    Epic,
    Priority,
    Task,
    TicketState,
    TicketType,
)
from .types import map_priority_from_asana, map_state_from_asana, map_state_to_asana

logger = logging.getLogger(__name__)


def parse_asana_datetime(date_str: str | None) -> datetime | None:
    """Parse Asana datetime string to datetime object.

    Args:
    ----
        date_str: ISO 8601 datetime string or None

    Returns:
    -------
        Parsed datetime or None

    """
    if not date_str:
        return None

    try:
        # Asana returns ISO 8601 format: "2024-11-15T10:30:00.000Z"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        logger.warning(f"Failed to parse Asana datetime '{date_str}': {e}")
        return None


def map_asana_project_to_epic(project: dict[str, Any]) -> Epic:
    """Map Asana project to Epic.

    Args:
    ----
        project: Asana project data

    Returns:
    -------
        Epic model instance

    """
    # Extract custom field for priority if exists
    priority = Priority.MEDIUM
    custom_fields = project.get("custom_fields", [])
    for field in custom_fields:
        if field.get("name", "").lower() == "priority" and field.get("enum_value"):
            priority = map_priority_from_asana(field["enum_value"].get("name"))
            break

    # Map project state (archived, current, on_hold) to TicketState
    archived = project.get("archived", False)
    state = TicketState.CLOSED if archived else TicketState.OPEN

    return Epic(
        id=project.get("gid"),
        title=project.get("name", ""),
        description=project.get("notes", ""),
        state=state,
        priority=priority,
        created_at=parse_asana_datetime(project.get("created_at")),
        updated_at=parse_asana_datetime(project.get("modified_at")),
        metadata={
            "asana_gid": project.get("gid"),
            "asana_permalink_url": project.get("permalink_url"),
            "asana_workspace_gid": project.get("workspace", {}).get("gid"),
            "asana_team_gid": (
                project.get("team", {}).get("gid") if project.get("team") else None
            ),
            "asana_color": project.get("color"),
            "asana_archived": archived,
            "asana_public": project.get("public", False),
        },
    )


def map_asana_task_to_task(task: dict[str, Any]) -> Task:
    """Map Asana task to Task.

    Detects task type based on hierarchy:
    - Has parent task → TASK (subtask)
    - No parent task → ISSUE (standard task)

    Args:
    ----
        task: Asana task data

    Returns:
    -------
        Task model instance

    """
    # Determine ticket type based on parent
    parent_task = task.get("parent")
    ticket_type = TicketType.TASK if parent_task else TicketType.ISSUE

    # Extract state from completed field AND Status custom field (Bug Fix #3)
    completed = task.get("completed", False)
    state = TicketState.OPEN
    custom_state = None

    # Check Status custom field first (if present)
    custom_fields = task.get("custom_fields", [])
    for field in custom_fields:
        if field.get("name", "").lower() == "status":
            enum_value = field.get("enum_value")
            if enum_value:
                custom_state = enum_value.get("name", "")
            break

    # Use enhanced state mapping that considers both Status field and completed boolean
    state = map_state_from_asana(completed, custom_state)

    # Extract priority from custom fields
    priority = Priority.MEDIUM
    for field in custom_fields:
        if field.get("name", "").lower() == "priority" and field.get("enum_value"):
            priority = map_priority_from_asana(field["enum_value"].get("name"))
            break

    # Extract tags
    tags = [tag.get("name", "") for tag in task.get("tags", []) if tag.get("name")]

    # Extract assignee
    assignee = None
    if task.get("assignee"):
        assignee = task["assignee"].get("gid")

    # Extract project (parent_epic for issues)
    parent_epic = None
    projects = task.get("projects", [])
    if projects and ticket_type == TicketType.ISSUE:
        # Use first project as parent epic
        parent_epic = projects[0].get("gid")

    # Extract parent task (parent_issue for subtasks)
    parent_issue = None
    if parent_task:
        parent_issue = parent_task.get("gid")

    return Task(
        id=task.get("gid"),
        title=task.get("name", ""),
        description=task.get("notes", ""),
        state=state,
        priority=priority,
        tags=tags,
        assignee=assignee,
        ticket_type=ticket_type,
        parent_epic=parent_epic,
        parent_issue=parent_issue,
        created_at=parse_asana_datetime(task.get("created_at")),
        updated_at=parse_asana_datetime(task.get("modified_at")),
        metadata={
            "asana_gid": task.get("gid"),
            "asana_permalink_url": task.get("permalink_url"),
            "asana_workspace_gid": task.get("workspace", {}).get("gid"),
            "asana_completed": completed,
            "asana_completed_at": task.get("completed_at"),
            "asana_due_on": task.get("due_on"),
            "asana_due_at": task.get("due_at"),
            "asana_num_subtasks": task.get("num_subtasks", 0),
            "asana_num_hearts": task.get("num_hearts", 0),
            "asana_num_likes": task.get("num_likes", 0),
        },
    )


def map_epic_to_asana_project(
    epic: Epic,
    workspace_gid: str,
    team_gid: str | None = None,
) -> dict[str, Any]:
    """Map Epic to Asana project create/update data.

    Args:
    ----
        epic: Epic model instance
        workspace_gid: Asana workspace GID
        team_gid: Asana team GID (optional, required for organization workspaces)

    Returns:
    -------
        Asana project data for create/update

    """
    project_data: dict[str, Any] = {
        "name": epic.title,
        "workspace": workspace_gid,
    }

    # Add team if provided (required for organization workspaces)
    if team_gid:
        project_data["team"] = team_gid

    if epic.description:
        project_data["notes"] = epic.description

    # Map state to archived
    if epic.state in (TicketState.CLOSED, TicketState.DONE):
        project_data["archived"] = True

    return project_data


def map_task_to_asana_task(
    task: Task,
    workspace_gid: str,
    project_gids: list[str] | None = None,
) -> dict[str, Any]:
    """Map Task to Asana task create/update data.

    Args:
    ----
        task: Task model instance
        workspace_gid: Asana workspace GID
        project_gids: List of project GIDs to add task to (optional)

    Returns:
    -------
        Asana task data for create/update

    """
    task_data: dict[str, Any] = {
        "name": task.title,
        "workspace": workspace_gid,
    }

    if task.description:
        task_data["notes"] = task.description

    # Map state to completed
    task_data["completed"] = map_state_to_asana(task.state)

    # Add to projects if provided
    if project_gids:
        task_data["projects"] = project_gids

    # Add parent if subtask
    if task.parent_issue:
        task_data["parent"] = task.parent_issue

    # Add assignee if provided
    if task.assignee:
        task_data["assignee"] = task.assignee

    # Due date mapping
    if task.metadata.get("asana_due_on"):
        task_data["due_on"] = task.metadata["asana_due_on"]
    elif task.metadata.get("asana_due_at"):
        task_data["due_at"] = task.metadata["asana_due_at"]

    return task_data


def map_asana_story_to_comment(story: dict[str, Any], task_gid: str) -> Comment | None:
    """Map Asana story to Comment.

    Only maps stories of type 'comment'. Other story types (system events) are filtered out.

    Args:
    ----
        story: Asana story data
        task_gid: Parent task GID

    Returns:
    -------
        Comment model instance or None if not a comment type

    """
    # Filter: only return actual comments, not system stories
    story_type = story.get("type", "")
    if story_type != "comment":
        return None

    # Extract author
    created_by = story.get("created_by", {})
    author = created_by.get("gid") or created_by.get("name", "Unknown")

    return Comment(
        id=story.get("gid"),
        ticket_id=task_gid,
        author=author,
        content=story.get("text", ""),
        created_at=parse_asana_datetime(story.get("created_at")),
        metadata={
            "asana_gid": story.get("gid"),
            "asana_type": story_type,
            "asana_created_by_name": created_by.get("name"),
        },
    )


def map_asana_attachment_to_attachment(
    attachment: dict[str, Any], task_gid: str
) -> Attachment:
    """Map Asana attachment to Attachment.

    IMPORTANT: Use permanent_url for reliable access, not download_url which expires.

    Args:
    ----
        attachment: Asana attachment data
        task_gid: Parent task GID

    Returns:
    -------
        Attachment model instance

    """
    # Extract creator info
    created_by_data = attachment.get("created_by", {})
    created_by = created_by_data.get("gid") or created_by_data.get("name", "Unknown")

    # Use permanent_url (not download_url which expires)
    url = attachment.get("permanent_url") or attachment.get("view_url")

    return Attachment(
        id=attachment.get("gid"),
        ticket_id=task_gid,
        filename=attachment.get("name", ""),
        url=url,
        content_type=attachment.get("resource_subtype"),  # e.g., "external", "asana"
        size_bytes=attachment.get("size"),
        created_at=parse_asana_datetime(attachment.get("created_at")),
        created_by=created_by,
        metadata={
            "asana_gid": attachment.get("gid"),
            "asana_host": attachment.get("host"),  # e.g., "asana", "dropbox", "google"
            "asana_resource_subtype": attachment.get("resource_subtype"),
            "asana_view_url": attachment.get("view_url"),
            "asana_download_url": attachment.get("download_url"),  # Expires!
            "asana_permanent_url": attachment.get("permanent_url"),  # Stable URL
        },
    )
