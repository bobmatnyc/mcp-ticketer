"""Type definitions and mappings for Jira adapter."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any

from ...core.models import Priority, TicketState

logger = logging.getLogger(__name__)


class JiraIssueType(str, Enum):
    """Common JIRA issue types."""

    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"
    SUBTASK = "Sub-task"
    IMPROVEMENT = "Improvement"
    NEW_FEATURE = "New Feature"


class JiraPriority(str, Enum):
    """Standard JIRA priority levels."""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


def get_state_mapping() -> dict[TicketState, str]:
    """Map universal states to common JIRA workflow states.

    Returns:
    -------
        Dictionary mapping TicketState enum values to JIRA status names

    """
    return {
        TicketState.OPEN: "To Do",
        TicketState.IN_PROGRESS: "In Progress",
        TicketState.READY: "In Review",
        TicketState.TESTED: "Testing",
        TicketState.DONE: "Done",
        TicketState.WAITING: "Waiting",
        TicketState.BLOCKED: "Blocked",
        TicketState.CLOSED: "Closed",
    }


def map_priority_to_jira(priority: Priority) -> str:
    """Map universal priority to JIRA priority.

    Args:
    ----
        priority: Universal Priority enum value

    Returns:
    -------
        JIRA priority string

    """
    mapping = {
        Priority.CRITICAL: JiraPriority.HIGHEST,
        Priority.HIGH: JiraPriority.HIGH,
        Priority.MEDIUM: JiraPriority.MEDIUM,
        Priority.LOW: JiraPriority.LOW,
    }
    return mapping.get(priority, JiraPriority.MEDIUM)


def map_priority_from_jira(jira_priority: dict[str, Any] | None) -> Priority:
    """Map JIRA priority to universal priority.

    Args:
    ----
        jira_priority: JIRA priority dictionary with 'name' field

    Returns:
    -------
        Universal Priority enum value

    """
    if not jira_priority:
        return Priority.MEDIUM

    name = jira_priority.get("name", "").lower()

    if "highest" in name or "urgent" in name or "critical" in name:
        return Priority.CRITICAL
    elif "high" in name:
        return Priority.HIGH
    elif "low" in name:
        return Priority.LOW
    else:
        return Priority.MEDIUM


def map_state_from_jira(status: dict[str, Any]) -> TicketState:
    """Map JIRA status to universal state.

    Args:
    ----
        status: JIRA status dictionary with 'name' and 'statusCategory' fields

    Returns:
    -------
        Universal TicketState enum value

    """
    if not status:
        return TicketState.OPEN

    name = status.get("name", "").lower()
    category = status.get("statusCategory", {}).get("key", "").lower()

    # Try to match by category first (more reliable)
    if category == "new":
        return TicketState.OPEN
    elif category == "indeterminate":
        return TicketState.IN_PROGRESS
    elif category == "done":
        return TicketState.DONE

    # Fall back to name matching
    if "block" in name:
        return TicketState.BLOCKED
    elif "wait" in name:
        return TicketState.WAITING
    elif "progress" in name or "doing" in name:
        return TicketState.IN_PROGRESS
    elif "review" in name:
        return TicketState.READY
    elif "test" in name:
        return TicketState.TESTED
    elif "done" in name or "resolved" in name:
        return TicketState.DONE
    elif "closed" in name:
        return TicketState.CLOSED
    else:
        return TicketState.OPEN


def parse_jira_datetime(date_str: str) -> datetime | None:
    """Parse JIRA datetime strings which can be in various formats.

    JIRA can return dates in formats like:
    - 2025-10-24T14:12:18.771-0400
    - 2025-10-24T14:12:18.771Z
    - 2025-10-24T14:12:18.771+00:00

    Args:
    ----
        date_str: JIRA datetime string

    Returns:
    -------
        datetime object or None if parsing fails

    """
    if not date_str:
        return None

    try:
        # Handle Z timezone
        if date_str.endswith("Z"):
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Handle timezone formats like -0400, +0500 (need to add colon)
        if re.match(r".*[+-]\d{4}$", date_str):
            # Insert colon in timezone: -0400 -> -04:00
            date_str = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", date_str)

        return datetime.fromisoformat(date_str)

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse JIRA datetime '{date_str}': {e}")
        return None


def extract_text_from_adf(adf_content: str | dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format (ADF).

    Args:
    ----
        adf_content: Either a string (already plain text) or ADF document dict

    Returns:
    -------
        Plain text string extracted from the ADF content

    """
    if isinstance(adf_content, str):
        return adf_content

    if not isinstance(adf_content, dict):
        return str(adf_content) if adf_content else ""

    def extract_text_recursive(node: dict[str, Any]) -> str:
        """Recursively extract text from ADF nodes."""
        if not isinstance(node, dict):
            return ""

        # If this is a text node, return its text
        if node.get("type") == "text":
            return node.get("text", "")

        # If this node has content, process it recursively
        content = node.get("content", [])
        if isinstance(content, list):
            return "".join(extract_text_recursive(child) for child in content)

        return ""

    try:
        return extract_text_recursive(adf_content)
    except Exception as e:
        logger.warning(f"Failed to extract text from ADF: {e}")
        return str(adf_content) if adf_content else ""


def convert_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text to Atlassian Document Format (ADF).

    ADF is required for JIRA Cloud description fields.
    This creates a simple document with paragraphs for each line.

    Args:
    ----
        text: Plain text to convert

    Returns:
    -------
        ADF document dictionary

    """
    if not text:
        return {"type": "doc", "version": 1, "content": []}

    # Split text into lines and create paragraphs
    lines = text.split("\n")
    content = []

    for line in lines:
        if line.strip():  # Non-empty line
            content.append(
                {"type": "paragraph", "content": [{"type": "text", "text": line}]}
            )
        else:  # Empty line becomes empty paragraph
            content.append({"type": "paragraph", "content": []})

    return {"type": "doc", "version": 1, "content": content}


def convert_from_adf(adf_content: Any) -> str:
    """Convert Atlassian Document Format (ADF) to plain text.

    This extracts text content from ADF structure for display.

    Args:
    ----
        adf_content: ADF document or plain string

    Returns:
    -------
        Plain text string

    """
    if not adf_content:
        return ""

    # If it's already a string, return it (JIRA Server)
    if isinstance(adf_content, str):
        return adf_content

    # Handle ADF structure
    if not isinstance(adf_content, dict):
        return str(adf_content)

    content_nodes = adf_content.get("content", [])
    lines = []

    for node in content_nodes:
        if node.get("type") == "paragraph":
            paragraph_text = ""
            for content_item in node.get("content", []):
                if content_item.get("type") == "text":
                    paragraph_text += content_item.get("text", "")
            lines.append(paragraph_text)
        elif node.get("type") == "heading":
            heading_text = ""
            for content_item in node.get("content", []):
                if content_item.get("type") == "text":
                    heading_text += content_item.get("text", "")
            lines.append(heading_text)

    return "\n".join(lines)
