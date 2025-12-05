"""GitHub-specific type definitions and conversion utilities.

This module contains:
- State and priority mappings between GitHub and universal models
- Type conversion helper functions
- GitHub-specific constants and enums
- TypedDict definitions for GitHub API responses
"""

from __future__ import annotations

from typing import Any, TypedDict

from ...core.models import Priority, TicketState


class GitHubStateMapping:
    """GitHub issue states and label-based extended states.

    Design Decision: GitHub's two-state model (open/closed)

    GitHub natively only supports two states: 'open' and 'closed'.
    To support richer workflow states, we use labels to extend the state model.

    Rationale:
    - Maintains compatibility with GitHub's API limitations
    - Allows flexible workflow states through labeling
    - Enables state transitions without closing issues

    Trade-offs:
    - State changes require label management (more API calls)
    - Labels are user-visible and can be manually modified
    - No built-in state transition validation in GitHub

    Extension Point: Custom state labels can be configured per repository
    through adapter configuration.
    """

    # GitHub native states
    OPEN = "open"
    CLOSED = "closed"

    # Extended states via labels
    # These labels represent workflow states beyond GitHub's native open/closed
    STATE_LABELS = {
        TicketState.IN_PROGRESS: "in-progress",
        TicketState.READY: "ready",
        TicketState.TESTED: "tested",
        TicketState.WAITING: "waiting",
        TicketState.BLOCKED: "blocked",
    }

    # Priority labels mapping
    # Multiple label patterns support different team conventions
    PRIORITY_LABELS = {
        Priority.CRITICAL: ["P0", "critical", "urgent"],
        Priority.HIGH: ["P1", "high"],
        Priority.MEDIUM: ["P2", "medium"],
        Priority.LOW: ["P3", "low"],
    }


def get_universal_state(
    github_state: str,
    labels: list[str],
) -> TicketState:
    """Convert GitHub state + labels to universal TicketState.

    GitHub has only two states (open/closed), so we use labels to infer
    the extended workflow state.

    Args:
    ----
        github_state: GitHub issue state ('open' or 'closed')
        labels: List of label names attached to the issue

    Returns:
    -------
        Universal ticket state enum value

    Performance:
    -----------
        Time Complexity: O(n*m) where n=number of labels, m=state labels to check
        Worst case: ~5 state labels * ~20 issue labels = 100 comparisons

    Example:
    -------
        >>> get_universal_state("open", ["in-progress", "bug"])
        TicketState.IN_PROGRESS
        >>> get_universal_state("closed", [])
        TicketState.CLOSED
    """
    # Closed issues are always CLOSED state
    if github_state == "closed":
        return TicketState.CLOSED

    # Normalize labels for comparison
    label_names = [label.lower() for label in labels]

    # Check for extended state labels
    for state, label_name in GitHubStateMapping.STATE_LABELS.items():
        if label_name.lower() in label_names:
            return state

    # Default to OPEN if no state label found
    return TicketState.OPEN


def extract_state_from_issue(issue: dict[str, Any]) -> TicketState:
    """Extract ticket state from GitHub issue data.

    Handles multiple GitHub API response formats:
    - REST API v3: labels as array of objects
    - GraphQL API v4: labels.nodes as array
    - Legacy formats: labels as array of strings

    Args:
    ----
        issue: GitHub issue data from REST or GraphQL API

    Returns:
    -------
        Universal ticket state

    Example:
    -------
        >>> issue = {"state": "open", "labels": [{"name": "ready"}]}
        >>> extract_state_from_issue(issue)
        TicketState.READY
    """
    # Extract labels from various formats
    labels = []
    if "labels" in issue:
        if isinstance(issue["labels"], list):
            # REST API format: array of objects or strings
            labels = [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in issue["labels"]
            ]
        elif isinstance(issue["labels"], dict) and "nodes" in issue["labels"]:
            # GraphQL format: labels.nodes array
            labels = [label["name"] for label in issue["labels"]["nodes"]]

    return get_universal_state(issue["state"], labels)


def get_priority_from_labels(
    labels: list[str],
    custom_priority_scheme: dict[str, list[str]] | None = None,
) -> Priority:
    """Extract priority from GitHub issue labels.

    Priority is inferred from labels since GitHub has no native priority field.
    Supports custom priority label schemes for team-specific conventions.

    Args:
    ----
        labels: List of label names
        custom_priority_scheme: Optional custom mapping of priority -> label patterns

    Returns:
    -------
        Priority enum value (defaults to MEDIUM if not found)

    Performance:
    -----------
        Time Complexity: O(n*m) where n=labels, m=priority patterns
        Expected: ~20 labels * ~12 priority patterns = 240 comparisons worst case

    Example:
    -------
        >>> get_priority_from_labels(["P0", "bug"])
        Priority.CRITICAL
        >>> get_priority_from_labels(["enhancement"])
        Priority.MEDIUM  # default
    """
    label_names = [label.lower() for label in labels]

    # Check custom priority scheme first
    if custom_priority_scheme:
        for priority_str, label_patterns in custom_priority_scheme.items():
            for pattern in label_patterns:
                if any(pattern.lower() in label for label in label_names):
                    return Priority(priority_str)

    # Check default priority labels
    for priority, priority_labels in GitHubStateMapping.PRIORITY_LABELS.items():
        for priority_label in priority_labels:
            if priority_label.lower() in label_names:
                return priority

    return Priority.MEDIUM


def get_priority_label(
    priority: Priority,
    custom_priority_scheme: dict[str, list[str]] | None = None,
) -> str:
    """Get label name for a priority level.

    Returns the first matching label from custom scheme or default labels.
    Falls back to P0/P1/P2/P3 notation if no match found.

    Args:
    ----
        priority: Universal priority enum
        custom_priority_scheme: Optional custom priority label mapping

    Returns:
    -------
        Label name to apply to issue

    Example:
    -------
        >>> get_priority_label(Priority.CRITICAL)
        'P0'
        >>> get_priority_label(Priority.HIGH, {"high": ["urgent", "high-priority"]})
        'urgent'
    """
    # Check custom scheme first
    if custom_priority_scheme:
        labels = custom_priority_scheme.get(priority.value, [])
        if labels:
            return labels[0]

    # Use default labels
    labels = GitHubStateMapping.PRIORITY_LABELS.get(priority, [])
    if labels:
        return labels[0]

    # Fallback to P0-P3 notation
    priority_index = list(Priority).index(priority)
    return f"P{priority_index}"


def get_state_label(state: TicketState) -> str | None:
    """Get the label name for extended workflow states.

    Args:
    ----
        state: Universal ticket state

    Returns:
    -------
        Label name if state requires a label, None for native GitHub states

    Example:
    -------
        >>> get_state_label(TicketState.IN_PROGRESS)
        'in-progress'
        >>> get_state_label(TicketState.OPEN)
        None  # Native GitHub state, no label needed
    """
    return GitHubStateMapping.STATE_LABELS.get(state)


def get_github_state(state: TicketState) -> str:
    """Map universal state to GitHub native state.

    Only two valid values: 'open' or 'closed'.
    Extended states map to 'open' with additional labels.

    Args:
    ----
        state: Universal ticket state

    Returns:
    -------
        GitHub state string ('open' or 'closed')

    Example:
    -------
        >>> get_github_state(TicketState.IN_PROGRESS)
        'open'
        >>> get_github_state(TicketState.CLOSED)
        'closed'
    """
    if state in (TicketState.DONE, TicketState.CLOSED):
        return GitHubStateMapping.CLOSED
    return GitHubStateMapping.OPEN


# =============================================================================
# GitHub Projects V2 Type Definitions
# =============================================================================


class ProjectV2Owner(TypedDict, total=False):
    """GitHub ProjectV2 owner (Organization or User).

    Attributes:
        __typename: Type discriminator ("Organization" or "User")
        login: Owner login name
        id: Owner node ID
    """

    __typename: str
    login: str
    id: str


class ProjectV2PageInfo(TypedDict, total=False):
    """GraphQL pagination info for ProjectV2 queries.

    Attributes:
        hasNextPage: Whether more results exist
        endCursor: Cursor for next page
    """

    hasNextPage: bool
    endCursor: str | None


class ProjectV2ItemsConnection(TypedDict, total=False):
    """ProjectV2 items connection.

    Attributes:
        totalCount: Total number of items in project
    """

    totalCount: int


class ProjectV2Node(TypedDict, total=False):
    """GitHub ProjectV2 GraphQL node.

    Represents a single GitHub Projects V2 project from the GraphQL API.
    This type matches the structure returned by PROJECT_V2_FRAGMENT.

    Design Decision: Total vs Required Fields
    -----------------------------------------
    Using total=False allows optional fields to be omitted, matching the
    GraphQL API where many fields are nullable or may not be queried.

    Required fields (id, number, title) are still enforced at the Pydantic
    model level in map_github_projectv2_to_project().

    Attributes:
        id: GitHub node ID (e.g., "PVT_kwDOABcdefgh")
        number: Project number (e.g., 5)
        title: Project title
        shortDescription: Brief description (max 256 chars)
        readme: Markdown readme content
        public: Whether project is publicly visible
        closed: Whether project is closed
        url: Direct URL to project
        createdAt: ISO timestamp of creation
        updatedAt: ISO timestamp of last update
        closedAt: ISO timestamp of closure (if closed)
        owner: Owner (Organization or User)
        items: Items connection with totalCount
    """

    id: str
    number: int
    title: str
    shortDescription: str | None
    readme: str | None
    public: bool
    closed: bool
    url: str
    createdAt: str
    updatedAt: str
    closedAt: str | None
    owner: ProjectV2Owner
    items: ProjectV2ItemsConnection | None


class ProjectV2Response(TypedDict, total=False):
    """Response from GET_PROJECT_QUERY or GET_PROJECT_BY_ID_QUERY.

    Single project query response wrapping the project node.

    Attributes:
        organization: Organization containing projectV2 field
        node: Direct node lookup result
    """

    organization: dict[str, ProjectV2Node | None]
    node: ProjectV2Node | None


class ProjectV2Connection(TypedDict, total=False):
    """Connection of ProjectV2 nodes with pagination.

    Attributes:
        totalCount: Total number of projects
        pageInfo: Pagination information
        nodes: List of project nodes
    """

    totalCount: int
    pageInfo: ProjectV2PageInfo
    nodes: list[ProjectV2Node]


class ProjectListResponse(TypedDict, total=False):
    """Response from LIST_PROJECTS_QUERY.

    Attributes:
        organization: Organization containing projectsV2 connection
    """

    organization: dict[str, ProjectV2Connection]


class ProjectItemContent(TypedDict, total=False):
    """Content of a project item (Issue, PR, or DraftIssue).

    Attributes:
        __typename: Content type discriminator
        id: Content node ID
        number: Issue/PR number (not present for DraftIssue)
        title: Content title
        state: Content state (OPEN/CLOSED for issues, etc.)
        labels: Labels connection (issues only)
    """

    __typename: str
    id: str
    number: int | None
    title: str
    state: str | None
    labels: dict[str, list[dict[str, str]]] | None


class ProjectItemNode(TypedDict, total=False):
    """Single project item node.

    Attributes:
        id: Project item ID (not the same as content ID)
        content: The actual content (Issue, PR, or DraftIssue)
    """

    id: str
    content: ProjectItemContent


class ProjectItemsConnection(TypedDict, total=False):
    """Connection of project items with pagination.

    Attributes:
        totalCount: Total items in project
        pageInfo: Pagination info
        nodes: List of project item nodes
    """

    totalCount: int
    pageInfo: ProjectV2PageInfo
    nodes: list[ProjectItemNode]


class ProjectItemsResponse(TypedDict, total=False):
    """Response from PROJECT_ITEMS_QUERY.

    Attributes:
        node: ProjectV2 node containing items connection
    """

    node: dict[str, ProjectItemsConnection]
