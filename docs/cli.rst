Command Line Interface
======================

The mcp-ticketer package provides two command-line tools for different use cases:

- **mcp-ticket**: Interactive CLI for ticket management operations
- **mcp-ticket-server**: MCP server for AI agent integration

Installation and Setup
-----------------------

After installing the package, both commands become available in your PATH:

.. code-block:: bash

    pip install mcp-ticketer

The CLI tools will be available as:

.. code-block:: bash

    mcp-ticket --help
    mcp-ticket-server --help

Main CLI Tool: mcp-ticket
--------------------------

The main CLI tool provides comprehensive ticket management functionality.

Global Options
~~~~~~~~~~~~~~

.. code-block:: bash

    mcp-ticket [GLOBAL_OPTIONS] COMMAND [COMMAND_OPTIONS] [ARGS]

Global options available for all commands:

- ``--help``: Show help message and exit

Available Commands
~~~~~~~~~~~~~~~~~~

init
^^^^

Initialize MCP Ticketer configuration in the current directory.

.. code-block:: bash

    mcp-ticket init [OPTIONS]

**Options:**

- ``--adapter TEXT``: Default adapter to configure (aitrackdown, linear, jira, github)
- ``--force``: Overwrite existing configuration
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Initialize with AITrackdown adapter
    mcp-ticket init --adapter aitrackdown

    # Force reinitialize with Linear adapter
    mcp-ticket init --adapter linear --force

set
^^^

Set default adapter and adapter-specific configuration.

.. code-block:: bash

    mcp-ticket set [OPTIONS] ADAPTER_NAME

**Arguments:**

- ``ADAPTER_NAME``: Name of the adapter to configure (aitrackdown, linear, jira, github)

**Options:**

- ``--url TEXT``: Base URL for the adapter service
- ``--token TEXT``: Authentication token
- ``--project TEXT``: Default project/workspace ID
- ``--team TEXT``: Default team ID (Linear specific)
- ``--org TEXT``: Organization name (GitHub specific)
- ``--repo TEXT``: Repository name (GitHub specific)
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Configure AITrackdown adapter
    mcp-ticket set aitrackdown --token "your-token" --project "project-id"

    # Configure Linear adapter with team
    mcp-ticket set linear --token "lin_api_token" --team "team-id"

    # Configure GitHub adapter
    mcp-ticket set github --token "ghp_token" --org "myorg" --repo "myrepo"

status
^^^^^^

Show queue and worker status.

.. code-block:: bash

    mcp-ticket status [OPTIONS]

**Options:**

- ``--detailed``: Show detailed status information
- ``--json``: Output status in JSON format
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Show basic status
    mcp-ticket status

    # Show detailed status in JSON
    mcp-ticket status --detailed --json

create
^^^^^^

Create a new ticket.

.. code-block:: bash

    mcp-ticket create [OPTIONS] TITLE

**Arguments:**

- ``TITLE``: Title of the ticket to create

**Options:**

- ``--description TEXT``: Ticket description
- ``--priority [low|medium|high|critical]``: Priority level (default: medium)
- ``--assignee TEXT``: Assign to user (email or username)
- ``--epic TEXT``: Parent epic ID
- ``--labels TEXT``: Comma-separated list of labels
- ``--adapter TEXT``: Override default adapter
- ``--async``: Queue the operation for background processing
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Create a simple task
    mcp-ticket create "Fix login bug"

    # Create a high priority task with description
    mcp-ticket create "Database performance issue" \\
        --description "Query times are too slow" \\
        --priority high \\
        --assignee "dev@company.com"

    # Create task in background queue
    mcp-ticket create "Long running task" --async

list
^^^^

List tickets with optional filters.

.. code-block:: bash

    mcp-ticket list [OPTIONS]

**Options:**

- ``--state [open|in_progress|ready|tested|done|waiting|blocked|closed]``: Filter by state
- ``--priority [low|medium|high|critical]``: Filter by priority
- ``--assignee TEXT``: Filter by assignee
- ``--creator TEXT``: Filter by creator
- ``--epic TEXT``: Filter by parent epic
- ``--limit INTEGER``: Maximum number of tickets to return (default: 20)
- ``--offset INTEGER``: Number of tickets to skip (default: 0)
- ``--format [table|json|csv]``: Output format (default: table)
- ``--adapter TEXT``: Override default adapter
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # List all open tickets
    mcp-ticket list --state open

    # List high priority tickets in JSON format
    mcp-ticket list --priority high --format json

    # List tickets assigned to specific user
    mcp-ticket list --assignee "dev@company.com" --limit 10

show
^^^^

Show detailed ticket information.

.. code-block:: bash

    mcp-ticket show [OPTIONS] TICKET_ID

**Arguments:**

- ``TICKET_ID``: ID of the ticket to show

**Options:**

- ``--format [table|json|yaml]``: Output format (default: table)
- ``--show-comments``: Include comments in output
- ``--adapter TEXT``: Override default adapter
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Show ticket details
    mcp-ticket show TICKET-123

    # Show ticket with comments in JSON
    mcp-ticket show TICKET-123 --show-comments --format json

update
^^^^^^

Update ticket fields.

.. code-block:: bash

    mcp-ticket update [OPTIONS] TICKET_ID

**Arguments:**

- ``TICKET_ID``: ID of the ticket to update

**Options:**

- ``--title TEXT``: New title
- ``--description TEXT``: New description
- ``--priority [low|medium|high|critical]``: New priority
- ``--assignee TEXT``: New assignee (email or username)
- ``--labels TEXT``: Comma-separated list of labels (replaces existing)
- ``--add-labels TEXT``: Comma-separated list of labels to add
- ``--remove-labels TEXT``: Comma-separated list of labels to remove
- ``--adapter TEXT``: Override default adapter
- ``--async``: Queue the operation for background processing
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Update ticket title and priority
    mcp-ticket update TICKET-123 \\
        --title "New title" \\
        --priority critical

    # Add labels to ticket
    mcp-ticket update TICKET-123 --add-labels "bug,urgent"

    # Reassign ticket
    mcp-ticket update TICKET-123 --assignee "newdev@company.com"

transition
^^^^^^^^^^

Change ticket state with validation.

.. code-block:: bash

    mcp-ticket transition [OPTIONS] TICKET_ID NEW_STATE

**Arguments:**

- ``TICKET_ID``: ID of the ticket to transition
- ``NEW_STATE``: Target state (open, in_progress, ready, tested, done, waiting, blocked, closed)

**Options:**

- ``--comment TEXT``: Add comment explaining the transition
- ``--force``: Force transition even if not normally allowed
- ``--adapter TEXT``: Override default adapter
- ``--async``: Queue the operation for background processing
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Transition ticket to in progress
    mcp-ticket transition TICKET-123 in_progress

    # Close ticket with comment
    mcp-ticket transition TICKET-123 closed \\
        --comment "Issue resolved and tested"

    # Force transition (bypass validation)
    mcp-ticket transition TICKET-123 done --force

search
^^^^^^

Search tickets with advanced query.

.. code-block:: bash

    mcp-ticket search [OPTIONS] QUERY

**Arguments:**

- ``QUERY``: Search query string

**Options:**

- ``--fields TEXT``: Comma-separated list of fields to search (title, description, comments)
- ``--state [open|in_progress|ready|tested|done|waiting|blocked|closed]``: Filter by state
- ``--priority [low|medium|high|critical]``: Filter by priority
- ``--assignee TEXT``: Filter by assignee
- ``--creator TEXT``: Filter by creator
- ``--created-after DATE``: Filter by creation date (YYYY-MM-DD)
- ``--created-before DATE``: Filter by creation date (YYYY-MM-DD)
- ``--limit INTEGER``: Maximum number of results (default: 20)
- ``--format [table|json|csv]``: Output format (default: table)
- ``--adapter TEXT``: Override default adapter
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Search for bugs
    mcp-ticket search "bug" --fields title,description

    # Search recent high priority tickets
    mcp-ticket search "critical" \\
        --priority high \\
        --created-after 2024-01-01

    # Search with complex query
    mcp-ticket search "database performance" \\
        --state open \\
        --assignee "dba@company.com"

check
^^^^^

Check status of a queued operation.

.. code-block:: bash

    mcp-ticket check [OPTIONS] OPERATION_ID

**Arguments:**

- ``OPERATION_ID``: ID of the queued operation to check

**Options:**

- ``--wait``: Wait for operation to complete
- ``--timeout INTEGER``: Timeout in seconds when waiting (default: 60)
- ``--format [table|json]``: Output format (default: table)
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Check operation status
    mcp-ticket check op-12345

    # Wait for operation to complete
    mcp-ticket check op-12345 --wait --timeout 120

queue
^^^^^

Queue management commands.

.. code-block:: bash

    mcp-ticket queue [OPTIONS] SUBCOMMAND

**Subcommands:**

- ``status``: Show queue status
- ``list``: List queued operations
- ``cancel``: Cancel a queued operation
- ``retry``: Retry a failed operation
- ``clear``: Clear completed operations
- ``pause``: Pause queue processing
- ``resume``: Resume queue processing

**Options:**

- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Show queue status
    mcp-ticket queue status

    # List all queued operations
    mcp-ticket queue list

    # Cancel specific operation
    mcp-ticket queue cancel op-12345

    # Clear completed operations
    mcp-ticket queue clear

MCP Server: mcp-ticket-server
-----------------------------

The MCP server provides AI agent integration through the Model Context Protocol.

Usage
~~~~~

.. code-block:: bash

    mcp-ticket-server [OPTIONS]

**Options:**

- ``--host TEXT``: Host to bind to (default: localhost)
- ``--port INTEGER``: Port to bind to (default: 8000)
- ``--config TEXT``: Path to configuration file
- ``--log-level [DEBUG|INFO|WARNING|ERROR]``: Log level (default: INFO)
- ``--help``: Show command help

**Examples:**

.. code-block:: bash

    # Start server on default port
    mcp-ticket-server

    # Start server on specific host and port
    mcp-ticket-server --host 0.0.0.0 --port 8080

    # Start with debug logging
    mcp-ticket-server --log-level DEBUG

Configuration
~~~~~~~~~~~~~

The MCP server can be configured using a YAML configuration file:

.. code-block:: yaml

    server:
      host: localhost
      port: 8000
      log_level: INFO

    adapters:
      default: aitrackdown

      aitrackdown:
        token: "your-token"
        project: "project-id"

      linear:
        token: "lin_api_token"
        team: "team-id"

Environment Variables
---------------------

The CLI tools support configuration through environment variables:

**Global Environment Variables:**

- ``MCP_TICKETER_DEFAULT_ADAPTER``: Default adapter name
- ``MCP_TICKETER_CONFIG_DIR``: Configuration directory path
- ``MCP_TICKETER_LOG_LEVEL``: Logging level

**Adapter-specific Environment Variables:**

**AITrackdown:**

- ``AITRACKDOWN_TOKEN``: Authentication token
- ``AITRACKDOWN_PROJECT``: Default project ID
- ``AITRACKDOWN_URL``: Base URL (optional)

**Linear:**

- ``LINEAR_TOKEN``: API token
- ``LINEAR_TEAM``: Default team ID

**Jira:**

- ``JIRA_URL``: Jira instance URL
- ``JIRA_TOKEN``: API token
- ``JIRA_PROJECT``: Default project key

**GitHub:**

- ``GITHUB_TOKEN``: Personal access token
- ``GITHUB_ORG``: Organization name
- ``GITHUB_REPO``: Repository name

**Examples:**

.. code-block:: bash

    # Set environment variables
    export MCP_TICKETER_DEFAULT_ADAPTER=linear
    export LINEAR_TOKEN=lin_api_your_token
    export LINEAR_TEAM=team-id

    # Use CLI with environment configuration
    mcp-ticket create "New feature request"

Configuration Files
-------------------

The CLI tools use configuration files stored in your project or home directory.

Local Configuration
~~~~~~~~~~~~~~~~~~~

Project-specific configuration is stored in ``.mcp-ticketer/config.yaml`` in your project directory:

.. code-block:: yaml

    default_adapter: aitrackdown

    adapters:
      aitrackdown:
        token: "project-token"
        project: "project-id"

Global Configuration
~~~~~~~~~~~~~~~~~~~~

User-level configuration is stored in ``~/.mcp-ticketer/config.yaml``:

.. code-block:: yaml

    default_adapter: linear

    adapters:
      linear:
        token: "user-token"
        team: "default-team"

      github:
        token: "ghp_user_token"
        org: "myorg"

Exit Codes
----------

The CLI tools use standard exit codes:

- ``0``: Success
- ``1``: General error
- ``2``: Misuse of shell command
- ``3``: Configuration error
- ``4``: Authentication error
- ``5``: Network error
- ``6``: Adapter error

Shell Completion
----------------

To enable shell completion, add the following to your shell configuration:

**Bash:**

.. code-block:: bash

    eval "$(_MCP_TICKET_COMPLETE=bash_source mcp-ticket)"

**Zsh:**

.. code-block:: bash

    eval "$(_MCP_TICKET_COMPLETE=zsh_source mcp-ticket)"

**Fish:**

.. code-block:: bash

    _MCP_TICKET_COMPLETE=fish_source mcp-ticket | source