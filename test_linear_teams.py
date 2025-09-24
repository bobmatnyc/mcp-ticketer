"""Test script to find available teams in Linear workspace."""

import asyncio
import os

# Add the source directory to the path
import sys
sys.path.insert(0, '/Users/masa/Projects/managed/mcp-ticketer/src')

from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport


async def list_teams():
    """List all available teams in the Linear workspace."""

    # Load environment
    from dotenv import load_dotenv
    load_dotenv('.env.local')

    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        raise ValueError("LINEAR_API_KEY not found in environment")

    # Setup GraphQL client
    transport = HTTPXAsyncTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": api_key},
        timeout=30.0,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    # Query to get all teams
    query = gql("""
        query GetTeams {
            teams {
                nodes {
                    id
                    name
                    key
                    description
                    createdAt
                    issueCount
                }
            }
        }
    """)

    async with client as session:
        result = await session.execute(query)

    print("Available teams in the Linear workspace:")
    print("=" * 60)

    teams = result["teams"]["nodes"]
    if not teams:
        print("No teams found!")
    else:
        for team in teams:
            print(f"Team Name: {team['name']}")
            print(f"  Key: {team['key']}")
            print(f"  ID: {team['id']}")
            print(f"  Description: {team.get('description', 'N/A')}")
            print(f"  Issue Count: {team.get('issueCount', 0)}")
            print(f"  Created: {team['createdAt']}")
            print("-" * 60)

    # Also try to get workspace info
    workspace_query = gql("""
        query GetWorkspace {
            organization {
                id
                name
                urlKey
                createdAt
            }
        }
    """)

    try:
        async with client as session:
            workspace_result = await session.execute(workspace_query)

        print("\nWorkspace Information:")
        print("=" * 60)
        org = workspace_result.get("organization")
        if org:
            print(f"Name: {org['name']}")
            print(f"URL Key: {org['urlKey']}")
            print(f"ID: {org['id']}")
            print(f"Created: {org['createdAt']}")
    except Exception as e:
        print(f"\nCould not fetch workspace info: {e}")

    await transport.close()


if __name__ == "__main__":
    asyncio.run(list_teams())