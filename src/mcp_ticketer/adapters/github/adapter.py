"""GitHub adapter implementation using REST API v3 and GraphQL API v4."""

from __future__ import annotations

import builtins
import logging
import re
import subprocess
from datetime import date, datetime
from pathlib import Path
from typing import Any

import httpx

from ...cache.memory import MemoryCache
from ...core.adapter import BaseAdapter
from ...core.env_loader import load_adapter_config, validate_adapter_config
from ...core.models import (
    Comment,
    Epic,
    Milestone,
    Priority,
    Project,
    ProjectScope,
    ProjectState,
    ProjectStatistics,
    SearchQuery,
    Task,
    TicketState,
)
from ...core.registry import AdapterRegistry
from .client import GitHubClient
from .mappers import (
    map_github_issue_to_task,
    map_github_milestone_to_epic,
    map_github_milestone_to_milestone,
    map_github_projectv2_to_project,
)
from .queries import (
    CREATE_PROJECT_MUTATION,
    DELETE_PROJECT_MUTATION,
    GET_PROJECT_BY_ID_QUERY,
    GET_PROJECT_ITERATIONS,
    GET_PROJECT_QUERY,
    ISSUE_FRAGMENT,
    LIST_PROJECTS_QUERY,
    SEARCH_ISSUES,
    UPDATE_PROJECT_MUTATION,
)
from .types import (
    GitHubStateMapping,
    extract_state_from_issue,
    get_github_state,
    get_priority_from_labels,
    get_priority_label,
    get_state_label,
)

logger = logging.getLogger(__name__)


def _get_gh_cli_token() -> str | None:
    """Get GitHub token from gh CLI as a fallback.

    Returns:
        GitHub token from gh CLI, or None if gh is not available or fails.

    """
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            token = result.stdout.strip()
            logger.debug("Retrieved GitHub token from gh CLI")
            return token
        else:
            logger.debug(
                f"gh CLI failed: returncode={result.returncode}, "
                f"stderr={result.stderr.strip()}"
            )
            return None
    except FileNotFoundError:
        logger.debug("gh CLI not found in PATH")
        return None
    except subprocess.TimeoutExpired:
        logger.debug("gh CLI timeout after 5 seconds")
        return None
    except Exception as e:
        logger.debug(f"Failed to get token from gh CLI: {e}")
        return None


def _resolve_github_token(config: dict[str, Any]) -> str | None:
    """Resolve GitHub token from multiple sources.

    Tries in order:
    1. Provided config (api_key or token)
    2. Environment variables (GITHUB_TOKEN, etc.)
    3. gh CLI (gh auth token)

    Args:
        config: Configuration dictionary with potential token values

    Returns:
        Resolved GitHub token, or None if not found

    """
    # Try config first (already includes environment variable resolution)
    token = config.get("api_key") or config.get("token")
    if token:
        logger.debug("Using GitHub token from config/environment")
        return token

    # Fallback to gh CLI
    token = _get_gh_cli_token()
    if token:
        logger.info("Using GitHub token from gh CLI")
        return token

    logger.warning(
        "No GitHub token found. Tried: config, environment variables, gh CLI"
    )
    return None


class GitHubAdapter(BaseAdapter[Task]):
    """Adapter for GitHub Issues tracking system."""

    def __init__(self, config: dict[str, Any]):
        """Initialize GitHub adapter.

        Args:
        ----
            config: Configuration with:
                - token: GitHub PAT (or GITHUB_TOKEN env var, or gh CLI fallback)
                - owner: Repository owner (or GITHUB_OWNER env var)
                - repo: Repository name (or GITHUB_REPO env var)
                - api_url: Optional API URL for GitHub Enterprise
                - use_projects_v2: Enable Projects v2 (default: False)
                - custom_priority_scheme: Custom priority label mapping
                - labels_ttl: Label cache TTL in seconds (default: 300.0)

        """
        super().__init__(config)

        # Load configuration with environment variable resolution
        full_config = load_adapter_config("github", config)

        # Validate required configuration
        missing_keys = validate_adapter_config("github", full_config)
        if missing_keys:
            missing = ", ".join(missing_keys)
            raise ValueError(
                f"GitHub adapter missing required configuration: {missing}"
            )

        # Resolve authentication token from multiple sources
        # (config, environment variables, gh CLI)
        self.token = _resolve_github_token(full_config)

        # Get repository information
        self.owner = full_config.get("owner")
        self.repo = full_config.get("repo")

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

        # Initialize GitHub API client
        self.gh_client = GitHubClient(
            token=self.token,
            owner=self.owner,
            repo=self.repo,
            api_url=self.api_url,
            timeout=30.0,
        )

        # Keep legacy client reference for backward compatibility
        # TODO: Gradually migrate all direct self.client usage to self.gh_client
        self.client = self.gh_client.client
        self.headers = self.gh_client.headers
        self.graphql_url = self.gh_client.graphql_url

        # Initialize TTL-based cache
        self._labels_ttl = config.get("labels_ttl", 300.0)  # 5 min default
        self._labels_cache = MemoryCache(default_ttl=self._labels_ttl)
        self._milestones_cache: list[dict[str, Any]] | None = None

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that required credentials are present.

        Returns:
        -------
            (is_valid, error_message) - Tuple of validation result and error message

        """
        if not self.token:
            return (
                False,
                "GITHUB_TOKEN is required. Set it in .env.local, environment, "
                "or authenticate with 'gh auth login'.",
            )
        if not self.owner:
            return (
                False,
                "GitHub owner is required. Set GITHUB_OWNER in .env.local "
                "or configure with 'mcp-ticketer init --adapter github "
                "--github-owner <owner>'",
            )
        if not self.repo:
            return (
                False,
                "GitHub repo is required. Set GITHUB_REPO in .env.local "
                "or configure with 'mcp-ticketer init --adapter github "
                "--github-repo <repo>'",
            )
        return True, ""

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Map universal states to GitHub states (delegated to types module)."""
        return {state: get_github_state(state) for state in TicketState}

    def _get_state_label(self, state: TicketState) -> str | None:
        """Get the label name for extended states (delegated to types module)."""
        return get_state_label(state)

    def _get_priority_from_labels(self, labels: list[str]) -> Priority:
        """Extract priority from issue labels (delegated to types module)."""
        return get_priority_from_labels(labels, self.custom_priority_scheme)

    def _get_priority_label(self, priority: Priority) -> str:
        """Get label name for a priority level (delegated to types module)."""
        return get_priority_label(priority, self.custom_priority_scheme)

    def _milestone_to_epic(self, milestone: dict[str, Any]) -> Epic:
        """Convert GitHub milestone to Epic model (delegated to mappers module)."""
        return map_github_milestone_to_epic(milestone)

    def _extract_state_from_issue(self, issue: dict[str, Any]) -> TicketState:
        """Extract ticket state from GitHub issue data (delegated to types module)."""
        return extract_state_from_issue(issue)

    def _task_from_github_issue(self, issue: dict[str, Any]) -> Task:
        """Convert GitHub issue to universal Task (delegated to mappers module)."""
        return map_github_issue_to_task(issue, self.custom_priority_scheme)

    async def _ensure_label_exists(
        self, label_name: str, color: str = "0366d6"
    ) -> bool:
        """Ensure a label exists in the repository.

        Args:
            label_name: Name of the label to ensure exists
            color: Hex color code (without #) for the label

        Returns:
            True if label exists or was created successfully, False otherwise
        """
        cache_key = "github_labels"
        cached_labels = await self._labels_cache.get(cache_key)

        if cached_labels is None:
            try:
                response = await self.client.get(
                    f"/repos/{self.owner}/{self.repo}/labels"
                )
                response.raise_for_status()
                cached_labels = response.json()
                await self._labels_cache.set(cache_key, cached_labels)
            except Exception as e:
                logger.warning(
                    f"Failed to fetch labels cache for {self.owner}/{self.repo}: {e}"
                )
                return False

        # Check if label exists
        existing_labels = [label["name"].lower() for label in cached_labels]
        if label_name.lower() not in existing_labels:
            # Create the label
            response = await self.client.post(
                f"/repos/{self.owner}/{self.repo}/labels",
                json={"name": label_name, "color": color},
            )

            if response.status_code == 201:
                # Successfully created
                cached_labels.append(response.json())
                await self._labels_cache.set(cache_key, cached_labels)
                return True
            elif response.status_code == 422:
                # Label already exists (race condition)
                # Another process created it between our check and create
                logger.info(
                    f"Label '{label_name}' already exists in {self.owner}/{self.repo} "
                    "(created by another process)"
                )
                return True
            elif response.status_code == 403:
                # Permission denied
                logger.warning(
                    f"Permission denied creating label '{label_name}' in "
                    f"{self.owner}/{self.repo}: insufficient permissions"
                )
                return False
            else:
                # Other error
                logger.warning(
                    f"Failed to create label '{label_name}' in {self.owner}/{self.repo}: "
                    f"status {response.status_code}"
                )
                return False

        # Label already exists
        return True

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
        failed_labels: list[str] = []

        # Add state label if needed
        state_label = self._get_state_label(ticket.state)
        if state_label:
            labels.append(state_label)
            if not await self._ensure_label_exists(state_label, "fbca04"):
                failed_labels.append(state_label)

        # Add priority label
        priority_label = self._get_priority_label(ticket.priority)
        labels.append(priority_label)
        if not await self._ensure_label_exists(priority_label, "d73a4a"):
            failed_labels.append(priority_label)

        # Ensure all labels exist
        for label in labels:
            if not await self._ensure_label_exists(label):
                if label not in failed_labels:
                    failed_labels.append(label)

        # Log warning if any labels failed to create
        if failed_labels:
            logger.warning(
                f"Failed to ensure existence of labels {failed_labels} in "
                f"{self.owner}/{self.repo}. Issue will still be created with available labels."
            )

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

    async def read(self, ticket_id: str) -> Task | Epic | None:
        """Read a GitHub issue OR milestone by number with unified find.

        Tries to find the entity in the following order:
        1. Issue (most common case) - returns Task
        2. Milestone (project/epic) - returns Epic

        Args:
        ----
            ticket_id: GitHub issue number or milestone number (as string)

        Returns:
        -------
            Task if issue found,
            Epic if milestone found,
            None if not found as either type

        Examples:
        --------
            >>> # Read issue #123
            >>> task = await adapter.read("123")
            >>> isinstance(task, Task)  # True
            >>>
            >>> # Read milestone #5
            >>> epic = await adapter.read("5")
            >>> isinstance(epic, Epic)  # True (if 5 is milestone, not issue)

        """
        # Validate credentials before attempting operation
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            entity_number = int(ticket_id)
        except ValueError:
            return None

        # Try reading as Issue first (most common case)
        try:
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/issues/{entity_number}"
            )
            if response.status_code == 200:
                response.raise_for_status()
                issue = response.json()
                logger.debug(f"Found GitHub entity as Issue: {ticket_id}")
                return self._task_from_github_issue(issue)
            elif response.status_code == 404:
                # Not found as issue, will try milestone next
                logger.debug(f"Not found as Issue ({ticket_id}), trying Milestone")
        except httpx.HTTPError as e:
            logger.debug(f"Error reading as Issue ({ticket_id}): {e}")

        # Try reading as Milestone (Epic)
        try:
            milestone = await self.get_milestone(entity_number)
            if milestone:
                logger.debug(f"Found GitHub entity as Milestone: {ticket_id}")
                return milestone
        except Exception as e:
            logger.debug(f"Error reading as Milestone ({ticket_id}): {e}")

        # Not found as either Issue or Milestone
        logger.warning(f"GitHub entity not found: {ticket_id}")
        return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
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
        failed_labels: list[str] = []

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
                if not await self._ensure_label_exists(state_label, "fbca04"):
                    failed_labels.append(state_label)
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
                all_priority_labels.extend([label.lower() for label in labels])

            labels_to_update = [
                label
                for label in labels_to_update
                if label.lower() not in all_priority_labels
                and not re.match(r"^P[0-3]$", label, re.IGNORECASE)
            ]

            # Add new priority label
            priority_label = self._get_priority_label(new_priority)
            if not await self._ensure_label_exists(priority_label, "d73a4a"):
                failed_labels.append(priority_label)
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
                if not await self._ensure_label_exists(tag):
                    if tag not in failed_labels:
                        failed_labels.append(tag)

            update_data["labels"] = preserved_labels + updates["tags"]

        # Log warning if any labels failed to create
        if failed_labels:
            logger.warning(
                f"Failed to ensure existence of labels {failed_labels} in "
                f"{self.owner}/{self.repo}. Issue will still be updated with available labels."
            )

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
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> list[Task]:
        """List GitHub issues with filters."""
        # Build query parameters
        params: dict[str, Any] = {
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

        # Updated after filter
        if query.updated_after:
            # Convert datetime to ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ)
            # GitHub search supports updated:>YYYY-MM-DD or updated:>=YYYY-MM-DD
            iso_date = query.updated_after.isoformat()
            # Extract just the date part for GitHub search (YYYY-MM-DD)
            date_str = iso_date.split("T")[0] if "T" in iso_date else iso_date
            search_parts.append(f"updated:>={date_str}")

        # Build final search query
        github_query = " ".join(search_parts)

        # Use GraphQL for better search capabilities
        # Note: SEARCH_ISSUES already includes ISSUE_FRAGMENT (pre-composed)
        full_query = SEARCH_ISSUES

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
    ) -> Task | None:
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
        except ValueError as e:
            raise ValueError(f"Invalid issue number: {comment.ticket_id}") from e

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
        return self._milestone_to_epic(created_milestone)

    async def get_milestone(self, milestone_number: int) -> Epic | None:
        """Get a GitHub milestone as an Epic."""
        try:
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()

            milestone = response.json()
            return self._milestone_to_epic(milestone)
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

        return [self._milestone_to_epic(milestone) for milestone in response.json()]

    async def delete_epic(self, epic_id: str) -> bool:
        """Delete a GitHub milestone (Epic).

        Args:
        ----
            epic_id: Milestone number (not ID) as a string

        Returns:
        -------
            True if successfully deleted, False otherwise

        Raises:
        ------
            ValueError: If credentials are invalid or epic_id is not a valid number

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Extract milestone number from epic_id
            milestone_number = int(epic_id)
        except ValueError as e:
            raise ValueError(
                f"Invalid milestone number '{epic_id}'. GitHub milestones use numeric IDs."
            ) from e

        try:
            # Delete milestone using REST API
            response = await self.client.delete(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
            )

            # GitHub returns 204 No Content on successful deletion
            if response.status_code == 204:
                return True

            # Handle 404 errors gracefully
            if response.status_code == 404:
                return False

            # Other errors - raise for visibility
            response.raise_for_status()
            return True

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Milestone not found
                return False
            # Re-raise other HTTP errors
            raise ValueError(f"Failed to delete milestone: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to delete milestone: {e}") from e

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
        head_branch: str | None = None,
        title: str | None = None,
        body: str | None = None,
        draft: bool = False,
    ) -> dict[str, Any]:
        """Create a pull request linked to an issue.

        Args:
        ----
            ticket_id: Issue number to link the PR to
            base_branch: Target branch for the PR (default: main)
            head_branch: Source branch name (auto-generated if not provided)
            title: PR title (uses ticket title if not provided)
            body: PR description (auto-generated with issue link if not provided)
            draft: Create as draft PR

        Returns:
        -------
            Dictionary with PR details including number, url, and branch

        """
        try:
            issue_number = int(ticket_id)
        except ValueError as e:
            raise ValueError(f"Invalid issue number: {ticket_id}") from e

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
**Link:** {issue.metadata.get("github", {}).get("url", "")}

## Description

{issue.description or "No description provided."}

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
        pr_msg = f"Pull request #{pr['number']} has been created: {pr['html_url']}"
        await self.add_comment(
            Comment(
                ticket_id=ticket_id,
                content=pr_msg,
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
        ----
            ticket_id: Issue number to link the PR to
            pr_url: GitHub PR URL to link

        Returns:
        -------
            Dictionary with link status and PR details

        """
        try:
            issue_number = int(ticket_id)
        except ValueError as e:
            raise ValueError(f"Invalid issue number: {ticket_id}") from e

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

    async def get_collaborators(self) -> builtins.list[dict[str, Any]]:
        """Get repository collaborators."""
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/collaborators"
        )
        response.raise_for_status()
        return response.json()

    async def get_current_user(self) -> dict[str, Any] | None:
        """Get current authenticated user information."""
        response = await self.client.get("/user")
        response.raise_for_status()
        return response.json()

    async def list_labels(self) -> builtins.list[dict[str, Any]]:
        """List all labels available in the repository.

        Returns:
        -------
            List of label dictionaries with 'id', 'name', and 'color' fields

        """
        cache_key = "github_labels"
        cached = await self._labels_cache.get(cache_key)
        if cached is not None:
            return cached

        response = await self.client.get(f"/repos/{self.owner}/{self.repo}/labels")
        response.raise_for_status()
        labels = response.json()

        # Transform to standardized format
        standardized_labels = [
            {"id": label["name"], "name": label["name"], "color": label["color"]}
            for label in labels
        ]

        await self._labels_cache.set(cache_key, standardized_labels)
        return standardized_labels

    async def update_milestone(
        self, milestone_number: int, updates: dict[str, Any]
    ) -> Epic | None:
        """Update a GitHub milestone (Epic).

        Args:
        ----
            milestone_number: Milestone number (not ID)
            updates: Dictionary with fields to update:
                - title: Milestone title
                - description: Milestone description (supports markdown)
                - state: TicketState value (maps to open/closed)
                - target_date: Due date in ISO format

        Returns:
        -------
            Updated Epic object or None if not found

        Raises:
        ------
            ValueError: If no fields to update
            httpx.HTTPError: If API request fails

        """
        update_data = {}

        # Map title directly
        if "title" in updates:
            update_data["title"] = updates["title"]

        # Map description (supports markdown)
        if "description" in updates:
            update_data["description"] = updates["description"]

        # Map state to GitHub milestone state
        if "state" in updates:
            state = updates["state"]
            if isinstance(state, TicketState):
                # GitHub only has open/closed
                update_data["state"] = (
                    "closed"
                    if state in [TicketState.DONE, TicketState.CLOSED]
                    else "open"
                )
            else:
                update_data["state"] = state

        # Map target_date to due_on
        if "target_date" in updates:
            # GitHub expects ISO 8601 format
            target_date = updates["target_date"]
            if isinstance(target_date, str):
                update_data["due_on"] = target_date
            elif hasattr(target_date, "isoformat"):
                update_data["due_on"] = target_date.isoformat()

        if not update_data:
            raise ValueError("At least one field must be updated")

        # Make API request
        response = await self.client.patch(
            f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}",
            json=update_data,
        )
        response.raise_for_status()

        # Convert response to Epic
        milestone_data = response.json()
        return self._milestone_to_epic(milestone_data)

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update a GitHub epic (milestone) by ID or number.

        This is a convenience wrapper around update_milestone() that accepts
        either a milestone number or the epic ID from the Epic object.

        Args:
        ----
            epic_id: Epic ID (e.g., "milestone-5") or milestone number as string
            updates: Dictionary with fields to update

        Returns:
        -------
            Updated Epic object or None if not found

        """
        # Extract milestone number from ID
        if epic_id.startswith("milestone-"):
            milestone_number = int(epic_id.replace("milestone-", ""))
        else:
            milestone_number = int(epic_id)

        return await self.update_milestone(milestone_number, updates)

    async def add_attachment_to_issue(
        self, issue_number: int, file_path: str, comment: str | None = None
    ) -> dict[str, Any]:
        """Attach file to GitHub issue via comment.

        GitHub doesn't have direct file attachment API. This method:
        1. Creates a comment with the file reference
        2. Returns metadata about the attachment

        Note: GitHub's actual file upload in comments requires browser-based
        drag-and-drop or git-lfs. This method creates a placeholder comment
        that users can edit to add actual file attachments through the UI.

        Args:
        ----
            issue_number: Issue number
            file_path: Path to file to attach
            comment: Optional comment text (defaults to "Attached: {filename}")

        Returns:
        -------
            Dictionary with comment data and file info

        Raises:
        ------
            FileNotFoundError: If file doesn't exist
            ValueError: If file too large (>25 MB)

        Note:
        ----
            GitHub file size limit: 25 MB
            Supported: Images, videos, documents

        """
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Check file size (25 MB limit)
        file_size = file_path_obj.stat().st_size
        if file_size > 25 * 1024 * 1024:  # 25 MB
            raise ValueError(
                f"File too large: {file_size} bytes (max 25 MB). "
                "Upload file externally and reference URL instead."
            )

        # Prepare comment body
        comment_body = comment or f"📎 Attached: `{file_path_obj.name}`"
        comment_body += (
            f"\n\n*Note: File `{file_path_obj.name}` ({file_size} bytes) "
            "needs to be manually uploaded through GitHub UI or referenced via URL.*"
        )

        # Create comment with file reference
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/issues/{issue_number}/comments",
            json={"body": comment_body},
        )
        response.raise_for_status()

        comment_data = response.json()

        return {
            "comment_id": comment_data["id"],
            "comment_url": comment_data["html_url"],
            "filename": file_path_obj.name,
            "file_size": file_size,
            "note": "File reference created. Upload file manually through GitHub UI.",
        }

    async def add_attachment_reference_to_milestone(
        self, milestone_number: int, file_url: str, description: str
    ) -> Epic | None:
        """Add file reference to milestone description.

        Since GitHub milestones don't support direct file attachments,
        this method appends a markdown link to the milestone description.

        Args:
        ----
            milestone_number: Milestone number
            file_url: URL to the file (external or GitHub-hosted)
            description: Description/title for the file

        Returns:
        -------
            Updated Epic object

        Example:
        -------
            await adapter.add_attachment_reference_to_milestone(
                5,
                "https://example.com/spec.pdf",
                "Technical Specification"
            )
            # Appends to description: "[Technical Specification](https://example.com/spec.pdf)"

        """
        # Get current milestone
        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/milestones/{milestone_number}"
        )
        response.raise_for_status()
        milestone = response.json()

        # Append file reference to description
        current_desc = milestone.get("description", "")
        attachment_markdown = f"\n\n📎 [{description}]({file_url})"
        new_description = current_desc + attachment_markdown

        # Update milestone with new description
        return await self.update_milestone(
            milestone_number, {"description": new_description}
        )

    async def add_attachment(
        self, ticket_id: str, file_path: str, description: str | None = None
    ) -> dict[str, Any]:
        """Add attachment to GitHub ticket (issue or milestone).

        This method routes to appropriate attachment method based on ticket type:
        - Issues: Creates comment with file reference
        - Milestones: Not supported, raises NotImplementedError with guidance

        Args:
        ----
            ticket_id: Ticket identifier (issue number or milestone ID)
            file_path: Path to file to attach
            description: Optional description

        Returns:
        -------
            Attachment metadata

        Raises:
        ------
            NotImplementedError: For milestones (no native support)
            FileNotFoundError: If file doesn't exist

        """
        # Determine ticket type from ID format
        if ticket_id.startswith("milestone-"):
            raise NotImplementedError(
                "GitHub milestones do not support direct file attachments. "
                "Workaround: Upload file externally and use "
                "add_attachment_reference_to_milestone() to add URL to description."
            )

        # Assume it's an issue number
        issue_number = int(ticket_id.replace("issue-", ""))
        return await self.add_attachment_to_issue(issue_number, file_path, description)

    async def list_cycles(
        self, project_id: str | None = None, limit: int = 50
    ) -> builtins.list[dict[str, Any]]:
        """List GitHub Project iterations (cycles/sprints).

        GitHub Projects V2 uses "iterations" for sprint/cycle functionality.
        Requires a project node ID (not numeric ID).

        Args:
        ----
            project_id: GitHub Project V2 node ID (e.g., 'PVT_kwDOABcdefgh').
                       This is required for Projects V2. Can be found in the
                       project's GraphQL ID.
            limit: Maximum number of iterations to return (default: 50)

        Returns:
        -------
            List of iteration dictionaries with fields:
                - id: Iteration node ID
                - title: Iteration title/name
                - startDate: Start date (ISO format)
                - duration: Duration in days
                - endDate: Calculated end date (startDate + duration)

        Raises:
        ------
            ValueError: If project_id not provided or credentials invalid
            httpx.HTTPError: If GraphQL query fails

        Example:
        -------
            >>> iterations = await adapter.list_cycles(
            ...     project_id="PVT_kwDOABCD1234",
            ...     limit=10
            ... )
            >>> for iteration in iterations:
            ...     print(f"{iteration['title']}: {iteration['startDate']} ({iteration['duration']} days)")

        Note:
        ----
            GitHub Projects V2 node IDs can be obtained via the GitHub GraphQL API.
            This is different from project numbers shown in the UI.

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        if not project_id:
            raise ValueError(
                "project_id is required for GitHub Projects V2. "
                "Provide a project node ID (e.g., 'PVT_kwDOABcdefgh'). "
                "Find this via GraphQL API: query { organization(login: 'org') { "
                "projectV2(number: 1) { id } } }"
            )

        # Execute GraphQL query to fetch iterations
        query = GET_PROJECT_ITERATIONS
        variables = {"projectId": project_id, "first": min(limit, 100), "after": None}

        try:
            result = await self._graphql_request(query, variables)

            # Extract iterations from response
            project_node = result.get("node")
            if not project_node:
                raise ValueError(
                    f"Project not found with ID: {project_id}. "
                    "Verify the project ID is correct and you have access."
                )

            iterations_data = project_node.get("iterations", {})
            iteration_nodes = iterations_data.get("nodes", [])

            # Transform to standard format and calculate end dates
            iterations = []
            for iteration in iteration_nodes:
                # Calculate end date from start date + duration
                start_date = iteration.get("startDate")
                duration = iteration.get("duration", 0)

                end_date = None
                if start_date and duration:
                    from datetime import datetime, timedelta

                    start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                    end_dt = start_dt + timedelta(days=duration)
                    end_date = end_dt.isoformat()

                iterations.append(
                    {
                        "id": iteration["id"],
                        "title": iteration.get("title", ""),
                        "startDate": start_date,
                        "duration": duration,
                        "endDate": end_date,
                    }
                )

            return iterations

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            raise ValueError(f"Failed to list project iterations: {e}") from e

    async def get_issue_status(self, issue_number: int) -> dict[str, Any]:
        """Get rich status information for a GitHub issue.

        GitHub issues have binary states (open/closed) natively. Extended status
        tracking uses labels following the status:* convention (e.g., status:in_progress).

        Args:
        ----
            issue_number: GitHub issue number

        Returns:
        -------
            Dictionary with comprehensive status information:
                - state: Native GitHub state ('open' or 'closed')
                - status_label: Extended status from labels (in_progress, blocked, etc.)
                - extended_state: Universal TicketState value
                - labels: All issue labels
                - state_reason: For closed issues (completed or not_planned)
                - metadata: Additional issue metadata (assignees, milestone, etc.)

        Raises:
        ------
            ValueError: If credentials invalid or issue not found
            httpx.HTTPError: If API request fails

        Example:
        -------
            >>> status = await adapter.get_issue_status(123)
            >>> print(f"Issue #{status['number']}: {status['extended_state']}")
            >>> print(f"Native state: {status['state']}")
            >>> if status['status_label']:
            ...     print(f"Label-based status: {status['status_label']}")

        Note:
        ----
            GitHub's binary state model is extended via labels:
            - open + no label = OPEN
            - open + status:in-progress = IN_PROGRESS
            - open + status:blocked = BLOCKED
            - closed = CLOSED (check state_reason for details)

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            # Fetch issue via REST API
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/issues/{issue_number}"
            )

            if response.status_code == 404:
                raise ValueError(f"Issue #{issue_number} not found")

            response.raise_for_status()
            issue = response.json()

            # Extract labels
            labels = [label["name"] for label in issue.get("labels", [])]

            # Derive extended state from issue data
            extended_state = self._extract_state_from_issue(issue)

            # Find status label if present
            status_label = None
            for _state, label_name in GitHubStateMapping.STATE_LABELS.items():
                if label_name.lower() in [label.lower() for label in labels]:
                    status_label = label_name
                    break

            # Build comprehensive status response
            status_info = {
                "number": issue["number"],
                "state": issue["state"],  # 'open' or 'closed'
                "status_label": status_label,  # Label-based extended status
                "extended_state": extended_state.value,  # Universal TicketState
                "labels": labels,
                "state_reason": issue.get(
                    "state_reason"
                ),  # 'completed' or 'not_planned'
                "metadata": {
                    "title": issue["title"],
                    "url": issue["html_url"],
                    "assignees": [
                        assignee["login"] for assignee in issue.get("assignees", [])
                    ],
                    "milestone": (
                        issue.get("milestone", {}).get("title")
                        if issue.get("milestone")
                        else None
                    ),
                    "created_at": issue["created_at"],
                    "updated_at": issue["updated_at"],
                    "closed_at": issue.get("closed_at"),
                },
            }

            return status_info

        except ValueError:
            # Re-raise validation errors
            raise
        except httpx.HTTPError as e:
            raise ValueError(f"Failed to get issue status: {e}") from e

    async def list_issue_statuses(self) -> builtins.list[dict[str, Any]]:
        """List available issue statuses in GitHub.

        Returns all possible issue statuses including native GitHub states
        and extended label-based states.

        Returns:
        -------
            List of status dictionaries with fields:
                - name: Status name (e.g., 'open', 'in_progress', 'closed')
                - type: Status type ('native' or 'extended')
                - label: Associated label name (for extended statuses)
                - description: Human-readable description
                - category: Status category (open, in_progress, done, etc.)

        Example:
        -------
            >>> statuses = await adapter.list_issue_statuses()
            >>> for status in statuses:
            ...     print(f"{status['name']}: {status['description']}")
            ...     if status['type'] == 'extended':
            ...         print(f"  Label: {status['label']}")

        Note:
        ----
            GitHub natively supports only 'open' and 'closed' states.
            Extended statuses are implemented via labels following the
            status:* naming convention (e.g., status:in-progress).

        """
        # Define native GitHub states
        statuses = [
            {
                "name": "open",
                "type": "native",
                "label": None,
                "description": "Issue is open and not yet completed",
                "category": "open",
            },
            {
                "name": "closed",
                "type": "native",
                "label": None,
                "description": "Issue is closed (completed or not planned)",
                "category": "done",
            },
        ]

        # Add extended label-based states
        for state, label_name in GitHubStateMapping.STATE_LABELS.items():
            statuses.append(
                {
                    "name": state.value,
                    "type": "extended",
                    "label": label_name,
                    "description": f"Issue is {state.value.replace('_', ' ')} (tracked via label)",
                    "category": state.value,
                }
            )

        return statuses

    async def list_project_labels(
        self, milestone_number: int | None = None
    ) -> builtins.list[dict[str, Any]]:
        """List labels used in a GitHub milestone (project/epic).

        If milestone_number is provided, returns only labels used by issues
        in that milestone. Otherwise, returns all repository labels.

        Args:
        ----
            milestone_number: Optional milestone number to filter labels.
                            If None, returns all repository labels.

        Returns:
        -------
            List of label dictionaries with fields:
                - id: Label identifier (name)
                - name: Label name
                - color: Label color (hex without #)
                - description: Label description (if available)
                - usage_count: Number of issues using this label (if milestone filtered)

        Example:
        -------
            >>> # Get all repository labels
            >>> all_labels = await adapter.list_project_labels()
            >>> print(f"Repository has {len(all_labels)} labels")
            >>>
            >>> # Get labels used in milestone 5
            >>> milestone_labels = await adapter.list_project_labels(milestone_number=5)
            >>> for label in milestone_labels:
            ...     print(f"{label['name']}: used by {label['usage_count']} issues")

        Note:
        ----
            Labels are repository-scoped in GitHub, not milestone-scoped.
            When filtering by milestone, this method queries issues in that
            milestone and extracts their unique labels.

        """
        # Validate credentials
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            if milestone_number is None:
                # Return all repository labels (delegate to existing method)
                return await self.list_labels()

            # Query issues in the milestone
            params = {
                "milestone": str(milestone_number),
                "state": "all",
                "per_page": 100,
            }

            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/issues", params=params
            )
            response.raise_for_status()
            issues = response.json()

            # Extract unique labels from issues
            label_usage = {}  # {label_name: {data, count}}
            for issue in issues:
                # Skip pull requests
                if "pull_request" in issue:
                    continue

                for label in issue.get("labels", []):
                    label_name = label["name"]
                    if label_name not in label_usage:
                        label_usage[label_name] = {
                            "id": label_name,
                            "name": label_name,
                            "color": label["color"],
                            "description": label.get("description", ""),
                            "usage_count": 0,
                        }
                    label_usage[label_name]["usage_count"] += 1

            # Convert to list and sort by usage count
            labels = list(label_usage.values())
            labels.sort(key=lambda x: x["usage_count"], reverse=True)

            return labels

        except httpx.HTTPError as e:
            raise ValueError(f"Failed to list project labels: {e}") from e

    # ========================================================================
    # New Milestone Methods (Phase 2 - GitHub Native Support)
    # ========================================================================

    async def milestone_create(
        self,
        name: str,
        target_date: date | None = None,
        labels: list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Milestone:
        """Create milestone using GitHub Milestones API.

        GitHub milestones are repository-scoped and natively supported.

        Args:
        ----
            name: Milestone name/title
            target_date: Target completion date (optional)
            labels: Labels for local storage (GitHub doesn't store labels on milestones)
            description: Milestone description
            project_id: Project ID (ignored for GitHub, repo-scoped)

        Returns:
        -------
            Created Milestone object

        Raises:
        ------
            ValueError: If repository is not configured
            httpx.HTTPError: If API request fails

        """
        from datetime import datetime as dt

        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        # GitHub API expects ISO 8601 datetime for due_on
        due_on = None
        if target_date:
            due_on = dt.combine(target_date, dt.min.time()).isoformat() + "Z"

        milestone_data = {
            "title": name,
            "description": description,
            "state": "open",
        }

        if due_on:
            milestone_data["due_on"] = due_on

        # Create milestone via GitHub API
        response = await self.client.post(
            f"/repos/{self.owner}/{self.repo}/milestones",
            json=milestone_data,
        )
        response.raise_for_status()

        gh_milestone = response.json()

        # Convert to Milestone model
        milestone = self._github_milestone_to_milestone(gh_milestone, labels)

        # Save to local storage for label tracking
        from pathlib import Path

        from ...core.milestone_manager import MilestoneManager

        config_dir = Path.home() / ".mcp-ticketer"
        manager = MilestoneManager(config_dir)
        manager.save_milestone(milestone)

        logger.info(f"Created GitHub milestone: {milestone.id} ({milestone.name})")
        return milestone

    async def milestone_get(self, milestone_id: str) -> Milestone | None:
        """Get milestone by ID (milestone number in GitHub).

        Args:
        ----
            milestone_id: Milestone number as string

        Returns:
        -------
            Milestone object or None if not found

        Raises:
        ------
            ValueError: If repository is not configured

        """
        from pathlib import Path

        from ...core.milestone_manager import MilestoneManager

        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        try:
            # milestone_id is the milestone number in GitHub
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_id}"
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            gh_milestone = response.json()

            # Load labels from local storage
            config_dir = Path.home() / ".mcp-ticketer"
            manager = MilestoneManager(config_dir)
            local_milestone = manager.get_milestone(milestone_id)
            labels = local_milestone.labels if local_milestone else []

            return self._github_milestone_to_milestone(gh_milestone, labels)

        except httpx.HTTPError as e:
            logger.error(f"Failed to get milestone {milestone_id}: {e}")
            return None

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> list[Milestone]:
        """List milestones from GitHub repository.

        Note: project_id is ignored for GitHub (repo-scoped).

        Args:
        ----
            project_id: Project ID (ignored, GitHub is repo-scoped)
            state: Filter by state (open, active, closed, completed)

        Returns:
        -------
            List of Milestone objects

        Raises:
        ------
            ValueError: If repository is not configured

        """
        from pathlib import Path

        from ...core.milestone_manager import MilestoneManager

        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        # Map our states to GitHub states
        github_state = "all"
        if state in ["open", "active"]:
            github_state = "open"
        elif state in ["completed", "closed"]:
            github_state = "closed"

        params = {
            "state": github_state,
            "sort": "due_on",
            "direction": "asc",
            "per_page": 100,
        }

        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/milestones",
            params=params,
        )
        response.raise_for_status()

        # Load labels from local storage
        config_dir = Path.home() / ".mcp-ticketer"
        manager = MilestoneManager(config_dir)

        milestones = []
        for gh_milestone in response.json():
            milestone_id = str(gh_milestone["number"])
            local_milestone = manager.get_milestone(milestone_id)
            labels = local_milestone.labels if local_milestone else []

            milestone = self._github_milestone_to_milestone(gh_milestone, labels)
            milestones.append(milestone)

        logger.info(
            f"Listed {len(milestones)} GitHub milestones (state={github_state})"
        )
        return milestones

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: date | None = None,
        state: str | None = None,
        labels: list[str] | None = None,
        description: str | None = None,
    ) -> Milestone | None:
        """Update milestone properties.

        Args:
        ----
            milestone_id: Milestone number as string
            name: New milestone name
            target_date: New target date
            state: New state (open, closed)
            labels: New labels (stored locally)
            description: New description

        Returns:
        -------
            Updated Milestone object or None if not found

        Raises:
        ------
            ValueError: If repository is not configured

        """
        from datetime import datetime as dt
        from pathlib import Path

        from ...core.milestone_manager import MilestoneManager

        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        update_data = {}

        if name:
            update_data["title"] = name
        if description is not None:
            update_data["description"] = description
        if target_date:
            due_on = dt.combine(target_date, dt.min.time()).isoformat() + "Z"
            update_data["due_on"] = due_on
        if state:
            # Map our states to GitHub states
            if state in ["completed", "closed"]:
                update_data["state"] = "closed"
            elif state in ["open", "active"]:
                update_data["state"] = "open"

        if not update_data and labels is None:
            raise ValueError("At least one field must be updated")

        # Update milestone via GitHub API
        if update_data:
            response = await self.client.patch(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_id}",
                json=update_data,
            )
            response.raise_for_status()
            gh_milestone = response.json()
        else:
            # Only labels updated, fetch current milestone
            response = await self.client.get(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_id}"
            )
            response.raise_for_status()
            gh_milestone = response.json()

        # Update labels in local storage
        config_dir = Path.home() / ".mcp-ticketer"
        manager = MilestoneManager(config_dir)

        if labels is not None:
            milestone = self._github_milestone_to_milestone(gh_milestone, labels)
            manager.save_milestone(milestone)
            logger.info(f"Updated GitHub milestone: {milestone_id} (including labels)")
            return milestone

        # Load existing labels
        local_milestone = manager.get_milestone(milestone_id)
        existing_labels = local_milestone.labels if local_milestone else []

        milestone = self._github_milestone_to_milestone(gh_milestone, existing_labels)
        logger.info(f"Updated GitHub milestone: {milestone_id}")
        return milestone

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Delete milestone from GitHub repository.

        Args:
        ----
            milestone_id: Milestone number as string

        Returns:
        -------
            True if deleted, False if not found

        Raises:
        ------
            ValueError: If repository is not configured

        """
        from pathlib import Path

        from ...core.milestone_manager import MilestoneManager

        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        try:
            response = await self.client.delete(
                f"/repos/{self.owner}/{self.repo}/milestones/{milestone_id}"
            )

            # GitHub returns 204 No Content on successful deletion
            if response.status_code == 204:
                # Remove from local storage
                config_dir = Path.home() / ".mcp-ticketer"
                manager = MilestoneManager(config_dir)
                manager.delete_milestone(milestone_id)

                logger.info(f"Deleted GitHub milestone: {milestone_id}")
                return True

            # Handle 404 errors gracefully
            if response.status_code == 404:
                logger.warning(f"Milestone {milestone_id} not found for deletion")
                return False

            response.raise_for_status()
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to delete milestone {milestone_id}: {e}")
            return False

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get issues in milestone.

        Args:
        ----
            milestone_id: Milestone number as string
            state: Filter by state (open, closed, all)

        Returns:
        -------
            List of issue dictionaries

        Raises:
        ------
            ValueError: If repository is not configured

        """
        if not self.repo:
            raise ValueError("Repository required for GitHub milestone operations")

        params = {
            "milestone": milestone_id,
            "state": state or "all",
            "per_page": 100,
        }

        response = await self.client.get(
            f"/repos/{self.owner}/{self.repo}/issues",
            params=params,
        )
        response.raise_for_status()

        # Convert GitHub issues to our format
        issues = []
        for gh_issue in response.json():
            # Skip pull requests (GitHub includes them in issues endpoint)
            if "pull_request" in gh_issue:
                continue

            issues.append(
                {
                    "id": str(gh_issue["number"]),
                    "identifier": f"#{gh_issue['number']}",
                    "title": gh_issue["title"],
                    "state": gh_issue["state"],
                    "labels": [label["name"] for label in gh_issue.get("labels", [])],
                    "created_at": gh_issue["created_at"],
                    "updated_at": gh_issue["updated_at"],
                }
            )

        logger.info(f"Retrieved {len(issues)} issues from milestone {milestone_id}")
        return issues

    async def search_users(self, query: str) -> list[dict[str, Any]]:
        """Search for users by name or email.

        Args:
        ----
            query: Search query (name or email)

        Returns:
        -------
            Empty list (user search not yet implemented for GitHub)

        Note:
        ----
            GitHub user search requires additional API permissions and implementation.
            Returns empty list for now. Future enhancement: implement GitHub user search API.

        """
        logger.info("search_users called but not yet implemented for GitHub adapter")
        return []

    def _github_milestone_to_milestone(
        self,
        gh_milestone: dict[str, Any],
        labels: list[str] | None = None,
    ) -> Milestone:
        """Convert GitHub Milestone to universal Milestone model (delegated to mappers module)."""
        return map_github_milestone_to_milestone(gh_milestone, self.repo, labels)

    # =============================================================================
    # GitHub Projects V2 Operations (Week 2: Core CRUD)
    # =============================================================================

    async def project_list(
        self,
        owner: str | None = None,
        scope: ProjectScope = ProjectScope.ORGANIZATION,
        state: ProjectState | None = None,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Project]:
        """List projects for an organization or user.

        Args:
        ----
            owner: Organization or user login (defaults to configured owner)
            scope: Project scope (ORGANIZATION or USER)
            state: Filter by project state (ACTIVE, COMPLETED, ARCHIVED)
            limit: Maximum number of projects to return (default: 10)
            cursor: Pagination cursor for next page

        Returns:
        -------
            List of Project objects

        Raises:
        ------
            ValueError: If owner not provided and not configured
            RuntimeError: If GraphQL query fails

        Example:
        -------
            projects = await adapter.project_list(owner="myorg", limit=20)

        """
        # Validate owner (use self.owner if not provided)
        owner = owner or self.owner
        if not owner:
            raise ValueError("Owner required for GitHub project operations")

        # Build GraphQL variables
        variables = {
            "owner": owner,
            "first": limit,
            "after": cursor,
        }

        try:
            # Execute LIST_PROJECTS_QUERY
            data = await self.gh_client.execute_graphql(
                query=LIST_PROJECTS_QUERY,
                variables=variables,
            )

            # Parse response and extract projects array
            org_data = data.get("organization")
            if not org_data:
                logger.warning(f"Organization {owner} not found")
                return []

            projects_data = org_data.get("projectsV2", {})
            project_nodes = projects_data.get("nodes", [])

            # Map each project using mapper
            projects = []
            for project_data in project_nodes:
                project = map_github_projectv2_to_project(project_data, owner)

                # Filter by state if provided (post-query filtering)
                if state is None or project.state == state:
                    projects.append(project)

            logger.info(f"Retrieved {len(projects)} projects for {owner}")
            return projects

        except Exception as e:
            logger.error(f"Failed to list projects for {owner}: {e}")
            raise RuntimeError(f"Failed to list projects: {e}") from e

    async def project_get(
        self,
        project_id: str,
        owner: str | None = None,
    ) -> Project | None:
        """Get a single project by ID or number.

        Automatically detects ID format:
        - Node ID format: "PVT_kwDOABCD..." (starts with PVT_)
        - Number format: "123" (numeric string)

        Args:
        ----
            project_id: Project node ID or number
            owner: Organization or user login (defaults to configured owner)

        Returns:
        -------
            Project object if found, None otherwise

        Raises:
        ------
            ValueError: If owner not provided for number-based lookup
            RuntimeError: If GraphQL query fails

        Example:
        -------
            # By number
            project = await adapter.project_get("42", owner="myorg")

            # By node ID
            project = await adapter.project_get("PVT_kwDOABCD1234")

        """
        try:
            # Auto-detect ID format
            if project_id.startswith("PVT_"):
                # Use GET_PROJECT_BY_ID_QUERY for node IDs
                data = await self.gh_client.execute_graphql(
                    query=GET_PROJECT_BY_ID_QUERY,
                    variables={"projectId": project_id},
                )

                project_data = data.get("node")
                if not project_data:
                    logger.warning(f"Project {project_id} not found")
                    return None

                # Extract owner from project data
                owner_data = project_data.get("owner", {})
                owner_login = owner_data.get("login", owner or self.owner)

                project = map_github_projectv2_to_project(project_data, owner_login)
                logger.info(f"Retrieved project {project_id} by node ID")
                return project

            else:
                # Numeric ID - requires owner
                owner = owner or self.owner
                if not owner:
                    raise ValueError("Owner required for number-based project lookup")

                # Convert to integer
                try:
                    project_number = int(project_id)
                except ValueError as e:
                    raise ValueError(f"Invalid project ID format: {project_id}") from e

                # Use GET_PROJECT_QUERY for number-based lookup
                data = await self.gh_client.execute_graphql(
                    query=GET_PROJECT_QUERY,
                    variables={"owner": owner, "number": project_number},
                )

                org_data = data.get("organization")
                if not org_data:
                    logger.warning(f"Organization {owner} not found")
                    return None

                project_data = org_data.get("projectV2")
                if not project_data:
                    logger.warning(f"Project {project_id} not found for {owner}")
                    return None

                project = map_github_projectv2_to_project(project_data, owner)
                logger.info(f"Retrieved project {project_id} by number")
                return project

        except Exception as e:
            logger.error(f"Failed to get project {project_id}: {e}")
            raise RuntimeError(f"Failed to get project: {e}") from e

    async def project_create(
        self,
        title: str,
        description: str | None = None,
        owner: str | None = None,
        scope: ProjectScope = ProjectScope.ORGANIZATION,
    ) -> Project:
        """Create a new GitHub Projects V2 project.

        Args:
        ----
            title: Project title (required)
            description: Project description (optional)
            owner: Organization or user login (defaults to configured owner)
            scope: Project scope (ORGANIZATION or USER)

        Returns:
        -------
            Newly created Project object

        Raises:
        ------
            ValueError: If owner not provided
            RuntimeError: If creation fails (permissions, etc.)

        Example:
        -------
            project = await adapter.project_create(
                title="Q4 Features",
                description="New features for Q4 2025",
                owner="myorg"
            )

        """
        # Validate owner
        owner = owner or self.owner
        if not owner:
            raise ValueError("Owner required for GitHub project creation")

        try:
            # Get owner node ID (query organization)
            # We need to fetch the organization/user to get its node ID
            org_query = """
                query GetOrgId($login: String!) {
                    organization(login: $login) {
                        id
                    }
                }
            """

            org_data = await self.gh_client.execute_graphql(
                query=org_query,
                variables={"login": owner},
            )

            org = org_data.get("organization")
            if not org:
                raise ValueError(f"Organization {owner} not found")

            owner_id = org.get("id")

            # Execute CREATE_PROJECT_MUTATION
            data = await self.gh_client.execute_graphql(
                query=CREATE_PROJECT_MUTATION,
                variables={
                    "ownerId": owner_id,
                    "title": title,
                },
            )

            # Parse response and extract created project
            create_result = data.get("createProjectV2", {})
            project_data = create_result.get("projectV2")

            if not project_data:
                raise RuntimeError("Project creation returned no data")

            # Map using mapper
            project = map_github_projectv2_to_project(project_data, owner)

            # Update description if provided (requires separate mutation)
            if description:
                await self.project_update(
                    project_id=project.id,
                    description=description,
                )

            logger.info(f"Created project: {project.id} ({title})")
            return project

        except Exception as e:
            logger.error(f"Failed to create project '{title}': {e}")
            raise RuntimeError(f"Failed to create project: {e}") from e

    async def project_update(
        self,
        project_id: str,
        title: str | None = None,
        description: str | None = None,
        readme: str | None = None,
        state: ProjectState | None = None,
    ) -> Project | None:
        """Update project metadata.

        Supports partial updates - only provided fields are updated.

        Args:
        ----
            project_id: Project node ID (PVT_...)
            title: New project title (optional)
            description: New project description (optional)
            readme: New project readme (optional)
            state: New project state (optional)

        Returns:
        -------
            Updated Project object

        Raises:
        ------
            ValueError: If project_id invalid or no fields to update
            RuntimeError: If update fails

        Example:
        -------
            project = await adapter.project_update(
                project_id="PVT_kwDOABCD1234",
                title="Updated Title",
                state=ProjectState.COMPLETED
            )

        """
        # Validate at least one field is provided
        if not any([title, description, readme, state]):
            raise ValueError("At least one field must be provided for update")

        try:
            # Build mutation variables (only include provided fields)
            variables: dict[str, Any] = {"projectId": project_id}

            if title is not None:
                variables["title"] = title

            if description is not None:
                variables["shortDescription"] = description

            if readme is not None:
                variables["readme"] = readme

            # Convert ProjectState to GitHub boolean
            if state is not None:
                # GitHub only has open/closed via the 'closed' boolean
                if state in (ProjectState.COMPLETED, ProjectState.ARCHIVED):
                    variables["closed"] = True
                elif state == ProjectState.ACTIVE:
                    variables["closed"] = False
                # PLANNED and CANCELLED don't have direct mappings
                # We'll keep the project open for PLANNED

            # Execute UPDATE_PROJECT_MUTATION
            data = await self.gh_client.execute_graphql(
                query=UPDATE_PROJECT_MUTATION,
                variables=variables,
            )

            # Parse response
            update_result = data.get("updateProjectV2", {})
            project_data = update_result.get("projectV2")

            if not project_data:
                logger.warning(f"Project {project_id} not found for update")
                return None

            # Extract owner from project data
            owner_data = project_data.get("owner", {})
            owner = owner_data.get("login", self.owner)

            # Map using mapper
            project = map_github_projectv2_to_project(project_data, owner)

            logger.info(f"Updated project: {project_id}")
            return project

        except Exception as e:
            logger.error(f"Failed to update project {project_id}: {e}")
            raise RuntimeError(f"Failed to update project: {e}") from e

    async def project_delete(
        self,
        project_id: str,
        hard_delete: bool = False,
    ) -> bool:
        """Delete a project.

        By default performs soft delete (closes project).
        Set hard_delete=True to permanently delete.

        Args:
        ----
            project_id: Project node ID (PVT_...)
            hard_delete: If True, permanently delete; if False, soft delete (close)

        Returns:
        -------
            True if successful, False otherwise

        Raises:
        ------
            RuntimeError: If deletion fails

        Example:
        -------
            # Soft delete (close)
            await adapter.project_delete("PVT_kwDOABCD1234")

            # Hard delete (permanent)
            await adapter.project_delete("PVT_kwDOABCD1234", hard_delete=True)

        """
        try:
            if hard_delete:
                # Hard delete using DELETE_PROJECT_MUTATION
                logger.warning(f"Permanently deleting project {project_id}")

                data = await self.gh_client.execute_graphql(
                    query=DELETE_PROJECT_MUTATION,
                    variables={"projectId": project_id},
                )

                delete_result = data.get("deleteProjectV2", {})
                deleted_project = delete_result.get("projectV2")

                if deleted_project:
                    logger.info(f"Permanently deleted project: {project_id}")
                    return True
                else:
                    logger.warning(f"Failed to delete project {project_id}")
                    return False

            else:
                # Soft delete by setting public=false and closed=true
                data = await self.gh_client.execute_graphql(
                    query=UPDATE_PROJECT_MUTATION,
                    variables={
                        "projectId": project_id,
                        "public": False,
                        "closed": True,
                    },
                )

                update_result = data.get("updateProjectV2", {})
                updated_project = update_result.get("projectV2")

                if updated_project:
                    logger.info(f"Soft deleted (closed) project: {project_id}")
                    return True
                else:
                    logger.warning(f"Failed to close project {project_id}")
                    return False

        except Exception as e:
            logger.error(f"Failed to delete project {project_id}: {e}")
            raise RuntimeError(f"Failed to delete project: {e}") from e

    async def invalidate_label_cache(self) -> None:
        """Manually invalidate the label cache.

        Useful when labels are modified externally or when you need
        to force a refresh of cached label data.
        """
        await self._labels_cache.clear()

    # =============================================================================
    # GitHub Projects V2 Issue Operations (Week 3)
    # =============================================================================

    async def project_add_issue(
        self,
        project_id: str,
        issue_id: str,
    ) -> bool:
        """Add an issue to a GitHub Projects V2 project.

        Args:
        ----
            project_id: Project node ID (PVT_kwDOABCD...)
            issue_id: Issue node ID (I_kwDOABCD...) or issue number with owner/repo

        Returns:
        -------
            True if issue was added successfully

        Raises:
        ------
            ValueError: If project_id or issue_id is invalid
            RuntimeError: If GraphQL mutation fails

        Example:
        -------
            # Add by issue node ID
            success = await adapter.project_add_issue(
                project_id="PVT_kwDOABCD1234",
                issue_id="I_kwDOABCD5678"
            )

            # Add by issue number (requires owner/repo context)
            success = await adapter.project_add_issue(
                project_id="PVT_kwDOABCD1234",
                issue_id="owner/repo#123"
            )

        Note:
        ----
            GitHub's addProjectV2ItemById mutation requires:
            - projectId: Project node ID
            - contentId: Issue/PR node ID (not item ID)

        """
        # Validate project_id format
        if not project_id or not project_id.startswith("PVT_"):
            raise ValueError(
                f"Invalid project_id: {project_id}. "
                "Project ID must start with 'PVT_' (e.g., PVT_kwDOABCD1234)"
            )

        # Validate issue_id is provided
        if not issue_id:
            raise ValueError("issue_id is required")

        # If issue_id is in "owner/repo#number" format, resolve to node ID
        content_id = issue_id
        if "#" in issue_id and "/" in issue_id:
            # Parse owner/repo#number format
            try:
                repo_part, number_str = issue_id.rsplit("#", 1)
                owner, repo = repo_part.split("/")
                issue_number = int(number_str)

                # Query GitHub to get issue node ID
                issue_query = """
                    query GetIssueNodeId($owner: String!, $repo: String!, $number: Int!) {
                        repository(owner: $owner, name: $repo) {
                            issue(number: $number) {
                                id
                            }
                        }
                    }
                """

                result = await self._graphql_request(
                    issue_query,
                    {"owner": owner, "repo": repo, "number": issue_number},
                )

                repo_data = result.get("repository")
                if not repo_data:
                    raise ValueError(f"Repository {owner}/{repo} not found")

                issue_data = repo_data.get("issue")
                if not issue_data:
                    raise ValueError(
                        f"Issue #{issue_number} not found in {owner}/{repo}"
                    )

                content_id = issue_data["id"]
                logger.debug(f"Resolved issue {issue_id} to node ID {content_id}")

            except ValueError:
                # Re-raise ValueError as-is (already has good message)
                raise
            except (KeyError, TypeError) as e:
                raise ValueError(
                    f"Invalid issue_id format: {issue_id}. "
                    "Expected 'owner/repo#number' or issue node ID (I_kwDO...)"
                ) from e

        # Validate issue node ID format
        if not content_id.startswith("I_") and not content_id.startswith("PR_"):
            raise ValueError(
                f"Invalid issue_id: {content_id}. "
                "Issue ID must start with 'I_' or 'PR_' (e.g., I_kwDOABCD5678)"
            )

        try:
            # Execute ADD_PROJECT_ITEM_MUTATION
            from .queries import ADD_PROJECT_ITEM_MUTATION

            data = await self.gh_client.execute_graphql(
                query=ADD_PROJECT_ITEM_MUTATION,
                variables={
                    "projectId": project_id,
                    "contentId": content_id,
                },
            )

            # Check for successful addition
            add_result = data.get("addProjectV2ItemById", {})
            item_data = add_result.get("item")

            if item_data:
                logger.info(
                    f"Successfully added issue {issue_id} to project {project_id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to add issue {issue_id} to project {project_id}: No item returned"
                )
                return False

        except Exception as e:
            error_msg = str(e).lower()

            # Handle "already exists" errors gracefully
            if "already exists" in error_msg or "duplicate" in error_msg:
                logger.info(f"Issue {issue_id} already exists in project {project_id}")
                return True

            # Log and re-raise other errors
            logger.error(f"Failed to add issue {issue_id} to project {project_id}: {e}")
            raise RuntimeError(f"Failed to add issue to project: {e}") from e

    async def project_remove_issue(
        self,
        project_id: str,
        item_id: str,
    ) -> bool:
        """Remove an issue from a GitHub Projects V2 project.

        Args:
        ----
            project_id: Project node ID (PVT_kwDOABCD...)
            item_id: Project item ID (PVTI_kwDOABCD...) NOT issue ID

        Returns:
        -------
            True if issue was removed successfully

        Raises:
        ------
            ValueError: If project_id or item_id is invalid
            RuntimeError: If GraphQL mutation fails

        Example:
        -------
            success = await adapter.project_remove_issue(
                project_id="PVT_kwDOABCD1234",
                item_id="PVTI_kwDOABCD5678"
            )

        Note:
        ----
            Requires the project ITEM ID (PVTI_*), not the issue ID (I_*).
            Use project_get_issues() to find the item ID for an issue.

        """
        # Validate project_id format
        if not project_id or not project_id.startswith("PVT_"):
            raise ValueError(
                f"Invalid project_id: {project_id}. "
                "Project ID must start with 'PVT_' (e.g., PVT_kwDOABCD1234)"
            )

        # Validate item_id format
        if not item_id or not item_id.startswith("PVTI_"):
            raise ValueError(
                f"Invalid item_id: {item_id}. "
                "Item ID must start with 'PVTI_' (e.g., PVTI_kwDOABCD5678). "
                "Note: This is the project item ID, not the issue ID. "
                "Use project_get_issues() to get the item ID for an issue."
            )

        try:
            # Execute REMOVE_PROJECT_ITEM_MUTATION
            from .queries import REMOVE_PROJECT_ITEM_MUTATION

            data = await self.gh_client.execute_graphql(
                query=REMOVE_PROJECT_ITEM_MUTATION,
                variables={
                    "projectId": project_id,
                    "itemId": item_id,
                },
            )

            # Check for successful removal
            delete_result = data.get("deleteProjectV2Item", {})
            deleted_item_id = delete_result.get("deletedItemId")

            if deleted_item_id:
                logger.info(
                    f"Successfully removed item {item_id} from project {project_id}"
                )
                return True
            else:
                logger.warning(
                    f"Failed to remove item {item_id} from project {project_id}: "
                    "No deleted item ID returned"
                )
                return False

        except Exception as e:
            error_msg = str(e).lower()

            # Handle "not found" errors gracefully
            if "not found" in error_msg or "does not exist" in error_msg:
                logger.warning(
                    f"Item {item_id} not found in project {project_id} "
                    "(may have been already removed)"
                )
                return False

            # Log and re-raise other errors
            logger.error(
                f"Failed to remove item {item_id} from project {project_id}: {e}"
            )
            raise RuntimeError(f"Failed to remove issue from project: {e}") from e

    async def project_get_issues(
        self,
        project_id: str,
        state: str | None = None,
        limit: int = 10,
        cursor: str | None = None,
    ) -> list[Task]:
        """Get issues in a GitHub Projects V2 project.

        Args:
        ----
            project_id: Project node ID (PVT_kwDOABCD...)
            state: Filter by issue state ("OPEN", "CLOSED", None for all)
            limit: Maximum number of issues to return (default 10)
            cursor: Pagination cursor for next page

        Returns:
        -------
            List of Task objects representing issues in the project

        Raises:
        ------
            ValueError: If project_id is invalid
            RuntimeError: If GraphQL query fails

        Example:
        -------
            # Get all open issues
            issues = await adapter.project_get_issues(
                project_id="PVT_kwDOABCD1234",
                state="OPEN",
                limit=20
            )

            # Get next page
            issues = await adapter.project_get_issues(
                project_id="PVT_kwDOABCD1234",
                cursor=last_cursor
            )

        Note:
        ----
            Returns Task objects with additional project context:
            - task.metadata["project_item_id"]: ID for removal operations
            - task.metadata["project_number"]: Project number

        """
        # Validate project_id format
        if not project_id or not project_id.startswith("PVT_"):
            raise ValueError(
                f"Invalid project_id: {project_id}. "
                "Project ID must start with 'PVT_' (e.g., PVT_kwDOABCD1234)"
            )

        try:
            # Execute PROJECT_ITEMS_QUERY
            from .queries import PROJECT_ITEMS_QUERY

            data = await self.gh_client.execute_graphql(
                query=PROJECT_ITEMS_QUERY,
                variables={
                    "projectId": project_id,
                    "first": limit,
                    "after": cursor,
                },
            )

            # Parse response and extract items array
            project_node = data.get("node")
            if not project_node:
                logger.warning(f"Project {project_id} not found")
                return []

            items_data = project_node.get("items", {})
            item_nodes = items_data.get("nodes", [])

            # Filter items by content type (only "Issue", skip "PullRequest", "DraftIssue")
            tasks = []
            for item in item_nodes:
                content = item.get("content")
                if not content:
                    # Skip archived items without content
                    logger.debug(f"Skipping item {item.get('id')} without content")
                    continue

                content_type = content.get("__typename")

                # Only process Issues
                if content_type != "Issue":
                    logger.debug(f"Skipping {content_type} item {item.get('id')}")
                    continue

                # Map GitHub issue to Task using existing mapper
                from .mappers import map_github_issue_to_task

                # Convert GraphQL format to format expected by mapper
                issue_dict = {
                    "number": content.get("number"),
                    "title": content.get("title"),
                    "state": content.get("state", "").lower(),
                    "labels": content.get("labels", {}),
                    # Note: PROJECT_ITEMS_QUERY doesn't include all issue fields
                    # Only basic fields are available
                }

                task = map_github_issue_to_task(issue_dict, self.custom_priority_scheme)

                # Add project context to metadata
                if "github" not in task.metadata:
                    task.metadata["github"] = {}

                task.metadata["github"]["project_item_id"] = item["id"]
                task.metadata["github"]["project_id"] = project_id

                # Extract project number from project_id if needed
                # Project node ID format: PVT_kwDO... but we don't have number here
                # We'll need to query the project separately or store it

                tasks.append(task)

            # Filter by state if provided (post-query filtering)
            if state:
                state_lower = state.lower()
                tasks = [
                    task
                    for task in tasks
                    if (isinstance(task.state, str) and task.state == state_lower)
                    or (
                        hasattr(task.state, "value") and task.state.value == state_lower
                    )
                    or (
                        state_lower == "open"
                        and (
                            (
                                isinstance(task.state, str)
                                and task.state
                                in ["open", "in_progress", "blocked", "waiting"]
                            )
                            or (
                                hasattr(task.state, "value")
                                and task.state.value
                                in ["open", "in_progress", "blocked", "waiting"]
                            )
                        )
                    )
                    or (
                        state_lower == "closed"
                        and (
                            (
                                isinstance(task.state, str)
                                and task.state in ["done", "closed"]
                            )
                            or (
                                hasattr(task.state, "value")
                                and task.state.value in ["done", "closed"]
                            )
                        )
                    )
                ]

            logger.info(
                f"Retrieved {len(tasks)} issues from project {project_id} "
                f"(filtered by state={state})"
            )

            return tasks

        except Exception as e:
            logger.error(f"Failed to get issues from project {project_id}: {e}")
            raise RuntimeError(f"Failed to get project issues: {e}") from e

    async def project_get_statistics(
        self,
        project_id: str,
    ) -> ProjectStatistics:
        """Get comprehensive statistics for a GitHub Projects V2 project.

        Calculates issue state breakdown, priority distribution, and health status
        by analyzing all issues in the project. Priority is determined from issue
        labels (priority:low, priority/medium, etc.), and blocked status is detected
        from "blocked" or "blocker" labels.

        Health Scoring Logic:
            - on_track: >70% complete AND <10% blocked
            - at_risk: >40% complete AND <30% blocked
            - off_track: Otherwise (low completion or high blocked rate)

        Args:
        ----
            project_id: Project node ID (PVT_kwDOABCD...)

        Returns:
        -------
            ProjectStatistics with metrics and health scoring

        Raises:
        ------
            ValueError: If project_id is invalid format
            RuntimeError: If statistics calculation fails

        Example:
        -------
            stats = await adapter.project_get_statistics("PVT_kwDOABCD1234")
            print(f"Health: {stats.health}, Progress: {stats.progress_percentage}%")
            print(f"Priority breakdown: H={stats.priority_high_count}, "
                  f"M={stats.priority_medium_count}")

        Note:
        ----
            Fetches up to 1000 issues for reasonable performance. For projects
            with >1000 issues, statistics may be based on a sample.

        """
        from ...core.models import ProjectStatistics

        # Validate project_id format
        if not project_id or not project_id.startswith("PVT_"):
            raise ValueError(
                f"Invalid project_id: {project_id}. "
                "Project ID must start with 'PVT_' (e.g., PVT_kwDOABCD1234)"
            )

        logger.debug(f"Calculating statistics for project {project_id}")

        try:
            # Fetch all issues (limit 1000 for reasonable performance)
            issues = await self.project_get_issues(project_id=project_id, limit=1000)
        except Exception as e:
            logger.error(f"Failed to fetch issues for statistics: {e}")
            raise RuntimeError(f"Failed to calculate project statistics: {e}") from e

        # Calculate basic counts
        total = len(issues)
        open_count = 0
        closed_count = 0
        in_progress_count = 0

        # Count by priority (from labels)
        priority_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        blocked_count = 0

        for issue in issues:
            # Count by state (GitHub only has OPEN/CLOSED)
            # We map based on state enum value
            state_value = (
                issue.state.value if hasattr(issue.state, "value") else str(issue.state)
            )

            if state_value in ["open", "in_progress", "blocked", "waiting"]:
                if state_value == "in_progress":
                    in_progress_count += 1
                else:
                    open_count += 1
            elif state_value in ["done", "closed"]:
                closed_count += 1
            else:
                # Default unrecognized states to open
                open_count += 1

            # Check tags (labels) for priority and blocked status
            for tag in issue.tags:
                tag_lower = tag.lower()

                # Priority detection (priority:high, priority/low, etc.)
                if "priority:" in tag_lower or "priority/" in tag_lower:
                    # Extract priority level
                    priority = (
                        tag_lower.replace("priority:", "")
                        .replace("priority/", "")
                        .strip()
                    )
                    if priority in priority_counts:
                        priority_counts[priority] += 1
                    elif "crit" in priority or "p0" in priority:
                        priority_counts["critical"] += 1
                    elif "high" in priority or "p1" in priority:
                        priority_counts["high"] += 1
                    elif "med" in priority or "p2" in priority:
                        priority_counts["medium"] += 1
                    elif "low" in priority or "p3" in priority:
                        priority_counts["low"] += 1

                # Blocked detection
                if "blocked" in tag_lower or "blocker" in tag_lower:
                    blocked_count += 1

        # Calculate health and progress
        if total == 0:
            health = "on_track"
            progress_pct = 0.0
        else:
            completed_pct = (closed_count / total) * 100
            blocked_pct = (blocked_count / total) * 100

            # Health scoring logic
            if completed_pct > 70 and blocked_pct < 10:
                health = "on_track"
            elif completed_pct > 40 and blocked_pct < 30:
                health = "at_risk"
            else:
                health = "off_track"

            progress_pct = completed_pct

        # Create statistics object
        stats = ProjectStatistics(
            total_count=total,
            open_count=open_count,
            in_progress_count=in_progress_count,
            completed_count=closed_count,
            blocked_count=blocked_count,
            priority_low_count=priority_counts["low"],
            priority_medium_count=priority_counts["medium"],
            priority_high_count=priority_counts["high"],
            priority_critical_count=priority_counts["critical"],
            health=health,
            progress_percentage=round(progress_pct, 1),
        )

        logger.info(
            f"Statistics for {project_id}: {total} issues, "
            f"{health} health, {progress_pct:.1f}% complete, "
            f"{blocked_count} blocked"
        )

        return stats

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self.client.aclose()


# Register the adapter
AdapterRegistry.register("github", GitHubAdapter)
