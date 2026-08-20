"""Incremental indexing using Merkle tree change detection."""

from __future__ import annotations

import gc
import logging
import os
import tempfile
import time
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from chunking.repo_profiler import RepoProfile

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder
from merkle.change_detector import ChangeDetector, FileChanges
from merkle.merkle_dag import MerkleDAG
from merkle.snapshot_manager import SnapshotManager
from utils.observability import traced_block
from utils.otel_attributes import (
    ATTR_INDEX_TYPE,
    ATTR_PROJECT_ID,
)
from utils.timing import timed

from .config import get_active_project_storage_dir, get_search_config
from .index_write_stage import IncrementalIndexResult, IndexWriteStage
from .indexer import CodeIndexManager as Indexer
from .parallel_chunker import ParallelChunker
from .summary_stage import SummaryStage


logger = logging.getLogger(__name__)

# Minimum GPU memory (MB) considered "still allocated" after cleanup.
# Below this threshold, residual allocations are expected (PyTorch runtime overhead ~50MB).
GPU_CLEANUP_THRESHOLD_MB = 100


class IncrementalIndexer:
    """Handles incremental indexing of code changes."""

    def __init__(
        self,
        indexer: Indexer | None = None,
        embedder: CodeEmbedder | None = None,
        chunker: MultiLanguageChunker | None = None,
        snapshot_manager: SnapshotManager | None = None,
        include_dirs: list | None = None,
        exclude_dirs: list | None = None,
        *,
        include_exclusive: bool = False,
    ):
        """Initialize incremental indexer.

        Args:
            indexer: Indexer instance
            embedder: Embedder instance
            chunker: Code chunker instance
            snapshot_manager: Snapshot manager instance
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
            include_exclusive: When True, every include_dirs pattern is treated
                as narrowing (whitelist-only), even ones that reach into a
                dependency tree (venv, site-packages, node_modules, ...) — the
                escape hatch back to the pre-additive behaviour. Forwarded to
                the chunker, the change detector, and every MerkleDAG built
                during a full or incremental pass.
        """
        self.include_exclusive = include_exclusive
        if indexer is None:
            # Create indexer with temporary storage directory for testing
            temp_dir = tempfile.mkdtemp(prefix="incremental_index_")
            self.indexer = Indexer(temp_dir)
        else:
            self.indexer = indexer
        self.embedder = embedder or CodeEmbedder()

        # Load configuration for chunker initialization
        config = get_search_config()

        # Initialize chunker with directory filters and entity tracking config
        self.chunker = chunker or MultiLanguageChunker(
            include_dirs=include_dirs,
            exclude_dirs=exclude_dirs,
            enable_entity_tracking=config.performance.enable_entity_tracking,
            include_exclusive=include_exclusive,
        )
        self.snapshot_manager = snapshot_manager or SnapshotManager()

        # Store directory filters for MerkleDAG creation
        self.include_dirs = include_dirs
        self.exclude_dirs = exclude_dirs

        # Cache supported extensions once — used by both full reindex and change
        # detection to skip content-hashing non-code assets (~95% I/O reduction
        # on asset-heavy projects). Must be stable across passes so the hash
        # scheme of a stored snapshot matches any DAG we rebuild from it.
        from chunking.tree_sitter import TreeSitterChunker

        self.supported_extensions: set[str] = set(
            TreeSitterChunker.get_supported_extensions()
        )

        # Create change detector with filters + extension-aware hashing
        self.change_detector = ChangeDetector(
            self.snapshot_manager,
            include_dirs,
            exclude_dirs,
            supported_extensions=self.supported_extensions,
            include_exclusive=include_exclusive,
        )

        # Load parallel chunking configuration
        self.enable_parallel_chunking = config.performance.enable_parallel_chunking
        self.max_chunking_workers = config.performance.max_chunking_workers

        # Initialize helper modules
        self._parallel_chunker = ParallelChunker(
            chunker=self.chunker,
            enable_parallel=self.enable_parallel_chunking,
            max_workers=self.max_chunking_workers,
        )
        self._summary_stage = SummaryStage()
        self._build_write_pipeline()
        self.repo_profile: RepoProfile | None = None  # Set during _full_index
        # Set from the active MerkleDAG's own path_filter in _full_index /
        # incremental_index, so per-file gates below reuse the SAME
        # precedence resolver (and hit-count diagnostics) the tree walk that
        # produced the file list already used — see _get_path_filter().
        self._path_filter = None

    def _build_write_pipeline(self) -> None:
        """(Re)build the resource-bound write pipeline.

        Call from __init__ and again immediately after _release_and_verify_resources()
        so IndexWriteStage is always bound to the current self.embedder /
        self.indexer — never to released objects.
        """
        self._index_write_stage = IndexWriteStage(
            embedder=self.embedder,
            indexer=self.indexer,
            snapshot_manager=self.snapshot_manager,
            build_metadata_fn=self._build_snapshot_metadata,
            clear_gpu_fn=self._clear_gpu_cache,
        )

    def _chunk_files_parallel(
        self, project_path: str, file_paths: list[str]
    ) -> list[CodeChunk]:
        """Chunk files in parallel or sequentially based on configuration.

        Args:
            project_path: Root project path
            file_paths: List of relative file paths to chunk

        Returns:
            List of CodeChunk objects from all files
        """
        return self._parallel_chunker.chunk_files(project_path, file_paths)

    def detect_changes(self, project_path: str) -> tuple[FileChanges, MerkleDAG]:
        """Detect changes in project since last snapshot.

        Args:
            project_path: Path to project

        Returns:
            Tuple of (FileChanges, current MerkleDAG)
        """
        return self.change_detector.detect_changes_from_snapshot(project_path)

    def _get_path_filter(self, project_path: str):
        """Return the active PathFilter for this indexing run.

        Prefers the PathFilter already built (and hit-counted) by the
        MerkleDAG walk that produced the current file list — see the
        `self._path_filter = dag.path_filter` assignments in _full_index and
        incremental_index. Falls back to building one directly from
        self.include_dirs/self.exclude_dirs when no DAG-derived filter has
        been set yet (e.g. a direct/unit-test call to _is_supported_file).
        """
        if self._path_filter is None:
            from search.filters import PathFilter

            self._path_filter = PathFilter(
                self.include_dirs,
                self.exclude_dirs,
                project_path,
                include_exclusive=self.include_exclusive,
            )
        return self._path_filter

    def _is_supported_file(self, project_path: str, file_path: str) -> bool:
        """Check if file is supported for indexing.

        Args:
            project_path: Root project path
            file_path: Relative file path

        Returns:
            True if file is supported and passes the include/exclude/default
            precedence resolver (PathFilter) — including any include_dirs
            override of a default-ignored directory (e.g. "venv",
            "site-packages").
        """
        full_path = Path(project_path) / file_path

        # Check if file extension is supported
        if not self.chunker.is_supported(str(full_path)):
            return False

        return self._get_path_filter(project_path).should_index_file(file_path)

    def incremental_index(
        self,
        project_path: str,
        project_name: str | None = None,
        force_full: bool = False,
    ) -> IncrementalIndexResult:
        """Perform incremental indexing of a project.

        Args:
            project_path: Path to project
            project_name: Optional project name
            force_full: Force full reindex even if snapshot exists

        Returns:
            IncrementalIndexResult with statistics
        """
        start_time = time.time()
        project_path = str(Path(project_path).resolve())

        if project_name is None:
            project_name = Path(project_path).name

        try:
            # Check if we should do full index
            if force_full or not self.snapshot_manager.has_snapshot(project_path):
                logger.info(f"Performing full index for {project_name}")

                # Free VRAM before full reindex to speed up indexing and prevent memory pressure
                if force_full:
                    logger.info("Freeing VRAM before force_full reindex...")
                else:
                    logger.info("Freeing VRAM before initial indexing...")
                try:
                    self.embedder.cleanup()
                    logger.info("VRAM cleanup completed successfully")
                except Exception as e:  # noqa: BLE001 - resilience: VRAM cleanup best-effort, indexing continues
                    logger.warning(
                        f"VRAM cleanup failed (continuing with index): {e}",
                        exc_info=True,
                    )

                with traced_block(
                    "index.full",
                    **{ATTR_PROJECT_ID: project_name, ATTR_INDEX_TYPE: "full"},
                ):
                    return self._full_index(project_path, project_name, start_time)

            # Detect changes
            logger.info(f"Detecting changes in {project_name}")
            changes, current_dag = self.detect_changes(project_path)
            # Reuse the DAG's own PathFilter (already recovered from the
            # snapshot's include/exclude dirs if this call's own values were
            # None) so _is_supported_file/_add_new_chunks apply the exact
            # same precedence resolver the change-detection walk just used.
            self._path_filter = current_dag.path_filter

            if not changes.has_changes():
                logger.info(f"No changes detected in {project_name}")
                # Even with no changes, save current statistics
                all_files = list(current_dag.get_all_files())
                supported_files = self._get_supported_files(project_path, all_files)
                total_chunks = self._get_total_chunks()

                metadata = self._build_snapshot_metadata(
                    project_name=project_name,
                    all_files=all_files,
                    supported_files=supported_files,
                    total_chunks=total_chunks,
                    is_full=False,
                )
                self.snapshot_manager.save_snapshot(current_dag, metadata)

                return self._zero_result(start_time, success=True)

            # Log changes
            logger.info(
                f"Changes detected - Added: {len(changes.added)}, "
                f"Removed: {len(changes.removed)}, Modified: {len(changes.modified)}"
            )

            # Process changes
            chunks_removed = self._remove_old_chunks(changes, project_name)

            # Load cached repo profile for adaptive chunk sizing (set by previous full index)
            self._restore_repo_profile(project_path)

            chunks_added = self._add_new_chunks(changes, project_path, project_name)

            # Validate index consistency after operations
            _consistency_target = self._consistency_target()
            if _consistency_target is not None:
                logger.info("[INCREMENTAL] Validating index consistency...")
                is_valid, issues = _consistency_target.validate_index_consistency()
                if not is_valid:
                    logger.error(
                        f"[INCREMENTAL] Index validation failed with {len(issues)} issues. "
                        "Triggering full re-index to recover."
                    )
                    return self._attempt_recovery(
                        f"Index validation failed after batch removal ({len(issues)} issues)",
                        project_path,
                        project_name,
                        start_time,
                    )

            # Re-inject resolver call edges (pyan/LibCST/LSP). Opt-in only —
            # the write stage owns the inject_on_incremental gate and
            # returns all-zero stats when it is off (ADR-0044).
            injection_stats = self._index_write_stage.inject_call_edges_if_enabled(
                project_path
            )

            # Update snapshot, index, BM25 sync, and GPU cache; build the result.
            # After processing changes, calculate cumulative stats.
            all_files = list(current_dag.get_all_files())
            supported_files = self._get_supported_files(project_path, all_files)
            total_chunks = self._get_total_chunks()

            return self._index_write_stage.finalize(
                dag=current_dag,
                project_name=project_name,
                all_files=all_files,
                supported_files=supported_files,
                total_chunks=total_chunks,
                is_full=False,
                repo_profile=None,
                start_time=start_time,
                log_prefix="INCREMENTAL",
                files_added=len(changes.added),
                files_removed=len(changes.removed),
                files_modified=len(changes.modified),
                chunks_added=chunks_added,
                chunks_removed=chunks_removed,
                call_edges_injected=injection_stats.injected,
                call_edge_resolvers=injection_stats.resolvers_run,
                metadata_changes={
                    "files_added": len(changes.added),
                    "files_removed": len(changes.removed),
                    "files_modified": len(changes.modified),
                },
            )

        except Exception as e:  # noqa: BLE001 - api-boundary: top-level indexing op converts failure to structured result
            logger.error(f"Incremental indexing failed: {e}")
            logger.error(traceback.format_exc())

            return self._attempt_recovery(
                f"Incremental indexing failed: {e}",
                project_path,
                project_name,
                start_time,
            )

    @staticmethod
    def _zero_result(
        start_time: float,
        *,
        success: bool,
        error: str | None = None,
    ) -> IncrementalIndexResult:
        """Return an all-zeros IncrementalIndexResult (no file changes, no chunks moved).

        Used for: no-changes detected (success=True), auto-reindex skipped (success=True),
        full-index failure (success=False), and recovery failure (success=False, error=...).
        ``time_taken`` is computed from ``start_time`` at the moment of the call.
        """
        return IncrementalIndexResult(
            files_added=0,
            files_removed=0,
            files_modified=0,
            chunks_added=0,
            chunks_removed=0,
            time_taken=time.time() - start_time,
            success=success,
            error=error,
            bm25_resynced=False,
            bm25_resync_count=0,
        )

    def _restore_repo_profile(self, project_path: str) -> None:
        """Restore the cached repo profile for adaptive chunk sizing.

        If the stored snapshot contains a ``repo_profile`` dict and the current chunking
        config uses ``sizing_mode == "adaptive"``, reconstruct the ``RepoProfile`` object
        and inject it into the parallel chunker so incremental updates use the same size
        calibration as the original full index.  No-ops silently when the profile is
        absent or adaptive sizing is disabled.
        """
        from chunking.repo_profiler import RepoProfile

        _incr_config = get_search_config()
        if _incr_config.chunking.sizing_mode != "adaptive":
            return
        _cached_meta = self.snapshot_manager.load_metadata(project_path)
        if not isinstance(_cached_meta, dict) or "repo_profile" not in _cached_meta:
            return
        _rp = _cached_meta["repo_profile"]
        _cached_profile = RepoProfile(
            function_count=_rp.get("function_count", 0),
            p25_chars=_rp.get("p25_chars", 0),
            p50_chars=_rp.get("p50_chars", 0),
            p75_chars=_rp.get("p75_chars", 0),
            p90_chars=_rp.get("p90_chars", 0),
            mean_chars=_rp.get("mean_chars", 0),
            max_complexity=_rp.get("max_complexity", 0),
        )
        self._parallel_chunker.chunker.tree_sitter_chunker.repo_profile = (
            _cached_profile
        )
        logger.info(
            f"[REPO_PROFILE] Loaded cached profile for incremental update: "
            f"P75={_cached_profile.p75_chars} chars, "
            f"max_cc={_cached_profile.max_complexity}"
        )

    def _consistency_target(self) -> Any:
        """Resolve the object that owns metadata_store + chunk_ids.

        self.indexer is a HybridSearcher in production (see
        mcp_server/tools/index_handlers.py's "indexer: HybridSearcher or
        CodeIndexManager" docstring) but a bare CodeIndexManager under most
        tests; only CodeIndexManager defines validate_index_consistency, so
        calling it unconditionally is dead code on the real path. Reuses the
        dense_index accessor idiom already used for the same purpose in
        index_write_stage.py's inject_call_edges.
        """
        if hasattr(self.indexer, "validate_index_consistency"):
            return self.indexer
        return getattr(self.indexer, "dense_index", None)

    _RECOVERY_MARKER_NAME = "index_recovery_failed.marker"

    def _recovery_marker_path(self) -> Path | None:
        """Resolve the recovery-marker path in the index storage directory.

        IncrementalIndexer is constructed fresh per MCP request
        (search_handlers.py, index_handlers.py), so a retry counter kept on
        ``self`` resets every call and can never bound anything — a marker
        file on disk is what actually survives across the request boundary
        that previously produced 62 consecutive recovery attempts.

        Reuses ``_consistency_target`` to resolve to a CodeIndexManager
        regardless of whether ``self.indexer`` is a HybridSearcher
        (production) or a bare CodeIndexManager (most tests).
        """
        target = self._consistency_target()
        storage_dir = getattr(target, "storage_dir", None)
        if not isinstance(storage_dir, (str, os.PathLike)):
            # None (no target resolved) or an unconfigured test double
            # (e.g. a bare Mock() with no storage_dir set) — either way
            # there is no real directory to write a marker into.
            return None
        return Path(storage_dir) / self._RECOVERY_MARKER_NAME

    def _attempt_recovery(
        self,
        original_error: str,
        project_path: str,
        project_name: str,
        start_time: float,
    ) -> IncrementalIndexResult:
        """Attempt recovery via full re-index after failure.

        Bounded by a marker file (see ``_recovery_marker_path``): if a prior
        recovery attempt already failed, this returns an error immediately
        instead of retrying clear_index()/full-index again, since the
        underlying cause (e.g. a held file handle) will not have changed on
        its own.

        Args:
            original_error: Description of the original failure
            project_path: Path to the project
            project_name: Name of the project
            start_time: Start time for duration calculation

        Returns:
            IncrementalIndexResult from recovery attempt or error result
        """
        marker_path = self._recovery_marker_path()
        if marker_path is not None and marker_path.exists():
            error = (
                f"Recovery already failed previously ({marker_path.name} "
                "present) and was not retried automatically. Call "
                "cleanup_resources to release any held file handles, then "
                "retry indexing; a successful recovery removes the marker."
            )
            logger.error(error)
            return self._zero_result(start_time, success=False, error=error)

        logger.warning(f"Attempting recovery via full re-index: {original_error}")
        try:
            self.indexer.clear_index()
            result = self._full_index(project_path, project_name, start_time)
        except Exception as recovery_error:  # noqa: BLE001 - api-boundary: recovery failure converted to structured error result
            logger.error(f"Recovery failed: {recovery_error}")
            logger.error(traceback.format_exc())
            if marker_path is not None:
                try:
                    marker_path.parent.mkdir(parents=True, exist_ok=True)
                    marker_path.write_text(
                        f"Original: {original_error}\nRecovery: {recovery_error}\n"
                        f"Timestamp: {time.time()}\n",
                        encoding="utf-8",
                    )
                except OSError as marker_error:  # noqa: BLE001 - best-effort: marker write failure must not mask the real error below
                    logger.warning(f"Could not write recovery marker: {marker_error}")
            return self._zero_result(
                start_time,
                success=False,
                error=(
                    f"Original: {original_error}, Recovery: {recovery_error}. "
                    "Call cleanup_resources to release held file handles "
                    "before retrying."
                ),
            )
        else:
            if marker_path is not None and marker_path.exists():
                try:
                    marker_path.unlink()
                except OSError as marker_error:  # noqa: BLE001 - best-effort: stale marker cleanup, not fatal to a successful recovery
                    logger.warning(
                        f"Recovery succeeded but could not clear stale marker: {marker_error}"
                    )
            return result

    def _release_and_verify_resources(self, project_path: str) -> None:
        """Mandatory resource release and verification before full reindex.

        Ensures all previous resources (index managers, searchers, embedders, GPU memory)
        are properly released before starting a full reindex operation. This prevents
        VRAM/memory pressure that could cause reindexing to fail.

        Performs:
        1. Save current model key before cleanup
        2. Release via ResourceManager.cleanup_previous_resources() (same as UI command)
        3. Verification of cleanup completeness
        4. Refresh embedder with fresh instance (preserving model key)
        5. Refresh indexer/searcher (required since cleanup shut it down)

        Args:
            project_path: Path to the project being indexed (needed to recreate searcher)

        This method is idempotent - safe to call even if cleanup was already performed.
        """
        logger.info("[FULL_INDEX] Mandatory pre-reindex resource release starting...")

        # Step 1: Release resources (same operation as UI "Release Resources" command)
        from mcp_server.resource_manager import _cleanup_previous_resources

        _cleanup_previous_resources()
        logger.info("[FULL_INDEX] Resource release completed")

        # Step 2: Verify cleanup completeness
        from mcp_server.services import get_state

        state = get_state()
        verification_passed = True
        warnings = []

        # Check embedder pool cleared
        if state.embedders:
            warnings.append(
                f"Embedder pool not fully cleared: {list(state.embedders.keys())}"
            )
            verification_passed = False

        # Check index_manager released
        if state.index_manager is not None:
            warnings.append("state.index_manager not None after cleanup")
            verification_passed = False

        # Check searcher released
        if state.searcher is not None:
            warnings.append("state.searcher not None after cleanup")
            verification_passed = False

        # Check GPU memory (if CUDA available)
        try:
            import torch

            if torch.cuda.is_available():
                allocated_mb = torch.cuda.memory_allocated() / (1024**2)
                if allocated_mb > GPU_CLEANUP_THRESHOLD_MB:
                    warnings.append(
                        f"GPU memory still allocated: {allocated_mb:.1f} MB"
                    )
                    verification_passed = False
        except ImportError:
            pass

        # If verification failed, attempt secondary cleanup and re-verify
        if not verification_passed:
            logger.warning(
                f"[FULL_INDEX] Initial verification failed: {warnings}. "
                "Attempting secondary cleanup..."
            )
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            # Re-verify
            state = get_state()
            recheck_warnings = []
            if state.embedders:
                recheck_warnings.append(
                    f"Embedder pool still not cleared: {list(state.embedders.keys())}"
                )
            if state.index_manager is not None:
                recheck_warnings.append("state.index_manager still not None")
            if state.searcher is not None:
                recheck_warnings.append("state.searcher still not None")

            if recheck_warnings:
                logger.warning(
                    f"[FULL_INDEX] Re-verification still shows issues: {recheck_warnings}. "
                    "Proceeding with reindex anyway."
                )
            else:
                logger.info(
                    "[FULL_INDEX] Secondary cleanup successful - verification passed"
                )
        else:
            logger.info(
                "[FULL_INDEX] Resource verification passed — all resources released"
            )

        # Step 3: Refresh embedder (required since cleanup cleared it)
        from mcp_server.model_pool_manager import get_embedder

        self.embedder = get_embedder()  # Fresh instance with config model
        logger.info("[FULL_INDEX] Fresh embedder acquired for reindex")

        # Step 4: Refresh indexer/searcher (required since cleanup shut it down)
        # Only refresh if the indexer was actually shut down (has _is_shutdown flag set to True)
        if hasattr(self.indexer, "_is_shutdown") and self.indexer._is_shutdown:
            from mcp_server.search_factory import get_searcher

            # load_existing=False (#reindex-log-audit-2026-07-30): this searcher
            # is a write-only target for the force-full reindex about to run —
            # _full_index() calls clear_index()/clear_hybrid_indices() on it
            # moments later, so loading the stale on-disk BM25 index here would
            # only cost time and log spurious version/tokenizer mismatch
            # warnings for data that is about to be discarded.
            # pyrefly: ignore [bad-assignment]
            self.indexer = get_searcher(project_path, load_existing=False)
            logger.info("[FULL_INDEX] Fresh indexer/searcher acquired for reindex")
        else:
            logger.debug(
                "[FULL_INDEX] Indexer not shut down or doesn't need refresh (test mock)"
            )

    def _full_index(
        self, project_path: str, project_name: str, start_time: float
    ) -> IncrementalIndexResult:
        """Perform full indexing of a project.

        Args:
            project_path: Path to project
            project_name: Project name
            start_time: Start time for timing

        Returns:
            IncrementalIndexResult
        """
        try:
            # === MANDATORY: Release resources before full reindex ===
            self._release_and_verify_resources(project_path)
            # Rebind write pipeline to freshly acquired embedder/indexer so the
            # stage never runs against the released (stale) objects.
            self._build_write_pipeline()
            # Defense in depth: Load filters from snapshot before deleting it
            # This handles cases where filters weren't passed during IncrementalIndexer creation
            if self.include_dirs is None or self.exclude_dirs is None:
                old_snapshot = self.snapshot_manager.load_snapshot(project_path)
                if old_snapshot and old_snapshot.directory_filter:
                    if (
                        self.include_dirs is None
                        and old_snapshot.directory_filter.include_dirs
                    ):
                        self.include_dirs = old_snapshot.directory_filter.include_dirs
                        logger.info(
                            f"[FULL_INDEX] Recovered include_dirs from snapshot: {self.include_dirs}"
                        )
                        # include_exclusive only means something alongside
                        # include_dirs, so recover it under the same condition.
                        if old_snapshot.path_filter:
                            self.include_exclusive = (
                                old_snapshot.path_filter.include_exclusive
                            )
                            logger.info(
                                f"[FULL_INDEX] Recovered include_exclusive from snapshot: {self.include_exclusive}"
                            )
                    if (
                        self.exclude_dirs is None
                        and old_snapshot.directory_filter.exclude_dirs
                    ):
                        self.exclude_dirs = old_snapshot.directory_filter.exclude_dirs
                        logger.info(
                            f"[FULL_INDEX] Recovered exclude_dirs from snapshot: {self.exclude_dirs}"
                        )

            # Build DAG for all files. Done BEFORE deleting the old snapshot /
            # clearing the existing index (below) so a bad filter set (e.g. an
            # include_dirs typo that matches nothing) can be caught and
            # reported without first destroying a good, existing index.
            dag = MerkleDAG(
                project_path,
                self.include_dirs,
                self.exclude_dirs,
                supported_extensions=self.supported_extensions,
                include_exclusive=self.include_exclusive,
            )
            dag.build()
            all_files = dag.get_all_files()
            # Reuse the DAG's own PathFilter (already carrying per-pattern
            # hit-count diagnostics from the walk that just produced
            # all_files) for the extension-only re-check below.
            self._path_filter = dag.path_filter

            # Filter supported files
            supported_files = self._get_supported_files(project_path, all_files)
            logger.info(
                f"Found {len(supported_files)} supported files out of {len(all_files)} total files"
            )

            # Per-pattern diagnostics: a pattern that matched nothing is the
            # exact silent-failure class this whole filtering system exists to
            # catch (e.g. a typo'd or absent package name under
            # site-packages) — surface it loudly instead of quietly indexing
            # whatever ancestor files happened to survive.
            for unmatched in self._path_filter.unmatched_patterns():
                logger.warning(
                    f"[FULL_INDEX] Directory filter pattern matched 0 files/dirs: {unmatched!r}"
                )
            if self._path_filter.all_includes_unmatched():
                error = (
                    f"All include_dirs patterns matched 0 files: {self.include_dirs}. "
                    "Aborting before touching the existing index/snapshot — nothing "
                    "would be indexed. Check for typos or absent directories."
                )
                logger.error(f"[FULL_INDEX] {error}")
                return self._zero_result(start_time, success=False, error=error)

            # Backstop for the residual failure mode Part 1's additive-by-default
            # classification can't catch: a *narrowing* include pattern (or the
            # include_exclusive escape hatch, which forces every pattern back to
            # narrowing) that happens to resolve entirely inside a dependency
            # tree, silently wiping first-party source the same way the
            # original incident did. Checked here — before delete_snapshot/
            # clear_index below — so a bad filter is caught without first
            # destroying a good, existing index.
            if self._path_filter.only_dependency_paths_matched(supported_files):
                segments = self._path_filter.dependency_segments(supported_files)
                error = (
                    f"Every matched file lies inside a dependency tree "
                    f"{segments} — include_dirs={self.include_dirs} narrowed "
                    "the whole project down to library code only, with no "
                    "first-party source surviving."
                )
                if self.include_exclusive:
                    logger.warning(
                        f"[FULL_INDEX] {error} include_exclusive=True was passed "
                        "deliberately, so proceeding — this index will contain "
                        "dependency code only."
                    )
                else:
                    error += (
                        " Aborting before touching the existing index/snapshot. "
                        "If a dependency-only index is intentional, pass "
                        "include_exclusive=True to acknowledge and proceed."
                    )
                    logger.error(f"[FULL_INDEX] {error}")
                    return self._zero_result(start_time, success=False, error=error)

            # Delete old Merkle snapshot for current model only (preserves other models)
            logger.info(
                f"[FULL_INDEX] Deleting old snapshot for current model: {project_name}"
            )
            self.snapshot_manager.delete_snapshot(project_path)
            logger.info("[FULL_INDEX] Deleted old snapshot for current model")

            # Clear existing index
            self.indexer.clear_index()

            # ========== Repository Profiling (Adaptive Sizing) ==========
            repo_profile = None
            _profile_config = get_search_config()
            if _profile_config.chunking.sizing_mode == "adaptive" and supported_files:
                from chunking.repo_profiler import profile_repository

                repo_profile = profile_repository(project_path, supported_files)
                if repo_profile:
                    logger.info(
                        f"[REPO_PROFILE] {repo_profile.function_count} functions analyzed: "
                        f"P75={repo_profile.p75_chars} chars, "
                        f"P90={repo_profile.p90_chars} chars, "
                        f"max_cc={repo_profile.max_complexity}"
                    )
                else:
                    logger.info(
                        "[REPO_PROFILE] Too few functions for profiling, using static defaults"
                    )
                self._parallel_chunker.chunker.tree_sitter_chunker.repo_profile = (
                    repo_profile
                )
            self.repo_profile = repo_profile
            # ========== END Repository Profiling ==========

            # ========== Auto-Tuning Probe: Pass 1 (ADR-0014) ==========
            # Writes <project_storage_dir>/search_overrides.json BEFORE the
            # get_search_config() call below, so this very run already sees
            # the merged overrides. Wired only here in _full_index —
            # incremental reindexes never re-probe, and an existing overrides
            # file keeps applying untouched. Storage dir comes from the
            # config layer's active-project seam (set by the MCP handlers);
            # when unset (CLI/tests), the probe is skipped entirely.
            probe_summary = None
            probe_storage = get_active_project_storage_dir()
            if probe_storage:
                try:
                    from .index_probe import probe_pre_chunking

                    probe_summary = probe_pre_chunking(
                        probe_storage,
                        supported_files,
                        repo_profile,
                        embedding_model=getattr(self.embedder, "model_name", None),
                    )
                except Exception as e:  # noqa: BLE001 - probe isolation: tuning must never break indexing
                    logger.warning(f"[INDEX_PROBE] Pass 1 failed: {e}")
            # ========== END Auto-Tuning Probe ==========

            # Collect all chunks first, then embed in a single pass for efficiency
            # Use parallel chunking for improved performance
            logger.info(
                f"Chunking files (parallel={'enabled' if self.enable_parallel_chunking else 'disabled'}, workers={self.max_chunking_workers})"
            )
            all_chunks = self._chunk_files_parallel(project_path, supported_files)

            # Zero-chunk files are now named directly by ParallelChunker's own
            # summary log (collected live during chunking, not reconciled here
            # afterwards by fragile file_path string-equality) — see
            # ParallelChunker._log_chunking_summary.
            logger.info(f"Total chunks collected: {len(all_chunks)}")

            # Stage 1: file-level module summaries (config-gated inside the stage)
            self._summary_stage.generate_and_extend(
                all_chunks,
                log_prefix="[FILE_SUMMARIES]",
                appended_noun="module summaries",
            )

            # Stage 2: embed, index, call-edge injection, snapshot, BM25, GPU
            result = self._index_write_stage.run(
                all_chunks,
                project_name,
                dag,
                all_files,
                supported_files,
                start_time,
                self.repo_profile,
                project_path=project_path,
            )
            result.probe_summary = probe_summary

            _consistency_target = self._consistency_target()
            if _consistency_target is not None:
                is_valid, issues = _consistency_target.validate_index_consistency()
                if not is_valid:
                    logger.error(
                        f"[FULL_INDEX] Index inconsistent after full index: {issues}"
                    )
                    result.success = False
                    result.error = (
                        f"Index inconsistent after full index "
                        f"({len(issues)} issues): {issues}"
                    )
            return result

        except Exception as e:
            logger.error(f"Full indexing failed: {e}", exc_info=True)
            # (#reindex-log-audit-2026-07-30) The searcher acquired above (see
            # _release_and_verify_resources) was built with load_existing=False,
            # so if this failure happened after construction but before
            # clear_hybrid_indices()/rebuild completed, state.searcher is an
            # empty write-only instance. Null it — same one-line invalidation
            # search_factory.get_searcher() already does for
            # DimensionMismatchError — so the next call rebuilds from disk
            # instead of returning an empty cached searcher.
            try:
                from mcp_server.services import get_state

                get_state().searcher = None
            except Exception:  # noqa: BLE001 - best-effort cache invalidation, never mask the original failure
                pass
            return self._zero_result(start_time, success=False, error=str(e))

    def _get_total_chunks(self) -> int:
        """Get total number of chunks currently in the index.

        Returns:
            Total chunk count from index stats or size
        """
        if hasattr(self.indexer, "get_stats"):
            stats = self.indexer.get_stats()
            return stats.get("total_chunks", 0)
        elif hasattr(self.indexer, "get_index_size"):
            return self.indexer.get_index_size()
        return 0

    def _get_supported_files(
        self, project_path: str, all_files: list[str]
    ) -> list[str]:
        """Filter files to only those supported for indexing.

        Args:
            project_path: Root project directory
            all_files: List of all file paths

        Returns:
            List of supported file paths
        """
        return [f for f in all_files if self._is_supported_file(project_path, f)]

    def _build_snapshot_metadata(
        self,
        project_name: str,
        all_files: list,
        supported_files: list,
        total_chunks: int,
        is_full: bool = False,
        repo_profile: RepoProfile | None = None,
        **changes,
    ) -> dict[str, Any]:
        """Build metadata dictionary for snapshot storage.

        Args:
            project_name: Name of the project
            all_files: List of all files in project
            supported_files: List of supported files
            total_chunks: Total number of indexed chunks
            is_full: Whether this is a full index (vs incremental)
            repo_profile: Optional RepoProfile for adaptive sizing (cached for incremental reuse)
            **changes: Optional file change counts (files_added, files_removed, files_modified, etc.)

        Returns:
            Metadata dictionary for snapshot
        """
        metadata: dict[str, Any] = {
            "project_name": project_name,
            "incremental_update": not is_full,
            "total_files": len(all_files),
            "supported_files": len(supported_files),
            "chunks_indexed": total_chunks,
        }

        # Add change statistics if provided
        metadata.update(changes)

        # Set defaults for missing change counts
        metadata.setdefault("files_added", 0)
        metadata.setdefault("files_removed", 0)
        metadata.setdefault("files_modified", 0)

        # Cache repo profile for incremental indexing reuse
        if repo_profile is not None:
            metadata["repo_profile"] = {
                "function_count": repo_profile.function_count,
                "p25_chars": repo_profile.p25_chars,
                "p50_chars": repo_profile.p50_chars,
                "p75_chars": repo_profile.p75_chars,
                "p90_chars": repo_profile.p90_chars,
                "mean_chars": repo_profile.mean_chars,
                "max_complexity": repo_profile.max_complexity,
            }

        return metadata

    def _remove_old_chunks(self, changes: FileChanges, project_name: str) -> int:
        """Remove chunks for deleted and modified files.

        Args:
            changes: File changes
            project_name: Project name

        Returns:
            Number of chunks removed
        """
        files_to_remove = self.change_detector.get_files_to_remove(changes)

        chunks_removed = 0
        if files_to_remove:
            chunks_removed = self.indexer.remove_files(
                set(files_to_remove), project_name
            )
            logger.info(
                f"Removed {chunks_removed} chunks from {len(files_to_remove)} files"
            )

        # Prune stale call-graph nodes for all removed/modified files.
        # The call graph and the metadata store are maintained independently; without
        # this step, old node IDs (which embed line ranges) survive incremental
        # reindex and cause "Chunk not found" errors in find_connections.
        # The graph is persisted later by save_indices() — no explicit save needed here.
        from graph.graph_storage import CodeGraphStorage

        graph_storage = getattr(self.indexer, "graph_storage", None)
        if isinstance(graph_storage, CodeGraphStorage) and files_to_remove:
            graph_nodes_removed = 0
            for fp in files_to_remove:
                graph_nodes_removed += graph_storage.remove_file_nodes(fp)
            if graph_nodes_removed:
                logger.info(
                    f"[GRAPH_PRUNE] Pruned {graph_nodes_removed} stale graph nodes "
                    f"across {len(files_to_remove)} files"
                )

        return chunks_removed

    @timed("index.incremental")
    def _add_new_chunks(
        self, changes: FileChanges, project_path: str, project_name: str
    ) -> int:
        """Add chunks for new and modified files.

        Args:
            changes: File changes
            project_path: Project root path
            project_name: Project name

        Returns:
            Number of chunks added
        """
        files_to_index = self.change_detector.get_files_to_reindex(changes)

        # Filter supported files through the same include/exclude/default
        # precedence resolver used by the tree walk (reused via
        # self._path_filter — set from the DAG in incremental_index/
        # _full_index; lazily built here if unset, e.g. direct calls).
        path_filter = self._get_path_filter(project_path)

        supported_files = [
            f
            for f in files_to_index
            if self.chunker.is_supported(f) and path_filter.should_index_file(f)
        ]

        for unmatched in path_filter.unmatched_patterns():
            logger.warning(
                f"[INCREMENTAL] Directory filter pattern matched 0 files/dirs: {unmatched!r}"
            )

        # Collect all chunks first, then embed in a single pass
        # Use parallel chunking for improved performance
        logger.info(
            f"[INCREMENTAL] Chunking {len(supported_files)} files (parallel={'enabled' if self.enable_parallel_chunking else 'disabled'})"
        )
        chunks_to_embed = self._chunk_files_parallel(project_path, supported_files)

        # File-level module summaries — shared with the full-index path via
        # SummaryStage.generate_and_extend (config-gated inside the stage).
        self._summary_stage.generate_and_extend(
            chunks_to_embed,
            log_prefix="[INCREMENTAL]",
            appended_noun="module summary chunks",
        )

        all_embedding_results = []
        if chunks_to_embed:
            # Let embed failures propagate — the caller's except routes to
            # _attempt_recovery, preventing a silent snapshot advance over
            # chunks that were removed but never re-embedded (#1).
            # cache_full_pass=False: this run's live_keys only covers the
            # handful of chunks that changed, never the whole project — see
            # ChunkEmbeddingCache._evict for why a full-pass cap here would
            # wrongly collapse a cache built by prior full indexes.
            all_embedding_results = self._index_write_stage.embed_and_attach_metadata(
                chunks_to_embed, project_name, cache_full_pass=False
            )

        # Add all embeddings to index at once, through the shared write seam.
        # Guarded here rather than inside add_to_index: an incremental pass
        # with only removals legitimately adds nothing, so the empty-input
        # warning would be noise on this path.
        if all_embedding_results:
            logger.info(f"[INCREMENTAL] Indexer type: {type(self.indexer).__name__}")
            self._index_write_stage.add_to_index(
                all_embedding_results, log_prefix="[INCREMENTAL] "
            )

        return len(all_embedding_results)

    def _clear_gpu_cache(self, log_prefix: str = "INCREMENTAL") -> None:
        """Clear GPU cache to free intermediate tensors from embedding batches.

        Args:
            log_prefix: Prefix for log messages (e.g., "INCREMENTAL" or "FULL_INDEX")
        """
        try:
            import torch

            gc.collect()  # Free Python wrapper objects first
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Then release CUDA cache
                logger.info(f"[{log_prefix}] GPU cache cleared after indexing")
        except ImportError:
            pass

    def get_indexing_stats(self, project_path: str) -> dict | None:
        """Get indexing statistics for a project.

        Args:
            project_path: Path to project

        Returns:
            Dictionary with statistics or None
        """
        metadata = self.snapshot_manager.load_metadata(project_path)
        if not metadata:
            return None

        # Add current index stats
        metadata["current_chunks"] = self.indexer.get_index_size()
        metadata["snapshot_age"] = self.snapshot_manager.get_snapshot_age(project_path)

        return metadata

    def needs_reindex(self, project_path: str, max_age_minutes: float = 5) -> bool:
        """Check if a project needs reindexing.

        Args:
            project_path: Path to project
            max_age_minutes: Maximum age of snapshot in minutes (default 5)

        Returns:
            True if reindex is needed
        """
        # No snapshot means needs index
        if not self.snapshot_manager.has_snapshot(project_path):
            return True

        # Check snapshot age (convert minutes to seconds)
        age = self.snapshot_manager.get_snapshot_age(project_path)
        if age and age > max_age_minutes * 60:
            return True

        # Quick check for changes
        return self.change_detector.quick_check(project_path)

    def auto_reindex_if_needed(
        self,
        project_path: str,
        project_name: str | None = None,
        max_age_minutes: float = 5,
    ) -> IncrementalIndexResult:
        """Automatically reindex if the index is stale.

        Args:
            project_path: Path to project
            project_name: Optional project name
            max_age_minutes: Maximum age before auto-reindex (default 5 minutes)

        Returns:
            IncrementalIndexResult with statistics
        """
        start_time = time.time()

        if self.needs_reindex(project_path, max_age_minutes):
            logger.info(
                f"Auto-reindexing {project_path} (index older than {max_age_minutes} minutes)"
            )

            # NOTE: previously this tore down state.embedders / ModelPoolManager /
            # self.embedder ("prevent OOM in multi-model mode") before reindexing.
            # The multi-model regime has been removed — state.embedders is a
            # single-entry pool by construction (mcp_server/model_pool_manager.py),
            # so that teardown only ever destroyed and reloaded the one active
            # model. Worse, it raced concurrent searches: a search mid-flight
            # (embed_query / reranker inference) could hit the torn-down embedder
            # and raise "cleaned up" or fall back to degraded scoring. Reindex now
            # reuses the live self.embedder; no teardown, no race.
            return self.incremental_index(project_path, project_name)
        else:
            logger.debug(f"Index for {project_path} is fresh, skipping reindex")
            return self._zero_result(start_time, success=True)
