"""Data transformation mappers for Linear API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...core.models import Attachment, Comment, Epic, Priority, Task, TicketState
from .types import extract_linear_metadata, get_universal_priority, get_universal_state


def map_linear_issue_to_task(issue_data: dict[str, Any]) -> Task:
    """Convert Linear issue or sub-issue data to universal Task model.

    Handles both top-level issues (no parent) and sub-issues (child items
    with a parent issue).

    Args:
    ----
        issue_data: Raw Linear issue data from GraphQL

    Returns:
    -------
        Universal Task model

    """
    # Extract basic fields
    task_id = issue_data["identifier"]
    title = issue_data["title"]
    description = issue_data.get("description", "")

    # Map priority
    linear_priority = issue_data.get("priority", 3)
    priority = get_universal_priority(linear_priority)

    # Map state with synonym matching (1M-164)
    state_data = issue_data.get("state", {})
    state_type = state_data.get("type", "unstarted")
    state_name = state_data.get("name")  # Extract state name for synonym matching
    state = get_universal_state(state_type, state_name)

    # Extract assignee
    assignee = None
    if issue_data.get("assignee"):
        assignee_data = issue_data["assignee"]
        assignee = assignee_data.get("email") or assignee_data.get("displayName")

    # Extract creator
    creator = None
    if issue_data.get("creator"):
        creator_data = issue_data["creator"]
        creator = creator_data.get("email") or creator_data.get("displayName")

    # Extract tags (labels)
    tags = []
    if issue_data.get("labels", {}).get("nodes"):
        tags = [label["name"] for label in issue_data["labels"]["nodes"]]

    # Extract parent epic (project)
    parent_epic = None
    if issue_data.get("project"):
        parent_epic = issue_data["project"]["id"]

    # Extract parent issue
    parent_issue = None
    if issue_data.get("parent"):
        parent_issue = issue_data["parent"]["identifier"]

    # Extract dates
    created_at = None
    if issue_data.get("createdAt"):
        created_at = datetime.fromisoformat(
            issue_data["createdAt"].replace("Z", "+00:00")
        )

    updated_at = None
    if issue_data.get("updatedAt"):
        updated_at = datetime.fromisoformat(
            issue_data["updatedAt"].replace("Z", "+00:00")
        )

    # Extract child issue IDs
    children = extract_child_issue_ids(issue_data)

    # Extract Linear-specific metadata
    linear_metadata = extract_linear_metadata(issue_data)
    metadata = {"linear": linear_metadata} if linear_metadata else {}

    return Task(
        id=task_id,
        title=title,
        description=description,
        state=state,
        priority=priority,
        assignee=assignee,
        creator=creator,
        tags=tags,
        parent_epic=parent_epic,
        parent_issue=parent_issue,
        children=children,
        created_at=created_at,
        updated_at=updated_at,
        metadata=metadata,
    )


def map_linear_project_to_epic(project_data: dict[str, Any]) -> Epic:
    """Convert Linear project data to universal Epic model.

    Args:
    ----
        project_data: Raw Linear project data from GraphQL

    Returns:
    -------
        Universal Epic model

    """
    # Extract basic fields
    epic_id = project_data["id"]
    title = project_data["name"]
    description = project_data.get("description", "")

    # Map state based on project state
    project_state = project_data.get("state", "planned")
    if project_state == "completed":
        state = TicketState.DONE
    elif project_state == "started":
        state = TicketState.IN_PROGRESS
    elif project_state == "canceled":
        state = TicketState.CLOSED
    else:
        state = TicketState.OPEN

    # Extract dates
    created_at = None
    if project_data.get("createdAt"):
        created_at = datetime.fromisoformat(
            project_data["createdAt"].replace("Z", "+00:00")
        )

    updated_at = None
    if project_data.get("updatedAt"):
        updated_at = datetime.fromisoformat(
            project_data["updatedAt"].replace("Z", "+00:00")
        )

    # Extract Linear-specific metadata
    metadata: dict[str, Any] = {"linear": {}}
    if project_data.get("url"):
        metadata["linear"]["linear_url"] = project_data["url"]
    if project_data.get("icon"):
        metadata["linear"]["icon"] = project_data["icon"]
    if project_data.get("color"):
        metadata["linear"]["color"] = project_data["color"]
    if project_data.get("targetDate"):
        metadata["linear"]["target_date"] = project_data["targetDate"]

    return Epic(
        id=epic_id,
        title=title,
        description=description,
        state=state,
        priority=Priority.MEDIUM,  # Projects don't have priority in Linear
        created_at=created_at,
        updated_at=updated_at,
        metadata=metadata if metadata["linear"] else {},
    )


def map_linear_comment_to_comment(
    comment_data: dict[str, Any], ticket_id: str
) -> Comment:
    """Convert Linear comment data to universal Comment model.

    Args:
    ----
        comment_data: Raw Linear comment data from GraphQL
        ticket_id: ID of the ticket this comment belongs to

    Returns:
    -------
        Universal Comment model

    """
    # Extract basic fields
    comment_id = comment_data["id"]
    body = comment_data.get("body", "")

    # Extract author
    author = None
    if comment_data.get("user"):
        user_data = comment_data["user"]
        author = user_data.get("email") or user_data.get("displayName")

    # Extract dates
    created_at = None
    if comment_data.get("createdAt"):
        created_at = datetime.fromisoformat(
            comment_data["createdAt"].replace("Z", "+00:00")
        )

    # Note: Comment model doesn't have updated_at field
    # Store it in metadata if needed
    metadata = {}
    if comment_data.get("updatedAt"):
        metadata["updated_at"] = comment_data["updatedAt"]

    return Comment(
        id=comment_id,
        ticket_id=ticket_id,
        content=body,
        author=author,
        created_at=created_at,
        metadata=metadata,
    )


def build_linear_issue_input(task: Task, team_id: str) -> dict[str, Any]:
    """Build Linear issue or sub-issue input from universal Task model.

    Creates input for a top-level issue when task.parent_issue is not set,
    or for a sub-issue when task.parent_issue is provided.

    Args:
    ----
        task: Universal Task model
        team_id: Linear team ID

    Returns:
    -------
        Linear issue input dictionary

    """
    from .types import get_linear_priority

    issue_input: dict[str, Any] = {
        "title": task.title,
        "teamId": team_id,
    }

    # Add description if provided
    if task.description:
        issue_input["description"] = task.description

    # Add priority
    if task.priority:
        issue_input["priority"] = get_linear_priority(task.priority)

    # Add assignee if provided (assumes it's a user ID)
    if task.assignee:
        issue_input["assigneeId"] = task.assignee

    # Add parent issue if provided
    if task.parent_issue:
        issue_input["parentId"] = task.parent_issue

    # Add project (epic) if provided
    if task.parent_epic:
        issue_input["projectId"] = task.parent_epic

    # DO NOT set labelIds here - adapter will handle label resolution
    # Labels are resolved from names to UUIDs in LinearAdapter._create_task()
    # If we set it here, we create a type mismatch (names vs UUIDs)
    # The adapter's label resolution logic (lines 982-988) handles this properly
    #
    # Bug Fix (v1.1.1): Previously, setting labelIds to tag names here caused
    # "Argument Validation Error" from Linear's GraphQL API. The API requires
    # UUIDs (e.g., "uuid-1"), not names (e.g., "bug"). This was fixed by:
    # 1. Removing labelIds assignment in mapper (this file)
    # 2. Adding UUID validation in adapter._create_task() (adapter.py:1047-1060)
    # 3. Changing GraphQL labelIds type to [String!]! (queries.py)
    #
    # See: docs/TROUBLESHOOTING.md#issue-argument-validation-error-when-creating-issues-with-labels

    # Add Linear-specific metadata
    if task.metadata and "linear" in task.metadata:
        linear_meta = task.metadata["linear"]
        if "due_date" in linear_meta:
            issue_input["dueDate"] = linear_meta["due_date"]
        if "cycle_id" in linear_meta:
            issue_input["cycleId"] = linear_meta["cycle_id"]
        if "estimate" in linear_meta:
            issue_input["estimate"] = linear_meta["estimate"]

    return issue_input


def build_linear_issue_update_input(updates: dict[str, Any]) -> dict[str, Any]:
    """Build Linear issue update input from update dictionary.

    Args:
    ----
        updates: Dictionary of fields to update

    Returns:
    -------
        Linear issue update input dictionary

    """
    from .types import get_linear_priority

    update_input = {}

    # Map standard fields
    if "title" in updates:
        update_input["title"] = updates["title"]

    if "description" in updates:
        update_input["description"] = updates["description"]

    if "priority" in updates:
        priority = (
            Priority(updates["priority"])
            if isinstance(updates["priority"], str)
            else updates["priority"]
        )
        update_input["priority"] = get_linear_priority(priority)

    if "assignee" in updates:
        update_input["assigneeId"] = updates["assignee"]

    # Handle state transitions (would need workflow state mapping)
    if "state" in updates:
        # This would need to be handled by the adapter with proper state mapping
        pass

    # Handle metadata updates
    if "metadata" in updates and "linear" in updates["metadata"]:
        linear_meta = updates["metadata"]["linear"]
        if "due_date" in linear_meta:
            update_input["dueDate"] = linear_meta["due_date"]
        if "cycle_id" in linear_meta:
            update_input["cycleId"] = linear_meta["cycle_id"]
        if "project_id" in linear_meta:
            update_input["projectId"] = linear_meta["project_id"]
        if "estimate" in linear_meta:
            update_input["estimate"] = linear_meta["estimate"]

    return update_input


def extract_child_issue_ids(issue_data: dict[str, Any]) -> list[str]:
    """Extract child issue IDs from Linear issue data.

    Args:
    ----
        issue_data: Raw Linear issue data from GraphQL

    Returns:
    -------
        List of child issue identifiers

    """
    child_ids = []
    if issue_data.get("children", {}).get("nodes"):
        child_ids = [child["identifier"] for child in issue_data["children"]["nodes"]]
    return child_ids


def map_linear_attachment_to_attachment(
    attachment_data: dict[str, Any], ticket_id: str
) -> Attachment:
    """Convert Linear attachment data to universal Attachment model.

    Args:
    ----
        attachment_data: Raw Linear attachment data from GraphQL
        ticket_id: ID of the ticket this attachment belongs to

    Returns:
    -------
        Universal Attachment model

    Note:
    ----
        Linear attachment URLs require authentication with API key.
        URLs are in format: https://files.linear.app/workspace/attachment-id/filename
        Authentication header: Authorization: Bearer {api_key}

    """
    # Extract basic fields
    attachment_id = attachment_data.get("id")
    title = attachment_data.get("title", "Untitled")
    url = attachment_data.get("url")
    subtitle = attachment_data.get("subtitle")

    # Extract dates
    created_at = None
    if attachment_data.get("createdAt"):
        created_at = datetime.fromisoformat(
            attachment_data["createdAt"].replace("Z", "+00:00")
        )

    if attachment_data.get("updatedAt"):
        datetime.fromisoformat(attachment_data["updatedAt"].replace("Z", "+00:00"))

    # Build metadata with Linear-specific fields
    metadata = {
        "linear": {
            "id": attachment_id,
            "title": title,
            "subtitle": subtitle,
            "metadata": attachment_data.get("metadata"),
            "updated_at": attachment_data.get("updatedAt"),
        }
    }

    return Attachment(
        id=attachment_id,
        ticket_id=ticket_id,
        filename=title,  # Linear uses 'title' as filename
        url=url,
        content_type=None,  # Linear doesn't provide MIME type in GraphQL
        size_bytes=None,  # Linear doesn't provide size in GraphQL
        created_at=created_at,
        created_by=None,  # Not included in standard fragment
        description=subtitle,
        metadata=metadata,
    )


def task_to_compact_format(task: Task) -> dict[str, Any]:
    """Convert Task to compact format for efficient token usage.

    Compact format includes only essential fields, reducing token usage by ~70-80%
    compared to full Task serialization.

    Args:
    ----
        task: Universal Task model

    Returns:
    -------
        Compact dictionary with minimal essential fields

    Design Decision: Compact Format Fields (1M-554)
    -----------------------------------------------
    Rationale: Selected fields based on token efficiency analysis and user needs.
    Full Task serialization averages ~600 tokens per item. Compact format targets
    ~120 tokens per item (80% reduction).

    Essential fields included:
    - id: Required for all operations (identifier)
    - title: Primary user-facing information
    - state: Critical for workflow understanding
    - priority: Important for triage and filtering
    - assignee: Key for task assignment visibility

    Fields excluded:
    - description: Often large (100-500 tokens), available via get()
    - creator: Less critical for list views
    - tags: Available in full format, not essential for scanning
    - children: Hierarchy details available via dedicated queries
    - created_at/updated_at: Not essential for list scanning
    - metadata: Platform-specific, not needed in compact view

    Performance: Reduces typical 50-item list from ~30,000 to ~6,000 tokens.

    """
    # Handle state - can be TicketState enum or string
    state_value = None
    if task.state:
        state_value = task.state.value if hasattr(task.state, "value") else task.state

    # Handle priority - can be Priority enum or string
    priority_value = None
    if task.priority:
        priority_value = (
            task.priority.value if hasattr(task.priority, "value") else task.priority
        )

    return {
        "id": task.id,
        "title": task.title,
        "state": state_value,
        "priority": priority_value,
        "assignee": task.assignee,
    }


def epic_to_compact_format(epic: Epic) -> dict[str, Any]:
    """Convert Epic to compact format for efficient token usage.

    Compact format includes only essential fields, reducing token usage by ~70-80%
    compared to full Epic serialization.

    Args:
    ----
        epic: Universal Epic model

    Returns:
    -------
        Compact dictionary with minimal essential fields

    Design Decision: Epic Compact Format (1M-554)
    ---------------------------------------------
    Rationale: Epics typically have less metadata than tasks, but descriptions
    can still be large. Compact format focuses on overview information.

    Essential fields:
    - id: Required for all operations
    - title: Primary identifier
    - state: Project status
    - child_count: Useful for project overview (if available)

    Performance: Similar token reduction to task compact format.

    """
    # Handle state - can be TicketState enum or string
    state_value = None
    if epic.state:
        state_value = epic.state.value if hasattr(epic.state, "value") else epic.state

    compact = {
        "id": epic.id,
        "title": epic.title,
        "state": state_value,
    }

    # Include child count if available in metadata
    if epic.metadata and "linear" in epic.metadata:
        linear_meta = epic.metadata["linear"]
        if "issue_count" in linear_meta:
            compact["child_count"] = linear_meta["issue_count"]

    return compact
