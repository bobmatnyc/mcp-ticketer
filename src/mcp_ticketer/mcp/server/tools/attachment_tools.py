"""Attachment management tools for tickets.

This module implements tools for attaching files to tickets and retrieving
attachment information. Note that file attachment functionality may not be
available in all adapters.
"""

import mimetypes
from pathlib import Path
from typing import Any

from ....core.models import Comment, TicketType
from ..server_sdk import get_adapter, mcp


async def _handle_attach(
    ticket_id: str,
    file_path: str,
    description: str = "",
) -> dict[str, Any]:
    """Handle file attachment to a ticket.

    Args:
        ticket_id: Unique identifier of the ticket
        file_path: Path to the file to attach
        description: Optional description of the attachment

    Returns:
        Attachment details including URL or ID, or error information
    """
    try:
        adapter = get_adapter()

        # Read ticket to validate it exists and determine type
        ticket = await adapter.read(ticket_id)
        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Check if file exists
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                "status": "error",
                "error": f"File not found: {file_path}",
                "ticket_id": ticket_id,
            }

        # Try Linear-specific upload methods first (most advanced)
        if hasattr(adapter, "upload_file") and hasattr(adapter, "attach_file_to_issue"):
            try:
                # Determine MIME type
                mime_type = mimetypes.guess_type(file_path)[0]

                # Upload file to Linear's storage
                file_url = await adapter.upload_file(file_path, mime_type)

                # Determine ticket type and attach accordingly
                ticket_type = getattr(ticket, "ticket_type", None)
                filename = file_path_obj.name

                if ticket_type == TicketType.EPIC and hasattr(
                    adapter, "attach_file_to_epic"
                ):
                    # Attach to epic (project)
                    result = await adapter.attach_file_to_epic(
                        epic_id=ticket_id,
                        file_url=file_url,
                        title=description or filename,
                        subtitle=f"Uploaded file: {filename}",
                    )
                else:
                    # Attach to issue/task
                    result = await adapter.attach_file_to_issue(
                        issue_id=ticket_id,
                        file_url=file_url,
                        title=description or filename,
                        subtitle=f"Uploaded file: {filename}",
                        comment_body=description if description else None,
                    )

                return {
                    "status": "completed",
                    "ticket_id": ticket_id,
                    "method": "linear_native_upload",
                    "file_url": file_url,
                    "attachment": result,
                }
            except Exception:
                # Fall through to legacy method if Linear-specific upload fails
                pass

        # Try legacy add_attachment method
        if hasattr(adapter, "add_attachment"):
            attachment = await adapter.add_attachment(
                ticket_id=ticket_id, file_path=file_path, description=description
            )

            return {
                "status": "completed",
                "ticket_id": ticket_id,
                "method": "adapter_native",
                "attachment": attachment,
            }

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


async def _handle_list_attachments(ticket_id: str) -> dict[str, Any]:
    """Handle listing attachments for a ticket.

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
        attachments = await adapter.get_attachments(ticket_id)

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


@mcp.tool(
    description="Manage ticket attachments - add files to tickets, list attachments, manage file uploads and downloads (where supported by platform)"
)
async def attachment(
    action: str,
    ticket_id: str,
    file_path: str | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Unified attachment management for tickets.

    Handles file attachments and attachment listing through a single interface.
    Note that file attachment functionality may not be available in all adapters.

    Args:
        action: Operation to perform. Valid values:
            - "attach": Attach a file to a ticket (requires file_path)
            - "list": Get all attachments for a ticket
        ticket_id: Unique identifier of the ticket (required)
        file_path: Path to file to attach (required for attach action)
        description: File description (optional for attach action)

    Returns:
        Results specific to action with status and relevant data

    Raises:
        ValueError: If action is invalid or required parameters missing

    Examples:
        # Attach file
        attachment(action="attach", ticket_id="PROJ-123", file_path="/path/to/file.pdf")

        # Attach with description
        attachment(action="attach", ticket_id="PROJ-123",
                  file_path="/path/to/doc.pdf", description="Design mockups")

        # List attachments
        attachment(action="list", ticket_id="PROJ-123")

    Migration from old tools:
        - ticket_attach(ticket_id, file_path, description)
          → attachment(action="attach", ticket_id=ticket_id, file_path=file_path, description=description)
        - ticket_attachments(ticket_id)
          → attachment(action="list", ticket_id=ticket_id)

    See: docs/mcp-api-reference.md for detailed response formats
    """
    # Validate action
    valid_actions = {"attach", "list"}
    if action not in valid_actions:
        return {
            "status": "error",
            "error": f"Invalid action '{action}'. Must be one of: {', '.join(sorted(valid_actions))}",
        }

    # Route to appropriate handler
    if action == "attach":
        # Validate required parameters
        if not file_path:
            return {
                "status": "error",
                "error": "file_path is required for 'attach' action",
            }
        return await _handle_attach(ticket_id, file_path, description)

    elif action == "list":
        return await _handle_list_attachments(ticket_id)

    # Should never reach here due to validation above
    return {
        "status": "error",
        "error": f"Unhandled action: {action}",
    }
