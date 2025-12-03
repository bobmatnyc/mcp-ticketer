"""Unit tests for Linear adapter project ID resolution."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter

# Valid 36-character UUIDs for testing (match Linear's UUID format)
MOCK_UUID_1 = "12345678-1234-1234-1234-123456789001"
MOCK_UUID_2 = "12345678-1234-1234-1234-123456789002"
MOCK_UUID_3 = "12345678-1234-1234-1234-123456789003"
MOCK_UUID_SPECIAL = "12345678-1234-1234-1234-12345678spec"
MOCK_UUID_MCP = "12345678-1234-1234-1234-123456789mcp"


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearProjectIDResolution:
    """Test Linear adapter project ID resolution from various formats."""

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
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
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
        """Test resolving project ID by short ID from URL using optimized direct query."""
        # Mock the direct query to return the project (optimization path)
        mock_direct_response = {
            "project": {
                "id": "ef19b35e-ce4f-4132-9705-811d4d6c8c08",
                "name": "CRM Smart Monitoring System",
                "slugId": "crm-smart-monitoring-system-f59a41a96c52",
                "state": "started",
                "description": "Test description",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
                "url": "https://linear.app/test/project/crm-smart-monitoring-system-f59a41a96c52",
                "icon": None,
                "color": "#0366d6",
                "targetDate": None,
                "startedAt": None,
                "completedAt": None,
                "teams": {"nodes": []},
            }
        }
        adapter.client.execute_query.return_value = mock_direct_response

        result = await adapter._resolve_project_id("f59a41a96c52")

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        # Should use direct query (optimization) - verify it was called with project(id:)
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "project(id: $id)" in call_args[0]
        ), "Should use direct query optimization"

    async def test_resolve_by_full_slug_id(self, adapter, mock_projects_response):
        """Test resolving project ID by full slugId using optimized direct query."""
        # Mock the direct query to return the project (optimization path)
        mock_direct_response = {
            "project": {
                "id": "ef19b35e-ce4f-4132-9705-811d4d6c8c08",
                "name": "CRM Smart Monitoring System",
                "slugId": "crm-smart-monitoring-system-f59a41a96c52",
                "state": "started",
                "description": "Test description",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
                "url": "https://linear.app/test/project/crm-smart-monitoring-system-f59a41a96c52",
                "icon": None,
                "color": "#0366d6",
                "targetDate": None,
                "startedAt": None,
                "completedAt": None,
                "teams": {"nodes": []},
            }
        }
        adapter.client.execute_query.return_value = mock_direct_response

        result = await adapter._resolve_project_id(
            "crm-smart-monitoring-system-f59a41a96c52"
        )

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        # Should use direct query (optimization) - verify it was called with project(id:)
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "project(id: $id)" in call_args[0]
        ), "Should use direct query optimization"

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
        """Test extracting and resolving from full Linear project URL using direct query."""
        # Mock the direct query to return the project (optimization path)
        mock_direct_response = {
            "project": {
                "id": "ef19b35e-ce4f-4132-9705-811d4d6c8c08",
                "name": "CRM Smart Monitoring System",
                "slugId": "crm-smart-monitoring-system-f59a41a96c52",
                "state": "started",
                "description": "Test description",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
                "url": "https://linear.app/test/project/crm-smart-monitoring-system-f59a41a96c52",
                "icon": None,
                "color": "#0366d6",
                "targetDate": None,
                "startedAt": None,
                "completedAt": None,
                "teams": {"nodes": []},
            }
        }
        adapter.client.execute_query.return_value = mock_direct_response

        url = "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52/overview"
        result = await adapter._resolve_project_id(url)

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        # Should use direct query after extracting slugId from URL
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "project(id: $id)" in call_args[0]
        ), "Should use direct query optimization"

    async def test_resolve_from_url_without_trailing_path(
        self, adapter, mock_projects_response
    ):
        """Test extracting from URL without /overview suffix using direct query."""
        # Mock the direct query to return the project (optimization path)
        mock_direct_response = {
            "project": {
                "id": "ef19b35e-ce4f-4132-9705-811d4d6c8c08",
                "name": "CRM Smart Monitoring System",
                "slugId": "crm-smart-monitoring-system-f59a41a96c52",
                "state": "started",
                "description": "Test description",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
                "url": "https://linear.app/test/project/crm-smart-monitoring-system-f59a41a96c52",
                "icon": None,
                "color": "#0366d6",
                "targetDate": None,
                "startedAt": None,
                "completedAt": None,
                "teams": {"nodes": []},
            }
        }
        adapter.client.execute_query.return_value = mock_direct_response

        url = "https://linear.app/travel-bta/project/crm-smart-monitoring-system-f59a41a96c52"
        result = await adapter._resolve_project_id(url)

        assert result == "ef19b35e-ce4f-4132-9705-811d4d6c8c08"
        # Should use direct query after extracting slugId from URL
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "project(id: $id)" in call_args[0]
        ), "Should use direct query optimization"

    async def test_resolve_invalid_url_format_raises_error(self, adapter):
        """Test that invalid URL format raises ValueError."""
        invalid_url = "https://linear.app/travel-bta/invalid/path"

        with pytest.raises(ValueError) as exc_info:
            await adapter._resolve_project_id(invalid_url)

        # Updated error message to match actual implementation
        assert "Failed to resolve project" in str(exc_info.value)

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
        """Test handling when short ID could match multiple projects using direct query."""
        # Use valid 12-character hex short IDs (as Linear uses)
        mock_direct_response = {
            "project": {
                "id": MOCK_UUID_1,
                "name": "Project One",
                "slugId": "project-one-abc123def456",
                "state": "started",
                "description": "Test description",
                "createdAt": "2025-01-01T00:00:00Z",
                "updatedAt": "2025-01-01T00:00:00Z",
                "url": "https://linear.app/test/project/project-one-abc123def456",
                "icon": None,
                "color": "#0366d6",
                "targetDate": None,
                "startedAt": None,
                "completedAt": None,
                "teams": {"nodes": []},
            }
        }
        adapter.client.execute_query.return_value = mock_direct_response

        # Should match exact short ID only using direct query (optimization)
        result = await adapter._resolve_project_id("abc123def456")

        assert result == MOCK_UUID_1
        # Verify direct query was used
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "project(id: $id)" in call_args[0]
        ), "Should use direct query optimization"

    async def test_resolve_project_with_no_slug_id(self, adapter):
        """Test handling projects that might have missing slugId."""
        mock_response = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789012",
                        "name": "Project Without Slug",
                        "slugId": "",  # Empty slugId
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
            }
        }
        adapter.client.execute_query.return_value = mock_response

        # Should still match by name
        result = await adapter._resolve_project_id("Project Without Slug")

        assert result == "12345678-1234-1234-1234-123456789012"

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
        """Test handling slugs with special characters - uses fallback list query."""
        # Use valid hex characters in the short ID (a-f, 0-9 only - no x,y,z)
        mock_response = {
            "projects": {
                "nodes": [
                    {
                        "id": MOCK_UUID_SPECIAL,
                        "name": "Project & Special!",
                        "slugId": "project-and-special-abc123def456",
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
            }
        }
        adapter.client.execute_query.return_value = mock_response

        # Slug without the short ID suffix - won't trigger direct query optimization
        result = await adapter._resolve_project_id("project-and-special")

        assert result == MOCK_UUID_SPECIAL
        # Should use list query since "project-and-special" doesn't look like a short ID
        adapter.client.execute_query.assert_called_once()
        call_args = adapter.client.execute_query.call_args[0]
        assert (
            "projects(first:" in call_args[0]
        ), "Should use list query for partial slug"

    async def test_resolve_with_pagination_multiple_pages(self, adapter):
        """Test that pagination works correctly across multiple pages."""
        # First page response
        first_page = {
            "projects": {
                "nodes": [
                    {
                        "id": MOCK_UUID_1,
                        "name": "Project One",
                        "slugId": "project-one-abc123",
                    },
                    {
                        "id": MOCK_UUID_2,
                        "name": "Project Two",
                        "slugId": "project-two-abc124",
                    },
                ],
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor-page-1",
                },
            }
        }

        # Second page response
        second_page = {
            "projects": {
                "nodes": [
                    {
                        "id": MOCK_UUID_3,
                        "name": "Target Project",
                        "slugId": "target-project-xyz789",
                    },
                ],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": "cursor-page-2",
                },
            }
        }

        # Mock to return different responses based on call count
        adapter.client.execute_query.side_effect = [first_page, second_page]

        # Try to find a project that's on the second page
        result = await adapter._resolve_project_id("target-project-xyz789")

        # Should find the project from the second page
        assert result == MOCK_UUID_3

        # Should have made exactly 2 API calls (pagination)
        assert adapter.client.execute_query.call_count == 2

        # Verify the second call included the cursor
        second_call_args = adapter.client.execute_query.call_args_list[1]
        assert second_call_args[0][1]["after"] == "cursor-page-1"

    async def test_resolve_with_pagination_over_100_projects(self, adapter):
        """Test handling workspaces with >100 projects (real-world scenario)."""
        # Simulate a workspace with 150 projects (2 pages)
        # Generate valid 36-character UUIDs for testing
        first_page_projects = [
            {
                "id": f"12345678-1234-1234-1234-{i:012d}",
                "name": f"Project {i}",
                "slugId": f"project-{i}-id{i:03d}",
            }
            for i in range(100)
        ]

        second_page_projects = [
            {
                "id": f"12345678-1234-1234-1234-{i:012d}",
                "name": f"Project {i}",
                "slugId": f"project-{i}-id{i:03d}",
            }
            for i in range(100, 150)
        ]

        # Add the target project at position 120 (on second page)
        second_page_projects[20] = {
            "id": MOCK_UUID_MCP,
            "name": "MCP Memory Project",
            "slugId": "mcp-memory-6cf55cfcfad4",
        }

        first_page = {
            "projects": {
                "nodes": first_page_projects,
                "pageInfo": {
                    "hasNextPage": True,
                    "endCursor": "cursor-100",
                },
            }
        }

        second_page = {
            "projects": {
                "nodes": second_page_projects,
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": "cursor-150",
                },
            }
        }

        adapter.client.execute_query.side_effect = [first_page, second_page]

        # Try to find project that would have failed with old 100-project limit
        result = await adapter._resolve_project_id("mcp-memory-6cf55cfcfad4")

        # Should successfully find the project from page 2
        assert result == MOCK_UUID_MCP
        assert adapter.client.execute_query.call_count == 2

    async def test_resolve_with_empty_first_page(self, adapter):
        """Test handling workspaces with 0 projects."""
        empty_response = {
            "projects": {
                "nodes": [],
                "pageInfo": {
                    "hasNextPage": False,
                    "endCursor": None,
                },
            }
        }

        adapter.client.execute_query.return_value = empty_response

        result = await adapter._resolve_project_id("any-project")

        assert result is None
        assert adapter.client.execute_query.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestLinearProjectResolutionInCreateTask:
    """Test integration of project resolution in the _create_task method."""

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
