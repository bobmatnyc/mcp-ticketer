"""Unit tests for new Linear adapter operations (cycles, status)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.fixture
def mock_adapter() -> None:
    """Create a LinearAdapter instance with mocked client."""
    config = {
        "api_key": "lin_api_test_key_12345",
        "team_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    }
    adapter = LinearAdapter(config)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock()
    adapter._initialized = True
    adapter._workflow_states = {
        "unstarted": {"id": "state-1", "type": "unstarted", "position": 1},
        "started": {"id": "state-2", "type": "started", "position": 2},
        "completed": {"id": "state-3", "type": "completed", "position": 3},
    }
    return adapter


@pytest.mark.asyncio
@pytest.mark.unit
class TestListCycles:
    """Test list_cycles() method."""

    async def test_list_cycles_success(self, mock_adapter):
        """Test successfully listing cycles."""
        # Mock response with pagination
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "cycles": {
                    "nodes": [
                        {
                            "id": "cycle-1",
                            "name": "Sprint 1",
                            "number": 1,
                            "startsAt": "2025-01-01T00:00:00Z",
                            "endsAt": "2025-01-14T23:59:59Z",
                            "completedAt": None,
                            "progress": 0.45,
                        },
                        {
                            "id": "cycle-2",
                            "name": "Sprint 2",
                            "number": 2,
                            "startsAt": "2025-01-15T00:00:00Z",
                            "endsAt": "2025-01-28T23:59:59Z",
                            "completedAt": None,
                            "progress": 0.12,
                        },
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        result = await mock_adapter.list_cycles()

        assert len(result) == 2
        assert result[0]["id"] == "cycle-1"
        assert result[0]["name"] == "Sprint 1"
        assert result[0]["number"] == 1
        assert result[0]["progress"] == 0.45
        assert result[1]["id"] == "cycle-2"
        assert result[1]["name"] == "Sprint 2"

        # Verify query was called with correct parameters
        mock_adapter.client.execute_query.assert_called_once()
        call_args = mock_adapter.client.execute_query.call_args
        assert call_args[0][1]["teamId"] == "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        assert call_args[0][1]["first"] == 50

    async def test_list_cycles_with_pagination(self, mock_adapter):
        """Test listing cycles with pagination."""
        # First page
        first_response = {
            "team": {
                "cycles": {
                    "nodes": [
                        {
                            "id": "cycle-1",
                            "name": "Sprint 1",
                            "number": 1,
                            "startsAt": "2025-01-01T00:00:00Z",
                            "endsAt": "2025-01-14T23:59:59Z",
                            "completedAt": None,
                            "progress": 0.45,
                        }
                    ],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                }
            }
        }

        # Second page
        second_response = {
            "team": {
                "cycles": {
                    "nodes": [
                        {
                            "id": "cycle-2",
                            "name": "Sprint 2",
                            "number": 2,
                            "startsAt": "2025-01-15T00:00:00Z",
                            "endsAt": "2025-01-28T23:59:59Z",
                            "completedAt": None,
                            "progress": 0.12,
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        mock_adapter.client.execute_query.side_effect = [
            first_response,
            second_response,
        ]

        result = await mock_adapter.list_cycles()

        assert len(result) == 2
        assert result[0]["id"] == "cycle-1"
        assert result[1]["id"] == "cycle-2"
        assert mock_adapter.client.execute_query.call_count == 2

    async def test_list_cycles_with_custom_limit(self, mock_adapter):
        """Test listing cycles with custom limit."""
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "cycles": {
                    "nodes": [
                        {
                            "id": "cycle-1",
                            "name": "Sprint 1",
                            "number": 1,
                            "startsAt": "2025-01-01T00:00:00Z",
                            "endsAt": "2025-01-14T23:59:59Z",
                            "completedAt": None,
                            "progress": 0.45,
                        }
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        result = await mock_adapter.list_cycles(limit=10)

        assert len(result) == 1
        call_args = mock_adapter.client.execute_query.call_args
        assert call_args[0][1]["first"] == 10

    async def test_list_cycles_with_custom_team_id(self, mock_adapter):
        """Test listing cycles with custom team ID."""
        custom_team_id = "custom-team-uuid"
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "cycles": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        await mock_adapter.list_cycles(team_id=custom_team_id)

        call_args = mock_adapter.client.execute_query.call_args
        assert call_args[0][1]["teamId"] == custom_team_id

    async def test_list_cycles_empty_result(self, mock_adapter):
        """Test listing cycles with no results."""
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "cycles": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }
            }
        }

        result = await mock_adapter.list_cycles()

        assert result == []

    async def test_list_cycles_error_handling(self, mock_adapter):
        """Test error handling in list_cycles."""
        mock_adapter.client.execute_query.side_effect = Exception(
            "GraphQL query failed"
        )

        with pytest.raises(ValueError) as exc_info:
            await mock_adapter.list_cycles()

        assert "Failed to list Linear cycles" in str(exc_info.value)

    async def test_list_cycles_invalid_credentials(self, mock_adapter):
        """Test list_cycles with invalid credentials."""
        mock_adapter.api_key = None

        with pytest.raises(ValueError) as exc_info:
            await mock_adapter.list_cycles()

        assert "Linear API key is required" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
class TestGetIssueStatus:
    """Test get_issue_status() method."""

    async def test_get_issue_status_success(self, mock_adapter):
        """Test successfully getting issue status."""
        # Mock _resolve_issue_id
        with patch.object(
            mock_adapter, "_resolve_issue_id", return_value="issue-uuid-123"
        ):
            mock_adapter.client.execute_query.return_value = {
                "issue": {
                    "id": "issue-uuid-123",
                    "state": {
                        "id": "state-1",
                        "name": "In Progress",
                        "type": "started",
                        "color": "#4A90E2",
                        "description": "Work is in progress",
                        "position": 2,
                    },
                }
            }

            result = await mock_adapter.get_issue_status("BTA-123")

            assert result is not None
            assert result["id"] == "state-1"
            assert result["name"] == "In Progress"
            assert result["type"] == "started"
            assert result["color"] == "#4A90E2"
            assert result["description"] == "Work is in progress"
            assert result["position"] == 2

    async def test_get_issue_status_issue_not_found(self, mock_adapter):
        """Test getting status for non-existent issue."""
        with patch.object(mock_adapter, "_resolve_issue_id", return_value=None):
            result = await mock_adapter.get_issue_status("INVALID-123")

            assert result is None

    async def test_get_issue_status_no_state_data(self, mock_adapter):
        """Test getting status when issue has no state data."""
        with patch.object(
            mock_adapter, "_resolve_issue_id", return_value="issue-uuid-123"
        ):
            mock_adapter.client.execute_query.return_value = {"issue": None}

            result = await mock_adapter.get_issue_status("BTA-123")

            assert result is None

    async def test_get_issue_status_error_handling(self, mock_adapter):
        """Test error handling in get_issue_status."""
        with patch.object(
            mock_adapter, "_resolve_issue_id", return_value="issue-uuid-123"
        ):
            mock_adapter.client.execute_query.side_effect = Exception(
                "GraphQL query failed"
            )

            with pytest.raises(ValueError) as exc_info:
                await mock_adapter.get_issue_status("BTA-123")

            assert "Failed to get issue status" in str(exc_info.value)
            assert "BTA-123" in str(exc_info.value)

    async def test_get_issue_status_with_uuid(self, mock_adapter):
        """Test getting status with direct UUID (no resolution needed)."""
        issue_uuid = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        with patch.object(mock_adapter, "_resolve_issue_id", return_value=issue_uuid):
            mock_adapter.client.execute_query.return_value = {
                "issue": {
                    "id": issue_uuid,
                    "state": {
                        "id": "state-1",
                        "name": "Done",
                        "type": "completed",
                        "color": "#00C875",
                        "description": "Work is complete",
                        "position": 5,
                    },
                }
            }

            result = await mock_adapter.get_issue_status(issue_uuid)

            assert result is not None
            assert result["type"] == "completed"

    async def test_get_issue_status_invalid_credentials(self, mock_adapter):
        """Test get_issue_status with invalid credentials."""
        mock_adapter.api_key = None

        with pytest.raises(ValueError) as exc_info:
            await mock_adapter.get_issue_status("BTA-123")

        assert "Linear API key is required" in str(exc_info.value)


@pytest.mark.asyncio
@pytest.mark.unit
class TestListIssueStatuses:
    """Test list_issue_statuses() method."""

    async def test_list_issue_statuses_success(self, mock_adapter):
        """Test successfully listing all workflow states."""
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "states": {
                    "nodes": [
                        {
                            "id": "state-1",
                            "name": "Backlog",
                            "type": "backlog",
                            "color": "#E0E0E0",
                            "description": "Work to be done",
                            "position": 0,
                        },
                        {
                            "id": "state-2",
                            "name": "To Do",
                            "type": "unstarted",
                            "color": "#95C5ED",
                            "description": "Ready to start",
                            "position": 1,
                        },
                        {
                            "id": "state-3",
                            "name": "In Progress",
                            "type": "started",
                            "color": "#4A90E2",
                            "description": "Work in progress",
                            "position": 2,
                        },
                        {
                            "id": "state-4",
                            "name": "Done",
                            "type": "completed",
                            "color": "#00C875",
                            "description": "Work complete",
                            "position": 5,
                        },
                        {
                            "id": "state-5",
                            "name": "Canceled",
                            "type": "canceled",
                            "color": "#FF6B6B",
                            "description": "Work canceled",
                            "position": 6,
                        },
                    ]
                }
            }
        }

        result = await mock_adapter.list_issue_statuses()

        assert len(result) == 5
        assert result[0]["name"] == "Backlog"
        assert result[0]["type"] == "backlog"
        assert result[1]["name"] == "To Do"
        assert result[1]["type"] == "unstarted"
        assert result[2]["name"] == "In Progress"
        assert result[2]["type"] == "started"
        assert result[3]["name"] == "Done"
        assert result[3]["type"] == "completed"
        assert result[4]["name"] == "Canceled"
        assert result[4]["type"] == "canceled"

        # Verify states are sorted by position
        positions = [state["position"] for state in result]
        assert positions == sorted(positions)

    async def test_list_issue_statuses_with_custom_team_id(self, mock_adapter):
        """Test listing statuses with custom team ID."""
        custom_team_id = "custom-team-uuid"
        mock_adapter.client.execute_query.return_value = {
            "team": {"states": {"nodes": []}}
        }

        await mock_adapter.list_issue_statuses(team_id=custom_team_id)

        call_args = mock_adapter.client.execute_query.call_args
        assert call_args[0][1]["teamId"] == custom_team_id

    async def test_list_issue_statuses_empty_result(self, mock_adapter):
        """Test listing statuses with no results."""
        mock_adapter.client.execute_query.return_value = {
            "team": {"states": {"nodes": []}}
        }

        result = await mock_adapter.list_issue_statuses()

        assert result == []

    async def test_list_issue_statuses_sorts_by_position(self, mock_adapter):
        """Test that statuses are sorted by position."""
        # Return states in random order
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "states": {
                    "nodes": [
                        {
                            "id": "state-4",
                            "name": "Done",
                            "type": "completed",
                            "color": "#00C875",
                            "description": "Work complete",
                            "position": 5,
                        },
                        {
                            "id": "state-1",
                            "name": "Backlog",
                            "type": "backlog",
                            "color": "#E0E0E0",
                            "description": "Work to be done",
                            "position": 0,
                        },
                        {
                            "id": "state-3",
                            "name": "In Progress",
                            "type": "started",
                            "color": "#4A90E2",
                            "description": "Work in progress",
                            "position": 2,
                        },
                    ]
                }
            }
        }

        result = await mock_adapter.list_issue_statuses()

        # Verify they're returned in position order
        assert result[0]["position"] == 0
        assert result[1]["position"] == 2
        assert result[2]["position"] == 5

    async def test_list_issue_statuses_error_handling(self, mock_adapter):
        """Test error handling in list_issue_statuses."""
        mock_adapter.client.execute_query.side_effect = Exception(
            "GraphQL query failed"
        )

        with pytest.raises(ValueError) as exc_info:
            await mock_adapter.list_issue_statuses()

        assert "Failed to list workflow states" in str(exc_info.value)

    async def test_list_issue_statuses_invalid_credentials(self, mock_adapter):
        """Test list_issue_statuses with invalid credentials."""
        mock_adapter.api_key = None

        with pytest.raises(ValueError) as exc_info:
            await mock_adapter.list_issue_statuses()

        assert "Linear API key is required" in str(exc_info.value)

    async def test_list_issue_statuses_all_state_types(self, mock_adapter):
        """Test that all Linear state types are properly handled."""
        mock_adapter.client.execute_query.return_value = {
            "team": {
                "states": {
                    "nodes": [
                        {
                            "id": "state-1",
                            "name": "Backlog",
                            "type": "backlog",
                            "color": "#E0E0E0",
                            "description": "Backlog items",
                            "position": 0,
                        },
                        {
                            "id": "state-2",
                            "name": "To Do",
                            "type": "unstarted",
                            "color": "#95C5ED",
                            "description": "Ready to start",
                            "position": 1,
                        },
                        {
                            "id": "state-3",
                            "name": "In Progress",
                            "type": "started",
                            "color": "#4A90E2",
                            "description": "In progress",
                            "position": 2,
                        },
                        {
                            "id": "state-4",
                            "name": "Done",
                            "type": "completed",
                            "color": "#00C875",
                            "description": "Completed",
                            "position": 3,
                        },
                        {
                            "id": "state-5",
                            "name": "Canceled",
                            "type": "canceled",
                            "color": "#FF6B6B",
                            "description": "Canceled",
                            "position": 4,
                        },
                    ]
                }
            }
        }

        result = await mock_adapter.list_issue_statuses()

        state_types = {state["type"] for state in result}
        assert "backlog" in state_types
        assert "unstarted" in state_types
        assert "started" in state_types
        assert "completed" in state_types
        assert "canceled" in state_types
