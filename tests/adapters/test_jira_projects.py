#!/usr/bin/env python3
"""
Test to find JIRA projects where we have create permissions.
"""

import asyncio
import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import httpx

from mcp_ticketer.core.env_loader import load_adapter_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.skip(
    reason="Standalone script, not a pytest test - run directly with python"
)
@pytest.mark.asyncio
async def test_jira_projects():
    """Test JIRA projects and permissions."""
    print("🔍 Testing JIRA projects and permissions...")

    # Load configuration
    config = load_adapter_config("jira", {})

    # Create HTTP client
    auth = (config["email"], config["api_token"])

    async with httpx.AsyncClient() as client:
        # Get all projects
        print("\n📋 Getting all accessible projects...")
        try:
            response = await client.get(
                f"{config['server']}/rest/api/3/project", auth=auth, timeout=30
            )
            response.raise_for_status()
            projects = response.json()

            print(f"✅ Found {len(projects)} accessible projects:")
            for project in projects:
                print(f"    - {project['key']}: {project['name']}")

        except Exception as e:
            print(f"❌ Failed to get projects: {e}")
            return

        # Test create permissions for each project
        print("\n🔍 Testing create permissions for each project...")

        for project in projects:
            project_key = project["key"]
            project_name = project["name"]

            print(f"\n📝 Testing project {project_key} ({project_name})...")

            # Try to get issue types for this project
            try:
                response = await client.get(
                    f"{config['server']}/rest/api/3/issue/createmeta",
                    params={"projectKeys": project_key},
                    auth=auth,
                    timeout=30,
                )
                response.raise_for_status()
                create_meta = response.json()

                if create_meta.get("projects"):
                    project_meta = create_meta["projects"][0]
                    issue_types = project_meta.get("issuetypes", [])

                    if issue_types:
                        print(f"    ✅ Can create issues in {project_key}")
                        print("    📋 Available issue types:")
                        for issue_type in issue_types[:3]:  # Show first 3
                            print(f"        - {issue_type['name']}")

                        # Try creating a test issue in this project
                        await test_create_issue(
                            client, config, project_key, issue_types[0]["name"]
                        )
                        return project_key  # Return the first working project
                    else:
                        print(f"    ❌ No issue types available in {project_key}")
                else:
                    print(f"    ❌ Cannot create issues in {project_key}")

            except Exception as e:
                print(f"    ❌ Error checking {project_key}: {e}")

        print("\n❌ No projects found with create permissions")
        return None


@pytest.mark.skip(
    reason="Standalone script helper, not a pytest test - run directly with python"
)
@pytest.mark.asyncio
async def test_create_issue(client, config, project_key, issue_type):
    """Test creating an issue in the specified project."""
    print(f"\n🧪 Testing issue creation in {project_key}...")

    # Prepare issue data
    issue_data = {
        "fields": {
            "project": {"key": project_key},
            "summary": "🧪 Test Issue for MCP Ticketer",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a test issue created by mcp-ticketer to verify JIRA integration.",
                            }
                        ],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        }
    }

    try:
        response = await client.post(
            f"{config['server']}/rest/api/3/issue",
            json=issue_data,
            auth=(config["email"], config["api_token"]),
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()

        issue_key = result.get("key")
        print(f"    ✅ Successfully created issue: {issue_key}")
        print(f"    🔗 URL: {config['server']}/browse/{issue_key}")

        return issue_key

    except Exception as e:
        print(f"    ❌ Failed to create issue: {e}")
        if hasattr(e, "response"):
            try:
                error_detail = e.response.json()
                print(f"    📋 Error details: {error_detail}")
            except Exception:  # noqa: S110
                pass
        return None


async def main():
    """Run the JIRA projects test."""
    print("🚀 Starting JIRA Projects and Permissions Test")
    print("=" * 60)

    working_project = await test_jira_projects()

    if working_project:
        print(f"\n🎉 Found working project: {working_project}")
        print(f"💡 Update your configuration to use project_key: {working_project}")
    else:
        print("\n❌ No projects found with create permissions")
        print("💡 Contact your JIRA administrator to grant create permissions")

    print("\n" + "=" * 60)
    print("✅ JIRA projects test complete!")


if __name__ == "__main__":
    asyncio.run(main())
