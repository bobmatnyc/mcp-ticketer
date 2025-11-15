"""Hierarchy management tools for Epic/Issue/Task structure.

This module implements tools for managing the three-level ticket hierarchy:
- Epic: Strategic level containers
- Issue: Standard work items
- Task: Sub-work items
"""

from datetime import datetime
from typing import Any

from ....core.models import Epic, Priority, Task, TicketType
from ..server_sdk import get_adapter, mcp
from .ticket_tools import detect_and_apply_labels


@mcp.tool()
async def epic_create(
    title: str,
    description: str = "",
    target_date: str | None = None,
    lead_id: str | None = None,
    child_issues: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new epic (strategic level container).

    Args:
        title: Epic title (required)
        description: Detailed description of the epic
        target_date: Target completion date in ISO format (YYYY-MM-DD)
        lead_id: User ID or email of the epic lead
        child_issues: List of existing issue IDs to link to this epic

    Returns:
        Created epic details including ID and metadata, or error information

    """
    try:
        adapter = get_adapter()

        # Parse target date if provided
        target_datetime = None
        if target_date:
            try:
                target_datetime = datetime.fromisoformat(target_date)
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid date format '{target_date}'. Use ISO format: YYYY-MM-DD",
                }

        # Create epic object
        epic = Epic(
            title=title,
            description=description or "",
            due_date=target_datetime,
            assignee=lead_id,
            child_issues=child_issues or [],
        )

        # Create via adapter
        created = await adapter.create(epic)

        return {
            "status": "completed",
            "epic": created.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create epic: {str(e)}",
        }


@mcp.tool()
async def epic_list(
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """List all epics with pagination.

    Args:
        limit: Maximum number of epics to return (default: 10)
        offset: Number of epics to skip for pagination (default: 0)

    Returns:
        List of epics, or error information

    """
    try:
        adapter = get_adapter()

        # List with epic filter
        filters = {"ticket_type": TicketType.EPIC}
        epics = await adapter.list(limit=limit, offset=offset, filters=filters)

        return {
            "status": "completed",
            "epics": [epic.model_dump() for epic in epics],
            "count": len(epics),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list epics: {str(e)}",
        }


@mcp.tool()
async def epic_issues(epic_id: str) -> dict[str, Any]:
    """Get all issues belonging to an epic.

    Args:
        epic_id: Unique identifier of the epic

    Returns:
        List of issues in the epic, or error information

    """
    try:
        adapter = get_adapter()

        # Read the epic to get child issue IDs
        epic = await adapter.read(epic_id)
        if epic is None:
            return {
                "status": "error",
                "error": f"Epic {epic_id} not found",
            }

        # If epic has no child_issues attribute, use empty list
        child_issue_ids = getattr(epic, "child_issues", [])

        # Fetch each child issue
        issues = []
        for issue_id in child_issue_ids:
            issue = await adapter.read(issue_id)
            if issue:
                issues.append(issue.model_dump())

        return {
            "status": "completed",
            "epic_id": epic_id,
            "issues": issues,
            "count": len(issues),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get epic issues: {str(e)}",
        }


@mcp.tool()
async def issue_create(
    title: str,
    description: str = "",
    epic_id: str | None = None,
    assignee: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
    auto_detect_labels: bool = True,
) -> dict[str, Any]:
    """Create a new issue (standard work item) with automatic label detection.

    This tool automatically scans available labels/tags and intelligently
    applies relevant ones based on the issue title and description.

    Args:
        title: Issue title (required)
        description: Detailed description of the issue
        epic_id: Parent epic ID to link this issue to
        assignee: User ID or email to assign the issue to
        priority: Priority level - must be one of: low, medium, high, critical
        tags: List of tags to categorize the issue (auto-detection adds to these)
        auto_detect_labels: Automatically detect and apply relevant labels (default: True)

    Returns:
        Created issue details including ID and metadata, or error information

    """
    try:
        adapter = get_adapter()

        # Validate and convert priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
            }

        # Auto-detect labels if enabled
        final_tags = tags
        if auto_detect_labels:
            final_tags = await detect_and_apply_labels(
                adapter, title, description or "", tags
            )

        # Create issue (Task with ISSUE type)
        issue = Task(
            title=title,
            description=description or "",
            ticket_type=TicketType.ISSUE,
            parent_epic=epic_id,
            assignee=assignee,
            priority=priority_enum,
            tags=final_tags or [],
        )

        # Create via adapter
        created = await adapter.create(issue)

        return {
            "status": "completed",
            "issue": created.model_dump(),
            "labels_applied": created.tags or [],
            "auto_detected": auto_detect_labels,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create issue: {str(e)}",
        }


@mcp.tool()
async def issue_tasks(issue_id: str) -> dict[str, Any]:
    """Get all tasks (sub-items) belonging to an issue.

    Args:
        issue_id: Unique identifier of the issue

    Returns:
        List of tasks in the issue, or error information

    """
    try:
        adapter = get_adapter()

        # Read the issue to get child task IDs
        issue = await adapter.read(issue_id)
        if issue is None:
            return {
                "status": "error",
                "error": f"Issue {issue_id} not found",
            }

        # Get child task IDs
        child_task_ids = getattr(issue, "children", [])

        # Fetch each child task
        tasks = []
        for task_id in child_task_ids:
            task = await adapter.read(task_id)
            if task:
                tasks.append(task.model_dump())

        return {
            "status": "completed",
            "issue_id": issue_id,
            "tasks": tasks,
            "count": len(tasks),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get issue tasks: {str(e)}",
        }


@mcp.tool()
async def task_create(
    title: str,
    description: str = "",
    issue_id: str | None = None,
    assignee: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
    auto_detect_labels: bool = True,
) -> dict[str, Any]:
    """Create a new task (sub-work item) with automatic label detection.

    This tool automatically scans available labels/tags and intelligently
    applies relevant ones based on the task title and description.

    Args:
        title: Task title (required)
        description: Detailed description of the task
        issue_id: Parent issue ID to link this task to
        assignee: User ID or email to assign the task to
        priority: Priority level - must be one of: low, medium, high, critical
        tags: List of tags to categorize the task (auto-detection adds to these)
        auto_detect_labels: Automatically detect and apply relevant labels (default: True)

    Returns:
        Created task details including ID and metadata, or error information

    """
    try:
        adapter = get_adapter()

        # Validate and convert priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
            }

        # Auto-detect labels if enabled
        final_tags = tags
        if auto_detect_labels:
            final_tags = await detect_and_apply_labels(
                adapter, title, description or "", tags
            )

        # Create task (Task with TASK type)
        task = Task(
            title=title,
            description=description or "",
            ticket_type=TicketType.TASK,
            parent_issue=issue_id,
            assignee=assignee,
            priority=priority_enum,
            tags=final_tags or [],
        )

        # Create via adapter
        created = await adapter.create(task)

        return {
            "status": "completed",
            "task": created.model_dump(),
            "labels_applied": created.tags or [],
            "auto_detected": auto_detect_labels,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create task: {str(e)}",
        }


@mcp.tool()
async def epic_update(
    epic_id: str,
    title: str | None = None,
    description: str | None = None,
    state: str | None = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """Update an existing epic's metadata and description.

    Args:
        epic_id: Epic identifier (required)
        title: New title for the epic
        description: New description for the epic
        state: New state (open, in_progress, done, closed)
        target_date: Target completion date in ISO format (YYYY-MM-DD)

    Returns:
        Updated epic details, or error information

    """
    try:
        adapter = get_adapter()

        # Check if adapter supports epic updates
        if not hasattr(adapter, "update_epic"):
            return {
                "status": "error",
                "error": f"Epic updates not supported by {type(adapter).__name__} adapter",
                "epic_id": epic_id,
                "note": "Use ticket_update instead for basic field updates",
            }

        # Build updates dictionary
        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if state is not None:
            updates["state"] = state
        if target_date is not None:
            # Parse target date if provided
            try:
                target_datetime = datetime.fromisoformat(target_date)
                updates["target_date"] = target_datetime
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid date format '{target_date}'. Use ISO format: YYYY-MM-DD",
                }

        if not updates:
            return {
                "status": "error",
                "error": "No updates provided. At least one field (title, description, state, target_date) must be specified.",
            }

        # Update via adapter
        updated = await adapter.update_epic(epic_id, updates)  # type: ignore

        if updated is None:
            return {
                "status": "error",
                "error": f"Epic {epic_id} not found or update failed",
            }

        return {
            "status": "completed",
            "epic": updated.model_dump(),
        }
    except AttributeError as e:
        return {
            "status": "error",
            "error": f"Epic update method not available: {str(e)}",
            "epic_id": epic_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to update epic: {str(e)}",
            "epic_id": epic_id,
        }


@mcp.tool()
async def hierarchy_tree(
    epic_id: str,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Get complete hierarchy tree for an epic.

    Retrieves the full hierarchy tree starting from an epic, including all
    child issues and their tasks up to the specified depth.

    Args:
        epic_id: Unique identifier of the root epic
        max_depth: Maximum depth to traverse (1=epic only, 2=epic+issues, 3=epic+issues+tasks)

    Returns:
        Complete hierarchy tree structure, or error information

    """
    try:
        adapter = get_adapter()

        # Read the epic
        epic = await adapter.read(epic_id)
        if epic is None:
            return {
                "status": "error",
                "error": f"Epic {epic_id} not found",
            }

        # Build tree structure
        tree = {
            "epic": epic.model_dump(),
            "issues": [],
        }

        if max_depth < 2:
            return {
                "status": "completed",
                "tree": tree,
            }

        # Get child issues
        child_issue_ids = getattr(epic, "child_issues", [])
        for issue_id in child_issue_ids:
            issue = await adapter.read(issue_id)
            if issue:
                issue_data = {
                    "issue": issue.model_dump(),
                    "tasks": [],
                }

                if max_depth >= 3:
                    # Get child tasks
                    child_task_ids = getattr(issue, "children", [])
                    for task_id in child_task_ids:
                        task = await adapter.read(task_id)
                        if task:
                            issue_data["tasks"].append(task.model_dump())

                tree["issues"].append(issue_data)

        return {
            "status": "completed",
            "tree": tree,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to build hierarchy tree: {str(e)}",
        }
