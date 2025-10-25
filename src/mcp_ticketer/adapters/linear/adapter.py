"""Main LinearAdapter class for Linear API integration."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

try:
    from gql import gql
    from gql.transport.exceptions import TransportQueryError
except ImportError:
    gql = None
    TransportQueryError = Exception

from ...core.adapter import BaseAdapter
from ...core.models import Comment, Epic, SearchQuery, Task, TicketState
from ...core.registry import AdapterRegistry
from .client import LinearGraphQLClient
from .mappers import (
    build_linear_issue_input,
    build_linear_issue_update_input,
    map_linear_comment_to_comment,
    map_linear_issue_to_task,
    map_linear_project_to_epic,
)
from .queries import (
    ALL_FRAGMENTS,
    CREATE_ISSUE_MUTATION,
    LIST_ISSUES_QUERY,
    SEARCH_ISSUES_QUERY,
    UPDATE_ISSUE_MUTATION,
    WORKFLOW_STATES_QUERY,
)
from .types import (
    LinearStateMapping,
    build_issue_filter,
    get_linear_priority,
    get_linear_state_type,
)


class LinearAdapter(BaseAdapter[Task]):
    """Adapter for Linear issue tracking system using native GraphQL API.

    This adapter provides comprehensive integration with Linear's GraphQL API,
    supporting all major ticket management operations including:

    - CRUD operations for issues and projects
    - State transitions and workflow management
    - User assignment and search functionality
    - Comment management
    - Epic/Issue/Task hierarchy support

    The adapter is organized into multiple modules for better maintainability:
    - client.py: GraphQL client management
    - queries.py: GraphQL queries and fragments
    - types.py: Linear-specific types and mappings
    - mappers.py: Data transformation logic
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize Linear adapter.

        Args:
            config: Configuration with:
                - api_key: Linear API key (or LINEAR_API_KEY env var)
                - workspace: Linear workspace name (optional, for documentation)
                - team_key: Linear team key (e.g., 'BTA') OR
                - team_id: Linear team UUID (e.g., '02d15669-7351-4451-9719-807576c16049')
                - api_url: Optional Linear API URL (defaults to https://api.linear.app/graphql)

        Raises:
            ValueError: If required configuration is missing

        """
        # Initialize instance variables before calling super().__init__
        # because parent constructor calls _get_state_mapping()
        self._team_data: Optional[Dict[str, Any]] = None
        self._workflow_states: Optional[Dict[str, Dict[str, Any]]] = None
        self._labels_cache: Optional[List[Dict[str, Any]]] = None
        self._users_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._initialized = False

        super().__init__(config)

        # Extract configuration
        self.api_key = config.get("api_key") or os.getenv("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Linear API key is required (api_key or LINEAR_API_KEY env var)"
            )

        # Clean API key - remove Bearer prefix if accidentally included in config
        # (The client will add it back when making requests)
        if self.api_key.startswith("Bearer "):
            self.api_key = self.api_key.replace("Bearer ", "")

        self.workspace = config.get("workspace", "")
        self.team_key = config.get("team_key")
        self.team_id = config.get("team_id")
        self.api_url = config.get("api_url", "https://api.linear.app/graphql")

        # Validate team configuration
        if not self.team_key and not self.team_id:
            raise ValueError("Either team_key or team_id must be provided")

        # Initialize client with clean API key
        self.client = LinearGraphQLClient(self.api_key)

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate Linear API credentials.

        Returns:
            Tuple of (is_valid, error_message)

        """
        if not self.api_key:
            return False, "Linear API key is required"

        if not self.team_key and not self.team_id:
            return False, "Either team_key or team_id must be provided"

        return True, ""

    async def initialize(self) -> None:
        """Initialize adapter by preloading team, states, and labels data concurrently."""
        if self._initialized:
            return

        try:
            # Test connection first
            if not await self.client.test_connection():
                raise ValueError("Failed to connect to Linear API - check credentials")

            # Load team data and workflow states concurrently
            team_id = await self._ensure_team_id()

            # Load workflow states for the team
            await self._load_workflow_states(team_id)

            self._initialized = True

        except Exception as e:
            raise ValueError(f"Failed to initialize Linear adapter: {e}")

    async def _ensure_team_id(self) -> str:
        """Ensure we have a team ID, resolving from team_key if needed.

        Returns:
            Linear team UUID

        Raises:
            ValueError: If team cannot be found or resolved

        """
        if self.team_id:
            return self.team_id

        if not self.team_key:
            raise ValueError("Either team_id or team_key must be provided")

        # Query team by key
        query = """
            query GetTeamByKey($key: String!) {
                teams(filter: { key: { eq: $key } }) {
                    nodes {
                        id
                        name
                        key
                        description
                    }
                }
            }
        """

        try:
            result = await self.client.execute_query(query, {"key": self.team_key})
            teams = result.get("teams", {}).get("nodes", [])

            if not teams:
                raise ValueError(f"Team with key '{self.team_key}' not found")

            team = teams[0]
            self.team_id = team["id"]
            self._team_data = team

            return self.team_id

        except Exception as e:
            raise ValueError(f"Failed to resolve team '{self.team_key}': {e}")

    async def _load_workflow_states(self, team_id: str) -> None:
        """Load and cache workflow states for the team.

        Args:
            team_id: Linear team ID

        """
        try:
            result = await self.client.execute_query(
                WORKFLOW_STATES_QUERY, {"teamId": team_id}
            )

            workflow_states = {}
            for state in result["workflowStates"]["nodes"]:
                state_type = state["type"].lower()
                if state_type not in workflow_states:
                    workflow_states[state_type] = state
                elif state["position"] < workflow_states[state_type]["position"]:
                    workflow_states[state_type] = state

            self._workflow_states = workflow_states

        except Exception as e:
            raise ValueError(f"Failed to load workflow states: {e}")

    def _get_state_mapping(self) -> Dict[TicketState, str]:
        """Get mapping from universal states to Linear workflow state IDs.

        Returns:
            Dictionary mapping TicketState to Linear state ID

        """
        if not self._workflow_states:
            # Return type-based mapping if states not loaded
            return {
                TicketState.OPEN: "unstarted",
                TicketState.IN_PROGRESS: "started",
                TicketState.READY: "unstarted",
                TicketState.TESTED: "started",
                TicketState.DONE: "completed",
                TicketState.CLOSED: "canceled",
                TicketState.WAITING: "unstarted",
                TicketState.BLOCKED: "unstarted",
            }

        # Return ID-based mapping using cached workflow states
        mapping = {}
        for universal_state, linear_type in LinearStateMapping.TO_LINEAR.items():
            if linear_type in self._workflow_states:
                mapping[universal_state] = self._workflow_states[linear_type]["id"]
            else:
                # Fallback to type name
                mapping[universal_state] = linear_type

        return mapping

    async def _get_user_id(self, user_identifier: str) -> Optional[str]:
        """Get Linear user ID from email or display name.

        Args:
            user_identifier: Email address or display name

        Returns:
            Linear user ID or None if not found

        """
        # Try to get user by email first
        user = await self.client.get_user_by_email(user_identifier)
        if user:
            return user["id"]

        # If not found by email, could implement search by display name
        # For now, assume the identifier is already a user ID
        return user_identifier if user_identifier else None

    # CRUD Operations

    async def create(self, ticket: Union[Epic, Task]) -> Union[Epic, Task]:
        """Create a new Linear issue or project with full field support.

        Args:
            ticket: Epic or Task to create

        Returns:
            Created ticket with populated ID and metadata

        Raises:
            ValueError: If credentials are invalid or creation fails

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Ensure adapter is initialized
        await self.initialize()

        # Handle Epic creation (Linear Projects)
        if isinstance(ticket, Epic):
            return await self._create_epic(ticket)

        # Handle Task creation (Linear Issues)
        return await self._create_task(ticket)

    async def _create_task(self, task: Task) -> Task:
        """Create a Linear issue from a Task.

        Args:
            task: Task to create

        Returns:
            Created task with Linear metadata

        """
        team_id = await self._ensure_team_id()

        # Build issue input using mapper
        issue_input = build_linear_issue_input(task, team_id)

        # Resolve assignee to user ID if provided
        if task.assignee:
            user_id = await self._get_user_id(task.assignee)
            if user_id:
                issue_input["assigneeId"] = user_id

        try:
            result = await self.client.execute_mutation(
                CREATE_ISSUE_MUTATION, {"input": issue_input}
            )

            if not result["issueCreate"]["success"]:
                raise ValueError("Failed to create Linear issue")

            created_issue = result["issueCreate"]["issue"]
            return map_linear_issue_to_task(created_issue)

        except Exception as e:
            raise ValueError(f"Failed to create Linear issue: {e}")

    async def _create_epic(self, epic: Epic) -> Epic:
        """Create a Linear project from an Epic.

        Args:
            epic: Epic to create

        Returns:
            Created epic with Linear metadata

        """
        team_id = await self._ensure_team_id()

        project_input = {
            "name": epic.title,
            "teamIds": [team_id],
        }

        if epic.description:
            project_input["description"] = epic.description

        # Create project mutation
        create_query = """
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
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
                                id
                                name
                                key
                                description
                            }
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_mutation(
                create_query, {"input": project_input}
            )

            if not result["projectCreate"]["success"]:
                raise ValueError("Failed to create Linear project")

            created_project = result["projectCreate"]["project"]
            return map_linear_project_to_epic(created_project)

        except Exception as e:
            raise ValueError(f"Failed to create Linear project: {e}")

    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read a Linear issue by identifier with full details.

        Args:
            ticket_id: Linear issue identifier (e.g., 'BTA-123')

        Returns:
            Task with full details or None if not found

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        query = (
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
            result = await self.client.execute_query(query, {"identifier": ticket_id})

            if result.get("issue"):
                return map_linear_issue_to_task(result["issue"])

        except TransportQueryError:
            # Issue not found
            pass

        return None

    async def update(self, ticket_id: str, updates: Dict[str, Any]) -> Optional[Task]:
        """Update a Linear issue with comprehensive field support.

        Args:
            ticket_id: Linear issue identifier
            updates: Dictionary of fields to update

        Returns:
            Updated task or None if not found

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # First get the Linear internal ID
        id_query = """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """

        try:
            result = await self.client.execute_query(
                id_query, {"identifier": ticket_id}
            )

            if not result.get("issue"):
                return None

            linear_id = result["issue"]["id"]

            # Build update input using mapper
            update_input = build_linear_issue_update_input(updates)

            # Handle state transitions
            if "state" in updates:
                target_state = (
                    TicketState(updates["state"])
                    if isinstance(updates["state"], str)
                    else updates["state"]
                )
                state_mapping = self._get_state_mapping()
                if target_state in state_mapping:
                    update_input["stateId"] = state_mapping[target_state]

            # Resolve assignee to user ID if provided
            if "assignee" in updates and updates["assignee"]:
                user_id = await self._get_user_id(updates["assignee"])
                if user_id:
                    update_input["assigneeId"] = user_id

            # Execute update
            result = await self.client.execute_mutation(
                UPDATE_ISSUE_MUTATION, {"id": linear_id, "input": update_input}
            )

            if not result["issueUpdate"]["success"]:
                raise ValueError("Failed to update Linear issue")

            updated_issue = result["issueUpdate"]["issue"]
            return map_linear_issue_to_task(updated_issue)

        except Exception as e:
            raise ValueError(f"Failed to update Linear issue: {e}")

    async def delete(self, ticket_id: str) -> bool:
        """Delete a Linear issue (archive it).

        Args:
            ticket_id: Linear issue identifier

        Returns:
            True if successfully deleted/archived

        """
        # Linear doesn't support true deletion, so we archive the issue
        try:
            result = await self.update(ticket_id, {"archived": True})
            return result is not None
        except Exception:
            return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[Dict[str, Any]] = None
    ) -> List[Task]:
        """List Linear issues with optional filtering.

        Args:
            limit: Maximum number of issues to return
            offset: Number of issues to skip (Note: Linear uses cursor-based pagination)
            filters: Optional filters (state, assignee, priority, etc.)

        Returns:
            List of tasks matching the criteria

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Build issue filter
        issue_filter = build_issue_filter(
            team_id=team_id,
            state=filters.get("state") if filters else None,
            priority=filters.get("priority") if filters else None,
            include_archived=(
                filters.get("includeArchived", False) if filters else False
            ),
        )

        # Add additional filters
        if filters:
            if "assignee" in filters:
                user_id = await self._get_user_id(filters["assignee"])
                if user_id:
                    issue_filter["assignee"] = {"id": {"eq": user_id}}

            if "created_after" in filters:
                issue_filter["createdAt"] = {"gte": filters["created_after"]}
            if "updated_after" in filters:
                issue_filter["updatedAt"] = {"gte": filters["updated_after"]}
            if "due_before" in filters:
                issue_filter["dueDate"] = {"lte": filters["due_before"]}

        try:
            result = await self.client.execute_query(
                LIST_ISSUES_QUERY, {"filter": issue_filter, "first": limit}
            )

            tasks = []
            for issue in result["issues"]["nodes"]:
                tasks.append(map_linear_issue_to_task(issue))

            return tasks

        except Exception as e:
            raise ValueError(f"Failed to list Linear issues: {e}")

    async def search(self, query: SearchQuery) -> List[Task]:
        """Search Linear issues using comprehensive filters.

        Args:
            query: Search query with filters and criteria

        Returns:
            List of tasks matching the search criteria

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()
        team_id = await self._ensure_team_id()

        # Build comprehensive issue filter
        issue_filter = {"team": {"id": {"eq": team_id}}}

        # Text search (Linear supports full-text search)
        if query.query:
            # Linear's search is quite sophisticated, but we'll use a simple approach
            # In practice, you might want to use Linear's search API endpoint
            issue_filter["title"] = {"containsIgnoreCase": query.query}

        # State filter
        if query.state:
            state_type = get_linear_state_type(query.state)
            issue_filter["state"] = {"type": {"eq": state_type}}

        # Priority filter
        if query.priority:
            linear_priority = get_linear_priority(query.priority)
            issue_filter["priority"] = {"eq": linear_priority}

        # Assignee filter
        if query.assignee:
            user_id = await self._get_user_id(query.assignee)
            if user_id:
                issue_filter["assignee"] = {"id": {"eq": user_id}}

        # Tags filter (labels in Linear)
        if query.tags:
            issue_filter["labels"] = {"some": {"name": {"in": query.tags}}}

        # Exclude archived by default
        issue_filter["archivedAt"] = {"null": True}

        try:
            result = await self.client.execute_query(
                SEARCH_ISSUES_QUERY, {"filter": issue_filter, "first": query.limit}
            )

            tasks = []
            for issue in result["issues"]["nodes"]:
                tasks.append(map_linear_issue_to_task(issue))

            return tasks

        except Exception as e:
            raise ValueError(f"Failed to search Linear issues: {e}")

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Task]:
        """Transition Linear issue to new state with workflow validation.

        Args:
            ticket_id: Linear issue identifier
            target_state: Target state to transition to

        Returns:
            Updated task or None if transition failed

        """
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def validate_transition(
        self, ticket_id: str, target_state: TicketState
    ) -> bool:
        """Validate if state transition is allowed.

        Args:
            ticket_id: Linear issue identifier
            target_state: Target state to validate

        Returns:
            True if transition is valid

        """
        # For now, allow all transitions
        # In practice, you might want to implement Linear's workflow rules
        return True

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a Linear issue.

        Args:
            comment: Comment to add

        Returns:
            Created comment with ID

        """
        # First get the Linear internal ID
        id_query = """
            query GetIssueId($identifier: String!) {
                issue(id: $identifier) {
                    id
                }
            }
        """

        try:
            result = await self.client.execute_query(
                id_query, {"identifier": comment.ticket_id}
            )

            if not result.get("issue"):
                raise ValueError(f"Issue {comment.ticket_id} not found")

            linear_id = result["issue"]["id"]

            # Create comment mutation
            create_comment_query = """
                mutation CreateComment($input: CommentCreateInput!) {
                    commentCreate(input: $input) {
                        success
                        comment {
                            id
                            body
                            createdAt
                            updatedAt
                            user {
                                id
                                name
                                email
                                displayName
                            }
                        }
                    }
                }
            """

            comment_input = {
                "issueId": linear_id,
                "body": comment.body,
            }

            result = await self.client.execute_mutation(
                create_comment_query, {"input": comment_input}
            )

            if not result["commentCreate"]["success"]:
                raise ValueError("Failed to create comment")

            created_comment = result["commentCreate"]["comment"]
            return map_linear_comment_to_comment(created_comment, comment.ticket_id)

        except Exception as e:
            raise ValueError(f"Failed to add comment: {e}")

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> List[Comment]:
        """Get comments for a Linear issue.

        Args:
            ticket_id: Linear issue identifier
            limit: Maximum number of comments to return
            offset: Number of comments to skip

        Returns:
            List of comments for the issue

        """
        query = """
            query GetIssueComments($identifier: String!, $first: Int!) {
                issue(id: $identifier) {
                    comments(first: $first) {
                        nodes {
                            id
                            body
                            createdAt
                            updatedAt
                            user {
                                id
                                name
                                email
                                displayName
                                avatarUrl
                            }
                            parent {
                                id
                            }
                        }
                    }
                }
            }
        """

        try:
            result = await self.client.execute_query(
                query, {"identifier": ticket_id, "first": limit}
            )

            if not result.get("issue"):
                return []

            comments = []
            for comment_data in result["issue"]["comments"]["nodes"]:
                comments.append(map_linear_comment_to_comment(comment_data, ticket_id))

            return comments

        except Exception:
            return []

    async def close(self) -> None:
        """Close the adapter and clean up resources."""
        await self.client.close()


# Register the adapter
AdapterRegistry.register("linear", LinearAdapter)
