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
    instruction_tools: Ticket instructions management
    config_tools: Configuration management (adapter, project, user settings)
    session_tools: Session tracking and ticket association management
    user_ticket_tools: User-specific ticket operations (my tickets, transitions)
    analysis_tools: Ticket analysis and cleanup tools (similar, stale, orphaned)

"""

# Import all tool modules to register them with FastMCP
# Order matters - import core functionality first
from . import analysis_tools  # noqa: F401
from . import attachment_tools  # noqa: F401
from . import bulk_tools  # noqa: F401
from . import comment_tools  # noqa: F401
from . import config_tools  # noqa: F401
from . import hierarchy_tools  # noqa: F401
from . import instruction_tools  # noqa: F401
from . import pr_tools  # noqa: F401
from . import search_tools  # noqa: F401
from . import session_tools  # noqa: F401
from . import ticket_tools  # noqa: F401
from . import user_ticket_tools  # noqa: F401

__all__ = [
    "analysis_tools",
    "attachment_tools",
    "bulk_tools",
    "comment_tools",
    "config_tools",
    "hierarchy_tools",
    "instruction_tools",
    "pr_tools",
    "search_tools",
    "session_tools",
    "ticket_tools",
    "user_ticket_tools",
]
