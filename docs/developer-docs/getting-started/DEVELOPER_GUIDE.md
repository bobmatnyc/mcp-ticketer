# MCP Ticketer Developer Guide

Comprehensive guide for developers who want to understand, extend, or contribute to MCP Ticketer.

## Table of Contents

- [Architecture Deep Dive](#architecture-deep-dive)
- [Creating Custom Adapters](#creating-custom-adapters)
- [Extending the Data Model](#extending-the-data-model)
- [Testing Guidelines](#testing-guidelines)
- [Performance Optimization](#performance-optimization)
- [API Extension](#api-extension)
- [Code Style and Conventions](#code-style-and-conventions)
- [Development Workflow](#development-workflow)

## Architecture Deep Dive

### Design Philosophy

MCP Ticketer is built on several key architectural principles:

1. **🔌 Plugin Architecture**: Adapters as first-class plugins
2. **🎯 Domain-Driven Design**: Clear separation between business logic and infrastructure
3. **⚡ Async-First**: All I/O operations are asynchronous
4. **🛡️ Type Safety**: Comprehensive type hints and validation
5. **🧪 Testability**: Dependency injection and mocking support

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Ticketer System                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │     CLI     │  │ MCP Server  │  │  Web API    │             │
│  │  (Typer)    │  │(JSON-RPC)   │  │ (FastAPI)   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│            │             │                │                    │
│            └─────────────┼────────────────┘                    │
│                          │                                     │
├──────────────────────────┼─────────────────────────────────────┤
│                  ┌───────▼───────┐                             │
│                  │  Core Engine  │                             │
│                  │               │                             │
│   ┌──────────────┤  ┌─────────┐  ├──────────────┐              │
│   │ Models       │  │Registry │  │  Validation  │              │
│   │(Pydantic)    │  │(Factory)│  │(State Mach.) │              │
│   └──────────────┤  └─────────┘  ├──────────────┘              │
│                  │               │                             │
│                  │  ┌─────────┐  │                             │
│                  │  │ Cache   │  │                             │
│                  │  │ (TTL)   │  │                             │
│                  └──┤         ├──┘                             │
│                     └─────────┘                                │
├─────────────────────────┼───────────────────────────────────────┤
│                  ┌──────▼──────┐                               │
│                  │   Adapters  │                               │
│                  │             │                               │
│  ┌─────────┐  ┌──┤ BaseAdapter ├──┐  ┌─────────┐  ┌─────────┐  │
│  │AITrckDwn│  │  │(Abstract)   │  │  │ Linear  │  │ GitHub  │  │
│  │Adapter  │  │  └─────────────┘  │  │ Adapter │  │ Adapter │  │
│  └─────────┘  │                   │  └─────────┘  └─────────┘  │
│               │  ┌─────────────┐   │                          │
│               │  │    JIRA     │   │                          │
│               │  │   Adapter   │   │                          │
│               │  └─────────────┘   │                          │
│               └───────────────────────────┘                    │
│                         │                                     │
├─────────────────────────┼───────────────────────────────────────┤
│              ┌──────────▼──────────┐                          │
│              │  External Systems   │                          │
│              │                     │                          │
│   ┌────────┐ │ ┌─────┐ ┌──────┐   │ ┌──────┐ ┌─────────┐     │
│   │  Local │ │ │Lin. │ │ JIRA │   │ │GitHub│ │Custom   │     │
│   │  Files │ │ │ API │ │ REST │   │ │ REST │ │Systems  │     │
│   └────────┘ │ └─────┘ └──────┘   │ └──────┘ └─────────┘     │
│              └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

### Core Abstractions

#### Universal Ticket Model

The system uses a simplified, universal ticket model that maps to different systems:

```python
# Core hierarchy
Epic (high-level initiatives)
├── Task (individual work items)
    └── Comment (discussions and updates)

# State machine
open → in_progress → ready → tested → done → closed
  ↓         ↓          ↓        ↑
waiting  blocked    blocked   ↗
```

#### BaseAdapter Pattern

All ticket systems implement the same interface:

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, TypeVar, Generic

T = TypeVar("T", Epic, Task)

class BaseAdapter(ABC, Generic[T]):
    """Abstract base for all ticket system adapters."""

    # CRUD operations
    async def create(self, ticket: T) -> T: ...
    async def read(self, ticket_id: str) -> Optional[T]: ...
    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[T]: ...
    async def delete(self, ticket_id: str) -> bool: ...

    # Query operations
    async def list(self, limit: int = 10, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> List[T]: ...
    async def search(self, query: SearchQuery) -> List[T]: ...

    # Workflow operations
    async def transition_state(self, ticket_id: str, target_state: TicketState) -> Optional[T]: ...

    # Comment operations
    async def add_comment(self, comment: Comment) -> Comment: ...
    async def get_comments(self, ticket_id: str, limit: int = 10, offset: int = 0) -> List[Comment]: ...
```

### Data Flow Architecture

```mermaid
graph TD
    A[User Input] --> B{Interface}
    B -->|CLI| C[Typer Commands]
    B -->|MCP| D[JSON-RPC Server]
    B -->|Web| E[REST API]

    C --> F[Core Engine]
    D --> F
    E --> F

    F --> G[Validation Layer]
    G --> H[Business Logic]
    H --> I[Cache Layer]
    I --> J[Adapter Registry]

    J --> K{Adapter Type}
    K -->|aitrackdown| L[File System]
    K -->|linear| M[Linear API]
    K -->|jira| N[JIRA REST]
    K -->|github| O[GitHub API]

    L --> P[Response Processing]
    M --> P
    N --> P
    O --> P

    P --> Q[Response Formatting]
    Q --> R[User Output]
```

### State Management

Each adapter maintains state mappings between universal and system-specific states:

```python
class LinearAdapter(BaseAdapter[Task]):
    def _get_state_mapping(self) -> Dict[TicketState, str]:
        return {
            TicketState.OPEN: "Todo",
            TicketState.IN_PROGRESS: "In Progress",
            TicketState.READY: "Ready for Review",
            TicketState.TESTED: "In Review",
            TicketState.DONE: "Done",
            TicketState.CLOSED: "Canceled",
            TicketState.WAITING: "Waiting",
            TicketState.BLOCKED: "Blocked",
        }
```

## Creating Custom Adapters

### Adapter Development Process

1. **Define Requirements**: Identify target system's API and capabilities
2. **Create Adapter Class**: Implement BaseAdapter interface
3. **Handle State Mapping**: Map universal states to system states
4. **Implement Authentication**: Handle API keys, tokens, etc.
5. **Add Error Handling**: Graceful degradation and error recovery
6. **Write Tests**: Comprehensive test coverage
7. **Register Adapter**: Add to registry and CLI options

### Step-by-Step Example: Slack Adapter

Let's create a custom adapter for Slack messages as "tickets":

#### 1. Create Adapter File

```python
# src/mcp_ticketer/adapters/slack.py
"""Slack adapter for MCP Ticketer."""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from ..core.adapter import BaseAdapter
from ..core.models import Task, Comment, SearchQuery, TicketState, Priority


class SlackAdapter(BaseAdapter[Task]):
    """Adapter for Slack messages as tickets."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Slack adapter.

        Args:
            config: Configuration with 'token' and 'channel_id'
        """
        super().__init__(config)
        self.token = config.get("token")
        self.channel_id = config.get("channel_id")

        if not self.token:
            raise ValueError("Slack token is required")
        if not self.channel_id:
            raise ValueError("Slack channel_id is required")

        self.client = AsyncWebClient(token=self.token)

    def _get_state_mapping(self) -> Dict[TicketState, str]:
        """Map universal states to Slack thread states."""
        return {
            TicketState.OPEN: "open",
            TicketState.IN_PROGRESS: "in_progress",
            TicketState.READY: "ready",
            TicketState.TESTED: "tested",
            TicketState.DONE: "done",
            TicketState.CLOSED: "closed",
            TicketState.WAITING: "waiting",
            TicketState.BLOCKED: "blocked",
        }

    def _message_to_task(self, message: Dict[str, Any]) -> Task:
        """Convert Slack message to Task."""
        # Extract metadata from message
        text = message.get("text", "")
        timestamp = message.get("ts", "")
        user = message.get("user", "")
        thread_ts = message.get("thread_ts", timestamp)

        # Parse priority and state from message reactions or text
        priority = self._extract_priority(message)
        state = self._extract_state(message)

        return Task(
            id=f"slack-{thread_ts}",
            title=text[:100] + "..." if len(text) > 100 else text,
            description=text,
            state=state,
            priority=priority,
            assignee=user,
            created_at=datetime.fromtimestamp(float(timestamp)),
            updated_at=datetime.fromtimestamp(float(timestamp)),
            metadata={
                "slack_ts": timestamp,
                "slack_thread_ts": thread_ts,
                "slack_channel": self.channel_id,
                "slack_user": user,
            }
        )

    def _extract_priority(self, message: Dict[str, Any]) -> Priority:
        """Extract priority from Slack message reactions or text."""
        reactions = message.get("reactions", [])

        # Check for priority reactions
        for reaction in reactions:
            name = reaction.get("name", "")
            if name == "fire" or name == "exclamation":
                return Priority.CRITICAL
            elif name == "warning":
                return Priority.HIGH

        # Check text for priority keywords
        text = message.get("text", "").lower()
        if "urgent" in text or "critical" in text:
            return Priority.CRITICAL
        elif "high" in text:
            return Priority.HIGH
        elif "low" in text:
            return Priority.LOW

        return Priority.MEDIUM

    def _extract_state(self, message: Dict[str, Any]) -> TicketState:
        """Extract state from Slack message reactions."""
        reactions = message.get("reactions", [])

        # Check for state reactions
        for reaction in reactions:
            name = reaction.get("name", "")
            if name == "white_check_mark":
                return TicketState.DONE
            elif name == "eyes":
                return TicketState.IN_PROGRESS
            elif name == "hourglass_flowing_sand":
                return TicketState.WAITING
            elif name == "no_entry_sign":
                return TicketState.BLOCKED

        return TicketState.OPEN

    async def create(self, ticket: Task) -> Task:
        """Create a new Slack message thread."""
        try:
            # Post message to create thread
            response = await self.client.chat_postMessage(
                channel=self.channel_id,
                text=ticket.description or ticket.title,
                thread_ts=None  # Create new thread
            )

            # Update ticket with Slack metadata
            ticket.id = f"slack-{response['ts']}"
            ticket.metadata.update({
                "slack_ts": response["ts"],
                "slack_thread_ts": response["ts"],
                "slack_channel": self.channel_id,
            })
            ticket.created_at = datetime.now()
            ticket.updated_at = datetime.now()

            return ticket

        except SlackApiError as e:
            raise RuntimeError(f"Failed to create Slack message: {e.response['error']}")

    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read a Slack message by thread timestamp."""
        try:
            # Extract timestamp from ticket ID
            if not ticket_id.startswith("slack-"):
                return None

            ts = ticket_id[6:]  # Remove "slack-" prefix

            # Get conversation history for the thread
            response = await self.client.conversations_replies(
                channel=self.channel_id,
                ts=ts,
                limit=1
            )

            messages = response.get("messages", [])
            if not messages:
                return None

            return self._message_to_task(messages[0])

        except SlackApiError:
            return None

    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update a Slack message thread."""
        # For Slack, we might post a reply with updates
        ticket = await self.read(ticket_id)
        if not ticket:
            return None

        try:
            # Create update message
            update_text = []
            for key, value in updates.items():
                if key == "state":
                    update_text.append(f"State changed to: {value}")
                elif key == "assignee":
                    update_text.append(f"Assigned to: <@{value}>")
                elif key == "priority":
                    update_text.append(f"Priority: {value}")

            if update_text:
                await self.client.chat_postMessage(
                    channel=self.channel_id,
                    text=f"Update: {', '.join(update_text)}",
                    thread_ts=ticket.metadata.get("slack_thread_ts")
                )

            # Update local ticket object
            for key, value in updates.items():
                if hasattr(ticket, key):
                    setattr(ticket, key, value)

            ticket.updated_at = datetime.now()
            return ticket

        except SlackApiError as e:
            raise RuntimeError(f"Failed to update Slack message: {e.response['error']}")

    async def delete(self, ticket_id: str) -> bool:
        """Delete a Slack message."""
        try:
            ts = ticket_id[6:]  # Remove "slack-" prefix

            await self.client.chat_delete(
                channel=self.channel_id,
                ts=ts
            )
            return True

        except SlackApiError:
            return False

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """List Slack messages as tickets."""
        try:
            response = await self.client.conversations_history(
                channel=self.channel_id,
                limit=limit + offset
            )

            messages = response.get("messages", [])

            # Apply offset
            messages = messages[offset:offset + limit]

            # Convert to tasks
            tasks = []
            for message in messages:
                # Skip bot messages and system messages
                if message.get("subtype") or message.get("bot_id"):
                    continue

                task = self._message_to_task(message)

                # Apply filters
                if filters:
                    if "state" in filters and task.state != filters["state"]:
                        continue
                    if "priority" in filters and task.priority != filters["priority"]:
                        continue
                    if "assignee" in filters and task.assignee != filters["assignee"]:
                        continue

                tasks.append(task)

            return tasks

        except SlackApiError as e:
            raise RuntimeError(f"Failed to list Slack messages: {e.response['error']}")

    async def search(self, query: SearchQuery) -> List[Task]:
        """Search Slack messages."""
        try:
            # Use Slack search API
            search_query = query.query or "*"

            response = await self.client.search_messages(
                query=f"{search_query} in:#{self.channel_id}",
                count=query.limit
            )

            messages = response.get("messages", {}).get("matches", [])

            tasks = []
            for message in messages:
                task = self._message_to_task(message)

                # Apply additional filters
                if query.state and task.state != query.state:
                    continue
                if query.priority and task.priority != query.priority:
                    continue
                if query.assignee and task.assignee != query.assignee:
                    continue

                tasks.append(task)

            return tasks[:query.limit]

        except SlackApiError as e:
            raise RuntimeError(f"Failed to search Slack: {e.response['error']}")

    async def transition_state(
        self,
        ticket_id: str,
        target_state: TicketState
    ) -> Optional[Task]:
        """Transition ticket state by adding reaction."""
        ticket = await self.read(ticket_id)
        if not ticket:
            return None

        try:
            ts = ticket.metadata.get("slack_ts")

            # Add appropriate reaction for state
            reaction_map = {
                TicketState.IN_PROGRESS: "eyes",
                TicketState.DONE: "white_check_mark",
                TicketState.WAITING: "hourglass_flowing_sand",
                TicketState.BLOCKED: "no_entry_sign",
            }

            if target_state in reaction_map:
                await self.client.reactions_add(
                    channel=self.channel_id,
                    name=reaction_map[target_state],
                    timestamp=ts
                )

            # Update ticket state
            ticket.state = target_state
            ticket.updated_at = datetime.now()

            return ticket

        except SlackApiError as e:
            raise RuntimeError(f"Failed to transition state: {e.response['error']}")

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment as a thread reply."""
        try:
            # Extract thread timestamp from ticket ID
            ticket_id = comment.ticket_id
            if not ticket_id.startswith("slack-"):
                raise ValueError("Invalid ticket ID for Slack")

            thread_ts = ticket_id[6:]  # Remove "slack-" prefix

            # Post reply to thread
            response = await self.client.chat_postMessage(
                channel=self.channel_id,
                text=comment.content,
                thread_ts=thread_ts
            )

            # Update comment with Slack metadata
            comment.id = f"slack-comment-{response['ts']}"
            comment.created_at = datetime.now()
            comment.metadata.update({
                "slack_ts": response["ts"],
                "slack_thread_ts": thread_ts,
                "slack_channel": self.channel_id,
            })

            return comment

        except SlackApiError as e:
            raise RuntimeError(f"Failed to add comment: {e.response['error']}")

    async def get_comments(
        self,
        ticket_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Comment]:
        """Get comments for a ticket (thread replies)."""
        try:
            if not ticket_id.startswith("slack-"):
                return []

            thread_ts = ticket_id[6:]  # Remove "slack-" prefix

            # Get thread replies
            response = await self.client.conversations_replies(
                channel=self.channel_id,
                ts=thread_ts,
                limit=limit + offset + 1  # +1 for parent message
            )

            messages = response.get("messages", [])

            # Skip parent message and apply offset
            replies = messages[1 + offset:1 + offset + limit]

            comments = []
            for message in replies:
                comment = Comment(
                    id=f"slack-comment-{message['ts']}",
                    ticket_id=ticket_id,
                    content=message.get("text", ""),
                    author=message.get("user", ""),
                    created_at=datetime.fromtimestamp(float(message["ts"])),
                    metadata={
                        "slack_ts": message["ts"],
                        "slack_thread_ts": thread_ts,
                        "slack_channel": self.channel_id,
                        "slack_user": message.get("user", ""),
                    }
                )
                comments.append(comment)

            return comments

        except SlackApiError as e:
            raise RuntimeError(f"Failed to get comments: {e.response['error']}")

    async def close(self) -> None:
        """Close adapter and cleanup resources."""
        if hasattr(self.client, 'close'):
            await self.client.close()
```

#### 2. Register the Adapter

```python
# src/mcp_ticketer/adapters/__init__.py
from .slack import SlackAdapter
from ..core.registry import AdapterRegistry

# Register the adapter
AdapterRegistry.register("slack", SlackAdapter)
```

#### 3. Add CLI Support

```python
# src/mcp_ticketer/cli/main.py
class AdapterType(str, Enum):
    # ... existing adapters
    SLACK = "slack"

# Add Slack options to init command
def init(
    # ... existing options
    slack_token: Optional[str] = typer.Option(
        None,
        "--slack-token",
        help="Slack Bot User OAuth Token"
    ),
    slack_channel: Optional[str] = typer.Option(
        None,
        "--slack-channel",
        help="Slack channel ID for tickets"
    ),
) -> None:
    """Initialize MCP Ticketer configuration."""
    # ... existing code

    elif adapter == AdapterType.SLACK:
        token = slack_token or os.getenv("SLACK_TOKEN")
        channel = slack_channel or os.getenv("SLACK_CHANNEL")

        if not token:
            console.print("[red]Error:[/red] Slack token is required")
            raise typer.Exit(1)

        if not channel:
            console.print("[red]Error:[/red] Slack channel ID is required")
            raise typer.Exit(1)

        config["config"]["token"] = token
        config["config"]["channel_id"] = channel
```

#### 4. Add Tests

```python
# tests/adapters/test_slack.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp_ticketer.adapters.slack import SlackAdapter
from mcp_ticketer.core.models import Task, Priority, TicketState


@pytest.fixture
def slack_config():
    return {
        "token": "xoxb-test-token",
        "channel_id": "C1234567890"
    }


@pytest.fixture
def slack_adapter(slack_config):
    adapter = SlackAdapter(slack_config)
    adapter.client = AsyncMock()
    return adapter


@pytest.mark.asyncio
async def test_create_ticket(slack_adapter):
    """Test creating a ticket in Slack."""
    # Mock Slack API response
    slack_adapter.client.chat_postMessage.return_value = {
        "ts": "1234567890.123456"
    }

    # Create ticket
    ticket = Task(
        title="Test ticket",
        description="Test description",
        priority=Priority.HIGH
    )

    result = await slack_adapter.create(ticket)

    # Verify API call
    slack_adapter.client.chat_postMessage.assert_called_once_with(
        channel="C1234567890",
        text="Test description",
        thread_ts=None
    )

    # Verify result
    assert result.id == "slack-1234567890.123456"
    assert result.title == "Test ticket"
    assert result.metadata["slack_ts"] == "1234567890.123456"


@pytest.mark.asyncio
async def test_list_tickets(slack_adapter):
    """Test listing tickets from Slack."""
    # Mock Slack API response
    slack_adapter.client.conversations_history.return_value = {
        "messages": [
            {
                "text": "Test message 1",
                "ts": "1234567890.123456",
                "user": "U123456",
                "reactions": [{"name": "fire"}]
            },
            {
                "text": "Test message 2",
                "ts": "1234567890.123457",
                "user": "U123457"
            }
        ]
    }

    # List tickets
    tickets = await slack_adapter.list(limit=10)

    # Verify results
    assert len(tickets) == 2
    assert tickets[0].title == "Test message 1"
    assert tickets[0].priority == Priority.CRITICAL  # fire reaction
    assert tickets[1].title == "Test message 2"
    assert tickets[1].priority == Priority.MEDIUM  # default
```

### Adapter Registration

The registry system automatically discovers and loads adapters:

```python
# src/mcp_ticketer/adapters/__init__.py
"""Adapter package with automatic registration."""

from ..core.registry import AdapterRegistry

# Import and register all adapters
from .aitrackdown import AITrackdownAdapter
from .linear import LinearAdapter
from .jira import JiraAdapter
from .github import GitHubAdapter
from .slack import SlackAdapter

# Automatic registration
AdapterRegistry.register("aitrackdown", AITrackdownAdapter)
AdapterRegistry.register("linear", LinearAdapter)
AdapterRegistry.register("jira", JiraAdapter)
AdapterRegistry.register("github", GitHubAdapter)
AdapterRegistry.register("slack", SlackAdapter)

__all__ = [
    "AITrackdownAdapter",
    "LinearAdapter",
    "JiraAdapter",
    "GitHubAdapter",
    "SlackAdapter",
]
```

### Configuration Schema

Define configuration schemas for type safety:

```python
# src/mcp_ticketer/adapters/slack.py
from pydantic import BaseModel, Field
from typing import Optional

class SlackConfig(BaseModel):
    """Configuration schema for Slack adapter."""

    token: str = Field(..., description="Slack Bot User OAuth Token")
    channel_id: str = Field(..., description="Slack channel ID for tickets")
    workspace_id: Optional[str] = Field(None, description="Slack workspace ID")
    thread_broadcast: bool = Field(False, description="Broadcast thread replies to channel")
    reaction_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "priority_high": "exclamation",
            "priority_critical": "fire",
            "state_done": "white_check_mark",
            "state_blocked": "no_entry_sign",
        },
        description="Custom emoji mappings"
    )

class SlackAdapter(BaseAdapter[Task]):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Validate configuration
        self.config_schema = SlackConfig(**config)

        self.token = self.config_schema.token
        self.channel_id = self.config_schema.channel_id
        self.client = AsyncWebClient(token=self.token)
```

## Extending the Data Model

### Custom Fields

Add custom fields while maintaining compatibility:

```python
# src/mcp_ticketer/core/models.py
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class ExtendedTask(Task):
    """Extended task model with additional fields."""

    # Custom fields
    story_points: Optional[int] = Field(None, description="Story points estimate")
    epic_id: Optional[str] = Field(None, description="Parent epic ID")
    sprint_id: Optional[str] = Field(None, description="Sprint identifier")
    external_url: Optional[str] = Field(None, description="External reference URL")

    # Custom metadata
    custom_fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="System-specific custom fields"
    )

    # Computed properties
    @property
    def is_overdue(self) -> bool:
        """Check if ticket is overdue."""
        if not self.due_date:
            return False
        return datetime.now() > self.due_date

    @property
    def age_in_days(self) -> int:
        """Calculate ticket age in days."""
        if not self.created_at:
            return 0
        return (datetime.now() - self.created_at).days

    # Custom validation
    @validator('story_points')
    def validate_story_points(cls, v):
        """Validate story points are positive."""
        if v is not None and v < 0:
            raise ValueError('Story points must be non-negative')
        return v
```

### Adapter-Specific Models

Create specialized models for different adapters:

```python
# src/mcp_ticketer/adapters/jira.py
from ..core.models import Task
from typing import List, Optional

class JiraTask(Task):
    """JIRA-specific task model."""

    # JIRA-specific fields
    issue_type: Optional[str] = Field(None, description="JIRA issue type")
    project_key: Optional[str] = Field(None, description="JIRA project key")
    components: List[str] = Field(default_factory=list, description="JIRA components")
    fix_versions: List[str] = Field(default_factory=list, description="Fix versions")
    affects_versions: List[str] = Field(default_factory=list, description="Affected versions")

    # JIRA workflow
    resolution: Optional[str] = Field(None, description="Resolution reason")
    status_category: Optional[str] = Field(None, description="Status category")

    @classmethod
    def from_jira_issue(cls, jira_issue: Dict[str, Any]) -> "JiraTask":
        """Convert JIRA API response to JiraTask."""
        fields = jira_issue.get("fields", {})

        return cls(
            id=jira_issue["key"],
            title=fields.get("summary", ""),
            description=fields.get("description", ""),
            state=cls._map_jira_status(fields.get("status", {})),
            priority=cls._map_jira_priority(fields.get("priority", {})),
            assignee=cls._extract_user(fields.get("assignee")),
            issue_type=fields.get("issuetype", {}).get("name"),
            project_key=fields.get("project", {}).get("key"),
            components=[c["name"] for c in fields.get("components", [])],
            resolution=fields.get("resolution", {}).get("name") if fields.get("resolution") else None,
            metadata={
                "jira_id": jira_issue["id"],
                "jira_key": jira_issue["key"],
                "jira_self": jira_issue["self"],
                "raw_fields": fields,
            }
        )

    def to_jira_update(self) -> Dict[str, Any]:
        """Convert to JIRA update format."""
        update = {}

        if self.title:
            update["summary"] = self.title
        if self.description:
            update["description"] = self.description
        if self.assignee:
            update["assignee"] = {"name": self.assignee}

        return {"fields": update}
```

### Universal Model Extensions

Add features that work across all adapters:

```python
# src/mcp_ticketer/core/models.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, List

class TicketSize(str, Enum):
    """Universal ticket size estimates."""
    XS = "xs"  # < 1 day
    S = "small"  # 1-2 days
    M = "medium"  # 3-5 days
    L = "large"  # 1-2 weeks
    XL = "xlarge"  # > 2 weeks

class TicketRelationType(str, Enum):
    """Types of relationships between tickets."""
    BLOCKS = "blocks"
    BLOCKED_BY = "blocked_by"
    RELATES_TO = "relates_to"
    DUPLICATES = "duplicates"
    DUPLICATED_BY = "duplicated_by"
    PARENT_OF = "parent_of"
    CHILD_OF = "child_of"

class TicketRelation(BaseModel):
    """Relationship between two tickets."""

    source_id: str = Field(..., description="Source ticket ID")
    target_id: str = Field(..., description="Target ticket ID")
    relation_type: TicketRelationType = Field(..., description="Type of relationship")
    created_at: Optional[datetime] = Field(None, description="When relation was created")
    created_by: Optional[str] = Field(None, description="Who created the relation")

class EnhancedTask(Task):
    """Enhanced task with additional universal fields."""

    # Estimation and tracking
    size_estimate: Optional[TicketSize] = Field(None, description="Size estimate")
    due_date: Optional[datetime] = Field(None, description="Due date")
    started_at: Optional[datetime] = Field(None, description="When work started")
    completed_at: Optional[datetime] = Field(None, description="When work completed")

    # Relationships
    relations: List[TicketRelation] = Field(
        default_factory=list,
        description="Relationships to other tickets"
    )

    # Workflow tracking
    state_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of state changes"
    )

    # Computed properties
    @property
    def cycle_time(self) -> Optional[timedelta]:
        """Calculate cycle time from start to completion."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def is_blocked(self) -> bool:
        """Check if ticket is blocked by other tickets."""
        return any(
            r.relation_type == TicketRelationType.BLOCKED_BY
            for r in self.relations
        )

    @property
    def blocking_tickets(self) -> List[str]:
        """Get IDs of tickets this one blocks."""
        return [
            r.target_id for r in self.relations
            if r.relation_type == TicketRelationType.BLOCKS
        ]

    def add_relation(
        self,
        target_id: str,
        relation_type: TicketRelationType,
        created_by: Optional[str] = None
    ) -> None:
        """Add a relationship to another ticket."""
        relation = TicketRelation(
            source_id=self.id,
            target_id=target_id,
            relation_type=relation_type,
            created_at=datetime.now(),
            created_by=created_by
        )
        self.relations.append(relation)

    def record_state_change(
        self,
        from_state: TicketState,
        to_state: TicketState,
        changed_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> None:
        """Record a state change in history."""
        self.state_history.append({
            "from_state": from_state,
            "to_state": to_state,
            "changed_at": datetime.now().isoformat(),
            "changed_by": changed_by,
            "reason": reason,
        })
```

## Testing Guidelines

### Testing Architecture

MCP Ticketer uses a comprehensive testing strategy:

```
tests/
├── unit/              # Fast, isolated unit tests
│   ├── core/          # Core business logic tests
│   ├── adapters/      # Adapter implementation tests
│   ├── cli/           # CLI interface tests
│   └── mcp/           # MCP server tests
├── integration/       # Integration tests with mocks
├── e2e/              # End-to-end tests with real systems
├── performance/       # Performance and load tests
├── fixtures/         # Test data and fixtures
└── conftest.py       # Pytest configuration
```

### Unit Testing Best Practices

#### Test Adapters with Mocks

```python
# tests/adapters/test_linear.py
import pytest
from unittest.mock import AsyncMock, patch
from mcp_ticketer.adapters.linear import LinearAdapter
from mcp_ticketer.core.models import Task, Priority, TicketState

@pytest.fixture
def linear_config():
    return {
        "team_id": "test-team-id",
        "api_key": "test-api-key"
    }

@pytest.fixture
def linear_adapter(linear_config):
    with patch('gql.Client'):
        adapter = LinearAdapter(linear_config)
        adapter.client = AsyncMock()
        return adapter

@pytest.mark.asyncio
async def test_create_task(linear_adapter):
    """Test task creation with Linear adapter."""
    # Mock GraphQL response
    linear_adapter.client.execute.return_value = {
        "issueCreate": {
            "issue": {
                "id": "test-issue-id",
                "title": "Test Issue",
                "state": {"name": "Todo"},
                "priority": 3,
                "createdAt": "2024-01-15T10:00:00Z"
            }
        }
    }

    # Create task
    task = Task(
        title="Test Issue",
        description="Test description",
        priority=Priority.HIGH
    )

    result = await linear_adapter.create(task)

    # Verify GraphQL call
    linear_adapter.client.execute.assert_called_once()

    # Verify result
    assert result.id == "test-issue-id"
    assert result.title == "Test Issue"
    assert result.state == TicketState.OPEN

@pytest.mark.asyncio
async def test_state_transition_validation(linear_adapter):
    """Test state transition validation."""
    # Mock existing task
    linear_adapter.read = AsyncMock(return_value=Task(
        id="test-id",
        title="Test",
        state=TicketState.OPEN
    ))

    # Valid transition
    assert await linear_adapter.validate_transition("test-id", TicketState.IN_PROGRESS)

    # Invalid transition
    assert not await linear_adapter.validate_transition("test-id", TicketState.DONE)

@pytest.mark.asyncio
async def test_error_handling(linear_adapter):
    """Test error handling in adapter."""
    # Mock GraphQL error
    linear_adapter.client.execute.side_effect = Exception("API Error")

    task = Task(title="Test")

    with pytest.raises(Exception):
        await linear_adapter.create(task)
```

#### Test Core Logic

```python
# tests/core/test_models.py
import pytest
from datetime import datetime
from mcp_ticketer.core.models import Task, TicketState, Priority

def test_ticket_state_transitions():
    """Test state machine transitions."""
    # Valid transitions
    assert TicketState.OPEN.can_transition_to(TicketState.IN_PROGRESS)
    assert TicketState.IN_PROGRESS.can_transition_to(TicketState.READY)
    assert TicketState.READY.can_transition_to(TicketState.TESTED)

    # Invalid transitions
    assert not TicketState.OPEN.can_transition_to(TicketState.DONE)
    assert not TicketState.DONE.can_transition_to(TicketState.OPEN)

def test_task_validation():
    """Test task field validation."""
    # Valid task
    task = Task(
        title="Valid Task",
        priority=Priority.HIGH,
        state=TicketState.OPEN
    )
    assert task.title == "Valid Task"

    # Invalid task - empty title
    with pytest.raises(ValueError):
        Task(title="", priority=Priority.HIGH)

def test_task_metadata():
    """Test task metadata handling."""
    task = Task(
        title="Test Task",
        metadata={"custom_field": "value"}
    )

    assert task.metadata["custom_field"] == "value"

    # Test metadata updates
    task.metadata["new_field"] = "new_value"
    assert task.metadata["new_field"] == "new_value"
```

#### Test CLI Commands

```python
# tests/cli/test_commands.py
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, AsyncMock
from mcp_ticketer.cli.main import app

runner = CliRunner()

def test_create_command():
    """Test ticket creation command."""
    with patch('mcp_ticketer.cli.main.get_adapter') as mock_adapter:
        # Mock adapter
        mock_instance = AsyncMock()
        mock_instance.create.return_value = Task(
            id="test-123",
            title="Test Ticket",
            state=TicketState.OPEN
        )
        mock_adapter.return_value = mock_instance

        # Run command
        result = runner.invoke(app, [
            "create", "Test Ticket",
            "--description", "Test description",
            "--priority", "high"
        ])

        # Verify output
        assert result.exit_code == 0
        assert "Created ticket: test-123" in result.stdout

def test_list_command():
    """Test ticket listing command."""
    with patch('mcp_ticketer.cli.main.get_adapter') as mock_adapter:
        # Mock adapter with tickets
        mock_instance = AsyncMock()
        mock_instance.list.return_value = [
            Task(id="1", title="Task 1", state=TicketState.OPEN),
            Task(id="2", title="Task 2", state=TicketState.IN_PROGRESS),
        ]
        mock_adapter.return_value = mock_instance

        # Run command
        result = runner.invoke(app, ["list", "--limit", "10"])

        # Verify output
        assert result.exit_code == 0
        assert "Task 1" in result.stdout
        assert "Task 2" in result.stdout
```

### Integration Testing

Test adapters with real APIs in controlled environments:

```python
# tests/integration/test_linear_integration.py
import pytest
import os
from mcp_ticketer.adapters.linear import LinearAdapter

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("LINEAR_API_KEY"),
    reason="LINEAR_API_KEY not set"
)
class TestLinearIntegration:
    """Integration tests for Linear adapter."""

    @pytest.fixture
    def linear_adapter(self):
        config = {
            "team_id": os.getenv("LINEAR_TEAM_ID"),
            "api_key": os.getenv("LINEAR_API_KEY")
        }
        return LinearAdapter(config)

    @pytest.mark.asyncio
    async def test_create_and_delete_ticket(self, linear_adapter):
        """Test creating and deleting a ticket."""
        # Create ticket
        task = Task(
            title="[Test] Integration test ticket",
            description="This is a test ticket created by integration tests",
            priority=Priority.LOW
        )

        created = await linear_adapter.create(task)
        assert created.id is not None
        assert created.title == task.title

        # Clean up
        deleted = await linear_adapter.delete(created.id)
        assert deleted

    @pytest.mark.asyncio
    async def test_search_functionality(self, linear_adapter):
        """Test search functionality."""
        from mcp_ticketer.core.models import SearchQuery

        query = SearchQuery(
            query="test",
            state=TicketState.OPEN,
            limit=5
        )

        results = await linear_adapter.search(query)
        assert isinstance(results, list)
        assert len(results) <= 5

        for ticket in results:
            assert isinstance(ticket, Task)
```

### Performance Testing

Measure and validate performance characteristics:

```python
# tests/performance/test_adapter_performance.py
import pytest
import asyncio
import time
from mcp_ticketer.adapters.aitrackdown import AITrackdownAdapter

@pytest.mark.performance
class TestAdapterPerformance:
    """Performance tests for adapters."""

    @pytest.fixture
    def aitrackdown_adapter(self, tmp_path):
        config = {"base_path": str(tmp_path)}
        return AITrackdownAdapter(config)

    @pytest.mark.asyncio
    async def test_bulk_create_performance(self, aitrackdown_adapter):
        """Test performance of bulk ticket creation."""
        num_tickets = 100

        # Generate test tickets
        tasks = [
            Task(
                title=f"Performance test ticket {i}",
                description=f"Test ticket {i} for performance testing",
                priority=Priority.MEDIUM
            )
            for i in range(num_tickets)
        ]

        # Measure creation time
        start_time = time.time()

        created_tasks = []
        for task in tasks:
            created = await aitrackdown_adapter.create(task)
            created_tasks.append(created)

        end_time = time.time()

        # Verify results
        assert len(created_tasks) == num_tickets

        # Performance assertion (adjust based on requirements)
        total_time = end_time - start_time
        time_per_ticket = total_time / num_tickets
        assert time_per_ticket < 0.1  # Less than 100ms per ticket

        print(f"Created {num_tickets} tickets in {total_time:.2f}s")
        print(f"Average time per ticket: {time_per_ticket:.3f}s")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, aitrackdown_adapter):
        """Test concurrent adapter operations."""
        num_concurrent = 10

        # Create tasks concurrently
        create_tasks = [
            aitrackdown_adapter.create(Task(
                title=f"Concurrent test {i}",
                description=f"Concurrent test ticket {i}"
            ))
            for i in range(num_concurrent)
        ]

        start_time = time.time()
        results = await asyncio.gather(*create_tasks)
        end_time = time.time()

        # Verify results
        assert len(results) == num_concurrent
        assert all(r.id for r in results)

        # Performance check
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete in under 2 seconds

        print(f"Created {num_concurrent} tickets concurrently in {total_time:.2f}s")
```

### Test Configuration

```python
# conftest.py
import pytest
import asyncio
from pathlib import Path
from mcp_ticketer.core.registry import AdapterRegistry

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def temp_config_dir(tmp_path):
    """Provide temporary directory for test configurations."""
    config_dir = tmp_path / "test_config"
    config_dir.mkdir()
    return config_dir

@pytest.fixture(autouse=True)
def clean_adapter_registry():
    """Clean adapter registry before each test."""
    # Store current state
    original_adapters = AdapterRegistry._adapters.copy()
    original_instances = AdapterRegistry._instances.copy()

    yield

    # Restore original state
    AdapterRegistry._adapters = original_adapters
    AdapterRegistry._instances = original_instances

# Pytest markers
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
```

### Test Execution

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/                    # Unit tests only
pytest tests/integration/ -m integration  # Integration tests
pytest tests/performance/ -m performance  # Performance tests

# Run with coverage
pytest --cov=mcp_ticketer --cov-report=html

# Run specific adapter tests
pytest tests/adapters/test_linear.py -v

# Run with different markers
pytest -m "not slow"                 # Skip slow tests
pytest -m "integration or performance"  # Run integration and performance
```

## Performance Optimization

### Caching Strategy

MCP Ticketer implements multi-level caching:

#### 1. In-Memory Cache with TTL

```python
# src/mcp_ticketer/cache/memory.py
from typing import Optional, Any
import time

class SmartCache:
    """Intelligent caching with adaptive TTL."""

    def __init__(self):
        self._cache = {}
        self._access_counts = {}
        self._hit_rates = {}

    async def get_with_stats(self, key: str) -> tuple[Optional[Any], dict]:
        """Get value with cache statistics."""
        entry = self._cache.get(key)

        if entry and not entry.is_expired():
            # Cache hit
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            self._update_hit_rate(key, hit=True)
            return entry.value, {"hit": True, "age": time.time() - entry.created_at}
        else:
            # Cache miss
            self._update_hit_rate(key, hit=False)
            if entry:
                del self._cache[key]  # Remove expired
            return None, {"hit": False}

    def _update_hit_rate(self, key: str, hit: bool):
        """Update hit rate statistics."""
        if key not in self._hit_rates:
            self._hit_rates[key] = {"hits": 0, "total": 0}

        if hit:
            self._hit_rates[key]["hits"] += 1
        self._hit_rates[key]["total"] += 1

    def get_cache_stats(self) -> dict:
        """Get comprehensive cache statistics."""
        total_entries = len(self._cache)
        total_hits = sum(stats["hits"] for stats in self._hit_rates.values())
        total_requests = sum(stats["total"] for stats in self._hit_rates.values())

        return {
            "total_entries": total_entries,
            "total_hits": total_hits,
            "total_requests": total_requests,
            "hit_rate": total_hits / total_requests if total_requests > 0 else 0,
            "by_key": self._hit_rates.copy()
        }
```

#### 2. Adapter-Level Caching

```python
# src/mcp_ticketer/adapters/linear.py
from functools import wraps
from ..cache.memory import cache_decorator

class LinearAdapter(BaseAdapter[Task]):

    @cache_decorator(ttl=300, key_prefix="linear")  # 5 minute cache
    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read ticket with caching."""
        # Implementation...
        pass

    @cache_decorator(ttl=60, key_prefix="linear")  # 1 minute cache for lists
    async def list(self, limit: int = 10, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> List[Task]:
        """List tickets with caching."""
        # Implementation...
        pass

    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update ticket and invalidate cache."""
        result = await self._do_update(ticket_id, updates)

        if result:
            # Invalidate related cache entries
            await self._invalidate_ticket_cache(ticket_id)
            await self._invalidate_list_cache()

        return result

    async def _invalidate_ticket_cache(self, ticket_id: str):
        """Invalidate cache entries for specific ticket."""
        # Remove from read cache
        self.read.cache_delete(ticket_id)

        # Could also invalidate search results containing this ticket
        # This is adapter-specific logic

    async def _invalidate_list_cache(self):
        """Invalidate list and search caches."""
        # This is a simplified approach - in practice you might be more selective
        await self.list.cache_clear()
```

### Async Optimization

#### Batch Operations

```python
# src/mcp_ticketer/adapters/base_batch.py
from typing import List, Dict, Any
import asyncio

class BatchAdapter(BaseAdapter[Task]):
    """Base adapter with batch operation support."""

    async def bulk_create(self, tickets: List[Task], batch_size: int = 10) -> List[Task]:
        """Create multiple tickets efficiently."""
        results = []

        # Process in batches to avoid overwhelming the API
        for i in range(0, len(tickets), batch_size):
            batch = tickets[i:i + batch_size]

            # Create batch concurrently
            batch_tasks = [self.create(ticket) for ticket in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    # Log error but continue with other tickets
                    print(f"Failed to create ticket {batch[j].title}: {result}")
                    # Could add to retry queue
                else:
                    results.append(result)

            # Rate limiting - pause between batches
            await asyncio.sleep(0.1)

        return results

    async def bulk_update(self, updates: List[Dict[str, Any]], batch_size: int = 10) -> List[Task]:
        """Update multiple tickets efficiently."""
        results = []

        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]

            # Update batch concurrently
            update_tasks = [
                self.update(update["ticket_id"], update["changes"])
                for update in batch
            ]

            batch_results = await asyncio.gather(*update_tasks, return_exceptions=True)

            # Process results
            for result in batch_results:
                if not isinstance(result, Exception) and result:
                    results.append(result)

            await asyncio.sleep(0.1)  # Rate limiting

        return results
```

#### Connection Pooling

```python
# src/mcp_ticketer/adapters/http_base.py
import httpx
from typing import Optional, Dict, Any

class HTTPAdapter(BaseAdapter[Task]):
    """Base adapter with HTTP connection pooling."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

        # Configure HTTP client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=5.0
            ),
            headers={
                "User-Agent": "MCP-Ticketer/1.0",
                "Accept": "application/json",
            }
        )

    async def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with automatic retries."""
        max_retries = 3
        backoff_factor = 1

        for attempt in range(max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

            except httpx.TimeoutException:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff_factor * (2 ** attempt))

            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    # Retry on server errors
                    await asyncio.sleep(backoff_factor * (2 ** attempt))
                    continue
                raise

    async def close(self) -> None:
        """Close HTTP client and connections."""
        await self._client.aclose()
```

### Database Optimization (for AITrackdown)

```python
# src/mcp_ticketer/adapters/aitrackdown_optimized.py
import aiofiles
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import sqlite3
import aiosqlite

class OptimizedAITrackdownAdapter(BaseAdapter[Task]):
    """Optimized AITrackdown adapter with SQLite indexing."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_path = Path(config.get("base_path", ".aitrackdown"))
        self.db_path = self.base_path / "index.db"

        # Initialize SQLite index
        asyncio.create_task(self._init_db())

    async def _init_db(self):
        """Initialize SQLite database for indexing."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    state TEXT,
                    priority TEXT,
                    assignee TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    tags TEXT,  -- JSON array
                    file_path TEXT
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_state ON tickets(state)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority ON tickets(priority)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_assignee ON tickets(assignee)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_created ON tickets(created_at)
            """)

            await db.commit()

    async def create(self, ticket: Task) -> Task:
        """Create ticket with automatic indexing."""
        # Create file
        created_ticket = await super().create(ticket)

        # Update index
        await self._index_ticket(created_ticket)

        return created_ticket

    async def _index_ticket(self, ticket: Task):
        """Add or update ticket in search index."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO tickets
                (id, title, state, priority, assignee, created_at, updated_at, tags, file_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket.id,
                ticket.title,
                ticket.state,
                ticket.priority,
                ticket.assignee,
                ticket.created_at.isoformat() if ticket.created_at else None,
                ticket.updated_at.isoformat() if ticket.updated_at else None,
                json.dumps(ticket.tags),
                str(self.base_path / f"{ticket.id}.json")
            ))
            await db.commit()

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """Fast listing using SQLite index."""
        query = "SELECT file_path FROM tickets"
        params = []

        if filters:
            conditions = []
            if "state" in filters:
                conditions.append("state = ?")
                params.append(filters["state"])
            if "priority" in filters:
                conditions.append("priority = ?")
                params.append(filters["priority"])
            if "assignee" in filters:
                conditions.append("assignee = ?")
                params.append(filters["assignee"])

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        # Load tickets from files
        tickets = []
        for (file_path,) in rows:
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    ticket_data = json.loads(content)
                    ticket = Task.model_validate(ticket_data)
                    tickets.append(ticket)
            except (FileNotFoundError, json.JSONDecodeError):
                # File might have been deleted, remove from index
                await self._remove_from_index(file_path)

        return tickets

    async def search(self, query: SearchQuery) -> List[Task]:
        """Fast search using SQLite FTS."""
        # Use SQLite's FTS (Full-Text Search) for text queries
        sql_query = """
            SELECT file_path FROM tickets
            WHERE 1=1
        """
        params = []

        # Text search
        if query.query:
            sql_query += " AND (title LIKE ? OR id LIKE ?)"
            search_term = f"%{query.query}%"
            params.extend([search_term, search_term])

        # Other filters
        if query.state:
            sql_query += " AND state = ?"
            params.append(query.state)

        if query.priority:
            sql_query += " AND priority = ?"
            params.append(query.priority)

        if query.assignee:
            sql_query += " AND assignee = ?"
            params.append(query.assignee)

        sql_query += " ORDER BY created_at DESC LIMIT ?"
        params.append(query.limit)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(sql_query, params) as cursor:
                rows = await cursor.fetchall()

        # Load matching tickets
        tickets = []
        for (file_path,) in rows:
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    ticket_data = json.loads(content)
                    ticket = Task.model_validate(ticket_data)
                    tickets.append(ticket)
            except (FileNotFoundError, json.JSONDecodeError):
                continue

        return tickets
```

### Monitoring and Metrics

```python
# src/mcp_ticketer/monitoring/metrics.py
import time
import asyncio
from typing import Dict, Any, Optional
from functools import wraps
from dataclasses import dataclass, field
from collections import defaultdict, deque

@dataclass
class OperationMetrics:
    """Metrics for a specific operation."""
    name: str
    count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    error_count: int = 0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def avg_time(self) -> float:
        return self.total_time / self.count if self.count > 0 else 0.0

    @property
    def p95_time(self) -> float:
        """Calculate 95th percentile response time."""
        if not self.recent_times:
            return 0.0
        times = sorted(self.recent_times)
        idx = int(len(times) * 0.95)
        return times[idx] if idx < len(times) else times[-1]

class PerformanceMonitor:
    """Monitor performance metrics for adapters."""

    def __init__(self):
        self.metrics: Dict[str, OperationMetrics] = defaultdict(
            lambda: OperationMetrics("")
        )
        self._start_time = time.time()

    def record_operation(
        self,
        operation: str,
        duration: float,
        error: bool = False
    ):
        """Record an operation's performance metrics."""
        metric = self.metrics[operation]
        metric.name = operation
        metric.count += 1
        metric.total_time += duration
        metric.min_time = min(metric.min_time, duration)
        metric.max_time = max(metric.max_time, duration)
        metric.recent_times.append(duration)

        if error:
            metric.error_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        uptime = time.time() - self._start_time

        return {
            "uptime_seconds": uptime,
            "operations": {
                name: {
                    "count": metric.count,
                    "avg_time": metric.avg_time,
                    "min_time": metric.min_time,
                    "max_time": metric.max_time,
                    "p95_time": metric.p95_time,
                    "error_rate": metric.error_count / metric.count if metric.count > 0 else 0,
                }
                for name, metric in self.metrics.items()
            }
        }

# Global monitor instance
_monitor = PerformanceMonitor()

def monitor_performance(operation_name: str):
    """Decorator to monitor function performance."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            error = False

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                duration = time.time() - start_time
                _monitor.record_operation(operation_name, duration, error)

        return wrapper
    return decorator

def get_performance_summary() -> Dict[str, Any]:
    """Get current performance summary."""
    return _monitor.get_summary()
```

Usage in adapters:

```python
# src/mcp_ticketer/adapters/linear.py
from ..monitoring.metrics import monitor_performance

class LinearAdapter(BaseAdapter[Task]):

    @monitor_performance("linear.create")
    async def create(self, ticket: Task) -> Task:
        # Implementation...
        pass

    @monitor_performance("linear.read")
    async def read(self, ticket_id: str) -> Optional[Task]:
        # Implementation...
        pass

    @monitor_performance("linear.search")
    async def search(self, query: SearchQuery) -> List[Task]:
        # Implementation...
        pass
```

## API Extension

### Adding New Endpoints

Extend the MCP server with custom endpoints:

```python
# src/mcp_ticketer/mcp/extensions.py
from typing import Dict, Any, List
from ..core.models import Task, SearchQuery

class ExtendedMCPServer(MCPTicketServer):
    """Extended MCP server with additional endpoints."""

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle extended requests."""
        method = request.get("method")

        # Handle custom methods
        if method.startswith("custom/"):
            return await self._handle_custom_method(request)

        # Delegate to parent for standard methods
        return await super().handle_request(request)

    async def _handle_custom_method(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle custom method requests."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            if method == "custom/analytics":
                result = await self._handle_analytics(params)
            elif method == "custom/bulk_operations":
                result = await self._handle_bulk_operations(params)
            elif method == "custom/templates":
                result = await self._handle_templates(params)
            else:
                return self._error_response(
                    request_id,
                    -32601,
                    f"Unknown custom method: {method}"
                )

            return {
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            }

        except Exception as e:
            return self._error_response(
                request_id,
                -32603,
                f"Custom method error: {str(e)}"
            )

    async def _handle_analytics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle analytics requests."""
        from ..monitoring.metrics import get_performance_summary

        analytics_type = params.get("type", "performance")

        if analytics_type == "performance":
            return get_performance_summary()

        elif analytics_type == "ticket_stats":
            # Get ticket statistics
            tickets = await self.adapter.list(limit=1000)  # Large limit for stats

            stats = {
                "total_tickets": len(tickets),
                "by_state": {},
                "by_priority": {},
                "by_assignee": {},
            }

            for ticket in tickets:
                # State statistics
                state = ticket.state
                stats["by_state"][state] = stats["by_state"].get(state, 0) + 1

                # Priority statistics
                priority = ticket.priority
                stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

                # Assignee statistics
                assignee = ticket.assignee or "unassigned"
                stats["by_assignee"][assignee] = stats["by_assignee"].get(assignee, 0) + 1

            return stats

        else:
            raise ValueError(f"Unknown analytics type: {analytics_type}")

    async def _handle_bulk_operations(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bulk operations."""
        operation = params.get("operation")

        if operation == "bulk_create":
            tickets_data = params.get("tickets", [])
            tickets = [Task(**ticket_data) for ticket_data in tickets_data]

            # Assuming adapter has bulk_create method
            if hasattr(self.adapter, 'bulk_create'):
                results = await self.adapter.bulk_create(tickets)
            else:
                # Fallback to individual creates
                results = []
                for ticket in tickets:
                    try:
                        result = await self.adapter.create(ticket)
                        results.append(result.model_dump())
                    except Exception as e:
                        results.append({"error": str(e)})

            return {"created": len([r for r in results if "error" not in r])}

        elif operation == "bulk_update":
            updates = params.get("updates", [])
            results = []

            for update in updates:
                ticket_id = update.get("ticket_id")
                changes = update.get("changes", {})

                try:
                    result = await self.adapter.update(ticket_id, changes)
                    results.append({"ticket_id": ticket_id, "success": True})
                except Exception as e:
                    results.append({"ticket_id": ticket_id, "error": str(e)})

            return {"results": results}

        else:
            raise ValueError(f"Unknown bulk operation: {operation}")

    async def _handle_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ticket templates."""
        action = params.get("action")

        if action == "list":
            # Return predefined templates
            return {
                "templates": [
                    {
                        "id": "bug_report",
                        "name": "Bug Report",
                        "template": {
                            "title": "Bug: {title}",
                            "description": "**Bug Description:**\n{description}\n\n**Steps to Reproduce:**\n1. \n\n**Expected Behavior:**\n\n**Actual Behavior:**\n\n**Environment:**\n- OS: \n- Browser: \n- Version: ",
                            "priority": "high",
                            "tags": ["bug"]
                        }
                    },
                    {
                        "id": "feature_request",
                        "name": "Feature Request",
                        "template": {
                            "title": "Feature: {title}",
                            "description": "**Feature Description:**\n{description}\n\n**Use Case:**\n\n**Acceptance Criteria:**\n- [ ] \n\n**Additional Context:**",
                            "priority": "medium",
                            "tags": ["enhancement", "feature"]
                        }
                    }
                ]
            }

        elif action == "apply":
            template_id = params.get("template_id")
            variables = params.get("variables", {})

            # Apply template with variable substitution
            templates = await self._handle_templates({"action": "list"})
            template = next(
                (t for t in templates["templates"] if t["id"] == template_id),
                None
            )

            if not template:
                raise ValueError(f"Template not found: {template_id}")

            # Apply variable substitution
            ticket_data = template["template"].copy()
            for key, value in ticket_data.items():
                if isinstance(value, str):
                    ticket_data[key] = value.format(**variables)

            # Create ticket from template
            ticket = Task(**ticket_data)
            result = await self.adapter.create(ticket)

            return {"ticket": result.model_dump()}

        else:
            raise ValueError(f"Unknown template action: {action}")
```

### WebSocket Support

Add real-time updates with WebSocket:

```python
# src/mcp_ticketer/mcp/websocket_server.py
import asyncio
import json
import websockets
from typing import Set, Dict, Any
from ..core.models import Task, TicketState

class WebSocketMCPServer:
    """WebSocket-based MCP server for real-time updates."""

    def __init__(self, adapter):
        self.adapter = adapter
        self.connections: Set[websockets.WebSocketServerProtocol] = set()
        self.subscriptions: Dict[str, Set[str]] = {}  # connection_id -> ticket_ids

    async def register_connection(self, websocket):
        """Register a new WebSocket connection."""
        self.connections.add(websocket)
        connection_id = id(websocket)
        self.subscriptions[connection_id] = set()

        try:
            await websocket.send(json.dumps({
                "type": "connection_established",
                "connection_id": connection_id
            }))

            async for message in websocket:
                await self.handle_message(websocket, json.loads(message))

        finally:
            self.connections.discard(websocket)
            del self.subscriptions[connection_id]

    async def handle_message(self, websocket, message: Dict[str, Any]):
        """Handle incoming WebSocket messages."""
        message_type = message.get("type")

        if message_type == "subscribe":
            # Subscribe to ticket updates
            ticket_id = message.get("ticket_id")
            if ticket_id:
                connection_id = id(websocket)
                self.subscriptions[connection_id].add(ticket_id)

                await websocket.send(json.dumps({
                    "type": "subscription_confirmed",
                    "ticket_id": ticket_id
                }))

        elif message_type == "unsubscribe":
            # Unsubscribe from ticket updates
            ticket_id = message.get("ticket_id")
            if ticket_id:
                connection_id = id(websocket)
                self.subscriptions[connection_id].discard(ticket_id)

                await websocket.send(json.dumps({
                    "type": "subscription_removed",
                    "ticket_id": ticket_id
                }))

        elif message_type == "rpc":
            # Handle JSON-RPC over WebSocket
            rpc_request = message.get("request")
            response = await self.handle_rpc_request(rpc_request)

            await websocket.send(json.dumps({
                "type": "rpc_response",
                "response": response
            }))

    async def broadcast_ticket_update(self, ticket: Task, event_type: str):
        """Broadcast ticket updates to subscribed connections."""
        if not self.connections:
            return

        update_message = {
            "type": "ticket_update",
            "event_type": event_type,  # "created", "updated", "transitioned", etc.
            "ticket": ticket.model_dump(),
            "timestamp": time.time()
        }

        # Find connections subscribed to this ticket
        subscribers = []
        for connection_id, ticket_ids in self.subscriptions.items():
            if ticket.id in ticket_ids:
                # Find connection by ID
                connection = next(
                    (conn for conn in self.connections if id(conn) == connection_id),
                    None
                )
                if connection:
                    subscribers.append(connection)

        # Send updates to subscribers
        if subscribers:
            message = json.dumps(update_message)
            await asyncio.gather(
                *[conn.send(message) for conn in subscribers],
                return_exceptions=True
            )

    async def start_server(self, host: str = "localhost", port: int = 8765):
        """Start the WebSocket server."""
        server = await websockets.serve(
            self.register_connection,
            host,
            port
        )

        print(f"WebSocket MCP server started on ws://{host}:{port}")
        return server

# Integration with existing adapter
class WebSocketEnabledAdapter(BaseAdapter[Task]):
    """Adapter wrapper that broadcasts WebSocket updates."""

    def __init__(self, base_adapter: BaseAdapter[Task], websocket_server: WebSocketMCPServer):
        self.base_adapter = base_adapter
        self.websocket_server = websocket_server

    async def create(self, ticket: Task) -> Task:
        """Create ticket and broadcast update."""
        result = await self.base_adapter.create(ticket)
        await self.websocket_server.broadcast_ticket_update(result, "created")
        return result

    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update ticket and broadcast update."""
        result = await self.base_adapter.update(ticket_id, updates)
        if result:
            await self.websocket_server.broadcast_ticket_update(result, "updated")
        return result

    async def transition_state(self, ticket_id: str, target_state: TicketState) -> Optional[Task]:
        """Transition state and broadcast update."""
        result = await self.base_adapter.transition_state(ticket_id, target_state)
        if result:
            await self.websocket_server.broadcast_ticket_update(result, "transitioned")
        return result

    # Delegate other methods to base adapter
    def __getattr__(self, name):
        return getattr(self.base_adapter, name)
```

## Code Style and Conventions

### Python Style Guidelines

MCP Ticketer follows PEP 8 with specific conventions:

```python
# Good: Clear, descriptive names
class LinearIssueAdapter(BaseAdapter[Task]):
    """Adapter for Linear issue tracking system."""

    async def create_issue_with_labels(
        self,
        title: str,
        description: Optional[str] = None,
        labels: List[str] = None
    ) -> Task:
        """Create an issue with specified labels.

        Args:
            title: Issue title (required)
            description: Optional detailed description
            labels: List of label names to apply

        Returns:
            Created task with populated ID and metadata

        Raises:
            LinearAPIError: If API request fails
            ValidationError: If title is empty or invalid
        """
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")

        # Implementation details...
        pass

# Bad: Unclear names, missing documentation
class LinAdap(BaseAdapter[Task]):
    async def cr(self, t: str, d: str = None, l: List[str] = None) -> Task:
        # Implementation...
        pass
```

### Type Annotations

Use comprehensive type hints:

```python
from typing import (
    Dict, List, Optional, Union, Any, TypeVar, Generic,
    Callable, Awaitable, AsyncIterator, Protocol
)
from datetime import datetime
from pathlib import Path

# Type variables for generics
T = TypeVar("T", bound=BaseTicket)
AdapterType = TypeVar("AdapterType", bound=BaseAdapter)

# Protocol for type checking
class TicketProvider(Protocol):
    """Protocol for objects that can provide tickets."""

    async def get_tickets(self, limit: int) -> List[Task]:
        """Get tickets from the provider."""
        ...

# Comprehensive function signatures
async def process_tickets_batch(
    provider: TicketProvider,
    processor: Callable[[Task], Awaitable[Task]],
    batch_size: int = 10,
    max_concurrent: int = 5
) -> AsyncIterator[List[Task]]:
    """Process tickets in batches with concurrency control.

    Args:
        provider: Source of tickets
        processor: Async function to process each ticket
        batch_size: Number of tickets per batch
        max_concurrent: Maximum concurrent operations

    Yields:
        Batches of processed tickets
    """
    # Implementation...
    pass
```

### Error Handling Patterns

```python
# Custom exception hierarchy
class MCPTicketerError(Exception):
    """Base exception for MCP Ticketer."""
    pass

class AdapterError(MCPTicketerError):
    """Base adapter error."""

    def __init__(self, message: str, adapter_name: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.adapter_name = adapter_name
        self.original_error = original_error

class AuthenticationError(AdapterError):
    """Authentication failed with external service."""
    pass

class RateLimitError(AdapterError):
    """Rate limit exceeded."""

    def __init__(self, message: str, adapter_name: str, retry_after: Optional[int] = None):
        super().__init__(message, adapter_name)
        self.retry_after = retry_after

class ValidationError(MCPTicketerError):
    """Data validation error."""

    def __init__(self, message: str, field: Optional[str] = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value

# Error handling in adapters
async def create_ticket_with_retry(self, ticket: Task) -> Task:
    """Create ticket with automatic retry logic."""
    max_retries = 3
    base_delay = 1.0

    for attempt in range(max_retries):
        try:
            return await self._do_create_ticket(ticket)

        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Wait for rate limit reset
            delay = e.retry_after or (base_delay * (2 ** attempt))
            await asyncio.sleep(delay)
            continue

        except AuthenticationError:
            # Don't retry auth errors
            raise

        except AdapterError as e:
            if attempt == max_retries - 1:
                raise

            # Exponential backoff
            await asyncio.sleep(base_delay * (2 ** attempt))
            continue

    # Should never reach here due to raises above
    raise AdapterError("All retry attempts failed", self.__class__.__name__)
```

### Logging Standards

```python
import logging
import structlog
from typing import Any, Dict

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

class LoggingMixin:
    """Mixin to add structured logging to classes."""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger bound to class context."""
        if not hasattr(self, '_logger'):
            self._logger = structlog.get_logger(self.__class__.__name__)
        return self._logger

    def log_operation(self, operation: str, **kwargs: Any):
        """Log an operation with context."""
        self.logger.info(
            "operation_started",
            operation=operation,
            **kwargs
        )

    def log_error(self, error: Exception, operation: str, **kwargs: Any):
        """Log an error with context."""
        self.logger.error(
            "operation_failed",
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            **kwargs
        )

# Usage in adapters
class LinearAdapter(BaseAdapter[Task], LoggingMixin):

    async def create(self, ticket: Task) -> Task:
        """Create ticket with comprehensive logging."""
        self.log_operation(
            "create_ticket",
            adapter="linear",
            ticket_title=ticket.title,
            priority=ticket.priority
        )

        try:
            # Create ticket
            result = await self._do_create(ticket)

            self.logger.info(
                "ticket_created",
                ticket_id=result.id,
                adapter="linear",
                duration_ms=(end_time - start_time) * 1000
            )

            return result

        except Exception as e:
            self.log_error(
                e,
                "create_ticket",
                adapter="linear",
                ticket_title=ticket.title
            )
            raise
```

### Documentation Standards

```python
"""Module for Linear adapter implementation.

This module provides integration with Linear's GraphQL API for ticket management.
It implements the BaseAdapter interface and handles Linear-specific data mapping.

Example:
    Basic usage of LinearAdapter:

    >>> config = {"team_id": "team_123", "api_key": "lin_api_xxx"}
    >>> adapter = LinearAdapter(config)
    >>> task = Task(title="Fix bug", priority=Priority.HIGH)
    >>> created_task = await adapter.create(task)

Note:
    Linear API requires authentication via API key. Generate keys at:
    https://linear.app/settings/api
"""

from typing import Dict, List, Optional, Any, cast
from datetime import datetime
import logging

from ..core.adapter import BaseAdapter
from ..core.models import Task, Comment, SearchQuery, TicketState, Priority

logger = logging.getLogger(__name__)


class LinearAdapter(BaseAdapter[Task]):
    """Linear GraphQL API adapter for MCP Ticketer.

    This adapter integrates with Linear's issue tracking system using their
    GraphQL API. It maps Linear issues to the universal Task model and handles
    state synchronization between systems.

    The adapter supports:
        - Issue creation, reading, updating, and deletion
        - State transitions with validation
        - Comment management
        - Advanced search and filtering
        - Automatic retry with exponential backoff

    Attributes:
        team_id: Linear team identifier
        api_key: Linear API authentication key
        client: Configured GraphQL client instance

    Example:
        >>> config = {
        ...     "team_id": "team_abc123",
        ...     "api_key": "lin_api_def456"
        ... }
        >>> adapter = LinearAdapter(config)
        >>>
        >>> # Create a high-priority bug
        >>> bug = Task(
        ...     title="Critical login issue",
        ...     description="Users cannot authenticate",
        ...     priority=Priority.CRITICAL,
        ...     tags=["bug", "auth"]
        ... )
        >>> created = await adapter.create(bug)
        >>> print(f"Created issue: {created.id}")
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize Linear adapter with configuration.

        Args:
            config: Configuration dictionary containing:
                - team_id (str): Linear team ID (required)
                - api_key (str): Linear API key (required)
                - endpoint (str, optional): GraphQL endpoint URL
                - timeout (int, optional): Request timeout in seconds

        Raises:
            ValueError: If required configuration is missing
            ConnectionError: If unable to connect to Linear API

        Example:
            >>> config = {
            ...     "team_id": "team_abc123",
            ...     "api_key": "lin_api_def456",
            ...     "timeout": 30
            ... }
            >>> adapter = LinearAdapter(config)
        """
        super().__init__(config)

        # Validate required configuration
        self.team_id = config.get("team_id")
        self.api_key = config.get("api_key")

        if not self.team_id:
            raise ValueError("Linear team_id is required")
        if not self.api_key:
            raise ValueError("Linear api_key is required")

        # Initialize GraphQL client
        self._init_client(config)

        logger.info(
            "Linear adapter initialized",
            team_id=self.team_id,
            endpoint=self.endpoint
        )

    async def create(self, ticket: Task) -> Task:
        """Create a new issue in Linear.

        Creates a Linear issue from the provided Task object. The issue will be
        created in the configured team with appropriate labels, priority, and
        initial state.

        Args:
            ticket: Task object containing issue details. Required fields:
                - title: Issue title (1-255 characters)
                - description: Optional issue description
                - priority: Priority level (mapped to Linear priority 1-4)
                - tags: Optional list of label names

        Returns:
            Task object with populated Linear-specific metadata including:
                - id: Linear issue identifier
                - created_at: Issue creation timestamp
                - updated_at: Issue last update timestamp
                - metadata: Linear-specific data (issue ID, URL, etc.)

        Raises:
            ValidationError: If ticket data is invalid
            AuthenticationError: If API key is invalid
            RateLimitError: If API rate limit exceeded
            AdapterError: If Linear API request fails

        Example:
            >>> task = Task(
            ...     title="Implement user search",
            ...     description="Add search functionality to user directory",
            ...     priority=Priority.MEDIUM,
            ...     tags=["feature", "frontend"]
            ... )
            >>> created = await adapter.create(task)
            >>> print(f"Issue created: {created.metadata['linear_url']}")
        """
        # Implementation details...
        pass
```

## Development Workflow

### Git Workflow

```bash
# Development workflow
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/slack-adapter

# Make changes with frequent commits
git add .
git commit -m "feat: add Slack adapter base structure"

git add .
git commit -m "feat: implement Slack message creation and reading"

git add .
git commit -m "test: add comprehensive Slack adapter tests"

git add .
git commit -m "docs: add Slack adapter documentation"

# Push and create PR
git push origin feature/slack-adapter
gh pr create --title "Add Slack Adapter" --body "Implements Slack integration as described in #123"
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
        language_version: python3.13

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.3
    hooks:
      - id: ruff
        args: [--fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

### Release Process

```bash
# Prepare release
./scripts/prepare_release.sh v0.2.0

# Update CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: update changelog for v0.2.0"

# Tag release
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# Build and publish
python -m build
twine upload dist/*

# Update documentation
./scripts/update_docs.sh
```

### Development Scripts

```bash
#!/bin/bash
# scripts/dev_setup.sh

set -e

echo "Setting up MCP Ticketer development environment..."

# Create virtual environment
python3.13 -m venv venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev,mcp,jira,github]"

# Install pre-commit hooks
pre-commit install

# Create test configuration
mkdir -p ~/.mcp-ticketer
cat > ~/.mcp-ticketer/test-config.json << EOF
{
  "adapter": "aitrackdown",
  "config": {
    "base_path": ".test-tickets"
  }
}
EOF

# Run initial tests
pytest tests/unit/ -v

echo "Development environment ready!"
echo "Next steps:"
echo "  1. source .venv/bin/activate"
echo "  2. pytest tests/ -v"
echo "  3. mcp-ticket init --adapter aitrackdown"
```

This comprehensive developer guide provides everything needed to understand, extend, and contribute to MCP Ticketer. The architecture is designed for extensibility, making it straightforward to add new adapters, extend functionality, and integrate with various systems while maintaining high code quality and performance standards.