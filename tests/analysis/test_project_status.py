"""Tests for project status analysis."""

from mcp_ticketer.analysis.project_status import (
    StatusAnalyzer,
)
from mcp_ticketer.core.models import Priority, Task, TicketState


def test_status_analyzer_creation():
    """Test StatusAnalyzer initialization."""
    analyzer = StatusAnalyzer()
    assert analyzer is not None
    assert analyzer.health_assessor is not None


def test_analyze_empty_project():
    """Test analysis of empty project."""
    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST-EPIC", "Test Project", [])

    assert result.project_id == "TEST-EPIC"
    assert result.project_name == "Test Project"
    assert result.summary["total"] == 0
    assert len(result.recommended_next) == 0


def test_analyze_simple_project():
    """Test analysis of project with a few tickets."""
    tickets = [
        Task(
            id="TEST-1",
            title="First task",
            state=TicketState.DONE,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-2",
            title="Second task",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-3",
            title="Third task",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST-EPIC", "Test Project", tickets)

    assert result.summary["total"] == 3
    assert result.summary["done"] == 1
    assert result.summary["in_progress"] == 1
    assert result.summary["open"] == 1


def test_build_state_summary():
    """Test state summary building."""
    tickets = [
        Task(
            id="TEST-1", title="Done", state=TicketState.DONE, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-2", title="Done", state=TicketState.DONE, priority=Priority.MEDIUM
        ),
        Task(
            id="TEST-3", title="Open", state=TicketState.OPEN, priority=Priority.MEDIUM
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    assert result.summary["total"] == 3
    assert result.summary["done"] == 2
    assert result.summary["open"] == 1


def test_build_priority_summary():
    """Test priority summary building."""
    tickets = [
        Task(
            id="TEST-1",
            title="Critical",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(id="TEST-2", title="High", state=TicketState.OPEN, priority=Priority.HIGH),
        Task(id="TEST-3", title="High", state=TicketState.OPEN, priority=Priority.HIGH),
        Task(
            id="TEST-4",
            title="Medium",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    assert result.priority_summary["critical"] == 1
    assert result.priority_summary["high"] == 2
    assert result.priority_summary["medium"] == 1


def test_build_work_distribution():
    """Test work distribution by assignee."""
    tickets = [
        Task(
            id="TEST-1",
            title="Alice task 1",
            state=TicketState.DONE,
            assignee="alice@example.com",
        ),
        Task(
            id="TEST-2",
            title="Alice task 2",
            state=TicketState.IN_PROGRESS,
            assignee="alice@example.com",
        ),
        Task(
            id="TEST-3",
            title="Bob task",
            state=TicketState.OPEN,
            assignee="bob@example.com",
        ),
        Task(id="TEST-4", title="Unassigned", state=TicketState.OPEN, assignee=None),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    assert result.work_distribution["alice@example.com"]["total"] == 2
    assert result.work_distribution["bob@example.com"]["total"] == 1
    assert result.work_distribution["unassigned"]["total"] == 1


def test_dependency_analysis():
    """Test dependency graph building and analysis."""
    tickets = [
        Task(
            id="TEST-1",
            title="Foundation",
            description="Blocks TEST-2 and TEST-3",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="Feature A",
            description="Depends on TEST-1",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Feature B",
            description="Depends on TEST-1",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should identify TEST-1 as blocker
    assert len(result.blockers) > 0
    assert result.blockers[0]["ticket_id"] == "TEST-1"
    assert result.blockers[0]["blocks_count"] == 2


def test_critical_path_identification():
    """Test critical path identification."""
    tickets = [
        Task(
            id="TEST-1",
            title="A",
            description="Blocks TEST-2",
            state=TicketState.OPEN,
        ),
        Task(
            id="TEST-2",
            title="B",
            description="Blocks TEST-3",
            state=TicketState.OPEN,
        ),
        Task(
            id="TEST-3",
            title="C",
            description="Final task",
            state=TicketState.OPEN,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should have a critical path
    assert len(result.critical_path) >= 3


def test_recommend_next_tickets():
    """Test recommendation of next tickets to work on."""
    tickets = [
        Task(
            id="TEST-1",
            title="Critical blocker",
            description="Blocks TEST-2, TEST-3",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="Blocked task",
            description="Depends on TEST-1",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Independent task",
            description="Can start anytime",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should recommend critical blocker first
    assert len(result.recommended_next) > 0
    assert result.recommended_next[0].ticket_id == "TEST-1"
    assert result.recommended_next[0].priority == "critical"


def test_recommend_skips_done_tickets():
    """Test that recommendations skip done/in-progress tickets."""
    tickets = [
        Task(
            id="TEST-1",
            title="Done task",
            state=TicketState.DONE,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="In progress",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
        ),
        Task(
            id="TEST-3",
            title="Open task",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should only recommend the open task
    assert len(result.recommended_next) <= 1
    if len(result.recommended_next) > 0:
        assert result.recommended_next[0].ticket_id == "TEST-3"


def test_recommendation_scoring_priority():
    """Test that priority affects recommendation scoring."""
    tickets = [
        Task(
            id="TEST-CRITICAL",
            title="Critical",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-LOW",
            title="Low",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Critical should be recommended first
    assert result.recommended_next[0].ticket_id == "TEST-CRITICAL"


def test_recommendation_scoring_blocks():
    """Test that blocking tickets get higher scores."""
    tickets = [
        Task(
            id="TEST-BLOCKER",
            title="Blocker",
            description="Blocks TEST-A, TEST-B, TEST-C",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="TEST-SIMPLE",
            title="Simple",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Blocker should be recommended first
    assert result.recommended_next[0].ticket_id == "TEST-BLOCKER"


def test_generate_recommendations_healthy_project():
    """Test recommendations for healthy project."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Task {i}",
            state=TicketState.DONE,
            priority=Priority.MEDIUM,
        )
        for i in range(7)
    ] + [
        Task(
            id=f"TEST-{i+7}",
            title=f"Task {i}",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        )
        for i in range(3)
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should have positive recommendations
    assert len(result.recommendations) > 0
    assert any("track" in r.lower() for r in result.recommendations)


def test_generate_recommendations_off_track():
    """Test recommendations for off-track project."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Blocked {i}",
            state=TicketState.BLOCKED,
            priority=Priority.HIGH,
        )
        for i in range(5)
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should have warning recommendations
    assert len(result.recommendations) > 0
    assert any(
        "off track" in r.lower() or "risk" in r.lower() for r in result.recommendations
    )


def test_generate_recommendations_critical_tickets():
    """Test recommendations when critical tickets exist."""
    tickets = [
        Task(
            id="TEST-CRIT",
            title="Critical",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-NORMAL",
            title="Normal",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should mention critical priority
    assert any("critical" in r.lower() for r in result.recommendations)


def test_generate_recommendations_blockers():
    """Test recommendations when blockers exist."""
    # Use realistic ticket ID format that will be detected
    tickets = [
        Task(
            id="1M-100",
            title="Blocker",
            description="Blocks 1M-101 and blocks 1M-102",
            state=TicketState.OPEN,
            priority=Priority.HIGH,
        ),
        Task(
            id="1M-101",
            title="Blocked A",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
        Task(
            id="1M-102",
            title="Blocked B",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should identify blockers
    assert len(result.blockers) > 0, f"Expected blockers but got: {result.blockers}"
    assert result.blockers[0]["ticket_id"] == "1M-100"
    assert result.blockers[0]["blocks_count"] == 2

    # Should have recommendations
    assert len(result.recommendations) > 0

    # Should mention resolving the blocker
    assert any(
        "unblock" in r.lower() or "1M-100" in r for r in result.recommendations
    ), f"Blocker not mentioned in recommendations: {result.recommendations}"


def test_generate_recommendations_no_completions():
    """Test recommendations when no tickets are completed."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Open {i}",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )
        for i in range(5)
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should suggest delivering first wins
    assert any(
        "complet" in r.lower() or "deliver" in r.lower() for r in result.recommendations
    )


def test_timeline_estimate():
    """Test timeline estimation."""
    tickets = [
        Task(
            id="TEST-1",
            title="Task",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2", title="Task", state=TicketState.BLOCKED, priority=Priority.HIGH
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Timeline estimate should exist
    assert result.timeline_estimate is not None
    assert "risk" in result.timeline_estimate


def test_recommendation_limit():
    """Test that only top 3 tickets are recommended."""
    tickets = [
        Task(
            id=f"TEST-{i}",
            title=f"Task {i}",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        )
        for i in range(10)
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Should recommend at most 3
    assert len(result.recommended_next) <= 3


def test_recommendation_reason_includes_context():
    """Test that recommendation reasons include helpful context."""
    tickets = [
        Task(
            id="TEST-1",
            title="Blocker",
            description="Blocks TEST-2",
            state=TicketState.OPEN,
            priority=Priority.CRITICAL,
        ),
        Task(
            id="TEST-2",
            title="Blocked",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
        ),
    ]

    analyzer = StatusAnalyzer()
    result = analyzer.analyze("TEST", "Test", tickets)

    # Reason should explain why
    if len(result.recommended_next) > 0:
        reason = result.recommended_next[0].reason
        assert len(reason) > 0
        # Should mention critical priority and/or unblocking
        assert "critical" in reason.lower() or "unblock" in reason.lower()
