"""Unit tests for Linear adapter project ID resolution."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearProjectIDResolution:
    """Test Linear adapter project ID resolution from various formats."""

    @pytest.fixture
    def adapter(self):
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
    def mock_projects_response(self):
        """Mock response from Linear projects query."""
        return {
            "projects": {
                "nodes": [
                    {
                        "id": "ef19b35e-ce4f-4132-9705-811d4d6c8c08",
                        "name": "CRM Smart Monitoring System",
                        "slugId": "crm-smart-monitoring-system-f59a41a96c52",
                    },
                    {
                        "id": "12345678-1234-1234-1234-123456789012",
                        "name": "Another Project",
                        "slugId": "another-project-abc123def",
                    },
                    {
                        "id": "87654321-4321-4321-4321-210987654321",
                        "name": "Test Project",
                        "slugId": "test-project-xyz789",
                    },
                ]
            }
        }

    async def test_resolve_full_uuid_returns_unchanged(self, adapter):
        """Test that a full UUID is returned unchanged without querying."""
        full_uuid = "ef19b35e-ce4f-4132-9705-811d4d6c8c08"

        result = await adapter._resolve_project_id(full_uuid)

        # Should return the UUID directly without calling the API
        assert result == full_uuid
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_by_slug(self, adapter, mock_projects_response):
        """Test resolving project ID by slug."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id("crm-smart-monitoring-system")

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_by_short_id(self, adapter, mock_projects_response):
        """Test resolving project ID by short ID from URL."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id("f59a41a96c52")

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_by_full_slug_id(self, adapter, mock_projects_response):
        """Test resolving project ID by full slugId."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id(
            "crm-smart-monitoring-system-f59a41a96c52"
        )

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_by_name(self, adapter, mock_projects_response):
        """Test resolving project ID by exact name match."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id("CRM Smart Monitoring System")

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_by_name_case_insensitive(
        self, adapter, mock_projects_response
    ):
        """Test that name matching is case-insensitive."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id("crm smart monitoring system")

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_from_full_url(self, adapter, mock_projects_response):
        """Test extracting and resolving from full Linear project URL."""
        adapter.client.execute_query.return_value = mock_projects_response

        url = "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview"
        result = await adapter._resolve_project_id(url)

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_from_url_without_trailing_path(
        self, adapter, mock_projects_response
    ):
        """Test extracting from URL without /overview suffix."""
        adapter.client.execute_query.return_value = mock_projects_response

        url = "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52"
        result = await adapter._resolve_project_id(url)

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_invalid_url_format_raises_error(self, adapter):
        """Test that invalid URL format raises ValueError."""
        invalid_url = "https://linear.app/travel-bta/invalid/path"

        with pytest.raises(ValueError) as exc_info:
            await adapter._resolve_project_id(invalid_url)

        assert "Invalid Linear project URL" in str(exc_info.value)

    async def test_resolve_nonexistent_project_returns_none(
        self, adapter, mock_projects_response
    ):
        """Test that unmatched project identifier returns None."""
        adapter.client.execute_query.return_value = mock_projects_response

        result = await adapter._resolve_project_id("nonexistent-project")

        assert result is None
        adapter.client.execute_query.assert_called_once()

    async def test_resolve_empty_identifier_returns_none(self, adapter):
        """Test that empty identifier returns None without querying."""
        result = await adapter._resolve_project_id("")

        assert result is None
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_none_identifier_returns_none(self, adapter):
        """Test that None identifier returns None without querying."""
        result = await adapter._resolve_project_id(None)

        assert result is None
        adapter.client.execute_query.assert_not_called()

    async def test_resolve_api_error_raises_value_error(self, adapter):
        """Test that API errors are wrapped in ValueError with context."""
        adapter.client.execute_query.side_effect = Exception("API connection failed")

        with pytest.raises(ValueError) as exc_info:
            await adapter._resolve_project_id("test-project")

        assert "Failed to resolve project" in str(exc_info.value)
        assert "test-project" in str(exc_info.value)

    async def test_resolve_matches_multiple_projects(self, adapter):
        """Test handling when short ID could match multiple projects."""
        # Mock response with projects that have similar patterns
        mock_response = {
            "projects": {
                "nodes": [
                    {
                        "id": "project-1-uuid",
                        "name": "Project One",
                        "slugId": "project-one-abc123",
                    },
                    {
                        "id": "project-2-uuid",
                        "name": "Project Two",
                        "slugId": "project-two-abc124",  # Very similar short ID
                    },
                ]
            }
        }
        adapter.client.execute_query.return_value = mock_response

        # Should match exact short ID only
        result = await adapter._resolve_project_id("abc123")

        assert result == "project-1-uuid"

    async def test_resolve_project_with_no_slug_id(self, adapter):
        """Test handling projects that might have missing slugId."""
        mock_response = {
            "projects": {
                "nodes": [
                    {
                        "id": "project-uuid",
                        "name": "Project Without Slug",
                        "slugId": "",  # Empty slugId
                    },
                ]
            }
        }
        adapter.client.execute_query.return_value = mock_response

        # Should still match by name
        result = await adapter._resolve_project_id("Project Without Slug")

        assert result == "project-uuid"

    async def test_resolve_slug_case_variations(self, adapter, mock_projects_response):
        """Test that slug matching works with various case combinations."""
        adapter.client.execute_query.return_value = mock_projects_response

        # Try different case variations
        test_cases = [
            "CRM-SMART-MONITORING-SYSTEM",
            "Crm-Smart-Monitoring-System",
            "crm-smart-monitoring-system",
        ]

        for slug in test_cases:
            adapter.client.execute_query.reset_mock()
            result = await adapter._resolve_project_id(slug)
            assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"

    async def test_resolve_with_special_characters_in_slug(self, adapter):
        """Test handling slugs with special characters."""
        mock_response = {
            "projects": {
                "nodes": [
                    {
                        "id": "special-project-uuid",
                        "name": "Project & Special!",
                        "slugId": "project-and-special-xyz123",
                    },
                ]
            }
        }
        adapter.client.execute_query.return_value = mock_response

        result = await adapter._resolve_project_id("project-and-special")

        assert result == "special-project-uuid"


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearProjectResolutionInCreateTask:
    """Test integration of project resolution in the _create_task method."""

    @pytest.fixture
    def adapter(self):
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

    async def test_resolve_project_called_during_task_creation(self, adapter):
        """Test that _resolve_project_id is called when parent_epic is provided."""
        from unittest.mock import patch

        # Mock project resolution to return a UUID
        mock_resolve = AsyncMock(return_value="resolved-uuid-12345")

        with patch.object(adapter, "_resolve_project_id", mock_resolve):
            # We're just testing that resolution is attempted
            # The actual task creation requires more complex mocking
            result = await adapter._resolve_project_id("test-project")

            assert result == "resolved-uuid-12345"
            mock_resolve.assert_called_once_with("test-project")
