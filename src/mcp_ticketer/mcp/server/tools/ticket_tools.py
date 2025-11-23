"""Basic CRUD operations for tickets.

This module implements the core create, read, update, delete, and list
operations for tickets using the FastMCP SDK.
"""

import logging
from pathlib import Path
from typing import Any

from ....core.adapter import BaseAdapter
from ....core.models import Priority, Task, TicketState
from ....core.project_config import ConfigResolver, TicketerConfig
from ....core.session_state import SessionStateManager
from ....core.url_parser import extract_id_from_url, is_url
from ..diagnostic_helper import (
    build_diagnostic_suggestion,
    get_quick_diagnostic_info,
    should_suggest_diagnostics,
)
from ..server_sdk import get_adapter, get_router, has_router, mcp


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
        else:
            label_name = str(label)

        label_name_lower = label_name.lower()

        # Direct match: label name appears in content
        if label_name_lower in content:
            if label_name not in matched_labels:
                matched_labels.append(label_name)
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
                    if label_name not in matched_labels:
                        matched_labels.append(label_name)
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

        # Build response with adapter metadata
        response = {
            "status": "completed",
            **_build_adapter_metadata(adapter, created.id),
            "ticket": created.model_dump(),
            "labels_applied": created.tags or [],
            "auto_detected": auto_detect_labels,
        }
        return response
    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to create ticket: {str(e)}",
        }
        try:
            adapter = get_adapter()
            error_response.update(_build_adapter_metadata(adapter))
        except Exception:
            pass  # If adapter not available, return error without metadata

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(f"Error classified as system-level, adding diagnostic suggestion")
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


@mcp.tool()
async def ticket_read(ticket_id: str) -> dict[str, Any]:
    """Read a ticket by its ID or URL.

    This tool supports both plain ticket IDs and full URLs from multiple platforms:
    - Plain IDs: Use the configured default adapter (e.g., "ABC-123", "456")
    - Linear URLs: https://linear.app/team/issue/ABC-123
    - GitHub URLs: https://github.com/owner/repo/issues/123
    - JIRA URLs: https://company.atlassian.net/browse/PROJ-123
    - Asana URLs: https://app.asana.com/0/1234567890/9876543210

    The tool automatically detects the platform from URLs and routes to the
    appropriate adapter. Multi-platform support must be configured for URL access.

    Args:
        ticket_id: Ticket ID or URL to read

    Returns:
        Ticket details if found, or error information

    """
    try:
        is_routed = False
        # Check if multi-platform routing is available
        if is_url(ticket_id) and has_router():
            # Use router for URL-based access
            router = get_router()
            logging.info(f"Routing ticket_read for URL: {ticket_id}")
            ticket = await router.route_read(ticket_id)
            is_routed = True
            # Get adapter from router's cache to extract metadata
            normalized_id, _, _ = router._normalize_ticket_id(ticket_id)
            adapter = router._get_adapter(router._detect_adapter_from_url(ticket_id))
        else:
            # Use default adapter for plain IDs OR URLs (without multi-platform routing)
            adapter = get_adapter()

            # If URL provided, extract ID for the adapter
            if is_url(ticket_id):
                # Extract ID from URL for default adapter
                adapter_type = type(adapter).__name__.lower().replace("adapter", "")
                extracted_id, error = extract_id_from_url(ticket_id, adapter_type=adapter_type)
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}"
                    }
                ticket = await adapter.read(extracted_id)
            else:
                ticket = await adapter.read(ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, ticket.id, is_routed),
            "ticket": ticket.model_dump(),
        }
    except ValueError as e:
        # ValueError from adapters contains helpful user-facing messages
        # (e.g., Linear view URL detection error)
        # Return the error message directly without generic wrapper
        return {
            "status": "error",
            "error": str(e),
        }
    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to read ticket: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(f"Error classified as system-level, adding diagnostic suggestion")
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


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
    """Update an existing ticket using ID or URL.

    Supports both plain ticket IDs and full URLs from multiple platforms.
    See ticket_read for supported URL formats.

    Args:
        ticket_id: Ticket ID or URL to update
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

        # Route to appropriate adapter
        is_routed = False
        if is_url(ticket_id) and has_router():
            router = get_router()
            logging.info(f"Routing ticket_update for URL: {ticket_id}")
            updated = await router.route_update(ticket_id, updates)
            is_routed = True
            normalized_id, _, _ = router._normalize_ticket_id(ticket_id)
            adapter = router._get_adapter(router._detect_adapter_from_url(ticket_id))
        else:
            adapter = get_adapter()

            # If URL provided, extract ID for the adapter
            if is_url(ticket_id):
                # Extract ID from URL for default adapter
                adapter_type = type(adapter).__name__.lower().replace("adapter", "")
                extracted_id, error = extract_id_from_url(ticket_id, adapter_type=adapter_type)
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}"
                    }
                updated = await adapter.update(extracted_id, updates)
            else:
                updated = await adapter.update(ticket_id, updates)

        if updated is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found or update failed",
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, updated.id, is_routed),
            "ticket": updated.model_dump(),
        }
    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to update ticket: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(f"Error classified as system-level, adding diagnostic suggestion")
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


@mcp.tool()
async def ticket_delete(ticket_id: str) -> dict[str, Any]:
    """Delete a ticket by its ID or URL.

    Supports both plain ticket IDs and full URLs from multiple platforms.
    See ticket_read for supported URL formats.

    Args:
        ticket_id: Ticket ID or URL to delete

    Returns:
        Success confirmation or error information

    """
    try:
        # Route to appropriate adapter
        is_routed = False
        if is_url(ticket_id) and has_router():
            router = get_router()
            logging.info(f"Routing ticket_delete for URL: {ticket_id}")
            success = await router.route_delete(ticket_id)
            is_routed = True
            normalized_id, _, _ = router._normalize_ticket_id(ticket_id)
            adapter = router._get_adapter(router._detect_adapter_from_url(ticket_id))
        else:
            adapter = get_adapter()

            # If URL provided, extract ID for the adapter
            if is_url(ticket_id):
                # Extract ID from URL for default adapter
                adapter_type = type(adapter).__name__.lower().replace("adapter", "")
                extracted_id, error = extract_id_from_url(ticket_id, adapter_type=adapter_type)
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}"
                    }
                success = await adapter.delete(extracted_id)
            else:
                success = await adapter.delete(ticket_id)

        if not success:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found or delete failed",
            }

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, ticket_id, is_routed),
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
    limit: int = 20,
    offset: int = 0,
    state: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """List tickets with pagination and optional filters.

    Token Usage Optimization:
        Default settings (limit=20, compact=True) return ~1.1k tokens per response.
        For detailed information, use compact=False (returns ~185 tokens per ticket).

        Token usage examples:
        - 20 tickets, compact=True: ~1.1k tokens (~0.55% of context)
        - 20 tickets, compact=False: ~3.7k tokens (~1.85% of context)
        - 50 tickets, compact=True: ~2.75k tokens (~1.4% of context)
        - 50 tickets, compact=False: ~9.25k tokens (~4.6% of context)

    Args:
        limit: Maximum number of tickets to return (default: 20, max: 100)
        offset: Number of tickets to skip for pagination (default: 0)
        state: Filter by state - must be one of: open, in_progress, ready, tested, done, closed, waiting, blocked
        priority: Filter by priority - must be one of: low, medium, high, critical
        assignee: Filter by assigned user ID or email
        compact: Return minimal fields for reduced token usage (default: True)
                Set to False for full ticket details with description, metadata, etc.

    Returns:
        List of tickets matching criteria, or error information

    Examples:
        # Default: 20 compact tickets (~1.1k tokens)
        tickets = await ticket_list()

        # Get full details for fewer tickets
        tickets = await ticket_list(limit=10, compact=False)

        # Large query with compact mode
        tickets = await ticket_list(limit=50, compact=True)

    """
    try:
        adapter = get_adapter()

        # Add warning for large non-compact queries
        if limit > 30 and not compact:
            logging.warning(
                f"Large query requested: limit={limit}, compact={compact}. "
                f"This may generate ~{limit * 185} tokens. "
                f"Consider using compact=True to reduce token usage."
            )

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
            **_build_adapter_metadata(adapter),
            "tickets": ticket_data,
            "count": len(tickets),
            "limit": limit,
            "offset": offset,
            "compact": compact,
        }
    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to list tickets: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(f"Error classified as system-level, adding diagnostic suggestion")
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


@mcp.tool()
async def ticket_assign(
    ticket_id: str,
    assignee: str | None,
    comment: str | None = None,
    auto_transition: bool = True,
) -> dict[str, Any]:
    """Assign or reassign a ticket to a user with automatic state transition.

    This tool provides dedicated assignment functionality with audit trail support
    and automatic state transitions. It accepts both plain ticket IDs and full URLs
    from multiple platforms:
    - Plain IDs: Use the configured default adapter (e.g., "ABC-123", "456")
    - Linear URLs: https://linear.app/team/issue/ABC-123
    - GitHub URLs: https://github.com/owner/repo/issues/123
    - JIRA URLs: https://company.atlassian.net/browse/PROJ-123
    - Asana URLs: https://app.asana.com/0/1234567890/9876543210

    The tool automatically detects the platform from URLs and routes to the
    appropriate adapter. Multi-platform support must be configured for URL access.

    Auto-Transition Behavior:
    When a ticket is assigned (not unassigned), the tool automatically transitions
    the ticket to IN_PROGRESS if it's currently in one of these states:
    - OPEN → IN_PROGRESS: When starting work on new ticket
    - WAITING → IN_PROGRESS: When resuming after waiting period
    - BLOCKED → IN_PROGRESS: When resuming after block removed

    States that do NOT auto-transition:
    - Already IN_PROGRESS: No change needed
    - READY, TESTED, DONE: Don't move backwards in workflow
    - CLOSED: Terminal state, should not be worked on
    - Unassignment (assignee=None): No state change
    - Can be disabled with auto_transition=False

    User Resolution:
    - Accepts user IDs, emails, or names (adapter-dependent)
    - Each adapter handles user resolution according to its platform's API
    - Linear: User ID (UUID) or email
    - GitHub: Username
    - JIRA: Account ID or email
    - Asana: User GID or email

    Unassignment:
    - Set assignee=None to unassign the ticket
    - The ticket will be moved to unassigned state
    - No automatic state change occurs during unassignment

    Audit Trail:
    - Optional comment parameter adds a note to the ticket
    - Useful for explaining assignment/reassignment decisions
    - Automatic comment is added if state is auto-transitioned and no comment provided
    - Comment support is adapter-dependent

    Args:
        ticket_id: Ticket ID or URL to assign
        assignee: User identifier (ID, email, or name) or None to unassign
        comment: Optional comment to add explaining the assignment
        auto_transition: Automatically transition to IN_PROGRESS when appropriate (default: True)

    Returns:
        Dictionary containing:
        - status: "completed" or "error"
        - ticket: Full updated ticket object
        - previous_assignee: Who the ticket was assigned to before (if any)
        - new_assignee: Who the ticket is now assigned to (if any)
        - previous_state: State before assignment
        - new_state: State after assignment
        - state_auto_transitioned: Boolean indicating if state was automatically changed
        - comment_added: Boolean indicating if comment was added
        - adapter: Which adapter handled the operation
        - adapter_name: Human-readable adapter name
        - routed_from_url: True if ticket_id was a URL (optional)

    Example:
        # Assign ticket to user by email (auto-transitions OPEN → IN_PROGRESS)
        >>> ticket_assign(
        ...     ticket_id="PROJ-123",
        ...     assignee="user@example.com",
        ...     comment="Taking ownership of this issue"
        ... )

        # Assign ticket using URL (with auto-transition)
        >>> ticket_assign(
        ...     ticket_id="https://linear.app/team/issue/ABC-123",
        ...     assignee="john.doe@example.com"
        ... )

        # Assign without auto-transition
        >>> ticket_assign(
        ...     ticket_id="PROJ-123",
        ...     assignee="user@example.com",
        ...     auto_transition=False
        ... )

        # Unassign ticket (no state change)
        >>> ticket_assign(ticket_id="PROJ-123", assignee=None)

        # Reassign with explanation
        >>> ticket_assign(
        ...     ticket_id="PROJ-123",
        ...     assignee="jane.smith@example.com",
        ...     comment="Reassigning to Jane who has domain expertise"
        ... )

    """
    try:
        # Read current ticket to get previous assignee
        is_routed = False
        if is_url(ticket_id) and has_router():
            router = get_router()
            logging.info(f"Routing ticket_assign for URL: {ticket_id}")
            ticket = await router.route_read(ticket_id)
            is_routed = True
            normalized_id, adapter_name, _ = router._normalize_ticket_id(ticket_id)
            adapter = router._get_adapter(adapter_name)
        else:
            adapter = get_adapter()

            # If URL provided, extract ID for the adapter
            actual_ticket_id = ticket_id
            if is_url(ticket_id):
                # Extract ID from URL for default adapter
                adapter_type = type(adapter).__name__.lower().replace("adapter", "")
                extracted_id, error = extract_id_from_url(ticket_id, adapter_type=adapter_type)
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}"
                    }
                actual_ticket_id = extracted_id

            ticket = await adapter.read(actual_ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Store previous assignee and state for response
        previous_assignee = ticket.assignee
        current_state = ticket.state

        # Import TicketState for state transitions
        from ....core.models import TicketState

        # Convert string state to enum if needed (Pydantic uses use_enum_values=True)
        if isinstance(current_state, str):
            current_state = TicketState(current_state)

        # Build updates dictionary
        updates: dict[str, Any] = {"assignee": assignee}

        # Auto-transition logic
        state_transitioned = False
        auto_comment = None

        if auto_transition and assignee is not None:  # Only when assigning (not unassigning)
            # Check if current state should auto-transition to IN_PROGRESS
            if current_state in [TicketState.OPEN, TicketState.WAITING, TicketState.BLOCKED]:
                # Validate workflow allows this transition
                if current_state.can_transition_to(TicketState.IN_PROGRESS):
                    updates["state"] = TicketState.IN_PROGRESS
                    state_transitioned = True

                    # Add automatic comment if no comment provided
                    if comment is None:
                        auto_comment = f"Automatically transitioned from {current_state.value} to in_progress when assigned to {assignee}"
                else:
                    # Log warning if transition validation fails (shouldn't happen based on our rules)
                    logging.warning(
                        f"State transition from {current_state.value} to IN_PROGRESS failed validation"
                    )

        if is_routed:
            updated = await router.route_update(ticket_id, updates)
        else:
            updated = await adapter.update(actual_ticket_id, updates)

        if updated is None:
            return {
                "status": "error",
                "error": f"Failed to update assignment for ticket {ticket_id}",
            }

        # Add comment if provided or auto-generated, and adapter supports it
        comment_added = False
        comment_to_add = comment or auto_comment

        if comment_to_add:
            try:
                from ....core.models import Comment as CommentModel

                # Use actual_ticket_id for non-routed case, original ticket_id for routed
                comment_ticket_id = ticket_id if is_routed else actual_ticket_id

                comment_obj = CommentModel(
                    ticket_id=comment_ticket_id, content=comment_to_add, author=""
                )

                if is_routed:
                    await router.route_add_comment(ticket_id, comment_obj)
                else:
                    await adapter.add_comment(comment_obj)
                comment_added = True
            except Exception as e:
                # Comment failed but assignment succeeded - log and continue
                logging.warning(f"Assignment succeeded but comment failed: {str(e)}")

        # Build response
        # Handle both string and enum state values
        previous_state_value = current_state.value if hasattr(current_state, 'value') else str(current_state)
        new_state_value = updated.state.value if hasattr(updated.state, 'value') else str(updated.state)

        response = {
            "status": "completed",
            **_build_adapter_metadata(adapter, updated.id, is_routed),
            "ticket": updated.model_dump(),
            "previous_assignee": previous_assignee,
            "new_assignee": assignee,
            "previous_state": previous_state_value,
            "new_state": new_state_value,
            "state_auto_transitioned": state_transitioned,
            "comment_added": comment_added,
        }

        return response

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to assign ticket: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(f"Error classified as system-level, adding diagnostic suggestion")
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response
