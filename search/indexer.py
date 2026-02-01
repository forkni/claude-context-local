"""Vector index management with FAISS and metadata storage."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np


if TYPE_CHECKING:
    from search.symbol_cache import SymbolHashCache


try:
    import faiss
except ImportError:
    faiss = None

try:
    from sqlitedict import SqliteDict
except ImportError:
    SqliteDict = None

from embeddings.embedder import EmbeddingResult
from search.batch_operations import BatchOperations
from search.faiss_index import FaissVectorIndex
from search.filters import FilterEngine
from search.graph_integration import GraphIntegration
from search.metadata import MetadataStore


class CodeIndexManager:
    """Manages FAISS vector index and metadata storage for code chunks."""

    def __init__(
        self,
        storage_dir: str,
        embedder=None,
        project_id: str | None = None,
        config=None,
    ):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.index_path = self.storage_dir / "code.index"
        self.metadata_path = self.storage_dir / "metadata.db"
        self.stats_path = self.storage_dir / "stats.json"

        # Initialize components
        self._metadata_store = MetadataStore(self.metadata_path)
        self._faiss_index = FaissVectorIndex(self.index_path, embedder=embedder)
        self._logger = logging.getLogger(__name__)
        self._logger.info(
            f"[INIT] CodeIndexManager created: storage_dir={storage_dir}, project_id={project_id}"
        )
        self.embedder = embedder  # Optional embedder for dimension validation

        # Initialize graph integration layer
        self._graph = GraphIntegration(project_id, self.storage_dir)

        # Backward compatibility: expose graph storage directly
        self.graph_storage = self._graph.storage

        # Initialize batch operations handler
        self._batch_ops = BatchOperations(
            self._faiss_index, self._metadata_store, self._logger
        )

        # Check dependencies
        self._check_dependencies()

        # Load existing index
        self._faiss_index.load()

    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        if faiss is None:
            raise ImportError(
                "faiss-cpu not found. Install with: pip install faiss-cpu"
            )

        if SqliteDict is None:
            raise ImportError(
                "sqlitedict not found. Install with: pip install sqlitedict"
            )

    @property
    def index(self) -> Optional["faiss.Index"]:
        """Access to underlying FAISS index."""
        return self._faiss_index.index

    @property
    def chunk_ids(self) -> list[str]:
        """Public property - List of all indexed chunk IDs."""
        return self._faiss_index.chunk_ids

    @property
    def ntotal(self) -> int:
        """Public property - Total number of vectors in index."""
        return self._faiss_index.ntotal

    @property
    def is_on_gpu(self) -> bool:
        """Public property - Whether index is currently on GPU."""
        return self._faiss_index.is_on_gpu

    @property
    def metadata_store(self) -> MetadataStore:
        """Access to metadata storage layer.

        Returns the MetadataStore instance for chunk metadata operations.
        """
        return self._metadata_store

    @property
    def symbol_cache(self) -> "SymbolHashCache":
        """Expose symbol cache for direct symbol lookup.

        Returns the SymbolHashCache instance from metadata_store,
        enabling O(1) symbol name → chunk_id lookups for find_path
        and other tools without relying on semantic search.
        """
        return self._metadata_store._symbol_cache

    def create_index(self, embedding_dimension: int, index_type: str = "flat") -> None:
        """Create a new FAISS index.

        Args:
            embedding_dimension: Dimension of embedding vectors
            index_type: Type of index to create ("flat" or "ivf")
        """
        self._faiss_index.create(embedding_dimension, index_type)

    def add_embeddings(self, embedding_results: list[EmbeddingResult]) -> None:
        """Add embeddings to the index and metadata to the database.

        Args:
            embedding_results: List of EmbeddingResult objects containing embeddings
                             and their associated metadata (chunk_id, content, etc.)

        Raises:
            ValueError: If embedding dimension doesn't match the model's expected dimension
        """
        if not embedding_results:
            return

        # Check memory requirements before proceeding
        embedding_dim = embedding_results[0].embedding.shape[0]
        num_new_vectors = len(embedding_results)

        # Validate embedding dimension matches expected model dimension
        if self.embedder is not None:
            try:
                model_info = self.embedder.get_model_info()
                expected_dim = model_info.get("embedding_dimension")
                if expected_dim and embedding_dim != expected_dim:
                    raise ValueError(
                        f"Embedding dimension mismatch detected!\n"
                        f"  Provided embeddings: {embedding_dim} dimensions\n"
                        f"  Expected for model '{self.embedder.model_name}': {expected_dim} dimensions\n"
                        f"  This usually means embeddings were generated with a different model.\n"
                        f"  Solution: Ensure embedder matches the model used to generate embeddings."
                    )
            except (KeyError, AttributeError) as e:
                # Model info not available yet (model not loaded) or get_model_info not available
                self._logger.debug(f"Cannot validate embedding dimension: {e}")

        memory_check = self.check_memory_requirements(num_new_vectors, embedding_dim)

        # Abort if insufficient memory to prevent OOM
        if not memory_check["sufficient_memory"]:
            raise MemoryError(
                f"Insufficient memory to add {num_new_vectors} vectors. "
                f"Need {memory_check['required_memory'] // (1024**2):.1f}MB, "
                f"have {memory_check['available_memory']['gpu_available' if memory_check['prefer_gpu'] else 'system_available'] // (1024**2):.1f}MB. "
                f"Consider indexing in smaller batches or freeing memory."
            )

        # Initialize index if needed
        if self.index is None:
            # Default to flat index for better recall - only use IVF for very large datasets
            index_type = "ivf" if num_new_vectors > 10000 else "flat"
            self.create_index(embedding_dim, index_type)

        # Prepare embeddings and metadata
        embeddings = np.array([result.embedding for result in embedding_results])
        chunk_ids_to_add = [result.chunk_id for result in embedding_results]

        # Add to FAISS index (handles normalization and training internally)
        start_id = self._faiss_index.ntotal
        self._faiss_index.add(embeddings, chunk_ids_to_add)

        # Store metadata
        for i, result in enumerate(embedding_results):
            chunk_id = result.chunk_id

            # Store in metadata database
            self.metadata_store.set(chunk_id, start_id + i, result.metadata)

            # Populate call graph via integration layer
            if self._graph.is_available:
                self._graph.add_chunk(chunk_id, result.metadata)
                self._logger.debug(
                    f"Graph storage check: chunk_id={chunk_id}, type={result.metadata.get('chunk_type')}, graph_nodes={len(self._graph)}"
                )

        self._logger.info(f"Added {len(embedding_results)} embeddings to index")

        # Commit metadata in a single transaction for performance
        try:
            self.metadata_store.commit()
        except sqlite3.Error:
            # If commit is unavailable for some reason, continue without failing
            pass

        # Save call graph if populated
        graph_status = "not None" if self.graph_storage is not None else "None"
        graph_nodes = len(self.graph_storage) if self.graph_storage else 0
        self._logger.info(
            f"Graph storage check before save: graph_storage={graph_status}, nodes={graph_nodes}"
        )
        if self.graph_storage is not None and len(self.graph_storage) > 0:
            try:
                self._logger.info(
                    f"Saving call graph with {len(self.graph_storage)} nodes to {self.graph_storage.graph_path}"
                )
                self.graph_storage.save()
                self._logger.info(
                    f"Successfully saved call graph with {len(self.graph_storage)} nodes"
                )
            except Exception as e:
                self._logger.warning(f"Failed to save call graph: {e}")
        else:
            skip_reason = "None" if self.graph_storage is None else "empty (0 nodes)"
            self._logger.warning(f"Skipping graph save: graph_storage is {skip_reason}")

        # Update statistics
        self._update_stats()

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Search for similar code chunks."""
        self._logger.info(f"Index manager search called with k={k}, filters={filters}")

        # Check if index exists and has vectors
        if self.index is None or self._faiss_index.ntotal == 0:
            self._logger.warning(
                f"Index is empty or None. Index: {self.index}, ntotal: {self._faiss_index.ntotal}"
            )
            return []

        self._logger.info(f"Index has {self._faiss_index.ntotal} total vectors")

        # Search in FAISS index (handles normalization internally)
        search_k = min(
            k * 3, self._faiss_index.ntotal
        )  # Get more results for filtering
        similarities, indices = self._faiss_index.search(query_embedding, search_k)

        results = []
        for _i, (similarity, index_id) in enumerate(
            zip(similarities, indices, strict=False)
        ):
            if index_id == -1:  # No more results
                break

            chunk_id = self.chunk_ids[index_id]
            metadata_entry = self.metadata_store.get(chunk_id)

            if metadata_entry is None:
                continue

            metadata = metadata_entry["metadata"]

            # Apply filters
            if filters and not self._matches_filters(metadata, filters):
                continue

            results.append((chunk_id, float(similarity), metadata))

            if len(results) >= k:
                break

        return results

    def _matches_filters(
        self, metadata: dict[str, Any], filters: dict[str, Any]
    ) -> bool:
        """Check if metadata matches the provided filters.

        Uses FilterEngine for unified filter logic across the codebase.
        Kept as a method for backward compatibility.
        """
        return FilterEngine.from_dict(filters).matches(metadata)

    def get_chunk_by_id(self, chunk_id: str) -> Optional[dict[str, Any]]:
        """Retrieve chunk metadata by ID with path normalization.

        Handles Windows backslash escaping issues in MCP transport by trying
        multiple path separator variants via symbol hash cache (O(1) lookup).

        Args:
            chunk_id: Chunk ID to lookup

        Returns:
            Chunk metadata dict if found, None otherwise
        """
        # MetadataStore.get() now handles hash cache lookup + variant fallback internally
        metadata_entry = self.metadata_store.get(chunk_id)

        if metadata_entry:
            return metadata_entry["metadata"]

        self._logger.warning(f"Chunk not found for ID: {chunk_id}")
        return None

    def get_similar_chunks(
        self, chunk_id: str, k: int = 5
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """Find chunks similar to a given chunk via symbol hash cache (O(1) lookup)."""
        # MetadataStore.get() now handles hash cache lookup + variant fallback internally
        metadata_entry = self.metadata_store.get(chunk_id)

        if not metadata_entry:
            return []

        index_id = metadata_entry["index_id"]
        if self.index is None or index_id >= self.index.ntotal:
            return []

        # Get the embedding for this chunk
        embedding = self._faiss_index.reconstruct(index_id)

        # Search for similar chunks (excluding the original)
        results = self.search(embedding, k + 1)

        # Filter out the original chunk
        return [(cid, sim, meta) for cid, sim, meta in results if cid != chunk_id][:k]

    def get_similar_chunks_batched(
        self, chunk_ids: list[str], k: int = 5
    ) -> dict[str, list[tuple[str, float, dict[str, Any]]]]:
        """
        Find chunks similar to multiple chunks in a single batched FAISS search.

        This is significantly faster than calling get_similar_chunks() multiple times,
        as it performs a single batched FAISS search instead of N individual searches.

        Args:
            chunk_ids: List of chunk IDs to find similar chunks for
            k: Number of similar chunks to return per query

        Returns:
            Dict mapping chunk_id -> list of (chunk_id, similarity, metadata) tuples
        """
        if not chunk_ids:
            return {}

        # Use property to trigger lazy loading
        index = self.index
        if index is None or index.ntotal == 0:
            return {cid: [] for cid in chunk_ids}

        # Collect embeddings and track original -> variant mapping
        embeddings = []
        valid_chunk_ids = []
        original_to_variant = {}  # Track mapping for correct key lookup

        for original_chunk_id in chunk_ids:
            # Try all path variants to handle Windows/Unix differences
            metadata_entry = None
            resolved_chunk_id = original_chunk_id  # Default to original

            for variant in MetadataStore.get_chunk_id_variants(original_chunk_id):
                metadata_entry = self.metadata_store.get(variant)
                if metadata_entry:
                    resolved_chunk_id = variant  # Use the variant that worked
                    break

            if not metadata_entry:
                continue

            index_id = metadata_entry["index_id"]
            if index_id >= index.ntotal:
                continue

            # Get the embedding for this chunk
            embedding = self._faiss_index.reconstruct(index_id)
            embeddings.append(embedding)
            valid_chunk_ids.append(resolved_chunk_id)
            original_to_variant[original_chunk_id] = resolved_chunk_id

        if not embeddings:
            return {cid: [] for cid in chunk_ids}

        # Perform batched search
        query_embeddings = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(query_embeddings)

        # Search for k+1 to account for excluding the query chunk itself
        search_k = min(k + 1, index.ntotal)
        similarities, indices = index.search(query_embeddings, search_k)

        # Process results - key by original chunk_id for correct caller lookup
        results_dict = {}
        variant_to_original = {v: k for k, v in original_to_variant.items()}

        for i, query_chunk_id in enumerate(valid_chunk_ids):
            query_results = []

            for similarity, index_id in zip(similarities[i], indices[i], strict=False):
                if index_id == -1:  # No more results
                    break

                chunk_id = self.chunk_ids[index_id]

                # Skip the original chunk
                if chunk_id == query_chunk_id:
                    continue

                metadata_entry = self.metadata_store.get(chunk_id)
                if metadata_entry is None:
                    continue

                metadata = metadata_entry["metadata"]
                query_results.append((chunk_id, float(similarity), metadata))

                if len(query_results) >= k:
                    break

            # Key by ORIGINAL chunk_id, not variant
            original_key = variant_to_original.get(query_chunk_id, query_chunk_id)
            results_dict[original_key] = query_results

        # Add empty results for invalid chunk_ids
        for chunk_id in chunk_ids:
            if chunk_id not in results_dict:
                results_dict[chunk_id] = []

        self._logger.debug(
            f"Batched search: {len(chunk_ids)} queries, {len(valid_chunk_ids)} valid"
        )

        return results_dict

    def remove_file_chunks(
        self, file_path: str, project_name: Optional[str] = None
    ) -> int:
        """Remove all chunks from a specific file.

        Args:
            file_path: Path to the file (relative or absolute)
            project_name: Optional project name filter

        Returns:
            Number of chunks removed
        """
        chunks_to_remove = []

        # Find chunks to remove
        for chunk_id in self.chunk_ids:
            metadata_entry = self.metadata_store.get(chunk_id)
            if not metadata_entry:
                continue

            metadata = metadata_entry["metadata"]

            # Check if this chunk belongs to the file
            chunk_file = metadata.get("file_path") or metadata.get("relative_path")
            if not chunk_file:
                continue

            # Check if paths match (handle both relative and absolute)
            if file_path in chunk_file or chunk_file in file_path:
                # Check project name if provided
                if project_name and metadata.get("project_name") != project_name:
                    continue
                chunks_to_remove.append(chunk_id)

        # Remove chunks from metadata
        for chunk_id in chunks_to_remove:
            self.metadata_store.delete(chunk_id)

        # Note: We don't remove from FAISS index directly as it's complex
        # Instead, we'll rebuild the index periodically or on demand

        self._logger.info(f"Removed {len(chunks_to_remove)} chunks from {file_path}")

        # Commit removals in batch
        try:
            self.metadata_store.commit()
        except sqlite3.Error:
            pass
        return len(chunks_to_remove)

    def remove_multiple_files(
        self, file_paths: set, project_name: Optional[str] = None
    ) -> int:
        """Remove chunks from multiple files in a single pass.

        This is much faster than calling remove_file_chunks() repeatedly,
        as it only scans through all chunks once instead of once per file.

        IMPORTANT: This method properly removes vectors from FAISS index by rebuilding it,
        which prevents index corruption and access violations.

        Args:
            file_paths: Set of file paths to remove
            project_name: Optional project name filter

        Returns:
            Total number of chunks removed
        """
        if not file_paths:
            return 0

        # Force lazy loading of index and chunk_ids before accessing them
        _ = self.index

        # Delegate to batch operations handler
        return self._batch_ops.remove_files(
            file_paths=file_paths,
            chunk_ids=self.chunk_ids,
            project_name=project_name,
            clear_index_callback=self.clear_index,
        )

    def save_index(self) -> None:
        """Save the FAISS index and chunk IDs to disk."""
        # Delegate FAISS index and chunk ID saving to FaissVectorIndex
        self._faiss_index.save()

        # Defensive: Check if graph storage is available
        if hasattr(self._graph, "storage") and self._graph.storage:
            # Storage exists, no need to re-init
            pass
        else:
            # Storage is None - try to find project_id
            # Note: project_id is not stored in CodeIndexManager, only passed to GraphIntegration
            # This defensive code path may not have access to project_id
            # Log warning but don't crash
            if self._graph.storage is None:
                self._logger.warning(
                    "[SAVE] Graph storage is None. Graph will not be saved. "
                    "This may occur if project was indexed without project_id."
                )

        # Save call graph via integration layer
        self._graph.save()

    def save_indices(self) -> None:
        """Save indices (alias for save_index for IncrementalIndexer compatibility)."""
        self.save_index()

        # Save model metadata for dimension validation (if embedder available)
        if self.embedder is not None:
            model_info_path = self.index_path.parent / "model_info.json"
            try:
                import json

                model_info = {
                    "model_name": self.embedder.model_name,
                    "embedding_dimension": self.embedder.get_model_info()[
                        "embedding_dimension"
                    ],
                    "created_at": (
                        str(self.index_path.stat().st_mtime)
                        if self.index_path.exists()
                        else None
                    ),
                }
                with open(model_info_path, "w") as f:
                    json.dump(model_info, f, indent=2)
                self._logger.debug(f"Saved model info to {model_info_path}")
            except Exception as e:
                self._logger.debug(f"Failed to save model info (non-critical): {e}")

        self._update_stats()

    def load(self) -> bool:
        """
        Public method to load index (for compatibility with other index classes).

        Returns:
            bool: True if index was loaded successfully or already exists, False otherwise
        """
        # Delegate to FaissVectorIndex
        return self._faiss_index.load()

    def _add_to_graph(self, chunk_id: str, metadata: dict[str, Any]) -> None:
        """Add chunk to call graph storage (compatibility wrapper).

        This method is kept for backward compatibility. New code should
        use the GraphIntegration layer directly.

        Args:
            chunk_id: Unique chunk identifier
            metadata: Chunk metadata including calls and relationships
        """
        self._graph.add_chunk(chunk_id, metadata)

    def _update_stats(self):
        """Update index statistics."""
        stats = {
            "total_chunks": len(self.chunk_ids),
            "index_size": self.ntotal if self.index else 0,
            "embedding_dimension": self.index.d if self.index else 0,
            "index_type": type(self.index).__name__ if self.index else "None",
        }

        # Add file and folder statistics
        file_counts = {}
        folder_counts = {}
        chunk_type_counts = {}
        tag_counts = {}

        for chunk_id in self.chunk_ids:
            metadata_entry = self.metadata_store.get(chunk_id)
            if not metadata_entry:
                continue

            metadata = metadata_entry["metadata"]

            # Count by file
            file_path = metadata.get("relative_path", "unknown")
            file_counts[file_path] = file_counts.get(file_path, 0) + 1

            # Count by folder
            for folder in metadata.get("folder_structure", []):
                folder_counts[folder] = folder_counts.get(folder, 0) + 1

            # Count by chunk type
            chunk_type = metadata.get("chunk_type", "unknown")
            chunk_type_counts[chunk_type] = chunk_type_counts.get(chunk_type, 0) + 1

            # Count by tags
            for tag in metadata.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        stats.update(
            {
                "files_indexed": len(file_counts),
                "top_folders": dict(
                    sorted(folder_counts.items(), key=lambda x: x[1], reverse=True)[:10]
                ),
                "chunk_types": chunk_type_counts,
                "top_tags": dict(
                    sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:20]
                ),
            }
        )

        # Save stats
        with open(self.stats_path, "w") as f:
            json.dump(stats, f, indent=2)

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        if self.stats_path.exists():
            with open(self.stats_path, "r") as f:
                return json.load(f)
        else:
            return {
                "total_chunks": 0,
                "index_size": 0,
                "embedding_dimension": 0,
                "files_indexed": 0,
            }

    def get_index_size(self) -> int:
        """Get the number of chunks in the index."""
        return len(self.chunk_ids)

    def validate_index_consistency(self) -> tuple[bool, list[str]]:
        """Validate consistency between FAISS index, chunk_ids, and metadata.

        This method checks for:
        1. FAISS index size matches chunk_ids list length
        2. All chunk_ids have corresponding metadata entries
        3. All metadata entries have valid index_ids
        4. No orphaned vectors in FAISS

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check if index exists
        if self.index is None:
            if len(self.chunk_ids) > 0:
                issues.append(
                    f"FAISS index is None but chunk_ids list has {len(self.chunk_ids)} entries"
                )
            if len(self.metadata_store) > 0:
                issues.append(
                    f"FAISS index is None but metadata has {len(self.metadata_store)} entries"
                )
            return len(issues) == 0, issues

        # Check 1: FAISS index size matches chunk_ids length
        faiss_size = self.ntotal
        chunk_ids_size = len(self.chunk_ids)
        if faiss_size != chunk_ids_size:
            issues.append(
                f"FAISS index size ({faiss_size}) != chunk_ids length ({chunk_ids_size})"
            )

        # Check 2: All chunk_ids have metadata entries
        missing_metadata = []
        for i, chunk_id in enumerate(self.chunk_ids):
            metadata_entry = self.metadata_store.get(chunk_id)
            if not metadata_entry:
                missing_metadata.append(f"{chunk_id} (position {i})")
            elif "index_id" in metadata_entry:
                # Check 3: Metadata index_id is valid
                index_id = metadata_entry["index_id"]
                if index_id != i:
                    issues.append(
                        f"Chunk {chunk_id} has index_id {index_id} but is at position {i}"
                    )
                if index_id >= faiss_size:
                    issues.append(
                        f"Chunk {chunk_id} has index_id {index_id} >= FAISS size {faiss_size}"
                    )

        if missing_metadata:
            issues.append(
                f"Missing metadata for {len(missing_metadata)} chunks: "
                f"{', '.join(missing_metadata[:5])}"
                + (
                    f" ... and {len(missing_metadata) - 5} more"
                    if len(missing_metadata) > 5
                    else ""
                )
            )

        # Check 4: Metadata database size consistency
        metadata_size = len(self.metadata_store)
        if metadata_size != chunk_ids_size:
            issues.append(
                f"Metadata database size ({metadata_size}) != chunk_ids length ({chunk_ids_size})"
            )

        is_valid = len(issues) == 0

        if is_valid:
            self._logger.info(
                f"Index consistency validated: {faiss_size} vectors, "
                f"{chunk_ids_size} chunk IDs, {metadata_size} metadata entries"
            )
        else:
            self._logger.warning(
                f"Index consistency validation failed with {len(issues)} issues"
            )
            for issue in issues:
                self._logger.warning(f"  - {issue}")

        return is_valid, issues

    def clear_index(self) -> None:
        """Clear the entire index and metadata."""
        # Close metadata store - do NOT reopen yet
        if self._metadata_store is not None:
            self._metadata_store.close()
            self._metadata_store = None

        # Clear BatchOperations reference to prevent lingering file handles (Windows)
        if hasattr(self, "_batch_ops") and self._batch_ops is not None:
            self._batch_ops._metadata_store = None

        # Clear FAISS index (includes GPU cleanup if needed)
        self._faiss_index.clear()

        # Force garbage collection to release file handles (Windows)
        import gc

        gc.collect()

        # Remove additional files - NOW safe because store is closed
        for file_path in [self.metadata_path, self.stats_path]:
            if file_path.exists():
                file_path.unlink()

        # Clear call graph via integration layer
        self._graph.clear()

        # Reinitialize metadata store AFTER deletion
        self._metadata_store = MetadataStore(self.metadata_path)

        self._logger.info("Index cleared")

    def check_memory_requirements(
        self, num_new_vectors: int, dimension: int
    ) -> dict[str, Any]:
        """Check if there's enough memory for adding new vectors.

        Args:
            num_new_vectors: Number of vectors to be added
            dimension: Dimension of vectors

        Returns:
            Dictionary with memory check results
        """
        # Delegate to FaissVectorIndex
        return self._faiss_index.check_memory_requirements(num_new_vectors, dimension)

    def get_memory_status(self) -> dict[str, Any]:
        """Get current memory usage status.

        Returns:
            Dictionary with memory status
        """
        # Delegate to FaissVectorIndex
        status = self._faiss_index.get_memory_status()

        # Add backward compatibility fields
        status["current_index_size"] = status.get("index_vectors", 0)
        status["is_gpu_enabled"] = status.get("on_gpu", False)
        status["gpu_available"] = FaissVectorIndex.gpu_is_available()

        return status

    def __enter__(self) -> "CodeIndexManager":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Context manager exit - cleanup resources."""
        if self._metadata_store is not None:
            self._metadata_store.close()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, "_metadata_store") and self._metadata_store is not None:
            self._metadata_store.close()
