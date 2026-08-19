"""Pipeline stage: embed chunks, write index, save snapshot, sync BM25, clear GPU."""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from chunking.python_ast_chunker import CodeChunk
from embeddings.chunk_cache import ChunkEmbeddingCache, resolve_chunk_cache
from merkle.merkle_dag import MerkleDAG
from merkle.snapshot_manager import SnapshotManager

from .call_edge_injection import InjectionStats, inject_call_edges
from .config import get_search_config
from .indexer import CodeIndexManager as Indexer


if TYPE_CHECKING:
    from chunking.repo_profiler import RepoProfile


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
    call_edges_injected: int = 0
    call_edge_resolvers: tuple[str, ...] = ()
    # Pass-1 auto-tuning probe summary (ADR-0014). Attached by _full_index
    # after the write stage returns; always None on incremental passes.
    probe_summary: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Uses dataclasses.asdict so a new field is never silently omitted here
        (the previous hand-listed version required updating this method too).
        """
        return asdict(self)


class IndexWriteStage:
    """Pipeline stage that embeds chunks, writes the FAISS index, saves the snapshot, syncs BM25, and clears GPU cache."""

    def __init__(
        self,
        embedder: Any,
        indexer: Indexer,
        snapshot_manager: SnapshotManager,
        build_metadata_fn: Callable[..., dict[str, Any]],
        clear_gpu_fn: Callable[[str], None],
    ) -> None:
        self._embedder = embedder
        self._indexer = indexer
        self._snapshot_manager = snapshot_manager
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
        repo_profile: RepoProfile | None,
        project_path: str = "",
    ) -> IncrementalIndexResult:
        """Embed, index, snapshot, BM25-sync, and GPU-clear for a full index pass.

        Args:
            all_chunks: Final chunk list after summary injection.
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
                all_embedding_results = self.embed_and_attach_metadata(
                    all_chunks, project_name
                )
                logger.info(
                    f"Successfully embedded {len(all_embedding_results)} chunks"
                )
            except Exception as e:  # noqa: BLE001 - api-boundary: embedding failure converted to structured error result
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

        # Inject cross-module call edges from the resolver pipeline.
        # Must run after add_embeddings (graph populated) and before
        # save_indices (graph persisted).
        injection_stats = InjectionStats()
        if project_path:
            injection_stats = self._inject_call_edges(project_path)

        return self.finalize(
            dag=dag,
            project_name=project_name,
            all_files=all_files,
            supported_files=supported_files,
            total_chunks=chunks_added,
            is_full=True,
            repo_profile=repo_profile,
            start_time=start_time,
            log_prefix="FULL_INDEX",
            files_added=len(supported_files),
            files_removed=0,
            files_modified=0,
            chunks_added=chunks_added,
            chunks_removed=0,
            call_edges_injected=injection_stats.injected,
            call_edge_resolvers=injection_stats.resolvers_run,
        )

    def finalize(
        self,
        *,
        dag: MerkleDAG,
        project_name: str,
        all_files: list[Any],
        supported_files: list[Any],
        total_chunks: int,
        is_full: bool,
        repo_profile: RepoProfile | None,
        start_time: float,
        log_prefix: str,
        files_added: int,
        files_removed: int,
        files_modified: int,
        chunks_added: int,
        chunks_removed: int,
        call_edges_injected: int = 0,
        call_edge_resolvers: tuple[str, ...] = (),
        metadata_changes: dict[str, int] | None = None,
    ) -> IncrementalIndexResult:
        """Save snapshot + index, resync BM25, clear GPU, and build the result.

        Shared tail of the full-index path (:meth:`run`) and the incremental
        path (``IncrementalIndexer.incremental_index``) — the part of an
        index pass that always runs once chunks are already embedded/added
        (or removed) and just needs to be persisted. ``call_edges_injected``/
        ``call_edge_resolvers`` default to 0/() since only :meth:`run`
        performs injection today.
        """
        metadata = self._build_metadata(
            project_name=project_name,
            all_files=all_files,
            supported_files=supported_files,
            total_chunks=total_chunks,
            is_full=is_full,
            repo_profile=repo_profile,
            **(metadata_changes or {}),
        )
        self._snapshot_manager.save_snapshot(dag, metadata)

        logger.info(f"[{log_prefix}] Saving index...")
        self._indexer.save_indices()
        logger.info(f"[{log_prefix}] Index saved")

        bm25_resynced, bm25_resync_count = self._indexer.resync_if_desynced(log_prefix)

        self._clear_gpu(log_prefix)

        return IncrementalIndexResult(
            files_added=files_added,
            files_removed=files_removed,
            files_modified=files_modified,
            chunks_added=chunks_added,
            chunks_removed=chunks_removed,
            time_taken=time.time() - start_time,
            success=True,
            bm25_resynced=bm25_resynced,
            bm25_resync_count=bm25_resync_count,
            call_edges_injected=call_edges_injected,
            call_edge_resolvers=call_edge_resolvers,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def embed_and_attach_metadata(
        self,
        chunks: list[CodeChunk],
        project_name: str,
        *,
        cache_full_pass: bool = True,
    ) -> list[Any]:
        """Batch-embed chunks and attach project_name/content to each result's metadata.

        Shared by the full-index path (via :meth:`run`) and the incremental
        path (``IncrementalIndexer._add_new_chunks``). Raises on embedding
        failure rather than catching it — :meth:`run` wraps this call in its
        own try/except to produce a structured failure result; the
        incremental path deliberately lets the exception propagate so its
        caller's except routes to ``_attempt_recovery`` instead.
        """
        embedding_results = self._embedder.embed_chunks(
            chunks,
            cache=self._resolve_chunk_cache(),
            cache_full_pass=cache_full_pass,
        )
        # strict=True: embed_chunks guarantees a 1:1, order-preserved result
        # per input chunk (see embedder.py's un-permute step). A length
        # mismatch here would otherwise silently attach the wrong chunk's
        # source text to a vector's metadata — better to fail loudly than
        # corrupt metadata across an entire index pass.
        for chunk, embedding_result in zip(chunks, embedding_results, strict=True):
            embedding_result.metadata["project_name"] = project_name
            embedding_result.metadata["content"] = chunk.content
        return embedding_results

    def _resolve_chunk_cache(self) -> ChunkEmbeddingCache | None:
        """Resolve this run's persistent chunk-embedding cache, if enabled.

        Resolved lazily here — inside :meth:`run`, never at ``__init__`` —
        for two reasons. First, ``IndexWriteStage`` is rebuilt in
        ``incremental_indexer.py``'s ``_build_write_pipeline`` after
        ``_release_and_verify_resources()``, so a cache captured at
        construction time could outlive that rebind stale; resolving per-run
        sidesteps that. Second, several existing tests construct
        ``IndexWriteStage(indexer=Mock(), ...)``, so eagerly building a
        ``Path`` from ``storage_dir`` at construction time would raise on a
        ``Mock``.

        Thin wrapper over ``embeddings.chunk_cache.resolve_chunk_cache`` —
        shared with the incremental embed site so both resolve a cache the
        same fail-soft way.
        """
        return resolve_chunk_cache(self._indexer.storage_dir, self._embedder)

    def _inject_call_edges(self, project_path: str) -> InjectionStats:
        """Resolve this run's collaborators and delegate to ``inject_call_edges``.

        Runs *after* :meth:`add_embeddings` (graph nodes already populated) and
        *before* :meth:`save_indices` (edges persisted). A no-op (with a
        warning, and an ``InjectionStats.error`` set) if the graph or metadata
        store is unavailable — the resolver pipeline itself lives in
        ``search.call_edge_injection`` and is pure with respect to this class.

        Args:
            project_path: Absolute path to the project root (passed through from
                :meth:`run`).
        """
        # Resolve graph storage.
        graph_integration = getattr(self._indexer, "_graph", None)
        if graph_integration is None:
            logger.warning(
                "[CALL_EDGES] Graph integration not available — skipping edge injection"
            )
            return InjectionStats(error="graph integration not available")
        storage = getattr(graph_integration, "storage", None)
        if storage is None:
            logger.warning(
                "[CALL_EDGES] Graph storage not available — skipping edge injection"
            )
            return InjectionStats(error="graph storage not available")

        # Resolve metadata store.
        dense_index = getattr(self._indexer, "dense_index", None)
        meta_store = (
            getattr(dense_index, "metadata_store", None) if dense_index else None
        )
        if meta_store is None:
            logger.warning(
                "[CALL_EDGES] Metadata store not available — skipping edge injection"
            )
            return InjectionStats(error="metadata store not available")

        cg_cfg = getattr(get_search_config(), "call_graph", None)
        return inject_call_edges(storage, meta_store, project_path, cg_cfg)
