"""ClickUp-specific types, constants, and state mappings."""

from ...core.models import Priority, TicketState

# ClickUp API v2 base URL.
CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"

# ClickUp priority is a small integer: 1=urgent, 2=high, 3=normal, 4=low, None=none.
# These map to/from the universal Priority enum.
PRIORITY_URGENT = 1
PRIORITY_HIGH = 2
PRIORITY_NORMAL = 3
PRIORITY_LOW = 4


class ClickUpStatusType:
    """ClickUp status "type" values returned by GET /list/{id}.

    Each ClickUp list defines its own ordered set of statuses. Every status has
    a ``type`` field that ClickUp guarantees across all lists, which lets us map
    arbitrary per-list status names back to a universal ``TicketState``:

    - ``open``: the not-started "to do" column (one per list).
    - ``custom``: any user-defined in-flight column (e.g. "in progress", "review").
    - ``done``: a completed-but-not-archived column.
    - ``closed``: the terminal "closed" column (one per list).
    """

    OPEN = "open"
    CUSTOM = "custom"
    DONE = "done"
    CLOSED = "closed"


class ClickUpPriorityMapping:
    """Mapping between universal Priority and ClickUp integer priority codes.

    ClickUp uses a fixed integer scale, unlike the per-list status names.
    """

    TO_CLICKUP = {
        Priority.LOW: PRIORITY_LOW,
        Priority.MEDIUM: PRIORITY_NORMAL,
        Priority.HIGH: PRIORITY_HIGH,
        Priority.CRITICAL: PRIORITY_URGENT,
    }

    FROM_CLICKUP = {
        PRIORITY_URGENT: Priority.CRITICAL,
        PRIORITY_HIGH: Priority.HIGH,
        PRIORITY_NORMAL: Priority.MEDIUM,
        PRIORITY_LOW: Priority.LOW,
    }


# Keyword buckets for resolving a universal TicketState to a per-list status NAME
# when the status "type" alone is not granular enough (ClickUp collapses every
# user-defined in-flight column under the single "custom" type). Ordered so the
# first matching keyword wins.
STATE_NAME_KEYWORDS: dict[TicketState, list[str]] = {
    TicketState.OPEN: ["to do", "todo", "open", "backlog", "not started", "new"],
    TicketState.IN_PROGRESS: [
        "in progress",
        "in-progress",
        "working",
        "started",
        "doing",
    ],
    TicketState.READY: ["ready", "ready for review", "review", "in review"],
    TicketState.TESTED: ["tested", "qa", "verified", "testing"],
    TicketState.DONE: ["done", "complete", "completed", "finished"],
    TicketState.WAITING: ["waiting", "on hold", "hold", "pending"],
    TicketState.BLOCKED: ["blocked", "stuck", "at risk"],
    TicketState.CLOSED: ["closed", "archived", "cancelled", "canceled"],
}


def map_priority_to_clickup(priority: Priority) -> int:
    """Map a universal priority to a ClickUp integer priority code.

    Args:
        priority: Universal priority level.

    Returns:
        ClickUp integer priority (1=urgent, 2=high, 3=normal, 4=low).

    """
    return ClickUpPriorityMapping.TO_CLICKUP.get(priority, PRIORITY_NORMAL)


def map_priority_from_clickup(clickup_priority: object) -> Priority:
    """Map a ClickUp priority value to a universal priority.

    ClickUp returns priority either as ``None`` (no priority) or as an object
    ``{"id": "1", "priority": "urgent", "orderindex": "1"}``. This helper
    accepts the raw value, an int, a numeric string, or the embedded object.

    Args:
        clickup_priority: Raw ClickUp priority value (None, int, str, or dict).

    Returns:
        Universal priority level (defaults to MEDIUM when absent/unknown).

    """
    if clickup_priority is None:
        return Priority.MEDIUM

    code: int | None = None

    if isinstance(clickup_priority, dict):
        # ClickUp embeds priority as {"id": "1", "priority": "urgent", ...}.
        raw_id = clickup_priority.get("id")
        if raw_id is not None:
            try:
                code = int(raw_id)
            except (ValueError, TypeError):
                code = None
        if code is None:
            name = str(clickup_priority.get("priority", "")).lower()
            name_to_code = {
                "urgent": PRIORITY_URGENT,
                "high": PRIORITY_HIGH,
                "normal": PRIORITY_NORMAL,
                "low": PRIORITY_LOW,
            }
            code = name_to_code.get(name)
    elif isinstance(clickup_priority, int):
        code = clickup_priority
    elif isinstance(clickup_priority, str):
        try:
            code = int(clickup_priority)
        except ValueError:
            code = None

    if code is None:
        return Priority.MEDIUM

    return ClickUpPriorityMapping.FROM_CLICKUP.get(code, Priority.MEDIUM)


def map_status_type_to_state(
    status_type: str | None, status_name: str | None
) -> TicketState:
    """Map a ClickUp status (type + name) to a universal TicketState.

    Resolution order:
    1. ``type == "open"``  -> OPEN
    2. ``type == "closed"`` -> CLOSED
    3. ``type == "done"``  -> DONE
    4. ``type == "custom"`` -> resolve by name keywords (in_progress/ready/...).
       Falls back to IN_PROGRESS for unrecognised custom columns, since a custom
       column is by definition an active, non-terminal stage.

    Args:
        status_type: ClickUp status ``type`` field ("open"/"custom"/"done"/"closed").
        status_name: ClickUp status display name (per-list, e.g. "in review").

    Returns:
        Universal ticket state.

    """
    stype = (status_type or "").lower()

    if stype == ClickUpStatusType.OPEN:
        return TicketState.OPEN
    if stype == ClickUpStatusType.CLOSED:
        return TicketState.CLOSED
    if stype == ClickUpStatusType.DONE:
        return TicketState.DONE

    # type == "custom" (or unknown): disambiguate by the display name.
    name_lower = (status_name or "").lower().strip()
    if name_lower:
        for state, keywords in STATE_NAME_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name_lower:
                    return state

    # A custom column with no recognisable name is an active stage.
    return TicketState.IN_PROGRESS


def resolve_state_to_status_name(
    state: TicketState, available_statuses: list[dict[str, object]]
) -> str | None:
    """Resolve a universal TicketState to a concrete per-list status NAME.

    Because ClickUp statuses are per-list, the adapter must pick a status name
    that actually exists in the target list. Strategy:

    1. Prefer a status whose ``type`` matches the state's category
       (OPEN->open, DONE->done, CLOSED->closed).
    2. For in-flight states, prefer a status whose name contains one of the
       state's keywords.
    3. Fall back to the first ``done``/``closed`` status for terminal states, or
       the first ``open`` status otherwise.

    Args:
        state: Universal ticket state to resolve.
        available_statuses: List of ClickUp status objects from GET /list/{id},
            each shaped ``{"status": "in progress", "type": "custom", ...}``.

    Returns:
        A matching ClickUp status name, or None if the list has no statuses.

    """
    if not available_statuses:
        return None

    def status_name(s: dict[str, object]) -> str:
        return str(s.get("status", ""))

    def status_type(s: dict[str, object]) -> str:
        return str(s.get("type", "")).lower()

    # 1. Type-category match for terminal/initial states.
    if state == TicketState.OPEN:
        for s in available_statuses:
            if status_type(s) == ClickUpStatusType.OPEN:
                return status_name(s)
    elif state == TicketState.DONE:
        for s in available_statuses:
            if status_type(s) == ClickUpStatusType.DONE:
                return status_name(s)
    elif state == TicketState.CLOSED:
        for s in available_statuses:
            if status_type(s) == ClickUpStatusType.CLOSED:
                return status_name(s)

    # 2. Keyword match against status names (handles in_progress/ready/etc.).
    keywords = STATE_NAME_KEYWORDS.get(state, [])
    for keyword in keywords:
        for s in available_statuses:
            if keyword in status_name(s).lower():
                return status_name(s)

    # 3. Sensible fallbacks by completion category.
    if state in (TicketState.DONE, TicketState.TESTED):
        for s in available_statuses:
            if status_type(s) == ClickUpStatusType.DONE:
                return status_name(s)
    if state == TicketState.CLOSED:
        for s in available_statuses:
            if status_type(s) == ClickUpStatusType.CLOSED:
                return status_name(s)

    # Default: the list's "open" status if present, else the first status.
    for s in available_statuses:
        if status_type(s) == ClickUpStatusType.OPEN:
            return status_name(s)
    return status_name(available_statuses[0])
