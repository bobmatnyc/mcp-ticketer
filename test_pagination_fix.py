#!/usr/bin/env python3
"""
Test script to demonstrate the Linear pagination fix.

This script shows that the _resolve_project_id() method now correctly
handles workspaces with >100 projects by implementing pagination.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


async def test_pagination_fix():
    """Test that pagination works for workspaces with >100 projects."""
    print("Testing Linear pagination fix for workspaces with >100 projects...")
    print("=" * 70)

    # Create adapter
    config = {
        "api_key": "lin_api_test123",
        "team_id": "test-team-id",
    }
    adapter = LinearAdapter(config)

    # Mock the client
    adapter.client = MagicMock()
    adapter.client.execute_query = AsyncMock()

    # Simulate a workspace with 150 projects (100 on page 1, 50 on page 2)
    first_page_projects = [
        {
            "id": f"project-{i}-uuid",
            "name": f"Project {i}",
            "slugId": f"project-{i}-id{i:03d}",
        }
        for i in range(100)
    ]

    second_page_projects = [
        {
            "id": f"project-{i}-uuid",
            "name": f"Project {i}",
            "slugId": f"project-{i}-id{i:03d}",
        }
        for i in range(100, 150)
    ]

    # Add the target project at position 120 (on second page)
    # This simulates the real-world "mcp-memory-6cf55cfcfad4" project
    second_page_projects[20] = {
        "id": "6cf55cfc-fad4-4444-9999-abcdef123456",
        "name": "MCP Memory Project",
        "slugId": "mcp-memory-6cf55cfcfad4",
    }

    first_page = {
        "projects": {
            "nodes": first_page_projects,
            "pageInfo": {
                "hasNextPage": True,
                "endCursor": "cursor-page-1",
            },
        }
    }

    second_page = {
        "projects": {
            "nodes": second_page_projects,
            "pageInfo": {
                "hasNextPage": False,
                "endCursor": "cursor-page-2",
            },
        }
    }

    # Mock returns different pages based on call count
    adapter.client.execute_query.side_effect = [first_page, second_page]

    # Test 1: Find project by slug ID (project #120, on page 2)
    print("\nTest 1: Finding project on page 2 by slug ID")
    print("-" * 70)
    result = await adapter._resolve_project_id("mcp-memory-6cf55cfcfad4")
    print(f"Input: 'mcp-memory-6cf55cfcfad4'")
    print(f"Expected UUID: '6cf55cfc-fad4-4444-9999-abcdef123456'")
    print(f"Actual UUID:   '{result}'")
    print(f"API Calls Made: {adapter.client.execute_query.call_count}")
    assert result == "6cf55cfc-fad4-4444-9999-abcdef123456", "Failed to find project on page 2!"
    print("✓ SUCCESS: Found project on page 2")

    # Reset mock
    adapter.client.execute_query.reset_mock()
    adapter.client.execute_query.side_effect = [first_page, second_page]

    # Test 2: Find project by short ID
    print("\nTest 2: Finding project on page 2 by short ID")
    print("-" * 70)
    result = await adapter._resolve_project_id("6cf55cfcfad4")
    print(f"Input: '6cf55cfcfad4' (short ID)")
    print(f"Expected UUID: '6cf55cfc-fad4-4444-9999-abcdef123456'")
    print(f"Actual UUID:   '{result}'")
    print(f"API Calls Made: {adapter.client.execute_query.call_count}")
    assert result == "6cf55cfc-fad4-4444-9999-abcdef123456", "Failed to find project by short ID!"
    print("✓ SUCCESS: Found project by short ID")

    # Verify pagination parameters
    print("\nTest 3: Verifying pagination parameters")
    print("-" * 70)
    first_call_args = adapter.client.execute_query.call_args_list[0]
    second_call_args = adapter.client.execute_query.call_args_list[1]

    print(f"First call variables: {first_call_args[0][1]}")
    print(f"Second call variables: {second_call_args[0][1]}")

    assert first_call_args[0][1] == {"first": 100}, "First call should not have 'after' cursor"
    assert second_call_args[0][1] == {"first": 100, "after": "cursor-page-1"}, "Second call should include cursor"
    print("✓ SUCCESS: Pagination parameters correct")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)
    print("\nThe pagination fix successfully:")
    print("1. Fetches all projects across multiple pages")
    print("2. Finds projects beyond the first 100 entries")
    print("3. Uses correct cursor-based pagination parameters")
    print("\nThis resolves the 'Project not found' errors for large workspaces.")


if __name__ == "__main__":
    asyncio.run(test_pagination_fix())
