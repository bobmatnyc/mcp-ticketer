"""Unit tests for Linear adapter main class."""

from unittest.mock import patch

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter
from mcp_ticketer.core.models import TicketState


@pytest.mark.unit
class TestLinearAdapterInit:
    """Test Linear adapter initialization."""

    def test_init_with_api_key_and_team_id(self):
        """Test initialization with API key and team ID."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test_key_12345"
        assert adapter.team_id == "team-123"
        assert adapter.team_key is None
        assert adapter.api_url == "https://api.linear.app/graphql"

    def test_init_with_api_key_and_team_key(self):
        """Test initialization with API key and team key."""
        config = {"api_key": "lin_api_test_key_12345", "team_key": "TEST"}

        adapter = LinearAdapter(config)

        assert adapter.team_key == "TEST"
        assert adapter.team_id is None

    def test_init_with_bearer_prefix(self):
        """Test initialization when API key already has Bearer prefix."""
        config = {"api_key": "Bearer lin_api_test_key_12345", "team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_test_key_12345"

    @patch.dict("os.environ", {}, clear=True)
    def test_init_missing_api_key(self):
        """Test initialization without API key."""
        config = {"team_id": "team-123"}

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Linear API key is required" in str(exc_info.value)

    def test_init_missing_team_info(self):
        """Test initialization without team key or ID."""
        config = {"api_key": "lin_api_test_key_12345"}

        with pytest.raises(ValueError) as exc_info:
            LinearAdapter(config)

        assert "Either team_key or team_id must be provided" in str(exc_info.value)

    @patch.dict("os.environ", {"LINEAR_API_KEY": "lin_api_env_key_12345"})
    def test_init_with_env_api_key(self):
        """Test initialization with API key from environment."""
        config = {"team_id": "team-123"}

        adapter = LinearAdapter(config)

        assert adapter.api_key == "lin_api_env_key_12345"

    def test_init_with_custom_api_url(self):
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

    def test_validate_credentials_success(self):
        """Test successful credential validation."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        is_valid, error_message = adapter.validate_credentials()

        assert is_valid is True
        assert error_message == ""

    def test_validate_credentials_missing_api_key(self):
        """Test credential validation with missing API key."""

        # Create adapter with missing API key by bypassing __init__ validation
        adapter = LinearAdapter.__new__(LinearAdapter)
        adapter.api_key = None
        adapter.team_id = "team-123"
        adapter.team_key = None

        is_valid, error_message = adapter.validate_credentials()

        assert is_valid is False
        assert "Linear API key is required" in error_message

    def test_validate_credentials_missing_team_info(self):
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

    def test_get_state_mapping_without_workflow_states(self):
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

    def test_get_state_mapping_with_workflow_states(self):
        """Test state mapping when workflow states are loaded."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        # Mock loaded workflow states
        adapter._workflow_states = {
            "unstarted": {"id": "state-1", "name": "To Do"},
            "started": {"id": "state-2", "name": "In Progress"},
            "completed": {"id": "state-3", "name": "Done"},
            "canceled": {"id": "state-4", "name": "Canceled"},
        }

        mapping = adapter._get_state_mapping()

        # Should return ID-based mapping
        assert mapping[TicketState.OPEN] == "state-1"
        assert mapping[TicketState.IN_PROGRESS] == "state-2"
        assert mapping[TicketState.DONE] == "state-3"
        assert mapping[TicketState.CLOSED] == "state-4"


@pytest.mark.unit
class TestLinearAdapterTeamResolution:
    """Test Linear adapter team resolution."""

    @pytest.mark.asyncio
    async def test_ensure_team_id_with_existing_id(self):
        """Test team ID resolution when ID is already provided."""
        config = {"api_key": "lin_api_test_key_12345", "team_id": "team-123"}
        adapter = LinearAdapter(config)

        team_id = await adapter._ensure_team_id()

        assert team_id == "team-123"

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

        assert "Either team_id or team_key must be provided" in str(exc_info.value)


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
                        {"id": "state-1", "type": "unstarted", "position": 1},
                        {"id": "state-2", "type": "started", "position": 1},
                        {"id": "state-3", "type": "completed", "position": 1},
                    ]
                }
            }
        }

        with patch.object(adapter.client, "execute_query", return_value=mock_result):
            await adapter._load_workflow_states("team-123")

        assert adapter._workflow_states is not None
        assert "unstarted" in adapter._workflow_states
        assert "started" in adapter._workflow_states
        assert "completed" in adapter._workflow_states
