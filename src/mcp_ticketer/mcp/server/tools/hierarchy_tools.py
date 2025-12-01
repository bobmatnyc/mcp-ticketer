"""Hierarchy management tools for Epic/Issue/Task structure.

This module implements tools for managing the three-level ticket hierarchy:
- Epic: Strategic level containers
- Issue: Standard work items
- Task: Sub-work items

The unified `hierarchy()` tool consolidates 11 separate tools into a single interface
for all hierarchy management operations.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

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
async def hierarchy(
    entity_type: Literal["epic", "issue", "task"],
    action: Literal[
        "create",
        "get",
        "list",
        "update",
        "delete",
        "get_children",
        "get_parent",
        "get_tree",
    ],
    # Entity identification
    entity_id: str | None = None,
    epic_id: str | None = None,
    issue_id: str | None = None,
    # Creation/Update parameters
    title: str | None = None,
    description: str = "",
    # Epic-specific
    target_date: str | None = None,
    lead_id: str | None = None,
    child_issues: list[str] | None = None,
    # List parameters
    project_id: str | None = None,
    state: str | None = None,
    limit: int = 10,
    offset: int = 0,
    include_completed: bool = False,
    # Tree parameters
    max_depth: int = 3,
    # Task/Issue parameters
    assignee: str | None = None,
    priority: str = "medium",
    tags: list[str] | None = None,
    auto_detect_labels: bool = True,
) -> dict[str, Any]:
    """Unified hierarchy management tool for epics, issues, and tasks.

    Consolidates 11 separate hierarchy tools into a single interface for
    all CRUD operations and hierarchical relationships across the three-tier
    structure: Epic → Issue → Task.

    This tool replaces:
    - epic_create, epic_get, epic_list, epic_update, epic_delete, epic_issues
    - issue_create, issue_get_parent, issue_tasks
    - task_create
    - hierarchy_tree

    Args:
        entity_type: Type of entity - "epic", "issue", or "task"
        action: Operation to perform - create, get, list, update, delete,
                get_children, get_parent, or get_tree
        entity_id: ID for get/update/delete operations
        epic_id: Parent epic ID (for issues/tasks/get_children)
        issue_id: Parent issue ID (for tasks/get_parent/get_children)
        title: Title for create/update operations
        description: Description for create/update operations
        target_date: Target date for epics (ISO YYYY-MM-DD format)
        lead_id: Lead user ID for epics
        child_issues: List of child issue IDs for epics
        project_id: Project filter for list operations
        state: State filter for list operations
        limit: Maximum results for list operations (default: 10)
        offset: Pagination offset for list operations (default: 0)
        include_completed: Include completed items in epic lists (default: False)
        max_depth: Maximum depth for tree operations (1-3, default: 3)
        assignee: Assigned user for issues/tasks
        priority: Priority level - low, medium, high, critical (default: medium)
        tags: Tags/labels for issues/tasks
        auto_detect_labels: Auto-detect labels from title/description (default: True)

    Returns:
        Operation results in standard format with status, data, and metadata

    Raises:
        ValueError: If action/entity_type combination is invalid

    Examples:
        # Create epic
        await hierarchy(
            entity_type="epic",
            action="create",
            title="Q4 Features",
            description="New features for Q4",
            target_date="2025-12-31"
        )

        # Get epic details
        await hierarchy(
            entity_type="epic",
            action="get",
            entity_id="EPIC-123"
        )

        # List epics in project
        await hierarchy(
            entity_type="epic",
            action="list",
            project_id="PROJECT-1",
            limit=20
        )

        # Get epic's child issues
        await hierarchy(
            entity_type="epic",
            action="get_children",
            entity_id="EPIC-123"
        )

        # Create issue under epic
        await hierarchy(
            entity_type="issue",
            action="create",
            title="User authentication",
            description="Implement OAuth2 flow",
            epic_id="EPIC-123",
            priority="high"
        )

        # Get issue's parent
        await hierarchy(
            entity_type="issue",
            action="get_parent",
            entity_id="ISSUE-456"
        )

        # Get issue's child tasks
        await hierarchy(
            entity_type="issue",
            action="get_children",
            entity_id="ISSUE-456",
            state="open"
        )

        # Create task under issue
        await hierarchy(
            entity_type="task",
            action="create",
            title="Write tests",
            issue_id="ISSUE-456",
            priority="medium"
        )

        # Get full hierarchy tree
        await hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-123",
            max_depth=3
        )

        # Update epic
        await hierarchy(
            entity_type="epic",
            action="update",
            entity_id="EPIC-123",
            title="Updated Title",
            state="in_progress"
        )

        # Delete epic
        await hierarchy(
            entity_type="epic",
            action="delete",
            entity_id="EPIC-123"
        )

    Migration from old tools:
        epic_create(...) → hierarchy(entity_type="epic", action="create", ...)
        epic_get(epic_id) → hierarchy(entity_type="epic", action="get", entity_id=epic_id)
        epic_list(...) → hierarchy(entity_type="epic", action="list", ...)
        epic_update(...) → hierarchy(entity_type="epic", action="update", ...)
        epic_delete(epic_id) → hierarchy(entity_type="epic", action="delete", entity_id=epic_id)
        epic_issues(epic_id) → hierarchy(entity_type="epic", action="get_children", entity_id=epic_id)
        issue_create(...) → hierarchy(entity_type="issue", action="create", ...)
        issue_get_parent(issue_id) → hierarchy(entity_type="issue", action="get_parent", entity_id=issue_id)
        issue_tasks(issue_id) → hierarchy(entity_type="issue", action="get_children", entity_id=issue_id)
        task_create(...) → hierarchy(entity_type="task", action="create", ...)
        hierarchy_tree(epic_id) → hierarchy(entity_type="epic", action="get_tree", entity_id=epic_id)

    See: docs/mcp-api-reference.md for detailed response formats
    """
    # Normalize entity_type and action to lowercase for case-insensitive matching
    entity_type_lower = entity_type.lower()
    action_lower = action.lower()

    # Route to appropriate handler based on entity_type + action
    try:
        if entity_type_lower == "epic":
            if action_lower == "create":
                return await epic_create(
                    title=title or "",
                    description=description,
                    target_date=target_date,
                    lead_id=lead_id,
                    child_issues=child_issues,
                )
            elif action_lower == "get":
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get operation",
                    }
                return await epic_get(epic_id=entity_id or epic_id or "")
            elif action_lower == "list":
                return await epic_list(
                    limit=limit,
                    offset=offset,
                    state=state,
                    project_id=project_id,
                    include_completed=include_completed,
                )
            elif action_lower == "update":
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for update operation",
                    }
                return await epic_update(
                    epic_id=entity_id or epic_id or "",
                    title=title,
                    description=description,
                    state=state,
                    target_date=target_date,
                )
            elif action_lower == "delete":
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for delete operation",
                    }
                return await epic_delete(epic_id=entity_id or epic_id or "")
            elif action_lower == "get_children":
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get_children operation",
                    }
                return await epic_issues(epic_id=entity_id or epic_id or "")
            elif action_lower == "get_tree":
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get_tree operation",
                    }
                return await hierarchy_tree(
                    epic_id=entity_id or epic_id or "", max_depth=max_depth
                )
            else:
                valid_actions = [
                    "create",
                    "get",
                    "list",
                    "update",
                    "delete",
                    "get_children",
                    "get_tree",
                ]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'epic'",
                    "valid_actions": valid_actions,
                    "hint": f"Use hierarchy(entity_type='epic', action=<one of {valid_actions}>, ...)",
                }

        elif entity_type_lower == "issue":
            if action_lower == "create":
                # Handle epic_id with sentinel for explicit None
                final_epic_id = _UNSET if epic_id is None else epic_id
                return await issue_create(
                    title=title or "",
                    description=description,
                    epic_id=final_epic_id,
                    assignee=assignee,
                    priority=priority,
                    tags=tags,
                    auto_detect_labels=auto_detect_labels,
                )
            elif action_lower == "get_parent":
                if not entity_id and not issue_id:
                    return {
                        "status": "error",
                        "error": "entity_id or issue_id required for get_parent operation",
                    }
                return await issue_get_parent(issue_id=entity_id or issue_id or "")
            elif action_lower == "get_children":
                if not entity_id and not issue_id:
                    return {
                        "status": "error",
                        "error": "entity_id or issue_id required for get_children operation",
                    }
                return await issue_tasks(
                    issue_id=entity_id or issue_id or "",
                    state=state,
                    assignee=assignee,
                    priority=priority,
                )
            else:
                valid_actions = ["create", "get_parent", "get_children"]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'issue'",
                    "valid_actions": valid_actions,
                    "hint": f"Use hierarchy(entity_type='issue', action=<one of {valid_actions}>, ...)",
                }

        elif entity_type_lower == "task":
            if action_lower == "create":
                return await task_create(
                    title=title or "",
                    description=description,
                    issue_id=issue_id,
                    assignee=assignee,
                    priority=priority,
                    tags=tags,
                    auto_detect_labels=auto_detect_labels,
                )
            else:
                valid_actions = ["create"]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'task'",
                    "valid_actions": valid_actions,
                    "hint": "Use hierarchy(entity_type='task', action='create', ...)",
                    "note": "Tasks support only create operation. Use ticket_read/ticket_update for other operations.",
                }

        else:
            valid_types = ["epic", "issue", "task"]
            return {
                "status": "error",
                "error": f"Invalid entity_type: {entity_type}",
                "valid_entity_types": valid_types,
                "hint": f"Use hierarchy(entity_type=<one of {valid_types}>, action=..., ...)",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Hierarchy operation failed: {str(e)}",
            "entity_type": entity_type,
            "action": action,
        }


@mcp.tool()
async def epic_create(
    title: str,
    description: str = "",
    target_date: str | None = None,
    lead_id: str | None = None,
    child_issues: list[str] | None = None,
) -> dict[str, Any]:
    """Create epic/project/milestone (all adapters supported).

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='create'`` instead.
        This function will be removed in version 2.0.0.

    Args: title (required), description, target_date (ISO YYYY-MM-DD), lead_id (user ID/email), child_issues (list of IDs)
    Returns: EpicResponse with created epic, ID, metadata
    See: docs/mcp-api-reference.md#epic-response-format

    Migration:
        epic_create(...) → hierarchy(entity_type="epic", action="create", ...)
    """
    import warnings

    warnings.warn(
        "epic_create is deprecated. Use hierarchy(entity_type='epic', action='create', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='get'`` instead.
        This function will be removed in version 2.0.0.

    Args: epic_id (required)
    Returns: EpicResponse with epic details
    See: docs/mcp-api-reference.md#epic-response-format

    Migration:
        epic_get(epic_id) → hierarchy(entity_type="epic", action="get", entity_id=epic_id)
    """
    import warnings

    warnings.warn(
        "epic_get is deprecated. Use hierarchy(entity_type='epic', action='get', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='list'`` instead.
        This function will be removed in version 2.0.0.

    ⚠️ Project Filtering Required:
    This tool requires project_id parameter OR default_project configuration.
    To set default project: config_set_default_project(project_id="YOUR-PROJECT")
    To check current config: config_get()

    Args: limit (default: 10), offset, state (adapter-specific), project_id (required), include_completed (Linear, default: False)
    Returns: ListResponse with epics array, count
    See: docs/mcp-api-reference.md#list-response-format

    Migration:
        epic_list(...) → hierarchy(entity_type="epic", action="list", ...)
    """
    import warnings

    warnings.warn(
        "epic_list is deprecated. Use hierarchy(entity_type='epic', action='list', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='get_children'`` instead.
        This function will be removed in version 2.0.0.

    Args: epic_id (required)
    Returns: IssueListResponse with issues array, count
    See: docs/mcp-api-reference.md#list-response-format

    Migration:
        epic_issues(epic_id) → hierarchy(entity_type="epic", action="get_children", entity_id=epic_id)
    """
    import warnings

    warnings.warn(
        "epic_issues is deprecated. Use hierarchy(entity_type='epic', action='get_children', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='issue', action='create'`` instead.
        This function will be removed in version 2.0.0.

    Args: title (required), description, epic_id (parent), assignee, priority, tags, auto_detect_labels (default: True)
    Returns: IssueResponse with created issue, ID, metadata
    See: docs/mcp-api-reference.md#issue-response-format

    Migration:
        issue_create(...) → hierarchy(entity_type="issue", action="create", ...)
    """
    import warnings

    warnings.warn(
        "issue_create is deprecated. Use hierarchy(entity_type='issue', action='create', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='issue', action='get_parent'`` instead.
        This function will be removed in version 2.0.0.

    Args: issue_id (required)
    Returns: ParentResponse with parent issue details or None
    See: docs/mcp-api-reference.md#hierarchy-response

    Migration:
        issue_get_parent(issue_id) → hierarchy(entity_type="issue", action="get_parent", entity_id=issue_id)
    """
    import warnings

    warnings.warn(
        "issue_get_parent is deprecated. Use hierarchy(entity_type='issue', action='get_parent', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='issue', action='get_children'`` instead.
        This function will be removed in version 2.0.0.

    Args: issue_id (required), state (optional), assignee (optional), priority (optional)
    Returns: TaskListResponse with tasks array, count, filters_applied
    See: docs/mcp-api-reference.md#list-response-format

    Migration:
        issue_tasks(issue_id, ...) → hierarchy(entity_type="issue", action="get_children", entity_id=issue_id, ...)
    """
    import warnings

    warnings.warn(
        "issue_tasks is deprecated. Use hierarchy(entity_type='issue', action='get_children', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='task', action='create'`` instead.
        This function will be removed in version 2.0.0.

    Args: title (required), description, issue_id (parent), assignee, priority, tags, auto_detect_labels (default: True)
    Returns: TaskResponse with created task, ID, metadata
    See: docs/mcp-api-reference.md#task-response-format

    Migration:
        task_create(...) → hierarchy(entity_type="task", action="create", ...)
    """
    import warnings

    warnings.warn(
        "task_create is deprecated. Use hierarchy(entity_type='task', action='create', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='update'`` instead.
        This function will be removed in version 2.0.0.

    Args: epic_id (required), title, description, state (adapter-specific), target_date (ISO YYYY-MM-DD)
    Returns: EpicResponse with updated epic
    See: docs/mcp-api-reference.md#epic-response-format

    Migration:
        epic_update(epic_id, ...) → hierarchy(entity_type="epic", action="update", entity_id=epic_id, ...)
    """
    import warnings

    warnings.warn(
        "epic_update is deprecated. Use hierarchy(entity_type='epic', action='update', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='delete'`` instead.
        This function will be removed in version 2.0.0.

    Args: epic_id (required)
    Returns: DeleteResponse with status
    See: docs/mcp-api-reference.md#delete-response

    Migration:
        epic_delete(epic_id) → hierarchy(entity_type="epic", action="delete", entity_id=epic_id)
    """
    import warnings

    warnings.warn(
        "epic_delete is deprecated. Use hierarchy(entity_type='epic', action='delete', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

    .. deprecated:: 1.5.0
        Use :func:`hierarchy` with ``entity_type='epic', action='get_tree'`` instead.
        This function will be removed in version 2.0.0.

    Args: epic_id (required), max_depth (1=epic, 2=+issues, 3=+tasks, default: 3)
    Returns: TreeResponse with hierarchical structure
    See: docs/mcp-api-reference.md#hierarchy-tree-format

    Migration:
        hierarchy_tree(epic_id, max_depth) → hierarchy(entity_type="epic", action="get_tree", entity_id=epic_id, max_depth=max_depth)
    """
    import warnings

    warnings.warn(
        "hierarchy_tree is deprecated. Use hierarchy(entity_type='epic', action='get_tree', entity_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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
