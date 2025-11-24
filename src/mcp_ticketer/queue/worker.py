"""Background worker for processing queued ticket operations."""

import asyncio
import logging
import signal
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Import adapters module to trigger registration
import mcp_ticketer.adapters  # noqa: F401

from ..core import AdapterRegistry, Task
from .queue import Queue, QueueItem, QueueStatus
from .ticket_registry import TicketRegistry

# Load environment variables from .env.local
env_path = Path.cwd() / ".env.local"
if env_path.exists():
    load_dotenv(env_path)


# Configure logging
LOG_DIR = Path.home() / ".mcp-ticketer" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "worker.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class Worker:
    """Background worker for processing queue items with batch processing and concurrency."""

    # Rate limits per adapter (requests per minute)
    RATE_LIMITS = {
        "linear": 60,
        "jira": 30,
        "github": 60,
        "aitrackdown": 1000,  # Local, no rate limit
    }

    # Retry configuration
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 5  # seconds

    # Batch processing configuration
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_MAX_CONCURRENT = 5

    def __init__(
        self,
        queue: Queue | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    ):
        """Initialize worker.

        Args:
            queue: Queue instance (creates default if not provided)
            batch_size: Number of items to process in a batch
            max_concurrent: Maximum concurrent operations per adapter

        """
        self.queue = queue or Queue()
        self.ticket_registry = TicketRegistry()
        self.running = False
        self.stop_event = threading.Event()
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent

        # Track rate limits per adapter
        self.last_request_times: dict[str, datetime] = {}
        self.adapter_semaphores: dict[str, asyncio.Semaphore] = {}

        # Statistics
        self.stats = {
            "items_processed": 0,
            "items_failed": 0,
            "batches_processed": 0,
            "start_time": None,
        }

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        logger.info(
            f"Worker initialized with batch_size={batch_size}, max_concurrent={max_concurrent}"
        )

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def start(self, daemon: bool = True) -> None:
        """Start the worker.

        Args:
            daemon: Run as daemon process

        """
        if self.running:
            logger.warning("Worker already running")
            return

        self.running = True
        self.stats["start_time"] = datetime.now()
        logger.info("Starting worker...")

        if daemon:
            # Run in separate thread for daemon mode
            thread = threading.Thread(target=self._run_loop)
            thread.daemon = True
            thread.start()
        else:
            # Run in main thread
            self._run_loop()

    def stop(self) -> None:
        """Stop the worker."""
        logger.info("Stopping worker...")
        self.running = False
        self.stop_event.set()

    def _run_loop(self) -> None:
        """Run main worker loop with batch processing."""
        logger.info("Worker loop started")

        # Reset any stuck items on startup
        self.queue.reset_stuck_items()

        while self.running:
            try:
                # Get batch of pending items
                batch = self._get_batch()

                if batch:
                    # Process batch
                    asyncio.run(self._process_batch(batch))
                    self.stats["batches_processed"] += 1
                else:
                    # No items, wait a bit
                    self.stop_event.wait(timeout=1)

            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
                time.sleep(5)  # Prevent tight error loop

        logger.info("Worker loop stopped")

    def _get_batch(self) -> list[QueueItem]:
        """Get a batch of pending items from the queue.

        Returns:
            List of queue items to process

        """
        batch = []
        for _ in range(self.batch_size):
            item = self.queue.get_next_pending()
            if item:
                batch.append(item)
            else:
                break
        return batch

    async def _process_batch(self, batch: list[QueueItem]) -> None:
        """Process a batch of queue items with concurrency control.

        Args:
            batch: List of queue items to process

        """
        logger.info(f"Processing batch of {len(batch)} items")

        # Group items by adapter for concurrent processing
        adapter_groups: dict[str, list[Any]] = {}
        for item in batch:
            if item.adapter not in adapter_groups:
                adapter_groups[item.adapter] = []
            adapter_groups[item.adapter].append(item)

        # Process each adapter group concurrently
        tasks = []
        for adapter, items in adapter_groups.items():
            task = self._process_adapter_group(adapter, items)
            tasks.append(task)

        # Wait for all adapter groups to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_adapter_group(
        self, adapter: str, items: list[QueueItem]
    ) -> None:
        """Process items for a specific adapter with concurrency control.

        Args:
            adapter: Adapter name
            items: List of items for this adapter

        """
        logger.debug(f"Processing {len(items)} items for adapter {adapter}")

        # Get or create semaphore for this adapter
        if adapter not in self.adapter_semaphores:
            self.adapter_semaphores[adapter] = asyncio.Semaphore(self.max_concurrent)

        semaphore = self.adapter_semaphores[adapter]

        # Process items with concurrency control
        async def process_with_semaphore(item: QueueItem) -> None:
            async with semaphore:
                await self._process_item(item)

        # Create tasks for all items
        tasks = [process_with_semaphore(item) for item in items]

        # Process with concurrency control
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_item(self, item: QueueItem) -> None:
        """Process a single queue item.

        Args:
            item: Queue item to process

        """
        logger.info(
            f"Processing queue item {item.id}: {item.operation} on {item.adapter}"
        )

        # Register operation start in ticket registry
        title = item.ticket_data.get("title", "Unknown")
        self.ticket_registry.register_ticket_operation(
            item.id, item.adapter, item.operation, title, item.ticket_data
        )
        self.ticket_registry.update_ticket_status(item.id, "processing")

        try:
            # Check rate limit
            await self._check_rate_limit(item.adapter)

            # Get adapter
            adapter = self._get_adapter(item)
            if not adapter:
                raise ValueError(f"Unknown adapter: {item.adapter}")

            # Process operation
            result = await self._execute_operation(adapter, item)

            # Extract ticket ID from result if available
            ticket_id = None
            if isinstance(result, dict):
                ticket_id = result.get("id")

            # Mark as completed in both queue and registry (atomic)
            success = self.queue.update_status(
                item.id,
                QueueStatus.COMPLETED,
                result=result,
                expected_status=QueueStatus.PROCESSING,
            )
            if success:
                self.ticket_registry.update_ticket_status(
                    item.id, "completed", ticket_id=ticket_id, result_data=result
                )
            else:
                logger.warning(
                    f"Failed to update status for {item.id} - item may have been processed by another worker"
                )

            self.stats["items_processed"] += 1
            logger.info(f"Successfully processed {item.id}, ticket ID: {ticket_id}")

        except Exception as e:
            logger.error(f"Error processing {item.id}: {e}")

            # Update registry with error
            self.ticket_registry.update_ticket_status(
                item.id, "failed", error_message=str(e), retry_count=item.retry_count
            )

            # Check retry count
            if item.retry_count < self.MAX_RETRIES:
                # Retry with exponential backoff
                retry_delay = self.BASE_RETRY_DELAY * (2**item.retry_count)
                logger.info(
                    f"Retrying {item.id} after {retry_delay}s (attempt {item.retry_count + 1}/{self.MAX_RETRIES})"
                )

                # Increment retry count and reset to pending (atomic)
                new_retry_count = self.queue.increment_retry(
                    item.id, expected_status=QueueStatus.PROCESSING
                )
                if new_retry_count >= 0:
                    self.ticket_registry.update_ticket_status(
                        item.id, "queued", retry_count=new_retry_count
                    )
                else:
                    logger.warning(
                        f"Failed to increment retry for {item.id} - item may have been processed by another worker"
                    )

                # Wait before retry
                await asyncio.sleep(retry_delay)
            else:
                # Max retries exceeded, mark as failed (atomic)
                success = self.queue.update_status(
                    item.id,
                    QueueStatus.FAILED,
                    error_message=str(e),
                    expected_status=QueueStatus.PROCESSING,
                )
                if success:
                    self.ticket_registry.update_ticket_status(
                        item.id,
                        "failed",
                        error_message=str(e),
                        retry_count=item.retry_count,
                    )
                else:
                    logger.warning(
                        f"Failed to mark {item.id} as failed - item may have been processed by another worker"
                    )
                self.stats["items_failed"] += 1
                logger.error(f"Max retries exceeded for {item.id}, marking as failed")

    async def _check_rate_limit(self, adapter: str) -> None:
        """Check and enforce rate limits.

        Args:
            adapter: Adapter name

        """
        if adapter not in self.RATE_LIMITS:
            return

        limit = self.RATE_LIMITS[adapter]
        min_interval = 60.0 / limit  # seconds between requests

        if adapter in self.last_request_times:
            last_time = self.last_request_times[adapter]
            elapsed = (datetime.now() - last_time).total_seconds()

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {adapter}")
                await asyncio.sleep(wait_time)

        self.last_request_times[adapter] = datetime.now()

    def _get_adapter(self, item: QueueItem) -> Any:
        """Get adapter instance for item.

        Args:
            item: Queue item

        Returns:
            Adapter instance

        """
        # Load configuration from the project directory where the item was created
        import os
        from pathlib import Path

        from ..cli.main import load_config

        # PRIORITY 1: Use adapter_config from queue item if available (explicit config)
        if item.adapter_config:
            logger.info("Worker using explicit adapter_config from queue item")
            adapter_config = item.adapter_config
            logger.info(f"Worker adapter config for {item.adapter}: {adapter_config}")
        else:
            # PRIORITY 2: Load from project config file
            # Use item's project_dir if available, otherwise use current directory
            project_path = Path(item.project_dir) if item.project_dir else None

            # Load environment variables from project directory's .env.local if it exists
            if project_path:
                env_file = project_path / ".env.local"
                if env_file.exists():
                    logger.info(f"Worker loading environment from {env_file}")
                    load_dotenv(env_file)

            logger.info(f"Worker project_path: {project_path}")
            logger.info(f"Worker current working directory: {os.getcwd()}")

            config = load_config(project_dir=project_path)
            logger.info(f"Worker loaded config: {config}")
            adapters_config = config.get("adapters", {})
            adapter_config = adapters_config.get(item.adapter, {})
            logger.info(f"Worker adapter config for {item.adapter}: {adapter_config}")

        # Add environment variables for authentication
        if item.adapter == "linear":
            if not adapter_config.get("api_key"):
                adapter_config["api_key"] = os.getenv("LINEAR_API_KEY")
        elif item.adapter == "github":
            if not adapter_config.get("token"):
                adapter_config["token"] = os.getenv("GITHUB_TOKEN")
        elif item.adapter == "jira":
            if not adapter_config.get("api_token"):
                adapter_config["api_token"] = os.getenv("JIRA_ACCESS_TOKEN")
            if not adapter_config.get("email"):
                adapter_config["email"] = os.getenv("JIRA_ACCESS_USER")

        logger.info(f"Worker final adapter config: {adapter_config}")

        # Add debugging for Linear adapter specifically
        if item.adapter == "linear":
            import os

            linear_api_key = os.getenv("LINEAR_API_KEY", "Not set")
            logger.info(
                f"Worker LINEAR_API_KEY: {linear_api_key[:20] if linear_api_key != 'Not set' else 'Not set'}..."
            )
            logger.info(
                f"Worker adapter_config api_key: {adapter_config.get('api_key', 'Not set')[:20] if adapter_config.get('api_key') else 'Not set'}..."
            )

        adapter = AdapterRegistry.get_adapter(item.adapter, adapter_config)
        logger.info(
            f"Worker created adapter: {type(adapter)} with team_id: {getattr(adapter, 'team_id_config', 'Not set')}"
        )

        # Add more debugging for Linear adapter
        if item.adapter == "linear":
            logger.info(
                f"Worker Linear adapter api_key: {getattr(adapter, 'api_key', 'Not set')[:20] if getattr(adapter, 'api_key', None) else 'Not set'}..."
            )
            logger.info(
                f"Worker Linear adapter team_key: {getattr(adapter, 'team_key', 'Not set')}"
            )

        return adapter

    async def _execute_operation(self, adapter: Any, item: QueueItem) -> dict[str, Any]:
        """Execute the queued operation.

        Args:
            adapter: Adapter instance
            item: Queue item

        Returns:
            Operation result

        """
        operation = item.operation
        data = item.ticket_data

        if operation == "create":
            task = Task(**data)
            result = await adapter.create(task)
            return {"id": result.id, "title": result.title, "state": result.state}

        elif operation == "update":
            ticket_id = data.pop("ticket_id")
            result = await adapter.update(ticket_id, data)
            return {"id": result.id if result else None, "success": bool(result)}

        elif operation == "delete":
            ticket_id = data.get("ticket_id")
            result = await adapter.delete(ticket_id)
            return {"success": result}

        elif operation == "transition":
            ticket_id = data.get("ticket_id")
            state = data.get("state")
            result = await adapter.transition_state(ticket_id, state)
            return {
                "id": result.id if result else None,
                "state": state,
                "success": bool(result),
            }

        elif operation == "comment":
            ticket_id = data.get("ticket_id")
            content = data.get("content")
            await adapter.add_comment(ticket_id, content)
            return {"success": True}

        # Hierarchy operations
        elif operation == "create_epic":
            result = await adapter.create_epic(
                title=data["title"],
                description=data.get("description"),
                **{k: v for k, v in data.items() if k not in ["title", "description"]},
            )
            return {
                "id": result.id if result else None,
                "title": result.title if result else None,
                "type": "epic",
                "success": bool(result),
            }

        elif operation == "create_issue":
            result = await adapter.create_issue(
                title=data["title"],
                description=data.get("description"),
                epic_id=data.get("epic_id"),
                **{
                    k: v
                    for k, v in data.items()
                    if k not in ["title", "description", "epic_id"]
                },
            )
            return {
                "id": result.id if result else None,
                "title": result.title if result else None,
                "type": "issue",
                "epic_id": data.get("epic_id"),
                "success": bool(result),
            }

        elif operation == "create_task":
            result = await adapter.create_task(
                title=data["title"],
                parent_id=data["parent_id"],
                description=data.get("description"),
                **{
                    k: v
                    for k, v in data.items()
                    if k not in ["title", "parent_id", "description"]
                },
            )
            return {
                "id": result.id if result else None,
                "title": result.title if result else None,
                "type": "task",
                "parent_id": data["parent_id"],
                "success": bool(result),
            }

        else:
            raise ValueError(f"Unknown operation: {operation}")

    def get_status(self) -> dict[str, Any]:
        """Get worker status.

        Returns:
            Status information

        """
        queue_stats = self.queue.get_stats()

        # Calculate throughput
        throughput = 0
        if self.stats["start_time"]:
            elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
            if elapsed > 0:
                throughput = (
                    self.stats["items_processed"] / elapsed * 60
                )  # items per minute

        return {
            "running": self.running,
            "configuration": {
                "batch_size": self.batch_size,
                "max_concurrent": self.max_concurrent,
            },
            "worker_stats": {
                "items_processed": self.stats["items_processed"],
                "items_failed": self.stats["items_failed"],
                "batches_processed": self.stats["batches_processed"],
                "throughput_per_minute": throughput,
                "uptime_seconds": (
                    (datetime.now() - self.stats["start_time"]).total_seconds()
                    if self.stats["start_time"]
                    else 0
                ),
            },
            "queue_stats": queue_stats,
            "total_pending": queue_stats.get(QueueStatus.PENDING.value, 0),
            "total_processing": queue_stats.get(QueueStatus.PROCESSING.value, 0),
            "total_completed": queue_stats.get(QueueStatus.COMPLETED.value, 0),
            "total_failed": queue_stats.get(QueueStatus.FAILED.value, 0),
        }

    @classmethod
    def get_logs(cls, lines: int = 50) -> str:
        """Get recent log entries.

        Args:
            lines: Number of lines to return

        Returns:
            Log content

        """
        if not LOG_FILE.exists():
            return "No logs available"

        with open(LOG_FILE) as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
