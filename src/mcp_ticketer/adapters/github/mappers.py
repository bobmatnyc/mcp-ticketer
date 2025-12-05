"""Data transformation between GitHub and universal models.

This module contains bidirectional mappers:
- GitHub → Universal models (read operations)
- Universal → GitHub input (write operations)

Design Pattern: Pure Transformation Functions
---------------------------------------------
All mappers are pure functions with no side effects:
- Input: GitHub API data or universal models
- Output: Universal models or GitHub API input
- No API calls, no state mutations
- Fully testable in isolation

This separation enables:
1. Easy unit testing without mocking HTTP clients
2. Reusable transformations across different operations
3. Clear data flow and debugging
4. Token usage optimization through compact formats
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from ...core.models import Comment, Epic, Milestone, Priority, Task, TicketState
from .types import extract_state_from_issue, get_priority_from_labels


def map_github_issue_to_task(
    issue: dict[str, Any],
    custom_priority_scheme: dict[str, list[str]] | None = None,
) -> Task:
    """Convert GitHub issue to universal Task model.

    Handles multiple GitHub API response formats:
    - REST API v3: Traditional JSON structure
    - GraphQL API v4: Nested nodes structure

    Args:
    ----
        issue: GitHub issue data from REST or GraphQL API
        custom_priority_scheme: Optional custom priority label mapping

    Returns:
    -------
        Universal Task model

    Performance:
    -----------
        Time Complexity: O(n) where n = number of labels
        Expected: ~20 labels, ~100μs transformation time

    Example:
    -------
        issue = {"number": 123, "title": "Bug fix", "state": "open", ...}
        task = map_github_issue_to_task(issue)
        assert task.id == "123"
        assert task.state == TicketState.OPEN
    """
    # Extract labels (handle different formats)
    labels = []
    if "labels" in issue:
        if isinstance(issue["labels"], list):
            # REST API format: array of objects or strings
            labels = [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in issue["labels"]
            ]
        elif isinstance(issue["labels"], dict) and "nodes" in issue["labels"]:
            # GraphQL format: labels.nodes array
            labels = [label["name"] for label in issue["labels"]["nodes"]]

    # Extract state using helper
    state = extract_state_from_issue(issue)

    # Extract priority from labels
    priority = get_priority_from_labels(labels, custom_priority_scheme)

    # Extract assignee (handle different formats)
    assignee = None
    if "assignees" in issue:
        if isinstance(issue["assignees"], list) and issue["assignees"]:
            assignee = issue["assignees"][0].get("login")
        elif isinstance(issue["assignees"], dict) and "nodes" in issue["assignees"]:
            nodes = issue["assignees"]["nodes"]
            if nodes:
                assignee = nodes[0].get("login")
    elif "assignee" in issue and issue["assignee"]:
        assignee = issue["assignee"].get("login")

    # Extract parent epic (milestone)
    parent_epic = None
    if issue.get("milestone"):
        parent_epic = str(issue["milestone"]["number"])

    # Parse creation timestamp
    created_at = None
    if issue.get("created_at"):
        created_at = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
    elif issue.get("createdAt"):
        created_at = datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))

    # Parse update timestamp
    updated_at = None
    if issue.get("updated_at"):
        updated_at = datetime.fromisoformat(issue["updated_at"].replace("Z", "+00:00"))
    elif issue.get("updatedAt"):
        updated_at = datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))

    # Build metadata
    metadata = {
        "github": {
            "number": issue.get("number"),
            "url": issue.get("url") or issue.get("html_url"),
            "author": (
                issue.get("user", {}).get("login")
                if "user" in issue
                else issue.get("author", {}).get("login")
            ),
            "labels": labels,
        }
    }

    # Add Projects V2 info if available
    if "projectCards" in issue and issue["projectCards"].get("nodes"):
        metadata["github"]["projects"] = [
            {
                "name": card["project"]["name"],
                "column": card["column"]["name"],
                "url": card["project"]["url"],
            }
            for card in issue["projectCards"]["nodes"]
        ]

    return Task(
        id=str(issue["number"]),
        title=issue["title"],
        description=issue.get("body") or issue.get("bodyText"),
        state=state,
        priority=priority,
        tags=labels,
        parent_epic=parent_epic,
        assignee=assignee,
        created_at=created_at,
        updated_at=updated_at,
        metadata=metadata,
    )


def map_github_milestone_to_epic(milestone: dict[str, Any]) -> Epic:
    """Convert GitHub milestone to universal Epic model.

    Args:
    ----
        milestone: GitHub milestone data from API

    Returns:
    -------
        Universal Epic model

    Example:
    -------
        milestone = {"number": 1, "title": "v1.0", "state": "open", ...}
        epic = map_github_milestone_to_epic(milestone)
        assert epic.id == "1"
    """
    return Epic(
        id=str(milestone["number"]),
        title=milestone["title"],
        description=milestone.get("description", ""),
        state=(
            TicketState.OPEN if milestone["state"] == "open" else TicketState.CLOSED
        ),
        created_at=datetime.fromisoformat(
            milestone["created_at"].replace("Z", "+00:00")
        ),
        updated_at=datetime.fromisoformat(
            milestone["updated_at"].replace("Z", "+00:00")
        ),
        metadata={
            "github": {
                "number": milestone["number"],
                "url": milestone.get("html_url"),
                "open_issues": milestone.get("open_issues", 0),
                "closed_issues": milestone.get("closed_issues", 0),
            }
        },
    )


def map_github_milestone_to_milestone(
    gh_milestone: dict[str, Any],
    repo: str,
    labels: list[str] | None = None,
) -> Milestone:
    """Convert GitHub Milestone to universal Milestone model.

    Args:
    ----
        gh_milestone: GitHub milestone data from API
        repo: Repository name (used as project_id)
        labels: Optional labels from local storage

    Returns:
    -------
        Universal Milestone model

    Example:
    -------
        milestone = map_github_milestone_to_milestone(
            {"number": 1, "title": "Sprint 1", ...},
            repo="my-repo"
        )
    """
    # Parse target date
    target_date = None
    if gh_milestone.get("due_on"):
        target_date = datetime.fromisoformat(
            gh_milestone["due_on"].replace("Z", "+00:00")
        ).date()

    # Determine state
    state = "closed" if gh_milestone["state"] == "closed" else "open"
    if state == "open" and target_date:
        if target_date < date.today():
            state = "closed"  # Past due
        else:
            state = "active"

    # Calculate progress
    total = gh_milestone.get("open_issues", 0) + gh_milestone.get("closed_issues", 0)
    closed = gh_milestone.get("closed_issues", 0)
    progress_pct = (closed / total * 100) if total > 0 else 0.0

    return Milestone(
        id=str(gh_milestone["number"]),
        name=gh_milestone["title"],
        description=gh_milestone.get("description", ""),
        target_date=target_date,
        state=state,
        labels=labels or [],
        total_issues=total,
        closed_issues=closed,
        progress_pct=progress_pct,
        project_id=repo,  # Repository name as project
        created_at=(
            datetime.fromisoformat(
                gh_milestone.get("created_at", "").replace("Z", "+00:00")
            )
            if gh_milestone.get("created_at")
            else None
        ),
        updated_at=(
            datetime.fromisoformat(
                gh_milestone.get("updated_at", "").replace("Z", "+00:00")
            )
            if gh_milestone.get("updated_at")
            else None
        ),
        platform_data={
            "github": {
                "milestone_number": gh_milestone["number"],
                "url": gh_milestone.get("html_url"),
                "created_at": gh_milestone.get("created_at"),
                "updated_at": gh_milestone.get("updated_at"),
            }
        },
    )


def map_github_comment_to_comment(
    comment_data: dict[str, Any],
    ticket_id: str,
) -> Comment:
    """Convert GitHub comment to universal Comment model.

    Args:
    ----
        comment_data: GitHub comment data from API
        ticket_id: Associated issue number

    Returns:
    -------
        Universal Comment model

    Example:
    -------
        comment = map_github_comment_to_comment(
            {"id": 123, "body": "Great work!", "author": {"login": "user"}},
            ticket_id="456"
        )
    """
    return Comment(
        id=str(comment_data["id"]),
        ticket_id=ticket_id,
        content=comment_data["body"],
        author=comment_data.get("author", {}).get("login"),
        created_at=datetime.fromisoformat(
            comment_data["createdAt"].replace("Z", "+00:00")
        ),
    )


def build_github_issue_input(
    task: Task,
    state_label: str | None = None,
    priority_label: str | None = None,
) -> dict[str, Any]:
    """Build GitHub issue creation input from Task.

    Args:
    ----
        task: Universal task model
        state_label: Optional state label to add
        priority_label: Optional priority label to add

    Returns:
    -------
        GitHub API issue creation payload

    Example:
    -------
        input_data = build_github_issue_input(
            task=Task(title="Fix bug", description="..."),
            state_label="in-progress",
            priority_label="P0"
        )
        # input_data = {"title": "Fix bug", "body": "...", "labels": [...]}
    """
    # Start with basic fields
    issue_data = {
        "title": task.title,
        "body": task.description or "",
    }

    # Build labels list
    labels = list(task.tags) if task.tags else []
    if state_label:
        labels.append(state_label)
    if priority_label:
        labels.append(priority_label)

    if labels:
        issue_data["labels"] = labels

    # Add assignee if specified
    if task.assignee:
        issue_data["assignees"] = [task.assignee]

    # Add milestone if parent_epic is specified
    if task.parent_epic:
        try:
            milestone_number = int(task.parent_epic)
            issue_data["milestone"] = milestone_number
        except ValueError:
            # If parent_epic is not a number, caller should resolve it
            pass

    return issue_data


def build_github_issue_update_input(
    updates: dict[str, Any],
    state_label: str | None = None,
    priority_label: str | None = None,
    remove_state_labels: list[str] | None = None,
) -> dict[str, Any]:
    """Build GitHub issue update input from universal updates.

    Args:
    ----
        updates: Universal update fields
        state_label: Optional new state label to add
        priority_label: Optional new priority label to add
        remove_state_labels: Optional state labels to remove

    Returns:
    -------
        GitHub API issue update payload

    Example:
    -------
        update_data = build_github_issue_update_input(
            updates={"title": "New title", "description": "New desc"},
            state_label="ready"
        )
    """
    issue_updates: dict[str, Any] = {}

    # Map universal fields to GitHub fields
    if "title" in updates:
        issue_updates["title"] = updates["title"]

    if "description" in updates:
        issue_updates["body"] = updates["description"]

    if "assignee" in updates:
        assignee = updates["assignee"]
        issue_updates["assignees"] = [assignee] if assignee else []

    # Handle labels
    labels = []
    if "tags" in updates:
        labels = list(updates["tags"])

    # Add state/priority labels if provided
    if state_label:
        labels.append(state_label)
    if priority_label:
        labels.append(priority_label)

    if labels:
        issue_updates["labels"] = labels

    # Handle milestone
    if "parent_epic" in updates:
        parent_epic = updates["parent_epic"]
        if parent_epic:
            try:
                milestone_number = int(parent_epic)
                issue_updates["milestone"] = milestone_number
            except ValueError:
                pass
        else:
            # Remove milestone
            issue_updates["milestone"] = None

    return issue_updates


def task_to_compact_format(task: Task) -> dict[str, Any]:
    """Convert Task to compact format for token optimization.

    Compact format includes only essential fields:
    - id, title, state, priority, assignee

    Full format would include:
    - description, tags, children, dates, metadata

    Token Savings:
    -------------
        Compact: ~120 tokens per task
        Full: ~600 tokens per task
        Savings: 80% reduction for large result sets

    Args:
    ----
        task: Universal task model

    Returns:
    -------
        Compact representation dict

    Example:
    -------
        task = Task(id="123", title="Fix bug", state=TicketState.OPEN, ...)
        compact = task_to_compact_format(task)
        # compact = {"id": "123", "title": "Fix bug", "state": "open", ...}
    """
    return {
        "id": task.id,
        "title": task.title,
        "state": task.state if isinstance(task.state, str) else (task.state.value if task.state else None),
        "priority": task.priority if isinstance(task.priority, str) else (task.priority.value if task.priority else None),
        "assignee": task.assignee,
    }


def epic_to_compact_format(epic: Epic) -> dict[str, Any]:
    """Convert Epic to compact format for token optimization.

    Args:
    ----
        epic: Universal epic model

    Returns:
    -------
        Compact representation dict
    """
    return {
        "id": epic.id,
        "title": epic.title,
        "state": epic.state if isinstance(epic.state, str) else (epic.state.value if epic.state else None),
    }
