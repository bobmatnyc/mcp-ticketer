"""JIRA adapter for universal ticket management.

This module provides a unified interface to JIRA REST API v3, supporting both
JIRA Cloud and JIRA Server/Data Center.

Public API:
-----------
    JiraAdapter: Main adapter class for JIRA operations
    JiraIssueType: Enum of common JIRA issue types
    JiraPriority: Enum of standard JIRA priority levels

Usage:
------
    from mcp_ticketer.adapters.jira import JiraAdapter

    config = {
        "server": "https://company.atlassian.net",
        "email": "user@example.com",
        "api_token": "your-token",
        "project_key": "PROJ",
    }

    adapter = JiraAdapter(config)
    tickets = await adapter.list(limit=10)

"""

from .adapter import JiraAdapter
from .types import JiraIssueType, JiraPriority

__all__ = [
    "JiraAdapter",
    "JiraIssueType",
    "JiraPriority",
]
