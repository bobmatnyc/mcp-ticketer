"""Linear adapter implementation using native GraphQL API with full feature support."""

import os
import asyncio
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum

from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport
from gql.transport.exceptions import TransportQueryError
import httpx

from ..core.adapter import BaseAdapter
from ..core.models import Epic, Task, Comment, SearchQuery, TicketState, Priority
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
        2: Priority.HIGH,      # Medium
        3: Priority.MEDIUM,    # Low
        4: Priority.LOW,       # No priority
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
    USER_FRAGMENT +
    WORKFLOW_STATE_FRAGMENT +
    TEAM_FRAGMENT +
    CYCLE_FRAGMENT +
    PROJECT_FRAGMENT +
    LABEL_FRAGMENT +
    ATTACHMENT_FRAGMENT +
    COMMENT_FRAGMENT +
    ISSUE_COMPACT_FRAGMENT +
    ISSUE_FULL_FRAGMENT
)

# Fragments needed for issue list/search (without comments)
ISSUE_LIST_FRAGMENTS = (
    USER_FRAGMENT +
    WORKFLOW_STATE_FRAGMENT +
    TEAM_FRAGMENT +
    CYCLE_FRAGMENT +
    PROJECT_FRAGMENT +
    LABEL_FRAGMENT +
    ATTACHMENT_FRAGMENT +
    ISSUE_COMPACT_FRAGMENT
)


class LinearAdapter(BaseAdapter[Task]):
    """Adapter for Linear issue tracking system using native GraphQL API."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Linear adapter.

        Args:
            config: Configuration with:
                - api_key: Linear API key (or LINEAR_API_KEY env var)
                - workspace: Linear workspace name (optional, for documentation)
                - team_key: Linear team key (required, e.g., 'BTA')
                - api_url: Optional Linear API URL
        """
        super().__init__(config)

        # Get API key from config or environment
        self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError("Linear API key required (config.api_key or LINEAR_API_KEY env var)")

        self.workspace = config.get("workspace")  # Optional, for documentation
        self.team_key = config.get("team_key")
        if not self.team_key:
            raise ValueError("Linear team_key is required in configuration")
        self.api_url = config.get("api_url", "https://api.linear.app/graphql")

        # Setup GraphQL client with authentication
        transport = HTTPXAsyncTransport(
            url=self.api_url,
            headers={"Authorization": self.api_key},
            timeout=30.0,
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=False)

        # Caches for frequently used data
        self._team_id: Optional[str] = None
        self._workflow_states: Optional[Dict[str, Dict[str, Any]]] = None
        self._labels: Optional[Dict[str, str]] = None  # name -> id
        self._users: Optional[Dict[str, str]] = None  # email -> id

        # Initialize state mapping
        self._state_mapping = self._get_state_mapping()

        # Initialization lock to prevent concurrent initialization
        self._init_lock = asyncio.Lock()
        self._initialized = False

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
        """Fetch team ID."""
        query = gql("""
            query GetTeam($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        name
                        key
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query, variable_values={"key": self.team_key})

        if not result["teams"]["nodes"]:
            raise ValueError(f"Team with key '{self.team_key}' not found")

        return result["teams"]["nodes"][0]["id"]

    async def _fetch_workflow_states_data(self, team_id: str) -> Dict[str, Dict[str, Any]]:
        """Fetch workflow states data."""
        query = gql("""
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
        """)

        async with self.client as session:
            result = await session.execute(query, variable_values={"teamId": team_id})

        workflow_states = {}
        for state in result["workflowStates"]["nodes"]:
            state_type = state["type"].lower()
            if state_type not in workflow_states:
                workflow_states[state_type] = state
            elif state["position"] < workflow_states[state_type]["position"]:
                workflow_states[state_type] = state

        return workflow_states

    async def _fetch_labels_data(self, team_id: str) -> Dict[str, str]:
        """Fetch labels data."""
        query = gql("""
            query GetLabels($teamId: ID!) {
                issueLabels(filter: { team: { id: { eq: $teamId } } }) {
                    nodes {
                        id
                        name
                    }
                }
            }
        """)

        async with self.client as session:
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

    async def _get_workflow_states(self) -> Dict[str, Dict[str, Any]]:
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
        search_query = gql("""
            query GetLabel($name: String!, $teamId: ID!) {
                issueLabels(filter: { name: { eq: $name }, team: { id: { eq: $teamId } } }) {
                    nodes {
                        id
                        name
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                search_query,
                variable_values={"name": name, "teamId": team_id}
            )

        if result["issueLabels"]["nodes"]:
            label_id = result["issueLabels"]["nodes"][0]["id"]
            self._labels[name] = label_id
            return label_id

        # Create new label
        create_query = gql("""
            mutation CreateLabel($input: IssueLabelCreateInput!) {
                issueLabelCreate(input: $input) {
                    issueLabel {
                        id
                        name
                    }
                }
            }
        """)

        label_input = {
            "name": name,
            "teamId": team_id,
        }
        if color:
            label_input["color"] = color

        async with self.client as session:
            result = await session.execute(
                create_query,
                variable_values={"input": label_input}
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

        query = gql("""
            query GetUser($email: String!) {
                users(filter: { email: { eq: $email } }) {
                    nodes {
                        id
                        email
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(query, variable_values={"email": email})

        if result["users"]["nodes"]:
            user_id = result["users"]["nodes"][0]["id"]
            self._users[email] = user_id
            return user_id

        return None

    def _get_state_mapping(self) -> Dict[TicketState, str]:
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

    def _map_linear_state(self, state_data: Dict[str, Any], labels: List[str]) -> TicketState:
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

    def _task_from_linear_issue(self, issue: Dict[str, Any]) -> Task:
        """Convert Linear issue to universal Task."""
        # Extract labels
        tags = []
        if issue.get("labels") and issue["labels"].get("nodes"):
            tags = [label["name"] for label in issue["labels"]["nodes"]]

        # Map priority
        linear_priority = issue.get("priority", 4)
        priority = LinearPriorityMapping.FROM_LINEAR.get(linear_priority, Priority.MEDIUM)

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
                "cycle_id": issue.get("cycle", {}).get("id") if issue.get("cycle") else None,
                "cycle_name": issue.get("cycle", {}).get("name") if issue.get("cycle") else None,
                "project_id": issue.get("project", {}).get("id") if issue.get("project") else None,
                "project_name": issue.get("project", {}).get("name") if issue.get("project") else None,
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

        return Task(
            id=issue["identifier"],
            title=issue["title"],
            description=issue.get("description"),
            state=state,
            priority=priority,
            tags=tags,
            parent_issue=issue.get("parent", {}).get("identifier") if issue.get("parent") else None,
            parent_epic=issue.get("project", {}).get("id") if issue.get("project") else None,
            assignee=issue.get("assignee", {}).get("email") if issue.get("assignee") else None,
            estimated_hours=issue.get("estimate"),
            created_at=datetime.fromisoformat(issue["createdAt"].replace("Z", "+00:00"))
            if issue.get("createdAt") else None,
            updated_at=datetime.fromisoformat(issue["updatedAt"].replace("Z", "+00:00"))
            if issue.get("updatedAt") else None,
            metadata=metadata,
        )

    async def create(self, ticket: Task) -> Task:
        """Create a new Linear issue with full field support."""
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
            issue_input["priority"] = LinearPriorityMapping.TO_LINEAR.get(ticket.priority, 3)

        # Handle labels/tags
        if ticket.tags:
            label_ids = []
            for tag in ticket.tags:
                # Add special state labels if needed
                if ticket.state == TicketState.BLOCKED and "blocked" not in [t.lower() for t in ticket.tags]:
                    label_ids.append(await self._get_or_create_label("blocked", "#FF0000"))
                elif ticket.state == TicketState.WAITING and "waiting" not in [t.lower() for t in ticket.tags]:
                    label_ids.append(await self._get_or_create_label("waiting", "#FFA500"))
                elif ticket.state == TicketState.READY and "ready" not in [t.lower() for t in ticket.tags]:
                    label_ids.append(await self._get_or_create_label("ready", "#00FF00"))

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
            parent_query = gql("""
                query GetIssue($identifier: String!) {
                    issue(id: $identifier) {
                        id
                    }
                }
            """)
            async with self.client as session:
                parent_result = await session.execute(
                    parent_query,
                    variable_values={"identifier": ticket.parent_issue}
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
        create_query = gql(ALL_FRAGMENTS + """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        ...IssueFullFields
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                create_query,
                variable_values={"input": issue_input}
            )

        if not result["issueCreate"]["success"]:
            raise Exception("Failed to create Linear issue")

        created_issue = result["issueCreate"]["issue"]
        return self._task_from_linear_issue(created_issue)

    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read a Linear issue by identifier with full details."""
        query = gql(ALL_FRAGMENTS + """
            query GetIssue($identifier: String!) {
                issue(id: $identifier) {
                    ...IssueFullFields
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    query,
                    variable_values={"identifier": ticket_id}
                )

            if result.get("issue"):
                return self._task_from_linear_issue(result["issue"])
        except TransportQueryError:
            # Issue not found
            pass

        return None

    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update a Linear issue with comprehensive field support."""
        # First get the Linear internal ID
        query = gql("""
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={"identifier": ticket_id}
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
        update_query = gql(ALL_FRAGMENTS + """
            mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
                issueUpdate(id: $id, input: $input) {
                    success
                    issue {
                        ...IssueFullFields
                    }
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                update_query,
                variable_values={"id": linear_id, "input": update_input}
            )

        if result["issueUpdate"]["success"]:
            return self._task_from_linear_issue(result["issueUpdate"]["issue"])

        return None

    async def delete(self, ticket_id: str) -> bool:
        """Archive (soft delete) a Linear issue."""
        # Get Linear ID
        query = gql("""
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={"identifier": ticket_id}
            )

        if not result.get("issue"):
            return False

        linear_id = result["issue"]["id"]

        # Archive mutation
        archive_query = gql("""
            mutation ArchiveIssue($id: String!) {
                issueArchive(id: $id) {
                    success
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                archive_query,
                variable_values={"id": linear_id}
            )

        return result.get("issueArchive", {}).get("success", False)

    async def list(
        self,
        limit: int = 10,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
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
        if not filters or "includeArchived" not in filters or not filters["includeArchived"]:
            issue_filter["archivedAt"] = {"null": True}

        query = gql(ISSUE_LIST_FRAGMENTS + """
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
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={
                    "filter": issue_filter,
                    "first": limit,
                    # Note: Linear uses cursor-based pagination, not offset
                    # For simplicity, we ignore offset here
                }
            )

        tasks = []
        for issue in result["issues"]["nodes"]:
            tasks.append(self._task_from_linear_issue(issue))

        return tasks

    async def search(self, query: SearchQuery) -> List[Task]:
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

        search_query = gql(ISSUE_LIST_FRAGMENTS + """
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
        """)

        async with self.client as session:
            result = await session.execute(
                search_query,
                variable_values={
                    "filter": issue_filter,
                    "first": query.limit,
                    # Note: Linear uses cursor-based pagination, not offset
                }
            )

        tasks = []
        for issue in result["issues"]["nodes"]:
            tasks.append(self._task_from_linear_issue(issue))

        return tasks

    async def transition_state(
        self,
        ticket_id: str,
        target_state: TicketState
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
        query = gql("""
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={"identifier": comment.ticket_id}
            )

        if not result.get("issue"):
            raise ValueError(f"Issue {comment.ticket_id} not found")

        linear_id = result["issue"]["id"]

        # Create comment mutation (only include needed fragments)
        create_comment_query = gql(USER_FRAGMENT + COMMENT_FRAGMENT + """
            mutation CreateComment($input: CommentCreateInput!) {
                commentCreate(input: $input) {
                    success
                    comment {
                        ...CommentFields
                    }
                }
            }
        """)

        comment_input = {
            "issueId": linear_id,
            "body": comment.content,
        }

        # Handle parent comment for threading
        if comment.metadata and "parent_comment_id" in comment.metadata:
            comment_input["parentId"] = comment.metadata["parent_comment_id"]

        async with self.client as session:
            result = await session.execute(
                create_comment_query,
                variable_values={"input": comment_input}
            )

        if not result["commentCreate"]["success"]:
            raise Exception("Failed to create comment")

        created_comment = result["commentCreate"]["comment"]

        return Comment(
            id=created_comment["id"],
            ticket_id=comment.ticket_id,
            author=created_comment["user"]["email"] if created_comment.get("user") else None,
            content=created_comment["body"],
            created_at=datetime.fromisoformat(created_comment["createdAt"].replace("Z", "+00:00")),
            metadata={
                "linear": {
                    "id": created_comment["id"],
                    "parent_id": created_comment.get("parent", {}).get("id") if created_comment.get("parent") else None,
                }
            },
        )

    async def get_comments(
        self,
        ticket_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Comment]:
        """Get comments for a Linear issue with pagination."""
        query = gql(USER_FRAGMENT + COMMENT_FRAGMENT + """
            query GetIssueComments($identifier: String!, $first: Int!) {
                issue(id: $identifier) {
                    comments(first: $first, orderBy: createdAt) {
                        nodes {
                            ...CommentFields
                        }
                    }
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    query,
                    variable_values={
                        "identifier": ticket_id,
                        "first": limit,
                        # Note: Linear uses cursor-based pagination
                    }
                )

            if not result.get("issue"):
                return []

            comments = []
            for comment_data in result["issue"]["comments"]["nodes"]:
                comments.append(Comment(
                    id=comment_data["id"],
                    ticket_id=ticket_id,
                    author=comment_data["user"]["email"] if comment_data.get("user") else None,
                    content=comment_data["body"],
                    created_at=datetime.fromisoformat(comment_data["createdAt"].replace("Z", "+00:00")),
                    metadata={
                        "linear": {
                            "id": comment_data["id"],
                            "parent_id": comment_data.get("parent", {}).get("id") if comment_data.get("parent") else None,
                        }
                    },
                ))

            return comments
        except TransportQueryError:
            return []

    async def create_project(self, name: str, description: Optional[str] = None) -> str:
        """Create a Linear project."""
        team_id = await self._ensure_team_id()

        create_query = gql("""
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
                        id
                        name
                    }
                }
            }
        """)

        project_input = {
            "name": name,
            "teamIds": [team_id],
        }
        if description:
            project_input["description"] = description

        async with self.client as session:
            result = await session.execute(
                create_query,
                variable_values={"input": project_input}
            )

        if not result["projectCreate"]["success"]:
            raise Exception("Failed to create project")

        return result["projectCreate"]["project"]["id"]

    async def get_cycles(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get Linear cycles (sprints) for the team."""
        team_id = await self._ensure_team_id()

        cycle_filter = {"team": {"id": {"eq": team_id}}}
        if active_only:
            cycle_filter["isActive"] = {"eq": True}

        query = gql("""
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
        """)

        async with self.client as session:
            result = await session.execute(
                query,
                variable_values={"filter": cycle_filter}
            )

        return result["cycles"]["nodes"]

    async def add_to_cycle(self, ticket_id: str, cycle_id: str) -> bool:
        """Add an issue to a cycle."""
        return await self.update(
            ticket_id,
            {"metadata": {"linear": {"cycle_id": cycle_id}}}
        ) is not None

    async def set_due_date(self, ticket_id: str, due_date: Union[str, date]) -> bool:
        """Set due date for an issue."""
        if isinstance(due_date, date):
            due_date = due_date.isoformat()

        return await self.update(
            ticket_id,
            {"metadata": {"linear": {"due_date": due_date}}}
        ) is not None

    async def add_reaction(self, comment_id: str, emoji: str) -> bool:
        """Add reaction to a comment."""
        create_query = gql("""
            mutation CreateReaction($input: ReactionCreateInput!) {
                reactionCreate(input: $input) {
                    success
                }
            }
        """)

        async with self.client as session:
            result = await session.execute(
                create_query,
                variable_values={
                    "input": {
                        "commentId": comment_id,
                        "emoji": emoji,
                    }
                }
            )

        return result.get("reactionCreate", {}).get("success", False)

    async def link_to_pull_request(
        self,
        ticket_id: str,
        pr_url: str,
        pr_number: Optional[int] = None,
    ) -> Dict[str, Any]:
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
        create_query = gql("""
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
        """)

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
                }
            },
        }

        async with self.client as session:
            result = await session.execute(
                create_query,
                variable_values={"input": attachment_input}
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
        github_config: Dict[str, Any],
    ) -> Dict[str, Any]:
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
        update_query = gql("""
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
        """)

        linear_id = issue.metadata.get("linear", {}).get("id")
        if not linear_id:
            # Need to get the full issue ID
            search_result = await self._search_by_identifier(ticket_id)
            if not search_result:
                raise ValueError(f"Could not find Linear ID for issue {ticket_id}")
            linear_id = search_result["id"]

        async with self.client as session:
            result = await session.execute(
                update_query,
                variable_values={
                    "id": linear_id,
                    "input": {"branchName": head_branch}
                }
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

    async def _search_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Search for an issue by its identifier."""
        search_query = gql("""
            query SearchIssue($identifier: String!) {
                issue(id: $identifier) {
                    id
                    identifier
                }
            }
        """)

        try:
            async with self.client as session:
                result = await session.execute(
                    search_query,
                    variable_values={"identifier": identifier}
                )
            return result.get("issue")
        except:
            return None

    async def close(self) -> None:
        """Close the GraphQL client connection."""
        if hasattr(self.client, 'close_async'):
            await self.client.close_async()
        elif hasattr(self.client.transport, 'close'):
            await self.client.transport.close()


# Register the adapter
AdapterRegistry.register("linear", LinearAdapter)