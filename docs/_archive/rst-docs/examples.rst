Usage Examples
==============

This page provides practical examples of using mcp-ticketer in various scenarios and workflows.

Getting Started
---------------

Quick Setup
~~~~~~~~~~~

Start with a simple AITrackdown setup:

.. code-block:: bash

    # Install mcp-ticketer
    pip install mcp-ticketer

    # Initialize configuration
    mcp-ticket init --adapter aitrackdown

    # Configure your adapter
    mcp-ticket set aitrackdown --token "your-token" --project "project-id"

    # Create your first ticket
    mcp-ticket create "Welcome to mcp-ticketer!"

Basic Operations
~~~~~~~~~~~~~~~~

**Create a Task:**

.. code-block:: bash

    mcp-ticket create "Fix login bug" \
        --description "Users cannot authenticate after recent update" \
        --priority high \
        --assignee "dev@company.com"

**List Tasks:**

.. code-block:: bash

    # List all open tasks
    mcp-ticket list --state open

    # List high priority tasks
    mcp-ticket list --priority high --limit 10

**Update Task:**

.. code-block:: bash

    # Update task details
    mcp-ticket update TASK-123 \
        --title "Critical login authentication bug" \
        --priority critical

    # Assign task to someone
    mcp-ticket update TASK-123 --assignee "senior-dev@company.com"

**Transition Task:**

.. code-block:: bash

    # Move task to in progress
    mcp-ticket transition TASK-123 in_progress

    # Complete task with comment
    mcp-ticket transition TASK-123 done \
        --comment "Fixed authentication flow and added tests"

Platform-Specific Examples
---------------------------

Linear Workflows
~~~~~~~~~~~~~~~~

**Setup Linear Integration:**

.. code-block:: bash

    # Configure Linear adapter
    mcp-ticket set linear \
        --token "lin_api_your_token" \
        --team "ENG"

    # Create issue in Linear
    mcp-ticket create "Implement dark mode" \
        --description "Add dark theme support across the application" \
        --priority medium \
        --labels "feature,ui"

**Linear Project Management:**

.. code-block:: bash

    # List issues in current cycle
    mcp-ticket list --state open --limit 20

    # Create epic for major feature
    mcp-ticket create "User Authentication Redesign" \
        --description "Modernize authentication system with OAuth2" \
        --priority high

    # Link tasks to epic (Linear-specific)
    mcp-ticket create "Implement OAuth2 provider" \
        --epic "ENG-456" \
        --assignee "auth-team@company.com"

Jira Enterprise Workflows
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Setup Jira Integration:**

.. code-block:: bash

    # Configure Jira adapter
    mcp-ticket set jira \
        --url "https://company.atlassian.net" \
        --token "your-api-token" \
        --project "PROJ"

**Bug Tracking Workflow:**

.. code-block:: bash

    # Create bug report
    mcp-ticket create "Database connection timeout" \
        --description "Application fails to connect to database after 30 seconds" \
        --priority critical

    # Assign to DBA team
    mcp-ticket update PROJ-789 --assignee "dba-team@company.com"

    # Move through workflow
    mcp-ticket transition PROJ-789 in_progress
    mcp-ticket transition PROJ-789 ready \
        --comment "Fix implemented, ready for testing"

**Epic Management:**

.. code-block:: bash

    # Create epic for major release
    mcp-ticket create "Q3 Performance Improvements" \
        --description "Initiative to improve application performance by 50%" \
        --priority high

    # Create stories under epic
    mcp-ticket create "Optimize database queries" \
        --epic "PROJ-800" \
        --priority high

    mcp-ticket create "Implement caching layer" \
        --epic "PROJ-800" \
        --priority medium

GitHub Issue Management
~~~~~~~~~~~~~~~~~~~~~~~

**Setup GitHub Integration:**

.. code-block:: bash

    # Configure GitHub adapter
    mcp-ticket set github \
        --token "ghp_your_token" \
        --org "mycompany" \
        --repo "myproject"

**Open Source Contribution Flow:**

.. code-block:: bash

    # Create feature request
    mcp-ticket create "Add REST API documentation" \
        --description "Generate API docs from OpenAPI spec" \
        --labels "documentation,enhancement,good-first-issue"

    # Create bug report
    mcp-ticket create "Memory leak in data processor" \
        --description "Application memory usage increases over time" \
        --labels "bug,performance"

**Release Management:**

.. code-block:: bash

    # List issues for next release
    mcp-ticket list --labels "release-2.1" --state open

    # Close completed features
    mcp-ticket transition 42 closed \
        --comment "Implemented in PR #156"

Advanced Workflows
------------------

Multi-Platform Coordination
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use different platforms for different purposes:

.. code-block:: bash

    # Track bugs in Jira for enterprise compliance
    mcp-ticket set jira --project "BUG"
    mcp-ticket create "Production database error" \
        --adapter jira \
        --priority critical

    # Track features in Linear for development team
    mcp-ticket set linear --team "product"
    mcp-ticket create "New user dashboard" \
        --adapter linear \
        --priority medium

    # Track documentation in GitHub for open source visibility
    mcp-ticket create "Update installation guide" \
        --adapter github \
        --labels "documentation"

Batch Operations
~~~~~~~~~~~~~~~~

**Bulk Task Creation:**

.. code-block:: bash

    # Create multiple related tasks
    for feature in "user-auth" "data-sync" "ui-refresh"; do
        mcp-ticket create "Implement $feature" \
            --description "Part of Q3 roadmap" \
            --priority medium \
            --epic "ROADMAP-Q3"
    done

**Mass Updates:**

.. code-block:: bash

    # Get all high priority open tasks and update them
    mcp-ticket list --priority high --state open --format json | \
    jq -r '.[].id' | \
    while read task_id; do
        mcp-ticket update "$task_id" --assignee "lead-dev@company.com"
    done

Automation and Scripts
~~~~~~~~~~~~~~~~~~~~~~

**Daily Standup Report:**

.. code-block:: bash

    #!/bin/bash
    # standup-report.sh

    echo "=== Daily Standup Report ==="
    echo ""

    echo "In Progress:"
    mcp-ticket list --state in_progress --assignee "$(whoami)" --format table

    echo ""
    echo "Ready for Review:"
    mcp-ticket list --state ready --assignee "$(whoami)" --format table

    echo ""
    echo "Completed Yesterday:"
    mcp-ticket search "updated:yesterday" --assignee "$(whoami)" --format table

**Sprint Planning:**

.. code-block:: bash

    #!/bin/bash
    # sprint-planning.sh

    SPRINT_EPIC="EPIC-123"

    echo "=== Sprint Planning: $SPRINT_EPIC ==="

    # Create sprint backlog
    mcp-ticket list --epic "$SPRINT_EPIC" --state open --format table

    # Show capacity
    echo ""
    echo "Team Capacity:"
    for dev in "dev1@company.com" "dev2@company.com" "dev3@company.com"; do
        count=$(mcp-ticket list --assignee "$dev" --state open --format json | jq length)
        echo "$dev: $count assigned tasks"
    done

API Integration Examples
------------------------

Python API Usage
~~~~~~~~~~~~~~~~

**Basic Task Management:**

.. code-block:: python

    import asyncio
    from mcp_ticketer.adapters import AITrackdownAdapter
    from mcp_ticketer.core.models import Task, Priority, TicketState


    async def main():
        # Initialize adapter
        adapter = AITrackdownAdapter()

        # Create a new task
        task = Task(
            title="Implement user authentication",
            description="Add OAuth2 support for user login",
            priority=Priority.HIGH,
            creator="product@company.com"
        )

        created_task = await adapter.create_task(task)
        print(f"Created task: {created_task.id}")

        # Update task
        updated_task = await adapter.update_task(created_task.id, {
            "assignee": "dev@company.com",
            "state": TicketState.IN_PROGRESS
        })

        # List related tasks
        tasks = await adapter.list_tasks(filters={
            "priority": Priority.HIGH,
            "state": TicketState.OPEN
        })

        for task in tasks:
            print(f"- {task.title} ({task.priority})")


    if __name__ == "__main__":
        asyncio.run(main())

**Adapter Registry Usage:**

.. code-block:: python

    import asyncio
    from mcp_ticketer.core.registry import AdapterRegistry
    from mcp_ticketer.core.models import Task, Priority


    async def create_cross_platform_task(title: str, description: str):
        """Create the same task across multiple platforms."""

        registry = AdapterRegistry()

        # Get all registered adapters
        for adapter_name in registry.list_adapters():
            try:
                adapter = registry.get_adapter(adapter_name)

                task = Task(
                    title=f"[{adapter_name.upper()}] {title}",
                    description=description,
                    priority=Priority.MEDIUM,
                    creator="automation@company.com"
                )

                created_task = await adapter.create_task(task)
                print(f"Created in {adapter_name}: {created_task.id}")

            except Exception as e:
                print(f"Failed to create in {adapter_name}: {e}")


    if __name__ == "__main__":
        asyncio.run(create_cross_platform_task(
            "Critical security update",
            "Apply security patches to all production servers"
        ))

MCP Server Integration
~~~~~~~~~~~~~~~~~~~~~~

**Claude Desktop Configuration:**

.. code-block:: json

    {
        "mcpServers": {
            "mcp-ticketer": {
                "command": "mcp-ticket-server",
                "env": {
                    "LINEAR_TOKEN": "your-token",
                    "LINEAR_TEAM": "your-team-id"
                }
            }
        }
    }

**AI Agent Interaction Example:**

.. code-block:: text

    User: Create a high priority task for fixing the login bug

    Assistant: I'll create a high priority task for the login bug using the mcp-ticketer.

    *Uses mcp-ticketer tool to create task*

    Task created successfully:
    - ID: LIN-789
    - Title: Fix login bug
    - Priority: High
    - Status: Open
    - Assigned to: engineering-team

    The task has been added to your Linear workspace. Would you like me to add any additional details or create related subtasks?

Integration Patterns
--------------------

CI/CD Pipeline Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~

**GitHub Actions Example:**

.. code-block:: yaml

    name: Auto-create tickets for failed deployments

    on:
      workflow_run:
        workflows: ["Deploy"]
        types:
          - completed

    jobs:
      create-ticket:
        if: ${{ github.event.workflow_run.conclusion == 'failure' }}
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3

          - name: Setup Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.11'

          - name: Install mcp-ticketer
            run: pip install mcp-ticketer

          - name: Create failure ticket
            env:
              LINEAR_TOKEN: ${{ secrets.LINEAR_TOKEN }}
              LINEAR_TEAM: ${{ secrets.LINEAR_TEAM }}
            run: |
              mcp-ticket create "Deployment failed: ${{ github.event.workflow_run.head_branch }}" \
                --description "Deployment workflow failed for commit ${{ github.event.workflow_run.head_sha }}" \
                --priority critical \
                --labels "deployment,ci-cd,urgent"

**Jenkins Pipeline:**

.. code-block:: groovy

    pipeline {
        agent any

        post {
            failure {
                script {
                    sh '''
                        pip install mcp-ticketer
                        mcp-ticket create "Build failed: ${JOB_NAME} #${BUILD_NUMBER}" \
                            --description "Build failed on ${NODE_NAME}" \
                            --priority high \
                            --assignee "devops@company.com"
                    '''
                }
            }
        }
    }

Monitoring Integration
~~~~~~~~~~~~~~~~~~~~~~

**Alerting to Tickets:**

.. code-block:: bash

    #!/bin/bash
    # monitoring-alert.sh
    # Called by monitoring system when alert triggers

    ALERT_NAME="$1"
    ALERT_SEVERITY="$2"
    ALERT_MESSAGE="$3"

    case "$ALERT_SEVERITY" in
        "critical")
            PRIORITY="critical"
            ;;
        "warning")
            PRIORITY="high"
            ;;
        *)
            PRIORITY="medium"
            ;;
    esac

    mcp-ticket create "Alert: $ALERT_NAME" \
        --description "$ALERT_MESSAGE" \
        --priority "$PRIORITY" \
        --labels "monitoring,alert" \
        --assignee "oncall@company.com"

Custom Workflow Examples
------------------------

Code Review Workflow
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    #!/bin/bash
    # review-workflow.sh

    TASK_ID="$1"
    PR_URL="$2"

    # Move task to review state
    mcp-ticket transition "$TASK_ID" ready \
        --comment "Ready for code review: $PR_URL"

    # Add reviewer
    mcp-ticket update "$TASK_ID" \
        --add-labels "needs-review" \
        --assignee "senior-dev@company.com"

Release Planning
~~~~~~~~~~~~~~~~

.. code-block:: python

    #!/usr/bin/env python3
    # release-planning.py

    import asyncio
    import json
    from datetime import datetime, timedelta
    from mcp_ticketer.core.registry import AdapterRegistry


    async def plan_release(version: str, release_date: str):
        """Plan a release by gathering all related tasks."""

        registry = AdapterRegistry()
        adapter = registry.get_adapter("linear")  # or your preferred platform

        # Search for tasks related to this release
        tasks = await adapter.search_tasks(f"label:release-{version}")

        print(f"=== Release Plan: {version} ===")
        print(f"Target Date: {release_date}")
        print(f"Total Tasks: {len(tasks)}")
        print()

        # Group by status
        by_status = {}
        for task in tasks:
            status = task.state.value
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(task)

        # Report status
        for status, task_list in by_status.items():
            print(f"{status.title()}: {len(task_list)} tasks")
            for task in task_list[:3]:  # Show first 3
                print(f"  - {task.title}")
            if len(task_list) > 3:
                print(f"  ... and {len(task_list) - 3} more")
            print()

        # Check readiness
        ready_count = len(by_status.get("done", [])) + len(by_status.get("tested", []))
        total_count = len(tasks)

        if total_count > 0:
            readiness = (ready_count / total_count) * 100
            print(f"Release Readiness: {readiness:.1f}%")

            if readiness < 80:
                print("⚠️  Release may need to be delayed")
            else:
                print("✅ Release looks on track")


    if __name__ == "__main__":
        asyncio.run(plan_release("v2.1.0", "2024-03-15"))

Testing and Quality Assurance
-----------------------------

Test Case Management
~~~~~~~~~~~~~~~~~~~~

**Create Test Tasks:**

.. code-block:: bash

    # Create test plan for new feature
    mcp-ticket create "Test Plan: User Authentication" \
        --description "Comprehensive testing for OAuth2 implementation" \
        --priority high \
        --assignee "qa@company.com"

    # Create specific test cases
    for test in "unit-tests" "integration-tests" "e2e-tests" "security-tests"; do
        mcp-ticket create "Execute $test for authentication" \
            --epic "TEST-PLAN-123" \
            --priority medium \
            --assignee "qa@company.com"
    done

Bug Triage Workflow
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    #!/bin/bash
    # bug-triage.sh

    # Get all new bug reports
    mcp-ticket list --labels "bug" --state open --format json > new_bugs.json

    # Process each bug
    cat new_bugs.json | jq -r '.[].id' | while read bug_id; do
        echo "Triaging bug: $bug_id"

        # Get bug details
        bug_details=$(mcp-ticket show "$bug_id" --format json)

        # Simple triage logic (you could make this more sophisticated)
        if echo "$bug_details" | grep -qi "crash\|error\|exception"; then
            mcp-ticket update "$bug_id" --priority high
            echo "  → Set to high priority (crash/error detected)"
        else
            mcp-ticket update "$bug_id" --priority medium
            echo "  → Set to medium priority"
        fi

        # Assign to appropriate team
        mcp-ticket update "$bug_id" --assignee "triage-team@company.com"
    done

Performance Tips
----------------

Efficient Querying
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Use specific filters to reduce API calls
    mcp-ticket list --state open --assignee "me@company.com" --limit 10

    # Cache results for scripts
    mcp-ticket list --state open --format json > open_tasks.json
    # Process cached data instead of repeated API calls

Batch Operations
~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Process multiple tasks efficiently
    task_ids=(TASK-1 TASK-2 TASK-3)

    for task_id in "${task_ids[@]}"; do
        mcp-ticket update "$task_id" --assignee "new-dev@company.com" &
    done
    wait  # Wait for all background jobs to complete

Configuration Management
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Use environment-specific configurations
    export MCP_TICKETER_CONFIG_DIR="./config/production"
    mcp-ticket list --state open

    # Different config for different environments
    cp config/staging.yaml .mcp-ticketer/config.yaml
    mcp-ticket create "Staging deployment task"

These examples demonstrate the flexibility and power of mcp-ticketer across different workflows and use cases. Start with the basic examples and gradually incorporate more advanced patterns as your team's needs evolve.