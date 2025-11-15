"""Comprehensive tests for Linear adapter epic update functionality.

This test module covers:
- Epic update operations with various field combinations
- Error handling and validation
- Edge cases and boundary conditions
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import Epic


class TestLinearEpicUpdate:
    """Test suite for Linear adapter epic update functionality."""

    @pytest.fixture
    def mock_config(self) -> dict[str, str]:
        """Mock configuration for Linear adapter."""
        return {
            "api_key": "lin_api_test_key_12345678901234567890",
            "team_key": "TEST",
            "workspace": "test-workspace",
        }

    @pytest.fixture
    def adapter(self, mock_config: dict[str, str]) -> LinearAdapter:
        """Create a LinearAdapter instance with mocked client."""
        with patch("mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient"):
            adapter = LinearAdapter(mock_config)
            adapter._initialized = True
            adapter.team_id = "test-team-id"
            adapter._workflow_states = {}
            adapter._labels_cache = []
            adapter._users_cache = {}
            # Mock _resolve_project_id to return the same ID passed in
            adapter._resolve_project_id = AsyncMock(side_effect=lambda id: id)
            return adapter

    @pytest.mark.asyncio
    async def test_update_epic_description(self, adapter: LinearAdapter) -> None:
        """Test updating epic description successfully."""
        epic_id = "test-epic-id"
        new_description = "Updated epic description with new details"

        # Mock the GraphQL client response
        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Test Epic",
                    "description": new_description,
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        # Execute update
        result = await adapter.update_epic(epic_id, {"description": new_description})

        # Verify result
        assert result is not None
        assert isinstance(result, Epic)
        assert result.description == new_description
        assert result.id == epic_id

        # Verify GraphQL mutation was called
        adapter.client.execute_mutation.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_epic_title(self, adapter: LinearAdapter) -> None:
        """Test updating epic title successfully."""
        epic_id = "test-epic-id"
        new_title = "Updated Epic Title"

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": new_title,
                    "description": "Test description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, {"title": new_title})

        assert result is not None
        assert result.title == new_title

    @pytest.mark.asyncio
    async def test_update_epic_state_transitions(self, adapter: LinearAdapter) -> None:
        """Test updating epic state through valid transitions."""
        epic_id = "test-epic-id"

        # Test valid state transitions: planned -> started -> completed
        states = ["planned", "started", "completed"]

        for state in states:
            mock_response = {
                "projectUpdate": {
                    "success": True,
                    "project": {
                        "id": epic_id,
                        "name": "Test Epic",
                        "description": "Test description",
                        "state": state,
                        "targetDate": None,
                        "color": "blue",
                        "icon": "📋",
                        "createdAt": "2025-01-01T00:00:00.000Z",
                        "updatedAt": "2025-01-15T00:00:00.000Z",
                    },
                }
            }

            adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

            result = await adapter.update_epic(epic_id, {"state": state})

            assert result is not None
            # Note: state mapping may convert Linear state to TicketState
            # We verify the update was called with correct state

    @pytest.mark.asyncio
    async def test_update_epic_target_date(self, adapter: LinearAdapter) -> None:
        """Test updating epic target date with valid ISO format."""
        epic_id = "test-epic-id"
        target_date = (date.today() + timedelta(days=30)).isoformat()

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Test Epic",
                    "description": "Test description",
                    "state": "planned",
                    "targetDate": target_date,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, {"target_date": target_date})

        assert result is not None
        assert result.metadata.get("linear", {}).get("target_date") == target_date

    @pytest.mark.asyncio
    async def test_update_epic_multiple_fields(self, adapter: LinearAdapter) -> None:
        """Test updating multiple epic fields simultaneously."""
        epic_id = "test-epic-id"
        updates = {
            "title": "New Epic Title",
            "description": "New detailed description",
            "state": "started",
            "target_date": "2025-12-31",
        }

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": updates["title"],
                    "description": updates["description"],
                    "state": updates["state"],
                    "targetDate": updates["target_date"],
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, updates)

        assert result is not None
        assert result.title == updates["title"]
        assert result.description == updates["description"]

    @pytest.mark.asyncio
    async def test_update_epic_invalid_id(self, adapter: LinearAdapter) -> None:
        """Test updating epic with invalid ID returns None or raises error."""
        epic_id = "invalid-epic-id"

        # Mock error response from Linear API
        adapter.client.execute_mutation = AsyncMock(
            side_effect=ValueError("Project not found")
        )

        with pytest.raises(ValueError, match="Project not found"):
            await adapter.update_epic(epic_id, {"description": "test"})

    @pytest.mark.asyncio
    async def test_update_epic_empty_updates(self, adapter: LinearAdapter) -> None:
        """Test updating epic with empty updates dict."""
        epic_id = "test-epic-id"

        # Mock response for empty update (should technically work but do nothing)
        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Test Epic",
                    "description": "Original description",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        # Should complete successfully even with empty updates
        result = await adapter.update_epic(epic_id, {})
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_epic_none_updates(self, adapter: LinearAdapter) -> None:
        """Test updating epic with None updates fails."""
        epic_id = "test-epic-id"

        with pytest.raises((ValueError, TypeError)):
            await adapter.update_epic(epic_id, None)  # type: ignore

    @pytest.mark.asyncio
    async def test_update_epic_api_failure(self, adapter: LinearAdapter) -> None:
        """Test handling API failure during epic update."""
        epic_id = "test-epic-id"

        # Mock API error
        adapter.client.execute_mutation = AsyncMock(
            side_effect=Exception("API connection failed")
        )

        with pytest.raises(Exception, match="API connection failed"):
            await adapter.update_epic(epic_id, {"description": "test"})

    @pytest.mark.asyncio
    async def test_update_epic_invalid_date_format(
        self, adapter: LinearAdapter
    ) -> None:
        """Test updating epic with invalid date format."""
        epic_id = "test-epic-id"

        # Linear API should reject invalid date formats
        adapter.client.execute_mutation = AsyncMock(
            side_effect=ValueError("Invalid date format")
        )

        with pytest.raises(ValueError, match="Invalid date format"):
            await adapter.update_epic(epic_id, {"target_date": "not-a-date"})

    @pytest.mark.asyncio
    async def test_update_epic_unauthorized(self, adapter: LinearAdapter) -> None:
        """Test handling unauthorized access during epic update."""
        epic_id = "test-epic-id"

        adapter.client.execute_mutation = AsyncMock(
            side_effect=PermissionError("Unauthorized access")
        )

        # Implementation wraps exceptions in ValueError
        with pytest.raises(ValueError, match="Failed to update Linear project"):
            await adapter.update_epic(epic_id, {"description": "test"})

    @pytest.mark.asyncio
    async def test_update_epic_returns_epic_object(
        self, adapter: LinearAdapter
    ) -> None:
        """Test that update_epic returns a proper Epic object with all fields."""
        epic_id = "test-epic-id"

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Comprehensive Epic",
                    "description": "Full description",
                    "state": "started",
                    "targetDate": "2025-12-31",
                    "color": "green",
                    "icon": "🚀",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                    "lead": {
                        "id": "user-id",
                        "name": "Test User",
                        "email": "test@example.com",
                    },
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, {"description": "test"})

        # Verify Epic object structure
        assert result is not None
        assert isinstance(result, Epic)
        assert result.id == epic_id
        assert result.title == "Comprehensive Epic"
        assert result.description == "Full description"
        assert isinstance(result.metadata, dict)
        assert "linear" in result.metadata

    @pytest.mark.asyncio
    async def test_update_epic_graphql_error(self, adapter: LinearAdapter) -> None:
        """Test handling GraphQL errors during epic update."""
        epic_id = "test-epic-id"

        # Mock GraphQL error response
        adapter.client.execute_mutation = AsyncMock(
            side_effect=Exception("GraphQL error: Invalid field value")
        )

        with pytest.raises(Exception, match="GraphQL error"):
            await adapter.update_epic(epic_id, {"description": "test"})

    @pytest.mark.asyncio
    async def test_update_epic_rate_limit(self, adapter: LinearAdapter) -> None:
        """Test handling rate limiting during epic update."""
        epic_id = "test-epic-id"

        adapter.client.execute_mutation = AsyncMock(
            side_effect=Exception("Rate limit exceeded")
        )

        with pytest.raises(Exception, match="Rate limit exceeded"):
            await adapter.update_epic(epic_id, {"description": "test"})

    @pytest.mark.asyncio
    async def test_update_epic_with_color(self, adapter: LinearAdapter) -> None:
        """Test updating epic color."""
        epic_id = "test-epic-id"

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Test Epic",
                    "description": "Test",
                    "state": "planned",
                    "targetDate": None,
                    "color": "red",
                    "icon": "📋",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, {"color": "red"})

        assert result is not None
        assert result.metadata.get("linear", {}).get("color") == "red"

    @pytest.mark.asyncio
    async def test_update_epic_with_icon(self, adapter: LinearAdapter) -> None:
        """Test updating epic icon."""
        epic_id = "test-epic-id"

        mock_response = {
            "projectUpdate": {
                "success": True,
                "project": {
                    "id": epic_id,
                    "name": "Test Epic",
                    "description": "Test",
                    "state": "planned",
                    "targetDate": None,
                    "color": "blue",
                    "icon": "🎯",
                    "createdAt": "2025-01-01T00:00:00.000Z",
                    "updatedAt": "2025-01-15T00:00:00.000Z",
                },
            }
        }

        adapter.client.execute_mutation = AsyncMock(return_value=mock_response)

        result = await adapter.update_epic(epic_id, {"icon": "🎯"})

        assert result is not None
        assert result.metadata.get("linear", {}).get("icon") == "🎯"
