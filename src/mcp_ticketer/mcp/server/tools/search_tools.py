"""Search and query tools for finding tickets.

This module implements advanced search capabilities for tickets using
various filters and criteria.
"""

import logging
from typing import Any

from ....core.models import Priority, SearchQuery, TicketState
from ....utils.time_utils import parse_time_filter
from ..server_sdk import get_adapter, mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    description="Search and filter tickets - query by text, state, priority, tags, assignee, project, milestone; support time-based filters and hierarchy traversal"
)
async def ticket_search(
    query: str | None = None,
    state: str | None = None,
    priority: str | None = None,
    tags: list[str] | None = None,
    assignee: str | None = None,
    project_id: str | None = None,
    milestone_id: str | None = None,
    updated_after: str | None = None,
    updated_before: str | None = None,
    since: str | None = None,
    include_activity: bool = False,
    include_comments: bool = False,
    activity_limit: int = 5,
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
    - updated_after: Filter tickets updated after this time (ISO datetime or relative like "24h", "7d")
    - updated_before: Filter tickets updated before this time (ISO datetime, optional)
    - since: Alias for updated_after (relative time shorthand)

    **Activity Options:**
    - include_activity: Include activity/comments per ticket (default: False)
    - include_comments: Include comment previews (default: False)
    - activity_limit: Max activity items per ticket (default: 5)

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
        updated_after: ISO datetime or relative time (e.g., "24h", "7d", "2w", "1m")
        updated_before: ISO datetime (optional upper bound)
        since: Alias for updated_after (relative time shorthand)
        include_activity: Include activity/comments for each ticket
        include_comments: Include comment previews in results
        activity_limit: Maximum number of activity items per ticket
        limit: Maximum number of results to return (default: 10, max: 100)
        include_hierarchy: Include parent/child relationships (default: False)
        include_children: Include child tickets in hierarchy (default: True)
        max_depth: Maximum hierarchy depth to traverse (default: 3)

    Returns:
        List of tickets matching search criteria, or error information

    Examples:
        # Simple search (backward compatible)
        await ticket_search(query="authentication bug", state="open", limit=5)

        # Search with time filter (last 24 hours)
        await ticket_search(updated_after="24h", state="open")

        # Search with time filter (since last week)
        await ticket_search(since="7d", project_id="proj-123")

        # Search with activity included
        await ticket_search(
            query="critical bug",
            include_activity=True,
            activity_limit=10
        )

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

        # Parse time filter (supports both ISO datetime and relative time like "24h", "7d")
        parsed_time_filter = None
        query_period = None
        try:
            parsed_time_filter = parse_time_filter(
                updated_after=updated_after, since=since
            )
            if parsed_time_filter:
                # Format query period for response
                time_source = updated_after or since
                query_period = time_source
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Invalid time filter: {str(e)}",
            }

        # Create search query with project scoping
        search_query = SearchQuery(
            query=query,
            state=state_enum,
            priority=priority_enum,
            tags=tags,
            assignee=assignee,
            project=final_project,  # Always required for search operations
            updated_after=parsed_time_filter,
            limit=min(limit, 100),  # Enforce max limit
        )

        # Execute search via adapter
        results = await adapter.search(search_query)

        # Build activity/comments map if requested
        ticket_activities = {}
        ticket_comments = {}
        if include_activity or include_comments:
            for ticket in results:
                try:
                    # Get comments using adapter's get_comments method
                    if hasattr(adapter, "get_comments"):
                        comments = await adapter.get_comments(
                            ticket.id, limit=activity_limit, offset=0
                        )
                        # Store activity data separately
                        if include_activity:
                            ticket_activities[ticket.id] = [
                                comment.model_dump() for comment in comments
                            ]
                        if include_comments:
                            # Store just the text preview for comments
                            ticket_comments[ticket.id] = [
                                {
                                    "author": comment.author,
                                    "text": comment.text[:200]
                                    + ("..." if len(comment.text) > 200 else ""),
                                    "created_at": (
                                        comment.created_at.isoformat()
                                        if comment.created_at
                                        else None
                                    ),
                                }
                                for comment in comments
                            ]
                except Exception as e:
                    # Log error but don't fail the search
                    logger.warning(
                        f"Failed to fetch comments for ticket {ticket.id}: {e}"
                    )

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
                ticket_dict = ticket.model_dump()
                # Add activity if requested
                if include_activity and ticket.id in ticket_activities:
                    ticket_dict["activity"] = ticket_activities[ticket.id]
                # Add comment previews if requested
                if include_comments and ticket.id in ticket_comments:
                    ticket_dict["comment_preview"] = ticket_comments[ticket.id]

                ticket_data = {
                    "ticket": ticket_dict,
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

            hierarchical_response = {
                "status": "completed",
                "results": hierarchical_results,
                "count": len(hierarchical_results),
                "query": query,
                "max_depth": max_depth,
            }

            # Add query_period if time filter was used
            if query_period:
                hierarchical_response["query_period"] = query_period

            return hierarchical_response

        # Standard search response - build ticket dicts with optional activity/comments
        ticket_dicts = []
        for ticket in results:
            ticket_dict = ticket.model_dump()
            # Add activity if requested
            if include_activity and ticket.id in ticket_activities:
                ticket_dict["activity"] = ticket_activities[ticket.id]
            # Add comment previews if requested
            if include_comments and ticket.id in ticket_comments:
                ticket_dict["comment_preview"] = ticket_comments[ticket.id]
            ticket_dicts.append(ticket_dict)

        response = {
            "status": "completed",
            "tickets": ticket_dicts,
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

        # Add query_period if time filter was used
        if query_period:
            response["query_period"] = query_period

        return response
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to search tickets: {str(e)}",
        }
