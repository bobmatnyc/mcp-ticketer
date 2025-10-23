"""Tests for queue system (SQLite-based async operations)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from mcp_ticketer.queue.queue import Queue, QueueItem, QueueStatus


class TestQueueStatus:
    """Tests for QueueStatus enum."""

    def test_all_statuses_exist(self) -> None:
        """Test all queue statuses are defined."""
        assert QueueStatus.PENDING == "pending"
        assert QueueStatus.PROCESSING == "processing"
        assert QueueStatus.COMPLETED == "completed"
        assert QueueStatus.FAILED == "failed"

    def test_status_from_string(self) -> None:
        """Test creating QueueStatus from string."""
        assert QueueStatus("pending") == QueueStatus.PENDING
        assert QueueStatus("completed") == QueueStatus.COMPLETED


class TestQueueItem:
    """Tests for QueueItem dataclass."""

    def test_queue_item_creation(self) -> None:
        """Test creating QueueItem."""
        now = datetime.now()
        item = QueueItem(
            id="Q-TEST123",
            ticket_data={"title": "Test"},
            adapter="aitrackdown",
            operation="create",
            status=QueueStatus.PENDING,
            created_at=now,
        )
        assert item.id == "Q-TEST123"
        assert item.ticket_data == {"title": "Test"}
        assert item.adapter == "aitrackdown"
        assert item.operation == "create"
        assert item.status == QueueStatus.PENDING
        assert item.created_at == now
        assert item.processed_at is None
        assert item.error_message is None
        assert item.retry_count == 0

    def test_queue_item_to_dict(self) -> None:
        """Test converting QueueItem to dictionary."""
        now = datetime.now()
        item = QueueItem(
            id="Q-TEST123",
            ticket_data={"title": "Test"},
            adapter="aitrackdown",
            operation="create",
            status=QueueStatus.COMPLETED,
            created_at=now,
            processed_at=now,
            result={"ticket_id": "TASK-001"},
        )
        item_dict = item.to_dict()

        assert isinstance(item_dict, dict)
        assert item_dict["id"] == "Q-TEST123"
        assert item_dict["adapter"] == "aitrackdown"
        assert item_dict["status"] == QueueStatus.COMPLETED
        # Timestamps should be ISO format strings
        assert isinstance(item_dict["created_at"], str)
        assert isinstance(item_dict["processed_at"], str)

    def test_queue_item_from_row(self) -> None:
        """Test creating QueueItem from database row."""
        now = datetime.now()
        row = (
            "Q-TEST123",
            '{"title": "Test"}',
            "aitrackdown",
            "create",
            "pending",
            now.isoformat(),
            None,
            None,
            0,
            None,
        )
        item = QueueItem.from_row(row)

        assert item.id == "Q-TEST123"
        assert item.ticket_data == {"title": "Test"}
        assert item.status == QueueStatus.PENDING
        assert item.retry_count == 0
        assert item.processed_at is None


class TestQueue:
    """Tests for Queue class."""

    def test_queue_initialization(self, temp_dir: Path) -> None:
        """Test queue initialization creates database."""
        db_path = temp_dir / "test.db"
        Queue(db_path=db_path)

        assert db_path.exists()
        # Check database schema
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='queue'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_queue_add_item(self, queue_db: Queue) -> None:
        """Test adding item to queue."""
        ticket_data = {"title": "Test ticket", "priority": "high"}
        queue_id = queue_db.add(
            ticket_data=ticket_data,
            adapter="aitrackdown",
            operation="create",
        )

        assert queue_id is not None
        assert queue_id.startswith("Q-")

        # Verify item was added
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.ticket_data == ticket_data
        assert item.adapter == "aitrackdown"
        assert item.operation == "create"
        assert item.status == QueueStatus.PENDING

    def test_queue_get_next_pending(self, queue_db: Queue) -> None:
        """Test getting next pending item from queue."""
        # Add multiple items
        id1 = queue_db.add({"title": "First"}, "aitrackdown", "create")
        id2 = queue_db.add({"title": "Second"}, "aitrackdown", "create")

        # Get first pending item
        item = queue_db.get_next_pending()
        assert item is not None
        assert item.id == id1
        assert item.status == QueueStatus.PROCESSING  # Should be marked as processing

        # Get second pending item
        item = queue_db.get_next_pending()
        assert item is not None
        assert item.id == id2

        # No more pending items
        item = queue_db.get_next_pending()
        assert item is None

    def test_queue_update_status(self, queue_db: Queue) -> None:
        """Test updating queue item status."""
        queue_id = queue_db.add({"title": "Test"}, "aitrackdown", "create")

        # Update to completed
        result = {"ticket_id": "TASK-001"}
        queue_db.update_status(
            queue_id=queue_id,
            status=QueueStatus.COMPLETED,
            result=result,
        )

        # Verify update
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.status == QueueStatus.COMPLETED
        assert item.result == result
        assert item.processed_at is not None

    def test_queue_update_status_failed(self, queue_db: Queue) -> None:
        """Test updating queue item status to failed."""
        queue_id = queue_db.add({"title": "Test"}, "aitrackdown", "create")

        # Update to failed
        error_msg = "Connection timeout"
        queue_db.update_status(
            queue_id=queue_id,
            status=QueueStatus.FAILED,
            error_message=error_msg,
        )

        # Verify update
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.status == QueueStatus.FAILED
        assert item.error_message == error_msg
        assert item.processed_at is not None

    def test_queue_increment_retry(self, queue_db: Queue) -> None:
        """Test incrementing retry count."""
        queue_id = queue_db.add({"title": "Test"}, "aitrackdown", "create")

        # Increment retry
        retry_count = queue_db.increment_retry(queue_id)
        assert retry_count == 1

        # Verify item
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.retry_count == 1
        assert item.status == QueueStatus.PENDING  # Reset to pending for retry

        # Increment again
        retry_count = queue_db.increment_retry(queue_id)
        assert retry_count == 2

    def test_queue_get_item(self, queue_db: Queue) -> None:
        """Test getting specific queue item by ID."""
        ticket_data = {"title": "Specific ticket"}
        queue_id = queue_db.add(ticket_data, "aitrackdown", "update")

        # Get item
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.id == queue_id
        assert item.ticket_data == ticket_data
        assert item.operation == "update"

    def test_queue_get_item_not_found(self, queue_db: Queue) -> None:
        """Test getting non-existent queue item returns None."""
        item = queue_db.get_item("Q-NOTEXIST")
        assert item is None

    def test_queue_list_items(self, queue_db: Queue) -> None:
        """Test listing queue items."""
        # Add items with different statuses
        id1 = queue_db.add({"title": "Pending"}, "aitrackdown", "create")
        id2 = queue_db.add({"title": "Another"}, "aitrackdown", "create")

        # Mark one as completed
        queue_db.update_status(id2, QueueStatus.COMPLETED)

        # List all items
        items = queue_db.list_items()
        assert len(items) == 2

        # List only pending
        pending_items = queue_db.list_items(status=QueueStatus.PENDING)
        assert len(pending_items) == 1
        assert pending_items[0].id == id1

        # List only completed
        completed_items = queue_db.list_items(status=QueueStatus.COMPLETED)
        assert len(completed_items) == 1
        assert completed_items[0].id == id2

    def test_queue_list_items_limit(self, queue_db: Queue) -> None:
        """Test listing queue items with limit."""
        # Add multiple items
        for i in range(10):
            queue_db.add({"title": f"Item {i}"}, "aitrackdown", "create")

        # List with limit
        items = queue_db.list_items(limit=5)
        assert len(items) == 5

    def test_queue_get_pending_count(self, queue_db: Queue) -> None:
        """Test getting count of pending items."""
        # Initially empty
        assert queue_db.get_pending_count() == 0

        # Add pending items
        queue_db.add({"title": "Test 1"}, "aitrackdown", "create")
        queue_db.add({"title": "Test 2"}, "aitrackdown", "create")
        assert queue_db.get_pending_count() == 2

        # Mark one as processing
        item = queue_db.get_next_pending()
        assert queue_db.get_pending_count() == 1

        # Mark as completed
        if item:
            queue_db.update_status(item.id, QueueStatus.COMPLETED)
        assert queue_db.get_pending_count() == 1

    def test_queue_cleanup_old(self, queue_db: Queue) -> None:
        """Test cleaning up old completed/failed items."""
        # Add items
        id1 = queue_db.add({"title": "Old completed"}, "aitrackdown", "create")
        id2 = queue_db.add({"title": "Old failed"}, "aitrackdown", "create")
        id3 = queue_db.add({"title": "Recent"}, "aitrackdown", "create")

        # Mark items
        queue_db.update_status(id1, QueueStatus.COMPLETED)
        queue_db.update_status(id2, QueueStatus.FAILED)

        # Manually update timestamps to simulate old items
        import sqlite3

        old_date = (datetime.now() - timedelta(days=10)).isoformat()
        with sqlite3.connect(queue_db.db_path) as conn:
            conn.execute(
                "UPDATE queue SET processed_at = ? WHERE id = ?",
                (old_date, id1),
            )
            conn.execute(
                "UPDATE queue SET processed_at = ? WHERE id = ?",
                (old_date, id2),
            )
            conn.commit()

        # Cleanup items older than 7 days
        queue_db.cleanup_old(days=7)

        # Old items should be deleted
        assert queue_db.get_item(id1) is None
        assert queue_db.get_item(id2) is None

        # Recent item should still exist
        assert queue_db.get_item(id3) is not None

    def test_queue_reset_stuck_items(self, queue_db: Queue) -> None:
        """Test resetting items stuck in processing state."""
        # Add item and mark as processing
        queue_id = queue_db.add({"title": "Stuck"}, "aitrackdown", "create")
        _ = queue_db.get_next_pending()  # Marks as processing

        # Manually update timestamp to simulate stuck item
        import sqlite3

        old_date = (datetime.now() - timedelta(hours=2)).isoformat()
        with sqlite3.connect(queue_db.db_path) as conn:
            conn.execute(
                "UPDATE queue SET created_at = ? WHERE id = ?",
                (old_date, queue_id),
            )
            conn.commit()

        # Reset stuck items (timeout 30 minutes)
        queue_db.reset_stuck_items(timeout_minutes=30)

        # Item should be reset to pending
        item = queue_db.get_item(queue_id)
        assert item is not None
        assert item.status == QueueStatus.PENDING
        assert item.error_message == "Reset from stuck processing state"

    def test_queue_get_stats(self, queue_db: Queue) -> None:
        """Test getting queue statistics."""
        # Initially all zero
        stats = queue_db.get_stats()
        assert stats[QueueStatus.PENDING.value] == 0
        assert stats[QueueStatus.PROCESSING.value] == 0
        assert stats[QueueStatus.COMPLETED.value] == 0
        assert stats[QueueStatus.FAILED.value] == 0

        # Add items with different statuses
        id1 = queue_db.add({"title": "Test 1"}, "aitrackdown", "create")
        id2 = queue_db.add({"title": "Test 2"}, "aitrackdown", "create")
        queue_db.add({"title": "Test 3"}, "aitrackdown", "create")

        queue_db.update_status(id1, QueueStatus.COMPLETED)
        queue_db.update_status(id2, QueueStatus.FAILED)
        # id3 remains pending

        # Check stats
        stats = queue_db.get_stats()
        assert stats[QueueStatus.PENDING.value] == 1
        assert stats[QueueStatus.COMPLETED.value] == 1
        assert stats[QueueStatus.FAILED.value] == 1
        assert stats[QueueStatus.PROCESSING.value] == 0

    def test_queue_thread_safety(self, temp_dir: Path) -> None:
        """Test queue operations are thread-safe."""
        import threading

        db_path = temp_dir / "threaded.db"
        queue = Queue(db_path=db_path)

        def add_items(start: int, count: int) -> None:
            for i in range(start, start + count):
                queue.add({"title": f"Item {i}"}, "aitrackdown", "create")

        # Create multiple threads adding items
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_items, args=(i * 10, 10))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have all 50 items
        items = queue.list_items(limit=100)
        assert len(items) == 50
