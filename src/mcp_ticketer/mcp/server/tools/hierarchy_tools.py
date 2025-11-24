"""Hierarchy management tools for Epic/Issue/Task structure.

This module implements tools for managing the three-level ticket hierarchy:
- Epic: Strategic level containers
- Issue: Standard work items
- Task: Sub-work items
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from ....core.adapter import BaseAdapter
from ....core.models import Epic, Priority, Task, TicketType
from ....core.project_config import ConfigResolver, TicketerConfig
from ..server_sdk import get_adapter, mcp
from .ticket_tools import detect_and_apply_labels


def _build_adapter_metadata(
    adapter: BaseAdapter,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    """Build adapter metadata for MCP responses.

    Args:
        adapter: The adapter that handled the operation
        ticket_id: Optional ticket ID to include in metadata

    Returns:
        Dictionary with adapter metadata fields

    """
    metadata = {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }

    if ticket_id:
        metadata["ticket_id"] = ticket_id

    return metadata


@mcp.tool()
async def epic_create(
    title: str,
    description: str = "",
    target_date: str | None = None,
    lead_id: str | None = None,
    child_issues: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new epic (strategic level container).

    Adapter Support: All adapters support epic creation
    - Linear: Creates project with timeline (via create())
    - JIRA: Creates epic in configured project (dedicated create_epic())
    - GitHub: Creates milestone (via create_milestone())
    - Asana: Creates project (dedicated create_epic())
    - AiTrackDown: Creates epic in local storage (dedicated create_epic())

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
            **_build_adapter_metadata(adapter, created.id),
            "epic": created.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create epic: {str(e)}",
        }


@mcp.tool()
async def epic_get(epic_id: str) -> dict[str, Any]:
    """Read an epic by its ID.

    This tool retrieves detailed information about a specific epic/project/milestone.

    Adapter Support: All adapters support reading epics
    - Linear: Reads project details (via read())
    - JIRA: Reads epic with dedicated get_epic() method
    - GitHub: Reads milestone (via read())
    - Asana: Reads project with dedicated get_epic() method
    - AiTrackDown: Reads epic with dedicated get_epic() method

    Args:
        epic_id: Unique identifier of the epic to retrieve

    Returns:
        Epic details if found, or error information

    """
    try:
        adapter = get_adapter()

        # Use adapter's get_epic method if available (optimized for some adapters)
        if hasattr(adapter, "get_epic"):
            epic = await adapter.get_epic(epic_id)
        else:
            # Fallback to generic read method
            epic = await adapter.read(epic_id)

        if epic is None:
            return {
                "status": "error",
                "error": f"Epic {epic_id} not found",
                **_build_adapter_metadata(adapter, epic_id),
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, epic_id),
            "epic": epic.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get epic: {str(e)}",
        }


@mcp.tool()
async def epic_list(
    limit: int = 10,
    offset: int = 0,
    state: str | None = None,
    include_completed: bool = False,
) -> dict[str, Any]:
    """List all epics with pagination and optional filtering.

    Adapter Support: All adapters support listing epics
    - Linear: Optimized list_epics() with state filter and include_completed
    - JIRA: Optimized list_epics() with state filtering (mapped to JIRA status)
    - GitHub: Generic list() method (state filter not supported)
    - Asana: Optimized list_epics() method (state filter not supported)
    - AiTrackDown: Optimized list_epics() with basic pagination

    Adapter-Specific Parameters:
    - state: Supported by Linear (e.g., "planned", "started", "completed") and JIRA (e.g., "To Do", "In Progress", "Done")
    - include_completed: Linear-specific parameter to include/exclude completed projects

    Args:
        limit: Maximum number of epics to return (default: 10)
        offset: Number of epics to skip for pagination (default: 0)
        state: Optional state filter - adapter-specific behavior
        include_completed: Include completed epics (Linear-specific, default: False)

    Returns:
        List of epics with adapter information, or error information

    """
    try:
        adapter = get_adapter()

        # Check if adapter has optimized list_epics method
        if hasattr(adapter, "list_epics"):
            # Build kwargs for adapter-specific parameters
            kwargs: dict[str, Any] = {"limit": limit, "offset": offset}

            # Add state filter if supported
            if state is not None:
                kwargs["state"] = state

            # Add include_completed for Linear adapter
            adapter_type = adapter.adapter_type.lower()
            if adapter_type == "linear" and include_completed:
                kwargs["include_completed"] = include_completed

            epics = await adapter.list_epics(**kwargs)
        else:
            # Fallback to generic list method with epic filter
            filters = {"ticket_type": TicketType.EPIC}
            if state is not None:
                filters["state"] = state
            epics = await adapter.list(limit=limit, offset=offset, filters=filters)

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "epics": [epic.model_dump() for epic in epics],
            "count": len(epics),
            "limit": limit,
            "offset": offset,
            "filters_applied": {
                "state": state,
                "include_completed": include_completed,
            },
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
            **_build_adapter_metadata(adapter, epic_id),
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

        # Use default_user if no assignee specified
        final_assignee = assignee
        if final_assignee is None:
            resolver = ConfigResolver(project_path=Path.cwd())
            config = resolver.load_project_config() or TicketerConfig()
            if config.default_user:
                final_assignee = config.default_user

        # Use default_project if no epic_id specified
        final_epic_id = epic_id
        if final_epic_id is None:
            resolver = ConfigResolver(project_path=Path.cwd())
            config = resolver.load_project_config() or TicketerConfig()
            # Try default_project first, fall back to default_epic
            if config.default_project:
                final_epic_id = config.default_project
            elif config.default_epic:
                final_epic_id = config.default_epic

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
            parent_epic=final_epic_id,
            assignee=final_assignee,
            priority=priority_enum,
            tags=final_tags or [],
        )

        # Create via adapter
        created = await adapter.create(issue)

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, created.id),
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
async def issue_get_parent(issue_id: str) -> dict[str, Any]:
    """Get the parent issue of a sub-issue.

    This tool retrieves the parent issue details for a given sub-issue ID.
    Returns None if the issue has no parent (i.e., it's a top-level issue).

    Args:
        issue_id: Unique identifier of the sub-issue (e.g., "ENG-842", UUID)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - parent: Parent issue details (dict) if exists, None if no parent
        - adapter: Adapter type that handled the operation
        - adapter_name: Human-readable adapter name
        - error: Error message (if failed)

    Example response (has parent):
        {
            "status": "completed",
            "parent": {
                "id": "abc-123",
                "identifier": "ENG-840",
                "title": "Implement hierarchy features",
                "state": "in_progress",
                ...
            },
            "adapter": "linear",
            "adapter_name": "Linear"
        }

    Example response (no parent):
        {
            "status": "completed",
            "parent": None,
            "adapter": "linear",
            "adapter_name": "Linear"
        }

    """
    try:
        adapter = get_adapter()

        # Read the issue to check if it has a parent
        issue = await adapter.read(issue_id)
        if issue is None:
            return {
                "status": "error",
                "error": f"Issue {issue_id} not found",
            }

        # Check for parent_issue attribute (sub-issues have this set)
        parent_issue_id = getattr(issue, "parent_issue", None)

        if not parent_issue_id:
            # No parent - this is a top-level issue
            return {
                "status": "completed",
                **_build_adapter_metadata(adapter, issue_id),
                "parent": None,
            }

        # Fetch parent issue details
        parent_issue = await adapter.read(parent_issue_id)
        if parent_issue is None:
            return {
                "status": "error",
                "error": f"Parent issue {parent_issue_id} not found",
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, issue_id),
            "parent": parent_issue.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get parent issue: {str(e)}",
        }


@mcp.tool()
async def issue_tasks(
    issue_id: str,
    state: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """Get all tasks (sub-items) belonging to an issue with optional filtering.

    This tool retrieves child tasks/sub-issues for a given issue ID, with support
    for filtering by state, assignee, and priority. All filter parameters are optional.

    Args:
        issue_id: Unique identifier of the issue
        state: Optional state filter - must be one of: open, in_progress, ready,
            tested, done, closed, waiting, blocked
        assignee: Optional user ID or email to filter by assignee
        priority: Optional priority filter - must be one of: low, medium, high, critical

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - tasks: List of task objects matching filters
        - count: Number of tasks returned
        - filters_applied: Dict showing which filters were used
        - adapter: Adapter type that handled the operation
        - error: Error message (if failed)

    Example:
        # Get all tasks for issue
        result = issue_tasks("ENG-840")

        # Get only in-progress tasks assigned to user
        result = issue_tasks("ENG-840", state="in_progress", assignee="user@example.com")

        # Get high priority tasks
        result = issue_tasks("ENG-840", priority="high")

    """
    try:
        adapter = get_adapter()

        # Validate filter parameters
        filters_applied = {}

        # Validate state if provided
        if state is not None:
            try:
                from ....core.models import TicketState

                state_enum = TicketState(state.lower())
                filters_applied["state"] = state_enum.value
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid state '{state}'. Must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked",
                }

        # Validate priority if provided
        if priority is not None:
            try:
                from ....core.models import Priority

                priority_enum = Priority(priority.lower())
                filters_applied["priority"] = priority_enum.value
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
                }

        if assignee is not None:
            filters_applied["assignee"] = assignee

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
                # Apply filters
                should_include = True

                # Filter by state
                if state is not None:
                    task_state = getattr(task, "state", None)
                    # Handle case where state might be stored as string
                    if isinstance(task_state, str):
                        should_include = should_include and (
                            task_state.lower() == state.lower()
                        )
                    else:
                        should_include = should_include and (task_state == state_enum)

                # Filter by priority
                if priority is not None:
                    task_priority = getattr(task, "priority", None)
                    # Handle case where priority might be stored as string
                    if isinstance(task_priority, str):
                        should_include = should_include and (
                            task_priority.lower() == priority.lower()
                        )
                    else:
                        should_include = should_include and (
                            task_priority == priority_enum
                        )

                # Filter by assignee
                if assignee is not None:
                    task_assignee = getattr(task, "assignee", None)
                    # Case-insensitive comparison for emails/usernames
                    should_include = should_include and (
                        task_assignee is not None
                        and assignee.lower() in str(task_assignee).lower()
                    )

                if should_include:
                    tasks.append(task.model_dump())

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, issue_id),
            "tasks": tasks,
            "count": len(tasks),
            "filters_applied": filters_applied,
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

        # Use default_user if no assignee specified
        final_assignee = assignee
        if final_assignee is None:
            resolver = ConfigResolver(project_path=Path.cwd())
            config = resolver.load_project_config() or TicketerConfig()
            if config.default_user:
                final_assignee = config.default_user

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
            assignee=final_assignee,
            priority=priority_enum,
            tags=final_tags or [],
        )

        # Create via adapter
        created = await adapter.create(task)

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, created.id),
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

    Adapter Support: All adapters support epic updates with dedicated update_epic() method
    - Linear: ✓ Updates project fields (title, description, state, target_date, etc.)
    - JIRA: ✓ Updates epic fields (title, description, status, due date)
    - GitHub: ✓ Updates milestone (title, description, state, due_on)
    - Asana: ✓ Updates project metadata (name, notes, due_on, color, etc.)
    - AiTrackDown: ✓ Updates epic in local storage

    Supported Update Fields:
    - title: Epic/project/milestone title (all adapters)
    - description: Detailed description (all adapters)
    - state: Epic state - adapter-specific values (Linear, JIRA, GitHub)
    - target_date: Due date in ISO format YYYY-MM-DD (all adapters)

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
            adapter_name = adapter.adapter_display_name
            return {
                "status": "error",
                "error": f"Epic updates not supported by {adapter_name} adapter",
                "epic_id": epic_id,
                "note": "This adapter should implement update_epic() method",
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
        updated = await adapter.update_epic(epic_id, updates)

        if updated is None:
            return {
                "status": "error",
                "error": f"Epic {epic_id} not found or update failed",
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, epic_id),
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
async def epic_delete(epic_id: str) -> dict[str, Any]:
    """Delete an epic/project/milestone by ID.

    Adapter Support:
    - GitHub: ✓ Deletes milestone (delete_epic() - permanent deletion)
    - Asana: ✓ Archives project (delete_epic() - can be restored from archive)
    - Linear: ✗ Linear API doesn't support project deletion
    - JIRA: ✗ JIRA API doesn't support epic deletion
    - AiTrackDown: ✗ Epic deletion not implemented yet

    Important Notes:
    - GitHub: Deletion is permanent and cannot be undone
    - Asana: Project is archived, not deleted, and can be restored
    - For unsupported adapters, the tool returns an error with details

    Args:
        epic_id: Unique identifier of the epic to delete

    Returns:
        Success/failure status with adapter information

    """
    try:
        adapter = get_adapter()

        # Check if adapter supports epic deletion
        if not hasattr(adapter, "delete_epic"):
            adapter_name = adapter.adapter_display_name
            return {
                "status": "error",
                "error": f"Epic deletion not supported by {adapter_name} adapter",
                **_build_adapter_metadata(adapter, epic_id),
                "supported_adapters": ["GitHub", "Asana"],
                "note": f"{adapter_name} does not provide API support for deleting epics/projects",
            }

        # Call adapter's delete_epic method
        success = await adapter.delete_epic(epic_id)

        if not success:
            return {
                "status": "error",
                "error": f"Failed to delete epic {epic_id}",
                **_build_adapter_metadata(adapter, epic_id),
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, epic_id),
            "message": f"Epic {epic_id} deleted successfully",
            "deleted": True,
        }
    except AttributeError:
        adapter_name = adapter.adapter_display_name
        return {
            "status": "error",
            "error": f"Epic deletion not supported by {adapter_name} adapter",
            **_build_adapter_metadata(adapter, epic_id),
            "supported_adapters": ["GitHub", "Asana"],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to delete epic: {str(e)}",
            **_build_adapter_metadata(adapter, epic_id),
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
            **_build_adapter_metadata(adapter, epic_id),
            "tree": tree,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to build hierarchy tree: {str(e)}",
        }
