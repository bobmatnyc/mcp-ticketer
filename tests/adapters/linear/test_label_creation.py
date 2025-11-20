"""Unit tests for Linear adapter label creation functionality."""

from unittest.mock import AsyncMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


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
        """Test that partial label creation failure doesn't block entire operation."""
        label_names = ["Success Label", "Failure Label", "Another Success"]
        team_id = "test-team-id"

        adapter._labels_cache = []
        adapter._ensure_team_id = AsyncMock(return_value=team_id)

        # Mock creation where middle label fails
        async def mock_create_label(name, tid, color="#0366d6"):
            if name == "Failure Label":
                raise ValueError("Simulated creation failure")
            return f"label-{name.replace(' ', '-').lower()}"

        adapter._create_label = AsyncMock(side_effect=mock_create_label)

        # Execute
        result = await adapter._ensure_labels_exist(label_names)

        # Verify - should have 2 labels (failed one skipped)
        assert len(result) == 2
        assert "label-success-label" in result
        assert "label-another-success" in result
        assert adapter._create_label.call_count == 3

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
