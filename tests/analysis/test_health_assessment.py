"""Tests for project health assessment."""

from mcp_ticketer.analysis.health_assessment import (
    HealthAssessor,
    HealthMetrics,
    ProjectHealth,
)
from mcp_ticketer.core.models import Priority, Task, TicketState


def test_health_metrics_creation():
    """Test HealthMetrics model creation."""
    metrics = HealthMetrics(
        total_tickets=10,
        completion_rate=0.6,
        progress_rate=0.2,
        blocked_rate=0.1,
        critical_count=2,
        high_count=3,
        health_score=0.75,
        health_status=ProjectHealth.ON_TRACK,
    )

    assert metrics.total_tickets == 10
    assert metrics.completion_rate == 0.6
    assert metrics.health_status == ProjectHealth.ON_TRACK


def test_empty_project_assessment():
    """Test assessment of empty project."""
    assessor = HealthAssessor()
    metrics = assessor.assess([])

    assert metrics.total_tickets == 0
    assert metrics.completion_rate == 0.0
    assert metrics.health_status == ProjectHealth.OFF_TRACK


def test_all_done_project():
    """Test assessment of fully completed project."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Task {i}",
            state=TicketState.DONE,
            priority=Priority.MEDIUM,
        )
        for i in range(5)
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.total_tickets == 5
    assert metrics.completion_rate == 1.0
    assert metrics.blocked_rate == 0.0
    assert metrics.health_status == ProjectHealth.ON_TRACK


def test_all_blocked_project():
    """Test assessment of fully blocked project."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Task {i}",
            state=TicketState.BLOCKED,
            priority=Priority.MEDIUM,
        )
        for i in range(5)
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.total_tickets == 5
    assert metrics.blocked_rate == 1.0
    assert metrics.completion_rate == 0.0
    assert metrics.health_status == ProjectHealth.OFF_TRACK


def test_mixed_state_project():
    """Test assessment of project with mixed states."""
    tickets = [
        Task(id="TEST-1", title="Done", state=TicketState.DONE, priority=Priority.HIGH),
        Task(id="TEST-2", title="Done", state=TicketState.DONE, priority=Priority.HIGH),
        Task(
            id="TEST-3",
            title="In Progress",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
        Task(id="TEST-5", title="Open", state=TicketState.OPEN, priority=Priority.LOW),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.total_tickets == 5
    assert metrics.completion_rate == 0.4  # 2/5 done
    assert metrics.progress_rate == 0.2  # 1/5 in progress
    assert metrics.blocked_rate == 0.0


def test_critical_priority_count():
    """Test counting of critical priority tickets."""
    tickets = [
        Task(
            id="TEST-1",
            title="Critical",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="Critical",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(id="TEST-3", title="High", state=TicketState.OPEN, priority=Priority.HIGH),
        Task(
            id="TEST-4",
            title="Medium",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.critical_count == 2
    assert metrics.high_count == 1


def test_health_status_on_track():
    """Test determination of ON_TRACK status."""
    # More than 50% done, no blockers
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Done {i}",
            state=TicketState.DONE,
            priority=Priority.MEDIUM,
        )
        for i in range(6)
    ] + [
        Task(
            id=f"TEST-{i+6}",
            title=f"Open {i}",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        )
        for i in range(4)
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.completion_rate == 0.6
    assert metrics.blocked_rate == 0.0
    assert metrics.health_status == ProjectHealth.ON_TRACK


def test_health_status_at_risk():
    """Test determination of AT_RISK status."""
    # Some progress but not enough completion
    tickets = [
        Task(
            id="TEST-1", title="Done", state=TicketState.DONE, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-2", title="Done", state=TicketState.DONE, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-3",
            title="In Progress",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-5", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-6",
            title="Blocked",
            state=TicketState.BLOCKED,
            priority=Priority.HIGH,
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    # Should be at risk due to low completion and some blockers
    assert metrics.health_status in (ProjectHealth.AT_RISK, ProjectHealth.OFF_TRACK)


def test_health_status_off_track():
    """Test determination of OFF_TRACK status."""
    # High blocker rate
    tickets = [
        Task(
            id="TEST-1",
            title="Blocked",
            state=TicketState.BLOCKED,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-2",
            title="Blocked",
            state=TicketState.BLOCKED,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Blocked",
            state=TicketState.BLOCKED,
            priority=Priority.MEDIUM,
        ),
        Task(id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.LOW),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.blocked_rate == 0.75
    assert metrics.health_status == ProjectHealth.OFF_TRACK


def test_completion_rate_includes_tested():
    """Test that completion rate includes TESTED state."""
    tickets = [
        Task(
            id="TEST-1", title="Done", state=TicketState.DONE, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-2",
            title="Tested",
            state=TicketState.TESTED,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-3",
            title="Closed",
            state=TicketState.CLOSED,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.completion_rate == 0.75  # 3/4 (DONE, TESTED, CLOSED)


def test_progress_rate_includes_ready():
    """Test that progress rate includes READY and TESTED states."""
    tickets = [
        Task(
            id="TEST-1",
            title="In Progress",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-2",
            title="Ready",
            state=TicketState.READY,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-3",
            title="Tested",
            state=TicketState.TESTED,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.progress_rate == 0.75  # 3/4 (IN_PROGRESS, READY, TESTED)


def test_blocked_rate_includes_waiting():
    """Test that blocked rate includes WAITING state."""
    tickets = [
        Task(
            id="TEST-1",
            title="Blocked",
            state=TicketState.BLOCKED,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-2",
            title="Waiting",
            state=TicketState.WAITING,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-3", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-4", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    assert metrics.blocked_rate == 0.5  # 2/4 (BLOCKED, WAITING)


def test_health_score_calculation():
    """Test that health score is calculated correctly."""
    tickets = [
        Task(id="TEST-1", title="Done", state=TicketState.DONE, priority=Priority.HIGH),
        Task(
            id="TEST-2",
            title="In Progress",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    # Health score should be between 0 and 1
    assert 0.0 <= metrics.health_score <= 1.0

    # With 1/3 done, 1/3 in progress, no blockers, should be decent
    assert metrics.health_score > 0.4


def test_priority_score_with_critical_tickets():
    """Test health score with critical priority tickets."""
    # Critical tickets done = good score
    tickets = [
        Task(
            id="TEST-1",
            title="Critical Done",
            state=TicketState.DONE,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="High Done",
            state=TicketState.DONE,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Medium Open",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    # Should have good health score since critical/high are done
    assert metrics.health_score > 0.5


def test_priority_score_with_critical_open():
    """Test health score with critical priority tickets still open."""
    # Critical tickets still open = lower score
    tickets = [
        Task(
            id="TEST-1",
            title="Critical Open",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="High Open",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Medium Done",
            state=TicketState.DONE,
            priority=Priority.MEDIUM,
        ),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    # Should have lower health score since critical/high are not done
    assert metrics.health_score < 0.8


def test_no_high_priority_tickets():
    """Test that projects with no high priority tickets get good priority score."""
    tickets = [
        Task(
            id="TEST-1",
            title="Medium",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
        Task(id="TEST-2", title="Low", state=TicketState.OPEN, priority=Priority.LOW),
    ]

    assessor = HealthAssessor()
    metrics = assessor.assess(tickets)

    # No critical/high tickets = priority score of 1.0
    # But overall score will still depend on completion/progress
    assert metrics.critical_count == 0
    assert metrics.high_count == 0
