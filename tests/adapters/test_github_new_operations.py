#!/usr/bin/env python3
"""Unit tests for new GitHub adapter operations.

Tests for:
- list_cycles() - GitHub Project V2 iterations
- get_issue_status() - Rich issue status information
- list_issue_statuses() - Available status definitions
- list_project_labels() - Labels for milestones
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.github import GitHubAdapter, GitHubStateMapping


@pytest.fixture
def github_adapter():
    """Create GitHub adapter instance for testing."""
    config = {
        "owner": "test-owner",
        "repo": "test-repo",
        "token": "test-token",
    }
    adapter = GitHubAdapter(config)
    return adapter


@pytest.mark.asyncio
class TestListCycles:
    """Test list_cycles() method for GitHub Project iterations."""

    async def test_list_cycles_success(self, github_adapter):
        """Test successful retrieval of project iterations."""
        # Mock GraphQL response
        mock_response = {
            "node": {
                "iterations": {
                    "nodes": [
                        {
                            "id": "PVTI_lADOABCD01234",
                            "title": "Sprint 1",
                            "startDate": "2024-01-01T00:00:00Z",
                            "duration": 14,
                        },
                        {
                            "id": "PVTI_lADOABCD05678",
                            "title": "Sprint 2",
                            "startDate": "2024-01-15T00:00:00Z",
                            "duration": 14,
                        },
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        github_adapter._graphql_request = AsyncMock(return_value=mock_response)

        # Execute method
        iterations = await github_adapter.list_cycles(
            project_id="PVT_kwDOABCD1234", limit=50
        )

        # Verify results
        assert len(iterations) == 2
        assert iterations[0]["id"] == "PVTI_lADOABCD01234"
        assert iterations[0]["title"] == "Sprint 1"
        assert iterations[0]["startDate"] == "2024-01-01T00:00:00Z"
        assert iterations[0]["duration"] == 14
        assert iterations[0]["endDate"] is not None  # Should be calculated

        # Verify end date calculation
        assert "2024-01-15" in iterations[0]["endDate"]

    async def test_list_cycles_no_project_id(self, github_adapter):
        """Test that ValueError is raised when project_id is missing."""
        with pytest.raises(ValueError) as exc_info:
            await github_adapter.list_cycles(project_id=None)

        assert "project_id is required" in str(exc_info.value)

    async def test_list_cycles_project_not_found(self, github_adapter):
        """Test error handling when project doesn't exist."""
        # Mock GraphQL response with null node
        mock_response = {"node": None}

        github_adapter._graphql_request = AsyncMock(return_value=mock_response)

        # Execute method and expect error
        with pytest.raises(ValueError) as exc_info:
            await github_adapter.list_cycles(project_id="PVT_invalid")

        assert "Project not found" in str(exc_info.value)

    async def test_list_cycles_invalid_credentials(self, github_adapter):
        """Test that invalid credentials raise ValueError."""
        # Mock invalid credentials
        github_adapter.token = None

        with pytest.raises(ValueError) as exc_info:
            await github_adapter.list_cycles(project_id="PVT_test")

        assert "GITHUB_TOKEN is required" in str(exc_info.value)

    async def test_list_cycles_empty_iterations(self, github_adapter):
        """Test handling of project with no iterations."""
        # Mock GraphQL response with empty iterations
        mock_response = {
            "node": {
                "iterations": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        github_adapter._graphql_request = AsyncMock(return_value=mock_response)

        # Execute method
        iterations = await github_adapter.list_cycles(project_id="PVT_test")

        # Verify empty list returned
        assert iterations == []


@pytest.mark.asyncio
class TestGetIssueStatus:
    """Test get_issue_status() method for rich status information."""

    async def test_get_issue_status_open_no_labels(self, github_adapter):
        """Test status for open issue with no extended state labels."""
        # Mock issue response
        mock_issue = {
            "number": 123,
            "state": "open",
            "title": "Test Issue",
            "html_url": "https://github.com/test/repo/issues/123",
            "labels": [{"name": "bug", "color": "d73a4a"}],
            "assignees": [],
            "milestone": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": None,
            "state_reason": None,
        }

        # Mock HTTP client response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        status = await github_adapter.get_issue_status(123)

        # Verify results
        assert status["number"] == 123
        assert status["state"] == "open"
        assert status["extended_state"] == "open"  # No extended label
        assert status["status_label"] is None
        assert "bug" in status["labels"]
        assert status["metadata"]["title"] == "Test Issue"

    async def test_get_issue_status_in_progress(self, github_adapter):
        """Test status for issue with in-progress label."""
        # Mock issue with in-progress label
        mock_issue = {
            "number": 124,
            "state": "open",
            "title": "In Progress Issue",
            "html_url": "https://github.com/test/repo/issues/124",
            "labels": [
                {"name": "in-progress", "color": "fbca04"},
                {"name": "feature", "color": "0075ca"},
            ],
            "assignees": [{"login": "developer1"}],
            "milestone": {"title": "v1.0"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": None,
            "state_reason": None,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        status = await github_adapter.get_issue_status(124)

        # Verify extended status
        assert status["state"] == "open"
        assert status["extended_state"] == "in_progress"
        assert status["status_label"] == "in-progress"
        assert status["metadata"]["assignees"] == ["developer1"]
        assert status["metadata"]["milestone"] == "v1.0"

    async def test_get_issue_status_closed(self, github_adapter):
        """Test status for closed issue."""
        # Mock closed issue
        mock_issue = {
            "number": 125,
            "state": "closed",
            "title": "Closed Issue",
            "html_url": "https://github.com/test/repo/issues/125",
            "labels": [],
            "assignees": [],
            "milestone": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": "2024-01-03T00:00:00Z",
            "state_reason": "completed",
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        status = await github_adapter.get_issue_status(125)

        # Verify closed status
        assert status["state"] == "closed"
        assert status["extended_state"] == "closed"
        assert status["state_reason"] == "completed"
        assert status["metadata"]["closed_at"] is not None

    async def test_get_issue_status_not_found(self, github_adapter):
        """Test error handling when issue doesn't exist."""
        # Mock 404 response
        mock_response = MagicMock()
        mock_response.status_code = 404

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method and expect error
        with pytest.raises(ValueError) as exc_info:
            await github_adapter.get_issue_status(999)

        assert "Issue #999 not found" in str(exc_info.value)

    async def test_get_issue_status_blocked(self, github_adapter):
        """Test status for blocked issue."""
        # Mock blocked issue
        mock_issue = {
            "number": 126,
            "state": "open",
            "title": "Blocked Issue",
            "html_url": "https://github.com/test/repo/issues/126",
            "labels": [{"name": "blocked", "color": "b60205"}],
            "assignees": [],
            "milestone": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "closed_at": None,
            "state_reason": None,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        status = await github_adapter.get_issue_status(126)

        # Verify blocked status
        assert status["extended_state"] == "blocked"
        assert status["status_label"] == "blocked"


@pytest.mark.asyncio
class TestListIssueStatuses:
    """Test list_issue_statuses() method."""

    async def test_list_issue_statuses_contains_all_states(self, github_adapter):
        """Test that all statuses are returned."""
        # Execute method
        statuses = await github_adapter.list_issue_statuses()

        # Verify native states
        status_names = [s["name"] for s in statuses]
        assert "open" in status_names
        assert "closed" in status_names

        # Verify extended states from GitHubStateMapping
        for state in GitHubStateMapping.STATE_LABELS.keys():
            assert state.value in status_names

    async def test_list_issue_statuses_structure(self, github_adapter):
        """Test that status dictionaries have correct structure."""
        # Execute method
        statuses = await github_adapter.list_issue_statuses()

        # Verify each status has required fields
        for status in statuses:
            assert "name" in status
            assert "type" in status
            assert "description" in status
            assert "category" in status
            assert status["type"] in ["native", "extended"]

    async def test_list_issue_statuses_native_vs_extended(self, github_adapter):
        """Test distinction between native and extended statuses."""
        # Execute method
        statuses = await github_adapter.list_issue_statuses()

        # Find native statuses
        native_statuses = [s for s in statuses if s["type"] == "native"]
        extended_statuses = [s for s in statuses if s["type"] == "extended"]

        # Verify counts
        assert len(native_statuses) == 2  # open, closed
        assert len(extended_statuses) == len(GitHubStateMapping.STATE_LABELS)

        # Verify native statuses have no labels
        for status in native_statuses:
            assert status["label"] is None

        # Verify extended statuses have labels
        for status in extended_statuses:
            assert status["label"] is not None


@pytest.mark.asyncio
class TestListProjectLabels:
    """Test list_project_labels() method."""

    async def test_list_project_labels_all_repository(self, github_adapter):
        """Test listing all repository labels when no milestone specified."""
        # Mock existing list_labels method
        mock_labels = [
            {"id": "bug", "name": "bug", "color": "d73a4a"},
            {"id": "feature", "name": "feature", "color": "0075ca"},
        ]

        github_adapter.list_labels = AsyncMock(return_value=mock_labels)

        # Execute method without milestone
        labels = await github_adapter.list_project_labels(milestone_number=None)

        # Verify delegation to list_labels
        assert labels == mock_labels
        github_adapter.list_labels.assert_called_once()

    async def test_list_project_labels_by_milestone(self, github_adapter):
        """Test listing labels for specific milestone."""
        # Mock issues in milestone
        mock_issues = [
            {
                "number": 1,
                "labels": [
                    {"name": "bug", "color": "d73a4a", "description": "Bug report"},
                    {
                        "name": "high-priority",
                        "color": "b60205",
                        "description": "High priority",
                    },
                ],
            },
            {
                "number": 2,
                "labels": [
                    {
                        "name": "bug",
                        "color": "d73a4a",
                        "description": "Bug report",
                    },  # Duplicate
                    {
                        "name": "feature",
                        "color": "0075ca",
                        "description": "New feature",
                    },
                ],
            },
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issues
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        labels = await github_adapter.list_project_labels(milestone_number=5)

        # Verify results
        assert len(labels) == 3  # bug, high-priority, feature
        label_names = [label["name"] for label in labels]
        assert "bug" in label_names
        assert "high-priority" in label_names
        assert "feature" in label_names

        # Verify usage counts
        bug_label = next(label for label in labels if label["name"] == "bug")
        assert bug_label["usage_count"] == 2  # Used by 2 issues

        high_priority_label = next(
            label for label in labels if label["name"] == "high-priority"
        )
        assert high_priority_label["usage_count"] == 1

    async def test_list_project_labels_excludes_pull_requests(self, github_adapter):
        """Test that pull requests are excluded from label counting."""
        # Mock issues including a PR
        mock_issues = [
            {"number": 1, "labels": [{"name": "bug", "color": "d73a4a"}]},
            {
                "number": 2,
                "pull_request": {
                    "url": "https://api.github.com/repos/test/repo/pulls/2"
                },
                "labels": [
                    {"name": "pr-label", "color": "0075ca"}
                ],  # Should be excluded
            },
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issues
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        labels = await github_adapter.list_project_labels(milestone_number=1)

        # Verify PR label not included
        label_names = [label["name"] for label in labels]
        assert "bug" in label_names
        assert "pr-label" not in label_names

    async def test_list_project_labels_sorted_by_usage(self, github_adapter):
        """Test that labels are sorted by usage count."""
        # Mock issues with varying label usage
        mock_issues = [
            {"number": 1, "labels": [{"name": "common", "color": "d73a4a"}]},
            {"number": 2, "labels": [{"name": "common", "color": "d73a4a"}]},
            {"number": 3, "labels": [{"name": "common", "color": "d73a4a"}]},
            {"number": 4, "labels": [{"name": "rare", "color": "0075ca"}]},
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issues
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        labels = await github_adapter.list_project_labels(milestone_number=1)

        # Verify sorting (most used first)
        assert labels[0]["name"] == "common"
        assert labels[0]["usage_count"] == 3
        assert labels[1]["name"] == "rare"
        assert labels[1]["usage_count"] == 1

    async def test_list_project_labels_empty_milestone(self, github_adapter):
        """Test handling of milestone with no issues."""
        # Mock empty issues list
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Execute method
        labels = await github_adapter.list_project_labels(milestone_number=999)

        # Verify empty list
        assert labels == []


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for new operations working together."""

    async def test_issue_workflow_with_status_tracking(self, github_adapter):
        """Test complete workflow using status methods."""
        # Mock issue at different states
        initial_issue = {
            "number": 100,
            "state": "open",
            "title": "New Feature",
            "html_url": "https://github.com/test/repo/issues/100",
            "labels": [],
            "assignees": [],
            "milestone": None,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "closed_at": None,
            "state_reason": None,
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = initial_issue
        mock_response.raise_for_status = MagicMock()

        github_adapter.client.get = AsyncMock(return_value=mock_response)

        # Get initial status
        status = await github_adapter.get_issue_status(100)
        assert status["extended_state"] == "open"

        # Get available statuses
        available_statuses = await github_adapter.list_issue_statuses()
        assert len(available_statuses) > 0

        # Verify we can transition to any extended state
        status_names = [s["name"] for s in available_statuses]
        assert "in_progress" in status_names
        assert "blocked" in status_names
        assert "ready" in status_names
