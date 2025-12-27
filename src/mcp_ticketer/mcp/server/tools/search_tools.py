"""Search and query tools for finding tickets.

This module implements advanced search capabilities for tickets using
various filters and criteria.
"""

import logging
from typing import Any

from ....core.models import Priority, SearchQuery, TicketState
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    project_id: str | None = None,
    milestone_id: str | None = None,
    limit: int = 10,
    include_hierarchy: bool = False,
    include_children: bool = True,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Search tickets with optional hierarchy information and milestone filtering.

    **Consolidates:**
    - ticket_search() → Default behavior (include_hierarchy=False)
    - ticket_search_hierarchy() → Set include_hierarchy=True

    ⚠️ Project Filtering Required:
    This tool requires project_id parameter OR default_project configuration.
    To set default project: config_set_default_project(project_id="YOUR-PROJECT")
    To check current config: config_get()

    Exception: Single ticket operations (ticket_read) don't require project filtering.

    **Search Filters:**
    - query: Text search in title and description
    - state: Filter by workflow state
    - priority: Filter by priority level
    - tags: Filter by tags (AND logic)
    - assignee: Filter by assigned user
    - project_id: Scope to specific project
    - milestone_id: Filter by milestone (NEW in 1M-607)

    **Hierarchy Options:**
    - include_hierarchy: Include parent/child relationships (default: False)
    - include_children: Include child tickets (default: True, requires include_hierarchy=True)
    - max_depth: Maximum hierarchy depth (default: 3, requires include_hierarchy=True)

    Args:
        query: Text search query to match against title and description
        state: Filter by state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        priority: Filter by priority - must be one of: low, medium, high, critical
        tags: Filter by tags - tickets must have all specified tags
        assignee: Filter by assigned user ID or email
        project_id: Project/epic ID (required unless default_project configured)
        milestone_id: Filter by milestone ID (NEW in 1M-607)
        limit: Maximum number of results to return (default: 10, max: 100)
        include_hierarchy: Include parent/child relationships (default: False)
        include_children: Include child tickets in hierarchy (default: True)
        max_depth: Maximum hierarchy depth to traverse (default: 3)

    Returns:
        List of tickets matching search criteria, or error information

    Examples:
        # Simple search (backward compatible)
        await ticket_search(query="authentication bug", state="open", limit=5)

        # Search with hierarchy
        await ticket_search(
            query="oauth implementation",
            project_id="proj-123",
            include_hierarchy=True,
            max_depth=2
        )

        # Search within milestone
        await ticket_search(
            milestone_id="milestone-123",
            state="open",
            limit=20
        )

    """
    try:
        # Validate project context (NEW: Required for search operations)
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

        # Add warning for unscoped searches
        if not query and not (state or priority or tags or assignee):
            logging.warning(
                "Unscoped search with no query or filters. "
                "This will search ALL tickets across all projects. "
                "Tip: Configure default_project or default_team for automatic scoping."
            )

        # Validate and build search query
        state_enum = None
        if state is not None:
            try:
                state_enum = TicketState(state.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid state '{state}'. Must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked",
                }

        priority_enum = None
        if priority is not None:
            try:
                priority_enum = Priority(priority.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
                }

        # Create search query with project scoping
        search_query = SearchQuery(
            query=query,
            state=state_enum,
            priority=priority_enum,
            tags=tags,
            assignee=assignee,
            project=final_project,  # Always required for search operations
            limit=min(limit, 100),  # Enforce max limit
        )

        # Execute search via adapter
        results = await adapter.search(search_query)

        # Filter by milestone if requested (NEW in 1M-607)
        if milestone_id:
            try:
                # Get issues in milestone
                milestone_issues = await adapter.milestone_get_issues(
                    milestone_id, state=state
                )
                milestone_issue_ids = {issue.id for issue in milestone_issues}

                # Filter search results to only include milestone issues
                results = [
                    ticket for ticket in results if ticket.id in milestone_issue_ids
                ]
            except Exception as e:
                logger.warning(f"Failed to filter by milestone {milestone_id}: {e}")
                # Continue with unfiltered results if milestone filtering fails

        # Add hierarchy if requested
        if include_hierarchy:
            # Validate max_depth
            if max_depth < 1 or max_depth > 3:
                return {
                    "status": "error",
                    "error": "max_depth must be between 1 and 3",
                }

            # Build hierarchical results
            hierarchical_results = []
            for ticket in results:
                ticket_data = {
                    "ticket": ticket.model_dump(),
                    "hierarchy": {},
                }

                # Get parent epic if applicable
                parent_epic_id = getattr(ticket, "parent_epic", None)
                if parent_epic_id and max_depth >= 2:
                    try:
                        parent_epic = await adapter.read(parent_epic_id)
                        if parent_epic:
                            ticket_data["hierarchy"][
                                "parent_epic"
                            ] = parent_epic.model_dump()
                    except Exception:
                        pass  # Parent not found, continue

                # Get parent issue if applicable (for tasks)
                parent_issue_id = getattr(ticket, "parent_issue", None)
                if parent_issue_id and max_depth >= 2:
                    try:
                        parent_issue = await adapter.read(parent_issue_id)
                        if parent_issue:
                            ticket_data["hierarchy"][
                                "parent_issue"
                            ] = parent_issue.model_dump()
                    except Exception:
                        pass  # Parent not found, continue

                # Get children if requested
                if include_children and max_depth >= 2:
                    children = []

                    # Get child issues (for epics)
                    child_issue_ids = getattr(ticket, "child_issues", [])
                    for child_id in child_issue_ids:
                        try:
                            child = await adapter.read(child_id)
                            if child:
                                children.append(child.model_dump())
                        except Exception:
                            pass  # Child not found, continue

                    # Get child tasks (for issues)
                    child_task_ids = getattr(ticket, "children", [])
                    for child_id in child_task_ids:
                        try:
                            child = await adapter.read(child_id)
                            if child:
                                children.append(child.model_dump())
                        except Exception:
                            pass  # Child not found, continue

                    if children:
                        ticket_data["hierarchy"]["children"] = children

                hierarchical_results.append(ticket_data)

            return {
                "status": "completed",
                "results": hierarchical_results,
                "count": len(hierarchical_results),
                "query": query,
                "max_depth": max_depth,
            }

        # Standard search response
        return {
            "status": "completed",
            "tickets": [ticket.model_dump() for ticket in results],
            "count": len(results),
            "query": {
                "text": query,
                "state": state,
                "priority": priority,
                "tags": tags,
                "assignee": assignee,
                "project": final_project,
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to search tickets: {str(e)}",
        }
