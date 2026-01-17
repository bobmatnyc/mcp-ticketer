"""MCP tools for session and ticket association management.

This module implements tools for session management and user ticket operations.

Features:
- user_session: Unified interface for user ticket queries, session info, and ticket association

All tools follow the MCP response pattern:
    {
        "status": "completed" | "error",
        "data": {...}
    }
"""

import logging
from pathlib import Path
from typing import Any, Literal

from ....core.session_state import SessionStateManager
from ..server_sdk import mcp

logger = logging.getLogger(__name__)


@mcp.tool(
    description="Manage work session context - attach tickets to sessions, track current work item, opt in/out of session tracking"
)
async def user_session(
    action: Literal[
        "get_my_tickets",
        "get_session_info",
        "attach_ticket",
        "detach_ticket",
        "get_attached",
        "opt_out",
    ],
    ticket_id: str | None = None,
    state: str | None = None,
    project_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Unified user session management tool.

    Handles user ticket queries, session information, and ticket association
    through a single interface. This tool consolidates get_my_tickets,
    get_session_info, and attach_ticket.

    Args:
        action: Operation to perform. Valid values:
            - "get_my_tickets": Get tickets assigned to default user
            - "get_session_info": Get current session information
            - "attach_ticket": Associate work with a ticket
            - "detach_ticket": Remove ticket association
            - "get_attached": Check current attachment status
            - "opt_out": Opt out of ticket association for this session
        ticket_id: Ticket ID to associate (required for attach_ticket action)
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

        # Attach to a ticket
        result = await user_session(
            action="attach_ticket",
            ticket_id="PROJ-123"
        )

        # Detach from current ticket
        result = await user_session(
            action="detach_ticket"
        )

        # Check attachment status
        result = await user_session(
            action="get_attached"
        )

        # Opt out of ticket association
        result = await user_session(
            action="opt_out"
        )

    Migration from old tools:
        - get_my_tickets(state=..., limit=...) → user_session(action="get_my_tickets", state=..., limit=...)
        - get_session_info() → user_session(action="get_session_info")
        - attach_ticket(action="set", ticket_id="...") → user_session(action="attach_ticket", ticket_id="...")
        - attach_ticket(action="clear") → user_session(action="detach_ticket")
        - attach_ticket(action="status") → user_session(action="get_attached")
        - attach_ticket(action="none") → user_session(action="opt_out")

    See: docs/mcp-api-reference.md for detailed response formats
    """
    action_lower = action.lower()

    # Route to appropriate handler based on action
    if action_lower == "get_my_tickets":
        # Inline implementation of get_my_tickets
        try:
            from ....core.models import TicketState
            from ....core.project_config import ConfigResolver, TicketerConfig
            from ..server_sdk import get_adapter

            # Validate limit
            if limit > 100:
                limit = 100

            # Load configuration to get default user and project
            resolver = ConfigResolver(project_path=Path.cwd())
            config = resolver.load_project_config() or TicketerConfig()

            if not config.default_user:
                return {
                    "status": "error",
                    "error": "No default user configured. Use config_set_default_user() to set a default user first.",
                    "setup_command": "config_set_default_user",
                }

            # Validate project context (Required for list operations)
            final_project = project_id or config.default_project

            if not final_project:
                return {
                    "status": "error",
                    "error": "project_id required. Provide project_id parameter or configure default_project.",
                    "help": "Use config_set_default_project(project_id='YOUR-PROJECT') to set default project",
                    "check_config": "Use config_get() to view current configuration",
                }

            # Validate state if provided
            state_filter = None
            if state is not None:
                try:
                    state_filter = TicketState(state.lower())
                except ValueError:
                    valid_states = [s.value for s in TicketState]
                    return {
                        "status": "error",
                        "error": f"Invalid state '{state}'. Must be one of: {', '.join(valid_states)}",
                        "valid_states": valid_states,
                    }

            # Build filters with required project scoping
            filters: dict[str, Any] = {
                "assignee": config.default_user,
                "project": final_project,
            }
            if state_filter:
                filters["state"] = state_filter

            # Query adapter
            adapter = get_adapter()
            tickets = await adapter.list(limit=limit, offset=0, filters=filters)

            # Build adapter metadata
            metadata = {
                "adapter": adapter.adapter_type,
                "adapter_name": adapter.adapter_display_name,
            }

            return {
                "status": "completed",
                **metadata,
                "tickets": [ticket.model_dump() for ticket in tickets],
                "count": len(tickets),
                "user": config.default_user,
                "state_filter": state if state else "all",
                "limit": limit,
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to retrieve tickets: {str(e)}",
            }
    elif action_lower == "get_session_info":
        # Inline implementation of get_session_info
        try:
            manager = SessionStateManager(project_path=Path.cwd())
            state_obj = manager.load_session()

            return {
                "success": True,
                "session_id": state_obj.session_id,
                "current_ticket": state_obj.current_ticket,
                "opted_out": state_obj.ticket_opted_out,
                "last_activity": state_obj.last_activity,
                "session_timeout_minutes": 30,
            }

        except Exception as e:
            logger.error(f"Error in get_session_info: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    elif action_lower == "attach_ticket":
        # Implementation of attach_ticket (was attach_ticket action="set")
        try:
            if not ticket_id:
                return {
                    "success": False,
                    "error": "ticket_id is required when action='attach_ticket'",
                    "guidance": "Please provide a ticket ID to associate with this session",
                }

            manager = SessionStateManager(project_path=Path.cwd())
            state_obj = manager.load_session()
            manager.set_current_ticket(ticket_id)

            return {
                "success": True,
                "message": f"Work session now associated with ticket: {ticket_id}",
                "current_ticket": ticket_id,
                "session_id": state_obj.session_id,
                "opted_out": False,
            }

        except Exception as e:
            logger.error(f"Error in attach_ticket: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    elif action_lower == "detach_ticket":
        # Implementation of detach_ticket (was attach_ticket action="clear")
        try:
            manager = SessionStateManager(project_path=Path.cwd())
            state_obj = manager.load_session()
            manager.set_current_ticket(None)

            return {
                "success": True,
                "message": "Ticket association cleared",
                "current_ticket": None,
                "session_id": state_obj.session_id,
                "opted_out": False,
                "guidance": "You can associate with a ticket anytime using user_session(action='attach_ticket', ticket_id='...')",
            }

        except Exception as e:
            logger.error(f"Error in detach_ticket: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    elif action_lower == "opt_out":
        # Implementation of opt_out (was attach_ticket action="none")
        try:
            manager = SessionStateManager(project_path=Path.cwd())
            state_obj = manager.load_session()
            manager.opt_out_ticket()

            return {
                "success": True,
                "message": "Opted out of ticket association for this session",
                "current_ticket": None,
                "session_id": state_obj.session_id,
                "opted_out": True,
                "note": "This opt-out will reset after 30 minutes of inactivity",
            }

        except Exception as e:
            logger.error(f"Error in opt_out: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    elif action_lower == "get_attached":
        # Implementation of get_attached (was attach_ticket action="status")
        try:
            manager = SessionStateManager(project_path=Path.cwd())
            state_obj = manager.load_session()
            current_ticket = manager.get_current_ticket()

            if state_obj.ticket_opted_out:
                status_msg = "No ticket associated (opted out for this session)"
            elif current_ticket:
                status_msg = f"Currently associated with ticket: {current_ticket}"
            else:
                status_msg = "No ticket associated"

            return {
                "success": True,
                "message": status_msg,
                "current_ticket": current_ticket,
                "session_id": state_obj.session_id,
                "opted_out": state_obj.ticket_opted_out,
                "guidance": (
                    (
                        "Associate with a ticket: user_session(action='attach_ticket', ticket_id='...')\n"
                        "Opt out: user_session(action='opt_out')"
                    )
                    if not current_ticket and not state_obj.ticket_opted_out
                    else None
                ),
            }

        except Exception as e:
            logger.error(f"Error in get_attached: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    else:
        valid_actions = [
            "get_my_tickets",
            "get_session_info",
            "attach_ticket",
            "detach_ticket",
            "get_attached",
            "opt_out",
        ]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use user_session(action='get_my_tickets'|'get_session_info'|'attach_ticket'|'detach_ticket'|'get_attached'|'opt_out', ...)",
        }


async def attach_ticket(
    action: str,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    """DEPRECATED: Use user_session() instead.

    This function has been consolidated into user_session() for better organization.

    Migration:
        - attach_ticket(action="set", ticket_id="...") → user_session(action="attach_ticket", ticket_id="...")
        - attach_ticket(action="clear") → user_session(action="detach_ticket")
        - attach_ticket(action="status") → user_session(action="get_attached")
        - attach_ticket(action="none") → user_session(action="opt_out")

    This function is kept for backward compatibility but is no longer registered
    as an MCP tool. Please migrate to user_session().

    Args:
        action: What to do with the ticket association (set/clear/none/status)
        ticket_id: Ticket ID to associate (e.g., "PROJ-123", UUID), required for 'set'

    Returns:
        Success status and current session state
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
