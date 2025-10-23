"""GitHub adapter implementation using REST API v3 and GraphQL API v4."""

import builtins
import os
import re
from datetime import datetime
from typing import Any, Optional

import httpx

from ..core.adapter import BaseAdapter
from ..core.models import Comment, Epic, Priority, SearchQuery, Task, TicketState
from ..core.registry import AdapterRegistry


class GitHubStateMapping:
    """GitHub issue states and label-based extended states."""

    # GitHub native states
    OPEN = "open"
    CLOSED = "closed"

    # Extended states via labels
    STATE_LABELS = {
        TicketState.IN_PROGRESS: "in-progress",
        TicketState.READY: "ready",
        TicketState.TESTED: "tested",
        TicketState.WAITING: "waiting",
        TicketState.BLOCKED: "blocked",
    }

    # Priority labels
    PRIORITY_LABELS = {
        Priority.CRITICAL: ["P0", "critical", "urgent"],
        Priority.HIGH: ["P1", "high"],
        Priority.MEDIUM: ["P2", "medium"],
        Priority.LOW: ["P3", "low"],
    }


class GitHubGraphQLQueries:
    """GraphQL queries for GitHub API v4."""

    ISSUE_FRAGMENT = """
        fragment IssueFields on Issue {
            id
            number
            title
            body
            state
            createdAt
            updatedAt
            url
            author {
                login
            }
            assignees(first: 10) {
                nodes {
                    login
                    email
                }
            }
            labels(first: 20) {
                nodes {
                    name
                    color
                }
            }
            milestone {
                id
                number
                title
                state
                description
            }
            projectCards(first: 10) {
                nodes {
                    project {
                        name
                        url
                    }
                    column {
                        name
                    }
                }
            }
            comments(first: 100) {
                nodes {
                    id
                    body
                    author {
                        login
                    }
                    createdAt
                }
            }
            reactions(first: 10) {
                nodes {
                    content
                    user {
                        login
                    }
                }
            }
        }
    """

    GET_ISSUE = """
        query GetIssue($owner: String!, $repo: String!, $number: Int!) {
            repository(owner: $owner, name: $repo) {
                issue(number: $number) {
                    ...IssueFields
                }
            }
        }
    """

    SEARCH_ISSUES = """
        query SearchIssues($query: String!, $first: Int!, $after: String) {
            search(query: $query, type: ISSUE, first: $first, after: $after) {
                issueCount
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    ... on Issue {
                        ...IssueFields
                    }
                }
            }
        }
    """


class GitHubAdapter(BaseAdapter[Task]):
    """Adapter for GitHub Issues tracking system."""

    def __init__(self, config: dict[str, Any]):
        """Initialize GitHub adapter.

        Args:
            config: Configuration with:
                - token: GitHub Personal Access Token (or GITHUB_TOKEN env var)
                - owner: Repository owner (or GITHUB_OWNER env var)
                - repo: Repository name (or GITHUB_REPO env var)
                - api_url: Optional API URL for GitHub Enterprise (defaults to github.com)
                - use_projects_v2: Enable GitHub Projects v2 integration (default: False)
                - custom_priority_scheme: Custom priority label mapping

        """
        super().__init__(config)

        # Get authentication token - support both 'api_key' and 'token' for compatibility
        self.token = (
            config.get("api_key") or config.get("token") or os.getenv("GITHUB_TOKEN")
        )
        if not self.token:
            raise ValueError(
                "GitHub token required (config.api_key, config.token or GITHUB_TOKEN env var)"
            )

        # Get repository information
        self.owner = config.get("owner") or os.getenv("GITHUB_OWNER")
        self.repo = config.get("repo") or os.getenv("GITHUB_REPO")

        if not self.owner or not self.repo:
            raise ValueError("GitHub owner and repo are required")

        # API URLs
        self.api_url = config.get("api_url", "https://api.github.com")
        self.graphql_url = (
            f"{self.api_url}/graphql"
            if "github.com" in self.api_url
            else f"{self.api_url}/api/graphql"
        )

        # Configuration options
        self.use_projects_v2 = config.get("use_projects_v2", False)
        self.custom_priority_scheme = config.get("custom_priority_scheme", {})

        # HTTP client with authentication
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        self.client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=self.headers,
            timeout=30.0,
        )

        # Cache for labels and milestones
        self._labels_cache: Optional[list[dict[str, Any]]] = None
        self._milestones_cache: Optional[list[dict[str, Any]]] = None
        self._rate_limit: dict[str, Any] = {}

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
            (is_valid, error_message) - Tuple of validation result and error message

        """
        if not self.token:
            return (
                False,
                "GITHUB_TOKEN is required but not found. Set it in .env.local or environment.",
            )
        if not self.owner:
            return (
                False,
                "GitHub owner is required in configuration. Set GITHUB_OWNER in .env.local or configure with 'mcp-ticketer init --adapter github --github-owner <owner>'",
            )
        if not self.repo:
            return (
                False,
                "GitHub repo is required in configuration. Set GITHUB_REPO in .env.local or configure with 'mcp-ticketer init --adapter github --github-repo <repo>'",
            )
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Map universal states to GitHub states."""
        return {
            TicketState.OPEN: GitHubStateMapping.OPEN,
            TicketState.IN_PROGRESS: GitHubStateMapping.OPEN,  # with label
            TicketState.READY: GitHubStateMapping.OPEN,  # with label
            TicketState.TESTED: GitHubStateMapping.OPEN,  # with label
            TicketState.DONE: GitHubStateMapping.CLOSED,
            TicketState.WAITING: GitHubStateMapping.OPEN,  # with label
            TicketState.BLOCKED: GitHubStateMapping.OPEN,  # with label
            TicketState.CLOSED: GitHubStateMapping.CLOSED,
        }

    def _get_state_label(self, state: TicketState) -> Optional[str]:
        """Get the label name for extended states."""
        return GitHubStateMapping.STATE_LABELS.get(state)

    def _get_priority_from_labels(self, labels: list[str]) -> Priority:
        """Extract priority from issue labels."""
        label_names = [label.lower() for label in labels]

        # Check custom priority scheme first
        if self.custom_priority_scheme:
            for priority_str, label_patterns in self.custom_priority_scheme.items():
                for pattern in label_patterns:
                    if any(pattern.lower() in label for label in label_names):
                        return Priority(priority_str)

        # Check default priority labels
        for priority, priority_labels in GitHubStateMapping.PRIORITY_LABELS.items():
            for priority_label in priority_labels:
                if priority_label.lower() in label_names:
                    return priority

        return Priority.MEDIUM

    def _get_priority_label(self, priority: Priority) -> str:
        """Get label name for a priority level."""
        # Check custom scheme first
        if self.custom_priority_scheme:
            labels = self.custom_priority_scheme.get(priority.value, [])
            if labels:
                return labels[0]

        # Use default labels
        labels = GitHubStateMapping.PRIORITY_LABELS.get(priority, [])
        return (
            labels[0]
            if labels
            else f"P{['0', '1', '2', '3'][list(Priority).index(priority)]}"
        )

    def _extract_state_from_issue(self, issue: dict[str, Any]) -> TicketState:
        """Extract ticket state from GitHub issue data."""
        # Check if closed
        if issue["state"] == "closed":
            return TicketState.CLOSED

        # Check labels for extended states
        labels = []
        if "labels" in issue:
            if isinstance(issue["labels"], list):
                labels = [
                    label.get("name", "") if isinstance(label, dict) else str(label)
                    for label in issue["labels"]
                ]
            elif isinstance(issue["labels"], dict) and "nodes" in issue["labels"]:
                labels = [label["name"] for label in issue["labels"]["nodes"]]

        label_names = [label.lower() for label in labels]

        # Check for extended state labels
        for state, label_name in GitHubStateMapping.STATE_LABELS.items():
            if label_name.lower() in label_names:
                return state

        return TicketState.OPEN

    def _task_from_github_issue(self, issue: dict[str, Any]) -> Task:
        """Convert GitHub issue to universal Task."""
        # Extract labels
        labels = []
        if "labels" in issue:
            if isinstance(issue["labels"], list):
                labels = [
                    label.get("name", "") if isinstance(label, dict) else str(label)
                    for label in issue["labels"]
                ]
            elif isinstance(issue["labels"], dict) and "nodes" in issue["labels"]:
                labels = [label["name"] for label in issue["labels"]["nodes"]]

        # Extract state
        state = self._extract_state_from_issue(issue)

        # Extract priority
        priority = self._get_priority_from_labels(labels)

        # Extract assignee
        assignee = None
        if "assignees" in issue:
            if isinstance(issue["assignees"], list) and issue["assignees"]:
                assignee = issue["assignees"][0].get("login")
            elif isinstance(issue["assignees"], dict) and "nodes" in issue["assignees"]:
                nodes = issue["assignees"]["nodes"]
                if nodes:
                    assignee = nodes[0].get("login")
        elif "assignee" in issue and issue["assignee"]:
            assignee = issue["assignee"].get("login")

        # Extract parent epic (milestone)
        parent_epic = None
        if issue.get("milestone"):
            parent_epic = str(issue["milestone"]["number"])

        # Parse dates
        created_at = None
        if issue.get("created_at"):
            created_at = datetime.fromisoformat(
                issue["created_at"].replace("Z", "+00:00")
            )
        elif issue.get("createdAt"):
            created_at = datetime.fromisoformat(
                issue["createdAt"].replace("Z", "+00:00")
            )

        updated_at = None
        if issue.get("updated_at"):
            updated_at = datetime.fromisoformat(
                issue["updated_at"].replace("Z", "+00:00")
            )
        elif issue.get("updatedAt"):
            updated_at = datetime.fromisoformat(
                issue["updatedAt"].replace("Z", "+00:00")
            )

        # Build metadata
        metadata = {
            "github": {
                "number": issue.get("number"),
                "url": issue.get("url") or issue.get("html_url"),
                "author": (
                    issue.get("user", {}).get("login")
                    if "user" in issue
                    else issue.get("author", {}).get("login")
                ),
                "labels": labels,
            }
        }

        # Add projects v2 info if available
        if "projectCards" in issue and issue["projectCards"].get("nodes"):
            metadata["github"]["projects"] = [
                {
                    "name": card["project"]["name"],
                    "column": card["column"]["name"],
                    "url": card["project"]["url"],
                }
                for card in issue["projectCards"]["nodes"]
            ]

        return Task(
            id=str(issue["number"]),
            title=issue["title"],
            description=issue.get("body") or issue.get("bodyText"),
            state=state,
            priority=priority,
            tags=labels,
            parent_epic=parent_epic,
            assignee=assignee,
            created_at=created_at,
            updated_at=updated_at,
            metadata=metadata,
        )

    async def _ensure_label_exists(
        self, label_name: str, color: str = "0366d6"
    ) -> None:
        """Ensure a label exists in the repository."""
        if not self._labels_cache:
            response = await self.client.get(f"/repos/{self.owner}/{self.repo}/labels")
            response.raise_for_status()
            self._labels_cache = response.json()

        # Check if label exists
        existing_labels = [label["name"].lower() for label in self._labels_cache]
        if label_name.lower() not in existing_labels:
            # Create the label
            response = await self.client.post(
                f"/repos/{self.owner}/{self.repo}/labels",
                json={"name": label_name, "color": color},
            )
            if response.status_code == 201:
                self._labels_cache.append(response.json())

    async def _graphql_request(
        self, query: str, variables: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a GraphQL query."""
        response = await self.client.post(
            self.graphql_url, json={"query": query, "variables": variables}
        )
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            raise ValueError(f"GraphQL errors: {data['errors']}")

        return data["data"]

    async def create(self, ticket: Task) -> Task:
        """Create a new GitHub issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        # Prepare labels
        labels = ticket.tags.copy() if ticket.tags else []

        # Add state label if needed
        state_label = self._get_state_label(ticket.state)
        if state_label:
            labels.append(state_label)
            await self._ensure_label_exists(state_label, "fbca04")

        # Add priority label
        priority_label = self._get_priority_label(ticket.priority)
        labels.append(priority_label)
        await self._ensure_label_exists(priority_label, "d73a4a")

        # Ensure all labels exist
        for label in labels:
            await self._ensure_label_exists(label)

        # Build issue data
        issue_data = {
            "title": ticket.title,
            "body": ticket.description or "",
            "labels": labels,
        }

        # Add assignee if specified
        if ticket.assignee:
            issue_data["assignees"] = [ticket.assignee]

        # Add milestone if parent_epic is specified
        if ticket.parent_epic:
            try:
                milestone_number = int(ticket.parent_epic)
                issue_data["milestone"] = milestone_number
            except ValueError:
                # Try to find milestone by title
                if not self._milestones_cache:
                    response = await self.client.get(
                        f"/repos/{self.owner}/{self.repo}/milestones"
                    )
                    response.raise_for_status()
                    self._milestones_cache = response.json()

                for milestone in self._milestones_cache:
                    if milestone["title"] == ticket.parent_epic:
                        issue_data["milestone"] = milestone["number"]
                        break

        # Create the issue
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues", json=issue_data
        )
        response.raise_for_status()

        created_issue = response.json()

        # If state requires closing, close the issue
        if ticket.state in [TicketState.DONE, TicketState.CLOSED]:
            await self.client.patch(
                f"/repos/{self.owner}/{self.repo}/issues/{created_issue['number']}",
                json={"state": "closed"},
            )
            created_issue["state"] = "closed"

        return self._task_from_github_issue(created_issue)

    async def read(self, ticket_id: str) -> Optional[Task]:
        """Read a GitHub issue by number."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue_number = int(ticket_id)
        except ValueError:
            return None

        try:
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()

            issue = response.json()
            return self._task_from_github_issue(issue)
        except httpx.HTTPError:
            return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Optional[Task]:
        """Update a GitHub issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue_number = int(ticket_id)
        except ValueError:
            return None

        # Get current issue to preserve labels
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()

        current_issue = response.json()
        current_labels = [label["name"] for label in current_issue.get("labels", [])]

        # Build update data
        update_data = {}

        if "title" in updates:
            update_data["title"] = updates["title"]

        if "description" in updates:
            update_data["body"] = updates["description"]

        # Handle state updates
        if "state" in updates:
            new_state = updates["state"]
            if isinstance(new_state, str):
                new_state = TicketState(new_state)

            # Remove old state labels
            labels_to_update = [
                label
                for label in current_labels
                if label.lower()
                not in [sl.lower() for sl in GitHubStateMapping.STATE_LABELS.values()]
            ]

            # Add new state label if needed
            state_label = self._get_state_label(new_state)
            if state_label:
                await self._ensure_label_exists(state_label, "fbca04")
                labels_to_update.append(state_label)

            update_data["labels"] = labels_to_update

            # Update issue state if needed
            if new_state in [TicketState.DONE, TicketState.CLOSED]:
                update_data["state"] = "closed"
            else:
                update_data["state"] = "open"

        # Handle priority updates
        if "priority" in updates:
            new_priority = updates["priority"]
            if isinstance(new_priority, str):
                new_priority = Priority(new_priority)

            # Remove old priority labels
            labels_to_update = update_data.get("labels", current_labels)
            all_priority_labels = []
            for labels in GitHubStateMapping.PRIORITY_LABELS.values():
                all_priority_labels.extend([l.lower() for l in labels])

            labels_to_update = [
                label
                for label in labels_to_update
                if label.lower() not in all_priority_labels
                and not re.match(r"^P[0-3]$", label, re.IGNORECASE)
            ]

            # Add new priority label
            priority_label = self._get_priority_label(new_priority)
            await self._ensure_label_exists(priority_label, "d73a4a")
            labels_to_update.append(priority_label)

            update_data["labels"] = labels_to_update

        # Handle assignee updates
        if "assignee" in updates:
            if updates["assignee"]:
                update_data["assignees"] = [updates["assignee"]]
            else:
                update_data["assignees"] = []

        # Handle tags updates
        if "tags" in updates:
            # Preserve state and priority labels
            preserved_labels = []
            for label in current_labels:
                if label.lower() in [
                    sl.lower() for sl in GitHubStateMapping.STATE_LABELS.values()
                ]:
                    preserved_labels.append(label)
                elif any(
                    label.lower() in [pl.lower() for pl in labels]
                    for labels in GitHubStateMapping.PRIORITY_LABELS.values()
                ):
                    preserved_labels.append(label)
                elif re.match(r"^P[0-3]$", label, re.IGNORECASE):
                    preserved_labels.append(label)

            # Add new tags
            for tag in updates["tags"]:
                await self._ensure_label_exists(tag)

            update_data["labels"] = preserved_labels + updates["tags"]

        # Apply updates
        if update_data:
            response = await self.client.patch(
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
                json=update_data,
            )
            response.raise_for_status()

            updated_issue = response.json()
            return self._task_from_github_issue(updated_issue)

        return await self.read(ticket_id)

    async def delete(self, ticket_id: str) -> bool:
        """Delete (close) a GitHub issue."""
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            issue_number = int(ticket_id)
        except ValueError:
            return False

        try:
            response = await self.client.patch(
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}",
                json={"state": "closed", "state_reason": "not_planned"},
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError:
            return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: Optional[dict[str, Any]] = None
    ) -> list[Task]:
        """List GitHub issues with filters."""
        # Build query parameters
        params = {
            "per_page": min(limit, 100),  # GitHub max is 100
            "page": (offset // limit) + 1 if limit > 0 else 1,
        }

        if filters:
            # State filter
            if "state" in filters:
                state = filters["state"]
                if isinstance(state, str):
                    state = TicketState(state)

                if state in [TicketState.DONE, TicketState.CLOSED]:
                    params["state"] = "closed"
                else:
                    params["state"] = "open"
                    # Add label filter for extended states
                    state_label = self._get_state_label(state)
                    if state_label:
                        params["labels"] = state_label

            # Priority filter via labels
            if "priority" in filters:
                priority = filters["priority"]
                if isinstance(priority, str):
                    priority = Priority(priority)
                priority_label = self._get_priority_label(priority)

                if "labels" in params:
                    params["labels"] += f",{priority_label}"
                else:
                    params["labels"] = priority_label

            # Assignee filter
            if "assignee" in filters:
                params["assignee"] = filters["assignee"]

            # Milestone filter (parent_epic)
            if "parent_epic" in filters:
                params["milestone"] = filters["parent_epic"]

        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues", params=params
        )
        response.raise_for_status()

        issues = response.json()

        # Store rate limit info
        self._rate_limit = {
            "limit": response.headers.get("X-RateLimit-Limit"),
            "remaining": response.headers.get("X-RateLimit-Remaining"),
            "reset": response.headers.get("X-RateLimit-Reset"),
        }

        # Filter out pull requests (they appear as issues in the API)
        issues = [issue for issue in issues if "pull_request" not in issue]

        return [self._task_from_github_issue(issue) for issue in issues]

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search GitHub issues using advanced search syntax."""
        # Build GitHub search query
        search_parts = [f"repo:{self.owner}/{self.repo}", "is:issue"]

        # Text search
        if query.query:
            # Escape special characters for GitHub search
            escaped_query = query.query.replace('"', '\\"')
            search_parts.append(f'"{escaped_query}"')

        # State filter
        if query.state:
            if query.state in [TicketState.DONE, TicketState.CLOSED]:
                search_parts.append("is:closed")
            else:
                search_parts.append("is:open")
                # Add label filter for extended states
                state_label = self._get_state_label(query.state)
                if state_label:
                    search_parts.append(f'label:"{state_label}"')

        # Priority filter
        if query.priority:
            priority_label = self._get_priority_label(query.priority)
            search_parts.append(f'label:"{priority_label}"')

        # Assignee filter
        if query.assignee:
            search_parts.append(f"assignee:{query.assignee}")

        # Tags filter
        if query.tags:
            for tag in query.tags:
                search_parts.append(f'label:"{tag}"')

        # Build final search query
        github_query = " ".join(search_parts)

        # Use GraphQL for better search capabilities
        full_query = (
            GitHubGraphQLQueries.ISSUE_FRAGMENT + GitHubGraphQLQueries.SEARCH_ISSUES
        )

        variables = {
            "query": github_query,
            "first": min(query.limit, 100),
            "after": None,
        }

        # Handle pagination for offset
        if query.offset > 0:
            # We need to paginate through to get to the offset
            # This is inefficient but GitHub doesn't support direct offset
            pages_to_skip = query.offset // 100
            for _ in range(pages_to_skip):
                temp_result = await self._graphql_request(full_query, variables)
                page_info = temp_result["search"]["pageInfo"]
                if page_info["hasNextPage"]:
                    variables["after"] = page_info["endCursor"]
                else:
                    return []  # Offset beyond available results

        result = await self._graphql_request(full_query, variables)

        issues = []
        for node in result["search"]["nodes"]:
            if node:  # Some nodes might be null
                # Convert GraphQL format to REST format for consistency
                rest_format = {
                    "number": node["number"],
                    "title": node["title"],
                    "body": node["body"],
                    "state": node["state"].lower(),
                    "created_at": node["createdAt"],
                    "updated_at": node["updatedAt"],
                    "html_url": node["url"],
                    "labels": node.get("labels", {}).get("nodes", []),
                    "milestone": node.get("milestone"),
                    "assignees": node.get("assignees", {}).get("nodes", []),
                    "author": node.get("author"),
                }
                issues.append(self._task_from_github_issue(rest_format))

        return issues

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Optional[Task]:
        """Transition GitHub issue to a new state."""
        # Validate transition
        if not await self.validate_transition(ticket_id, target_state):
            return None

        # Update state
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a GitHub issue."""
        try:
            issue_number = int(comment.ticket_id)
        except ValueError:
            raise ValueError(f"Invalid issue number: {comment.ticket_id}")

        # Create comment
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json={"body": comment.content},
        )
        response.raise_for_status()

        created_comment = response.json()

        return Comment(
            id=str(created_comment["id"]),
            ticket_id=comment.ticket_id,
            author=created_comment["user"]["login"],
            content=created_comment["body"],
            created_at=datetime.fromisoformat(
                created_comment["created_at"].replace("Z", "+00:00")
            ),
            metadata={
                "github": {
                    "id": created_comment["id"],
                    "url": created_comment["html_url"],
                    "author_avatar": created_comment["user"]["avatar_url"],
                }
            },
        )

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a GitHub issue."""
        try:
            issue_number = int(ticket_id)
        except ValueError:
            return []

        params = {
            "per_page": min(limit, 100),
            "page": (offset // limit) + 1 if limit > 0 else 1,
        }

        try:
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
                params=params,
            )
            response.raise_for_status()

            comments = []
            for comment_data in response.json():
                comments.append(
                    Comment(
                        id=str(comment_data["id"]),
                        ticket_id=ticket_id,
                        author=comment_data["user"]["login"],
                        content=comment_data["body"],
                        created_at=datetime.fromisoformat(
                            comment_data["created_at"].replace("Z", "+00:00")
                        ),
                        metadata={
                            "github": {
                                "id": comment_data["id"],
                                "url": comment_data["html_url"],
                                "author_avatar": comment_data["user"]["avatar_url"],
                            }
                        },
                    )
                )

            return comments
        except httpx.HTTPError:
            return []

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current rate limit status."""
        response = await self.client.get("/rate_limit")
        response.raise_for_status()
        return response.json()

    async def create_milestone(self, epic: Epic) -> Epic:
        """Create a GitHub milestone as an Epic."""
        milestone_data = {
            "title": epic.title,
            "description": epic.description or "",
            "state": "open" if epic.state != TicketState.CLOSED else "closed",
        }

        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/milestones", json=milestone_data
        )
        response.raise_for_status()

        created_milestone = response.json()

        return Epic(
            id=str(created_milestone["number"]),
            title=created_milestone["title"],
            description=created_milestone["description"],
            state=(
                TicketState.OPEN
                if created_milestone["state"] == "open"
                else TicketState.CLOSED
            ),
            created_at=datetime.fromisoformat(
                created_milestone["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                created_milestone["updated_at"].replace("Z", "+00:00")
            ),
            metadata={
                "github": {
                    "number": created_milestone["number"],
                    "url": created_milestone["html_url"],
                    "open_issues": created_milestone["open_issues"],
                    "closed_issues": created_milestone["closed_issues"],
                }
            },
        )

    async def get_milestone(self, milestone_number: int) -> Optional[Epic]:
        """Get a GitHub milestone as an Epic."""
        try:
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()

            milestone = response.json()

            return Epic(
                id=str(milestone["number"]),
                title=milestone["title"],
                description=milestone["description"],
                state=(
                    TicketState.OPEN
                    if milestone["state"] == "open"
                    else TicketState.CLOSED
                ),
                created_at=datetime.fromisoformat(
                    milestone["created_at"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    milestone["updated_at"].replace("Z", "+00:00")
                ),
                metadata={
                    "github": {
                        "number": milestone["number"],
                        "url": milestone["html_url"],
                        "open_issues": milestone["open_issues"],
                        "closed_issues": milestone["closed_issues"],
                    }
                },
            )
        except httpx.HTTPError:
            return None

    async def list_milestones(
        self, state: str = "open", limit: int = 10, offset: int = 0
    ) -> builtins.list[Epic]:
        """List GitHub milestones as Epics."""
        params = {
            "state": state,
            "per_page": min(limit, 100),
            "page": (offset // limit) + 1 if limit > 0 else 1,
        }

        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/milestones", params=params
        )
        response.raise_for_status()

        epics = []
        for milestone in response.json():
            epics.append(
                Epic(
                    id=str(milestone["number"]),
                    title=milestone["title"],
                    description=milestone["description"],
                    state=(
                        TicketState.OPEN
                        if milestone["state"] == "open"
                        else TicketState.CLOSED
                    ),
                    created_at=datetime.fromisoformat(
                        milestone["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        milestone["updated_at"].replace("Z", "+00:00")
                    ),
                    metadata={
                        "github": {
                            "number": milestone["number"],
                            "url": milestone["html_url"],
                            "open_issues": milestone["open_issues"],
                            "closed_issues": milestone["closed_issues"],
                        }
                    },
                )
            )

        return epics

    async def link_to_pull_request(self, issue_number: int, pr_number: int) -> bool:
        """Link an issue to a pull request using keywords."""
        # This is typically done through PR description keywords like "fixes #123"
        # We can add a comment to track the link
        comment = f"Linked to PR #{pr_number}"

        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json={"body": comment},
        )

        return response.status_code == 201

    async def create_pull_request(
        self,
        ticket_id: str,
        base_branch: str = "main",
        head_branch: Optional[str] = None,
        title: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
    ) -> dict[str, Any]:
        """Create a pull request linked to an issue.

        Args:
            ticket_id: Issue number to link the PR to
            base_branch: Target branch for the PR (default: main)
            head_branch: Source branch name (auto-generated if not provided)
            title: PR title (uses ticket title if not provided)
            body: PR description (auto-generated with issue link if not provided)
            draft: Create as draft PR

        Returns:
            Dictionary with PR details including number, url, and branch

        """
        try:
            issue_number = int(ticket_id)
        except ValueError:
            raise ValueError(f"Invalid issue number: {ticket_id}")

        # Get the issue details
        issue = await self.read(ticket_id)
        if not issue:
            raise ValueError(f"Issue #{ticket_id} not found")

        # Auto-generate branch name if not provided
        if not head_branch:
            # Create branch name from issue number and title
            # e.g., "123-fix-authentication-bug"
            safe_title = "-".join(
                issue.title.lower()
                .replace("[", "")
                .replace("]", "")
                .replace("#", "")
                .replace("/", "-")
                .replace("\\", "-")
                .split()[:5]  # Limit to 5 words
            )
            head_branch = f"{issue_number}-{safe_title}"

        # Auto-generate title if not provided
        if not title:
            # Include issue number in PR title
            title = f"[#{issue_number}] {issue.title}"

        # Auto-generate body if not provided
        if not body:
            body = f"""## Summary

This PR addresses issue #{issue_number}.

**Issue:** #{issue_number} - {issue.title}
**Link:** {issue.metadata.get('github', {}).get('url', '')}

## Description

{issue.description or 'No description provided.'}

## Changes

- [ ] Implementation details to be added

## Testing

- [ ] Tests have been added/updated
- [ ] All tests pass

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated if needed

Fixes #{issue_number}
"""

        # Check if the head branch exists
        try:
            branch_response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/branches/{head_branch}"
            )
            branch_exists = branch_response.status_code == 200
        except httpx.HTTPError:
            branch_exists = False

        if not branch_exists:
            # Get the base branch SHA
            base_response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/branches/{base_branch}"
            )
            base_response.raise_for_status()
            base_sha = base_response.json()["commit"]["sha"]

            # Create the new branch
            ref_response = await self.client.post(
                f"/repos/{self.owner}/{self.repo}/git/refs",
                json={
                    "ref": f"refs/heads/{head_branch}",
                    "sha": base_sha,
                },
            )

            if ref_response.status_code != 201:
                # Branch might already exist on remote, try to use it
                pass

        # Create the pull request
        pr_data = {
            "title": title,
            "body": body,
            "head": head_branch,
            "base": base_branch,
            "draft": draft,
        }

        pr_response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/pulls", json=pr_data
        )

        if pr_response.status_code == 422:
            # PR might already exist, try to get it
            search_response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/pulls",
                params={
                    "head": f"{self.owner}:{head_branch}",
                    "base": base_branch,
                    "state": "open",
                },
            )

            if search_response.status_code == 200:
                existing_prs = search_response.json()
                if existing_prs:
                    pr = existing_prs[0]
                    return {
                        "number": pr["number"],
                        "url": pr["html_url"],
                        "api_url": pr["url"],
                        "branch": head_branch,
                        "state": pr["state"],
                        "draft": pr.get("draft", False),
                        "title": pr["title"],
                        "existing": True,
                        "linked_issue": issue_number,
                    }

            raise ValueError(f"Failed to create PR: {pr_response.text}")

        pr_response.raise_for_status()
        pr = pr_response.json()

        # Add a comment to the issue about the PR
        await self.add_comment(
            Comment(
                ticket_id=ticket_id,
                content=f"Pull request #{pr['number']} has been created: {pr['html_url']}",
                author="system",
            )
        )

        return {
            "number": pr["number"],
            "url": pr["html_url"],
            "api_url": pr["url"],
            "branch": head_branch,
            "state": pr["state"],
            "draft": pr.get("draft", False),
            "title": pr["title"],
            "linked_issue": issue_number,
        }

    async def link_existing_pull_request(
        self,
        ticket_id: str,
        pr_url: str,
    ) -> dict[str, Any]:
        """Link an existing pull request to a ticket.

        Args:
            ticket_id: Issue number to link the PR to
            pr_url: GitHub PR URL to link

        Returns:
            Dictionary with link status and PR details

        """
        try:
            issue_number = int(ticket_id)
        except ValueError:
            raise ValueError(f"Invalid issue number: {ticket_id}")

        # Parse PR URL to extract owner, repo, and PR number
        # Expected format: https://github.com/owner/repo/pull/123
        import re

        pr_pattern = r"github\.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.search(pr_pattern, pr_url)

        if not match:
            raise ValueError(f"Invalid GitHub PR URL format: {pr_url}")

        pr_owner, pr_repo, pr_number = match.groups()

        # Verify the PR is from the same repository
        if pr_owner != self.owner or pr_repo != self.repo:
            raise ValueError(
                f"PR must be from the same repository ({self.owner}/{self.repo})"
            )

        # Get PR details
        pr_response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        )

        if pr_response.status_code == 404:
            raise ValueError(f"Pull request #{pr_number} not found")

        pr_response.raise_for_status()
        pr = pr_response.json()

        # Update PR body to include issue reference if not already present
        current_body = pr.get("body", "")
        issue_ref = f"#{issue_number}"

        if issue_ref not in current_body:
            # Add issue reference to the body
            updated_body = current_body or ""
            if updated_body:
                updated_body += "\n\n"
            updated_body += f"Related to #{issue_number}"

            # Update the PR
            update_response = await self.client.patch(
                f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}",
                json={"body": updated_body},
            )
            update_response.raise_for_status()

        # Add a comment to the issue about the PR
        await self.add_comment(
            Comment(
                ticket_id=ticket_id,
                content=f"Linked to pull request #{pr_number}: {pr_url}",
                author="system",
            )
        )

        return {
            "success": True,
            "pr_number": pr["number"],
            "pr_url": pr["html_url"],
            "pr_title": pr["title"],
            "pr_state": pr["state"],
            "linked_issue": issue_number,
            "message": f"Successfully linked PR #{pr_number} to issue #{issue_number}",
        }

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self.client.aclose()


# Register the adapter
AdapterRegistry.register("github", GitHubAdapter)
