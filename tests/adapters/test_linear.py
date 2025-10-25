#!/usr/bin/env python3
"""Test script for Linear adapter functionality."""

import asyncio
import os
from datetime import datetime

import pytest
from dotenv import load_dotenv

from mcp_ticketer.core import AdapterRegistry, Priority, Task, TicketState
from mcp_ticketer.core.models import Comment, SearchQuery

# Load environment variables
load_dotenv()


@pytest.mark.asyncio
async def test_linear_adapter():
    """Test basic Linear adapter operations."""

    # Check for required environment variables
    api_key = os.getenv("LINEAR_API_KEY")
    team_id = os.getenv("LINEAR_TEAM_ID")

    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        print("Please set it in .env file or export it")
        return

    if not team_id:
        print("❌ LINEAR_TEAM_ID environment variable not set")
        print("Please set it in .env file or export it")
        return

    print(f"✅ Using Linear team: {team_id}")

    # Initialize adapter
    config = {"api_key": api_key, "team_id": team_id}

    try:
        adapter = AdapterRegistry.get_adapter("linear", config)
        print("✅ Linear adapter initialized")
    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return

    # Test 1: Create a task
    print("\n📝 Test 1: Creating a task...")
    task = Task(
        title=f"Test Task - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        description="This is a test task created by mcp-ticketer Linear adapter",
        priority=Priority.MEDIUM,
        tags=["test", "mcp-ticketer"],
    )

    try:
        created_task = await adapter.create(task)
        print(f"✅ Created task: {created_task.id} - {created_task.title}")
        task_id = created_task.id
    except Exception as e:
        print(f"❌ Failed to create task: {e}")
        return

    # Test 2: Read the task
    print(f"\n📖 Test 2: Reading task {task_id}...")
    try:
        read_task = await adapter.read(task_id)
        if read_task:
            print(f"✅ Read task: {read_task.title}")
            print(f"  State: {read_task.state}")
            print(f"  Priority: {read_task.priority}")
        else:
            print(f"❌ Task {task_id} not found")
    except Exception as e:
        print(f"❌ Failed to read task: {e}")

    # Test 3: Update the task
    print(f"\n✏️ Test 3: Updating task {task_id}...")
    try:
        updated_task = await adapter.update(
            task_id,
            {
                "title": f"Updated Test Task - {datetime.now().strftime('%H:%M')}",
                "priority": Priority.HIGH,
            },
        )
        if updated_task:
            print(f"✅ Updated task: {updated_task.title}")
            print(f"  New priority: {updated_task.priority}")
        else:
            print(f"❌ Failed to update task {task_id}")
    except Exception as e:
        print(f"❌ Failed to update task: {e}")

    # Test 4: Add a comment
    print(f"\n💬 Test 4: Adding comment to task {task_id}...")
    comment = Comment(
        ticket_id=task_id, content="This is a test comment from mcp-ticketer"
    )

    try:
        created_comment = await adapter.add_comment(comment)
        print(f"✅ Added comment: {created_comment.content[:50]}...")
    except Exception as e:
        print(f"❌ Failed to add comment: {e}")

    # Test 5: List tasks
    print("\n📋 Test 5: Listing tasks...")
    try:
        tasks = await adapter.list(limit=5)
        print(f"✅ Found {len(tasks)} tasks:")
        for t in tasks[:3]:
            print(f"  - {t.id}: {t.title}")
    except Exception as e:
        print(f"❌ Failed to list tasks: {e}")

    # Test 6: Search tasks
    print("\n🔍 Test 6: Searching for 'test' tasks...")
    search_query = SearchQuery(query="test", limit=5)

    try:
        results = await adapter.search(search_query)
        print(f"✅ Found {len(results)} matching tasks:")
        for r in results[:3]:
            print(f"  - {r.id}: {r.title}")
    except Exception as e:
        print(f"❌ Failed to search tasks: {e}")

    # Test 7: Transition state
    print(f"\n🔄 Test 7: Transitioning task {task_id} to in_progress...")
    try:
        transitioned = await adapter.transition_state(task_id, TicketState.IN_PROGRESS)
        if transitioned:
            print(f"✅ Transitioned to: {transitioned.state}")
        else:
            print(f"❌ Failed to transition task {task_id}")
    except Exception as e:
        print(f"❌ Failed to transition state: {e}")

    # Test 8: Get comments
    print(f"\n💬 Test 8: Getting comments for task {task_id}...")
    try:
        comments = await adapter.get_comments(task_id, limit=5)
        print(f"✅ Found {len(comments)} comments:")
        for c in comments:
            print(f"  - {c.author or 'Unknown'}: {c.content[:50]}...")
    except Exception as e:
        print(f"❌ Failed to get comments: {e}")

    # Cleanup
    await adapter.close()
    print("\n✅ All tests completed!")
    print("\n⚠️  Note: Created test task was left in Linear for manual verification")
    print(f"    Task ID: {task_id}")


if __name__ == "__main__":
    print("🚀 Linear Adapter Test Suite")
    print("=" * 40)
    asyncio.run(test_linear_adapter())
