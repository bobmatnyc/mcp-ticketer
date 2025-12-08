"""Unit tests for Linear adapter main class."""

from unittest.mock import patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import TicketState


@pytest.mark.unit
class TestLinearAdapterInit:
    """Test Linear adapter initialization."""

    def test_init_with_api_key_and_team_id(self) -> None:
        """Test initialization with API key and team ID."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test_key_12345"
        assert adapter.team_id == "team-123"
        assert adapter.team_key is None
        assert adapter.api_url == "https://api.linear.app/graphql"

    def test_init_with_api_key_and_team_key(self) -> None:
        """Test initialization with API key and team key."""
        config = {"api_key": "lin_api_test_key_12345", "team_key": "TEST"}

        adapter = LinearAdapter(config)

        assert adapter.team_key == "TEST"
        assert adapter.team_id is None

    def test_init_with_bearer_prefix(self) -> None:
        """Test initialization when API key already has Bearer prefix."""
        config = {"api_key": "Bearer lin_api_test_key_12345", "team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test_key_12345"

    @patch.dict("os.environ", {}, clear=True)
    def test_init_missing_api_key(self) -> None:
        """Test initialization without API key."""
        config = {"team_id": "team-123"}

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Linear API key is required" in str(exc_info.value)

    def test_init_missing_team_info(self) -> None:
        """Test initialization without team key or ID."""
        config = {"api_key": "lin_api_test_key_12345"}

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Either team_key or team_id must be provided" in str(exc_info.value)

    @patch.dict("os.environ", {"LINEAR_API_KEY": "lin_api_env_key_12345"})
    def test_init_with_env_api_key(self) -> None:
        """Test initialization with API key from environment."""
        config = {"team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_env_key_12345"

    def test_init_with_custom_api_url(self) -> None:
        """Test initialization with custom API URL."""
        config = {
            "api_key": "lin_api_test_key_12345",
            "team_id": "team-123",
            "api_url": "https://custom.linear.app/graphql",
        }

        adapter = LinearAdapter(config)

        assert adapter.api_url == "https://custom.linear.app/graphql"


@pytest.mark.unit
class TestLinearAdapterValidation:
    """Test Linear adapter validation methods."""

    def test_validate_credentials_success(self) -> None:
        """Test successful credential validation."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        is_valid, error_message = adapter.validate_credentials()

        assert is_valid is True
        assert error_message == ""

    def test_validate_credentials_missing_api_key(self) -> None:
        """Test credential validation with missing API key."""

        # Create adapter with missing API key by bypassing __init__ validation
        adapter = LinearAdapter.__new__(LinearAdapter)
        adapter.api_key = None
        adapter.team_id = "team-123"
        adapter.team_key = None

        is_valid, error_message = adapter.validate_credentials()

        assert is_valid is False
        assert "Linear API key is required" in error_message

    def test_validate_credentials_missing_team_info(self) -> None:
        """Test credential validation with missing team info."""

        # Create adapter with missing team info by bypassing __init__ validation
        adapter = LinearAdapter.__new__(LinearAdapter)
        adapter.api_key = "lin_api_test_key_12345"
        adapter.team_id = None
        adapter.team_key = None

        is_valid, error_message = adapter.validate_credentials()

        assert is_valid is False
        assert "Either team_key or team_id must be provided" in error_message


@pytest.mark.unit
class TestLinearAdapterStateMapping:
    """Test Linear adapter state mapping."""

    def test_get_state_mapping_without_workflow_states(self) -> None:
        """Test state mapping when workflow states are not loaded."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Ensure workflow states are not loaded
        adapter._workflow_states = None

        mapping = adapter._get_state_mapping()

        # Should return type-based mapping
        assert mapping[TicketState.OPEN] == "unstarted"
        assert mapping[TicketState.IN_PROGRESS] == "started"
        assert mapping[TicketState.DONE] == "completed"
        assert mapping[TicketState.CLOSED] == "canceled"

    def test_get_state_mapping_with_workflow_states(self) -> None:
        """Test state mapping when workflow states are loaded."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Mock loaded workflow states
        # _workflow_states is keyed by universal_state.value (e.g., "open")
        # and contains state UUIDs directly (not dict with "id" key)
        adapter._workflow_states = {
            "open": "state-uuid-1",
            "in_progress": "state-uuid-2",
            "done": "state-uuid-3",
            "closed": "state-uuid-4",
            "ready": "state-uuid-5",
            "tested": "state-uuid-6",
            "waiting": "state-uuid-7",
            "blocked": "state-uuid-8",
        }

        mapping = adapter._get_state_mapping()

        # Should return UUID-based mapping
        assert mapping[TicketState.OPEN] == "state-uuid-1"
        assert mapping[TicketState.IN_PROGRESS] == "state-uuid-2"
        assert mapping[TicketState.DONE] == "state-uuid-3"
        assert mapping[TicketState.CLOSED] == "state-uuid-4"
        assert mapping[TicketState.READY] == "state-uuid-5"
        assert mapping[TicketState.TESTED] == "state-uuid-6"
        assert mapping[TicketState.WAITING] == "state-uuid-7"
        assert mapping[TicketState.BLOCKED] == "state-uuid-8"


@pytest.mark.unit
class TestLinearAdapterTeamResolution:
    """Test Linear adapter team resolution."""

    @pytest.mark.asyncio
    async def test_ensure_team_id_with_existing_id(self):
        """Test team ID resolution when ID is already provided."""
        valid_uuid = "12345678-1234-1234-1234-123456789012"
        config = {"api_key": "lin_api_test_key_12345", "team_id": valid_uuid}
        adapter = LinearAdapter(config)

        team_id = await adapter._ensure_team_id()

        assert team_id == valid_uuid

    @pytest.mark.asyncio
    async def test_ensure_team_id_with_team_key(self):
        """Test team ID resolution from team key."""
        config = {"api_key": "lin_api_test_key_12345", "team_key": "TEST"}
        adapter = LinearAdapter(config)

        # Mock the client query
        mock_result = {
            "teams": {
                "nodes": [
                    {
                        "id": "team-456",
                        "name": "Test Team",
                        "key": "TEST",
                        "description": "Test team",
                    }
                ]
            }
        }

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            team_id = await adapter._ensure_team_id()

        assert team_id == "team-456"
        assert adapter.team_id == "team-456"
        assert adapter._team_data["name"] == "Test Team"

    @pytest.mark.asyncio
    async def test_ensure_team_id_team_not_found(self):
        """Test team ID resolution when team is not found."""
        config = {"api_key": "lin_api_test_key_12345", "team_key": "NONEXISTENT"}
        adapter = LinearAdapter(config)

        # Mock empty result
        mock_result = {"teams": {"nodes": []}}

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            with pytest.raises(ValueError) as exc_info:
                await adapter._ensure_team_id()

        assert "Team with key 'NONEXISTENT' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_ensure_team_id_missing_team_key(self):
        """Test team ID resolution without team key or ID."""

        # Create adapter bypassing validation
        adapter = LinearAdapter.__new__(LinearAdapter)
        adapter.team_id = None
        adapter.team_key = None

        with pytest.raises(ValueError) as exc_info:
            await adapter._ensure_team_id()

        assert "Either team_id (UUID) or team_key (short code) must be provided" in str(
            exc_info.value
        )


@pytest.mark.unit
class TestLinearAdapterUserResolution:
    """Test Linear adapter user resolution."""

    @pytest.mark.asyncio
    async def test_get_user_id_by_email(self):
        """Test user ID resolution by email."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        mock_user = {"id": "user-456", "email": "test@example.com", "name": "Test User"}

        with patch.object(adapter.client, "get_user_by_email", return_value=mock_user):
            user_id = await adapter._get_user_id("test@example.com")

        assert user_id == "user-456"

    @pytest.mark.asyncio
    async def test_get_user_id_not_found(self):
        """Test user ID resolution when user is not found."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        with patch.object(adapter.client, "get_user_by_email", return_value=None):
            user_id = await adapter._get_user_id("nonexistent@example.com")

        # Should return the identifier as-is (assuming it's already a user ID)
        assert user_id == "nonexistent@example.com"

    @pytest.mark.asyncio
    async def test_get_user_id_empty_identifier(self):
        """Test user ID resolution with empty identifier."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        user_id = await adapter._get_user_id("")

        assert user_id is None


@pytest.mark.unit
class TestLinearAdapterInitialization:
    """Test Linear adapter initialization process."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful adapter initialization."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Mock client methods
        with patch.object(adapter.client, "test_connection", return_value=True):
            with patch.object(adapter, "_ensure_team_id", return_value="team-123"):
                with patch.object(adapter, "_load_workflow_states"):
                    await adapter.initialize()

        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """Test adapter initialization with connection failure."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        with patch.object(adapter.client, "test_connection", return_value=False):
            with pytest.raises(ValueError) as exc_info:
                await adapter.initialize()

        assert "Failed to connect to Linear API" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self):
        """Test adapter initialization when already initialized."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)
        adapter._initialized = True

        # Should return immediately without doing anything
        await adapter.initialize()

        assert adapter._initialized is True

    @pytest.mark.asyncio
    async def test_load_workflow_states(self):
        """Test workflow states loading."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        mock_result = {
            "team": {
                "states": {
                    "nodes": [
                        {
                            "id": "state-1",
                            "name": "Todo",
                            "type": "unstarted",
                            "position": 1,
                        },
                        {
                            "id": "state-2",
                            "name": "In Progress",
                            "type": "started",
                            "position": 1,
                        },
                        {
                            "id": "state-3",
                            "name": "Done",
                            "type": "completed",
                            "position": 1,
                        },
                    ]
                }
            }
        }

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            await adapter._load_workflow_states("team-123")

        # Verify workflow states were loaded with semantic mapping
        # (Uses universal state names, not Linear type names)
        assert adapter._workflow_states is not None
        assert "open" in adapter._workflow_states  # Maps to "Todo" (unstarted type)
        assert (
            "in_progress" in adapter._workflow_states
        )  # Maps to "In Progress" (started type)
        assert "done" in adapter._workflow_states  # Maps to "Done" (completed type)

        # Verify mapping correctness
        assert adapter._workflow_states["open"] == "state-1"
        assert adapter._workflow_states["in_progress"] == "state-2"
        assert adapter._workflow_states["done"] == "state-3"


@pytest.mark.unit
class TestLinearAdapterRead:
    """Test Linear adapter read operations."""

    @pytest.mark.asyncio
    async def test_read_issue(self):
        """Test reading an issue by identifier."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        mock_issue_data = {
            "issue": {
                "identifier": "BTA-123",
                "title": "Test Issue",
                "description": "Test description",
                "priority": 1,
                "state": {"type": "started"},
                "createdAt": "2024-01-01T00:00:00Z",
                "updatedAt": "2024-01-01T00:00:00Z",
                "team": {"id": "team-123", "name": "Team", "key": "TEAM"},
            }
        }

        with patch.object(
            adapter.client, "execute_query", return_value=mock_issue_data
        ):
            result = await adapter.read("BTA-123")

            assert result is not None
            assert result.id == "BTA-123"
            assert result.title == "Test Issue"

    @pytest.mark.asyncio
    async def test_read_project(self):
        """Test reading a project (epic) by UUID."""
        from mcp_ticketer.core.models import TicketType

        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        project_uuid = "6cf55cfcfad4-test-uuid"

        # Mock execute_query to throw error (issue not found)
        # Then mock get_project to return project data
        from gql.transport.exceptions import TransportQueryError

        with patch.object(
            adapter.client,
            "execute_query",
            side_effect=TransportQueryError("Not found"),
        ):
            with patch.object(adapter, "get_project") as mock_get_project:
                mock_get_project.return_value = {
                    "id": project_uuid,
                    "name": "Test Project",
                    "description": "Test description",
                    "state": "started",
                    "createdAt": "2024-01-01T00:00:00Z",
                    "updatedAt": "2024-01-01T00:00:00Z",
                }

                result = await adapter.read(project_uuid)

                assert result is not None
                assert result.ticket_type == TicketType.EPIC
                assert result.title == "Test Project"
                mock_get_project.assert_called_once_with(project_uuid)

    @pytest.mark.asyncio
    async def test_read_not_found(self):
        """Test reading a non-existent ticket."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        from gql.transport.exceptions import TransportQueryError

        # Mock both issue and project lookups to fail
        with patch.object(
            adapter.client,
            "execute_query",
            side_effect=TransportQueryError("Not found"),
        ):
            with patch.object(
                adapter, "get_project", side_effect=Exception("Not found")
            ):
                result = await adapter.read("NOTFOUND-123")

                assert result is None


@pytest.mark.unit
class TestLinearAdapterFieldValidation:
    """Test Linear adapter field validation."""

    @pytest.mark.asyncio
    async def test_update_epic_validates_description_length(self):
        """Test that update_epic validates description length."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Mock _resolve_project_id to return a valid UUID
        project_uuid = "12345678-1234-1234-1234-123456789012"
        with patch.object(adapter, "_resolve_project_id", return_value=project_uuid):
            # Try to update with oversized description (>255 chars)
            long_description = "x" * 300

            with pytest.raises(ValueError, match="255 characters"):
                await adapter.update_epic(
                    "test-project", {"description": long_description}
                )

    @pytest.mark.asyncio
    async def test_update_epic_validates_title_length(self):
        """Test that update_epic validates title length."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Mock _resolve_project_id to return a valid UUID
        project_uuid = "12345678-1234-1234-1234-123456789012"
        with patch.object(adapter, "_resolve_project_id", return_value=project_uuid):
            # Try to update with oversized title (>255 chars)
            long_title = "y" * 300

            with pytest.raises(ValueError, match="255 characters"):
                await adapter.update_epic("test-project", {"title": long_title})
