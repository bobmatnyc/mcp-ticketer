"""Unit tests for GitHub Projects V2 CRUD operations.

Tests the 5 core project methods implemented in Week 2:
- project_list()
- project_get()
- project_create()
- project_update()
- project_delete()

Test Coverage Requirements:
- Happy paths for all 5 methods
- Error cases (not found, missing owner, invalid ID)
- Edge cases (empty lists, pagination, state filtering)
- Partial updates
- Auto-detection in project_get()
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_ticketer.adapters.github.adapter import GitHubAdapter
from mcp_ticketer.core.models import ProjectState


@pytest.fixture
def mock_config():
    """Create mock configuration for adapter."""
    return {
        "token": "test-token",
        "owner": "test-org",
        "repo": "test-repo",
    }


@pytest.fixture
def adapter(mock_config):
    """Create adapter with mocked GraphQL client."""
    with patch("mcp_ticketer.adapters.github.adapter.GitHubClient"):
        adapter = GitHubAdapter(mock_config)
        # Replace the client's execute_graphql with a mock
        adapter.gh_client.execute_graphql = AsyncMock()
        return adapter


class TestProjectList:
    """Tests for project_list() method."""

    @pytest.mark.asyncio
    async def test_project_list_success(self, adapter):
        """Test successful project listing."""
        # Mock GraphQL response
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectsV2": {
                    "nodes": [
                        {
                            "id": "PVT_TEST1",
                            "number": 1,
                            "title": "Test Project 1",
                            "shortDescription": "Description 1",
                            "closed": False,
                            "public": True,
                            "url": "https://github.com/orgs/test-org/projects/1",
                            "createdAt": "2025-01-01T00:00:00Z",
                            "updatedAt": "2025-01-02T00:00:00Z",
                            "owner": {
                                "__typename": "Organization",
                                "login": "test-org",
                                "id": "ORG123",
                            },
                        },
                        {
                            "id": "PVT_TEST2",
                            "number": 2,
                            "title": "Test Project 2",
                            "shortDescription": "Description 2",
                            "closed": False,
                            "public": True,
                            "url": "https://github.com/orgs/test-org/projects/2",
                            "createdAt": "2025-01-03T00:00:00Z",
                            "updatedAt": "2025-01-04T00:00:00Z",
                            "owner": {
                                "__typename": "Organization",
                                "login": "test-org",
                                "id": "ORG123",
                            },
                        },
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }
        }

        projects = await adapter.project_list(limit=10)

        assert len(projects) == 2
        assert projects[0].name == "Test Project 1"
        assert projects[0].platform == "github"
        assert projects[0].state == ProjectState.ACTIVE
        assert projects[1].name == "Test Project 2"
        adapter.gh_client.execute_graphql.assert_called_once()

    @pytest.mark.asyncio
    async def test_project_list_with_pagination(self, adapter):
        """Test project listing with pagination cursor."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectsV2": {
                    "nodes": [],
                    "pageInfo": {"hasNextPage": True, "endCursor": "cursor123"},
                }
            }
        }

        await adapter.project_list(limit=10, cursor="cursor123")

        # Verify cursor was passed to query
        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args[1]["variables"]["after"] == "cursor123"

    @pytest.mark.asyncio
    async def test_project_list_empty(self, adapter):
        """Test project listing with no results."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectsV2": {"nodes": [], "pageInfo": {"hasNextPage": False}}
            }
        }

        projects = await adapter.project_list()

        assert len(projects) == 0

    @pytest.mark.asyncio
    async def test_project_list_filter_by_state(self, adapter):
        """Test project listing with state filter."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectsV2": {
                    "nodes": [
                        {
                            "id": "PVT_ACTIVE",
                            "number": 1,
                            "title": "Active Project",
                            "closed": False,
                            "public": True,
                            "owner": {
                                "__typename": "Organization",
                                "login": "test-org",
                                "id": "ORG123",
                            },
                        },
                        {
                            "id": "PVT_CLOSED",
                            "number": 2,
                            "title": "Closed Project",
                            "closed": True,
                            "closedAt": "2025-01-05T00:00:00Z",
                            "public": True,
                            "owner": {
                                "__typename": "Organization",
                                "login": "test-org",
                                "id": "ORG123",
                            },
                        },
                    ],
                    "pageInfo": {"hasNextPage": False},
                }
            }
        }

        # Filter for active projects only
        projects = await adapter.project_list(state=ProjectState.ACTIVE)

        assert len(projects) == 1
        assert projects[0].name == "Active Project"
        assert projects[0].state == ProjectState.ACTIVE

    @pytest.mark.asyncio
    async def test_project_list_missing_owner(self, adapter):
        """Test project listing fails when owner not configured."""
        adapter.owner = None

        with pytest.raises(ValueError, match="Owner required"):
            await adapter.project_list()

    @pytest.mark.asyncio
    async def test_project_list_org_not_found(self, adapter):
        """Test project listing when organization doesn't exist."""
        adapter.gh_client.execute_graphql.return_value = {}

        projects = await adapter.project_list(owner="nonexistent-org")

        assert len(projects) == 0


class TestProjectGet:
    """Tests for project_get() method."""

    @pytest.mark.asyncio
    async def test_project_get_by_number(self, adapter):
        """Test getting project by number."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectV2": {
                    "id": "PVT_TEST",
                    "number": 42,
                    "title": "Test Project",
                    "closed": False,
                    "public": True,
                    "owner": {
                        "__typename": "Organization",
                        "login": "test-org",
                        "id": "ORG123",
                    },
                }
            }
        }

        project = await adapter.project_get("42", owner="test-org")

        assert project is not None
        assert project.name == "Test Project"
        assert project.platform_id == "42"

    @pytest.mark.asyncio
    async def test_project_get_by_node_id(self, adapter):
        """Test getting project by node ID."""
        adapter.gh_client.execute_graphql.return_value = {
            "node": {
                "id": "PVT_kwDOABCD1234",
                "number": 42,
                "title": "Test Project",
                "closed": False,
                "public": True,
                "owner": {
                    "__typename": "Organization",
                    "login": "test-org",
                    "id": "ORG123",
                },
            }
        }

        project = await adapter.project_get("PVT_kwDOABCD1234")

        assert project is not None
        assert project.name == "Test Project"
        assert project.id == "PVT_kwDOABCD1234"

    @pytest.mark.asyncio
    async def test_project_get_not_found(self, adapter):
        """Test getting project that doesn't exist."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {"projectV2": None}
        }

        project = await adapter.project_get("999", owner="test-org")

        assert project is None

    @pytest.mark.asyncio
    async def test_project_get_invalid_id_format(self, adapter):
        """Test getting project with invalid ID format."""
        with pytest.raises(RuntimeError, match="Failed to get project"):
            await adapter.project_get("invalid-id")

    @pytest.mark.asyncio
    async def test_project_get_missing_owner_for_number(self, adapter):
        """Test getting project by number without owner."""
        adapter.owner = None

        with pytest.raises(RuntimeError, match="Failed to get project"):
            await adapter.project_get("42")


class TestProjectCreate:
    """Tests for project_create() method."""

    @pytest.mark.asyncio
    async def test_project_create_success(self, adapter):
        """Test successful project creation."""
        # Mock organization query for owner ID
        adapter.gh_client.execute_graphql.side_effect = [
            # First call: Get org ID
            {"organization": {"id": "ORG123"}},
            # Second call: Create project
            {
                "createProjectV2": {
                    "projectV2": {
                        "id": "PVT_NEW",
                        "number": 10,
                        "title": "New Project",
                        "url": "https://github.com/orgs/test-org/projects/10",
                        "createdAt": "2025-01-10T00:00:00Z",
                        "closed": False,
                        "public": True,
                        "owner": {
                            "__typename": "Organization",
                            "login": "test-org",
                            "id": "ORG123",
                        },
                    }
                }
            },
        ]

        project = await adapter.project_create(title="New Project", owner="test-org")

        assert project is not None
        assert project.name == "New Project"
        assert project.platform == "github"
        assert adapter.gh_client.execute_graphql.call_count == 2

    @pytest.mark.asyncio
    async def test_project_create_with_description(self, adapter):
        """Test project creation with description."""
        adapter.gh_client.execute_graphql.side_effect = [
            # Get org ID
            {"organization": {"id": "ORG123"}},
            # Create project
            {
                "createProjectV2": {
                    "projectV2": {
                        "id": "PVT_NEW",
                        "number": 10,
                        "title": "New Project",
                        "closed": False,
                        "public": True,
                        "owner": {
                            "__typename": "Organization",
                            "login": "test-org",
                            "id": "ORG123",
                        },
                    }
                }
            },
            # Update with description
            {
                "updateProjectV2": {
                    "projectV2": {
                        "id": "PVT_NEW",
                        "number": 10,
                        "title": "New Project",
                        "shortDescription": "Test description",
                        "closed": False,
                        "public": True,
                        "owner": {
                            "__typename": "Organization",
                            "login": "test-org",
                            "id": "ORG123",
                        },
                    }
                }
            },
        ]

        project = await adapter.project_create(
            title="New Project", description="Test description", owner="test-org"
        )

        assert project is not None
        assert adapter.gh_client.execute_graphql.call_count == 3

    @pytest.mark.asyncio
    async def test_project_create_missing_owner(self, adapter):
        """Test project creation fails when owner not provided."""
        adapter.owner = None

        with pytest.raises(ValueError, match="Owner required"):
            await adapter.project_create(title="New Project")

    @pytest.mark.asyncio
    async def test_project_create_org_not_found(self, adapter):
        """Test project creation fails when organization doesn't exist."""
        adapter.gh_client.execute_graphql.return_value = {}

        with pytest.raises(RuntimeError, match="Failed to create project"):
            await adapter.project_create(title="New Project", owner="nonexistent-org")


class TestProjectUpdate:
    """Tests for project_update() method."""

    @pytest.mark.asyncio
    async def test_project_update_title(self, adapter):
        """Test updating project title."""
        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_TEST",
                    "number": 1,
                    "title": "Updated Title",
                    "closed": False,
                    "public": True,
                    "owner": {
                        "__typename": "Organization",
                        "login": "test-org",
                        "id": "ORG123",
                    },
                }
            }
        }

        project = await adapter.project_update(
            project_id="PVT_TEST", title="Updated Title"
        )

        assert project is not None
        assert project.name == "Updated Title"

    @pytest.mark.asyncio
    async def test_project_update_state(self, adapter):
        """Test updating project state."""
        from datetime import datetime, timezone

        # Use a very recent closedAt to ensure COMPLETED state (not ARCHIVED)
        recent_close = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_TEST",
                    "number": 1,
                    "title": "Test Project",
                    "closed": True,
                    "closedAt": recent_close,
                    "public": True,
                    "owner": {
                        "__typename": "Organization",
                        "login": "test-org",
                        "id": "ORG123",
                    },
                }
            }
        }

        project = await adapter.project_update(
            project_id="PVT_TEST", state=ProjectState.COMPLETED
        )

        assert project is not None
        assert project.state == ProjectState.COMPLETED

        # Verify 'closed' was set to True
        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args[1]["variables"]["closed"] is True

    @pytest.mark.asyncio
    async def test_project_update_partial(self, adapter):
        """Test partial project update with only some fields."""
        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_TEST",
                    "number": 1,
                    "title": "Test Project",
                    "shortDescription": "New description",
                    "closed": False,
                    "public": True,
                    "owner": {
                        "__typename": "Organization",
                        "login": "test-org",
                        "id": "ORG123",
                    },
                }
            }
        }

        project = await adapter.project_update(
            project_id="PVT_TEST", description="New description"
        )

        assert project is not None
        # Verify only shortDescription was in variables
        call_args = adapter.gh_client.execute_graphql.call_args
        variables = call_args[1]["variables"]
        assert "shortDescription" in variables
        assert "title" not in variables

    @pytest.mark.asyncio
    async def test_project_update_no_fields(self, adapter):
        """Test project update fails when no fields provided."""
        with pytest.raises(ValueError, match="At least one field must be provided"):
            await adapter.project_update(project_id="PVT_TEST")

    @pytest.mark.asyncio
    async def test_project_update_not_found(self, adapter):
        """Test project update when project doesn't exist."""
        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {"projectV2": None}
        }

        project = await adapter.project_update(
            project_id="PVT_NONEXISTENT", title="New Title"
        )

        assert project is None


class TestProjectDelete:
    """Tests for project_delete() method."""

    @pytest.mark.asyncio
    async def test_project_delete_soft(self, adapter):
        """Test soft delete (close) of project."""
        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {
                "projectV2": {
                    "id": "PVT_TEST",
                    "number": 1,
                    "title": "Test Project",
                    "closed": True,
                    "public": False,
                    "owner": {
                        "__typename": "Organization",
                        "login": "test-org",
                        "id": "ORG123",
                    },
                }
            }
        }

        result = await adapter.project_delete("PVT_TEST")

        assert result is True
        # Verify soft delete sets closed=True and public=False
        call_args = adapter.gh_client.execute_graphql.call_args
        variables = call_args[1]["variables"]
        assert variables["closed"] is True
        assert variables["public"] is False

    @pytest.mark.asyncio
    async def test_project_delete_hard(self, adapter):
        """Test hard delete (permanent) of project."""
        adapter.gh_client.execute_graphql.return_value = {
            "deleteProjectV2": {"projectV2": {"id": "PVT_TEST", "number": 1}}
        }

        result = await adapter.project_delete("PVT_TEST", hard_delete=True)

        assert result is True
        # Verify DELETE_PROJECT_MUTATION was used
        call_args = adapter.gh_client.execute_graphql.call_args
        query = call_args[1]["query"]
        assert "deleteProjectV2" in query

    @pytest.mark.asyncio
    async def test_project_delete_not_found(self, adapter):
        """Test deleting project that doesn't exist."""
        adapter.gh_client.execute_graphql.return_value = {
            "updateProjectV2": {"projectV2": None}
        }

        result = await adapter.project_delete("PVT_NONEXISTENT")

        assert result is False

    @pytest.mark.asyncio
    async def test_project_delete_failure(self, adapter):
        """Test project deletion failure."""
        adapter.gh_client.execute_graphql.side_effect = Exception("API error")

        with pytest.raises(RuntimeError, match="Failed to delete project"):
            await adapter.project_delete("PVT_TEST")


class TestProjectListEdgeCases:
    """Additional edge case tests for project_list()."""

    @pytest.mark.asyncio
    async def test_project_list_custom_owner(self, adapter):
        """Test project listing with custom owner."""
        adapter.gh_client.execute_graphql.return_value = {
            "organization": {
                "projectsV2": {"nodes": [], "pageInfo": {"hasNextPage": False}}
            }
        }

        await adapter.project_list(owner="custom-org")

        call_args = adapter.gh_client.execute_graphql.call_args
        assert call_args[1]["variables"]["owner"] == "custom-org"

    @pytest.mark.asyncio
    async def test_project_list_graphql_error(self, adapter):
        """Test project listing with GraphQL error."""
        adapter.gh_client.execute_graphql.side_effect = Exception("GraphQL error")

        with pytest.raises(RuntimeError, match="Failed to list projects"):
            await adapter.project_list()
