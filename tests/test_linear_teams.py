#!/usr/bin/env python3
"""
Test script to find the correct Linear team key
"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport

# Load environment variables
env_path = Path(".env.local")
if env_path.exists():
    load_dotenv(env_path)


async def find_teams():
    """Find available teams in the Linear workspace"""
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("LINEAR_API_KEY not found!")
        return

    transport = HTTPXAsyncTransport(
        url="https://api.linear.app/graphql", headers={"Authorization": api_key}
    )

    client = Client(transport=transport)

    # Query to get viewer info and workspaces
    viewer_query = gql(
        """
        query GetViewer {
            viewer {
                id
                name
                email
                organization {
                    id
                    name
                    urlKey
                }
            }
        }
    """
    )

    # Try different approaches to find workspaces
    user_memberships_query = gql(
        """
        query GetUserMemberships {
            viewer {
                id
                name
                email
                organizationMemberships {
                    nodes {
                        organization {
                            id
                            name
                            urlKey
                        }
                    }
                }
            }
        }
    """
    )

    # Alternative: try to get organization metadata
    org_meta_query = gql(
        """
        query GetOrgMeta {
            organizationMeta {
                hasActiveSubscription
                hasSubscriptionEnded
            }
            organization {
                id
                name
                urlKey
                allowMembersToInvite
                createdAt
            }
        }
    """
    )

    # Query to get all teams (this should get teams from all accessible workspaces)
    gql(
        """
        query GetAllTeams {
            teams {
                nodes {
                    id
                    key
                    name
                    description
                    organization {
                        id
                        name
                        urlKey
                    }
                }
            }
        }
    """
    )

    # Alternative query to try getting teams with different pagination
    teams_with_pagination = gql(
        """
        query GetTeamsWithPagination($first: Int, $after: String) {
            teams(first: $first, after: $after) {
                nodes {
                    id
                    key
                    name
                    description
                    organization {
                        id
                        name
                        urlKey
                    }
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    """
    )

    # Try to query for organizations directly
    gql(
        """
        query GetOrganizations {
            organizations {
                nodes {
                    id
                    name
                    urlKey
                }
            }
        }
    """
    )

    # Try alternative approach with issues to see if we can find other workspaces
    gql(
        """
        query GetRecentIssues {
            issues(first: 10) {
                nodes {
                    id
                    identifier
                    title
                    team {
                        id
                        key
                        name
                        organization {
                            id
                            name
                            urlKey
                        }
                    }
                }
            }
        }
    """
    )

    try:
        # First get viewer info
        viewer_result = await client.execute_async(viewer_query)
        viewer = viewer_result.get("viewer", {})
        current_org = viewer.get("organization", {})

        print(f"👤 User: {viewer.get('name')} ({viewer.get('email')})")
        print(
            f"🏢 Current/Default Organization: {current_org.get('name')} ({current_org.get('urlKey')})"
        )
        print()

        # Try to get user memberships across organizations
        print("🔍 Trying to fetch user organization memberships...")
        try:
            memberships_result = await client.execute_async(user_memberships_query)
            viewer_data = memberships_result.get("viewer", {})
            memberships = viewer_data.get("organizationMemberships", {}).get(
                "nodes", []
            )

            print(f"🏢 Found {len(memberships)} organization membership(s):")
            for membership in memberships:
                org = membership.get("organization", {})
                print(
                    f"   - {org.get('name')} ({org.get('urlKey')}) - ID: {org.get('id')}"
                )
                if org.get("urlKey") == "1m-hyperdev":
                    print("     ✅ Found 1m-hyperdev workspace!")
            print()

        except Exception as e:
            print(f"❌ Could not fetch organization memberships: {e}")

            # Try alternative org meta query
            print("🔍 Trying organization metadata query...")
            try:
                org_meta_result = await client.execute_async(org_meta_query)
                org_data = org_meta_result.get("organization", {})
                print("🏢 Organization details:")
                print(f"   Name: {org_data.get('name')}")
                print(f"   URL Key: {org_data.get('urlKey')}")
                print(f"   ID: {org_data.get('id')}")
                print(f"   Created: {org_data.get('createdAt')}")
                print()
            except Exception as e2:
                print(f"❌ Could not fetch organization metadata: {e2}")
                print()

        # Try to get all teams with pagination to ensure we get everything
        all_teams = []
        has_next_page = True
        after_cursor = None

        print("🔍 Fetching all teams with pagination...")
        while has_next_page:
            variables = {"first": 50}
            if after_cursor:
                variables["after"] = after_cursor

            result = await client.execute_async(
                teams_with_pagination, variable_values=variables
            )
            teams_data = result.get("teams", {})
            page_teams = teams_data.get("nodes", [])
            page_info = teams_data.get("pageInfo", {})

            all_teams.extend(page_teams)
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")

            print(f"   Fetched {len(page_teams)} teams (total: {len(all_teams)})")

        print(
            f"🏷️  Found {len(all_teams)} team(s) total across all accessible workspaces:\n"
        )

        # Group teams by workspace
        workspaces = {}
        hyperdev_teams = []

        for team in all_teams:
            org = team.get("organization", {})
            workspace_key = org.get("urlKey", "unknown")
            workspace_name = org.get("name", "Unknown")

            if workspace_key not in workspaces:
                workspaces[workspace_key] = {"name": workspace_name, "teams": []}
            workspaces[workspace_key]["teams"].append(team)

            # Check if this is from 1m-hyperdev workspace
            if workspace_key == "1m-hyperdev":
                hyperdev_teams.append(team)

        # Display all workspaces and teams
        for workspace_key, workspace_data in workspaces.items():
            print(f"🏢 Workspace: {workspace_data['name']} ({workspace_key})")

            if workspace_key == "1m-hyperdev":
                print("   ✅ This is the 1m-hyperdev workspace!")

            for team in workspace_data["teams"]:
                print(f"   🏷️  Team: {team['name']}")
                print(f"      Key: {team['key']}")
                print(f"      ID: {team['id']}")
                if team.get("description"):
                    print(f"      Description: {team['description']}")
            print()

        # Check if we found 1m-hyperdev teams
        if hyperdev_teams:
            print(f"✅ Found {len(hyperdev_teams)} team(s) in 1m-hyperdev workspace!")
            team = hyperdev_teams[0]  # Use the first team
            print("✅ Recommended configuration:")
            print(f"   Team Key: '{team['key']}'")
            print(f"   Team ID: '{team['id']}'")
            print(f"   Team Name: '{team['name']}'")
            return team["key"], team["id"], "1m-hyperdev"
        else:
            print("❌ No teams found in 1m-hyperdev workspace.")
            print("Available workspaces:")
            for workspace_key, workspace_data in workspaces.items():
                print(f"   - {workspace_data['name']} ({workspace_key})")
            return None, None, None

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    asyncio.run(find_teams())
