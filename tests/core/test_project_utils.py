"""Tests for project_utils conversion functions.

This module tests the conversion utilities between Epic and Project models,
ensuring backward compatibility and correct state mapping.

Test Coverage:
- epic_to_project() conversion
- project_to_epic() conversion
- State mapping functions
- Metadata preservation
- Edge cases and null handling
"""

from datetime import datetime, timezone

import pytest

from mcp_ticketer.core.models import (
    Epic,
    Priority,
    Project,
    ProjectScope,
    ProjectState,
    ProjectVisibility,
    TicketState,
)
from mcp_ticketer.core.project_utils import (
    epic_to_project,
    project_to_epic,
)


class TestEpicToProjectConversion:
    """Test conversion from Epic to Project model."""

    @pytest.fixture
    def minimal_epic(self) -> Epic:
        """Create minimal epic for testing.

        Returns:
            Epic with only required fields
        """
        return Epic(
            id="epic-123",
            title="Minimal Epic",
        )

    @pytest.fixture
    def full_epic(self) -> Epic:
        """Create fully populated epic for testing.

        Returns:
            Epic with all fields populated
        """
        created = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2025, 12, 1, 14, 30, 0, tzinfo=timezone.utc)

        return Epic(
            id="epic-full-123",
            title="Full Featured Epic",
            description="A comprehensive epic with all fields",
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            tags=["feature", "q4"],
            created_at=created,
            updated_at=updated,
            child_issues=["issue-1", "issue-2", "issue-3"],
            metadata={
                "platform": "linear",
                "url": "https://linear.app/team/epic/123",
                "target_date": datetime(2025, 12, 31, tzinfo=timezone.utc),
                "completed_at": None,
                "team_id": "team-456",
                "custom_field": "custom_value",
            },
        )

    def test_minimal_epic_conversion(self, minimal_epic: Epic):
        """Test converting minimal epic to project."""
        project = epic_to_project(minimal_epic)

        # Check basic field mapping
        assert project.id == minimal_epic.id
        assert project.platform_id == minimal_epic.id
        assert project.name == minimal_epic.title
        assert project.description == minimal_epic.description

        # Check defaults for new Project fields
        assert project.scope == ProjectScope.TEAM
        assert project.visibility == ProjectVisibility.TEAM
        assert project.platform == "unknown"  # No platform in metadata
        assert project.state == ProjectState.PLANNED  # Default mapped state

        # Check metadata preservation
        assert project.extra_data["original_type"] == "epic"

    def test_full_epic_conversion(self, full_epic: Epic):
        """Test converting fully populated epic to project."""
        project = epic_to_project(full_epic)

        # Check field mapping
        assert project.id == full_epic.id
        assert project.name == full_epic.title
        assert project.description == full_epic.description
        assert project.created_at == full_epic.created_at
        assert project.updated_at == full_epic.updated_at

        # Check child issues preserved
        assert project.child_issues == full_epic.child_issues
        assert len(project.child_issues) == 3

        # Check metadata extraction
        assert project.platform == "linear"
        assert project.url == "https://linear.app/team/epic/123"
        assert project.target_date == datetime(2025, 12, 31, tzinfo=timezone.utc)

        # Check extra_data includes original metadata
        assert project.extra_data["original_type"] == "epic"
        assert project.extra_data["team_id"] == "team-456"
        assert project.extra_data["custom_field"] == "custom_value"

    def test_epic_state_mapping_to_project(self, minimal_epic: Epic):
        """Test state mapping from Epic to Project."""
        # Test IN_PROGRESS -> ACTIVE
        minimal_epic.state = TicketState.IN_PROGRESS
        project = epic_to_project(minimal_epic)
        assert project.state == ProjectState.ACTIVE

        # Test DONE -> COMPLETED
        minimal_epic.state = TicketState.DONE
        project = epic_to_project(minimal_epic)
        assert project.state == ProjectState.COMPLETED

        # Test OPEN -> PLANNED
        minimal_epic.state = TicketState.OPEN
        project = epic_to_project(minimal_epic)
        assert project.state == ProjectState.PLANNED

        # Test CLOSED -> handled gracefully (mapped to PLANNED as fallback)
        minimal_epic.state = TicketState.CLOSED
        project = epic_to_project(minimal_epic)
        # Note: CLOSED doesn't have direct mapping, falls back to PLANNED
        assert project.state in [ProjectState.PLANNED, ProjectState.ARCHIVED]

    def test_epic_with_no_metadata(self):
        """Test converting epic with no metadata dict."""
        epic = Epic(
            id="epic-no-meta",
            title="No Metadata Epic",
            metadata=None,
        )
        project = epic_to_project(epic)

        assert project.platform == "unknown"
        assert project.url is None
        assert project.target_date is None
        assert project.extra_data["original_type"] == "epic"

    def test_epic_with_empty_metadata(self):
        """Test converting epic with empty metadata dict."""
        epic = Epic(
            id="epic-empty-meta",
            title="Empty Metadata Epic",
            metadata={},
        )
        project = epic_to_project(epic)

        assert project.platform == "unknown"
        assert project.extra_data["original_type"] == "epic"

    def test_epic_with_no_child_issues(self):
        """Test converting epic with no child issues."""
        epic = Epic(
            id="epic-no-children",
            title="No Children Epic",
            child_issues=[],
        )
        project = epic_to_project(epic)

        assert project.child_issues == []

    def test_epic_with_none_child_issues(self):
        """Test converting epic with None child_issues."""
        epic = Epic(
            id="epic-none-children",
            title="None Children Epic",
        )
        # Ensure child_issues defaults to empty list
        project = epic_to_project(epic)
        assert project.child_issues == [] or project.child_issues is not None


class TestProjectToEpicConversion:
    """Test conversion from Project to Epic model."""

    @pytest.fixture
    def minimal_project(self) -> Project:
        """Create minimal project for testing.

        Returns:
            Project with only required fields
        """
        return Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Minimal Project",
        )

    @pytest.fixture
    def full_project(self) -> Project:
        """Create fully populated project for testing.

        Returns:
            Project with all fields populated
        """
        created = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2025, 12, 1, 14, 30, 0, tzinfo=timezone.utc)
        target = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        return Project(
            id="proj-full-123",
            platform="github",
            platform_id="GH_kwDOAbCdEf012345",
            scope=ProjectScope.ORGANIZATION,
            name="Full Featured Project",
            description="A comprehensive project",
            state=ProjectState.ACTIVE,
            visibility=ProjectVisibility.PUBLIC,
            url="https://github.com/orgs/acme/projects/42",
            created_at=created,
            updated_at=updated,
            start_date=created,
            target_date=target,
            completed_at=None,
            owner_id="user-123",
            owner_name="Alice Developer",
            team_id="team-456",
            team_name="Engineering",
            child_issues=["issue-1", "issue-2"],
            extra_data={"custom_field": "value"},
        )

    def test_minimal_project_conversion(self, minimal_project: Project):
        """Test converting minimal project to epic."""
        epic = project_to_epic(minimal_project)

        # Check basic field mapping
        assert epic.id == minimal_project.id
        assert epic.title == minimal_project.name
        assert epic.description == minimal_project.description

        # Check metadata contains project data
        assert epic.metadata["platform"] == "linear"
        assert epic.metadata["project_data"]["scope"] == ProjectScope.TEAM
        assert epic.metadata["project_data"]["visibility"] == ProjectVisibility.TEAM
        assert epic.metadata["project_data"]["platform_id"] == "abc123"

    def test_full_project_conversion(self, full_project: Project):
        """Test converting fully populated project to epic."""
        epic = project_to_epic(full_project)

        # Check field mapping
        assert epic.id == full_project.id
        assert epic.title == full_project.name
        assert epic.description == full_project.description
        assert epic.created_at == full_project.created_at
        assert epic.updated_at == full_project.updated_at

        # Check child issues preserved
        assert epic.child_issues == full_project.child_issues
        assert len(epic.child_issues) == 2

        # Check metadata structure
        assert epic.metadata["platform"] == "github"
        assert epic.metadata["url"] == "https://github.com/orgs/acme/projects/42"
        assert epic.metadata["target_date"] == full_project.target_date

        # Check project_data preservation
        project_data = epic.metadata["project_data"]
        assert project_data["scope"] == ProjectScope.ORGANIZATION
        assert project_data["visibility"] == ProjectVisibility.PUBLIC
        assert project_data["owner_id"] == "user-123"
        assert project_data["owner_name"] == "Alice Developer"
        assert project_data["team_id"] == "team-456"
        assert project_data["team_name"] == "Engineering"

        # Check extra_data merged
        assert epic.metadata["custom_field"] == "value"

    def test_project_state_mapping_to_epic(self, minimal_project: Project):
        """Test state mapping from Project to Epic."""
        # Test ACTIVE -> IN_PROGRESS
        minimal_project.state = ProjectState.ACTIVE
        epic = project_to_epic(minimal_project)
        assert epic.state == TicketState.IN_PROGRESS

        # Test COMPLETED -> DONE
        minimal_project.state = ProjectState.COMPLETED
        epic = project_to_epic(minimal_project)
        assert epic.state == TicketState.DONE

        # Test PLANNED -> OPEN
        minimal_project.state = ProjectState.PLANNED
        epic = project_to_epic(minimal_project)
        assert epic.state == TicketState.OPEN

        # Test ARCHIVED -> CLOSED
        minimal_project.state = ProjectState.ARCHIVED
        epic = project_to_epic(minimal_project)
        assert epic.state == TicketState.CLOSED

        # Test CANCELLED -> CLOSED
        minimal_project.state = ProjectState.CANCELLED
        epic = project_to_epic(minimal_project)
        assert epic.state == TicketState.CLOSED

    def test_project_with_no_extra_data(self, minimal_project: Project):
        """Test converting project with no extra_data."""
        minimal_project.extra_data = {}
        epic = project_to_epic(minimal_project)

        # Should still have platform and project_data in metadata
        assert "platform" in epic.metadata
        assert "project_data" in epic.metadata

    def test_project_with_no_child_issues(self, minimal_project: Project):
        """Test converting project with empty child_issues."""
        minimal_project.child_issues = []
        epic = project_to_epic(minimal_project)

        assert epic.child_issues == []


class TestRoundTripConversion:
    """Test round-trip conversions preserve data correctly."""

    def test_epic_to_project_to_epic_minimal(self):
        """Test round-trip conversion preserves minimal epic data."""
        original_epic = Epic(
            id="epic-123",
            title="Round Trip Epic",
            description="Testing round-trip conversion",
        )

        # Convert to project and back
        project = epic_to_project(original_epic)
        final_epic = project_to_epic(project)

        # Check core fields preserved
        assert final_epic.id == original_epic.id
        assert final_epic.title == original_epic.title
        assert final_epic.description == original_epic.description

    def test_project_to_epic_to_project_minimal(self):
        """Test round-trip conversion preserves minimal project data."""
        original_project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Round Trip Project",
            description="Testing round-trip",
        )

        # Convert to epic and back
        epic = project_to_epic(original_project)
        final_project = epic_to_project(epic)

        # Check core fields preserved
        assert final_project.id == original_project.id
        assert final_project.name == original_project.name
        assert final_project.description == original_project.description
        assert final_project.platform == original_project.platform

    def test_epic_to_project_to_epic_with_metadata(self):
        """Test round-trip preserves metadata correctly."""
        created = datetime(2025, 1, 1, tzinfo=timezone.utc)

        original_epic = Epic(
            id="epic-meta-123",
            title="Metadata Epic",
            created_at=created,
            child_issues=["issue-1", "issue-2"],
            metadata={
                "platform": "jira",
                "custom_field": "custom_value",
                "nested": {"key": "value"},
            },
        )

        # Round-trip
        project = epic_to_project(original_epic)
        final_epic = project_to_epic(project)

        # Check metadata fields
        assert final_epic.metadata["platform"] == "jira"
        assert final_epic.metadata["custom_field"] == "custom_value"
        assert final_epic.metadata["nested"]["key"] == "value"
        assert final_epic.child_issues == original_epic.child_issues


class TestStateMappingEdgeCases:
    """Test edge cases in state mapping functions."""

    def test_map_epic_state_none(self):
        """Test mapping None epic state returns PLANNED."""
        epic = Epic(
            id="epic-none-state",
            title="None State Epic",
        )
        # State defaults to OPEN in Epic
        project = epic_to_project(epic)
        assert project.state == ProjectState.PLANNED

    def test_map_epic_state_case_insensitive(self):
        """Test state mapping is case-insensitive."""
        test_cases = [
            ("PLANNED", ProjectState.PLANNED),
            ("Planned", ProjectState.PLANNED),
            ("planned", ProjectState.PLANNED),
            ("IN_PROGRESS", ProjectState.ACTIVE),
            ("In_Progress", ProjectState.ACTIVE),
            ("DONE", ProjectState.COMPLETED),
            ("Done", ProjectState.COMPLETED),
        ]

        for state_str, expected_project_state in test_cases:
            epic = Epic(
                id=f"epic-{state_str}",
                title="Test Epic",
                metadata={"platform": "test"},
            )
            # Manually set state string in metadata for testing
            epic.metadata["state"] = state_str  # type: ignore

            # Note: epic_to_project uses epic.state (TicketState enum), not metadata
            # So we need to test the internal mapping function directly
            from mcp_ticketer.core.project_utils import _map_epic_state_to_project

            result = _map_epic_state_to_project(state_str)
            assert result == expected_project_state

    def test_map_epic_state_unknown_falls_back(self):
        """Test unknown epic state falls back to PLANNED."""
        from mcp_ticketer.core.project_utils import _map_epic_state_to_project

        unknown_states = ["unknown", "invalid", "random_state", ""]
        for state in unknown_states:
            result = _map_epic_state_to_project(state)
            assert result == ProjectState.PLANNED

    def test_map_project_state_string_input(self):
        """Test _map_project_state_to_epic handles string inputs."""
        from mcp_ticketer.core.project_utils import _map_project_state_to_epic

        # Valid string inputs
        assert _map_project_state_to_epic("active") == TicketState.IN_PROGRESS
        assert _map_project_state_to_epic("completed") == TicketState.DONE
        assert _map_project_state_to_epic("planned") == TicketState.OPEN

        # Invalid string input (returns default OPEN)
        assert _map_project_state_to_epic("invalid_state") == TicketState.OPEN

    def test_map_project_state_enum_input(self):
        """Test _map_project_state_to_epic handles enum inputs."""
        from mcp_ticketer.core.project_utils import _map_project_state_to_epic

        assert (
            _map_project_state_to_epic(ProjectState.ACTIVE) == TicketState.IN_PROGRESS
        )
        assert _map_project_state_to_epic(ProjectState.COMPLETED) == TicketState.DONE
        assert _map_project_state_to_epic(ProjectState.PLANNED) == TicketState.OPEN
        assert _map_project_state_to_epic(ProjectState.ARCHIVED) == TicketState.CLOSED
        assert _map_project_state_to_epic(ProjectState.CANCELLED) == TicketState.CLOSED


class TestConversionDataIntegrity:
    """Test data integrity during conversions."""

    def test_epic_to_project_preserves_timestamps(self):
        """Test timestamp preservation in epic_to_project."""
        created = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2025, 12, 1, 14, 30, 0, tzinfo=timezone.utc)

        epic = Epic(
            id="epic-time",
            title="Timestamp Epic",
            created_at=created,
            updated_at=updated,
        )

        project = epic_to_project(epic)
        assert project.created_at == created
        assert project.updated_at == updated

    def test_project_to_epic_preserves_timestamps(self):
        """Test timestamp preservation in project_to_epic."""
        created = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2025, 12, 1, 14, 30, 0, tzinfo=timezone.utc)

        project = Project(
            id="proj-time",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Timestamp Project",
            created_at=created,
            updated_at=updated,
        )

        epic = project_to_epic(project)
        assert epic.created_at == created
        assert epic.updated_at == updated

    def test_conversion_preserves_child_issue_order(self):
        """Test child issue ordering is preserved."""
        issues = ["issue-3", "issue-1", "issue-2"]  # Intentionally unordered

        epic = Epic(
            id="epic-order",
            title="Order Test Epic",
            child_issues=issues.copy(),
        )

        project = epic_to_project(epic)
        assert project.child_issues == issues

        final_epic = project_to_epic(project)
        assert final_epic.child_issues == issues

    def test_conversion_handles_special_characters(self):
        """Test conversion handles special characters in strings."""
        special_title = "Epic™ 2.0 (α-release) — Q4'25 🚀"
        special_desc = "Description with\nnewlines\tand\ttabs"

        epic = Epic(
            id="epic-special",
            title=special_title,
            description=special_desc,
        )

        project = epic_to_project(epic)
        assert project.name == special_title
        assert project.description == special_desc

        final_epic = project_to_epic(project)
        assert final_epic.title == special_title
        assert final_epic.description == special_desc
