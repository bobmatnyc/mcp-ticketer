"""Comment management tools for tickets.

This module implements tools for adding and retrieving comments on tickets.
"""

from typing import Any

from ....core.models import Comment
from ..server_sdk import get_adapter, mcp


@mcp.tool()
async def ticket_comment(
    ticket_id: str,
    operation: str,
    text: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """Add or list comments on a ticket.

    This tool supports two operations:
    - 'add': Add a new comment to a ticket (requires 'text' parameter)
    - 'list': Retrieve comments from a ticket (supports pagination)

    Args:
        ticket_id: Unique identifier of the ticket
        operation: Operation to perform - must be 'add' or 'list'
        text: Comment text (required when operation='add')
        limit: Maximum number of comments to return (used when operation='list', default: 10)
        offset: Number of comments to skip for pagination (used when operation='list', default: 0)

    Returns:
        Comment data or list of comments, or error information

    """
    try:
        adapter = get_adapter()

        # Validate operation
        if operation not in ["add", "list"]:
            return {
                "status": "error",
                "error": f"Invalid operation '{operation}'. Must be 'add' or 'list'",
            }

        if operation == "add":
            # Add comment operation
            if not text:
                return {
                    "status": "error",
                    "error": "Parameter 'text' is required when operation='add'",
                }

            # Create comment object
            comment = Comment(
                ticket_id=ticket_id,
                content=text,
            )

            # Add comment via adapter
            created = await adapter.add_comment(comment)

            return {
                "status": "completed",
                "operation": "add",
                "comment": created.model_dump(),
            }

        else:  # operation == "list"
            # List comments operation
            comments = await adapter.get_comments(
                ticket_id=ticket_id, limit=limit, offset=offset
            )

            return {
                "status": "completed",
                "operation": "list",
                "ticket_id": ticket_id,
                "comments": [comment.model_dump() for comment in comments],
                "count": len(comments),
                "limit": limit,
                "offset": offset,
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Comment operation failed: {str(e)}",
        }
