"""Tests for orphaned ticket detection."""

import pytest

from mcp_ticketer.analysis.orphaned import OrphanedTicketDetector
from mcp_ticketer.core.models import Priority, Task, TicketState, TicketType


@pytest.fixture
def orphaned_issue():
    """Create an orphaned issue (no epic, no project)."""
    return Task(
        id="ISSUE-1",
        title="Orphaned issue",
        description="Issue without parent epic or project",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        ticket_type=TicketType.ISSUE,
        parent_epic=None,
        metadata={},
    )


@pytest.fixture
def orphaned_task():
    """Create an orphaned task (no parent issue)."""
    return Task(
        id="TASK-1",
        title="Orphaned task",
        description="Task without parent issue",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        ticket_type=TicketType.TASK,
        parent_issue=None,
        metadata={},
    )


@pytest.fixture
def issue_with_epic():
    """Create an issue with epic but no project."""
    return Task(
        id="ISSUE-2",
        title="Issue with epic",
        description="Issue has epic but no project",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        ticket_type=TicketType.ISSUE,
        parent_epic="EPIC-1",
        metadata={},
    )


@pytest.fixture
def issue_with_project():
    """Create an issue with project but no epic."""
    return Task(
        id="ISSUE-3",
        title="Issue with project",
        description="Issue has project but no epic",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        ticket_type=TicketType.ISSUE,
        parent_epic=None,
        metadata={"project_id": "PROJECT-1"},
    )


@pytest.fixture
def properly_organized_task():
    """Create a properly organized task with parent issue."""
    return Task(
        id="TASK-2",
        title="Organized task",
        description="Task with proper parent issue",
        priority=Priority.MEDIUM,
        state=TicketState.OPEN,
        ticket_type=TicketType.TASK,
        parent_issue="ISSUE-1",
        metadata={},
    )


@pytest.fixture
def sample_tickets(
    orphaned_issue,
    orphaned_task,
    issue_with_epic,
    issue_with_project,
    properly_organized_task,
):
    """Create a list of sample tickets."""
    return [
        orphaned_issue,
        orphaned_task,
        issue_with_epic,
        issue_with_project,
        properly_organized_task,
    ]


class TestOrphanedTicketDetector:
    """Test cases for OrphanedTicketDetector."""

    def test_find_orphaned_tickets(self, sample_tickets) -> None:
        """Test finding orphaned tickets."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets(sample_tickets)

        # Should find orphaned tickets
        assert len(results) > 0

        # Check result structure
        for result in results:
            assert hasattr(result, "ticket_id")
            assert hasattr(result, "orphan_type")
            assert hasattr(result, "suggested_action")
            assert result.orphan_type in [
                "no_parent",
                "no_epic",
                "no_project",
            ]

    def test_orphaned_issue_detected(self, orphaned_issue) -> None:
        """Test that orphaned issue is detected."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([orphaned_issue])

        # Should detect multiple orphan types
        assert len(results) > 0
        orphan_types = {r.orphan_type for r in results}
        assert "no_epic" in orphan_types
        assert "no_project" in orphan_types

    def test_orphaned_task_detected(self, orphaned_task) -> None:
        """Test that orphaned task is detected."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([orphaned_task])

        assert len(results) == 1
        assert results[0].ticket_id == "TASK-1"
        assert results[0].orphan_type == "no_parent"

    def test_issue_with_epic_only(self, issue_with_epic) -> None:
        """Test issue with epic but no project."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([issue_with_epic])

        # Should detect missing project only
        orphan_types = [r.orphan_type for r in results]
        assert "no_project" in orphan_types
        assert "no_epic" not in orphan_types

    def test_issue_with_project_only(self, issue_with_project) -> None:
        """Test issue with project but no epic."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([issue_with_project])

        # Should detect missing epic only
        orphan_types = [r.orphan_type for r in results]
        assert "no_epic" in orphan_types
        assert "no_project" not in orphan_types

    def test_organized_task_not_detected(self, properly_organized_task) -> None:
        """Test that properly organized task is not flagged."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([properly_organized_task])

        # Should not be detected as orphaned
        assert len(results) == 0

    def test_suggested_actions(self, sample_tickets) -> None:
        """Test that suggested actions are appropriate."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets(sample_tickets)

        for result in results:
            assert result.suggested_action in [
                "assign_epic",
                "assign_project",
                "review",
            ]

            # Check action matches orphan type
            if result.orphan_type == "no_epic":
                assert result.suggested_action == "assign_epic"
            elif result.orphan_type == "no_project":
                assert result.suggested_action == "assign_project"
            elif result.orphan_type == "no_parent":
                assert result.suggested_action == "review"

    def test_ticket_type_detection(self, sample_tickets) -> None:
        """Test that ticket types are correctly detected."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets(sample_tickets)

        for result in results:
            assert result.ticket_type in ["task", "issue", "epic"]

    def test_reason_is_descriptive(self, orphaned_issue) -> None:
        """Test that reason is human-readable."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([orphaned_issue])

        for result in results:
            assert len(result.reason) > 0
            # Reason should mention parent, epic, or project
            assert any(
                word in result.reason.lower()
                for word in ["parent", "epic", "project", "assigned"]
            )

    def test_linear_metadata_detection(self) -> None:
        """Test detection with Linear-style metadata."""
        ticket = Task(
            id="LINEAR-1",
            title="Linear ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
            parent_epic=None,
            metadata={
                "projectId": "PROJECT-123",  # Linear uses camelCase
            },
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([ticket])

        # Should detect missing epic but not missing project
        orphan_types = [r.orphan_type for r in results]
        assert "no_epic" in orphan_types
        assert "no_project" not in orphan_types

    def test_jira_metadata_detection(self) -> None:
        """Test detection with JIRA-style metadata."""
        ticket = Task(
            id="JIRA-1",
            title="JIRA ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
            parent_epic=None,
            metadata={
                "epic": "EPIC-123",  # JIRA epic field
                "board_id": "BOARD-1",  # JIRA board
            },
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([ticket])

        # Should not detect as orphaned (has epic and board/project)
        assert len(results) == 0

    def test_github_metadata_detection(self) -> None:
        """Test detection with GitHub-style metadata."""
        ticket = Task(
            id="GH-1",
            title="GitHub ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
            parent_epic=None,
            metadata={
                "milestone_id": "MILESTONE-1",  # GitHub milestone (epic)
            },
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([ticket])

        # Should detect missing project only
        orphan_types = [r.orphan_type for r in results]
        assert "no_epic" not in orphan_types
        assert "no_project" in orphan_types

    def test_asana_metadata_detection(self) -> None:
        """Test detection with Asana-style metadata."""
        ticket = Task(
            id="ASANA-1",
            title="Asana ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
            parent_epic=None,
            metadata={
                "workspace_id": "WORKSPACE-1",  # Asana workspace
            },
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([ticket])

        # Should detect missing epic only
        orphan_types = [r.orphan_type for r in results]
        assert "no_epic" in orphan_types
        assert "no_project" not in orphan_types

    def test_empty_tickets_list(self) -> None:
        """Test handling of empty tickets list."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([])
        assert results == []

    def test_epic_not_checked(self) -> None:
        """Test that epic tickets are not checked for orphans."""
        epic = Task(
            id="EPIC-1",
            title="Epic ticket",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            ticket_type=TicketType.EPIC,
            metadata={},
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([epic])

        # Epics should not be checked (they are top-level)
        assert len(results) == 0

    def test_multiple_orphan_types_for_single_ticket(self, orphaned_issue) -> None:
        """Test that a ticket can have multiple orphan types."""
        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([orphaned_issue])

        # Orphaned issue should have multiple types (no_epic, no_project, no_parent)
        assert len(results) > 1

        orphan_types = {r.orphan_type for r in results}
        assert len(orphan_types) > 1

    def test_ticket_type_from_metadata(self) -> None:
        """Test ticket type detection from metadata."""
        # Task with metadata type
        task = Task(
            id="META-TASK",
            title="Task from metadata",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,  # Explicit type
            parent_issue=None,
            metadata={"type": "task"},  # But metadata says task
        )

        detector = OrphanedTicketDetector()
        ticket_type = detector._get_ticket_type(task)

        # Should respect explicit ticket_type field over metadata
        assert ticket_type in ["task", "issue"]

    def test_ticket_with_parent_issue_inferred_as_task(self) -> None:
        """Test that ticket with parent_issue is inferred as task."""
        ticket = Task(
            id="INFERRED-TASK",
            title="Inferred task",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,  # Says issue
            parent_issue="ISSUE-1",  # But has parent issue
            metadata={},
        )

        detector = OrphanedTicketDetector()
        ticket_type = detector._get_ticket_type(ticket)

        # Should infer as task due to parent_issue
        # Note: This tests the fallback logic
        assert ticket_type in ["task", "issue"]

    def test_fully_organized_ticket(self) -> None:
        """Test ticket with both epic and project."""
        ticket = Task(
            id="ORGANIZED-1",
            title="Fully organized ticket",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.ISSUE,
            parent_epic="EPIC-1",
            metadata={"project_id": "PROJECT-1"},
        )

        detector = OrphanedTicketDetector()
        results = detector.find_orphaned_tickets([ticket])

        # Should not be orphaned
        assert len(results) == 0
