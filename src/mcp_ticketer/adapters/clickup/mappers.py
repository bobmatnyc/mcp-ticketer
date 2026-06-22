"""Data mappers for converting between ClickUp and mcp-ticketer models."""

import logging
from datetime import datetime, timezone
from typing import Any

from ...core.models import (
    Comment,
    Epic,
    Priority,
    Task,
    TicketState,
    TicketType,
)
from .types import (
    map_priority_from_clickup,
    map_priority_to_clickup,
    map_status_type_to_state,
)

logger = logging.getLogger(__name__)


def parse_clickup_epoch_ms(value: Any) -> datetime | None:
    """Parse a ClickUp epoch-milliseconds timestamp to a datetime.

    ClickUp returns timestamps as millisecond epoch strings (e.g. ``"1700000000000"``).

    Args:
        value: Epoch-milliseconds value as a string, int, or None.

    Returns:
        Timezone-aware UTC datetime, or None if the value is missing/invalid.

    """
    if value is None or value == "":
        return None
    try:
        ms = int(value)
    except (ValueError, TypeError):
        logger.warning("Failed to parse ClickUp timestamp '%s'", value)
        return None
    try:
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (ValueError, OverflowError, OSError):
        logger.warning("ClickUp timestamp out of range '%s'", value)
        return None


def to_clickup_epoch_ms(value: datetime) -> int:
    """Convert a datetime to ClickUp epoch milliseconds.

    Args:
        value: A datetime (naive datetimes are treated as UTC).

    Returns:
        Epoch milliseconds as an int.

    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp() * 1000)


def map_clickup_list_to_epic(clickup_list: dict[str, Any]) -> Epic:
    """Map a ClickUp List to an Epic.

    The Epic/Issue/Task hierarchy maps to ClickUp as:
    - Epic  -> ClickUp List
    - Issue -> ClickUp Task (no parent)
    - Task  -> ClickUp Subtask (has parent)

    Args:
        clickup_list: ClickUp list object.

    Returns:
        Epic model instance.

    """
    # ClickUp lists are archived rather than "closed"; map that to CLOSED.
    archived = bool(clickup_list.get("archived", False))
    state = TicketState.CLOSED if archived else TicketState.OPEN

    folder = clickup_list.get("folder") or {}
    space = clickup_list.get("space") or {}

    return Epic(
        id=clickup_list.get("id"),
        title=clickup_list.get("name", ""),
        description=clickup_list.get("content") or "",
        state=state,
        priority=Priority.MEDIUM,
        created_at=None,
        updated_at=None,
        metadata={
            "clickup_id": clickup_list.get("id"),
            "clickup_folder_id": folder.get("id"),
            "clickup_folder_name": folder.get("name"),
            "clickup_space_id": space.get("id"),
            "clickup_space_name": space.get("name"),
            "clickup_archived": archived,
            "clickup_task_count": clickup_list.get("task_count"),
        },
    )


def map_clickup_task_to_task(task: dict[str, Any]) -> Task:
    """Map a ClickUp task to a Task.

    Detects the ticket type from the hierarchy:
    - Has ``parent`` -> TASK (subtask)
    - No ``parent``  -> ISSUE (standard task)

    Args:
        task: ClickUp task object.

    Returns:
        Task model instance.

    """
    parent = task.get("parent")
    ticket_type = TicketType.TASK if parent else TicketType.ISSUE

    # Status is per-list: {"status": "in progress", "type": "custom", ...}.
    status_obj = task.get("status") or {}
    status_name = status_obj.get("status") if isinstance(status_obj, dict) else None
    status_type = status_obj.get("type") if isinstance(status_obj, dict) else None
    state = map_status_type_to_state(status_type, status_name)

    priority = map_priority_from_clickup(task.get("priority"))

    # Tags are objects: {"name": "bug", "tag_fg": "...", ...}.
    tags = [
        t.get("name", "")
        for t in task.get("tags", [])
        if isinstance(t, dict) and t.get("name")
    ]

    # Assignees are objects: take the first one's id as the universal assignee.
    assignee = None
    assignees = task.get("assignees", [])
    if assignees and isinstance(assignees[0], dict):
        assignee_id = assignees[0].get("id")
        assignee = str(assignee_id) if assignee_id is not None else None

    # parent_epic (the List) for issues; parent_issue (the task) for subtasks.
    list_obj = task.get("list") or {}
    list_id = list_obj.get("id") if isinstance(list_obj, dict) else None

    parent_epic = None
    parent_issue = None
    if parent:
        parent_issue = str(parent)
    elif list_id:
        parent_epic = str(list_id)

    # ClickUp returns description as plain "description" and "text_content".
    description = task.get("description")
    if description is None:
        description = task.get("text_content") or ""

    return Task(
        id=task.get("id"),
        title=task.get("name", ""),
        description=description,
        state=state,
        priority=priority,
        tags=tags,
        assignee=assignee,
        ticket_type=ticket_type,
        parent_epic=parent_epic,
        parent_issue=parent_issue,
        created_at=parse_clickup_epoch_ms(task.get("date_created")),
        updated_at=parse_clickup_epoch_ms(task.get("date_updated")),
        metadata={
            "clickup_id": task.get("id"),
            "clickup_url": task.get("url"),
            "clickup_list_id": list_id,
            "clickup_folder_id": (task.get("folder") or {}).get("id"),
            "clickup_space_id": (task.get("space") or {}).get("id"),
            "clickup_status_name": status_name,
            "clickup_status_type": status_type,
            "clickup_due_date": task.get("due_date"),
            "clickup_start_date": task.get("start_date"),
            "clickup_date_closed": task.get("date_closed"),
            "clickup_assignee_ids": [
                a.get("id") for a in assignees if isinstance(a, dict)
            ],
            "clickup_parent": parent,
        },
    )


def map_task_to_clickup_payload(task: Task) -> dict[str, Any]:
    """Map a Task to a ClickUp task create payload.

    Status is intentionally NOT included here: ClickUp statuses are per-list and
    must be resolved against the target list's statuses by the adapter before
    being added to the payload.

    Args:
        task: Task model instance.

    Returns:
        ClickUp task create payload.

    """
    payload: dict[str, Any] = {"name": task.title}

    if task.description:
        payload["description"] = task.description

    payload["priority"] = map_priority_to_clickup(task.priority)

    if task.tags:
        payload["tags"] = list(task.tags)

    # Subtask linkage: ClickUp uses "parent" = parent task id.
    if task.parent_issue:
        payload["parent"] = task.parent_issue

    # Due date if the caller stashed an epoch-ms value in metadata.
    due_date = task.metadata.get("clickup_due_date")
    if due_date is not None:
        payload["due_date"] = due_date

    return payload


def map_clickup_comment_to_comment(comment: dict[str, Any], task_id: str) -> Comment:
    """Map a ClickUp comment to a Comment.

    ClickUp comments are shaped::

        {
          "id": "...",
          "comment_text": "Hello",
          "user": {"id": 123, "username": "Jane"},
          "date": "1700000000000"
        }

    Args:
        comment: ClickUp comment object.
        task_id: Parent task id.

    Returns:
        Comment model instance.

    """
    user = comment.get("user") or {}
    author_id = user.get("id")
    author = str(author_id) if author_id is not None else user.get("username")

    # ClickUp returns either "comment_text" (string) or "comment" (rich blocks).
    content = comment.get("comment_text")
    if not content:
        blocks = comment.get("comment")
        if isinstance(blocks, list):
            content = "".join(b.get("text", "") for b in blocks if isinstance(b, dict))
    if not content:
        # Comment.content has min_length=1; never emit an empty string.
        content = " "

    return Comment(
        id=str(comment.get("id")) if comment.get("id") is not None else None,
        ticket_id=task_id,
        author=author,
        content=content,
        created_at=parse_clickup_epoch_ms(comment.get("date")),
        metadata={
            "clickup_id": comment.get("id"),
            "clickup_username": user.get("username"),
            "clickup_resolved": comment.get("resolved"),
        },
    )
