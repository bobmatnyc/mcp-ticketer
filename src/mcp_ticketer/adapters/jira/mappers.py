"""Data transformation functions for mapping between Jira and universal models."""

from __future__ import annotations

from typing import Any

from ...core.models import Epic, Priority, Task
from .types import (
    JiraIssueType,
    convert_from_adf,
    convert_to_adf,
    map_priority_from_jira,
    map_priority_to_jira,
    map_state_from_jira,
    parse_jira_datetime,
)


def issue_to_ticket(
    issue: dict[str, Any],
    server: str,
) -> Epic | Task:
    """Convert JIRA issue to universal ticket model.

    Args:
    ----
        issue: JIRA issue dictionary from API
        server: JIRA server URL for constructing browse URLs

    Returns:
    -------
        Epic or Task object depending on issue type

    """
    fields = issue.get("fields", {})

    # Determine ticket type
    issue_type = fields.get("issuetype", {}).get("name", "").lower()
    is_epic = "epic" in issue_type

    # Extract common fields
    # Convert ADF description back to plain text if needed
    description = convert_from_adf(fields.get("description", ""))

    base_data = {
        "id": issue.get("key"),
        "title": fields.get("summary", ""),
        "description": description,
        "state": map_state_from_jira(fields.get("status", {})),
        "priority": map_priority_from_jira(fields.get("priority")),
        "tags": [
            label.get("name", "") if isinstance(label, dict) else str(label)
            for label in fields.get("labels", [])
        ],
        "created_at": parse_jira_datetime(fields.get("created")),
        "updated_at": parse_jira_datetime(fields.get("updated")),
        "metadata": {
            "jira": {
                "id": issue.get("id"),
                "key": issue.get("key"),
                "self": issue.get("self"),
                "url": f"{server}/browse/{issue.get('key')}",
                "issue_type": fields.get("issuetype", {}),
                "project": fields.get("project", {}),
                "components": fields.get("components", []),
                "fix_versions": fields.get("fixVersions", []),
                "resolution": fields.get("resolution"),
            }
        },
    }

    if is_epic:
        # Create Epic
        return Epic(
            **base_data,
            child_issues=[subtask.get("key") for subtask in fields.get("subtasks", [])],
        )
    else:
        # Create Task
        parent = fields.get("parent", {})
        epic_link = fields.get("customfield_10014")  # Common epic link field

        return Task(
            **base_data,
            parent_issue=parent.get("key") if parent else None,
            parent_epic=epic_link if epic_link else None,
            assignee=(
                fields.get("assignee", {}).get("displayName")
                if fields.get("assignee")
                else None
            ),
            estimated_hours=(
                fields.get("timetracking", {}).get("originalEstimateSeconds", 0) / 3600
                if fields.get("timetracking")
                else None
            ),
            actual_hours=(
                fields.get("timetracking", {}).get("timeSpentSeconds", 0) / 3600
                if fields.get("timetracking")
                else None
            ),
        )


def ticket_to_issue_fields(
    ticket: Epic | Task,
    issue_type: str | None = None,
    is_cloud: bool = True,
    project_key: str | None = None,
) -> dict[str, Any]:
    """Convert universal ticket to JIRA issue fields.

    Args:
    ----
        ticket: Epic or Task object
        issue_type: Optional issue type override
        is_cloud: Whether this is JIRA Cloud (affects description format)
        project_key: Project key for new issues

    Returns:
    -------
        Dictionary of JIRA issue fields

    """
    # Convert description to ADF format for JIRA Cloud
    description = (
        convert_to_adf(ticket.description or "")
        if is_cloud
        else (ticket.description or "")
    )

    fields = {
        "summary": ticket.title,
        "description": description,
        "labels": ticket.tags,
    }

    # Only add priority for Tasks, not Epics (some JIRA configurations don't allow priority on Epics)
    if isinstance(ticket, Task):
        fields["priority"] = {"name": map_priority_to_jira(ticket.priority)}

    # Add project if creating new issue
    if not ticket.id and project_key:
        fields["project"] = {"key": project_key}

    # Set issue type
    if issue_type:
        fields["issuetype"] = {"name": issue_type}
    elif isinstance(ticket, Epic):
        fields["issuetype"] = {"name": JiraIssueType.EPIC}
    else:
        fields["issuetype"] = {"name": JiraIssueType.TASK}

    # Add task-specific fields
    if isinstance(ticket, Task):
        if ticket.assignee:
            # Note: Need to resolve user account ID
            fields["assignee"] = {"accountId": ticket.assignee}

        if ticket.parent_issue:
            fields["parent"] = {"key": ticket.parent_issue}

        # Time tracking
        if ticket.estimated_hours:
            fields["timetracking"] = {
                "originalEstimate": f"{int(ticket.estimated_hours)}h"
            }

    return fields


def map_update_fields(
    updates: dict[str, Any],
    is_cloud: bool = True,
) -> dict[str, Any]:
    """Map update dictionary to JIRA field updates.

    Args:
    ----
        updates: Dictionary of field updates
        is_cloud: Whether this is JIRA Cloud

    Returns:
    -------
        Dictionary of JIRA field updates

    """
    fields = {}

    if "title" in updates:
        fields["summary"] = updates["title"]
    if "description" in updates:
        fields["description"] = updates["description"]
    if "priority" in updates:
        fields["priority"] = {"name": map_priority_to_jira(updates["priority"])}
    if "tags" in updates:
        fields["labels"] = updates["tags"]
    if "assignee" in updates:
        fields["assignee"] = {"accountId": updates["assignee"]}

    return fields


def map_epic_update_fields(
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Map epic update dictionary to JIRA field updates.

    Args:
    ----
        updates: Dictionary with fields to update:
            - title: Epic title (maps to summary)
            - description: Epic description (auto-converted to ADF)
            - state: TicketState value (transitions via workflow)
            - tags: List of labels
            - priority: Priority level

    Returns:
    -------
        Dictionary of JIRA field updates

    """
    fields = {}

    # Map title to summary
    if "title" in updates:
        fields["summary"] = updates["title"]

    # Convert description to ADF format
    if "description" in updates:
        fields["description"] = convert_to_adf(updates["description"])

    # Map tags to labels
    if "tags" in updates:
        fields["labels"] = updates["tags"]

    # Map priority (some JIRA configs allow priority on Epics)
    if "priority" in updates:
        priority_value = updates["priority"]
        if isinstance(priority_value, Priority):
            fields["priority"] = {"name": map_priority_to_jira(priority_value)}
        else:
            # String priority passed directly
            fields["priority"] = {"name": priority_value}

    return fields
