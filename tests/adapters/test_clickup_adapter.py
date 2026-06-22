"""Mocked-HTTP unit tests for the ClickUp adapter.

All ClickUp REST calls are mocked at the ``ClickUpClient`` method level
(``get``/``post``/``put``/``delete``) so the suite runs with no network access
and no real ClickUp token. This mirrors the JIRA adapter's mocking approach in
``tests/adapters/test_jira_new_methods.py``.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from mcp_ticketer.adapters.clickup import ClickUpAdapter
from mcp_ticketer.adapters.clickup.client import ClickUpClient
from mcp_ticketer.adapters.clickup.mappers import (
    map_clickup_comment_to_comment,
    map_clickup_list_to_epic,
    map_clickup_task_to_task,
    parse_clickup_epoch_ms,
    to_clickup_epoch_ms,
)
from mcp_ticketer.adapters.clickup.types import (
    map_priority_from_clickup,
    map_priority_to_clickup,
    map_status_type_to_state,
    resolve_state_to_status_name,
)
from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
    TicketType,
)
from mcp_ticketer.core.registry import AdapterRegistry

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def clickup_config():
    """Standard ClickUp configuration for testing."""
    return {
        "api_token": "pk_test_TOKEN_123",
        "team_id": "9007001",
        "list_id": "901000123",
        "space_id": "90120001",
        "folder_id": "90130002",
    }


@pytest.fixture
def adapter(clickup_config):
    """Create a ClickUp adapter that is already 'initialized' (no network)."""
    a = ClickUpAdapter(clickup_config)
    # Pretend initialize() already ran so methods don't try to test_connection.
    a._initialized = True
    return a


# Sample ClickUp API objects -------------------------------------------------

LIST_STATUSES = [
    {"status": "to do", "type": "open", "orderindex": 0},
    {"status": "in progress", "type": "custom", "orderindex": 1},
    {"status": "in review", "type": "custom", "orderindex": 2},
    {"status": "complete", "type": "done", "orderindex": 3},
    {"status": "closed", "type": "closed", "orderindex": 4},
]


def make_task_obj(**overrides):
    """Build a representative ClickUp task object."""
    obj = {
        "id": "task_abc",
        "name": "Fix login bug",
        "description": "Users cannot log in",
        "status": {"status": "in progress", "type": "custom"},
        "priority": {"id": "2", "priority": "high"},
        "tags": [{"name": "bug"}, {"name": "auth"}],
        "assignees": [{"id": 42, "username": "jane"}],
        "list": {"id": "901000123", "name": "Sprint 1"},
        "folder": {"id": "90130002"},
        "space": {"id": "90120001"},
        "parent": None,
        "date_created": "1700000000000",
        "date_updated": "1700000100000",
        "url": "https://app.clickup.com/t/task_abc",
    }
    obj.update(overrides)
    return obj


# --------------------------------------------------------------------------
# Registration & credentials
# --------------------------------------------------------------------------


class TestRegistration:
    """Adapter registration in the global registry."""

    def test_clickup_registered(self):
        """ClickUp adapter is registered under the 'clickup' name."""
        assert AdapterRegistry.is_registered("clickup")

    def test_registry_returns_clickup_class(self):
        """The registry maps 'clickup' to ClickUpAdapter."""
        assert AdapterRegistry.list_adapters()["clickup"] is ClickUpAdapter

    def test_adapter_type_property(self, adapter):
        """adapter_type derives 'clickup' from the class name."""
        assert adapter.adapter_type == "clickup"


class TestCredentials:
    """Credential handling and token sourcing."""

    def test_missing_token_raises(self, monkeypatch):
        """Constructing without a token raises ValueError."""
        monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
        monkeypatch.delenv("MCP_TICKETER_CLICKUP_API_TOKEN", raising=False)
        with pytest.raises(ValueError, match="ClickUp API token is required"):
            ClickUpAdapter({})

    def test_token_from_env(self, monkeypatch):
        """Token is read from CLICKUP_API_TOKEN when not in config."""
        monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_env_TOKEN")
        a = ClickUpAdapter({})
        assert a.api_token == "pk_env_TOKEN"

    def test_token_prefix_stripped(self):
        """An accidental NAME=value prefix on the token is stripped."""
        a = ClickUpAdapter({"api_token": "CLICKUP_API_TOKEN=pk_real"})
        assert a.api_token == "pk_real"

    def test_validate_credentials_ok(self, adapter):
        """validate_credentials returns (True, '') with a token present."""
        is_valid, msg = adapter.validate_credentials()
        assert is_valid is True
        assert msg == ""

    def test_config_overrides_env(self, monkeypatch):
        """Config team/list win over environment variables."""
        monkeypatch.setenv("CLICKUP_TEAM_ID", "env_team")
        monkeypatch.setenv("CLICKUP_LIST_ID", "env_list")
        a = ClickUpAdapter(
            {"api_token": "pk_x", "team_id": "cfg_team", "list_id": "cfg_list"}
        )
        assert a._team_id == "cfg_team"
        assert a._default_list_id == "cfg_list"


# --------------------------------------------------------------------------
# Pure mapping helpers (no I/O)
# --------------------------------------------------------------------------


class TestPriorityMapping:
    """Priority conversions between universal and ClickUp."""

    @pytest.mark.parametrize(
        "priority,code",
        [
            (Priority.CRITICAL, 1),
            (Priority.HIGH, 2),
            (Priority.MEDIUM, 3),
            (Priority.LOW, 4),
        ],
    )
    def test_to_clickup(self, priority, code):
        """Each universal priority maps to its ClickUp integer code."""
        assert map_priority_to_clickup(priority) == code

    @pytest.mark.parametrize(
        "value,expected",
        [
            (None, Priority.MEDIUM),
            (1, Priority.CRITICAL),
            ("2", Priority.HIGH),
            ({"id": "4", "priority": "low"}, Priority.LOW),
            ({"priority": "urgent"}, Priority.CRITICAL),
            ("garbage", Priority.MEDIUM),
        ],
    )
    def test_from_clickup(self, value, expected):
        """ClickUp priority values map back to universal priorities."""
        assert map_priority_from_clickup(value) == expected


class TestStatusMapping:
    """Per-list status <-> universal state mapping (the core mapping work)."""

    @pytest.mark.parametrize(
        "stype,name,expected",
        [
            ("open", "to do", TicketState.OPEN),
            ("closed", "closed", TicketState.CLOSED),
            ("done", "complete", TicketState.DONE),
            ("custom", "in progress", TicketState.IN_PROGRESS),
            ("custom", "in review", TicketState.READY),
            ("custom", "QA testing", TicketState.TESTED),
            ("custom", "blocked", TicketState.BLOCKED),
            ("custom", "waiting", TicketState.WAITING),
            ("custom", "something weird", TicketState.IN_PROGRESS),
        ],
    )
    def test_status_type_to_state(self, stype, name, expected):
        """Status type+name resolves to the right universal state."""
        assert map_status_type_to_state(stype, name) == expected

    def test_resolve_state_open(self):
        """OPEN resolves to the list's 'open'-type status name."""
        assert resolve_state_to_status_name(TicketState.OPEN, LIST_STATUSES) == "to do"

    def test_resolve_state_done(self):
        """DONE resolves to the list's 'done'-type status name."""
        assert (
            resolve_state_to_status_name(TicketState.DONE, LIST_STATUSES) == "complete"
        )

    def test_resolve_state_closed(self):
        """CLOSED resolves to the list's 'closed'-type status name."""
        assert (
            resolve_state_to_status_name(TicketState.CLOSED, LIST_STATUSES) == "closed"
        )

    def test_resolve_state_in_progress_by_keyword(self):
        """IN_PROGRESS resolves to a custom column whose name matches a keyword."""
        assert (
            resolve_state_to_status_name(TicketState.IN_PROGRESS, LIST_STATUSES)
            == "in progress"
        )

    def test_resolve_state_ready_by_keyword(self):
        """READY resolves to the 'in review' custom column."""
        assert (
            resolve_state_to_status_name(TicketState.READY, LIST_STATUSES)
            == "in review"
        )

    def test_resolve_state_empty_list(self):
        """Resolving against an empty status list returns None."""
        assert resolve_state_to_status_name(TicketState.OPEN, []) is None


class TestTimestampMapping:
    """Epoch-millisecond conversions."""

    def test_parse_epoch_ms(self):
        """A millisecond epoch string parses to a UTC datetime."""
        dt = parse_clickup_epoch_ms("1700000000000")
        assert dt is not None
        assert dt.year == 2023

    def test_parse_epoch_ms_none(self):
        """None/empty input parses to None."""
        assert parse_clickup_epoch_ms(None) is None
        assert parse_clickup_epoch_ms("") is None

    def test_parse_epoch_ms_invalid(self):
        """A non-numeric value parses to None (not an exception)."""
        assert parse_clickup_epoch_ms("not-a-number") is None

    def test_round_trip(self):
        """to_clickup_epoch_ms inverts parse_clickup_epoch_ms (to the second)."""
        dt = parse_clickup_epoch_ms("1700000000000")
        assert to_clickup_epoch_ms(dt) == 1700000000000


class TestObjectMappers:
    """ClickUp object -> universal model mappers."""

    def test_map_task_issue(self):
        """A parent-less ClickUp task maps to an ISSUE Task with full fields."""
        task = map_clickup_task_to_task(make_task_obj())
        assert isinstance(task, Task)
        assert task.id == "task_abc"
        assert task.title == "Fix login bug"
        assert task.ticket_type == TicketType.ISSUE
        assert task.state == TicketState.IN_PROGRESS
        assert task.priority == Priority.HIGH
        assert task.tags == ["bug", "auth"]
        assert task.assignee == "42"
        assert task.parent_epic == "901000123"
        assert task.parent_issue is None

    def test_map_task_subtask(self):
        """A ClickUp task with a parent maps to a TASK (subtask)."""
        obj = make_task_obj(parent="task_parent")
        task = map_clickup_task_to_task(obj)
        assert task.ticket_type == TicketType.TASK
        assert task.parent_issue == "task_parent"
        assert task.parent_epic is None

    def test_map_list_to_epic(self):
        """A ClickUp list maps to an Epic."""
        epic = map_clickup_list_to_epic(
            {
                "id": "901000123",
                "name": "Sprint 1",
                "content": "Backlog list",
                "archived": False,
                "folder": {"id": "90130002", "name": "F"},
                "space": {"id": "90120001", "name": "S"},
            }
        )
        assert isinstance(epic, Epic)
        assert epic.id == "901000123"
        assert epic.title == "Sprint 1"
        assert epic.state == TicketState.OPEN
        assert epic.metadata["clickup_folder_id"] == "90130002"

    def test_map_archived_list_is_closed(self):
        """An archived list maps to CLOSED state."""
        epic = map_clickup_list_to_epic({"id": "1", "name": "X", "archived": True})
        assert epic.state == TicketState.CLOSED

    def test_map_comment(self):
        """A ClickUp comment maps to a Comment."""
        comment = map_clickup_comment_to_comment(
            {
                "id": "c1",
                "comment_text": "Looks good",
                "user": {"id": 7, "username": "bob"},
                "date": "1700000000000",
            },
            "task_abc",
        )
        assert isinstance(comment, Comment)
        assert comment.content == "Looks good"
        assert comment.author == "7"
        assert comment.ticket_id == "task_abc"

    def test_map_comment_rich_blocks(self):
        """A ClickUp comment with rich blocks is flattened to text."""
        comment = map_clickup_comment_to_comment(
            {
                "id": "c2",
                "comment": [{"text": "Hello "}, {"text": "world"}],
                "user": {"id": 7, "username": "bob"},
            },
            "task_abc",
        )
        assert comment.content == "Hello world"

    def test_map_comment_empty_never_violates_min_length(self):
        """An empty comment body becomes a single space (min_length=1 guard)."""
        comment = map_clickup_comment_to_comment(
            {"id": "c3", "user": {"id": 7}}, "task_abc"
        )
        assert comment.content == " "


# --------------------------------------------------------------------------
# CRUD operations (mocked client)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCreate:
    """create() for tasks and epics."""

    async def test_create_issue(self, adapter):
        """Creating an issue posts to /list/{id}/task and resolves status."""
        created_resp = {"id": "task_new"}
        full_task = make_task_obj(id="task_new", name="New issue")

        with (
            patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get,
            patch.object(adapter.client, "post", new_callable=AsyncMock) as mock_post,
        ):
            # get() is called for: list statuses (status resolution) + full read.
            mock_get.side_effect = [
                {"statuses": LIST_STATUSES},  # _get_list_statuses
                full_task,  # re-read after create
            ]
            mock_post.return_value = created_resp

            task = Task(
                title="New issue",
                ticket_type=TicketType.ISSUE,
                parent_epic="901000123",
                state=TicketState.IN_PROGRESS,
                priority=Priority.HIGH,
            )
            result = await adapter.create(task)

            assert result.id == "task_new"
            # POST went to the list task endpoint.
            post_endpoint = mock_post.call_args.args[0]
            assert post_endpoint == "/list/901000123/task"
            # Payload carried a resolved per-list status name + integer priority.
            payload = mock_post.call_args.args[1]
            assert payload["status"] == "in progress"
            assert payload["priority"] == 2
            assert payload["name"] == "New issue"

    async def test_create_subtask_sets_parent(self, adapter):
        """Creating a subtask passes the parent task id in the payload."""
        with (
            patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get,
            patch.object(adapter.client, "post", new_callable=AsyncMock) as mock_post,
        ):
            # Default state is OPEN, so no status resolution get() — the only
            # get() is the post-create re-read.
            mock_get.return_value = make_task_obj(id="sub1", parent="task_parent")
            mock_post.return_value = {"id": "sub1"}

            task = Task(
                title="A subtask",
                ticket_type=TicketType.TASK,
                parent_issue="task_parent",
            )
            result = await adapter.create(task)

            assert result.ticket_type == TicketType.TASK
            payload = mock_post.call_args.args[1]
            assert payload["parent"] == "task_parent"

    async def test_create_task_without_list_raises(self, adapter):
        """Creating a task with no parent_epic and no default list raises."""
        adapter._default_list_id = None
        task = Task(title="Orphan", ticket_type=TicketType.ISSUE)
        with pytest.raises(ValueError, match="requires a target list"):
            await adapter.create(task)

    async def test_create_epic_in_folder(self, adapter):
        """Creating an epic posts to the configured folder list endpoint."""
        with patch.object(adapter.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "list_new", "name": "Epic A"}
            epic = Epic(title="Epic A", description="desc")
            result = await adapter.create(epic)
            assert isinstance(result, Epic)
            assert result.id == "list_new"
            assert mock_post.call_args.args[0] == "/folder/90130002/list"

    async def test_create_epic_without_scope_raises(self, adapter):
        """Creating an epic with no folder/space configured raises."""
        adapter._folder_id = None
        adapter._space_id = None
        with pytest.raises(ValueError, match="folder_id .* or space_id"):
            await adapter.create(Epic(title="Epic B"))


@pytest.mark.asyncio
class TestReadUpdateDelete:
    """read / update / delete / transition_state."""

    async def test_read_found(self, adapter):
        """read() returns a mapped Task."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = make_task_obj()
            task = await adapter.read("task_abc")
            assert task is not None
            assert task.title == "Fix login bug"
            assert mock_get.call_args.args[0] == "/task/task_abc"

    async def test_read_not_found_returns_none(self, adapter):
        """read() returns None when the client raises (e.g. 404)."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("ClickUp API error (404): not found")
            assert await adapter.read("missing") is None

    async def test_update_title_and_priority(self, adapter):
        """update() puts name/priority and re-reads the task."""
        with (
            patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get,
            patch.object(adapter.client, "put", new_callable=AsyncMock) as mock_put,
        ):
            mock_get.return_value = make_task_obj(name="Updated")
            mock_put.return_value = {}

            result = await adapter.update(
                "task_abc", {"title": "Updated", "priority": Priority.CRITICAL}
            )
            assert result.title == "Updated"
            payload = mock_put.call_args.args[1]
            assert payload["name"] == "Updated"
            assert payload["priority"] == 1

    async def test_update_state_resolves_status(self, adapter):
        """update(state=...) looks up the task's list then resolves the status."""
        with (
            patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get,
            patch.object(adapter.client, "put", new_callable=AsyncMock) as mock_put,
        ):
            # get() calls: _task_list_id, _get_list_statuses, final re-read.
            mock_get.side_effect = [
                {"list": {"id": "901000123"}},
                {"statuses": LIST_STATUSES},
                make_task_obj(status={"status": "complete", "type": "done"}),
            ]
            mock_put.return_value = {}

            result = await adapter.update("task_abc", {"state": TicketState.DONE})
            assert result.state == TicketState.DONE
            payload = mock_put.call_args.args[1]
            assert payload["status"] == "complete"

    async def test_delete_success(self, adapter):
        """delete() returns True on success."""
        with patch.object(adapter.client, "delete", new_callable=AsyncMock) as mock_del:
            mock_del.return_value = {}
            assert await adapter.delete("task_abc") is True
            assert mock_del.call_args.args[0] == "/task/task_abc"

    async def test_delete_failure_returns_false(self, adapter):
        """delete() returns False when the client raises."""
        with patch.object(adapter.client, "delete", new_callable=AsyncMock) as mock_del:
            mock_del.side_effect = ValueError("boom")
            assert await adapter.delete("task_abc") is False

    async def test_transition_state_delegates_to_update(self, adapter):
        """transition_state() routes through update()."""
        with patch.object(adapter, "update", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            await adapter.transition_state("task_abc", TicketState.READY)
            mock_update.assert_called_once_with(
                "task_abc", {"state": TicketState.READY}
            )


@pytest.mark.asyncio
class TestListAndSearch:
    """list() and search()."""

    async def test_list_by_epic(self, adapter):
        """list() fetches tasks from the list endpoint and maps them."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "tasks": [make_task_obj(id="t1"), make_task_obj(id="t2")]
            }
            tasks = await adapter.list(filters={"parent_epic": "901000123"})
            assert len(tasks) == 2
            assert mock_get.call_args.args[0] == "/list/901000123/task"

    async def test_list_state_filter(self, adapter):
        """list() applies a client-side state filter."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "tasks": [
                    make_task_obj(id="t1", status={"status": "to do", "type": "open"}),
                    make_task_obj(
                        id="t2", status={"status": "complete", "type": "done"}
                    ),
                ]
            }
            tasks = await adapter.list(
                filters={"parent_epic": "901000123", "state": TicketState.DONE}
            )
            assert [t.id for t in tasks] == ["t2"]

    async def test_list_no_list_id_returns_empty(self, adapter):
        """list() with no resolvable list returns an empty list."""
        adapter._default_list_id = None
        assert await adapter.list() == []

    async def test_search_text_filter(self, adapter):
        """search() filters by title text on top of list()."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "tasks": [
                    make_task_obj(id="t1", name="login bug"),
                    make_task_obj(id="t2", name="dashboard work"),
                ]
            }
            results = await adapter.search(
                SearchQuery(query="login", project="901000123")
            )
            assert [t.id for t in results] == ["t1"]


@pytest.mark.asyncio
class TestComments:
    """add_comment / get_comments."""

    async def test_add_comment(self, adapter):
        """add_comment posts comment_text and returns a Comment."""
        with patch.object(adapter.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"id": "c99", "date": "1700000000000"}
            result = await adapter.add_comment(
                Comment(ticket_id="task_abc", content="Nice work")
            )
            assert result.content == "Nice work"
            assert mock_post.call_args.args[0] == "/task/task_abc/comment"
            assert mock_post.call_args.args[1] == {"comment_text": "Nice work"}

    async def test_get_comments(self, adapter):
        """get_comments returns mapped comments with offset/limit applied."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "comments": [
                    {"id": "c1", "comment_text": "a", "user": {"id": 1}},
                    {"id": "c2", "comment_text": "b", "user": {"id": 2}},
                ]
            }
            comments = await adapter.get_comments("task_abc", limit=1)
            assert len(comments) == 1
            assert comments[0].content == "a"


@pytest.mark.asyncio
class TestHierarchyAndUsers:
    """Epic helpers and user search."""

    async def test_get_epic(self, adapter):
        """get_epic reads a list and maps it to an Epic."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"id": "901000123", "name": "Sprint 1"}
            epic = await adapter.get_epic("901000123")
            assert epic.title == "Sprint 1"

    async def test_list_subtasks(self, adapter):
        """list_tasks_by_issue reads the parent then each subtask fully."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                {"id": "p1", "subtasks": [{"id": "s1"}, {"id": "s2"}]},
                make_task_obj(id="s1", parent="p1"),
                make_task_obj(id="s2", parent="p1"),
            ]
            subs = await adapter.list_tasks_by_issue("p1")
            assert [t.id for t in subs] == ["s1", "s2"]
            assert all(t.ticket_type == TicketType.TASK for t in subs)

    async def test_search_users(self, adapter):
        """search_users matches members by username/email."""
        with patch.object(adapter.client, "get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {
                "teams": [
                    {
                        "id": "9007001",
                        "members": [
                            {
                                "user": {
                                    "id": 1,
                                    "username": "jane",
                                    "email": "jane@x.io",
                                }
                            },
                            {"user": {"id": 2, "username": "bob", "email": "bob@x.io"}},
                        ],
                    }
                ]
            }
            results = await adapter.search_users("jane")
            assert len(results) == 1
            assert results[0]["id"] == "1"
            assert results[0]["email"] == "jane@x.io"


# --------------------------------------------------------------------------
# Milestones — unsupported
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMilestonesUnsupported:
    """Every milestone_* method raises NotImplementedError with a clear reason."""

    async def test_milestone_create(self, adapter):
        """milestone_create is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_create("M1")

    async def test_milestone_get(self, adapter):
        """milestone_get is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_get("m1")

    async def test_milestone_list(self, adapter):
        """milestone_list is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_list()

    async def test_milestone_update(self, adapter):
        """milestone_update is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_update("m1", name="x")

    async def test_milestone_delete(self, adapter):
        """milestone_delete is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_delete("m1")

    async def test_milestone_get_issues(self, adapter):
        """milestone_get_issues is unsupported."""
        with pytest.raises(NotImplementedError, match="no native milestone"):
            await adapter.milestone_get_issues("m1")


# --------------------------------------------------------------------------
# Client security: the auth token must never leak into errors/logs
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestClientSecurity:
    """The personal token must not appear in raised exceptions."""

    async def test_auth_header_set_without_bearer(self):
        """ClickUp uses the raw token in Authorization (no 'Bearer ' prefix)."""
        client = ClickUpClient("pk_secret_TOKEN")
        assert client.headers["Authorization"] == "pk_secret_TOKEN"
        assert "Bearer" not in client.headers["Authorization"]

    async def test_error_message_excludes_token(self):
        """A 4xx error message contains the status/detail but not the token."""
        client = ClickUpClient("pk_secret_TOKEN")

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401, json={"err": "Token invalid", "ECODE": "OAUTH_017"}
            )

        transport = httpx.MockTransport(handler)
        client._client = httpx.AsyncClient(transport=transport, headers=client.headers)

        with pytest.raises(ValueError) as exc_info:
            await client.get("/user")

        message = str(exc_info.value)
        assert "401" in message
        assert "Token invalid" in message
        assert "pk_secret_TOKEN" not in message
        await client.close()

    async def test_timeout_error_excludes_token(self):
        """A timeout error message does not contain the token."""
        client = ClickUpClient("pk_secret_TOKEN", max_retries=0)

        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("timed out", request=request)

        transport = httpx.MockTransport(handler)
        client._client = httpx.AsyncClient(transport=transport, headers=client.headers)

        with pytest.raises(ValueError) as exc_info:
            await client.get("/user")

        assert "pk_secret_TOKEN" not in str(exc_info.value)
        await client.close()
