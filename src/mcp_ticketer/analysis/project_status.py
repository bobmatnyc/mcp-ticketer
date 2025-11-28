"""Project status analysis and work plan generation.

This module provides comprehensive project/epic analysis including:
- Status breakdown by state, priority, assignee
- Dependency analysis and critical path
- Health assessment
- Next ticket recommendations
- Actionable recommendations for project managers
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .dependency_graph import DependencyGraph
from .health_assessment import HealthAssessor, HealthMetrics, ProjectHealth

if TYPE_CHECKING:
    from ..core.models import Task


def _get_value(enum_or_str: Any) -> str:
    """Safely get value from enum or string.

    Args:
        enum_or_str: Either an enum with .value or a string

    Returns:
        String value
    """
    return enum_or_str.value if hasattr(enum_or_str, "value") else enum_or_str


class TicketRecommendation(BaseModel):
    """Recommended ticket to work on next.

    Attributes:
        ticket_id: ID of the recommended ticket
        title: Title of the ticket
        priority: Priority level
        reason: Explanation of why this ticket is recommended
        blocks: List of ticket IDs this ticket blocks (if any)
        impact_score: Numeric score for impact (higher = more important)

    """

    ticket_id: str
    title: str
    priority: str
    reason: str
    blocks: list[str] = []
    impact_score: float = 0.0


class ProjectStatusResult(BaseModel):
    """Complete project status analysis result.

    Attributes:
        project_id: ID of the project/epic
        project_name: Name of the project/epic
        health: Overall project health status
        health_metrics: Detailed health metrics
        summary: Ticket count by state
        priority_summary: Ticket count by priority
        work_distribution: Ticket count by assignee
        recommended_next: Top tickets to start next
        blockers: Tickets that are blocking others
        critical_path: Longest dependency chain
        recommendations: Actionable recommendations for PMs
        timeline_estimate: Timeline projections (if applicable)

    """

    project_id: str
    project_name: str
    health: str
    health_metrics: HealthMetrics
    summary: dict[str, int]
    priority_summary: dict[str, int]
    work_distribution: dict[str, dict[str, int]]
    recommended_next: list[TicketRecommendation]
    blockers: list[dict[str, Any]]
    critical_path: list[str]
    recommendations: list[str]
    timeline_estimate: dict[str, Any]


class StatusAnalyzer:
    """Analyze project/epic status and generate work plans.

    Combines multiple analysis techniques:
    1. State and priority analysis
    2. Dependency graph analysis
    3. Health assessment
    4. Work distribution analysis
    5. Intelligent recommendations
    """

    def __init__(self) -> None:
        """Initialize the status analyzer."""
        self.health_assessor = HealthAssessor()

    def analyze(
        self, project_id: str, project_name: str, tickets: list["Task"]
    ) -> ProjectStatusResult:
        """Perform comprehensive project status analysis.

        Args:
            project_id: ID of the project/epic
            project_name: Name of the project/epic
            tickets: List of tickets in the project

        Returns:
            Complete project status analysis

        """
        # Basic state and priority analysis
        summary = self._build_state_summary(tickets)
        priority_summary = self._build_priority_summary(tickets)
        work_distribution = self._build_work_distribution(tickets)

        # Dependency analysis
        dep_graph = self._build_dependency_graph(tickets)
        critical_path = dep_graph.get_critical_path()
        blockers = self._identify_blockers(dep_graph, tickets)

        # Health assessment
        health_metrics = self.health_assessor.assess(tickets)

        # Generate recommendations
        recommended_next = self._recommend_next_tickets(
            tickets, dep_graph, health_metrics
        )
        recommendations = self._generate_recommendations(
            tickets, dep_graph, health_metrics, blockers
        )

        # Timeline estimation
        timeline_estimate = self._estimate_timeline(tickets, dep_graph)

        return ProjectStatusResult(
            project_id=project_id,
            project_name=project_name,
            health=health_metrics.health_status.value,
            health_metrics=health_metrics,
            summary=summary,
            priority_summary=priority_summary,
            work_distribution=work_distribution,
            recommended_next=recommended_next,
            blockers=blockers,
            critical_path=critical_path,
            recommendations=recommendations,
            timeline_estimate=timeline_estimate,
        )

    def _build_state_summary(self, tickets: list["Task"]) -> dict[str, int]:
        """Build summary of tickets by state.

        Args:
            tickets: List of tickets

        Returns:
            Dictionary mapping state -> count

        """
        summary: dict[str, int] = defaultdict(int)
        summary["total"] = len(tickets)

        for ticket in tickets:
            if ticket.state:
                state_value = _get_value(ticket.state)
                summary[state_value] = summary.get(state_value, 0) + 1

        return dict(summary)

    def _build_priority_summary(self, tickets: list["Task"]) -> dict[str, int]:
        """Build summary of tickets by priority.

        Args:
            tickets: List of tickets

        Returns:
            Dictionary mapping priority -> count

        """
        summary: dict[str, int] = defaultdict(int)

        for ticket in tickets:
            if ticket.priority:
                priority_value = _get_value(ticket.priority)
                summary[priority_value] = summary.get(priority_value, 0) + 1

        return dict(summary)

    def _build_work_distribution(
        self, tickets: list["Task"]
    ) -> dict[str, dict[str, int]]:
        """Build work distribution by assignee.

        Args:
            tickets: List of tickets

        Returns:
            Dictionary mapping assignee -> {state: count}

        """
        distribution: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for ticket in tickets:
            assignee = ticket.assignee or "unassigned"
            state = _get_value(ticket.state) if ticket.state else "unknown"

            distribution[assignee]["total"] = distribution[assignee].get("total", 0) + 1
            distribution[assignee][state] = distribution[assignee].get(state, 0) + 1

        return {k: dict(v) for k, v in distribution.items()}

    def _build_dependency_graph(self, tickets: list["Task"]) -> DependencyGraph:
        """Build dependency graph from tickets.

        Args:
            tickets: List of tickets

        Returns:
            Populated and finalized dependency graph

        """
        graph = DependencyGraph()

        for ticket in tickets:
            graph.add_ticket(ticket)

        graph.finalize()
        return graph

    def _identify_blockers(
        self, dep_graph: DependencyGraph, tickets: list["Task"]
    ) -> list[dict[str, Any]]:
        """Identify tickets that are blocking others.

        Args:
            dep_graph: Dependency graph
            tickets: List of tickets

        Returns:
            List of blocker information dicts

        """
        from ..core.models import TicketState

        blockers = []
        high_impact = dep_graph.get_high_impact_tickets()
        ticket_map = {t.id: t for t in tickets if t.id}

        for ticket_id, blocked_count in high_impact:
            ticket = ticket_map.get(ticket_id)
            if not ticket:
                continue

            # Only include if the blocker is not done
            if ticket.state not in (
                TicketState.DONE,
                TicketState.CLOSED,
                TicketState.TESTED,
            ):
                blockers.append(
                    {
                        "ticket_id": ticket_id,
                        "title": ticket.title or "",
                        "state": (
                            _get_value(ticket.state) if ticket.state else "unknown"
                        ),
                        "priority": (
                            _get_value(ticket.priority) if ticket.priority else "medium"
                        ),
                        "blocks_count": blocked_count,
                        "blocks": list(dep_graph.edges.get(ticket_id, set())),
                    }
                )

        # Sort by blocks_count descending
        return sorted(blockers, key=lambda x: x["blocks_count"], reverse=True)

    def _recommend_next_tickets(
        self,
        tickets: list["Task"],
        dep_graph: DependencyGraph,
        health_metrics: HealthMetrics,
    ) -> list[TicketRecommendation]:
        """Recommend top 3 tickets to work on next.

        Scoring factors:
        1. Priority (critical > high > medium > low)
        2. Not blocked by others
        3. Blocks other tickets (high impact)
        4. On critical path
        5. State (open > waiting)

        Args:
            tickets: List of tickets
            dep_graph: Dependency graph
            health_metrics: Health assessment results

        Returns:
            List of top 3 recommended tickets

        """
        from ..core.models import TicketState

        # Filter to actionable tickets (not done, not in progress)
        actionable = [
            t
            for t in tickets
            if t.state
            in (
                TicketState.OPEN,
                TicketState.WAITING,
                TicketState.BLOCKED,
                TicketState.READY,
            )
        ]

        if not actionable:
            return []

        # Score each ticket
        scored_tickets = []
        critical_path_set = set(dep_graph.get_critical_path())

        for ticket in actionable:
            ticket_id = ticket.id or ""
            if not ticket_id:
                continue

            score = self._calculate_ticket_score(
                ticket, ticket_id, dep_graph, critical_path_set
            )

            reason = self._generate_recommendation_reason(
                ticket, ticket_id, dep_graph, critical_path_set
            )

            blocks = list(dep_graph.edges.get(ticket_id, set()))

            scored_tickets.append(
                (
                    score,
                    TicketRecommendation(
                        ticket_id=ticket_id,
                        title=ticket.title or "",
                        priority=(
                            _get_value(ticket.priority) if ticket.priority else "medium"
                        ),
                        reason=reason,
                        blocks=blocks,
                        impact_score=score,
                    ),
                )
            )

        # Sort by score descending and return top 3
        scored_tickets.sort(key=lambda x: x[0], reverse=True)
        return [rec for _, rec in scored_tickets[:3]]

    def _calculate_ticket_score(
        self,
        ticket: "Task",
        ticket_id: str,
        dep_graph: DependencyGraph,
        critical_path_set: set[str],
    ) -> float:
        """Calculate recommendation score for a ticket.

        Args:
            ticket: The ticket to score
            ticket_id: Ticket ID
            dep_graph: Dependency graph
            critical_path_set: Set of ticket IDs on critical path

        Returns:
            Score (higher = more recommended)

        """
        from ..core.models import Priority, TicketState

        score = 0.0

        # Priority score (30 points max)
        priority_scores = {
            Priority.CRITICAL: 30.0,
            Priority.HIGH: 20.0,
            Priority.MEDIUM: 10.0,
            Priority.LOW: 5.0,
        }
        score += priority_scores.get(ticket.priority, 10.0)

        # Not blocked bonus (20 points)
        blocked_by = dep_graph.reverse_edges.get(ticket_id, set())
        if not blocked_by:
            score += 20.0
        else:
            # Penalty for being blocked
            score -= len(blocked_by) * 5.0

        # Blocks others bonus (up to 25 points)
        blocks_count = len(dep_graph.edges.get(ticket_id, set()))
        score += min(blocks_count * 5.0, 25.0)

        # Critical path bonus (15 points)
        if ticket_id in critical_path_set:
            score += 15.0

        # State bonus (10 points for ready/open)
        if ticket.state == TicketState.OPEN:
            score += 10.0
        elif ticket.state == TicketState.READY:
            score += 8.0
        elif ticket.state == TicketState.WAITING:
            score += 5.0

        return score

    def _generate_recommendation_reason(
        self,
        ticket: "Task",
        ticket_id: str,
        dep_graph: DependencyGraph,
        critical_path_set: set[str],
    ) -> str:
        """Generate human-readable reason for recommendation.

        Args:
            ticket: The ticket
            ticket_id: Ticket ID
            dep_graph: Dependency graph
            critical_path_set: Set of ticket IDs on critical path

        Returns:
            Reason string

        """
        from ..core.models import Priority

        reasons = []

        # Priority
        if ticket.priority == Priority.CRITICAL:
            reasons.append("Critical priority")
        elif ticket.priority == Priority.HIGH:
            reasons.append("High priority")

        # Impact
        blocks_count = len(dep_graph.edges.get(ticket_id, set()))
        if blocks_count > 0:
            reasons.append(
                f"Unblocks {blocks_count} ticket{'s' if blocks_count > 1 else ''}"
            )

        # Critical path
        if ticket_id in critical_path_set:
            reasons.append("On critical path")

        # Not blocked
        blocked_by = dep_graph.reverse_edges.get(ticket_id, set())
        if not blocked_by:
            reasons.append("No blockers")
        else:
            reasons.append(
                f"Blocked by {len(blocked_by)} ticket{'s' if len(blocked_by) > 1 else ''}"
            )

        return ", ".join(reasons) if reasons else "Available to start"

    def _generate_recommendations(
        self,
        tickets: list["Task"],
        dep_graph: DependencyGraph,
        health_metrics: HealthMetrics,
        blockers: list[dict[str, Any]],
    ) -> list[str]:
        """Generate actionable recommendations for project managers.

        Args:
            tickets: List of tickets
            dep_graph: Dependency graph
            health_metrics: Health metrics
            blockers: Blocker information

        Returns:
            List of recommendation strings

        """
        recommendations = []

        # Health-based recommendations
        if health_metrics.health_status == ProjectHealth.OFF_TRACK:
            recommendations.append("⚠️ Project is OFF TRACK - Immediate action required")

            if health_metrics.blocked_rate > 0.3:
                recommendations.append(
                    f"🚧 {int(health_metrics.blocked_rate * 100)}% of tickets are blocked - Focus on resolving blockers"
                )

        elif health_metrics.health_status == ProjectHealth.AT_RISK:
            recommendations.append("⚡ Project is AT RISK - Monitor closely")

        # Blocker recommendations
        if blockers:
            top_blocker = blockers[0]
            recommendations.append(
                f"🔓 Resolve {top_blocker['ticket_id']} first ({top_blocker['priority']}) - "
                f"Unblocks {top_blocker['blocks_count']} ticket{'s' if top_blocker['blocks_count'] > 1 else ''}"
            )

        # Priority recommendations
        if health_metrics.critical_count > 0:
            from ..core.models import Priority, TicketState

            critical_open = sum(
                1
                for t in tickets
                if t.priority == Priority.CRITICAL
                and t.state not in (TicketState.DONE, TicketState.CLOSED)
            )
            if critical_open > 0:
                recommendations.append(
                    f"🔥 {critical_open} critical priority ticket{'s' if critical_open > 1 else ''} need{'s' if critical_open == 1 else ''} attention"
                )

        # Progress recommendations
        if health_metrics.completion_rate == 0.0 and len(tickets) > 0:
            recommendations.append(
                "🏁 No tickets completed yet - Focus on delivering first wins"
            )

        # Work distribution recommendations
        work_dist = self._build_work_distribution(tickets)
        if len(work_dist) > 1:
            # Check for imbalanced workload
            ticket_counts = [info.get("total", 0) for info in work_dist.values()]
            if ticket_counts:
                max_tickets = max(ticket_counts)
                min_tickets = min(ticket_counts)
                if max_tickets > min_tickets * 2:
                    recommendations.append(
                        "⚖️ Workload is imbalanced - Consider redistributing tickets"
                    )

        # Default positive message
        if not recommendations:
            recommendations.append("✅ Project is on track - Continue current momentum")

        return recommendations

    def _estimate_timeline(
        self, tickets: list["Task"], dep_graph: DependencyGraph
    ) -> dict[str, Any]:
        """Estimate timeline for project completion.

        Args:
            tickets: List of tickets
            dep_graph: Dependency graph

        Returns:
            Timeline estimation information

        """
        # For now, return basic risk assessment
        # Future: Could incorporate estimates if available in ticket data
        risk_factors = []

        if any(t.priority and _get_value(t.priority) == "critical" for t in tickets):
            risk_factors.append("Multiple high-priority items")

        from ..core.models import TicketState

        completed = sum(
            1
            for t in tickets
            if t.state in (TicketState.DONE, TicketState.CLOSED, TicketState.TESTED)
        )
        if completed == 0 and len(tickets) > 0:
            risk_factors.append("No completions yet")

        blockers = dep_graph.get_blocked_tickets()
        if len(blockers) > len(tickets) * 0.3:
            risk_factors.append("High number of blocked tickets")

        return {
            "days_to_completion": None,  # Would need estimates
            "critical_path_days": None,  # Would need estimates
            "risk": ", ".join(risk_factors) if risk_factors else "On track",
        }
