"""Basic CRUD operations for tickets.

This module implements the core create, read, update, delete, and list
operations for tickets using the FastMCP SDK.
"""

import logging
from pathlib import Path
from typing import Any

from ....core.models import Priority, Task, TicketState
from ....core.project_config import ConfigResolver, TicketerConfig
from ....core.session_state import SessionStateManager
from ..server_sdk import get_adapter, mcp


async def detect_and_apply_labels(
    adapter: Any,
    ticket_title: str,
    ticket_description: str,
    existing_labels: list[str] | None = None,
) -> list[str]:
    """Detect and suggest labels/tags based on ticket content.

    This function analyzes the ticket title and description to automatically
    detect relevant labels/tags from the adapter's available labels.

    Args:
        adapter: The ticket adapter instance
        ticket_title: Ticket title text
        ticket_description: Ticket description text
        existing_labels: Labels already specified by user (optional)

    Returns:
        List of label/tag identifiers to apply (combines auto-detected + user-specified)

    """
    # Get available labels from adapter
    available_labels = []
    try:
        if hasattr(adapter, "list_labels"):
            available_labels = await adapter.list_labels()
        elif hasattr(adapter, "get_labels"):
            available_labels = await adapter.get_labels()
    except Exception:
        # Adapter doesn't support labels or listing failed - return user labels only
        return existing_labels or []

    if not available_labels:
        return existing_labels or []

    # Combine title and description for matching (lowercase for case-insensitive matching)
    content = f"{ticket_title} {ticket_description or ''}".lower()

    # Common label keyword patterns
    label_keywords = {
        "bug": ["bug", "error", "broken", "crash", "fix", "issue", "defect"],
        "feature": ["feature", "add", "new", "implement", "create", "enhancement"],
        "improvement": [
            "enhance",
            "improve",
            "update",
            "upgrade",
            "refactor",
            "optimize",
        ],
        "documentation": ["doc", "documentation", "readme", "guide", "manual"],
        "test": ["test", "testing", "qa", "validation", "verify"],
        "security": ["security", "vulnerability", "auth", "permission", "exploit"],
        "performance": ["performance", "slow", "optimize", "speed", "latency"],
        "ui": ["ui", "ux", "interface", "design", "layout", "frontend"],
        "api": ["api", "endpoint", "rest", "graphql", "backend"],
        "backend": ["backend", "server", "database", "storage"],
        "frontend": ["frontend", "client", "web", "react", "vue"],
        "critical": ["critical", "urgent", "emergency", "blocker"],
        "high-priority": ["urgent", "asap", "important", "critical"],
    }

    # Match labels against content
    matched_labels = []

    for label in available_labels:
        # Extract label name (handle both dict and string formats)
        if isinstance(label, dict):
            label_name = label.get("name", "")
            label_id = label.get("id", label_name)
        else:
            label_name = str(label)
            label_id = label_name

        label_name_lower = label_name.lower()

        # Direct match: label name appears in content
        if label_name_lower in content:
            if label_id not in matched_labels:
                matched_labels.append(label_id)
            continue

        # Keyword match: check if label matches any keyword category
        for keyword_category, keywords in label_keywords.items():
            # Check if label name relates to the category
            if (
                keyword_category in label_name_lower
                or label_name_lower in keyword_category
            ):
                # Check if any keyword from this category appears in content
                if any(kw in content for kw in keywords):
                    if label_id not in matched_labels:
                        matched_labels.append(label_id)
                    break

    # Combine user-specified labels with auto-detected ones
    final_labels = list(existing_labels or [])
    for label in matched_labels:
        if label not in final_labels:
            final_labels.append(label)

    return final_labels


@mcp.tool()
async def ticket_create(
    title: str,
    description: str = "",
    priority: str = "medium",
    tags: list[str] | None = None,
    assignee: str | None = None,
    parent_epic: str | None = None,
    auto_detect_labels: bool = True,
) -> dict[str, Any]:
    """Create a new ticket with automatic label/tag detection.

    This tool automatically scans available labels/tags and intelligently
    applies relevant ones based on the ticket title and description.

    Label Detection:
    - Scans all available labels in the configured adapter
    - Matches labels based on keywords in title/description
    - Combines auto-detected labels with user-specified ones
    - Can be disabled by setting auto_detect_labels=false

    Common label patterns detected:
    - bug, feature, improvement, documentation
    - test, security, performance
    - ui, api, backend, frontend

    Args:
        title: Ticket title (required)
        description: Detailed description of the ticket
        priority: Priority level - must be one of: low, medium, high, critical
        tags: List of tags to categorize the ticket (auto-detection adds to these)
        assignee: User ID or email to assign the ticket to
        parent_epic: Parent epic/project ID to assign this ticket to (optional)
        auto_detect_labels: Automatically detect and apply relevant labels (default: True)

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

        # Apply configuration defaults if values not provided
        resolver = ConfigResolver(project_path=Path.cwd())
        config = resolver.load_project_config() or TicketerConfig()

        # Session ticket integration (NEW)
        session_manager = SessionStateManager(project_path=Path.cwd())
        session_state = session_manager.load_session()

        # Check if we should prompt for ticket association
        if parent_epic is None and not session_state.ticket_opted_out:
            if session_state.current_ticket:
                # Use session ticket as parent_epic
                final_parent_epic = session_state.current_ticket
                logging.info(
                    f"Using session ticket as parent_epic: {final_parent_epic}"
                )
            else:
                # No session ticket and user hasn't opted out - provide guidance
                return {
                    "status": "error",
                    "requires_ticket_association": True,
                    "guidance": (
                        "⚠️  No ticket association found for this work session.\n\n"
                        "It's recommended to associate your work with a ticket for proper tracking.\n\n"
                        "**Options**:\n"
                        "1. Associate with a ticket: attach_ticket(action='set', ticket_id='PROJ-123')\n"
                        "2. Skip for this session: attach_ticket(action='none')\n"
                        "3. Provide parent_epic directly: ticket_create(..., parent_epic='PROJ-123')\n\n"
                        "After associating, run ticket_create again to create the ticket."
                    ),
                    "session_id": session_state.session_id,
                }

        # Default user/assignee
        final_assignee = assignee
        if final_assignee is None and config.default_user:
            final_assignee = config.default_user
            logging.debug(f"Using default assignee from config: {final_assignee}")

        # Default project/epic (if not set by session)
        if "final_parent_epic" not in locals():
            final_parent_epic = parent_epic
            if final_parent_epic is None:
                # Try default_project first, fall back to default_epic
                if config.default_project:
                    final_parent_epic = config.default_project
                    logging.debug(
                        f"Using default project from config: {final_parent_epic}"
                    )
                elif config.default_epic:
                    final_parent_epic = config.default_epic
                    logging.debug(
                        f"Using default epic from config: {final_parent_epic}"
                    )

        # Default tags - merge with provided tags
        final_tags = tags or []
        if config.default_tags:
            # Add default tags that aren't already in the provided tags
            for default_tag in config.default_tags:
                if default_tag not in final_tags:
                    final_tags.append(default_tag)
            if final_tags != (tags or []):
                logging.debug(f"Merged default tags from config: {config.default_tags}")

        # Auto-detect labels if enabled (adds to existing tags)
        if auto_detect_labels:
            final_tags = await detect_and_apply_labels(
                adapter, title, description or "", final_tags
            )

        # Create task object
        task = Task(
            title=title,
            description=description or "",
            priority=priority_enum,
            tags=final_tags or [],
            assignee=final_assignee,
            parent_epic=final_parent_epic,
        )

        # Create via adapter
        created = await adapter.create(task)

        return {
            "status": "completed",
            "ticket": created.model_dump(),
            "labels_applied": created.tags or [],
            "auto_detected": auto_detect_labels,
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


def _compact_ticket(ticket_dict: dict[str, Any]) -> dict[str, Any]:
    """Extract compact representation of ticket for reduced token usage.

    This helper function reduces ticket data from ~185 tokens to ~55 tokens by
    including only essential fields. Use for listing operations where full
    details are not needed.

    Args:
        ticket_dict: Full ticket dictionary from model_dump()

    Returns:
        Compact ticket dictionary with only essential fields:
        - id: Ticket identifier
        - title: Ticket title
        - state: Current state
        - priority: Priority level
        - assignee: Assigned user (if any)
        - tags: List of tags/labels
        - parent_epic: Parent epic/project ID (if any)

    """
    return {
        "id": ticket_dict.get("id"),
        "title": ticket_dict.get("title"),
        "state": ticket_dict.get("state"),
        "priority": ticket_dict.get("priority"),
        "assignee": ticket_dict.get("assignee"),
        "tags": ticket_dict.get("tags", []),
        "parent_epic": ticket_dict.get("parent_epic"),
    }


@mcp.tool()
async def ticket_list(
    limit: int = 10,
    offset: int = 0,
    state: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    compact: bool = False,
) -> dict[str, Any]:
    """List tickets with pagination and optional filters.

    Token Usage Optimization:
        When listing many tickets, use compact=True to reduce token usage by ~70%.
        - Standard mode: ~185 tokens per ticket (full details including description,
          metadata, timestamps, children, hours)
        - Compact mode: ~55 tokens per ticket (only id, title, state, priority,
          assignee, tags, parent_epic)

        Example: 100 tickets = 18,500 tokens (standard) vs 5,500 tokens (compact)

    Args:
        limit: Maximum number of tickets to return (default: 10)
        offset: Number of tickets to skip for pagination (default: 0)
        state: Filter by state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        priority: Filter by priority - must be one of: low, medium, high, critical
        assignee: Filter by assigned user ID or email
        compact: Return minimal fields for reduced token usage (default: False)

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

        # Apply compact mode if requested
        if compact:
            ticket_data = [_compact_ticket(ticket.model_dump()) for ticket in tickets]
        else:
            ticket_data = [ticket.model_dump() for ticket in tickets]

        return {
            "status": "completed",
            "tickets": ticket_data,
            "count": len(tickets),
            "limit": limit,
            "offset": offset,
            "compact": compact,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list tickets: {str(e)}",
        }
