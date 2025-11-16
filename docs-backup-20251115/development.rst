Development Guide
=================

This guide explains how to contribute to mcp-ticketer, create custom adapters, and extend the system.

Project Architecture
---------------------

mcp-ticketer follows a modular architecture with clear separation of concerns:

.. code-block:: text

    mcp-ticketer/
    ├── src/mcp_ticketer/
    │   ├── core/                 # Core abstractions and models
    │   │   ├── models.py         # Universal ticket models
    │   │   ├── adapter.py        # Base adapter interface
    │   │   └── registry.py       # Adapter registry
    │   ├── adapters/             # Platform-specific adapters
    │   │   ├── aitrackdown.py    # AITrackdown adapter
    │   │   ├── linear.py         # Linear adapter
    │   │   ├── jira.py           # Jira adapter
    │   │   └── github.py         # GitHub adapter
    │   ├── cache/                # Caching system
    │   │   └── memory.py         # Memory-based cache
    │   ├── cli/                  # Command-line interface
    │   │   └── main.py           # CLI implementation
    │   ├── mcp/                  # MCP server integration
    │   │   └── server.py         # MCP server
    │   └── __init__.py           # Package initialization
    ├── tests/                    # Test suite
    └── docs/                     # Documentation

Key Concepts
~~~~~~~~~~~~

**Universal Models:** All ticket data is represented using universal models (Task, Epic, Comment) that abstract platform-specific details.

**Adapter Pattern:** Each platform integration is implemented as an adapter that translates between universal models and platform APIs.

**Async-First:** All I/O operations use async/await for better performance and concurrency.

**Type Safety:** Full type hints and Pydantic models ensure reliability and developer experience.

Development Environment Setup
------------------------------

Prerequisites
~~~~~~~~~~~~~

- Python 3.9 or higher
- Git
- Virtual environment tool (venv, conda, or similar)

Setup Steps
~~~~~~~~~~~

1. **Clone the Repository:**

   .. code-block:: bash

       git clone https://github.com/mcp-ticketer/mcp-ticketer.git
       cd mcp-ticketer

2. **Create Virtual Environment:**

   .. code-block:: bash

       python -m venv .venv
       source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

3. **Install Development Dependencies:**

   .. code-block:: bash

       pip install -e ".[dev,test,docs]"

4. **Install Pre-commit Hooks:**

   .. code-block:: bash

       pre-commit install

5. **Verify Installation:**

   .. code-block:: bash

       python -m pytest tests/
       mcp-ticket --help

Development Workflow
~~~~~~~~~~~~~~~~~~~~

1. **Create Feature Branch:**

   .. code-block:: bash

       git checkout -b feature/your-feature-name

2. **Make Changes:**

   Follow the coding standards and write tests for new functionality.

3. **Run Tests:**

   .. code-block:: bash

       python -m pytest tests/ -v
       python -m pytest tests/ --cov=mcp_ticketer

4. **Run Linting:**

   .. code-block:: bash

       black src tests
       ruff check src tests
       mypy src

5. **Update Documentation:**

   .. code-block:: bash

       cd docs
       make html

6. **Commit Changes:**

   .. code-block:: bash

       git add .
       git commit -m "feat: add your feature description"

7. **Push and Create PR:**

   .. code-block:: bash

       git push origin feature/your-feature-name

Testing
-------

Test Structure
~~~~~~~~~~~~~~

The test suite is organized by functionality:

.. code-block:: text

    tests/
    ├── unit/                     # Unit tests
    │   ├── test_models.py        # Model tests
    │   ├── test_adapters/        # Adapter tests
    │   └── test_cli.py           # CLI tests
    ├── integration/              # Integration tests
    │   ├── test_adapters.py      # End-to-end adapter tests
    │   └── test_mcp.py           # MCP server tests
    ├── fixtures/                 # Test fixtures and data
    └── conftest.py               # Test configuration

Running Tests
~~~~~~~~~~~~~

**All Tests:**

.. code-block:: bash

    python -m pytest tests/

**Specific Test Categories:**

.. code-block:: bash

    # Unit tests only
    python -m pytest tests/unit/ -v

    # Integration tests only
    python -m pytest tests/integration/ -v

    # Specific adapter tests
    python -m pytest tests/unit/test_adapters/test_linear.py -v

**Coverage Report:**

.. code-block:: bash

    python -m pytest tests/ --cov=mcp_ticketer --cov-report=html
    open htmlcov/index.html

**Performance Tests:**

.. code-block:: bash

    python -m pytest tests/ -m "not slow"  # Skip slow tests
    python -m pytest tests/ -m slow        # Only slow tests

Writing Tests
~~~~~~~~~~~~~

**Unit Test Example:**

.. code-block:: python

    import pytest
    from mcp_ticketer.core.models import Task, Priority, TicketState


    class TestTask:
        def test_task_creation(self):
            task = Task(
                id="test-1",
                title="Test Task",
                description="Test description",
                priority=Priority.MEDIUM,
                state=TicketState.OPEN,
                creator="test@example.com"
            )

            assert task.id == "test-1"
            assert task.title == "Test Task"
            assert task.priority == Priority.MEDIUM
            assert task.state == TicketState.OPEN

        def test_state_transition(self):
            task = Task(
                id="test-1",
                title="Test Task",
                state=TicketState.OPEN,
                creator="test@example.com"
            )

            # Valid transition
            assert task.state.can_transition_to(TicketState.IN_PROGRESS)

            # Invalid transition
            assert not task.state.can_transition_to(TicketState.DONE)

**Integration Test Example:**

.. code-block:: python

    import pytest
    from mcp_ticketer.adapters.linear import LinearAdapter
    from mcp_ticketer.core.models import Task, Priority


    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_linear_adapter_create_task():
        # This test requires LINEAR_TOKEN environment variable
        adapter = LinearAdapter()

        task = Task(
            title="Integration Test Task",
            description="Created by integration test",
            priority=Priority.LOW,
            creator="test@example.com"
        )

        created_task = await adapter.create_task(task)

        assert created_task.id is not None
        assert created_task.title == task.title

        # Cleanup
        await adapter.delete_task(created_task.id)

Creating Custom Adapters
-------------------------

Adapter Interface
~~~~~~~~~~~~~~~~~

All adapters must implement the ``BaseAdapter`` interface:

.. code-block:: python

    from abc import ABC, abstractmethod
    from typing import List, Optional, Dict, Any
    from mcp_ticketer.core.models import Task, Epic, Comment


    class BaseAdapter(ABC):
        """Base adapter interface for ticket management platforms."""

        @abstractmethod
        async def create_task(self, task: Task) -> Task:
            """Create a new task."""
            pass

        @abstractmethod
        async def get_task(self, task_id: str) -> Optional[Task]:
            """Get task by ID."""
            pass

        @abstractmethod
        async def update_task(self, task_id: str, updates: Dict[str, Any]) -> Task:
            """Update task fields."""
            pass

        @abstractmethod
        async def list_tasks(
            self,
            limit: int = 20,
            offset: int = 0,
            filters: Optional[Dict[str, Any]] = None
        ) -> List[Task]:
            """List tasks with optional filtering."""
            pass

        @abstractmethod
        async def search_tasks(self, query: str) -> List[Task]:
            """Search tasks by query."""
            pass

        # Similar methods for epics and comments...

Example Adapter Implementation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Here's a simplified example of creating a custom adapter:

.. code-block:: python

    import httpx
    from typing import List, Optional, Dict, Any
    from mcp_ticketer.core.adapter import BaseAdapter
    from mcp_ticketer.core.models import Task, Priority, TicketState


    class CustomAdapter(BaseAdapter):
        """Adapter for a custom ticket management system."""

        def __init__(self, base_url: str, token: str, project_id: str):
            self.base_url = base_url
            self.token = token
            self.project_id = project_id
            self.client = httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"}
            )

        async def create_task(self, task: Task) -> Task:
            """Create a new task."""
            payload = {
                "title": task.title,
                "description": task.description,
                "priority": task.priority.value,
                "project_id": self.project_id,
                "assignee": task.assignee,
            }

            response = await self.client.post(
                f"{self.base_url}/api/tasks",
                json=payload
            )
            response.raise_for_status()

            data = response.json()
            return self._map_to_task(data)

        async def get_task(self, task_id: str) -> Optional[Task]:
            """Get task by ID."""
            try:
                response = await self.client.get(
                    f"{self.base_url}/api/tasks/{task_id}"
                )
                response.raise_for_status()

                data = response.json()
                return self._map_to_task(data)
            except httpx.HTTPStatusError:
                return None

        async def list_tasks(
            self,
            limit: int = 20,
            offset: int = 0,
            filters: Optional[Dict[str, Any]] = None
        ) -> List[Task]:
            """List tasks with optional filtering."""
            params = {
                "limit": limit,
                "offset": offset,
                "project_id": self.project_id,
            }

            if filters:
                params.update(filters)

            response = await self.client.get(
                f"{self.base_url}/api/tasks",
                params=params
            )
            response.raise_for_status()

            data = response.json()
            return [self._map_to_task(item) for item in data["tasks"]]

        def _map_to_task(self, data: Dict[str, Any]) -> Task:
            """Map platform data to universal Task model."""
            return Task(
                id=str(data["id"]),
                title=data["title"],
                description=data.get("description", ""),
                priority=Priority(data.get("priority", "medium")),
                state=self._map_state(data.get("status")),
                creator=data.get("creator", ""),
                assignee=data.get("assignee"),
                created_at=data.get("created_at"),
                updated_at=data.get("updated_at"),
                platform_data=data  # Store original data
            )

        def _map_state(self, platform_state: str) -> TicketState:
            """Map platform state to universal state."""
            mapping = {
                "new": TicketState.OPEN,
                "assigned": TicketState.OPEN,
                "working": TicketState.IN_PROGRESS,
                "review": TicketState.READY,
                "testing": TicketState.TESTED,
                "completed": TicketState.DONE,
                "closed": TicketState.CLOSED,
            }
            return mapping.get(platform_state, TicketState.OPEN)

Registering Your Adapter
~~~~~~~~~~~~~~~~~~~~~~~~~

To make your adapter available to the CLI and MCP server:

.. code-block:: python

    from mcp_ticketer.core.registry import AdapterRegistry
    from .custom_adapter import CustomAdapter

    # Register the adapter
    registry = AdapterRegistry()
    registry.register("custom", CustomAdapter)

Configuration Support
~~~~~~~~~~~~~~~~~~~~~

Add configuration support for your adapter:

.. code-block:: python

    class CustomAdapter(BaseAdapter):
        @classmethod
        def from_config(cls, config: Dict[str, Any]) -> "CustomAdapter":
            """Create adapter instance from configuration."""
            return cls(
                base_url=config["url"],
                token=config["token"],
                project_id=config["project"]
            )

        def get_config_schema(self) -> Dict[str, Any]:
            """Return configuration schema."""
            return {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "API base URL"},
                    "token": {"type": "string", "description": "Authentication token"},
                    "project": {"type": "string", "description": "Project ID"}
                },
                "required": ["url", "token", "project"]
            }

Extending Core Models
---------------------

Adding Custom Fields
~~~~~~~~~~~~~~~~~~~~~

You can extend the core models with platform-specific fields:

.. code-block:: python

    from pydantic import Field
    from mcp_ticketer.core.models import Task


    class CustomTask(Task):
        """Extended task model with custom fields."""

        custom_field: Optional[str] = None
        tags: List[str] = Field(default_factory=list)

        class Config:
            # Allow additional fields for platform-specific data
            extra = "allow"

Adding New Model Types
~~~~~~~~~~~~~~~~~~~~~~

Create new model types for specialized use cases:

.. code-block:: python

    from mcp_ticketer.core.models import BaseTicket


    class Release(BaseTicket):
        """Release model for tracking software releases."""

        version: str
        release_date: Optional[datetime] = None
        changelog: Optional[str] = None
        artifacts: List[str] = Field(default_factory=list)

MCP Server Extensions
---------------------

The MCP server can be extended with custom tools and handlers.

Custom Tools
~~~~~~~~~~~~

Add new MCP tools:

.. code-block:: python

    from mcp import Tool
    from mcp_ticketer.mcp.server import TicketServer


    class CustomTicketServer(TicketServer):
        """Extended MCP server with custom tools."""

        def get_tools(self) -> List[Tool]:
            """Return available tools."""
            tools = super().get_tools()

            # Add custom tool
            tools.append(Tool(
                name="analyze_tickets",
                description="Analyze ticket patterns and provide insights",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "timeframe": {"type": "string", "default": "30d"},
                        "filters": {"type": "object"}
                    }
                }
            ))

            return tools

        async def handle_analyze_tickets(self, arguments: Dict[str, Any]) -> str:
            """Handle ticket analysis tool."""
            # Implementation here
            return "Analysis results..."

CLI Extensions
--------------

Adding Custom Commands
~~~~~~~~~~~~~~~~~~~~~~

Extend the CLI with custom commands:

.. code-block:: python

    import typer
    from mcp_ticketer.cli.main import app


    @app.command()
    def analyze(
        timeframe: str = typer.Option("30d", help="Analysis timeframe"),
        format: str = typer.Option("table", help="Output format")
    ):
        """Analyze ticket patterns."""
        # Implementation here
        typer.echo("Analysis complete!")

Custom Output Formatters
~~~~~~~~~~~~~~~~~~~~~~~~~

Add new output formats:

.. code-block:: python

    from mcp_ticketer.cli.formatters import BaseFormatter


    class CustomFormatter(BaseFormatter):
        """Custom output formatter."""

        def format_tasks(self, tasks: List[Task]) -> str:
            """Format tasks for output."""
            # Custom formatting logic
            return formatted_output

Contribution Guidelines
-----------------------

Code Style
~~~~~~~~~~

We use the following tools for code consistency:

- **Black:** Code formatting
- **Ruff:** Linting and code quality
- **MyPy:** Type checking
- **isort:** Import sorting

Run these before committing:

.. code-block:: bash

    black src tests
    ruff check --fix src tests
    mypy src
    isort src tests

Documentation
~~~~~~~~~~~~~

- Document all public APIs with docstrings
- Use type hints for all function signatures
- Update documentation when adding features
- Include examples in docstrings

**Docstring Example:**

.. code-block:: python

    async def create_task(self, task: Task) -> Task:
        """Create a new task in the platform.

        Args:
            task: Task data to create

        Returns:
            The created task with platform-assigned ID

        Raises:
            AdapterError: If task creation fails

        Example:
            >>> adapter = LinearAdapter()
            >>> task = Task(title="New feature", creator="dev@example.com")
            >>> created = await adapter.create_task(task)
            >>> print(f"Created task {created.id}")
        """

Testing Guidelines
~~~~~~~~~~~~~~~~~~

- Write tests for all new functionality
- Aim for >90% test coverage
- Use descriptive test names
- Test both success and error paths
- Mock external API calls in unit tests

Commit Messages
~~~~~~~~~~~~~~~

Use conventional commit format:

.. code-block:: text

    <type>(<scope>): <description>

    [optional body]

    [optional footer]

**Types:**

- ``feat``: New feature
- ``fix``: Bug fix
- ``docs``: Documentation changes
- ``refactor``: Code refactoring
- ``test``: Adding tests
- ``chore``: Maintenance tasks

**Examples:**

.. code-block:: text

    feat(adapters): add Slack adapter support
    fix(cli): handle missing configuration gracefully
    docs(api): add examples to adapter documentation

Pull Request Process
~~~~~~~~~~~~~~~~~~~~

1. Create feature branch from ``main``
2. Make your changes with tests
3. Update documentation
4. Run full test suite
5. Create pull request with description
6. Address review feedback
7. Squash commits before merge

Release Process
---------------

Version Management
~~~~~~~~~~~~~~~~~~

We use semantic versioning (SemVer):

- **Major (X.0.0):** Breaking changes
- **Minor (0.X.0):** New features (backward compatible)
- **Patch (0.0.X):** Bug fixes

Creating a Release
~~~~~~~~~~~~~~~~~~

1. **Update Version:**

   .. code-block:: bash

       bump2version minor  # or major/patch

2. **Update Changelog:**

   Document changes in ``CHANGELOG.md``

3. **Create Release PR:**

   .. code-block:: bash

       git checkout -b release/v1.2.0
       git push origin release/v1.2.0

4. **Tag Release:**

   .. code-block:: bash

       git tag v1.2.0
       git push origin v1.2.0

5. **Build and Publish:**

   .. code-block:: bash

       python -m build
       twine upload dist/*

Getting Help
------------

- **GitHub Issues:** Report bugs and request features
- **Discussions:** General questions and discussions
- **Discord:** Real-time chat with maintainers
- **Documentation:** https://mcp-ticketer.readthedocs.io

We welcome contributions of all kinds - code, documentation, testing, and feedback!