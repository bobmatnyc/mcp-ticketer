"""Shared test fixtures for mcp-ticketer tests."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest

from mcp_ticketer.core.models import (
    Comment,
    Epic,
    Priority,
    SearchQuery,
    Task,
    TicketState,
)
from mcp_ticketer.queue.queue import Queue


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all adapter-related environment variables for test isolation.

    This fixture runs automatically before each test to ensure clean state.
    """
    # List of environment variable prefixes to clear
    env_prefixes = [
        "LINEAR_",
        "JIRA_",
        "GITHUB_",
        "MCP_TICKETER_",
        "AITRACKDOWN_",
    ]

    # Clear all matching environment variables
    for key in list(os.environ.keys()):
        for prefix in env_prefixes:
            if key.startswith(prefix):
                monkeypatch.delenv(key, raising=False)
                break


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Temporary directory for test files.

    Yields:
        Path to temporary directory
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db() -> Generator[sqlite3.Connection, None, None]:
    """In-memory SQLite database for testing.

    Yields:
        SQLite connection
    """
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def sample_task_data() -> dict[str, Any]:
    """Sample task data for tests.

    Returns:
        Dictionary with task data
    """
    return {
        "id": "TEST-123",
        "title": "Test ticket",
        "description": "Test description",
        "state": "open",
        "priority": "high",
        "tags": ["test", "sample"],
        "assignee": "test_user",
    }


@pytest.fixture
def sample_task(sample_task_data: dict[str, Any]) -> Task:
    """Sample Task instance for tests.

    Args:
        sample_task_data: Task data fixture

    Returns:
        Task instance
    """
    return Task(**sample_task_data)


@pytest.fixture
def sample_epic_data() -> dict[str, Any]:
    """Sample epic data for tests.

    Returns:
        Dictionary with epic data
    """
    return {
        "id": "EPIC-001",
        "title": "Test Epic",
        "description": "Epic description",
        "state": "open",
        "priority": "high",
        "tags": ["epic"],
        "child_issues": ["TEST-123", "TEST-124"],
    }


@pytest.fixture
def sample_epic(sample_epic_data: dict[str, Any]) -> Epic:
    """Sample Epic instance for tests.

    Args:
        sample_epic_data: Epic data fixture

    Returns:
        Epic instance
    """
    return Epic(**sample_epic_data)


@pytest.fixture
def sample_comment_data() -> dict[str, Any]:
    """Sample comment data for tests.

    Returns:
        Dictionary with comment data
    """
    return {
        "id": "COMMENT-1",
        "ticket_id": "TEST-123",
        "author": "test_user",
        "content": "This is a test comment",
        "created_at": datetime.now(),
    }


@pytest.fixture
def sample_comment(sample_comment_data: dict[str, Any]) -> Comment:
    """Sample Comment instance for tests.

    Args:
        sample_comment_data: Comment data fixture

    Returns:
        Comment instance
    """
    return Comment(**sample_comment_data)


@pytest.fixture
def sample_search_query() -> SearchQuery:
    """Sample SearchQuery instance for tests.

    Returns:
        SearchQuery instance
    """
    return SearchQuery(
        query="test",
        state=TicketState.OPEN,
        priority=Priority.HIGH,
        tags=["test"],
        limit=10,
        offset=0,
    )


@pytest.fixture
def queue_db(temp_dir: Path) -> Generator[Queue, None, None]:
    """Queue instance with temporary database.

    Args:
        temp_dir: Temporary directory fixture

    Yields:
        Queue instance
    """
    db_path = temp_dir / "test_queue.db"
    queue = Queue(db_path=db_path)
    yield queue


@pytest.fixture
def mock_adapter_config() -> dict[str, Any]:
    """Mock adapter configuration.

    Returns:
        Configuration dictionary
    """
    return {"base_path": ".test_aitrackdown", "test_mode": True}


@pytest.fixture
def aitrackdown_temp_dir(temp_dir: Path) -> Path:
    """Temporary directory for AITrackdown adapter tests.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        Path to AITrackdown directory
    """
    ai_dir = temp_dir / ".aitrackdown"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "tickets").mkdir(exist_ok=True)
    (ai_dir / "comments").mkdir(exist_ok=True)
    return ai_dir


@pytest.fixture
def sample_ticket_file(
    aitrackdown_temp_dir: Path, sample_task_data: dict[str, Any]
) -> Path:
    """Create a sample ticket file for testing.

    Args:
        aitrackdown_temp_dir: AITrackdown directory
        sample_task_data: Task data

    Returns:
        Path to ticket file
    """
    ticket_file = aitrackdown_temp_dir / "tickets" / f"{sample_task_data['id']}.json"
    with open(ticket_file, "w") as f:
        json.dump(sample_task_data, f)
    return ticket_file


@pytest.fixture
def mock_http_client() -> Mock:
    """Mock HTTP client for adapter tests.

    Returns:
        Mock HTTP client
    """
    client = Mock()
    client.get = Mock(return_value=Mock(status_code=200, json=lambda: {}))
    client.post = Mock(return_value=Mock(status_code=201, json=lambda: {}))
    client.put = Mock(return_value=Mock(status_code=200, json=lambda: {}))
    client.delete = Mock(return_value=Mock(status_code=204))
    return client


@pytest.fixture
def state_transitions() -> dict[TicketState, list[TicketState]]:
    """Valid state transitions for testing.

    Returns:
        Dictionary mapping states to valid target states
    """
    return {
        TicketState.OPEN: [
            TicketState.IN_PROGRESS,
            TicketState.WAITING,
            TicketState.BLOCKED,
            TicketState.CLOSED,
        ],
        TicketState.IN_PROGRESS: [
            TicketState.READY,
            TicketState.WAITING,
            TicketState.BLOCKED,
            TicketState.OPEN,
        ],
        TicketState.READY: [
            TicketState.TESTED,
            TicketState.IN_PROGRESS,
            TicketState.BLOCKED,
        ],
        TicketState.TESTED: [TicketState.DONE, TicketState.IN_PROGRESS],
        TicketState.DONE: [TicketState.CLOSED],
        TicketState.WAITING: [
            TicketState.OPEN,
            TicketState.IN_PROGRESS,
            TicketState.CLOSED,
        ],
        TicketState.BLOCKED: [
            TicketState.OPEN,
            TicketState.IN_PROGRESS,
            TicketState.CLOSED,
        ],
        TicketState.CLOSED: [],
    }
