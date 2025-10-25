#!/usr/bin/env python
"""Test script for JIRA adapter functionality."""

import asyncio
import os
from datetime import datetime

import pytest
from dotenv import load_dotenv

from mcp_ticketer.adapters.jira import JiraAdapter
from mcp_ticketer.core import Comment, Priority, Task, TicketState
from mcp_ticketer.core.models import SearchQuery

# Load environment variables
load_dotenv()


def get_test_config():
    """Get JIRA configuration from environment."""
    return {
        "server": os.getenv("JIRA_SERVER"),
        "email": os.getenv("JIRA_EMAIL"),
        "api_token": os.getenv("JIRA_API_TOKEN"),
        "project_key": os.getenv("JIRA_PROJECT_KEY", "TEST"),
        "cloud": os.getenv("JIRA_CLOUD", "true").lower() == "true",
    }


@pytest.mark.asyncio
async def test_jira_adapter():
    """Test basic JIRA adapter operations."""
    print("\n=== JIRA Adapter Test ===\n")

    # Check for required environment variables
    config = get_test_config()
    if not all([config["server"], config["email"], config["api_token"]]):
        print("❌ Missing required JIRA configuration")
        print("Please set: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN")
        print("\nExample:")
        print("export JIRA_SERVER='https://yourcompany.atlassian.net'")
        print("export JIRA_EMAIL='your.email@company.com'")
        print("export JIRA_API_TOKEN='your-api-token'")
        print("export JIRA_PROJECT_KEY='TEST'  # Optional")
        return

    print("🔧 Configuration:")
    print(f"  Server: {config['server']}")
    print(f"  Email: {config['email']}")
    print(f"  Project: {config.get('project_key', 'Not specified')}")
    print(f"  Cloud: {config['cloud']}")
    print()

    try:
        # Initialize adapter
        adapter = JiraAdapter(config)
        print("✅ Adapter initialized successfully\n")

        # Test 1: Create a task
        print("📝 Test 1: Creating a task...")
        test_task = Task(
            title=f"Test Task - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="This is a test task created by mcp-ticketer JIRA adapter",
            priority=Priority.MEDIUM,
            tags=["test", "mcp-ticketer"],
        )

        created_task = await adapter.create(test_task)
        print(f"✅ Task created: {created_task.id}")
        print(f"   Title: {created_task.title}")
        print(f"   State: {created_task.state}")
        print(f"   URL: {created_task.metadata.get('jira', {}).get('url', 'N/A')}\n")

        # Test 2: Read the task
        print("🔍 Test 2: Reading the task...")
        read_task = await adapter.read(created_task.id)
        if read_task:
            print(f"✅ Task read successfully: {read_task.id}")
            print(f"   Title: {read_task.title}")
            print(f"   State: {read_task.state}\n")
        else:
            print("❌ Failed to read task\n")

        # Test 3: Update the task
        print("✏️ Test 3: Updating the task...")
        updated = await adapter.update(
            created_task.id,
            {
                "title": created_task.title + " [UPDATED]",
                "priority": Priority.HIGH,
            },
        )
        if updated:
            print("✅ Task updated successfully")
            print(f"   New Title: {updated.title}")
            print(f"   New Priority: {updated.priority}\n")
        else:
            print("❌ Failed to update task\n")

        # Test 4: Add a comment
        print("💬 Test 4: Adding a comment...")
        comment = Comment(
            ticket_id=created_task.id,
            content="This is a test comment from mcp-ticketer",
        )
        created_comment = await adapter.add_comment(comment)
        print(f"✅ Comment added: {created_comment.id}")
        print(f"   Content: {created_comment.content[:50]}...\n")

        # Test 5: List tasks
        print("📋 Test 5: Listing tasks...")
        tasks = await adapter.list(limit=5)
        print(f"✅ Found {len(tasks)} tasks")
        for i, task in enumerate(tasks[:3], 1):
            print(f"   {i}. {task.id}: {task.title[:50]}...")
        if len(tasks) > 3:
            print(f"   ... and {len(tasks) - 3} more\n")
        else:
            print()

        # Test 6: Search tasks
        print("🔎 Test 6: Searching tasks...")
        search_query = SearchQuery(query="test", limit=5)
        search_results = await adapter.search(search_query)
        print(f"✅ Found {len(search_results)} matching tasks")
        for i, task in enumerate(search_results[:3], 1):
            print(f"   {i}. {task.id}: {task.title[:50]}...")
        print()

        # Test 7: Transition state (if possible)
        print("🔄 Test 7: Testing state transition...")
        try:
            transitioned = await adapter.transition_state(
                created_task.id, TicketState.IN_PROGRESS
            )
            if transitioned:
                print(f"✅ Task transitioned to: {transitioned.state}\n")
            else:
                print("⚠️ State transition not available\n")
        except Exception as e:
            print(f"⚠️ State transition failed: {e}\n")

        # Test 8: Get comments
        print("📖 Test 8: Getting comments...")
        comments = await adapter.get_comments(created_task.id, limit=5)
        print(f"✅ Found {len(comments)} comments")
        for comment in comments:
            print(f"   - {comment.author}: {comment.content[:50]}...")
        print()

        # Test 9: Get project info
        print("ℹ️ Test 9: Getting project information...")
        try:
            project_info = await adapter.get_project_info()
            print(f"✅ Project: {project_info['project']['name']}")
            print(f"   Key: {project_info['project']['key']}")
            print(f"   Issue Types: {len(project_info['issue_types'])} types")
            print(f"   Priorities: {len(project_info['priorities'])} levels")
            print(f"   Custom Fields: {len(project_info['custom_fields'])} fields\n")
        except Exception as e:
            print(f"⚠️ Could not get project info: {e}\n")

        # Optional: Clean up (delete the test task)
        print("🗑️ Cleaning up...")
        cleanup = input("Delete the test task? (y/n): ").strip().lower()
        if cleanup == "y":
            deleted = await adapter.delete(created_task.id)
            if deleted:
                print("✅ Test task deleted\n")
            else:
                print("❌ Failed to delete test task\n")
        else:
            print(f"ℹ️ Test task kept: {created_task.id}\n")

        print("✅ All tests completed successfully!")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        await adapter.close()


@pytest.mark.asyncio
async def test_jira_jql():
    """Test JIRA JQL queries."""
    print("\n=== JIRA JQL Test ===\n")

    config = get_test_config()
    if not all([config["server"], config["email"], config["api_token"]]):
        print("❌ Missing required JIRA configuration")
        return

    adapter = JiraAdapter(config)

    try:
        # Test custom JQL queries
        jql_queries = [
            f"project = {config.get('project_key', 'TEST')} ORDER BY created DESC",
            "status = 'In Progress'",
            "priority in (High, Highest) AND created >= -7d",
            "assignee = currentUser()",
        ]

        for jql in jql_queries:
            print(f"📝 Testing JQL: {jql}")
            try:
                results = await adapter.execute_jql(jql, limit=3)
                print(f"   Found {len(results)} results")
                for task in results[:2]:
                    print(f"   - {task.id}: {task.title[:40]}...")
            except Exception as e:
                print(f"   ⚠️ Query failed: {e}")
            print()

    finally:
        await adapter.close()


async def main():
    """Run all JIRA adapter tests."""
    # Basic functionality tests
    await test_jira_adapter()

    # Additional JQL tests (optional)
    print("\n" + "=" * 50)
    run_jql = input("\nRun JQL tests? (y/n): ").strip().lower()
    if run_jql == "y":
        await test_jira_jql()


if __name__ == "__main__":
    print(
        """
╔══════════════════════════════════════════════╗
║        JIRA Adapter Test Suite               ║
╚══════════════════════════════════════════════╝

This script tests the JIRA adapter functionality.
Make sure you have set the required environment variables:
- JIRA_SERVER: Your JIRA server URL
- JIRA_EMAIL: Your JIRA email
- JIRA_API_TOKEN: Your JIRA API token
- JIRA_PROJECT_KEY: (Optional) Default project key
    """
    )

    asyncio.run(main())
