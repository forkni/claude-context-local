"""Deferred cleanup queue for failed project deletions.

Handles edge cases where project deletion fails due to locked files,
queueing them for retry on next server startup.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from mcp_server.storage_manager import get_storage_dir

logger = logging.getLogger(__name__)


class CleanupQueue:
    """Manages deferred cleanup tasks for locked resources.

    When a project deletion fails (e.g., database file is locked by another
    process), the directory is added to a persistent queue. On next server
    startup, the queue is processed and failed deletions are retried.

    Queue items are retried up to 3 times before being marked as permanently failed.
    """

    def __init__(self):
        """Initialize cleanup queue from persistent storage."""
        self.queue_file = get_storage_dir() / "cleanup_queue.json"
        self._queue: List[dict] = []
        self._load()

    def _load(self):
        """Load queue from disk."""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, encoding="utf-8") as f:
                    self._queue = json.load(f)
                logger.debug(f"Loaded {len(self._queue)} pending cleanup tasks")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cleanup queue: {e}")
                self._queue = []

    def _save(self):
        """Save queue to disk."""
        try:
            with open(self.queue_file, "w", encoding="utf-8") as f:
                json.dump(self._queue, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cleanup queue: {e}")

    def add(self, project_dir: str, reason: str) -> None:
        """Add a directory to the cleanup queue.

        Args:
            project_dir: Path to the directory to clean up
            reason: Human-readable reason for the failed deletion
        """
        self._queue.append(
            {
                "directory": str(project_dir),
                "reason": reason,
                "added_at": datetime.now().isoformat(),
                "attempts": 0,
            }
        )
        self._save()
        logger.info(f"Added to cleanup queue: {project_dir} (reason: {reason})")

    def process(self) -> dict:
        """Attempt to process pending cleanup tasks.

        This is called automatically on server startup. Each queued item is
        retried, and items that fail after 3 attempts are marked as permanently
        failed.

        Returns:
            dict with:
                - processed: Number of successfully deleted directories
                - failed: List of directories that failed after 3 attempts
                - remaining: Number of items still pending in queue
        """
        import shutil

        if not self._queue:
            return {"processed": 0, "failed": [], "remaining": 0}

        logger.info(f"Processing {len(self._queue)} deferred cleanup tasks...")

        processed = 0
        failed = []
        remaining = []

        for item in self._queue:
            path = Path(item["directory"])

            # If path doesn't exist, cleanup was already done (externally)
            if not path.exists():
                processed += 1
                logger.debug(f"Cleanup already done: {path}")
                continue

            # Attempt to delete
            try:
                shutil.rmtree(path)
                processed += 1
                logger.info(f"Deferred cleanup succeeded: {path}")
            except PermissionError as e:
                item["attempts"] += 1
                if item["attempts"] < 3:
                    remaining.append(item)
                    logger.warning(
                        f"Cleanup failed (attempt {item['attempts']}/3): {path} - {e}"
                    )
                else:
                    failed.append(item["directory"])
                    logger.error(
                        f"Cleanup failed after 3 attempts (giving up): {path} - {e}"
                    )
            except Exception as e:
                # Unexpected error, don't retry
                failed.append(item["directory"])
                logger.error(f"Unexpected cleanup error: {path} - {e}")

        # Update queue (keep only remaining items)
        self._queue = remaining
        self._save()

        result = {
            "processed": processed,
            "failed": failed,
            "remaining": len(remaining),
        }

        if processed > 0:
            logger.info(f"Cleanup summary: {processed} processed, {len(failed)} failed")

        return result

    def get_pending(self) -> List[dict]:
        """Get list of pending cleanup tasks.

        Returns:
            List of dicts with keys: directory, reason, added_at, attempts
        """
        return self._queue.copy()

    def clear(self) -> None:
        """Clear all pending tasks from the queue."""
        self._queue = []
        self._save()
        logger.info("Cleanup queue cleared")
