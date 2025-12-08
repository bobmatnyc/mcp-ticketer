"""Unit tests for GitHub Projects V2 mapper functions.

Tests the data transformation between GitHub ProjectV2 GraphQL responses
and our unified Project model.

Test Coverage:
- map_github_projectv2_to_project(): Project mapping with various configurations
- calculate_project_statistics(): Statistics calculation from project items
- Edge cases: missing fields, different scopes, date parsing
"""

from datetime import datetime, timezone

import pytest

from mcp_ticketer.adapters.github.mappers import (
    calculate_project_statistics,
    map_github_projectv2_to_project,
)
from mcp_ticketer.core.models import (
    ProjectScope,
    ProjectState,
    ProjectVisibility,
)


class TestMapGitHubProjectV2ToProject:
    """Test suite for map_github_projectv2_to_project() function."""

    def test_basic_organization_project(self):
        """Test mapping a basic organization project."""
        # Arrange
        project_data = {
            "id": "PVT_kwDOABcdefgh",
            "number": 5,
            "title": "Product Roadmap",
            "shortDescription": "Q4 2025 roadmap",
            "readme": "# Product Roadmap\n\nDetailed readme content",
            "public": True,
            "closed": False,
            "url": "https://github.com/orgs/test-org/projects/5",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-12-05T12:00:00Z",
            "closedAt": None,
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
                "id": "ORG123",
            },
            "items": {"totalCount": 42},
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert project.id == "PVT_kwDOABcdefgh"
        assert project.platform == "github"
        assert project.platform_id == "5"
        assert project.scope == ProjectScope.ORGANIZATION
        assert project.name == "Product Roadmap"
        assert project.description == "Q4 2025 roadmap"
        assert project.state == ProjectState.ACTIVE
        assert project.visibility == ProjectVisibility.PUBLIC
        assert project.url == "https://github.com/orgs/test-org/projects/5"
        assert project.owner_id == "ORG123"
        assert project.owner_name == "test-org"
        assert project.issue_count == 42
        assert project.extra_data["github"]["number"] == 5
        assert project.extra_data["github"]["owner_type"] == "Organization"

    def test_user_scoped_project(self):
        """Test mapping a user-scoped project."""
        # Arrange
        project_data = {
            "id": "PVT_user123",
            "number": 3,
            "title": "Personal Tasks",
            "shortDescription": None,
            "readme": None,
            "public": False,
            "closed": False,
            "url": "https://github.com/users/john-doe/projects/3",
            "createdAt": "2025-06-01T00:00:00Z",
            "updatedAt": "2025-12-01T00:00:00Z",
            "closedAt": None,
            "owner": {
                "__typename": "User",
                "login": "john-doe",
                "id": "USER456",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "john-doe")

        # Assert
        assert project.scope == ProjectScope.USER
        assert project.visibility == ProjectVisibility.PRIVATE
        assert project.owner_name == "john-doe"
        assert project.description is None

    def test_closed_project_recently(self):
        """Test mapping a recently closed project (COMPLETED state)."""
        # Arrange
        # Closed 10 days ago - should be COMPLETED
        closed_date = datetime.now(timezone.utc).replace(microsecond=0)
        closed_date_str = closed_date.isoformat().replace("+00:00", "Z")

        project_data = {
            "id": "PVT_closed1",
            "number": 10,
            "title": "Sprint 42",
            "shortDescription": "Completed sprint",
            "public": True,
            "closed": True,
            "url": "https://github.com/orgs/test-org/projects/10",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-12-05T12:00:00Z",
            "closedAt": closed_date_str,
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
                "id": "ORG123",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert project.state == ProjectState.COMPLETED
        assert project.completed_at is not None

    def test_closed_project_long_ago(self):
        """Test mapping a project closed long ago (ARCHIVED state)."""
        # Arrange
        # Closed 60 days ago - should be ARCHIVED
        project_data = {
            "id": "PVT_archived1",
            "number": 1,
            "title": "Ancient Project",
            "shortDescription": "Old project",
            "public": False,
            "closed": True,
            "url": "https://github.com/orgs/test-org/projects/1",
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-10-01T00:00:00Z",
            "closedAt": "2024-10-01T00:00:00Z",  # ~60 days ago
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
                "id": "ORG123",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert project.state == ProjectState.ARCHIVED

    def test_description_from_readme_fallback(self):
        """Test description extraction from readme when shortDescription is missing."""
        # Arrange
        project_data = {
            "id": "PVT_readme1",
            "number": 7,
            "title": "Readme Project",
            "shortDescription": None,
            "readme": "# Main Heading\n\nThis is the first line of the readme.\nSecond line here.",
            "public": True,
            "closed": False,
            "url": "https://github.com/orgs/test-org/projects/7",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-12-05T12:00:00Z",
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
                "id": "ORG123",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert project.description == "# Main Heading"

    def test_long_readme_truncation(self):
        """Test that long readme first lines are truncated."""
        # Arrange
        long_line = "A" * 300  # 300 characters
        project_data = {
            "id": "PVT_long1",
            "number": 8,
            "title": "Long Readme",
            "shortDescription": None,
            "readme": long_line,
            "public": True,
            "closed": False,
            "url": "https://github.com/orgs/test-org/projects/8",
            "createdAt": "2025-01-01T00:00:00Z",
            "updatedAt": "2025-12-05T12:00:00Z",
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
                "id": "ORG123",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert len(project.description) == 200
        assert project.description == "A" * 200

    def test_missing_optional_fields(self):
        """Test mapping with minimal required fields only."""
        # Arrange
        project_data = {
            "id": "PVT_minimal1",
            "number": 99,
            "title": "Minimal Project",
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert
        assert project.id == "PVT_minimal1"
        assert project.name == "Minimal Project"
        assert project.description is None
        assert project.url is None
        assert project.created_at is None
        assert project.updated_at is None
        assert project.issue_count is None

    def test_invalid_date_formats_handled(self):
        """Test that invalid date formats don't crash mapping."""
        # Arrange
        project_data = {
            "id": "PVT_baddate1",
            "number": 15,
            "title": "Bad Dates",
            "createdAt": "invalid-date",
            "updatedAt": "also-invalid",
            "closedAt": "not-a-date",
            "owner": {
                "__typename": "Organization",
                "login": "test-org",
            },
        }

        # Act
        project = map_github_projectv2_to_project(project_data, "test-org")

        # Assert - dates should be None, not crash
        assert project.created_at is None
        assert project.updated_at is None
        assert project.completed_at is None


class TestCalculateProjectStatistics:
    """Test suite for calculate_project_statistics() function."""

    def test_empty_project(self):
        """Test statistics for empty project."""
        # Arrange
        items_data = []

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert
        assert stats["total_issues"] == 0
        assert stats["total_issues_only"] == 0
        assert stats["open_issues"] == 0
        assert stats["in_progress_issues"] == 0
        assert stats["completed_issues"] == 0
        assert stats["blocked_issues"] == 0
        assert stats["priority_counts"] == {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

    def test_mixed_content_types(self):
        """Test that PRs and draft issues are counted separately."""
        # Arrange
        items_data = [
            {
                "id": "item1",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": []},
                },
            },
            {
                "id": "item2",
                "content": {
                    "__typename": "PullRequest",
                    "state": "OPEN",
                },
            },
            {
                "id": "item3",
                "content": {
                    "__typename": "DraftIssue",
                    "title": "Draft",
                },
            },
        ]

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert
        assert stats["total_issues"] == 3  # All items
        assert stats["total_issues_only"] == 1  # Only issues
        assert stats["open_issues"] == 1

    def test_state_counting(self):
        """Test counting issues by state."""
        # Arrange
        items_data = [
            {
                "id": "item1",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": []},
                },
            },
            {
                "id": "item2",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}]},
                },
            },
            {
                "id": "item3",
                "content": {
                    "__typename": "Issue",
                    "state": "CLOSED",
                    "labels": {"nodes": []},
                },
            },
            {
                "id": "item4",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "blocked"}]},
                },
            },
        ]

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert
        assert stats["total_issues_only"] == 4
        assert stats["open_issues"] == 1
        assert stats["in_progress_issues"] == 1
        assert stats["completed_issues"] == 1
        assert stats["blocked_issues"] == 1

    def test_priority_counting(self):
        """Test counting issues by priority labels."""
        # Arrange
        items_data = [
            {
                "id": "item1",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "P0"}]},
                },
            },
            {
                "id": "item2",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "P1"}, {"name": "bug"}]},
                },
            },
            {
                "id": "item3",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "P2"}]},
                },
            },
            {
                "id": "item4",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": []},  # No priority - defaults to medium
                },
            },
        ]

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert
        assert stats["priority_counts"]["critical"] == 1  # P0
        assert stats["priority_counts"]["high"] == 1  # P1
        assert stats["priority_counts"]["medium"] == 2  # P2 + default
        assert stats["priority_counts"]["low"] == 0

    def test_missing_labels_handled(self):
        """Test that issues without labels field are handled gracefully."""
        # Arrange
        items_data = [
            {
                "id": "item1",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    # No labels field
                },
            },
            {
                "id": "item2",
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": None,  # Explicitly None
                },
            },
        ]

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert - should not crash
        assert stats["total_issues_only"] == 2
        assert stats["open_issues"] == 2
        assert stats["priority_counts"]["medium"] == 2  # Default priority

    def test_realistic_project_statistics(self):
        """Test statistics calculation with realistic project data."""
        # Arrange
        items_data = [
            # 3 open issues
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "P1"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "P2"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": []},
                }
            },
            # 5 in-progress issues
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}, {"name": "P0"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}]},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "in-progress"}]},
                }
            },
            # 2 completed issues
            {
                "content": {
                    "__typename": "Issue",
                    "state": "CLOSED",
                    "labels": {"nodes": []},
                }
            },
            {
                "content": {
                    "__typename": "Issue",
                    "state": "CLOSED",
                    "labels": {"nodes": []},
                }
            },
            # 1 blocked issue
            {
                "content": {
                    "__typename": "Issue",
                    "state": "OPEN",
                    "labels": {"nodes": [{"name": "blocked"}, {"name": "P0"}]},
                }
            },
            # 2 pull requests (should be counted in total but not in states)
            {"content": {"__typename": "PullRequest", "state": "OPEN"}},
            {"content": {"__typename": "PullRequest", "state": "MERGED"}},
        ]

        # Act
        stats = calculate_project_statistics(items_data)

        # Assert
        assert stats["total_issues"] == 13  # All items
        assert stats["total_issues_only"] == 11  # Issues only (no PRs)
        assert stats["open_issues"] == 3
        assert stats["in_progress_issues"] == 5
        assert stats["completed_issues"] == 2
        assert stats["blocked_issues"] == 1
        assert stats["priority_counts"]["critical"] == 2  # 2x P0
        assert stats["priority_counts"]["high"] == 1  # 1x P1
        assert stats["priority_counts"]["medium"] == 8  # 1x P2 + 7x default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
