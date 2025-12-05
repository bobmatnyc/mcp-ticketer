"""JQL query builders and query utilities for Jira adapter."""

from __future__ import annotations

from typing import Any

from ...core.models import SearchQuery
from .types import map_priority_to_jira


def build_list_jql(
    project_key: str,
    filters: dict[str, Any] | None = None,
    state_mapper: callable | None = None,
) -> str:
    """Build JQL query for listing issues.

    Args:
    ----
        project_key: JIRA project key
        filters: Optional filters dictionary with keys:
            - state: TicketState value
            - priority: Priority value
            - assignee: User identifier
            - ticket_type: Issue type name
        state_mapper: Function to map TicketState to JIRA status string

    Returns:
    -------
        JQL query string

    """
    jql_parts = []

    if project_key:
        jql_parts.append(f"project = {project_key}")

    if filters:
        if "state" in filters and state_mapper:
            status = state_mapper(filters["state"])
            jql_parts.append(f'status = "{status}"')
        if "priority" in filters:
            priority = map_priority_to_jira(filters["priority"])
            jql_parts.append(f'priority = "{priority}"')
        if "assignee" in filters:
            jql_parts.append(f'assignee = "{filters["assignee"]}"')
        if "ticket_type" in filters:
            jql_parts.append(f'issuetype = "{filters["ticket_type"]}"')

    return " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"


def build_search_jql(
    project_key: str,
    query: SearchQuery,
    state_mapper: callable | None = None,
) -> str:
    """Build JQL query for searching issues.

    Args:
    ----
        project_key: JIRA project key
        query: SearchQuery object with search parameters
        state_mapper: Function to map TicketState to JIRA status string

    Returns:
    -------
        JQL query string

    """
    jql_parts = []

    if project_key:
        jql_parts.append(f"project = {project_key}")

    # Text search
    if query.query:
        jql_parts.append(f'text ~ "{query.query}"')

    # State filter
    if query.state and state_mapper:
        status = state_mapper(query.state)
        jql_parts.append(f'status = "{status}"')

    # Priority filter
    if query.priority:
        priority = map_priority_to_jira(query.priority)
        jql_parts.append(f'priority = "{priority}"')

    # Assignee filter
    if query.assignee:
        jql_parts.append(f'assignee = "{query.assignee}"')

    # Tags/labels filter
    if query.tags:
        label_conditions = [f'labels = "{tag}"' for tag in query.tags]
        jql_parts.append(f"({' OR '.join(label_conditions)})")

    return " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"


def build_epic_list_jql(
    project_key: str,
    state: str | None = None,
) -> str:
    """Build JQL query for listing epics.

    Args:
    ----
        project_key: JIRA project key
        state: Optional status name to filter by

    Returns:
    -------
        JQL query string

    """
    jql_parts = [f"project = {project_key}", 'issuetype = "Epic"']

    # Add state filter if provided
    if state:
        jql_parts.append(f'status = "{state}"')

    return " AND ".join(jql_parts) + " ORDER BY updated DESC"


def build_labels_list_jql(
    project_key: str,
    max_results: int = 100,
) -> str:
    """Build JQL query for listing labels from recent issues.

    Args:
    ----
        project_key: JIRA project key
        max_results: Maximum number of issues to sample

    Returns:
    -------
        JQL query string

    """
    return f"project = {project_key} ORDER BY updated DESC"


def build_project_labels_jql(
    project_key: str,
    max_results: int = 500,
) -> str:
    """Build JQL query for listing all project labels.

    Args:
    ----
        project_key: JIRA project key
        max_results: Maximum number of issues to sample

    Returns:
    -------
        JQL query string

    """
    return f"project = {project_key} ORDER BY updated DESC"


def get_search_params(
    jql: str,
    start_at: int = 0,
    max_results: int = 50,
    fields: str = "*all",
    expand: str = "renderedFields",
) -> dict[str, Any]:
    """Get standard search query parameters.

    Args:
    ----
        jql: JQL query string
        start_at: Pagination offset
        max_results: Maximum number of results
        fields: Fields to include in response
        expand: Additional data to expand

    Returns:
    -------
        Dictionary of query parameters

    """
    return {
        "jql": jql,
        "startAt": start_at,
        "maxResults": max_results,
        "fields": fields,
        "expand": expand,
    }


def get_labels_search_params(
    jql: str,
    max_results: int = 100,
) -> dict[str, Any]:
    """Get search parameters for label listing.

    Args:
    ----
        jql: JQL query string
        max_results: Maximum number of results

    Returns:
    -------
        Dictionary of query parameters

    """
    return {
        "jql": jql,
        "maxResults": max_results,
        "fields": "labels",
    }
