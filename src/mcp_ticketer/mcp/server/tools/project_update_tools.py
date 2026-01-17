"""Project update management tools for status updates with health indicators.

.. deprecated::
    Use project(action="create_update"|"get_update"|"list_updates", ...) instead from project_tools module.
    This module will be removed in v3.0.0.

This module provides a unified interface for creating, listing, and retrieving project
status updates with health indicators across multiple platforms.

v2.0.0 Consolidation (Phase 3 Sprint 3.4):
- Single `project_update()` tool with action-based routing
- Replaces 4 separate tools (create, get, list) with unified interface
- Helper functions retained for internal use with deprecation warnings
- ~1,100 tokens saved (69% reduction)

v2.1.0 Consolidation (Phase 3 Sprint 3.5):
- Merged into unified `project()` tool in project_tools module
- project_update(action="create") → project(action="create_update")
- project_update(action="get") → project(action="get_update")
- project_update(action="list") → project(action="list_updates")
- This module kept for backward compatibility with deprecation warnings

Platform Support:
- Linear: Native ProjectUpdate entities with health, diff_markdown, staleness
- GitHub V2: ProjectV2StatusUpdate with status options
- Asana: Project Status Updates with color-coded health
- JIRA: Comments with custom formatting (workaround)

Primary Tool:
- project_update(action): Unified interface for all operations
  - action="create": Create project status update
  - action="get": Get specific update by ID
  - action="list": List updates for a project

Internal Helpers (deprecated):
- project_update_create(): Use project_update(action="create") instead
- project_update_get(): Use project_update(action="get") instead
- project_update_list(): Use project_update(action="list") instead

Response Format:
    {
        "status": "completed" | "error",
        "adapter": "adapter_type",
        "adapter_name": "Adapter Display Name",
        ... action-specific data ...
    }

Related Tickets:
- 1M-238: Add project updates support with flexible project identification
- 1M-487: Phase 3 Sprint 3.4 - Consolidate project_update tools (v2.0.0)
"""

import logging
import warnings
from typing import Any, Literal

from ....core.adapter import BaseAdapter
from ....core.models import ProjectUpdateHealth
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


def _build_adapter_metadata(
    adapter: BaseAdapter,
    project_id: str | None = None,
) -> dict[str, Any]:
    """Build adapter metadata for MCP responses.

    Args:
        adapter: The adapter that handled the operation
        project_id: Optional project ID to include in metadata

    Returns:
        Dictionary with adapter metadata fields

    """
    metadata = {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }

    if project_id:
        metadata["project_id"] = project_id

    return metadata


@mcp.tool(
    description="Update GitHub project items - add tickets to projects, update field values, modify project board item properties"
)
async def project_update(
    action: Literal["create", "get", "list"],
    project_id: str | None = None,
    update_id: str | None = None,
    body: str | None = None,
    health: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Unified project update management with action-based routing.

    .. deprecated::
        Use project(action="create_update"|"get_update"|"list_updates", ...) instead.
        This tool will be removed in v3.0.0.

    This tool consolidates all project update operations into a single interface:
    - create: Create new project status update
    - get: Get specific update by ID
    - list: List updates for a project

    Args:
        action: Operation to perform. Valid values:
            - "create": Create new project status update
            - "get": Get specific update by ID
            - "list": List updates for a project

        # Parameters for "create" action (required: project_id, body)
        project_id: Project identifier (UUID, slugId, or URL)
        body: Update content in Markdown format
        health: Optional health status - must be one of:
            - on_track: Project is progressing as planned
            - at_risk: Project has some issues but recoverable
            - off_track: Project is significantly behind or blocked
            - complete: Project is finished (GitHub-specific)
            - inactive: Project is not actively being worked on (GitHub-specific)

        # Parameters for "get" action (required: update_id)
        update_id: Project update identifier (UUID or platform-specific ID)

        # Parameters for "list" action (required: project_id)
        # project_id: Project identifier
        limit: Maximum number of updates to return (default: 10, max: 50)

    Returns:
        Results specific to action with status and relevant data

    Examples:
        # Create update
        project_update(action="create", project_id="PROJ-123",
                      body="Sprint completed with 15/20 stories done",
                      health="at_risk")

        # Get update
        project_update(action="get", update_id="update-456")

        # List updates
        project_update(action="list", project_id="PROJ-123", limit=5)

    Note:
        Related to ticket 1M-238: Add project updates support with flexible
        project identification.
        Related to ticket 1M-484: Phase 2 Sprint 1.1 - Consolidate project_update tools.

    Migration:
        project_update(action="create", ...) → project(action="create_update", ...)
        project_update(action="get", ...) → project(action="get_update", ...)
        project_update(action="list", ...) → project(action="list_updates", ...)

    """
    warnings.warn(
        "project_update is deprecated. Use project(action='create_update'|'get_update'|'list_updates', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Validate action
    valid_actions = ["create", "get", "list"]
    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}",
        }

    # Route to appropriate handler based on action
    if action == "create":
        # Validate required parameters for create
        if not project_id:
            return {
                "status": "error",
                "error": "Parameter 'project_id' is required for action='create'",
            }
        if not body:
            return {
                "status": "error",
                "error": "Parameter 'body' is required for action='create'",
            }
        return await project_update_create(
            project_id=project_id,
            body=body,
            health=health,
        )

    elif action == "get":
        # Validate required parameters for get
        if not update_id:
            return {
                "status": "error",
                "error": "Parameter 'update_id' is required for action='get'",
            }
        return await project_update_get(update_id=update_id)

    elif action == "list":
        # Validate required parameters for list
        if not project_id:
            return {
                "status": "error",
                "error": "Parameter 'project_id' is required for action='list'",
            }
        return await project_update_list(
            project_id=project_id,
            limit=limit,
        )

    # Should never reach here due to action validation above
    return {
        "status": "error",
        "error": f"Unhandled action: {action}",
    }


async def project_update_create(
    project_id: str,
    body: str,
    health: str | None = None,
) -> dict[str, Any]:
    """Create a project status update.

    .. deprecated::
        Use project_update(action="create", ...) instead.
        This tool will be removed in a future version.

    Creates a status update for a project with optional health indicator.
    Supports Linear (native), GitHub V2, Asana, and JIRA (via workaround).

    Platform Support:
    - Linear: Native ProjectUpdate entity with health, diff_markdown, staleness
    - GitHub V2: ProjectV2StatusUpdate with status options
    - Asana: Project Status Updates with color-coded health
    - JIRA: Comments with custom formatting (workaround)

    Args:
        project_id: Project identifier (UUID, slugId, or URL)
        body: Update content in Markdown format (required)
        health: Optional health status - must be one of:
            - on_track: Project is progressing as planned
            - at_risk: Project has some issues but recoverable
            - off_track: Project is significantly behind or blocked
            - complete: Project is finished (GitHub-specific)
            - inactive: Project is not actively being worked on (GitHub-specific)

    Returns:
        Created ProjectUpdate details as JSON with adapter metadata, or error information

    Example:
        >>> result = await project_update_create(
        ...     project_id="PROJ-123",
        ...     body="Sprint completed with 15/20 stories done",
        ...     health="at_risk"
        ... )
    Example: See Returns section

    Note:
        Related to ticket 1M-238: Add project updates support with flexible
        project identification.

    """
    warnings.warn(
        "project_update_create is deprecated. Use project_update(action='create', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate body is not empty (before calling get_adapter)
        if not body or not body.strip():
            return {
                "status": "error",
                "error": "Update body cannot be empty",
            }

        # Parse health status if provided (before calling get_adapter)
        health_enum = None
        if health:
            try:
                health_enum = ProjectUpdateHealth(health.lower())
            except ValueError:
                valid_values = [h.value for h in ProjectUpdateHealth]
                return {
                    "status": "error",
                    "error": f"Invalid health status '{health}'. Valid values: {', '.join(valid_values)}",
                }

        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "create_project_update"):
            return {
                "status": "error",
                "error": f"Adapter '{adapter.adapter_type}' does not support project updates",
                **_build_adapter_metadata(adapter, project_id),
            }

        # Create project update
        update = await adapter.create_project_update(
            project_id=project_id,
            body=body.strip(),
            health=health_enum,
        )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, project_id),
            "update": update.model_dump(),
        }

    except ValueError as e:
        # Adapter-specific validation errors
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Failed to create project update: {e}")
        return {
            "status": "error",
            "error": f"Failed to create project update: {str(e)}",
        }


async def project_update_list(
    project_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List project updates for a project.

    .. deprecated::
        Use project_update(action="list", ...) instead.
        This tool will be removed in a future version.

    Retrieves status updates for a specific project with pagination support.
    Returns updates in reverse chronological order (newest first).

    Platform Support:
    - Linear: Lists ProjectUpdate entities via project.projectUpdates
    - GitHub V2: Lists ProjectV2StatusUpdate via project status updates
    - Asana: Lists Project Status Updates
    - JIRA: Returns formatted comments (workaround)

    Args:
        project_id: Project identifier (UUID, slugId, or URL)
        limit: Maximum number of updates to return (default: 10, max: 50)

    Returns:
        List of ProjectUpdate objects as JSON with adapter metadata, or error information

    Example:
        >>> result = await project_update_list(
        ...     project_id="PROJ-123",
        ...     limit=5
        ... )
    Example: See Returns section

    Note:
        Related to ticket 1M-238: Add project updates support with flexible
        project identification.

    """
    warnings.warn(
        "project_update_list is deprecated. Use project_update(action='list', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate limit (before calling get_adapter)
        if limit < 1 or limit > 50:
            return {
                "status": "error",
                "error": "Limit must be between 1 and 50",
            }

        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "list_project_updates"):
            return {
                "status": "error",
                "error": f"Adapter '{adapter.adapter_type}' does not support project updates",
                **_build_adapter_metadata(adapter, project_id),
            }

        # List project updates
        updates = await adapter.list_project_updates(
            project_id=project_id,
            limit=limit,
        )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, project_id),
            "count": len(updates),
            "updates": [update.model_dump() for update in updates],
        }

    except ValueError as e:
        # Adapter-specific validation errors (e.g., project not found)
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Failed to list project updates: {e}")
        return {
            "status": "error",
            "error": f"Failed to list project updates: {str(e)}",
        }


async def project_update_get(
    update_id: str,
) -> dict[str, Any]:
    """Get a specific project update by ID.

    .. deprecated::
        Use project_update(action="get", ...) instead.
        This tool will be removed in a future version.

    Retrieves detailed information about a single project status update.

    Platform Support:
    - Linear: Fetches ProjectUpdate entity by ID
    - GitHub V2: Fetches ProjectV2StatusUpdate by node ID
    - Asana: Fetches Project Status Update by GID
    - JIRA: Returns formatted comment (workaround)

    Args:
        update_id: Project update identifier (UUID or platform-specific ID)

    Returns:
        ProjectUpdate details as JSON with adapter metadata, or error information

    Example:
        >>> result = await project_update_get(
        ...     update_id="update-456"
        ... )
    Example: See Returns section

    Note:
        Related to ticket 1M-238: Add project updates support with flexible
        project identification.

    """
    warnings.warn(
        "project_update_get is deprecated. Use project_update(action='get', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate update_id is not empty (before calling get_adapter)
        if not update_id or not update_id.strip():
            return {
                "status": "error",
                "error": "Update ID cannot be empty",
            }

        adapter = get_adapter()

        # Check if adapter supports project updates
        if not hasattr(adapter, "get_project_update"):
            return {
                "status": "error",
                "error": f"Adapter '{adapter.adapter_type}' does not support project updates",
                **_build_adapter_metadata(adapter),
            }

        # Get project update
        update = await adapter.get_project_update(update_id=update_id.strip())

        if update is None:
            return {
                "status": "error",
                "error": f"Project update '{update_id}' not found",
                **_build_adapter_metadata(adapter),
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "update": update.model_dump(),
        }

    except ValueError as e:
        # Adapter-specific validation errors
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Failed to get project update: {e}")
        return {
            "status": "error",
            "error": f"Failed to get project update: {str(e)}",
        }
