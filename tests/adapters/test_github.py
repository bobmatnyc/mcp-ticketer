#!/usr/bin/env python3
"""Test script for GitHub adapter integration."""

import asyncio
import os
from datetime import datetime

import pytest
from dotenv import load_dotenv

from mcp_ticketer.adapters.github import GitHubAdapter
from mcp_ticketer.core.models import Comment, Priority, SearchQuery, Task, TicketState

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_github_adapter():
    """Test basic GitHub adapter functionality."""
    print("Testing GitHub Adapter Integration")
    print("=" * 50)

    # Configuration
    config = {
        "owner": os.getenv("GITHUB_OWNER", "test-owner"),
        "repo": os.getenv("GITHUB_REPO", "test-repo"),
        "token": os.getenv("GITHUB_TOKEN"),
    }

    if not config["token"]:
        print("ERROR: GITHUB_TOKEN environment variable not set")
        print("Please set: export GITHUB_TOKEN=your_github_pat")
        return

    print("\nConfiguration:")
    print(f"  Owner: {config['owner']}")
    print(f"  Repo: {config['repo']}")
    print(f"  Token: {'*' * 10}...")

    try:
        # Initialize adapter
        adapter = GitHubAdapter(config)
        print("\n✓ Adapter initialized successfully")

        # Test 1: Create an issue
        print("\n1. Creating test issue...")
        test_task = Task(
            title="Test Issue from mcp-ticketer",
            description="This is a test issue created by the mcp-ticketer GitHub adapter.\n\n"
            "## Features Tested\n"
            "- Issue creation\n"
            "- State management via labels\n"
            "- Priority labeling\n"
            "- Tag support",
            priority=Priority.HIGH,
            state=TicketState.OPEN,
            tags=["test", "mcp-ticketer", "automated"],
        )

        created_task = await adapter.create(test_task)
        print(f"✓ Created issue #{created_task.id}: {created_task.title}")
        print(f"  State: {created_task.state}")
        print(f"  Priority: {created_task.priority}")
        print(f"  Tags: {', '.join(created_task.tags)}")

        # Test 2: Read the issue
        print(f"\n2. Reading issue #{created_task.id}...")
        read_task = await adapter.read(created_task.id)
        if read_task:
            print(f"✓ Successfully read issue #{read_task.id}")
            print(f"  Title: {read_task.title}")
            print(f"  State: {read_task.state}")
        else:
            print("✗ Failed to read issue")

        # Test 3: Update the issue
        print(f"\n3. Updating issue #{created_task.id}...")
        updates = {
            "title": "Test Issue from mcp-ticketer (Updated)",
            "state": TicketState.IN_PROGRESS,
            "priority": Priority.CRITICAL,
        }
        updated_task = await adapter.update(created_task.id, updates)
        if updated_task:
            print(f"✓ Updated issue #{updated_task.id}")
            print(f"  New Title: {updated_task.title}")
            print(f"  New State: {updated_task.state}")
            print(f"  New Priority: {updated_task.priority}")
        else:
            print("✗ Failed to update issue")

        # Test 4: Add a comment
        print(f"\n4. Adding comment to issue #{created_task.id}...")
        comment = Comment(
            ticket_id=created_task.id,
            content="This is a test comment from mcp-ticketer.\n\n"
            "The GitHub adapter is working correctly! 🎉",
        )
        created_comment = await adapter.add_comment(comment)
        print(f"✓ Added comment (ID: {created_comment.id})")
        print(f"  Author: {created_comment.author}")

        # Test 5: Get comments
        print(f"\n5. Getting comments for issue #{created_task.id}...")
        comments = await adapter.get_comments(created_task.id)
        print(f"✓ Retrieved {len(comments)} comment(s)")
        for idx, comm in enumerate(comments, 1):
            print(f"  Comment {idx}: {comm.content[:50]}...")

        # Test 6: List issues
        print("\n6. Listing open issues...")
        issues = await adapter.list(limit=5, filters={"state": TicketState.OPEN})
        print(f"✓ Found {len(issues)} open issue(s)")
        for issue in issues[:3]:  # Show first 3
            print(f"  #{issue.id}: {issue.title}")

        # Test 7: Search issues
        print("\n7. Searching for test issues...")
        search_query = SearchQuery(
            query="mcp-ticketer",
            state=TicketState.IN_PROGRESS,
            limit=5,
        )
        search_results = await adapter.search(search_query)
        print(f"✓ Found {len(search_results)} matching issue(s)")
        for issue in search_results:
            print(f"  #{issue.id}: {issue.title}")

        # Test 8: State transition
        print(f"\n8. Transitioning issue #{created_task.id} to READY...")
        transitioned = await adapter.transition_state(
            created_task.id, TicketState.READY
        )
        if transitioned:
            print(f"✓ Transitioned to {transitioned.state}")
        else:
            print("✗ Failed to transition state")

        # Test 9: Close the issue
        print(f"\n9. Closing issue #{created_task.id}...")
        final_update = await adapter.update(
            created_task.id, {"state": TicketState.CLOSED}
        )
        if final_update and final_update.state == TicketState.CLOSED:
            print(f"✓ Closed issue #{created_task.id}")
        else:
            print("✗ Failed to close issue")

        # Test 10: Get rate limit info
        print("\n10. Checking rate limits...")
        rate_limit = await adapter.get_rate_limit()
        core_limit = rate_limit.get("resources", {}).get("core", {})
        print("✓ Rate Limit Status:")
        print(
            f"  Remaining: {core_limit.get('remaining', 'N/A')}/{core_limit.get('limit', 'N/A')}"
        )
        reset_time = core_limit.get("reset")
        if reset_time:
            reset_dt = datetime.fromtimestamp(reset_time)
            print(f"  Resets at: {reset_dt.strftime('%Y-%m-%d %H:%M:%S')}")

        print("\n" + "=" * 50)
        print("All tests completed successfully! ✓")

    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        if "adapter" in locals():
            await adapter.close()
            print("\n✓ Adapter closed")


if __name__ == "__main__":
    print("GitHub Adapter Test Script")
    print("Make sure you have set:")
    print("  - GITHUB_TOKEN (Personal Access Token)")
    print("  - GITHUB_OWNER (Repository owner)")
    print("  - GITHUB_REPO (Repository name)")
    print("")

    asyncio.run(test_github_adapter())
