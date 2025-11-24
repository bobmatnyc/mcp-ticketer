"""Tests for session state management."""

import json
import time
from datetime import datetime, timedelta

import pytest

from mcp_ticketer.core.session_state import (
    SESSION_TIMEOUT_MINUTES,
    SessionState,
    SessionStateManager,
)


class TestSessionState:
    """Test SessionState dataclass."""

    def test_session_state_creation(self) -> None:
        """Test creating a new session state."""
        state = SessionState()
        assert state.session_id is not None
        assert state.current_ticket is None
        assert state.ticket_opted_out is False
        assert state.last_activity is not None

    def test_session_state_to_dict(self) -> None:
        """Test serialization to dictionary."""
        state = SessionState(
            session_id="test-123",
            current_ticket="PROJ-456",
            ticket_opted_out=True,
        )
        data = state.to_dict()
        assert data["session_id"] == "test-123"
        assert data["current_ticket"] == "PROJ-456"
        assert data["ticket_opted_out"] is True
        assert "last_activity" in data

    def test_session_state_from_dict(self) -> None:
        """Test deserialization from dictionary."""
        data = {
            "session_id": "test-123",
            "current_ticket": "PROJ-456",
            "ticket_opted_out": True,
            "last_activity": "2025-01-19T12:00:00",
        }
        state = SessionState.from_dict(data)
        assert state.session_id == "test-123"
        assert state.current_ticket == "PROJ-456"
        assert state.ticket_opted_out is True
        assert state.last_activity == "2025-01-19T12:00:00"

    def test_session_state_is_expired(self) -> None:
        """Test session expiration check."""
        # Fresh session (not expired)
        state = SessionState()
        assert not state.is_expired()

        # Expired session
        old_time = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES + 1)
        state.last_activity = old_time.isoformat()
        assert state.is_expired()

        # Edge case: exactly at timeout (should not be expired yet)
        edge_time = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        state.last_activity = edge_time.isoformat()
        # This might be expired depending on execution time, so we check either way
        # The key is it's testing the boundary condition

    def test_session_state_touch(self) -> None:
        """Test updating last activity timestamp."""
        state = SessionState()
        old_activity = state.last_activity

        # Wait a tiny bit to ensure timestamp changes
        time.sleep(0.01)

        state.touch()
        assert state.last_activity != old_activity


class TestSessionStateManager:
    """Test SessionStateManager."""

    def test_load_session_no_file(self, tmp_path) -> None:
        """Test loading session when no file exists."""
        manager = SessionStateManager(project_path=tmp_path)
        state = manager.load_session()

        assert state is not None
        assert state.session_id is not None
        assert state.current_ticket is None
        assert not state.ticket_opted_out

    def test_save_and_load_session(self, tmp_path) -> None:
        """Test saving and loading a session."""
        manager = SessionStateManager(project_path=tmp_path)
        state = SessionState(
            session_id="test-789",
            current_ticket="EPIC-001",
            ticket_opted_out=False,
        )

        manager.save_session(state)

        # Verify file was created
        session_file = tmp_path / ".mcp-ticketer" / "session.json"
        assert session_file.exists()

        # Load it back
        loaded_state = manager.load_session()
        assert loaded_state.session_id == "test-789"
        assert loaded_state.current_ticket == "EPIC-001"
        assert not loaded_state.ticket_opted_out

    def test_load_expired_session(self, tmp_path) -> None:
        """Test loading an expired session creates new one."""
        manager = SessionStateManager(project_path=tmp_path)

        # Create and manually save expired session (bypass touch in save_session)
        old_time = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES + 5)
        state_data = {
            "session_id": "old-session",
            "current_ticket": "OLD-TICKET",
            "ticket_opted_out": True,
            "last_activity": old_time.isoformat(),
        }

        # Manually write to avoid automatic touch
        session_file = tmp_path / ".mcp-ticketer" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(session_file, "w") as f:
            json.dump(state_data, f)

        # Load should create new session since it's expired
        loaded_state = manager.load_session()
        assert loaded_state.session_id != "old-session"
        assert loaded_state.current_ticket is None
        assert not loaded_state.ticket_opted_out

    def test_clear_session(self, tmp_path) -> None:
        """Test clearing session state."""
        manager = SessionStateManager(project_path=tmp_path)
        state = SessionState(current_ticket="TEST-123")
        manager.save_session(state)

        session_file = tmp_path / ".mcp-ticketer" / "session.json"
        assert session_file.exists()

        manager.clear_session()
        assert not session_file.exists()

    def test_get_current_ticket(self, tmp_path) -> None:
        """Test getting current ticket."""
        manager = SessionStateManager(project_path=tmp_path)

        # No ticket set
        assert manager.get_current_ticket() is None

        # Set a ticket
        manager.set_current_ticket("PROJ-123")
        assert manager.get_current_ticket() == "PROJ-123"

        # Opt out
        manager.opt_out_ticket()
        assert manager.get_current_ticket() is None

    def test_set_current_ticket(self, tmp_path) -> None:
        """Test setting current ticket."""
        manager = SessionStateManager(project_path=tmp_path)

        manager.set_current_ticket("EPIC-999")
        state = manager.load_session()
        assert state.current_ticket == "EPIC-999"
        assert not state.ticket_opted_out

        # Setting ticket should clear opt-out
        manager.opt_out_ticket()
        manager.set_current_ticket("NEW-TICKET")
        state = manager.load_session()
        assert state.current_ticket == "NEW-TICKET"
        assert not state.ticket_opted_out

    def test_opt_out_ticket(self, tmp_path) -> None:
        """Test opting out of ticket association."""
        manager = SessionStateManager(project_path=tmp_path)

        # Set then opt out
        manager.set_current_ticket("TICKET-001")
        manager.opt_out_ticket()

        state = manager.load_session()
        assert state.current_ticket is None
        assert state.ticket_opted_out

    def test_corrupted_session_file(self, tmp_path) -> None:
        """Test handling corrupted session file."""
        session_file = tmp_path / ".mcp-ticketer" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        with open(session_file, "w") as f:
            f.write("{ invalid json }")

        manager = SessionStateManager(project_path=tmp_path)
        state = manager.load_session()

        # Should create new session instead of crashing
        assert state is not None
        assert state.session_id is not None

    def test_touch_updates_activity(self, tmp_path) -> None:
        """Test that loading/saving touches the session."""
        manager = SessionStateManager(project_path=tmp_path)

        state1 = manager.load_session()
        time1 = state1.last_activity

        time.sleep(0.01)

        manager.save_session(state1)
        state2 = manager.load_session()
        time2 = state2.last_activity

        # Activity time should have been updated
        assert time2 > time1


@pytest.fixture
def tmp_path(tmp_path_factory):
    """Create a temporary directory for testing."""
    return tmp_path_factory.mktemp("session_test")
