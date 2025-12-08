"""Unit tests for Linear adapter label creation functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.exceptions import AdapterError


@pytest.mark.unit
class TestLabelCreation:
    """Test label creation and resolution in Linear adapter."""

    @pytest.fixture
    def adapter(self):
        """Create a Linear adapter instance for testing."""
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": "02d15669-7351-4451-9719-807576c16049",
        }
        return LinearAdapter(config)

    @pytest.mark.asyncio
    async def test_create_label_success(self, adapter):
        """Test successful label creation."""
        team_id = "test-team-id"
        label_name = "MCP Ticketer"
        expected_label_id = "label-id-123"

        # Mock the mutation execution
        mock_result = {
            "issueLabelCreate": {
                "success": True,
                "issueLabel": {
                    "id": expected_label_id,
                    "name": label_name,
                    "color": "#0366d6",
                    "description": None,
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_result)
        adapter._labels_cache = []

        # Execute
        result = await adapter._create_label(label_name, team_id)

        # Verify
        assert result == expected_label_id
        assert len(adapter._labels_cache) == 1
        assert adapter._labels_cache[0]["id"] == expected_label_id
        assert adapter._labels_cache[0]["name"] == label_name

    @pytest.mark.asyncio
    async def test_create_label_failure(self, adapter):
        """Test label creation failure handling."""
        team_id = "test-team-id"
        label_name = "Test Label"

        # Mock failed mutation
        mock_result = {"issueLabelCreate": {"success": False}}
        adapter.client.execute_mutation = AsyncMock(return_value=mock_result)

        # Execute and verify exception
        with pytest.raises(ValueError) as exc_info:
            await adapter._create_label(label_name, team_id)

        assert "Failed to create label" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_label_with_custom_color(self, adapter):
        """Test label creation with custom color."""
        team_id = "test-team-id"
        label_name = "Bug"
        custom_color = "#ff0000"
        expected_label_id = "label-red-123"

        # Mock the mutation execution
        mock_result = {
            "issueLabelCreate": {
                "success": True,
                "issueLabel": {
                    "id": expected_label_id,
                    "name": label_name,
                    "color": custom_color,
                    "description": None,
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_result)
        adapter._labels_cache = []

        # Execute
        result = await adapter._create_label(label_name, team_id, color=custom_color)

        # Verify
        assert result == expected_label_id
        adapter.client.execute_mutation.assert_called_once()
        # Check that the color parameter was passed correctly to _create_label
        # The execute_mutation is called with (CREATE_LABEL_MUTATION, {"input": {...}})
        call_args = adapter.client.execute_mutation.call_args[0]  # positional args
        mutation_vars = (
            call_args[1]
            if len(call_args) > 1
            else adapter.client.execute_mutation.call_args[1]
        )
        assert mutation_vars["input"]["color"] == custom_color

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_all_new(self, adapter):
        """Test ensuring labels exist when all labels are new."""
        label_names = ["MCP Ticketer", "Bug", "Enhancement"]
        team_id = "test-team-id"

        # Mock no existing labels
        adapter._labels_cache = []
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock Tier 2: Server check returns None (labels don't exist)
        adapter._find_label_by_name = AsyncMock(return_value=None)

        # Mock label creation
        created_ids = ["label-1", "label-2", "label-3"]

        async def mock_create_label(name, tid, color="#0366d6"):
            idx = label_names.index(name)
            return created_ids[idx]

        adapter._create_label = AsyncMock(side_effect=mock_create_label)

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify
        assert result == created_ids
        assert adapter._create_label.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_all_existing(self, adapter):
        """Test ensuring labels exist when all labels already exist."""
        label_names = ["MCP Ticketer", "Bug"]
        team_id = "test-team-id"
        existing_ids = ["existing-label-1", "existing-label-2"]

        # Mock existing labels
        adapter._labels_cache = [
            {"id": existing_ids[0], "name": "MCP Ticketer", "color": "#0366d6"},
            {"id": existing_ids[1], "name": "Bug", "color": "#ff0000"},
        ]
        adapter._ensure_team_id = AsyncMock(return_value=team_id)
        adapter._create_label = AsyncMock()

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify
        assert result == existing_ids
        adapter._create_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_mixed(self, adapter):
        """Test ensuring labels exist with mix of existing and new labels."""
        label_names = ["MCP Ticketer", "Bug", "Enhancement"]
        team_id = "test-team-id"

        # Mock one existing label, two new
        adapter._labels_cache = [
            {"id": "existing-label-1", "name": "MCP Ticketer", "color": "#0366d6"},
        ]
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock Tier 2: Server check returns None for new labels
        adapter._find_label_by_name = AsyncMock(return_value=None)

        # Mock creating new labels
        new_ids = {"Bug": "new-label-1", "Enhancement": "new-label-2"}

        async def mock_create_label(name, tid, color="#0366d6"):
            return new_ids[name]

        adapter._create_label = AsyncMock(side_effect=mock_create_label)

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify
        assert len(result) == 3
        assert result[0] == "existing-label-1"  # Existing
        assert result[1] == "new-label-1"  # New (Bug)
        assert result[2] == "new-label-2"  # New (Enhancement)
        assert adapter._create_label.call_count == 2

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_case_insensitive(self, adapter):
        """Test case-insensitive label matching."""
        label_names = ["mcp ticketer", "BUG", "Enhancement"]
        team_id = "test-team-id"

        # Mock existing labels with different casing
        adapter._labels_cache = [
            {"id": "existing-label-1", "name": "MCP Ticketer", "color": "#0366d6"},
            {"id": "existing-label-2", "name": "bug", "color": "#ff0000"},
            {"id": "existing-label-3", "name": "ENHANCEMENT", "color": "#00ff00"},
        ]
        adapter._ensure_team_id = AsyncMock(return_value=team_id)
        adapter._create_label = AsyncMock()

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify - all should match existing labels despite case differences
        assert len(result) == 3
        assert result == ["existing-label-1", "existing-label-2", "existing-label-3"]
        adapter._create_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_partial_failure(self, adapter):
        """Test that label creation failure propagates (fail-fast behavior, 1M-396)."""
        label_names = ["Success Label", "Failure Label", "Another Success"]
        team_id = "test-team-id"

        adapter._labels_cache = []
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock Tier 2: Server check returns None (labels don't exist)
        adapter._find_label_by_name = AsyncMock(return_value=None)

        # Mock creation where middle label fails
        async def mock_create_label(name, tid, color="#0366d6"):
            if name == "Failure Label":
                raise ValueError("Simulated creation failure")
            return f"label-{name.replace(' ', '-').lower()}"

        adapter._create_label = AsyncMock(side_effect=mock_create_label)

        # Execute - should raise exception on first failure (fail-fast)
        with pytest.raises(ValueError) as exc_info:
            await adapter._ensure_labels_exist(label_names)

        # Verify exception message
        assert "Simulated creation failure" in str(exc_info.value)
        # First label succeeds, second fails and raises
        assert adapter._create_label.call_count == 2

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_empty_list(self, adapter):
        """Test handling of empty label list."""
        result = await adapter._ensure_labels_exist([])
        assert result == []

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_cache_not_loaded(self, adapter):
        """Test that labels are loaded if cache is None."""
        label_names = ["Test Label"]
        team_id = "test-team-id"

        # Cache not loaded yet
        adapter._labels_cache = None
        adapter._ensure_team_id = AsyncMock(return_value=team_id)
        adapter._load_team_labels = AsyncMock(
            side_effect=lambda tid: setattr(adapter, "_labels_cache", [])
        )
        # Mock Tier 2: Server check returns None (label doesn't exist)
        adapter._find_label_by_name = AsyncMock(return_value=None)
        adapter._create_label = AsyncMock(return_value="new-label-id")

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify cache was loaded
        adapter._load_team_labels.assert_called_once_with(team_id)
        assert result == ["new-label-id"]

    @pytest.mark.asyncio
    async def test_resolve_label_ids_delegates_to_ensure_labels_exist(self, adapter):
        """Test that _resolve_label_ids properly delegates to _ensure_labels_exist."""
        label_names = ["Test Label"]
        expected_ids = ["label-id-123"]

        adapter._ensure_labels_exist = AsyncMock(return_value=expected_ids)

        # Execute
        result = await adapter._resolve_label_ids(label_names)

        # Verify
        assert result == expected_ids
        adapter._ensure_labels_exist.assert_called_once_with(label_names)

    @pytest.mark.asyncio
    async def test_find_label_by_name_success(self, adapter):
        """Test finding a label by name via server-side search (1M-443)."""
        team_id = "test-team-id"
        label_name = "Existing Label"
        expected_label = {
            "id": "server-label-id-123",
            "name": "Existing Label",
            "color": "#0366d6",
            "description": "Test label",
        }

        # Mock server response
        mock_result = {
            "team": {
                "labels": {
                    "nodes": [
                        expected_label,
                        {"id": "other-id", "name": "Other Label", "color": "#ff0000"},
                    ]
                }
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=mock_result)

        # Execute
        result = await adapter._find_label_by_name(label_name, team_id)

        # Verify
        assert result == expected_label
        adapter.client.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_label_by_name_case_insensitive(self, adapter):
        """Test case-insensitive label search (1M-443)."""
        team_id = "test-team-id"
        expected_label = {
            "id": "label-id-456",
            "name": "MCP Ticketer",
            "color": "#0366d6",
            "description": None,
        }

        mock_result = {"team": {"labels": {"nodes": [expected_label]}}}
        adapter.client.execute_query = AsyncMock(return_value=mock_result)

        # Execute with different casing
        result = await adapter._find_label_by_name("mcp ticketer", team_id)

        # Verify - should find despite case difference
        assert result == expected_label

    @pytest.mark.asyncio
    async def test_find_label_by_name_not_found(self, adapter):
        """Test label not found in server-side search (1M-443)."""
        team_id = "test-team-id"
        label_name = "Nonexistent Label"

        mock_result = {
            "team": {
                "labels": {
                    "nodes": [
                        {"id": "id-1", "name": "Label 1", "color": "#ff0000"},
                        {"id": "id-2", "name": "Label 2", "color": "#00ff00"},
                    ]
                }
            }
        }

        adapter.client.execute_query = AsyncMock(return_value=mock_result)

        # Execute
        result = await adapter._find_label_by_name(label_name, team_id)

        # Verify
        assert result is None

    @pytest.mark.asyncio
    async def test_find_label_by_name_api_failure(self, adapter):
        """Test that API failures propagate after retries (1M-443 hotfix)."""
        team_id = "test-team-id"
        label_name = "Test Label"

        # Mock API failure
        adapter.client.execute_query = AsyncMock(
            side_effect=Exception("API connection error")
        )

        # Execute - should raise after 3 retries
        with pytest.raises(Exception, match="API connection error"):
            await adapter._find_label_by_name(label_name, team_id)

    @pytest.mark.asyncio
    async def test_find_label_by_name_retry_success(self, adapter):
        """Test retry logic succeeds on second attempt (1M-443 hotfix)."""
        team_id = "test-team-id"
        label_name = "Test Label"
        expected_label = {
            "id": "label-id-123",
            "name": "Test Label",
            "color": "#0366d6",
            "description": "Found on retry",
        }

        # Mock: Fail once, then succeed
        call_count = 0

        async def mock_query(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient network error")
            return {"team": {"labels": {"nodes": [expected_label]}}}

        adapter.client.execute_query = AsyncMock(side_effect=mock_query)

        # Execute - should succeed on retry
        result = await adapter._find_label_by_name(label_name, team_id)

        # Verify
        assert result == expected_label
        assert adapter.client.execute_query.call_count == 2

    @pytest.mark.asyncio
    async def test_find_label_by_name_retry_exhaustion(self, adapter):
        """Test retry exhaustion raises exception (1M-443 hotfix)."""
        team_id = "test-team-id"
        label_name = "Test Label"

        # Mock: Always fail
        adapter.client.execute_query = AsyncMock(
            side_effect=Exception("Persistent network failure")
        )

        # Execute - should raise after 3 retries
        with pytest.raises(Exception, match="Persistent network failure"):
            await adapter._find_label_by_name(label_name, team_id)

        # Verify retry count (3 attempts)
        assert adapter.client.execute_query.call_count == 3

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_server_check_failure_propagates(self, adapter):
        """Test that server check failures prevent label creation (1M-443 hotfix)."""
        label_names = ["Test Label"]
        team_id = "test-team-id"

        # Setup
        adapter._labels_cache = []  # Cache miss
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock server check failure (after retries)
        adapter._find_label_by_name = AsyncMock(
            side_effect=Exception("Network timeout after retries")
        )

        # Execute - should raise ValueError preventing duplicate creation
        with pytest.raises(ValueError, match="Unable to verify label.*existence"):
            await adapter._ensure_labels_exist(label_names)

        # Verify _create_label was NOT called (critical for duplicate prevention)
        # We need to mock it to verify it wasn't called
        adapter._create_label = AsyncMock()

        # Try again to verify create isn't called
        adapter._find_label_by_name = AsyncMock(
            side_effect=Exception("Network timeout after retries")
        )

        with pytest.raises(ValueError):
            await adapter._ensure_labels_exist(label_names)

        adapter._create_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_cache_staleness(self, adapter):
        """Test three-tier approach handles cache staleness (1M-443).

        Scenario: Label exists in Linear but not in local cache (stale cache).
        Expected: Tier 2 finds label on server, updates cache, no duplicate error.
        """
        label_names = ["Stale Label"]
        team_id = "test-team-id"
        server_label = {
            "id": "stale-label-id",
            "name": "Stale Label",
            "color": "#0366d6",
            "description": "Exists on server",
        }

        # Cache is empty (stale)
        adapter._labels_cache = []
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock Tier 2: Server has the label
        adapter._find_label_by_name = AsyncMock(return_value=server_label)

        # Mock should NOT be called (Tier 3 skipped)
        adapter._create_label = AsyncMock()

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify
        assert result == ["stale-label-id"]
        adapter._find_label_by_name.assert_called_once_with("Stale Label", team_id)
        adapter._create_label.assert_not_called()  # Should NOT create duplicate
        # Cache should be updated
        assert len(adapter._labels_cache) == 1
        assert adapter._labels_cache[0] == server_label

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_duplicate_prevention(self, adapter):
        """Test that existing labels are never recreated (1M-443).

        Scenario: Label exists on server but cache missed it.
        Expected: Tier 2 prevents duplicate creation.
        """
        label_names = ["Existing Label"]
        team_id = "test-team-id"

        adapter._labels_cache = []
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Tier 2 finds it on server
        adapter._find_label_by_name = AsyncMock(
            return_value={
                "id": "existing-id",
                "name": "Existing Label",
                "color": "#ff0000",
            }
        )

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify - should use existing label, not create new one
        assert result == ["existing-id"]
        adapter._find_label_by_name.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_labels_exist_three_tier_flow(self, adapter):
        """Test complete three-tier flow with mixed scenarios (1M-443).

        Scenario:
        - Label 1: In cache (Tier 1 hit)
        - Label 2: On server but not in cache (Tier 2 hit)
        - Label 3: Doesn't exist anywhere (Tier 3 create)
        """
        label_names = ["Cached Label", "Server Label", "New Label"]
        team_id = "test-team-id"

        # Cache has only first label
        adapter._labels_cache = [
            {"id": "cached-id", "name": "Cached Label", "color": "#0366d6"}
        ]
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Tier 2 finds second label, misses third
        async def mock_find_label(name, tid):
            if name == "Server Label":
                return {
                    "id": "server-id",
                    "name": "Server Label",
                    "color": "#ff0000",
                }
            return None

        adapter._find_label_by_name = AsyncMock(side_effect=mock_find_label)

        # Tier 3 creates third label
        adapter._create_label = AsyncMock(return_value="new-id")

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify
        assert result == ["cached-id", "server-id", "new-id"]
        # Tier 2 called twice (skipped for cached label)
        assert adapter._find_label_by_name.call_count == 2
        # Tier 3 called once (only for truly new label)
        adapter._create_label.assert_called_once_with("New Label", team_id)
        # Cache updated with server label
        assert len(adapter._labels_cache) == 2

    @pytest.mark.asyncio
    async def test_create_label_duplicate_recovery_success(self, adapter):
        """Test Priority 2: Successful recovery from duplicate label error (1M-398)."""
        team_id = "test-team-id"
        label_name = "Duplicate Label"
        existing_label_id = "existing-label-id-456"

        # Mock: Creation fails with duplicate error
        duplicate_error = AdapterError(
            "Label already exists: duplicate label name", "linear"
        )
        adapter.client.execute_mutation = AsyncMock(side_effect=duplicate_error)

        # Mock: Recovery lookup finds the existing label
        existing_label = {
            "id": existing_label_id,
            "name": label_name,
            "color": "#0366d6",
            "description": None,
        }
        adapter._find_label_by_name = AsyncMock(return_value=existing_label)
        adapter._labels_cache = []

        # Execute - should recover gracefully
        result = await adapter._create_label(label_name, team_id)

        # Verify
        assert result == existing_label_id
        adapter._find_label_by_name.assert_called_once_with(label_name, team_id)
        # Cache should be updated with recovered label
        assert len(adapter._labels_cache) == 1
        assert adapter._labels_cache[0] == existing_label

    @pytest.mark.asyncio
    async def test_create_label_duplicate_recovery_failure(self, adapter):
        """Test Priority 2: Recovery fails when label exists but can't be retrieved (1M-398)."""
        team_id = "test-team-id"
        label_name = "Inaccessible Label"

        # Mock: Creation fails with duplicate error
        duplicate_error = AdapterError(
            "Label already exists: duplicate label name", "linear"
        )
        adapter.client.execute_mutation = AsyncMock(side_effect=duplicate_error)

        # Mock: Recovery lookup returns None (permissions issue or API inconsistency)
        adapter._find_label_by_name = AsyncMock(return_value=None)
        adapter._labels_cache = []

        # Execute - should raise clear error message
        with pytest.raises(ValueError) as exc_info:
            await adapter._create_label(label_name, team_id)

        # Verify error message explains the situation
        assert "already exists but could not retrieve ID" in str(exc_info.value)
        assert "Permissions issue" in str(exc_info.value)
        # Should have tried 5 times with retry logic (initial + 4 retries)
        assert adapter._find_label_by_name.call_count == 5

    @pytest.mark.asyncio
    async def test_create_label_non_duplicate_error_propagates(self, adapter):
        """Test that non-duplicate errors are propagated without recovery attempt (1M-398)."""
        team_id = "test-team-id"
        label_name = "Test Label"

        # Mock: Creation fails with non-duplicate error
        network_error = AdapterError("Network timeout", "linear")
        adapter.client.execute_mutation = AsyncMock(side_effect=network_error)
        adapter._find_label_by_name = AsyncMock()
        adapter._labels_cache = []

        # Execute - should raise original error
        with pytest.raises(ValueError) as exc_info:
            await adapter._create_label(label_name, team_id)

        # Verify error message contains original error
        assert "Network timeout" in str(exc_info.value)
        # Recovery lookup should NOT be called for non-duplicate errors
        adapter._find_label_by_name.assert_not_called()


@pytest.mark.unit
class TestTransportQueryErrorHandling:
    """Test Priority 1: TransportQueryError handling in GraphQL client (1M-398)."""

    @pytest.fixture
    def client(self):
        """Create a Linear GraphQL client for testing."""
        from mcp_ticketer.adapters.linear.client import LinearGraphQLClient

        return LinearGraphQLClient(api_key="test_api_key_12345")

    @pytest.mark.asyncio
    async def test_transport_query_error_duplicate_label(self, client):
        """Test TransportQueryError with duplicate label error produces clear message."""
        # Import TransportQueryError
        try:
            from gql.transport.exceptions import TransportQueryError
        except ImportError:
            pytest.skip("gql library not installed")

        # Mock TransportQueryError with duplicate label error
        mock_error = TransportQueryError(
            "GraphQL validation error",
            errors=[{"message": "duplicate label name", "path": ["issueLabelCreate"]}],
        )

        query_string = "mutation { issueLabelCreate(input: {}) { success } }"

        with patch.object(client, "create_client") as mock_create_client:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=mock_error)
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client_instance

            # Execute - should raise AdapterError with clear message
            with pytest.raises(AdapterError) as exc_info:
                await client.execute_query(query_string, {})

            # Verify error message is clear (not "transport error")
            error_msg = str(exc_info.value)
            assert "Label already exists" in error_msg
            assert "duplicate label name" in error_msg
            assert "transport error" not in error_msg.lower()

    @pytest.mark.asyncio
    async def test_transport_query_error_generic_validation(self, client):
        """Test TransportQueryError with generic validation error."""
        try:
            from gql.transport.exceptions import TransportQueryError
        except ImportError:
            pytest.skip("gql library not installed")

        # Mock TransportQueryError with generic validation error
        mock_error = TransportQueryError(
            "GraphQL validation error",
            errors=[
                {
                    "message": "Invalid input: field 'name' is required",
                    "path": ["issueCreate"],
                }
            ],
        )

        query_string = "mutation { issueCreate(input: {}) { success } }"

        with patch.object(client, "create_client") as mock_create_client:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=mock_error)
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client_instance

            # Execute - should raise AdapterError with validation message
            with pytest.raises(AdapterError) as exc_info:
                await client.execute_query(query_string, {})

            # Verify error message contains validation details
            error_msg = str(exc_info.value)
            assert "GraphQL validation error" in error_msg
            assert "Invalid input" in error_msg

    @pytest.mark.asyncio
    async def test_transport_query_error_no_errors_attribute(self, client):
        """Test TransportQueryError without errors attribute (fallback)."""
        try:
            from gql.transport.exceptions import TransportQueryError
        except ImportError:
            pytest.skip("gql library not installed")

        # Mock TransportQueryError without errors attribute
        mock_error = TransportQueryError("Unknown GraphQL error")
        mock_error.errors = None

        query_string = "query { viewer { id } }"

        with patch.object(client, "create_client") as mock_create_client:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(side_effect=mock_error)
            mock_client_instance = AsyncMock()
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_session)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client_instance

            # Execute - should raise AdapterError with fallback message
            with pytest.raises(AdapterError) as exc_info:
                await client.execute_query(query_string, {})

            # Verify fallback error message
            error_msg = str(exc_info.value)
            assert "Linear GraphQL error" in error_msg


@pytest.mark.integration
class TestLabelCreationIntegration:
    """Integration tests for label creation in ticket workflow."""

    @pytest.fixture
    def adapter(self):
        """Create a Linear adapter instance for testing."""
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": "02d15669-7351-4451-9719-807576c16049",
        }
        return LinearAdapter(config)

    @pytest.mark.asyncio
    async def test_create_task_with_new_labels(self, adapter):
        """Test creating a task with new labels that need to be created."""
        from mcp_ticketer.core.models import Priority, Task, TicketState

        task = Task(
            title="Test Task",
            description="Test description",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            tags=["MCP Ticketer", "Bug", "Enhancement"],
        )

        team_id = "test-team-id"
        adapter._ensure_team_id = AsyncMock(return_value=team_id)
        adapter._initialized = True
        adapter._workflow_states = {"unstarted": {"id": "state-id-1", "position": 0}}
        adapter._labels_cache = []

        # Mock label creation
        created_label_ids = ["label-1", "label-2", "label-3"]
        adapter._ensure_labels_exist = AsyncMock(return_value=created_label_ids)

        # Mock issue creation
        mock_issue = {
            "identifier": "TEST-123",
            "title": task.title,
            "description": task.description,
            "priority": 2,
            "state": {"type": "unstarted"},
            "labels": {
                "nodes": [
                    {"name": "MCP Ticketer"},
                    {"name": "Bug"},
                    {"name": "Enhancement"},
                ]
            },
            "createdAt": "2025-01-19T00:00:00Z",
            "updatedAt": "2025-01-19T00:00:00Z",
        }

        adapter.client.execute_mutation = AsyncMock(
            return_value={"issueCreate": {"success": True, "issue": mock_issue}}
        )

        # Execute
        result = await adapter._create_task(task)

        # Verify labels were ensured to exist
        adapter._ensure_labels_exist.assert_called_once_with(task.tags)

        # Verify task was created successfully
        assert result.id == "TEST-123"
        assert result.tags == ["MCP Ticketer", "Bug", "Enhancement"]

    @pytest.mark.asyncio
    async def test_update_task_with_new_labels(self, adapter):
        """Test updating a task to add new labels."""
        ticket_id = "TEST-123"
        updates = {"tags": ["New Label 1", "New Label 2"]}
        team_id = "test-team-id"

        adapter._ensure_team_id = AsyncMock(return_value=team_id)
        adapter._initialized = True
        adapter._workflow_states = {"unstarted": {"id": "state-id-1", "position": 0}}
        adapter._labels_cache = []

        # Mock label creation
        new_label_ids = ["new-label-1", "new-label-2"]
        adapter._ensure_labels_exist = AsyncMock(return_value=new_label_ids)

        # Mock issue ID query
        adapter.client.execute_query = AsyncMock(
            return_value={"issue": {"id": "internal-id-123"}}
        )

        # Mock issue update
        mock_updated_issue = {
            "identifier": ticket_id,
            "title": "Test Task",
            "description": "Test",
            "priority": 3,
            "state": {"type": "started"},
            "labels": {"nodes": [{"name": "New Label 1"}, {"name": "New Label 2"}]},
            "createdAt": "2025-01-19T00:00:00Z",
            "updatedAt": "2025-01-19T00:00:00Z",
        }

        adapter.client.execute_mutation = AsyncMock(
            return_value={"issueUpdate": {"success": True, "issue": mock_updated_issue}}
        )

        # Execute
        result = await adapter.update(ticket_id, updates)

        # Verify labels were ensured to exist
        adapter._ensure_labels_exist.assert_called_once()

        # Verify task was updated successfully
        assert result is not None
        assert result.id == ticket_id
