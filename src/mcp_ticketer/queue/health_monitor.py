"""Queue health monitoring and alerting system."""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import psutil

from .manager import WorkerManager
from .queue import Queue, QueueStatus

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class HealthAlert:
    """Health alert with severity and details."""

    def __init__(
        self,
        level: HealthStatus,
        message: str,
        details: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ):
        self.level = level
        self.message = message
        self.details = details or {}
        self.timestamp = timestamp or datetime.now()

    def __str__(self) -> str:
        """Return string representation of alert."""
        return f"[{self.level.upper()}] {self.message}"


class QueueHealthMonitor:
    """Monitors queue health and provides immediate alerts."""

    # Health check thresholds
    WORKER_TIMEOUT_SECONDS = 30  # Worker should process items within 30s
    STUCK_ITEM_THRESHOLD = 300  # 5 minutes for stuck items
    HIGH_FAILURE_RATE = 0.3  # 30% failure rate is concerning
    QUEUE_BACKLOG_WARNING = 10  # Warn if more than 10 pending items
    QUEUE_BACKLOG_CRITICAL = 50  # Critical if more than 50 pending items

    def __init__(self, queue: Queue | None = None):
        """Initialize health monitor.

        Args:
            queue: Queue instance to monitor. Creates new if None.

        """
        self.queue = queue or Queue()
        self.manager = WorkerManager()
        self.last_check = datetime.now()
        self.alerts: list[HealthAlert] = []

    def check_health(self) -> dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status with alerts and metrics

        """
        self.alerts.clear()

        # Check worker status
        worker_health = self._check_worker_health()

        # Check queue status
        queue_health = self._check_queue_health()

        # Check for stuck items
        stuck_health = self._check_stuck_items()

        # Check failure rates
        failure_health = self._check_failure_rates()

        # Determine overall health
        overall_status = self._determine_overall_status()

        health_report = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "alerts": [
                {
                    "level": alert.level,
                    "message": alert.message,
                    "details": alert.details,
                }
                for alert in self.alerts
            ],
            "metrics": {
                "worker": worker_health,
                "queue": queue_health,
                "stuck_items": stuck_health,
                "failure_rate": failure_health,
            },
        }

        self.last_check = datetime.now()
        return health_report

    def _check_worker_health(self) -> dict[str, Any]:
        """Check worker process health."""
        worker_status = self.manager.get_status()

        metrics = {
            "running": worker_status["running"],
            "pid": worker_status.get("pid"),
            "cpu_percent": worker_status.get("cpu_percent", 0),
            "memory_mb": worker_status.get("memory_mb", 0),
        }

        if not worker_status["running"]:
            # Check if we have pending items but no worker
            pending_count = self.queue.get_pending_count()
            if pending_count > 0:
                self.alerts.append(
                    HealthAlert(
                        HealthStatus.CRITICAL,
                        f"Worker not running but {pending_count} items pending",
                        {"pending_count": pending_count, "action": "start_worker"},
                    )
                )
            else:
                self.alerts.append(
                    HealthAlert(
                        HealthStatus.WARNING,
                        "Worker not running (no pending items)",
                        {"action": "worker_idle"},
                    )
                )
        else:
            # Worker is running, check if it's responsive
            pid = worker_status.get("pid")
            if pid:
                try:
                    psutil.Process(pid)
                    # Check if worker has been idle too long with pending items
                    pending_count = self.queue.get_pending_count()
                    if pending_count > 0:
                        # Check for items that have been pending too long
                        old_pending = self._get_old_pending_items()
                        if old_pending:
                            self.alerts.append(
                                HealthAlert(
                                    HealthStatus.WARNING,
                                    f"Worker running but {len(old_pending)} items pending for >30s",
                                    {
                                        "old_pending_count": len(old_pending),
                                        "worker_pid": pid,
                                    },
                                )
                            )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    self.alerts.append(
                        HealthAlert(
                            HealthStatus.CRITICAL,
                            "Worker PID exists but process not accessible",
                            {"pid": pid, "action": "restart_worker"},
                        )
                    )

        return metrics

    def _check_queue_health(self) -> dict[str, Any]:
        """Check queue status and backlog."""
        stats = self.queue.get_stats()

        pending = stats.get("pending", 0)
        processing = stats.get("processing", 0)
        failed = stats.get("failed", 0)
        completed = stats.get("completed", 0)

        metrics = {
            "pending": pending,
            "processing": processing,
            "failed": failed,
            "completed": completed,
            "total": pending + processing + failed + completed,
        }

        # Check backlog levels
        if pending >= self.QUEUE_BACKLOG_CRITICAL:
            self.alerts.append(
                HealthAlert(
                    HealthStatus.CRITICAL,
                    f"Critical queue backlog: {pending} pending items",
                    {"pending_count": pending, "action": "scale_workers"},
                )
            )
        elif pending >= self.QUEUE_BACKLOG_WARNING:
            self.alerts.append(
                HealthAlert(
                    HealthStatus.WARNING,
                    f"High queue backlog: {pending} pending items",
                    {"pending_count": pending},
                )
            )

        # Check for too many processing items (might indicate stuck workers)
        if processing > 5:  # Should rarely have more than a few processing
            self.alerts.append(
                HealthAlert(
                    HealthStatus.WARNING,
                    f"Many items in processing state: {processing}",
                    {"processing_count": processing, "action": "check_stuck_items"},
                )
            )

        return metrics

    def _check_stuck_items(self) -> dict[str, Any]:
        """Check for items stuck in processing state."""
        # Reset stuck items first
        self.queue.reset_stuck_items(timeout_minutes=5)  # 5 minute timeout

        # Get current stuck items
        stuck_items = self._get_stuck_processing_items()

        metrics = {
            "stuck_count": len(stuck_items),
            "stuck_items": [item.id for item in stuck_items],
        }

        if stuck_items:
            self.alerts.append(
                HealthAlert(
                    HealthStatus.WARNING,
                    f"Found {len(stuck_items)} stuck items, auto-reset applied",
                    {
                        "stuck_items": [item.id for item in stuck_items],
                        "action": "items_reset",
                    },
                )
            )

        return metrics

    def _check_failure_rates(self) -> dict[str, Any]:
        """Check recent failure rates."""
        stats = self.queue.get_stats()

        total_items = sum(stats.values())
        failed_items = stats.get("failed", 0)

        failure_rate = failed_items / total_items if total_items > 0 else 0

        metrics = {
            "failure_rate": failure_rate,
            "failed_count": failed_items,
            "total_count": total_items,
        }

        if failure_rate >= self.HIGH_FAILURE_RATE and total_items >= 10:
            self.alerts.append(
                HealthAlert(
                    HealthStatus.CRITICAL,
                    f"High failure rate: {failure_rate:.1%} ({failed_items}/{total_items})",
                    {"failure_rate": failure_rate, "action": "investigate_failures"},
                )
            )

        return metrics

    def _determine_overall_status(self) -> HealthStatus:
        """Determine overall health status from alerts."""
        if not self.alerts:
            return HealthStatus.HEALTHY

        # Check for critical alerts
        if any(alert.level == HealthStatus.CRITICAL for alert in self.alerts):
            return HealthStatus.CRITICAL

        # Check for warnings
        if any(alert.level == HealthStatus.WARNING for alert in self.alerts):
            return HealthStatus.WARNING

        return HealthStatus.HEALTHY

    def _get_old_pending_items(self) -> list:
        """Get items that have been pending for too long."""
        cutoff_time = datetime.now() - timedelta(seconds=self.WORKER_TIMEOUT_SECONDS)

        items = self.queue.list_items(status=QueueStatus.PENDING, limit=100)
        return [item for item in items if item.created_at < cutoff_time]

    def _get_stuck_processing_items(self) -> list:
        """Get items stuck in processing state."""
        cutoff_time = datetime.now() - timedelta(seconds=self.STUCK_ITEM_THRESHOLD)

        items = self.queue.list_items(status=QueueStatus.PROCESSING, limit=100)
        return [item for item in items if item.created_at < cutoff_time]

    def get_immediate_alerts(self) -> list[HealthAlert]:
        """Get alerts that require immediate attention."""
        return [
            alert
            for alert in self.alerts
            if alert.level in [HealthStatus.CRITICAL, HealthStatus.FAILED]
        ]

    def auto_repair(self) -> dict[str, Any]:
        """Attempt automatic repair of detected issues."""
        repair_actions = []

        # Check health first
        self.check_health()

        for alert in self.alerts:
            action = alert.details.get("action")

            if action == "start_worker":
                try:
                    if self.manager.start():
                        repair_actions.append(
                            f"Started worker for {alert.details.get('pending_count')} pending items"
                        )
                    else:
                        repair_actions.append("Failed to start worker")
                except Exception as e:
                    repair_actions.append(f"Error starting worker: {e}")

            elif action == "restart_worker":
                try:
                    self.manager.stop()
                    time.sleep(2)
                    if self.manager.start():
                        repair_actions.append("Restarted unresponsive worker")
                    else:
                        repair_actions.append("Failed to restart worker")
                except Exception as e:
                    repair_actions.append(f"Error restarting worker: {e}")

            elif action == "items_reset":
                repair_actions.append(
                    f"Reset {alert.details.get('stuck_items', [])} stuck items"
                )

        return {
            "actions_taken": repair_actions,
            "timestamp": datetime.now().isoformat(),
        }
