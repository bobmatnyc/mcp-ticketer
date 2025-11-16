API Reference
=============

This section provides comprehensive API documentation for the mcp-ticketer package.

Core Models
-----------

The core models provide universal ticket representations that work across all adapters.

Base Model Classes
~~~~~~~~~~~~~~~~~~

.. automodule:: mcp_ticketer.core.models
   :members:
   :undoc-members:
   :show-inheritance:

Priority and State Enums
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: mcp_ticketer.core.models.Priority
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.models.TicketState
   :members:
   :undoc-members:
   :show-inheritance:

Ticket Models
~~~~~~~~~~~~~

.. autoclass:: mcp_ticketer.core.models.BaseTicket
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.models.Task
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.models.Epic
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.models.Comment
   :members:
   :undoc-members:
   :show-inheritance:

Adapter System
--------------

The adapter system provides a pluggable architecture for different ticket management platforms.

Base Adapter
~~~~~~~~~~~~

.. automodule:: mcp_ticketer.core.adapter
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.adapter.BaseAdapter
   :members:
   :undoc-members:
   :show-inheritance:

Adapter Registry
~~~~~~~~~~~~~~~~

.. automodule:: mcp_ticketer.core.registry
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.core.registry.AdapterRegistry
   :members:
   :undoc-members:
   :show-inheritance:

Adapter Implementations
~~~~~~~~~~~~~~~~~~~~~~~

AITrackdown Adapter
^^^^^^^^^^^^^^^^^^^

.. automodule:: mcp_ticketer.adapters.aitrackdown
   :members:
   :undoc-members:
   :show-inheritance:

Linear Adapter
^^^^^^^^^^^^^^

.. automodule:: mcp_ticketer.adapters.linear
   :members:
   :undoc-members:
   :show-inheritance:

Jira Adapter
^^^^^^^^^^^^

.. automodule:: mcp_ticketer.adapters.jira
   :members:
   :undoc-members:
   :show-inheritance:

GitHub Adapter
^^^^^^^^^^^^^^

.. automodule:: mcp_ticketer.adapters.github
   :members:
   :undoc-members:
   :show-inheritance:

Cache System
------------

The cache system provides performance optimizations for adapter operations.

Memory Cache
~~~~~~~~~~~~

.. automodule:: mcp_ticketer.cache.memory
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: mcp_ticketer.cache.memory.MemoryCache
   :members:
   :undoc-members:
   :show-inheritance:

MCP Server API
--------------

The MCP (Model Context Protocol) server provides AI agent integration.

Server Implementation
~~~~~~~~~~~~~~~~~~~~~

.. automodule:: mcp_ticketer.mcp.server
   :members:
   :undoc-members:
   :show-inheritance:

Core Functions
~~~~~~~~~~~~~~

The following functions provide the main entry points for the package:

.. autofunction:: mcp_ticketer.get_version

.. autofunction:: mcp_ticketer.get_user_agent

Package Information
-------------------

The package provides utility functions for version and user agent information:

Example Usage
-------------

Basic API Usage
~~~~~~~~~~~~~~~

Here's a basic example of using the core API:

.. code-block:: python

    from mcp_ticketer.core.models import Task, Priority, TicketState
    from mcp_ticketer.adapters import AITrackdownAdapter

    # Create a new task
    task = Task(
        id="task-1",
        title="Example Task",
        description="This is an example task",
        priority=Priority.HIGH,
        state=TicketState.OPEN,
        creator="user@example.com"
    )

    # Initialize an adapter
    adapter = AITrackdownAdapter()

    # Create the task using the adapter
    created_task = await adapter.create_task(task)
    print(f"Created task: {created_task.title}")

Adapter Registry Usage
~~~~~~~~~~~~~~~~~~~~~~

Using the adapter registry to work with multiple adapters:

.. code-block:: python

    from mcp_ticketer.core.registry import AdapterRegistry

    # Get the singleton registry
    registry = AdapterRegistry()

    # Register an adapter
    registry.register("aitrackdown", AITrackdownAdapter)

    # Get an adapter instance
    adapter = registry.get_adapter("aitrackdown")

    # List all registered adapters
    adapters = registry.list_adapters()
    print(f"Available adapters: {adapters}")

State Transitions
~~~~~~~~~~~~~~~~~

Working with ticket state transitions:

.. code-block:: python

    from mcp_ticketer.core.models import TicketState

    # Check valid transitions
    current_state = TicketState.OPEN
    target_state = TicketState.IN_PROGRESS

    if current_state.can_transition_to(target_state):
        print("Transition is valid")
        # Perform the transition
        task.state = target_state
    else:
        print("Invalid transition")

    # Get all valid transitions from current state
    valid_transitions = TicketState.valid_transitions()[current_state]
    print(f"Valid transitions from {current_state}: {valid_transitions}")