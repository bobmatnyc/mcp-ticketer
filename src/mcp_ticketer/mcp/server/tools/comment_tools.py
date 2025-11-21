"""Comment management tools for tickets.

This module implements tools for adding and retrieving comments on tickets.
"""

import logging
from typing import Any

from ....core.models import Comment
from ....core.url_parser import is_url
from ..server_sdk import get_adapter, get_router, has_router, mcp


@mcp.tool()
async def ticket_comment(
    ticket_id: str,
    operation: str,
    text: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """Add or list comments on a ticket using ID or URL.

    This tool supports two operations:
    - 'add': Add a new comment to a ticket (requires 'text' parameter)
    - 'list': Retrieve comments from a ticket (supports pagination)

    Supports both plain ticket IDs and full URLs from multiple platforms.
    See ticket_read for supported URL formats.

    Args:
        ticket_id: Ticket ID or URL
        operation: Operation to perform - must be 'add' or 'list'
        text: Comment text (required when operation='add')
        limit: Maximum number of comments to return (used when operation='list', default: 10)
        offset: Number of comments to skip for pagination (used when operation='list', default: 0)

    Returns:
        Comment data or list of comments, or error information

    """
    try:
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
                ticket_id=ticket_id,  # Will be normalized by router if URL
                content=text,
            )

            # Route to appropriate adapter
            if is_url(ticket_id) and has_router():
                router = get_router()
                logging.info(f"Routing add_comment for URL: {ticket_id}")
                created = await router.route_add_comment(ticket_id, comment)
            else:
                adapter = get_adapter()
                created = await adapter.add_comment(comment)

            return {
                "status": "completed",
                "operation": "add",
                "comment": created.model_dump(),
                "platform_detected": "url" if is_url(ticket_id) else "default",
            }

        else:  # operation == "list"
            # List comments operation
            # Route to appropriate adapter
            if is_url(ticket_id) and has_router():
                router = get_router()
                logging.info(f"Routing get_comments for URL: {ticket_id}")
                comments = await router.route_get_comments(
                    ticket_id, limit=limit, offset=offset
                )
            else:
                adapter = get_adapter()
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
                "platform_detected": "url" if is_url(ticket_id) else "default",
            }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Comment operation failed: {str(e)}",
        }
