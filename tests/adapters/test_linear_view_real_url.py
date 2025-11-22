#!/usr/bin/env python3
"""Test Linear view URL error handling with real-world URL case.

This test verifies the fix for the exception handling bug where
TransportQueryError was not caught, preventing helpful view error messages.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear import LinearAdapter


@pytest.mark.asyncio
async def test_real_view_url_from_user():
    """Test the actual user-reported view URL case.

    URL: https://linear.app/1m-hyperdev/view/mcp-skills-issues-0d0359fabcf9
    View ID extracted: mcp-skills-issues-0d0359fabcf9

    This should show a helpful error message, not crash with exception.
    """

    config = {
        "api_key": "lin_api_mock1234567890abcdef",
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock the client to simulate API failure (exception case from bug)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value={})

    # Test with extracted view ID from real URL
    view_id = "mcp-skills-issues-0d0359fabcf9"

    # Should raise helpful ValueError, not crash
    with pytest.raises(ValueError) as exc_info:
        await adapter.read(view_id)

    # Verify error message content
    error_msg = str(exc_info.value)
    assert "Linear view URLs are not supported" in error_msg
    assert view_id in error_msg
    assert "ticket_list or ticket_search" in error_msg
    print(f"✓ Real URL test passed. Error message:\n{error_msg}")


@pytest.mark.asyncio
async def test_view_id_with_api_success():
    """Test view ID when API successfully returns view data."""

    config = {
        "api_key": "lin_api_mock1234567890abcdef",
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock successful API response with view data
    mock_view_data = {
        "customView": {
            "id": "mcp-skills-issues-0d0359fabcf9",
            "name": "MCP Skills Issues",
            "issues": {
                "nodes": [
                    {"id": "issue1", "title": "Issue 1"},
                    {"id": "issue2", "title": "Issue 2"},
                    {"id": "issue3", "title": "Issue 3"},
                ],
                "pageInfo": {"hasNextPage": True},
            },
        }
    }

    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value=mock_view_data)

    view_id = "mcp-skills-issues-0d0359fabcf9"

    # Should raise helpful ValueError with view name
    with pytest.raises(ValueError) as exc_info:
        await adapter.read(view_id)

    error_msg = str(exc_info.value)
    assert "Linear view URLs are not supported" in error_msg
    assert "MCP Skills Issues" in error_msg
    assert "3+ issues" in error_msg
    print(f"✓ API success test passed. Error message:\n{error_msg}")


@pytest.mark.asyncio
async def test_regression_valid_issue_id():
    """Regression test: Valid issue IDs should still work normally."""

    config = {
        "api_key": "lin_api_mock1234567890abcdef",
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock successful issue fetch - use actual Linear API response structure
    mock_issue_data = {
        "issue": {
            "id": "issue-uuid-123",
            "identifier": "BTA-123",
            "title": "Test Issue",
            "description": "Test description",
            "state": {"id": "state-123", "name": "In Progress"},
            "priority": 2,
            "assignee": None,
            "labels": {"nodes": []},
            "createdAt": "2025-01-01T00:00:00.000Z",
            "updatedAt": "2025-01-01T00:00:00.000Z",
            "team": {"id": "team-123", "name": "Test Team"},
        }
    }

    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value=mock_issue_data)

    # Test with valid issue ID - should work normally
    issue_id = "BTA-123"
    result = await adapter.read(issue_id)

    # Should return a Task object, not raise exception
    assert result is not None
    assert result.id == "BTA-123"
    assert result.title == "Test Issue"
    assert result.description == "Test description"
    print("✓ Regression test passed: Valid issue ID works normally")


@pytest.mark.asyncio
async def test_regression_invalid_id_returns_none():
    """Regression test: Invalid IDs should return None, not raise exception."""

    config = {
        "api_key": "lin_api_mock1234567890abcdef",
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock not found (empty response)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value={})

    # Test with invalid ID that doesn't match view pattern
    invalid_id = "INVALID-999"
    result = await adapter.read(invalid_id)

    # Should return None, not raise exception
    assert result is None
    print("✓ Regression test passed: Invalid ID returns None")


@pytest.mark.asyncio
async def test_exception_handling_catches_all():
    """Test that exception handling catches any exception, not just TransportQueryError.

    This specifically tests the fix: changed from 'except TransportQueryError:'
    to 'except Exception:' so view detection always runs.
    """

    config = {
        "api_key": "lin_api_mock1234567890abcdef",
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock client that raises a generic exception (not TransportQueryError)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(
        side_effect=RuntimeError("Simulated API error")
    )

    view_id = "my-view-abc123def456"

    # Should still catch the exception and show helpful view error
    with pytest.raises(ValueError) as exc_info:
        await adapter.read(view_id)

    error_msg = str(exc_info.value)
    assert "Linear view URLs are not supported" in error_msg
    assert view_id in error_msg
    print("✓ Exception handling test passed: Catches all exceptions")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
