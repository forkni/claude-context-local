"""Incremental indexing using Merkle tree change detection."""

import gc
import logging
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder
from merkle.change_detector import ChangeDetector, FileChanges
from merkle.merkle_dag import MerkleDAG
from merkle.snapshot_manager import SnapshotManager

from .bm25_sync import BM25SyncManager
from .config import get_search_config
from .graph_integration import GraphIntegration
from .indexer import CodeIndexManager as Indexer
from .parallel_chunker import ParallelChunker


logger = logging.getLogger(__name__)


@dataclass
class IncrementalIndexResult:
    """Result of incremental indexing operation."""

    files_added: int
    files_removed: int
    files_modified: int
    chunks_added: int
    chunks_removed: int
    time_taken: float
    success: bool
    error: Optional[str] = None
    bm25_resynced: bool = False
    bm25_resync_count: int = 0

    def to_dict(self) -> dict:
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


class IncrementalIndexer:
    """Handles incremental indexing of code changes."""

    def __init__(
        self,
        indexer: Optional[Indexer] = None,
        embedder: Optional[CodeEmbedder] = None,
        chunker: Optional[MultiLanguageChunker] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        include_dirs: Optional[list] = None,
        exclude_dirs: Optional[list] = None,
    ):
        """Initialize incremental indexer.

        Args:
            indexer: Indexer instance
            embedder: Embedder instance
            chunker: Code chunker instance
            snapshot_manager: Snapshot manager instance
            include_dirs: Optional list of directories to include
            exclude_dirs: Optional list of directories to exclude
        """
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
        )
        self.snapshot_manager = snapshot_manager or SnapshotManager()

        # Store directory filters for MerkleDAG creation
        self.include_dirs = include_dirs
        self.exclude_dirs = exclude_dirs

        # Create change detector with filters
        self.change_detector = ChangeDetector(
            self.snapshot_manager, include_dirs, exclude_dirs
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
        self._bm25_sync = BM25SyncManager(indexer=self.indexer)

    def _get_symbol_cache(self):
        """Get symbol cache, handling both CodeIndexManager and HybridSearcher.

        Returns:
            SymbolHashCache instance or None if not available
        """
        # Try direct access (CodeIndexManager)
        if hasattr(self.indexer, "metadata_store"):
            return self.indexer.metadata_store._symbol_cache

        # Try via dense_index (HybridSearcher)
        if hasattr(self.indexer, "dense_index"):
            dense_index = self.indexer.dense_index
            if hasattr(dense_index, "metadata_store"):
                return dense_index.metadata_store._symbol_cache

        return None

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

    def _is_supported_file(self, project_path: str, file_path: str) -> bool:
        """Check if file is supported for indexing.

        Args:
            project_path: Root project path
            file_path: Relative file path

        Returns:
            True if file is supported and not in ignored directories
        """
        full_path = Path(project_path) / file_path

        # Check if file extension is supported
        if not self.chunker.is_supported(str(full_path)):
            return False

        # Check if file is in ignored directory
        from chunking.multi_language_chunker import MultiLanguageChunker

        ignored_dirs = MultiLanguageChunker.DEFAULT_IGNORED_DIRS

        if any(part in ignored_dirs for part in Path(file_path).parts):
            return False

        return True

    def incremental_index(
        self,
        project_path: str,
        project_name: Optional[str] = None,
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

        if not project_name:
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
                except Exception as e:
                    logger.warning(f"VRAM cleanup failed (continuing with index): {e}")

                return self._full_index(project_path, project_name, start_time)

            # Detect changes
            logger.info(f"Detecting changes in {project_name}")
            changes, current_dag = self.detect_changes(project_path)

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

                return IncrementalIndexResult(
                    files_added=0,
                    files_removed=0,
                    files_modified=0,
                    chunks_added=0,
                    chunks_removed=0,
                    time_taken=time.time() - start_time,
                    success=True,
                    bm25_resynced=False,
                    bm25_resync_count=0,
                )

            # Log changes
            logger.info(
                f"Changes detected - Added: {len(changes.added)}, "
                f"Removed: {len(changes.removed)}, Modified: {len(changes.modified)}"
            )

            # Process changes
            chunks_removed = self._remove_old_chunks(changes, project_name)
            chunks_added = self._add_new_chunks(changes, project_path, project_name)

            # Validate index consistency after operations
            if hasattr(self.indexer, "validate_index_consistency"):
                logger.info("[INCREMENTAL] Validating index consistency...")
                is_valid, issues = self.indexer.validate_index_consistency()
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

            # Update snapshot
            # After processing changes, calculate cumulative stats
            all_files = list(current_dag.get_all_files())
            supported_files = self._get_supported_files(project_path, all_files)
            total_chunks = self._get_total_chunks()

            metadata = self._build_snapshot_metadata(
                project_name=project_name,
                all_files=all_files,
                supported_files=supported_files,
                total_chunks=total_chunks,
                is_full=False,
                files_added=len(changes.added),
                files_removed=len(changes.removed),
                files_modified=len(changes.modified),
            )
            self.snapshot_manager.save_snapshot(current_dag, metadata)

            # Update index
            logger.info("[INCREMENTAL] Saving index...")
            self.indexer.save_indices()
            logger.info("[INCREMENTAL] Index saved")

            # Auto-sync BM25 if significant desync detected (>10% difference)
            bm25_resynced, bm25_resync_count = self._sync_bm25_if_needed("INCREMENTAL")

            # Clear GPU cache to free intermediate tensors from embedding batches
            self._clear_gpu_cache("INCREMENTAL")

            return IncrementalIndexResult(
                files_added=len(changes.added),
                files_removed=len(changes.removed),
                files_modified=len(changes.modified),
                chunks_added=chunks_added,
                chunks_removed=chunks_removed,
                time_taken=time.time() - start_time,
                success=True,
                bm25_resynced=bm25_resynced,
                bm25_resync_count=bm25_resync_count,
            )

        except Exception as e:
            logger.error(f"Incremental indexing failed: {e}")
            import traceback

            logger.error(traceback.format_exc())

            return self._attempt_recovery(
                f"Incremental indexing failed: {e}",
                project_path,
                project_name,
                start_time,
            )

    def _attempt_recovery(
        self,
        original_error: str,
        project_path: str,
        project_name: str,
        start_time: float,
    ) -> IncrementalIndexResult:
        """Attempt recovery via full re-index after failure.

        Args:
            original_error: Description of the original failure
            project_path: Path to the project
            project_name: Name of the project
            start_time: Start time for duration calculation

        Returns:
            IncrementalIndexResult from recovery attempt or error result
        """
        logger.warning(f"Attempting recovery via full re-index: {original_error}")
        try:
            self.indexer.clear_index()
            return self._full_index(project_path, project_name, start_time)
        except Exception as recovery_error:
            logger.error(f"Recovery failed: {recovery_error}")
            import traceback

            logger.error(traceback.format_exc())
            return IncrementalIndexResult(
                files_added=0,
                files_removed=0,
                files_modified=0,
                chunks_added=0,
                chunks_removed=0,
                time_taken=time.time() - start_time,
                success=False,
                error=f"Original: {original_error}, Recovery: {recovery_error}",
                bm25_resynced=False,
                bm25_resync_count=0,
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
                    if (
                        self.exclude_dirs is None
                        and old_snapshot.directory_filter.exclude_dirs
                    ):
                        self.exclude_dirs = old_snapshot.directory_filter.exclude_dirs
                        logger.info(
                            f"[FULL_INDEX] Recovered exclude_dirs from snapshot: {self.exclude_dirs}"
                        )

            # Delete old Merkle snapshot for current model only (preserves other models)
            logger.info(
                f"[FULL_INDEX] Deleting old snapshot for current model: {project_name}"
            )
            self.snapshot_manager.delete_snapshot(project_path)
            logger.info("[FULL_INDEX] Deleted old snapshot for current model")

            # Clear existing index
            self.indexer.clear_index()

            # Build DAG for all files
            dag = MerkleDAG(project_path, self.include_dirs, self.exclude_dirs)
            dag.build()
            all_files = dag.get_all_files()

            # Filter supported files
            supported_files = self._get_supported_files(project_path, all_files)
            logger.info(
                f"Found {len(supported_files)} supported files out of {len(all_files)} total files"
            )
            for sf in supported_files:
                logger.info(f"  Supported: {sf}")

            # Collect all chunks first, then embed in a single pass for efficiency
            # Use parallel chunking for improved performance
            logger.info(
                f"Chunking files (parallel={'enabled' if self.enable_parallel_chunking else 'disabled'}, workers={self.max_chunking_workers})"
            )
            all_chunks = self._chunk_files_parallel(project_path, supported_files)

            # Log any files that didn't produce chunks
            files_with_chunks = sum(
                1
                for f in supported_files
                if any(c.file_path == str(Path(project_path) / f) for c in all_chunks)
            )
            if files_with_chunks < len(supported_files):
                logger.warning(
                    f"{len(supported_files) - files_with_chunks} files produced no chunks"
                )

            logger.info(f"Total chunks collected: {len(all_chunks)}")

            # ========== Community Detection & Remerge ==========
            # Community merge flow: Chunk → Build graph → Detect communities → (Optional) Remerge → Embed
            # Community detection runs independently of chunk merging
            config = get_search_config()
            community_map = None  # Will be populated if community detection runs

            # Step A: Community Detection (Independent - can run without merging)
            if config.chunking.enable_community_detection and all_chunks:
                logger.info("[COMMUNITY_DETECT] Running community detection")
                logger.info(
                    f"[COMMUNITY_DETECT] Starting with {len(all_chunks)} chunks"
                )

                try:
                    # Build graph from chunks (NetworkX DiGraph)
                    # Uses GraphIntegration.build_graph_from_chunks() - no embeddings needed
                    temp_graph = self._build_temp_graph(all_chunks)

                    # Detect communities using native Louvain algorithm
                    # NetworkX native (no external dependencies: igraph/leidenalg)
                    from graph.community_detector import CommunityDetector

                    detector = CommunityDetector(temp_graph.storage)
                    community_map = detector.detect_communities(
                        resolution=config.chunking.community_resolution
                    )
                    logger.info(
                        f"[COMMUNITY_DETECT] Detected {len(set(community_map.values()))} communities from {len(community_map)} nodes"
                    )

                    # NEW: Persist community_map to graph storage for future use
                    if community_map and temp_graph:
                        temp_graph.storage.store_community_map(community_map)
                        logger.info(
                            "[COMMUNITY_DETECT] Community map persisted to graph storage"
                        )

                except Exception as e:
                    logger.error(f"[COMMUNITY_DETECT] Failed: {e}")
                    import traceback

                    logger.error(traceback.format_exc())
                    logger.warning(
                        "[COMMUNITY_DETECT] Continuing without community data"
                    )
                    community_map = None

            # Step B: Community-based Remerge (Full index only)
            if config.chunking.enable_community_merge and community_map and all_chunks:
                logger.info("[COMMUNITY_MERGE] Running community-based remerge")

                try:
                    # Remerge with community boundaries
                    # Uses fixed remerge_chunks_with_communities() from base.py
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

                    # Regenerate proper chunk_ids (line numbers changed after merge)
                    all_chunks = self._regenerate_chunk_ids(all_chunks, project_path)

                    logger.info(
                        f"[COMMUNITY_MERGE] Community merge complete: {len(all_chunks)} final chunks"
                    )

                except Exception as e:
                    logger.error(f"[COMMUNITY_MERGE] Failed: {e}")
                    import traceback

                    logger.error(traceback.format_exc())
                    logger.warning(
                        "[COMMUNITY_MERGE] Continuing with unmerged chunks from Pass 1"
                    )
            # ========== END Community Detection & Remerge ==========

            # Embed all chunks in one batched call
            all_embedding_results = []
            if all_chunks:
                try:
                    logger.info(f"Starting embedding for {len(all_chunks)} chunks")
                    all_embedding_results = self.embedder.embed_chunks(all_chunks)
                    logger.info(
                        f"Successfully embedded {len(all_embedding_results)} chunks"
                    )
                    # Update metadata
                    for chunk, embedding_result in zip(
                        all_chunks, all_embedding_results, strict=False
                    ):
                        embedding_result.metadata["project_name"] = project_name
                        embedding_result.metadata["content"] = chunk.content
                except Exception as e:
                    logger.error(f"Embedding failed: {e}")
                    import traceback

                    logger.error(traceback.format_exc())

            # Add all embeddings to index at once
            if all_embedding_results:
                logger.info(f"Adding {len(all_embedding_results)} embeddings to index")
                self.indexer.add_embeddings(all_embedding_results)
                logger.info("Successfully added embeddings to index")
            else:
                logger.warning("No embedding results to add to index")

            chunks_added = len(all_embedding_results)

            # Save snapshot
            metadata = self._build_snapshot_metadata(
                project_name=project_name,
                all_files=all_files,
                supported_files=supported_files,
                total_chunks=chunks_added,
                is_full=True,
            )
            self.snapshot_manager.save_snapshot(dag, metadata)

            # Save index
            logger.info("[INCREMENTAL] Saving index...")
            self.indexer.save_indices()
            logger.info("[INCREMENTAL] Index saved")

            # Auto-sync BM25 if significant desync detected (>10% difference)
            bm25_resynced, bm25_resync_count = self._sync_bm25_if_needed("FULL_INDEX")

            # Clear GPU cache to free intermediate tensors from embedding batches
            self._clear_gpu_cache("FULL_INDEX")

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

        except Exception as e:
            logger.error(f"Full indexing failed: {e}")
            return IncrementalIndexResult(
                files_added=0,
                files_removed=0,
                files_modified=0,
                chunks_added=0,
                chunks_removed=0,
                time_taken=time.time() - start_time,
                success=False,
                error=str(e),
                bm25_resynced=False,
                bm25_resync_count=0,
            )

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

    def _build_temp_graph(self, chunks: list[CodeChunk]) -> GraphIntegration:
        """Build temporary graph from chunks for community detection.

        Creates a GraphIntegration instance and builds the NetworkX graph
        from unmerged chunks WITHOUT embeddings. Used for pre-embedding
        community detection in two-pass chunking flow.

        Args:
            chunks: List of CodeChunk objects with chunk_id, calls, relationships

        Returns:
            GraphIntegration instance with populated NetworkX graph

        Reference:
            search/graph_integration.py:build_graph_from_chunks()
        """
        # Create temporary GraphIntegration with project ID
        # Use indexer's storage directory for graph storage
        storage_dir = (
            Path(self.indexer.storage_dir)
            if hasattr(self.indexer, "storage_dir")
            else Path(tempfile.mkdtemp(prefix="temp_graph_"))
        )

        # Extract project ID from parent directory name matching search_factory.py convention
        # Parent dir name = "projectname_hash_modelslug_dimd", strip "_dimd" suffix
        project_id = (
            storage_dir.parent.name.rsplit("_", 1)[0]
            if storage_dir.exists()
            else "temp_community_graph"
        )

        graph_integration = GraphIntegration(
            project_id=project_id, storage_dir=storage_dir
        )

        # Build graph from chunks (NetworkX DiGraph API)
        graph_integration.build_graph_from_chunks(chunks)

        logger.info(
            f"[COMMUNITY_MERGE] Built temporary graph: {graph_integration.node_count} nodes"
        )

        return graph_integration

    def _regenerate_chunk_ids(
        self, chunks: list[CodeChunk], project_path: str
    ) -> list[CodeChunk]:
        """Regenerate proper chunk_ids after community-based remerge.

        After remerging chunks with community boundaries, line numbers change
        and chunk_ids become invalid. This method regenerates chunk_ids with
        correct line ranges and proper format.

        Format: {relative_path}:{start_line}-{end_line}:{chunk_type}:{name}

        Args:
            chunks: List of CodeChunk objects after remerge
            project_path: Root project directory for computing relative paths

        Returns:
            List of CodeChunk with regenerated chunk_ids

        Example:
            src/auth.py:10-50:function:login
            src/models.py:5-120:class:User
            src/utils.py:15-45:method:Database.connect
        """
        from dataclasses import replace

        result = []
        project_root = Path(project_path)

        for chunk in chunks:
            # Compute relative path
            if chunk.relative_path:
                rel_path = chunk.relative_path
            else:
                chunk_path = Path(chunk.file_path)
                try:
                    rel_path = str(chunk_path.relative_to(project_root))
                except ValueError:
                    # If relative_to fails, use the filename
                    rel_path = chunk_path.name

            # Normalize path separators to forward slash
            normalized_path = str(rel_path).replace("\\", "/")

            # Build chunk_id: path:lines:type:name
            chunk_id = f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"

            # Add qualified name if available
            if chunk.parent_name and chunk.name:
                chunk_id += f":{chunk.parent_name}.{chunk.name}"
            elif chunk.name:
                chunk_id += f":{chunk.name}"

            # Create new chunk with regenerated ID
            new_chunk = replace(chunk, chunk_id=chunk_id)
            result.append(new_chunk)

            # Register symbol mappings for all symbols in this chunk
            symbol_cache = self._get_symbol_cache()
            if symbol_cache is not None:
                # Register primary symbol name
                if chunk.name:
                    symbol_cache.add_symbol_mapping(chunk.name, chunk_id)

                # Register all merged symbol names (for merged chunks)
                # Use merged_from attribute instead of metadata
                if chunk.merged_from:
                    for symbol_name in chunk.merged_from:
                        if symbol_name:  # Skip empty names
                            symbol_cache.add_symbol_mapping(symbol_name, chunk_id)

        logger.info(f"[COMMUNITY_MERGE] Regenerated chunk_ids for {len(result)} chunks")

        return result

    def _build_snapshot_metadata(
        self,
        project_name: str,
        all_files: list,
        supported_files: list,
        total_chunks: int,
        is_full: bool = False,
        **changes,
    ) -> dict[str, Any]:
        """Build metadata dictionary for snapshot storage.

        Args:
            project_name: Name of the project
            all_files: List of all files in project
            supported_files: List of supported files
            total_chunks: Total number of indexed chunks
            is_full: Whether this is a full index (vs incremental)
            **changes: Optional file change counts (files_added, files_removed, files_modified, etc.)

        Returns:
            Metadata dictionary for snapshot
        """
        metadata = {
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

        # Use batch removal for efficiency (single pass instead of one per file)
        # Handles FAISS vector removal and index reconstruction
        if hasattr(self.indexer, "remove_multiple_files") and files_to_remove:
            try:
                chunks_removed = self.indexer.remove_multiple_files(
                    set(files_to_remove), project_name
                )
                logger.info(
                    f"Batch removed {chunks_removed} chunks from {len(files_to_remove)} files"
                )
                return chunks_removed
            except Exception as e:
                logger.error(f"Batch removal failed: {e}")
                logger.warning("Falling back to individual file removal")
                # Fall back to individual removal on error
                chunks_removed = 0
                for file_path in files_to_remove:
                    removed = self.indexer.remove_file_chunks(file_path, project_name)
                    chunks_removed += removed
                    logger.debug(f"Removed {removed} chunks from {file_path}")
                return chunks_removed
        else:
            # Fallback to individual removal if batch method not available
            chunks_removed = 0
            for file_path in files_to_remove:
                removed = self.indexer.remove_file_chunks(file_path, project_name)
                chunks_removed += removed
                logger.debug(f"Removed {removed} chunks from {file_path}")
            return chunks_removed

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

        # Filter supported files and exclude ignored directories
        from chunking.multi_language_chunker import MultiLanguageChunker

        ignored_dirs = MultiLanguageChunker.DEFAULT_IGNORED_DIRS

        supported_files = [
            f
            for f in files_to_index
            if self.chunker.is_supported(f)
            and not any(part in ignored_dirs for part in Path(f).parts)
        ]

        # Collect all chunks first, then embed in a single pass
        # Use parallel chunking for improved performance
        logger.info(
            f"[INCREMENTAL] Chunking {len(supported_files)} files (parallel={'enabled' if self.enable_parallel_chunking else 'disabled'})"
        )
        chunks_to_embed = self._chunk_files_parallel(project_path, supported_files)

        all_embedding_results = []
        if chunks_to_embed:
            try:
                all_embedding_results = self.embedder.embed_chunks(chunks_to_embed)
                # Update metadata
                for chunk, embedding_result in zip(
                    chunks_to_embed, all_embedding_results, strict=False
                ):
                    embedding_result.metadata["project_name"] = project_name
                    embedding_result.metadata["content"] = chunk.content
            except Exception as e:
                logger.warning(f"Embedding failed: {e}")

        # Add all embeddings to index at once
        if all_embedding_results:
            logger.info(
                f"[INCREMENTAL] Adding {len(all_embedding_results)} embeddings to index"
            )
            logger.info(f"[INCREMENTAL] Indexer type: {type(self.indexer).__name__}")

            # Add embeddings
            self.indexer.add_embeddings(all_embedding_results)

            logger.info("[INCREMENTAL] Successfully added embeddings")

        return len(all_embedding_results)

    def _sync_bm25_if_needed(self, log_prefix: str = "INCREMENTAL") -> tuple[bool, int]:
        """Auto-sync BM25 if significant desync detected (>10% difference).

        Args:
            log_prefix: Prefix for log messages (e.g., "INCREMENTAL" or "FULL_INDEX")

        Returns:
            tuple[bool, int]: (bm25_resynced, bm25_resync_count)
        """
        return self._bm25_sync.sync_if_needed(log_prefix)

    def _clear_gpu_cache(self, log_prefix: str = "INCREMENTAL") -> None:
        """Clear GPU cache to free intermediate tensors from embedding batches.

        Args:
            log_prefix: Prefix for log messages (e.g., "INCREMENTAL" or "FULL_INDEX")
        """
        try:
            import gc

            import torch

            gc.collect()  # Free Python wrapper objects first
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Then release CUDA cache
                logger.info(f"[{log_prefix}] GPU cache cleared after indexing")
        except ImportError:
            pass

    def get_indexing_stats(self, project_path: str) -> Optional[dict]:
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
        project_name: Optional[str] = None,
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
        import time

        start_time = time.time()

        if self.needs_reindex(project_path, max_age_minutes):
            logger.info(
                f"Auto-reindexing {project_path} (index older than {max_age_minutes} minutes)"
            )

            # Free VRAM before re-indexing to prevent OOM in multi-model mode
            logger.info("Freeing VRAM before auto-reindex (multi-model cleanup)...")
            try:
                # Import here to avoid circular dependencies
                from mcp_server.model_pool_manager import reset_pool_manager
                from mcp_server.services import get_state

                state = get_state()

                # Clear ALL embedders in multi-model pool (not just self.embedder)
                if state.embedders:
                    embedder_count = len(state.embedders)
                    logger.info(
                        f"Clearing {embedder_count} cached embedder(s) before reindex: "
                        f"{list(state.embedders.keys())}"
                    )
                    state.clear_embedders()
                    logger.info("Embedder pool cleared - VRAM released")

                # Reset ModelPoolManager singleton to release all model references
                reset_pool_manager()
                logger.info("ModelPoolManager singleton reset")

                # Force garbage collection and GPU cache cleanup
                gc.collect()
                logger.info("Garbage collection completed")

                try:
                    import torch

                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        logger.info("GPU cache cleared")
                except ImportError:
                    pass

                logger.info("Multi-model VRAM cleanup completed successfully")
            except Exception as e:
                logger.warning(
                    f"Multi-model VRAM cleanup failed (continuing with reindex): {e}"
                )

            # Cleanup OUR OWN embedder reference before creating a new one
            # This prevents VRAM accumulation (old embedder + new embedder)
            if hasattr(self, "embedder") and hasattr(self.embedder, "cleanup"):
                logger.info("Cleaning up IncrementalIndexer's embedder reference...")
                self.embedder.cleanup()
                logger.info("IncrementalIndexer's embedder cleaned")

            # Refresh embedder after cleanup - old one can't reload (model loader cleared)
            # This ensures cleanup happens before model is loaded for reindex
            from mcp_server.model_pool_manager import (
                get_embedder,
                get_model_key_from_name,
            )
            from search.dimension_validator import read_index_metadata

            # CRITICAL: Read the model from the existing index to ensure we use the SAME model
            # that was used to create the index (prevents dimension mismatch errors)
            model_key = None
            try:
                # Get storage_dir from indexer (CodeIndexManager or HybridSearcher.dense_index)
                if hasattr(self.indexer, "storage_dir"):
                    storage_dir = self.indexer.storage_dir
                elif hasattr(self.indexer, "dense_index") and hasattr(
                    self.indexer.dense_index, "storage_dir"
                ):
                    storage_dir = self.indexer.dense_index.storage_dir
                else:
                    storage_dir = None

                if storage_dir:
                    metadata = read_index_metadata(storage_dir)
                    if metadata and metadata.get("embedding_model"):
                        model_name = metadata["embedding_model"]
                        model_key = get_model_key_from_name(model_name)
                        logger.info(
                            f"Using model from index: {model_name} (key: {model_key})"
                        )
            except Exception as e:
                logger.warning(f"Could not read model from index metadata: {e}")

            self.embedder = get_embedder(model_key)
            logger.info("Embedder refreshed after cleanup - ready for reindex")

            return self.incremental_index(project_path, project_name)
        else:
            logger.debug(f"Index for {project_path} is fresh, skipping reindex")
            return IncrementalIndexResult(
                files_added=0,
                files_removed=0,
                files_modified=0,
                chunks_added=0,
                chunks_removed=0,
                time_taken=time.time() - start_time,
                success=True,
                bm25_resynced=False,
                bm25_resync_count=0,
            )
