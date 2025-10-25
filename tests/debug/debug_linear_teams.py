#!/usr/bin/env python3
"""Debug Linear teams and API key access."""

import asyncio
import os
import sys
from pathlib import Path

# Load environment variables from .env.local
from dotenv import load_dotenv

load_dotenv(".env.local")

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport


async def debug_linear_teams():
    """Debug Linear teams accessible by the current API key."""
    print("🔍 Debugging Linear teams and API key access...")

    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY not found in environment")
        return

    print(f"🔑 Using API key: {api_key[:20]}...")

    # Create GraphQL client
    # Linear uses the API key directly, not as a Bearer token
    transport = HTTPXAsyncTransport(
        url="https://api.linear.app/graphql", headers={"Authorization": api_key}
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    try:
        # Query all teams accessible by this API key
        teams_query = gql(
            """
            query GetAllTeams {
                teams {
                    nodes {
                        id
                        name
                        key
                        description
                        organization {
                            id
                            name
                        }
                    }
                }
            }
        """
        )

        async with client as session:
            result = await session.execute(teams_query)

        teams = result["teams"]["nodes"]
        print(f"\n📋 Found {len(teams)} teams accessible by this API key:")

        for i, team in enumerate(teams, 1):
            print(f"\n{i}. Team: {team['name']}")
            print(f"   ID: {team['id']}")
            print(f"   Key: {team['key']}")
            print(f"   Description: {team.get('description', 'No description')}")
            print(f"   Organization: {team['organization']['name']}")

            # Check if this is our configured team
            if team["id"] == "b366b0de-2f3f-4641-8100-eea12b6aa5df":
                print("   ✅ This is our configured team (1M)!")
            elif team["key"] == "CLU":
                print("   ⚠️  This is the CLU team (wrong team)!")

        # Check which team would be used by default
        print("\n🎯 Team Analysis:")
        target_team_id = "b366b0de-2f3f-4641-8100-eea12b6aa5df"
        target_team = next((t for t in teams if t["id"] == target_team_id), None)

        if target_team:
            print(f"✅ Target team found: {target_team['name']} ({target_team['key']})")
        else:
            print(
                f"❌ Target team NOT found! API key doesn't have access to team {target_team_id}"
            )

        clu_team = next((t for t in teams if t["key"] == "CLU"), None)
        if clu_team:
            print(f"⚠️  CLU team found: {clu_team['name']} ({clu_team['id']})")
            print("   This might be the default team being used")

        # Test creating a ticket with explicit team ID
        print("\n🎫 Testing ticket creation with explicit team ID...")

        if target_team:
            create_query = gql(
                """
                mutation CreateIssue($input: IssueCreateInput!) {
                    issueCreate(input: $input) {
                        success
                        issue {
                            id
                            identifier
                            title
                            team {
                                id
                                name
                                key
                            }
                        }
                    }
                }
            """
            )

            issue_input = {
                "title": "DEBUG - Team ID Test",
                "description": "Testing explicit team ID assignment",
                "teamId": target_team_id,
            }

            async with client as session:
                create_result = await session.execute(
                    create_query, variable_values={"input": issue_input}
                )

            if create_result["issueCreate"]["success"]:
                issue = create_result["issueCreate"]["issue"]
                print(f"✅ Successfully created ticket: {issue['identifier']}")
                print(f"   Title: {issue['title']}")
                print(f"   Team: {issue['team']['name']} ({issue['team']['key']})")
                print(f"   Team ID: {issue['team']['id']}")

                # Check if the prefix matches
                prefix = issue["identifier"].split("-")[0]
                if prefix == "1M":
                    print(f"   ✅ Correct prefix: {prefix}")
                else:
                    print(f"   ❌ Wrong prefix: {prefix} (expected 1M)")
            else:
                print("❌ Failed to create ticket")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_linear_teams())
