"""Exception classes for MCP Ticketer.

Error Severity Classification:
    CRITICAL - System-level issues (auth, config, network) → Always suggest diagnostics
    MEDIUM - Resource issues (not found, permissions) → Suggest diagnostics
    LOW - User input errors (validation, state transitions) → No diagnostics
"""

from __future__ import annotations

from typing import Any

from .models import TicketState


class MCPTicketerError(Exception):
    """Base exception for MCP Ticketer."""

    pass


class AdapterError(MCPTicketerError):
    """Base adapter error."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        original_error: Exception | None = None,
    ):
        """Initialize adapter error.

        Args:
            message: Error message
            adapter_name: Name of the adapter that raised the error
            original_error: Original exception that caused this error

        """
        super().__init__(message)
        self.adapter_name = adapter_name
        self.original_error = original_error

    def __str__(self) -> str:
        """Return string representation of the error."""
        base_msg = f"[{self.adapter_name}] {super().__str__()}"
        if self.original_error:
            base_msg += f" (caused by: {self.original_error})"
        return base_msg


class AuthenticationError(AdapterError):
    """Authentication failed with external service."""

    pass


class RateLimitError(AdapterError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str,
        adapter_name: str,
        retry_after: int | None = None,
        original_error: Exception | None = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            adapter_name: Name of the adapter
            retry_after: Seconds to wait before retrying
            original_error: Original exception

        """
        super().__init__(message, adapter_name, original_error)
        self.retry_after = retry_after


class ValidationError(MCPTicketerError):
    """Data validation error."""

    def __init__(self, message: str, field: str | None = None, value: Any = None):
        """Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            value: Value that failed validation

        """
        super().__init__(message)
        self.field = field
        self.value = value

    def __str__(self) -> str:
        """Return string representation of the error."""
        base_msg = super().__str__()
        if self.field:
            base_msg += f" (field: {self.field})"
        if self.value is not None:
            base_msg += f" (value: {self.value})"
        return base_msg


class ConfigurationError(MCPTicketerError):
    """Configuration error."""

    pass


class CacheError(MCPTicketerError):
    """Cache operation error."""

    pass


class StateTransitionError(MCPTicketerError):
    """Invalid state transition."""

    def __init__(self, message: str, from_state: TicketState, to_state: TicketState):
        """Initialize state transition error.

        Args:
            message: Error message
            from_state: Current state
            to_state: Target state

        """
        super().__init__(message)
        self.from_state = from_state
        self.to_state = to_state

    def __str__(self) -> str:
        """Return string representation of the error."""
        return f"{super().__str__()} ({self.from_state} -> {self.to_state})"


class NetworkError(AdapterError):
    """Network-related error."""

    pass


class TimeoutError(AdapterError):
    """Request timeout error."""

    pass


class NotFoundError(AdapterError):
    """Resource not found error."""

    pass


class PermissionError(AdapterError):
    """Permission denied error."""

    pass
