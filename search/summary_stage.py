"""Summary-chunk generation for full and incremental indexing.

generate_module_summaries() is called directly from
IncrementalIndexer._full_index(), pre-embed.

Catches its own errors and returns [] on failure, matching the
graceful-degradation contract of the inline code it replaces.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk

logger = logging.getLogger(__name__)


class SummaryStage:
    """Owns summary-chunk generation for a full index pass.

    generate_module_summaries() runs pre-embed, called directly from
    IncrementalIndexer._full_index().
    """

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
