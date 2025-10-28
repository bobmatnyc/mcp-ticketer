"""Search and query tools for finding tickets.

This module implements advanced search capabilities for tickets using
various filters and criteria.
"""

from typing import Any

from ....core.models import Priority, SearchQuery, TicketState
from ..server_sdk import get_adapter, mcp


@mcp.tool()
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search tickets using advanced filters.

    Searches for tickets matching the specified criteria. All filters are
    optional and can be combined.

    Args:
        query: Text search query to match against title and description
        state: Filter by state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        priority: Filter by priority - must be one of: low, medium, high, critical
        tags: Filter by tags - tickets must have all specified tags
        assignee: Filter by assigned user ID or email
        limit: Maximum number of results to return (default: 10, max: 100)

    Returns:
        List of tickets matching search criteria, or error information

    """
    try:
        adapter = get_adapter()

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

        # Create search query
        search_query = SearchQuery(
            query=query,
            state=state_enum,
            priority=priority_enum,
            tags=tags,
            assignee=assignee,
            limit=min(limit, 100),  # Enforce max limit
        )

        # Execute search via adapter
        results = await adapter.search(search_query)

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
            },
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to search tickets: {str(e)}",
        }


@mcp.tool()
async def ticket_search_hierarchy(
    query: str,
    include_children: bool = True,
    max_depth: int = 3,
) -> dict[str, Any]:
    """Search tickets and include their hierarchy.

    Performs a text search and returns matching tickets along with their
    hierarchical context (parent epics/issues and child issues/tasks).

    Args:
        query: Text search query to match against title and description
        include_children: Whether to include child tickets in results
        max_depth: Maximum hierarchy depth to include (1-3, default: 3)

    Returns:
        List of tickets with hierarchy information, or error information

    """
    try:
        adapter = get_adapter()

        # Validate max_depth
        if max_depth < 1 or max_depth > 3:
            return {
                "status": "error",
                "error": "max_depth must be between 1 and 3",
            }

        # Create search query
        search_query = SearchQuery(
            query=query,
            limit=50,  # Reasonable limit for hierarchical search
        )

        # Execute search via adapter
        results = await adapter.search(search_query)

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
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to search with hierarchy: {str(e)}",
        }
