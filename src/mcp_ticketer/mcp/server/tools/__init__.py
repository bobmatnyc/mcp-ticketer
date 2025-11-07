"""MCP tool modules for ticket operations.

This package contains all FastMCP tool implementations organized by
functional area. Tools are automatically registered with the FastMCP
server when imported.

Modules:
    ticket_tools: Basic CRUD operations for tickets
    hierarchy_tools: Epic/Issue/Task hierarchy management
    search_tools: Search and query operations
    bulk_tools: Bulk create and update operations
    comment_tools: Comment management
    pr_tools: Pull request integration
    attachment_tools: File attachment handling

"""

# Import all tool modules to register them with FastMCP
# Order matters - import core functionality first
from . import attachment_tools  # noqa: F401
from . import bulk_tools  # noqa: F401
from . import comment_tools  # noqa: F401
from . import hierarchy_tools  # noqa: F401
from . import pr_tools  # noqa: F401
from . import search_tools  # noqa: F401
from . import ticket_tools  # noqa: F401

__all__ = [
    "ticket_tools",
    "hierarchy_tools",
    "search_tools",
    "bulk_tools",
    "comment_tools",
    "pr_tools",
    "attachment_tools",
]
