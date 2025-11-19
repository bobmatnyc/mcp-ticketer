"""User-specific ticket management tools.

This module provides tools for managing tickets from a user's perspective,
including listing assigned tickets and transitioning tickets through workflow
states with validation.

Design Decision: Workflow State Validation
------------------------------------------
State transitions are validated using TicketState.can_transition_to() to ensure
tickets follow the defined workflow. This prevents invalid state changes that
could break integrations or confuse team members.

Valid workflow transitions:
- OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
- IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
- READY → TESTED, IN_PROGRESS, BLOCKED
- TESTED → DONE, IN_PROGRESS
- DONE → CLOSED
- WAITING/BLOCKED → OPEN, IN_PROGRESS, CLOSED
- CLOSED → (no transitions, terminal state)

Performance Considerations:
- get_my_tickets uses adapter's native filtering when available
- Falls back to client-side filtering for adapters without assignee filter
- State transition validation is O(1) lookup in predefined state machine
"""

from pathlib import Path
from typing import Any

from ....core.models import TicketState
from ....core.project_config import ConfigResolver, TicketerConfig
from ..server_sdk import get_adapter, mcp


def get_config_resolver() -> ConfigResolver:
    """Get configuration resolver for current project.

    Returns:
        ConfigResolver instance for current working directory
    """
    return ConfigResolver(project_path=Path.cwd())


@mcp.tool()
async def get_my_tickets(
    state: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Get tickets assigned to the configured default user.

    Retrieves tickets assigned to the user specified in default_user configuration.
    Requires default_user to be set via config_set_default_user().

    Args:
        state: Optional state filter - must be one of: open, in_progress, ready,
            tested, done, closed, waiting, blocked
        limit: Maximum number of tickets to return (default: 10, max: 100)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - tickets: List of ticket objects assigned to user
        - count: Number of tickets returned
        - user: User ID that was queried
        - state_filter: State filter applied (if any)
        - error: Error details (if failed)

    Example:
        >>> result = await get_my_tickets(state="in_progress", limit=5)
        >>> print(result)
        {
            "status": "completed",
            "tickets": [
                {"id": "TICKET-1", "title": "Fix bug", "state": "in_progress"},
                {"id": "TICKET-2", "title": "Add feature", "state": "in_progress"}
            ],
            "count": 2,
            "user": "user@example.com",
            "state_filter": "in_progress"
        }

    Error Conditions:
        - No default user configured: Returns error with setup instructions
        - Invalid state: Returns error with valid state options
        - Adapter query failure: Returns error with details

    Usage Notes:
        - Requires default_user to be set in configuration
        - Use config_set_default_user() to configure the user first
        - Limit is capped at 100 to prevent performance issues
    """
    try:
        # Validate limit
        if limit > 100:
            limit = 100

        # Load configuration to get default user
        resolver = get_config_resolver()
        config = resolver.load_project_config() or TicketerConfig()

        if not config.default_user:
            return {
                "status": "error",
                "error": "No default user configured. Use config_set_default_user() to set a default user first.",
                "setup_command": "config_set_default_user",
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

        # Build filters
        filters: dict[str, Any] = {"assignee": config.default_user}
        if state_filter:
            filters["state"] = state_filter

        # Query adapter
        adapter = get_adapter()
        tickets = await adapter.list(limit=limit, offset=0, filters=filters)

        return {
            "status": "completed",
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


@mcp.tool()
async def get_available_transitions(ticket_id: str) -> dict[str, Any]:
    """Get valid next states for a ticket based on workflow rules.

    Retrieves the ticket's current state and returns all valid target states
    according to the defined workflow state machine. This helps AI agents and
    users understand which state transitions are allowed.

    Args:
        ticket_id: Unique identifier of the ticket

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - ticket_id: ID of the queried ticket
        - current_state: Current workflow state
        - available_transitions: List of valid target states
        - transition_descriptions: Human-readable descriptions of each transition
        - error: Error details (if failed)

    Example:
        >>> result = await get_available_transitions("TICKET-123")
        >>> print(result)
        {
            "status": "completed",
            "ticket_id": "TICKET-123",
            "current_state": "in_progress",
            "available_transitions": ["ready", "waiting", "blocked", "open"],
            "transition_descriptions": {
                "ready": "Mark work as complete and ready for review",
                "waiting": "Pause work while waiting for external dependency",
                "blocked": "Work is blocked by an impediment",
                "open": "Move back to backlog"
            }
        }

    Error Conditions:
        - Ticket not found: Returns error with ticket ID
        - Adapter query failure: Returns error with details
        - Terminal state (CLOSED): Returns empty transitions list

    Usage Notes:
        - CLOSED is a terminal state with no valid transitions
        - Use this before ticket_transition() to validate intended state change
        - Transition validation prevents workflow violations
    """
    try:
        # Get ticket from adapter
        adapter = get_adapter()
        ticket = await adapter.read(ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Get current state
        current_state = ticket.state

        # Get valid transitions from state machine
        valid_transitions = TicketState.valid_transitions()
        # Handle both TicketState enum and string values
        if isinstance(current_state, str):
            current_state = TicketState(current_state)
        available = valid_transitions.get(current_state, [])

        # Create human-readable descriptions
        descriptions = {
            TicketState.OPEN: "Move to backlog (not yet started)",
            TicketState.IN_PROGRESS: "Begin active work on ticket",
            TicketState.READY: "Mark as complete and ready for review/testing",
            TicketState.TESTED: "Mark as tested and verified",
            TicketState.DONE: "Mark as complete and accepted",
            TicketState.WAITING: "Pause work while waiting for external dependency",
            TicketState.BLOCKED: "Work is blocked by an impediment",
            TicketState.CLOSED: "Close and archive ticket (final state)",
        }

        transition_descriptions = {
            state.value: descriptions.get(state, "") for state in available
        }

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "current_state": current_state.value,
            "available_transitions": [state.value for state in available],
            "transition_descriptions": transition_descriptions,
            "is_terminal": len(available) == 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get available transitions: {str(e)}",
        }


@mcp.tool()
async def ticket_transition(
    ticket_id: str,
    to_state: str,
    comment: str | None = None,
) -> dict[str, Any]:
    """Move ticket through workflow with validation and optional comment.

    Transitions a ticket to a new state, validating the transition against the
    defined workflow rules. Optionally adds a comment explaining the transition.

    Workflow State Machine:
        OPEN → IN_PROGRESS, WAITING, BLOCKED, CLOSED
        IN_PROGRESS → READY, WAITING, BLOCKED, OPEN
        READY → TESTED, IN_PROGRESS, BLOCKED
        TESTED → DONE, IN_PROGRESS
        DONE → CLOSED
        WAITING → OPEN, IN_PROGRESS, CLOSED
        BLOCKED → OPEN, IN_PROGRESS, CLOSED
        CLOSED → (no transitions)

    Args:
        ticket_id: Unique identifier of the ticket to transition
        to_state: Target state - must be valid for current state
        comment: Optional comment explaining the transition reason

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - ticket: Updated ticket object with new state
        - previous_state: State before transition
        - new_state: State after transition
        - comment_added: Whether a comment was added (if applicable)
        - error: Error details (if failed)

    Example:
        >>> result = await ticket_transition(
        ...     "TICKET-123",
        ...     "ready",
        ...     "Work complete, ready for code review"
        ... )
        >>> print(result)
        {
            "status": "completed",
            "ticket": {"id": "TICKET-123", "state": "ready", ...},
            "previous_state": "in_progress",
            "new_state": "ready",
            "comment_added": True
        }

    Error Conditions:
        - Ticket not found: Returns error with ticket ID
        - Invalid transition: Returns error with valid options
        - Invalid state name: Returns error with valid states
        - Adapter update failure: Returns error with details

    Usage Notes:
        - Use get_available_transitions() first to see valid options
        - Comments are adapter-dependent (some may not support them)
        - Validation prevents workflow violations
        - Terminal state (CLOSED) has no valid transitions
    """
    try:
        # Get ticket from adapter
        adapter = get_adapter()
        ticket = await adapter.read(ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Validate target state
        try:
            target_state = TicketState(to_state.lower())
        except ValueError:
            valid_states = [s.value for s in TicketState]
            return {
                "status": "error",
                "error": f"Invalid state '{to_state}'. Must be one of: {', '.join(valid_states)}",
                "valid_states": valid_states,
            }

        # Store current state for response
        current_state = ticket.state
        # Handle both TicketState enum and string values
        if isinstance(current_state, str):
            current_state = TicketState(current_state)

        # Validate transition
        if not current_state.can_transition_to(target_state):
            valid_transitions = TicketState.valid_transitions().get(current_state, [])
            valid_values = [s.value for s in valid_transitions]
            return {
                "status": "error",
                "error": f"Invalid transition from '{current_state.value}' to '{target_state.value}'",
                "current_state": current_state.value,
                "valid_transitions": valid_values,
                "message": f"Cannot transition from {current_state.value} to {target_state.value}. "
                f"Valid transitions: {', '.join(valid_values) if valid_values else 'none (terminal state)'}",
            }

        # Update ticket state
        updated = await adapter.update(ticket_id, {"state": target_state})

        if updated is None:
            return {
                "status": "error",
                "error": f"Failed to update ticket {ticket_id}",
            }

        # Add comment if provided and adapter supports it
        comment_added = False
        if comment and hasattr(adapter, "add_comment"):
            try:
                await adapter.add_comment(ticket_id, comment)
                comment_added = True
            except Exception as e:
                # Log but don't fail the transition
                comment_added = False

        return {
            "status": "completed",
            "ticket": updated.model_dump(),
            "previous_state": current_state.value,
            "new_state": target_state.value,
            "comment_added": comment_added,
            "message": f"Ticket {ticket_id} transitioned from {current_state.value} to {target_state.value}",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to transition ticket: {str(e)}",
        }
