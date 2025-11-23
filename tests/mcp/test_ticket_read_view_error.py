#!/usr/bin/env python3
"""Test that ticket_read MCP tool properly handles Linear view URL errors.

This test verifies the fix for the exception handling bug in ticket_tools.py where
ValueError from adapters was being caught by the generic Exception handler, causing
helpful error messages to be wrapped in "Failed to read ticket: ..." prefix.

The fix adds a specific ValueError handler that preserves the helpful error message.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_ticketer.mcp.server.tools.ticket_tools import ticket_read


@pytest.mark.asyncio
async def test_ticket_read_preserves_view_error_message():
    """Test that ticket_read preserves helpful ValueError from Linear adapter.

    When a Linear view URL is provided, the adapter raises ValueError with a
    helpful message explaining that views aren't supported and suggesting
    alternatives. This error should be passed through to the user without
    wrapping it in generic "Failed to read ticket" prefix.
    """

    # Mock adapter that raises ValueError (like Linear view detection)
    helpful_error_msg = (
        "Linear view URLs are not supported in ticket_read.\n"
        "\n"
        "View: 'Linear View' (mcp-skills-issues-0d0359fabcf9)\n"
        "This view contains 0 issues.\n"
        "\n"
        "Use ticket_list or ticket_search to query issues instead."
    )

    mock_adapter = MagicMock()
    mock_adapter.read = AsyncMock(side_effect=ValueError(helpful_error_msg))

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            # Test with view ID (extracted from URL)
            result = await ticket_read("mcp-skills-issues-0d0359fabcf9")

            # Should return error status
            assert result["status"] == "error"

            # Error message should be preserved exactly, not wrapped
            assert result["error"] == helpful_error_msg

            # Should NOT contain generic wrapper
            assert not result["error"].startswith("Failed to read ticket:")


@pytest.mark.asyncio
async def test_ticket_read_wraps_other_exceptions():
    """Test that ticket_read still wraps non-ValueError exceptions.

    Other exceptions (like network errors, auth failures, etc.) should still
    be wrapped with "Failed to read ticket: " prefix for clarity.
    """

    mock_adapter = MagicMock()
    mock_adapter.read = AsyncMock(side_effect=RuntimeError("Network timeout"))

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.get_adapter",
        return_value=mock_adapter,
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=False
        ):
            result = await ticket_read("PROJ-123")

            # Should return error status
            assert result["status"] == "error"

            # Should wrap the error with generic prefix
            assert result["error"] == "Failed to read ticket: Network timeout"


@pytest.mark.asyncio
async def test_ticket_read_url_routing_with_view_error():
    """Test that URL routing also preserves ValueError messages.

    When using URL routing (multi-platform support), the ValueError should
    still be preserved and passed through.
    """

    helpful_error_msg = (
        "Linear view URLs are not supported in ticket_read.\n"
        "\n"
        "View: 'Linear View' (mcp-skills-issues-0d0359fabcf9)\n"
        "This view contains 0 issues.\n"
        "\n"
        "Use ticket_list or ticket_search to query issues instead."
    )

    # Mock router that raises ValueError
    mock_router = MagicMock()
    mock_router.route_read = AsyncMock(side_effect=ValueError(helpful_error_msg))

    with patch(
        "mcp_ticketer.mcp.server.tools.ticket_tools.has_router", return_value=True
    ):
        with patch(
            "mcp_ticketer.mcp.server.tools.ticket_tools.get_router",
            return_value=mock_router,
        ):
            with patch(
                "mcp_ticketer.mcp.server.tools.ticket_tools.is_url", return_value=True
            ):
                # Test with full Linear view URL
                url = (
                    "https://linear.app/1m-hyperdev/view/mcp-skills-issues-0d0359fabcf9"
                )
                result = await ticket_read(url)

                # Should preserve the helpful error message
                assert result["status"] == "error"
                assert result["error"] == helpful_error_msg
                assert "Linear view URLs are not supported" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
