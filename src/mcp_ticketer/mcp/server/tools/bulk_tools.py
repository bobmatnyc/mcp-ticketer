"""Bulk operations for creating and updating multiple tickets.

This module implements tools for batch operations on tickets to improve
efficiency when working with multiple items.

Features:
- ticket_bulk: Unified interface for all bulk operations (create, update)

All tools follow the MCP response pattern:
    {
        "status": "completed" | "error",
        "summary": {"total": N, "created": N, "updated": N, "failed": N},
        "results": {...}
    }
"""

from typing import Any

from ....core.models import Priority, Task, TicketState, TicketType
from ..server_sdk import get_adapter, mcp


@mcp.tool(
    description="Bulk ticket operations - update multiple tickets at once (state transitions, priority changes, assignments, tag management)"
)
async def ticket_bulk(
    action: str,
    tickets: list[dict[str, Any]] | None = None,
    updates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Unified bulk ticket operations tool.

    Performs bulk create or update operations on tickets through a single
    interface.

    Args:
        action: Operation to perform. Valid values:
            - "create": Create multiple new tickets
            - "update": Update multiple existing tickets
        tickets: List of ticket dicts for bulk create (required if action="create")
                Each dict should contain at minimum 'title', with optional fields:
                description, priority, tags, assignee, ticket_type, parent_epic, parent_issue
        updates: List of update dicts for bulk update (required if action="update")
                Each dict must contain 'ticket_id' and at least one field to update.
                Valid update fields: title, description, priority, state, assignee, tags

    Returns:
        Results dictionary containing:
        - status: "completed" or "error"
        - summary: Statistics (total, created/updated, failed)
        - results: Detailed results for each operation

    Raises:
        ValueError: If action is invalid or required parameters missing

    Examples:
        # Bulk create
        result = await ticket_bulk(
            action="create",
            tickets=[
                {"title": "Bug 1", "priority": "high", "description": "Fix login"},
                {"title": "Bug 2", "priority": "medium", "tags": ["backend"]}
            ]
        )

        # Bulk update
        result = await ticket_bulk(
            action="update",
            updates=[
                {"ticket_id": "PROJ-123", "state": "done", "priority": "low"},
                {"ticket_id": "PROJ-456", "assignee": "user@example.com"}
            ]
        )

    See: docs/mcp-api-reference.md for detailed response formats
    """
    action_lower = action.lower()

    # Route to appropriate handler based on action
    if action_lower == "create":
        if tickets is None:
            return {
                "status": "error",
                "error": "tickets parameter required for action='create'",
                "hint": "Use ticket_bulk(action='create', tickets=[...])",
            }
        # Inline implementation of bulk create
        try:
            adapter = get_adapter()

            if not tickets:
                return {
                    "status": "error",
                    "error": "No tickets provided for bulk creation",
                }

            results: dict[str, list[Any]] = {
                "created": [],
                "failed": [],
            }

            for i, ticket_data in enumerate(tickets):
                try:
                    # Validate required fields
                    if "title" not in ticket_data:
                        results["failed"].append(
                            {
                                "index": i,
                                "error": "Missing required field: title",
                                "data": ticket_data,
                            }
                        )
                        continue

                    # Parse priority if provided
                    priority = Priority.MEDIUM  # Default
                    if "priority" in ticket_data:
                        try:
                            priority = Priority(ticket_data["priority"].lower())
                        except ValueError:
                            results["failed"].append(
                                {
                                    "index": i,
                                    "error": f"Invalid priority: {ticket_data['priority']}",
                                    "data": ticket_data,
                                }
                            )
                            continue

                    # Parse ticket type if provided
                    ticket_type = TicketType.ISSUE  # Default
                    if "ticket_type" in ticket_data:
                        try:
                            ticket_type = TicketType(ticket_data["ticket_type"].lower())
                        except ValueError:
                            results["failed"].append(
                                {
                                    "index": i,
                                    "error": f"Invalid ticket_type: {ticket_data['ticket_type']}",
                                    "data": ticket_data,
                                }
                            )
                            continue

                    # Create task object
                    task = Task(
                        title=ticket_data["title"],
                        description=ticket_data.get("description", ""),
                        priority=priority,
                        ticket_type=ticket_type,
                        tags=ticket_data.get("tags", []),
                        assignee=ticket_data.get("assignee"),
                        parent_epic=ticket_data.get("parent_epic"),
                        parent_issue=ticket_data.get("parent_issue"),
                    )

                    # Create via adapter
                    created = await adapter.create(task)
                    results["created"].append(
                        {
                            "index": i,
                            "ticket": created.model_dump(),
                        }
                    )

                except Exception as e:
                    results["failed"].append(
                        {
                            "index": i,
                            "error": str(e),
                            "data": ticket_data,
                        }
                    )

            return {
                "status": "completed",
                "summary": {
                    "total": len(tickets),
                    "created": len(results["created"]),
                    "failed": len(results["failed"]),
                },
                "results": results,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Bulk creation failed: {str(e)}",
            }

    elif action_lower == "update":
        if updates is None:
            return {
                "status": "error",
                "error": "updates parameter required for action='update'",
                "hint": "Use ticket_bulk(action='update', updates=[...])",
            }
        # Inline implementation of bulk update
        try:
            adapter = get_adapter()

            if not updates:
                return {
                    "status": "error",
                    "error": "No updates provided for bulk operation",
                }

            results: dict[str, list[Any]] = {
                "updated": [],
                "failed": [],
            }

            for i, update_data in enumerate(updates):
                try:
                    # Validate required fields
                    if "ticket_id" not in update_data:
                        results["failed"].append(
                            {
                                "index": i,
                                "error": "Missing required field: ticket_id",
                                "data": update_data,
                            }
                        )
                        continue

                    ticket_id = update_data["ticket_id"]

                    # Build update dict
                    update_fields: dict[str, Any] = {}

                    if "title" in update_data:
                        update_fields["title"] = update_data["title"]
                    if "description" in update_data:
                        update_fields["description"] = update_data["description"]
                    if "assignee" in update_data:
                        update_fields["assignee"] = update_data["assignee"]
                    if "tags" in update_data:
                        update_fields["tags"] = update_data["tags"]

                    # Parse priority if provided
                    if "priority" in update_data:
                        try:
                            update_fields["priority"] = Priority(
                                update_data["priority"].lower()
                            )
                        except ValueError:
                            results["failed"].append(
                                {
                                    "index": i,
                                    "error": f"Invalid priority: {update_data['priority']}",
                                    "data": update_data,
                                }
                            )
                            continue

                    # Parse state if provided
                    if "state" in update_data:
                        try:
                            update_fields["state"] = TicketState(
                                update_data["state"].lower()
                            )
                        except ValueError:
                            results["failed"].append(
                                {
                                    "index": i,
                                    "error": f"Invalid state: {update_data['state']}",
                                    "data": update_data,
                                }
                            )
                            continue

                    if not update_fields:
                        results["failed"].append(
                            {
                                "index": i,
                                "error": "No valid update fields provided",
                                "data": update_data,
                            }
                        )
                        continue

                    # Update via adapter
                    updated = await adapter.update(ticket_id, update_fields)
                    if updated is None:
                        results["failed"].append(
                            {
                                "index": i,
                                "error": f"Ticket {ticket_id} not found or update failed",
                                "data": update_data,
                            }
                        )
                    else:
                        results["updated"].append(
                            {
                                "index": i,
                                "ticket": updated.model_dump(),
                            }
                        )

                except Exception as e:
                    results["failed"].append(
                        {
                            "index": i,
                            "error": str(e),
                            "data": update_data,
                        }
                    )

            return {
                "status": "completed",
                "summary": {
                    "total": len(updates),
                    "updated": len(results["updated"]),
                    "failed": len(results["failed"]),
                },
                "results": results,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Bulk update failed: {str(e)}",
            }

    else:
        valid_actions = ["create", "update"]
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(valid_actions)}",
            "valid_actions": valid_actions,
            "hint": "Use ticket_bulk(action='create'|'update', ...)",
        }
