"""Tests for GitHub adapter label creation error handling."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter
from mcp_ticketer.core.models import Priority, Task, TicketState


@pytest.fixture
def mock_config() -> dict[str, Any]:
    """Provide mock configuration for GitHub adapter."""
    return {
        "token": "test_token",
        "owner": "test-owner",
        "repo": "test-repo",
    }


@pytest.fixture
def github_adapter(mock_config: dict[str, Any]) -> GitHubAdapter:
    """Create a GitHub adapter instance with mocked client."""
    with patch("mcp_ticketer.adapters.github.adapter.httpx.AsyncClient"):
        adapter = GitHubAdapter(mock_config)
        adapter.client = AsyncMock()
        return adapter


class TestEnsureLabelExists:
    """Test cases for _ensure_label_exists method."""

    @pytest.mark.asyncio
    async def test_label_already_exists_in_cache(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test that existing labels return True without API calls."""
        # Setup: Populate cache with existing label
        await github_adapter._labels_cache.set(
            "github_labels",
            [
                {"name": "bug", "color": "d73a4a"},
                {"name": "feature", "color": "0366d6"},
            ],
        )

        # Execute
        result = await github_adapter._ensure_label_exists("bug")

        # Verify: Returns True, no POST request made
        assert result is True
        github_adapter.client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_label_creation_success_201(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test successful label creation returns True."""
        # Setup: Empty cache, successful creation
        await github_adapter._labels_cache.set("github_labels", [])
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"name": "new-label", "color": "0366d6"}
        github_adapter.client.post.return_value = mock_response

        # Execute
        result = await github_adapter._ensure_label_exists("new-label", "0366d6")

        # Verify: Returns True, label added to cache
        assert result is True
        github_adapter.client.post.assert_called_once()
        cached_labels = await github_adapter._labels_cache.get("github_labels")
        assert len(cached_labels) == 1
        assert cached_labels[0]["name"] == "new-label"

    @pytest.mark.asyncio
    async def test_label_creation_race_condition_422(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test 422 status (race condition) returns True."""
        # Setup: Empty cache, 422 response (label already exists)
        await github_adapter._labels_cache.set("github_labels", [])
        mock_response = MagicMock()
        mock_response.status_code = 422
        github_adapter.client.post.return_value = mock_response

        # Execute
        result = await github_adapter._ensure_label_exists("race-label")

        # Verify: Returns True (race condition is acceptable)
        assert result is True

    @pytest.mark.asyncio
    async def test_label_creation_permission_denied_403(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test 403 status (permission denied) returns False and logs warning."""
        # Setup: Empty cache, 403 response
        await github_adapter._labels_cache.set("github_labels", [])
        mock_response = MagicMock()
        mock_response.status_code = 403
        github_adapter.client.post.return_value = mock_response

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter._ensure_label_exists("forbidden-label")

            # Verify: Returns False, warning logged
            assert result is False
            mock_logger.warning.assert_called_once()
            assert "Permission denied" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_label_creation_other_error_500(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test other errors (500, etc.) return False and log warning."""
        # Setup: Empty cache, 500 response
        await github_adapter._labels_cache.set("github_labels", [])
        mock_response = MagicMock()
        mock_response.status_code = 500
        github_adapter.client.post.return_value = mock_response

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter._ensure_label_exists("error-label")

            # Verify: Returns False, warning logged
            assert result is False
            mock_logger.warning.assert_called_once()
            assert "status 500" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_cache_fetch_failure(self, github_adapter: GitHubAdapter) -> None:
        """Test cache fetch failure returns False and logs warning."""
        # Setup: Make cache fetch fail
        github_adapter.client.get.side_effect = Exception("Network error")

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter._ensure_label_exists("test-label")

            # Verify: Returns False, warning logged
            assert result is False
            mock_logger.warning.assert_called_once()
            assert "Failed to fetch labels cache" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_case_insensitive_label_matching(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test that label matching is case-insensitive."""
        # Setup: Cache with mixed-case label
        await github_adapter._labels_cache.set(
            "github_labels", [{"name": "BugFix", "color": "d73a4a"}]
        )

        # Execute: Try to create same label with different case
        result = await github_adapter._ensure_label_exists("bugfix")

        # Verify: Returns True (label exists), no POST call
        assert result is True
        github_adapter.client.post.assert_not_called()


class TestCreateWithLabelTracking:
    """Test create() method tracks label creation success/failure."""

    @pytest.mark.asyncio
    async def test_create_tracks_failed_labels(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test create() logs warning when labels fail to create."""
        # Setup: Start with empty cache, mock GET to return empty list
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = []
        github_adapter.client.get.return_value = get_response

        # Make state label creation fail (403)
        state_response = MagicMock()
        state_response.status_code = 403

        # Make priority label creation succeed (201)
        priority_response = MagicMock()
        priority_response.status_code = 201
        priority_response.json.return_value = {"name": "P2", "color": "d73a4a"}

        # Make custom tag creation fail (500)
        tag_response = MagicMock()
        tag_response.status_code = 500

        # Mock issue creation
        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 1,
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [],
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Set up side effects for POST calls
        # Note: labels are checked twice - once explicitly, once in the loop
        github_adapter.client.post.side_effect = [
            state_response,  # Explicit check for state label
            priority_response,  # Explicit check for priority label
            state_response,  # Loop check for state label (in labels list)
            # priority_label skipped in loop (already in cache)
            tag_response,  # Loop check for custom-tag
            issue_response,  # Issue creation
        ]

        # Create ticket with tags
        ticket = Task(
            id="",
            title="Test Issue",
            description="Test body",
            state=TicketState.IN_PROGRESS,
            priority=Priority.MEDIUM,
            tags=["custom-tag"],
        )

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter.create(ticket)

            # Verify: Issue created, but warning logged for failed labels
            assert result is not None
            mock_logger.warning.assert_called()

            # Check that warning mentions failed labels
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "Failed to ensure existence of labels" in call for call in warning_calls
            )

    @pytest.mark.asyncio
    async def test_create_no_warning_when_all_labels_succeed(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test create() does not log warning when all labels succeed."""
        # Setup: Mock GET to return empty labels
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = []
        github_adapter.client.get.return_value = get_response

        label_response = MagicMock()
        label_response.status_code = 201
        label_response.json.return_value = {
            "name": "P3",
            "color": "d73a4a",
        }  # LOW priority = P3

        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 1,
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [],
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        github_adapter.client.post.side_effect = [
            label_response,  # priority label (OPEN state has no label)
            issue_response,  # issue creation
        ]

        ticket = Task(
            id="",
            title="Test Issue",
            description="Test body",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        )

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter.create(ticket)

            # Verify: No warning about failed labels
            assert result is not None
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "Failed to ensure existence" in str(call)
            ]
            assert len(warning_calls) == 0


class TestUpdateWithLabelTracking:
    """Test update() method tracks label creation success/failure."""

    @pytest.mark.asyncio
    async def test_update_tracks_failed_labels(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test update() logs warning when labels fail to create."""
        # Setup: Mock GET for labels cache
        get_labels_response = MagicMock()
        get_labels_response.status_code = 200
        get_labels_response.json.return_value = []

        # Setup: Mock GET for current issue
        current_issue_response = MagicMock()
        current_issue_response.status_code = 200
        current_issue_response.json.return_value = {
            "id": 1,
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [{"name": "bug"}],
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Return different responses based on URL
        def get_side_effect(url: str) -> MagicMock:
            if "labels" in url and "issues" not in url:
                return get_labels_response
            return current_issue_response

        github_adapter.client.get.side_effect = get_side_effect

        # Make label creation fail
        label_response = MagicMock()
        label_response.status_code = 403
        github_adapter.client.post.return_value = label_response

        # Mock update response
        update_response = MagicMock()
        update_response.status_code = 200
        update_response.json.return_value = current_issue_response.json.return_value
        github_adapter.client.patch.return_value = update_response

        # Execute
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            result = await github_adapter.update(
                "1", {"priority": Priority.CRITICAL, "tags": ["new-tag"]}
            )

            # Verify: Warning logged for failed labels
            assert result is not None
            warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
            assert any(
                "Failed to ensure existence of labels" in call for call in warning_calls
            )

    @pytest.mark.asyncio
    async def test_update_deduplicates_failed_labels(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test update() does not duplicate labels in failed_labels list."""
        # Setup: Mock GET for labels cache
        get_labels_response = MagicMock()
        get_labels_response.status_code = 200
        get_labels_response.json.return_value = []

        # Setup: Mock GET for current issue
        current_issue_response = MagicMock()
        current_issue_response.status_code = 200
        current_issue_response.json.return_value = {
            "id": 1,
            "number": 1,
            "title": "Test Issue",
            "body": "Test body",
            "state": "open",
            "labels": [],
            "html_url": "https://github.com/test-owner/test-repo/issues/1",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Return different responses based on URL
        def get_side_effect(url: str) -> MagicMock:
            if "labels" in url and "issues" not in url:
                return get_labels_response
            return current_issue_response

        github_adapter.client.get.side_effect = get_side_effect

        # All label creations fail
        label_response = MagicMock()
        label_response.status_code = 403
        github_adapter.client.post.return_value = label_response

        update_response = MagicMock()
        update_response.status_code = 200
        update_response.json.return_value = current_issue_response.json.return_value
        github_adapter.client.patch.return_value = update_response

        # Execute: Update both state and tags with overlapping labels
        with patch("mcp_ticketer.adapters.github.adapter.logger") as mock_logger:
            await github_adapter.update(
                "1",
                {
                    "state": TicketState.IN_PROGRESS,
                    "tags": ["tag1", "tag2"],
                },
            )

            # Verify: Warning called, check failed labels don't have duplicates
            mock_logger.warning.assert_called()
            warning_msg = str(mock_logger.warning.call_args)
            # Should only mention each label once
            assert warning_msg.count("tag1") <= 2  # Once in list, maybe once in message
