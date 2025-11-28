"""Project health assessment for epics and projects.

This module evaluates project health based on:
- Completion rate (% of tickets done)
- Progress rate (% of tickets in progress)
- Blocker rate (% of tickets blocked)
- Priority distribution
- Work distribution balance
"""

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from ..core.models import Task


class ProjectHealth(str, Enum):
    """Project health status levels.

    Attributes:
        ON_TRACK: Project is progressing well, no major issues
        AT_RISK: Project has some concerns but still recoverable
        OFF_TRACK: Project has serious issues requiring intervention

    """

    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    OFF_TRACK = "off_track"


class HealthMetrics(BaseModel):
    """Calculated health metrics for a project.

    Attributes:
        total_tickets: Total number of tickets
        completion_rate: Percentage of tickets done (0.0-1.0)
        progress_rate: Percentage of tickets in progress (0.0-1.0)
        blocked_rate: Percentage of tickets blocked (0.0-1.0)
        critical_count: Number of critical priority tickets
        high_count: Number of high priority tickets
        health_score: Overall health score (0.0-1.0, higher is better)
        health_status: Overall health status

    """

    total_tickets: int
    completion_rate: float
    progress_rate: float
    blocked_rate: float
    critical_count: int
    high_count: int
    health_score: float
    health_status: ProjectHealth


class HealthAssessor:
    """Assess project health based on ticket metrics.

    Uses weighted scoring of multiple factors:
    - Completion rate (30% weight): How many tickets are done
    - Progress rate (25% weight): How many tickets are actively worked
    - Blocker rate (30% weight): How many tickets are blocked (negative)
    - Priority balance (15% weight): Critical/high priority completion
    """

    # Thresholds for health determination
    HEALTHY_COMPLETION_THRESHOLD = 0.5
    HEALTHY_PROGRESS_THRESHOLD = 0.2
    RISKY_BLOCKED_THRESHOLD = 0.2
    CRITICAL_BLOCKED_THRESHOLD = 0.4

    # Weights for health score calculation
    COMPLETION_WEIGHT = 0.30
    PROGRESS_WEIGHT = 0.25
    BLOCKER_WEIGHT = 0.30
    PRIORITY_WEIGHT = 0.15

    def __init__(self) -> None:
        """Initialize the health assessor."""
        pass

    def assess(self, tickets: list["Task"]) -> HealthMetrics:
        """Assess project health from a list of tickets.

        Args:
            tickets: List of tickets in the project

        Returns:
            Health metrics including status and score

        """
        if not tickets:
            return HealthMetrics(
                total_tickets=0,
                completion_rate=0.0,
                progress_rate=0.0,
                blocked_rate=0.0,
                critical_count=0,
                high_count=0,
                health_score=0.0,
                health_status=ProjectHealth.OFF_TRACK,
            )

        total = len(tickets)

        # Calculate state-based metrics
        completion_rate = self._calculate_completion_rate(tickets)
        progress_rate = self._calculate_progress_rate(tickets)
        blocked_rate = self._calculate_blocked_rate(tickets)

        # Count priority tickets
        critical_count = self._count_by_priority(tickets, "critical")
        high_count = self._count_by_priority(tickets, "high")

        # Calculate overall health score
        health_score = self._calculate_health_score(
            completion_rate, progress_rate, blocked_rate, tickets
        )

        # Determine health status
        health_status = self._determine_health_status(
            completion_rate, progress_rate, blocked_rate, health_score
        )

        return HealthMetrics(
            total_tickets=total,
            completion_rate=completion_rate,
            progress_rate=progress_rate,
            blocked_rate=blocked_rate,
            critical_count=critical_count,
            high_count=high_count,
            health_score=health_score,
            health_status=health_status,
        )

    def _calculate_completion_rate(self, tickets: list["Task"]) -> float:
        """Calculate percentage of completed tickets."""
        from ..core.models import TicketState

        if not tickets:
            return 0.0

        completed = sum(
            1
            for t in tickets
            if t.state in (TicketState.DONE, TicketState.CLOSED, TicketState.TESTED)
        )
        return completed / len(tickets)

    def _calculate_progress_rate(self, tickets: list["Task"]) -> float:
        """Calculate percentage of in-progress tickets."""
        from ..core.models import TicketState

        if not tickets:
            return 0.0

        in_progress = sum(
            1
            for t in tickets
            if t.state
            in (TicketState.IN_PROGRESS, TicketState.READY, TicketState.TESTED)
        )
        return in_progress / len(tickets)

    def _calculate_blocked_rate(self, tickets: list["Task"]) -> float:
        """Calculate percentage of blocked tickets."""
        from ..core.models import TicketState

        if not tickets:
            return 0.0

        blocked = sum(
            1 for t in tickets if t.state in (TicketState.BLOCKED, TicketState.WAITING)
        )
        return blocked / len(tickets)

    def _count_by_priority(self, tickets: list["Task"], priority: str) -> int:
        """Count tickets with a specific priority."""
        # Handle both enum and string values
        return sum(
            1
            for t in tickets
            if t.priority
            and (t.priority.value if hasattr(t.priority, "value") else t.priority)
            == priority
        )

    def _calculate_health_score(
        self,
        completion_rate: float,
        progress_rate: float,
        blocked_rate: float,
        tickets: list["Task"],
    ) -> float:
        """Calculate weighted health score.

        Args:
            completion_rate: Percentage of completed tickets
            progress_rate: Percentage of in-progress tickets
            blocked_rate: Percentage of blocked tickets
            tickets: All tickets (for priority analysis)

        Returns:
            Health score from 0.0 (worst) to 1.0 (best)

        """
        # Completion score (0.0-1.0)
        completion_score = completion_rate

        # Progress score (0.0-1.0, capped at reasonable level)
        # Having some progress is good, but 100% in progress isn't ideal
        progress_score = min(progress_rate * 2, 1.0)

        # Blocker score (0.0-1.0, inverted since blockers are bad)
        blocker_score = max(0.0, 1.0 - (blocked_rate * 2.5))

        # Priority score: Check if critical/high priority items are addressed
        priority_score = self._calculate_priority_score(tickets)

        # Weighted average
        health_score = (
            completion_score * self.COMPLETION_WEIGHT
            + progress_score * self.PROGRESS_WEIGHT
            + blocker_score * self.BLOCKER_WEIGHT
            + priority_score * self.PRIORITY_WEIGHT
        )

        return min(1.0, max(0.0, health_score))

    def _calculate_priority_score(self, tickets: list["Task"]) -> float:
        """Calculate score based on critical/high priority completion.

        Returns:
            Score from 0.0-1.0 based on priority ticket completion

        """
        from ..core.models import Priority, TicketState

        critical_tickets = [
            t
            for t in tickets
            if t.priority == Priority.CRITICAL or t.priority == Priority.HIGH
        ]

        if not critical_tickets:
            return 1.0  # No high priority items = good score

        completed_critical = sum(
            1
            for t in critical_tickets
            if t.state in (TicketState.DONE, TicketState.CLOSED, TicketState.TESTED)
        )

        in_progress_critical = sum(
            1
            for t in critical_tickets
            if t.state in (TicketState.IN_PROGRESS, TicketState.READY)
        )

        # Score: 1.0 for completed, 0.5 for in progress, 0.0 for not started
        score = (completed_critical + 0.5 * in_progress_critical) / len(
            critical_tickets
        )

        return score

    def _determine_health_status(
        self,
        completion_rate: float,
        progress_rate: float,
        blocked_rate: float,
        health_score: float,
    ) -> ProjectHealth:
        """Determine overall health status from metrics.

        Args:
            completion_rate: Percentage of completed tickets
            progress_rate: Percentage of in-progress tickets
            blocked_rate: Percentage of blocked tickets
            health_score: Overall health score

        Returns:
            Health status (ON_TRACK, AT_RISK, or OFF_TRACK)

        """
        # Critical thresholds take priority
        if blocked_rate >= self.CRITICAL_BLOCKED_THRESHOLD:
            return ProjectHealth.OFF_TRACK

        # Check for on-track conditions
        if completion_rate >= self.HEALTHY_COMPLETION_THRESHOLD and blocked_rate == 0.0:
            return ProjectHealth.ON_TRACK

        # Use health score as tie-breaker
        if health_score >= 0.7:
            return ProjectHealth.ON_TRACK
        elif health_score >= 0.4:
            return ProjectHealth.AT_RISK
        else:
            return ProjectHealth.OFF_TRACK
