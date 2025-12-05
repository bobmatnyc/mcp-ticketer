"""GitHub adapter for MCP Ticketer.

This module provides integration with GitHub's REST and GraphQL APIs for universal ticket management.
The adapter is split into multiple modules for better organization:

- adapter.py: Main GitHubAdapter class with core functionality
- queries.py: GraphQL queries and fragments
- types.py: GitHub-specific types and mappings
- client.py: HTTP/GraphQL client management
- mappers.py: Data transformation between GitHub and universal models

Usage:
    from mcp_ticketer.adapters.github import GitHubAdapter

    config = {
        "token": "your_github_token",
        "owner": "repository_owner",
        "repo": "repository_name"
    }
    adapter = GitHubAdapter(config)
"""

from .adapter import GitHubAdapter
from .types import GitHubStateMapping

__all__ = ["GitHubAdapter", "GitHubStateMapping"]
