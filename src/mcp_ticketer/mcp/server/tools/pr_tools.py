"""Pull request integration tools for tickets.

This module implements tools for linking tickets with pull requests and
creating PRs from tickets. Note that PR functionality may not be available
in all adapters.
"""

from typing import Any

from ..server_sdk import get_adapter


async def ticket_create_pr(
    ticket_id: str,
    title: str,
    description: str = "",
    source_branch: str | None = None,
    target_branch: str = "main",
) -> dict[str, Any]:
    """Create a pull request linked to a ticket.

    Creates a new pull request and automatically links it to the specified
    ticket. This functionality may not be available in all adapters.

    Args:
        ticket_id: Unique identifier of the ticket to link the PR to
        title: Pull request title
        description: Pull request description
        source_branch: Source branch for the PR (if not specified, may use ticket ID)
        target_branch: Target branch for the PR (default: main)

    Returns:
        Created PR details and link information, or error information

    """
    try:
        adapter = get_adapter()

        # Check if adapter supports PR operations
        if not hasattr(adapter, "create_pull_request"):
            return {
                "status": "error",
                "error": f"Pull request creation not supported by {type(adapter).__name__} adapter",
                "ticket_id": ticket_id,
            }

        # Read ticket to validate it exists
        ticket = await adapter.read(ticket_id)
        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Use ticket ID as source branch if not specified
        if source_branch is None:
            source_branch = f"feature/{ticket_id}"

        # Create PR via adapter
        pr_data = await adapter.create_pull_request(
            ticket_id=ticket_id,
            title=title,
            description=description,
            source_branch=source_branch,
            target_branch=target_branch,
        )

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "pull_request": pr_data,
        }

    except AttributeError:
        return {
            "status": "error",
            "error": "Pull request creation not supported by this adapter",
            "ticket_id": ticket_id,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create pull request: {str(e)}",
            "ticket_id": ticket_id,
        }


async def ticket_link_pr(
    ticket_id: str,
    pr_url: str,
) -> dict[str, Any]:
    """Link an existing pull request to a ticket.

    Associates an existing pull request (identified by URL) with a ticket.
    This is typically done by adding the PR URL to the ticket's metadata
    or as a comment.

    Args:
        ticket_id: Unique identifier of the ticket
        pr_url: URL of the pull request to link

    Returns:
        Link confirmation and updated ticket details, or error information

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

        # Check if adapter has specialized PR linking
        if hasattr(adapter, "link_pull_request"):
            result = await adapter.link_pull_request(ticket_id=ticket_id, pr_url=pr_url)
            return {
                "status": "completed",
                "ticket_id": ticket_id,
                "pr_url": pr_url,
                "result": result,
            }

        # Fallback: Add PR link as comment
        from ....core.models import Comment

        comment = Comment(
            ticket_id=ticket_id,
            content=f"Pull Request: {pr_url}",
        )

        created_comment = await adapter.add_comment(comment)

        return {
            "status": "completed",
            "ticket_id": ticket_id,
            "pr_url": pr_url,
            "method": "comment",
            "comment": created_comment.model_dump(),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to link pull request: {str(e)}",
            "ticket_id": ticket_id,
        }
