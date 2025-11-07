"""JIRA adapter implementation using REST API v3."""

import asyncio
import builtins
import logging
import re
from datetime import datetime
from enum import Enum
from typing import Any, Union

import httpx
from httpx import AsyncClient, HTTPStatusError, TimeoutException

from ..core.adapter import BaseAdapter
from ..core.env_loader import load_adapter_config, validate_adapter_config
from ..core.models import Comment, Epic, Priority, SearchQuery, Task, TicketState
from ..core.registry import AdapterRegistry

logger = logging.getLogger(__name__)


def parse_jira_datetime(date_str: str) -> datetime | None:
    """Parse JIRA datetime strings which can be in various formats.

    JIRA can return dates in formats like:
    - 2025-10-24T14:12:18.771-0400
    - 2025-10-24T14:12:18.771Z
    - 2025-10-24T14:12:18.771+00:00
    """
    if not date_str:
        return None

    try:
        # Handle Z timezone
        if date_str.endswith("Z"):
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        # Handle timezone formats like -0400, +0500 (need to add colon)
        if re.match(r".*[+-]\d{4}$", date_str):
            # Insert colon in timezone: -0400 -> -04:00
            date_str = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", date_str)

        return datetime.fromisoformat(date_str)

    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse JIRA datetime '{date_str}': {e}")
        return None


def extract_text_from_adf(adf_content: str | dict[str, Any]) -> str:
    """Extract plain text from Atlassian Document Format (ADF).

    Args:
        adf_content: Either a string (already plain text) or ADF document dict

    Returns:
        Plain text string extracted from the ADF content

    """
    if isinstance(adf_content, str):
        return adf_content

    if not isinstance(adf_content, dict):
        return str(adf_content) if adf_content else ""

    def extract_text_recursive(node: dict[str, Any]) -> str:
        """Recursively extract text from ADF nodes."""
        if not isinstance(node, dict):
            return ""

        # If this is a text node, return its text
        if node.get("type") == "text":
            return node.get("text", "")

        # If this node has content, process it recursively
        content = node.get("content", [])
        if isinstance(content, list):
            return "".join(extract_text_recursive(child) for child in content)

        return ""

    try:
        return extract_text_recursive(adf_content)
    except Exception as e:
        logger.warning(f"Failed to extract text from ADF: {e}")
        return str(adf_content) if adf_content else ""


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

        # Load configuration with environment variable resolution
        full_config = load_adapter_config("jira", config)

        # Validate required configuration
        missing_keys = validate_adapter_config("jira", full_config)
        if missing_keys:
            raise ValueError(
                f"JIRA adapter missing required configuration: {', '.join(missing_keys)}"
            )

        # Configuration
        self.server = full_config.get("server", "")
        self.email = full_config.get("email", "")
        self.api_token = full_config.get("api_token", "")
        self.project_key = full_config.get("project_key", "")
        self.is_cloud = full_config.get("cloud", True)
        self.verify_ssl = full_config.get("verify_ssl", True)
        self.timeout = full_config.get("timeout", 30)
        self.max_retries = full_config.get("max_retries", 3)

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
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
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
        self, project_key: str | None = None
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

    def _map_priority_from_jira(self, jira_priority: dict[str, Any] | None) -> Priority:
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

    def _issue_to_ticket(self, issue: dict[str, Any]) -> Epic | Task:
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
            "created_at": parse_jira_datetime(fields.get("created")),
            "updated_at": parse_jira_datetime(fields.get("updated")),
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
        self, ticket: Epic | Task, issue_type: str | None = None
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
        }

        # Only add priority for Tasks, not Epics (some JIRA configurations don't allow priority on Epics)
        if isinstance(ticket, Task):
            fields["priority"] = {"name": self._map_priority_to_jira(ticket.priority)}

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

    async def create(self, ticket: Epic | Task) -> Epic | Task:
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

    async def read(self, ticket_id: str) -> Epic | Task | None:
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
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[Epic | Task]:
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

        # Search issues using the JIRA API endpoint
        data = await self._make_request(
            "GET",
            "search/jql",  # JIRA search endpoint (new API v3)
            params={
                "jql": jql,
                "startAt": offset,
                "maxResults": limit,
                "fields": "*all",
                "expand": "renderedFields",
            },
        )

        # Convert issues
        issues = data.get("issues", [])
        return [self._issue_to_ticket(issue) for issue in issues]

    async def search(self, query: SearchQuery) -> builtins.list[Epic | Task]:
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

        # Execute search using the JIRA API endpoint
        data = await self._make_request(
            "GET",
            "search/jql",  # JIRA search endpoint (new API v3)
            params={
                "jql": jql,
                "startAt": query.offset,
                "maxResults": query.limit,
                "fields": "*all",
                "expand": "renderedFields",
            },
        )

        # Convert and return results
        issues = data.get("issues", [])
        return [self._issue_to_ticket(issue) for issue in issues]

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
        await self._make_request(
            "POST",
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
        result = await self._make_request(
            "POST", f"issue/{comment.ticket_id}/comment", data=data
        )

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

        issue = await self._make_request("GET", f"issue/{ticket_id}", params=params)

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
    ) -> builtins.list[Epic | Task]:
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
        self, board_id: int | None = None
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

    async def get_project_users(self) -> builtins.list[dict[str, Any]]:
        """Get users who have access to the project."""
        if not self.project_key:
            return []

        try:
            # Get project role users
            project_data = await self._make_request(
                "GET", f"project/{self.project_key}"
            )

            # Get users from project roles
            users = []
            if "roles" in project_data:
                for _role_name, role_url in project_data["roles"].items():
                    # Extract role ID from URL
                    role_id = role_url.split("/")[-1]
                    try:
                        role_data = await self._make_request(
                            "GET", f"project/{self.project_key}/role/{role_id}"
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
                users_data = await self._make_request(
                    "GET",
                    "user/assignable/search",
                    params={"project": self.project_key, "maxResults": 50},
                )
                return users_data if isinstance(users_data, list) else []
            except Exception:
                return []

    async def get_current_user(self) -> dict[str, Any] | None:
        """Get current authenticated user information."""
        try:
            return await self._make_request("GET", "myself")
        except Exception:
            return None

    async def close(self) -> None:
        """Close the adapter and cleanup resources."""
        # Clear caches
        self._workflow_cache.clear()
        self._priority_cache.clear()
        self._issue_types_cache.clear()
        self._custom_fields_cache.clear()


# Register the adapter
AdapterRegistry.register("jira", JiraAdapter)
