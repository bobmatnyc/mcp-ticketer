# Project Status Analysis Guide

Comprehensive guide to using project status analysis for intelligent project health assessment and work planning.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Health Assessment](#health-assessment)
  - [Dependency Analysis](#dependency-analysis)
  - [Smart Recommendations](#smart-recommendations)
- [MCP Tools Reference](#mcp-tools-reference)
  - [project_status](#project_status)
- [Workflows](#workflows)
  - [PM Agent Workflow](#pm-agent-workflow)
  - [Project Health Monitoring](#project-health-monitoring)
  - [Sprint Planning](#sprint-planning)
- [Advanced Usage](#advanced-usage)
  - [Custom Health Criteria](#custom-health-criteria)
  - [Dependency Graph Analysis](#dependency-graph-analysis)
  - [Integrating with Ticketing Systems](#integrating-with-ticketing-systems)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Examples](#examples)

## Overview

The Project Status Analysis feature provides comprehensive project/epic analysis with automated health assessment, dependency tracking, and intelligent work recommendations. It's designed for PM agents and product managers who need quick, actionable insights into project health and next steps.

### What is Project Status Analysis?

Project Status Analysis automatically evaluates your project by:

1. **Analyzing ticket states** - Tracks completion, progress, and blockers
2. **Building dependency graphs** - Parses ticket descriptions for dependencies
3. **Scoring project health** - Multi-factor weighted scoring (completion, progress, blockers, priorities)
4. **Recommending next actions** - Top 3 tickets to start based on priority, impact, and dependencies
5. **Identifying risks** - Highlights blockers, critical path bottlenecks, and workload imbalances

### Why Use It?

- **Save Time**: Get instant project insights instead of manually reviewing tickets
- **Make Better Decisions**: Data-driven recommendations for ticket prioritization
- **Prevent Issues**: Early warning system for project risks (blockers, delays, imbalances)
- **Optimize Flow**: Identify critical path and high-impact work
- **Automate Standups**: Generate daily standup reports automatically

### When to Use It

**Daily Operations:**
- Morning standup prep
- Sprint planning
- Daily health checks
- Work assignment

**Project Management:**
- Sprint reviews
- Stakeholder updates
- Risk assessment
- Resource allocation

**Team Coordination:**
- Identifying blockers
- Balancing workload
- Tracking progress
- Dependency management

## Quick Start

### 30-Second Example

```python
# Get project status (uses default_project from config)
status = await project_status()

# Check health
print(f"Health: {status['health']}")  # on_track, at_risk, or off_track

# See what to work on next
for ticket in status['recommended_next']:
    print(f"{ticket['ticket_id']}: {ticket['reason']}")
```

### Setup

1. **Configure default project** (one-time setup):

```python
# Set default project for automatic analysis
result = await config_set_default_project(project_id="eac28953c267")
```

2. **Run analysis**:

```python
# Analyze default project
status = await project_status()

# Or analyze specific project
status = await project_status(project_id="proj-123")
```

3. **Use the insights**:

```python
# Check health
if status['health'] == 'off_track':
    print("⚠️ Immediate action needed!")

# Get recommendations
for rec in status['recommendations']:
    print(rec)

# Find blockers
for blocker in status['blockers']:
    print(f"Resolve {blocker['ticket_id']} - blocking {blocker['blocks_count']} tickets")
```

## Core Concepts

### Health Assessment

Project health is automatically calculated using a **weighted scoring system** that considers multiple factors:

#### Health Score Formula

```
health_score = (
    completion_rate × 0.30 +
    progress_rate × 0.25 +
    blocker_score × 0.30 +
    priority_score × 0.15
)
```

**Components:**

1. **Completion Rate (30% weight)**
   - Percentage of tickets in DONE, CLOSED, or TESTED states
   - Higher is better
   - Formula: `completed_tickets / total_tickets`

2. **Progress Rate (25% weight)**
   - Percentage of tickets in IN_PROGRESS, READY, or TESTED states
   - Sweet spot around 40-60% (too high = not finishing, too low = not working)
   - Formula: `min(in_progress_tickets / total_tickets × 2, 1.0)`

3. **Blocker Score (30% weight)**
   - Inverted percentage of BLOCKED or WAITING tickets
   - Lower blockers = higher score
   - Formula: `max(0, 1.0 - (blocked_tickets / total_tickets × 2.5))`

4. **Priority Score (15% weight)**
   - Completion rate of CRITICAL and HIGH priority tickets
   - Completed = 1.0, In Progress = 0.5, Not Started = 0.0
   - Formula: `(completed_critical + 0.5 × inprogress_critical) / total_critical`

#### Health Levels

**ON_TRACK** (score ≥ 0.7 OR completion ≥ 50% with no blockers)
- ✅ Project progressing well
- No major issues
- Continue current momentum

**AT_RISK** (score 0.4-0.7)
- ⚡ Some concerns
- Monitor closely
- Address issues soon

**OFF_TRACK** (score < 0.4 OR blocked_rate ≥ 40%)
- ⚠️ Serious issues
- Immediate intervention needed
- High blocker rate or very low progress

#### Health Metrics

```python
status = await project_status()
metrics = status['health_metrics']

# Available metrics
metrics['total_tickets']       # Total ticket count
metrics['completion_rate']     # 0.0-1.0 (% done)
metrics['progress_rate']       # 0.0-1.0 (% in progress)
metrics['blocked_rate']        # 0.0-1.0 (% blocked)
metrics['critical_count']      # Number of critical tickets
metrics['high_count']          # Number of high priority tickets
metrics['health_score']        # 0.0-1.0 overall score
metrics['health_status']       # on_track, at_risk, off_track
```

### Dependency Analysis

The dependency graph is **automatically constructed** by parsing ticket titles and descriptions for reference patterns.

#### Supported Dependency Patterns

The system recognizes these patterns (case-insensitive):

**Explicit Dependencies:**
```
Depends on TICKET-123
Depends on #456
Blocked by PROJ-789
Blocked by #123
```

**Blocking Relationships:**
```
Blocks TICKET-123
Blocks #456
```

**Related References:**
```
Related to TICKET-123
Related to #456
1M-316: Implement feature (inline reference)
PROJ-789: Bug fix (inline reference)
```

**Format Support:**
- Full IDs: `TICKET-123`, `PROJ-789`, `1M-316`
- Number-only: `#123`, `#456` (inherits project prefix from current ticket)

#### Dependency Graph Features

**Critical Path:**
- Longest chain of dependencies
- Tickets on this path should be prioritized
- Delays here directly impact project timeline

**High-Impact Tickets:**
- Tickets that block the most other work
- Resolving these unblocks multiple tickets
- Automatically surfaced in recommendations

**Blocker Detection:**
- Identifies tickets in BLOCKED/WAITING states
- Shows what's blocking them
- Prioritizes resolving blockers

**Circular Dependency Handling:**
- Automatically detected and handled
- Won't cause infinite loops
- Reported in analysis

#### Graph Structure

```python
status = await project_status()

# Critical path (longest dependency chain)
critical_path = status['critical_path']
print(f"Critical path length: {len(critical_path)}")
for ticket_id in critical_path:
    print(f"  → {ticket_id}")

# Active blockers
for blocker in status['blockers']:
    print(f"{blocker['ticket_id']} blocks {blocker['blocks_count']} tickets:")
    for blocked in blocker['blocks']:
        print(f"  - {blocked}")
```

### Smart Recommendations

The recommendation engine uses **multi-factor scoring** to identify the top 3 tickets to work on next.

#### Scoring Factors

Tickets are scored based on:

1. **Priority (up to 30 points)**
   - Critical: 30 points
   - High: 20 points
   - Medium: 10 points
   - Low: 5 points

2. **Not Blocked Bonus (20 points)**
   - No blockers: +20 points
   - Has blockers: -5 points per blocker

3. **Blocks Others Bonus (up to 25 points)**
   - +5 points per ticket blocked (capped at 25)
   - High-impact work gets prioritized

4. **Critical Path Bonus (15 points)**
   - On critical path: +15 points
   - Affects overall timeline

5. **State Bonus (up to 10 points)**
   - OPEN: +10 points
   - READY: +8 points
   - WAITING: +5 points
   - BLOCKED: 0 points

#### Recommendation Format

Each recommendation includes:

```python
{
    "ticket_id": "1M-317",
    "title": "Fix authentication bug",
    "priority": "critical",
    "reason": "Critical priority, Unblocks 2 tickets, On critical path",
    "blocks": ["1M-315", "1M-316"],
    "impact_score": 75.0
}
```

**Reason field** explains WHY this ticket is recommended:
- "Critical priority" - High priority work
- "Unblocks N tickets" - Has downstream impact
- "On critical path" - Affects timeline
- "No blockers" - Can start immediately

#### Filtering Logic

Only **actionable tickets** are considered:
- States: OPEN, WAITING, BLOCKED, READY
- Excludes: IN_PROGRESS, DONE, CLOSED, TESTED

This ensures recommendations are for work that can be started, not work already being done or completed.

## MCP Tools Reference

### project_status

Analyze project/epic status and generate comprehensive work plan.

**Function Signature:**
```python
async def project_status(project_id: str | None = None) -> dict[str, Any]
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project_id` | `str` | No | Uses `default_project` from config | ID of the project/epic to analyze |

**Returns:**

Dictionary with comprehensive project analysis:

```python
{
    "status": "success",  # or "error"
    "project_id": str,
    "project_name": str,
    "health": str,  # on_track, at_risk, off_track
    "health_metrics": {
        "total_tickets": int,
        "completion_rate": float,  # 0.0-1.0
        "progress_rate": float,
        "blocked_rate": float,
        "critical_count": int,
        "high_count": int,
        "health_score": float,  # 0.0-1.0
        "health_status": str
    },
    "summary": {
        "total": int,
        "open": int,
        "in_progress": int,
        "ready": int,
        "tested": int,
        "done": int,
        "closed": int,
        "waiting": int,
        "blocked": int
    },
    "priority_summary": {
        "critical": int,
        "high": int,
        "medium": int,
        "low": int
    },
    "work_distribution": {
        "user@example.com": {
            "total": int,
            "open": int,
            "in_progress": int,
            ...
        },
        "unassigned": {...}
    },
    "recommended_next": [
        {
            "ticket_id": str,
            "title": str,
            "priority": str,
            "reason": str,
            "blocks": [str],
            "impact_score": float
        }
    ],
    "blockers": [
        {
            "ticket_id": str,
            "title": str,
            "state": str,
            "priority": str,
            "blocks_count": int,
            "blocks": [str]
        }
    ],
    "critical_path": [str],  # List of ticket IDs
    "recommendations": [str],  # Human-readable recommendations
    "timeline_estimate": {
        "days_to_completion": int | None,
        "critical_path_days": int | None,
        "risk": str
    }
}
```

**Example Usage:**

```python
# Use default project
status = await project_status()

# Analyze specific project
status = await project_status(project_id="eac28953c267")

# Check for errors
if status['status'] == 'error':
    print(f"Error: {status['error']}")
```

**Error Cases:**

```python
# No project_id and no default configured
{
    "status": "error",
    "error": "No project_id provided and no default_project configured",
    "message": "Use config_set_project to set a default project, or provide project_id parameter"
}

# Project not found
{
    "status": "error",
    "error": "Project/Epic proj-123 not found"
}

# Project has no tickets
{
    "status": "success",
    "health": "on_track",
    "message": "Project has no tickets yet",
    "recommendations": ["Project is empty - Create tickets to get started"]
}
```

## Workflows

### PM Agent Workflow

Complete daily workflow for PM agents to monitor project health and coordinate team.

#### Morning Standup Preparation

```python
async def prepare_standup():
    """Generate standup report with project insights."""

    # 1. Get project status
    status = await project_status()

    # 2. Check overall health
    health = status['health']
    emoji = {
        'on_track': '✅',
        'at_risk': '⚡',
        'off_track': '⚠️'
    }[health]

    print(f"{emoji} Project Health: {health.upper()}")
    print(f"Completion: {status['health_metrics']['completion_rate']:.0%}")
    print(f"In Progress: {status['summary'].get('in_progress', 0)} tickets")
    print()

    # 3. Identify blockers
    if status['blockers']:
        print(f"🚧 {len(status['blockers'])} Active Blockers:")
        for blocker in status['blockers'][:3]:
            print(f"  • {blocker['ticket_id']}: {blocker['title']}")
            print(f"    Blocking {blocker['blocks_count']} tickets")
        print()

    # 4. Show priorities
    print("🎯 Top Priorities:")
    for ticket in status['recommended_next']:
        print(f"  • {ticket['ticket_id']}: {ticket['title']}")
        print(f"    {ticket['reason']}")
    print()

    # 5. Team workload
    print("👥 Team Workload:")
    for assignee, workload in status['work_distribution'].items():
        if assignee != 'unassigned':
            in_prog = workload.get('in_progress', 0)
            total = workload['total']
            print(f"  • {assignee}: {in_prog}/{total} in progress")
    print()

    # 6. Recommendations
    print("💡 Recommendations:")
    for rec in status['recommendations']:
        print(f"  • {rec}")

    return status
```

#### Daily Health Monitoring

```python
async def monitor_health():
    """Track project health over time."""

    status = await project_status()

    # Record metrics
    metrics = {
        'timestamp': datetime.now().isoformat(),
        'health': status['health'],
        'health_score': status['health_metrics']['health_score'],
        'completion_rate': status['health_metrics']['completion_rate'],
        'blocked_rate': status['health_metrics']['blocked_rate'],
        'total_tickets': status['summary']['total']
    }

    # Check for critical issues
    if status['health'] == 'off_track':
        await send_alert(
            f"⚠️ Project OFF TRACK - Health score: {metrics['health_score']:.2f}"
        )

    # Check for blockers
    if len(status['blockers']) > 3:
        await send_alert(
            f"🚧 {len(status['blockers'])} blockers detected - Immediate action needed"
        )

    return metrics
```

#### Work Assignment

```python
async def assign_next_work(assignee: str):
    """Intelligently assign next ticket to team member."""

    # Get recommendations
    status = await project_status()

    if not status['recommended_next']:
        print("No actionable tickets available")
        return None

    # Get top recommendation
    next_ticket = status['recommended_next'][0]

    # Assign ticket
    result = await ticket_assign(
        ticket_id=next_ticket['ticket_id'],
        assignee=assignee,
        comment=f"Assigned based on project analysis: {next_ticket['reason']}",
        auto_transition=True  # Move to IN_PROGRESS
    )

    print(f"✅ Assigned {next_ticket['ticket_id']} to {assignee}")
    print(f"   Priority: {next_ticket['priority']}")
    print(f"   Reason: {next_ticket['reason']}")

    if next_ticket['blocks']:
        print(f"   Unblocks: {', '.join(next_ticket['blocks'])}")

    return result
```

### Project Health Monitoring

#### Automated Health Checks

```python
import asyncio
from datetime import datetime

async def continuous_monitoring(interval_minutes: int = 60):
    """Run continuous health monitoring."""

    while True:
        try:
            status = await project_status()

            # Log health metrics
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            health = status['health']
            score = status['health_metrics']['health_score']

            print(f"[{timestamp}] Health: {health} (score: {score:.2f})")

            # Alert on degradation
            if health == 'off_track':
                await alert_team(status)

        except Exception as e:
            print(f"Monitoring error: {e}")

        # Wait for next check
        await asyncio.sleep(interval_minutes * 60)
```

#### Health Trend Analysis

```python
from collections import deque
from datetime import datetime, timedelta

class HealthTrendAnalyzer:
    """Track and analyze health trends over time."""

    def __init__(self, window_days: int = 7):
        self.window_days = window_days
        self.history = deque(maxlen=window_days * 24)  # Hourly samples

    async def record_health(self):
        """Record current health metrics."""
        status = await project_status()

        self.history.append({
            'timestamp': datetime.now(),
            'health': status['health'],
            'score': status['health_metrics']['health_score'],
            'completion': status['health_metrics']['completion_rate'],
            'blocked': status['health_metrics']['blocked_rate']
        })

    def get_trend(self) -> dict:
        """Analyze health trend."""
        if len(self.history) < 2:
            return {'trend': 'insufficient_data'}

        # Get scores from last 24 hours
        cutoff = datetime.now() - timedelta(hours=24)
        recent = [h for h in self.history if h['timestamp'] > cutoff]

        if not recent:
            return {'trend': 'no_recent_data'}

        # Calculate trend
        scores = [h['score'] for h in recent]
        avg_score = sum(scores) / len(scores)

        first_score = scores[0]
        last_score = scores[-1]
        change = last_score - first_score

        trend = 'stable'
        if change > 0.1:
            trend = 'improving'
        elif change < -0.1:
            trend = 'degrading'

        return {
            'trend': trend,
            'avg_score': avg_score,
            'change_24h': change,
            'current_health': recent[-1]['health']
        }
```

### Sprint Planning

#### Sprint Capacity Planning

```python
async def plan_sprint(
    team_capacity_hours: dict[str, int],
    sprint_length_days: int = 14
):
    """Plan sprint based on project status and team capacity."""

    status = await project_status()

    # Get recommended tickets
    candidates = status['recommended_next'][:10]  # Top 10 candidates

    # Analyze team capacity
    print(f"📋 Sprint Planning ({sprint_length_days} days)")
    print(f"\n👥 Team Capacity:")
    total_capacity = sum(team_capacity_hours.values())
    print(f"  Total: {total_capacity} hours")
    for member, hours in team_capacity_hours.items():
        print(f"  {member}: {hours} hours")

    # Prioritize tickets
    print(f"\n🎯 Recommended Sprint Tickets:")
    sprint_tickets = []

    for i, ticket in enumerate(candidates, 1):
        print(f"\n{i}. {ticket['ticket_id']}: {ticket['title']}")
        print(f"   Priority: {ticket['priority']}")
        print(f"   Reason: {ticket['reason']}")

        if ticket['blocks']:
            print(f"   Unblocks: {', '.join(ticket['blocks'])}")

        sprint_tickets.append(ticket['ticket_id'])

    # Check health risks
    print(f"\n⚠️ Sprint Risks:")
    if status['blockers']:
        print(f"  • {len(status['blockers'])} blockers exist")
    if status['health'] != 'on_track':
        print(f"  • Project health is {status['health']}")

    return {
        'sprint_tickets': sprint_tickets,
        'capacity_hours': total_capacity,
        'health': status['health'],
        'risks': status['recommendations']
    }
```

#### Sprint Review Analysis

```python
async def analyze_sprint_completion():
    """Analyze sprint completion and identify carryover."""

    status = await project_status()

    # Calculate velocity
    completed = status['summary'].get('done', 0)
    in_progress = status['summary'].get('in_progress', 0)
    total = status['summary']['total']

    velocity = completed / total if total > 0 else 0

    print("📊 Sprint Review Analysis")
    print(f"\nVelocity: {velocity:.0%}")
    print(f"Completed: {completed} tickets")
    print(f"In Progress: {in_progress} tickets (carryover)")
    print(f"Total: {total} tickets")

    # Identify carryover work
    print(f"\n📦 Carryover Items:")
    # Get in-progress tickets (would need ticket_list with state filter)
    # For now, show count
    print(f"  {in_progress} tickets to carry over to next sprint")

    # Health assessment
    print(f"\n🏥 Sprint Health: {status['health']}")
    for rec in status['recommendations']:
        print(f"  • {rec}")

    return {
        'velocity': velocity,
        'completed': completed,
        'carryover': in_progress,
        'health': status['health']
    }
```

## Advanced Usage

### Custom Health Criteria

While the default health assessment works well for most projects, you can **interpret health scores** based on your team's needs.

#### Understanding Health Scores

```python
status = await project_status()
metrics = status['health_metrics']

# Get detailed breakdown
print("Health Breakdown:")
print(f"  Overall Score: {metrics['health_score']:.2f}/1.00")
print(f"  Status: {metrics['health_status']}")
print()

# Component analysis
completion = metrics['completion_rate']
progress = metrics['progress_rate']
blocked = metrics['blocked_rate']

print("Component Scores:")
print(f"  Completion: {completion:.1%} (weight: 30%)")
print(f"  Progress: {progress:.1%} (weight: 25%)")
print(f"  Blocked: {blocked:.1%} (weight: 30%, inverted)")
print(f"  Priority: (weight: 15%)")
```

#### Custom Thresholds

```python
def custom_health_assessment(status: dict) -> str:
    """Apply custom health criteria for your team."""

    metrics = status['health_metrics']

    # Your custom rules
    if metrics['blocked_rate'] > 0.5:
        return 'critical'  # Over 50% blocked = critical

    if metrics['completion_rate'] < 0.2 and metrics['progress_rate'] < 0.3:
        return 'stalled'  # Low completion AND low progress = stalled

    if metrics['completion_rate'] > 0.8:
        return 'finishing'  # Over 80% done = finishing strong

    # Fall back to default
    return status['health']
```

### Dependency Graph Analysis

#### Deep Dependency Inspection

```python
async def analyze_dependencies():
    """Deep dive into dependency structure."""

    status = await project_status()

    # Critical path analysis
    critical_path = status['critical_path']
    print(f"🛣️ Critical Path ({len(critical_path)} tickets):")
    for i, ticket_id in enumerate(critical_path):
        print(f"  {i+1}. {ticket_id}")

    # Blocker analysis
    blockers = status['blockers']
    print(f"\n🚧 Blocker Analysis:")
    print(f"  Total blockers: {len(blockers)}")

    if blockers:
        top_blocker = blockers[0]
        print(f"\n  Top Blocker: {top_blocker['ticket_id']}")
        print(f"    Blocks: {top_blocker['blocks_count']} tickets")
        print(f"    State: {top_blocker['state']}")
        print(f"    Priority: {top_blocker['priority']}")
        print(f"    Affected tickets:")
        for blocked in top_blocker['blocks']:
            print(f"      - {blocked}")

    # Calculate dependency depth
    if critical_path:
        print(f"\n📏 Dependency Metrics:")
        print(f"  Max depth: {len(critical_path)} levels")
        print(f"  Avg dependencies per ticket: {calculate_avg_deps(status):.1f}")
```

#### Detecting Dependency Cycles

```python
def detect_cycles(status: dict) -> list[list[str]]:
    """Detect circular dependencies (not common but possible)."""

    # Build adjacency list from blockers
    graph = {}
    for blocker in status['blockers']:
        ticket_id = blocker['ticket_id']
        blocks = blocker['blocks']
        graph[ticket_id] = blocks

    # DFS to detect cycles
    def has_cycle(node, visited, rec_stack):
        visited.add(node)
        rec_stack.add(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True

        rec_stack.remove(node)
        return False

    cycles = []
    visited = set()

    for node in graph:
        if node not in visited:
            if has_cycle(node, visited, set()):
                cycles.append(node)

    return cycles
```

### Integrating with Ticketing Systems

#### Linear Integration

```python
async def sync_with_linear():
    """Sync project status to Linear project updates."""

    # Get status
    status = await project_status(project_id="eac28953c267")

    # Create project update
    health_map = {
        'on_track': 'on_track',
        'at_risk': 'at_risk',
        'off_track': 'off_track'
    }

    # Build update body
    summary = status['summary']
    body = f"""Sprint Status:
- Total: {summary['total']} tickets
- Completed: {summary.get('done', 0)} ({status['health_metrics']['completion_rate']:.0%})
- In Progress: {summary.get('in_progress', 0)}
- Blocked: {summary.get('blocked', 0)}

Top Priorities:
"""

    for ticket in status['recommended_next']:
        body += f"- {ticket['ticket_id']}: {ticket['title']}\n"

    body += f"\nRecommendations:\n"
    for rec in status['recommendations']:
        body += f"- {rec}\n"

    # Create update
    update = await project_update_create(
        project_id="eac28953c267",
        body=body,
        health=health_map[status['health']]
    )

    return update
```

#### GitHub Integration

```python
async def create_github_issue_comment(issue_number: int):
    """Post project status as GitHub issue comment."""

    status = await project_status()

    # Format as markdown
    comment = f"""## Project Status Update

**Health**: {status['health'].upper()} ({status['health_metrics']['health_score']:.2f}/1.00)

### Summary
- Total: {status['summary']['total']} tickets
- Completed: {status['summary'].get('done', 0)} ({status['health_metrics']['completion_rate']:.0%})
- In Progress: {status['summary'].get('in_progress', 0)}
- Blocked: {status['summary'].get('blocked', 0)}

### Top Priorities
"""

    for ticket in status['recommended_next']:
        comment += f"1. **{ticket['ticket_id']}**: {ticket['title']} ({ticket['priority']})\n"
        comment += f"   - {ticket['reason']}\n"

    if status['blockers']:
        comment += f"\n### Blockers ({len(status['blockers'])})\n"
        for blocker in status['blockers'][:5]:
            comment += f"- **{blocker['ticket_id']}**: Blocking {blocker['blocks_count']} tickets\n"

    comment += f"\n### Recommendations\n"
    for rec in status['recommendations']:
        comment += f"- {rec}\n"

    # Post comment using GitHub API
    # (Implementation depends on your GitHub adapter)

    return comment
```

## Troubleshooting

### Common Issues

#### "No project_id provided and no default_project configured"

**Problem**: Calling `project_status()` without setting a default project.

**Solution**:
```python
# Set default project
await config_set_default_project(project_id="your-project-id")

# Or pass project_id explicitly
status = await project_status(project_id="your-project-id")
```

#### "Project/Epic not found"

**Problem**: Invalid project ID or insufficient permissions.

**Solutions**:
1. Verify project ID is correct
2. Check adapter credentials have access to project
3. For Linear: Use project slug ID, short ID, or UUID

```python
# Try different ID formats
status = await project_status(project_id="eac28953c267")  # UUID
status = await project_status(project_id="mcp-ticketer-eac28953c267")  # Slug ID
```

#### "Project has no tickets yet"

**Problem**: Project exists but has no child issues/tickets.

**Solutions**:
1. Create tickets in the project
2. Link existing tickets to the epic/project
3. Verify project is properly configured in ticketing system

#### Empty Recommendations

**Problem**: `recommended_next` is empty.

**Causes**:
- All tickets are DONE, CLOSED, or IN_PROGRESS
- No actionable tickets (everything blocked or completed)

**Solutions**:
1. Check ticket states: `status['summary']`
2. Review blockers: `status['blockers']`
3. Create new tickets if project is complete

#### Low Health Score Despite Good Progress

**Problem**: Health score is low even though work is progressing.

**Causes**:
- High blocker rate (30% weight)
- Low priority completion
- Too many tickets in progress (not finishing)

**Solutions**:
```python
# Analyze components
metrics = status['health_metrics']

if metrics['blocked_rate'] > 0.3:
    print("Issue: Too many blocked tickets")
    # Focus on resolving blockers

if metrics['progress_rate'] > 0.6 and metrics['completion_rate'] < 0.2:
    print("Issue: Starting work but not finishing")
    # Focus on completing in-progress work
```

### Performance Issues

#### Slow Analysis on Large Projects

**Problem**: Analysis takes too long for projects with 100+ tickets.

**Solutions**:
1. The analysis is asynchronous and should handle large projects
2. Check network latency to ticketing system
3. Consider caching project data

```python
# If you need to run frequently, cache the result
import asyncio
from functools import lru_cache
from datetime import datetime, timedelta

_status_cache = {}
_cache_duration = timedelta(minutes=5)

async def get_cached_status(project_id: str = None):
    """Get project status with 5-minute cache."""
    cache_key = project_id or "default"

    if cache_key in _status_cache:
        cached_time, cached_status = _status_cache[cache_key]
        if datetime.now() - cached_time < _cache_duration:
            return cached_status

    # Cache miss - fetch fresh data
    status = await project_status(project_id=project_id)
    _status_cache[cache_key] = (datetime.now(), status)

    return status
```

## API Reference

### Data Models

#### ProjectStatusResult

```python
class ProjectStatusResult(BaseModel):
    project_id: str              # Project/epic ID
    project_name: str            # Project/epic name
    health: str                  # on_track, at_risk, off_track
    health_metrics: HealthMetrics
    summary: dict[str, int]      # State counts
    priority_summary: dict[str, int]  # Priority counts
    work_distribution: dict[str, dict[str, int]]  # Assignee workload
    recommended_next: list[TicketRecommendation]  # Top 3 recommendations
    blockers: list[dict]         # Active blockers
    critical_path: list[str]     # Ticket IDs in critical path
    recommendations: list[str]   # Human-readable recommendations
    timeline_estimate: dict      # Timeline projection
```

#### HealthMetrics

```python
class HealthMetrics(BaseModel):
    total_tickets: int           # Total ticket count
    completion_rate: float       # 0.0-1.0 (% done)
    progress_rate: float         # 0.0-1.0 (% in progress)
    blocked_rate: float          # 0.0-1.0 (% blocked)
    critical_count: int          # Number of critical tickets
    high_count: int              # Number of high priority tickets
    health_score: float          # 0.0-1.0 overall score
    health_status: ProjectHealth # Enum: ON_TRACK, AT_RISK, OFF_TRACK
```

#### TicketRecommendation

```python
class TicketRecommendation(BaseModel):
    ticket_id: str               # Ticket ID
    title: str                   # Ticket title
    priority: str                # Priority level
    reason: str                  # Why recommended
    blocks: list[str]            # Ticket IDs this blocks
    impact_score: float          # Calculated score (0-100)
```

### Constants

#### Health Score Weights

```python
COMPLETION_WEIGHT = 0.30  # 30%
PROGRESS_WEIGHT = 0.25    # 25%
BLOCKER_WEIGHT = 0.30     # 30%
PRIORITY_WEIGHT = 0.15    # 15%
```

#### Health Thresholds

```python
HEALTHY_COMPLETION_THRESHOLD = 0.5   # 50% completion = healthy
HEALTHY_PROGRESS_THRESHOLD = 0.2     # 20% in progress = healthy
RISKY_BLOCKED_THRESHOLD = 0.2        # 20% blocked = at risk
CRITICAL_BLOCKED_THRESHOLD = 0.4     # 40% blocked = off track
```

#### Recommendation Score Points

```python
PRIORITY_CRITICAL = 30  # Points for critical priority
PRIORITY_HIGH = 20      # Points for high priority
PRIORITY_MEDIUM = 10    # Points for medium priority
PRIORITY_LOW = 5        # Points for low priority

NOT_BLOCKED_BONUS = 20  # Points for no blockers
BLOCKER_PENALTY = 5     # Penalty per blocker

BLOCKS_POINTS = 5       # Points per ticket blocked (max 25)
CRITICAL_PATH_BONUS = 15  # Points for critical path

STATE_OPEN_BONUS = 10   # Points for OPEN state
STATE_READY_BONUS = 8   # Points for READY state
STATE_WAITING_BONUS = 5 # Points for WAITING state
```

## Examples

### Complete Examples

See [examples/project_status_examples.py](../examples/project_status_examples.py) for fully runnable code examples including:

1. **Basic Project Status** - Simple health check
2. **Track Project Updates Over Time** - Historical tracking
3. **Dependency Analysis** - Deep dependency inspection
4. **PM Agent Workflow** - Complete daily workflow
5. **Sprint Planning** - Capacity and velocity planning

### Quick Examples

#### Daily Health Dashboard

```python
async def health_dashboard():
    """Generate health dashboard."""
    status = await project_status()

    print("=" * 50)
    print(f"PROJECT HEALTH DASHBOARD")
    print("=" * 50)

    # Health indicator
    emoji = {'on_track': '✅', 'at_risk': '⚡', 'off_track': '⚠️'}
    print(f"\n{emoji[status['health']]} Overall Health: {status['health'].upper()}")
    print(f"Score: {status['health_metrics']['health_score']:.2f}/1.00")

    # Progress
    print(f"\n📊 Progress:")
    print(f"  Completion: {status['health_metrics']['completion_rate']:.0%}")
    print(f"  In Progress: {status['summary'].get('in_progress', 0)} tickets")
    print(f"  Blocked: {status['summary'].get('blocked', 0)} tickets")

    # Priorities
    print(f"\n🎯 Next Actions:")
    for i, ticket in enumerate(status['recommended_next'], 1):
        print(f"  {i}. {ticket['ticket_id']}: {ticket['title']}")
        print(f"     {ticket['reason']}")

    # Recommendations
    print(f"\n💡 Recommendations:")
    for rec in status['recommendations']:
        print(f"  • {rec}")

    print("=" * 50)
```

#### Automated Blocker Resolution

```python
async def resolve_top_blocker():
    """Automatically escalate top blocker."""
    status = await project_status()

    if not status['blockers']:
        print("✅ No blockers - project flowing smoothly")
        return

    # Get top blocker
    top = status['blockers'][0]

    print(f"🚧 Top Blocker Detected:")
    print(f"  Ticket: {top['ticket_id']}")
    print(f"  Title: {top['title']}")
    print(f"  Blocking: {top['blocks_count']} tickets")
    print(f"  Priority: {top['priority']}")

    # Escalate to manager
    await ticket_update(
        ticket_id=top['ticket_id'],
        priority='critical',  # Escalate to critical
        comment=f"Escalated: Blocking {top['blocks_count']} tickets"
    )

    # Assign to experienced developer
    await ticket_assign(
        ticket_id=top['ticket_id'],
        assignee='senior.dev@company.com',
        comment='High-priority blocker - needs immediate attention'
    )

    print(f"✅ Escalated and assigned")
```

---

**Related Documentation:**
- [README.md](../README.md#-project-status-analysis-new-in-v130) - Quick overview
- [examples/project_status_examples.py](../examples/project_status_examples.py) - Runnable code
- [PM_MONITORING_TOOLS.md](PM_MONITORING_TOOLS.md) - Ticket cleanup tools
- [Linear Setup Guide](integrations/setup/LINEAR_SETUP.md) - Platform-specific setup
