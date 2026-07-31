"""Summary-chunk generation for full and incremental indexing.

Call sequence:
  1. generate_module_summaries() — called directly from
     IncrementalIndexer._full_index(), pre-embed.
  2. compute_community_summaries() — inside CommunityStage.run_post_injection(),
     AFTER call-edge injection. community_map keys are final, post-remerge
     chunk_ids — the same ids the resolved graph and the just-embedded
     chunks share, because detection itself now runs against that same
     enriched graph rather than a pre-embed temp graph.

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

    generate_module_summaries() runs pre-embed, called directly from
    IncrementalIndexer._full_index(). compute_community_summaries() runs
    post-embed, inside CommunityStage.run_post_injection(), after
    IndexWriteStage._inject_call_edges resolves the call graph.
    """

    def compute_community_summaries(
        self,
        all_chunks: list[CodeChunk],
        community_map: dict[str, int],
        graph: GraphIntegration | None,
    ) -> list[CodeChunk]:
        """Compute community-summary CodeChunks with centrality-weighted hub detection.

        Called from CommunityStage.run_post_injection() with the real,
        fully-resolved GraphIntegration — community_map keys are final,
        post-remerge chunk_ids, matching graph's nodes.
        CommunityRefreshStage._regenerate_summaries also calls this, with
        graph=None, for its centrality-free incremental refresh.
        Returns [] on any failure so the caller can proceed without community summaries.
        """
        try:
            from graph.community_summarizer import generate_community_summaries

            centrality_scores: dict[str, float] | None = None
            if graph is not None:
                try:
                    from graph.graph_queries import GraphQueryEngine

                    # pyrefly: ignore [bad-argument-type]
                    gqe = GraphQueryEngine(graph.storage)
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
