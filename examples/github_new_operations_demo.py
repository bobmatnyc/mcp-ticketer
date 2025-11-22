#!/usr/bin/env python3
"""Demonstration of new GitHub adapter operations.

This script showcases the four new methods added to the GitHub adapter:
1. list_cycles() - List GitHub Project iterations
2. get_issue_status() - Get rich issue status information
3. list_issue_statuses() - List available statuses
4. list_project_labels() - List labels for milestones

Requirements:
- GITHUB_TOKEN environment variable set
- GITHUB_OWNER environment variable set
- GITHUB_REPO environment variable set
- A GitHub Project V2 with iterations (optional, for list_cycles demo)
- A milestone with issues (optional, for list_project_labels demo)
"""

import asyncio
import os

from dotenv import load_dotenv

from mcp_ticketer.adapters.github import GitHubAdapter

# Load environment variables
load_dotenv()


async def demo_new_operations():
    """Demonstrate all new GitHub adapter operations."""
    print("=" * 80)
    print("GitHub Adapter - New Operations Demo")
    print("=" * 80)

    # Initialize adapter
    config = {
        "owner": os.getenv("GITHUB_OWNER", "test-owner"),
        "repo": os.getenv("GITHUB_REPO", "test-repo"),
        "token": os.getenv("GITHUB_TOKEN"),
    }

    if not config["token"]:
        print("\n❌ ERROR: GITHUB_TOKEN environment variable not set")
        print("Please set: export GITHUB_TOKEN=your_github_pat")
        return

    adapter = GitHubAdapter(config)
    print(f"\n✓ Adapter initialized for {config['owner']}/{config['repo']}")

    try:
        # ========================================
        # Demo 1: List Available Issue Statuses
        # ========================================
        print("\n" + "=" * 80)
        print("1. LIST AVAILABLE ISSUE STATUSES")
        print("=" * 80)
        print("\nFetching all available issue statuses...")

        statuses = await adapter.list_issue_statuses()

        print(f"\n✓ Found {len(statuses)} available statuses\n")
        print("Native GitHub States:")
        print("-" * 40)
        for status in [s for s in statuses if s["type"] == "native"]:
            print(f"  • {status['name']:12} - {status['description']}")

        print("\nExtended States (via labels):")
        print("-" * 40)
        for status in [s for s in statuses if s["type"] == "extended"]:
            print(f"  • {status['name']:12} (label: {status['label']})")
            print(f"    {status['description']}")

        # ========================================
        # Demo 2: Get Issue Status
        # ========================================
        print("\n" + "=" * 80)
        print("2. GET RICH ISSUE STATUS")
        print("=" * 80)

        # Try to get status for an existing issue
        # You can change this to an actual issue number from your repo
        try:
            issue_number = int(
                input("\nEnter an issue number to check status (or press Enter to skip): ")
                or "0"
            )

            if issue_number > 0:
                print(f"\nFetching status for issue #{issue_number}...")
                status = await adapter.get_issue_status(issue_number)

                print(f"\n✓ Issue #{status['number']}: {status['metadata']['title']}")
                print(f"  URL: {status['metadata']['url']}")
                print("\nState Information:")
                print(f"  Native State:   {status['state']}")
                print(f"  Extended State: {status['extended_state']}")
                if status["status_label"]:
                    print(f"  Status Label:   {status['status_label']}")
                if status["state_reason"]:
                    print(f"  State Reason:   {status['state_reason']}")

                print("\nMetadata:")
                print(f"  Labels:     {', '.join(status['labels']) or 'None'}")
                print(f"  Assignees:  {', '.join(status['metadata']['assignees']) or 'None'}")
                print(f"  Milestone:  {status['metadata']['milestone'] or 'None'}")
                print(f"  Created:    {status['metadata']['created_at']}")
                print(f"  Updated:    {status['metadata']['updated_at']}")
            else:
                print("\n⊘ Skipping issue status demo")

        except ValueError as e:
            print(f"\n⊘ Skipping issue status demo: {e}")

        # ========================================
        # Demo 3: List Project Labels
        # ========================================
        print("\n" + "=" * 80)
        print("3. LIST PROJECT LABELS")
        print("=" * 80)

        # List all repository labels
        print("\nFetching all repository labels...")
        all_labels = await adapter.list_project_labels(milestone_number=None)
        print(f"\n✓ Repository has {len(all_labels)} labels total")

        if all_labels:
            print("\nSample labels:")
            for label in all_labels[:5]:
                print(f"  • {label['name']} (#{label['color']})")

        # Try to get labels for a specific milestone
        try:
            milestone_number = int(
                input(
                    "\nEnter a milestone number to see its labels (or press Enter to skip): "
                )
                or "0"
            )

            if milestone_number > 0:
                print(f"\nFetching labels for milestone {milestone_number}...")
                milestone_labels = await adapter.list_project_labels(
                    milestone_number=milestone_number
                )

                print(f"\n✓ Found {len(milestone_labels)} labels in milestone {milestone_number}")
                if milestone_labels:
                    print("\nLabels by usage:")
                    for label in milestone_labels[:10]:  # Top 10
                        print(
                            f"  • {label['name']:20} - {label['usage_count']:2} issues"
                        )
            else:
                print("\n⊘ Skipping milestone labels demo")

        except ValueError as e:
            print(f"\n⊘ Skipping milestone labels demo: {e}")

        # ========================================
        # Demo 4: List Project Cycles/Iterations
        # ========================================
        print("\n" + "=" * 80)
        print("4. LIST PROJECT ITERATIONS (CYCLES)")
        print("=" * 80)

        print("\nNote: This requires a GitHub Project V2 node ID")
        print("Example format: PVT_kwDOABCD1234")
        print("You can find this via GraphQL API or GitHub GraphQL Explorer")

        try:
            project_id = input(
                "\nEnter a Project V2 node ID (or press Enter to skip): "
            ).strip()

            if project_id:
                print(f"\nFetching iterations for project {project_id[:20]}...")
                iterations = await adapter.list_cycles(
                    project_id=project_id, limit=10
                )

                print(f"\n✓ Found {len(iterations)} iterations")

                if iterations:
                    print("\nIterations:")
                    for iteration in iterations:
                        print(f"\n  • {iteration['title']}")
                        print(f"    ID:       {iteration['id']}")
                        print(f"    Start:    {iteration['startDate']}")
                        print(f"    Duration: {iteration['duration']} days")
                        if iteration["endDate"]:
                            print(f"    End:      {iteration['endDate']}")
                else:
                    print("\n  Project has no iterations configured")
            else:
                print("\n⊘ Skipping project iterations demo")

        except ValueError as e:
            print(f"\n⊘ Error with project iterations: {e}")
            print("Tip: Make sure you're using a valid Project V2 node ID")

        # ========================================
        # Summary
        # ========================================
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("\nNew GitHub Adapter Operations:")
        print("  ✓ list_issue_statuses()  - List all available statuses")
        print("  ✓ get_issue_status()     - Get rich status for specific issue")
        print("  ✓ list_project_labels()  - List labels (all or by milestone)")
        print("  ✓ list_cycles()          - List Project V2 iterations")
        print("\nAll operations demonstrated successfully! 🎉")

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cleanup
        await adapter.close()
        print("\n✓ Adapter closed")


if __name__ == "__main__":
    print("\nGitHub Adapter - New Operations Demo")
    print("=" * 80)
    print("\nThis demo showcases the four new methods added to the GitHub adapter.")
    print("You can interact with the demo by providing issue numbers, milestone")
    print("numbers, and project IDs when prompted, or skip sections by pressing Enter.")
    print("\nMake sure you have set:")
    print("  - GITHUB_TOKEN (Personal Access Token)")
    print("  - GITHUB_OWNER (Repository owner)")
    print("  - GITHUB_REPO (Repository name)")
    print("\n")

    asyncio.run(demo_new_operations())
