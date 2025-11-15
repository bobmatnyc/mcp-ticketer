#!/usr/bin/env python
"""Test script for JIRA adapter epic update and attachment functionality."""

import asyncio
import os
import tempfile
from datetime import datetime

import pytest
from dotenv import load_dotenv

from mcp_ticketer.adapters.jira import JiraAdapter
from mcp_ticketer.core import Epic, Priority, TicketState

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
async def test_jira_epic_update():
    """Test JIRA epic update functionality."""
    print("\n=== JIRA Epic Update Test ===\n")

    # Check for required environment variables
    config = get_test_config()
    if not all([config["server"], config["email"], config["api_token"]]):
        print("❌ Missing required JIRA configuration")
        print("Please set: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN")
        pytest.skip("Missing JIRA credentials")
        return

    print("🔧 Configuration:")
    print(f"  Server: {config['server']}")
    print(f"  Email: {config['email']}")
    print(f"  Project: {config.get('project_key', 'Not specified')}")
    print()

    try:
        # Initialize adapter
        adapter = JiraAdapter(config)
        print("✅ Adapter initialized successfully\n")

        # Test 1: Create an epic
        print("📝 Test 1: Creating an epic...")
        test_epic = Epic(
            title=f"Test Epic - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="This is a test epic created by mcp-ticketer JIRA adapter",
            priority=Priority.MEDIUM,
            tags=["test", "mcp-ticketer", "epic"],
        )

        created_epic = await adapter.create(test_epic)
        print(f"✅ Epic created: {created_epic.id}")
        print(f"   Title: {created_epic.title}")
        print(f"   State: {created_epic.state}")
        print(f"   URL: {created_epic.metadata.get('jira', {}).get('url', 'N/A')}\n")

        # Test 2: Update epic using update_epic method
        print("✏️ Test 2: Updating epic with update_epic()...")
        updated_epic = await adapter.update_epic(
            created_epic.id,
            {
                "title": created_epic.title + " [UPDATED]",
                "description": "Updated description for test epic",
                "tags": ["test", "mcp-ticketer", "epic", "updated"],
                "priority": Priority.HIGH,
            },
        )
        if updated_epic:
            print("✅ Epic updated successfully")
            print(f"   New Title: {updated_epic.title}")
            print(f"   New Priority: {updated_epic.priority}")
            print(f"   New Tags: {updated_epic.tags}\n")
        else:
            print("❌ Failed to update epic\n")

        # Test 3: Update epic state
        print("✏️ Test 3: Updating epic state...")
        state_updated = await adapter.update_epic(
            created_epic.id, {"state": TicketState.IN_PROGRESS}
        )
        if state_updated:
            print(f"✅ Epic state updated: {state_updated.state}\n")
        else:
            print("❌ Failed to update epic state\n")

        # Cleanup
        print("🧹 Cleaning up...")
        deleted = await adapter.delete(created_epic.id)
        if deleted:
            print(f"✅ Epic deleted: {created_epic.id}\n")
        else:
            print(f"❌ Failed to delete epic: {created_epic.id}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


@pytest.mark.asyncio
async def test_jira_attachments():
    """Test JIRA attachment functionality."""
    print("\n=== JIRA Attachments Test ===\n")

    # Check for required environment variables
    config = get_test_config()
    if not all([config["server"], config["email"], config["api_token"]]):
        print("❌ Missing required JIRA configuration")
        print("Please set: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN")
        pytest.skip("Missing JIRA credentials")
        return

    print("🔧 Configuration:")
    print(f"  Server: {config['server']}")
    print(f"  Email: {config['email']}")
    print()

    try:
        # Initialize adapter
        adapter = JiraAdapter(config)
        print("✅ Adapter initialized successfully\n")

        # Create a test epic for attachments
        print("📝 Creating test epic for attachments...")
        test_epic = Epic(
            title=f"Test Epic for Attachments - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            description="Epic for testing attachment functionality",
            priority=Priority.MEDIUM,
        )

        created_epic = await adapter.create(test_epic)
        print(f"✅ Epic created: {created_epic.id}\n")

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as temp_file:
            temp_file.write(
                f"Test attachment file created at {datetime.now().isoformat()}\n"
            )
            temp_file.write("This is a test file for JIRA attachment functionality.\n")
            temp_file_path = temp_file.name

        try:
            # Test 1: Add attachment
            print(f"📎 Test 1: Adding attachment from {temp_file_path}...")
            attachment = await adapter.add_attachment(
                created_epic.id,
                temp_file_path,
                description="Test attachment from mcp-ticketer",
            )
            print("✅ Attachment added successfully")
            print(f"   ID: {attachment.id}")
            print(f"   Filename: {attachment.filename}")
            print(f"   Size: {attachment.size_bytes} bytes")
            print(f"   Content Type: {attachment.content_type}")
            print(f"   URL: {attachment.url}\n")

            # Test 2: Get attachments
            print("📋 Test 2: Getting attachments...")
            attachments = await adapter.get_attachments(created_epic.id)
            print(f"✅ Found {len(attachments)} attachment(s)")
            for att in attachments:
                print(f"   - {att.filename} ({att.size_bytes} bytes)")
            print()

            # Test 3: Delete attachment
            print(f"🗑️ Test 3: Deleting attachment {attachment.id}...")
            deleted = await adapter.delete_attachment(created_epic.id, attachment.id)
            if deleted:
                print("✅ Attachment deleted successfully\n")
            else:
                print("❌ Failed to delete attachment\n")

            # Verify deletion
            print("📋 Verifying deletion...")
            remaining = await adapter.get_attachments(created_epic.id)
            print(f"✅ Remaining attachments: {len(remaining)}\n")

        finally:
            # Cleanup temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                print(f"🧹 Cleaned up temporary file: {temp_file_path}")

        # Cleanup epic
        print("🧹 Cleaning up epic...")
        deleted = await adapter.delete(created_epic.id)
        if deleted:
            print(f"✅ Epic deleted: {created_epic.id}\n")
        else:
            print(f"❌ Failed to delete epic: {created_epic.id}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling for edge cases."""
    print("\n=== JIRA Error Handling Test ===\n")

    config = get_test_config()
    if not all([config["server"], config["email"], config["api_token"]]):
        pytest.skip("Missing JIRA credentials")
        return

    adapter = JiraAdapter(config)
    print("✅ Adapter initialized\n")

    # Test 1: File not found
    print("🧪 Test 1: File not found error...")
    try:
        await adapter.add_attachment("TEST-1", "/nonexistent/file.txt")
        print("❌ Should have raised FileNotFoundError")
    except FileNotFoundError as e:
        print(f"✅ Correctly raised FileNotFoundError: {e}\n")

    # Test 2: Empty update
    print("🧪 Test 2: Empty update error...")
    try:
        await adapter.update_epic("TEST-1", {})
        print("❌ Should have raised ValueError")
    except ValueError as e:
        print(f"✅ Correctly raised ValueError: {e}\n")

    # Test 3: Invalid attachment ID
    print("🧪 Test 3: Invalid attachment deletion...")
    result = await adapter.delete_attachment("TEST-1", "999999")
    if not result:
        print("✅ Correctly returned False for invalid attachment\n")
    else:
        print("❌ Should have returned False\n")

    print("✅ All error handling tests passed\n")


if __name__ == "__main__":
    print("Running JIRA Epic & Attachments Tests")
    print("=" * 50)

    # Run tests
    asyncio.run(test_jira_epic_update())
    asyncio.run(test_jira_attachments())
    asyncio.run(test_error_handling())
