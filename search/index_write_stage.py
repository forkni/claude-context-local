"""Pipeline stage: embed chunks, write index, save snapshot, sync BM25, clear GPU."""

import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chunking.python_ast_chunker import CodeChunk
from chunking.relationships.external_call_graph import build_call_edges
from evaluation.chunk_mapping import build_line_to_chunk_map
from merkle.merkle_dag import MerkleDAG
from merkle.snapshot_manager import SnapshotManager

from .bm25_sync import BM25SyncManager
from .indexer import CodeIndexManager as Indexer


logger = logging.getLogger(__name__)


@dataclass
class IncrementalIndexResult:
    """Result of an incremental or full index pass."""

    files_added: int
    files_removed: int
    files_modified: int
    chunks_added: int
    chunks_removed: int
    time_taken: float
    success: bool
    error: str | None = None
    bm25_resynced: bool = False
    bm25_resync_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "files_added": self.files_added,
            "files_removed": self.files_removed,
            "files_modified": self.files_modified,
            "chunks_added": self.chunks_added,
            "chunks_removed": self.chunks_removed,
            "time_taken": self.time_taken,
            "success": self.success,
            "error": self.error,
            "bm25_resynced": self.bm25_resynced,
            "bm25_resync_count": self.bm25_resync_count,
        }


class IndexWriteStage:
    """Pipeline stage that embeds chunks, writes the FAISS index, saves the snapshot, syncs BM25, and clears GPU cache."""

    def __init__(
        self,
        embedder: Any,
        indexer: Indexer,
        snapshot_manager: SnapshotManager,
        bm25_sync: BM25SyncManager,
        build_metadata_fn: Callable[..., dict[str, Any]],
        clear_gpu_fn: Callable[[str], None],
    ) -> None:
        self._embedder = embedder
        self._indexer = indexer
        self._snapshot_manager = snapshot_manager
        self._bm25_sync = bm25_sync
        self._build_metadata = build_metadata_fn
        self._clear_gpu = clear_gpu_fn

    def run(
        self,
        all_chunks: list[CodeChunk],
        project_name: str,
        dag: MerkleDAG,
        all_files: list[Any],
        supported_files: list[Any],
        start_time: float,
        repo_profile: object | None,
        project_path: str = "",
    ) -> IncrementalIndexResult:
        """Embed, index, snapshot, BM25-sync, and GPU-clear for a full index pass.

        Args:
            all_chunks: Final chunk list after community remerge and summary injection.
            project_name: Name used to key the snapshot and embedding metadata.
            dag: Merkle DAG built during this index pass.
            all_files: All files discovered by the DAG walker.
            supported_files: Subset of all_files with supported extensions.
            start_time: Epoch timestamp from the start of the full index pass.
            repo_profile: Repository profile computed during adaptive sizing, or None.
            project_path: Absolute path to the project root.  Used to gather
                Python files for pyan3 cross-module call-edge injection.
                Defaults to empty string (injection skipped when absent).

        Returns:
            IncrementalIndexResult describing the outcome of the index pass.
        """
        # Embed all chunks in one batched call
        all_embedding_results = []
        embed_error: str | None = None
        if all_chunks:
            try:
                logger.info(f"Starting embedding for {len(all_chunks)} chunks")
                all_embedding_results = self._embedder.embed_chunks(all_chunks)
                logger.info(
                    f"Successfully embedded {len(all_embedding_results)} chunks"
                )
                for chunk, embedding_result in zip(
                    all_chunks, all_embedding_results, strict=False
                ):
                    embedding_result.metadata["project_name"] = project_name
                    embedding_result.metadata["content"] = chunk.content
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                logger.error(traceback.format_exc())
                embed_error = str(e)

        if embed_error is not None:
            self._clear_gpu("FULL_INDEX")
            return IncrementalIndexResult(
                files_added=0,
                files_removed=0,
                files_modified=0,
                chunks_added=0,
                chunks_removed=0,
                time_taken=time.time() - start_time,
                success=False,
                error=embed_error,
            )

        # Add all embeddings to index at once
        if all_embedding_results:
            logger.info(f"Adding {len(all_embedding_results)} embeddings to index")
            self._indexer.add_embeddings(all_embedding_results)
            logger.info("Successfully added embeddings to index")
        else:
            logger.warning("No embedding results to add to index")

        chunks_added = len(all_embedding_results)

        # Inject cross-module call edges from pyan3 static analysis.
        # Must run after add_embeddings (graph populated) and before
        # save_indices (graph persisted).
        if project_path:
            self._inject_pyan_edges(project_path)

        # Save snapshot (reset cumulative_changed_files on full index pass)
        metadata = self._build_metadata(
            project_name=project_name,
            all_files=all_files,
            supported_files=supported_files,
            total_chunks=chunks_added,
            is_full=True,
            repo_profile=repo_profile,
            cumulative_changed_files=0,
        )
        self._snapshot_manager.save_snapshot(dag, metadata)

        logger.info("[INCREMENTAL] Saving index...")
        self._indexer.save_indices()
        logger.info("[INCREMENTAL] Index saved")

        bm25_resynced, bm25_resync_count = self._bm25_sync.sync_if_needed("FULL_INDEX")

        self._clear_gpu("FULL_INDEX")

        return IncrementalIndexResult(
            files_added=len(supported_files),
            files_removed=0,
            files_modified=0,
            chunks_added=chunks_added,
            chunks_removed=0,
            time_taken=time.time() - start_time,
            success=True,
            bm25_resynced=bm25_resynced,
            bm25_resync_count=bm25_resync_count,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _inject_pyan_edges(self, project_path: str) -> None:
        """Inject cross-module call edges produced by pyan3 into the code graph.

        This runs *after* :meth:`add_embeddings` (so graph nodes are already
        populated) and *before* :meth:`save_indices` (so the injected edges
        are persisted).

        The method is a no-op (with a warning) if the graph or metadata store
        is unavailable.  A crash inside pyan3 is caught and logged as a
        warning so it never aborts the full index.

        Args:
            project_path: Absolute path to the project root (passed through
                from :meth:`run`).
        """
        # Resolve graph storage.
        graph_integration = getattr(self._indexer, "_graph", None)
        if graph_integration is None:
            logger.warning(
                "[PYAN] Graph integration not available — skipping edge injection"
            )
            return
        storage = getattr(graph_integration, "storage", None)
        if storage is None:
            logger.warning(
                "[PYAN] Graph storage not available — skipping edge injection"
            )
            return

        # Resolve metadata store.
        dense_index = getattr(self._indexer, "dense_index", None)
        meta_store = (
            getattr(dense_index, "metadata_store", None) if dense_index else None
        )
        if meta_store is None:
            logger.warning(
                "[PYAN] Metadata store not available — skipping edge injection"
            )
            return

        try:
            # Build raw-id line map (normalize=False → ids match graph node keys).
            raw_line_map = build_line_to_chunk_map(meta_store, normalize=False)

            # Run pyan3 analysis.
            edges = build_call_edges(Path(project_path).resolve(), raw_line_map, logger)

            # Inject edges whose both endpoints are already in the graph.
            g = storage.graph
            injected = 0
            skipped = 0
            for caller_id, callee_id, line_num, is_method in edges:
                if (
                    caller_id in g
                    and callee_id in g
                    and not g.has_edge(caller_id, callee_id)
                ):
                    storage.add_call_edge(
                        caller_id,
                        callee_name=callee_id,
                        line_number=line_num,
                        is_method_call=is_method,
                        is_resolved=True,
                        source="pyan",
                    )
                    injected += 1
                else:
                    skipped += 1

            logger.info(
                "[PYAN] Injected %d cross-module call edges (%d skipped — "
                "node not in graph or edge already present)",
                injected,
                skipped,
            )

        except Exception:
            logger.warning(
                "[PYAN] Edge injection failed (non-fatal):\n%s",
                traceback.format_exc(),
            )
