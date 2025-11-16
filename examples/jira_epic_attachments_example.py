#!/usr/bin/env python3
"""Example script demonstrating JIRA epic update and attachment features."""

import asyncio
import os
import tempfile
from datetime import datetime

from dotenv import load_dotenv

from mcp_ticketer.adapters.jira import JiraAdapter
from mcp_ticketer.core.models import Epic, Priority, TicketState

# Load environment variables
load_dotenv()


async def main():
    """Demonstrate JIRA epic update and attachment functionality."""
    # Initialize adapter
    config = {
        "server": os.getenv("JIRA_SERVER"),
        "email": os.getenv("JIRA_EMAIL"),
        "api_token": os.getenv("JIRA_API_TOKEN"),
        "project_key": os.getenv("JIRA_PROJECT_KEY", "TEST"),
        "cloud": True,
    }

    adapter = JiraAdapter(config)

    print("=" * 60)
    print("JIRA Epic Update & Attachments Example")
    print("=" * 60)
    print()

    # Example 1: Create and Update an Epic
    print("1️⃣  Creating a new epic...")
    epic = Epic(
        title=f"Example Epic - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        description="This is an example epic demonstrating the new features",
        priority=Priority.MEDIUM,
        tags=["example", "demo"],
    )

    created_epic = await adapter.create(epic)
    print(f"   ✅ Created epic: {created_epic.id}")
    print(f"   📝 Title: {created_epic.title}")
    print(f"   🔗 URL: {created_epic.metadata['jira']['url']}")
    print()

    # Example 2: Update Epic Fields
    print("2️⃣  Updating epic fields...")
    updated_epic = await adapter.update_epic(
        created_epic.id,
        {
            "title": created_epic.title + " [Updated]",
            "description": "Updated description with **formatted** text",
            "priority": Priority.HIGH,
            "tags": ["example", "demo", "updated"],
        }
    )
    print("   ✅ Updated successfully")
    print(f"   📝 New title: {updated_epic.title}")
    print(f"   ⚡ New priority: {updated_epic.priority}")
    print(f"   🏷️  New tags: {', '.join(updated_epic.tags)}")
    print()

    # Example 3: Update Epic State
    print("3️⃣  Transitioning epic state...")
    state_updated = await adapter.update_epic(
        created_epic.id,
        {"state": TicketState.IN_PROGRESS}
    )
    print(f"   ✅ State updated to: {state_updated.state}")
    print()

    # Example 4: Add Attachment
    print("4️⃣  Adding attachment...")
    # Create a temporary file
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as temp_file:
        temp_file.write(f"Example attachment created at {datetime.now()}\n")
        temp_file.write("This demonstrates the attachment functionality.\n")
        temp_file.write("\nFeatures:\n")
        temp_file.write("- File upload\n")
        temp_file.write("- Metadata tracking\n")
        temp_file.write("- Download URLs\n")
        temp_file_path = temp_file.name

    try:
        attachment = await adapter.add_attachment(
            created_epic.id,
            temp_file_path,
            description="Example attachment"
        )
        print("   ✅ Attachment added")
        print(f"   📎 Filename: {attachment.filename}")
        print(f"   💾 Size: {attachment.size_bytes} bytes")
        print(f"   🔗 URL: {attachment.url}")
        print()

        # Example 5: List Attachments
        print("5️⃣  Listing all attachments...")
        attachments = await adapter.get_attachments(created_epic.id)
        print(f"   ✅ Found {len(attachments)} attachment(s)")
        for i, att in enumerate(attachments, 1):
            print(f"   {i}. {att.filename} ({att.size_bytes} bytes)")
            print(f"      Created by: {att.created_by}")
            print(f"      Type: {att.content_type}")
        print()

        # Example 6: Delete Attachment
        print("6️⃣  Deleting attachment...")
        deleted = await adapter.delete_attachment(created_epic.id, attachment.id)
        if deleted:
            print("   ✅ Attachment deleted successfully")
        else:
            print("   ❌ Failed to delete attachment")
        print()

        # Verify deletion
        remaining = await adapter.get_attachments(created_epic.id)
        print(f"   📊 Remaining attachments: {len(remaining)}")
        print()

    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    # Example 7: Cleanup
    print("7️⃣  Cleaning up...")
    deleted = await adapter.delete(created_epic.id)
    if deleted:
        print(f"   ✅ Epic deleted: {created_epic.id}")
    else:
        print(f"   ℹ️  Note: You may need to manually delete {created_epic.id}")
    print()

    print("=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
