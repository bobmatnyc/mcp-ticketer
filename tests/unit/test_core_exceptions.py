"""Unit tests for core exceptions module."""

import pytest

from mcp_ticketer.core.exceptions import (
    AdapterError,
    AuthenticationError,
    CacheError,
    ConfigurationError,
    MCPTicketerError,
    NetworkError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    StateTransitionError,
    TimeoutError,
    ValidationError,
)
from mcp_ticketer.core.models import TicketState


@pytest.mark.unit
class TestMCPTicketerError:
    """Test base MCPTicketerError exception."""

    def test_create_base_error(self) -> None:
        """Test creating the base error."""
        error = MCPTicketerError("Test error")

        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_raise_base_error(self) -> None:
        """Test raising the base error."""
        with pytest.raises(MCPTicketerError) as exc_info:
            raise MCPTicketerError("Test error")

        assert str(exc_info.value) == "Test error"


@pytest.mark.unit
class TestAdapterError:
    """Test AdapterError exception."""

    def test_create_adapter_error(self) -> None:
        """Test creating adapter error with minimal args."""
        error = AdapterError("Connection failed", "linear")

        assert error.adapter_name == "linear"
        assert error.original_error is None
        assert "[linear]" in str(error)
        assert "Connection failed" in str(error)

    def test_adapter_error_with_original_error(self) -> None:
        """Test adapter error with original exception."""
        original = ValueError("Invalid API key")
        error = AdapterError("Auth failed", "jira", original)

        assert error.adapter_name == "jira"
        assert error.original_error is original
        assert "[jira]" in str(error)
        assert "Auth failed" in str(error)
        assert "caused by:" in str(error)
        assert "Invalid API key" in str(error)

    def test_adapter_error_inheritance(self) -> None:
        """Test that AdapterError inherits from MCPTicketerError."""
        error = AdapterError("Test", "test_adapter")

        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)
        assert isinstance(error, Exception)

    def test_raise_adapter_error(self) -> None:
        """Test raising adapter error."""
        with pytest.raises(AdapterError) as exc_info:
            raise AdapterError("Test error", "test_adapter")

        assert exc_info.value.adapter_name == "test_adapter"


@pytest.mark.unit
class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_create_authentication_error(self) -> None:
        """Test creating authentication error."""
        error = AuthenticationError("Invalid credentials", "github")

        assert error.adapter_name == "github"
        assert "[github]" in str(error)
        assert "Invalid credentials" in str(error)

    def test_authentication_error_inheritance(self) -> None:
        """Test that AuthenticationError inherits from AdapterError."""
        error = AuthenticationError("Auth failed", "linear")

        assert isinstance(error, AuthenticationError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_authentication_error(self) -> None:
        """Test raising authentication error."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Unauthorized", "jira")

        assert exc_info.value.adapter_name == "jira"


@pytest.mark.unit
class TestRateLimitError:
    """Test RateLimitError exception."""

    def test_create_rate_limit_error_without_retry_after(self) -> None:
        """Test creating rate limit error without retry_after."""
        error = RateLimitError("Rate limit exceeded", "github")

        assert error.adapter_name == "github"
        assert error.retry_after is None
        assert "[github]" in str(error)
        assert "Rate limit exceeded" in str(error)

    def test_create_rate_limit_error_with_retry_after(self) -> None:
        """Test creating rate limit error with retry_after."""
        error = RateLimitError("Too many requests", "linear", retry_after=60)

        assert error.adapter_name == "linear"
        assert error.retry_after == 60
        assert "[linear]" in str(error)
        assert "Too many requests" in str(error)

    def test_rate_limit_error_with_original_error(self) -> None:
        """Test rate limit error with original exception."""
        original = ConnectionError("HTTP 429")
        error = RateLimitError(
            "Rate limited", "jira", retry_after=30, original_error=original
        )

        assert error.adapter_name == "jira"
        assert error.retry_after == 30
        assert error.original_error is original
        assert "caused by:" in str(error)
        assert "HTTP 429" in str(error)

    def test_rate_limit_error_inheritance(self) -> None:
        """Test that RateLimitError inherits from AdapterError."""
        error = RateLimitError("Rate limit", "test", retry_after=10)

        assert isinstance(error, RateLimitError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_rate_limit_error(self) -> None:
        """Test raising rate limit error."""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("Too fast", "test", retry_after=120)

        assert exc_info.value.retry_after == 120


@pytest.mark.unit
class TestValidationError:
    """Test ValidationError exception."""

    def test_create_validation_error_minimal(self) -> None:
        """Test creating validation error with only message."""
        error = ValidationError("Invalid data")

        assert str(error) == "Invalid data"
        assert error.field is None
        assert error.value is None

    def test_create_validation_error_with_field(self) -> None:
        """Test creating validation error with field."""
        error = ValidationError("Field is required", field="title")

        assert error.field == "title"
        assert error.value is None
        assert "Field is required" in str(error)
        assert "(field: title)" in str(error)

    def test_create_validation_error_with_field_and_value(self) -> None:
        """Test creating validation error with field and value."""
        error = ValidationError("Invalid priority", field="priority", value="invalid")

        assert error.field == "priority"
        assert error.value == "invalid"
        assert "Invalid priority" in str(error)
        assert "(field: priority)" in str(error)
        assert "(value: invalid)" in str(error)

    def test_validation_error_with_none_value(self) -> None:
        """Test validation error where value is explicitly None."""
        error = ValidationError("Required field", field="description", value=None)

        # value=None should not appear in string (only if not None)
        error_str = str(error)
        assert "Required field" in error_str
        assert "(field: description)" in error_str
        # Should not include value when it's None
        assert "(value: None)" not in error_str

    def test_validation_error_inheritance(self) -> None:
        """Test that ValidationError inherits from MCPTicketerError."""
        error = ValidationError("Validation failed", field="test")

        assert isinstance(error, ValidationError)
        assert isinstance(error, MCPTicketerError)
        assert isinstance(error, Exception)

    def test_raise_validation_error(self) -> None:
        """Test raising validation error."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid", field="state", value="bad_state")

        assert exc_info.value.field == "state"
        assert exc_info.value.value == "bad_state"


@pytest.mark.unit
class TestConfigurationError:
    """Test ConfigurationError exception."""

    def test_create_configuration_error(self) -> None:
        """Test creating configuration error."""
        error = ConfigurationError("Missing API key")

        assert str(error) == "Missing API key"

    def test_configuration_error_inheritance(self) -> None:
        """Test that ConfigurationError inherits from MCPTicketerError."""
        error = ConfigurationError("Config error")

        assert isinstance(error, ConfigurationError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_configuration_error(self) -> None:
        """Test raising configuration error."""
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Invalid config")

        assert "Invalid config" in str(exc_info.value)


@pytest.mark.unit
class TestCacheError:
    """Test CacheError exception."""

    def test_create_cache_error(self) -> None:
        """Test creating cache error."""
        error = CacheError("Cache write failed")

        assert str(error) == "Cache write failed"

    def test_cache_error_inheritance(self) -> None:
        """Test that CacheError inherits from MCPTicketerError."""
        error = CacheError("Cache error")

        assert isinstance(error, CacheError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_cache_error(self) -> None:
        """Test raising cache error."""
        with pytest.raises(CacheError) as exc_info:
            raise CacheError("Cache corrupted")

        assert "Cache corrupted" in str(exc_info.value)


@pytest.mark.unit
class TestStateTransitionError:
    """Test StateTransitionError exception."""

    def test_create_state_transition_error(self) -> None:
        """Test creating state transition error."""
        error = StateTransitionError(
            "Invalid transition", from_state=TicketState.OPEN, to_state=TicketState.DONE
        )

        assert error.from_state == TicketState.OPEN
        assert error.to_state == TicketState.DONE
        assert "Invalid transition" in str(error)
        assert "OPEN" in str(error)
        assert "DONE" in str(error)
        assert "->" in str(error)

    def test_state_transition_error_string_representation(self) -> None:
        """Test state transition error string representation."""
        error = StateTransitionError(
            "Cannot transition",
            from_state=TicketState.CLOSED,
            to_state=TicketState.IN_PROGRESS,
        )

        error_str = str(error)
        assert "Cannot transition" in error_str
        assert "CLOSED" in error_str
        assert "IN_PROGRESS" in error_str
        assert "->" in error_str

    def test_state_transition_error_inheritance(self) -> None:
        """Test that StateTransitionError inherits from MCPTicketerError."""
        error = StateTransitionError(
            "Transition error", from_state=TicketState.OPEN, to_state=TicketState.CLOSED
        )

        assert isinstance(error, StateTransitionError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_state_transition_error(self) -> None:
        """Test raising state transition error."""
        with pytest.raises(StateTransitionError) as exc_info:
            raise StateTransitionError(
                "Bad transition",
                from_state=TicketState.READY,
                to_state=TicketState.OPEN,
            )

        assert exc_info.value.from_state == TicketState.READY
        assert exc_info.value.to_state == TicketState.OPEN


@pytest.mark.unit
class TestNetworkError:
    """Test NetworkError exception."""

    def test_create_network_error(self) -> None:
        """Test creating network error."""
        error = NetworkError("Connection timeout", "github")

        assert error.adapter_name == "github"
        assert "[github]" in str(error)
        assert "Connection timeout" in str(error)

    def test_network_error_inheritance(self) -> None:
        """Test that NetworkError inherits from AdapterError."""
        error = NetworkError("Network error", "linear")

        assert isinstance(error, NetworkError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_network_error(self) -> None:
        """Test raising network error."""
        with pytest.raises(NetworkError) as exc_info:
            raise NetworkError("DNS failed", "jira")

        assert exc_info.value.adapter_name == "jira"


@pytest.mark.unit
class TestTimeoutError:
    """Test TimeoutError exception."""

    def test_create_timeout_error(self) -> None:
        """Test creating timeout error."""
        error = TimeoutError("Request timed out", "linear")

        assert error.adapter_name == "linear"
        assert "[linear]" in str(error)
        assert "Request timed out" in str(error)

    def test_timeout_error_inheritance(self) -> None:
        """Test that TimeoutError inherits from AdapterError."""
        error = TimeoutError("Timeout", "github")

        assert isinstance(error, TimeoutError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_timeout_error(self) -> None:
        """Test raising timeout error."""
        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("Too slow", "test")

        assert exc_info.value.adapter_name == "test"


@pytest.mark.unit
class TestNotFoundError:
    """Test NotFoundError exception."""

    def test_create_not_found_error(self) -> None:
        """Test creating not found error."""
        error = NotFoundError("Ticket not found", "jira")

        assert error.adapter_name == "jira"
        assert "[jira]" in str(error)
        assert "Ticket not found" in str(error)

    def test_not_found_error_inheritance(self) -> None:
        """Test that NotFoundError inherits from AdapterError."""
        error = NotFoundError("Not found", "linear")

        assert isinstance(error, NotFoundError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_not_found_error(self) -> None:
        """Test raising not found error."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Missing resource", "github")

        assert exc_info.value.adapter_name == "github"


@pytest.mark.unit
class TestPermissionError:
    """Test PermissionError exception."""

    def test_create_permission_error(self) -> None:
        """Test creating permission error."""
        error = PermissionError("Access denied", "linear")

        assert error.adapter_name == "linear"
        assert "[linear]" in str(error)
        assert "Access denied" in str(error)

    def test_permission_error_inheritance(self) -> None:
        """Test that PermissionError inherits from AdapterError."""
        error = PermissionError("Forbidden", "jira")

        assert isinstance(error, PermissionError)
        assert isinstance(error, AdapterError)
        assert isinstance(error, MCPTicketerError)

    def test_raise_permission_error(self) -> None:
        """Test raising permission error."""
        with pytest.raises(PermissionError) as exc_info:
            raise PermissionError("No access", "github")

        assert exc_info.value.adapter_name == "github"


@pytest.mark.unit
class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_adapter_errors_inherit_from_adapter_error(self) -> None:
        """Test that all adapter-specific errors inherit from AdapterError."""
        adapter_errors = [
            AuthenticationError("test", "test"),
            RateLimitError("test", "test"),
            NetworkError("test", "test"),
            TimeoutError("test", "test"),
            NotFoundError("test", "test"),
            PermissionError("test", "test"),
        ]

        for error in adapter_errors:
            assert isinstance(error, AdapterError)
            assert isinstance(error, MCPTicketerError)

    def test_all_errors_inherit_from_base(self) -> None:
        """Test that all errors ultimately inherit from MCPTicketerError."""
        all_errors = [
            MCPTicketerError("test"),
            AdapterError("test", "test"),
            AuthenticationError("test", "test"),
            RateLimitError("test", "test"),
            ValidationError("test"),
            ConfigurationError("test"),
            CacheError("test"),
            StateTransitionError("test", TicketState.OPEN, TicketState.CLOSED),
            NetworkError("test", "test"),
            TimeoutError("test", "test"),
            NotFoundError("test", "test"),
            PermissionError("test", "test"),
        ]

        for error in all_errors:
            assert isinstance(error, MCPTicketerError)
            assert isinstance(error, Exception)

    def test_catch_specific_errors(self) -> None:
        """Test that specific errors can be caught specifically."""
        with pytest.raises(AuthenticationError):
            raise AuthenticationError("Auth failed", "test")

        with pytest.raises(RateLimitError):
            raise RateLimitError("Rate limit", "test")

        with pytest.raises(ValidationError):
            raise ValidationError("Validation failed")

    def test_catch_all_with_base_exception(self) -> None:
        """Test that all errors can be caught with MCPTicketerError."""
        errors_to_test = [
            AuthenticationError("test", "test"),
            ValidationError("test"),
            ConfigurationError("test"),
        ]

        for error in errors_to_test:
            with pytest.raises(MCPTicketerError):
                raise error
