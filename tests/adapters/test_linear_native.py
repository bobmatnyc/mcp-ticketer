"""Test script for Linear adapter with native GraphQL API."""

import asyncio
import os

# Add the source directory to the path
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, "/Users/masa/Projects/managed/mcp-ticketer/src")

from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Comment, Priority, SearchQuery, Task, TicketState


@pytest.mark.asyncio
async def test_linear_adapter():
    """Test the Linear adapter with the 1m-hyperdev workspace."""

    # Load environment
    from dotenv import load_dotenv

    load_dotenv(".env.local")

    # Initialize adapter with BTA workspace and BTA team
    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "workspace": "travel-bta",
        "team_key": "BTA",
    }

    adapter = LinearAdapter(config)

    try:
        print("=" * 80)
        print("Testing Linear Adapter with Native GraphQL API")
        print("Workspace: travel-bta | Team: BTA")
        print("=" * 80)

        # Test 1: Create a comprehensive issue
        print("\n1. Creating a new issue with full details...")
        new_task = Task(
            title="[Test] Full GraphQL API Integration Test",
            description=(
                "This is a comprehensive test issue created via the native Linear GraphQL API.\n\n"
                "## Features to test:\n"
                "- ✅ Issue creation with all fields\n"
                "- ✅ Priority management\n"
                "- ✅ Label management\n"
                "- ✅ State workflow\n"
                "- ✅ Comments and reactions\n"
                "- ✅ Cycles and projects\n"
                "- ✅ Due dates and estimates\n\n"
                "This issue demonstrates the full capabilities of the Linear adapter."
            ),
            state=TicketState.IN_PROGRESS,
            priority=Priority.HIGH,
            tags=["api-test", "graphql", "integration"],
            estimated_hours=4.5,
            metadata={
                "linear": {
                    "due_date": (datetime.now() + timedelta(days=7)).date().isoformat()
                }
            },
        )

        created_task = await adapter.create(new_task)
        print(f"✅ Created issue: {created_task.id}")
        print(f"   Title: {created_task.title}")
        print(f"   State: {created_task.state}")
        print(f"   Priority: {created_task.priority}")
        print(f"   Tags: {created_task.tags}")
        print(f"   URL: {created_task.metadata['linear'].get('url')}")

        # Test 2: Read the issue back with full details
        print(f"\n2. Reading issue {created_task.id} with full details...")
        read_task = await adapter.read(created_task.id)
        if read_task:
            print("✅ Successfully read issue")
            print(f"   Team: {read_task.metadata['linear'].get('team_name')}")
            print(f"   State: {read_task.metadata['linear'].get('state_name')}")
            print(
                f"   Priority Label: {read_task.metadata['linear'].get('priority_label')}"
            )
            print(f"   Due Date: {read_task.metadata['linear'].get('due_date')}")
            print(f"   Estimate: {read_task.estimated_hours}")

        # Test 3: Add a comment with threading
        print(f"\n3. Adding comments to issue {created_task.id}...")
        comment1 = Comment(
            ticket_id=created_task.id,
            content="This is the first comment testing the GraphQL comment API.",
        )
        created_comment1 = await adapter.add_comment(comment1)
        print(f"✅ Added comment: {created_comment1.id}")

        # Add a threaded reply
        comment2 = Comment(
            ticket_id=created_task.id,
            content="This is a reply to the first comment, demonstrating comment threading.",
            metadata={"parent_comment_id": created_comment1.id},
        )
        created_comment2 = await adapter.add_comment(comment2)
        print(f"✅ Added reply comment: {created_comment2.id}")

        # Test 4: Get comments
        print(f"\n4. Getting comments for issue {created_task.id}...")
        comments = await adapter.get_comments(created_task.id)
        print(f"✅ Retrieved {len(comments)} comments")
        for comment in comments:
            print(f"   - {comment.content[:50]}...")

        # Test 5: Update the issue
        print(f"\n5. Updating issue {created_task.id}...")
        updates = {
            "title": "[Test] Updated - Full GraphQL API Integration Test",
            "priority": Priority.CRITICAL,
            "state": TicketState.READY,
            "tags": ["api-test", "graphql", "updated", "ready-for-review"],
            "estimated_hours": 6.0,
        }
        updated_task = await adapter.update(created_task.id, updates)
        if updated_task:
            print("✅ Updated issue successfully")
            print(f"   New Title: {updated_task.title}")
            print(f"   New Priority: {updated_task.priority}")
            print(f"   New State: {updated_task.state}")
            print(f"   New Tags: {updated_task.tags}")

        # Test 6: Create a project
        print("\n6. Creating a new project...")
        project_id = await adapter.create_project(
            "Test GraphQL Project", "A test project created via the Linear GraphQL API"
        )
        print(f"✅ Created project: {project_id}")

        # Test 7: Create a sub-issue
        print(f"\n7. Creating a sub-issue under {created_task.id}...")
        sub_task = Task(
            title="[Sub-task] Test child issue functionality",
            description="This is a child issue to test parent-child relationships",
            state=TicketState.OPEN,
            priority=Priority.MEDIUM,
            parent_issue=created_task.id,
            parent_epic=project_id,
            tags=["sub-task", "api-test"],
        )
        created_sub_task = await adapter.create(sub_task)
        print(f"✅ Created sub-issue: {created_sub_task.id}")
        print(f"   Parent: {created_sub_task.parent_issue}")
        print(f"   Project: {created_sub_task.parent_epic}")

        # Test 8: Search issues
        print("\n8. Searching for issues...")
        search = SearchQuery(
            query="GraphQL",
            state=TicketState.READY,
            priority=Priority.CRITICAL,
            tags=["api-test"],
            limit=5,
        )
        search_results = await adapter.search(search)
        print(f"✅ Found {len(search_results)} matching issues")
        for task in search_results:
            print(f"   - {task.id}: {task.title}")

        # Test 9: List issues with filters
        print("\n9. Listing issues with filters...")
        filters = {
            "state": TicketState.IN_PROGRESS,
            "priority": Priority.HIGH,
            "labels": ["api-test"],
        }
        listed_tasks = await adapter.list(limit=5, filters=filters)
        print(f"✅ Listed {len(listed_tasks)} issues matching filters")

        # Test 10: Get cycles
        print("\n10. Getting active cycles...")
        cycles = await adapter.get_cycles(active_only=True)
        print(f"✅ Found {len(cycles)} active cycles")
        for cycle in cycles[:3]:
            print(f"   - Cycle {cycle.get('number')}: {cycle.get('name')}")
            if cycle.get("startsAt"):
                print(f"     Starts: {cycle['startsAt']}")
            if cycle.get("endsAt"):
                print(f"     Ends: {cycle['endsAt']}")

        # Test 11: Add to cycle (if there are active cycles)
        if cycles:
            print("\n11. Adding issue to cycle...")
            cycle_id = cycles[0]["id"]
            success = await adapter.add_to_cycle(created_task.id, cycle_id)
            if success:
                print(f"✅ Added issue to cycle: {cycles[0].get('name')}")

        # Test 12: Set due date
        print("\n12. Setting due date for issue...")
        due_date = datetime.now() + timedelta(days=14)
        success = await adapter.set_due_date(created_task.id, due_date.date())
        if success:
            print(f"✅ Set due date to: {due_date.date()}")

        # Test 13: Add reaction to comment
        if comments:
            print("\n13. Adding reaction to comment...")
            success = await adapter.add_reaction(comments[0].id, "👍")
            if success:
                print("✅ Added 👍 reaction to comment")

        # Test 14: Transition states
        print("\n14. Testing state transitions...")
        transitions = [
            (TicketState.TESTED, "Moving to tested"),
            (TicketState.DONE, "Marking as done"),
        ]

        for target_state, description in transitions:
            print(f"   Transitioning to {target_state}: {description}")
            transitioned = await adapter.transition_state(created_task.id, target_state)
            if transitioned:
                print(f"   ✅ Successfully transitioned to {transitioned.state}")

        # Test 15: Archive (soft delete) the test issues
        print("\n15. Archiving test issues...")
        archived1 = await adapter.delete(created_task.id)
        if archived1:
            print(f"✅ Archived main issue: {created_task.id}")

        archived2 = await adapter.delete(created_sub_task.id)
        if archived2:
            print(f"✅ Archived sub-issue: {created_sub_task.id}")

        print("\n" + "=" * 80)
        print("✅ All tests completed successfully!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Clean up
        await adapter.close()
        print("\nAdapter connection closed.")


if __name__ == "__main__":
    asyncio.run(test_linear_adapter())
