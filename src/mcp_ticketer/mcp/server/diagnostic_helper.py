"""Diagnostic helper for MCP error handling.

Provides quick diagnostic checks and error classification to help users
troubleshoot system configuration issues when MCP tools encounter errors.
"""

import logging
from enum import Enum
from typing import Any

from ...core.exceptions import (
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

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Classification of error severity for diagnostic suggestions."""

    CRITICAL = "critical"  # Always suggest diagnostics
    MEDIUM = "medium"  # Suggest if pattern detected
    LOW = "low"  # Never suggest diagnostics


# Map exception types to severity levels
ERROR_SEVERITY_MAP = {
    AuthenticationError: ErrorSeverity.CRITICAL,
    ConfigurationError: ErrorSeverity.CRITICAL,
    NetworkError: ErrorSeverity.CRITICAL,
    TimeoutError: ErrorSeverity.CRITICAL,
    NotFoundError: ErrorSeverity.MEDIUM,
    PermissionError: ErrorSeverity.MEDIUM,
    RateLimitError: ErrorSeverity.MEDIUM,
    ValidationError: ErrorSeverity.LOW,
    StateTransitionError: ErrorSeverity.LOW,
}


def should_suggest_diagnostics(exception: Exception) -> bool:
    """Determine if error response should include diagnostic suggestion.

    Args:
        exception: The exception that was raised

    Returns:
        True if diagnostics should be suggested

    """
    severity = get_error_severity(exception)
    return severity in (ErrorSeverity.CRITICAL, ErrorSeverity.MEDIUM)


def get_error_severity(exception: Exception) -> ErrorSeverity:
    """Get severity level for an exception.

    Args:
        exception: The exception to classify

    Returns:
        Error severity level

    """
    exception_type = type(exception)
    return ERROR_SEVERITY_MAP.get(exception_type, ErrorSeverity.MEDIUM)


async def get_quick_diagnostic_info() -> dict[str, Any]:
    """Get lightweight diagnostic info without running full test suite.

    Performs fast checks (< 100ms) to provide immediate troubleshooting hints:
    - Adapter configuration status
    - Credential presence
    - Queue system status

    Returns:
        Dictionary with quick diagnostic results

    """
    info: dict[str, Any] = {}

    try:
        # Check adapter configuration (fast file read)
        from ...cli.utils import CommonPatterns

        config = CommonPatterns.load_config()
        adapters = config.get("adapters", {})

        info["adapter_configured"] = len(adapters) > 0
        info["configured_adapters"] = list(adapters.keys())
        info["default_adapter"] = config.get("default_adapter")

    except Exception as e:
        logger.debug(f"Quick diagnostic config check failed: {e}")
        info["adapter_configured"] = False
        info["config_error"] = str(e)

    try:
        # Check queue system status (fast status check, no operations)
        from ...queue.worker import Worker

        worker = Worker()
        info["queue_running"] = worker.running

    except Exception as e:
        logger.debug(f"Quick diagnostic queue check failed: {e}")
        info["queue_running"] = False

    try:
        # Get version information
        from ...__version__ import __version__

        info["mcp_ticketer_version"] = __version__

    except Exception as e:
        logger.debug(f"Quick diagnostic version check failed: {e}")
        info["mcp_ticketer_version"] = "unknown"

    return info


def build_diagnostic_suggestion(
    exception: Exception, quick_info: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Build diagnostic suggestion dict for error response.

    Args:
        exception: The exception that occurred
        quick_info: Optional quick diagnostic info (from get_quick_diagnostic_info())

    Returns:
        Diagnostic suggestion dictionary for inclusion in error response

    """
    severity = get_error_severity(exception)

    suggestion: dict[str, Any] = {
        "severity": severity.value,
        "message": _get_severity_message(severity),
        "recommendation": _get_recommendation(severity),
        "command": "Use the 'system_diagnostics' MCP tool or CLI: mcp-ticketer doctor",
    }

    if quick_info:
        suggestion["quick_checks"] = quick_info

    return suggestion


def _get_severity_message(severity: ErrorSeverity) -> str:
    """Get human-readable message for severity level."""
    messages = {
        ErrorSeverity.CRITICAL: "This appears to be a system configuration issue",
        ErrorSeverity.MEDIUM: "This may indicate a configuration or permission issue",
        ErrorSeverity.LOW: "This is a validation or input error",
    }
    return messages.get(severity, "An error occurred")


def _get_recommendation(severity: ErrorSeverity) -> str:
    """Get recommendation text for severity level."""
    recommendations = {
        ErrorSeverity.CRITICAL: "Run system diagnostics to identify the problem",
        ErrorSeverity.MEDIUM: "Consider running diagnostics if the issue persists",
        ErrorSeverity.LOW: "Check your input and try again",
    }
    return recommendations.get(severity, "Review the error message")
