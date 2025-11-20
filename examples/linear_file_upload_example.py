"""Example: Upload files and attach them to Linear issues/epics.

This example demonstrates the new file upload and attachment functionality
in the Linear adapter.

Requirements:
    - Linear API key (LINEAR_API_KEY environment variable)
    - Team ID or team key configured
    - httpx library installed (already in dependencies)
"""

import asyncio
import os
from pathlib import Path


async def example_file_upload_and_attachment():
    """Demonstrate file upload and attachment to Linear issues and epics."""
    from mcp_ticketer.adapters.linear.adapter import LinearAdapter

    # Initialize adapter with your configuration
    config = {
        "api_key": os.getenv("LINEAR_API_KEY"),
        "team_key": "BTA",  # Replace with your team key
        # or use team_id: "your-team-uuid"
    }

    adapter = LinearAdapter(config)
    await adapter.initialize()

    try:
        # ===================================================================
        # Example 1: Update Epic Description
        # ===================================================================

        epic_id = "crm-smart-monitoring-system-f59a41a96c52"  # Your epic slug/ID
        updated_epic = await adapter.update_epic(
            epic_id,
            updates={
                "description": "Updated description with new details",
                "state": "started",
                "target_date": "2025-12-31",
            },
        )

        if updated_epic:
            pass

        # ===================================================================
        # Example 2: Upload a File
        # ===================================================================

        # Create a test file
        test_file = Path("/tmp/test_document.txt")
        test_file.write_text("This is a test document for Linear attachment.")

        # Upload the file to Linear
        asset_url = await adapter.upload_file(
            file_path=str(test_file),
            mime_type="text/plain",  # Optional, will auto-detect if not provided
        )


        # ===================================================================
        # Example 3: Attach File to an Issue
        # ===================================================================

        issue_id = "BTA-123"  # Replace with your issue ID
        await adapter.attach_file_to_issue(
            issue_id=issue_id,
            file_url=asset_url,
            title="Test Document",
            subtitle="Uploaded via API",
            comment_body="Attaching test document for review",
        )


        # ===================================================================
        # Example 4: Attach File to an Epic
        # ===================================================================

        await adapter.attach_file_to_epic(
            epic_id=epic_id,
            file_url=asset_url,
            title="Epic Documentation",
            subtitle="Project overview document",
        )


        # ===================================================================
        # Example 5: Attach External URL
        # ===================================================================

        # You can also attach external URLs without uploading
        await adapter.attach_file_to_issue(
            issue_id=issue_id,
            file_url="https://example.com/document.pdf",
            title="External Document",
            subtitle="Reference document",
        )


        # ===================================================================
        # Example 6: Upload Multiple Files
        # ===================================================================

        # Create multiple test files
        files_to_upload = []
        for i in range(3):
            file_path = Path(f"/tmp/test_file_{i}.txt")
            file_path.write_text(f"Test file number {i}")
            files_to_upload.append(file_path)

        # Upload all files
        asset_urls = []
        for file_path in files_to_upload:
            url = await adapter.upload_file(str(file_path))
            asset_urls.append(url)

        # Attach all files to an issue
        for i, url in enumerate(asset_urls):
            await adapter.attach_file_to_issue(
                issue_id=issue_id,
                file_url=url,
                title=f"Batch Upload {i + 1}",
            )


    except Exception:
        pass
    finally:
        await adapter.close()


if __name__ == "__main__":
    # Run the example
    asyncio.run(example_file_upload_and_attachment())
