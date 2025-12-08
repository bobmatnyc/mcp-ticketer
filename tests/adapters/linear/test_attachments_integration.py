"""Integration test for Linear adapter get_attachments() method.

This test requires valid Linear credentials and a real issue with attachments.
Run with: uv run pytest tests/adapters/linear/test_attachments_integration.py -v -s

Note: This test is skipped by default. Set LINEAR_RUN_INTEGRATION_TESTS=1 to enable.
"""

import os

import pytest

from mcp_ticketer.adapters.linear.adapter import LinearAdapter


@pytest.mark.skipif(
    os.getenv("LINEAR_RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests disabled. Set LINEAR_RUN_INTEGRATION_TESTS=1 to enable.",
)
@pytest.mark.asyncio
async def test_get_attachments_real_issue():
    """Test get_attachments() with a real Linear issue.

    Prerequisites:
    - Valid LINEAR_API_KEY in environment
    - Valid LINEAR_TEAM_KEY in environment
    - Issue identifier with attachments (default: use first open issue)
    """
    api_key = os.getenv("LINEAR_API_KEY")
    team_key = os.getenv("LINEAR_TEAM_KEY")
    test_issue_id = os.getenv("LINEAR_TEST_ISSUE_ID")  # Optional

    if not api_key or not team_key:
        pytest.skip("LINEAR_API_KEY and LINEAR_TEAM_KEY required for integration test")

    # Create adapter
    config = {
        "api_key": api_key,
        "team_key": team_key,
    }
    adapter = LinearAdapter(config)

    # If test issue ID not provided, find first open issue
    if not test_issue_id:
        issues = await adapter.list(limit=1, state="open")
        if not issues:
            pytest.skip("No open issues found in Linear workspace")
        test_issue_id = issues[0].id

    print(f"\n🔍 Testing get_attachments() for issue: {test_issue_id}")

    # Get attachments
    attachments = await adapter.get_attachments(test_issue_id)

    # Display results
    print(f"✅ Found {len(attachments)} attachment(s)")

    if attachments:
        for i, att in enumerate(attachments, 1):
            print(f"\n📎 Attachment {i}:")
            print(f"   ID: {att.id}")
            print(f"   Filename: {att.filename}")
            print(f"   URL: {att.url}")
            print(f"   Description: {att.description or '(none)'}")
            print(f"   Created: {att.created_at}")

            # Verify URL format
            assert att.url, "Attachment URL should not be None"
            assert att.url.startswith("https://"), "URL should be HTTPS"

            # Verify metadata
            assert "linear" in att.metadata, "Should have Linear metadata"
            assert att.metadata["linear"]["id"] == att.id
    else:
        print("ℹ️  No attachments found (this is OK - issue may have no attachments)")

    # Test non-existent issue
    print("\n🔍 Testing get_attachments() for non-existent issue")
    empty_attachments = await adapter.get_attachments("INVALID-999999")
    assert empty_attachments == [], "Should return empty list for non-existent issue"
    print("✅ Correctly returned empty list")


@pytest.mark.skipif(
    os.getenv("LINEAR_RUN_INTEGRATION_TESTS") != "1",
    reason="Integration tests disabled. Set LINEAR_RUN_INTEGRATION_TESTS=1 to enable.",
)
@pytest.mark.asyncio
async def test_get_attachments_real_project():
    """Test get_attachments() with a real Linear project.

    Prerequisites:
    - Valid LINEAR_API_KEY in environment
    - Valid LINEAR_TEAM_KEY in environment
    - Project UUID with documents (optional, uses first found)
    """
    api_key = os.getenv("LINEAR_API_KEY")
    team_key = os.getenv("LINEAR_TEAM_KEY")
    test_project_id = os.getenv("LINEAR_TEST_PROJECT_ID")  # Optional

    if not api_key or not team_key:
        pytest.skip("LINEAR_API_KEY and LINEAR_TEAM_KEY required for integration test")

    # Create adapter
    config = {
        "api_key": api_key,
        "team_key": team_key,
    }
    adapter = LinearAdapter(config)

    # If project ID not provided, find first project
    if not test_project_id:
        projects = await adapter.list_epics(limit=1)
        if not projects:
            pytest.skip("No projects found in Linear workspace")
        test_project_id = projects[0].id

    print(f"\n🔍 Testing get_attachments() for project: {test_project_id}")

    # Get documents (project attachments)
    documents = await adapter.get_attachments(test_project_id)

    # Display results
    print(f"✅ Found {len(documents)} document(s)")

    if documents:
        for i, doc in enumerate(documents, 1):
            print(f"\n📄 Document {i}:")
            print(f"   ID: {doc.id}")
            print(f"   Filename: {doc.filename}")
            print(f"   URL: {doc.url}")
            print(f"   Created: {doc.created_at}")

            # Verify URL format
            assert doc.url, "Document URL should not be None"
            assert doc.url.startswith("https://"), "URL should be HTTPS"
    else:
        print("ℹ️  No documents found (this is OK - project may have no documents)")


if __name__ == "__main__":
    print("Integration Test for Linear Attachments")
    print("=" * 50)
    print("\nTo run this test:")
    print("1. Set environment variables:")
    print("   export LINEAR_API_KEY=lin_api_...")
    print("   export LINEAR_TEAM_KEY=ENG")
    print("   export LINEAR_RUN_INTEGRATION_TESTS=1")
    print(
        "2. Run: uv run pytest tests/adapters/linear/test_attachments_integration.py -v -s"
    )
    print("\nOptional:")
    print("   export LINEAR_TEST_ISSUE_ID=ENG-123  # Use specific issue")
    print("   export LINEAR_TEST_PROJECT_ID=...    # Use specific project")
