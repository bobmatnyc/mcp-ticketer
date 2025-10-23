"""JIRA adapter implementation using REST API v3."""

import asyncio
import builtins
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union

import httpx
from httpx import AsyncClient, HTTPStatusError, TimeoutException

from ..core.adapter import BaseAdapter
from ..core.models import Comment, Epic, Priority, SearchQuery, Task, TicketState
from ..core.registry import AdapterRegistry

logger = logging.getLogger(__name__)


class JiraIssueType(str, Enum):
    """Common JIRA issue types."""

    EPIC = "Epic"
    STORY = "Story"
    TASK = "Task"
    BUG = "Bug"
    SUBTASK = "Sub-task"
    IMPROVEMENT = "Improvement"
    NEW_FEATURE = "New Feature"


class JiraPriority(str, Enum):
    """Standard JIRA priority levels."""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class JiraAdapter(BaseAdapter[Union[Epic, Task]]):
    """Adapter for JIRA using REST API v3."""

    def __init__(self, config: dict[str, Any]):
        """Initialize JIRA adapter.

        Args:
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

        # Configuration
        self.server = config.get("server") or os.getenv("JIRA_SERVER", "")
        self.email = config.get("email") or os.getenv("JIRA_EMAIL", "")
        self.api_token = config.get("api_token") or os.getenv("JIRA_API_TOKEN", "")
        self.project_key = config.get("project_key") or os.getenv(
            "JIRA_PROJECT_KEY", ""
        )
        self.is_cloud = config.get("cloud", True)
        self.verify_ssl = config.get("verify_ssl", True)
        self.timeout = config.get("timeout", 30)
        self.max_retries = config.get("max_retries", 3)

        # Validate required fields
        if not all([self.server, self.email, self.api_token]):
            raise ValueError("JIRA adapter requires server, email, and api_token")

        # Clean up server URL
        self.server = self.server.rstrip("/")

        # API base URL
        self.api_base = (
            f"{self.server}/rest/api/3"
            if self.is_cloud
            else f"{self.server}/rest/api/2"
        )

        # HTTP client setup
        self.auth = httpx.BasicAuth(self.email, self.api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # Cache for workflow states and transitions
        self._workflow_cache: dict[str, Any] = {}
        self._priority_cache: list[dict[str, Any]] = []
        self._issue_types_cache: dict[str, Any] = {}
        self._custom_fields_cache: dict[str, Any] = {}

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
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
        return {
            TicketState.OPEN: "To Do",
            TicketState.IN_PROGRESS: "In Progress",
            TicketState.READY: "In Review",
            TicketState.TESTED: "Testing",
            TicketState.DONE: "Done",
            TicketState.WAITING: "Waiting",
            TicketState.BLOCKED: "Blocked",
            TicketState.CLOSED: "Closed",
        }

    async def _get_client(self) -> AsyncClient:
        """Get configured async HTTP client."""
        return AsyncClient(
            auth=self.auth,
            headers=self.headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
        retry_count: int = 0,
    ) -> dict[str, Any]:
        """Make HTTP request to JIRA API with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            retry_count: Current retry attempt

        Returns:
            Response data

        Raises:
            HTTPStatusError: On API errors
            TimeoutException: On timeout

        """
        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        async with await self._get_client() as client:
            try:
                response = await client.request(
                    method=method, url=url, json=data, params=params
                )
                response.raise_for_status()

                # Handle empty responses
                if response.status_code == 204:
                    return {}

                return response.json()

            except TimeoutException as e:
                if retry_count < self.max_retries:
                    await asyncio.sleep(2**retry_count)  # Exponential backoff
                    return await self._make_request(
                        method, endpoint, data, params, retry_count + 1
                    )
                raise e

            except HTTPStatusError as e:
                # Handle rate limiting
                if e.response.status_code == 429 and retry_count < self.max_retries:
                    retry_after = int(e.response.headers.get("Retry-After", 5))
                    await asyncio.sleep(retry_after)
                    return await self._make_request(
                        method, endpoint, data, params, retry_count + 1
                    )

                # Log error details
                logger.error(
                    f"JIRA API error: {e.response.status_code} - {e.response.text}"
                )
                raise e

    async def _get_priorities(self) -> list[dict[str, Any]]:
        """Get available priorities from JIRA."""
        if not self._priority_cache:
            self._priority_cache = await self._make_request("GET", "priority")
        return self._priority_cache

    async def _get_issue_types(
        self, project_key: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """Get available issue types for a project."""
        key = project_key or self.project_key
        if key not in self._issue_types_cache:
            data = await self._make_request("GET", f"project/{key}")
            self._issue_types_cache[key] = data.get("issueTypes", [])
        return self._issue_types_cache[key]

    async def _get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Get available transitions for an issue."""
        data = await self._make_request("GET", f"issue/{issue_key}/transitions")
        return data.get("transitions", [])

    async def _get_custom_fields(self) -> dict[str, str]:
        """Get custom field definitions."""
        if not self._custom_fields_cache:
            fields = await self._make_request("GET", "field")
            self._custom_fields_cache = {
                field["name"]: field["id"]
                for field in fields
                if field.get("custom", False)
            }
        return self._custom_fields_cache

    def _convert_from_adf(self, adf_content: Any) -> str:
        """Convert Atlassian Document Format (ADF) to plain text.

        This extracts text content from ADF structure for display.
        """
        if not adf_content:
            return ""

        # If it's already a string, return it (JIRA Server)
        if isinstance(adf_content, str):
            return adf_content

        # Handle ADF structure
        if not isinstance(adf_content, dict):
            return str(adf_content)

        content_nodes = adf_content.get("content", [])
        lines = []

        for node in content_nodes:
            if node.get("type") == "paragraph":
                paragraph_text = ""
                for content_item in node.get("content", []):
                    if content_item.get("type") == "text":
                        paragraph_text += content_item.get("text", "")
                lines.append(paragraph_text)
            elif node.get("type") == "heading":
                heading_text = ""
                for content_item in node.get("content", []):
                    if content_item.get("type") == "text":
                        heading_text += content_item.get("text", "")
                lines.append(heading_text)

        return "\n".join(lines)

    def _convert_to_adf(self, text: str) -> dict[str, Any]:
        """Convert plain text to Atlassian Document Format (ADF).

        ADF is required for JIRA Cloud description fields.
        This creates a simple document with paragraphs for each line.
        """
        if not text:
            return {"type": "doc", "version": 1, "content": []}

        # Split text into lines and create paragraphs
        lines = text.split("\n")
        content = []

        for line in lines:
            if line.strip():  # Non-empty line
                content.append(
                    {"type": "paragraph", "content": [{"type": "text", "text": line}]}
                )
            else:  # Empty line becomes empty paragraph
                content.append({"type": "paragraph", "content": []})

        return {"type": "doc", "version": 1, "content": content}

    def _map_priority_to_jira(self, priority: Priority) -> str:
        """Map universal priority to JIRA priority."""
        mapping = {
            Priority.CRITICAL: JiraPriority.HIGHEST,
            Priority.HIGH: JiraPriority.HIGH,
            Priority.MEDIUM: JiraPriority.MEDIUM,
            Priority.LOW: JiraPriority.LOW,
        }
        return mapping.get(priority, JiraPriority.MEDIUM)

    def _map_priority_from_jira(
        self, jira_priority: Optional[dict[str, Any]]
    ) -> Priority:
        """Map JIRA priority to universal priority."""
        if not jira_priority:
            return Priority.MEDIUM

        name = jira_priority.get("name", "").lower()

        if "highest" in name or "urgent" in name or "critical" in name:
            return Priority.CRITICAL
        elif "high" in name:
            return Priority.HIGH
        elif "low" in name:
            return Priority.LOW
        else:
            return Priority.MEDIUM

    def _map_state_from_jira(self, status: dict[str, Any]) -> TicketState:
        """Map JIRA status to universal state."""
        if not status:
            return TicketState.OPEN

        name = status.get("name", "").lower()
        category = status.get("statusCategory", {}).get("key", "").lower()

        # Try to match by category first (more reliable)
        if category == "new":
            return TicketState.OPEN
        elif category == "indeterminate":
            return TicketState.IN_PROGRESS
        elif category == "done":
            return TicketState.DONE

        # Fall back to name matching
        if "block" in name:
            return TicketState.BLOCKED
        elif "wait" in name:
            return TicketState.WAITING
        elif "progress" in name or "doing" in name:
            return TicketState.IN_PROGRESS
        elif "review" in name:
            return TicketState.READY
        elif "test" in name:
            return TicketState.TESTED
        elif "done" in name or "resolved" in name:
            return TicketState.DONE
        elif "closed" in name:
            return TicketState.CLOSED
        else:
            return TicketState.OPEN

    def _issue_to_ticket(self, issue: dict[str, Any]) -> Union[Epic, Task]:
        """Convert JIRA issue to universal ticket model."""
        fields = issue.get("fields", {})

        # Determine ticket type
        issue_type = fields.get("issuetype", {}).get("name", "").lower()
        is_epic = "epic" in issue_type

        # Extract common fields
        # Convert ADF description back to plain text if needed
        description = self._convert_from_adf(fields.get("description", ""))

        base_data = {
            "id": issue.get("key"),
            "title": fields.get("summary", ""),
            "description": description,
            "state": self._map_state_from_jira(fields.get("status", {})),
            "priority": self._map_priority_from_jira(fields.get("priority")),
            "tags": [
                label.get("name", "") if isinstance(label, dict) else str(label)
                for label in fields.get("labels", [])
            ],
            "created_at": (
                datetime.fromisoformat(fields.get("created", "").replace("Z", "+00:00"))
                if fields.get("created")
                else None
            ),
            "updated_at": (
                datetime.fromisoformat(fields.get("updated", "").replace("Z", "+00:00"))
                if fields.get("updated")
                else None
            ),
            "metadata": {
                "jira": {
                    "id": issue.get("id"),
                    "key": issue.get("key"),
                    "self": issue.get("self"),
                    "url": f"{self.server}/browse/{issue.get('key')}",
                    "issue_type": fields.get("issuetype", {}),
                    "project": fields.get("project", {}),
                    "components": fields.get("components", []),
                    "fix_versions": fields.get("fixVersions", []),
                    "resolution": fields.get("resolution"),
                }
            },
        }

        if is_epic:
            # Create Epic
            return Epic(
                **base_data,
                child_issues=[
                    subtask.get("key") for subtask in fields.get("subtasks", [])
                ],
            )
        else:
            # Create Task
            parent = fields.get("parent", {})
            epic_link = fields.get("customfield_10014")  # Common epic link field

            return Task(
                **base_data,
                parent_issue=parent.get("key") if parent else None,
                parent_epic=epic_link if epic_link else None,
                assignee=(
                    fields.get("assignee", {}).get("displayName")
                    if fields.get("assignee")
                    else None
                ),
                estimated_hours=(
                    fields.get("timetracking", {}).get("originalEstimateSeconds", 0)
                    / 3600
                    if fields.get("timetracking")
                    else None
                ),
                actual_hours=(
                    fields.get("timetracking", {}).get("timeSpentSeconds", 0) / 3600
                    if fields.get("timetracking")
                    else None
                ),
            )

    def _ticket_to_issue_fields(
        self, ticket: Union[Epic, Task], issue_type: Optional[str] = None
    ) -> dict[str, Any]:
        """Convert universal ticket to JIRA issue fields."""
        # Convert description to ADF format for JIRA Cloud
        description = (
            self._convert_to_adf(ticket.description or "")
            if self.is_cloud
            else (ticket.description or "")
        )

        fields = {
            "summary": ticket.title,
            "description": description,
            "labels": ticket.tags,
            "priority": {"name": self._map_priority_to_jira(ticket.priority)},
        }

        # Add project if creating new issue
        if not ticket.id and self.project_key:
            fields["project"] = {"key": self.project_key}

        # Set issue type
        if issue_type:
            fields["issuetype"] = {"name": issue_type}
        elif isinstance(ticket, Epic):
            fields["issuetype"] = {"name": JiraIssueType.EPIC}
        else:
            fields["issuetype"] = {"name": JiraIssueType.TASK}

        # Add task-specific fields
        if isinstance(ticket, Task):
            if ticket.assignee:
                # Note: Need to resolve user account ID
                fields["assignee"] = {"accountId": ticket.assignee}

            if ticket.parent_issue:
                fields["parent"] = {"key": ticket.parent_issue}

            # Time tracking
            if ticket.estimated_hours:
                fields["timetracking"] = {
                    "originalEstimate": f"{int(ticket.estimated_hours)}h"
                }

        return fields

    async def create(self, ticket: Union[Epic, Task]) -> Union[Epic, Task]:
        """Create a new JIRA issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Prepare issue fields
        fields = self._ticket_to_issue_fields(ticket)

        # Create issue
        data = await self._make_request("POST", "issue", data={"fields": fields})

        # Set the ID and fetch full issue data
        ticket.id = data.get("key")

        # Fetch complete issue data
        created_issue = await self._make_request("GET", f"issue/{ticket.id}")
        return self._issue_to_ticket(created_issue)

    async def read(self, ticket_id: str) -> Optional[Union[Epic, Task]]:
        """Read a JIRA issue by key."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue = await self._make_request(
                "GET", f"issue/{ticket_id}", params={"expand": "renderedFields"}
            )
            return self._issue_to_ticket(issue)
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def update(
        self, ticket_id: str, updates: dict[str, Any]
    ) -> Optional[Union[Epic, Task]]:
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
        fields = {}

        if "title" in updates:
            fields["summary"] = updates["title"]
        if "description" in updates:
            fields["description"] = updates["description"]
        if "priority" in updates:
            fields["priority"] = {
                "name": self._map_priority_to_jira(updates["priority"])
            }
        if "tags" in updates:
            fields["labels"] = updates["tags"]
        if "assignee" in updates:
            fields["assignee"] = {"accountId": updates["assignee"]}

        # Apply update
        if fields:
            await self._make_request(
                "PUT", f"issue/{ticket_id}", data={"fields": fields}
            )

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
            await self._make_request("DELETE", f"issue/{ticket_id}")
            return True
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return False
            raise

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[dict[str, Any]] = None
    ) -> list[Union[Epic, Task]]:
        """List JIRA issues with pagination."""
        # Build JQL query
        jql_parts = []

        if self.project_key:
            jql_parts.append(f"project = {self.project_key}")

        if filters:
            if "state" in filters:
                status = self.map_state_to_system(filters["state"])
                jql_parts.append(f'status = "{status}"')
            if "priority" in filters:
                priority = self._map_priority_to_jira(filters["priority"])
                jql_parts.append(f'priority = "{priority}"')
            if "assignee" in filters:
                jql_parts.append(f'assignee = "{filters["assignee"]}"')
            if "ticket_type" in filters:
                jql_parts.append(f'issuetype = "{filters["ticket_type"]}"')

        jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"

        # Search issues using the new API endpoint
        data = await self._make_request(
            "POST",
            "search/jql",  # Updated to use new API endpoint
            data={
                "jql": jql,
                "startAt": offset,
                "maxResults": limit,
                "fields": ["*all"],
                "expand": ["renderedFields"],
            },
        )

        # Convert issues
        issues = data.get("issues", [])
        return [self._issue_to_ticket(issue) for issue in issues]

    async def search(self, query: SearchQuery) -> builtins.list[Union[Epic, Task]]:
        """Search JIRA issues using JQL."""
        # Build JQL query
        jql_parts = []

        if self.project_key:
            jql_parts.append(f"project = {self.project_key}")

        # Text search
        if query.query:
            jql_parts.append(f'text ~ "{query.query}"')

        # State filter
        if query.state:
            status = self.map_state_to_system(query.state)
            jql_parts.append(f'status = "{status}"')

        # Priority filter
        if query.priority:
            priority = self._map_priority_to_jira(query.priority)
            jql_parts.append(f'priority = "{priority}"')

        # Assignee filter
        if query.assignee:
            jql_parts.append(f'assignee = "{query.assignee}"')

        # Tags/labels filter
        if query.tags:
            label_conditions = [f'labels = "{tag}"' for tag in query.tags]
            jql_parts.append(f"({' OR '.join(label_conditions)})")

        jql = " AND ".join(jql_parts) if jql_parts else "ORDER BY created DESC"

        # Execute search using the new API endpoint
        data = await self._make_request(
            "POST",
            "search/jql",  # Updated to use new API endpoint
            data={
                "jql": jql,
                "startAt": query.offset,
                "maxResults": query.limit,
                "fields": ["*all"],
                "expand": ["renderedFields"],
            },
        )

        # Convert and return results
        issues = data.get("issues", [])
        return [self._issue_to_ticket(issue) for issue in issues]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Union[Epic, Task]]:
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
        await self._make_request(
            "POST",
            f"issue/{ticket_id}/transitions",
            data={"transition": {"id": transition["id"]}},
        )

        # Return updated issue
        return await self.read(ticket_id)

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a JIRA issue."""
        # Prepare comment data
        data = {"body": comment.content}

        # Add comment
        result = await self._make_request(
            "POST", f"issue/{comment.ticket_id}/comment", data=data
        )

        # Update comment with JIRA data
        comment.id = result.get("id")
        comment.created_at = (
            datetime.fromisoformat(result.get("created", "").replace("Z", "+00:00"))
            if result.get("created")
            else datetime.now()
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

        issue = await self._make_request("GET", f"issue/{ticket_id}", params=params)

        # Extract comments
        comments_data = issue.get("fields", {}).get("comment", {}).get("comments", [])

        # Apply pagination
        paginated = comments_data[offset : offset + limit]

        # Convert to Comment objects
        comments = []
        for comment_data in paginated:
            comment = Comment(
                id=comment_data.get("id"),
                ticket_id=ticket_id,
                author=comment_data.get("author", {}).get("displayName", "Unknown"),
                content=comment_data.get("body", ""),
                created_at=(
                    datetime.fromisoformat(
                        comment_data.get("created", "").replace("Z", "+00:00")
                    )
                    if comment_data.get("created")
                    else None
                ),
                metadata={"jira": comment_data},
            )
            comments.append(comment)

        return comments

    async def get_project_info(
        self, project_key: Optional[str] = None
    ) -> dict[str, Any]:
        """Get JIRA project information including workflows and fields."""
        key = project_key or self.project_key
        if not key:
            raise ValueError("Project key is required")

        project = await self._make_request("GET", f"project/{key}")

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
    ) -> builtins.list[Union[Epic, Task]]:
        """Execute a raw JQL query.

        Args:
            jql: JIRA Query Language string
            limit: Maximum number of results

        Returns:
            List of matching tickets

        """
        data = await self._make_request(
            "POST",
            "search",
            data={
                "jql": jql,
                "startAt": 0,
                "maxResults": limit,
                "fields": ["*all"],
            },
        )

        issues = data.get("issues", [])
        return [self._issue_to_ticket(issue) for issue in issues]

    async def get_sprints(
        self, board_id: Optional[int] = None
    ) -> builtins.list[dict[str, Any]]:
        """Get active sprints for a board (requires JIRA Software).

        Args:
            board_id: Agile board ID

        Returns:
            List of sprint information

        """
        if not board_id:
            # Try to find a board for the project
            boards_data = await self._make_request(
                "GET",
                "/rest/agile/1.0/board",
                params={"projectKeyOrId": self.project_key},
            )
            boards = boards_data.get("values", [])
            if not boards:
                return []
            board_id = boards[0]["id"]

        # Get sprints for the board
        sprints_data = await self._make_request(
            "GET",
            f"/rest/agile/1.0/board/{board_id}/sprint",
            params={"state": "active,future"},
        )

        return sprints_data.get("values", [])

    async def close(self) -> None:
        """Close the adapter and cleanup resources."""
        # Clear caches
        self._workflow_cache.clear()
        self._priority_cache.clear()
        self._issue_types_cache.clear()
        self._custom_fields_cache.clear()


# Register the adapter
AdapterRegistry.register("jira", JiraAdapter)
