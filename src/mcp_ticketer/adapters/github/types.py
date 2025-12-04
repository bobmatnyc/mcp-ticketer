"""GitHub-specific type definitions and conversion utilities.

This module contains:
- State and priority mappings between GitHub and universal models
- Type conversion helper functions
- GitHub-specific constants and enums
"""

from __future__ import annotations

from typing import Any

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
