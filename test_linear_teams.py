#!/usr/bin/env python3
"""
Test script to find the correct Linear team key
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport

# Load environment variables
env_path = Path('.env.local')
if env_path.exists():
    load_dotenv(env_path)

async def find_teams():
    """Find available teams in the Linear workspace"""
    api_key = os.getenv('LINEAR_API_KEY')
    if not api_key:
        print("LINEAR_API_KEY not found!")
        return

    transport = HTTPXAsyncTransport(
        url="https://api.linear.app/graphql",
        headers={"Authorization": api_key}
    )

    client = Client(transport=transport)

    # Query to get teams
    query = gql("""
        query GetTeams {
            teams {
                nodes {
                    id
                    key
                    name
                    description
                }
            }
        }
    """)

    try:
        result = await client.execute_async(query)
        teams = result.get('teams', {}).get('nodes', [])

        print(f"Found {len(teams)} team(s) in Linear workspace:\n")
        for team in teams:
            print(f"Team Name: {team['name']}")
            print(f"  Key: {team['key']}")
            print(f"  ID: {team['id']}")
            if team.get('description'):
                print(f"  Description: {team['description']}")
            print()

        if teams:
            print(f"✓ Use team key '{teams[0]['key']}' for the Linear adapter")
            return teams[0]['key']
        else:
            print("No teams found. Check your API key permissions.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(find_teams())