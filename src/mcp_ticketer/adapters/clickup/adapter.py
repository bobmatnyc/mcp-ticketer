"""Main ClickUpAdapter class for ClickUp REST API v2 integration.

Milestone support
-----------------
ClickUp has no native milestone primitive. ClickUp "Goals" are a separate
object with different semantics (they aggregate "targets"/key-results across
spaces, not a label-grouped set of issues with a target date), so they cannot
be mapped cleanly onto the universal ``Milestone`` model. All ``milestone_*``
methods therefore raise ``NotImplementedError`` with an explanatory message
rather than faking support. See the individual method docstrings.
"""

from __future__ import annotations

import builtins
import logging
import os
from datetime import datetime
from typing import Any

from ...core.adapter import BaseAdapter
from ...core.models import (
    Comment,
    Epic,
    Milestone,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from ...core.registry import AdapterRegistry
from .client import ClickUpClient
from .mappers import (
    map_clickup_comment_to_comment,
    map_clickup_list_to_epic,
    map_clickup_task_to_task,
    map_task_to_clickup_payload,
)
from .types import map_priority_to_clickup, resolve_state_to_status_name

logger = logging.getLogger(__name__)

# Message used by all milestone_* methods (ClickUp has no native milestones).
_MILESTONE_UNSUPPORTED = (
    "ClickUp has no native milestone concept; Goals differ semantically "
    "(target/key-result aggregation, not label-grouped issues with a due date) "
    "— not supported in v1."
)


class ClickUpAdapter(BaseAdapter[Task]):
    """Adapter for ClickUp task management using REST API v2.

    Provides integration with ClickUp's REST API, supporting the major ticket
    management operations:

    - CRUD operations for lists (epics) and tasks
    - Epic/Issue/Task hierarchy support
    - State transitions via per-list statuses
    - User assignment and tag management
    - Comment management

    Hierarchy Mapping:
    - Epic  -> ClickUp List
    - Issue -> ClickUp Task (in a list, no parent task)
    - Task  -> ClickUp Subtask (has a parent task)

    Note:
        Milestones are not supported (ClickUp has no native milestone object).
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize the ClickUp adapter.

        Args:
            config: Configuration with:
                - api_token / api_key: ClickUp personal token (``pk_...``) or
                  ``CLICKUP_API_TOKEN`` env var.
                - team_id / workspace_id: ClickUp workspace (team) id (optional;
                  also read from ``CLICKUP_TEAM_ID``).
                - list_id: default list id for task creation (optional; also read
                  from ``CLICKUP_LIST_ID``).
                - space_id / folder_id: optional scoping ids.
                - timeout: request timeout in seconds (default 30).
                - max_retries: maximum retry attempts (default 3).

        Raises:
            ValueError: If the required API token is missing.

        """
        # Set instance attributes before super().__init__ (which calls
        # _get_state_mapping, mirroring the Asana adapter ordering).
        self._team_id: str | None = None
        self._default_list_id: str | None = None
        self._space_id: str | None = None
        self._folder_id: str | None = None
        # Cache: list_id -> ordered list of status objects from GET /list/{id}.
        self._list_statuses_cache: dict[str, list[dict[str, Any]]] = {}
        self._initialized = False

        super().__init__(config)

        # Extract token from config or environment.
        self.api_token = (
            config.get("api_token")
            or config.get("api_key")
            or os.getenv("CLICKUP_API_TOKEN")
            or os.getenv("MCP_TICKETER_CLICKUP_API_TOKEN")
        )
        if not self.api_token:
            raise ValueError(
                "ClickUp API token is required (api_token or CLICKUP_API_TOKEN env var)"
            )

        # Strip an accidental "NAME=value" prefix (mirrors Asana hardening).
        if isinstance(self.api_token, str) and "=" in self.api_token:
            parts = self.api_token.split("=", 1)
            if len(parts) == 2 and parts[0].upper() in (
                "CLICKUP_API_TOKEN",
                "CLICKUP_TOKEN",
                "CLICKUP_API_KEY",
                "API_TOKEN",
                "API_KEY",
            ):
                self.api_token = parts[1]

        # Optional scoping configuration (config wins over env).
        self._team_id = (
            config.get("team_id")
            or config.get("workspace_id")
            or os.getenv("CLICKUP_TEAM_ID")
            or os.getenv("MCP_TICKETER_CLICKUP_TEAM_ID")
        )
        self._default_list_id = (
            config.get("list_id")
            or config.get("default_list_id")
            or os.getenv("CLICKUP_LIST_ID")
            or os.getenv("MCP_TICKETER_CLICKUP_LIST_ID")
        )
        self._space_id = config.get("space_id") or os.getenv("CLICKUP_SPACE_ID")
        self._folder_id = config.get("folder_id") or os.getenv("CLICKUP_FOLDER_ID")

        timeout = config.get("timeout", 30)
        max_retries = config.get("max_retries", 3)

        self.client = ClickUpClient(
            self.api_token, timeout=timeout, max_retries=max_retries
        )

    def _get_state_mapping(self) -> dict[TicketState, str]:
        """Get the mapping from universal states to ClickUp status categories.

        ClickUp statuses are defined per-list, so this mapping is only the
        coarse "type category" each universal state belongs to. The concrete
        per-list status NAME is resolved at write time against the target list's
        statuses (see ``_resolve_status_name``).

        Returns:
            Dictionary mapping ``TicketState`` to a ClickUp status type
            ("open", "custom", "done", "closed").

        """
        return {
            TicketState.OPEN: "open",
            TicketState.IN_PROGRESS: "custom",
            TicketState.READY: "custom",
            TicketState.TESTED: "custom",
            TicketState.DONE: "done",
            TicketState.WAITING: "custom",
            TicketState.BLOCKED: "custom",
            TicketState.CLOSED: "closed",
        }

    def validate_credentials(self) -> tuple[bool, str]:
        """Validate that the ClickUp API token is present.

        Returns:
            Tuple of (is_valid, error_message).

        """
        if not self.api_token:
            return False, "ClickUp API token is required"
        return True, ""

    async def initialize(self) -> None:
        """Initialize the adapter by verifying credentials and resolving the team."""
        if self._initialized:
            return

        try:
            if not await self.client.test_connection():
                raise ValueError("Failed to connect to ClickUp API - check credentials")

            # Resolve a default team (workspace) if none was provided.
            if not self._team_id:
                await self._resolve_team()

            self._initialized = True
            logger.info(
                "ClickUp adapter initialized (team_id=%s, default_list_id=%s)",
                self._team_id,
                self._default_list_id,
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize ClickUp adapter: {e}") from e

    async def _resolve_team(self) -> None:
        """Resolve the default team (workspace) id via ``GET /team``."""
        try:
            response = await self.client.get("/team")
            teams = response.get("teams", [])
            if teams:
                self._team_id = str(teams[0].get("id"))
                logger.info(
                    "Resolved ClickUp team: %s (id=%s)",
                    teams[0].get("name"),
                    self._team_id,
                )
            else:
                logger.warning("No ClickUp teams (workspaces) found for this token")
        except Exception as e:
            logger.warning("Failed to resolve ClickUp team: %s", e)

    # ------------------------------------------------------------------
    # Status / list helpers (the core of the ClickUp state-mapping work)
    # ------------------------------------------------------------------

    async def _load_list_statuses(self, list_id: str) -> list[dict[str, Any]]:
        """Load the ordered set of statuses configured for a ClickUp list.

        ClickUp statuses are per-list. ``GET /list/{list_id}`` returns a
        ``statuses`` array of objects shaped
        ``{"status": "in progress", "type": "custom", "orderindex": 1, ...}``.

        Args:
            list_id: ClickUp list id.

        Returns:
            List of status objects (empty list on failure).

        """
        try:
            list_obj = await self.client.get(f"/list/{list_id}")
            statuses = list_obj.get("statuses", [])
            if isinstance(statuses, list):
                return statuses
            return []
        except Exception as e:
            logger.warning("Failed to load statuses for list %s: %s", list_id, e)
            return []

    async def _get_list_statuses(self, list_id: str) -> list[dict[str, Any]]:
        """Get a list's statuses, loading and caching them on first access.

        Args:
            list_id: ClickUp list id.

        Returns:
            Ordered list of status objects.

        """
        if list_id not in self._list_statuses_cache:
            self._list_statuses_cache[list_id] = await self._load_list_statuses(list_id)
        return self._list_statuses_cache[list_id]

    async def _resolve_status_name(
        self, state: TicketState, list_id: str | None
    ) -> str | None:
        """Resolve a universal state to a concrete per-list status name.

        Args:
            state: Universal ticket state.
            list_id: Target ClickUp list id (None -> cannot resolve).

        Returns:
            A status name that exists in the list, or None if unresolvable.

        """
        if not list_id:
            return None
        statuses = await self._get_list_statuses(list_id)
        return resolve_state_to_status_name(state, statuses)

    async def _task_list_id(self, ticket_id: str) -> str | None:
        """Look up the list id a task belongs to (needed for status resolution).

        Args:
            ticket_id: ClickUp task id.

        Returns:
            The task's list id, or None if not found.

        """
        try:
            task = await self.client.get(f"/task/{ticket_id}")
            list_obj = task.get("list") or {}
            list_id = list_obj.get("id") if isinstance(list_obj, dict) else None
            return str(list_id) if list_id is not None else None
        except Exception as e:
            logger.error("Failed to look up list for task %s: %s", ticket_id, e)
            return None

    def _resolve_list_id_for_create(self, task: Task) -> str | None:
        """Determine which list a new task/issue should be created in.

        Resolution order:
        1. ``task.parent_epic`` (Epic == ClickUp List).
        2. The adapter's configured default list id.

        Subtasks (``task.parent_issue`` set) inherit the parent's list, so a
        list id is not strictly required for them; ClickUp still requires a list
        endpoint, so the default list is used as the creation endpoint and the
        ``parent`` field links it to the parent task.

        Args:
            task: Task being created.

        Returns:
            Target list id, or None if none can be determined.

        """
        if task.parent_epic:
            return str(task.parent_epic)
        if self._default_list_id:
            return str(self._default_list_id)
        return None

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    async def create(self, ticket: Epic | Task) -> Epic | Task:  # type: ignore[override]
        """Create a new ClickUp list (Epic) or task (Issue/Task).

        Args:
            ticket: Epic or Task to create.

        Returns:
            Created ticket with its id populated.

        Raises:
            ValueError: If creation fails.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        if isinstance(ticket, Epic):
            return await self._create_epic(ticket)
        return await self._create_task(ticket)

    async def _create_epic(self, epic: Epic) -> Epic:
        """Create a ClickUp list from an Epic.

        A list is created inside a folder (if ``folder_id`` is configured) or
        "folderless" inside a space (if ``space_id`` is configured).

        Args:
            epic: Epic to create.

        Returns:
            Created epic with ClickUp metadata.

        Raises:
            ValueError: If no folder/space is configured, or creation fails.

        """
        payload: dict[str, Any] = {"name": epic.title}
        if epic.description:
            payload["content"] = epic.description

        try:
            if self._folder_id:
                created = await self.client.post(
                    f"/folder/{self._folder_id}/list", payload
                )
            elif self._space_id:
                created = await self.client.post(
                    f"/space/{self._space_id}/list", payload
                )
            else:
                raise ValueError(
                    "Creating an Epic (ClickUp list) requires a configured "
                    "folder_id (CLICKUP_FOLDER_ID) or space_id (CLICKUP_SPACE_ID)"
                )
            return map_clickup_list_to_epic(created)
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to create ClickUp list: {e}") from e

    async def _create_task(self, task: Task) -> Task:
        """Create a ClickUp task or subtask from a Task.

        Args:
            task: Task to create.

        Returns:
            Created task with ClickUp metadata.

        Raises:
            ValueError: If no target list can be resolved or creation fails.

        """
        list_id = self._resolve_list_id_for_create(task)
        if not list_id:
            raise ValueError(
                "Creating a task requires a target list: set parent_epic (a "
                "ClickUp list id) or configure a default list_id (CLICKUP_LIST_ID)"
            )

        payload = map_task_to_clickup_payload(task)

        # Resolve assignee (ClickUp expects integer user ids).
        if task.assignee:
            assignee_id = self._coerce_user_id(task.assignee)
            if assignee_id is not None:
                payload["assignees"] = [assignee_id]
            else:
                logger.warning(
                    "Could not coerce assignee '%s' to a ClickUp user id",
                    task.assignee,
                )

        # Resolve a concrete per-list status name from the requested state.
        if task.state and task.state != TicketState.OPEN:
            status_name = await self._resolve_status_name(task.state, list_id)
            if status_name:
                payload["status"] = status_name

        try:
            created = await self.client.post(f"/list/{list_id}/task", payload)
            # Re-read so we get the fully-populated task (status object, list, etc.).
            full = await self.client.get(f"/task/{created['id']}")
            return map_clickup_task_to_task(full)
        except Exception as e:
            raise ValueError(f"Failed to create ClickUp task: {e}") from e

    def _coerce_user_id(self, user_identifier: str) -> int | None:
        """Coerce a user identifier to a ClickUp integer user id.

        ClickUp assignees are integer user ids. This adapter accepts a numeric
        id (as int or string); non-numeric identifiers (names/emails) cannot be
        resolved without a members lookup and are rejected here.

        Args:
            user_identifier: User id as a string.

        Returns:
            Integer user id, or None if not numeric.

        """
        if user_identifier is None:
            return None
        try:
            return int(user_identifier)
        except (ValueError, TypeError):
            return None

    async def read(self, ticket_id: str) -> Task | None:
        """Read a ClickUp task by id.

        Args:
            ticket_id: ClickUp task id.

        Returns:
            Task if found, None otherwise.

        Raises:
            ValueError: If credentials are invalid.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            task = await self.client.get(f"/task/{ticket_id}")
            return map_clickup_task_to_task(task)
        except Exception as e:
            logger.error("Failed to read task %s: %s", ticket_id, e)
            return None

    async def update(self, ticket_id: str, updates: dict[str, Any]) -> Task | None:
        """Update a ClickUp task.

        Args:
            ticket_id: ClickUp task id.
            updates: Fields to update. Recognised keys: ``title``,
                ``description``, ``priority``, ``state``, ``assignee``,
                ``due_date``, ``tags``.

        Returns:
            Updated task, or None on failure.

        Raises:
            ValueError: If credentials are invalid.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        try:
            payload: dict[str, Any] = {}

            if "title" in updates:
                payload["name"] = updates["title"]

            if "description" in updates:
                payload["description"] = updates["description"]

            if "priority" in updates:
                payload["priority"] = self._coerce_priority_update(updates["priority"])

            if "assignee" in updates and updates["assignee"]:
                assignee_id = self._coerce_user_id(updates["assignee"])
                if assignee_id is not None:
                    # ClickUp PUT uses {"assignees": {"add": [...], "rem": [...]}}.
                    payload["assignees"] = {"add": [assignee_id]}

            if "due_date" in updates:
                payload["due_date"] = updates["due_date"]

            if "state" in updates:
                state = updates["state"]
                if isinstance(state, str):
                    state = TicketState(state)
                list_id = await self._task_list_id(ticket_id)
                status_name = await self._resolve_status_name(state, list_id)
                if status_name:
                    payload["status"] = status_name
                else:
                    logger.warning(
                        "Could not resolve a list status for state %s on task %s",
                        state,
                        ticket_id,
                    )

            if payload:
                await self.client.put(f"/task/{ticket_id}", payload)

            # Tags are updated via dedicated endpoints (not the task PUT body).
            if "tags" in updates:
                await self._replace_tags(ticket_id, updates.get("tags") or [])

            full = await self.client.get(f"/task/{ticket_id}")
            return map_clickup_task_to_task(full)
        except Exception as e:
            logger.error("Failed to update task %s: %s", ticket_id, e)
            return None

    def _coerce_priority_update(self, value: Any) -> int:
        """Coerce a priority update value to a ClickUp integer priority code.

        Accepts a ``Priority`` enum, its string value, or a raw ClickUp int.

        Args:
            value: Priority enum, string, or int.

        Returns:
            ClickUp integer priority (1=urgent..4=low; defaults to 3=normal).

        """
        if isinstance(value, int):
            return value
        if isinstance(value, Priority):
            return map_priority_to_clickup(value)
        if isinstance(value, str):
            try:
                return map_priority_to_clickup(Priority(value.lower()))
            except ValueError:
                return 3
        return 3

    async def _replace_tags(self, ticket_id: str, new_tags: list[str]) -> None:
        """Replace a task's tags with ``new_tags``.

        ClickUp manages tags via ``POST/DELETE /task/{id}/tag/{tag_name}``.

        Args:
            ticket_id: ClickUp task id.
            new_tags: Desired set of tag names.

        """
        try:
            current = await self.client.get(f"/task/{ticket_id}")
            existing = [
                t.get("name")
                for t in current.get("tags", [])
                if isinstance(t, dict) and t.get("name")
            ]

            for tag_name in existing:
                if tag_name not in new_tags:
                    try:
                        await self.client.delete(f"/task/{ticket_id}/tag/{tag_name}")
                    except Exception as e:
                        logger.warning(
                            "Failed to remove tag '%s' from task %s: %s",
                            tag_name,
                            ticket_id,
                            e,
                        )

            for tag_name in new_tags:
                if tag_name not in existing:
                    try:
                        await self.client.post(f"/task/{ticket_id}/tag/{tag_name}", {})
                    except Exception as e:
                        logger.warning(
                            "Failed to add tag '%s' to task %s: %s",
                            tag_name,
                            ticket_id,
                            e,
                        )
        except Exception as e:
            logger.warning("Failed to replace tags for task %s: %s", ticket_id, e)

    async def delete(self, ticket_id: str) -> bool:
        """Delete a ClickUp task.

        Args:
            ticket_id: ClickUp task id.

        Returns:
            True if deleted, False otherwise.

        """
        try:
            await self.client.delete(f"/task/{ticket_id}")
            return True
        except Exception as e:
            logger.error("Failed to delete task %s: %s", ticket_id, e)
            return False

    async def list(
        self, limit: int = 10, offset: int = 0, filters: dict[str, Any] | None = None
    ) -> builtins.list[Task]:
        """List ClickUp tasks with optional filtering.

        Tasks are fetched from a list endpoint (``GET /list/{id}/task``). The
        target list is taken from ``filters['parent_epic']`` / ``filters['project']``
        or the adapter's default list id.

        Args:
            limit: Maximum number of tasks to return.
            offset: Number of tasks to skip (ClickUp paginates by page; the
                ``page`` derived from offset/limit is used).
            filters: Optional filters (``parent_epic``/``project``, ``state``,
                ``ticket_type``).

        Returns:
            List of tasks matching the criteria.

        Raises:
            ValueError: If credentials are invalid.

        """
        is_valid, error_message = self.validate_credentials()
        if not is_valid:
            raise ValueError(error_message)

        await self.initialize()

        filters = filters or {}

        list_id = (
            filters.get("parent_epic")
            or filters.get("project")
            or self._default_list_id
        )
        if not list_id:
            logger.warning(
                "ClickUp list() requires a list id (parent_epic/project filter "
                "or default list_id); returning empty result"
            )
            return []

        # ClickUp uses page-based pagination (100 tasks/page).
        page = offset // limit if limit else 0
        params: dict[str, Any] = {
            "page": page,
            "subtasks": "true",
            "include_closed": "true",
        }

        try:
            response = await self.client.get(f"/list/{list_id}/task", params=params)
            raw_tasks = response.get("tasks", [])
            tasks = [map_clickup_task_to_task(t) for t in raw_tasks]
        except Exception as e:
            logger.error("Failed to list tasks for list %s: %s", list_id, e)
            return []

        # Client-side filters (state / ticket_type).
        if "state" in filters:
            state = filters["state"]
            if isinstance(state, str):
                state = TicketState(state)
            tasks = [t for t in tasks if t.state == state]

        if "ticket_type" in filters:
            ticket_type = filters["ticket_type"]
            tasks = [t for t in tasks if t.ticket_type == ticket_type]

        return tasks[:limit]

    async def search(self, query: SearchQuery) -> builtins.list[Task]:
        """Search ClickUp tasks using filters and client-side text matching.

        Args:
            query: Search query with filters.

        Returns:
            List of tasks matching the search criteria.

        """
        filters: dict[str, Any] = {}
        if query.project:
            filters["parent_epic"] = query.project
        if query.state:
            filters["state"] = query.state

        tasks = await self.list(limit=query.limit, offset=query.offset, filters=filters)

        if query.query:
            query_lower = query.query.lower()
            tasks = [
                t
                for t in tasks
                if query_lower in t.title.lower()
                or (t.description and query_lower in t.description.lower())
            ]

        if query.assignee:
            tasks = [t for t in tasks if t.assignee == query.assignee]

        if query.tags:
            tasks = [t for t in tasks if any(tag in t.tags for tag in query.tags)]

        return tasks[: query.limit]

    async def transition_state(
        self, ticket_id: str, target_state: TicketState
    ) -> Task | None:
        """Transition a task to a new state.

        Args:
            ticket_id: ClickUp task id.
            target_state: Target universal state.

        Returns:
            Updated task, or None on failure.

        """
        return await self.update(ticket_id, {"state": target_state})

    async def add_comment(self, comment: Comment) -> Comment:
        """Add a comment to a ClickUp task.

        Args:
            comment: Comment to add.

        Returns:
            Created comment with its id populated.

        Raises:
            ValueError: If comment creation fails.

        """
        try:
            created = await self.client.post(
                f"/task/{comment.ticket_id}/comment",
                {"comment_text": comment.content},
            )
            # ClickUp returns {"id": ..., "hist_id": ..., "date": ...}; merge id
            # into a comment shape the mapper understands.
            created.setdefault("comment_text", comment.content)
            return map_clickup_comment_to_comment(created, comment.ticket_id)
        except Exception as e:
            raise ValueError(f"Failed to add comment: {e}") from e

    async def get_comments(
        self, ticket_id: str, limit: int = 10, offset: int = 0
    ) -> builtins.list[Comment]:
        """Get comments for a ClickUp task.

        Args:
            ticket_id: ClickUp task id.
            limit: Maximum number of comments to return.
            offset: Number of comments to skip.

        Returns:
            List of comments for the task.

        """
        try:
            response = await self.client.get(f"/task/{ticket_id}/comment")
            raw_comments = response.get("comments", [])
            comments = [
                map_clickup_comment_to_comment(c, ticket_id) for c in raw_comments
            ]
            return comments[offset : offset + limit]
        except Exception as e:
            logger.error("Failed to get comments for task %s: %s", ticket_id, e)
            return []

    # ------------------------------------------------------------------
    # Epic/Issue/Task hierarchy methods
    # ------------------------------------------------------------------

    async def get_epic(self, epic_id: str) -> Epic | None:
        """Get a ClickUp list (Epic) by id.

        Args:
            epic_id: ClickUp list id.

        Returns:
            Epic if found, None otherwise.

        """
        try:
            list_obj = await self.client.get(f"/list/{epic_id}")
            return map_clickup_list_to_epic(list_obj)
        except Exception as e:
            logger.error("Failed to get list %s: %s", epic_id, e)
            return None

    async def list_epics(self, **kwargs: Any) -> builtins.list[Epic]:
        """List ClickUp lists (Epics) within the configured folder/space.

        Args:
            **kwargs: Optional ``archived`` filter.

        Returns:
            List of epics.

        """
        await self.initialize()

        try:
            if self._folder_id:
                response = await self.client.get(f"/folder/{self._folder_id}/list")
            elif self._space_id:
                response = await self.client.get(
                    f"/space/{self._space_id}/list",
                    params={"archived": "false"},
                )
            else:
                logger.warning(
                    "list_epics requires folder_id or space_id configuration"
                )
                return []

            raw_lists = response.get("lists", [])
            epics = [map_clickup_list_to_epic(item) for item in raw_lists]

            if "archived" in kwargs:
                archived = kwargs["archived"]
                epics = [
                    e for e in epics if e.metadata.get("clickup_archived") == archived
                ]
            return epics
        except Exception as e:
            logger.error("Failed to list lists (epics): %s", e)
            return []

    async def update_epic(self, epic_id: str, updates: dict[str, Any]) -> Epic | None:
        """Update a ClickUp list (Epic).

        Args:
            epic_id: ClickUp list id.
            updates: Recognised keys: ``title``, ``description``.

        Returns:
            Updated epic, or None on failure.

        """
        payload: dict[str, Any] = {}
        if "title" in updates:
            payload["name"] = updates["title"]
        if "description" in updates:
            payload["content"] = updates["description"]

        try:
            if payload:
                await self.client.put(f"/list/{epic_id}", payload)
            return await self.get_epic(epic_id)
        except Exception as e:
            logger.error("Failed to update list %s: %s", epic_id, e)
            return None

    async def delete_epic(self, epic_id: str) -> bool:
        """Delete a ClickUp list (Epic).

        Args:
            epic_id: ClickUp list id.

        Returns:
            True if deleted, False otherwise.

        """
        try:
            await self.client.delete(f"/list/{epic_id}")
            return True
        except Exception as e:
            logger.error("Failed to delete list %s: %s", epic_id, e)
            return False

    async def list_issues_by_epic(self, epic_id: str) -> builtins.list[Task]:
        """List all tasks in a ClickUp list (Epic).

        Args:
            epic_id: ClickUp list id.

        Returns:
            List of issues in the list.

        """
        return await self.list(
            limit=100,
            filters={"parent_epic": epic_id, "ticket_type": TicketType.ISSUE},
        )

    async def list_tasks_by_issue(self, issue_id: str) -> builtins.list[Task]:
        """List all subtasks of a task (Issue).

        ClickUp returns subtasks inline on the parent when requested with
        ``include_subtasks``. Each child is fetched fully to populate its fields.

        Args:
            issue_id: Parent ClickUp task id.

        Returns:
            List of subtasks.

        """
        try:
            parent = await self.client.get(
                f"/task/{issue_id}", params={"include_subtasks": "true"}
            )
            subtasks = parent.get("subtasks", [])
            tasks: list[Task] = []
            for sub in subtasks:
                sub_id = sub.get("id")
                if not sub_id:
                    continue
                try:
                    full = await self.client.get(f"/task/{sub_id}")
                    tasks.append(map_clickup_task_to_task(full))
                except Exception as e:
                    logger.warning("Failed to read subtask %s: %s", sub_id, e)
            return tasks
        except Exception as e:
            logger.error("Failed to list subtasks for task %s: %s", issue_id, e)
            return []

    async def search_users(self, query: str) -> builtins.list[dict[str, Any]]:
        """Search for users (members) in the ClickUp workspace.

        ClickUp exposes members via ``GET /team`` (each team carries a
        ``members`` array). This performs a client-side case-insensitive match
        on username/email.

        Args:
            query: Search query (username or email substring).

        Returns:
            List of user dicts with keys ``id``, ``name``, ``email``.

        """
        try:
            response = await self.client.get("/team")
            teams = response.get("teams", [])
            results: list[dict[str, Any]] = []
            query_lower = (query or "").lower()

            for team in teams:
                if self._team_id and str(team.get("id")) != str(self._team_id):
                    continue
                for member in team.get("members", []):
                    user = member.get("user", {}) if isinstance(member, dict) else {}
                    username = str(user.get("username") or "")
                    email = str(user.get("email") or "")
                    if (
                        not query_lower
                        or query_lower in username.lower()
                        or query_lower in email.lower()
                    ):
                        results.append(
                            {
                                "id": str(user.get("id"))
                                if user.get("id") is not None
                                else None,
                                "name": username,
                                "email": email,
                            }
                        )
            return results
        except Exception as e:
            logger.error("Failed to search ClickUp users: %s", e)
            return []

    async def close(self) -> None:
        """Close the adapter and cleanup resources."""
        await self.client.close()

    # ------------------------------------------------------------------
    # Milestone methods — NOT SUPPORTED (ClickUp has no native milestones)
    # ------------------------------------------------------------------

    async def milestone_create(
        self,
        name: str,
        target_date: datetime | None = None,
        labels: builtins.list[str] | None = None,
        description: str = "",
        project_id: str | None = None,
    ) -> Milestone:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            name: Milestone name.
            target_date: Target completion date.
            labels: Labels that define this milestone.
            description: Milestone description.
            project_id: Associated project id.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)

    async def milestone_get(self, milestone_id: str) -> Milestone | None:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            milestone_id: Milestone identifier.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)

    async def milestone_list(
        self,
        project_id: str | None = None,
        state: str | None = None,
    ) -> builtins.list[Milestone]:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            project_id: Filter by project.
            state: Filter by state.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)

    async def milestone_update(
        self,
        milestone_id: str,
        name: str | None = None,
        target_date: datetime | None = None,
        state: str | None = None,
        labels: builtins.list[str] | None = None,
        description: str | None = None,
    ) -> Milestone | None:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            milestone_id: Milestone identifier.
            name: New name.
            target_date: New target date.
            state: New state.
            labels: New labels.
            description: New description.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)

    async def milestone_delete(self, milestone_id: str) -> bool:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            milestone_id: Milestone identifier.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)

    async def milestone_get_issues(
        self,
        milestone_id: str,
        state: str | None = None,
    ) -> builtins.list[Task]:
        """Not supported — ClickUp has no native milestone concept.

        Args:
            milestone_id: Milestone identifier.
            state: Filter by issue state.

        Raises:
            NotImplementedError: Always — see module docstring.

        """
        raise NotImplementedError(_MILESTONE_UNSUPPORTED)


# Register the adapter.
AdapterRegistry.register("clickup", ClickUpAdapter)
