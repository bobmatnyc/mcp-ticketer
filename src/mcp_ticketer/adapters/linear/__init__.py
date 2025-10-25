"""Linear adapter for MCP Ticketer.

This module provides integration with Linear's GraphQL API for universal ticket management.
The adapter is split into multiple modules for better organization:

- adapter.py: Main LinearAdapter class with core functionality
- queries.py: GraphQL queries and fragments
- types.py: Linear-specific types and mappings
- client.py: GraphQL client management
- mappers.py: Data transformation between Linear and universal models

Usage:
    from mcp_ticketer.adapters.linear import LinearAdapter

    config = {
        "api_key": "your_linear_api_key",
        "team_id": "your_team_id"
    }
    adapter = LinearAdapter(config)
"""

from .adapter import LinearAdapter

__all__ = ["LinearAdapter"]
