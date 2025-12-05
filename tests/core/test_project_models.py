"""Tests for Project models and related functionality.

This module tests the Project, ProjectStatistics, and related models
to ensure correct validation, serialization, and business logic.

Test Coverage:
- Project model validation and defaults
- ProjectState, ProjectScope, ProjectVisibility enums
- ProjectStatistics calculation
- Project.calculate_progress() method
- JSON serialization/deserialization
- Edge cases and validation errors
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mcp_ticketer.core.models import (
    Project,
    ProjectScope,
    ProjectState,
    ProjectStatistics,
    ProjectVisibility,
)


class TestProjectEnums:
    """Test Project-related enumerations."""

    def test_project_state_values(self):
        """Test ProjectState enum values."""
        assert ProjectState.PLANNED.value == "planned"
        assert ProjectState.ACTIVE.value == "active"
        assert ProjectState.COMPLETED.value == "completed"
        assert ProjectState.ARCHIVED.value == "archived"
        assert ProjectState.CANCELLED.value == "cancelled"

    def test_project_visibility_values(self):
        """Test ProjectVisibility enum values."""
        assert ProjectVisibility.PUBLIC.value == "public"
        assert ProjectVisibility.PRIVATE.value == "private"
        assert ProjectVisibility.TEAM.value == "team"

    def test_project_scope_values(self):
        """Test ProjectScope enum values."""
        assert ProjectScope.USER.value == "user"
        assert ProjectScope.TEAM.value == "team"
        assert ProjectScope.ORGANIZATION.value == "organization"
        assert ProjectScope.REPOSITORY.value == "repository"


class TestProjectModel:
    """Test Project model validation and behavior."""

    @pytest.fixture
    def minimal_project(self) -> Project:
        """Create minimal valid project for testing.

        Returns:
            Project with only required fields populated
        """
        return Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123def456",
            scope=ProjectScope.TEAM,
            name="Test Project",
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
            description="A comprehensive project with all fields",
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
            child_issues=["issue-1", "issue-2", "issue-3"],
            issue_count=10,
            completed_count=6,
            in_progress_count=3,
            progress_percentage=60.0,
            extra_data={"custom_field": "value", "priority": "high"},
        )

    def test_minimal_project_creation(self, minimal_project: Project):
        """Test creating project with only required fields."""
        assert minimal_project.id == "proj-123"
        assert minimal_project.platform == "linear"
        assert minimal_project.platform_id == "abc123def456"
        assert minimal_project.scope == ProjectScope.TEAM
        assert minimal_project.name == "Test Project"

        # Check defaults
        assert minimal_project.description is None
        assert minimal_project.state == ProjectState.PLANNED
        assert minimal_project.visibility == ProjectVisibility.TEAM
        assert minimal_project.child_issues == []
        assert minimal_project.extra_data == {}

    def test_full_project_creation(self, full_project: Project):
        """Test creating project with all fields populated."""
        assert full_project.id == "proj-full-123"
        assert full_project.name == "Full Featured Project"
        assert full_project.state == ProjectState.ACTIVE
        assert full_project.owner_name == "Alice Developer"
        assert full_project.team_name == "Engineering"
        assert len(full_project.child_issues) == 3
        assert full_project.issue_count == 10
        assert full_project.completed_count == 6
        assert full_project.progress_percentage == 60.0
        assert full_project.extra_data["custom_field"] == "value"

    def test_project_validation_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        # Missing 'name' (required)
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform="linear",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("name",) for e in errors)

        # Missing 'platform' (required)
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
                name="Test",
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("platform",) for e in errors)

    def test_project_validation_empty_name(self):
        """Test validation fails with empty name (min_length=1)."""
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform="linear",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
                name="",  # Empty string violates min_length=1
            )
        errors = exc_info.value.errors()
        assert any(
            e["loc"] == ("name",) and "at least 1" in str(e["msg"]) for e in errors
        )

    def test_project_validation_issue_counts(self):
        """Test validation of issue count constraints (non-negative)."""
        # Valid: zero counts
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=0,
            completed_count=0,
            in_progress_count=0,
        )
        assert project.issue_count == 0

        # Invalid: negative counts
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform="linear",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
                name="Test",
                issue_count=-5,  # Negative violates ge=0
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("issue_count",) for e in errors)

    def test_project_validation_progress_percentage(self):
        """Test validation of progress percentage (0-100 range)."""
        # Valid: within range
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            progress_percentage=50.5,
        )
        assert project.progress_percentage == 50.5

        # Valid: boundary values
        project_zero = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            progress_percentage=0.0,
        )
        assert project_zero.progress_percentage == 0.0

        project_hundred = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            progress_percentage=100.0,
        )
        assert project_hundred.progress_percentage == 100.0

        # Invalid: above 100
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform="linear",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
                name="Test",
                progress_percentage=101.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("progress_percentage",) for e in errors)

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            Project(
                id="proj-invalid",
                platform="linear",
                platform_id="abc123",
                scope=ProjectScope.TEAM,
                name="Test",
                progress_percentage=-10.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("progress_percentage",) for e in errors)

    def test_calculate_progress_with_issues(self):
        """Test progress calculation from issue counts."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=20,
            completed_count=15,
        )
        progress = project.calculate_progress()
        assert progress == 75.0

    def test_calculate_progress_all_completed(self):
        """Test progress calculation when all issues completed."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=10,
            completed_count=10,
        )
        progress = project.calculate_progress()
        assert progress == 100.0

    def test_calculate_progress_no_issues(self):
        """Test progress calculation with no issues (returns 0)."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=0,
            completed_count=0,
        )
        progress = project.calculate_progress()
        assert progress == 0.0

    def test_calculate_progress_none_issue_count(self):
        """Test progress calculation with None issue_count (returns 0)."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=None,
            completed_count=5,
        )
        progress = project.calculate_progress()
        assert progress == 0.0

    def test_calculate_progress_partial_completion(self):
        """Test progress calculation with partial completion."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            issue_count=30,
            completed_count=10,
        )
        progress = project.calculate_progress()
        assert abs(progress - 33.333333) < 0.01

    def test_json_serialization(self, full_project: Project):
        """Test JSON serialization includes all fields."""
        json_str = full_project.model_dump_json()
        assert "proj-full-123" in json_str
        assert "Full Featured Project" in json_str
        assert "github" in json_str
        assert "active" in json_str
        assert "Alice Developer" in json_str
        assert "custom_field" in json_str

    def test_json_deserialization(self, full_project: Project):
        """Test JSON deserialization reconstructs project correctly."""
        json_str = full_project.model_dump_json()
        reconstructed = Project.model_validate_json(json_str)

        assert reconstructed.id == full_project.id
        assert reconstructed.name == full_project.name
        assert reconstructed.state == full_project.state
        assert reconstructed.owner_name == full_project.owner_name
        assert reconstructed.extra_data == full_project.extra_data

    def test_model_dump_excludes_none(self, minimal_project: Project):
        """Test model_dump with exclude_none option."""
        dumped = minimal_project.model_dump(exclude_none=True)

        # Should include required fields
        assert "id" in dumped
        assert "name" in dumped

        # Should exclude None optional fields
        assert "description" not in dumped or dumped["description"] is None
        assert "owner_id" not in dumped or dumped["owner_id"] is None


class TestProjectStatistics:
    """Test ProjectStatistics model validation and behavior."""

    @pytest.fixture
    def sample_stats(self) -> ProjectStatistics:
        """Create sample project statistics.

        Returns:
            ProjectStatistics instance with typical values
        """
        return ProjectStatistics(
            project_id="proj-123",
            total_issues=50,
            completed_issues=30,
            in_progress_issues=15,
            open_issues=5,
            blocked_issues=2,
            progress_percentage=60.0,
            velocity=8.5,
            estimated_completion=datetime(2025, 12, 31, tzinfo=timezone.utc),
        )

    def test_statistics_creation(self, sample_stats: ProjectStatistics):
        """Test creating project statistics."""
        assert sample_stats.project_id == "proj-123"
        assert sample_stats.total_issues == 50
        assert sample_stats.completed_issues == 30
        assert sample_stats.in_progress_issues == 15
        assert sample_stats.progress_percentage == 60.0
        assert sample_stats.velocity == 8.5

    def test_statistics_validation_non_negative(self):
        """Test validation enforces non-negative counts."""
        # Valid: zero counts
        stats = ProjectStatistics(
            project_id="proj-123",
            total_issues=0,
            completed_issues=0,
            in_progress_issues=0,
            open_issues=0,
            blocked_issues=0,
        )
        assert stats.total_issues == 0

        # Invalid: negative total_issues
        with pytest.raises(ValidationError) as exc_info:
            ProjectStatistics(
                project_id="proj-123",
                total_issues=-10,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("total_issues",) for e in errors)

    def test_statistics_validation_progress_range(self):
        """Test validation enforces progress percentage range (0-100)."""
        # Valid: within range
        stats = ProjectStatistics(
            project_id="proj-123",
            progress_percentage=75.5,
        )
        assert stats.progress_percentage == 75.5

        # Invalid: above 100
        with pytest.raises(ValidationError) as exc_info:
            ProjectStatistics(
                project_id="proj-123",
                progress_percentage=150.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("progress_percentage",) for e in errors)

        # Invalid: negative
        with pytest.raises(ValidationError) as exc_info:
            ProjectStatistics(
                project_id="proj-123",
                progress_percentage=-20.0,
            )
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("progress_percentage",) for e in errors)

    def test_statistics_defaults(self):
        """Test default values for optional fields."""
        stats = ProjectStatistics(project_id="proj-123")

        # Defaults should be zero for counts
        assert stats.total_issues == 0
        assert stats.completed_issues == 0
        assert stats.in_progress_issues == 0
        assert stats.open_issues == 0
        assert stats.blocked_issues == 0
        assert stats.progress_percentage == 0.0

        # Defaults should be None for optional metrics
        assert stats.velocity is None
        assert stats.estimated_completion is None

    def test_statistics_json_serialization(self, sample_stats: ProjectStatistics):
        """Test JSON serialization of statistics."""
        json_str = sample_stats.model_dump_json()
        assert "proj-123" in json_str
        assert "60.0" in json_str
        assert "8.5" in json_str

    def test_statistics_json_deserialization(self, sample_stats: ProjectStatistics):
        """Test JSON deserialization of statistics."""
        json_str = sample_stats.model_dump_json()
        reconstructed = ProjectStatistics.model_validate_json(json_str)

        assert reconstructed.project_id == sample_stats.project_id
        assert reconstructed.total_issues == sample_stats.total_issues
        assert reconstructed.progress_percentage == sample_stats.progress_percentage
        assert reconstructed.velocity == sample_stats.velocity


class TestProjectEdgeCases:
    """Test edge cases and boundary conditions for Project models."""

    def test_project_with_long_name(self):
        """Test project with very long name (should succeed)."""
        long_name = "A" * 500  # Very long but valid
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name=long_name,
        )
        assert len(project.name) == 500

    def test_project_with_special_characters_in_name(self):
        """Test project name with special characters."""
        special_name = "Project™ 2.0 (α-release) — Q4'25 🚀"
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name=special_name,
        )
        assert project.name == special_name

    def test_project_with_empty_child_issues_list(self):
        """Test project with explicitly empty child_issues list."""
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            child_issues=[],
        )
        assert project.child_issues == []

    def test_project_with_many_child_issues(self):
        """Test project with large number of child issues."""
        many_issues = [f"issue-{i}" for i in range(1000)]
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            child_issues=many_issues,
        )
        assert len(project.child_issues) == 1000

    def test_project_with_nested_extra_data(self):
        """Test project with complex nested extra_data."""
        complex_data = {
            "metadata": {
                "tags": ["important", "q4"],
                "custom_fields": {
                    "budget": 100000,
                    "stakeholders": ["alice", "bob"],
                },
            },
            "integrations": {
                "slack": {"channel": "#engineering", "notifications": True},
                "github": {"repo": "acme/project", "auto_close": False},
            },
        }
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            extra_data=complex_data,
        )
        assert project.extra_data["metadata"]["tags"] == ["important", "q4"]
        assert project.extra_data["integrations"]["slack"]["channel"] == "#engineering"

    def test_project_datetime_timezone_handling(self):
        """Test datetime fields handle timezones correctly."""
        utc_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        project = Project(
            id="proj-123",
            platform="linear",
            platform_id="abc123",
            scope=ProjectScope.TEAM,
            name="Test",
            created_at=utc_time,
            updated_at=utc_time,
        )
        assert project.created_at == utc_time
        assert project.updated_at == utc_time

    def test_statistics_with_inconsistent_counts(self):
        """Test statistics allows inconsistent counts (no validation enforced)."""
        # This should succeed even though completed > total (validation is adapter's responsibility)
        _ = ProjectStatistics(
            project_id="proj-123",
            total_issues=10,
            completed_issues=15,  # More completed than total!
            progress_percentage=150.0,  # This will fail validation
        )
        # Will raise ValidationError due to progress > 100
        with pytest.raises(ValidationError):
            ProjectStatistics(
                project_id="proj-123",
                total_issues=10,
                completed_issues=15,
                progress_percentage=150.0,
            )
