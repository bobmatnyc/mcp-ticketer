Adapter Documentation
====================

This guide explains how to use and configure each adapter supported by mcp-ticketer.

Adapter Overview
----------------

mcp-ticketer provides adapters for popular ticket management platforms:

- **AITrackdown**: AI-powered ticket management system
- **Linear**: Modern issue tracking for software teams
- **Jira**: Enterprise project management and issue tracking
- **GitHub**: Issues and project management on GitHub

Each adapter implements the same interface, allowing you to switch between platforms seamlessly.

AITrackdown Adapter
-------------------

The AITrackdown adapter integrates with AI-powered ticket management systems.

Configuration
~~~~~~~~~~~~~

**Required Configuration:**

- ``token``: Authentication token for the AITrackdown API
- ``project``: Default project ID to use for operations

**Optional Configuration:**

- ``url``: Base URL of the AITrackdown instance (defaults to production)

**Environment Variables:**

- ``AITRACKDOWN_TOKEN``: Authentication token
- ``AITRACKDOWN_PROJECT``: Default project ID
- ``AITRACKDOWN_URL``: Base URL (optional)

Setup
~~~~~

1. **CLI Configuration:**

   .. code-block:: bash

       mcp-ticket set aitrackdown --token "your-token" --project "project-id"

2. **Environment Variables:**

   .. code-block:: bash

       export AITRACKDOWN_TOKEN=your-token
       export AITRACKDOWN_PROJECT=project-id

3. **Configuration File:**

   .. code-block:: yaml

       adapters:
         aitrackdown:
           token: "your-token"
           project: "project-id"

Features
~~~~~~~~

**Supported Operations:**

- ✅ Create tasks and epics
- ✅ List tickets with filtering
- ✅ Update ticket properties
- ✅ State transitions
- ✅ Comments and attachments
- ✅ Search functionality
- ✅ Custom fields support

**Special Features:**

- AI-powered ticket classification
- Automatic priority inference
- Smart duplicate detection
- Enhanced search with semantic matching

Usage Examples
~~~~~~~~~~~~~~

.. code-block:: bash

    # Create a task with AITrackdown
    mcp-ticket create "Fix authentication bug" \
        --description "Users cannot login after recent update" \
        --priority high

    # Search with semantic matching
    mcp-ticket search "login issues" --fields title,description

    # List recent high priority items
    mcp-ticket list --priority high --state open --limit 10

Linear Adapter
--------------

The Linear adapter provides integration with Linear's modern issue tracking platform.

Configuration
~~~~~~~~~~~~~

**Required Configuration:**

- ``token``: Linear API token
- ``team``: Default team ID for operations

**Optional Configuration:**

- ``project``: Default project ID (if using Linear projects)

**Environment Variables:**

- ``LINEAR_TOKEN``: API token
- ``LINEAR_TEAM``: Default team ID
- ``LINEAR_PROJECT``: Default project ID (optional)

Setup
~~~~~

1. **Obtain API Token:**

   Visit https://linear.app/settings/api and create a personal API token.

2. **Find Team ID:**

   Use Linear's API explorer or check team settings in the Linear app.

3. **CLI Configuration:**

   .. code-block:: bash

       mcp-ticket set linear --token "lin_api_your_token" --team "team-id"

4. **Environment Variables:**

   .. code-block:: bash

       export LINEAR_TOKEN=lin_api_your_token
       export LINEAR_TEAM=team-id

5. **Configuration File:**

   .. code-block:: yaml

       adapters:
         linear:
           token: "lin_api_your_token"
           team: "team-id"
           project: "project-id"  # optional

Features
~~~~~~~~

**Supported Operations:**

- ✅ Create issues
- ✅ List issues with filtering
- ✅ Update issue properties
- ✅ State transitions
- ✅ Comments
- ✅ Labels management
- ✅ Search functionality
- ✅ Projects and roadmaps

**Linear-specific Features:**

- Issue templates
- Cycle management
- Project milestones
- Triage integration
- Custom workflows

**State Mapping:**

Linear states are mapped to universal states as follows:

- ``Backlog`` → ``open``
- ``Todo`` → ``open``
- ``In Progress`` → ``in_progress``
- ``In Review`` → ``ready``
- ``Done`` → ``done``
- ``Canceled`` → ``closed``

Usage Examples
~~~~~~~~~~~~~~

.. code-block:: bash

    # Create an issue in Linear
    mcp-ticket create "Implement dark mode" \
        --description "Add dark theme support to the application" \
        --priority medium \
        --labels "feature,ui"

    # Transition issue through workflow
    mcp-ticket transition LIN-123 in_progress

    # List issues in current cycle
    mcp-ticket list --state open --limit 20

Jira Adapter
------------

The Jira adapter integrates with Atlassian Jira for enterprise project management.

Configuration
~~~~~~~~~~~~~

**Required Configuration:**

- ``url``: Jira instance URL (e.g., ``https://company.atlassian.net``)
- ``token``: API token or PAT (Personal Access Token)
- ``project``: Default project key (e.g., ``PROJ``)

**Optional Configuration:**

- ``username``: Username for basic auth (if not using token auth)

**Environment Variables:**

- ``JIRA_URL``: Jira instance URL
- ``JIRA_TOKEN``: API token
- ``JIRA_PROJECT``: Default project key
- ``JIRA_USERNAME``: Username (for basic auth)

Setup
~~~~~

1. **Create API Token:**

   Visit https://id.atlassian.com/manage-profile/security/api-tokens

2. **CLI Configuration:**

   .. code-block:: bash

       mcp-ticket set jira \
           --url "https://company.atlassian.net" \
           --token "your-api-token" \
           --project "PROJ"

3. **Environment Variables:**

   .. code-block:: bash

       export JIRA_URL=https://company.atlassian.net
       export JIRA_TOKEN=your-api-token
       export JIRA_PROJECT=PROJ

4. **Configuration File:**

   .. code-block:: yaml

       adapters:
         jira:
           url: "https://company.atlassian.net"
           token: "your-api-token"
           project: "PROJ"

Features
~~~~~~~~

**Supported Operations:**

- ✅ Create issues (Story, Task, Bug, Epic)
- ✅ List issues with JQL filtering
- ✅ Update issue properties
- ✅ State transitions
- ✅ Comments
- ✅ Attachments
- ✅ Custom fields
- ✅ Epic management

**Jira-specific Features:**

- JQL (Jira Query Language) support
- Custom issue types
- Workflows and transitions
- Components and fix versions
- Time tracking
- Subtasks

**Issue Type Mapping:**

- ``Task`` → Jira Task
- ``Epic`` → Jira Epic
- ``Bug`` → Jira Bug (when priority is high/critical)
- ``Story`` → Jira Story (default for medium/low priority)

**State Mapping:**

- ``To Do`` → ``open``
- ``In Progress`` → ``in_progress``
- ``Code Review`` → ``ready``
- ``Testing`` → ``tested``
- ``Done`` → ``done``
- ``Won't Do`` → ``closed``

Usage Examples
~~~~~~~~~~~~~~

.. code-block:: bash

    # Create a bug in Jira
    mcp-ticket create "Database connection timeout" \
        --description "Connection timeouts after 30 seconds" \
        --priority critical

    # Create epic
    mcp-ticket create "User Authentication Redesign" \
        --description "Modernize authentication system" \
        --priority high

    # Search using JQL-like syntax
    mcp-ticket search "assignee = currentUser() AND status = 'In Progress'"

    # List issues with complex filters
    mcp-ticket list --state open --assignee "john@company.com"

GitHub Adapter
--------------

The GitHub adapter integrates with GitHub Issues and Projects.

Configuration
~~~~~~~~~~~~~

**Required Configuration:**

- ``token``: GitHub Personal Access Token
- ``org``: Organization name
- ``repo``: Repository name

**Optional Configuration:**

- ``project``: GitHub Project number (for project v2 integration)

**Environment Variables:**

- ``GITHUB_TOKEN``: Personal Access Token
- ``GITHUB_ORG``: Organization name
- ``GITHUB_REPO``: Repository name
- ``GITHUB_PROJECT``: Project number (optional)

Setup
~~~~~

1. **Create Personal Access Token:**

   Visit https://github.com/settings/tokens and create a token with:
   - ``repo`` scope (for repository issues)
   - ``project`` scope (for GitHub Projects)

2. **CLI Configuration:**

   .. code-block:: bash

       mcp-ticket set github \
           --token "ghp_your_token" \
           --org "myorg" \
           --repo "myrepo"

3. **Environment Variables:**

   .. code-block:: bash

       export GITHUB_TOKEN=ghp_your_token
       export GITHUB_ORG=myorg
       export GITHUB_REPO=myrepo

4. **Configuration File:**

   .. code-block:: yaml

       adapters:
         github:
           token: "ghp_your_token"
           org: "myorg"
           repo: "myrepo"
           project: 1  # optional

Features
~~~~~~~~

**Supported Operations:**

- ✅ Create issues
- ✅ List issues with filtering
- ✅ Update issue properties
- ✅ State transitions (open/closed)
- ✅ Comments
- ✅ Labels management
- ✅ Assignees
- ✅ Milestones
- ✅ Projects v2 integration

**GitHub-specific Features:**

- Pull request integration
- GitHub Projects v2 support
- Issue templates
- Automatic linking
- Reaction tracking

**State Mapping:**

GitHub has simple state model:

- ``open`` → GitHub Open
- ``closed`` → GitHub Closed
- All other states → GitHub Open with labels

Usage Examples
~~~~~~~~~~~~~~

.. code-block:: bash

    # Create issue in GitHub
    mcp-ticket create "Update README" \
        --description "Add installation and usage instructions" \
        --labels "documentation,good-first-issue"

    # Close issue
    mcp-ticket transition 42 closed \
        --comment "Fixed in PR #43"

    # List open issues assigned to current user
    mcp-ticket list --state open --assignee "@me"

Cross-Adapter Operations
------------------------

Working with Multiple Adapters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can work with multiple adapters in the same project:

.. code-block:: bash

    # Use specific adapter for one operation
    mcp-ticket create "Bug report" --adapter jira

    # Switch default adapter
    mcp-ticket set linear --token "new-token" --team "team-id"

    # List tickets from all configured adapters
    mcp-ticket list --adapter aitrackdown
    mcp-ticket list --adapter linear
    mcp-ticket list --adapter github

Configuration Priority
~~~~~~~~~~~~~~~~~~~~~~

Configuration is resolved in this order (highest to lowest):

1. Command-line arguments
2. Environment variables
3. Local project configuration (``.mcp-ticketer/config.yaml``)
4. Global user configuration (``~/.mcp-ticketer/config.yaml``)
5. Default values

Adapter Selection
~~~~~~~~~~~~~~~~~

The active adapter is determined by:

1. ``--adapter`` command-line flag
2. ``MCP_TICKETER_DEFAULT_ADAPTER`` environment variable
3. ``default_adapter`` in configuration files
4. First configured adapter
5. ``aitrackdown`` (fallback default)

Common Patterns
---------------

Multi-Platform Workflows
~~~~~~~~~~~~~~~~~~~~~~~~

Use different adapters for different purposes:

.. code-block:: bash

    # Track bugs in Jira
    mcp-ticket set jira --project "BUG"
    mcp-ticket create "Critical bug" --adapter jira

    # Track features in Linear
    mcp-ticket set linear --team "feature-team"
    mcp-ticket create "New feature" --adapter linear

    # Track documentation in GitHub
    mcp-ticket create "Update docs" --adapter github

Synchronization
~~~~~~~~~~~~~~~

Keep tickets synchronized across platforms:

.. code-block:: bash

    # Create ticket in primary system
    mcp-ticket create "Important issue" --adapter linear

    # Mirror in secondary system
    mcp-ticket create "Important issue [LINEAR-123]" --adapter jira

Migration
~~~~~~~~~

Migrate tickets between platforms:

.. code-block:: bash

    # Export from source
    mcp-ticket list --adapter linear --format json > tickets.json

    # Import to destination
    # (Custom scripting required for data transformation)

Troubleshooting
---------------

Authentication Issues
~~~~~~~~~~~~~~~~~~~~~

**Invalid Token:**

.. code-block:: bash

    Error: Authentication failed (401)

Solution: Verify your token is valid and has necessary permissions.

**Expired Token:**

.. code-block:: bash

    Error: Token expired

Solution: Generate a new token and update your configuration.

Configuration Issues
~~~~~~~~~~~~~~~~~~~~

**Missing Configuration:**

.. code-block:: bash

    Error: No adapter configured

Solution: Run ``mcp-ticket init`` or ``mcp-ticket set <adapter>``.

**Invalid Project/Team:**

.. code-block:: bash

    Error: Project not found

Solution: Verify the project/team ID in your adapter configuration.

Network Issues
~~~~~~~~~~~~~~

**Connection Timeout:**

.. code-block:: bash

    Error: Connection timeout

Solution: Check your internet connection and adapter URL.

**Rate Limiting:**

.. code-block:: bash

    Error: Rate limit exceeded

Solution: Wait before retrying, or configure rate limiting settings.

Adapter-Specific Issues
~~~~~~~~~~~~~~~~~~~~~~~

**Linear GraphQL Errors:**

.. code-block:: bash

    Error: GraphQL query failed

Solution: Check Linear API status and verify your team ID.

**Jira JQL Errors:**

.. code-block:: bash

    Error: Invalid JQL syntax

Solution: Verify your search query syntax matches Jira JQL.

**GitHub Permission Errors:**

.. code-block:: bash

    Error: Insufficient permissions

Solution: Ensure your token has ``repo`` and ``project`` scopes.