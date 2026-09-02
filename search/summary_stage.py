"""Summary-chunk generation for full and incremental indexing.

generate_and_extend() owns the whole pre-embed summary step — config
gate included — for both IncrementalIndexer._full_index() and
IncrementalIndexer._add_new_chunks().

Catches its own errors and returns [] on failure, matching the
graceful-degradation contract of the inline code it replaces.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .config import get_search_config


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk

logger = logging.getLogger(__name__)


class SummaryStage:
    """Owns pre-embed summary-chunk generation for full and incremental passes."""

    def generate_and_extend(
        self,
        chunks: list[CodeChunk],
        *,
        log_prefix: str,
        appended_noun: str,
    ) -> int:
        """Generate module summaries and append them to ``chunks`` in place.

        Owns the whole calling idiom shared by the full path
        (``IncrementalIndexer._full_index``) and the incremental path
        (``IncrementalIndexer._add_new_chunks``), including the
        ``enable_file_summaries`` config gate — disabled or empty input
        is a zero-work no-op.

        Args:
            chunks: Chunk list to summarize and extend in place.
            log_prefix: Log-line prefix (e.g. ``"[FILE_SUMMARIES]"``).
            appended_noun: Noun for the appended-count log line (the two
                passes historically word it differently).

        Returns:
            Number of summary chunks appended.
        """
        if not (get_search_config().chunking.enable_file_summaries and chunks):
            return 0
        module_summaries = self.generate_module_summaries(chunks)
        if module_summaries:
            chunks.extend(module_summaries)
            logger.info(
                f"{log_prefix} Appended {len(module_summaries)} {appended_noun}"
            )
        return len(module_summaries)

    def generate_module_summaries(
        self,
        all_chunks: list[CodeChunk],
    ) -> list[CodeChunk]:
        """Generate per-file module-summary CodeChunks.

        Returns [] on any failure.
        """
        try:
            from chunking.file_summarizer import generate_file_summaries

            summaries = generate_file_summaries(all_chunks)
            if summaries:
                logger.info(
                    f"[FILE_SUMMARIES] Generated {len(summaries)} module summary chunks"
                )
            return summaries

        except Exception as e:  # noqa: BLE001 - resilience: optional module summaries, empty list on failure
            logger.warning(f"[FILE_SUMMARIES] Failed: {e}")
            return []
