"""Linear-specific CLI commands for workspace and team management."""

import os
import re

import typer
from gql import Client, gql
from gql.transport.httpx import HTTPXTransport
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="linear", help="Linear workspace and team management")
console = Console()


async def derive_team_from_url(
    api_key: str, team_url: str
) -> tuple[str | None, str | None]:
    """Derive team ID from Linear team issues URL.

    Accepts URLs like:
    - https://linear.app/1m-hyperdev/team/1M/active
    - https://linear.app/1m-hyperdev/team/1M/
    - https://linear.app/1m-hyperdev/team/1M

    Args:
        api_key: Linear API key
        team_url: URL to Linear team issues page

    Returns:
        Tuple of (team_id, error_message). If successful, team_id is set and error_message is None.
        If failed, team_id is None and error_message contains the error.

    """
    # Extract team key from URL using regex
    # Pattern: https://linear.app/<workspace>/team/<TEAM_KEY>/...
    pattern = r"https://linear\.app/[\w-]+/team/([\w-]+)"
    match = re.search(pattern, team_url)

    if not match:
        return (
            None,
            "Invalid Linear team URL format. Expected: https://linear.app/<workspace>/team/<TEAM_KEY>",
        )

    team_key = match.group(1)
    console.print(f"[dim]Extracted team key: {team_key}[/dim]")

    # Query Linear API to resolve team key to team ID
    query = gql(
        """
        query GetTeamByKey($key: String!) {
            teams(filter: { key: { eq: $key } }) {
                nodes {
                    id
                    key
                    name
                    organization {
                        name
                        urlKey
                    }
                }
            }
        }
    """
    )

    try:
        # Create client
        transport = HTTPXTransport(
            url="https://api.linear.app/graphql", headers={"Authorization": api_key}
        )
        client = Client(transport=transport, fetch_schema_from_transport=False)

        # Execute query
        result = client.execute(query, variable_values={"key": team_key})
        teams = result.get("teams", {}).get("nodes", [])

        if not teams:
            return (
                None,
                f"Team with key '{team_key}' not found. Please check your team URL and API key.",
            )

        team = teams[0]
        team_id = team["id"]
        team_name = team["name"]

        console.print(
            f"[green]✓[/green] Resolved team: {team_name} (Key: {team_key}, ID: {team_id})"
        )

        return team_id, None

    except Exception as e:
        return None, f"Failed to query Linear API: {str(e)}"


def _create_linear_client() -> Client:
    """Create a Linear GraphQL client."""
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        console.print("[red]❌ LINEAR_API_KEY not found in environment[/red]")
        console.print("Set it in .env.local or environment variables")
        raise typer.Exit(1) from None

    transport = HTTPXTransport(
        url="https://api.linear.app/graphql", headers={"Authorization": api_key}
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


@app.command("workspaces")
def list_workspaces() -> None:
    """List all accessible Linear workspaces."""
    console.print("🔍 Discovering Linear workspaces...")

    # Query for current organization and user info
    query = gql(
        """
        query GetWorkspaceInfo {
            viewer {
                id
                name
                email
                organization {
                    id
                    name
                    urlKey
                    createdAt
                }
            }
        }
    """
    )

    try:
        client = _create_linear_client()
        result = client.execute(query)

        viewer = result.get("viewer", {})
        organization = viewer.get("organization", {})

        console.print(f"\n👤 User: {viewer.get('name')} ({viewer.get('email')})")
        console.print("🏢 Current Workspace:")
        console.print(f"   Name: {organization.get('name')}")
        console.print(f"   URL Key: {organization.get('urlKey')}")
        console.print(f"   ID: {organization.get('id')}")
        if organization.get("createdAt"):
            console.print(f"   Created: {organization.get('createdAt')}")

        console.print(
            f"\n✅ API key has access to: {organization.get('name')} workspace"
        )
        console.print(
            f"🌐 Workspace URL: https://linear.app/{organization.get('urlKey')}"
        )

    except Exception as e:
        console.print(f"[red]❌ Error fetching workspace info: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("teams")
def list_teams(
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace URL key (optional)"
    ),
    all_teams: bool = typer.Option(
        False, "--all", "-a", help="Show all teams across all workspaces"
    ),
) -> None:
    """List all teams in the current workspace or all accessible teams."""
    if all_teams:
        console.print("🔍 Discovering ALL accessible Linear teams across workspaces...")
    else:
        console.print("🔍 Discovering Linear teams...")

    # Query for all teams with pagination
    query = gql(
        """
        query GetTeams($first: Int, $after: String) {
            viewer {
                organization {
                    name
                    urlKey
                }
            }
            teams(first: $first, after: $after) {
                nodes {
                    id
                    key
                    name
                    description
                    private
                    createdAt
                    organization {
                        name
                        urlKey
                    }
                    members {
                        nodes {
                            id
                            name
                        }
                    }
                    issues(first: 1) {
                        nodes {
                            id
                        }
                    }
                    projects(first: 1) {
                        nodes {
                            id
                        }
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

    try:
        client = _create_linear_client()

        # Fetch all teams with pagination
        all_teams = []
        has_next_page = True
        after_cursor = None
        current_workspace = None

        while has_next_page:
            variables = {"first": 50}
            if after_cursor:
                variables["after"] = after_cursor

            result = client.execute(query, variable_values=variables)

            # Get workspace info from first page
            if current_workspace is None:
                viewer = result.get("viewer", {})
                current_workspace = viewer.get("organization", {})

            teams_data = result.get("teams", {})
            page_teams = teams_data.get("nodes", [])
            page_info = teams_data.get("pageInfo", {})

            all_teams.extend(page_teams)
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")

        # Display workspace info
        console.print(
            f"\n🏢 Workspace: {current_workspace.get('name')} ({current_workspace.get('urlKey')})"
        )

        # Filter teams by workspace if specified
        if workspace:
            filtered_teams = [
                team
                for team in all_teams
                if team.get("organization", {}).get("urlKey") == workspace
            ]
            if not filtered_teams:
                console.print(
                    f"[yellow]No teams found in workspace '{workspace}'[/yellow]"
                )
                return
            all_teams = filtered_teams
        elif not all_teams and current_workspace:
            # If not showing all teams, filter to current workspace only
            filtered_teams = [
                team
                for team in all_teams
                if team.get("organization", {}).get("urlKey")
                == current_workspace.get("urlKey")
            ]
            all_teams = filtered_teams

        if not all_teams:
            console.print("[yellow]No teams found[/yellow]")
            return

        # Create table
        title_suffix = " (all workspaces)" if all_teams else ""
        table = Table(title=f"Linear Teams ({len(all_teams)} found){title_suffix}")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Workspace", style="dim")
        table.add_column("ID", style="dim")
        table.add_column("Members", justify="center")
        table.add_column("Issues", justify="center")
        table.add_column("Projects", justify="center")
        table.add_column("Private", justify="center")

        for team in all_teams:
            member_count = len(team.get("members", {}).get("nodes", []))
            issue_count = len(team.get("issues", {}).get("nodes", []))
            project_count = len(team.get("projects", {}).get("nodes", []))
            is_private = "🔒" if team.get("private") else "🌐"
            workspace_key = team.get("organization", {}).get("urlKey", "")

            table.add_row(
                team.get("key", ""),
                team.get("name", ""),
                workspace_key,
                team.get("id", ""),
                str(member_count),
                str(issue_count),
                str(project_count),
                is_private,
            )

        console.print(table)

        # Show configuration suggestions
        if all_teams:
            console.print("\n💡 Configuration suggestions:")
            for team in all_teams[:3]:  # Show first 3 teams
                console.print(f"   Team '{team.get('name')}':")
                console.print(f"     team_key: '{team.get('key')}'")
                console.print(f"     team_id: '{team.get('id')}'")
                console.print()

    except Exception as e:
        console.print(f"[red]❌ Error fetching teams: {e}[/red]")
        raise typer.Exit(1) from e


@app.command("configure")
def configure_team(
    team_key: str | None = typer.Option(
        None, "--team-key", "-k", help="Team key (e.g., '1M')"
    ),
    team_id: str | None = typer.Option(None, "--team-id", "-i", help="Team UUID"),
    workspace: str | None = typer.Option(
        None, "--workspace", "-w", help="Workspace URL key"
    ),
) -> None:
    """Configure Linear adapter with a specific team."""
    from ..cli.main import load_config, save_config

    if not team_key and not team_id:
        console.print("[red]❌ Either --team-key or --team-id is required[/red]")
        raise typer.Exit(1) from None

    console.print("🔧 Configuring Linear adapter...")

    # Validate team exists
    if team_id:
        # Validate team by ID
        query = gql(
            """
            query GetTeamById($id: String!) {
                team(id: $id) {
                    id
                    key
                    name
                    organization {
                        name
                        urlKey
                    }
                }
            }
        """
        )

        try:
            client = _create_linear_client()
            result = client.execute(query, variable_values={"id": team_id})
            team = result.get("team")

            if not team:
                console.print(f"[red]❌ Team with ID '{team_id}' not found[/red]")
                raise typer.Exit(1) from None

        except Exception as e:
            console.print(f"[red]❌ Error validating team: {e}[/red]")
            raise typer.Exit(1) from e

    elif team_key:
        # Validate team by key
        query = gql(
            """
            query GetTeamByKey($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        key
                        name
                        organization {
                            name
                            urlKey
                        }
                    }
                }
            }
        """
        )

        try:
            client = _create_linear_client()
            result = client.execute(query, variable_values={"key": team_key})
            teams = result.get("teams", {}).get("nodes", [])

            if not teams:
                console.print(f"[red]❌ Team with key '{team_key}' not found[/red]")
                raise typer.Exit(1) from None

            team = teams[0]
            team_id = team["id"]  # Use the found team ID

        except Exception as e:
            console.print(f"[red]❌ Error validating team: {e}[/red]")
            raise typer.Exit(1) from e

    # Update configuration
    config = load_config()

    # Ensure adapters section exists
    if "adapters" not in config:
        config["adapters"] = {}

    # Update Linear adapter configuration
    linear_config = {"type": "linear", "team_id": team_id}

    if team_key:
        linear_config["team_key"] = team_key
    if workspace:
        linear_config["workspace"] = workspace

    config["adapters"]["linear"] = linear_config

    # Save configuration
    save_config(config)

    console.print("✅ Linear adapter configured successfully!")
    console.print(f"   Team: {team.get('name')} ({team.get('key')})")
    console.print(f"   Team ID: {team_id}")
    console.print(f"   Workspace: {team.get('organization', {}).get('name')}")

    # Test the configuration
    console.print("\n🧪 Testing configuration...")
    try:
        from ..adapters.linear import LinearAdapter

        adapter = LinearAdapter(linear_config)

        # Test by listing a few tickets
        import asyncio

        tickets = asyncio.run(adapter.list(limit=1))
        console.print(
            f"✅ Configuration test successful! Found {len(tickets)} ticket(s)"
        )

    except Exception as e:
        console.print(f"[yellow]⚠️  Configuration saved but test failed: {e}[/yellow]")
        console.print("You may need to check your API key or team permissions")


@app.command("info")
def show_info(
    team_key: str | None = typer.Option(
        None, "--team-key", "-k", help="Team key to show info for"
    ),
    team_id: str | None = typer.Option(
        None, "--team-id", "-i", help="Team UUID to show info for"
    ),
) -> None:
    """Show detailed information about a specific team."""
    if not team_key and not team_id:
        console.print("[red]❌ Either --team-key or --team-id is required[/red]")
        raise typer.Exit(1) from None

    # Query for detailed team information
    if team_id:
        query = gql(
            """
            query GetTeamInfo($id: String!) {
                team(id: $id) {
                    id
                    key
                    name
                    description
                    private
                    createdAt
                    updatedAt
                    organization {
                        name
                        urlKey
                    }
                    members(first: 10) {
                        nodes {
                            id
                            name
                            active
                        }
                    }
                    states(first: 20) {
                        nodes {
                            id
                            name
                            type
                            position
                        }
                    }
                }
            }
        """
        )
        variables = {"id": team_id}
    else:
        query = gql(
            """
            query GetTeamInfoByKey($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        key
                        name
                        description
                        private
                        createdAt
                        updatedAt
                        organization {
                            name
                            urlKey
                        }
                        members(first: 10) {
                            nodes {
                                id
                                name
                                active
                            }
                        }
                        states(first: 20) {
                            nodes {
                                id
                                name
                                type
                                position
                            }
                        }
                    }
                }
            }
        """
        )
        variables = {"key": team_key}

    try:
        client = _create_linear_client()
        result = client.execute(query, variable_values=variables)

        if team_id:
            team = result.get("team")
        else:
            teams = result.get("teams", {}).get("nodes", [])
            team = teams[0] if teams else None

        if not team:
            identifier = team_id or team_key
            console.print(f"[red]❌ Team '{identifier}' not found[/red]")
            raise typer.Exit(1) from None

        # Display team information
        console.print(f"\n🏷️  Team: {team.get('name')}")
        console.print(f"   Key: {team.get('key')}")
        console.print(f"   ID: {team.get('id')}")
        console.print(
            f"   Workspace: {team.get('organization', {}).get('name')} ({team.get('organization', {}).get('urlKey')})"
        )
        console.print(
            f"   Privacy: {'🔒 Private' if team.get('private') else '🌐 Public'}"
        )

        if team.get("description"):
            console.print(f"   Description: {team.get('description')}")

        console.print(f"   Created: {team.get('createdAt')}")

        # Statistics
        member_count = len(team.get("members", {}).get("nodes", []))
        state_count = len(team.get("states", {}).get("nodes", []))

        console.print("\n📊 Statistics:")
        console.print(f"   Members: {member_count}")
        console.print(f"   Workflow States: {state_count}")

        # Show members
        members = team.get("members", {}).get("nodes", [])
        if members:
            console.print(f"\n👥 Members ({len(members)}):")
            for member in members:
                status = "✅" if member.get("active") else "❌"
                console.print(f"   {status} {member.get('name')}")
            if len(members) == 10:
                console.print("   ... (showing first 10 members)")

        # Show workflow states
        states = team.get("states", {}).get("nodes", [])
        if states:
            console.print(f"\n🔄 Workflow States ({len(states)}):")
            for state in sorted(states, key=lambda s: s.get("position", 0)):
                console.print(f"   {state.get('name')} ({state.get('type')})")
            if len(states) == 20:
                console.print("   ... (showing first 20 states)")

    except Exception as e:
        console.print(f"[red]❌ Error fetching team info: {e}[/red]")
        raise typer.Exit(1) from e
