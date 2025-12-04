#!/usr/bin/env python3
"""Unit tests for LinearAdapter._resolve_project_id() URL parsing fix (1M-171)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.fixture
def mock_config():
    """Mock configuration for LinearAdapter."""
    return {
        "api_key": "lin_api_test_key_1234567890",
        "team_id": "test_team_id",
    }


@pytest.fixture
def mock_client():
    """Mock GraphQL client."""
    client = MagicMock()
    client.execute_query = AsyncMock()
    return client


@pytest.fixture
def linear_adapter(mock_config, mock_client):
    """Create a LinearAdapter instance with mocked client."""
    with patch(
        "mcp_ticketer.adapters.linear.adapter.LinearGraphQLClient",
        return_value=mock_client,
    ):
        adapter = LinearAdapter(mock_config)
        adapter.client = mock_client
        return adapter


class TestResolveProjectIdURLParsing:
    """Test URL parsing in _resolve_project_id() method."""

    @pytest.mark.asyncio
    async def test_full_url_with_overview_suffix(self, linear_adapter, mock_client):
        """Test that full URLs with /overview suffix are correctly parsed."""
        # Setup mock response for project query
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789123",
                        "name": "Matsuoka.com",
                        "slugId": "matsuokacom-1dc4f2881467",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        # Test URL with /overview suffix
        url = "https://linear.app/1m-hyperdev/project/matsuokacom-1dc4f2881467/overview"
        result = await linear_adapter._resolve_project_id(url)

        # Should extract "matsuokacom-1dc4f2881467" and find matching project
        assert result == "12345678-1234-1234-1234-123456789123"

    @pytest.mark.asyncio
    async def test_full_url_without_suffix(self, linear_adapter, mock_client):
        """Test URLs without trailing path segments."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789456",
                        "name": "Test Project",
                        "slugId": "test-project-abc123def456",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        url = "https://linear.app/team/project/test-project-abc123def456"
        result = await linear_adapter._resolve_project_id(url)

        assert result == "12345678-1234-1234-1234-123456789456"

    @pytest.mark.asyncio
    async def test_slug_id_format(self, linear_adapter, mock_client):
        """Test slug-id format (no URL)."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789789",
                        "name": "Another Project",
                        "slugId": "another-project-123456789abc",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        slug_id = "another-project-123456789abc"
        result = await linear_adapter._resolve_project_id(slug_id)

        assert result == "12345678-1234-1234-1234-123456789789"

    @pytest.mark.asyncio
    async def test_short_id_format(self, linear_adapter, mock_client):
        """Test short ID (12 hex chars) format."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789abc",
                        "name": "Short ID Project",
                        "slugId": "short-id-project-abc123def456",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        short_id = "abc123def456"
        result = await linear_adapter._resolve_project_id(short_id)

        assert result == "12345678-1234-1234-1234-123456789abc"

    @pytest.mark.asyncio
    async def test_full_uuid_format(self, linear_adapter, mock_client):
        """Test that full UUIDs are returned as-is without API calls."""
        uuid = "12345678-1234-1234-1234-123456789abc"
        result = await linear_adapter._resolve_project_id(uuid)

        # Should return UUID directly without querying API
        assert result == uuid
        mock_client.execute_query.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_slug_with_multiple_hyphens(self, linear_adapter, mock_client):
        """Test long slugs with many hyphens are correctly parsed from URLs."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789lng",
                        "name": "MCP Skills",
                        "slugId": "mcp-skills-dynamic-rag-skills-for-code-assistants-0000af8da9b0",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        url = "https://linear.app/1m-hyperdev/project/mcp-skills-dynamic-rag-skills-for-code-assistants-0000af8da9b0/overview"
        result = await linear_adapter._resolve_project_id(url)

        # Should correctly extract the full slug-id
        assert result == "12345678-1234-1234-1234-123456789lng"

    @pytest.mark.asyncio
    async def test_project_name_fallback(self, linear_adapter, mock_client):
        """Test that project names still work as fallback."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789nam",
                        "name": "My Project Name",
                        "slugId": "my-project-name-123456789abc",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        project_name = "My Project Name"
        result = await linear_adapter._resolve_project_id(project_name)

        # Should find by name
        assert result == "12345678-1234-1234-1234-123456789nam"

    @pytest.mark.asyncio
    async def test_invalid_url_format(self, linear_adapter, mock_client):
        """Test handling of invalid URL formats."""
        # Setup mock to return no projects
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        # Invalid URL that can't be parsed should be treated as a name and not found
        invalid_url = "https://example.com/not-a-linear-url"
        result = await linear_adapter._resolve_project_id(invalid_url)

        # Should return None when project not found
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_identifier(self, linear_adapter, mock_client):
        """Test handling of empty identifier."""
        result = await linear_adapter._resolve_project_id("")
        assert result is None

        result = await linear_adapter._resolve_project_id(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_url_with_updates_suffix(self, linear_adapter, mock_client):
        """Test URL with /updates suffix (specific case from ticket 1M-238)."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789mct",
                        "name": "mcp-ticketer",
                        "slugId": "mcp-ticketer-eac28953c267",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        # Test the exact URL format from ticket 1M-238
        url = "https://linear.app/1m-hyperdev/project/mcp-ticketer-eac28953c267/updates"
        result = await linear_adapter._resolve_project_id(url)

        # Should extract "mcp-ticketer-eac28953c267" and find matching project
        assert result == "12345678-1234-1234-1234-123456789mct"

    @pytest.mark.asyncio
    async def test_url_parser_integration(self, linear_adapter, mock_client):
        """Test that url_parser.normalize_project_id is used correctly."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789int",
                        "name": "Integration Test",
                        "slugId": "integration-test-abc123456789",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        # Test various URL formats that url_parser handles
        test_cases = [
            "https://linear.app/team/project/integration-test-abc123456789/overview",
            "https://linear.app/team/project/integration-test-abc123456789/issues",
            "https://linear.app/team/project/integration-test-abc123456789/updates",
            "https://linear.app/team/project/integration-test-abc123456789",
        ]

        for url in test_cases:
            result = await linear_adapter._resolve_project_id(url)
            assert (
                result == "12345678-1234-1234-1234-123456789int"
            ), f"Failed for URL: {url}"


class TestResolveProjectIdEdgeCases:
    """Test edge cases for _resolve_project_id()."""

    @pytest.mark.asyncio
    async def test_pagination_handling(self, linear_adapter, mock_client):
        """Test that pagination works correctly when searching through many projects."""
        # Setup mock to return projects across multiple pages
        call_count = [0]

        def mock_execute_query(query, variables):
            call_count[0] += 1
            if call_count[0] == 1:
                # First page
                return {
                    "projects": {
                        "nodes": [
                            {
                                "id": "12345678-1234-1234-1234-000000000001",
                                "name": "Project 1",
                                "slugId": "project-1-aaa111bbb222",
                            }
                        ],
                        "pageInfo": {
                            "hasNextPage": True,
                            "endCursor": "cursor1",
                        },
                    }
                }
            elif call_count[0] == 2:
                # Second page with matching project
                return {
                    "projects": {
                        "nodes": [
                            {
                                "id": "12345678-1234-1234-1234-000000000002",
                                "name": "Target Project",
                                "slugId": "target-project-abc123def456",
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }

        mock_client.execute_query = AsyncMock(side_effect=mock_execute_query)

        result = await linear_adapter._resolve_project_id("target-project-abc123def456")

        # Should find project on second page
        assert result == "12345678-1234-1234-1234-000000000002"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, linear_adapter, mock_client):
        """Test that project matching is case-insensitive."""
        mock_client.execute_query.return_value = {
            "projects": {
                "nodes": [
                    {
                        "id": "12345678-1234-1234-1234-123456789cas",
                        "name": "CamelCase Project",
                        "slugId": "CamelCase-Project-ABC123DEF456",
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }

        # Test various case combinations
        test_inputs = [
            "camelcase-project-abc123def456",
            "CAMELCASE-PROJECT-ABC123DEF456",
            "CamelCase-Project-ABC123DEF456",
        ]

        for test_input in test_inputs:
            result = await linear_adapter._resolve_project_id(test_input)
            assert (
                result == "12345678-1234-1234-1234-123456789cas"
            ), f"Failed for input: {test_input}"
