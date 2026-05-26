"""Pipeline stage: community detection, Phase-1 summaries, chunk remerge, Phase-2 summaries."""

import logging
import traceback
from collections.abc import Callable

from chunking.python_ast_chunker import CodeChunk

from .config import SearchConfig
from .graph_integration import GraphIntegration
from .summary_stage import SummaryStage


logger = logging.getLogger(__name__)


class CommunityStage:
    """Pipeline stage encapsulating community detection, community+module summarisation, and remerge.

    Ordering constraint (from SummaryStage): compute_community_summaries must be called with
    pre-remerge chunk_ids; generate_module_summaries must be called after remerge.
    """

    def __init__(
        self,
        build_graph_fn: Callable[[list[CodeChunk]], GraphIntegration],
        regenerate_ids_fn: Callable[[list[CodeChunk], str], list[CodeChunk]],
        summary_stage: SummaryStage,
    ) -> None:
        self._build_graph = build_graph_fn
        self._regenerate_ids = regenerate_ids_fn
        self._summary_stage = summary_stage

    def run(
        self,
        all_chunks: list[CodeChunk],
        project_path: str,
        config: SearchConfig,
    ) -> list[CodeChunk]:
        """Run community detection, summaries, and remerge.

        Args:
            all_chunks: Chunks from the chunking pass (pre-remerge).
            project_path: Absolute path to the indexed project root.
            config: Current search configuration snapshot.

        Returns:
            Final chunk list after community remerge and summary injection.
        """
        community_map = None
        temp_graph = None

        # ========== Step A: Community Detection ==========
        if config.chunking.enable_community_detection and all_chunks:
            logger.info("[COMMUNITY_DETECT] Running community detection")
            logger.info(f"[COMMUNITY_DETECT] Starting with {len(all_chunks)} chunks")

            try:
                temp_graph = self._build_graph(all_chunks)

                from graph.community_detector import CommunityDetector

                # pyrefly: ignore [bad-argument-type]
                detector = CommunityDetector(temp_graph.storage)
                community_map = detector.detect_communities(
                    resolution=config.chunking.community_resolution,
                    max_phantom_degree=getattr(
                        config.chunking, "max_phantom_degree", 20
                    ),
                )
                logger.info(
                    f"[COMMUNITY_DETECT] Detected {len(set(community_map.values()))} communities"
                    f" from {len(community_map)} nodes"
                )

                if community_map and temp_graph:
                    # pyrefly: ignore [missing-attribute]
                    temp_graph.storage.store_community_map(community_map)
                    logger.info(
                        "[COMMUNITY_DETECT] Community map persisted to graph storage"
                    )

            except Exception as e:
                logger.error(f"[COMMUNITY_DETECT] Failed: {e}")
                logger.error(traceback.format_exc())
                logger.warning("[COMMUNITY_DETECT] Continuing without community data")
                community_map = None

        # ========== Community Summaries Phase 1: Compute (pre-remerge chunk_ids) ==========
        community_summaries: list[CodeChunk] = []
        if config.chunking.enable_community_summaries and community_map and all_chunks:
            community_summaries = self._summary_stage.compute_community_summaries(
                all_chunks, community_map, temp_graph
            )

        # ========== Step B: Community-based Remerge ==========
        if config.chunking.enable_community_merge and community_map and all_chunks:
            logger.info("[COMMUNITY_MERGE] Running community-based remerge")

            try:
                from chunking.languages.base import LanguageChunker

                all_chunks = LanguageChunker.remerge_chunks_with_communities(
                    chunks=all_chunks,
                    community_map=community_map,
                    min_tokens=config.chunking.min_chunk_tokens,
                    max_merged_tokens=config.chunking.max_merged_tokens,
                    token_method=config.chunking.token_estimation,
                    size_method=config.chunking.size_method,
                )
                logger.info(
                    f"[COMMUNITY_MERGE] Community remerge complete: {len(all_chunks)} chunks"
                )

                all_chunks = self._regenerate_ids(all_chunks, project_path)

                logger.info(
                    f"[COMMUNITY_MERGE] Community merge complete: {len(all_chunks)} final chunks"
                )

            except Exception as e:
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

        # ========== Community Summaries Phase 2: Append (post-remerge) ==========
        if community_summaries:
            all_chunks.extend(community_summaries)
            logger.info(
                f"[COMMUNITY_SUMMARIES] Appended {len(community_summaries)} community summaries"
            )

        return all_chunks
