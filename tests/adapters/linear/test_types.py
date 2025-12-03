"""Unit tests for Linear adapter types and mappings."""

import pytest

from mcp_ticketer.adapters.linear.types import (
    LinearPriorityMapping,
    LinearStateMapping,
    build_issue_filter,
    build_project_filter,
    extract_linear_metadata,
    get_linear_priority,
    get_linear_state_type,
    get_universal_priority,
    get_universal_state,
)
from mcp_ticketer.core.models import Priority, TicketState


@pytest.mark.unit
class TestLinearPriorityMapping:
    """Test Linear priority mapping functionality."""

    def test_priority_to_linear_mapping(self) -> None:
        """Test conversion from universal Priority to Linear priority."""
        assert LinearPriorityMapping.TO_LINEAR[Priority.CRITICAL] == 1
        assert LinearPriorityMapping.TO_LINEAR[Priority.HIGH] == 2
        assert LinearPriorityMapping.TO_LINEAR[Priority.MEDIUM] == 3
        assert LinearPriorityMapping.TO_LINEAR[Priority.LOW] == 4

    def test_priority_from_linear_mapping(self) -> None:
        """Test conversion from Linear priority to universal Priority."""
        assert LinearPriorityMapping.FROM_LINEAR[0] == Priority.LOW
        assert LinearPriorityMapping.FROM_LINEAR[1] == Priority.CRITICAL
        assert LinearPriorityMapping.FROM_LINEAR[2] == Priority.HIGH
        assert LinearPriorityMapping.FROM_LINEAR[3] == Priority.MEDIUM
        assert LinearPriorityMapping.FROM_LINEAR[4] == Priority.LOW

    def test_get_linear_priority(self) -> None:
        """Test get_linear_priority helper function."""
        assert get_linear_priority(Priority.CRITICAL) == 1
        assert get_linear_priority(Priority.HIGH) == 2
        assert get_linear_priority(Priority.MEDIUM) == 3
        assert get_linear_priority(Priority.LOW) == 4

    def test_get_universal_priority(self) -> None:
        """Test get_universal_priority helper function."""
        assert get_universal_priority(0) == Priority.LOW
        assert get_universal_priority(1) == Priority.CRITICAL
        assert get_universal_priority(2) == Priority.HIGH
        assert get_universal_priority(3) == Priority.MEDIUM
        assert get_universal_priority(4) == Priority.LOW

    def test_get_universal_priority_unknown(self) -> None:
        """Test get_universal_priority with unknown value."""
        assert get_universal_priority(99) == Priority.MEDIUM  # Default


@pytest.mark.unit
class TestLinearStateMapping:
    """Test Linear state mapping functionality."""

    def test_state_to_linear_mapping(self) -> None:
        """Test conversion from universal TicketState to Linear state type."""
        assert LinearStateMapping.TO_LINEAR[TicketState.OPEN] == "unstarted"
        assert LinearStateMapping.TO_LINEAR[TicketState.IN_PROGRESS] == "started"
        assert LinearStateMapping.TO_LINEAR[TicketState.DONE] == "completed"
        assert LinearStateMapping.TO_LINEAR[TicketState.CLOSED] == "canceled"

    def test_state_from_linear_mapping(self) -> None:
        """Test conversion from Linear state type to universal TicketState."""
        assert LinearStateMapping.FROM_LINEAR["unstarted"] == TicketState.OPEN
        assert LinearStateMapping.FROM_LINEAR["started"] == TicketState.IN_PROGRESS
        assert LinearStateMapping.FROM_LINEAR["completed"] == TicketState.DONE
        assert LinearStateMapping.FROM_LINEAR["canceled"] == TicketState.CLOSED

    def test_get_linear_state_type(self) -> None:
        """Test get_linear_state_type helper function."""
        assert get_linear_state_type(TicketState.OPEN) == "unstarted"
        assert get_linear_state_type(TicketState.IN_PROGRESS) == "started"
        assert get_linear_state_type(TicketState.DONE) == "completed"

    def test_get_universal_state(self) -> None:
        """Test get_universal_state helper function."""
        assert get_universal_state("unstarted") == TicketState.OPEN
        assert get_universal_state("started") == TicketState.IN_PROGRESS
        assert get_universal_state("completed") == TicketState.DONE

    def test_get_universal_state_unknown(self) -> None:
        """Test get_universal_state with unknown value."""
        assert get_universal_state("unknown") == TicketState.OPEN  # Default

    def test_get_universal_state_done_synonyms(self) -> None:
        """Test that done/completed synonyms map to DONE (v2.0.4 bug fix)."""
        # Exact matches
        assert get_universal_state("unknown", "done") == TicketState.DONE
        assert get_universal_state("unknown", "completed") == TicketState.DONE
        assert get_universal_state("unknown", "finished") == TicketState.DONE
        assert get_universal_state("unknown", "resolved") == TicketState.DONE

        # Case insensitive
        assert get_universal_state("unknown", "DONE") == TicketState.DONE
        assert get_universal_state("unknown", "Completed") == TicketState.DONE
        assert get_universal_state("unknown", "FINISHED") == TicketState.DONE

        # Partial matches (substring)
        assert get_universal_state("unknown", "Completed ✓") == TicketState.DONE
        assert get_universal_state("unknown", "Work Finished") == TicketState.DONE

    def test_get_universal_state_closed_synonyms(self) -> None:
        """Test that closed/canceled synonyms map to CLOSED."""
        # Exact matches
        assert get_universal_state("unknown", "closed") == TicketState.CLOSED
        assert get_universal_state("unknown", "canceled") == TicketState.CLOSED
        assert get_universal_state("unknown", "cancelled") == TicketState.CLOSED
        assert get_universal_state("unknown", "won't do") == TicketState.CLOSED
        assert get_universal_state("unknown", "wont do") == TicketState.CLOSED
        assert get_universal_state("unknown", "rejected") == TicketState.CLOSED

        # Case insensitive
        assert get_universal_state("unknown", "CLOSED") == TicketState.CLOSED
        assert get_universal_state("unknown", "Canceled") == TicketState.CLOSED
        assert get_universal_state("unknown", "CANCELLED") == TicketState.CLOSED

        # Partial matches
        assert get_universal_state("unknown", "Won't Do") == TicketState.CLOSED

    def test_get_universal_state_linear_integration(self) -> None:
        """Test with actual Linear state names from default workflows."""
        # Linear's default "Done" state (type: completed)
        assert get_universal_state("completed", "Done") == TicketState.DONE

        # Linear's default "Canceled" state (type: canceled)
        assert get_universal_state("canceled", "Canceled") == TicketState.CLOSED

        # Custom states with semantic names
        assert get_universal_state("unknown", "Completed ✓") == TicketState.DONE
        assert get_universal_state("unknown", "Won't Do") == TicketState.CLOSED
        assert get_universal_state("unknown", "Finished") == TicketState.DONE

    def test_get_universal_state_synonym_separation(self) -> None:
        """Test that DONE and CLOSED synonyms are properly separated (regression test)."""
        # This test prevents the bug where "completed" was in closed_synonyms
        # Verify DONE synonyms don't return CLOSED
        done_states = ["done", "completed", "finished", "resolved"]
        for state_name in done_states:
            result = get_universal_state("unknown", state_name)
            assert (
                result == TicketState.DONE
            ), f"{state_name} should map to DONE, not {result}"

        # Verify CLOSED synonyms don't return DONE
        closed_states = ["closed", "canceled", "cancelled", "won't do", "rejected"]
        for state_name in closed_states:
            result = get_universal_state("unknown", state_name)
            assert (
                result == TicketState.CLOSED
            ), f"{state_name} should map to CLOSED, not {result}"


@pytest.mark.unit
class TestFilterBuilders:
    """Test filter building utilities."""

    def test_build_issue_filter_basic(self) -> None:
        """Test basic issue filter building."""
        filter_obj = build_issue_filter(team_id="team-123")

        assert filter_obj["team"]["id"]["eq"] == "team-123"
        assert filter_obj["archivedAt"]["null"] is True

    def test_build_issue_filter_with_state(self) -> None:
        """Test issue filter with state."""
        filter_obj = build_issue_filter(
            team_id="team-123", state=TicketState.IN_PROGRESS
        )

        assert filter_obj["state"]["type"]["eq"] == "started"

    def test_build_issue_filter_with_priority(self) -> None:
        """Test issue filter with priority."""
        filter_obj = build_issue_filter(team_id="team-123", priority=Priority.HIGH)

        assert filter_obj["priority"]["eq"] == 2

    def test_build_issue_filter_with_assignee(self) -> None:
        """Test issue filter with assignee."""
        filter_obj = build_issue_filter(team_id="team-123", assignee_id="user-456")

        assert filter_obj["assignee"]["id"]["eq"] == "user-456"

    def test_build_issue_filter_with_labels(self) -> None:
        """Test issue filter with labels."""
        filter_obj = build_issue_filter(team_id="team-123", labels=["bug", "frontend"])

        assert filter_obj["labels"]["some"]["name"]["in"] == ["bug", "frontend"]

    def test_build_issue_filter_with_dates(self) -> None:
        """Test issue filter with date filters."""
        filter_obj = build_issue_filter(
            team_id="team-123",
            created_after="2023-01-01T00:00:00Z",
            updated_after="2023-01-02T00:00:00Z",
            due_before="2023-12-31T23:59:59Z",
        )

        assert filter_obj["createdAt"]["gte"] == "2023-01-01T00:00:00Z"
        assert filter_obj["updatedAt"]["gte"] == "2023-01-02T00:00:00Z"
        assert filter_obj["dueDate"]["lte"] == "2023-12-31T23:59:59Z"

    def test_build_issue_filter_include_archived(self) -> None:
        """Test issue filter with archived issues included."""
        filter_obj = build_issue_filter(team_id="team-123", include_archived=True)

        # Should not have archivedAt filter when including archived
        assert "archivedAt" not in filter_obj

    def test_build_project_filter_basic(self) -> None:
        """Test basic project filter building."""
        filter_obj = build_project_filter(team_id="team-123")

        assert filter_obj["teams"]["some"]["id"]["eq"] == "team-123"

    def test_build_project_filter_with_state(self) -> None:
        """Test project filter with state."""
        filter_obj = build_project_filter(team_id="team-123", state="started")

        assert filter_obj["state"]["eq"] == "started"

    def test_build_project_filter_exclude_completed(self) -> None:
        """Test project filter excluding completed projects."""
        filter_obj = build_project_filter(team_id="team-123", include_completed=False)

        assert filter_obj["state"]["neq"] == "completed"


@pytest.mark.unit
class TestMetadataExtraction:
    """Test metadata extraction from Linear data."""

    def test_extract_linear_metadata_basic(self) -> None:
        """Test basic metadata extraction."""
        issue_data = {
            "id": "issue-123",
            "title": "Test Issue",
            "url": "https://linear.app/team/issue/TEST-123",
        }

        metadata = extract_linear_metadata(issue_data)

        assert metadata["linear_url"] == "https://linear.app/team/issue/TEST-123"

    def test_extract_linear_metadata_comprehensive(self) -> None:
        """Test comprehensive metadata extraction."""
        issue_data = {
            "dueDate": "2023-12-31T23:59:59Z",
            "cycle": {"id": "cycle-456", "name": "Sprint 1"},
            "estimate": 5,
            "branchName": "feature/test-123",
            "url": "https://linear.app/team/issue/TEST-123",
            "slaBreachesAt": "2023-12-30T00:00:00Z",
            "customerTicketCount": 3,
        }

        metadata = extract_linear_metadata(issue_data)

        assert metadata["due_date"] == "2023-12-31T23:59:59Z"
        assert metadata["cycle_id"] == "cycle-456"
        assert metadata["cycle_name"] == "Sprint 1"
        assert metadata["estimate"] == 5
        assert metadata["branch_name"] == "feature/test-123"
        assert metadata["linear_url"] == "https://linear.app/team/issue/TEST-123"
        assert metadata["sla_breaches_at"] == "2023-12-30T00:00:00Z"
        assert metadata["customer_ticket_count"] == 3

    def test_extract_linear_metadata_empty(self) -> None:
        """Test metadata extraction with empty data."""
        issue_data = {"id": "issue-123", "title": "Test Issue"}

        metadata = extract_linear_metadata(issue_data)

        assert metadata == {}

    def test_extract_linear_metadata_partial(self) -> None:
        """Test metadata extraction with partial data."""
        issue_data = {
            "dueDate": "2023-12-31T23:59:59Z",
            "estimate": None,  # Null value should be ignored
            "url": "https://linear.app/team/issue/TEST-123",
        }

        metadata = extract_linear_metadata(issue_data)

        assert metadata["due_date"] == "2023-12-31T23:59:59Z"
        assert metadata["linear_url"] == "https://linear.app/team/issue/TEST-123"
        assert "estimate" not in metadata  # Null values should be excluded
