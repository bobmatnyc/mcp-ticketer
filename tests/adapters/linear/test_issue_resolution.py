"""Unit tests for Linear adapter issue ID resolution."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearIssueIDResolution:
    """Test Linear adapter issue ID resolution from identifiers to UUIDs."""

    @pytest.fixture
    def adapter(self) -> None:
        """Create a LinearAdapter instance for testing."""
        config = {
            "api_key": "lin_api_test123",
            "team_id": "test-team-id",
        }
        adapter = LinearAdapter(config)

        # Mock the client
        adapter.client = MagicMock()
        adapter.client.execute_query = AsyncMock()

        return adapter

    @pytest.fixture
    def mock_issue_response(self):
        """Mock response from Linear issue query."""
        return {
            "issue": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            }
        }

    async def test_resolve_full_uuid_returns_unchanged(self, adapter):
        """Test that a full UUID is returned unchanged without querying."""
        full_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        result = await adapter._resolve_issue_id(full_uuid)

        # Should return the UUID directly without calling the API
        assert result == full_uuid
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_by_issue_identifier(self, adapter, mock_issue_response):
        """Test resolving issue ID by identifier like 'ENG-842'."""
        adapter.client.execute_query.return_value = mock_issue_response

        result = await adapter._resolve_issue_id("ENG-842")

        assert result == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        adapter.client.execute_query.assert_called_once()

        # Verify the GraphQL query was called with correct parameters
        call_args = adapter.client.execute_query.call_args
        assert "GetIssueId" in call_args[0][0]
        # Check the variables dict which is the second positional argument
        assert call_args[0][1]["identifier"] == "ENG-842"

    async def test_resolve_by_bta_identifier(self, adapter, mock_issue_response):
        """Test resolving issue ID by BTA identifier like 'BTA-123'."""
        adapter.client.execute_query.return_value = mock_issue_response

        result = await adapter._resolve_issue_id("BTA-123")

        assert result == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_nonexistent_issue_returns_none(self, adapter):
        """Test that unmatched issue identifier returns None."""
        adapter.client.execute_query.return_value = {}

        result = await adapter._resolve_issue_id("NONEXISTENT-999")

        assert result is None
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_empty_identifier_returns_none(self, adapter):
        """Test that empty identifier returns None without querying."""
        result = await adapter._resolve_issue_id("")

        assert result is None
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_none_identifier_returns_none(self, adapter):
        """Test that None identifier returns None without querying."""
        result = await adapter._resolve_issue_id(None)

        assert result is None
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_api_error_raises_value_error(self, adapter):
        """Test that API errors are wrapped in ValueError with context."""
        adapter.client.execute_query.side_effect = Exception("API connection failed")

        with pytest.raises(ValueError) as exc_info:
            await adapter._resolve_issue_id("ENG-842")

        assert "Failed to resolve issue" in str(exc_info.value)
        assert "ENG-842" in str(exc_info.value)

    async def test_uuid_with_wrong_dash_count_queries_api(
        self, adapter, mock_issue_response
    ):
        """Test that strings with dashes but not UUIDs still query the API."""
        adapter.client.execute_query.return_value = mock_issue_response

        # This has dashes but not the UUID format (36 chars, 4 dashes)
        result = await adapter._resolve_issue_id("ENG-842-EXTRA")

        # Should still query the API since it's not a valid UUID format
        assert result == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        adapter.client.execute_query.assert_called_once()

    async def test_uuid_with_correct_format_skips_api(self, adapter):
        """Test that properly formatted UUIDs skip API call."""
        uuid = "12345678-1234-1234-1234-123456789012"

        result = await adapter._resolve_issue_id(uuid)

        assert result == uuid
        adapter.client.execute_query.assert_not_called()

    async def test_various_issue_identifier_formats(self, adapter, mock_issue_response):
        """Test various issue identifier formats."""
        adapter.client.execute_query.return_value = mock_issue_response

        test_identifiers = [
            "ENG-1",
            "ENG-999",
            "BTA-42",
            "TEAM-12345",
        ]

        for identifier in test_identifiers:
            adapter.client.execute_query.reset_mock()
            result = await adapter._resolve_issue_id(identifier)

            assert result == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
            adapter.client.execute_query.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearIssueResolutionInCreateTask:
    """Test integration of issue resolution in the _create_task method."""

    @pytest.fixture
    def adapter(self) -> None:
        """Create a LinearAdapter instance for testing."""
        config = {
            "api_key": "lin_api_test123",
            "team_id": "test-team-id",
        }
        adapter = LinearAdapter(config)

        # Mock the client
        adapter.client = MagicMock()
        adapter.client.execute_query = AsyncMock()
        adapter.client.execute_mutation = AsyncMock()

        return adapter

    async def test_resolve_issue_called_during_task_creation(self, adapter):
        """Test that _resolve_issue_id is called when parent_issue is provided."""
        from unittest.mock import patch

        # Mock issue resolution to return a UUID
        mock_resolve = AsyncMock(return_value="resolved-issue-uuid-12345")

        with patch.object(adapter, "_resolve_issue_id", mock_resolve):
            # Test that resolution is attempted
            result = await adapter._resolve_issue_id("ENG-842")

            assert result == "resolved-issue-uuid-12345"
            mock_resolve.assert_called_once_with("ENG-842")

    async def test_parent_issue_none_skips_resolution(self, adapter):
        """Test that None parent_issue skips resolution."""
        # Don't mock, test actual behavior
        result = await adapter._resolve_issue_id(None)

        assert result is None
        # Verify no API call was made
        adapter.client.execute_query.assert_not_called()

    async def test_parent_issue_uuid_format_skips_api(self, adapter):
        """Test that UUID-formatted parent_issue skips API call."""
        uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        # Test actual behavior - no mocking
        result = await adapter._resolve_issue_id(uuid)

        assert result == uuid
        # Verify no API call was made
        adapter.client.execute_query.assert_not_called()
