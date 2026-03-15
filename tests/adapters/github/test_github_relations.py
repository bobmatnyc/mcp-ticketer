"""Unit tests for GitHub adapter sub-issue relationship methods."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter
from mcp_ticketer.core.models import RelationType, Task, TicketRelation


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_adapter() -> GitHubAdapter:
    """Create a GitHubAdapter with a minimal config and mocked HTTP client."""
    config = {
        "token": "ghp_testtoken1234567890",
        "owner": "test-owner",
        "repo": "test-repo",
    }
    adapter = GitHubAdapter(config=config)
    # Replace the underlying httpx client so no real network calls happen
    adapter.client = MagicMock()
    return adapter


# ---------------------------------------------------------------------------
# Tests for _get_issue_node_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGetIssueNodeId:
    """Test _get_issue_node_id helper."""

    async def test_returns_node_id(self) -> None:
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {"id": "I_kwDOABCD1234", "number": 42}
                }
            }
        )

        node_id = await adapter._get_issue_node_id(42)

        assert node_id == "I_kwDOABCD1234"
        adapter._graphql_request.assert_called_once()
        call_vars = adapter._graphql_request.call_args[0][1]
        assert call_vars["number"] == 42
        assert call_vars["owner"] == "test-owner"
        assert call_vars["repo"] == "test-repo"

    async def test_raises_when_issue_not_found(self) -> None:
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={"repository": {"issue": None}}
        )

        with pytest.raises(ValueError, match="not found"):
            await adapter._get_issue_node_id(999)


# ---------------------------------------------------------------------------
# Tests for add_relation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGitHubAdapterAddRelation:
    """Test GitHubAdapter.add_relation for sub-issues."""

    async def test_add_relation_parent_type(self) -> None:
        """PARENT: source is child, target is parent."""
        adapter = _make_adapter()

        # _get_issue_node_id returns different IDs per call
        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "node-10", "number": 10, "title": "Parent"},
                    "subIssue": {"id": "node-20", "number": 20, "title": "Child"},
                }
            }
        )

        result = await adapter.add_relation("20", "10", RelationType.PARENT)

        assert isinstance(result, TicketRelation)
        assert result.source_ticket_id == "20"
        assert result.target_ticket_id == "10"
        assert result.relation_type == RelationType.PARENT

        # Verify mutation called with correct direction: parent=target, child=source
        gql_call = adapter._graphql_request.call_args
        variables = gql_call[0][1]
        assert variables["parentId"] == "node-10"
        assert variables["subIssueId"] == "node-20"

    async def test_add_relation_child_type(self) -> None:
        """CHILD: source is parent, target is child."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "node-10", "number": 10, "title": "Parent"},
                    "subIssue": {"id": "node-30", "number": 30, "title": "Child"},
                }
            }
        )

        result = await adapter.add_relation("10", "30", RelationType.CHILD)

        assert isinstance(result, TicketRelation)
        assert result.source_ticket_id == "10"
        assert result.target_ticket_id == "30"
        assert result.relation_type == RelationType.CHILD

        # Verify mutation called with correct direction: parent=source, child=target
        gql_call = adapter._graphql_request.call_args
        variables = gql_call[0][1]
        assert variables["parentId"] == "node-10"
        assert variables["subIssueId"] == "node-30"

    async def test_add_relation_metadata_populated(self) -> None:
        """Verify github metadata is populated in the returned relation."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "node-5", "number": 5, "title": "Parent Issue"},
                    "subIssue": {"id": "node-6", "number": 6, "title": "Child Issue"},
                }
            }
        )

        result = await adapter.add_relation("6", "5", RelationType.PARENT)

        assert "github" in result.metadata
        meta = result.metadata["github"]
        assert meta["parent_number"] == 5
        assert meta["parent_node_id"] == "node-5"
        assert meta["child_number"] == 6
        assert meta["child_node_id"] == "node-6"

    async def test_add_relation_unsupported_type_raises(self) -> None:
        """Non-PARENT/CHILD relation types must raise NotImplementedError."""
        adapter = _make_adapter()

        with pytest.raises(NotImplementedError, match="PARENT/CHILD"):
            await adapter.add_relation("1", "2", RelationType.BLOCKS)

    async def test_add_relation_non_numeric_id_raises(self) -> None:
        """Non-numeric issue IDs must raise ValueError."""
        adapter = _make_adapter()

        with pytest.raises(ValueError, match="numeric"):
            await adapter.add_relation("abc", "2", RelationType.CHILD)

    async def test_add_relation_graphql_error_propagates(self) -> None:
        """GraphQL errors raised by _graphql_request should propagate."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            side_effect=ValueError("GraphQL errors: [{'message': 'Not found'}]")
        )

        with pytest.raises(ValueError):
            await adapter.add_relation("1", "2", RelationType.CHILD)


# ---------------------------------------------------------------------------
# Tests for remove_relation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGitHubAdapterRemoveRelation:
    """Test GitHubAdapter.remove_relation for sub-issues."""

    async def test_remove_relation_parent_type_success(self) -> None:
        """PARENT removal succeeds — source is child, target is parent."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            return_value={
                "removeSubIssue": {
                    "issue": {"id": "node-10", "number": 10, "title": "Parent"},
                    "subIssue": {"id": "node-20", "number": 20, "title": "Child"},
                }
            }
        )

        result = await adapter.remove_relation("20", "10", RelationType.PARENT)

        assert result is True
        gql_call = adapter._graphql_request.call_args
        variables = gql_call[0][1]
        assert variables["parentId"] == "node-10"
        assert variables["subIssueId"] == "node-20"

    async def test_remove_relation_child_type_success(self) -> None:
        """CHILD removal succeeds — source is parent, target is child."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            return_value={
                "removeSubIssue": {
                    "issue": {"id": "node-10", "number": 10, "title": "Parent"},
                    "subIssue": {"id": "node-30", "number": 30, "title": "Child"},
                }
            }
        )

        result = await adapter.remove_relation("10", "30", RelationType.CHILD)

        assert result is True
        gql_call = adapter._graphql_request.call_args
        variables = gql_call[0][1]
        assert variables["parentId"] == "node-10"
        assert variables["subIssueId"] == "node-30"

    async def test_remove_relation_unsupported_type_raises(self) -> None:
        """Non-PARENT/CHILD relation types must raise NotImplementedError."""
        adapter = _make_adapter()

        with pytest.raises(NotImplementedError, match="PARENT/CHILD"):
            await adapter.remove_relation("1", "2", RelationType.RELATES_TO)

    async def test_remove_relation_non_numeric_id_raises(self) -> None:
        """Non-numeric IDs raise ValueError (consistent with add_relation)."""
        adapter = _make_adapter()

        with pytest.raises(ValueError, match="must be numeric"):
            await adapter.remove_relation("abc", "2", RelationType.CHILD)

    async def test_remove_relation_api_error_propagates(self) -> None:
        """Unexpected API errors propagate rather than being swallowed."""
        adapter = _make_adapter()

        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)
        adapter._graphql_request = AsyncMock(
            side_effect=ValueError("GraphQL error")
        )

        with pytest.raises(ValueError, match="GraphQL error"):
            await adapter.remove_relation("20", "10", RelationType.PARENT)


# ---------------------------------------------------------------------------
# Tests for list_relations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGitHubAdapterListRelations:
    """Test GitHubAdapter.list_relations for sub-issues."""

    async def test_list_relations_returns_parent_and_children(self) -> None:
        """list_relations returns both parent and children when no filter."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {
                        "id": "node-50",
                        "number": 50,
                        "title": "Middle Issue",
                        "parent": {
                            "id": "node-10",
                            "number": 10,
                            "title": "Parent Issue",
                        },
                        "subIssues": {
                            "nodes": [
                                {
                                    "id": "node-60",
                                    "number": 60,
                                    "title": "Child One",
                                    "state": "OPEN",
                                },
                                {
                                    "id": "node-70",
                                    "number": 70,
                                    "title": "Child Two",
                                    "state": "CLOSED",
                                },
                            ],
                            "totalCount": 2,
                        },
                    }
                }
            }
        )

        result = await adapter.list_relations("50")

        assert len(result) == 3

        parent_relations = [r for r in result if r.relation_type == RelationType.PARENT]
        child_relations = [r for r in result if r.relation_type == RelationType.CHILD]

        assert len(parent_relations) == 1
        assert len(child_relations) == 2

        parent_rel = parent_relations[0]
        assert parent_rel.source_ticket_id == "50"
        assert parent_rel.target_ticket_id == "10"
        assert parent_rel.metadata["github"]["parent_number"] == 10

        child_numbers = {r.target_ticket_id for r in child_relations}
        assert child_numbers == {"60", "70"}

    async def test_list_relations_filter_parent_only(self) -> None:
        """PARENT filter returns only the parent relation."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {
                        "id": "node-50",
                        "number": 50,
                        "title": "Issue",
                        "parent": {
                            "id": "node-10",
                            "number": 10,
                            "title": "Parent",
                        },
                        "subIssues": {
                            "nodes": [
                                {"id": "node-60", "number": 60, "title": "Child", "state": "OPEN"}
                            ],
                            "totalCount": 1,
                        },
                    }
                }
            }
        )

        result = await adapter.list_relations("50", RelationType.PARENT)

        assert len(result) == 1
        assert result[0].relation_type == RelationType.PARENT
        assert result[0].target_ticket_id == "10"

    async def test_list_relations_filter_child_only(self) -> None:
        """CHILD filter returns only children."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {
                        "id": "node-50",
                        "number": 50,
                        "title": "Issue",
                        "parent": {
                            "id": "node-10",
                            "number": 10,
                            "title": "Parent",
                        },
                        "subIssues": {
                            "nodes": [
                                {"id": "node-60", "number": 60, "title": "Child", "state": "OPEN"}
                            ],
                            "totalCount": 1,
                        },
                    }
                }
            }
        )

        result = await adapter.list_relations("50", RelationType.CHILD)

        assert len(result) == 1
        assert result[0].relation_type == RelationType.CHILD
        assert result[0].target_ticket_id == "60"

    async def test_list_relations_no_parent_no_children(self) -> None:
        """Issue with no parent and no children returns empty list."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {
                        "id": "node-50",
                        "number": 50,
                        "title": "Standalone Issue",
                        "parent": None,
                        "subIssues": {"nodes": [], "totalCount": 0},
                    }
                }
            }
        )

        result = await adapter.list_relations("50")

        assert result == []

    async def test_list_relations_issue_not_found_returns_empty(self) -> None:
        """Missing issue returns empty list."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={"repository": {"issue": None}}
        )

        result = await adapter.list_relations("999")

        assert result == []

    async def test_list_relations_api_error_propagates(self) -> None:
        """Unexpected API errors propagate rather than being swallowed."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            side_effect=ValueError("GraphQL error")
        )

        with pytest.raises(ValueError, match="GraphQL error"):
            await adapter.list_relations("50")

    async def test_list_relations_non_numeric_id_raises(self) -> None:
        """Non-numeric ticket ID raises ValueError (consistent with add_relation)."""
        adapter = _make_adapter()

        with pytest.raises(ValueError, match="must be numeric"):
            await adapter.list_relations("not-a-number")

    async def test_list_relations_unsupported_type_raises(self) -> None:
        """Unsupported relation_type filter raises NotImplementedError."""
        adapter = _make_adapter()

        with pytest.raises(NotImplementedError, match="PARENT/CHILD"):
            await adapter.list_relations("50", RelationType.BLOCKS)

    async def test_list_relations_child_metadata_populated(self) -> None:
        """Child relation metadata contains child details."""
        adapter = _make_adapter()
        adapter._graphql_request = AsyncMock(
            return_value={
                "repository": {
                    "issue": {
                        "id": "node-1",
                        "number": 1,
                        "title": "Parent",
                        "parent": None,
                        "subIssues": {
                            "nodes": [
                                {
                                    "id": "node-2",
                                    "number": 2,
                                    "title": "Child Issue",
                                    "state": "OPEN",
                                }
                            ],
                            "totalCount": 1,
                        },
                    }
                }
            }
        )

        result = await adapter.list_relations("1", RelationType.CHILD)

        assert len(result) == 1
        meta = result[0].metadata["github"]
        assert meta["child_number"] == 2
        assert meta["child_node_id"] == "node-2"
        assert meta["child_title"] == "Child Issue"
        assert meta["child_state"] == "OPEN"


# ---------------------------------------------------------------------------
# Tests for create() with parent_issue wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestGitHubAdapterCreateWithParentIssue:
    """Test create() wires parent_issue via addSubIssue mutation."""

    async def test_create_with_parent_issue_calls_add_sub_issue(self) -> None:
        """When parent_issue is set, addSubIssue mutation must be called."""
        adapter = _make_adapter()

        # Stub validate_credentials
        adapter.validate_credentials = MagicMock(return_value=(True, ""))

        # Stub label-related helpers so create() doesn't fail on label setup
        adapter._get_state_label = MagicMock(return_value=None)
        adapter._get_priority_label = MagicMock(return_value="priority:medium")
        adapter._ensure_label_exists = AsyncMock(return_value=True)

        # Stub the REST POST that creates the issue
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "number": 42,
                "node_id": "I_kwDO_child_42",
                "id": 12345,
                "title": "New Sub-issue",
                "body": "",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "labels": [],
                "assignees": [],
                "milestone": None,
                "html_url": "https://github.com/test-owner/test-repo/issues/42",
                "user": {"login": "testuser"},
            }
        )
        adapter.client.post = AsyncMock(return_value=mock_response)

        # Stub _get_issue_node_id for parent resolution
        async def fake_node_id(num: int) -> str:
            return f"node-{num}"

        adapter._get_issue_node_id = AsyncMock(side_effect=fake_node_id)

        # Stub _graphql_request to capture the addSubIssue call
        adapter._graphql_request = AsyncMock(
            return_value={
                "addSubIssue": {
                    "issue": {"id": "node-10", "number": 10, "title": "Parent"},
                    "subIssue": {"id": "I_kwDO_child_42", "number": 42, "title": "Child"},
                }
            }
        )

        ticket = Task(title="New Sub-issue", parent_issue="10")
        result = await adapter.create(ticket)

        # create() should succeed and call _graphql_request with addSubIssue
        assert result is not None
        adapter._graphql_request.assert_called_once()
        call_vars = adapter._graphql_request.call_args[0][1]
        # Parent node ID comes from _get_issue_node_id(10)
        assert call_vars["parentId"] == "node-10"
        # Child node_id comes from created_issue["node_id"]
        assert call_vars["subIssueId"] == "I_kwDO_child_42"

    async def test_create_without_parent_issue_skips_graphql(self) -> None:
        """When parent_issue is None, no addSubIssue call is made."""
        adapter = _make_adapter()

        adapter.validate_credentials = MagicMock(return_value=(True, ""))
        adapter._get_state_label = MagicMock(return_value=None)
        adapter._get_priority_label = MagicMock(return_value="priority:medium")
        adapter._ensure_label_exists = AsyncMock(return_value=True)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "number": 43,
                "node_id": "I_kwDO_standalone_43",
                "id": 99999,
                "title": "Standalone Issue",
                "body": "",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "labels": [],
                "assignees": [],
                "milestone": None,
                "html_url": "https://github.com/test-owner/test-repo/issues/43",
                "user": {"login": "testuser"},
            }
        )
        adapter.client.post = AsyncMock(return_value=mock_response)
        adapter._graphql_request = AsyncMock()

        ticket = Task(title="Standalone Issue")
        result = await adapter.create(ticket)

        assert result is not None
        # No GraphQL call should be made when parent_issue is absent
        adapter._graphql_request.assert_not_called()

    async def test_create_parent_issue_failure_does_not_block_creation(self) -> None:
        """If addSubIssue fails, create() still returns the created issue."""
        adapter = _make_adapter()

        adapter.validate_credentials = MagicMock(return_value=(True, ""))
        adapter._get_state_label = MagicMock(return_value=None)
        adapter._get_priority_label = MagicMock(return_value="priority:medium")
        adapter._ensure_label_exists = AsyncMock(return_value=True)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = MagicMock(
            return_value={
                "number": 44,
                "node_id": "I_kwDO_44",
                "id": 44444,
                "title": "Child With Bad Parent",
                "body": "",
                "state": "open",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "labels": [],
                "assignees": [],
                "milestone": None,
                "html_url": "https://github.com/test-owner/test-repo/issues/44",
                "user": {"login": "testuser"},
            }
        )
        adapter.client.post = AsyncMock(return_value=mock_response)

        # Make _get_issue_node_id fail for the parent
        adapter._get_issue_node_id = AsyncMock(
            side_effect=ValueError("Parent issue not found")
        )
        adapter._graphql_request = AsyncMock()

        ticket = Task(title="Child With Bad Parent", parent_issue="9999")
        # Should NOT raise — failure is logged as warning
        result = await adapter.create(ticket)

        assert result is not None
        assert result.title == "Child With Bad Parent"


# ---------------------------------------------------------------------------
# Tests for RelationType PARENT/CHILD values and inverse
# ---------------------------------------------------------------------------


class TestRelationTypeParentChild:
    """Test the PARENT/CHILD enum values and inverse mappings."""

    def test_parent_value(self) -> None:
        assert RelationType.PARENT.value == "parent"

    def test_child_value(self) -> None:
        assert RelationType.CHILD.value == "child"

    def test_parent_inverse_is_child(self) -> None:
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.PARENT,
        )
        assert relation.get_inverse_type() == RelationType.CHILD

    def test_child_inverse_is_parent(self) -> None:
        relation = TicketRelation(
            source_ticket_id="A",
            target_ticket_id="B",
            relation_type=RelationType.CHILD,
        )
        assert relation.get_inverse_type() == RelationType.PARENT

    def test_create_inverse_parent(self) -> None:
        relation = TicketRelation(
            source_ticket_id="10",
            target_ticket_id="20",
            relation_type=RelationType.PARENT,
        )
        inverse = relation.create_inverse()
        assert inverse.source_ticket_id == "20"
        assert inverse.target_ticket_id == "10"
        assert inverse.relation_type == RelationType.CHILD

    def test_create_inverse_child(self) -> None:
        relation = TicketRelation(
            source_ticket_id="10",
            target_ticket_id="20",
            relation_type=RelationType.CHILD,
        )
        inverse = relation.create_inverse()
        assert inverse.source_ticket_id == "20"
        assert inverse.target_ticket_id == "10"
        assert inverse.relation_type == RelationType.PARENT
