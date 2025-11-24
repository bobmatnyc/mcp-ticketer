"""Tests for stale ticket detection."""

from datetime import datetime, timedelta

import pytest

from mcp_ticketer.analysis.staleness import StaleTicketDetector
from mcp_ticketer.core.models import Priority, Task, TicketState


@pytest.fixture
def old_stale_ticket():
    """Create an old, stale ticket."""
    now = datetime.now()
    return Task(
        id="STALE-1",
        title="Old inactive ticket",
        description="This ticket has been inactive for a long time",
        priority=Priority.LOW,
        state=TicketState.OPEN,
        created_at=now - timedelta(days=200),
        updated_at=now - timedelta(days=100),
    )


@pytest.fixture
def recent_active_ticket():
    """Create a recent, active ticket."""
    now = datetime.now()
    return Task(
        id="ACTIVE-1",
        title="Recent active ticket",
        description="This ticket was recently updated",
        priority=Priority.HIGH,
        state=TicketState.IN_PROGRESS,
        created_at=now - timedelta(days=10),
        updated_at=now - timedelta(days=1),
    )


@pytest.fixture
def blocked_old_ticket():
    """Create an old blocked ticket."""
    now = datetime.now()
    return Task(
        id="BLOCKED-1",
        title="Old blocked ticket",
        description="This ticket has been blocked for months",
        priority=Priority.MEDIUM,
        state=TicketState.BLOCKED,
        created_at=now - timedelta(days=150),
        updated_at=now - timedelta(days=60),
    )


@pytest.fixture
def waiting_ticket():
    """Create a waiting ticket."""
    now = datetime.now()
    return Task(
        id="WAITING-1",
        title="Waiting ticket",
        description="This ticket is waiting on external dependency",
        priority=Priority.MEDIUM,
        state=TicketState.WAITING,
        created_at=now - timedelta(days=120),
        updated_at=now - timedelta(days=45),
    )


@pytest.fixture
def sample_tickets(
    old_stale_ticket, recent_active_ticket, blocked_old_ticket, waiting_ticket
):
    """Create a list of sample tickets."""
    return [
        old_stale_ticket,
        recent_active_ticket,
        blocked_old_ticket,
        waiting_ticket,
    ]


class TestStaleTicketDetector:
    """Test cases for StaleTicketDetector."""

    def test_initialization(self) -> None:
        """Test detector initialization with default parameters."""
        detector = StaleTicketDetector()
        assert detector.age_threshold == 90
        assert detector.activity_threshold == 30
        assert len(detector.check_states) == 3

    def test_custom_initialization(self) -> None:
        """Test detector initialization with custom parameters."""
        detector = StaleTicketDetector(
            age_threshold_days=60,
            activity_threshold_days=20,
            check_states=[TicketState.OPEN],
        )
        assert detector.age_threshold == 60
        assert detector.activity_threshold == 20
        assert detector.check_states == [TicketState.OPEN]

    def test_find_stale_tickets(self, sample_tickets) -> None:
        """Test finding stale tickets."""
        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets(sample_tickets)

        # Should find at least the old stale ticket
        assert len(results) > 0

        # Check result structure
        for result in results:
            assert hasattr(result, "ticket_id")
            assert hasattr(result, "staleness_score")
            assert hasattr(result, "suggested_action")
            assert result.age_days > 90
            assert result.days_since_update > 30

    def test_stale_ticket_detected(self, old_stale_ticket) -> None:
        """Test that genuinely stale ticket is detected."""
        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets([old_stale_ticket])

        assert len(results) == 1
        assert results[0].ticket_id == "STALE-1"
        assert results[0].staleness_score > 0.5

    def test_active_ticket_not_detected(self, recent_active_ticket) -> None:
        """Test that active ticket is not flagged as stale."""
        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets([recent_active_ticket])

        # Active ticket should not be detected (not old enough)
        assert len(results) == 0

    def test_blocked_ticket_high_staleness(self, blocked_old_ticket) -> None:
        """Test that blocked tickets get higher staleness scores."""
        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets([blocked_old_ticket])

        assert len(results) == 1
        # Blocked state should increase staleness score
        assert results[0].staleness_score > 0.5

    def test_waiting_ticket_detection(self, waiting_ticket) -> None:
        """Test that waiting tickets are detected as stale."""
        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets([waiting_ticket])

        assert len(results) == 1
        assert results[0].ticket_id == "WAITING-1"
        assert "waiting state" in results[0].reason

    def test_priority_affects_staleness(self) -> None:
        """Test that priority affects staleness score."""
        now = datetime.now()

        low_priority = Task(
            id="LOW-1",
            title="Low priority ticket",
            priority=Priority.LOW,
            state=TicketState.OPEN,
            created_at=now - timedelta(days=120),
            updated_at=now - timedelta(days=50),
        )

        high_priority = Task(
            id="HIGH-1",
            title="High priority ticket",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            created_at=now - timedelta(days=120),
            updated_at=now - timedelta(days=50),
        )

        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )

        low_results = detector.find_stale_tickets([low_priority])
        high_results = detector.find_stale_tickets([high_priority])

        # Low priority should have higher staleness score
        assert low_results[0].staleness_score > high_results[0].staleness_score

    def test_suggested_actions(self, sample_tickets) -> None:
        """Test that suggested actions are appropriate."""
        detector = StaleTicketDetector(
            age_threshold_days=60,
            activity_threshold_days=20,
        )
        results = detector.find_stale_tickets(sample_tickets)

        for result in results:
            assert result.suggested_action in ["close", "review", "keep"]
            # Very stale tickets should suggest close
            if result.staleness_score > 0.8:
                assert result.suggested_action == "close"

    def test_reason_contains_age_info(self, old_stale_ticket) -> None:
        """Test that reason contains age information."""
        detector = StaleTicketDetector()
        results = detector.find_stale_tickets([old_stale_ticket])

        assert len(results) == 1
        assert "days" in results[0].reason
        # Should mention either age or inactivity
        assert any(
            word in results[0].reason.lower() for word in ["old", "inactive", "updates"]
        )

    def test_limit_parameter(self, sample_tickets) -> None:
        """Test that limit parameter is respected."""
        # Create more stale tickets
        now = datetime.now()
        many_stale = [
            Task(
                id=f"STALE-{i}",
                title=f"Stale ticket {i}",
                priority=Priority.LOW,
                state=TicketState.OPEN,
                created_at=now - timedelta(days=150 + i),
                updated_at=now - timedelta(days=60 + i),
            )
            for i in range(10)
        ]

        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets(many_stale, limit=5)

        assert len(results) <= 5

    def test_sorting_by_staleness_score(self, sample_tickets) -> None:
        """Test that results are sorted by staleness score."""
        detector = StaleTicketDetector(
            age_threshold_days=60,
            activity_threshold_days=20,
        )
        results = detector.find_stale_tickets(sample_tickets)

        if len(results) > 1:
            # Check that scores are in descending order
            scores = [r.staleness_score for r in results]
            assert scores == sorted(scores, reverse=True)

    def test_state_filter(self, sample_tickets) -> None:
        """Test that state filter works correctly."""
        # Only check OPEN tickets
        detector = StaleTicketDetector(
            age_threshold_days=60,
            activity_threshold_days=20,
            check_states=[TicketState.OPEN],
        )
        results = detector.find_stale_tickets(sample_tickets)

        # Should only find OPEN tickets
        for result in results:
            assert result.ticket_state == "open"

    def test_empty_tickets_list(self) -> None:
        """Test handling of empty tickets list."""
        detector = StaleTicketDetector()
        results = detector.find_stale_tickets([])
        assert results == []

    def test_ticket_without_timestamps(self) -> None:
        """Test handling of tickets without timestamps."""
        ticket = Task(
            id="NO-TIME",
            title="Ticket without timestamps",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            created_at=None,
            updated_at=None,
        )

        detector = StaleTicketDetector()
        results = detector.find_stale_tickets([ticket])

        # Should handle gracefully (treat as 0 days)
        assert len(results) == 0

    def test_days_since_calculation(self) -> None:
        """Test the days_since calculation method."""
        detector = StaleTicketDetector()
        now = datetime.now()

        # Test with a datetime 30 days ago
        past = now - timedelta(days=30)
        days = detector._days_since(past, now)
        assert days == 30

        # Test with None
        days = detector._days_since(None, now)
        assert days == 0

    def test_critical_priority_ticket(self) -> None:
        """Test that critical priority tickets have lower staleness scores."""
        now = datetime.now()

        critical_ticket = Task(
            id="CRITICAL-1",
            title="Critical priority ticket",
            priority=Priority.CRITICAL,
            state=TicketState.OPEN,
            created_at=now - timedelta(days=120),
            updated_at=now - timedelta(days=50),
        )

        detector = StaleTicketDetector(
            age_threshold_days=90,
            activity_threshold_days=30,
        )
        results = detector.find_stale_tickets([critical_ticket])

        if results:
            # Critical tickets should have lower staleness scores
            assert results[0].staleness_score < 0.7

    def test_done_tickets_not_checked(self) -> None:
        """Test that DONE tickets are not flagged as stale."""
        now = datetime.now()

        done_ticket = Task(
            id="DONE-1",
            title="Done ticket",
            priority=Priority.LOW,
            state=TicketState.DONE,
            created_at=now - timedelta(days=200),
            updated_at=now - timedelta(days=100),
        )

        detector = StaleTicketDetector()
        results = detector.find_stale_tickets([done_ticket])

        # DONE tickets should not be checked by default
        assert len(results) == 0
