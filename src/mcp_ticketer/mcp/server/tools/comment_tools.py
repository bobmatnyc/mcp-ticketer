"""Comment management tools for tickets.

This module implements tools for adding and retrieving comments on tickets.

Version 2.0.0 changes:
- Removed @mcp.tool() decorator from ticket_comment (consolidated into ticket() tool)
- ticket_comment retained as internal helper for backward compatibility
- Use ticket(action="add_comment"|"list_comments") instead
"""

import logging
from typing import Any

from ....core.adapter import BaseAdapter
from ....core.models import Comment
from ....core.url_parser import is_url
from ..server_sdk import get_adapter, get_router, has_router


def _build_adapter_metadata(
    adapter: BaseAdapter,
    ticket_id: str | None = None,
    is_routed: bool = False,
) -> dict[str, Any]:
    """Build adapter metadata for MCP responses.

    Args:
        adapter: The adapter that handled the operation
        ticket_id: Optional ticket ID to include in metadata
        is_routed: Whether this was routed via URL detection

    Returns:
        Dictionary with adapter metadata fields

    """
    metadata = {
        "adapter": adapter.adapter_type,
        "adapter_name": adapter.adapter_display_name,
    }

    if ticket_id:
        metadata["ticket_id"] = ticket_id

    if is_routed:
        metadata["routed_from_url"] = True

    return metadata


async def ticket_comment(
    ticket_id: str,
    operation: str,
    text: str | None = None,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """Add or list comments on a ticket using ID or URL.

    .. deprecated:: 2.0.0
        Use :func:`ticket` with ``action='add_comment'`` or ``action='list_comments'`` instead.
        This function is retained for backward compatibility but is no longer exposed as an MCP tool.

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

    Migration:
        - ticket_comment(operation="add", text=...) → ticket(action="add_comment", comment_text=...)
        - ticket_comment(operation="list", limit=..., offset=...) → ticket(action="list_comments", comment_limit=..., comment_offset=...)

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
            is_routed = False
            if is_url(ticket_id) and has_router():
                router = get_router()
                logging.info(f"Routing add_comment for URL: {ticket_id}")
                created = await router.route_add_comment(ticket_id, comment)
                is_routed = True
                normalized_id, _, _ = router._normalize_ticket_id(ticket_id)
                adapter = router._get_adapter(
                    router._detect_adapter_from_url(ticket_id)
                )
            else:
                adapter = get_adapter()
                created = await adapter.add_comment(comment)

            return {
                "status": "completed",
                **_build_adapter_metadata(adapter, created.ticket_id, is_routed),
                "operation": "add",
                "comment": created.model_dump(),
            }

        else:  # operation == "list"
            # List comments operation
            # Route to appropriate adapter
            is_routed = False
            if is_url(ticket_id) and has_router():
                router = get_router()
                logging.info(f"Routing get_comments for URL: {ticket_id}")
                comments = await router.route_get_comments(
                    ticket_id, limit=limit, offset=offset
                )
                is_routed = True
                normalized_id, _, _ = router._normalize_ticket_id(ticket_id)
                adapter = router._get_adapter(
                    router._detect_adapter_from_url(ticket_id)
                )
            else:
                adapter = get_adapter()
                comments = await adapter.get_comments(
                    ticket_id=ticket_id, limit=limit, offset=offset
                )

            return {
                "status": "completed",
                **_build_adapter_metadata(adapter, ticket_id, is_routed),
                "operation": "list",
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
