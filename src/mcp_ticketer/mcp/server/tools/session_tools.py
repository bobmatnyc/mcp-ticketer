"""MCP tools for session and ticket association management."""

import logging
from pathlib import Path
from typing import Any

from ....core.session_state import SessionStateManager
from ..server_sdk import mcp

logger = logging.getLogger(__name__)


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

    Returns session metadata including ID, current ticket, and activity status.

    Returns:
        Session information dictionary

    Example:
        {
            "session_id": "abc-123",
            "current_ticket": "PROJ-123",
            "opted_out": false,
            "last_activity": "2025-01-19T20:00:00"
        }

    """
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
