"""MCP tools for session and ticket association management.

This module implements tools for session management and user ticket operations.

Features:
- user_session: Unified interface for user ticket queries and session info
- get_my_tickets: Get user's tickets (deprecated, use user_session)
- get_session_info: Get session metadata (deprecated, use user_session)
- attach_ticket: Associate work session with ticket

All tools follow the MCP response pattern:
    {
        "status": "completed" | "error",
        "data": {...}
    }
"""

import logging
import warnings
from pathlib import Path
from typing import Any, Literal

from ....core.session_state import SessionStateManager
from ..server_sdk import mcp

# Import for user_session routing
# Note: We import the implementation, not the decorated tool to avoid decorator issues
from . import user_ticket_tools

logger = logging.getLogger(__name__)


@mcp.tool()
async def user_session(
    action: Literal["get_my_tickets", "get_session_info"],
    state: str | None = None,
    project_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Unified user session management tool.

    Handles user ticket queries and session information through a single
    interface. This tool consolidates get_my_tickets and get_session_info.

    Args:
        action: Operation to perform. Valid values:
            - "get_my_tickets": Get tickets assigned to default user
            - "get_session_info": Get current session information
        state: Filter tickets by state (for get_my_tickets only)
        project_id: Filter tickets by project (for get_my_tickets only)
        limit: Maximum tickets to return (for get_my_tickets, default: 10, max: 100)

    Returns:
        Results dictionary containing operation-specific data

    Raises:
        ValueError: If action is invalid

    Examples:
        # Get user's tickets
        result = await user_session(
            action="get_my_tickets",
            state="open",
            limit=20
        )

        # Get user's tickets with project filter
        result = await user_session(
            action="get_my_tickets",
            project_id="PROJ-123",
            state="in_progress"
        )

        # Get session info
        result = await user_session(
            action="get_session_info"
        )

    Migration from old tools:
        - get_my_tickets(state=..., limit=...) → user_session(action="get_my_tickets", state=..., limit=...)
        - get_session_info() → user_session(action="get_session_info")

    See: docs/mcp-api-reference.md for detailed response formats
    """
    action_lower = action.lower()

    # Route to appropriate handler based on action
    if action_lower == "get_my_tickets":
        return await user_ticket_tools.get_my_tickets(
            state=state, project_id=project_id, limit=limit
        )
    elif action_lower == "get_session_info":
        return await get_session_info()
    else:
        valid_actions = ["get_my_tickets", "get_session_info"]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use user_session(action='get_my_tickets'|'get_session_info', ...)",
        }


@mcp.tool()
async def attach_ticket(
    action: str,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    """Associate current work session with a ticket.

    This tool helps track which ticket your current work is related to.
    The association persists for the session (30 minutes of inactivity).

    **Important**: It's recommended to associate work with a ticket for proper
    tracking and organization.

    Actions:
    - **set**: Associate work with a specific ticket
    - **clear**: Remove current ticket association
    - **none**: Opt out of ticket association for this session
    - **status**: Check current ticket association

    Args:
        action: What to do with the ticket association (set/clear/none/status)
        ticket_id: Ticket ID to associate (e.g., "PROJ-123", UUID), required for 'set'

    Returns:
        Success status and current session state

    Examples:
        # Associate with a ticket
        attach_ticket(action="set", ticket_id="PROJ-123")

        # Opt out for this session
        attach_ticket(action="none")

        # Check current status
        attach_ticket(action="status")

    """
    try:
        manager = SessionStateManager(project_path=Path.cwd())
        state = manager.load_session()

        if action == "set":
            if not ticket_id:
                return {
                    "success": False,
                    "error": "ticket_id is required when action='set'",
                    "guidance": "Please provide a ticket ID to associate with this session",
                }

            manager.set_current_ticket(ticket_id)
            return {
                "success": True,
                "message": f"Work session now associated with ticket: {ticket_id}",
                "current_ticket": ticket_id,
                "session_id": state.session_id,
                "opted_out": False,
            }

        elif action == "clear":
            manager.set_current_ticket(None)
            return {
                "success": True,
                "message": "Ticket association cleared",
                "current_ticket": None,
                "session_id": state.session_id,
                "opted_out": False,
                "guidance": "You can associate with a ticket anytime using attach_ticket(action='set', ticket_id='...')",
            }

        elif action == "none":
            manager.opt_out_ticket()
            return {
                "success": True,
                "message": "Opted out of ticket association for this session",
                "current_ticket": None,
                "session_id": state.session_id,
                "opted_out": True,
                "note": "This opt-out will reset after 30 minutes of inactivity",
            }

        elif action == "status":
            current_ticket = manager.get_current_ticket()

            if state.ticket_opted_out:
                status_msg = "No ticket associated (opted out for this session)"
            elif current_ticket:
                status_msg = f"Currently associated with ticket: {current_ticket}"
            else:
                status_msg = "No ticket associated"

            return {
                "success": True,
                "message": status_msg,
                "current_ticket": current_ticket,
                "session_id": state.session_id,
                "opted_out": state.ticket_opted_out,
                "guidance": (
                    (
                        "Associate with a ticket: attach_ticket(action='set', ticket_id='...')\n"
                        "Opt out: attach_ticket(action='none')"
                    )
                    if not current_ticket and not state.ticket_opted_out
                    else None
                ),
            }

        else:
            return {
                "success": False,
                "error": f"Invalid action: {action}",
                "valid_actions": ["set", "clear", "none", "status"],
            }

    except Exception as e:
        logger.error(f"Error in attach_ticket: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@mcp.tool()
async def get_session_info() -> dict[str, Any]:
    """Get current session information and ticket association status.

    .. deprecated:: 1.5.0
        Use :func:`user_session` with ``action='get_session_info'`` instead.
        This function will be removed in version 2.0.0.

    Returns session metadata including ID, current ticket, and activity status.

    Returns:
        Session information dictionary

    Examples:
        # Old way (deprecated)
        result = await get_session_info()

        # New way (recommended)
        result = await user_session(action="get_session_info")

    Example Response:
        {
            "session_id": "abc-123",
            "current_ticket": "PROJ-123",
            "opted_out": false,
            "last_activity": "2025-01-19T20:00:00"
        }

    """
    warnings.warn(
        "get_session_info is deprecated. Use user_session(action='get_session_info') instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        manager = SessionStateManager(project_path=Path.cwd())
        state = manager.load_session()

        return {
            "success": True,
            "session_id": state.session_id,
            "current_ticket": state.current_ticket,
            "opted_out": state.ticket_opted_out,
            "last_activity": state.last_activity,
            "session_timeout_minutes": 30,
        }

    except Exception as e:
        logger.error(f"Error in get_session_info: {e}")
        return {
            "success": False,
            "error": str(e),
        }
