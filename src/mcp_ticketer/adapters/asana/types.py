"""Asana-specific types, constants, and state mappings."""

from enum import Enum

from ...core.models import Priority, TicketState


class AsanaCustomFieldType(str, Enum):
    """Asana custom field types."""

    TEXT = "text"
    NUMBER = "number"
    ENUM = "enum"
    MULTI_ENUM = "multi_enum"
    DATE = "date"
    PEOPLE = "people"


class AsanaStateMapping:
    """Mapping between universal TicketState and Asana states.

    Asana doesn't have built-in workflow states like Linear or JIRA.
    Instead, we use:
    - completed boolean field (true/false)
    - Custom field for extended states (if configured)

    For now, we'll use a simple completed boolean mapping:
    - DONE, CLOSED → completed = true
    - All others → completed = false
    """

    TO_ASANA = {
        TicketState.OPEN: False,
        TicketState.IN_PROGRESS: False,
        TicketState.READY: False,
        TicketState.TESTED: False,
        TicketState.DONE: True,
        TicketState.WAITING: False,
        TicketState.BLOCKED: False,
        TicketState.CLOSED: True,
    }

    FROM_ASANA = {
        True: TicketState.DONE,  # completed = true
        False: TicketState.OPEN,  # completed = false (default to OPEN)
    }


class AsanaPriorityMapping:
    """Mapping between universal Priority and Asana custom field values.

    Asana doesn't have built-in priority field. We'll use custom enum field.
    If no custom field exists, we store priority in tags.
    """

    TO_ASANA = {
        Priority.LOW: "Low",
        Priority.MEDIUM: "Medium",
        Priority.HIGH: "High",
        Priority.CRITICAL: "Critical",
    }

    FROM_ASANA = {
        "low": Priority.LOW,
        "medium": Priority.MEDIUM,
        "high": Priority.HIGH,
        "critical": Priority.CRITICAL,
        "urgent": Priority.CRITICAL,  # Map "urgent" to critical
    }


def map_priority_to_asana(priority: Priority) -> str:
    """Map universal priority to Asana custom field value.

    Args:
        priority: Universal priority level

    Returns:
        Asana priority string

    """
    return AsanaPriorityMapping.TO_ASANA.get(priority, "Medium")


def map_priority_from_asana(asana_priority: str | None) -> Priority:
    """Map Asana custom field value to universal priority.

    Args:
        asana_priority: Asana priority string (can be None)

    Returns:
        Universal priority level

    """
    if not asana_priority:
        return Priority.MEDIUM

    return AsanaPriorityMapping.FROM_ASANA.get(asana_priority.lower(), Priority.MEDIUM)


def map_state_to_asana(state: TicketState) -> bool:
    """Map universal state to Asana completed boolean.

    Args:
        state: Universal ticket state

    Returns:
        True if completed, False otherwise

    """
    return AsanaStateMapping.TO_ASANA.get(state, False)


def map_state_from_asana(
    completed: bool, custom_state: str | None = None
) -> TicketState:
    """Map Asana completed boolean to universal state.

    Args:
        completed: Asana completed boolean
        custom_state: Optional custom field state value

    Returns:
        Universal ticket state

    """
    # If custom state provided, try to map it
    if custom_state:
        state_lower = custom_state.lower()
        if "progress" in state_lower or "started" in state_lower:
            return TicketState.IN_PROGRESS
        if "ready" in state_lower or "review" in state_lower:
            return TicketState.READY
        if "test" in state_lower:
            return TicketState.TESTED
        if "wait" in state_lower:
            return TicketState.WAITING
        if "block" in state_lower:
            return TicketState.BLOCKED
        if "done" in state_lower or "complete" in state_lower:
            return TicketState.DONE
        if "closed" in state_lower or "cancel" in state_lower:
            return TicketState.CLOSED

    # Fallback to simple completed boolean mapping
    return AsanaStateMapping.FROM_ASANA.get(completed, TicketState.OPEN)
