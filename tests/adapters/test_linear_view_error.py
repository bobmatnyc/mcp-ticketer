#!/usr/bin/env python3
"""Test Linear view URL error handling."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_ticketer.adapters.linear import LinearAdapter


@pytest.mark.asyncio
async def test_view_url_helpful_error_when_api_fails():
    """Test that view URLs show helpful error even when API query fails."""

    # Setup: Mock LinearAdapter with API that fails
    config = {
        "api_key": "lin_api_mock1234567890abcdef",  # Valid format: starts with lin_api_
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock the client to simulate API failure
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(
        return_value={}
    )  # Empty result = API failed

    # Test: Read with a view URL identifier (slug-uuid format)
    view_id = "mcp-skills-issues-0d0359fabcf9"

    # Should raise ValueError with helpful message, not return None
    with pytest.raises(ValueError) as exc_info:
        await adapter.read(view_id)

    # Verify error message is helpful
    error_msg = str(exc_info.value)
    assert "Linear view URLs are not supported" in error_msg
    assert "Linear View" in error_msg  # Generic name since API failed
    assert view_id in error_msg  # Should include the view ID
    assert "ticket_list or ticket_search" in error_msg  # Should suggest alternatives


@pytest.mark.asyncio
async def test_view_url_helpful_error_when_api_succeeds():
    """Test that view URLs show helpful error when API successfully fetches view."""

    # Setup: Mock LinearAdapter with API that succeeds
    config = {
        "api_key": "lin_api_mock1234567890abcdef",  # Valid format: starts with lin_api_
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock the client to simulate successful API response
    mock_view_data = {
        "customView": {
            "id": "test-view-123",
            "name": "My Custom View",
            "issues": {
                "nodes": [
                    {"id": "issue1"},
                    {"id": "issue2"},
                ],
                "pageInfo": {"hasNextPage": True},
            },
        }
    }

    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value=mock_view_data)

    # Test: Read with a view URL identifier
    view_id = "test-view-123"

    # Should raise ValueError with helpful message including actual view name
    with pytest.raises(ValueError) as exc_info:
        await adapter.read(view_id)

    # Verify error message uses actual view name
    error_msg = str(exc_info.value)
    assert "Linear view URLs are not supported" in error_msg
    assert "My Custom View" in error_msg  # Actual view name from API
    assert "2+ issues" in error_msg  # Issue count with + due to hasNextPage


@pytest.mark.asyncio
async def test_non_view_id_does_not_trigger_view_error():
    """Test that non-view IDs (issue IDs, project IDs) don't trigger view error."""

    # Setup: Mock LinearAdapter
    config = {
        "api_key": "lin_api_mock1234567890abcdef",  # Valid format: starts with lin_api_
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock the client to simulate not found (empty response)
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value={})

    # Test: Short IDs without hyphens should not trigger view error
    short_id = "abc123456789"  # 12 chars, no hyphens
    result = await adapter.read(short_id)

    # Should return None (not found), not raise view error
    assert result is None

    # Test: Issue IDs (BTA-123 format) should not trigger view error
    issue_id = "BTA-123"  # Has hyphen but only 7 chars
    result = await adapter.read(issue_id)

    # Should return None (not found), not raise view error
    assert result is None


@pytest.mark.asyncio
async def test_view_id_pattern_detection():
    """Test the view ID pattern detection logic."""

    # Setup: Mock LinearAdapter
    config = {
        "api_key": "lin_api_mock1234567890abcdef",  # Valid format: starts with lin_api_
        "team_id": "mock_team",
    }

    adapter = LinearAdapter(config)

    # Mock the client to simulate API failure
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock(return_value={})

    # Test cases: (view_id, should_trigger_view_error)
    test_cases = [
        ("mcp-skills-issues-0d0359fabcf9", True),  # Typical view URL ID
        ("active-bugs-f59a41a96c52", True),  # Another view URL ID
        ("my-view-abc123def456", True),  # View with long ID
        ("BTA-123", False),  # Issue ID (too short)
        ("abc123456789", False),  # UUID-like but no hyphens
        ("a-b-c", False),  # Has hyphens but too short
        ("project-123", False),  # Short project ID
    ]

    for view_id, should_raise in test_cases:
        if should_raise:
            # Should raise helpful view error
            with pytest.raises(ValueError) as exc_info:
                await adapter.read(view_id)
            assert "Linear view URLs are not supported" in str(exc_info.value)
        else:
            # Should return None (not found) without view error
            result = await adapter.read(view_id)
            assert result is None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
