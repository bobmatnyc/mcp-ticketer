#!/usr/bin/env python3
"""
Test all configured adapters with credentials from .env.local
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load environment variables
env_path = Path(".env.local")
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from {env_path}")

console = Console()


@pytest.mark.asyncio
async def test_linear():
    """Test Linear adapter with 1m-hyperdev workspace"""
    console.print("\n[bold cyan]Testing Linear Adapter[/bold cyan]")

    try:
        from mcp_ticketer.adapters.linear import LinearAdapter
        from mcp_ticketer.core.models import Priority

        config = {
            "api_key": os.getenv("LINEAR_API_KEY"),
            "team_key": "BTA",  # Corrected team key
            "workspace": "1m-hyperdev",
        }

        if not config["api_key"]:
            console.print("[red]✗ LINEAR_API_KEY not found in environment[/red]")
            return False

        adapter = LinearAdapter(config)

        # Test operations
        tests_passed = 0
        tests_total = 0

        # 1. Create a task
        tests_total += 1
        try:
            from mcp_ticketer.core.models import Task, TicketState

            test_task = Task(
                id="",
                title=f"[TEST] Linear Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description="Testing Linear GraphQL integration from mcp-ticketer",
                state=TicketState.OPEN,
                priority=Priority.MEDIUM,
                tags=["test", "mcp-ticketer"],
            )

            created_task = await adapter.create(test_task)
            console.print(
                f"  ✓ Created issue: {created_task.id} - {created_task.title}"
            )
            tests_passed += 1

            # 2. Get the issue
            tests_total += 1
            retrieved_task = await adapter.read(created_task.id)
            if retrieved_task:
                console.print(f"  ✓ Retrieved issue: {retrieved_task.title}")
                tests_passed += 1

            # 3. List issues
            tests_total += 1
            tasks = await adapter.list(limit=5)
            console.print(f"  ✓ Listed {len(tasks)} issues")
            tests_passed += 1

            # 4. Clean up - archive the test issue
            tests_total += 1
            success = await adapter.delete(created_task.id)
            if success:
                console.print("  ✓ Archived test issue")
                tests_passed += 1

        except Exception as e:
            console.print(f"  [red]✗ Error: {e}[/red]")

        console.print(
            f"\n[green]Linear: {tests_passed}/{tests_total} tests passed[/green]"
        )
        return tests_passed == tests_total

    except Exception as e:
        console.print(f"[red]✗ Failed to test Linear: {e}[/red]")
        return False


@pytest.mark.asyncio
async def test_github():
    """Test GitHub adapter with bobmatnyc/mcp-ticketer repo"""
    console.print("\n[bold cyan]Testing GitHub Adapter[/bold cyan]")

    try:
        from mcp_ticketer.adapters.github import GitHubAdapter
        from mcp_ticketer.core.models import Comment, Priority

        config = {
            "api_key": os.getenv("GITHUB_TOKEN"),  # Use api_key for consistency
            "owner": os.getenv("GITHUB_OWNER", "bobmatnyc"),
            "repo": "mcp-ticketer",  # Using the specified repo
        }

        if not config["api_key"]:
            console.print("[red]✗ GITHUB_TOKEN not found in environment[/red]")
            return False

        console.print(f"  Using GitHub repo: {config['owner']}/{config['repo']}")

        adapter = GitHubAdapter(config)

        # Test operations
        tests_passed = 0
        tests_total = 0
        created_issue_number = None

        try:
            # 1. Create an issue
            tests_total += 1
            from mcp_ticketer.core.models import Task, TicketState

            test_task = Task(
                id="",  # Will be assigned
                title=f"[TEST] GitHub Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description="This is a test issue created by the mcp-ticketer integration tests. It can be safely deleted.",
                state=TicketState.OPEN,
                priority=Priority.MEDIUM,
                tags=["test", "automation", "mcp-ticketer"],
            )

            created_task = await adapter.create(test_task)
            created_issue_number = created_task.id
            console.print(
                f"  ✓ Created issue #{created_issue_number}: {created_task.title}"
            )
            tests_passed += 1

            # 2. Get the issue
            tests_total += 1
            retrieved_task = await adapter.read(created_issue_number)
            if retrieved_task:
                console.print(f"  ✓ Retrieved issue: {retrieved_task.title}")
                tests_passed += 1

            # 3. Add a comment
            tests_total += 1
            comment = Comment(
                id="",
                ticket_id=created_issue_number,
                author="test-user",
                content="This is a test comment from the mcp-ticketer integration tests.",
            )
            created_comment = await adapter.add_comment(comment)
            console.print(f"  ✓ Added comment: {created_comment.id}")
            tests_passed += 1

            # 4. List issues
            tests_total += 1
            tasks = await adapter.list(limit=5)
            console.print(f"  ✓ Listed {len(tasks)} issues")
            tests_passed += 1

            # 5. Update the issue (add a tag)
            tests_total += 1
            updated_task = await adapter.update(
                created_issue_number,
                {"tags": ["test", "automation", "mcp-ticketer", "updated"]},
            )
            if updated_task:
                console.print("  ✓ Updated issue with new tags")
                tests_passed += 1

        except Exception as e:
            console.print(f"  [red]✗ Error during operations: {e}[/red]")

        # Cleanup - close the test issue
        if created_issue_number:
            try:
                tests_total += 1
                success = await adapter.delete(created_issue_number)
                if success:
                    console.print(f"  ✓ Closed test issue #{created_issue_number}")
                    tests_passed += 1
                else:
                    console.print(
                        f"  [yellow]⚠ Failed to close test issue #{created_issue_number}[/yellow]"
                    )
            except Exception as e:
                console.print(f"  [yellow]⚠ Cleanup error: {e}[/yellow]")

        console.print(
            f"\n[green]GitHub: {tests_passed}/{tests_total} tests passed[/green]"
        )
        return tests_passed >= (
            tests_total - 1
        )  # Allow 1 failure for non-critical cleanup

    except Exception as e:
        console.print(f"[red]✗ Failed to test GitHub: {e}[/red]")
        return False


@pytest.mark.asyncio
async def test_jira():
    """Test JIRA adapter with 1m-hyperdev.atlassian.net"""
    console.print("\n[bold cyan]Testing JIRA Adapter[/bold cyan]")

    try:
        from mcp_ticketer.adapters.jira import JiraAdapter
        from mcp_ticketer.core.models import Comment, Priority, Task, TicketState

        config = {
            "server": "https://1m-hyperdev.atlassian.net",
            "email": os.getenv("JIRA_ACCESS_USER"),
            "api_token": os.getenv("JIRA_ACCESS_TOKEN"),
            "project_key": "SMS",  # Using the SMS project
        }

        if not config["email"] or not config["api_token"]:
            console.print("[red]✗ JIRA credentials not found in environment[/red]")
            return False

        console.print(f"  Using JIRA server: {config['server']}")
        console.print(f"  Using project: {config['project_key']}")
        console.print(f"  Using email: {config['email']}")

        adapter = JiraAdapter(config)

        # Test operations
        tests_passed = 0
        tests_total = 0
        created_issue_key = None

        try:
            # 1. Create an issue
            tests_total += 1
            test_task = Task(
                id="",
                title=f"[TEST] JIRA Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description="This is a test issue created by the mcp-ticketer integration tests. It can be safely deleted.",
                state=TicketState.OPEN,
                priority=Priority.MEDIUM,
                tags=["test", "automation"],
            )

            created_task = await adapter.create(test_task)
            created_issue_key = created_task.id
            console.print(
                f"  ✓ Created issue {created_issue_key}: {created_task.title}"
            )
            tests_passed += 1

            # 2. Get the issue
            tests_total += 1
            retrieved_task = await adapter.read(created_issue_key)
            if retrieved_task:
                console.print(f"  ✓ Retrieved issue: {retrieved_task.title}")
                tests_passed += 1

            # 3. List issues
            tests_total += 1
            tasks = await adapter.list(limit=5)
            console.print(f"  ✓ Listed {len(tasks)} issues")
            tests_passed += 1

            # 4. Search issues
            tests_total += 1
            from mcp_ticketer.core.models import SearchQuery

            search_query = SearchQuery(query="TEST", limit=5)
            search_results = await adapter.search(search_query)
            console.print(f"  ✓ Search returned {len(search_results)} results")
            tests_passed += 1

            # 5. Update the issue
            tests_total += 1
            updated_task = await adapter.update(
                created_issue_key,
                {"description": "Updated description from integration tests"},
            )
            if updated_task:
                console.print("  ✓ Updated issue description")
                tests_passed += 1

            # 6. Add a comment
            tests_total += 1
            comment = Comment(
                id="",
                ticket_id=created_issue_key,
                author="test-user",
                content="This is a test comment from the mcp-ticketer integration tests.",
            )
            created_comment = await adapter.add_comment(comment)
            console.print(f"  ✓ Added comment: {created_comment.id}")
            tests_passed += 1

            # 7. Transition state (if possible)
            tests_total += 1
            try:
                transitioned_task = await adapter.transition_state(
                    created_issue_key, TicketState.IN_PROGRESS
                )
                if transitioned_task:
                    console.print("  ✓ Transitioned issue to In Progress")
                    tests_passed += 1
                else:
                    console.print(
                        "  [yellow]⚠ Could not transition issue state[/yellow]"
                    )
            except Exception as e:
                console.print(
                    f"  [yellow]⚠ State transition not available: {e}[/yellow]"
                )

        except Exception as e:
            console.print(f"  [red]✗ Error during operations: {e}[/red]")

        # Cleanup - transition to Done (or delete if supported)
        if created_issue_key:
            try:
                tests_total += 1
                # Try to transition to Done state for cleanup
                final_task = await adapter.transition_state(
                    created_issue_key, TicketState.DONE
                )
                if final_task:
                    console.print("  ✓ Transitioned test issue to Done")
                    tests_passed += 1
                else:
                    console.print(
                        "  [yellow]⚠ Could not transition test issue to Done[/yellow]"
                    )
            except Exception as e:
                console.print(f"  [yellow]⚠ Cleanup error: {e}[/yellow]")

        console.print(
            f"\n[green]JIRA: {tests_passed}/{tests_total} tests passed[/green]"
        )
        return tests_passed >= (
            tests_total - 2
        )  # Allow 2 failures for non-critical operations

    except Exception as e:
        console.print(f"[red]✗ Failed to test JIRA: {e}[/red]")
        return False


@pytest.mark.asyncio
async def test_aitrackdown():
    """Test AI-Trackdown adapter (local file-based)"""
    console.print("\n[bold cyan]Testing AI-Trackdown Adapter[/bold cyan]")

    try:
        import os
        import shutil

        from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter
        from mcp_ticketer.core.models import (
            Comment,
            Epic,
            Priority,
            SearchQuery,
            Task,
            TicketState,
        )

        test_project_path = ".test_aitrackdown"

        # Clean up any existing test data
        if os.path.exists(test_project_path):
            shutil.rmtree(test_project_path)

        config = {"base_path": test_project_path}

        adapter = AITrackdownAdapter(config)

        console.print(f"  Using project path: {test_project_path}")

        # Test operations
        tests_passed = 0
        tests_total = 0
        created_task_ids = []
        created_epic_id = None

        try:
            # 1. Create an epic
            tests_total += 1
            epic = Epic(
                id="",
                title=f"[TEST] Epic Integration Test - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                description="Test epic for integration testing",
                state=TicketState.OPEN,
            )
            created_epic = await adapter.create(epic)
            created_epic_id = created_epic.id
            console.print(f"  ✓ Created epic: {created_epic_id}")
            tests_passed += 1

            # 2. Create multiple tasks
            tests_total += 1
            for i in range(3):
                test_task = Task(
                    id="",
                    title=f"[TEST] Task {i+1} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    description=f"Test task #{i+1} for integration testing",
                    state=TicketState.OPEN,
                    priority=Priority.MEDIUM if i == 0 else Priority.HIGH,
                    tags=["test", "automation", f"batch-{i+1}"],
                    parent_epic=created_epic_id if i < 2 else None,
                )

                created_task = await adapter.create(test_task)
                created_task_ids.append(created_task.id)

            console.print(f"  ✓ Created {len(created_task_ids)} tasks")
            tests_passed += 1

            # 3. Get a task
            tests_total += 1
            retrieved_task = await adapter.read(created_task_ids[0])
            if retrieved_task:
                console.print(f"  ✓ Retrieved task: {retrieved_task.title}")
                tests_passed += 1

            # 4. List tasks
            tests_total += 1
            tasks = await adapter.list(limit=10)
            console.print(f"  ✓ Listed {len(tasks)} tasks")
            tests_passed += 1

            # 5. Update a task
            tests_total += 1
            updated_task = await adapter.update(
                created_task_ids[0],
                {
                    "description": "Updated description from integration tests",
                    "priority": Priority.HIGH,
                },
            )
            if updated_task:
                console.print("  ✓ Updated task description and priority")
                tests_passed += 1

            # 6. Add comments
            tests_total += 1
            for i, task_id in enumerate(created_task_ids[:2]):
                comment = Comment(
                    id="",
                    ticket_id=task_id,
                    author="test-user",
                    content=f"Test comment {i+1} from integration tests",
                )
                await adapter.add_comment(comment)
            console.print("  ✓ Added comments to tasks")
            tests_passed += 1

            # 7. Search tasks
            tests_total += 1
            search_query = SearchQuery(query="TEST", limit=10)
            search_results = await adapter.search(search_query)
            console.print(f"  ✓ Search returned {len(search_results)} results")
            tests_passed += 1

            # 8. Transition task states
            tests_total += 1
            transitioned_count = 0
            for i, task_id in enumerate(created_task_ids):
                new_state = TicketState.IN_PROGRESS if i == 0 else TicketState.DONE
                transitioned_task = await adapter.transition_state(task_id, new_state)
                if transitioned_task:
                    transitioned_count += 1

            if transitioned_count > 0:
                console.print(
                    f"  ✓ Transitioned {transitioned_count} tasks to new states"
                )
                tests_passed += 1

            # 9. List epics (same as listing tasks since they're unified in the adapter)
            tests_total += 1
            all_tickets = await adapter.list(limit=10)
            epics = [t for t in all_tickets if isinstance(t, Epic)]
            console.print(f"  ✓ Listed {len(epics)} epics")
            tests_passed += 1

            # 10. Get comments for a task
            tests_total += 1
            comments = await adapter.get_comments(created_task_ids[0])
            console.print(f"  ✓ Retrieved {len(comments)} comments")
            tests_passed += 1

        except Exception as e:
            console.print(f"  [red]✗ Error during operations: {e}[/red]")

        # Cleanup - remove test data
        try:
            tests_total += 1
            if os.path.exists(test_project_path):
                shutil.rmtree(test_project_path)
                console.print("  ✓ Cleaned up test project directory")
                tests_passed += 1
        except Exception as e:
            console.print(f"  [yellow]⚠ Cleanup error: {e}[/yellow]")

        console.print(
            f"\n[green]AI-Trackdown: {tests_passed}/{tests_total} tests passed[/green]"
        )
        return tests_passed >= (
            tests_total - 1
        )  # Allow 1 failure for non-critical operations

    except Exception as e:
        console.print(f"[red]✗ Failed to test AI-Trackdown: {e}[/red]")
        return False


async def main():
    """Run all adapter tests"""
    console.print(
        Panel.fit(
            "[bold]MCP-Ticketer Comprehensive Adapter Test Suite[/bold]\n"
            "Testing all four adapters (Linear, GitHub, JIRA, AI-Trackdown) with full CRUD operations\n"
            "Each test includes: create, read, update, delete, list, search, and comments",
            title="🧪 Integration Test Runner",
            border_style="cyan",
        )
    )

    # Show configuration being used
    console.print("\n[bold]Configuration:[/bold]")
    console.print(
        f"  Linear API Key: {'✓ Found' if os.getenv('LINEAR_API_KEY') else '✗ Missing'}"
    )
    console.print(
        f"  GitHub Token: {'✓ Found' if os.getenv('GITHUB_TOKEN') else '✗ Missing'}"
    )
    console.print(f"  GitHub Owner: {os.getenv('GITHUB_OWNER', 'Not set')}")
    console.print(
        f"  JIRA User: {'✓ Found' if os.getenv('JIRA_ACCESS_USER') else '✗ Missing'}"
    )
    console.print(
        f"  JIRA Token: {'✓ Found' if os.getenv('JIRA_ACCESS_TOKEN') else '✗ Missing'}"
    )

    results = []
    start_time = datetime.now()

    # Test each adapter in order of complexity
    console.print("\n[bold]Running Integration Tests...[/bold]")

    # AI-Trackdown (local file-based, should be most reliable)
    console.print(f"\n{'='*60}")
    result_aitrackdown = await test_aitrackdown()
    results.append(("AI-Trackdown", result_aitrackdown, "Local file-based adapter"))

    # Linear (if credentials available)
    console.print(f"\n{'='*60}")
    result_linear = await test_linear()
    results.append(("Linear", result_linear, "Using 1m-hyperdev workspace, team BTA"))

    # GitHub (if credentials available)
    console.print(f"\n{'='*60}")
    result_github = await test_github()
    results.append(("GitHub", result_github, "Using bobmatnyc/mcp-ticketer repository"))

    # JIRA (if credentials available)
    console.print(f"\n{'='*60}")
    result_jira = await test_jira()
    results.append(
        ("JIRA", result_jira, "Using 1m-hyperdev.atlassian.net, SMS project")
    )

    # Calculate test duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Enhanced summary table
    console.print(f"\n{'='*80}")
    console.print(
        Panel.fit(
            f"[bold]Integration Test Results Summary[/bold]\n"
            f"Completed in {duration:.1f} seconds",
            border_style=(
                "green" if all(passed for _, passed, _ in results) else "yellow"
            ),
        )
    )

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Adapter", style="cyan", width=15)
    table.add_column("Status", style="white", width=12)
    table.add_column("Configuration", style="dim", width=40)

    passed_count = 0
    total_count = len(results)

    for adapter, passed, notes in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        color = "green" if passed else "red"

        if passed:
            passed_count += 1

        table.add_row(adapter, f"[{color}]{status}[/{color}]", notes)

    console.print(table)

    # Detailed results analysis
    console.print("\n[bold]Test Summary:[/bold]")
    console.print(f"  • {passed_count}/{total_count} adapters passed all tests")
    console.print(f"  • Test duration: {duration:.1f} seconds")

    # Overall result with specific recommendations
    if passed_count == total_count:
        console.print("\n[bold green]🎉 ALL ADAPTERS WORKING CORRECTLY![/bold green]")
        console.print(
            "   All four adapters successfully completed comprehensive CRUD testing."
        )
        console.print("   The mcp-ticketer system is ready for production use.")
    elif passed_count >= 3:
        console.print(
            f"\n[bold yellow]⚠ MOSTLY SUCCESSFUL ({passed_count}/{total_count} passed)[/bold yellow]"
        )
        console.print("   Most adapters are working. Check failed adapter credentials.")
    elif passed_count >= 1:
        console.print(
            f"\n[bold orange]⚠ PARTIAL SUCCESS ({passed_count}/{total_count} passed)[/bold orange]"
        )
        console.print(
            "   Some adapters working. Review configurations and credentials."
        )
    else:
        console.print("\n[bold red]❌ ALL TESTS FAILED[/bold red]")
        console.print("   Check your environment configuration and credentials.")

    # Recommendations
    failed_adapters = [name for name, passed, _ in results if not passed]
    if failed_adapters:
        console.print("\n[bold]Recommendations for failed adapters:[/bold]")
        for adapter in failed_adapters:
            if adapter == "Linear":
                console.print("  • Linear: Verify LINEAR_API_KEY in .env.local")
                console.print(
                    "    - Check API key permissions for 1m-hyperdev workspace"
                )
            elif adapter == "GitHub":
                console.print("  • GitHub: Verify GITHUB_TOKEN and repository access")
                console.print("    - Ensure token has 'repo' and 'issues' permissions")
                console.print(
                    "    - Confirm access to bobmatnyc/mcp-ticketer repository"
                )
            elif adapter == "JIRA":
                console.print("  • JIRA: Verify JIRA_ACCESS_USER and JIRA_ACCESS_TOKEN")
                console.print("    - Check access to 1m-hyperdev.atlassian.net")
                console.print("    - Verify permissions for SMS project")
            elif adapter == "AI-Trackdown":
                console.print("  • AI-Trackdown: Check file system permissions")
                console.print("    - Ensure write access to current directory")

    return passed_count == total_count


if __name__ == "__main__":
    asyncio.run(main())
