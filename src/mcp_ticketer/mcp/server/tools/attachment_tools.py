"""Attachment management tools for tickets.

This module implements tools for attaching files to tickets and retrieving
attachment information. Note that file attachment functionality may not be
available in all adapters.
"""

from typing import Any

from ....core.models import Comment
from ..server_sdk import get_adapter, mcp


@mcp.tool()
async def ticket_attach(
    ticket_id: str,
    file_path: str,
    description: str = "",
) -> dict[str, Any]:  # Keep as dict for MCP compatibility
    """Attach a file to a ticket.

    Uploads a file and associates it with the specified ticket. This
    functionality may not be available in all adapters.

    Args:
        ticket_id: Unique identifier of the ticket
        file_path: Path to the file to attach
        description: Optional description of the attachment

    Returns:
        Attachment details including URL or ID, or error information

    """
    try:
        adapter = get_adapter()

        # Read ticket to validate it exists
        ticket = await adapter.read(ticket_id)
        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Check if adapter supports attachments
        if not hasattr(adapter, "add_attachment"):
            return {
                "status": "error",
                "error": f"File attachments not supported by {type(adapter).__name__} adapter",
                "ticket_id": ticket_id,
                "note": "Consider using ticket_comment to add a reference to the file location",
            }

        # Add attachment via adapter
        attachment = await adapter.add_attachment(  # type: ignore
            ticket_id=ticket_id, file_path=file_path, description=description
        )

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "attachment": attachment,
        }

    except AttributeError:
        # Fallback: Add file reference as comment
        comment_text = f"Attachment: {file_path}"
        if description:
            comment_text += f"\nDescription: {description}"

        comment = Comment(
            ticket_id=ticket_id,
            content=comment_text,
        )

        created_comment = await adapter.add_comment(comment)

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "method": "comment_reference",
            "file_path": file_path,
            "comment": created_comment.model_dump(),
            "note": "Adapter does not support direct file uploads. File reference added as comment.",
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {file_path}",
            "ticket_id": ticket_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to attach file: {str(e)}",
            "ticket_id": ticket_id,
        }


@mcp.tool()
async def ticket_attachments(
    ticket_id: str,
) -> dict[str, Any]:  # Keep as dict for MCP compatibility
    """Get all attachments for a ticket.

    Retrieves a list of all files attached to the specified ticket.
    This functionality may not be available in all adapters.

    Args:
        ticket_id: Unique identifier of the ticket

    Returns:
        List of attachments with metadata, or error information

    """
    try:
        adapter = get_adapter()

        # Read ticket to validate it exists
        ticket = await adapter.read(ticket_id)
        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Check if adapter supports attachments
        if not hasattr(adapter, "get_attachments"):
            return {
                "status": "error",
                "error": f"Attachment retrieval not supported by {type(adapter).__name__} adapter",
                "ticket_id": ticket_id,
                "note": "Check ticket comments for file references",
            }

        # Get attachments via adapter
        attachments = await adapter.get_attachments(ticket_id)  # type: ignore

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "attachments": attachments,
            "count": len(attachments) if isinstance(attachments, list) else 0,
        }

    except AttributeError:
        # Fallback: Check comments for attachment references
        comments = await adapter.get_comments(ticket_id=ticket_id, limit=100)

        # Look for comments that reference files
        attachment_refs = []
        for comment in comments:
            content = comment.content or ""
            if content.startswith("Attachment:") or "file://" in content:
                attachment_refs.append(
                    {
                        "type": "comment_reference",
                        "comment_id": comment.id,
                        "content": content,
                        "created_at": comment.created_at,
                    }
                )

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "method": "comment_references",
            "attachments": attachment_refs,
            "count": len(attachment_refs),
            "note": "Adapter does not support direct attachments. Showing file references from comments.",
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get attachments: {str(e)}",
            "ticket_id": ticket_id,
        }
