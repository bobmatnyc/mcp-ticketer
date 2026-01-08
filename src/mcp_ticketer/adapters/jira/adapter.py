"""JIRA adapter implementation using REST API v3."""

from __future__ import annotations

import builtins
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Union

from httpx import HTTPStatusError

from ...core.adapter import BaseAdapter
from ...core.env_loader import load_adapter_config, validate_adapter_config
from ...core.models import (
    Attachment,
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)
from ...core.registry import AdapterRegistry
from .client import JiraClient
from .mappers import (
    issue_to_ticket,
    map_epic_update_fields,
    map_update_fields,
    ticket_to_issue_fields,
)
from .queries import (
    build_epic_list_jql,
    build_list_jql,
    build_project_labels_jql,
    build_search_jql,
    get_labels_search_params,
    get_search_params,
)
from .types import (
    extract_text_from_adf,
    get_state_mapping,
    parse_jira_datetime,
)

logger = logging.getLogger(__name__)


class JiraAdapter(BaseAdapter[Union[Epic, Task]]):
    """Adapter for JIRA using REST API v3."""

    def __init__(self, config: dict[str, Any]):
        """Initialize JIRA adapter.

        Args:
        ----
            config: Configuration with:
                - server: JIRA server URL (e.g., https://company.atlassian.net)
                - email: User email for authentication
                - api_token: API token for authentication
                - project_key: Default project key
                - cloud: Whether this is JIRA Cloud (default: True)
                - verify_ssl: Whether to verify SSL certificates (default: True)
                - timeout: Request timeout in seconds (default: 30)
                - max_retries: Maximum retry attempts (default: 3)

        """
        super().__init__(config)

        # Load configuration with environment variable resolution
        full_config = load_adapter_config("jira", config)

        # Validate required configuration
        missing_keys = validate_adapter_config("jira", full_config)
        if missing_keys:
            raise ValueError(
                f"JIRA adapter missing required configuration: {', '.join(missing_keys)}"
            )

        # Configuration
        self.server = full_config.get("server", "").rstrip("/")
        self.email = full_config.get("email", "")
        self.api_token = full_config.get("api_token", "")
        self.project_key = full_config.get("project_key", "")
        self.is_cloud = full_config.get("cloud", True)
        self.verify_ssl = full_config.get("verify_ssl", True)
        self.timeout = full_config.get("timeout", 30)
        self.max_retries = full_config.get("max_retries", 3)

        # Initialize HTTP client
        self.client = JiraClient(
            server=self.server,
            email=self.email,
            api_token=self.api_token,
            is_cloud=self.is_cloud,
            verify_ssl=self.verify_ssl,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )

        # Cache for workflow states and transitions
        self._workflow_cache: dict[str, Any] = {}
        self._priority_cache: list[dict[str, Any]] = []
        self._issue_types_cache: dict[str, Any] = {}
        self._custom_fields_cache: dict[str, Any] = {}

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
        -------
            (is_valid, error_message) - Tuple of validation result and error message

        """
        if not self.server:
            return (
                False,
                "JIRA_SERVER is required but not found. Set it in .env.local or environment.",
            )
        if not self.email:
            return (
                False,
                "JIRA_EMAIL is required but not found. Set it in .env.local or environment.",
            )
        if not self.api_token:
            return (
                False,
                "JIRA_API_TOKEN is required but not found. Set it in .env.local or environment.",
            )
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Map universal states to common JIRA workflow states."""
        return get_state_mapping()

    async def _get_priorities(self) -> list[dict[str, Any]]:
        """Get available priorities from JIRA."""
        if not self._priority_cache:
            self._priority_cache = await self.client.get("priority")
        return self._priority_cache

    async def _get_issue_types(
        self, project_key: str | None = None
    ) -> list[dict[str, Any]]:
        """Get available issue types for a project."""
        key = project_key or self.project_key
        if key not in self._issue_types_cache:
            data = await self.client.get(f"project/{key}")
            self._issue_types_cache[key] = data.get("issueTypes", [])
        return self._issue_types_cache[key]

    async def _get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue."""
        data = await self.client.get(f"issue/{issue_key}/transitions")
        return data.get("transitions", [])

    async def _get_custom_fields(self) -> dict[str, str]:
        """Get custom field definitions."""
        if not self._custom_fields_cache:
            fields = await self.client.get("field")
            self._custom_fields_cache = {
                field["name"]: field["id"]
                for field in fields
                if field.get("custom", False)
            }
        return self._custom_fields_cache

    async def create(self, ticket: Epic | Task) -> Epic | Task:
        """Create a new JIRA issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Prepare issue fields
        fields = ticket_to_issue_fields(
            ticket,
            is_cloud=self.is_cloud,
            project_key=self.project_key,
        )

        # Create issue
        data = await self.client.post("issue", data={"fields": fields})

        # Set the ID and fetch full issue data
        ticket.id = data.get("key")

        # Fetch complete issue data
        created_issue = await self.client.get(f"issue/{ticket.id}")
        return issue_to_ticket(created_issue, self.server)

    async def read(self, ticket_id: str) -> Epic | Task | None:
        """Read a JIRA issue by key."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue = await self.client.get(
                f"issue/{ticket_id}", params={"expand": "renderedFields"}
            )
            return issue_to_ticket(issue, self.server)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def update(
        self, ticket_id: str, updates: dict[str, Any]
    ) -> Epic | Task | None:
        """Update a JIRA issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Read current issue
        current = await self.read(ticket_id)
        if not current:
            return None

        # Prepare update fields
        fields = map_update_fields(updates, is_cloud=self.is_cloud)

        # Apply update
        if fields:
            await self.client.put(f"issue/{ticket_id}", data={"fields": fields})

        # Handle state transitions separately
        if "state" in updates:
            await self.transition_state(ticket_id, updates["state"])

        # Return updated issue
        return await self.read(ticket_id)

    async def delete(self, ticket_id: str) -> bool:
        """Delete a JIRA issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            await self.client.delete(f"issue/{ticket_id}")
            return True
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[Epic | Task]:
        """List JIRA issues with pagination."""
        # Build JQL query
        jql = build_list_jql(
            self.project_key,
            filters=filters,
            state_mapper=self.map_state_to_system,
        )

        # Search issues using the JIRA API endpoint
        params = get_search_params(jql, start_at=offset, max_results=limit)
        data = await self.client.get("search/jql", params=params)

        # Convert issues
        issues = data.get("issues", [])
        return [issue_to_ticket(issue, self.server) for issue in issues]

    async def search(self, query: SearchQuery) -> builtins.list[Epic | Task]:
        """Search JIRA issues using JQL."""
        # Build JQL query
        jql = build_search_jql(
            self.project_key,
            query,
            state_mapper=self.map_state_to_system,
        )

        # Execute search using the JIRA API endpoint
        params = get_search_params(
            jql,
            start_at=query.offset,
            max_results=query.limit,
        )
        data = await self.client.get("search/jql", params=params)

        # Convert and return results
        issues = data.get("issues", [])
        return [issue_to_ticket(issue, self.server) for issue in issues]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Epic | Task | None:
        """Transition JIRA issue to a new state."""
        # Get available transitions
        transitions = await self._get_transitions(ticket_id)

        # Find matching transition
        target_name = self.map_state_to_system(target_state).lower()
        transition = None

        for trans in transitions:
            trans_name = trans.get("to", {}).get("name", "").lower()
            if target_name in trans_name or trans_name in target_name:
                transition = trans
                break

        if not transition:
            # Try to find by status category
            for trans in transitions:
                category = (
                    trans.get("to", {}).get("statusCategory", {}).get("key", "").lower()
                )
                if (
                    (target_state == TicketState.DONE and category == "done")
                    or (
                        target_state == TicketState.IN_PROGRESS
                        and category == "indeterminate"
                    )
                    or (target_state == TicketState.OPEN and category == "new")
                ):
                    transition = trans
                    break

        if not transition:
            logger.warning(
                f"No transition found to move {ticket_id} to {target_state}. "
                f"Available transitions: {[t.get('name') for t in transitions]}"
            )
            return None

        # Execute transition
        await self.client.post(
            f"issue/{ticket_id}/transitions",
            data={"transition": {"id": transition["id"]}},
        )

        # Return updated issue
        return await self.read(ticket_id)

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a JIRA issue."""
        # Prepare comment data in Atlassian Document Format
        data = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": comment.content}],
                    }
                ],
            }
        }

        # Add comment
        result = await self.client.post(f"issue/{comment.ticket_id}/comment", data=data)

        # Update comment with JIRA data
        comment.id = result.get("id")
        comment.created_at = (
            parse_jira_datetime(result.get("created")) or datetime.now()
        )
        comment.author = result.get("author", {}).get("displayName", comment.author)
        comment.metadata["jira"] = result

        return comment

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a JIRA issue."""
        # Fetch issue with comments
        params = {"expand": "comments", "fields": "comment"}

        issue = await self.client.get(f"issue/{ticket_id}", params=params)

        # Extract comments
        comments_data = issue.get("fields", {}).get("comment", {}).get("comments", [])

        # Apply pagination
        paginated = comments_data[offset : offset + limit]

        # Convert to Comment objects
        comments = []
        for comment_data in paginated:
            # Extract text content from ADF format
            body_content = comment_data.get("body", "")
            text_content = extract_text_from_adf(body_content)

            comment = Comment(
                id=comment_data.get("id"),
                ticket_id=ticket_id,
                author=comment_data.get("author", {}).get("displayName", "Unknown"),
                content=text_content,
                created_at=parse_jira_datetime(comment_data.get("created")),
                metadata={"jira": comment_data},
            )
            comments.append(comment)

        return comments

    async def get_project_info(self, project_key: str | None = None) -> dict[str, Any]:
        """Get JIRA project information including workflows and fields."""
        key = project_key or self.project_key
        if not key:
            raise ValueError("Project key is required")

        project = await self.client.get(f"project/{key}")

        # Get additional project details
        issue_types = await self._get_issue_types(key)
        priorities = await self._get_priorities()
        custom_fields = await self._get_custom_fields()

        return {
            "project": project,
            "issue_types": issue_types,
            "priorities": priorities,
            "custom_fields": custom_fields,
        }

    async def execute_jql(
        self, jql: str, limit: int = 50
    ) -> builtins.list[Epic | Task]:
        """Execute a raw JQL query.

        Args:
        ----
            jql: JIRA Query Language string
            limit: Maximum number of results

        Returns:
        -------
            List of matching tickets

        """
        data = await self.client.post(
            "search",
            data={
                "jql": jql,
                "startAt": 0,
                "maxResults": limit,
                "fields": ["*all"],
            },
        )

        issues = data.get("issues", [])
        return [issue_to_ticket(issue, self.server) for issue in issues]

    async def get_sprints(
        self, board_id: int | None = None
    ) -> builtins.list[dict[str, Any]]:
        """Get active sprints for a board (requires JIRA Software).

        Args:
        ----
            board_id: Agile board ID

        Returns:
        -------
            List of sprint information

        """
        if not board_id:
            # Try to find a board for the project
            boards_data = await self.client.get(
                "/rest/agile/1.0/board",
                params={"projectKeyOrId": self.project_key},
            )
            boards = boards_data.get("values", [])
            if not boards:
                return []
            board_id = boards[0]["id"]

        # Get sprints for the board
        sprints_data = await self.client.get(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": "active,future"},
        )

        return sprints_data.get("values", [])

    async def get_project_users(self) -> builtins.list[dict[str, Any]]:
        """Get users who have access to the project."""
        if not self.project_key:
            return []

        try:
            # Get project role users
            project_data = await self.client.get(f"project/{self.project_key}")

            # Get users from project roles
            users = []
            if "roles" in project_data:
                for _role_name, role_url in project_data["roles"].items():
                    # Extract role ID from URL
                    role_id = role_url.split("/")[-1]
                    try:
                        role_data = await self.client.get(
                            f"project/{self.project_key}/role/{role_id}"
                        )
                        if "actors" in role_data:
                            for actor in role_data["actors"]:
                                if actor.get("type") == "atlassian-user-role-actor":
                                    users.append(actor.get("actorUser", {}))
                    except Exception:
                        # Skip if role access fails
                        continue

            # Remove duplicates based on accountId
            seen_ids = set()
            unique_users = []
            for user in users:
                account_id = user.get("accountId")
                if account_id and account_id not in seen_ids:
                    seen_ids.add(account_id)
                    unique_users.append(user)

            return unique_users

        except Exception:
            # Fallback: try to get assignable users for the project
            try:
                users_data = await self.client.get(
                    "user/assignable/search",
                    params={"project": self.project_key, "maxResults": 50},
                )
                return users_data if isinstance(users_data, list) else []
            except Exception:
                return []

    async def get_current_user(self) -> dict[str, Any] | None:
        """Get current authenticated user information."""
        try:
            return await self.client.get("myself")
        except Exception:
            return None

    async def list_labels(self) -> builtins.list[dict[str, Any]]:
        """List all labels used in the project.

        JIRA doesn't have a direct "list all labels" endpoint, so we query
        recent issues and extract unique labels from them.

        Returns:
        -------
            List of label dictionaries with 'id' and 'name' fields

        """
        try:
            # Query recent issues to get labels in use
            jql = f"project = {self.project_key} ORDER BY updated DESC"
            params = get_labels_search_params(jql, max_results=100)
            data = await self.client.get("search/jql", params=params)

            # Collect unique labels
            unique_labels = set()
            for issue in data.get("issues", []):
                labels = issue.get("fields", {}).get("labels", [])
                for label in labels:
                    if isinstance(label, dict):
                        unique_labels.add(label.get("name", ""))
                    else:
                        unique_labels.add(str(label))

            # Transform to standardized format
            return [
                {"id": label, "name": label} for label in sorted(unique_labels) if label
            ]

        except Exception:
            # Fallback: return empty list if query fails
            return []

    async def create_issue_label(
        self, name: str, color: str | None = None
    ) -> dict[str, Any]:
        """Create a new issue label in JIRA.

        Note: JIRA doesn't have a dedicated label creation API. Labels are
        created automatically when first used on an issue. This method
        validates the label name and returns a success response.

        Args:
        ----
            name: Label name to create
            color: Optional color (JIRA doesn't support colors natively, ignored)

        Returns:
        -------
            Dict with label details:
                - id: Label name (same as name in JIRA)
                - name: Label name
                - status: "ready" indicating the label can be used

        Raises:
        ------
            ValueError: If credentials are invalid or label name is invalid

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Validate label name
        if not name or not name.strip():
            raise ValueError("Label name cannot be empty")

        # JIRA label names must not contain spaces
        if " " in name:
            raise ValueError(
                "JIRA label names cannot contain spaces. Use underscores or hyphens instead."
            )

        # Return success response
        # The label will be created automatically when first used on an issue
        return {"id": name, "name": name, "status": "ready"}

    async def list_project_labels(
        self, project_key: str | None = None, limit: int = 100
    ) -> builtins.list[dict[str, Any]]:
        """List all labels used in a JIRA project.

        JIRA doesn't have a dedicated endpoint for listing project labels.
        This method queries recent issues and extracts unique labels.

        Args:
        ----
            project_key: JIRA project key (e.g., 'PROJ'). If None, uses configured project.
            limit: Maximum number of labels to return (default: 100)

        Returns:
        -------
            List of label dictionaries with 'id', 'name', and 'usage_count' fields

        Raises:
        ------
            ValueError: If credentials are invalid or project key not available

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Use configured project if not specified
        key = project_key or self.project_key
        if not key:
            raise ValueError("Project key is required")

        try:
            # Query recent issues to get labels in use
            jql = build_project_labels_jql(key, max_results=500)
            params = get_labels_search_params(jql, max_results=500)
            data = await self.client.get("search/jql", params=params)

            # Collect labels with usage count
            label_counts: dict[str, int] = {}
            for issue in data.get("issues", []):
                labels = issue.get("fields", {}).get("labels", [])
                for label in labels:
                    label_name = (
                        label.get("name", "") if isinstance(label, dict) else str(label)
                    )
                    if label_name:
                        label_counts[label_name] = label_counts.get(label_name, 0) + 1

            # Transform to standardized format with usage counts
            result = [
                {"id": label, "name": label, "usage_count": count}
                for label, count in sorted(
                    label_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]

            return result[:limit]

        except Exception as e:
            logger.error(f"Failed to list project labels: {e}")
            raise ValueError(f"Failed to list project labels: {e}") from e

    async def list_cycles(
        self, board_id: str | None = None, state: str | None = None, limit: int = 50
    ) -> builtins.list[dict[str, Any]]:
        """List JIRA sprints (cycles) for a board.

        Requires JIRA Agile/Software. Falls back to empty list if not available.

        Args:
        ----
            board_id: JIRA Agile board ID. If None, finds first board for project.
            state: Filter by state ('active', 'closed', 'future'). If None, returns all.
            limit: Maximum number of sprints to return (default: 50)

        Returns:
        -------
            List of sprint dictionaries with fields:
                - id: Sprint ID
                - name: Sprint name
                - state: Sprint state (active, closed, future)
                - startDate: Start date (ISO format)
                - endDate: End date (ISO format)
                - completeDate: Completion date (ISO format, None if not completed)
                - goal: Sprint goal

        Raises:
        ------
            ValueError: If credentials are invalid

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # If no board_id provided, try to find a board for the project
            if not board_id:
                boards_data = await self.client.get(
                    "/rest/agile/1.0/board",
                    params={"projectKeyOrId": self.project_key, "maxResults": 1},
                )
                boards = boards_data.get("values", [])
                if not boards:
                    logger.warning(
                        f"No Agile boards found for project {self.project_key}"
                    )
                    return []
                board_id = str(boards[0]["id"])

            # Get sprints for the board
            params = {"maxResults": limit}
            if state:
                params["state"] = state

            sprints_data = await self.client.get(
                f"/rest/agile/1.0/board/{board_id}/sprint", params=params
            )

            sprints = sprints_data.get("values", [])

            # Transform to standardized format
            return [
                {
                    "id": sprint.get("id"),
                    "name": sprint.get("name"),
                    "state": sprint.get("state"),
                    "startDate": sprint.get("startDate"),
                    "endDate": sprint.get("endDate"),
                    "completeDate": sprint.get("completeDate"),
                    "goal": sprint.get("goal", ""),
                }
                for sprint in sprints
            ]

        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning("JIRA Agile API not available (404)")
                return []
            logger.error(f"Failed to list sprints: {e}")
            raise ValueError(f"Failed to list sprints: {e}") from e
        except Exception as e:
            logger.warning(f"JIRA Agile may not be available: {e}")
            return []

    async def list_issue_statuses(
        self, project_key: str | None = None
    ) -> builtins.list[dict[str, Any]]:
        """List all workflow statuses in JIRA.

        Args:
        ----
            project_key: Optional project key to filter statuses.
                        If None, returns all statuses.

        Returns:
        -------
            List of status dictionaries with fields:
                - id: Status ID
                - name: Status name (e.g., "To Do", "In Progress", "Done")
                - category: Status category key (e.g., "new", "indeterminate", "done")
                - categoryName: Human-readable category name
                - description: Status description

        Raises:
        ------
            ValueError: If credentials are invalid

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Use project-specific statuses if project key provided
            if project_key:
                # Get statuses for the project
                data = await self.client.get(f"project/{project_key}/statuses")

                # Extract unique statuses from all issue types
                status_map: dict[str, dict[str, Any]] = {}
                for issue_type_data in data:
                    for status in issue_type_data.get("statuses", []):
                        status_id = status.get("id")
                        if status_id not in status_map:
                            status_map[status_id] = status

                statuses = list(status_map.values())
            else:
                # Get all statuses
                statuses = await self.client.get("status")

            # Transform to standardized format
            return [
                {
                    "id": status.get("id"),
                    "name": status.get("name"),
                    "category": status.get("statusCategory", {}).get("key", ""),
                    "categoryName": status.get("statusCategory", {}).get("name", ""),
                    "description": status.get("description", ""),
                }
                for status in statuses
            ]

        except Exception as e:
            logger.error(f"Failed to list issue statuses: {e}")
            raise ValueError(f"Failed to list issue statuses: {e}") from e

    async def get_issue_status(self, issue_key: str) -> dict[str, Any] | None:
        """Get rich status information for an issue.

        Args:
        ----
            issue_key: JIRA issue key (e.g., 'PROJ-123')

        Returns:
        -------
            Dict with status details and available transitions:
                - id: Status ID
                - name: Status name
                - category: Status category key
                - categoryName: Human-readable category name
                - description: Status description
                - transitions: List of available transitions with:
                    - id: Transition ID
                    - name: Transition name
                    - to: Target status info (id, name, category)
            Returns None if issue not found.

        Raises:
        ------
            ValueError: If credentials are invalid

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Get issue with status field
            issue = await self.client.get(
                f"issue/{issue_key}", params={"fields": "status"}
            )

            if not issue:
                return None

            status = issue.get("fields", {}).get("status", {})

            # Get available transitions
            transitions_data = await self.client.get(f"issue/{issue_key}/transitions")
            transitions = transitions_data.get("transitions", [])

            # Transform transitions to simplified format
            transition_list = [
                {
                    "id": trans.get("id"),
                    "name": trans.get("name"),
                    "to": {
                        "id": trans.get("to", {}).get("id"),
                        "name": trans.get("to", {}).get("name"),
                        "category": trans.get("to", {})
                        .get("statusCategory", {})
                        .get("key", ""),
                    },
                }
                for trans in transitions
            ]

            return {
                "id": status.get("id"),
                "name": status.get("name"),
                "category": status.get("statusCategory", {}).get("key", ""),
                "categoryName": status.get("statusCategory", {}).get("name", ""),
                "description": status.get("description", ""),
                "transitions": transition_list,
            }

        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get issue status: {e}")
            raise ValueError(f"Failed to get issue status: {e}") from e
        except Exception as e:
            logger.error(f"Failed to get issue status: {e}")
            raise ValueError(f"Failed to get issue status: {e}") from e

    async def create_epic(
        self,
        title: str,
        description: str = "",
        priority: Priority = Priority.MEDIUM,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> Epic:
        """Create a new JIRA Epic.

        Args:
        ----
            title: Epic title
            description: Epic description
            priority: Priority level
            tags: List of labels
            **kwargs: Additional fields (reserved for future use)

        Returns:
        -------
            Created Epic with ID populated

        Raises:
        ------
            ValueError: If credentials are invalid or creation fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Build epic input
        epic = Epic(
            id="",  # Will be populated by JIRA
            title=title,
            description=description,
            priority=priority,
            tags=tags or [],
            state=TicketState.OPEN,
        )

        # Create using base create method with Epic type
        created_epic = await self.create(epic)

        if not isinstance(created_epic, Epic):
            raise ValueError("Created ticket is not an Epic")

        return created_epic

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get a JIRA Epic by key or ID.

        Args:
        ----
            epic_id: Epic identifier (key like PROJ-123)

        Returns:
        -------
            Epic object if found and is an Epic type, None otherwise

        Raises:
        ------
            ValueError: If credentials are invalid

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Read issue
        ticket = await self.read(epic_id)

        if not ticket:
            return None

        # Verify it's an Epic
        if not isinstance(ticket, Epic):
            return None

        return ticket

    async def list_epics(
        self, limit: int = 50, offset: int = 0, state: str | None = None, **kwargs: Any
    ) -> builtins.list[Epic]:
        """List JIRA Epics with pagination.

        Args:
        ----
            limit: Maximum number of epics to return (default: 50)
            offset: Number of epics to skip for pagination (default: 0)
            state: Filter by state/status name (e.g., "To Do", "In Progress", "Done")
            **kwargs: Additional filter parameters (reserved for future use)

        Returns:
        -------
            List of Epic objects

        Raises:
        ------
            ValueError: If credentials are invalid or query fails

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Build JQL query for epics
        jql = build_epic_list_jql(self.project_key, state=state)

        try:
            # Execute search
            params = get_search_params(jql, start_at=offset, max_results=limit)
            data = await self.client.get("search/jql", params=params)

            # Convert issues to tickets
            issues = data.get("issues", [])
            epics = []

            for issue in issues:
                ticket = issue_to_ticket(issue, self.server)
                # Only include if it's actually an Epic
                if isinstance(ticket, Epic):
                    epics.append(ticket)

            return epics

        except Exception as e:
            raise ValueError(f"Failed to list JIRA epics: {e}") from e

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update a JIRA Epic with epic-specific field handling.

        Args:
        ----
            epic_id: Epic identifier (key like PROJ-123 or ID)
            updates: Dictionary with fields to update:
                - title: Epic title (maps to summary)
                - description: Epic description (auto-converted to ADF)
                - state: TicketState value (transitions via workflow)
                - tags: List of labels
                - priority: Priority level

        Returns:
        -------
            Updated Epic object or None if not found

        Raises:
        ------
            ValueError: If no fields provided for update
            HTTPStatusError: If update fails

        """
        fields = map_epic_update_fields(updates)

        if not fields and "state" not in updates:
            raise ValueError("At least one field must be updated")

        # Apply field updates if any
        if fields:
            await self.client.put(f"issue/{epic_id}", data={"fields": fields})

        # Handle state transitions separately (JIRA uses workflow transitions)
        if "state" in updates:
            await self.transition_state(epic_id, updates["state"])

        # Fetch and return updated epic
        return await self.read(epic_id)

    async def add_attachment(
        self, ticket_id: str, file_path: str, description: str | None = None
    ) -> Attachment:
        """Attach file to JIRA issue (including Epic).

        Args:
        ----
            ticket_id: Issue key (e.g., PROJ-123) or ID
            file_path: Path to file to attach
            description: Optional description (stored in metadata, not used by JIRA directly)

        Returns:
        -------
            Attachment object with metadata

        Raises:
        ------
            FileNotFoundError: If file doesn't exist
            ValueError: If credentials invalid
            HTTPStatusError: If upload fails

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Upload file
        result = await self.client.upload_file(
            f"issue/{ticket_id}/attachments",
            str(file_path_obj),
            file_path_obj.name,
        )

        # JIRA returns array with single attachment
        attachment_data = result[0]

        return Attachment(
            id=attachment_data["id"],
            ticket_id=ticket_id,
            filename=attachment_data["filename"],
            url=attachment_data["content"],
            content_type=attachment_data["mimeType"],
            size_bytes=attachment_data["size"],
            created_at=parse_jira_datetime(attachment_data["created"]),
            created_by=attachment_data["author"]["displayName"],
            description=description,
            metadata={"jira": attachment_data},
        )

    async def get_attachments(self, ticket_id: str) -> builtins.list[Attachment]:
        """Get all attachments for a JIRA issue.

        Args:
        ----
            ticket_id: Issue key or ID

        Returns:
        -------
            List of Attachment objects

        Raises:
        ------
            ValueError: If credentials invalid
            HTTPStatusError: If request fails

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Fetch issue with attachment field
        issue = await self.client.get(
            f"issue/{ticket_id}", params={"fields": "attachment"}
        )

        attachments = []
        for att_data in issue.get("fields", {}).get("attachment", []):
            attachments.append(
                Attachment(
                    id=att_data["id"],
                    ticket_id=ticket_id,
                    filename=att_data["filename"],
                    url=att_data["content"],
                    content_type=att_data["mimeType"],
                    size_bytes=att_data["size"],
                    created_at=parse_jira_datetime(att_data["created"]),
                    created_by=att_data["author"]["displayName"],
                    metadata={"jira": att_data},
                )
            )

        return attachments

    async def delete_attachment(self, ticket_id: str, attachment_id: str) -> bool:
        """Delete an attachment from a JIRA issue.

        Args:
        ----
            ticket_id: Issue key or ID (for validation/context)
            attachment_id: Attachment ID to delete

        Returns:
        -------
            True if deleted successfully, False otherwise

        Raises:
        ------
            ValueError: If credentials invalid

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            await self.client.delete(f"attachment/{attachment_id}")
            return True
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Attachment {attachment_id} not found")
                return False
            logger.error(
                f"Failed to delete attachment {attachment_id}: {e.response.status_code} - {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting attachment {attachment_id}: {e}")
            return False

    async def close(self) -> None:
        """Close the adapter and cleanup resources."""
        # Clear caches
        self._workflow_cache.clear()
        self._priority_cache.clear()
        self._issue_types_cache.clear()
        self._custom_fields_cache.clear()

    # Milestone Methods (Not yet implemented)

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Any:
        """Create milestone - not yet implemented for Jira.

        Args:
        ----
            name: Milestone name
            target_date: Target completion date
            labels: Labels that define this milestone
            description: Milestone description
            project_id: Associated project ID

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def milestone_get(self, milestone_id: str) -> Any:
        """Get milestone - not yet implemented for Jira.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Any]:
        """List milestones - not yet implemented for Jira.

        Args:
        ----
            project_id: Filter by project
            state: Filter by state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Any:
        """Update milestone - not yet implemented for Jira.

        Args:
        ----
            milestone_id: Milestone identifier
            name: New name
            target_date: New target date
            state: New state
            labels: New labels
            description: New description

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete milestone - not yet implemented for Jira.

        Args:
        ----
            milestone_id: Milestone identifier

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> list[Any]:
        """Get milestone issues - not yet implemented for Jira.

        Args:
        ----
            milestone_id: Milestone identifier
            state: Filter by issue state

        Raises:
        ------
            NotImplementedError: Milestone support coming in v2.1.0

        """
        raise NotImplementedError("Milestone support for Jira coming in v2.1.0")

    async def search_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            Empty list (user search not yet implemented for Jira)

        Note:
        ----
            Jira user search API implementation pending.
            Returns empty list for now.

        """
        logger.info("search_users called but not yet implemented for Jira adapter")
        return []


# Register the adapter
AdapterRegistry.register("jira", JiraAdapter)
