"""Unified project management tools for status analysis and updates.

This module consolidates project_status and project_update into a single
unified interface with action-based routing.

v2.1.0 Consolidation (Phase 3 Sprint 3.5):
- Single `project()` tool with action-based routing
- Combines project status analysis with project update management
- Replaces 2 separate tools (project_status, project_update) with unified interface
- ~800 tokens saved (50% reduction)

Tools:
    project(action): Unified interface for all project operations
        - status: Analyze project health and generate work plan (was project_status)
        - create_update: Create project status update (was project_update action=create)
        - get_update: Get specific update by ID (was project_update action=get)
        - list_updates: List updates for project (was project_update action=list)

Response Format:
    {
        "status": "success" | "error",
        ... action-specific data ...
    }

Related Tickets:
- 1M-316: Project status analysis and work planning
- 1M-238: Add project updates support with flexible project identification
- 1M-487: Phase 3 Sprint 3.4 - Consolidate project_update tools (v2.0.0)
- TBD: Phase 3 Sprint 3.5 - Consolidate project_status and project_update (v2.1.0)
"""

import logging
from typing import Any, Literal

from ....analysis.project_status import StatusAnalyzer
from ....core.adapter import BaseAdapter
from ....core.models import ProjectUpdateHealth
from ....core.project_config import ConfigResolver
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


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


async def _handle_project_status(project_id: str | None = None) -> dict[str, Any]:
    """Analyze project/epic status and generate work plan with recommendations.

    This is the implementation of the "status" action from the unified project tool.

    Args:
        project_id: ID of the project/epic to analyze (optional, uses default_project if not provided)

    Returns:
        Complete project status analysis with recommendations, or error information

    """
    try:
        adapter = get_adapter()

        # Use default project if not provided
        if not project_id:
            resolver = ConfigResolver()
            config = resolver.resolve()
            project_id = config.default_project

            if not project_id:
                return {
                    "status": "error",
                    "error": "No project_id provided and no default_project configured",
                    "message": "Use config_set_project to set a default project, or provide project_id parameter",
                }

        # Read the epic/project to get name
        try:
            epic = await adapter.read(project_id)
            if epic is None:
                return {
                    "status": "error",
                    "error": f"Project/Epic {project_id} not found",
                }
            project_name = epic.title or project_id
        except Exception as e:
            logger.warning(
                f"Failed to read project {project_id} for name: {e}. Using ID as name."
            )
            project_name = project_id

        # Get all child issues
        child_issue_ids = getattr(epic, "child_issues", [])

        if not child_issue_ids:
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name,
                "health": "on_track",
                "summary": {"total": 0},
                "message": "Project has no tickets yet",
                "recommended_next": [],
                "recommendations": ["Project is empty - Create tickets to get started"],
            }

        # Fetch each child issue
        tickets = []
        for issue_id in child_issue_ids:
            try:
                issue = await adapter.read(issue_id)
                if issue:
                    tickets.append(issue)
            except Exception as e:
                logger.warning(f"Failed to read issue {issue_id}: {e}")
                continue

        if not tickets:
            return {
                "status": "success",
                "project_id": project_id,
                "project_name": project_name,
                "health": "at_risk",
                "summary": {"total": 0},
                "message": f"Could not load tickets for project (found {len(child_issue_ids)} IDs but couldn't read them)",
                "recommended_next": [],
                "recommendations": ["Check ticket IDs and permissions"],
            }

        # Perform status analysis
        analyzer = StatusAnalyzer()
        result = analyzer.analyze(project_id, project_name, tickets)

        # Convert to dict and add success status
        result_dict = result.model_dump()
        result_dict["status"] = "success"

        return result_dict

    except Exception as e:
        logger.error(f"Error analyzing project status: {e}", exc_info=True)
        return {
            "status": "error",
            "error": f"Failed to analyze project status: {str(e)}",
        }


async def _handle_create_update(
    project_id: str,
    body: str,
    health: str | None = None,
) -> dict[str, Any]:
    """Create a project status update.

    This is the implementation of the "create_update" action from the unified project tool.

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

    """
    try:
        # Validate body is not empty
        if not body or not body.strip():
            return {
                "status": "error",
                "error": "Update body cannot be empty",
            }

        # Parse health status if provided
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


async def _handle_get_update(update_id: str) -> dict[str, Any]:
    """Get a specific project update by ID.

    This is the implementation of the "get_update" action from the unified project tool.

    Args:
        update_id: Project update identifier (UUID or platform-specific ID)

    Returns:
        ProjectUpdate details as JSON with adapter metadata, or error information

    """
    try:
        # Validate update_id is not empty
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


async def _handle_list_updates(
    project_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List project updates for a project.

    This is the implementation of the "list_updates" action from the unified project tool.

    Args:
        project_id: Project identifier (UUID, slugId, or URL)
        limit: Maximum number of updates to return (default: 10, max: 50)

    Returns:
        List of ProjectUpdate objects as JSON with adapter metadata, or error information

    """
    try:
        # Validate limit
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


# ============================================================================
# Unified Project Tool
# ============================================================================


@mcp.tool(
    description="Manage projects - create, read, update, delete, list projects; organize tickets into project workspaces and teams"
)
async def project(
    action: Literal["status", "create_update", "get_update", "list_updates"],
    project_id: str | None = None,
    update_id: str | None = None,
    body: str | None = None,
    health: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Unified project management for status analysis and updates.

    Consolidates project status analysis and project update management into a
    single interface with action-based routing.

    Actions:
        - status: Analyze project health and generate work plan (was project_status)
        - create_update: Create project status update (was project_update action=create)
        - get_update: Get specific update by ID (was project_update action=get)
        - list_updates: List updates for project (was project_update action=list)

    Args:
        action: Operation to perform. Valid values:
            - "status": Analyze project health and generate work plan
            - "create_update": Create new project status update
            - "get_update": Get specific update by ID
            - "list_updates": List updates for a project

        # Parameters for "status" action
        project_id: Project/epic ID to analyze (optional, uses default_project if not provided)

        # Parameters for "create_update" action (required: project_id, body)
        project_id: Project identifier (UUID, slugId, or URL)
        body: Update content in Markdown format
        health: Optional health status - must be one of:
            - on_track: Project is progressing as planned
            - at_risk: Project has some issues but recoverable
            - off_track: Project is significantly behind or blocked
            - complete: Project is finished (GitHub-specific)
            - inactive: Project is not actively being worked on (GitHub-specific)

        # Parameters for "get_update" action (required: update_id)
        update_id: Project update identifier (UUID or platform-specific ID)

        # Parameters for "list_updates" action (required: project_id)
        # project_id: Project identifier
        limit: Maximum number of updates to return (default: 10, max: 50)

    Returns:
        Results specific to action with status and relevant data

    Examples:
        # Analyze project status
        project(action="status", project_id="eac28953c267")

        # Analyze default project
        project(action="status")

        # Create update
        project(action="create_update", project_id="PROJ-123",
                body="Sprint completed with 15/20 stories done",
                health="at_risk")

        # Get update
        project(action="get_update", update_id="update-456")

        # List updates
        project(action="list_updates", project_id="PROJ-123", limit=5)

    Migration from deprecated tools:
        - project_status(project_id=...) → project(action="status", project_id=...)
        - project_update(action="create", ...) → project(action="create_update", ...)
        - project_update(action="get", ...) → project(action="get_update", ...)
        - project_update(action="list", ...) → project(action="list_updates", ...)

    Note:
        Related to tickets:
        - 1M-316: Project status analysis and work planning
        - 1M-238: Add project updates support with flexible project identification
        - 1M-487: Phase 3 Sprint 3.4 - Consolidate project_update tools
        - TBD: Phase 3 Sprint 3.5 - Consolidate project_status and project_update

    """
    # Validate action
    valid_actions = ["status", "create_update", "get_update", "list_updates"]
    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Valid actions: {', '.join(valid_actions)}",
        }

    # Route to appropriate handler based on action
    if action == "status":
        return await _handle_project_status(project_id=project_id)

    elif action == "create_update":
        # Validate required parameters for create_update
        if not project_id:
            return {
                "status": "error",
                "error": "Parameter 'project_id' is required for action='create_update'",
            }
        if not body:
            return {
                "status": "error",
                "error": "Parameter 'body' is required for action='create_update'",
            }
        return await _handle_create_update(
            project_id=project_id,
            body=body,
            health=health,
        )

    elif action == "get_update":
        # Validate required parameters for get_update
        if not update_id:
            return {
                "status": "error",
                "error": "Parameter 'update_id' is required for action='get_update'",
            }
        return await _handle_get_update(update_id=update_id)

    elif action == "list_updates":
        # Validate required parameters for list_updates
        if not project_id:
            return {
                "status": "error",
                "error": "Parameter 'project_id' is required for action='list_updates'",
            }
        return await _handle_list_updates(
            project_id=project_id,
            limit=limit,
        )

    # Should never reach here due to action validation above
    return {
        "status": "error",
        "error": f"Unhandled action: {action}",
    }
