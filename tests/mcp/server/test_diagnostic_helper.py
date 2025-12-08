#!/usr/bin/env python3
"""Test suite for diagnostic helper module (1M-134).

Tests error classification, quick diagnostics, and diagnostic suggestion building.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_ticketer.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    StateTransitionError,
    TimeoutError,
    ValidationError,
)
from mcp_ticketer.core.models import TicketState
from mcp_ticketer.mcp.server.diagnostic_helper import (
    ErrorSeverity,
    build_diagnostic_suggestion,
    get_error_severity,
    get_quick_diagnostic_info,
    should_suggest_diagnostics,
)


class TestErrorClassification:
    """Test error severity classification."""

    def test_critical_errors(self) -> None:
        """Test that CRITICAL errors are classified correctly."""
        critical_errors = [
            AuthenticationError("Auth failed", "linear"),
            ConfigurationError("Config invalid"),
            NetworkError("Network timeout", "github"),
            TimeoutError("Request timeout", "jira"),
        ]

        for error in critical_errors:
            severity = get_error_severity(error)
            assert (
                severity == ErrorSeverity.CRITICAL
            ), f"{type(error).__name__} should be CRITICAL, got {severity}"

    def test_medium_errors(self) -> None:
        """Test that MEDIUM errors are classified correctly."""
        medium_errors = [
            NotFoundError("Ticket not found", "linear"),
            PermissionError("Access denied", "github"),
            RateLimitError("Rate limit exceeded", "jira"),
        ]

        for error in medium_errors:
            severity = get_error_severity(error)
            assert (
                severity == ErrorSeverity.MEDIUM
            ), f"{type(error).__name__} should be MEDIUM, got {severity}"

    def test_low_errors(self) -> None:
        """Test that LOW errors are classified correctly."""
        low_errors = [
            ValidationError("Invalid input"),
            StateTransitionError(
                "Invalid state transition",
                TicketState.OPEN,
                TicketState.DONE,
            ),
        ]

        for error in low_errors:
            severity = get_error_severity(error)
            assert (
                severity == ErrorSeverity.LOW
            ), f"{type(error).__name__} should be LOW, got {severity}"

    def test_unknown_error_defaults_to_medium(self) -> None:
        """Test that unknown errors default to MEDIUM severity."""
        unknown_error = RuntimeError("Unknown error")
        severity = get_error_severity(unknown_error)
        assert severity == ErrorSeverity.MEDIUM


class TestDiagnosticSuggestion:
    """Test diagnostic suggestion logic."""

    def test_should_suggest_for_critical_errors(self) -> None:
        """Test that diagnostics are suggested for CRITICAL errors."""
        error = AuthenticationError("Auth failed", "linear")
        assert should_suggest_diagnostics(error) is True

    def test_should_suggest_for_medium_errors(self) -> None:
        """Test that diagnostics are suggested for MEDIUM errors."""
        error = NotFoundError("Not found", "linear")
        assert should_suggest_diagnostics(error) is True

    def test_should_not_suggest_for_low_errors(self) -> None:
        """Test that diagnostics are NOT suggested for LOW errors."""
        error = ValidationError("Invalid input")
        assert should_suggest_diagnostics(error) is False

    def test_critical_errors_always_suggest(self) -> None:
        """Verify all CRITICAL error types suggest diagnostics."""
        critical_errors = [
            AuthenticationError("test", "test"),
            ConfigurationError("test"),
            NetworkError("test", "test"),
            TimeoutError("test", "test"),
        ]

        for error in critical_errors:
            assert (
                should_suggest_diagnostics(error) is True
            ), f"{type(error).__name__} should suggest diagnostics"

    def test_low_errors_never_suggest(self) -> None:
        """Verify all LOW error types never suggest diagnostics."""
        low_errors = [
            ValidationError("test"),
            StateTransitionError("test", TicketState.OPEN, TicketState.DONE),
        ]

        for error in low_errors:
            assert (
                should_suggest_diagnostics(error) is False
            ), f"{type(error).__name__} should not suggest diagnostics"


@pytest.mark.asyncio
class TestQuickDiagnostics:
    """Test quick diagnostic info gathering."""

    async def test_quick_diagnostics_includes_adapter_config(self):
        """Test that quick diagnostics includes adapter configuration."""
        mock_config = {
            "default_adapter": "linear",
            "adapters": {
                "linear": {"api_key": "test-key", "team_id": "test-team"},
                "github": {"token": "test-token"},
            },
        }

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            info = await get_quick_diagnostic_info()

            assert info["adapter_configured"] is True
            assert "linear" in info["configured_adapters"]
            assert "github" in info["configured_adapters"]
            assert info["default_adapter"] == "linear"

    async def test_quick_diagnostics_handles_no_adapters(self):
        """Test quick diagnostics when no adapters configured."""
        mock_config = {"adapters": {}}

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value=mock_config,
        ):
            info = await get_quick_diagnostic_info()

            assert info["adapter_configured"] is False
            assert info["configured_adapters"] == []

    async def test_quick_diagnostics_handles_config_error(self):
        """Test quick diagnostics when config loading fails."""
        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            side_effect=FileNotFoundError("Config not found"),
        ):
            info = await get_quick_diagnostic_info()

            assert info["adapter_configured"] is False
            assert "config_error" in info
            assert "Config not found" in info["config_error"]

    async def test_quick_diagnostics_includes_version(self):
        """Test that version information is included."""
        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value={"adapters": {}},
        ):
            with patch(
                "mcp_ticketer.__version__.__version__",
                "1.1.6",
            ):
                info = await get_quick_diagnostic_info()

                assert "mcp_ticketer_version" in info
                # Version might be "unknown" if import fails, that's ok
                assert info["mcp_ticketer_version"] in ["1.1.6", "unknown"]

    async def test_quick_diagnostics_checks_queue_system(self):
        """Test that queue system status is checked."""
        mock_worker = MagicMock()
        mock_worker.running = True

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value={"adapters": {}},
        ):
            with patch(
                "mcp_ticketer.queue.worker.Worker",
                return_value=mock_worker,
            ):
                info = await get_quick_diagnostic_info()

                assert "queue_running" in info
                # May be True or False depending on Worker mock


class TestDiagnosticSuggestionBuilding:
    """Test building diagnostic suggestion dictionaries."""

    def test_build_suggestion_for_critical_error(self) -> None:
        """Test building suggestion for CRITICAL error."""
        error = AuthenticationError("Auth failed", "linear")
        suggestion = build_diagnostic_suggestion(error)

        assert suggestion["severity"] == "critical"
        assert "system configuration issue" in suggestion["message"]
        assert "Run system diagnostics" in suggestion["recommendation"]
        assert "system_diagnostics" in suggestion["command"]

    def test_build_suggestion_for_medium_error(self) -> None:
        """Test building suggestion for MEDIUM error."""
        error = NotFoundError("Not found", "linear")
        suggestion = build_diagnostic_suggestion(error)

        assert suggestion["severity"] == "medium"
        assert "configuration or permission issue" in suggestion["message"]
        assert "Consider running diagnostics" in suggestion["recommendation"]

    def test_build_suggestion_for_low_error(self) -> None:
        """Test building suggestion for LOW error."""
        error = ValidationError("Invalid input")
        suggestion = build_diagnostic_suggestion(error)

        assert suggestion["severity"] == "low"
        assert "validation or input error" in suggestion["message"]
        assert "Check your input" in suggestion["recommendation"]

    def test_build_suggestion_includes_quick_info(self) -> None:
        """Test that suggestion includes quick diagnostic info when provided."""
        error = AuthenticationError("Auth failed", "linear")
        quick_info = {
            "adapter_configured": False,
            "queue_running": True,
        }

        suggestion = build_diagnostic_suggestion(error, quick_info)

        assert "quick_checks" in suggestion
        assert suggestion["quick_checks"] == quick_info

    def test_build_suggestion_without_quick_info(self) -> None:
        """Test that suggestion works without quick diagnostic info."""
        error = ConfigurationError("Config invalid")
        suggestion = build_diagnostic_suggestion(error)

        assert "quick_checks" not in suggestion
        assert "severity" in suggestion
        assert "message" in suggestion
        assert "recommendation" in suggestion
        assert "command" in suggestion


class TestPerformance:
    """Test performance requirements for quick diagnostics."""

    @pytest.mark.asyncio
    async def test_quick_diagnostics_is_fast(self):
        """Test that quick diagnostics completes in < 100ms.

        NOTE: This test may be flaky on slow systems. The requirement
        is < 100ms under normal conditions, not worst-case.
        """
        import time

        with patch(
            "mcp_ticketer.cli.utils.CommonPatterns.load_config",
            return_value={"adapters": {"linear": {}}},
        ):
            start = time.time()
            await get_quick_diagnostic_info()
            elapsed = (time.time() - start) * 1000  # Convert to ms

            # Allow some margin for test overhead (200ms instead of 100ms)
            assert (
                elapsed < 200
            ), f"Quick diagnostics took {elapsed:.1f}ms, should be < 200ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
