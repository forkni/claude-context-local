"""Summary-chunk generation for full and incremental indexing.

Ordering constraint (see incremental_indexer._full_index for the call sequence):
  1. compute_community_summaries() — BEFORE community remerge, because
     community_map keys are pre-remerge chunk_ids.
  2. generate_module_summaries() — AFTER community remerge, because remerge
     shifts line numbers and finalises chunk_ids.

Each method catches its own errors and returns [] on failure, matching the
graceful-degradation contract of the inline code it replaces.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk
    from search.graph_integration import GraphIntegration

logger = logging.getLogger(__name__)


class SummaryStage:
    """Owns summary-chunk generation for a full index pass.

    The two methods encode the ordering constraint that _full_index imposes:
    compute_community_summaries() must run before remerge; generate_module_summaries()
    must run after. The caller is responsible for the interleaved remerge step.
    """

    def compute_community_summaries(
        self,
        all_chunks: list[CodeChunk],
        community_map: dict[str, int],
        temp_graph: GraphIntegration | None,
    ) -> list[CodeChunk]:
        """Compute community-summary CodeChunks with centrality-weighted hub detection.

        Must be called BEFORE community remerge (chunk_ids must match community_map).
        Returns [] on any failure so the caller can proceed without community summaries.
        """
        try:
            from graph.community_summarizer import generate_community_summaries

            centrality_scores: dict[str, float] | None = None
            if temp_graph is not None:
                try:
                    from graph.graph_queries import GraphQueryEngine

                    # pyrefly: ignore [bad-argument-type]
                    gqe = GraphQueryEngine(temp_graph.storage)
                    centrality_scores = gqe.compute_centrality(method="pagerank")
                    logger.info(
                        f"[COMMUNITY_SUMMARIES] Computed centrality for "
                        f"{len(centrality_scores)} nodes"
                    )
                except Exception as ce:  # noqa: BLE001 - resilience: centrality optional, falls back to line-count weighting
                    logger.debug(
                        f"[COMMUNITY_SUMMARIES] Centrality unavailable, "
                        f"using line-count fallback: {ce}"
                    )

            summaries = generate_community_summaries(
                all_chunks, community_map, centrality_scores
            )
            logger.info(
                f"[COMMUNITY_SUMMARIES] Computed {len(summaries)} community summary chunks"
            )
            return summaries

        except Exception as e:  # noqa: BLE001 - resilience: optional community summaries, empty list on failure
            logger.warning(f"[COMMUNITY_SUMMARIES] Failed to compute: {e}")
            return []

    def generate_module_summaries(
        self,
        all_chunks: list[CodeChunk],
    ) -> list[CodeChunk]:
        """Generate per-file module-summary CodeChunks.

        Must be called AFTER community remerge (chunk_ids must be stable).
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
