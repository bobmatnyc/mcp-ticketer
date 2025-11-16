"""Ticket ID persistence and recovery system."""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


class TicketRegistry:
    """Persistent registry for tracking ticket IDs and their lifecycle."""

    def __init__(self, db_path: Path | None = None):
        """Initialize ticket registry.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.mcp-ticketer/tickets.db

        """
        if db_path is None:
            db_dir = Path.home() / ".mcp-ticketer"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "tickets.db"

        self.db_path = str(db_path)
        self._lock = threading.Lock()
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            # Ticket registry table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ticket_registry (
                    queue_id TEXT PRIMARY KEY,
                    ticket_id TEXT,
                    adapter TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    title TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    ticket_data TEXT,
                    result_data TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'recovered'))
                )
            """
            )

            # Create indices
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_registry_ticket_id
                ON ticket_registry(ticket_id)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_registry_status
                ON ticket_registry(status)
            """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ticket_registry_adapter
                ON ticket_registry(adapter)
            """
            )

            # Ticket recovery log table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recovery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    queue_id TEXT NOT NULL,
                    recovery_type TEXT NOT NULL,
                    recovery_data TEXT,
                    timestamp TEXT NOT NULL,
                    success BOOLEAN NOT NULL
                )
            """
            )

    def register_ticket_operation(
        self,
        queue_id: str,
        adapter: str,
        operation: str,
        title: str,
        ticket_data: dict[str, Any],
    ) -> None:
        """Register a new ticket operation.

        Args:
            queue_id: Queue operation ID
            adapter: Adapter name
            operation: Operation type (create, update, etc.)
            title: Ticket title
            ticket_data: Original ticket data

        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO ticket_registry (
                        queue_id, adapter, operation, title, status,
                        created_at, updated_at, ticket_data, retry_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        queue_id,
                        adapter,
                        operation,
                        title,
                        "queued",
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps(ticket_data),
                        0,
                    ),
                )
                conn.commit()

    def update_ticket_status(
        self,
        queue_id: str,
        status: str,
        ticket_id: str | None = None,
        result_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        retry_count: int | None = None,
    ) -> None:
        """Update ticket operation status.

        Args:
            queue_id: Queue operation ID
            status: New status
            ticket_id: Created ticket ID (if available)
            result_data: Operation result data
            error_message: Error message if failed
            retry_count: Current retry count

        """
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                update_fields = ["status = ?", "updated_at = ?"]
                values: list[Any] = [status, datetime.now().isoformat()]

                if ticket_id is not None:
                    update_fields.append("ticket_id = ?")
                    values.append(ticket_id)

                if result_data is not None:
                    update_fields.append("result_data = ?")
                    values.append(json.dumps(result_data))

                if error_message is not None:
                    update_fields.append("error_message = ?")
                    values.append(error_message)

                if retry_count is not None:
                    update_fields.append("retry_count = ?")
                    values.append(retry_count)

                values.append(queue_id)

                conn.execute(
                    f"""
                    UPDATE ticket_registry
                    SET {', '.join(update_fields)}
                    WHERE queue_id = ?
                """,
                    values,
                )
                conn.commit()

    def get_ticket_info(self, queue_id: str) -> dict[str, Any] | None:
        """Get ticket information by queue ID.

        Args:
            queue_id: Queue operation ID

        Returns:
            Ticket information or None if not found

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ticket_registry WHERE queue_id = ?
            """,
                (queue_id,),
            )

            row = cursor.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            ticket_info = dict(zip(columns, row, strict=False))

            # Parse JSON fields
            if ticket_info.get("ticket_data"):
                ticket_info["ticket_data"] = json.loads(ticket_info["ticket_data"])
            if ticket_info.get("result_data"):
                ticket_info["result_data"] = json.loads(ticket_info["result_data"])

            return ticket_info

    def find_tickets_by_id(self, ticket_id: str) -> list[dict[str, Any]]:
        """Find all operations for a specific ticket ID.

        Args:
            ticket_id: Ticket ID to search for

        Returns:
            List of ticket operations

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ticket_registry
                WHERE ticket_id = ?
                ORDER BY created_at DESC
            """,
                (ticket_id,),
            )

            results = []
            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                ticket_info = dict(zip(columns, row, strict=False))

                # Parse JSON fields
                if ticket_info.get("ticket_data"):
                    ticket_info["ticket_data"] = json.loads(ticket_info["ticket_data"])
                if ticket_info.get("result_data"):
                    ticket_info["result_data"] = json.loads(ticket_info["result_data"])

                results.append(ticket_info)

            return results

    def get_failed_operations(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get failed operations that might need recovery.

        Args:
            limit: Maximum number of operations to return

        Returns:
            List of failed operations

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ticket_registry
                WHERE status = 'failed'
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (limit,),
            )

            results = []
            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                ticket_info = dict(zip(columns, row, strict=False))

                # Parse JSON fields
                if ticket_info.get("ticket_data"):
                    ticket_info["ticket_data"] = json.loads(ticket_info["ticket_data"])
                if ticket_info.get("result_data"):
                    ticket_info["result_data"] = json.loads(ticket_info["result_data"])

                results.append(ticket_info)

            return results

    def get_orphaned_tickets(self) -> list[dict[str, Any]]:
        """Get tickets that were created but queue operation failed.

        Returns:
            List of potentially orphaned tickets

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM ticket_registry
                WHERE ticket_id IS NOT NULL
                AND status IN ('processing', 'failed')
                ORDER BY updated_at DESC
            """
            )

            results = []
            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                ticket_info = dict(zip(columns, row, strict=False))

                # Parse JSON fields
                if ticket_info.get("ticket_data"):
                    ticket_info["ticket_data"] = json.loads(ticket_info["ticket_data"])
                if ticket_info.get("result_data"):
                    ticket_info["result_data"] = json.loads(ticket_info["result_data"])

                results.append(ticket_info)

            return results

    def attempt_recovery(self, queue_id: str, recovery_type: str) -> dict[str, Any]:
        """Attempt to recover a failed operation.

        Args:
            queue_id: Queue operation ID to recover
            recovery_type: Type of recovery to attempt

        Returns:
            Recovery result

        """
        ticket_info = self.get_ticket_info(queue_id)
        if not ticket_info:
            return {"success": False, "error": "Ticket operation not found"}

        recovery_data = {
            "original_status": ticket_info["status"],
            "recovery_type": recovery_type,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            if recovery_type == "mark_completed":
                # Mark as completed if ticket ID exists
                if ticket_info.get("ticket_id"):
                    self.update_ticket_status(
                        queue_id,
                        "recovered",
                        result_data={"recovery": "marked_completed"},
                    )
                    recovery_data["success"] = True
                    recovery_data["action"] = (
                        "Marked as completed based on existing ticket ID"
                    )
                else:
                    recovery_data["success"] = False
                    recovery_data["error"] = (
                        "No ticket ID available to mark as completed"
                    )

            elif recovery_type == "retry_operation":
                # Reset to queued status for retry
                self.update_ticket_status(
                    queue_id,
                    "queued",
                    error_message=None,
                    retry_count=ticket_info.get("retry_count", 0),
                )
                recovery_data["success"] = True
                recovery_data["action"] = "Reset to queued for retry"

            else:
                recovery_data["success"] = False
                recovery_data["error"] = f"Unknown recovery type: {recovery_type}"

            # Log recovery attempt
            self._log_recovery(
                queue_id, recovery_type, recovery_data, recovery_data["success"]
            )

            return recovery_data

        except Exception as e:
            recovery_data["success"] = False
            recovery_data["error"] = str(e)
            self._log_recovery(queue_id, recovery_type, recovery_data, False)
            return recovery_data

    def _log_recovery(
        self,
        queue_id: str,
        recovery_type: str,
        recovery_data: dict[str, Any],
        success: bool,
    ) -> None:
        """Log recovery attempt."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO recovery_log (
                        queue_id, recovery_type, recovery_data, timestamp, success
                    ) VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        queue_id,
                        recovery_type,
                        json.dumps(recovery_data),
                        datetime.now().isoformat(),
                        success,
                    ),
                )
                conn.commit()

    def get_recovery_history(self, queue_id: str) -> list[dict[str, Any]]:
        """Get recovery history for a queue operation.

        Args:
            queue_id: Queue operation ID

        Returns:
            List of recovery attempts

        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT * FROM recovery_log
                WHERE queue_id = ?
                ORDER BY timestamp DESC
            """,
                (queue_id,),
            )

            results = []
            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                recovery_info = dict(zip(columns, row, strict=False))
                if recovery_info.get("recovery_data"):
                    recovery_info["recovery_data"] = json.loads(
                        recovery_info["recovery_data"]
                    )
                results.append(recovery_info)

            return results

    def cleanup_old_entries(self, days: int = 30) -> int:
        """Clean up old completed entries.

        Args:
            days: Remove entries older than this many days

        Returns:
            Number of entries removed

        """
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM ticket_registry
                    WHERE status IN ('completed', 'recovered')
                    AND updated_at < ?
                """,
                    (cutoff_date,),
                )

                deleted_count = cursor.rowcount
                conn.commit()

                return deleted_count
