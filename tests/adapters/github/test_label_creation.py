"""Tests for GitHub adapter label creation error handling."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter
from mcp_ticketer.core.models import Epic, Priority, Task, TicketState, TicketType


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


class TestCreateEpicAutoLabeling:
    """Test that create() auto-applies the 'epic' label when creating an Epic."""

    @pytest.mark.asyncio
    async def test_create_epic_applies_epic_label(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test that creating an Epic adds the 'epic' label automatically.

        Covers the branch at adapter.py ~line 694:
            if isinstance(ticket, Epic) or getattr(ticket, 'ticket_type', None) == TicketType.EPIC:
                if 'epic' not in labels ...: labels.append('epic')
        """
        # Setup: empty labels cache so all label POSTs go through
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = []
        github_adapter.client.get.return_value = get_response

        label_response = MagicMock()
        label_response.status_code = 201
        label_response.json.return_value = {"name": "epic", "color": "0075ca"}

        priority_label_response = MagicMock()
        priority_label_response.status_code = 201
        priority_label_response.json.return_value = {"name": "P3", "color": "d73a4a"}

        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 10,
            "number": 10,
            "title": "Big Epic Feature",
            "body": "Epic description",
            "state": "open",
            "labels": [{"name": "epic"}, {"name": "P3"}],
            "html_url": "https://github.com/test-owner/test-repo/issues/10",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # The create() path calls _ensure_label_exists for 'epic' then 'P3',
        # then POSTs the issue itself.
        github_adapter.client.post.side_effect = [
            label_response,       # 'epic' label creation
            priority_label_response,  # priority label creation
            issue_response,       # issue creation
        ]

        epic = Epic(
            id="",
            title="Big Epic Feature",
            description="Epic description",
            state=TicketState.OPEN,
            priority=Priority.LOW,
        )

        result = await github_adapter.create(epic)

        assert result is not None
        assert result.title == "Big Epic Feature"

        # Verify the POST request for issue creation included 'epic' in labels
        issue_post_call = github_adapter.client.post.call_args_list[-1]
        sent_labels: list[str] = issue_post_call.kwargs["json"]["labels"]
        assert "epic" in sent_labels, (
            f"Expected 'epic' label in issue creation payload, got: {sent_labels}"
        )

    @pytest.mark.asyncio
    async def test_create_epic_does_not_duplicate_epic_label(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """Test that 'epic' is not added twice when already present in tags.

        When tags=["epic"] is passed to an Epic, the guard at line 695 should
        skip appending a second 'epic' entry, so the final label list contains
        it exactly once.
        """
        # Populate the cache upfront so _ensure_label_exists finds both labels
        # without making any POST calls, allowing a clean count of POST calls.
        await github_adapter._labels_cache.set(
            "github_labels",
            [
                {"name": "epic", "color": "0075ca"},
                {"name": "P2", "color": "d73a4a"},
            ],
        )

        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 11,
            "number": 11,
            "title": "Another Epic",
            "body": "",
            "state": "open",
            "labels": [{"name": "epic"}, {"name": "P2"}],
            "html_url": "https://github.com/test-owner/test-repo/issues/11",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        # Only one POST call expected: the issue creation itself.
        # All label ensures short-circuit because they're already cached.
        github_adapter.client.post.return_value = issue_response

        # Pass 'epic' explicitly in tags to exercise the de-dup guard
        epic = Epic(
            id="",
            title="Another Epic",
            description="",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
            tags=["epic"],
        )

        result = await github_adapter.create(epic)

        assert result is not None
        issue_post_call = github_adapter.client.post.call_args_list[-1]
        sent_labels: list[str] = issue_post_call.kwargs["json"]["labels"]
        assert sent_labels.count("epic") == 1, (
            f"'epic' label should appear exactly once, got: {sent_labels}"
        )


class TestCreateNodeIdFallback:
    """Test the node_id fallback path in create() when REST response omits node_id."""

    @pytest.mark.asyncio
    async def test_create_falls_back_to_get_issue_node_id(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """REST create response without node_id triggers _get_issue_node_id fallback.

        Covers the branch at adapter.py ~line 816:
            child_node_id = created_issue.get('node_id') or await self._get_issue_node_id(child_number)
        """
        # Setup: empty labels cache
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = []
        github_adapter.client.get.return_value = get_response

        priority_label_response = MagicMock()
        priority_label_response.status_code = 201
        priority_label_response.json.return_value = {"name": "P3", "color": "d73a4a"}

        # REST create response deliberately omits 'node_id'
        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 99,
            "number": 42,
            "title": "Child Issue",
            "body": "Child body",
            "state": "open",
            "labels": [],
            "html_url": "https://github.com/test-owner/test-repo/issues/42",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            # node_id intentionally absent
        }

        github_adapter.client.post.side_effect = [
            priority_label_response,  # priority label creation
            issue_response,           # issue creation (no node_id in response)
        ]

        # Mock _get_issue_node_id so the fallback path returns a known value
        github_adapter._get_issue_node_id = AsyncMock(return_value="I_fallback_node_42")

        # Mock _graphql_request so the addSubIssue mutation succeeds
        github_adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "I_parent_node", "number": 7, "title": "Parent"},
                    "subIssue": {"id": "I_fallback_node_42", "number": 42, "title": "Child Issue"},
                }
            }
        )

        # Also mock _get_issue_node_id for the parent lookup in create()
        # The create() code calls _get_issue_node_id twice:
        #   1. For the child (fallback, since node_id absent)
        #   2. For the parent
        github_adapter._get_issue_node_id = AsyncMock(
            side_effect=["I_fallback_node_42", "I_parent_node_7"]
        )

        ticket = Task(
            id="",
            title="Child Issue",
            description="Child body",
            state=TicketState.OPEN,
            priority=Priority.LOW,
            parent_issue="7",  # triggers the sub-issue linking path
        )

        result = await github_adapter.create(ticket)

        assert result is not None
        assert result.title == "Child Issue"

        # Verify _get_issue_node_id was called for the child (fallback)
        github_adapter._get_issue_node_id.assert_called()
        child_call_args = github_adapter._get_issue_node_id.call_args_list[0]
        assert child_call_args.args[0] == 42  # child issue number

        # Verify the addSubIssue GraphQL mutation was called with the fallback node ID
        github_adapter._graphql_request.assert_called_once()
        mutation_vars = github_adapter._graphql_request.call_args[0][1]
        assert mutation_vars["subIssueId"] == "I_fallback_node_42"
        assert mutation_vars["parentId"] == "I_parent_node_7"

    @pytest.mark.asyncio
    async def test_create_uses_rest_node_id_when_present(
        self, github_adapter: GitHubAdapter
    ) -> None:
        """When REST response includes node_id, _get_issue_node_id is NOT called for child.

        Verifies the happy-path branch so the fallback test is meaningful.
        """
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = []
        github_adapter.client.get.return_value = get_response

        priority_label_response = MagicMock()
        priority_label_response.status_code = 201
        priority_label_response.json.return_value = {"name": "P3", "color": "d73a4a"}

        # REST create response WITH node_id present
        issue_response = MagicMock()
        issue_response.status_code = 201
        issue_response.json.return_value = {
            "id": 100,
            "number": 55,
            "node_id": "I_present_node_55",
            "title": "Child With NodeId",
            "body": "",
            "state": "open",
            "labels": [],
            "html_url": "https://github.com/test-owner/test-repo/issues/55",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        github_adapter.client.post.side_effect = [
            priority_label_response,
            issue_response,
        ]

        # _get_issue_node_id should only be called for the PARENT, not the child
        github_adapter._get_issue_node_id = AsyncMock(return_value="I_parent_node_8")

        github_adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "I_parent_node_8", "number": 8, "title": "Parent"},
                    "subIssue": {
                        "id": "I_present_node_55",
                        "number": 55,
                        "title": "Child With NodeId",
                    },
                }
            }
        )

        ticket = Task(
            id="",
            title="Child With NodeId",
            description="",
            state=TicketState.OPEN,
            priority=Priority.LOW,
            parent_issue="8",
        )

        result = await github_adapter.create(ticket)

        assert result is not None

        # _get_issue_node_id called exactly once — only for the parent
        github_adapter._get_issue_node_id.assert_called_once_with(8)

        # The mutation used the node_id directly from the REST response
        mutation_vars = github_adapter._graphql_request.call_args[0][1]
        assert mutation_vars["subIssueId"] == "I_present_node_55"
