"""Unified ticket CRUD operations (v2.0.0).

This module implements ticket management through a single unified `ticket()` interface.

Version 2.0.0 changes:
- Removed @mcp.tool() decorators from individual operations (converted to private helpers)
- Single `ticket()` function is the only exposed MCP tool
- All operations accessible via ticket(action="create"|"get"|"update"|"delete"|"list"|"summary"|"get_activity"|"assign")
- Individual functions retained as internal helpers for code organization
"""

import logging
import re
import warnings
from pathlib import Path
from typing import Any, Literal

from ....core.adapter import BaseAdapter
from ....core.models import Priority, Task, TicketState
from ....core.priority_matcher import get_priority_matcher
from ....core.project_config import ConfigResolver, TicketerConfig
from ....core.session_state import SessionStateManager
from ....core.url_parser import extract_id_from_url, is_url
from ..diagnostic_helper import (
    build_diagnostic_suggestion,
    get_quick_diagnostic_info,
    should_suggest_diagnostics,
)
from ..server_sdk import get_adapter, get_router, has_router, mcp

# Sentinel value to distinguish between "parameter not provided" and "explicitly None"
_UNSET = object()


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


def extract_project_url_from_text(text: str) -> str | None:
    """Extract Linear/GitHub/Jira project URL from text if present.

    Supports project URLs from:
    - Linear: https://linear.app/{workspace}/project/{projectId}
    - GitHub: https://github.com/{owner}/projects/{projectNumber}
    - Jira: https://{domain}.atlassian.net/browse/{projectKey}

    Args:
        text: Text to search for project URLs (title, description, etc.)

    Returns:
        First project URL found, or None if no project URL detected

    Note:
        Only extracts project URLs, not individual ticket/issue URLs.
        Ticket URLs are intentionally ignored to avoid confusion.

    Examples:
        >>> extract_project_url_from_text("Fix bug in https://linear.app/hello-recess/project/v2-f7a18fae1c21")
        'https://linear.app/hello-recess/project/v2-f7a18fae1c21'

        >>> extract_project_url_from_text("No URL here")
        None

    """
    if not text:
        return None

    # Linear project URL pattern
    # Format: https://linear.app/{workspace}/project/{projectId}
    # projectId is alphanumeric with hyphens (e.g., v2-f7a18fae1c21)
    linear_pattern = r"https?://linear\.app/[^/\s]+/project/[a-zA-Z0-9-]+"

    # GitHub project URL pattern
    # Format: https://github.com/{owner}/projects/{projectNumber}
    # projectNumber is numeric
    github_pattern = r"https?://github\.com/[^/\s]+/projects/\d+"

    # Jira project URL pattern
    # Format: https://{domain}.atlassian.net/browse/{projectKey}
    # projectKey is typically uppercase letters (e.g., PROJ, ABC)
    jira_pattern = r"https?://[^/\s]+\.atlassian\.net/browse/[A-Z][A-Z0-9]+"

    # Combined patterns
    patterns = [linear_pattern, github_pattern, jira_pattern]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)

    return None


async def detect_and_apply_labels(
    adapter: Any,
    ticket_title: str,
    ticket_description: str,
    existing_labels: list[str] | None = None,
    max_auto_labels: int = 4,
) -> list[str]:
    """Detect and suggest labels/tags based on ticket content.

    This function analyzes the ticket title and description to automatically
    detect relevant labels/tags from the adapter's available labels.

    Args:
        adapter: The ticket adapter instance
        ticket_title: Ticket title text
        ticket_description: Ticket description text
        existing_labels: Labels already specified by user (optional)
        max_auto_labels: Maximum number of auto-detected labels to apply (default: 4)

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

        # Skip hierarchical labels (containing "/") unless exact match
        # This prevents overly broad matches like "Test Suite/Authentication" matching "test"
        if "/" in label_name_lower:
            if label_name_lower not in content:
                continue

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

    # Combine user-specified labels with auto-detected ones (apply limit to auto-detected)
    final_labels = list(existing_labels or [])
    for label in matched_labels[:max_auto_labels]:  # Apply max limit
        if label not in final_labels:
            final_labels.append(label)

    return final_labels


@mcp.tool(
    description="Unified ticket operations - create, read, update, delete, list, summarize tickets; manage assignments, comments, and activity tracking"
)
async def ticket(
    action: Literal[
        "create",
        "get",
        "update",
        "delete",
        "list",
        "summary",
        "get_activity",
        "assign",
        "add_comment",
        "list_comments",
    ],
    # Ticket identification
    ticket_id: str | None = None,
    # Create parameters
    title: str | None = None,
    description: str = "",
    priority: str = "medium",
    tags: list[str] | None = None,
    assignee: str | None = None,
    parent_epic: str | None = _UNSET,
    auto_detect_labels: bool = True,
    max_auto_labels: int = 4,
    # Update parameters
    state: str | None = None,
    # List parameters
    limit: int = 20,
    offset: int = 0,
    project_id: str | None = None,
    compact: bool = True,
    # Assign parameters
    comment: str | None = None,
    auto_transition: bool = True,
    # Comment parameters
    comment_text: str | None = None,
    comment_limit: int = 10,
    comment_offset: int = 0,
) -> dict[str, Any]:
    """Unified ticket management tool for all CRUD operations.

    Handles ticket creation, reading, updating, deletion, listing,
    summarization, activity tracking, assignment, and comments in a single interface.

    Args:
        action: Operation to perform (create, get, update, delete, list, summary, get_activity, assign, add_comment, list_comments)
        ticket_id: Ticket ID for get/update/delete/summary/assign/comment operations
        title: Ticket title (required for create)
        description: Ticket description
        priority: Ticket priority (low, medium, high, critical)
        tags: List of tags/labels
        assignee: User ID or email to assign ticket
        parent_epic: Parent epic/project ID
        auto_detect_labels: Auto-detect labels from content
        max_auto_labels: Maximum number of auto-detected labels to apply (default: 4)
        state: Ticket state for updates
        limit: Maximum results for list/get_activity operations
        offset: Pagination offset for list
        project_id: Project filter for list operations
        compact: Return compact format for list (saves tokens)
        comment: Comment when assigning ticket
        auto_transition: Auto-transition state when assigning
        comment_text: Comment text (required for add_comment action)
        comment_limit: Maximum comments to return (for list_comments, default: 10)
        comment_offset: Pagination offset for list_comments (default: 0)

    Returns:
        dict: Operation results

    Raises:
        ValueError: If action is invalid or required parameters missing

    Examples:
        # Create ticket
        await ticket(
            action="create",
            title="Fix login bug",
            priority="high",
            tags=["bug", "security"]
        )

        # Get ticket details
        await ticket(
            action="get",
            ticket_id="PROJ-123"
        )

        # Update ticket
        await ticket(
            action="update",
            ticket_id="PROJ-123",
            state="in_progress",
            priority="critical"
        )

        # List tickets
        await ticket(
            action="list",
            project_id="PROJ",
            state="open",
            limit=50
        )

        # Get compact summary
        await ticket(
            action="summary",
            ticket_id="PROJ-123"
        )

        # Get activity/comments
        await ticket(
            action="get_activity",
            ticket_id="PROJ-123",
            limit=5
        )

        # Assign ticket
        await ticket(
            action="assign",
            ticket_id="PROJ-123",
            assignee="user@example.com",
            comment="Taking this one"
        )

        # Delete ticket
        await ticket(
            action="delete",
            ticket_id="PROJ-123"
        )

        # Add comment
        await ticket(
            action="add_comment",
            ticket_id="PROJ-123",
            comment_text="Working on this now"
        )

        # List comments
        await ticket(
            action="list_comments",
            ticket_id="PROJ-123",
            comment_limit=5
        )

    Migration from deprecated tools:
        - ticket_comment(operation="add", text=...) → ticket(action="add_comment", comment_text=...)
        - ticket_comment(operation="list", limit=..., offset=...) → ticket(action="list_comments", comment_limit=..., comment_offset=...)
    """
    # Normalize action to lowercase for case-insensitive matching
    action_lower = action.lower()

    if action_lower == "create":
        if not title:
            return {
                "status": "error",
                "error": "title parameter required for action='create'",
                "hint": "Example: ticket(action='create', title='Fix bug', priority='high')",
            }
        return await ticket_create(
            title,
            description,
            priority,
            tags,
            assignee,
            parent_epic,
            auto_detect_labels,
            max_auto_labels,
        )

    elif action_lower == "get":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='get'",
                "hint": "Example: ticket(action='get', ticket_id='PROJ-123')",
            }
        return await ticket_read(ticket_id)

    elif action_lower == "update":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='update'",
                "hint": "Example: ticket(action='update', ticket_id='PROJ-123', state='done')",
            }
        return await ticket_update(
            ticket_id, title, description, priority, state, assignee, tags
        )

    elif action_lower == "delete":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='delete'",
                "hint": "Example: ticket(action='delete', ticket_id='PROJ-123')",
            }
        return await ticket_delete(ticket_id)

    elif action_lower == "list":
        return await ticket_list(
            limit, offset, state, priority, assignee, project_id, compact
        )

    elif action_lower == "summary":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='summary'",
                "hint": "Example: ticket(action='summary', ticket_id='PROJ-123')",
            }
        return await ticket_summary(ticket_id)

    elif action_lower == "get_activity":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='get_activity'",
                "hint": "Example: ticket(action='get_activity', ticket_id='PROJ-123', limit=5)",
            }
        return await ticket_latest(ticket_id, limit)

    elif action_lower == "assign":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='assign'",
                "hint": "Example: ticket(action='assign', ticket_id='PROJ-123', assignee='user@example.com')",
            }
        return await ticket_assign(ticket_id, assignee, comment, auto_transition)

    elif action_lower == "add_comment":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='add_comment'",
                "hint": "Example: ticket(action='add_comment', ticket_id='PROJ-123', comment_text='Working on this')",
            }
        if not comment_text:
            return {
                "status": "error",
                "error": "comment_text parameter required for action='add_comment'",
                "hint": "Example: ticket(action='add_comment', ticket_id='PROJ-123', comment_text='Working on this')",
            }
        return await _ticket_add_comment(ticket_id, comment_text)

    elif action_lower == "list_comments":
        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id parameter required for action='list_comments'",
                "hint": "Example: ticket(action='list_comments', ticket_id='PROJ-123', comment_limit=5)",
            }
        return await _ticket_list_comments(ticket_id, comment_limit, comment_offset)

    else:
        return {
            "status": "error",
            "error": f"Invalid action: {action}",
            "valid_actions": [
                "create",
                "get",
                "update",
                "delete",
                "list",
                "summary",
                "get_activity",
                "assign",
                "add_comment",
                "list_comments",
            ],
            "hint": "Use one of the valid actions listed above",
        }


async def ticket_create(
    title: str,
    description: str = "",
    priority: str = "medium",
    tags: list[str] | None = None,
    assignee: str | None = None,
    parent_epic: str | None = _UNSET,
    auto_detect_labels: bool = True,
    max_auto_labels: int = 4,
) -> dict[str, Any]:
    """Create ticket with auto-label detection and semantic priority matching.

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='create'`` instead.
        This function will be removed in version 2.0.0.

    Args: title (required), description, priority (supports natural language), tags, assignee, parent_epic (optional), auto_detect_labels (default: True)
    Returns: TicketResponse with created ticket, ID, metadata
    See: docs/mcp-api-reference.md#ticket-response-format, docs/mcp-api-reference.md#semantic-priority-matching
    """
    warnings.warn(
        "ticket_create is deprecated. Use ticket(action='create', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        adapter = get_adapter()

        # Validate and convert priority using semantic matcher (ISS-0002)
        priority_matcher = get_priority_matcher()
        match_result = priority_matcher.match_priority(priority)

        # Handle low confidence matches - provide suggestions
        if match_result.is_low_confidence():
            suggestions = priority_matcher.suggest_priorities(priority, top_n=3)
            return {
                "status": "ambiguous",
                "message": f"Priority input '{priority}' is ambiguous. Please choose from suggestions or use exact values.",
                "original_input": priority,
                "suggestions": [
                    {
                        "priority": s.priority.value,
                        "confidence": round(s.confidence, 2),
                    }
                    for s in suggestions
                ],
                "exact_values": ["low", "medium", "high", "critical"],
            }

        priority_enum = match_result.priority

        # Auto-detect project URL from description if parent_epic not provided
        # This happens BEFORE priority resolution so explicit parent_epic takes precedence
        if parent_epic is _UNSET:
            combined_text = f"{title} {description or ''}"
            detected_project = extract_project_url_from_text(combined_text)
            if detected_project:
                parent_epic = detected_project
                logging.info(
                    f"Auto-detected project URL from ticket content: {detected_project}"
                )

        # Apply configuration defaults if values not provided
        resolver = ConfigResolver(project_path=Path.cwd())
        config = resolver.load_project_config() or TicketerConfig()

        # Determine final_parent_epic based on priority order:
        # Priority 1: Explicit parent_epic argument (including explicit None for opt-out)
        # Priority 2: Auto-detected project URL from title/description
        # Priority 3: Config default (default_epic or default_project)
        # Priority 4: Session-attached ticket
        # Priority 5: Prompt user (last resort only if nothing configured)

        final_parent_epic: str | None = None

        if parent_epic is not _UNSET:
            # Priority 1: Explicit value provided (including None for opt-out)
            final_parent_epic = parent_epic
            if parent_epic is not None:
                logging.debug(f"Using explicit parent_epic: {parent_epic}")
            else:
                logging.debug("Explicitly opted out of parent_epic (parent_epic=None)")
        elif config.default_project or config.default_epic:
            # Priority 2: Use configured default
            final_parent_epic = config.default_project or config.default_epic
            logging.debug(f"Using default epic from config: {final_parent_epic}")
        else:
            # Priority 3 & 4: Check session, then prompt
            session_manager = SessionStateManager(project_path=Path.cwd())
            session_state = session_manager.load_session()

            if session_state.current_ticket:
                # Priority 3: Use session ticket as parent_epic
                final_parent_epic = session_state.current_ticket
                logging.info(
                    f"Using session ticket as parent_epic: {final_parent_epic}"
                )
            elif not session_state.ticket_opted_out:
                # Priority 4: No default, no session, no opt-out - provide guidance
                return {
                    "status": "error",
                    "requires_ticket_association": True,
                    "guidance": (
                        "⚠️  No ticket association found for this work session.\n\n"
                        "It's recommended to associate your work with a ticket for proper tracking.\n\n"
                        "**Options**:\n"
                        "1. Associate with a ticket: user_session(action='attach_ticket', ticket_id='PROJ-123')\n"
                        "2. Skip for this session: user_session(action='opt_out')\n"
                        "3. Provide parent_epic directly: ticket_create(..., parent_epic='PROJ-123')\n"
                        "4. Set a default: config_set_default_project(project_id='PROJ-123')\n\n"
                        "After associating, run ticket_create again to create the ticket."
                    ),
                    "session_id": session_state.session_id,
                }
            # else: session opted out, final_parent_epic stays None

        # Default user/assignee
        final_assignee = assignee
        if final_assignee is None and config.default_user:
            final_assignee = config.default_user
            logging.debug(f"Using default assignee from config: {final_assignee}")

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
                adapter, title, description or "", final_tags, max_auto_labels
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
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def ticket_read(ticket_id: str) -> dict[str, Any]:
    """Read ticket by ID or URL (supports Linear, GitHub, JIRA, Asana URLs with multi-platform routing).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='get'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or full URL)
    Returns: TicketResponse with ticket details
    See: docs/mcp-api-reference.md#ticket-response-format, docs/mcp-api-reference.md#url-routing
    """
    warnings.warn(
        "ticket_read is deprecated. Use ticket(action='get', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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
                extracted_id, error = extract_id_from_url(
                    ticket_id, adapter_type=adapter_type
                )
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}",
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
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def ticket_update(
    ticket_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    state: str | None = None,
    assignee: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Update ticket using ID or URL (semantic priority matching, workflow states).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='update'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or URL), title, description, priority (natural language), state (workflow), assignee, tags
    Returns: TicketResponse with updated ticket
    See: docs/mcp-api-reference.md#ticket-response-format, docs/mcp-api-reference.md#semantic-priority-matching
    """
    warnings.warn(
        "ticket_update is deprecated. Use ticket(action='update', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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

        # Validate and convert priority if provided (ISS-0002)
        if priority is not None:
            priority_matcher = get_priority_matcher()
            match_result = priority_matcher.match_priority(priority)

            # Handle low confidence matches - provide suggestions
            if match_result.is_low_confidence():
                suggestions = priority_matcher.suggest_priorities(priority, top_n=3)
                return {
                    "status": "ambiguous",
                    "message": f"Priority input '{priority}' is ambiguous. Please choose from suggestions or use exact values.",
                    "original_input": priority,
                    "suggestions": [
                        {
                            "priority": s.priority.value,
                            "confidence": round(s.confidence, 2),
                        }
                        for s in suggestions
                    ],
                    "exact_values": ["low", "medium", "high", "critical"],
                }

            updates["priority"] = match_result.priority

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
                extracted_id, error = extract_id_from_url(
                    ticket_id, adapter_type=adapter_type
                )
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}",
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
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def ticket_delete(ticket_id: str) -> dict[str, Any]:
    """Delete ticket by ID or URL.

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='delete'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or URL)
    Returns: DeleteResponse with status confirmation
    See: docs/mcp-api-reference.md#delete-response
    """
    warnings.warn(
        "ticket_delete is deprecated. Use ticket(action='delete', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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
                extracted_id, error = extract_id_from_url(
                    ticket_id, adapter_type=adapter_type
                )
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}",
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

    This helper function reduces ticket data from ~185 tokens to ~50 tokens by
    including only the most essential fields. Use for listing operations where full
    details are not needed.

    Args:
        ticket_dict: Full ticket dictionary from model_dump()

    Returns:
        Compact ticket dictionary with essential fields:
        - id: Ticket identifier
        - title: Ticket title
        - state: Current state (for quick status check)
        - priority: Priority level
        - assignee: Assigned user (if any)
        - tags: List of tags/labels (if any)
        - parent_epic: Parent epic ID (if any)

    """
    return {
        "id": ticket_dict.get("id"),
        "title": ticket_dict.get("title"),
        "state": ticket_dict.get("state"),
        "priority": ticket_dict.get("priority"),
        "assignee": ticket_dict.get("assignee"),
        "tags": ticket_dict.get("tags") or [],
        "parent_epic": ticket_dict.get("parent_epic"),
    }


async def ticket_list(
    limit: int = 20,
    offset: int = 0,
    state: str | None = None,
    priority: str | None = None,
    assignee: str | None = None,
    project_id: str | None = None,
    compact: bool = True,
) -> dict[str, Any]:
    """List tickets with pagination and filters (compact mode default, project scoping required).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='list'`` instead.
        This function will be removed in version 2.0.0.

    ⚠️ Project Filtering Required:
    This tool requires project_id parameter OR default_project configuration.
    To set default project: config_set_default_project(project_id="YOUR-PROJECT")
    To check current config: config_get()

    Args: limit (max: 100, default: 20), offset (pagination), state, priority, assignee, project_id (required), compact (default: True, ~50 tokens/ticket vs ~185 full)
    Returns: ListResponse with tickets array, count, pagination
    See: docs/mcp-api-reference.md#list-response-format, docs/mcp-api-reference.md#token-usage-optimization
    """
    warnings.warn(
        "ticket_list is deprecated. Use ticket(action='list', ...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate project context (Optional for list operations)
        from pathlib import Path

        from ....core.project_config import ConfigResolver

        resolver = ConfigResolver(project_path=Path.cwd())
        config = resolver.load_project_config()
        final_project = project_id or (config.default_project if config else None)

        adapter = get_adapter()

        # Add warning for large non-compact queries
        if limit > 30 and not compact:
            logging.warning(
                f"Large query requested: limit={limit}, compact={compact}. "
                f"This may generate ~{limit * 185} tokens. "
                f"Consider using compact=True to reduce token usage."
            )

        # Add warning for large unscoped queries
        if limit > 50 and not (state or priority or assignee or final_project):
            logging.warning(
                f"Large unscoped query: limit={limit} with no filters. "
                f"Consider using state, priority, or assignee filters to reduce result set. "
                f"Tip: Configure default_team or default_project for automatic scoping."
            )

        # Build filters dictionary (only add project if provided)
        filters: dict[str, Any] = {}
        if final_project:
            filters["project"] = final_project

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

        # Build response
        response_data = {
            "status": "completed",
            **_build_adapter_metadata(adapter),
            "tickets": ticket_data,
            "count": len(tickets),
            "limit": limit,
            "offset": offset,
            "compact": compact,
        }

        # Estimate and validate token count to prevent MCP limit violations
        # MCP has a 25k token limit per response; we use 20k as safety margin
        from ....utils.token_utils import estimate_json_tokens

        estimated_tokens = estimate_json_tokens(response_data)

        # If exceeds 20k tokens (safety margin below 25k MCP limit)
        if estimated_tokens > 20_000:
            # Calculate recommended limit based on current token-per-ticket ratio
            if len(tickets) > 0:
                tokens_per_ticket = estimated_tokens / len(tickets)
                recommended_limit = int(20_000 / tokens_per_ticket)
            else:
                recommended_limit = 20

            return {
                "status": "error",
                "error": f"Response would exceed MCP token limit ({estimated_tokens:,} tokens)",
                "recommendation": (
                    f"Use smaller limit (try limit={recommended_limit}), "
                    "add filters (state=open, project_id=...), or enable compact mode"
                ),
                "current_settings": {
                    "limit": limit,
                    "compact": compact,
                    "estimated_tokens": estimated_tokens,
                    "max_allowed": 25_000,
                },
            }

        # Add token estimate to successful response for monitoring
        response_data["estimated_tokens"] = estimated_tokens

        return response_data
    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to list tickets: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def ticket_summary(ticket_id: str) -> dict[str, Any]:
    """Get ultra-compact summary (id, title, state, priority, assignee only - ~20 tokens vs ~185 full).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='summary'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or URL)
    Returns: SummaryResponse with minimal fields (90% token savings)
    See: docs/mcp-api-reference.md#compact-ticket-format
    """
    warnings.warn(
        "ticket_summary is deprecated. Use ticket(action='summary', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Use ticket_read to get full ticket
        result = await ticket_read(ticket_id)

        if result["status"] == "error":
            return result

        ticket = result["ticket"]

        # Extract only ultra-essential fields
        summary = {
            "id": ticket.get("id"),
            "title": ticket.get("title"),
            "state": ticket.get("state"),
            "priority": ticket.get("priority"),
            "assignee": ticket.get("assignee"),
        }

        return {
            "status": "completed",
            **_build_adapter_metadata(
                get_adapter(), ticket.get("id"), result.get("routed_from_url", False)
            ),
            "summary": summary,
            "token_savings": "~90% smaller than full ticket_read",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get ticket summary: {str(e)}",
        }


async def ticket_latest(ticket_id: str, limit: int = 5) -> dict[str, Any]:
    """Get recent activity (comments, state changes, updates - adapter-dependent behavior).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='get_activity'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or URL), limit (max: 20, default: 5)
    Returns: ActivityResponse with recent activities, timestamps, change descriptions
    See: docs/mcp-api-reference.md#activity-response-format
    """
    warnings.warn(
        "ticket_latest is deprecated. Use ticket(action='get_activity', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
    try:
        # Validate limit
        if limit < 1 or limit > 20:
            return {
                "status": "error",
                "error": "Limit must be between 1 and 20",
            }

        # Route to appropriate adapter
        is_routed = False
        if is_url(ticket_id) and has_router():
            router = get_router()
            logging.info(f"Routing ticket_latest for URL: {ticket_id}")
            # First get the ticket to verify it exists
            ticket = await router.route_read(ticket_id)
            is_routed = True
            normalized_id, adapter_name, _ = router._normalize_ticket_id(ticket_id)
            adapter = router._get_adapter(adapter_name)
            actual_ticket_id = normalized_id
        else:
            adapter = get_adapter()

            # If URL provided, extract ID for the adapter
            actual_ticket_id = ticket_id
            if is_url(ticket_id):
                adapter_type = type(adapter).__name__.lower().replace("adapter", "")
                extracted_id, error = extract_id_from_url(
                    ticket_id, adapter_type=adapter_type
                )
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}",
                    }
                actual_ticket_id = extracted_id

            # Get ticket to verify it exists
            ticket = await adapter.read(actual_ticket_id)

        if ticket is None:
            return {
                "status": "error",
                "error": f"Ticket {ticket_id} not found",
            }

        # Try to get comments if adapter supports it
        recent_activity = []
        supports_comments = False

        try:
            # Check if adapter has list_comments method
            if hasattr(adapter, "list_comments"):
                comments = await adapter.list_comments(actual_ticket_id, limit=limit)
                supports_comments = True

                # Convert comments to activity format
                for comment in comments[:limit]:
                    activity_item = {
                        "type": "comment",
                        "timestamp": (
                            comment.created_at
                            if hasattr(comment, "created_at")
                            else None
                        ),
                        "author": (
                            comment.author if hasattr(comment, "author") else None
                        ),
                        "content": comment.content[:200]
                        + ("..." if len(comment.content) > 200 else ""),
                    }
                    recent_activity.append(activity_item)
        except Exception as e:
            logging.debug(f"Comment listing not supported or failed: {e}")

        # If no comments available, provide last update info
        if not recent_activity:
            recent_activity.append(
                {
                    "type": "last_update",
                    "timestamp": (
                        ticket.updated_at if hasattr(ticket, "updated_at") else None
                    ),
                    "state": ticket.state,
                    "priority": ticket.priority,
                    "assignee": ticket.assignee,
                }
            )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, ticket.id, is_routed),
            "ticket_id": ticket.id,
            "ticket_title": ticket.title,
            "recent_activity": recent_activity,
            "activity_count": len(recent_activity),
            "supports_full_history": supports_comments,
            "limit": limit,
        }

    except Exception as e:
        error_response = {
            "status": "error",
            "error": f"Failed to get recent activity: {str(e)}",
        }

        # Add diagnostic suggestion for system-level errors
        if should_suggest_diagnostics(e):
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def ticket_assign(
    ticket_id: str,
    assignee: str | None,
    comment: str | None = None,
    auto_transition: bool = True,
) -> dict[str, Any]:
    """Assign/unassign ticket with auto-transition to IN_PROGRESS (OPEN/WAITING/BLOCKED → IN_PROGRESS when assigned).

    .. deprecated:: 1.5.0
        Use :func:`ticket` with ``action='assign'`` instead.
        This function will be removed in version 2.0.0.

    Args: ticket_id (ID or URL), assignee (user ID/email or None to unassign), comment (optional audit trail), auto_transition (default: True)
    Returns: AssignmentResponse with ticket, previous/new assignee, previous/new state, state_auto_transitioned, comment_added
    See: docs/ticket-workflows.md#auto-transitions, docs/mcp-api-reference.md#user-identifiers
    """
    warnings.warn(
        "ticket_assign is deprecated. Use ticket(action='assign', ticket_id=...) instead. "
        "This function will be removed in version 2.0.0.",
        DeprecationWarning,
        stacklevel=2,
    )
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
                extracted_id, error = extract_id_from_url(
                    ticket_id, adapter_type=adapter_type
                )
                if error or not extracted_id:
                    return {
                        "status": "error",
                        "error": f"Failed to extract ticket ID from URL: {ticket_id}. {error}",
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

        # Resolve assignee with user disambiguation
        resolved_assignee = assignee
        if assignee is not None:
            try:
                # Try to search for users if adapter supports it
                if hasattr(adapter, "search_users"):
                    matches = await adapter.search_users(assignee)

                    # Handle different match scenarios
                    if len(matches) == 0:
                        return {
                            "status": "error",
                            "error": f"No users found matching '{assignee}'",
                        }
                    elif len(matches) > 1:
                        return {
                            "status": "disambiguation_required",
                            "message": f"Multiple users match '{assignee}'. Please be more specific:",
                            "matches": matches,
                            "hint": "Use exact email or full name",
                        }
                    else:
                        # Exactly one match - use that user's ID
                        resolved_assignee = matches[0]["id"]
                        logging.info(
                            f"Resolved assignee '{assignee}' to user ID '{resolved_assignee}'"
                        )
            except NotImplementedError:
                # Adapter doesn't support search_users, fall back to direct assignment
                logging.debug(
                    f"Adapter {type(adapter).__name__} doesn't support search_users, using assignee directly"
                )
            except Exception as e:
                # Log but don't fail - fall back to direct assignment
                logging.warning(
                    f"User search failed for '{assignee}': {e}. Using assignee directly."
                )

        # Build updates dictionary
        updates: dict[str, Any] = {"assignee": resolved_assignee}

        # Auto-transition logic
        state_transitioned = False
        auto_comment = None

        if (
            auto_transition and assignee is not None
        ):  # Only when assigning (not unassigning)
            # Check if current state should auto-transition to IN_PROGRESS
            if current_state in [
                TicketState.OPEN,
                TicketState.WAITING,
                TicketState.BLOCKED,
            ]:
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
        previous_state_value = (
            current_state.value
            if hasattr(current_state, "value")
            else str(current_state)
        )
        new_state_value = (
            updated.state.value
            if hasattr(updated.state, "value")
            else str(updated.state)
        )

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
            logging.debug(
                "Error classified as system-level, adding diagnostic suggestion"
            )
            try:
                quick_info = await get_quick_diagnostic_info()
                error_response["diagnostic_suggestion"] = build_diagnostic_suggestion(
                    e, quick_info
                )
            except Exception as diag_error:
                # Never block error response on diagnostic failure
                logging.debug(f"Diagnostic suggestion generation failed: {diag_error}")

        return error_response


async def _ticket_add_comment(ticket_id: str, text: str) -> dict[str, Any]:
    """Add a comment to a ticket (internal helper for ticket tool).

    Args:
        ticket_id: Ticket ID or URL
        text: Comment text

    Returns:
        dict: Comment response with created comment data

    """
    try:
        # Import Comment model
        from ....core.models import Comment

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
            adapter = router._get_adapter(router._detect_adapter_from_url(ticket_id))
        else:
            adapter = get_adapter()
            created = await adapter.add_comment(comment)

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, created.ticket_id, is_routed),
            "operation": "add_comment",
            "comment": created.model_dump(),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to add comment: {str(e)}",
        }


async def _ticket_list_comments(
    ticket_id: str, limit: int = 10, offset: int = 0
) -> dict[str, Any]:
    """List comments on a ticket (internal helper for ticket tool).

    Args:
        ticket_id: Ticket ID or URL
        limit: Maximum number of comments to return (default: 10)
        offset: Pagination offset (default: 0)

    Returns:
        dict: List of comments with metadata

    """
    try:
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
            adapter = router._get_adapter(router._detect_adapter_from_url(ticket_id))
        else:
            adapter = get_adapter()
            comments = await adapter.get_comments(
                ticket_id=ticket_id, limit=limit, offset=offset
            )

        return {
            "status": "completed",
            **_build_adapter_metadata(adapter, ticket_id, is_routed),
            "operation": "list_comments",
            "comments": [comment.model_dump() for comment in comments],
            "count": len(comments),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list comments: {str(e)}",
        }
