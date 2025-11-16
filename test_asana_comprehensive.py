#!/usr/bin/env python3
"""Comprehensive test for Asana adapter functionality."""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from mcp_ticketer.adapters.asana import AsanaAdapter
from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    Task,
    TicketState,
    TicketType,
)


async def test_asana_comprehensive():
    """Test comprehensive Asana adapter functionality."""
    print("=" * 70)
    print("ASANA ADAPTER - COMPREHENSIVE FUNCTIONALITY TEST")
    print("=" * 70)

    # Get API key from environment
    api_key = os.getenv("ASANA_PAT")
    if not api_key:
        print("ERROR: ASANA_PAT environment variable not set")
        return False

    print("\n>>> Initializing adapter...")
    adapter = AsanaAdapter({"api_key": api_key})
    await adapter.initialize()
    print(f"✓ Workspace: {adapter._workspace_gid}")

    created_items = []  # Track created items for cleanup

    try:
        # TEST 1: Create Epic (Project)
        print("\n" + "=" * 70)
        print("TEST 1: Create Epic (Project)")
        print("=" * 70)

        epic = await adapter.create_epic(
            title="Test Epic - Asana Adapter Testing",
            description="This is a test epic created to validate the Asana adapter implementation",
        )

        if epic:
            print(f"✓ Created epic: {epic.title}")
            print(f"  GID: {epic.id}")
            print(f"  URL: {epic.metadata.get('asana_permalink_url')}")
            created_items.append(("epic", epic.id))
        else:
            print("✗ Failed to create epic")
            return False

        # TEST 2: List Epics
        print("\n" + "=" * 70)
        print("TEST 2: List Epics")
        print("=" * 70)

        epics = await adapter.list_epics()
        print(f"✓ Found {len(epics)} epics")
        for e in epics[:3]:
            print(f"  - {e.title} (GID: {e.id})")

        # TEST 3: Create Issue (Task in Project)
        print("\n" + "=" * 70)
        print("TEST 3: Create Issue (Task in Project)")
        print("=" * 70)

        issue = Task(
            title="Test Issue - Parent Task",
            description="This is a test issue (top-level task) in the epic",
            priority=Priority.HIGH,
            state=TicketState.IN_PROGRESS,
            ticket_type=TicketType.ISSUE,
            parent_epic=epic.id,
            tags=["test", "automated"],
        )

        created_issue = await adapter.create(issue)
        if created_issue:
            print(f"✓ Created issue: {created_issue.title}")
            print(f"  GID: {created_issue.id}")
            print(f"  Type: {created_issue.ticket_type}")
            print(f"  State: {created_issue.state}")
            print(f"  Priority: {created_issue.priority}")
            print(f"  Tags: {created_issue.tags}")
            print(f"  URL: {created_issue.metadata.get('asana_permalink_url')}")
            created_items.append(("task", created_issue.id))
        else:
            print("✗ Failed to create issue")
            return False

        # TEST 4: Create Task (Subtask)
        print("\n" + "=" * 70)
        print("TEST 4: Create Task (Subtask)")
        print("=" * 70)

        subtask = Task(
            title="Test Subtask - Child Task",
            description="This is a subtask of the parent issue",
            priority=Priority.MEDIUM,
            state=TicketState.OPEN,
            ticket_type=TicketType.TASK,
            parent_issue=created_issue.id,
        )

        created_subtask = await adapter.create(subtask)
        if created_subtask:
            print(f"✓ Created subtask: {created_subtask.title}")
            print(f"  GID: {created_subtask.id}")
            print(f"  Type: {created_subtask.ticket_type}")
            print(f"  Parent: {created_subtask.parent_issue}")
            created_items.append(("task", created_subtask.id))
        else:
            print("✗ Failed to create subtask")
            return False

        # TEST 5: Read Task
        print("\n" + "=" * 70)
        print("TEST 5: Read Task")
        print("=" * 70)

        read_task = await adapter.read(created_issue.id)
        if read_task:
            print(f"✓ Read task: {read_task.title}")
            print(f"  Description: {read_task.description[:50]}...")
            print(f"  State: {read_task.state}")
        else:
            print("✗ Failed to read task")
            return False

        # TEST 6: Update Task
        print("\n" + "=" * 70)
        print("TEST 6: Update Task")
        print("=" * 70)

        updated_task = await adapter.update(
            created_issue.id,
            {
                "title": "Test Issue - UPDATED",
                "description": "This task has been updated",
                "state": TicketState.READY,
            }
        )

        if updated_task:
            print(f"✓ Updated task: {updated_task.title}")
            print(f"  State: {updated_task.state}")
            print(f"  Description: {updated_task.description}")
        else:
            print("✗ Failed to update task")
            return False

        # TEST 7: Add Comment
        print("\n" + "=" * 70)
        print("TEST 7: Add Comment")
        print("=" * 70)

        comment = Comment(
            ticket_id=created_issue.id,
            content="This is a test comment added by the Asana adapter",
        )

        created_comment = await adapter.add_comment(comment)
        if created_comment and created_comment.id:
            print(f"✓ Added comment: {created_comment.content[:50]}...")
            print(f"  GID: {created_comment.id}")
        else:
            print("✗ Failed to add comment")
            return False

        # TEST 8: Get Comments
        print("\n" + "=" * 70)
        print("TEST 8: Get Comments")
        print("=" * 70)

        comments = await adapter.get_comments(created_issue.id)
        print(f"✓ Found {len(comments)} comments")
        for c in comments:
            print(f"  - {c.content[:50]}... (by {c.author})")

        # TEST 9: List Issues by Epic
        print("\n" + "=" * 70)
        print("TEST 9: List Issues by Epic")
        print("=" * 70)

        issues = await adapter.list_issues_by_epic(epic.id)
        print(f"✓ Found {len(issues)} issues in epic")
        for i in issues:
            print(f"  - {i.title} (Type: {i.ticket_type})")

        # TEST 10: List Subtasks by Issue
        print("\n" + "=" * 70)
        print("TEST 10: List Subtasks by Issue")
        print("=" * 70)

        subtasks = await adapter.list_tasks_by_issue(created_issue.id)
        print(f"✓ Found {len(subtasks)} subtasks")
        for st in subtasks:
            print(f"  - {st.title}")

        # TEST 11: Transition State
        print("\n" + "=" * 70)
        print("TEST 11: Transition State")
        print("=" * 70)

        transitioned = await adapter.transition_state(created_issue.id, TicketState.DONE)
        if transitioned:
            print(f"✓ Transitioned task to: {transitioned.state}")
            print(f"  Completed: {transitioned.metadata.get('asana_completed')}")
        else:
            print("✗ Failed to transition state")
            return False

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        print("\n" + "=" * 70)
        print("CLEANUP: Deleting test items...")
        print("=" * 70)

        # Delete in reverse order (subtasks first, then tasks, then epics)
        for item_type, item_id in reversed(created_items):
            try:
                if item_type == "task":
                    deleted = await adapter.delete(item_id)
                    if deleted:
                        print(f"✓ Deleted task: {item_id}")
                    else:
                        print(f"✗ Failed to delete task: {item_id}")
                elif item_type == "epic":
                    # Archive epic (Asana doesn't delete projects, only archives them)
                    await adapter.update_epic(item_id, {"state": TicketState.CLOSED})
                    print(f"✓ Archived epic: {item_id}")
            except Exception as e:
                print(f"✗ Cleanup error for {item_id}: {e}")

        await adapter.close()
        print("\n✓ Cleanup complete")


if __name__ == "__main__":
    # Load environment variables from .env.local
    env_file = Path(__file__).parent / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

    # Run test
    success = asyncio.run(test_asana_comprehensive())
    sys.exit(0 if success else 1)
