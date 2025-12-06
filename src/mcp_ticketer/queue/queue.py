"""SQLite-based queue system for async ticket operations."""

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any


class QueueStatus(str, Enum):
    """Queue item status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueItem:
    """Represents a queued operation."""

    id: str
    ticket_data: dict[str, Any]
    adapter: str
    operation: str
    status: QueueStatus
    created_at: datetime
    processed_at: datetime | None = None
    error_message: str | None = None
    retry_count: int = 0
    result: dict[str, Any] | None = None
    project_dir: str | None = None
    adapter_config: dict[str, Any] | None = None  # Adapter configuration

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.processed_at:
            data["processed_at"] = self.processed_at.isoformat()
        return data

    @classmethod
    def from_row(cls, row: tuple) -> "QueueItem":
        """Create from database row."""
        return cls(
            id=row[0],
            ticket_data=json.loads(row[1]),
            adapter=row[2],
            operation=row[3],
            status=QueueStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            processed_at=datetime.fromisoformat(row[6]) if row[6] else None,
            error_message=row[7],
            retry_count=row[8],
            result=json.loads(row[9]) if row[9] else None,
            project_dir=row[10] if len(row) > 10 else None,
            adapter_config=json.loads(row[11]) if len(row) > 11 and row[11] else None,
        )


class Queue:
    """Thread-safe SQLite queue for ticket operations."""

    def __init__(self, db_path: Path | None = None):
        """Initialize queue with database connection.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.mcp-ticketer/queue.db

        """
        if db_path is None:
            db_dir = Path.home() / ".mcp-ticketer"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "queue.db"

        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS queue (
                    id TEXT PRIMARY KEY,
                    ticket_data TEXT NOT NULL,
                    adapter TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    result TEXT,
                    CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
                )
            """
            )

            # Create indices for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_status
                ON queue(status)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_created
                ON queue(created_at)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_queue_adapter
                ON queue(adapter)
            """
            )

            # Migration: Add project_dir column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(queue)")
            columns = [row[1] for row in cursor.fetchall()]
            if "project_dir" not in columns:
                conn.execute("ALTER TABLE queue ADD COLUMN project_dir TEXT")
            if "adapter_config" not in columns:
                conn.execute("ALTER TABLE queue ADD COLUMN adapter_config TEXT")

            conn.commit()

    def add(
        self,
        ticket_data: dict[str, Any],
        adapter: str,
        operation: str,
        project_dir: str | None = None,
        adapter_config: dict[str, Any] | None = None,
    ) -> str:
        """Add item to queue.

        Args:
            ticket_data: The ticket data for the operation
            adapter: Name of the adapter to use
            operation: Operation to perform (create, update, delete, etc.)
            project_dir: Project directory for config resolution (defaults to current directory)
            adapter_config: Adapter configuration to use (optional, for explicit config passing)

        Returns:
            Queue ID for tracking

        """
        queue_id = f"Q-{uuid.uuid4().hex[:8].upper()}"

        # Default to current working directory if not provided
        if project_dir is None:
            project_dir = str(Path.cwd())

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO queue (
                        id, ticket_data, adapter, operation,
                        status, created_at, retry_count, project_dir, adapter_config
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        queue_id,
                        json.dumps(ticket_data),
                        adapter,
                        operation,
                        QueueStatus.PENDING.value,
                        datetime.now().isoformat(),
                        0,
                        project_dir,
                        json.dumps(adapter_config) if adapter_config else None,
                    ),
                )
                conn.commit()

        return queue_id

    def get_next_pending(self) -> QueueItem | None:
        """Get next pending item from queue atomically.

        Returns:
            Next pending QueueItem or None if queue is empty

        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                # Use a transaction to atomically get and update the item
                conn.execute("BEGIN IMMEDIATE")
                try:
                    # Get next pending item ordered by creation time
                    cursor = conn.execute(
                        """
                        SELECT * FROM queue
                        WHERE status = ?
                        ORDER BY created_at
                        LIMIT 1
                    """,
                        (QueueStatus.PENDING.value,),
                    )

                    row = cursor.fetchone()
                    if row:
                        # Atomically mark as processing
                        update_cursor = conn.execute(
                            """
                            UPDATE queue
                            SET status = ?, processed_at = ?
                            WHERE id = ? AND status = ?
                        """,
                            (
                                QueueStatus.PROCESSING.value,
                                datetime.now().isoformat(),
                                row[0],
                                QueueStatus.PENDING.value,
                            ),
                        )

                        # Check if update was successful (prevents race conditions)
                        if update_cursor.rowcount == 1:
                            conn.commit()
                            # Create QueueItem from row and update status
                            item = QueueItem.from_row(row)
                            item.status = QueueStatus.PROCESSING
                            return item
                        else:
                            # Item was already taken by another worker
                            conn.rollback()
                            return None
                    else:
                        conn.rollback()
                        return None

                except Exception:
                    conn.rollback()
                    raise

        return None

    def update_status(
        self,
        queue_id: str,
        status: QueueStatus,
        error_message: str | None = None,
        result: dict[str, Any] | None = None,
        expected_status: QueueStatus | None = None,
    ) -> bool:
        """Update queue item status atomically.

        Args:
            queue_id: Queue item ID
            status: New status
            error_message: Error message if failed
            result: Result data if completed
            expected_status: Expected current status (for atomic updates)

        Returns:
            True if update was successful, False if item was in unexpected state

        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    processed_at = (
                        datetime.now().isoformat()
                        if status in [QueueStatus.COMPLETED, QueueStatus.FAILED]
                        else None
                    )

                    if expected_status:
                        # Atomic update with status check
                        cursor = conn.execute(
                            """
                            UPDATE queue
                            SET status = ?, processed_at = ?,
                                error_message = ?, result = ?
                            WHERE id = ? AND status = ?
                        """,
                            (
                                status.value,
                                processed_at,
                                error_message,
                                json.dumps(result) if result else None,
                                queue_id,
                                expected_status.value,
                            ),
                        )
                        success = cursor.rowcount == 1
                    else:
                        # Regular update
                        cursor = conn.execute(
                            """
                            UPDATE queue
                            SET status = ?, processed_at = ?,
                                error_message = ?, result = ?
                            WHERE id = ?
                        """,
                            (
                                status.value,
                                processed_at,
                                error_message,
                                json.dumps(result) if result else None,
                                queue_id,
                            ),
                        )
                        success = cursor.rowcount == 1

                    if success:
                        conn.commit()
                    else:
                        conn.rollback()

                    return success

                except Exception:
                    conn.rollback()
                    raise

    def increment_retry(
        self, queue_id: str, expected_status: QueueStatus | None = None
    ) -> int:
        """Increment retry count and reset to pending atomically.

        Args:
            queue_id: Queue item ID
            expected_status: Expected current status for atomic operation

        Returns:
            New retry count, or -1 if operation failed

        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                try:
                    if expected_status:
                        # Atomic increment with status check
                        cursor = conn.execute(
                            """
                            UPDATE queue
                            SET retry_count = retry_count + 1,
                                status = ?, processed_at = NULL,
                                error_message = NULL
                            WHERE id = ? AND status = ?
                            RETURNING retry_count
                        """,
                            (
                                QueueStatus.PENDING.value,
                                queue_id,
                                expected_status.value,
                            ),
                        )
                    else:
                        # Regular increment
                        cursor = conn.execute(
                            """
                            UPDATE queue
                            SET retry_count = retry_count + 1,
                                status = ?, processed_at = NULL,
                                error_message = NULL
                            WHERE id = ?
                            RETURNING retry_count
                        """,
                            (QueueStatus.PENDING.value, queue_id),
                        )

                    result = cursor.fetchone()
                    if result:
                        conn.commit()
                        return result[0]
                    else:
                        conn.rollback()
                        return -1

                except Exception:
                    conn.rollback()
                    raise

    def get_item(self, queue_id: str) -> QueueItem | None:
        """Get specific queue item by ID.

        Args:
            queue_id: Queue item ID

        Returns:
            QueueItem or None if not found

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM queue WHERE id = ?
            """,
                (queue_id,),
            )

            row = cursor.fetchone()
            return QueueItem.from_row(row) if row else None

    def list_items(
        self, status: QueueStatus | None = None, limit: int = 50
    ) -> list[QueueItem]:
        """List queue items.

        Args:
            status: Filter by status (optional)
            limit: Maximum items to return

        Returns:
            List of QueueItems

        """
        with sqlite3.connect(self.db_path) as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT * FROM queue
                    WHERE status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (status.value, limit),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM queue
                    ORDER BY created_at DESC
                    LIMIT ?
                """,
                    (limit,),
                )

            return [QueueItem.from_row(row) for row in cursor.fetchall()]

    def get_pending_count(self) -> int:
        """Get count of pending items.

        Returns:
            Number of pending items

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT COUNT(*) FROM queue
                WHERE status = ?
            """,
                (QueueStatus.PENDING.value,),
            )

            return cursor.fetchone()[0]

    def cleanup_old(self, days: int = 7) -> None:
        """Clean up old completed/failed items.

        Args:
            days: Delete items older than this many days

        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM queue
                    WHERE status IN (?, ?)
                    AND processed_at < ?
                """,
                    (
                        QueueStatus.COMPLETED.value,
                        QueueStatus.FAILED.value,
                        cutoff_date,
                    ),
                )
                conn.commit()

    def reset_stuck_items(self, timeout_minutes: int = 30) -> None:
        """Reset items stuck in processing state.

        Args:
            timeout_minutes: Consider items stuck after this many minutes

        """
        cutoff_time = (datetime.now() - timedelta(minutes=timeout_minutes)).isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE queue
                    SET status = ?, error_message = ?
                    WHERE status = ?
                    AND created_at < ?
                """,
                    (
                        QueueStatus.PENDING.value,
                        "Reset from stuck processing state",
                        QueueStatus.PROCESSING.value,
                        cutoff_time,
                    ),
                )
                conn.commit()

    def get_stats(self) -> dict[str, int]:
        """Get queue statistics.

        Returns:
            Dictionary with counts by status

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT status, COUNT(*)
                FROM queue
                GROUP BY status
            """
            )

            stats = {status.value: 0 for status in QueueStatus}
            for status, count in cursor.fetchall():
                stats[status] = count

            return stats

    def poll_until_complete(
        self,
        queue_id: str,
        timeout: float = 30.0,
        poll_interval: float = 0.5,
    ) -> QueueItem:
        """Poll queue item until completion or timeout.

        This enables synchronous waiting for queue operations, useful for:
        - CLI commands that need immediate results
        - Testing that requires actual ticket IDs
        - GitHub adapter operations requiring ticket numbers

        Args:
            queue_id: Queue ID to poll (e.g., "Q-9E7B5050")
            timeout: Maximum seconds to wait (default: 30.0)
            poll_interval: Seconds between polls (default: 0.5)

        Returns:
            Completed QueueItem with result data

        Raises:
            TimeoutError: If operation doesn't complete within timeout
            RuntimeError: If operation fails or queue item not found

        Example:
            >>> queue = Queue()
            >>> queue_id = queue.add(ticket_data={...}, adapter="github", operation="create")
            >>> # Start worker to process the queue
            >>> completed_item = queue.poll_until_complete(queue_id, timeout=30)
            >>> ticket_id = completed_item.result["id"]

        """
        import time

        start_time = time.time()
        elapsed = 0.0

        while elapsed < timeout:
            item = self.get_item(queue_id)

            if item is None:
                raise RuntimeError(f"Queue item not found: {queue_id}")

            if item.status == QueueStatus.COMPLETED:
                if item.result is None:
                    raise RuntimeError(
                        f"Queue operation completed but has no result data: {queue_id}"
                    )
                return item

            elif item.status == QueueStatus.FAILED:
                error_msg = item.error_message or "Unknown error"
                raise RuntimeError(
                    f"Queue operation failed: {error_msg} (queue_id: {queue_id})"
                )

            # Still pending or processing - wait and retry
            time.sleep(poll_interval)
            elapsed = time.time() - start_time

        # Timeout reached
        final_item = self.get_item(queue_id)
        final_status = final_item.status.value if final_item else "UNKNOWN"
        raise TimeoutError(
            f"Queue operation timed out after {timeout}s (status: {final_status}, queue_id: {queue_id})"
        )
