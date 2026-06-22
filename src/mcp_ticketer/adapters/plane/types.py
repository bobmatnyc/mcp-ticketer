"""Plane-specific types, constants, and state mappings.

Plane organises issue states into *state groups* (backlog, unstarted, started,
completed, cancelled) with one or more named states per group, configured
per-project. Unlike Asana (a simple completed boolean), Plane has real
workflow states, so the mapping here resolves a universal ``TicketState`` to a
concrete state UUID by matching first on the state *name* and then falling back
to the state *group*.
"""

from enum import Enum

from ...core.models import Priority, TicketState


class PlaneStateGroup(str, Enum):
    """Plane state groups.

    Every Plane state belongs to exactly one of these groups. The group is the
    most reliable signal for mapping to a universal ``TicketState`` because the
    per-project state *names* are user-defined and free-form.
    """

    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PlanePriority(str, Enum):
    """Plane priority values (native API enum)."""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


# Universal TicketState -> Plane state group.
#
# This is the coarse mapping used to choose a target state when transitioning.
# The adapter refines the choice by also matching on the state name (see
# ``resolve_state_id`` in the adapter) so richer universal states such as
# READY / TESTED / WAITING / BLOCKED land on an appropriately named state when
# the project defines one.
STATE_TO_GROUP: dict[TicketState, PlaneStateGroup] = {
    TicketState.OPEN: PlaneStateGroup.UNSTARTED,
    TicketState.IN_PROGRESS: PlaneStateGroup.STARTED,
    TicketState.READY: PlaneStateGroup.STARTED,
    TicketState.TESTED: PlaneStateGroup.STARTED,
    TicketState.DONE: PlaneStateGroup.COMPLETED,
    TicketState.WAITING: PlaneStateGroup.STARTED,
    TicketState.BLOCKED: PlaneStateGroup.STARTED,
    TicketState.CLOSED: PlaneStateGroup.CANCELLED,
}


# Plane state group -> universal TicketState.
#
# Used when reading an issue back. Group is authoritative; the adapter applies
# name-based refinement on top of this for fine-grained states.
GROUP_TO_STATE: dict[PlaneStateGroup, TicketState] = {
    PlaneStateGroup.BACKLOG: TicketState.OPEN,
    PlaneStateGroup.UNSTARTED: TicketState.OPEN,
    PlaneStateGroup.STARTED: TicketState.IN_PROGRESS,
    PlaneStateGroup.COMPLETED: TicketState.DONE,
    PlaneStateGroup.CANCELLED: TicketState.CLOSED,
}


# Keyword hints used to refine a universal state from a Plane state *name*.
# Order matters: the first universal state whose keywords match the (lowercased)
# state name wins. Only states that are otherwise indistinguishable by group
# are listed here; DONE/CLOSED/OPEN are handled by the group mapping.
STATE_NAME_KEYWORDS: list[tuple[TicketState, tuple[str, ...]]] = [
    (TicketState.BLOCKED, ("blocked", "stuck", "impediment")),
    (TicketState.WAITING, ("waiting", "on hold", "hold", "paused")),
    (TicketState.TESTED, ("tested", "qa", "verified", "verify")),
    (TicketState.READY, ("ready", "review", "in review")),
    (TicketState.IN_PROGRESS, ("progress", "started", "doing", "active")),
]


# Universal Priority -> Plane priority.
TO_PLANE_PRIORITY: dict[Priority, str] = {
    Priority.LOW: PlanePriority.LOW.value,
    Priority.MEDIUM: PlanePriority.MEDIUM.value,
    Priority.HIGH: PlanePriority.HIGH.value,
    Priority.CRITICAL: PlanePriority.URGENT.value,
}


# Plane priority -> universal Priority.
FROM_PLANE_PRIORITY: dict[str, Priority] = {
    PlanePriority.URGENT.value: Priority.CRITICAL,
    PlanePriority.HIGH.value: Priority.HIGH,
    PlanePriority.MEDIUM.value: Priority.MEDIUM,
    PlanePriority.LOW.value: Priority.LOW,
    PlanePriority.NONE.value: Priority.MEDIUM,
}


def map_priority_to_plane(priority: Priority) -> str:
    """Map universal priority to a Plane priority value.

    Args:
        priority: Universal priority level.

    Returns:
        Plane priority string (one of urgent/high/medium/low/none).

    """
    return TO_PLANE_PRIORITY.get(priority, PlanePriority.MEDIUM.value)


def map_priority_from_plane(plane_priority: str | None) -> Priority:
    """Map a Plane priority value to a universal priority.

    Args:
        plane_priority: Plane priority string (may be None).

    Returns:
        Universal priority level.

    """
    if not plane_priority:
        return Priority.MEDIUM
    return FROM_PLANE_PRIORITY.get(plane_priority.lower(), Priority.MEDIUM)


def refine_state_from_name(
    group_state: TicketState, state_name: str | None
) -> TicketState:
    """Refine a group-derived state using the Plane state name.

    The state *group* gives a coarse state (e.g. STARTED -> IN_PROGRESS). When
    the project defines more granular states (e.g. a "Blocked" or "Ready for
    review" state, both in the ``started`` group), the name lets us recover the
    richer universal state.

    Completed and cancelled groups are never refined: a completed state always
    maps to DONE and a cancelled state always maps to CLOSED.

    Args:
        group_state: Universal state derived from the Plane state group.
        state_name: The Plane state name (may be None).

    Returns:
        The refined universal ticket state.

    """
    if group_state in (TicketState.DONE, TicketState.CLOSED):
        return group_state

    if not state_name:
        return group_state

    name_lower = state_name.lower()
    for state, keywords in STATE_NAME_KEYWORDS:
        if any(keyword in name_lower for keyword in keywords):
            return state

    return group_state
