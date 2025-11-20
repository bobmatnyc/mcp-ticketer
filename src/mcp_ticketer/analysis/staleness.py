"""Stale ticket detection based on age and activity.

This module identifies tickets that may need closing or review based on:
- Age: How long since the ticket was created
- Inactivity: How long since the last update
- State: Tickets in certain states (open, waiting, blocked)
- Priority: Lower priority tickets are more likely to be stale

The staleness score combines these factors to identify candidates for cleanup.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..core.models import Task, TicketState


class StalenessResult(BaseModel):
    """Result of staleness analysis for a ticket.

    Attributes:
        ticket_id: ID of the stale ticket
        ticket_title: Title of the stale ticket
        ticket_state: Current state of the ticket
        age_days: Days since ticket was created
        days_since_update: Days since last update
        days_since_comment: Days since last comment (if available)
        staleness_score: Overall staleness score (0.0-1.0, higher = staler)
        suggested_action: Recommended action (close, review, keep)
        reason: Human-readable explanation

    """

    ticket_id: str
    ticket_title: str
    ticket_state: str
    age_days: int
    days_since_update: int
    days_since_comment: int | None
    staleness_score: float  # 0.0-1.0
    suggested_action: str  # "close", "review", "keep"
    reason: str


class StaleTicketDetector:
    """Detects stale tickets based on age and activity.

    Analyzes tickets to find those that are old, inactive, and may be
    candidates for closing or review. Uses configurable thresholds for
    age and activity, along with state and priority factors.

    Attributes:
        age_threshold: Minimum age in days to consider
        activity_threshold: Days without activity to consider stale
        check_states: List of states to check for staleness

    """

    def __init__(
        self,
        age_threshold_days: int = 90,
        activity_threshold_days: int = 30,
        check_states: list["TicketState"] | None = None,
    ):
        """Initialize the stale ticket detector.

        Args:
            age_threshold_days: Minimum age to consider (default: 90)
            activity_threshold_days: Days without activity (default: 30)
            check_states: Ticket states to check (default: open, waiting, blocked)

        """
        from ..core.models import TicketState

        self.age_threshold = age_threshold_days
        self.activity_threshold = activity_threshold_days
        self.check_states = check_states or [
            TicketState.OPEN,
            TicketState.WAITING,
            TicketState.BLOCKED,
        ]

    def find_stale_tickets(
        self,
        tickets: list["Task"],
        limit: int = 50,
    ) -> list[StalenessResult]:
        """Find stale tickets that may need attention.

        Args:
            tickets: List of tickets to analyze
            limit: Maximum results

        Returns:
            List of staleness results, sorted by staleness score

        """
        now = datetime.now()
        results = []

        for ticket in tickets:
            # Skip tickets not in check_states
            if ticket.state not in self.check_states:
                continue

            # Calculate metrics
            age_days = self._days_since(ticket.created_at, now)
            days_since_update = self._days_since(ticket.updated_at, now)

            # Check staleness criteria
            is_old = age_days > self.age_threshold
            is_inactive = days_since_update > self.activity_threshold

            if is_old and is_inactive:
                staleness_score = self._calculate_staleness_score(
                    age_days, days_since_update, ticket
                )

                result = StalenessResult(
                    ticket_id=ticket.id or "unknown",
                    ticket_title=ticket.title,
                    ticket_state=(
                        ticket.state.value
                        if hasattr(ticket.state, "value")
                        else str(ticket.state)
                    ),
                    age_days=age_days,
                    days_since_update=days_since_update,
                    days_since_comment=None,  # Can be enhanced with comment data
                    staleness_score=staleness_score,
                    suggested_action=self._suggest_action(staleness_score),
                    reason=self._build_reason(age_days, days_since_update, ticket),
                )
                results.append(result)

        # Sort by staleness score
        results.sort(key=lambda x: x.staleness_score, reverse=True)
        return results[:limit]

    def _days_since(self, dt: datetime | None, now: datetime) -> int:
        """Calculate days since a datetime.

        Args:
            dt: Datetime to calculate from
            now: Current datetime

        Returns:
            Number of days since dt (0 if dt is None)

        """
        if dt is None:
            return 0
        # Handle timezone-aware and naive datetimes
        if dt.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=dt.tzinfo)
        elif dt.tzinfo is None and now.tzinfo is not None:
            dt = dt.replace(tzinfo=now.tzinfo)
        return (now - dt).days

    def _calculate_staleness_score(
        self,
        age_days: int,
        days_since_update: int,
        ticket: "Task",
    ) -> float:
        """Calculate staleness score (0.0-1.0, higher = staler).

        Args:
            age_days: Days since creation
            days_since_update: Days since last update
            ticket: The ticket being analyzed

        Returns:
            Staleness score between 0.0 and 1.0

        """
        from ..core.models import Priority, TicketState

        # Base score from age and inactivity
        age_factor = min(age_days / 365, 1.0)  # Normalize to 1 year
        activity_factor = min(days_since_update / 180, 1.0)  # Normalize to 6 months

        base_score = (age_factor + activity_factor) / 2

        # Priority adjustment (low priority = more stale)
        priority_weights = {
            Priority.CRITICAL: 0.0,
            Priority.HIGH: 0.3,
            Priority.MEDIUM: 0.7,
            Priority.LOW: 1.0,
        }
        priority_factor = priority_weights.get(ticket.priority, 0.5)

        # State adjustment
        state_weights = {
            TicketState.BLOCKED: 0.8,  # Blocked tickets are very stale
            TicketState.WAITING: 0.9,  # Waiting tickets are very stale
            TicketState.OPEN: 0.6,
        }
        state_factor = state_weights.get(ticket.state, 0.5)

        # Weighted combination
        final_score = base_score * 0.5 + priority_factor * 0.3 + state_factor * 0.2

        return min(final_score, 1.0)

    def _suggest_action(self, score: float) -> str:
        """Suggest action based on staleness score.

        Args:
            score: Staleness score

        Returns:
            Suggested action string

        """
        if score > 0.8:
            return "close"  # Very stale, likely won't be done
        elif score > 0.6:
            return "review"  # Moderately stale, needs review
        else:
            return "keep"  # Still relevant

    def _build_reason(
        self,
        age_days: int,
        days_since_update: int,
        ticket: "Task",
    ) -> str:
        """Build human-readable reason string.

        Args:
            age_days: Days since creation
            days_since_update: Days since last update
            ticket: The ticket being analyzed

        Returns:
            Human-readable explanation

        """
        from ..core.models import Priority, TicketState

        reasons = []

        if age_days > 365:
            reasons.append(f"created {age_days} days ago")
        elif age_days > self.age_threshold:
            reasons.append(f"old ({age_days} days)")

        if days_since_update > 180:
            reasons.append(f"no updates for {days_since_update} days")
        elif days_since_update > self.activity_threshold:
            reasons.append(f"inactive for {days_since_update} days")

        if ticket.state == TicketState.BLOCKED:
            reasons.append("blocked state")
        elif ticket.state == TicketState.WAITING:
            reasons.append("waiting state")

        if ticket.priority == Priority.LOW:
            reasons.append("low priority")

        return ", ".join(reasons)
