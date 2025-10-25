"""Linear-specific types and enums."""

from __future__ import annotations

from enum import Enum
from typing import Any

from mcp_ticketer.core.models import Priority, TicketState


class LinearPriorityMapping:
    """Mapping between universal Priority and Linear priority values."""

    # Linear uses numeric priorities: 0=No priority, 1=Urgent, 2=High, 3=Medium, 4=Low
    TO_LINEAR: dict[Priority, int] = {
        Priority.CRITICAL: 1,  # Urgent
        Priority.HIGH: 2,  # High
        Priority.MEDIUM: 3,  # Medium
        Priority.LOW: 4,  # Low
    }

    FROM_LINEAR: dict[int, Priority] = {
        0: Priority.LOW,  # No priority -> Low
        1: Priority.CRITICAL,  # Urgent -> Critical
        2: Priority.HIGH,  # High -> High
        3: Priority.MEDIUM,  # Medium -> Medium
        4: Priority.LOW,  # Low -> Low
    }


class LinearStateMapping:
    """Mapping between universal TicketState and Linear workflow state types."""

    # Linear workflow state types
    TO_LINEAR: dict[TicketState, str] = {
        TicketState.OPEN: "unstarted",
        TicketState.IN_PROGRESS: "started",
        TicketState.READY: "unstarted",  # No direct equivalent, use unstarted
        TicketState.TESTED: "started",  # No direct equivalent, use started
        TicketState.DONE: "completed",
        TicketState.CLOSED: "canceled",
        TicketState.WAITING: "unstarted",
        TicketState.BLOCKED: "unstarted",
    }

    FROM_LINEAR: dict[str, TicketState] = {
        "backlog": TicketState.OPEN,
        "unstarted": TicketState.OPEN,
        "started": TicketState.IN_PROGRESS,
        "completed": TicketState.DONE,
        "canceled": TicketState.CLOSED,
    }


class LinearWorkflowStateType(Enum):
    """Linear workflow state types."""

    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class LinearProjectState(Enum):
    """Linear project states."""

    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"
    PAUSED = "paused"


class LinearIssueRelationType(Enum):
    """Linear issue relation types."""

    BLOCKS = "blocks"
    BLOCKED_BY = "blockedBy"
    DUPLICATE = "duplicate"
    DUPLICATED_BY = "duplicatedBy"
    RELATES = "relates"


class LinearCommentType(Enum):
    """Linear comment types."""

    COMMENT = "comment"
    SYSTEM = "system"


def get_linear_priority(priority: Priority) -> int:
    """Convert universal Priority to Linear priority value.

    Args:
        priority: Universal priority enum

    Returns:
        Linear priority integer (0-4)

    """
    return LinearPriorityMapping.TO_LINEAR.get(priority, 3)  # Default to Medium


def get_universal_priority(linear_priority: int) -> Priority:
    """Convert Linear priority value to universal Priority.

    Args:
        linear_priority: Linear priority integer (0-4)

    Returns:
        Universal priority enum

    """
    return LinearPriorityMapping.FROM_LINEAR.get(linear_priority, Priority.MEDIUM)


def get_linear_state_type(state: TicketState) -> str:
    """Convert universal TicketState to Linear workflow state type.

    Args:
        state: Universal ticket state enum

    Returns:
        Linear workflow state type string

    """
    return LinearStateMapping.TO_LINEAR.get(state, "unstarted")


def get_universal_state(linear_state_type: str) -> TicketState:
    """Convert Linear workflow state type to universal TicketState.

    Args:
        linear_state_type: Linear workflow state type string

    Returns:
        Universal ticket state enum

    """
    return LinearStateMapping.FROM_LINEAR.get(linear_state_type, TicketState.OPEN)


def build_issue_filter(
    state: TicketState | None = None,
    assignee_id: str | None = None,
    priority: Priority | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    labels: list[str] | None = None,
    created_after: str | None = None,
    updated_after: str | None = None,
    due_before: str | None = None,
    include_archived: bool = False,
) -> dict[str, Any]:
    """Build a Linear issue filter from parameters.

    Args:
        state: Filter by ticket state
        assignee_id: Filter by assignee Linear user ID
        priority: Filter by priority
        team_id: Filter by team ID
        project_id: Filter by project ID
        labels: Filter by label names
        created_after: Filter by creation date (ISO string)
        updated_after: Filter by update date (ISO string)
        due_before: Filter by due date (ISO string)
        include_archived: Whether to include archived issues

    Returns:
        Linear GraphQL filter object

    """
    issue_filter: dict[str, Any] = {}

    # Team filter (required for most operations)
    if team_id:
        issue_filter["team"] = {"id": {"eq": team_id}}

    # State filter
    if state:
        state_type = get_linear_state_type(state)
        issue_filter["state"] = {"type": {"eq": state_type}}

    # Assignee filter
    if assignee_id:
        issue_filter["assignee"] = {"id": {"eq": assignee_id}}

    # Priority filter
    if priority:
        linear_priority = get_linear_priority(priority)
        issue_filter["priority"] = {"eq": linear_priority}

    # Project filter
    if project_id:
        issue_filter["project"] = {"id": {"eq": project_id}}

    # Labels filter
    if labels:
        issue_filter["labels"] = {"some": {"name": {"in": labels}}}

    # Date filters
    if created_after:
        issue_filter["createdAt"] = {"gte": created_after}
    if updated_after:
        issue_filter["updatedAt"] = {"gte": updated_after}
    if due_before:
        issue_filter["dueDate"] = {"lte": due_before}

    # Archived filter
    if not include_archived:
        issue_filter["archivedAt"] = {"null": True}

    return issue_filter


def build_project_filter(
    state: str | None = None,
    team_id: str | None = None,
    include_completed: bool = True,
) -> dict[str, Any]:
    """Build a Linear project filter from parameters.

    Args:
        state: Filter by project state
        team_id: Filter by team ID
        include_completed: Whether to include completed projects

    Returns:
        Linear GraphQL filter object

    """
    project_filter: dict[str, Any] = {}

    # Team filter
    if team_id:
        project_filter["teams"] = {"some": {"id": {"eq": team_id}}}

    # State filter
    if state:
        project_filter["state"] = {"eq": state}
    elif not include_completed:
        # Exclude completed projects by default
        project_filter["state"] = {"neq": "completed"}

    return project_filter


def extract_linear_metadata(issue_data: dict[str, Any]) -> dict[str, Any]:
    """Extract Linear-specific metadata from issue data.

    Args:
        issue_data: Raw Linear issue data from GraphQL

    Returns:
        Dictionary of Linear-specific metadata

    """
    metadata = {}

    # Extract Linear-specific fields
    if "dueDate" in issue_data and issue_data["dueDate"]:
        metadata["due_date"] = issue_data["dueDate"]

    if "cycle" in issue_data and issue_data["cycle"]:
        metadata["cycle_id"] = issue_data["cycle"]["id"]
        metadata["cycle_name"] = issue_data["cycle"]["name"]

    if "estimate" in issue_data and issue_data["estimate"]:
        metadata["estimate"] = issue_data["estimate"]

    if "branchName" in issue_data and issue_data["branchName"]:
        metadata["branch_name"] = issue_data["branchName"]

    if "url" in issue_data:
        metadata["linear_url"] = issue_data["url"]

    if "slaBreachesAt" in issue_data and issue_data["slaBreachesAt"]:
        metadata["sla_breaches_at"] = issue_data["slaBreachesAt"]

    if "customerTicketCount" in issue_data:
        metadata["customer_ticket_count"] = issue_data["customerTicketCount"]

    return metadata
