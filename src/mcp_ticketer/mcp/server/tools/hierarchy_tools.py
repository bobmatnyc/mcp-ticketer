"""Hierarchy management tools for Epic/Issue/Task structure (v2.0.0).

This module implements tools for managing the three-level ticket hierarchy:
- Epic: Strategic level containers
- Issue: Standard work items
- Task: Sub-work items

Version 2.0.0 changes:
- Removed all deprecated functions (epic_create, epic_get, epic_list, etc.)
- Single `hierarchy()` function provides all hierarchy operations
- All deprecated function logic has been inlined into the unified interface
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from ....core.adapter import BaseAdapter
from ....core.models import (
    Epic,
    Priority,
    RelationType,
    Task,
    TicketType,
)
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


@mcp.tool(
    description="Manage ticket hierarchy - create/read/update/delete epics, issues, tasks; navigate parent-child relationships; build tree views of epic→issue→task structure"
)
async def ticket_hierarchy(
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
        "add_relation",
        "remove_relation",
        "list_relations",
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
    max_auto_labels: int = 4,
    # Relationship parameters
    source_id: str | None = None,
    target_id: str | None = None,
    relation_type: str | None = None,
) -> dict[str, Any]:
    """Unified hierarchy management tool for epics, issues, and tasks.

    Consolidates 11 separate hierarchy tools into a single interface for
    all CRUD operations and hierarchical relationships across the three-tier
    structure: Epic → Issue → Task.

    This tool replaces:
    - epic_create, epic_get, epic_list, epic_update, epic_delete, epic_issues
    - issue_create, issue_get_parent, issue_tasks
    - task_create
    - hierarchy_tree (deprecated name: hierarchy)

    Args:
        entity_type: Type of entity - "epic", "issue", or "task"
        action: Operation to perform - create, get, list, update, delete,
                get_children, get_parent, get_tree, add_relation, remove_relation,
                or list_relations
        entity_id: ID for get/update/delete/list_relations operations
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
        max_auto_labels: Maximum number of auto-detected labels to apply (default: 4)
        source_id: Source ticket ID for relationship operations
        target_id: Target ticket ID for relationship operations
        relation_type: Type of relationship - blocks, blocked_by, relates_to,
                      duplicates, or duplicated_by

    Returns:
        Operation results in standard format with status, data, and metadata

    Raises:
        ValueError: If action/entity_type combination is invalid

    Examples:
        # Create epic
        await ticket_hierarchy(
            entity_type="epic",
            action="create",
            title="Q4 Features",
            description="New features for Q4",
            target_date="2025-12-31"
        )

        # Get epic details
        await ticket_hierarchy(
            entity_type="epic",
            action="get",
            entity_id="EPIC-123"
        )

        # List epics in project
        await ticket_hierarchy(
            entity_type="epic",
            action="list",
            project_id="PROJECT-1",
            limit=20
        )

        # Get epic's child issues
        await ticket_hierarchy(
            entity_type="epic",
            action="get_children",
            entity_id="EPIC-123"
        )

        # Create issue under epic
        await ticket_hierarchy(
            entity_type="issue",
            action="create",
            title="User authentication",
            description="Implement OAuth2 flow",
            epic_id="EPIC-123",
            priority="high"
        )

        # Get issue's parent
        await ticket_hierarchy(
            entity_type="issue",
            action="get_parent",
            entity_id="ISSUE-456"
        )

        # Get issue's child tasks
        await ticket_hierarchy(
            entity_type="issue",
            action="get_children",
            entity_id="ISSUE-456",
            state="open"
        )

        # Create task under issue
        await ticket_hierarchy(
            entity_type="task",
            action="create",
            title="Write tests",
            issue_id="ISSUE-456",
            priority="medium"
        )

        # Get full hierarchy tree
        await ticket_hierarchy(
            entity_type="epic",
            action="get_tree",
            entity_id="EPIC-123",
            max_depth=3
        )

        # Update epic
        await ticket_hierarchy(
            entity_type="epic",
            action="update",
            entity_id="EPIC-123",
            title="Updated Title",
            state="in_progress"
        )

        # Delete epic
        await ticket_hierarchy(
            entity_type="epic",
            action="delete",
            entity_id="EPIC-123"
        )

        # Add relationship (blocking dependency)
        await ticket_hierarchy(
            entity_type="epic",
            action="add_relation",
            source_id="ISSUE-123",
            target_id="ISSUE-456",
            relation_type="blocks"
        )

        # Remove relationship
        await ticket_hierarchy(
            entity_type="issue",
            action="remove_relation",
            source_id="ISSUE-123",
            target_id="ISSUE-456",
            relation_type="blocks"
        )

        # List all relationships for a ticket
        await ticket_hierarchy(
            entity_type="task",
            action="list_relations",
            entity_id="TASK-789"
        )

        # List specific relationship type
        await ticket_hierarchy(
            entity_type="epic",
            action="list_relations",
            entity_id="EPIC-123",
            relation_type="blocks"
        )

    Migration from old tools:
        epic_create(...) → ticket_hierarchy(entity_type="epic", action="create", ...)
        epic_get(epic_id) → ticket_hierarchy(entity_type="epic", action="get", entity_id=epic_id)
        epic_list(...) → ticket_hierarchy(entity_type="epic", action="list", ...)
        epic_update(...) → ticket_hierarchy(entity_type="epic", action="update", ...)
        epic_delete(epic_id) → ticket_hierarchy(entity_type="epic", action="delete", entity_id=epic_id)
        epic_issues(epic_id) → ticket_hierarchy(entity_type="epic", action="get_children", entity_id=epic_id)
        issue_create(...) → ticket_hierarchy(entity_type="issue", action="create", ...)
        issue_get_parent(issue_id) → ticket_hierarchy(entity_type="issue", action="get_parent", entity_id=issue_id)
        issue_tasks(issue_id) → ticket_hierarchy(entity_type="issue", action="get_children", entity_id=issue_id)
        task_create(...) → ticket_hierarchy(entity_type="task", action="create", ...)
        hierarchy_tree(epic_id) → ticket_hierarchy(entity_type="epic", action="get_tree", entity_id=epic_id)

    See: docs/mcp-api-reference.md for detailed response formats
    """
    # Normalize entity_type and action to lowercase for case-insensitive matching
    entity_type_lower = entity_type.lower()
    action_lower = action.lower()

    # Route to appropriate handler based on entity_type + action
    try:
        adapter = get_adapter()

        # Relationship operations (entity_type independent) - check FIRST
        if action_lower == "add_relation":
            if not source_id or not target_id or not relation_type:
                return {
                    "status": "error",
                    "error": "source_id, target_id, and relation_type required for add_relation",
                    "hint": "Example: ticket_hierarchy(entity_type='epic', action='add_relation', source_id='ISSUE-123', target_id='ISSUE-456', relation_type='blocks')",
                }
            try:
                rel_type = RelationType(relation_type)
            except ValueError:
                valid_types = [r.value for r in RelationType]
                return {
                    "status": "error",
                    "error": f"Invalid relation_type '{relation_type}'. Must be one of: {valid_types}",
                }
            try:
                relation = await adapter.add_relation(source_id, target_id, rel_type)
                return {
                    "status": "completed",
                    "operation": "add_relation",
                    **_build_adapter_metadata(adapter),
                    "relation": relation.model_dump(),
                }
            except NotImplementedError:
                return {
                    "status": "error",
                    "error": f"Ticket relationships not supported by {adapter.adapter_display_name} adapter",
                    **_build_adapter_metadata(adapter),
                    "note": "This adapter does not implement relationship support",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to add relation: {str(e)}",
                    **_build_adapter_metadata(adapter),
                }

        elif action_lower == "remove_relation":
            if not source_id or not target_id or not relation_type:
                return {
                    "status": "error",
                    "error": "source_id, target_id, and relation_type required for remove_relation",
                    "hint": "Example: ticket_hierarchy(entity_type='issue', action='remove_relation', source_id='ISSUE-123', target_id='ISSUE-456', relation_type='blocks')",
                }
            try:
                rel_type = RelationType(relation_type)
            except ValueError:
                valid_types = [r.value for r in RelationType]
                return {
                    "status": "error",
                    "error": f"Invalid relation_type '{relation_type}'. Must be one of: {valid_types}",
                }
            try:
                success = await adapter.remove_relation(source_id, target_id, rel_type)
                return {
                    "status": "completed",
                    "operation": "remove_relation",
                    **_build_adapter_metadata(adapter),
                    "removed": success,
                }
            except NotImplementedError:
                return {
                    "status": "error",
                    "error": f"Ticket relationships not supported by {adapter.adapter_display_name} adapter",
                    **_build_adapter_metadata(adapter),
                    "note": "This adapter does not implement relationship support",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to remove relation: {str(e)}",
                    **_build_adapter_metadata(adapter),
                }

        elif action_lower == "list_relations":
            if not entity_id:
                return {
                    "status": "error",
                    "error": "entity_id required for list_relations",
                    "hint": "Example: ticket_hierarchy(entity_type='task', action='list_relations', entity_id='TASK-789')",
                }
            try:
                rel_type = RelationType(relation_type) if relation_type else None
                relations = await adapter.list_relations(entity_id, rel_type)
                return {
                    "status": "completed",
                    "operation": "list_relations",
                    **_build_adapter_metadata(adapter, entity_id),
                    "relations": [r.model_dump() for r in relations],
                    "count": len(relations),
                    "filter_applied": rel_type.value if rel_type else None,
                }
            except ValueError:
                valid_types = [r.value for r in RelationType]
                return {
                    "status": "error",
                    "error": f"Invalid relation_type '{relation_type}'. Must be one of: {valid_types}",
                }
            except NotImplementedError:
                return {
                    "status": "error",
                    "error": f"Ticket relationships not supported by {adapter.adapter_display_name} adapter",
                    **_build_adapter_metadata(adapter, entity_id),
                    "note": "This adapter does not implement relationship support",
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Failed to list relations: {str(e)}",
                    **_build_adapter_metadata(adapter, entity_id),
                }

        # Entity-specific operations
        if entity_type_lower == "epic":
            if action_lower == "create":
                # Inline implementation of epic_create
                try:
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
                        title=title or "",
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

            elif action_lower == "get":
                # Inline implementation of epic_get
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get operation",
                    }
                try:
                    final_epic_id = entity_id or epic_id or ""

                    # Use adapter's get_epic method if available (optimized for some adapters)
                    if hasattr(adapter, "get_epic"):
                        epic = await adapter.get_epic(final_epic_id)
                    else:
                        # Fallback to generic read method
                        epic = await adapter.read(final_epic_id)

                    if epic is None:
                        return {
                            "status": "error",
                            "error": f"Epic {final_epic_id} not found",
                            **_build_adapter_metadata(adapter, final_epic_id),
                        }

                    return {
                        "status": "completed",
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "epic": epic.model_dump(),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to get epic: {str(e)}",
                    }

            elif action_lower == "list":
                # Inline implementation of epic_list
                try:
                    # Validate project context (Required for list operations)
                    resolver = ConfigResolver(project_path=Path.cwd())
                    config = resolver.load_project_config()
                    final_project = project_id or (
                        config.default_project if config else None
                    )

                    if not final_project:
                        return {
                            "status": "error",
                            "error": "project_id required. Provide project_id parameter or configure default_project.",
                            "help": "Use config_set_default_project(project_id='YOUR-PROJECT') to set default project",
                            "check_config": "Use config_get() to view current configuration",
                        }

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
                        filters = {
                            "ticket_type": TicketType.EPIC,
                            "project": final_project,
                        }
                        if state is not None:
                            filters["state"] = state
                        epics = await adapter.list(
                            limit=limit, offset=offset, filters=filters
                        )

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

            elif action_lower == "update":
                # Inline implementation of epic_update
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for update operation",
                    }
                try:
                    final_epic_id = entity_id or epic_id or ""

                    # Check if adapter supports epic updates
                    if not hasattr(adapter, "update_epic"):
                        adapter_name = adapter.adapter_display_name
                        return {
                            "status": "error",
                            "error": f"Epic updates not supported by {adapter_name} adapter",
                            "epic_id": final_epic_id,
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
                    updated = await adapter.update_epic(final_epic_id, updates)

                    if updated is None:
                        return {
                            "status": "error",
                            "error": f"Epic {final_epic_id} not found or update failed",
                        }

                    return {
                        "status": "completed",
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "epic": updated.model_dump(),
                    }
                except AttributeError as e:
                    return {
                        "status": "error",
                        "error": f"Epic update method not available: {str(e)}",
                        "epic_id": final_epic_id,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to update epic: {str(e)}",
                        "epic_id": final_epic_id,
                    }

            elif action_lower == "delete":
                # Inline implementation of epic_delete
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for delete operation",
                    }
                try:
                    final_epic_id = entity_id or epic_id or ""

                    # Check if adapter supports epic deletion
                    if not hasattr(adapter, "delete_epic"):
                        adapter_name = adapter.adapter_display_name
                        return {
                            "status": "error",
                            "error": f"Epic deletion not supported by {adapter_name} adapter",
                            **_build_adapter_metadata(adapter, final_epic_id),
                            "supported_adapters": ["GitHub", "Asana"],
                            "note": f"{adapter_name} does not provide API support for deleting epics/projects",
                        }

                    # Call adapter's delete_epic method
                    success = await adapter.delete_epic(final_epic_id)

                    if not success:
                        return {
                            "status": "error",
                            "error": f"Failed to delete epic {final_epic_id}",
                            **_build_adapter_metadata(adapter, final_epic_id),
                        }

                    return {
                        "status": "completed",
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "message": f"Epic {final_epic_id} deleted successfully",
                        "deleted": True,
                    }
                except AttributeError:
                    adapter_name = adapter.adapter_display_name
                    return {
                        "status": "error",
                        "error": f"Epic deletion not supported by {adapter_name} adapter",
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "supported_adapters": ["GitHub", "Asana"],
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to delete epic: {str(e)}",
                        **_build_adapter_metadata(adapter, final_epic_id),
                    }

            elif action_lower == "get_children":
                # Inline implementation of epic_issues
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get_children operation",
                    }
                try:
                    final_epic_id = entity_id or epic_id or ""

                    # Read the epic to get child issue IDs
                    epic = await adapter.read(final_epic_id)
                    if epic is None:
                        return {
                            "status": "error",
                            "error": f"Epic {final_epic_id} not found",
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
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "issues": issues,
                        "count": len(issues),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to get epic issues: {str(e)}",
                    }

            elif action_lower == "get_tree":
                # Inline implementation of hierarchy_tree
                if not entity_id and not epic_id:
                    return {
                        "status": "error",
                        "error": "entity_id or epic_id required for get_tree operation",
                    }
                try:
                    final_epic_id = entity_id or epic_id or ""

                    # Read the epic
                    epic = await adapter.read(final_epic_id)
                    if epic is None:
                        return {
                            "status": "error",
                            "error": f"Epic {final_epic_id} not found",
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
                        **_build_adapter_metadata(adapter, final_epic_id),
                        "tree": tree,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to build hierarchy tree: {str(e)}",
                    }
            else:
                valid_actions = [
                    "create",
                    "get",
                    "list",
                    "update",
                    "delete",
                    "get_children",
                    "get_tree",
                    "add_relation",
                    "remove_relation",
                    "list_relations",
                ]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'epic'",
                    "valid_actions": valid_actions,
                    "hint": f"Use ticket_hierarchy(entity_type='epic', action=<one of {valid_actions}>, ...)",
                }

        elif entity_type_lower == "issue":
            if action_lower == "create":
                # Inline implementation of issue_create
                try:
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

                    # Handle epic_id with sentinel for explicit None
                    effective_epic_id = _UNSET if epic_id is None else epic_id

                    if effective_epic_id is not _UNSET:
                        # Priority 1: Explicit value provided (including None for opt-out)
                        final_epic_id = effective_epic_id
                    elif config.default_project or config.default_epic:
                        # Priority 2: Use configured default
                        final_epic_id = config.default_project or config.default_epic

                    # Auto-detect labels if enabled
                    final_tags = tags
                    if auto_detect_labels:
                        final_tags = await detect_and_apply_labels(
                            adapter,
                            title or "",
                            description or "",
                            tags,
                            max_auto_labels,
                        )

                    # Create issue (Task with ISSUE type)
                    issue = Task(
                        title=title or "",
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

            elif action_lower == "get_parent":
                # Inline implementation of issue_get_parent
                if not entity_id and not issue_id:
                    return {
                        "status": "error",
                        "error": "entity_id or issue_id required for get_parent operation",
                    }
                try:
                    final_issue_id = entity_id or issue_id or ""

                    # Read the issue to check if it has a parent
                    issue = await adapter.read(final_issue_id)
                    if issue is None:
                        return {
                            "status": "error",
                            "error": f"Issue {final_issue_id} not found",
                        }

                    # Check for parent_issue attribute (sub-issues have this set)
                    parent_issue_id = getattr(issue, "parent_issue", None)

                    if not parent_issue_id:
                        # No parent - this is a top-level issue
                        return {
                            "status": "completed",
                            **_build_adapter_metadata(adapter, final_issue_id),
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
                        **_build_adapter_metadata(adapter, final_issue_id),
                        "parent": parent_issue.model_dump(),
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to get parent issue: {str(e)}",
                    }

            elif action_lower == "get_children":
                # Inline implementation of issue_tasks
                if not entity_id and not issue_id:
                    return {
                        "status": "error",
                        "error": "entity_id or issue_id required for get_children operation",
                    }
                try:
                    final_issue_id = entity_id or issue_id or ""

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
                    issue = await adapter.read(final_issue_id)
                    if issue is None:
                        return {
                            "status": "error",
                            "error": f"Issue {final_issue_id} not found",
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
                                    should_include = should_include and (
                                        task_state == state_enum
                                    )

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
                        **_build_adapter_metadata(adapter, final_issue_id),
                        "tasks": tasks,
                        "count": len(tasks),
                        "filters_applied": filters_applied,
                    }
                except Exception as e:
                    return {
                        "status": "error",
                        "error": f"Failed to get issue tasks: {str(e)}",
                    }
            else:
                valid_actions = [
                    "create",
                    "get_parent",
                    "get_children",
                    "add_relation",
                    "remove_relation",
                    "list_relations",
                ]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'issue'",
                    "valid_actions": valid_actions,
                    "hint": f"Use ticket_hierarchy(entity_type='issue', action=<one of {valid_actions}>, ...)",
                }

        elif entity_type_lower == "task":
            if action_lower == "create":
                # Inline implementation of task_create
                try:
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
                            adapter,
                            title or "",
                            description or "",
                            tags,
                            max_auto_labels,
                        )

                    # Create task (Task with TASK type)
                    task = Task(
                        title=title or "",
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
            else:
                valid_actions = [
                    "create",
                    "add_relation",
                    "remove_relation",
                    "list_relations",
                ]
                return {
                    "status": "error",
                    "error": f"Invalid action '{action}' for entity_type 'task'",
                    "valid_actions": valid_actions,
                    "hint": "Use ticket_hierarchy(entity_type='task', action='create', ...) or relationship actions",
                    "note": "Tasks support create and relationship operations. Use ticket() tool for read/update/delete.",
                }

        else:
            valid_types = ["epic", "issue", "task"]
            return {
                "status": "error",
                "error": f"Invalid entity_type: {entity_type}",
                "valid_entity_types": valid_types,
                "hint": f"Use ticket_hierarchy(entity_type=<one of {valid_types}>, action=..., ...)",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Hierarchy operation failed: {str(e)}",
            "entity_type": entity_type,
            "action": action,
        }
