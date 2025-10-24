"""Linear adapter implementation using native GraphQL API with full feature support."""

import asyncio
import builtins
import os
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional, Union

from gql import Client, gql
from gql.transport.exceptions import TransportQueryError
from gql.transport.httpx import HTTPXAsyncTransport

from ..core.adapter import BaseAdapter
from ..core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from ..core.registry import AdapterRegistry


class LinearStateType(str, Enum):
    """Linear workflow state types."""

    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


class LinearPriorityMapping:
    """Maps between Linear priority numbers and our Priority enum."""

    TO_LINEAR = {
        Priority.LOW: 4,
        Priority.MEDIUM: 3,
        Priority.HIGH: 2,
        Priority.CRITICAL: 1,
    }

    FROM_LINEAR = {
        0: Priority.CRITICAL,  # Urgent
        1: Priority.CRITICAL,  # High
        2: Priority.HIGH,  # Medium
        3: Priority.MEDIUM,  # Low
        4: Priority.LOW,  # No priority
    }


# GraphQL Fragments for reusable field definitions
USER_FRAGMENT = """
    fragment UserFields on User {
        id
        name
        email
        displayName
        avatarUrl
        isMe
    }
"""

WORKFLOW_STATE_FRAGMENT = """
    fragment WorkflowStateFields on WorkflowState {
        id
        name
        type
        position
        color
    }
"""

TEAM_FRAGMENT = """
    fragment TeamFields on Team {
        id
        name
        key
        description
    }
"""

CYCLE_FRAGMENT = """
    fragment CycleFields on Cycle {
        id
        number
        name
        description
        startsAt
        endsAt
        completedAt
    }
"""

PROJECT_FRAGMENT = """
    fragment ProjectFields on Project {
        id
        name
        description
        state
        createdAt
        updatedAt
        url
        icon
        color
        targetDate
        startedAt
        completedAt
        teams {
            nodes {
                ...TeamFields
            }
        }
    }
"""

LABEL_FRAGMENT = """
    fragment LabelFields on IssueLabel {
        id
        name
        color
        description
    }
"""

ATTACHMENT_FRAGMENT = """
    fragment AttachmentFields on Attachment {
        id
        url
        title
        subtitle
        metadata
        source
        sourceType
        createdAt
    }
"""

COMMENT_FRAGMENT = """
    fragment CommentFields on Comment {
        id
        body
        createdAt
        updatedAt
        user {
            ...UserFields
        }
        parent {
            id
        }
    }
"""

ISSUE_COMPACT_FRAGMENT = """
    fragment IssueCompactFields on Issue {
        id
        identifier
        title
        description
        priority
        priorityLabel
        estimate
        dueDate
        slaBreachesAt
        slaStartedAt
        createdAt
        updatedAt
        archivedAt
        canceledAt
        completedAt
        startedAt
        startedTriageAt
        triagedAt
        url
        branchName
        customerTicketCount

        state {
            ...WorkflowStateFields
        }
        assignee {
            ...UserFields
        }
        creator {
            ...UserFields
        }
        labels {
            nodes {
                ...LabelFields
            }
        }
        team {
            ...TeamFields
        }
        cycle {
            ...CycleFields
        }
        project {
            ...ProjectFields
        }
        parent {
            id
            identifier
            title
        }
        children {
            nodes {
                id
                identifier
                title
            }
        }
        attachments {
            nodes {
                ...AttachmentFields
            }
        }
    }
"""

ISSUE_FULL_FRAGMENT = """
    fragment IssueFullFields on Issue {
        ...IssueCompactFields
        comments {
            nodes {
                ...CommentFields
            }
        }
        subscribers {
            nodes {
                ...UserFields
            }
        }
        relations {
            nodes {
                id
                type
                relatedIssue {
                    id
                    identifier
                    title
                }
            }
        }
    }
"""

# Combine all fragments
ALL_FRAGMENTS = (
    USER_FRAGMENT
    + WORKFLOW_STATE_FRAGMENT
    + TEAM_FRAGMENT
    + CYCLE_FRAGMENT
    + PROJECT_FRAGMENT
    + LABEL_FRAGMENT
    + ATTACHMENT_FRAGMENT
    + COMMENT_FRAGMENT
    + ISSUE_COMPACT_FRAGMENT
    + ISSUE_FULL_FRAGMENT
)

# Fragments needed for issue list/search (without comments)
ISSUE_LIST_FRAGMENTS = (
    USER_FRAGMENT
    + WORKFLOW_STATE_FRAGMENT
    + TEAM_FRAGMENT
    + CYCLE_FRAGMENT
    + PROJECT_FRAGMENT
    + LABEL_FRAGMENT
    + ATTACHMENT_FRAGMENT
    + ISSUE_COMPACT_FRAGMENT
)


class LinearAdapter(BaseAdapter[Task]):
    """Adapter for Linear issue tracking system using native GraphQL API."""

    def __init__(self, config: dict[str, Any]):
        """Initialize Linear adapter.

        Args:
            config: Configuration with:
                - api_key: Linear API key (or LINEAR_API_KEY env var)
                - workspace: Linear workspace name (optional, for documentation)
                - team_key: Linear team key (e.g., 'BTA') OR
                - team_id: Linear team UUID (e.g., '02d15669-7351-4451-9719-807576c16049')
                - api_url: Optional Linear API URL

        Note: Either team_key or team_id is required. If both are provided, team_id takes precedence.

        """
        super().__init__(config)

        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Linear API key required (config.api_key or LINEAR_API_KEY env var)"
            )

        self.workspace = config.get("workspace")  # Optional, for documentation

        # Support both team_key (short key) and team_id (UUID)
        self.team_key = config.get("team_key")  # Short key like "BTA"
        self.team_id_config = config.get("team_id")  # UUID like "02d15669-..."

        # Require at least one team identifier
        if not self.team_key and not self.team_id_config:
            raise ValueError("Either team_key or team_id is required in configuration")

        self.api_url = config.get("api_url", "https://api.linear.app/graphql")

        # Caches for frequently used data
        self._team_id: Optional[str] = None
        self._workflow_states: Optional[dict[str, dict[str, Any]]] = None
        self._labels: Optional[dict[str, str]] = None  # name -> id
        self._users: Optional[dict[str, str]] = None  # email -> id

        # Initialize state mapping
        self._state_mapping = self._get_state_mapping()

        # Initialization lock to prevent concurrent initialization
        self._init_lock = asyncio.Lock()
        self._initialized = False

    def _create_client(self) -> Client:
        """Create a fresh GraphQL client for each operation.

        This prevents 'Transport is already connected' errors by ensuring
        each operation gets its own client and transport instance.

        Returns:
            Client: Fresh GraphQL client instance

        """
        transport = HTTPXAsyncTransport(
            url=self.api_url,
            headers={"Authorization": self.api_key},
            timeout=30.0,
        )
        return Client(transport=transport, fetch_schema_from_transport=False)

    async def initialize(self) -> None:
        """Initialize adapter by preloading team, states, and labels data concurrently."""
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            try:
                # First get team ID as it's required for other queries
                team_id = await self._fetch_team_data()

                # Then fetch states and labels concurrently
                states_task = self._fetch_workflow_states_data(team_id)
                labels_task = self._fetch_labels_data(team_id)

                workflow_states, labels = await asyncio.gather(states_task, labels_task)

                # Cache the results
                self._team_id = team_id
                self._workflow_states = workflow_states
                self._labels = labels
                self._initialized = True

            except Exception as e:
                # Reset on error
                self._team_id = None
                self._workflow_states = None
                self._labels = None
                raise e

    async def _fetch_team_data(self) -> str:
        """Fetch team ID.

        If team_id is configured, validate it exists and return it.
        If team_key is configured, fetch the team_id by key.
        """
        # If team_id (UUID) is provided, use it directly (preferred)
        if self.team_id_config:
            # Validate that this team ID exists
            query = gql(
                """
                query GetTeamById($id: String!) {
                    team(id: $id) {
                        id
                        name
                        key
                    }
                }
            """
            )

            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    query, variable_values={"id": self.team_id_config}
                )

            if not result.get("team"):
                raise ValueError(f"Team with ID '{self.team_id_config}' not found")

            return result["team"]["id"]

        # Otherwise, fetch team ID by key
        query = gql(
            """
            query GetTeamByKey($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        name
                        key
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query, variable_values={"key": self.team_key}
            )

        if not result["teams"]["nodes"]:
            raise ValueError(f"Team with key '{self.team_key}' not found")

        return result["teams"]["nodes"][0]["id"]

    async def _fetch_workflow_states_data(
        self, team_id: str
    ) -> dict[str, dict[str, Any]]:
        """Fetch workflow states data."""
        query = gql(
            """
            query WorkflowStates($teamId: ID!) {
                workflowStates(filter: { team: { id: { eq: $teamId } } }) {
                    nodes {
                        id
                        name
                        type
                        position
                        color
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(query, variable_values={"teamId": team_id})

        workflow_states = {}
        for state in result["workflowStates"]["nodes"]:
            state_type = state["type"].lower()
            if state_type not in workflow_states:
                workflow_states[state_type] = state
            elif state["position"] < workflow_states[state_type]["position"]:
                workflow_states[state_type] = state

        return workflow_states

    async def _fetch_labels_data(self, team_id: str) -> dict[str, str]:
        """Fetch labels data."""
        query = gql(
            """
            query GetLabels($teamId: ID!) {
                issueLabels(filter: { team: { id: { eq: $teamId } } }) {
                    nodes {
                        id
                        name
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(query, variable_values={"teamId": team_id})

        return {label["name"]: label["id"] for label in result["issueLabels"]["nodes"]}

    async def _ensure_initialized(self) -> None:
        """Ensure adapter is initialized before operations."""
        if not self._initialized:
            await self.initialize()

    async def _ensure_team_id(self) -> str:
        """Get and cache the team ID."""
        await self._ensure_initialized()
        return self._team_id

    async def _get_workflow_states(self) -> dict[str, dict[str, Any]]:
        """Get cached workflow states from Linear."""
        await self._ensure_initialized()
        return self._workflow_states

    async def _get_or_create_label(self, name: str, color: Optional[str] = None) -> str:
        """Get existing label ID or create new label."""
        await self._ensure_initialized()

        # Check cache
        if name in self._labels:
            return self._labels[name]

        # Try to find existing label (may have been added since initialization)
        team_id = self._team_id
        search_query = gql(
            """
            query GetLabel($name: String!, $teamId: ID!) {
                issueLabels(filter: { name: { eq: $name }, team: { id: { eq: $teamId } } }) {
                    nodes {
                        id
                        name
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                search_query, variable_values={"name": name, "teamId": team_id}
            )

        if result["issueLabels"]["nodes"]:
            label_id = result["issueLabels"]["nodes"][0]["id"]
            self._labels[name] = label_id
            return label_id

        # Create new label
        create_query = gql(
            """
            mutation CreateLabel($input: IssueLabelCreateInput!) {
                issueLabelCreate(input: $input) {
                    issueLabel {
                        id
                        name
                    }
                }
            }
        """
        )

        label_input = {
            "name": name,
            "teamId": team_id,
        }
        if color:
            label_input["color"] = color

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": label_input}
            )

        label_id = result["issueLabelCreate"]["issueLabel"]["id"]
        self._labels[name] = label_id
        return label_id

    async def _get_user_id(self, email: str) -> Optional[str]:
        """Get user ID by email."""
        if not self._users:
            self._users = {}

        if email in self._users:
            return self._users[email]

        query = gql(
            """
            query GetUser($email: String!) {
                users(filter: { email: { eq: $email } }) {
                    nodes {
                        id
                        email
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(query, variable_values={"email": email})

        if result["users"]["nodes"]:
            user_id = result["users"]["nodes"][0]["id"]
            self._users[email] = user_id
            return user_id

        return None

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
            (is_valid, error_message) - Tuple of validation result and error message

        """
        if not self.api_key:
            return (
                False,
                "LINEAR_API_KEY is required but not found. Set it in .env.local or environment.",
            )
        if not self.team_key and not self.team_id_config:
            return (
                False,
                "Either Linear team_key or team_id is required in configuration. Set it in .mcp-ticketer/config.json",
            )
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get mapping from universal states to Linear state types.

        Required by BaseAdapter abstract method.
        """
        return {
            TicketState.OPEN: LinearStateType.BACKLOG,
            TicketState.IN_PROGRESS: LinearStateType.STARTED,
            TicketState.READY: LinearStateType.STARTED,  # Will use label for distinction
            TicketState.TESTED: LinearStateType.STARTED,  # Will use label
            TicketState.DONE: LinearStateType.COMPLETED,
            TicketState.WAITING: LinearStateType.UNSTARTED,
            TicketState.BLOCKED: LinearStateType.UNSTARTED,  # Will use label
            TicketState.CLOSED: LinearStateType.CANCELED,
        }

    def _map_state_to_linear(self, state: TicketState) -> str:
        """Map universal state to Linear state type."""
        # Handle both enum and string values
        if isinstance(state, str):
            state = TicketState(state)
        return self._state_mapping.get(state, LinearStateType.BACKLOG)

    def _map_linear_state(
        self, state_data: dict[str, Any], labels: list[str]
    ) -> TicketState:
        """Map Linear state and labels to universal state."""
        state_type = state_data.get("type", "").lower()

        # Check for special states via labels
        labels_lower = [l.lower() for l in labels]
        if "blocked" in labels_lower:
            return TicketState.BLOCKED
        if "waiting" in labels_lower:
            return TicketState.WAITING
        if "ready" in labels_lower or "review" in labels_lower:
            return TicketState.READY
        if "tested" in labels_lower or "qa" in labels_lower:
            return TicketState.TESTED

        # Map by state type
        state_mapping = {
            "backlog": TicketState.OPEN,
            "unstarted": TicketState.OPEN,
            "started": TicketState.IN_PROGRESS,
            "completed": TicketState.DONE,
            "canceled": TicketState.CLOSED,
        }
        return state_mapping.get(state_type, TicketState.OPEN)

    def _task_from_linear_issue(self, issue: dict[str, Any]) -> Task:
        """Convert Linear issue to universal Task."""
        # Extract labels
        tags = []
        if issue.get("labels") and issue["labels"].get("nodes"):
            tags = [label["name"] for label in issue["labels"]["nodes"]]

        # Map priority
        linear_priority = issue.get("priority", 4)
        priority = LinearPriorityMapping.FROM_LINEAR.get(
            linear_priority, Priority.MEDIUM
        )

        # Map state
        state = self._map_linear_state(issue.get("state", {}), tags)

        # Build metadata with all Linear-specific fields
        metadata = {
            "linear": {
                "id": issue["id"],
                "identifier": issue["identifier"],
                "url": issue.get("url"),
                "state_id": issue.get("state", {}).get("id"),
                "state_name": issue.get("state", {}).get("name"),
                "team_id": issue.get("team", {}).get("id"),
                "team_name": issue.get("team", {}).get("name"),
                "cycle_id": (
                    issue.get("cycle", {}).get("id") if issue.get("cycle") else None
                ),
                "cycle_name": (
                    issue.get("cycle", {}).get("name") if issue.get("cycle") else None
                ),
                "project_id": (
                    issue.get("project", {}).get("id") if issue.get("project") else None
                ),
                "project_name": (
                    issue.get("project", {}).get("name")
                    if issue.get("project")
                    else None
                ),
                "priority_label": issue.get("priorityLabel"),
                "estimate": issue.get("estimate"),
                "due_date": issue.get("dueDate"),
                "branch_name": issue.get("branchName"),
            }
        }

        # Add timestamps if available
        if issue.get("startedAt"):
            metadata["linear"]["started_at"] = issue["startedAt"]
        if issue.get("completedAt"):
            metadata["linear"]["completed_at"] = issue["completedAt"]
        if issue.get("canceledAt"):
            metadata["linear"]["canceled_at"] = issue["canceledAt"]

        # Add attachments metadata
        if issue.get("attachments") and issue["attachments"].get("nodes"):
            metadata["linear"]["attachments"] = [
                {
                    "id": att["id"],
                    "url": att["url"],
                    "title": att.get("title"),
                    "source": att.get("source"),
                }
                for att in issue["attachments"]["nodes"]
            ]

        # Extract child issue IDs
        child_ids = []
        if issue.get("children") and issue["children"].get("nodes"):
            child_ids = [child["identifier"] for child in issue["children"]["nodes"]]
            metadata["linear"]["child_issues"] = child_ids

        # Determine ticket type based on parent relationships
        ticket_type = TicketType.ISSUE
        parent_issue_id = None
        parent_epic_id = None

        if issue.get("parent"):
            # Has a parent issue, so this is a sub-task
            ticket_type = TicketType.TASK
            parent_issue_id = issue["parent"]["identifier"]
        elif issue.get("project"):
            # Has a project but no parent, so it's a standard issue under an epic
            ticket_type = TicketType.ISSUE
            parent_epic_id = issue["project"]["id"]

        return Task(
            id=issue["identifier"],
            title=issue["title"],
            description=issue.get("description"),
            state=state,
            priority=priority,
            tags=tags,
            ticket_type=ticket_type,
            parent_issue=parent_issue_id,
            parent_epic=parent_epic_id,
            assignee=(
                issue.get("assignee", {}).get("email")
                if issue.get("assignee")
                else None
            ),
            children=child_ids,
            estimated_hours=issue.get("estimate"),
            created_at=(
                datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
                if issue.get("createdAt")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
                if issue.get("updatedAt")
                else None
            ),
            metadata=metadata,
        )

    def _epic_from_linear_project(self, project: dict[str, Any]) -> Epic:
        """Convert Linear project to universal Epic."""
        # Map project state to ticket state
        project_state = project.get("state", "planned").lower()
        state_mapping = {
            "planned": TicketState.OPEN,
            "started": TicketState.IN_PROGRESS,
            "paused": TicketState.WAITING,
            "completed": TicketState.DONE,
            "canceled": TicketState.CLOSED,
        }
        state = state_mapping.get(project_state, TicketState.OPEN)

        # Extract teams
        teams = []
        if project.get("teams") and project["teams"].get("nodes"):
            teams = [team["name"] for team in project["teams"]["nodes"]]

        metadata = {
            "linear": {
                "id": project["id"],
                "state": project.get("state"),
                "url": project.get("url"),
                "icon": project.get("icon"),
                "color": project.get("color"),
                "target_date": project.get("targetDate"),
                "started_at": project.get("startedAt"),
                "completed_at": project.get("completedAt"),
                "teams": teams,
            }
        }

        return Epic(
            id=project["id"],
            title=project["name"],
            description=project.get("description"),
            state=state,
            ticket_type=TicketType.EPIC,
            tags=[f"team:{team}" for team in teams],
            created_at=(
                datetime.fromisoformat(project["createdAt"].replace("Z", "+00:00"))
                if project.get("createdAt")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(project["updatedAt"].replace("Z", "+00:00"))
                if project.get("updatedAt")
                else None
            ),
            metadata=metadata,
        )

    async def create(self, ticket: Task) -> Task:
        """Create a new Linear issue with full field support."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        team_id = await self._ensure_team_id()
        states = await self._get_workflow_states()

        # Map state to Linear state ID
        linear_state_type = self._map_state_to_linear(ticket.state)
        state_data = states.get(linear_state_type)
        if not state_data:
            # Fallback to backlog state
            state_data = states.get("backlog")
        state_id = state_data["id"] if state_data else None

        # Build issue input
        issue_input = {
            "title": ticket.title,
            "teamId": team_id,
        }

        if ticket.description:
            issue_input["description"] = ticket.description

        if state_id:
            issue_input["stateId"] = state_id

        # Set priority
        if ticket.priority:
            issue_input["priority"] = LinearPriorityMapping.TO_LINEAR.get(
                ticket.priority, 3
            )

        # Handle labels/tags
        if ticket.tags:
            label_ids = []
            for tag in ticket.tags:
                # Add special state labels if needed
                if ticket.state == TicketState.BLOCKED and "blocked" not in [
                    t.lower() for t in ticket.tags
                ]:
                    label_ids.append(
                        await self._get_or_create_label("blocked", "#FF0000")
                    )
                elif ticket.state == TicketState.WAITING and "waiting" not in [
                    t.lower() for t in ticket.tags
                ]:
                    label_ids.append(
                        await self._get_or_create_label("waiting", "#FFA500")
                    )
                elif ticket.state == TicketState.READY and "ready" not in [
                    t.lower() for t in ticket.tags
                ]:
                    label_ids.append(
                        await self._get_or_create_label("ready", "#00FF00")
                    )

                label_id = await self._get_or_create_label(tag)
                label_ids.append(label_id)
            if label_ids:
                issue_input["labelIds"] = label_ids

        # Handle assignee
        if ticket.assignee:
            user_id = await self._get_user_id(ticket.assignee)
            if user_id:
                issue_input["assigneeId"] = user_id

        # Handle estimate (Linear uses integer points, so we round hours)
        if ticket.estimated_hours:
            issue_input["estimate"] = int(round(ticket.estimated_hours))

        # Handle parent issue
        if ticket.parent_issue:
            # Get parent issue's Linear ID
            parent_query = gql(
                """
                query GetIssue($identifier: String!) {
                    issue(id: $identifier) {
                        id
                    }
                }
            """
            )
            client = self._create_client()
            async with client as session:
                parent_result = await session.execute(
                    parent_query, variable_values={"identifier": ticket.parent_issue}
                )
            if parent_result.get("issue"):
                issue_input["parentId"] = parent_result["issue"]["id"]

        # Handle project (epic)
        if ticket.parent_epic:
            issue_input["projectId"] = ticket.parent_epic

        # Handle metadata fields
        if ticket.metadata and "linear" in ticket.metadata:
            linear_meta = ticket.metadata["linear"]
            if "due_date" in linear_meta:
                issue_input["dueDate"] = linear_meta["due_date"]
            if "cycle_id" in linear_meta:
                issue_input["cycleId"] = linear_meta["cycle_id"]

        # Create issue mutation with full fields
        create_query = gql(
            ALL_FRAGMENTS
            + """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        ...IssueFullFields
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": issue_input}
            )

        if not result["issueCreate"]["success"]:
            raise Exception("Failed to create Linear issue")

        created_issue = result["issueCreate"]["issue"]
        return self._task_from_linear_issue(created_issue)

    async def create_epic(self, title: str, description: str = None, **kwargs) -> Task:
        """Create a new epic (Linear project).

        Args:
            title: Epic title
            description: Epic description
            **kwargs: Additional epic properties

        Returns:
            Created Task instance representing the epic
        """
        # In Linear, epics are represented as issues with special labels/properties
        task = Task(
            title=title,
            description=description,
            tags=kwargs.get('tags', []) + ['epic'],  # Add epic tag
            **{k: v for k, v in kwargs.items() if k != 'tags'}
        )
        return await self.create(task)

    async def create_issue(self, title: str, parent_epic: str = None, description: str = None, **kwargs) -> Task:
        """Create a new issue.

        Args:
            title: Issue title
            parent_epic: Parent epic ID
            description: Issue description
            **kwargs: Additional issue properties

        Returns:
            Created Task instance representing the issue
        """
        task = Task(
            title=title,
            description=description,
            parent_epic=parent_epic,
            **kwargs
        )
        return await self.create(task)

    async def create_task(self, title: str, parent_id: str, description: str = None, **kwargs) -> Task:
        """Create a new task under an issue.

        Args:
            title: Task title
            parent_id: Parent issue ID
            description: Task description
            **kwargs: Additional task properties

        Returns:
            Created Task instance
        """
        task = Task(
            title=title,
            description=description,
            parent_issue=parent_id,
            **kwargs
        )
        return await self.create(task)

    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read a Linear issue by identifier with full details."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        query = gql(
            ALL_FRAGMENTS
            + """
            query GetIssue($identifier: String!) {
                issue(id: $identifier) {
                    ...IssueFullFields
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    query, variable_values={"identifier": ticket_id}
                )

            if result.get("issue"):
                return self._task_from_linear_issue(result["issue"])
        except TransportQueryError:
            # Issue not found
            pass

        return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Optional[Task]:
        """Update a Linear issue with comprehensive field support."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # First get the Linear internal ID
        query = gql(
            """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query, variable_values={"identifier": ticket_id}
            )

        if not result.get("issue"):
            return None

        linear_id = result["issue"]["id"]

        # Build update input
        update_input = {}

        if "title" in updates:
            update_input["title"] = updates["title"]

        if "description" in updates:
            update_input["description"] = updates["description"]

        if "priority" in updates:
            priority = updates["priority"]
            if isinstance(priority, str):
                priority = Priority(priority)
            update_input["priority"] = LinearPriorityMapping.TO_LINEAR.get(priority, 3)

        if "state" in updates:
            states = await self._get_workflow_states()
            state = updates["state"]
            if isinstance(state, str):
                state = TicketState(state)
            linear_state_type = self._map_state_to_linear(state)
            state_data = states.get(linear_state_type)
            if state_data:
                update_input["stateId"] = state_data["id"]

        if "assignee" in updates:
            if updates["assignee"]:
                user_id = await self._get_user_id(updates["assignee"])
                if user_id:
                    update_input["assigneeId"] = user_id
            else:
                update_input["assigneeId"] = None

        if "tags" in updates:
            label_ids = []
            for tag in updates["tags"]:
                label_id = await self._get_or_create_label(tag)
                label_ids.append(label_id)
            update_input["labelIds"] = label_ids

        if "estimated_hours" in updates:
            update_input["estimate"] = int(round(updates["estimated_hours"]))

        # Handle metadata updates
        if "metadata" in updates and "linear" in updates["metadata"]:
            linear_meta = updates["metadata"]["linear"]
            if "due_date" in linear_meta:
                update_input["dueDate"] = linear_meta["due_date"]
            if "cycle_id" in linear_meta:
                update_input["cycleId"] = linear_meta["cycle_id"]
            if "project_id" in linear_meta:
                update_input["projectId"] = linear_meta["project_id"]

        # Update mutation
        update_query = gql(
            ALL_FRAGMENTS
            + """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        ...IssueFullFields
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                update_query, variable_values={"id": linear_id, "input": update_input}
            )

        if result["issueUpdate"]["success"]:
            return self._task_from_linear_issue(result["issueUpdate"]["issue"])

        return None

    async def delete(self, ticket_id: str) -> bool:
        """Archive (soft delete) a Linear issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Get Linear ID
        query = gql(
            """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query, variable_values={"identifier": ticket_id}
            )

        if not result.get("issue"):
            return False

        linear_id = result["issue"]["id"]

        # Archive mutation
        archive_query = gql(
            """
            mutation ArchiveIssue($id: String!) {
                issueArchive(id: $id) {
                    success
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                archive_query, variable_values={"id": linear_id}
            )

        return result.get("issueArchive", {}).get("success", False)

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[dict[str, Any]] = None
    ) -> list[Task]:
        """List Linear issues with comprehensive filtering."""
        team_id = await self._ensure_team_id()

        # Build filter
        issue_filter = {"team": {"id": {"eq": team_id}}}

        if filters:
            # State filter
            if "state" in filters:
                state = filters["state"]
                if isinstance(state, str):
                    state = TicketState(state)
                # Map to Linear state types
                state_mapping = {
                    TicketState.OPEN: ["backlog", "unstarted"],
                    TicketState.IN_PROGRESS: ["started"],
                    TicketState.DONE: ["completed"],
                    TicketState.CLOSED: ["canceled"],
                }
                if state in state_mapping:
                    issue_filter["state"] = {"type": {"in": state_mapping[state]}}

            # Priority filter
            if "priority" in filters:
                priority = filters["priority"]
                if isinstance(priority, str):
                    priority = Priority(priority)
                linear_priority = LinearPriorityMapping.TO_LINEAR.get(priority, 3)
                issue_filter["priority"] = {"eq": linear_priority}

            # Assignee filter
            if "assignee" in filters and filters["assignee"]:
                user_id = await self._get_user_id(filters["assignee"])
                if user_id:
                    issue_filter["assignee"] = {"id": {"eq": user_id}}

            # Project filter
            if "project_id" in filters:
                issue_filter["project"] = {"id": {"eq": filters["project_id"]}}

            # Cycle filter
            if "cycle_id" in filters:
                issue_filter["cycle"] = {"id": {"eq": filters["cycle_id"]}}

            # Label filter
            if "labels" in filters:
                issue_filter["labels"] = {"some": {"name": {"in": filters["labels"]}}}

            # Parent filter
            if "parent_id" in filters:
                issue_filter["parent"] = {"identifier": {"eq": filters["parent_id"]}}

            # Date filters
            if "created_after" in filters:
                issue_filter["createdAt"] = {"gte": filters["created_after"]}
            if "updated_after" in filters:
                issue_filter["updatedAt"] = {"gte": filters["updated_after"]}
            if "due_before" in filters:
                issue_filter["dueDate"] = {"lte": filters["due_before"]}

        # Exclude archived issues by default
        if (
            not filters
            or "includeArchived" not in filters
            or not filters["includeArchived"]
        ):
            issue_filter["archivedAt"] = {"null": True}

        query = gql(
            ISSUE_LIST_FRAGMENTS
            + """
            query ListIssues($filter: IssueFilter, $first: Int!) {
                issues(
                    filter: $filter
                    first: $first
                    orderBy: updatedAt
                ) {
                    nodes {
                        ...IssueCompactFields
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query,
                variable_values={
                    "filter": issue_filter,
                    "first": limit,
                    # Note: Linear uses cursor-based pagination, not offset
                    # For simplicity, we ignore offset here
                },
            )

        tasks = []
        for issue in result["issues"]["nodes"]:
            tasks.append(self._task_from_linear_issue(issue))

        return tasks

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search Linear issues with advanced filtering and text search."""
        team_id = await self._ensure_team_id()

        # Build filter
        issue_filter = {"team": {"id": {"eq": team_id}}}

        # Text search in title and description
        if query.query:
            issue_filter["or"] = [
                {"title": {"containsIgnoreCase": query.query}},
                {"description": {"containsIgnoreCase": query.query}},
            ]

        # State filter
        if query.state:
            state_mapping = {
                TicketState.OPEN: ["backlog", "unstarted"],
                TicketState.IN_PROGRESS: ["started"],
                TicketState.DONE: ["completed"],
                TicketState.CLOSED: ["canceled"],
            }
            if query.state in state_mapping:
                issue_filter["state"] = {"type": {"in": state_mapping[query.state]}}

        # Priority filter
        if query.priority:
            linear_priority = LinearPriorityMapping.TO_LINEAR.get(query.priority, 3)
            issue_filter["priority"] = {"eq": linear_priority}

        # Assignee filter
        if query.assignee:
            user_id = await self._get_user_id(query.assignee)
            if user_id:
                issue_filter["assignee"] = {"id": {"eq": user_id}}

        # Tags filter (labels in Linear)
        if query.tags:
            issue_filter["labels"] = {"some": {"name": {"in": query.tags}}}

        # Exclude archived
        issue_filter["archivedAt"] = {"null": True}

        search_query = gql(
            ISSUE_LIST_FRAGMENTS
            + """
            query SearchIssues($filter: IssueFilter, $first: Int!) {
                issues(
                    filter: $filter
                    first: $first
                    orderBy: updatedAt
                ) {
                    nodes {
                        ...IssueCompactFields
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                search_query,
                variable_values={
                    "filter": issue_filter,
                    "first": query.limit,
                    # Note: Linear uses cursor-based pagination, not offset
                },
            )

        tasks = []
        for issue in result["issues"]["nodes"]:
            tasks.append(self._task_from_linear_issue(issue))

        return tasks

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Task]:
        """Transition Linear issue to new state with workflow validation."""
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add comment to a Linear issue."""
        # Get Linear issue ID
        query = gql(
            """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query, variable_values={"identifier": comment.ticket_id}
            )

        if not result.get("issue"):
            raise ValueError(f"Issue {comment.ticket_id} not found")

        linear_id = result["issue"]["id"]

        # Create comment mutation (only include needed fragments)
        create_comment_query = gql(
            USER_FRAGMENT
            + COMMENT_FRAGMENT
            + """
            mutation CreateComment($input: CommentCreateInput!) {
                commentCreate(input: $input) {
                    success
                    comment {
                        ...CommentFields
                    }
                }
            }
        """
        )

        comment_input = {
            "issueId": linear_id,
            "body": comment.content,
        }

        # Handle parent comment for threading
        if comment.metadata and "parent_comment_id" in comment.metadata:
            comment_input["parentId"] = comment.metadata["parent_comment_id"]

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_comment_query, variable_values={"input": comment_input}
            )

        if not result["commentCreate"]["success"]:
            raise Exception("Failed to create comment")

        created_comment = result["commentCreate"]["comment"]

        return Comment(
            id=created_comment["id"],
            ticket_id=comment.ticket_id,
            author=(
                created_comment["user"]["email"]
                if created_comment.get("user")
                else None
            ),
            content=created_comment["body"],
            created_at=datetime.fromisoformat(
                created_comment["createdAt"].replace("Z", "+00:00")
            ),
            metadata={
                "linear": {
                    "id": created_comment["id"],
                    "parent_id": (
                        created_comment.get("parent", {}).get("id")
                        if created_comment.get("parent")
                        else None
                    ),
                }
            },
        )

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a Linear issue with pagination."""
        query = gql(
            USER_FRAGMENT
            + COMMENT_FRAGMENT
            + """
            query GetIssueComments($identifier: String!, $first: Int!) {
                issue(id: $identifier) {
                    comments(first: $first, orderBy: createdAt) {
                        nodes {
                            ...CommentFields
                        }
                    }
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    query,
                    variable_values={
                        "identifier": ticket_id,
                        "first": limit,
                        # Note: Linear uses cursor-based pagination
                    },
                )

            if not result.get("issue"):
                return []

            comments = []
            for comment_data in result["issue"]["comments"]["nodes"]:
                comments.append(
                    Comment(
                        id=comment_data["id"],
                        ticket_id=ticket_id,
                        author=(
                            comment_data["user"]["email"]
                            if comment_data.get("user")
                            else None
                        ),
                        content=comment_data["body"],
                        created_at=datetime.fromisoformat(
                            comment_data["createdAt"].replace("Z", "+00:00")
                        ),
                        metadata={
                            "linear": {
                                "id": comment_data["id"],
                                "parent_id": (
                                    comment_data.get("parent", {}).get("id")
                                    if comment_data.get("parent")
                                    else None
                                ),
                            }
                        },
                    )
                )

            return comments
        except TransportQueryError:
            return []

    async def create_project(self, name: str, description: Optional[str] = None) -> str:
        """Create a Linear project."""
        team_id = await self._ensure_team_id()

        create_query = gql(
            """
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
                        id
                        name
                    }
                }
            }
        """
        )

        project_input = {
            "name": name,
            "teamIds": [team_id],
        }
        if description:
            project_input["description"] = description

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": project_input}
            )

        if not result["projectCreate"]["success"]:
            raise Exception("Failed to create project")

        return result["projectCreate"]["project"]["id"]

    async def get_cycles(
        self, active_only: bool = True
    ) -> builtins.list[dict[str, Any]]:
        """Get Linear cycles (sprints) for the team."""
        team_id = await self._ensure_team_id()

        cycle_filter = {"team": {"id": {"eq": team_id}}}
        if active_only:
            cycle_filter["isActive"] = {"eq": True}

        query = gql(
            """
            query GetCycles($filter: CycleFilter) {
                cycles(filter: $filter, orderBy: createdAt) {
                    nodes {
                        id
                        number
                        name
                        description
                        startsAt
                        endsAt
                        completedAt
                        issues {
                            nodes {
                                id
                                identifier
                            }
                        }
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query, variable_values={"filter": cycle_filter}
            )

        return result["cycles"]["nodes"]

    async def add_to_cycle(self, ticket_id: str, cycle_id: str) -> bool:
        """Add an issue to a cycle."""
        return (
            await self.update(
                ticket_id, {"metadata": {"linear": {"cycle_id": cycle_id}}}
            )
            is not None
        )

    async def set_due_date(self, ticket_id: str, due_date: Union[str, date]) -> bool:
        """Set due date for an issue."""
        if isinstance(due_date, date):
            due_date = due_date.isoformat()

        return (
            await self.update(
                ticket_id, {"metadata": {"linear": {"due_date": due_date}}}
            )
            is not None
        )

    async def add_reaction(self, comment_id: str, emoji: str) -> bool:
        """Add reaction to a comment."""
        create_query = gql(
            """
            mutation CreateReaction($input: ReactionCreateInput!) {
                reactionCreate(input: $input) {
                    success
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query,
                variable_values={
                    "input": {
                        "commentId": comment_id,
                        "emoji": emoji,
                    }
                },
            )

        return result.get("reactionCreate", {}).get("success", False)

    async def link_to_pull_request(
        self,
        ticket_id: str,
        pr_url: str,
        pr_number: Optional[int] = None,
    ) -> dict[str, Any]:
        """Link a Linear issue to a GitHub pull request.

        Args:
            ticket_id: Linear issue identifier (e.g., 'BTA-123')
            pr_url: GitHub PR URL
            pr_number: Optional PR number (extracted from URL if not provided)

        Returns:
            Dictionary with link status and details

        """
        # Parse PR URL to extract details
        import re

        pr_pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.search(pr_pattern, pr_url)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL format: {pr_url}")

        owner, repo, extracted_pr_number = match.groups()
        if not pr_number:
            pr_number = int(extracted_pr_number)

        # Create an attachment to link the PR
        create_query = gql(
            """
            mutation CreateAttachment($input: AttachmentCreateInput!) {
                attachmentCreate(input: $input) {
                    attachment {
                        id
                        url
                        title
                        subtitle
                        source
                    }
                    success
                }
            }
        """
        )

        # Get the issue ID from the identifier
        issue = await self.read(ticket_id)
        if not issue:
            raise ValueError(f"Issue {ticket_id} not found")

        # Create attachment input
        attachment_input = {
            "issueId": issue.metadata.get("linear", {}).get("id"),
            "url": pr_url,
            "title": f"Pull Request #{pr_number}",
            "subtitle": f"{owner}/{repo}",
            "source": {
                "type": "githubPr",
                "data": {
                    "number": pr_number,
                    "owner": owner,
                    "repo": repo,
                },
            },
        }

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": attachment_input}
            )

        if result.get("attachmentCreate", {}).get("success"):
            attachment = result["attachmentCreate"]["attachment"]

            # Also add a comment about the PR link
            comment_text = f"Linked to GitHub PR: {pr_url}"
            await self.add_comment(
                Comment(
                    ticket_id=ticket_id,
                    content=comment_text,
                    author="system",
                )
            )

            return {
                "success": True,
                "attachment_id": attachment["id"],
                "pr_url": pr_url,
                "pr_number": pr_number,
                "linked_issue": ticket_id,
                "message": f"Successfully linked PR #{pr_number} to issue {ticket_id}",
            }
        else:
            return {
                "success": False,
                "pr_url": pr_url,
                "pr_number": pr_number,
                "linked_issue": ticket_id,
                "message": "Failed to create attachment link",
            }

    async def create_pull_request_for_issue(
        self,
        ticket_id: str,
        github_config: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a GitHub PR for a Linear issue using GitHub integration.

        This requires GitHub integration to be configured in Linear.

        Args:
            ticket_id: Linear issue identifier
            github_config: GitHub configuration including:
                - owner: GitHub repository owner
                - repo: GitHub repository name
                - base_branch: Target branch (default: main)
                - head_branch: Source branch (auto-generated if not provided)

        Returns:
            Dictionary with PR creation status

        """
        # Get the issue details
        issue = await self.read(ticket_id)
        if not issue:
            raise ValueError(f"Issue {ticket_id} not found")

        # Generate branch name if not provided
        head_branch = github_config.get("head_branch")
        if not head_branch:
            # Use Linear's branch naming convention
            # e.g., "bta-123-fix-authentication-bug"
            safe_title = "-".join(
                issue.title.lower()
                .replace("[", "")
                .replace("]", "")
                .replace("#", "")
                .replace("/", "-")
                .replace("\\", "-")
                .split()[:5]  # Limit to 5 words
            )
            head_branch = f"{ticket_id.lower()}-{safe_title}"

        # Update the issue with the branch name
        update_query = gql(
            """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    issue {
                        id
                        identifier
                        branchName
                    }
                    success
                }
            }
        """
        )

        linear_id = issue.metadata.get("linear", {}).get("id")
        if not linear_id:
            # Need to get the full issue ID
            search_result = await self._search_by_identifier(ticket_id)
            if not search_result:
                raise ValueError(f"Could not find Linear ID for issue {ticket_id}")
            linear_id = search_result["id"]

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                update_query,
                variable_values={"id": linear_id, "input": {"branchName": head_branch}},
            )

        if result.get("issueUpdate", {}).get("success"):
            # Prepare PR metadata to return
            pr_metadata = {
                "branch_name": head_branch,
                "issue_id": ticket_id,
                "issue_title": issue.title,
                "issue_description": issue.description,
                "github_owner": github_config.get("owner"),
                "github_repo": github_config.get("repo"),
                "base_branch": github_config.get("base_branch", "main"),
                "message": f"Branch name '{head_branch}' set for issue {ticket_id}. Use GitHub integration or API to create the actual PR.",
            }

            # Add a comment about the branch
            await self.add_comment(
                Comment(
                    ticket_id=ticket_id,
                    content=f"Branch created: `{head_branch}`\nReady for pull request to `{pr_metadata['base_branch']}`",
                    author="system",
                )
            )

            return pr_metadata
        else:
            raise ValueError(f"Failed to update issue {ticket_id} with branch name")

    async def _search_by_identifier(self, identifier: str) -> Optional[dict[str, Any]]:
        """Search for an issue by its identifier."""
        search_query = gql(
            """
            query SearchIssue($identifier: String!) {
                issue(id: $identifier) {
                    id
                    identifier
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    search_query, variable_values={"identifier": identifier}
                )
            return result.get("issue")
        except Exception:
            return None

    # Epic/Issue/Task Hierarchy Methods (Linear: Project = Epic, Issue = Issue, Sub-issue = Task)

    async def create_epic(
        self, title: str, description: Optional[str] = None, **kwargs
    ) -> Optional[Epic]:
        """Create epic (Linear Project).

        Args:
            title: Epic/Project name
            description: Epic/Project description
            **kwargs: Additional fields (e.g., target_date, lead_id)

        Returns:
            Created epic or None if failed

        """
        team_id = await self._ensure_team_id()

        create_query = gql(
            PROJECT_FRAGMENT
            + """
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
                        ...ProjectFields
                    }
                }
            }
        """
        )

        project_input = {
            "name": title,
            "teamIds": [team_id],
        }
        if description:
            project_input["description"] = description

        # Handle additional Linear-specific fields
        if "target_date" in kwargs:
            project_input["targetDate"] = kwargs["target_date"]
        if "lead_id" in kwargs:
            project_input["leadId"] = kwargs["lead_id"]

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": project_input}
            )

        if not result["projectCreate"]["success"]:
            return None

        project = result["projectCreate"]["project"]
        return self._epic_from_linear_project(project)

    async def get_epic(self, epic_id: str) -> Optional[Epic]:
        """Get epic (Linear Project) by ID.

        Args:
            epic_id: Linear project ID

        Returns:
            Epic if found, None otherwise

        """
        query = gql(
            PROJECT_FRAGMENT
            + """
            query GetProject($id: String!) {
                project(id: $id) {
                    ...ProjectFields
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(query, variable_values={"id": epic_id})

            if result.get("project"):
                return self._epic_from_linear_project(result["project"])
        except TransportQueryError:
            pass

        return None

    async def list_epics(self, **kwargs) -> builtins.list[Epic]:
        """List all Linear Projects (Epics).

        Args:
            **kwargs: Optional filters (team_id, state)

        Returns:
            List of epics

        """
        team_id = await self._ensure_team_id()

        # Build project filter
        project_filter = {"team": {"id": {"eq": team_id}}}

        if "state" in kwargs:
            # Map TicketState to Linear project state
            state_mapping = {
                TicketState.OPEN: "planned",
                TicketState.IN_PROGRESS: "started",
                TicketState.WAITING: "paused",
                TicketState.DONE: "completed",
                TicketState.CLOSED: "canceled",
            }
            linear_state = state_mapping.get(kwargs["state"], "planned")
            project_filter["state"] = {"eq": linear_state}

        query = gql(
            PROJECT_FRAGMENT
            + """
            query ListProjects($filter: ProjectFilter, $first: Int!) {
                projects(filter: $filter, first: $first, orderBy: updatedAt) {
                    nodes {
                        ...ProjectFields
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                query,
                variable_values={
                    "filter": project_filter,
                    "first": kwargs.get("limit", 50),
                },
            )

        epics = []
        for project in result["projects"]["nodes"]:
            epics.append(self._epic_from_linear_project(project))

        return epics

    async def create_issue(
        self,
        title: str,
        description: Optional[str] = None,
        epic_id: Optional[str] = None,
        **kwargs,
    ) -> Optional[Task]:
        """Create issue and optionally associate with project (epic).

        Args:
            title: Issue title
            description: Issue description
            epic_id: Optional Linear project ID (epic)
            **kwargs: Additional fields

        Returns:
            Created issue or None if failed

        """
        # Use existing create method but ensure it's created as an ISSUE type
        task = Task(
            title=title,
            description=description,
            ticket_type=TicketType.ISSUE,
            parent_epic=epic_id,
            **{k: v for k, v in kwargs.items() if k in Task.__fields__},
        )

        # The existing create method handles project association via parent_epic field
        return await self.create(task)

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List all issues in a Linear project (epic).

        Args:
            epic_id: Linear project ID

        Returns:
            List of issues belonging to project

        """
        query = gql(
            ISSUE_LIST_FRAGMENTS
            + """
            query GetProjectIssues($projectId: String!, $first: Int!) {
                project(id: $projectId) {
                    issues(first: $first) {
                        nodes {
                            ...IssueCompactFields
                        }
                    }
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    query, variable_values={"projectId": epic_id, "first": 100}
                )

            if not result.get("project"):
                return []

            issues = []
            for issue_data in result["project"]["issues"]["nodes"]:
                task = self._task_from_linear_issue(issue_data)
                # Only return issues (not sub-tasks)
                if task.is_issue():
                    issues.append(task)

            return issues
        except TransportQueryError:
            return []

    async def create_task(
        self, title: str, parent_id: str, description: Optional[str] = None, **kwargs
    ) -> Optional[Task]:
        """Create task as sub-issue of parent.

        Args:
            title: Task title
            parent_id: Required parent issue identifier (e.g., 'BTA-123')
            description: Task description
            **kwargs: Additional fields

        Returns:
            Created task or None if failed

        Raises:
            ValueError: If parent_id is not provided

        """
        if not parent_id:
            raise ValueError("Tasks must have a parent_id (issue identifier)")

        # Get parent issue's Linear ID
        parent_query = gql(
            """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            parent_result = await session.execute(
                parent_query, variable_values={"identifier": parent_id}
            )

        if not parent_result.get("issue"):
            raise ValueError(f"Parent issue {parent_id} not found")

        parent_linear_id = parent_result["issue"]["id"]

        # Create task using existing create method
        task = Task(
            title=title,
            description=description,
            ticket_type=TicketType.TASK,
            parent_issue=parent_id,
            **{k: v for k, v in kwargs.items() if k in Task.__fields__},
        )

        # Validate hierarchy
        errors = task.validate_hierarchy()
        if errors:
            raise ValueError(f"Invalid task hierarchy: {'; '.join(errors)}")

        # Create with parent relationship
        team_id = await self._ensure_team_id()
        states = await self._get_workflow_states()

        # Map state to Linear state ID
        linear_state_type = self._map_state_to_linear(task.state)
        state_data = states.get(linear_state_type)
        if not state_data:
            state_data = states.get("backlog")
        state_id = state_data["id"] if state_data else None

        # Build issue input (sub-issue)
        issue_input = {
            "title": task.title,
            "teamId": team_id,
            "parentId": parent_linear_id,  # This makes it a sub-issue
        }

        if task.description:
            issue_input["description"] = task.description

        if state_id:
            issue_input["stateId"] = state_id

        # Set priority
        if task.priority:
            issue_input["priority"] = LinearPriorityMapping.TO_LINEAR.get(
                task.priority, 3
            )

        # Create sub-issue mutation
        create_query = gql(
            ALL_FRAGMENTS
            + """
            mutation CreateSubIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        ...IssueFullFields
                    }
                }
            }
        """
        )

        client = self._create_client()
        async with client as session:
            result = await session.execute(
                create_query, variable_values={"input": issue_input}
            )

        if not result["issueCreate"]["success"]:
            return None

        created_issue = result["issueCreate"]["issue"]
        return self._task_from_linear_issue(created_issue)

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List all tasks (sub-issues) under an issue.

        Args:
            issue_id: Issue identifier (e.g., 'BTA-123')

        Returns:
            List of tasks belonging to issue

        """
        query = gql(
            ISSUE_LIST_FRAGMENTS
            + """
            query GetIssueSubtasks($identifier: String!) {
                issue(id: $identifier) {
                    children {
                        nodes {
                            ...IssueCompactFields
                        }
                    }
                }
            }
        """
        )

        try:
            client = self._create_client()
            async with client as session:
                result = await session.execute(
                    query, variable_values={"identifier": issue_id}
                )

            if not result.get("issue"):
                return []

            tasks = []
            for child_data in result["issue"]["children"]["nodes"]:
                task = self._task_from_linear_issue(child_data)
                # Only return tasks (sub-issues)
                if task.is_task():
                    tasks.append(task)

            return tasks
        except TransportQueryError:
            return []

    async def close(self) -> None:
        """Close the GraphQL client connection.

        Since we create fresh clients for each operation, there's no persistent
        connection to close. Each client's transport is automatically closed when
        the async context manager exits.
        """
        pass


# Register the adapter
AdapterRegistry.register("linear", LinearAdapter)
