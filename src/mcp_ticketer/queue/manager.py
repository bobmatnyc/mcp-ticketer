"""Worker manager with file-based locking for single instance."""

import fcntl
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import psutil

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages worker process with file-based locking."""

    def __init__(self) -> None:
        """Initialize worker manager."""
        # Lazy import to avoid circular dependency
        from .queue import Queue

        self.lock_file = Path.home() / ".mcp-ticketer" / "worker.lock"
        self.pid_file = Path.home() / ".mcp-ticketer" / "worker.pid"
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.queue = Queue()

    def _acquire_lock(self) -> bool:
        """Acquire exclusive lock for worker.

        Returns:
            True if lock acquired, False otherwise

        """
        try:
            # Create lock file if it doesn't exist
            if not self.lock_file.exists():
                self.lock_file.touch()

            # Try to acquire exclusive lock
            self.lock_fd = open(self.lock_file, "w")
            fcntl.lockf(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

            # Write PID to lock file
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()

            return True
        except OSError:
            # Lock already held
            return False

    def _release_lock(self) -> None:
        """Release worker lock."""
        if hasattr(self, "lock_fd"):
            fcntl.lockf(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()

        # Clean up PID file
        if self.pid_file.exists():
            self.pid_file.unlink()

    def start_if_needed(self) -> bool:
        """Start worker if not already running and there are pending items.

        Returns:
            True if worker started or already running, False otherwise

        """
        # Check if worker is already running
        if self.is_running():
            logger.debug("Worker already running")
            return True

        # Check if there are pending items
        if self.queue.get_pending_count() == 0:
            logger.debug("No pending items, worker not needed")
            return False

        # Try to start worker
        return self.start()

    def start(self, timeout: float = 30.0) -> bool:
        """Start the worker process.

        Args:
            timeout: Maximum seconds to wait for worker to become fully operational (default: 30)

        Returns:
            True if started successfully, False otherwise

        Raises:
            TimeoutError: If worker doesn't start within timeout period

        Note:
            If timeout occurs, a worker may already be running in another process.
            Check for stale lock files or processes using `get_status()`.

        """
        # Check if already running
        if self.is_running():
            logger.info("Worker is already running")
            return True

        # Try to acquire lock
        if not self._acquire_lock():
            logger.warning("Could not acquire lock - another worker may be running")
            # Wait briefly to see if worker becomes operational
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.is_running():
                    logger.info("Worker started by another process")
                    return True
                time.sleep(1)

            raise TimeoutError(
                f"Worker start timed out after {timeout}s. "
                f"Lock is held but worker is not running. "
                f"Check for stale lock files or zombie processes."
            )

        try:
            # Start worker in subprocess using the same Python executable as the CLI
            # This ensures the worker can import mcp_ticketer modules
            # Lazy import to avoid circular dependency
            from ..cli.python_detection import get_mcp_ticketer_python

            python_executable = get_mcp_ticketer_python()
            cmd = [python_executable, "-m", "mcp_ticketer.queue.run_worker"]

            # Prepare environment for subprocess
            # Ensure the subprocess gets the same environment as the parent
            subprocess_env = os.environ.copy()

            # Explicitly load environment variables from .env.local if it exists
            env_file = Path.cwd() / ".env.local"
            if env_file.exists():
                logger.debug(f"Loading environment from {env_file} for subprocess")
                from dotenv import dotenv_values

                env_vars = dotenv_values(env_file)
                subprocess_env.update(env_vars)
                logger.debug(
                    f"Added {len(env_vars)} environment variables from .env.local"
                )

            # Start as background process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=subprocess_env,  # Pass environment explicitly
                cwd=str(Path.cwd()),  # Ensure correct working directory
            )

            # Save PID
            self.pid_file.write_text(str(process.pid))

            # Wait for worker to become fully operational with timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Check if process exists
                if not psutil.pid_exists(process.pid):
                    logger.error("Worker process died during startup")
                    self._cleanup()
                    return False

                # Check if worker is fully running (not just process exists)
                if self.is_running():
                    elapsed = time.time() - start_time
                    logger.info(
                        f"Worker started successfully in {elapsed:.1f}s with PID {process.pid}"
                    )
                    return True

                # Log progress for long startups
                elapsed = time.time() - start_time
                if elapsed > 5 and int(elapsed) % 5 == 0:
                    logger.debug(
                        f"Waiting for worker to start, elapsed: {elapsed:.1f}s"
                    )

                time.sleep(0.5)

            # Timeout reached
            raise TimeoutError(
                f"Worker start timed out after {timeout}s. "
                f"Process spawned (PID {process.pid}) but worker did not become operational. "
                f"Check worker logs for startup errors."
            )

        except TimeoutError:
            # Re-raise timeout errors with context preserved
            raise
        except Exception as e:
            logger.error(f"Failed to start worker: {e}")
            self._release_lock()
            return False

    def stop(self) -> bool:
        """Stop the worker process.

        Returns:
            True if stopped successfully, False otherwise

        """
        pid = self._get_pid()
        if not pid:
            logger.info("No worker process to stop")
            return True

        try:
            # Check if process exists
            if not psutil.pid_exists(pid):
                logger.info("Worker process not found, cleaning up")
                self._cleanup()
                return True

            # Send SIGTERM
            process = psutil.Process(pid)
            process.terminate()

            # Wait for graceful shutdown
            gone, alive = psutil.wait_procs([process], timeout=10)

            if gone:
                logger.info(f"Worker process {pid} terminated gracefully")
            else:
                # Force kill if still alive
                for p in alive:
                    logger.warning(f"Force killing worker process {p.pid}")
                    p.kill()

            self._cleanup()
            return True

        except Exception as e:
            logger.error(f"Error stopping worker: {e}")
            return False

    def restart(self) -> bool:
        """Restart the worker process.

        Returns:
            True if restarted successfully, False otherwise

        """
        logger.info("Restarting worker...")
        self.stop()
        time.sleep(1)  # Brief pause between stop and start
        return self.start()

    def is_running(self) -> bool:
        """Check if worker is currently running.

        Returns:
            True if running, False otherwise

        """
        pid = self._get_pid()
        if not pid:
            return False

        try:
            # Check if process exists and is actually our worker
            if psutil.pid_exists(pid):
                process = psutil.Process(pid)
                cmdline = " ".join(process.cmdline())
                return "run_worker" in cmdline or "mcp_ticketer.queue" in cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return False

    def get_status(self) -> dict[str, Any]:
        """Get detailed worker status.

        Returns:
            Status information

        """
        is_running = self.is_running()
        pid = self._get_pid() if is_running else None

        status: dict[str, Any] = {"running": is_running, "pid": pid}

        # Add process info if running
        if is_running and pid:
            try:
                process = psutil.Process(pid)
                status.update(
                    {
                        "cpu_percent": process.cpu_percent(),
                        "memory_mb": process.memory_info().rss / 1024 / 1024,
                        "create_time": process.create_time(),
                        "status": process.status(),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        # Add queue stats
        queue_stats = self.queue.get_stats()
        status["queue"] = queue_stats

        return status

    def _get_pid(self) -> int | None:
        """Get worker PID from file.

        Returns:
            Process ID or None if not found

        """
        if not self.pid_file.exists():
            return None

        try:
            pid_text = self.pid_file.read_text().strip()
            return int(pid_text)
        except (OSError, ValueError):
            return None

    def _cleanup(self) -> None:
        """Clean up lock and PID files."""
        self._release_lock()
        if self.pid_file.exists():
            self.pid_file.unlink()
        if self.lock_file.exists():
            self.lock_file.unlink()
