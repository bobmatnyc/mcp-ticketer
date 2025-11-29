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

# Sentinel value to distinguish between "parameter not provided" and "explicitly None"
_UNSET = object()


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
    """Create epic/project/milestone (all adapters supported).

    Args: title (required), description, target_date (ISO YYYY-MM-DD), lead_id (user ID/email), child_issues (list of IDs)
    Returns: EpicResponse with created epic, ID, metadata
    See: docs/mcp-api-reference.md#epic-response-format
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
    """Read epic/project/milestone by ID (all adapters supported).

    Args: epic_id (required)
    Returns: EpicResponse with epic details
    See: docs/mcp-api-reference.md#epic-response-format
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
    project_id: str | None = None,
    include_completed: bool = False,
) -> dict[str, Any]:
    """List epics with pagination and filters (project scoping required).

    ⚠️ Project Filtering Required:
    This tool requires project_id parameter OR default_project configuration.
    To set default project: config_set_default_project(project_id="YOUR-PROJECT")
    To check current config: config_get()

    Args: limit (default: 10), offset, state (adapter-specific), project_id (required), include_completed (Linear, default: False)
    Returns: ListResponse with epics array, count
    See: docs/mcp-api-reference.md#list-response-format
    """
    try:
        # Validate project context (NEW: Required for list operations)
        from pathlib import Path

        from ....core.project_config import ConfigResolver

        resolver = ConfigResolver(project_path=Path.cwd())
        config = resolver.load_project_config()
        final_project = project_id or (config.default_project if config else None)

        if not final_project:
            return {
                "status": "error",
                "error": "project_id required. Provide project_id parameter or configure default_project.",
                "help": "Use config_set_default_project(project_id='YOUR-PROJECT') to set default project",
                "check_config": "Use config_get() to view current configuration",
            }

        adapter = get_adapter()

        # Check if adapter has optimized list_epics method
        if hasattr(adapter, "list_epics"):
            # Build kwargs for adapter-specific parameters with required project scoping
            kwargs: dict[str, Any] = {
                "limit": limit,
                "offset": offset,
                "project": final_project,
            }

            # Add state filter if supported
            if state is not None:
                kwargs["state"] = state

            # Add include_completed for Linear adapter
            adapter_type = adapter.adapter_type.lower()
            if adapter_type == "linear" and include_completed:
                kwargs["include_completed"] = include_completed

            epics = await adapter.list_epics(**kwargs)
        else:
            # Fallback to generic list method with epic filter and project scoping
            filters = {"ticket_type": TicketType.EPIC, "project": final_project}
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
    """Get all issues in epic (child issues list).

    Args: epic_id (required)
    Returns: IssueListResponse with issues array, count
    See: docs/mcp-api-reference.md#list-response-format
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
    epic_id: str | None = _UNSET,
    assignee: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
    auto_detect_labels: bool = True,
) -> dict[str, Any]:
    """Create issue with auto-label detection.

    Args: title (required), description, epic_id (parent), assignee, priority, tags, auto_detect_labels (default: True)
    Returns: IssueResponse with created issue, ID, metadata
    See: docs/mcp-api-reference.md#issue-response-format
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

        # Load configuration
        resolver = ConfigResolver(project_path=Path.cwd())
        config = resolver.load_project_config() or TicketerConfig()

        # Use default_user if no assignee specified
        final_assignee = assignee
        if final_assignee is None and config.default_user:
            final_assignee = config.default_user

        # Determine final_epic_id based on priority order:
        # Priority 1: Explicit epic_id argument (including explicit None for opt-out)
        # Priority 2: Config default (default_epic or default_project)

        final_epic_id: str | None = None

        if epic_id is not _UNSET:
            # Priority 1: Explicit value provided (including None for opt-out)
            final_epic_id = epic_id
        elif config.default_project or config.default_epic:
            # Priority 2: Use configured default
            final_epic_id = config.default_project or config.default_epic

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
    """Get parent issue of sub-issue (returns None if top-level).

    Args: issue_id (required)
    Returns: ParentResponse with parent issue details or None
    See: docs/mcp-api-reference.md#hierarchy-response
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
    """Get tasks in issue with optional filters (state, assignee, priority).

    Args: issue_id (required), state (optional), assignee (optional), priority (optional)
    Returns: TaskListResponse with tasks array, count, filters_applied
    See: docs/mcp-api-reference.md#list-response-format
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
    """Create task with auto-label detection.

    Args: title (required), description, issue_id (parent), assignee, priority, tags, auto_detect_labels (default: True)
    Returns: TaskResponse with created task, ID, metadata
    See: docs/mcp-api-reference.md#task-response-format
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
    """Update epic metadata (all adapters with update_epic method).

    Args: epic_id (required), title, description, state (adapter-specific), target_date (ISO YYYY-MM-DD)
    Returns: EpicResponse with updated epic
    See: docs/mcp-api-reference.md#epic-response-format
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
    """Delete epic/project/milestone (GitHub: permanent, Asana: archive, Linear/JIRA: not supported).

    Args: epic_id (required)
    Returns: DeleteResponse with status
    See: docs/mcp-api-reference.md#delete-response
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
    """Get full hierarchy tree (epic → issues → tasks, up to max_depth).

    Args: epic_id (required), max_depth (1=epic, 2=+issues, 3=+tasks, default: 3)
    Returns: TreeResponse with hierarchical structure
    See: docs/mcp-api-reference.md#hierarchy-tree-format
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
