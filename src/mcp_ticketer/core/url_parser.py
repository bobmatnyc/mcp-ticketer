"""URL parsing utilities for extracting project/issue IDs from adapter URLs.

This module provides functionality to detect and parse URLs from various ticket
management platforms (Linear, JIRA, GitHub) and extract the relevant project or
issue identifiers.

Supported URL patterns:
- Linear: https://linear.app/team-key/project/project-key-123
- Linear: https://linear.app/team-key/issue/ISS-123
- JIRA: https://company.atlassian.net/browse/PROJ
- JIRA: https://company.atlassian.net/browse/PROJ-123
- GitHub: https://github.com/owner/repo/projects/1
- GitHub: https://github.com/owner/repo/issues/123
"""

import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class URLParserError(Exception):
    """Raised when URL parsing fails."""

    pass


def is_url(value: str) -> bool:
    """Detect if a string is a URL.

    Args:
        value: String to check

    Returns:
        True if the string appears to be a URL, False otherwise

    Examples:
        >>> is_url("https://linear.app/team/project/abc-123")
        True
        >>> is_url("PROJ-123")
        False
        >>> is_url("http://example.com")
        True
    """
    if not value or not isinstance(value, str):
        return False

    # Check for URL scheme
    return bool(
        value.startswith(("http://", "https://"))
        or re.match(r"^[\w.-]+://", value)
    )


def extract_linear_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract project or issue ID from Linear URL.

    Supported formats:
    - https://linear.app/workspace/project/project-slug-abc123/overview → "project-slug-abc123"
    - https://linear.app/workspace/issue/ISS-123 → "ISS-123"
    - https://linear.app/workspace/team/TEAM → "TEAM" (team key)

    Args:
        url: Linear URL string

    Returns:
        Tuple of (extracted_id, error_message). If successful, error_message is None.

    Examples:
        >>> extract_linear_id("https://linear.app/travel-bta/project/crm-system-f59a41/overview")
        ('crm-system-f59a41', None)
        >>> extract_linear_id("https://linear.app/myteam/issue/BTA-123")
        ('BTA-123', None)
    """
    if not url:
        return None, "Empty URL provided"

    # Pattern 1: Project URLs - extract slug-id
    # https://linear.app/workspace/project/project-slug-shortid/...
    project_pattern = r"https?://linear\.app/[\w-]+/project/([\w-]+)"
    match = re.search(project_pattern, url, re.IGNORECASE)
    if match:
        project_id = match.group(1)
        logger.debug(f"Extracted Linear project ID '{project_id}' from URL")
        return project_id, None

    # Pattern 2: Issue URLs - extract issue key
    # https://linear.app/workspace/issue/ISS-123
    issue_pattern = r"https?://linear\.app/[\w-]+/issue/([\w]+-\d+)"
    match = re.search(issue_pattern, url, re.IGNORECASE)
    if match:
        issue_id = match.group(1)
        logger.debug(f"Extracted Linear issue ID '{issue_id}' from URL")
        return issue_id, None

    # Pattern 3: Team URLs - extract team key
    # https://linear.app/workspace/team/TEAM
    team_pattern = r"https?://linear\.app/[\w-]+/team/([\w-]+)"
    match = re.search(team_pattern, url, re.IGNORECASE)
    if match:
        team_key = match.group(1)
        logger.debug(f"Extracted Linear team key '{team_key}' from URL")
        return team_key, None

    return None, f"Could not extract Linear ID from URL: {url}"


def extract_jira_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract project or issue key from JIRA URL.

    Supported formats:
    - https://company.atlassian.net/browse/PROJ → "PROJ"
    - https://company.atlassian.net/browse/PROJ-123 → "PROJ-123"
    - https://jira.company.com/browse/PROJ → "PROJ"

    Args:
        url: JIRA URL string

    Returns:
        Tuple of (extracted_id, error_message). If successful, error_message is None.

    Examples:
        >>> extract_jira_id("https://company.atlassian.net/browse/PROJ")
        ('PROJ', None)
        >>> extract_jira_id("https://company.atlassian.net/browse/PROJ-123")
        ('PROJ-123', None)
    """
    if not url:
        return None, "Empty URL provided"

    # Pattern: Extract key from browse URL
    # https://company.atlassian.net/browse/PROJ or PROJ-123
    browse_pattern = r"https?://[\w.-]+/browse/([\w]+-?\d*)"
    match = re.search(browse_pattern, url, re.IGNORECASE)
    if match:
        issue_key = match.group(1)
        logger.debug(f"Extracted JIRA key '{issue_key}' from URL")
        return issue_key, None

    # Alternative pattern for project URLs
    # https://company.atlassian.net/projects/PROJ
    project_pattern = r"https?://[\w.-]+/projects/([\w]+)"
    match = re.search(project_pattern, url, re.IGNORECASE)
    if match:
        project_key = match.group(1)
        logger.debug(f"Extracted JIRA project key '{project_key}' from URL")
        return project_key, None

    return None, f"Could not extract JIRA key from URL: {url}"


def extract_github_id(url: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract project or issue number from GitHub URL.

    Supported formats:
    - https://github.com/owner/repo/projects/1 → "1"
    - https://github.com/owner/repo/issues/123 → "123"
    - https://github.com/owner/repo/pull/456 → "456"

    Args:
        url: GitHub URL string

    Returns:
        Tuple of (extracted_id, error_message). If successful, error_message is None.

    Examples:
        >>> extract_github_id("https://github.com/owner/repo/projects/1")
        ('1', None)
        >>> extract_github_id("https://github.com/owner/repo/issues/123")
        ('123', None)
    """
    if not url:
        return None, "Empty URL provided"

    # Pattern 1: Project URLs - extract project number
    # https://github.com/owner/repo/projects/1
    project_pattern = r"https?://github\.com/[\w-]+/[\w-]+/projects/(\d+)"
    match = re.search(project_pattern, url, re.IGNORECASE)
    if match:
        project_id = match.group(1)
        logger.debug(f"Extracted GitHub project ID '{project_id}' from URL")
        return project_id, None

    # Pattern 2: Issue URLs - extract issue number
    # https://github.com/owner/repo/issues/123
    issue_pattern = r"https?://github\.com/[\w-]+/[\w-]+/issues/(\d+)"
    match = re.search(issue_pattern, url, re.IGNORECASE)
    if match:
        issue_id = match.group(1)
        logger.debug(f"Extracted GitHub issue ID '{issue_id}' from URL")
        return issue_id, None

    # Pattern 3: Pull request URLs - extract PR number
    # https://github.com/owner/repo/pull/456
    pr_pattern = r"https?://github\.com/[\w-]+/[\w-]+/pull/(\d+)"
    match = re.search(pr_pattern, url, re.IGNORECASE)
    if match:
        pr_id = match.group(1)
        logger.debug(f"Extracted GitHub PR ID '{pr_id}' from URL")
        return pr_id, None

    return None, f"Could not extract GitHub ID from URL: {url}"


def extract_id_from_url(url: str, adapter_type: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """Extract project/issue ID from URL for any supported adapter.

    This is the main entry point for URL parsing. It auto-detects the adapter type
    from the URL if not explicitly provided.

    Args:
        url: URL string to parse
        adapter_type: Optional adapter type hint ("linear", "jira", "github").
                     If not provided, adapter is auto-detected from URL domain.

    Returns:
        Tuple of (extracted_id, error_message). If successful, error_message is None.

    Raises:
        URLParserError: If URL parsing fails

    Examples:
        >>> extract_id_from_url("https://linear.app/team/project/abc-123")
        ('abc-123', None)
        >>> extract_id_from_url("https://company.atlassian.net/browse/PROJ-123")
        ('PROJ-123', None)
        >>> extract_id_from_url("https://github.com/owner/repo/issues/123")
        ('123', None)
    """
    if not url:
        return None, "Empty URL provided"

    if not is_url(url):
        # Not a URL - return as-is (could be a plain ID)
        return url, None

    # Auto-detect adapter type from URL if not provided
    if not adapter_type:
        # Check for specific domains first (more reliable than path patterns)
        if "linear.app" in url.lower():
            adapter_type = "linear"
        elif "github.com" in url.lower():
            adapter_type = "github"
        elif "atlassian.net" in url.lower():
            adapter_type = "jira"
        # Fallback to path-based detection for self-hosted instances
        elif "/browse/" in url:
            adapter_type = "jira"
        else:
            return None, f"Unknown URL format - cannot auto-detect adapter: {url}"

    # Route to appropriate parser
    if adapter_type.lower() == "linear":
        return extract_linear_id(url)
    elif adapter_type.lower() == "jira":
        return extract_jira_id(url)
    elif adapter_type.lower() == "github":
        return extract_github_id(url)
    else:
        return None, f"Unsupported adapter type: {adapter_type}"


def normalize_project_id(value: str, adapter_type: Optional[str] = None) -> str:
    """Normalize a project ID by extracting from URL if necessary.

    This is a convenience function that handles both URLs and plain IDs.
    If the value is a URL, it extracts the ID. If it's already a plain ID,
    it returns it unchanged.

    Args:
        value: Project ID or URL
        adapter_type: Optional adapter type hint

    Returns:
        Normalized project ID (extracted from URL if applicable)

    Raises:
        URLParserError: If URL parsing fails

    Examples:
        >>> normalize_project_id("PROJ-123")
        'PROJ-123'
        >>> normalize_project_id("https://linear.app/team/project/abc-123")
        'abc-123'
    """
    if not value:
        return value

    # If not a URL, return as-is
    if not is_url(value):
        return value

    # Extract ID from URL
    extracted_id, error = extract_id_from_url(value, adapter_type)

    if error:
        raise URLParserError(error)

    return extracted_id or value
