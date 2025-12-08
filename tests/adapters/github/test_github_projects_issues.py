"""Unit tests for GitHub Projects V2 issue operations (Week 3).

Tests the three issue operation methods:
- project_add_issue(): Add issues to projects
- project_remove_issue(): Remove issues from projects
- project_get_issues(): List issues in a project

Design Pattern: Mock-Based Unit Testing
----------------------------------------
All tests use mocked GraphQL client to avoid actual API calls:
- Fast execution (~100ms for full test suite)
- No network dependencies
- Predictable test data
- Full error coverage

Test Coverage Requirements:
- Success paths for all operations
- Error handling (validation, API errors, edge cases)
- ID format validation
- Duplicate/not found handling
- State filtering
- Pagination support
"""

from unittest.mock import AsyncMock, Mock

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter


@pytest.fixture
def adapter():
    """Create GitHubAdapter with mocked GraphQL client."""
    adapter = GitHubAdapter(
        config={
            "token": "test-token",
            "owner": "test-org",
            "repo": "test-repo",
        }
    )

    # Mock the GraphQL client
    adapter.gh_client = Mock()
    adapter.gh_client.execute_graphql = AsyncMock()

    # Also mock _graphql_request for issue node ID resolution
    adapter._graphql_request = AsyncMock()

    return adapter


# =============================================================================
# project_add_issue() Tests
# =============================================================================


class TestProjectAddIssue:
    """Tests for project_add_issue() method."""

    @pytest.mark.asyncio
    async def test_add_issue_by_node_id_success(self, adapter):
        """Test adding issue by node ID (I_kwDO...)."""
        # Mock successful addition
        adapter.gh_client.execute_graphql.return_value = {
            "addProjectV2ItemById": {
                "item": {
                    "id": "PVTI_TEST1",
                    "content": {
                        "id": "I_TEST",
                        "number": 123,
                        "title": "Test Issue",
                    },
                }
            }
        }

        result = await adapter.project_add_issue(
            project_id="PVT_TEST",
            issue_id="I_TEST",
        )

        assert result is True
        adapter.gh_client.execute_graphql.assert_called_once()

        # Verify mutation variables
        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args.kwargs["variables"]["projectId"] == "PVT_TEST"
        assert call_args.kwargs["variables"]["contentId"] == "I_TEST"

    @pytest.mark.asyncio
    async def test_add_issue_by_pr_node_id(self, adapter):
        """Test adding pull request by node ID (PR_kwDO...)."""
        adapter.gh_client.execute_graphql.return_value = {
            "addProjectV2ItemById": {
                "item": {
                    "id": "PVTI_TEST1",
                }
            }
        }

        result = await adapter.project_add_issue(
            project_id="PVT_TEST",
            issue_id="PR_TEST",
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_add_issue_by_number_format(self, adapter):
        """Test adding issue by owner/repo#number format."""
        # Mock issue node ID resolution
        adapter._graphql_request.return_value = {
            "repository": {"issue": {"id": "I_RESOLVED_NODE_ID"}}
        }

        # Mock successful addition
        adapter.gh_client.execute_graphql.return_value = {
            "addProjectV2ItemById": {"item": {"id": "PVTI_TEST1"}}
        }

        result = await adapter.project_add_issue(
            project_id="PVT_TEST",
            issue_id="test-org/test-repo#123",
        )

        assert result is True

        # Verify resolution query was called
        adapter._graphql_request.assert_called_once()
        call_args = adapter._graphql_request.call_args
        assert call_args.args[1]["owner"] == "test-org"
        assert call_args.args[1]["repo"] == "test-repo"
        assert call_args.args[1]["number"] == 123

        # Verify mutation used resolved node ID
        mutation_call = adapter.gh_client.execute_graphql.call_args
        assert mutation_call.kwargs["variables"]["contentId"] == "I_RESOLVED_NODE_ID"

    @pytest.mark.asyncio
    async def test_add_issue_already_exists(self, adapter):
        """Test adding issue that already exists (should return True)."""
        # Mock error for duplicate
        adapter.gh_client.execute_graphql.side_effect = RuntimeError(
            "Item already exists in project"
        )

        result = await adapter.project_add_issue(
            project_id="PVT_TEST",
            issue_id="I_TEST",
        )

        # Should return True even for duplicates
        assert result is True

    @pytest.mark.asyncio
    async def test_add_issue_invalid_project_id(self, adapter):
        """Test validation of project_id format."""
        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_add_issue(
                project_id="INVALID_ID",  # Missing PVT_ prefix
                issue_id="I_TEST",
            )

    @pytest.mark.asyncio
    async def test_add_issue_empty_project_id(self, adapter):
        """Test validation of empty project_id."""
        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_add_issue(
                project_id="",
                issue_id="I_TEST",
            )

    @pytest.mark.asyncio
    async def test_add_issue_invalid_issue_id_format(self, adapter):
        """Test validation of issue_id format."""
        with pytest.raises(ValueError, match="Invalid issue_id"):
            await adapter.project_add_issue(
                project_id="PVT_TEST",
                issue_id="INVALID_ID",  # Not I_ or PR_ or owner/repo#number
            )

    @pytest.mark.asyncio
    async def test_add_issue_empty_issue_id(self, adapter):
        """Test validation of empty issue_id."""
        with pytest.raises(ValueError, match="issue_id is required"):
            await adapter.project_add_issue(
                project_id="PVT_TEST",
                issue_id="",
            )

    @pytest.mark.asyncio
    async def test_add_issue_number_format_invalid(self, adapter):
        """Test invalid owner/repo#number format."""
        with pytest.raises(ValueError, match="Invalid issue_id"):
            await adapter.project_add_issue(
                project_id="PVT_TEST",
                issue_id="invalid#format",  # Missing /
            )

    @pytest.mark.asyncio
    async def test_add_issue_number_not_found(self, adapter):
        """Test handling of issue not found during resolution."""
        # Mock issue not found
        adapter._graphql_request.return_value = {"repository": {"issue": None}}

        with pytest.raises(ValueError, match="Issue #123 not found"):
            await adapter.project_add_issue(
                project_id="PVT_TEST",
                issue_id="test-org/test-repo#123",
            )

    @pytest.mark.asyncio
    async def test_add_issue_mutation_failure(self, adapter):
        """Test handling of mutation failure."""
        # Mock mutation error
        adapter.gh_client.execute_graphql.side_effect = RuntimeError(
            "Permission denied"
        )

        with pytest.raises(RuntimeError, match="Failed to add issue to project"):
            await adapter.project_add_issue(
                project_id="PVT_TEST",
                issue_id="I_TEST",
            )

    @pytest.mark.asyncio
    async def test_add_issue_no_item_returned(self, adapter):
        """Test handling of mutation succeeding but no item returned."""
        # Mock mutation with no item
        adapter.gh_client.execute_graphql.return_value = {
            "addProjectV2ItemById": {"item": None}
        }

        result = await adapter.project_add_issue(
            project_id="PVT_TEST",
            issue_id="I_TEST",
        )

        assert result is False


# =============================================================================
# project_remove_issue() Tests
# =============================================================================


class TestProjectRemoveIssue:
    """Tests for project_remove_issue() method."""

    @pytest.mark.asyncio
    async def test_remove_issue_success(self, adapter):
        """Test successful issue removal."""
        adapter.gh_client.execute_graphql.return_value = {
            "deleteProjectV2Item": {"deletedItemId": "PVTI_TEST"}
        }

        result = await adapter.project_remove_issue(
            project_id="PVT_TEST",
            item_id="PVTI_TEST",
        )

        assert result is True
        adapter.gh_client.execute_graphql.assert_called_once()

        # Verify mutation variables
        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args.kwargs["variables"]["projectId"] == "PVT_TEST"
        assert call_args.kwargs["variables"]["itemId"] == "PVTI_TEST"

    @pytest.mark.asyncio
    async def test_remove_issue_invalid_project_id(self, adapter):
        """Test validation of project_id format."""
        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_remove_issue(
                project_id="INVALID_ID",
                item_id="PVTI_TEST",
            )

    @pytest.mark.asyncio
    async def test_remove_issue_invalid_item_id(self, adapter):
        """Test validation of item_id format (must be PVTI_)."""
        with pytest.raises(ValueError, match="Invalid item_id"):
            await adapter.project_remove_issue(
                project_id="PVT_TEST",
                item_id="I_WRONG",  # Issue ID instead of item ID
            )

    @pytest.mark.asyncio
    async def test_remove_issue_empty_item_id(self, adapter):
        """Test validation of empty item_id."""
        with pytest.raises(ValueError, match="Invalid item_id"):
            await adapter.project_remove_issue(
                project_id="PVT_TEST",
                item_id="",
            )

    @pytest.mark.asyncio
    async def test_remove_issue_not_found(self, adapter):
        """Test handling of item not found (should return False)."""
        # Mock not found error
        adapter.gh_client.execute_graphql.side_effect = RuntimeError(
            "Item not found in project"
        )

        result = await adapter.project_remove_issue(
            project_id="PVT_TEST",
            item_id="PVTI_NOTFOUND",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_issue_mutation_failure(self, adapter):
        """Test handling of mutation failure (not "not found" error)."""
        # Mock permission error
        adapter.gh_client.execute_graphql.side_effect = RuntimeError(
            "Permission denied"
        )

        with pytest.raises(RuntimeError, match="Failed to remove issue from project"):
            await adapter.project_remove_issue(
                project_id="PVT_TEST",
                item_id="PVTI_TEST",
            )

    @pytest.mark.asyncio
    async def test_remove_issue_no_deleted_id(self, adapter):
        """Test handling of mutation succeeding but no deleted ID returned."""
        adapter.gh_client.execute_graphql.return_value = {
            "deleteProjectV2Item": {"deletedItemId": None}
        }

        result = await adapter.project_remove_issue(
            project_id="PVT_TEST",
            item_id="PVTI_TEST",
        )

        assert result is False


# =============================================================================
# project_get_issues() Tests
# =============================================================================


class TestProjectGetIssues:
    """Tests for project_get_issues() method."""

    @pytest.mark.asyncio
    async def test_get_issues_success(self, adapter):
        """Test getting issues from project."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "totalCount": 2,
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": None,
                    },
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "id": "I_TEST1",
                                "number": 1,
                                "title": "Test Issue 1",
                                "state": "OPEN",
                                "labels": {
                                    "nodes": [
                                        {"name": "bug"},
                                        {"name": "P1"},
                                    ]
                                },
                            },
                        },
                        {
                            "id": "PVTI_TEST2",
                            "content": {
                                "__typename": "Issue",
                                "id": "I_TEST2",
                                "number": 2,
                                "title": "Test Issue 2",
                                "state": "CLOSED",
                                "labels": {"nodes": []},
                            },
                        },
                    ],
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
            limit=10,
        )

        assert len(issues) == 2

        # Verify first issue
        assert issues[0].title == "Test Issue 1"
        assert issues[0].id == "1"
        assert "project_item_id" in issues[0].metadata.get("github", {})
        assert issues[0].metadata["github"]["project_item_id"] == "PVTI_TEST1"
        assert issues[0].metadata["github"]["project_id"] == "PVT_TEST"

        # Verify second issue
        assert issues[1].title == "Test Issue 2"
        assert issues[1].id == "2"

    @pytest.mark.asyncio
    async def test_get_issues_filter_state_open(self, adapter):
        """Test filtering issues by state (OPEN)."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "number": 1,
                                "title": "Open Issue",
                                "state": "OPEN",
                                "labels": {"nodes": []},
                            },
                        },
                        {
                            "id": "PVTI_TEST2",
                            "content": {
                                "__typename": "Issue",
                                "number": 2,
                                "title": "Closed Issue",
                                "state": "CLOSED",
                                "labels": {"nodes": []},
                            },
                        },
                    ]
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
            state="OPEN",
        )

        # Only open issue should be returned
        assert len(issues) == 1
        assert issues[0].title == "Open Issue"

    @pytest.mark.asyncio
    async def test_get_issues_filter_state_closed(self, adapter):
        """Test filtering issues by state (CLOSED)."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "number": 1,
                                "title": "Open Issue",
                                "state": "OPEN",
                                "labels": {"nodes": []},
                            },
                        },
                        {
                            "id": "PVTI_TEST2",
                            "content": {
                                "__typename": "Issue",
                                "number": 2,
                                "title": "Closed Issue",
                                "state": "CLOSED",
                                "labels": {"nodes": []},
                            },
                        },
                    ]
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
            state="CLOSED",
        )

        # Only closed issue should be returned
        assert len(issues) == 1
        assert issues[0].title == "Closed Issue"

    @pytest.mark.asyncio
    async def test_get_issues_skip_pull_requests(self, adapter):
        """Test that pull requests are skipped."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "number": 1,
                                "title": "Issue",
                                "state": "OPEN",
                                "labels": {"nodes": []},
                            },
                        },
                        {
                            "id": "PVTI_TEST2",
                            "content": {
                                "__typename": "PullRequest",
                                "number": 2,
                                "title": "PR",
                                "state": "OPEN",
                            },
                        },
                        {
                            "id": "PVTI_TEST3",
                            "content": {
                                "__typename": "DraftIssue",
                                "title": "Draft",
                            },
                        },
                    ]
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
        )

        # Only issue should be returned (not PR or draft)
        assert len(issues) == 1
        assert issues[0].title == "Issue"

    @pytest.mark.asyncio
    async def test_get_issues_skip_archived_items(self, adapter):
        """Test that archived items (no content) are skipped."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "number": 1,
                                "title": "Active Issue",
                                "state": "OPEN",
                                "labels": {"nodes": []},
                            },
                        },
                        {
                            "id": "PVTI_TEST2",
                            "content": None,  # Archived item
                        },
                    ]
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
        )

        # Only active issue should be returned
        assert len(issues) == 1
        assert issues[0].title == "Active Issue"

    @pytest.mark.asyncio
    async def test_get_issues_empty_project(self, adapter):
        """Test handling of empty project."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "totalCount": 0,
                    "nodes": [],
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
        )

        assert len(issues) == 0
        assert isinstance(issues, list)

    @pytest.mark.asyncio
    async def test_get_issues_project_not_found(self, adapter):
        """Test handling of project not found."""
        adapter.gh_client.execute_graphql.return_value = {"node": None}

        issues = await adapter.project_get_issues(
            project_id="PVT_NOTFOUND",
        )

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_get_issues_invalid_project_id(self, adapter):
        """Test validation of project_id format."""
        with pytest.raises(ValueError, match="Invalid project_id"):
            await adapter.project_get_issues(
                project_id="INVALID_ID",
            )

    @pytest.mark.asyncio
    async def test_get_issues_with_pagination(self, adapter):
        """Test pagination support."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "items": {
                    "totalCount": 1,
                    "pageInfo": {
                        "hasNextPage": True,
                        "endCursor": "cursor123",
                    },
                    "nodes": [
                        {
                            "id": "PVTI_TEST1",
                            "content": {
                                "__typename": "Issue",
                                "number": 1,
                                "title": "Issue",
                                "state": "OPEN",
                                "labels": {"nodes": []},
                            },
                        },
                    ],
                }
            }
        }

        issues = await adapter.project_get_issues(
            project_id="PVT_TEST",
            cursor="prev_cursor",
        )

        assert len(issues) == 1

        # Verify cursor was passed
        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args.kwargs["variables"]["after"] == "prev_cursor"

    @pytest.mark.asyncio
    async def test_get_issues_query_failure(self, adapter):
        """Test handling of query failure."""
        adapter.gh_client.execute_graphql.side_effect = RuntimeError("GraphQL error")

        with pytest.raises(RuntimeError, match="Failed to get project issues"):
            await adapter.project_get_issues(
                project_id="PVT_TEST",
            )
