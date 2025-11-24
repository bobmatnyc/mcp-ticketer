"""Tests for Linear project-team association functionality."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.fixture
def adapter() -> None:
    """Create LinearAdapter instance with mocked client."""
    config = {
        "api_key": "lin_api_test_key_12345",
        "team_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",  # Valid UUID format
    }
    adapter = LinearAdapter(config)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock()
    adapter.client.execute_mutation = AsyncMock()
    adapter.client.test_connection = AsyncMock(return_value=True)
    adapter._initialized = True
    return adapter


@pytest.mark.asyncio
@pytest.mark.unit
class TestProjectTeamAssociation:
    """Test project-team association validation and management."""

    async def test_validate_project_team_association_valid(self, adapter):
        """Test validation when team is already in project."""
        # Mock get_project to return project with teams
        adapter.get_project = AsyncMock(
            return_value={
                "id": "project-123",
                "teams": {
                    "nodes": [
                        {
                            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "name": "Team A",
                        },
                        {"id": "team-456", "name": "Team B"},
                    ]
                },
            }
        )

        is_valid, team_ids = await adapter._validate_project_team_association(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert is_valid is True
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" in team_ids
        assert "team-456" in team_ids

    async def test_validate_project_team_association_invalid(self, adapter):
        """Test validation when team is NOT in project."""
        adapter.get_project = AsyncMock(
            return_value={
                "id": "project-123",
                "teams": {"nodes": [{"id": "team-456", "name": "Team B"}]},
            }
        )

        is_valid, team_ids = await adapter._validate_project_team_association(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert is_valid is False
        assert "a1b2c3d4-e5f6-7890-abcd-ef1234567890" not in team_ids
        assert "team-456" in team_ids

    async def test_validate_project_team_association_project_not_found(self, adapter):
        """Test validation when project doesn't exist."""
        adapter.get_project = AsyncMock(return_value=None)

        is_valid, team_ids = await adapter._validate_project_team_association(
            "nonexistent-project", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert is_valid is False
        assert team_ids == []

    async def test_ensure_team_in_project_already_associated(self, adapter):
        """Test when team is already in project (no update needed)."""
        adapter._validate_project_team_association = AsyncMock(
            return_value=(True, ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
        )

        result = await adapter._ensure_team_in_project(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert result is True
        # Should not call execute_mutation since already associated
        adapter.client.execute_mutation.assert_not_called()

    async def test_ensure_team_in_project_adds_team_successfully(self, adapter):
        """Test adding team to project successfully."""
        adapter._validate_project_team_association = AsyncMock(
            return_value=(False, ["team-456"])
        )
        adapter.client.execute_mutation = AsyncMock(
            return_value={
                "projectUpdate": {"success": True, "project": {"id": "project-123"}}
            }
        )

        result = await adapter._ensure_team_in_project(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert result is True
        adapter.client.execute_mutation.assert_called_once()

        # Verify mutation includes both existing and new team
        call_args = adapter.client.execute_mutation.call_args
        assert call_args[0][1]["input"]["teamIds"] == [
            "team-456",
            "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        ]

    async def test_ensure_team_in_project_fails(self, adapter):
        """Test when adding team to project fails."""
        adapter._validate_project_team_association = AsyncMock(
            return_value=(False, ["team-456"])
        )
        adapter.client.execute_mutation = AsyncMock(
            return_value={"projectUpdate": {"success": False}}
        )

        result = await adapter._ensure_team_in_project(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert result is False

    async def test_ensure_team_in_project_api_error(self, adapter):
        """Test when API call raises exception."""
        adapter._validate_project_team_association = AsyncMock(
            return_value=(False, ["team-456"])
        )
        adapter.client.execute_mutation = AsyncMock(side_effect=Exception("API error"))

        result = await adapter._ensure_team_in_project(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        assert result is False

    async def test_create_task_with_project_association_valid(self, adapter):
        """Test issue creation when team is already in project."""
        from mcp_ticketer.core.models import Priority, Task, TicketState

        task = Task(
            title="Test Issue",
            description="Test description",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            parent_epic="project-slug",
        )

        adapter._resolve_project_id = AsyncMock(return_value="project-123")
        adapter._validate_project_team_association = AsyncMock(
            return_value=(True, ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
        )
        adapter.client.execute_mutation = AsyncMock(
            return_value={
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "PROJ-1",
                        "title": "Test Issue",
                    },
                }
            }
        )

        result = await adapter.create(task)

        assert result is not None

        # Verify projectId was included in mutation
        call_args = adapter.client.execute_mutation.call_args
        assert call_args[0][1]["input"]["projectId"] == "project-123"

    async def test_create_task_with_project_association_requires_update(self, adapter):
        """Test issue creation when team needs to be added to project."""
        from mcp_ticketer.core.models import Priority, Task, TicketState

        task = Task(
            title="Test Issue",
            description="Test description",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            parent_epic="project-slug",
        )

        adapter._resolve_project_id = AsyncMock(return_value="project-123")
        adapter._validate_project_team_association = AsyncMock(
            return_value=(False, ["team-456"])
        )
        adapter._ensure_team_in_project = AsyncMock(return_value=True)
        adapter.client.execute_mutation = AsyncMock(
            return_value={
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "PROJ-1",
                        "title": "Test Issue",
                    },
                }
            }
        )

        result = await adapter.create(task)

        assert result is not None

        # Verify _ensure_team_in_project was called
        adapter._ensure_team_in_project.assert_called_once_with(
            "project-123", "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        )

        # Verify projectId was included in mutation
        call_args = adapter.client.execute_mutation.call_args
        assert call_args[0][1]["input"]["projectId"] == "project-123"

    async def test_create_task_project_association_fails(self, adapter):
        """Test issue creation when team cannot be added to project."""
        from mcp_ticketer.core.models import Priority, Task, TicketState

        task = Task(
            title="Test Issue",
            description="Test description",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            parent_epic="project-slug",
        )

        adapter._resolve_project_id = AsyncMock(return_value="project-123")
        adapter._validate_project_team_association = AsyncMock(
            return_value=(False, ["team-456"])
        )
        adapter._ensure_team_in_project = AsyncMock(return_value=False)
        adapter.client.execute_mutation = AsyncMock(
            return_value={
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-123",
                        "identifier": "PROJ-1",
                        "title": "Test Issue",
                    },
                }
            }
        )

        result = await adapter.create(task)

        assert result is not None

        # Verify _ensure_team_in_project was called
        adapter._ensure_team_in_project.assert_called_once()

        # Verify projectId was NOT included in mutation (falls back to no project)
        call_args = adapter.client.execute_mutation.call_args
        assert "projectId" not in call_args[0][1]["input"]
