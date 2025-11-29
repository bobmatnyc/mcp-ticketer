#!/usr/bin/env python3
"""
Project Status Analysis Examples

This file demonstrates how to use the project status analysis features
in mcp-ticketer. These examples are runnable and can be used as templates
for your own workflows.

Requirements:
- mcp-ticketer installed
- MCP server configured
- Project with tickets in Linear/GitHub/JIRA
- Python 3.9+

Setup:
    pip install mcp-ticketer
    mcp-ticketer init --adapter linear  # or github, jira, aitrackdown

    # Set default project (optional but recommended)
    # Via Python:
    from mcp_ticketer.core.project_config import ConfigResolver
    # Or via CLI:
    # mcp-ticketer config set-project YOUR_PROJECT_ID

Usage:
    python examples/project_status_examples.py
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any


# Example 1: Basic Project Status
async def example_basic_project_status():
    """
    Get basic project health assessment.

    This example shows how to analyze a project and get:
    - Overall health status
    - Ticket breakdown by state
    - Recommended next actions

    Returns:
        Project status dictionary
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Project Status")
    print("=" * 70)

    # Import the MCP tool (this simulates calling via MCP)
    # In real MCP usage, you'd call this through your AI client
    from mcp_ticketer.mcp.server.tools.project_status_tools import project_status

    # Get project status (uses default_project from config)
    # If no default is set, pass project_id explicitly:
    # status = await project_status(project_id="your-project-id")
    status = await project_status()

    # Check if successful
    if status["status"] == "error":
        print(f"❌ Error: {status['error']}")
        if "message" in status:
            print(f"   {status['message']}")
        return None

    # Display overall health
    health_emoji = {
        "on_track": "✅",
        "at_risk": "⚡",
        "off_track": "⚠️",
    }
    emoji = health_emoji.get(status["health"], "❓")

    print(f"\n{emoji} Project Health: {status['health'].upper()}")
    print(f"Project: {status['project_name']} (ID: {status['project_id']})")

    # Display health metrics
    metrics = status["health_metrics"]
    print(f"\nHealth Metrics:")
    print(f"  Overall Score: {metrics['health_score']:.2f}/1.00")
    print(f"  Completion Rate: {metrics['completion_rate']:.1%}")
    print(f"  Progress Rate: {metrics['progress_rate']:.1%}")
    print(f"  Blocked Rate: {metrics['blocked_rate']:.1%}")
    print(f"  Critical Tickets: {metrics['critical_count']}")
    print(f"  High Priority: {metrics['high_count']}")

    # Display ticket summary
    summary = status["summary"]
    print(f"\nTicket Summary:")
    print(f"  Total: {summary['total']}")
    for state, count in summary.items():
        if state != "total" and count > 0:
            print(f"  {state.replace('_', ' ').title()}: {count}")

    # Display recommendations
    print(f"\n💡 Recommendations:")
    for rec in status["recommendations"]:
        print(f"  • {rec}")

    return status


# Example 2: Track Project Updates Over Time
async def example_project_updates():
    """
    Create and track project status updates.

    Shows how to:
    - Create status update with health indicator
    - List historical updates
    - Track project health over time

    Note: This requires project_update_create tool (available in Linear, GitHub V2, Asana)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Track Project Updates Over Time")
    print("=" * 70)

    from mcp_ticketer.mcp.server.tools.project_status_tools import project_status

    try:
        from mcp_ticketer.mcp.server.tools.project_update_tools import (
            project_update_create,
            project_update_list,
        )
    except ImportError:
        print("⚠️ Project updates not available in this adapter")
        return None

    # Get current status
    status = await project_status()

    if status["status"] == "error":
        print(f"❌ Cannot analyze project: {status['error']}")
        return None

    # Create a status update based on current health
    print(f"\n📝 Creating project status update...")

    # Build update body from analysis
    summary = status["summary"]
    metrics = status["health_metrics"]

    update_body = f"""Project Status Update - {datetime.now().strftime('%Y-%m-%d')}

**Health**: {status['health']} (score: {metrics['health_score']:.2f}/1.00)

**Progress**:
- Total tickets: {summary['total']}
- Completed: {summary.get('done', 0)} ({metrics['completion_rate']:.0%})
- In Progress: {summary.get('in_progress', 0)}
- Blocked: {summary.get('blocked', 0)}

**Top Priorities**:
"""

    for i, ticket in enumerate(status["recommended_next"], 1):
        update_body += f"{i}. {ticket['ticket_id']}: {ticket['title']} ({ticket['priority']})\n"

    update_body += "\n**Recommendations**:\n"
    for rec in status["recommendations"]:
        update_body += f"- {rec}\n"

    # Create the update
    try:
        update = await project_update_create(
            project_id=status["project_id"],
            body=update_body,
            health=status["health"],
        )

        if update["status"] == "completed":
            print(f"✅ Update created: {update['update']['id']}")
        else:
            print(f"❌ Failed to create update: {update.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"⚠️ Could not create update: {e}")

    # List recent updates
    print(f"\n📋 Recent Project Updates:")
    try:
        updates = await project_update_list(project_id=status["project_id"], limit=5)

        if updates["status"] == "completed":
            for i, update in enumerate(updates["updates"], 1):
                created = update.get("created_at", "Unknown")
                health = update.get("health", "unknown")
                print(f"\n{i}. Update {update['id']} ({created})")
                print(f"   Health: {health}")
                body_preview = update.get("body", "")[:100]
                print(f"   {body_preview}...")
        else:
            print(f"⚠️ Could not list updates: {updates.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"⚠️ Could not list updates: {e}")

    return status


# Example 3: Dependency Analysis
async def example_dependency_analysis():
    """
    Analyze project dependencies and critical path.

    Demonstrates:
    - Identifying blockers
    - Finding critical path items
    - Detecting dependency depth
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Dependency Analysis")
    print("=" * 70)

    from mcp_ticketer.mcp.server.tools.project_status_tools import project_status

    status = await project_status()

    if status["status"] == "error":
        print(f"❌ Error: {status['error']}")
        return None

    # Analyze critical path
    critical_path = status["critical_path"]
    print(f"\n🛣️ Critical Path Analysis:")
    print(f"  Length: {len(critical_path)} tickets")

    if critical_path:
        print(f"\n  Dependency Chain:")
        for i, ticket_id in enumerate(critical_path):
            print(f"    {i + 1}. {ticket_id}")
            if i < len(critical_path) - 1:
                print(f"       ↓ blocks")
        print(
            f"\n  ⏱️ Impact: Delays in critical path directly affect project timeline"
        )
    else:
        print(f"  ✅ No dependency chain (tickets are independent)")

    # Analyze blockers
    blockers = status["blockers"]
    print(f"\n🚧 Blocker Analysis:")
    print(f"  Total active blockers: {len(blockers)}")

    if blockers:
        print(f"\n  Top Blockers (by impact):")
        for i, blocker in enumerate(blockers[:5], 1):
            print(f"\n  {i}. {blocker['ticket_id']}: {blocker['title']}")
            print(f"     State: {blocker['state']}")
            print(f"     Priority: {blocker['priority']}")
            print(f"     Blocks {blocker['blocks_count']} ticket(s):")
            for blocked in blocker["blocks"][:3]:  # Show first 3
                print(f"       - {blocked}")
            if len(blocker["blocks"]) > 3:
                print(f"       ... and {len(blocker['blocks']) - 3} more")

        # Calculate blocker impact
        total_blocked = sum(b["blocks_count"] for b in blockers)
        print(f"\n  📊 Blocker Impact:")
        print(f"     {total_blocked} tickets are waiting on blockers")
        print(f"     Resolving top blocker would unblock {blockers[0]['blocks_count']} tickets")
    else:
        print(f"  ✅ No active blockers - work is flowing smoothly")

    # Dependency patterns
    print(f"\n🔍 Dependency Insights:")
    if critical_path and blockers:
        print(
            f"  ⚠️ High dependency complexity - careful coordination needed"
        )
    elif critical_path:
        print(f"  📌 Sequential work - focus on maintaining critical path flow")
    elif blockers:
        print(f"  🚦 Some bottlenecks - resolve blockers to improve flow")
    else:
        print(f"  ✨ Low dependency complexity - high parallelization potential")

    return status


# Example 4: PM Agent Workflow
async def example_pm_agent_workflow():
    """
    Complete PM agent workflow using project status.

    Full workflow showing:
    - Daily standup health check
    - Identify blockers
    - Generate action items
    - Work assignment recommendations
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: PM Agent Daily Workflow")
    print("=" * 70)

    from mcp_ticketer.mcp.server.tools.project_status_tools import project_status

    # Step 1: Get project status
    print(f"\n📊 Step 1: Analyzing Project Health...")
    status = await project_status()

    if status["status"] == "error":
        print(f"❌ Error: {status['error']}")
        return None

    # Step 2: Daily Standup Summary
    print(f"\n" + "=" * 70)
    print(f"DAILY STANDUP - {datetime.now().strftime('%Y-%m-%d')}")
    print(f"=" * 70)

    # Health overview
    health_emoji = {"on_track": "✅", "at_risk": "⚡", "off_track": "⚠️"}
    emoji = health_emoji[status["health"]]

    print(f"\n{emoji} Overall Health: {status['health'].upper()}")
    print(f"Project: {status['project_name']}")

    metrics = status["health_metrics"]
    summary = status["summary"]

    print(f"\n📈 Progress:")
    print(f"  Completion: {metrics['completion_rate']:.0%} ({summary.get('done', 0)}/{summary['total']} tickets)")
    print(f"  In Progress: {summary.get('in_progress', 0)} tickets")
    print(f"  Blocked: {summary.get('blocked', 0)} tickets")
    print(f"  Health Score: {metrics['health_score']:.2f}/1.00")

    # Step 3: Blocker Review
    print(f"\n🚧 Step 2: Blocker Review")
    blockers = status["blockers"]

    if blockers:
        print(f"  {len(blockers)} active blocker(s) identified:")
        for i, blocker in enumerate(blockers[:3], 1):
            print(f"\n  {i}. {blocker['ticket_id']}: {blocker['title']}")
            print(f"     Priority: {blocker['priority']}, State: {blocker['state']}")
            print(f"     Blocking: {blocker['blocks_count']} ticket(s)")

        # Action item for blockers
        print(f"\n  ⚡ ACTION: Resolve {blockers[0]['ticket_id']} to unblock {blockers[0]['blocks_count']} tickets")
    else:
        print(f"  ✅ No blockers - work flowing smoothly")

    # Step 4: Work Priorities
    print(f"\n🎯 Step 3: Today's Priorities")
    recommended = status["recommended_next"]

    if recommended:
        print(f"  Top {len(recommended)} tickets to focus on:\n")
        for i, ticket in enumerate(recommended, 1):
            print(f"  {i}. {ticket['ticket_id']}: {ticket['title']}")
            print(f"     Priority: {ticket['priority']}")
            print(f"     Reason: {ticket['reason']}")
            if ticket["blocks"]:
                print(f"     Unblocks: {', '.join(ticket['blocks'])}")
            print()
    else:
        print(f"  ℹ️ No actionable tickets (all work in progress or complete)")

    # Step 5: Team Workload
    print(f"\n👥 Step 4: Team Workload Distribution")
    work_dist = status["work_distribution"]

    # Sort by total workload
    sorted_assignees = sorted(
        work_dist.items(), key=lambda x: x[1].get("total", 0), reverse=True
    )

    for assignee, workload in sorted_assignees:
        if assignee == "unassigned":
            print(f"\n  ⚠️ {assignee}: {workload['total']} ticket(s) need assignment")
        else:
            in_progress = workload.get("in_progress", 0)
            total = workload["total"]
            print(f"\n  • {assignee}: {in_progress}/{total} in progress")

            # Show state breakdown for this assignee
            states = {k: v for k, v in workload.items() if k != "total" and v > 0}
            if states:
                state_summary = ", ".join(f"{k}: {v}" for k, v in states.items())
                print(f"    ({state_summary})")

    # Check for workload imbalance
    if len(work_dist) > 1:
        ticket_counts = [w.get("total", 0) for w in work_dist.values()]
        max_tickets = max(ticket_counts)
        min_tickets = min(ticket_counts)
        if max_tickets > min_tickets * 2:
            print(f"\n  ⚖️ NOTICE: Workload imbalance detected - consider redistribution")

    # Step 6: Recommendations
    print(f"\n💡 Step 5: Recommendations")
    for rec in status["recommendations"]:
        print(f"  • {rec}")

    # Step 7: Summary Action Items
    print(f"\n" + "=" * 70)
    print(f"ACTION ITEMS FOR TODAY")
    print(f"=" * 70)

    action_count = 1

    # Actions from blockers
    if blockers:
        print(f"\n{action_count}. CRITICAL: Resolve blocker {blockers[0]['ticket_id']}")
        action_count += 1

    # Actions from recommendations
    if recommended:
        print(f"\n{action_count}. Work on priority ticket {recommended[0]['ticket_id']}")
        action_count += 1

    # Actions from health status
    if status["health"] == "off_track":
        print(f"\n{action_count}. URGENT: Address project health issues")
        action_count += 1

    # Actions from workload
    unassigned = work_dist.get("unassigned", {}).get("total", 0)
    if unassigned > 0:
        print(f"\n{action_count}. Assign {unassigned} unassigned ticket(s)")
        action_count += 1

    if action_count == 1:
        print(f"\n✅ No urgent actions - continue current work")

    print(f"\n" + "=" * 70)

    return status


# Example 5: Sprint Planning
async def example_sprint_planning():
    """
    Use project status for sprint planning.

    Shows how to:
    - Assess current sprint health
    - Identify carryover items
    - Plan next sprint based on capacity
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Sprint Planning")
    print("=" * 70)

    from mcp_ticketer.mcp.server.tools.project_status_tools import project_status

    # Get current project status
    status = await project_status()

    if status["status"] == "error":
        print(f"❌ Error: {status['error']}")
        return None

    # Sprint Configuration
    SPRINT_LENGTH_DAYS = 14
    TEAM_CAPACITY = {
        "alice@example.com": 60,  # 60 hours capacity
        "bob@example.com": 60,
        "charlie@example.com": 40,  # Part-time
    }

    print(f"\n🏃 Sprint Planning Session")
    print(f"Sprint Length: {SPRINT_LENGTH_DAYS} days")
    print(f"Team Size: {len(TEAM_CAPACITY)} members")
    print(f"Total Capacity: {sum(TEAM_CAPACITY.values())} hours")

    # Analyze current sprint
    print(f"\n📊 Current Sprint Analysis:")
    summary = status["summary"]
    metrics = status["health_metrics"]

    total = summary["total"]
    completed = summary.get("done", 0)
    in_progress = summary.get("in_progress", 0)
    blocked = summary.get("blocked", 0)

    if total > 0:
        velocity = completed / total
        print(f"  Velocity: {velocity:.0%} ({completed}/{total} completed)")
        print(f"  Carryover: {in_progress} tickets in progress")
        print(f"  Blocked: {blocked} tickets need attention")
    else:
        print(f"  No tickets in current sprint")
        velocity = 0

    # Health assessment
    print(f"\n🏥 Sprint Health: {status['health'].upper()}")
    print(f"  Health Score: {metrics['health_score']:.2f}/1.00")
    print(f"  Completion Rate: {metrics['completion_rate']:.0%}")
    print(f"  Blocked Rate: {metrics['blocked_rate']:.0%}")

    # Risk factors
    print(f"\n⚠️ Sprint Risks:")
    risks = []

    if velocity < 0.5 and total > 0:
        risks.append("Low velocity - may need to reduce next sprint commitment")

    if blocked > 0:
        risks.append(f"{blocked} blocked tickets - resolve before next sprint")

    if metrics["blocked_rate"] > 0.3:
        risks.append("High blocker rate - process issues need addressing")

    if status["health"] == "off_track":
        risks.append("Project off track - requires immediate intervention")

    if risks:
        for risk in risks:
            print(f"  • {risk}")
    else:
        print(f"  ✅ No major risks identified")

    # Next Sprint Planning
    print(f"\n📋 Next Sprint Recommendations:")

    # Recommend tickets based on priority and dependencies
    recommended = status["recommended_next"]

    if recommended:
        print(f"\n  Top Priority Tickets:")
        sprint_tickets = []

        for i, ticket in enumerate(recommended[:10], 1):  # Top 10
            print(f"\n  {i}. {ticket['ticket_id']}: {ticket['title']}")
            print(f"     Priority: {ticket['priority']}")
            print(f"     Reason: {ticket['reason']}")

            if ticket["blocks"]:
                print(f"     Unblocks: {', '.join(ticket['blocks'])}")

            sprint_tickets.append(ticket["ticket_id"])

        # Capacity planning
        print(f"\n  📊 Capacity Planning:")
        print(f"     Team capacity: {sum(TEAM_CAPACITY.values())} hours")
        print(f"     Recommended tickets: {len(sprint_tickets)}")

        # Rough estimate (assume 8 hours per ticket average)
        estimated_hours = len(sprint_tickets) * 8
        capacity_usage = (
            estimated_hours / sum(TEAM_CAPACITY.values())
            if sum(TEAM_CAPACITY.values()) > 0
            else 0
        )

        print(f"     Estimated effort: ~{estimated_hours} hours")
        print(f"     Capacity usage: ~{capacity_usage:.0%}")

        if capacity_usage > 1.0:
            print(f"     ⚠️ WARNING: Over capacity - reduce ticket count")
        elif capacity_usage < 0.5:
            print(
                f"     ℹ️ NOTE: Under capacity - consider adding more tickets"
            )
        else:
            print(f"     ✅ Capacity looks good")

    else:
        print(f"  ℹ️ No actionable tickets available for next sprint")

    # Work distribution recommendations
    print(f"\n  👥 Team Assignment Recommendations:")

    work_dist = status["work_distribution"]

    for member, capacity in TEAM_CAPACITY.items():
        current_workload = work_dist.get(member, {}).get("total", 0)
        print(f"     {member}:")
        print(f"       Current: {current_workload} tickets")
        print(f"       Capacity: {capacity} hours")

        # Suggest tickets based on capacity
        if current_workload == 0:
            print(f"       Suggestion: Can take 2-3 new tickets")
        elif current_workload < 3:
            print(f"       Suggestion: Can take 1-2 more tickets")
        else:
            print(f"       Suggestion: Currently at capacity")

    # Summary
    print(f"\n" + "=" * 70)
    print(f"SPRINT PLANNING SUMMARY")
    print(f"=" * 70)

    print(f"\nCurrent Sprint:")
    print(f"  ✅ Completed: {completed} tickets")
    print(f"  🔄 Carryover: {in_progress} tickets")
    print(f"  ⚠️ Blocked: {blocked} tickets")

    print(f"\nNext Sprint:")
    if recommended:
        print(f"  🎯 Recommended: {len(sprint_tickets)} tickets")
        print(f"  ⏱️ Estimated: ~{len(sprint_tickets) * 8} hours")
        print(f"  💪 Team Capacity: {sum(TEAM_CAPACITY.values())} hours")
    else:
        print(f"  ℹ️ No tickets ready for sprint")

    print(f"\nKey Actions:")
    print(f"  1. Review and finalize sprint ticket selection")
    print(f"  2. Resolve {len(status['blockers'])} blocker(s) before sprint start")
    print(f"  3. Balance workload across team members")
    print(f"  4. Set sprint goals and success criteria")

    print(f"\n" + "=" * 70)

    return status


# Main execution
async def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("PROJECT STATUS ANALYSIS EXAMPLES")
    print("=" * 70)
    print("\nThis script demonstrates project status analysis features.")
    print("Make sure you have configured mcp-ticketer with a default project.")
    print("\nPress Ctrl+C to skip to next example.\n")

    examples = [
        ("Basic Project Status", example_basic_project_status),
        ("Track Project Updates", example_project_updates),
        ("Dependency Analysis", example_dependency_analysis),
        ("PM Agent Workflow", example_pm_agent_workflow),
        ("Sprint Planning", example_sprint_planning),
    ]

    for name, example_func in examples:
        try:
            print(f"\n{'=' * 70}")
            print(f"Running: {name}")
            print(f"{'=' * 70}")
            await example_func()
            print(f"\n✅ {name} completed")

            # Pause between examples
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            print(f"\n⏭️ Skipping to next example...")
            continue
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            import traceback

            traceback.print_exc()
            continue

    print("\n" + "=" * 70)
    print("ALL EXAMPLES COMPLETED")
    print("=" * 70)
    print("\nFor more information:")
    print("  - Full Guide: docs/PROJECT_STATUS.md")
    print("  - README: README.md#-project-status-analysis")
    print("  - API Docs: https://mcp-ticketer.readthedocs.io")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Run the examples
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Examples interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
