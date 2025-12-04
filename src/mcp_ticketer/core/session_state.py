"""Session state management for tracking current ticket associations."""

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Session timeout: 30 minutes of inactivity
SESSION_TIMEOUT_MINUTES = 30
SESSION_STATE_FILE = ".mcp-ticketer/session.json"


@dataclass
class SessionState:
    """Track session-specific state for ticket associations."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    current_ticket: str | None = None  # Current ticket ID
    ticket_opted_out: bool = False  # User explicitly chose "none"
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "session_id": self.session_id,
            "current_ticket": self.current_ticket,
            "ticket_opted_out": self.ticket_opted_out,
            "last_activity": self.last_activity,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        """Deserialize from dictionary."""
        return cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            current_ticket=data.get("current_ticket"),
            ticket_opted_out=data.get("ticket_opted_out", False),
            last_activity=data.get("last_activity", datetime.now().isoformat()),
        )

    def is_expired(self) -> bool:
        """Check if session has expired due to inactivity."""
        try:
            last_activity = datetime.fromisoformat(self.last_activity)
            timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            return datetime.now() - last_activity > timeout
        except (ValueError, TypeError):
            # Invalid timestamp, consider expired
            return True

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now().isoformat()


class SessionStateManager:
    """Manage session state persistence and lifecycle."""

    def __init__(self, project_path: Path | None = None):
        """Initialize session state manager.

        Args:
            project_path: Project root directory (defaults to current directory)

        """
        self.project_path = project_path or Path.cwd()
        self.state_file = self.project_path / SESSION_STATE_FILE

    def load_session(self) -> SessionState:
        """Load session state from file.

        Automatically updates last_activity timestamp on every load to prevent
        session expiration during active use.

        Returns:
            SessionState instance (creates new if expired or not found)

        """
        if not self.state_file.exists():
            logger.debug("No session state file found, creating new session")
            return SessionState()

        try:
            with open(self.state_file) as f:
                data = json.load(f)

            state = SessionState.from_dict(data)

            # Check if session expired
            if state.is_expired():
                logger.info(
                    f"Session {state.session_id} expired after "
                    f"{SESSION_TIMEOUT_MINUTES} minutes, creating new session"
                )
                return SessionState()

            # Auto-renew: Update last_activity and persist on every load
            state.touch()
            self.save_session(state)

            return state

        except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
            logger.warning(f"Failed to load session state: {e}, creating new session")
            return SessionState()

    def save_session(self, state: SessionState) -> None:
        """Save session state to file.

        Args:
            state: SessionState to persist

        """
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Touch before saving
            state.touch()

            # Write state
            with open(self.state_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2)

            logger.debug(f"Saved session state: session_id={state.session_id}")

        except Exception as e:
            logger.error(f"Failed to save session state: {e}")

    def clear_session(self) -> None:
        """Clear session state (delete file)."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
                logger.info("Session state cleared")
        except Exception as e:
            logger.error(f"Failed to clear session state: {e}")

    def get_current_ticket(self) -> str | None:
        """Get current ticket for this session (convenience method).

        Returns:
            Current ticket ID or None

        """
        state = self.load_session()

        # If user opted out, return None
        if state.ticket_opted_out:
            return None

        return state.current_ticket

    def set_current_ticket(self, ticket_id: str | None) -> None:
        """Set current ticket for this session (convenience method).

        Args:
            ticket_id: Ticket ID to set (None to clear)

        """
        state = self.load_session()
        state.current_ticket = ticket_id
        state.ticket_opted_out = False  # Clear opt-out when setting ticket
        self.save_session(state)

    def opt_out_ticket(self) -> None:
        """Mark that user doesn't want to associate work with a ticket (convenience method)."""
        state = self.load_session()
        state.current_ticket = None
        state.ticket_opted_out = True
        self.save_session(state)
