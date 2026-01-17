"""User-specific ticket management tools.

This module provides tools for managing tickets from a user's perspective,
including transitioning tickets through workflow states with validation.

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
- State transition validation is O(1) lookup in predefined state machine
"""

from typing import Any

from ....core.adapter import BaseAdapter
from ....core.models import TicketState
from ....core.state_matcher import get_state_matcher
from ..server_sdk import get_adapter, mcp


def _build_adapter_metadata(
    adapter: BaseAdapter,
    ticket_id: str | None = None,
) -> dict[str, Any]:
    """Build adapter metadata for MCP responses."""
    metadata = {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }
    if ticket_id:
        metadata["ticket_id"] = ticket_id
    return metadata


@mcp.tool(
    description="Manage custom workflows - create, update, delete workflow states; configure state transitions and workflow automation rules"
)
async def workflow(
    action: str,
    ticket_id: str,
    to_state: str | None = None,
    comment: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """Unified workflow management for ticket state transitions.

    Consolidates workflow state operations into a single interface for
    getting available transitions and performing state transitions.

    Args:
        action: Operation to perform. Valid values:
            - "get_transitions": Get valid next states for ticket
            - "transition": Move ticket through workflow with validation
        ticket_id: Ticket ID (required for all actions)
        to_state: Target state (required for "transition", supports natural language)
        comment: Optional comment when transitioning
        auto_confirm: Auto-confirm medium confidence matches (default: True)

    Returns:
        For get_transitions: TransitionResponse with current_state, available_transitions,
                           transition_descriptions, is_terminal
        For transition: TransitionResponse with status, ticket, previous_state, new_state,
                       matched_state, confidence, suggestions (if ambiguous)

    Examples:
        # Get available transitions
        workflow(action="get_transitions", ticket_id="PROJ-123")

        # Transition ticket (exact state name)
        workflow(action="transition", ticket_id="PROJ-123", to_state="in_progress")

        # Transition with natural language
        workflow(action="transition", ticket_id="PROJ-123", to_state="working on it")

        # Transition with comment
        workflow(
            action="transition",
            ticket_id="PROJ-123",
            to_state="done",
            comment="Implementation complete and tested"
        )

    Migration from deprecated tools:
        - get_available_transitions(ticket_id) → workflow(action="get_transitions", ticket_id=ticket_id)
        - ticket_transition(ticket_id, to_state, ...) → workflow(action="transition", ticket_id=ticket_id, to_state=to_state, ...)

    See:
        - docs/ticket-workflows.md#valid-state-transitions
        - docs/ticket-workflows.md#semantic-state-matching
    """
    if action == "get_transitions":
        return await _handle_get_transitions(ticket_id)
    elif action == "transition":
        if to_state is None:
            return {
                "status": "error",
                "error": "to_state is required for transition action",
            }
        return await _handle_transition(ticket_id, to_state, comment, auto_confirm)
    else:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be 'get_transitions' or 'transition'",
        }


async def _handle_get_transitions(ticket_id: str) -> dict[str, Any]:
    """Get valid next states for ticket based on workflow state machine.

    This is the internal implementation for workflow(action="get_transitions").

    Args:
        ticket_id: Ticket ID to get transitions for

    Returns:
        TransitionResponse with current_state, available_transitions,
        transition_descriptions, is_terminal
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
            **_build_adapter_metadata(adapter, ticket_id),
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


async def _handle_transition(
    ticket_id: str,
    to_state: str,
    comment: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """Move ticket through workflow with validation and semantic matching.

    This is the internal implementation for workflow(action="transition").
    Supports natural language state names (e.g., "working on it" → "in_progress").

    Args:
        ticket_id: Ticket ID to transition
        to_state: Target state (supports natural language)
        comment: Optional comment to add with transition
        auto_confirm: Auto-confirm medium confidence matches (default: True)

    Returns:
        TransitionResponse with status, ticket, previous_state, new_state,
        matched_state, confidence, suggestions (if ambiguous)
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

        # Store current state for response
        current_state = ticket.state
        # Handle both TicketState enum and string values
        if isinstance(current_state, str):
            current_state = TicketState(current_state)

        # Use semantic matcher to resolve target state
        matcher = get_state_matcher()
        match_result = matcher.match_state(to_state)

        # Build response with semantic match info
        response: dict[str, Any] = {
            "ticket_id": ticket_id,
            "original_input": to_state,
            "matched_state": match_result.state.value,
            "confidence": match_result.confidence,
            "match_type": match_result.match_type,
            "current_state": current_state.value,
        }

        # Handle low confidence - provide suggestions
        if match_result.is_low_confidence():
            suggestions = matcher.suggest_states(to_state, top_n=3)
            return {
                **response,
                "status": "ambiguous",
                "message": "Input is ambiguous. Please choose from suggestions.",
                "suggestions": [
                    {
                        "state": s.state.value,
                        "confidence": s.confidence,
                        "description": _get_state_description(s.state),
                    }
                    for s in suggestions
                ],
            }

        # Handle medium confidence - needs confirmation unless auto_confirm
        if match_result.is_medium_confidence() and not auto_confirm:
            return {
                **response,
                "status": "needs_confirmation",
                "message": f"Matched '{to_state}' to '{match_result.state.value}' with {match_result.confidence:.0%} confidence. Please confirm.",
                "confirm_required": True,
            }

        target_state = match_result.state

        # Validate transition using adapter (includes parent/child state constraints)
        is_valid = await adapter.validate_transition(ticket_id, target_state)
        if not is_valid:
            # Check if it's a workflow violation or parent constraint violation
            workflow_valid = current_state.can_transition_to(target_state)
            valid_transitions = TicketState.valid_transitions().get(current_state, [])
            valid_values = [s.value for s in valid_transitions]

            if workflow_valid:
                # Workflow is valid, so this must be a parent constraint violation
                # Get children to determine max child state
                from ....core.models import Task

                if isinstance(ticket, Task) and ticket.children:
                    try:
                        children = await adapter.list_tasks_by_issue(ticket_id)
                        if children:
                            max_child_state = None
                            max_child_level = 0
                            for child in children:
                                child_state = child.state
                                if isinstance(child_state, str):
                                    try:
                                        child_state = TicketState(child_state)
                                    except ValueError:
                                        continue
                                child_level = child_state.completion_level()
                                if child_level > max_child_level:
                                    max_child_level = child_level
                                    max_child_state = child_state

                            return {
                                **response,
                                "status": "error",
                                "error": f"Cannot transition to '{target_state.value}': parent issue has children in higher completion states",
                                "reason": "parent_constraint_violation",
                                "max_child_state": (
                                    max_child_state.value if max_child_state else None
                                ),
                                "message": f"Cannot transition to {target_state.value}: "
                                f"parent issue has children in higher completion states (max child state: {max_child_state.value if max_child_state else 'unknown'}). "
                                f"Please update child states first.",
                                "valid_transitions": valid_values,
                            }
                    except Exception:
                        # Fallback to generic message if we can't determine child states
                        pass

                # Generic parent constraint violation message
                return {
                    **response,
                    "status": "error",
                    "error": f"Cannot transition to '{target_state.value}': parent/child state constraint violation",
                    "reason": "parent_constraint_violation",
                    "message": f"Cannot transition to {target_state.value}: "
                    f"parent issue has children in higher completion states. Please update child states first.",
                    "valid_transitions": valid_values,
                }
            else:
                # Workflow violation
                return {
                    **response,
                    "status": "error",
                    "error": f"Invalid transition from '{current_state.value}' to '{target_state.value}'",
                    "reason": "workflow_violation",
                    "valid_transitions": valid_values,
                    "message": f"Cannot transition from {current_state.value} to {target_state.value}. "
                    f"Valid transitions: {', '.join(valid_values) if valid_values else 'none (terminal state)'}",
                }

        # Update ticket state
        updated = await adapter.update(ticket_id, {"state": target_state})

        if updated is None:
            return {
                **response,
                "status": "error",
                "error": f"Failed to update ticket {ticket_id}",
            }

        # Add comment if provided and adapter supports it
        comment_added = False
        if comment and hasattr(adapter, "add_comment"):
            try:
                await adapter.add_comment(ticket_id, comment)
                comment_added = True
            except Exception:
                # Log but don't fail the transition
                comment_added = False

        # Auto project update hook (1M-315)
        # Trigger automatic project update if enabled and ticket has parent epic
        auto_update_result = None
        try:
            from pathlib import Path

            from ....automation.project_updates import AutoProjectUpdateManager
            from ....core.project_config import ConfigResolver

            # Load config
            resolver = ConfigResolver(project_path=Path.cwd())
            config_obj = resolver.load_project_config()
            config_dict = config_obj.to_dict() if config_obj else {}

            # Check if auto updates enabled
            auto_updates_mgr = AutoProjectUpdateManager(config_dict, adapter)
            if auto_updates_mgr.is_enabled():
                # Check if ticket has parent_epic
                parent_epic = (
                    updated.parent_epic if hasattr(updated, "parent_epic") else None
                )

                if parent_epic:
                    # Only trigger on configured frequency
                    update_frequency = auto_updates_mgr.get_update_frequency()
                    should_trigger = update_frequency == "on_transition"

                    # For "on_completion", only trigger if transitioned to done/closed
                    if update_frequency == "on_completion":
                        from ....core.models import TicketState as TSEnum

                        should_trigger = target_state in (TSEnum.DONE, TSEnum.CLOSED)

                    if should_trigger:
                        auto_update_result = (
                            await auto_updates_mgr.create_transition_update(
                                ticket_id=ticket_id,
                                ticket_title=updated.title or "",
                                old_state=current_state.value,
                                new_state=target_state.value,
                                parent_epic=parent_epic,
                            )
                        )
        except Exception as e:
            # Log error but don't block the transition
            import logging

            logging.getLogger(__name__).warning(
                f"Auto project update failed (non-blocking): {e}"
            )

        # Build final response
        final_response = {
            **response,
            **_build_adapter_metadata(adapter, ticket_id),
            "status": "completed",
            "ticket": updated.model_dump(),
            "previous_state": current_state.value,
            "new_state": target_state.value,
            "comment_added": comment_added,
            "message": f"Ticket {ticket_id} transitioned from {current_state.value} to {target_state.value}",
        }

        # Include auto update result if applicable
        if auto_update_result:
            final_response["auto_project_update"] = auto_update_result

        return final_response
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to transition ticket: {str(e)}",
        }


def _get_state_description(state: TicketState) -> str:
    """Get human-readable description of a state.

    Args:
        state: TicketState to describe

    Returns:
        Description string

    """
    descriptions = {
        TicketState.OPEN: "Work not yet started, in backlog",
        TicketState.IN_PROGRESS: "Work is actively being done",
        TicketState.READY: "Work complete, ready for review or testing",
        TicketState.TESTED: "Work has been tested and verified",
        TicketState.DONE: "Work is complete and accepted",
        TicketState.WAITING: "Work paused, waiting for external dependency",
        TicketState.BLOCKED: "Work blocked by an impediment",
        TicketState.CLOSED: "Ticket closed or archived (final state)",
    }
    return descriptions.get(state, "")


# Deprecated functions - kept for backward compatibility
# These will be removed in a future version


async def get_available_transitions(ticket_id: str) -> dict[str, Any]:
    """Get valid next states for ticket based on workflow state machine.

    .. deprecated::
        Use workflow(action="get_transitions", ticket_id=ticket_id) instead.
        This tool will be removed in a future version.

    Args: ticket_id (required)
    Returns: TransitionResponse with current_state, available_transitions, transition_descriptions, is_terminal
    See: docs/ticket-workflows.md#valid-state-transitions
    """
    import warnings

    warnings.warn(
        "get_available_transitions is deprecated. Use workflow(action='get_transitions', ticket_id=ticket_id) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await _handle_get_transitions(ticket_id)


async def ticket_transition(
    ticket_id: str,
    to_state: str,
    comment: str | None = None,
    auto_confirm: bool = True,
) -> dict[str, Any]:
    """Move ticket through workflow with validation and semantic matching (natural language support).

    .. deprecated::
        Use workflow(action="transition", ticket_id=ticket_id, to_state=to_state, ...) instead.
        This tool will be removed in a future version.

    Args: ticket_id (required), to_state (supports natural language like "working on it"), comment (optional), auto_confirm (default: True)
    Returns: TransitionResponse with status, ticket, previous_state, new_state, matched_state, confidence, suggestions (if ambiguous)
    See: docs/ticket-workflows.md#semantic-state-matching, docs/ticket-workflows.md#valid-state-transitions
    """
    import warnings

    warnings.warn(
        "ticket_transition is deprecated. Use workflow(action='transition', ticket_id=ticket_id, to_state=to_state, ...) instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await _handle_transition(ticket_id, to_state, comment, auto_confirm)
