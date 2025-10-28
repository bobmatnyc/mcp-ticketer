"""Basic CRUD operations for tickets.

This module implements the core create, read, update, delete, and list
operations for tickets using the FastMCP SDK.
"""

from typing import Any

from ....core.models import Priority, Task, TicketState
from ..server_sdk import get_adapter, mcp


@mcp.tool()
async def ticket_create(
    title: str,
    description: str = "",
    priority: str = "medium",
    tags: list[str] | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    """Create a new ticket with specified details.

    Args:
        title: Ticket title (required)
        description: Detailed description of the ticket
        priority: Priority level - must be one of: low, medium, high, critical
        tags: List of tags to categorize the ticket
        assignee: User ID or email to assign the ticket to

    Returns:
        Created ticket details including ID and metadata, or error information

    """
    try:
        adapter = get_adapter()

        # Validate and convert priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            return {
                "status": "error",
                "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
            }

        # Create task object
        task = Task(
            title=title,
            description=description or "",
            priority=priority_enum,
            tags=tags or [],
            assignee=assignee,
        )

        # Create via adapter
        created = await adapter.create(task)

        return {
            "status": "completed",
            "ticket": created.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create ticket: {str(e)}",
        }


@mcp.tool()
async def ticket_read(ticket_id: str) -> dict[str, Any]:
    """Read a ticket by its ID.

    Args:
        ticket_id: Unique identifier of the ticket to retrieve

    Returns:
        Ticket details if found, or error information

    """
    try:
        adapter = get_adapter()
        ticket = await adapter.read(ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        return {
            "status": "completed",
            "ticket": ticket.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to read ticket: {str(e)}",
        }


@mcp.tool()
async def ticket_update(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignee: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update an existing ticket.

    Args:
        ticket_id: Unique identifier of the ticket to update
        title: New title for the ticket
        description: New description for the ticket
        priority: New priority - must be one of: low, medium, high, critical
        state: New state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        assignee: User ID or email to assign the ticket to
        tags: New list of tags (replaces existing tags)

    Returns:
        Updated ticket details, or error information

    """
    try:
        adapter = get_adapter()

        # Build updates dictionary with only provided fields
        updates: dict[str, Any] = {}

        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if assignee is not None:
            updates["assignee"] = assignee
        if tags is not None:
            updates["tags"] = tags

        # Validate and convert priority if provided
        if priority is not None:
            try:
                updates["priority"] = Priority(priority.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
                }

        # Validate and convert state if provided
        if state is not None:
            try:
                updates["state"] = TicketState(state.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid state '{state}'. Must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked",
                }

        # Update via adapter
        updated = await adapter.update(ticket_id, updates)

        if updated is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found or update failed",
            }

        return {
            "status": "completed",
            "ticket": updated.model_dump(),
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to update ticket: {str(e)}",
        }


@mcp.tool()
async def ticket_delete(ticket_id: str) -> dict[str, Any]:
    """Delete a ticket by its ID.

    Args:
        ticket_id: Unique identifier of the ticket to delete

    Returns:
        Success confirmation or error information

    """
    try:
        adapter = get_adapter()
        success = await adapter.delete(ticket_id)

        if not success:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found or delete failed",
            }

        return {
            "status": "completed",
            "message": f"Ticket {ticket_id} deleted successfully",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to delete ticket: {str(e)}",
        }


@mcp.tool()
async def ticket_list(
    limit: int = 10,
    offset: int = 0,
    state: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
) -> dict[str, Any]:
    """List tickets with pagination and optional filters.

    Args:
        limit: Maximum number of tickets to return (default: 10)
        offset: Number of tickets to skip for pagination (default: 0)
        state: Filter by state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        priority: Filter by priority - must be one of: low, medium, high, critical
        assignee: Filter by assigned user ID or email

    Returns:
        List of tickets matching criteria, or error information

    """
    try:
        adapter = get_adapter()

        # Build filters dictionary
        filters: dict[str, Any] = {}

        if state is not None:
            try:
                filters["state"] = TicketState(state.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid state '{state}'. Must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked",
                }

        if priority is not None:
            try:
                filters["priority"] = Priority(priority.lower())
            except ValueError:
                return {
                    "status": "error",
                    "error": f"Invalid priority '{priority}'. Must be one of: low, medium, high, critical",
                }

        if assignee is not None:
            filters["assignee"] = assignee

        # List tickets via adapter
        tickets = await adapter.list(
            limit=limit, offset=offset, filters=filters if filters else None
        )

        return {
            "status": "completed",
            "tickets": [ticket.model_dump() for ticket in tickets],
            "count": len(tickets),
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list tickets: {str(e)}",
        }
