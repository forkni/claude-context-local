"""Pipeline stage: community-based remerge (pre-embed) and authoritative
community detection + summarisation (post-injection)."""

import logging
import traceback
from collections.abc import Callable
from typing import Any

from chunking.python_ast_chunker import CodeChunk
from embeddings.chunk_cache import resolve_chunk_cache
from graph.community_detector import CommunityDetector

from .config import SearchConfig, get_search_config
from .graph_integration import GraphIntegration
from .summary_stage import SummaryStage


logger = logging.getLogger(__name__)


class CommunityStage:
    """Pipeline stage encapsulating community-based remerge, module summaries,
    and (post-injection) authoritative community detection + summarisation.

    Split across two entry points because only the remerge is a chunk-set
    mutation that has to happen before embedding:

    - ``run()`` — pre-embed. Community-based remerge (only if
      ``enable_community_merge``) using a throwaway partition detected on a
      graph built from chunk metadata alone (no resolved call edges yet —
      the resolvers need ``metadata_store``, which doesn't exist until after
      embedding). That partition is remerge input only and is never
      persisted. Then module summaries, which must run after remerge
      finalises chunk_ids.
    - ``run_post_injection()`` — after ``IndexWriteStage._inject_call_edges``
      resolves the full call graph (pyan/libcst/LSP), re-detects communities
      on the now-enriched graph, persists that as the authoritative
      ``community_map``, and builds+embeds+indexes community summaries
      against it. This is the map ``CommunityRefreshStage``,
      ``EgoGraphRetriever``, and ``SubgraphExtractor`` read back later — its
      keys are final, post-remerge chunk_ids, matching what those consumers
      already assume.
    """

    def __init__(
        self,
        build_graph_fn: Callable[[list[CodeChunk]], GraphIntegration],
        regenerate_ids_fn: Callable[[list[CodeChunk], str], list[CodeChunk]],
        summary_stage: SummaryStage,
        embedder: Any | None = None,
        indexer: Any | None = None,
    ) -> None:
        self._build_graph = build_graph_fn
        self._regenerate_ids = regenerate_ids_fn
        self._summary_stage = summary_stage
        # Only needed by run_post_injection() (embed + add_embeddings).
        # Optional so the five construction sites in
        # tests/unit/search/test_community_stage.py that only exercise
        # run() keep working unmodified.
        self._embedder = embedder
        self._indexer = indexer

    def run(
        self,
        all_chunks: list[CodeChunk],
        project_path: str,
        config: SearchConfig,
    ) -> list[CodeChunk]:
        """Run community-based remerge and module summaries (pre-embed).

        Args:
            all_chunks: Chunks from the chunking pass (pre-remerge).
            project_path: Absolute path to the indexed project root.
            config: Current search configuration snapshot.

        Returns:
            Final chunk list after community remerge and module-summary
            injection. Community summaries are added later, by
            ``run_post_injection()``.
        """
        community_map = None

        # ========== Step A: Community-based Remerge ==========
        # Detection here feeds remerge only — the graph is built from chunk
        # metadata alone (no resolved call edges yet), so this partition is
        # deliberately transient and is never persisted. The authoritative,
        # persisted map is always run_post_injection()'s, computed on the
        # fully resolved graph.
        if config.chunking.enable_community_merge and all_chunks:
            logger.info("[COMMUNITY_MERGE] Detecting transient partition for remerge")

            try:
                temp_graph = self._build_graph(all_chunks)

                # pyrefly: ignore [bad-argument-type]
                detector = CommunityDetector(temp_graph.storage)
                community_map = detector.detect_communities(
                    resolution=config.chunking.community_resolution,
                    max_phantom_degree=getattr(
                        config.chunking, "max_phantom_degree", 20
                    ),
                )
                logger.info(
                    f"[COMMUNITY_MERGE] Detected {len(set(community_map.values()))} communities"
                    f" from {len(community_map)} nodes (transient, remerge input only)"
                )
            except Exception as e:  # noqa: BLE001 - resilience: optional community detection, continue without it
                logger.error(f"[COMMUNITY_MERGE] Detection failed: {e}")
                logger.error(traceback.format_exc())
                logger.warning("[COMMUNITY_MERGE] Continuing without community data")
                community_map = None

            if community_map:
                logger.info("[COMMUNITY_MERGE] Running community-based remerge")

                try:
                    # Deferred import: chunking.community_remerge pulls in the
                    # chunker stack which imports graph modules — keep
                    # deferred to avoid a cycle.
                    from chunking.community_remerge import (
                        remerge_chunks_with_communities,
                    )

                    all_chunks = remerge_chunks_with_communities(
                        chunks=all_chunks,
                        community_map=community_map,
                        # merger not supplied — community_remerge lazily
                        # constructs PythonChunker() to borrow
                        # _greedy_merge_small_chunks (P5).
                        min_tokens=config.chunking.min_chunk_tokens,
                        max_merged_tokens=config.chunking.max_merged_tokens,
                        token_method=config.chunking.token_estimation,
                        size_method=config.chunking.size_method,
                        use_community_boundary=(
                            config.chunking.merge_boundary != "sibling"
                        ),
                    )
                    logger.info(
                        f"[COMMUNITY_MERGE] Community remerge complete: {len(all_chunks)} chunks"
                    )

                    all_chunks = self._regenerate_ids(all_chunks, project_path)

                    logger.info(
                        f"[COMMUNITY_MERGE] Community merge complete: {len(all_chunks)} final chunks"
                    )

                except Exception as e:  # noqa: BLE001 - resilience: optional community remerge, fall back to unmerged chunks
                    logger.error(f"[COMMUNITY_MERGE] Failed: {e}")
                    logger.error(traceback.format_exc())
                    logger.warning(
                        "[COMMUNITY_MERGE] Continuing with unmerged chunks from Pass 1"
                    )

        # ========== File-Level Module Summaries (post-remerge) ==========
        if config.chunking.enable_file_summaries and all_chunks:
            module_summaries = self._summary_stage.generate_module_summaries(all_chunks)
            if module_summaries:
                all_chunks.extend(module_summaries)
                logger.info(
                    f"[FILE_SUMMARIES] Appended {len(module_summaries)} module summaries"
                )

        return all_chunks

    def run_post_injection(
        self,
        all_chunks: list[CodeChunk],
        project_name: str,
    ) -> int:
        """Detect communities on the fully resolved graph, persist, summarise.

        Must run after ``IndexWriteStage._inject_call_edges`` (the graph
        carries every pyan/libcst/LSP-resolved edge, not just the
        AST-derived subset available before embedding) and before
        ``save_indices`` (so the new summary chunks are persisted). A no-op
        returning 0 when community detection is disabled, there are no
        chunks, or this stage was constructed without an indexer/embedder
        (e.g. most of ``test_community_stage.py``'s construction sites,
        which only exercise ``run()``).

        Every step below is independently wrapped so a community-detection
        or summary failure never fails an otherwise-good reindex — matching
        the graceful-degradation contract used throughout this module.

        Args:
            all_chunks: Final, post-remerge, post-embed chunk list.
            project_name: Name used to key embedding metadata.

        Returns:
            Number of community-summary chunks embedded and indexed.
        """
        config = get_search_config()
        if not (
            config.chunking.enable_community_detection
            and all_chunks
            and self._indexer is not None
        ):
            return 0

        # Take the real graph from the indexer — the same accessor idiom
        # IndexWriteStage._inject_call_edges uses — never a temp graph.
        graph_integration = getattr(self._indexer, "_graph", None)
        storage = getattr(graph_integration, "storage", None)
        if storage is None:
            logger.warning("[COMMUNITY_DETECT] Graph storage not available — skipping")
            return 0

        logger.info("[COMMUNITY_DETECT] Running community detection on resolved graph")

        community_map: dict[str, int] | None = None
        try:
            detector = CommunityDetector(storage)
            community_map = detector.detect_communities(
                resolution=config.chunking.community_resolution,
                max_phantom_degree=getattr(config.chunking, "max_phantom_degree", 20),
            )
            logger.info(
                f"[COMMUNITY_DETECT] Detected {len(set(community_map.values()))} communities"
                f" from {len(community_map)} nodes"
            )
        except Exception as e:  # noqa: BLE001 - resilience: optional community detection, continue without it
            logger.error(f"[COMMUNITY_DETECT] Failed: {e}")
            logger.error(traceback.format_exc())
            return 0

        if not community_map:
            return 0

        try:
            storage.store_community_map(community_map)
            logger.info(
                "[COMMUNITY_DETECT] Community map persisted to graph storage"
                " (final, post-injection chunk_ids)"
            )
        except Exception as e:  # noqa: BLE001 - resilience: persistence failure must not fail the reindex
            logger.error(f"[COMMUNITY_DETECT] Failed to persist community map: {e}")
            logger.error(traceback.format_exc())
            # Detection succeeded but persistence didn't — still worth trying
            # to compute and index summaries from the in-memory map.

        if not config.chunking.enable_community_summaries:
            return 0

        try:
            community_summaries = self._summary_stage.compute_community_summaries(
                all_chunks, community_map, graph_integration
            )
        except Exception as e:  # noqa: BLE001 - resilience: optional community summaries, continue without them
            logger.error(f"[COMMUNITY_SUMMARIES] Failed to compute: {e}")
            logger.error(traceback.format_exc())
            return 0

        if not community_summaries or self._embedder is None:
            return 0

        try:
            # Same idiom as CommunityRefreshStage._regenerate_summaries —
            # cache_full_pass=False, strict=True zip, project_name/content
            # set per result. Do not re-derive it.
            embedding_results = self._embedder.embed_chunks(
                community_summaries,
                cache=resolve_chunk_cache(self._indexer.storage_dir, self._embedder),
                cache_full_pass=False,
            )
            for chunk, result in zip(
                community_summaries, embedding_results, strict=True
            ):
                result.metadata["project_name"] = project_name
                result.metadata["content"] = chunk.content
            if embedding_results:
                self._indexer.add_embeddings(embedding_results)
            logger.info(
                f"[COMMUNITY_SUMMARIES] Embedded and indexed {len(embedding_results)} community summaries"
            )
            return len(embedding_results)
        except Exception as e:  # noqa: BLE001 - resilience: optional community summary embed/index, continue without it
            logger.error(f"[COMMUNITY_SUMMARIES] Failed to embed/index: {e}")
            logger.error(traceback.format_exc())
            return 0
