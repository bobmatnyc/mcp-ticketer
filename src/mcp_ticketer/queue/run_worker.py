"""Standalone worker runner module."""

import logging
import sys

from .queue import Queue
from .worker import Worker

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Run the worker process."""
    logger.info("Starting standalone worker process")

    try:
        # Create queue and worker
        queue = Queue()
        worker = Worker(queue)

        # Run worker (blocking)
        worker.start(daemon=False)

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Worker failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
