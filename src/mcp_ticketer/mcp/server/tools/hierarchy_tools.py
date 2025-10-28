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
) -> dict[str, Any]:
    """Create a new issue (standard work item).

    Args:
        title: Issue title (required)
        description: Detailed description of the issue
        epic_id: Parent epic ID to link this issue to
        assignee: User ID or email to assign the issue to
        priority: Priority level - must be one of: low, medium, high, critical

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

        # Create issue (Task with ISSUE type)
        issue = Task(
            title=title,
            description=description or "",
            ticket_type=TicketType.ISSUE,
            parent_epic=epic_id,
            assignee=assignee,
            priority=priority_enum,
        )

        # Create via adapter
        created = await adapter.create(issue)

        return {
            "status": "completed",
            "issue": created.model_dump(),
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
) -> dict[str, Any]:
    """Create a new task (sub-work item).

    Args:
        title: Task title (required)
        description: Detailed description of the task
        issue_id: Parent issue ID to link this task to
        assignee: User ID or email to assign the task to
        priority: Priority level - must be one of: low, medium, high, critical

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

        # Create task (Task with TASK type)
        task = Task(
            title=title,
            description=description or "",
            ticket_type=TicketType.TASK,
            parent_issue=issue_id,
            assignee=assignee,
            priority=priority_enum,
        )

        # Create via adapter
        created = await adapter.create(task)

        return {
            "status": "completed",
            "task": created.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create task: {str(e)}",
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
