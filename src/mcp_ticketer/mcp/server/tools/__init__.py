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
    config_tools: Configuration management (adapter, project, user settings)
    session_tools: Session tracking and ticket association management
    user_ticket_tools: User-specific ticket operations (my tickets, transitions)
    analysis_tools: Ticket analysis and cleanup tools (similar, stale, orphaned)
    label_tools: Label management, normalization, deduplication, and cleanup
    project_tools: Unified project management (status analysis + updates) - v2.1.0
    project_update_tools: DEPRECATED - Use project_tools instead (kept for backward compatibility)
    project_status_tools: DEPRECATED - Use project_tools instead (kept for backward compatibility)
    milestone_tools: Milestone management and progress tracking (1M-607)
    attachment_tools: File attachment management (ticket_attach, ticket_attachments)

Note:
    instruction_tools: Removed from MCP server (CLI-only as of Phase 2 Sprint 2.3)
    pr_tools: Removed from MCP server (CLI-only as of Phase 2 Sprint 1.3)
    These tools are available via CLI commands but not exposed through MCP interface.
    Use GitHub MCP for PR management.

"""

# Import all tool modules to register them with FastMCP
# Order matters - import core functionality first
from . import (
    analysis_tools,  # noqa: F401
    attachment_tools,  # noqa: F401
    bulk_tools,  # noqa: F401
    comment_tools,  # noqa: F401
    config_tools,  # noqa: F401
    hierarchy_tools,  # noqa: F401
    # instruction_tools removed - CLI-only (Phase 2 Sprint 2.3)
    label_tools,  # noqa: F401
    milestone_tools,  # noqa: F401
    project_status_tools,  # noqa: F401 - DEPRECATED, kept for backward compatibility
    # pr_tools removed - CLI-only (Phase 2 Sprint 1.3 - use GitHub MCP)
    project_tools,  # noqa: F401 - v2.1.0 unified project management
    project_update_tools,  # noqa: F401 - DEPRECATED, kept for backward compatibility
    search_tools,  # noqa: F401
    session_tools,  # noqa: F401
    ticket_tools,  # noqa: F401
    user_ticket_tools,  # noqa: F401
)

__all__ = [
    "analysis_tools",
    "attachment_tools",
    "bulk_tools",
    "comment_tools",
    "config_tools",
    "hierarchy_tools",
    # "instruction_tools" removed - CLI-only (Phase 2 Sprint 2.3)
    "label_tools",
    "milestone_tools",
    # "pr_tools" removed - CLI-only (Phase 2 Sprint 1.3)
    "project_tools",  # v2.1.0 unified project management
    "project_status_tools",  # DEPRECATED - kept for backward compatibility
    "project_update_tools",  # DEPRECATED - kept for backward compatibility
    "search_tools",
    "session_tools",
    "ticket_tools",
    "user_ticket_tools",
]
