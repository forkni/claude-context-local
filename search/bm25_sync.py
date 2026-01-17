"""BM25 index synchronization utilities."""

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .indexer import CodeIndexManager

logger = logging.getLogger(__name__)

# Threshold for triggering resync (10% difference affects search quality)
DESYNC_THRESHOLD = 0.10


class BM25SyncManager:
    """Manages BM25 index synchronization with dense vectors."""

    def __init__(self, indexer: "CodeIndexManager"):
        """Initialize BM25 sync manager.

        Args:
            indexer: CodeIndexManager instance to manage
        """
        self.indexer = indexer

    def sync_if_needed(self, log_prefix: str = "INCREMENTAL") -> tuple[bool, int]:
        """Auto-sync BM25 if significant desync detected (>10% difference).

        Args:
            log_prefix: Prefix for log messages (e.g., "INCREMENTAL" or "FULL_INDEX")

        Returns:
            tuple[bool, int]: (bm25_resynced, bm25_resync_count)
        """
        bm25_resynced = False
        bm25_resync_count = 0

        if hasattr(self.indexer, "get_stats") and hasattr(
            self.indexer, "resync_bm25_from_dense"
        ):
            try:
                stats = self.indexer.get_stats()
                bm25_count = stats.get("bm25_documents", 0)
                dense_count = stats.get("dense_vectors", 0)

                # Ensure counts are integers (not Mock objects in tests)
                if (
                    isinstance(bm25_count, int)
                    and isinstance(dense_count, int)
                    and dense_count > 0
                ):
                    desync_ratio = abs(dense_count - bm25_count) / dense_count
                    if desync_ratio > DESYNC_THRESHOLD:
                        logger.warning(
                            f"[{log_prefix}] Significant desync detected: BM25={bm25_count}, "
                            f"Dense={dense_count} ({desync_ratio:.1%} difference)"
                        )
                        logger.info(
                            f"[{log_prefix}] Auto-syncing BM25 from dense metadata..."
                        )
                        bm25_resync_count = self.indexer.resync_bm25_from_dense()
                        bm25_resynced = True
                        logger.info(
                            f"[{log_prefix}] BM25 resync complete: {bm25_resync_count} documents"
                        )
            except Exception as e:
                logger.debug(f"[{log_prefix}] BM25 sync check skipped: {e}")

        return bm25_resynced, bm25_resync_count
