"""Project update management tools for status updates with health indicators.

This module implements MCP tools for creating, listing, and retrieving project
status updates with health indicators. Supports Linear (native), GitHub V2,
Asana, and JIRA (via workaround).

Related to ticket 1M-238: Add project updates support with flexible project
identification.
"""

import logging
from typing import Any

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


@mcp.tool()
async def project_update_create(
    project_id: str,
    body: str,
    health: str | None = None,
) -> dict[str, Any]:
    """Create a project status update.

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


@mcp.tool()
async def project_update_list(
    project_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List project updates for a project.

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


@mcp.tool()
async def project_update_get(
    update_id: str,
) -> dict[str, Any]:
    """Get a specific project update by ID.

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
