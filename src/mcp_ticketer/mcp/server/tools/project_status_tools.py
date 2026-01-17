"""MCP tools for project status analysis and work planning.

.. deprecated::
    Use project(action="status", ...) instead from project_tools module.
    This module will be removed in v3.0.0.

This module provides PM-focused tools to analyze project health and
generate intelligent work plans with recommendations.

Tools:
- project_status: Comprehensive project/epic analysis with health assessment
  DEPRECATED: Use project(action="status", ...) instead

Migration:
    project_status(project_id="123") → project(action="status", project_id="123")
"""

import logging
import warnings
from typing import Any

from ....analysis.project_status import StatusAnalyzer
from ....core.project_config import ConfigResolver
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    description="Manage GitHub project status fields - create, update, delete custom status field options for project boards and workflows"
)
async def project_status(project_id: str | None = None) -> dict[str, Any]:
    """Analyze project/epic status and generate work plan with recommendations.

    .. deprecated::
        Use project(action="status", ...) instead.
        This tool will be removed in v3.0.0.

    Provides comprehensive project analysis including:
    - Health assessment (on_track, at_risk, off_track)
    - Status breakdown by state and priority
    - Dependency analysis and critical path
    - Top 3 recommended tickets to start next
    - Blocker identification
    - Work distribution by assignee
    - Actionable recommendations for project managers

    Args:
        project_id: ID of the project/epic to analyze (optional, uses default_project if not provided)

    Returns:
        Complete project status analysis with recommendations, or error information

    Example:
        # Analyze specific project
        result = await project_status(project_id="eac28953c267")

        # Analyze default project
        result = await project_status()

    Example Response:
        {
            "status": "success",
            "project_id": "eac28953c267",
            "project_name": "MCP Ticketer",
            "health": "at_risk",
            "summary": {
                "total": 4,
                "open": 3,
                "in_progress": 1,
                "done": 0
            },
            "recommended_next": [
                {
                    "ticket_id": "1M-317",
                    "title": "Fix project organization",
                    "priority": "critical",
                    "reason": "Critical priority, Unblocks 2 tickets",
                    "blocks": ["1M-315", "1M-316"]
                }
            ],
            "recommendations": [
                "Resolve 1M-317 first (critical) - Unblocks 2 tickets",
                "1 critical priority ticket needs attention"
            ]
        }

    """
    warnings.warn(
        "project_status is deprecated. Use project(action='status', ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
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
