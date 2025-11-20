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


    # Example 1: Create and Update an Epic
    epic = Epic(
        title=f"Example Epic - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        description="This is an example epic demonstrating the new features",
        priority=Priority.MEDIUM,
        tags=["example", "demo"],
    )

    created_epic = await adapter.create(epic)

    # Example 2: Update Epic Fields
    await adapter.update_epic(
        created_epic.id,
        {
            "title": created_epic.title + " [Updated]",
            "description": "Updated description with **formatted** text",
            "priority": Priority.HIGH,
            "tags": ["example", "demo", "updated"],
        }
    )

    # Example 3: Update Epic State
    await adapter.update_epic(
        created_epic.id,
        {"state": TicketState.IN_PROGRESS}
    )

    # Example 4: Add Attachment
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

        # Example 5: List Attachments
        attachments = await adapter.get_attachments(created_epic.id)
        for _i, _att in enumerate(attachments, 1):
            pass

        # Example 6: Delete Attachment
        deleted = await adapter.delete_attachment(created_epic.id, attachment.id)
        if deleted:
            pass
        else:
            pass

        # Verify deletion
        await adapter.get_attachments(created_epic.id)

    finally:
        # Cleanup temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    # Example 7: Cleanup
    deleted = await adapter.delete(created_epic.id)
    if deleted:
        pass
    else:
        pass



if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception:
        import traceback
        traceback.print_exc()
