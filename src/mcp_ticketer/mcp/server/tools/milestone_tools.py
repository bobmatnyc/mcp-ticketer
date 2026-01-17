"""Unified milestone management tools (v2.0.0).

This module implements milestone management through a single unified `milestone()` interface.

Version 2.0.0 changes:
- Single `milestone()` function is the exposed MCP tool
- All operations accessible via milestone(action="create"|"get"|"list"|"update"|"delete"|"get_issues")
- Follows the pattern from ticket() and hierarchy() unified tools
"""

import logging
from datetime import datetime
from typing import Any, Literal

from ....core.adapter import BaseAdapter
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)

# Sentinel value to distinguish between "parameter not provided" and "explicitly None"
_UNSET = object()


def _build_adapter_metadata(
    adapter: BaseAdapter,
    milestone_id: str | None = None,
) -> dict[str, Any]:
    """Build adapter metadata for MCP responses.

    Args:
        adapter: The adapter that handled the operation
        milestone_id: Optional milestone ID to include in metadata

    Returns:
        Dictionary with adapter metadata fields

    """
    metadata = {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }

    if milestone_id:
        metadata["milestone_id"] = milestone_id

    return metadata


@mcp.tool(
    description="Manage milestones and sprints - create, read, update, list milestones; track progress and completion; organize work into time-boxed iterations"
)
async def milestone(
    action: Literal["create", "get", "list", "update", "delete", "get_issues"],
    # Entity identification
    milestone_id: str | None = None,
    # Creation/Update parameters
    name: str | None = None,
    target_date: str | None = None,
    labels: list[str] | None = None,
    description: str = "",
    state: str | None = None,
    # List/filter parameters
    project_id: str | None = None,
) -> dict[str, Any]:
    """Unified milestone management tool for cross-platform milestone support.

    A milestone is a list of labels with target dates, into which issues can be grouped.

    Consolidates all milestone operations into a single interface with progress tracking.

    Args:
        action: Operation to perform:
            - "create": Create new milestone
            - "get": Get milestone by ID with progress
            - "list": List milestones (optionally filtered)
            - "update": Update milestone properties
            - "delete": Delete milestone
            - "get_issues": Get issues in milestone
        milestone_id: Milestone ID (required for get, update, delete, get_issues)
        name: Milestone name (required for create)
        target_date: Target completion date (ISO format: YYYY-MM-DD)
        labels: Labels that define this milestone (user's definition)
        description: Milestone description
        state: Milestone state (open, active, completed, closed)
        project_id: Project/repository filter for list operations

    Returns:
        Operation results with status, data, and metadata

    Raises:
        ValueError: If action is invalid or required parameters missing

    Examples:
        # Create milestone
        await milestone(
            action="create",
            name="v2.1.0 Release",
            target_date="2025-12-31",
            labels=["v2.1", "release"]
        )

        # Get milestone with progress
        await milestone(action="get", milestone_id="milestone-123")

        # List active milestones
        await milestone(action="list", state="active")

        # Update milestone
        await milestone(
            action="update",
            milestone_id="milestone-123",
            state="completed"
        )

        # Get issues in milestone
        await milestone(action="get_issues", milestone_id="milestone-123")

        # Delete milestone
        await milestone(action="delete", milestone_id="milestone-123")

    """
    try:
        # Get adapter from registry
        adapter = get_adapter()

        # Validate action
        valid_actions = ["create", "get", "list", "update", "delete", "get_issues"]
        if action not in valid_actions:
            return {
                "status": "error",
                "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            }

        # Route to appropriate handler
        if action == "create":
            return await _handle_create(
                adapter, name, target_date, labels, description, project_id
            )
        elif action == "get":
            return await _handle_get(adapter, milestone_id)
        elif action == "list":
            return await _handle_list(adapter, project_id, state)
        elif action == "update":
            return await _handle_update(
                adapter, milestone_id, name, target_date, state, labels, description
            )
        elif action == "delete":
            return await _handle_delete(adapter, milestone_id)
        elif action == "get_issues":
            return await _handle_get_issues(adapter, milestone_id, state)

    except Exception as e:
        logger.exception("Milestone operation failed")
        return {
            "status": "error",
            "error": f"Milestone operation failed: {str(e)}",
            "action": action,
            "milestone_id": milestone_id,
        }


async def _handle_create(
    adapter: BaseAdapter,
    name: str | None,
    target_date: str | None,
    labels: list[str] | None,
    description: str,
    project_id: str | None,
) -> dict[str, Any]:
    """Handle milestone creation."""
    if not name:
        return {
            "status": "error",
            "error": "name is required for create action",
        }

    # Parse target_date if provided (expect date object, not string)
    parsed_date = None
    if target_date:
        try:
            # Try parsing as ISO date string
            parsed_date = datetime.fromisoformat(target_date)
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid date format '{target_date}'. Use ISO format: YYYY-MM-DD",
            }

    milestone_obj = await adapter.milestone_create(
        name=name,
        target_date=parsed_date,
        labels=labels or [],
        description=description,
        project_id=project_id,
    )

    return {
        "status": "completed",
        "message": f"Milestone '{name}' created successfully",
        "milestone": milestone_obj.model_dump(),
        "metadata": _build_adapter_metadata(adapter, milestone_obj.id),
    }


async def _handle_get(adapter: BaseAdapter, milestone_id: str | None) -> dict[str, Any]:
    """Handle milestone retrieval with progress calculation."""
    if not milestone_id:
        return {
            "status": "error",
            "error": "milestone_id is required for get action",
        }

    milestone_obj = await adapter.milestone_get(milestone_id)

    if not milestone_obj:
        return {
            "status": "error",
            "error": f"Milestone '{milestone_id}' not found",
        }

    return {
        "status": "completed",
        "milestone": milestone_obj.model_dump(),
        "metadata": _build_adapter_metadata(adapter, milestone_id),
    }


async def _handle_list(
    adapter: BaseAdapter,
    project_id: str | None,
    state: str | None,
) -> dict[str, Any]:
    """Handle milestone listing with optional filters."""
    milestones = await adapter.milestone_list(project_id=project_id, state=state)

    return {
        "status": "completed",
        "message": f"Found {len(milestones)} milestone(s)",
        "milestones": [m.model_dump() for m in milestones],
        "count": len(milestones),
        "metadata": _build_adapter_metadata(adapter),
    }


async def _handle_update(
    adapter: BaseAdapter,
    milestone_id: str | None,
    name: str | None,
    target_date: str | None,
    state: str | None,
    labels: list[str] | None,
    description: str | None,
) -> dict[str, Any]:
    """Handle milestone update."""
    if not milestone_id:
        return {
            "status": "error",
            "error": "milestone_id is required for update action",
        }

    # Parse target_date if provided
    parsed_date = None
    if target_date:
        try:
            parsed_date = datetime.fromisoformat(target_date)
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid date format '{target_date}'. Use ISO format: YYYY-MM-DD",
            }

    milestone_obj = await adapter.milestone_update(
        milestone_id=milestone_id,
        name=name,
        target_date=parsed_date,
        state=state,
        labels=labels,
        description=description,
    )

    if not milestone_obj:
        return {
            "status": "error",
            "error": f"Failed to update milestone '{milestone_id}'",
        }

    return {
        "status": "completed",
        "message": f"Milestone '{milestone_id}' updated successfully",
        "milestone": milestone_obj.model_dump(),
        "metadata": _build_adapter_metadata(adapter, milestone_id),
    }


async def _handle_delete(
    adapter: BaseAdapter, milestone_id: str | None
) -> dict[str, Any]:
    """Handle milestone deletion."""
    if not milestone_id:
        return {
            "status": "error",
            "error": "milestone_id is required for delete action",
        }

    success = await adapter.milestone_delete(milestone_id)

    if success:
        return {
            "status": "completed",
            "message": f"Milestone '{milestone_id}' deleted successfully",
            "metadata": _build_adapter_metadata(adapter, milestone_id),
        }
    else:
        return {
            "status": "error",
            "error": f"Failed to delete milestone '{milestone_id}'",
        }


async def _handle_get_issues(
    adapter: BaseAdapter,
    milestone_id: str | None,
    state: str | None,
) -> dict[str, Any]:
    """Handle getting issues in milestone."""
    if not milestone_id:
        return {
            "status": "error",
            "error": "milestone_id is required for get_issues action",
        }

    issues = await adapter.milestone_get_issues(milestone_id, state=state)

    return {
        "status": "completed",
        "message": f"Found {len(issues)} issue(s) in milestone",
        "issues": [issue.model_dump() for issue in issues],
        "count": len(issues),
        "metadata": _build_adapter_metadata(adapter, milestone_id),
    }
