"""Vector index management with FAISS and metadata storage."""

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import psutil

try:
    import faiss
except ImportError:
    faiss = None

try:
    from sqlitedict import SqliteDict
except ImportError:
    SqliteDict = None

try:
    import torch
except ImportError:
    torch = None

from embeddings.embedder import EmbeddingResult
from search.filters import matches_directory_filter

# Import graph storage for call graph
try:
    from graph.graph_storage import CodeGraphStorage

    GRAPH_STORAGE_AVAILABLE = True
except ImportError:
    GRAPH_STORAGE_AVAILABLE = False
    CodeGraphStorage = None


def get_available_memory() -> Dict[str, int]:
    """Get available system and GPU memory in bytes."""
    memory_info = {
        "system_total": psutil.virtual_memory().total,
        "system_available": psutil.virtual_memory().available,
        "gpu_total": 0,
        "gpu_available": 0,
    }

    # Get GPU memory if CUDA available
    if torch and torch.cuda.is_available():
        try:
            gpu_props = torch.cuda.get_device_properties(0)
            memory_info["gpu_total"] = gpu_props.total_memory
            memory_info["gpu_available"] = (
                gpu_props.total_memory - torch.cuda.memory_allocated(0)
            )
        except Exception:
            pass

    return memory_info


def estimate_index_memory_usage(
    num_vectors: int, dimension: int, index_type: str = "flat"
) -> Dict[str, int]:
    """Estimate memory usage for FAISS index in bytes."""
    # Base vector storage (float32 = 4 bytes per element)
    vector_memory = num_vectors * dimension * 4

    # FAISS overhead depends on index type
    if index_type.lower() == "flat":
        # Flat index: minimal overhead
        overhead = vector_memory * 0.1  # ~10% overhead
    else:
        # IVF/other indexes: more overhead for centroids, inverted lists
        overhead = vector_memory * 0.3  # ~30% overhead

    total_memory = int(vector_memory + overhead)

    return {
        "vectors": int(vector_memory),
        "overhead": int(overhead),
        "total": total_memory,
    }


class CodeIndexManager:
    """Manages FAISS vector index and metadata storage for code chunks."""

    def __init__(self, storage_dir: str, embedder=None, project_id: str = None):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # File paths
        self.index_path = self.storage_dir / "code.index"
        self.metadata_path = self.storage_dir / "metadata.db"
        self.chunk_id_path = self.storage_dir / "chunk_ids.pkl"
        self.stats_path = self.storage_dir / "stats.json"

        # Initialize components
        self._index = None
        self._metadata_db = None
        self._chunk_ids = []
        self._logger = logging.getLogger(__name__)
        self._logger.info(
            f"[INIT] CodeIndexManager created: storage_dir={storage_dir}, project_id={project_id}"
        )
        self._on_gpu = False
        self.embedder = embedder  # Optional embedder for dimension validation

        # Initialize call graph storage (Phase 1)
        self.graph_storage = None
        if GRAPH_STORAGE_AVAILABLE and project_id:
            try:
                # Store graph in same directory as vector index
                graph_dir = self.storage_dir.parent
                self.graph_storage = CodeGraphStorage(
                    project_id=project_id, storage_dir=graph_dir
                )
                self._logger.info(
                    f"Call graph storage initialized for project: {project_id}"
                )
            except Exception as e:
                self._logger.warning(f"Failed to initialize graph storage: {e}")

        # Check dependencies
        self._check_dependencies()

    def _check_dependencies(self):
        """Check if required dependencies are available."""
        if faiss is None:
            raise ImportError(
                "faiss-cpu not found. Install with: pip install faiss-cpu"
            )

        if SqliteDict is None:
            raise ImportError(
                "sqlitedict not found. Install with: pip install sqlitedict"
            )

    @staticmethod
    def normalize_chunk_id(chunk_id: str) -> str:
        """Normalize chunk_id path separators to forward slashes.

                Converts chunk_id to cross-platform compatible format with forward slashes.
                Handles Windows backslashes and ensures consistent path format.

                Args:
                    chunk_id: Chunk ID in format "file:lines:type:name"

                Returns:
                    Normalized chunk_id with forward slashes

                Example:
                    >>> normalize_chunk_id("search
        eranker.py:36-137:method:rerank")
                    "search/reranker.py:36-137:method:rerank"
        """
        # Split by chunk_id structure (file:lines:type:name)
        parts = chunk_id.split(":")
        if len(parts) >= 4:
            # First part is the file path - normalize it
            file_path = parts[0].replace("\\", "/")
            # Reconstruct chunk_id
            return f"{file_path}:{':'.join(parts[1:])}"
        # Fallback: just normalize backslashes
        return chunk_id.replace("\\", "/")

    @staticmethod
    def get_chunk_id_variants(chunk_id: str) -> list:
        """Get all possible chunk_id variants for robust lookup.

        Returns list of chunk_id variants to try during lookup, handling:
        - Original format (exact match)
        - Un-double-escaped (fixes MCP JSON transport bug on Windows)
        - Forward slash normalized (cross-platform)
        - Backslash normalized (Windows native)

        Args:
            chunk_id: Original chunk ID to generate variants for

        Returns:
            List of chunk_id variants to try in lookup order
        """
        variants = [
            chunk_id,  # Original (exact match)
            chunk_id.replace("\\\\", "\\"),  # Un-double-escape (MCP bug fix)
            chunk_id.replace("\\", "/"),  # Normalize to forward slash
            chunk_id.replace("/", "\\"),  # Try backslash variant
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)

        return unique_variants

    @property
    def index(self):
        """Lazy loading of FAISS index."""
        if self._index is None:
            self._load_index()
        return self._index

    @property
    def metadata_db(self):
        """Lazy loading of metadata database."""
        if self._metadata_db is None:
            self._metadata_db = SqliteDict(
                str(self.metadata_path), autocommit=False, journal_mode="WAL"
            )
        return self._metadata_db

    def _load_index(self):
        """Load existing FAISS index or create new one."""
        if self.index_path.exists():
            self._logger.info(f"Loading existing index from {self.index_path}")
            self._index = faiss.read_index(str(self.index_path))

            # Validate index dimension matches current model (if embedder provided)
            if self.embedder is not None:
                try:
                    stored_dim = self._index.d
                    current_model_dim = self.embedder.get_model_info()[
                        "embedding_dimension"
                    ]

                    if stored_dim != current_model_dim:
                        self._logger.warning(
                            f"Index dimension mismatch detected!\n"
                            f"  Stored index: {stored_dim} dimensions\n"
                            f"  Current model: {current_model_dim} dimensions\n"
                            f"  Model: {self.embedder.model_name}\n"
                            f"This index was created with a different embedding model.\n"
                            f"Creating new index for current model..."
                        )
                        # Clear the incompatible index
                        self._index = None
                        self._chunk_ids = []
                        return  # Will create new index when embeddings are added
                except Exception as e:
                    self._logger.debug(f"Could not validate index dimension: {e}")

            # If GPU support is available, optionally move to GPU for runtime speed
            self._maybe_move_index_to_gpu()

            # Load chunk IDs
            if self.chunk_id_path.exists():
                with open(self.chunk_id_path, "rb") as f:
                    self._chunk_ids = pickle.load(f)
        else:
            self._logger.info("Creating new index")
            # Create a new index - we'll initialize it when we get the first embedding
            self._index = None
            self._chunk_ids = []

    def create_index(self, embedding_dimension: int, index_type: str = "flat"):
        """Create a new FAISS index."""
        if index_type == "flat":
            # Simple flat index for exact search
            self._index = faiss.IndexFlatIP(
                embedding_dimension
            )  # Inner product (cosine similarity)
        elif index_type == "ivf":
            # IVF index for faster approximate search on large datasets
            quantizer = faiss.IndexFlatIP(embedding_dimension)
            n_centroids = min(
                100, max(10, embedding_dimension // 8)
            )  # Adaptive number of centroids
            self._index = faiss.IndexIVFFlat(
                quantizer, embedding_dimension, n_centroids
            )
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        self._logger.info(
            f"Created {index_type} index with dimension {embedding_dimension}"
        )
        self._maybe_move_index_to_gpu()

    def add_embeddings(self, embedding_results: List[EmbeddingResult]) -> None:
        """Add embeddings to the index and metadata to the database."""
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

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Train IVF index if needed
        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            self._logger.info("Training IVF index...")
            self._index.train(embeddings)

        # Add to FAISS index
        start_id = len(self._chunk_ids)
        self._index.add(embeddings)

        # Store metadata and update chunk IDs
        for i, result in enumerate(embedding_results):
            chunk_id = result.chunk_id
            self._chunk_ids.append(chunk_id)

            # Store in metadata database
            self.metadata_db[chunk_id] = {
                "index_id": start_id + i,
                "metadata": result.metadata,
            }

            # Populate call graph
            if self.graph_storage is not None:
                self._add_to_graph(chunk_id, result.metadata)
                self._logger.debug(
                    f"Graph storage check: chunk_id={chunk_id}, type={result.metadata.get('chunk_type')}, graph_nodes={len(self.graph_storage)}"
                )

        self._logger.info(f"Added {len(embedding_results)} embeddings to index")

        # Commit metadata in a single transaction for performance
        try:
            self.metadata_db.commit()
        except Exception:
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

    def _gpu_is_available(self) -> bool:
        """Check if GPU FAISS support is available and GPUs are present."""
        try:
            if not hasattr(faiss, "StandardGpuResources"):
                return False
            get_num_gpus = getattr(faiss, "get_num_gpus", None)
            if get_num_gpus is None:
                return False
            return get_num_gpus() > 0
        except Exception:
            return False

    def _maybe_move_index_to_gpu(self) -> None:
        """Move the current index to GPU if supported. No-op if already on GPU or unsupported."""
        if self.index is None or self._on_gpu:
            return
        if not self._gpu_is_available():
            return
        try:
            # Move index to all GPUs for faster add/search
            self._index = faiss.index_cpu_to_all_gpus(self._index)
            self._on_gpu = True
            self._logger.info("FAISS index moved to GPU(s)")
        except Exception as e:
            self._logger.warning(
                f"Failed to move FAISS index to GPU, continuing on CPU: {e}"
            )

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar code chunks."""
        import logging

        logger = logging.getLogger(__name__)

        logger.info(f"Index manager search called with k={k}, filters={filters}")

        # Use property to trigger lazy loading
        index = self.index
        if index is None or index.ntotal == 0:
            logger.warning(
                f"Index is empty or None. Index: {index}, ntotal: {index.ntotal if index else 'N/A'}"
            )
            return []

        logger.info(f"Index has {index.ntotal} total vectors")

        # Normalize query embedding
        query_embedding = query_embedding.reshape(1, -1)
        faiss.normalize_L2(query_embedding)

        # Search in FAISS index
        search_k = min(k * 3, index.ntotal)  # Get more results for filtering
        similarities, indices = index.search(query_embedding, search_k)

        results = []
        for _i, (similarity, index_id) in enumerate(
            zip(similarities[0], indices[0], strict=False)
        ):
            if index_id == -1:  # No more results
                break

            chunk_id = self._chunk_ids[index_id]
            metadata_entry = self.metadata_db.get(chunk_id)

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
        self, metadata: Dict[str, Any], filters: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches the provided filters."""
        for key, value in filters.items():
            if key == "include_dirs" or key == "exclude_dirs":
                # Directory filtering - handled together
                include_dirs = filters.get("include_dirs")
                exclude_dirs = filters.get("exclude_dirs")
                relative_path = metadata.get("relative_path", "")
                if not matches_directory_filter(
                    relative_path, include_dirs, exclude_dirs
                ):
                    return False
                # Skip further processing of these keys
                continue
            elif key == "file_pattern":
                # Pattern matching for file paths
                if not any(
                    pattern in metadata.get("relative_path", "") for pattern in value
                ):
                    return False
            elif key == "chunk_type":
                # Exact match for chunk type
                if metadata.get("chunk_type") != value:
                    return False
            elif key == "tags":
                # Tag intersection
                chunk_tags = set(metadata.get("tags", []))
                required_tags = set(value if isinstance(value, list) else [value])
                if not required_tags.intersection(chunk_tags):
                    return False
            elif key == "folder_structure":
                # Check if any of the required folders are in the path
                chunk_folders = set(metadata.get("folder_structure", []))
                required_folders = set(value if isinstance(value, list) else [value])
                if not required_folders.intersection(chunk_folders):
                    return False
            elif key in metadata:
                # Direct metadata comparison
                if metadata[key] != value:
                    return False

        return True

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve chunk metadata by ID with path normalization.

        Handles Windows backslash escaping issues in MCP transport by trying
        multiple path separator variants.

        Args:
            chunk_id: Chunk ID to lookup

        Returns:
            Chunk metadata dict if found, None otherwise
        """
        # Try multiple path separator variants for robust lookup
        variants = self.get_chunk_id_variants(chunk_id)

        for variant in variants:
            metadata_entry = self.metadata_db.get(variant)
            if metadata_entry:
                if variant != chunk_id:
                    self._logger.debug(
                        f"Found chunk with variant: {variant} (original: {chunk_id})"
                    )
                return metadata_entry["metadata"]

        self._logger.warning(
            f"Chunk not found for ID (tried {len(variants)} variants): {chunk_id}"
        )
        return None

    def get_similar_chunks(
        self, chunk_id: str, k: int = 5
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Find chunks similar to a given chunk."""
        # Try all path variants to handle Windows/Unix differences
        metadata_entry = None
        for variant in self.get_chunk_id_variants(chunk_id):
            metadata_entry = self.metadata_db.get(variant)
            if metadata_entry:
                chunk_id = variant  # Use the variant that worked
                break

        if not metadata_entry:
            return []

        index_id = metadata_entry["index_id"]
        if self.index is None or index_id >= self.index.ntotal:
            return []

        # Get the embedding for this chunk
        embedding = self._index.reconstruct(index_id)

        # Search for similar chunks (excluding the original)
        results = self.search(embedding, k + 1)

        # Filter out the original chunk
        return [(cid, sim, meta) for cid, sim, meta in results if cid != chunk_id][:k]

    def get_similar_chunks_batched(
        self, chunk_ids: List[str], k: int = 5
    ) -> Dict[str, List[Tuple[str, float, Dict[str, Any]]]]:
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
        import logging

        logger = logging.getLogger(__name__)

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

            for variant in self.get_chunk_id_variants(original_chunk_id):
                metadata_entry = self.metadata_db.get(variant)
                if metadata_entry:
                    resolved_chunk_id = variant  # Use the variant that worked
                    break

            if not metadata_entry:
                continue

            index_id = metadata_entry["index_id"]
            if index_id >= index.ntotal:
                continue

            # Get the embedding for this chunk
            embedding = self._index.reconstruct(index_id)
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

                chunk_id = self._chunk_ids[index_id]

                # Skip the original chunk
                if chunk_id == query_chunk_id:
                    continue

                metadata_entry = self.metadata_db.get(chunk_id)
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

        logger.debug(
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
        for chunk_id in self._chunk_ids:
            metadata_entry = self.metadata_db.get(chunk_id)
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
            del self.metadata_db[chunk_id]

        # Note: We don't remove from FAISS index directly as it's complex
        # Instead, we'll rebuild the index periodically or on demand

        self._logger.info(f"Removed {len(chunks_to_remove)} chunks from {file_path}")

        # Commit removals in batch
        try:
            self.metadata_db.commit()
        except Exception:
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

        # Force lazy loading of index and chunk_ids before accessing _chunk_ids
        _ = self.index

        chunks_to_remove_ids = set()
        chunks_to_remove_positions = []

        # Single pass to identify chunks to remove
        for position, chunk_id in enumerate(self._chunk_ids):
            metadata_entry = self.metadata_db.get(chunk_id)
            if not metadata_entry:
                continue

            metadata = metadata_entry["metadata"]

            # Check if this chunk belongs to any of the files
            chunk_file = metadata.get("file_path") or metadata.get("relative_path")
            if not chunk_file:
                continue

            # Check if chunk matches any file in the set
            for file_path in file_paths:
                if file_path in chunk_file or chunk_file in file_path:
                    # Check project name if provided
                    if project_name and metadata.get("project_name") != project_name:
                        continue
                    chunks_to_remove_ids.add(chunk_id)
                    chunks_to_remove_positions.append(position)
                    break  # Found match, no need to check other files

        if not chunks_to_remove_ids:
            self._logger.info("No chunks found to remove")
            return 0

        self._logger.info(
            f"Removing {len(chunks_to_remove_ids)} chunks from {len(file_paths)} files"
        )

        try:
            # Rebuild FAISS index without removed chunks
            if self.index is not None and self.index.ntotal > 0:
                # Get positions to keep (all except those being removed)
                positions_to_remove_set = set(chunks_to_remove_positions)
                positions_to_keep = [
                    i
                    for i in range(len(self._chunk_ids))
                    if i not in positions_to_remove_set
                ]

                if positions_to_keep:
                    # Reconstruct embeddings for chunks we want to keep
                    embeddings_to_keep = []
                    for pos in positions_to_keep:
                        try:
                            embedding = self._index.reconstruct(int(pos))
                            embeddings_to_keep.append(embedding)
                        except Exception as e:
                            self._logger.warning(
                                f"Failed to reconstruct embedding at position {pos}: {e}"
                            )
                            continue

                    if embeddings_to_keep:
                        # Create new index with kept embeddings
                        embeddings_array = np.array(
                            embeddings_to_keep, dtype=np.float32
                        )

                        # Get embedding dimension
                        embedding_dim = embeddings_array.shape[1]

                        # Determine index type from current index
                        if hasattr(self._index, "metric_type"):
                            # Preserve metric type
                            pass

                        # Check if we were on GPU
                        was_on_gpu = self._on_gpu

                        # Create new CPU index
                        new_index = faiss.IndexFlatIP(embedding_dim)

                        # Normalize embeddings (we use cosine similarity)
                        faiss.normalize_L2(embeddings_array)

                        # Add kept embeddings to new index
                        new_index.add(embeddings_array)

                        # Replace old index
                        if self._on_gpu:
                            # Clear GPU memory from old index
                            del self._index
                            if torch and torch.cuda.is_available():
                                torch.cuda.empty_cache()

                        self._index = new_index
                        self._on_gpu = False

                        # Move to GPU if it was on GPU before
                        if was_on_gpu:
                            self._maybe_move_index_to_gpu()

                        self._logger.info(
                            f"Rebuilt FAISS index: {self._index.ntotal} vectors "
                            f"(removed {len(chunks_to_remove_ids)})"
                        )
                    else:
                        # No embeddings to keep, clear the index
                        self._logger.warning(
                            "No valid embeddings to keep, clearing index"
                        )
                        self.clear_index()
                        return len(chunks_to_remove_ids)
                else:
                    # All chunks removed, clear the index
                    self._logger.info("All chunks removed, clearing index")
                    self.clear_index()
                    return len(chunks_to_remove_ids)

            # Update chunk_ids list (remove chunks at removed positions)
            new_chunk_ids = [
                chunk_id
                for i, chunk_id in enumerate(self._chunk_ids)
                if i not in set(chunks_to_remove_positions)
            ]
            self._chunk_ids = new_chunk_ids

            # Remove chunks from metadata and update index_ids
            for chunk_id in chunks_to_remove_ids:
                if chunk_id in self.metadata_db:
                    del self.metadata_db[chunk_id]

            # Update metadata with new index positions
            for new_pos, chunk_id in enumerate(self._chunk_ids):
                if chunk_id in self.metadata_db:
                    metadata_entry = self.metadata_db[chunk_id]
                    metadata_entry["index_id"] = new_pos
                    self.metadata_db[chunk_id] = metadata_entry

            # Commit all changes
            try:
                self.metadata_db.commit()
            except Exception as e:
                self._logger.warning(f"Failed to commit metadata changes: {e}")

            self._logger.info(
                f"Successfully batch removed {len(chunks_to_remove_ids)} chunks from {len(file_paths)} files"
            )

            return len(chunks_to_remove_ids)

        except Exception as e:
            self._logger.error(f"Failed to batch remove chunks: {e}")
            import traceback

            self._logger.error(traceback.format_exc())
            # Don't leave index in corrupted state - if rebuild fails, clear it
            self._logger.warning(
                "Batch removal failed, clearing index to prevent corruption"
            )
            self.clear_index()
            raise

    def save_index(self):
        """Save the FAISS index and chunk IDs to disk."""
        if self.index is not None:
            try:
                index_to_write = self._index
                # If on GPU, convert to CPU before saving
                if self._on_gpu and hasattr(faiss, "index_gpu_to_cpu"):
                    index_to_write = faiss.index_gpu_to_cpu(self._index)
                faiss.write_index(index_to_write, str(self.index_path))
                self._logger.info(f"Saved index to {self.index_path}")
            except Exception as e:
                self._logger.warning(
                    f"Failed to save GPU index directly, attempting CPU fallback: {e}"
                )
                try:
                    cpu_index = faiss.index_gpu_to_cpu(self._index)
                    faiss.write_index(cpu_index, str(self.index_path))
                    self._logger.info(
                        f"Saved index to {self.index_path} (CPU fallback)"
                    )
                except Exception as e2:
                    self._logger.error(f"Failed to save FAISS index: {e2}")

        # Save chunk IDs
        with open(self.chunk_id_path, "wb") as f:
            pickle.dump(self._chunk_ids, f)

        # Save call graph if populated (Phase 1)
        graph_status = "not None" if self.graph_storage is not None else "None"
        graph_nodes = len(self.graph_storage) if self.graph_storage else 0
        self._logger.info(
            f"[save_index] Graph storage check: graph_storage={graph_status}, nodes={graph_nodes}"
        )
        if self.graph_storage is not None and len(self.graph_storage) > 0:
            try:
                self._logger.info(
                    f"[save_index] Saving call graph with {len(self.graph_storage)} nodes to {self.graph_storage.graph_path}"
                )
                self.graph_storage.save()
                self._logger.info("[save_index] Successfully saved call graph")
            except Exception as e:
                self._logger.warning(f"[save_index] Failed to save call graph: {e}")
        else:
            skip_reason = "None" if self.graph_storage is None else "empty (0 nodes)"
            self._logger.info(
                f"[save_index] Skipping graph save: graph_storage is {skip_reason}"
            )

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
        # Index is already loaded in __init__, so just check if it exists
        if self.index is not None and len(self._chunk_ids) > 0:
            return True

        # Try to reload if index file exists but index is None
        if self.index_path.exists():
            try:
                self._load_index()
                return self._index is not None
            except Exception as e:
                self._logger.error(f"Failed to reload index: {e}")
                return False

        return False

    def _add_to_graph(self, chunk_id: str, metadata: Dict[str, Any]) -> None:
        """Add chunk to call graph storage.

        Args:
            chunk_id: Unique chunk identifier
            metadata: Chunk metadata including calls and relationships
        """
        if self.graph_storage is None:
            self._logger.debug(
                f"_add_to_graph: graph_storage is None, skipping {chunk_id}"
            )
            return

        try:
            # Phase 3: Process all semantic chunk types for relationships
            # - Functions/methods: call relationships (Phase 1)
            # - Classes/structs/interfaces/etc: inheritance, type usage (Phase 3)
            chunk_type = metadata.get("chunk_type")
            chunk_name = metadata.get("name")
            relationships = metadata.get("relationships", [])

            self._logger.debug(
                f"_add_to_graph called: chunk_id={chunk_id}, type={chunk_type}, name={chunk_name}"
            )

            # Semantic chunk types that can have relationships
            # Based on Codanna's approach: index ALL semantic symbols
            SEMANTIC_TYPES = (
                "function",
                "method",
                "class",
                "struct",
                "interface",
                "enum",
                "trait",
                "impl",
                "constant",
                "variable",
            )

            if chunk_type not in SEMANTIC_TYPES:
                # Allow through if it has Phase 3 relationships (edge case)
                if not relationships:
                    self._logger.debug(
                        f"Skipping non-semantic chunk: {chunk_id} (type={chunk_type})"
                    )
                    return
                else:
                    self._logger.debug(
                        f"Processing non-semantic chunk with relationships: {chunk_id} (type={chunk_type}, rels={len(relationships)})"
                    )

            self._logger.debug(f"Adding {chunk_type} '{metadata.get('name')}' to graph")

            # Add node for this chunk
            self.graph_storage.add_node(
                chunk_id=chunk_id,
                name=metadata.get("name", "unknown"),
                chunk_type=chunk_type,
                file_path=metadata.get("file_path", ""),
                language=metadata.get("language", "python"),
            )

            # Phase 1: Add legacy call edges (backwards compatibility)
            calls = metadata.get("calls", [])
            for call_dict in calls:
                self.graph_storage.add_call_edge(
                    caller_id=chunk_id,
                    callee_name=call_dict.get("callee_name", "unknown"),
                    line_number=call_dict.get("line_number", 0),
                    is_method_call=call_dict.get("is_method_call", False),
                )

            # Phase 3: Add all relationship edges
            relationships = metadata.get("relationships", [])
            if relationships:
                self._logger.debug(
                    f"[PHASE3] Processing {len(relationships)} relationship edges for {chunk_id}"
                )
                for rel_dict in relationships:
                    try:
                        # Import RelationshipEdge to reconstruct from dict
                        from graph.relationship_types import (
                            RelationshipEdge,
                            RelationshipType,
                        )

                        # Reconstruct RelationshipEdge from dict
                        edge = RelationshipEdge(
                            source_id=rel_dict.get("source_id", chunk_id),
                            target_name=rel_dict.get("target_name", "unknown"),
                            relationship_type=RelationshipType(
                                rel_dict.get("relationship_type", "calls")
                            ),
                            line_number=rel_dict.get("line_number", 0),
                            confidence=rel_dict.get("confidence", 1.0),
                            metadata=rel_dict.get("metadata", {}),
                        )

                        # Add to graph storage
                        self.graph_storage.add_relationship_edge(edge)

                    except Exception as e:
                        self._logger.warning(
                            f"Failed to add relationship edge from {chunk_id}: {e}"
                        )

        except Exception as e:
            self._logger.warning(f"Failed to add {chunk_id} to graph: {e}")

    def _update_stats(self):
        """Update index statistics."""
        stats = {
            "total_chunks": len(self._chunk_ids),
            "index_size": self._index.ntotal if self._index else 0,
            "embedding_dimension": self._index.d if self._index else 0,
            "index_type": type(self._index).__name__ if self._index else "None",
        }

        # Add file and folder statistics
        file_counts = {}
        folder_counts = {}
        chunk_type_counts = {}
        tag_counts = {}

        for chunk_id in self._chunk_ids:
            metadata_entry = self.metadata_db.get(chunk_id)
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

    def get_stats(self) -> Dict[str, Any]:
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
        return len(self._chunk_ids)

    def validate_index_consistency(self) -> Tuple[bool, List[str]]:
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
            if len(self._chunk_ids) > 0:
                issues.append(
                    f"FAISS index is None but chunk_ids list has {len(self._chunk_ids)} entries"
                )
            if len(self.metadata_db) > 0:
                issues.append(
                    f"FAISS index is None but metadata has {len(self.metadata_db)} entries"
                )
            return len(issues) == 0, issues

        # Check 1: FAISS index size matches chunk_ids length
        faiss_size = self._index.ntotal
        chunk_ids_size = len(self._chunk_ids)
        if faiss_size != chunk_ids_size:
            issues.append(
                f"FAISS index size ({faiss_size}) != chunk_ids length ({chunk_ids_size})"
            )

        # Check 2: All chunk_ids have metadata entries
        missing_metadata = []
        for i, chunk_id in enumerate(self._chunk_ids):
            metadata_entry = self.metadata_db.get(chunk_id)
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
        metadata_size = len(self.metadata_db)
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

    def clear_index(self):
        """Clear the entire index and metadata."""
        # Close database connection
        if self._metadata_db is not None:
            self._metadata_db.close()
            self._metadata_db = None

        # Remove files
        for file_path in [
            self.index_path,
            self.metadata_path,
            self.chunk_id_path,
            self.stats_path,
        ]:
            if file_path.exists():
                file_path.unlink()

        # Reset in-memory state
        self._index = None
        self._chunk_ids = []

        # Clear call graph
        if self.graph_storage is not None:
            try:
                self.graph_storage.clear()
                self._logger.info("Call graph cleared")
            except Exception as e:
                self._logger.warning(f"Failed to clear call graph: {e}")

        self._logger.info("Index cleared")

    def check_memory_requirements(
        self, num_new_vectors: int, dimension: int
    ) -> Dict[str, Any]:
        """Check if there's enough memory for adding new vectors."""
        # Get current memory status
        available = get_available_memory()

        # Estimate memory needed for new vectors
        estimate_index_memory_usage(num_new_vectors, dimension)

        # Check current index size
        current_size = self.get_index_size()
        total_vectors_after = current_size + num_new_vectors

        # Estimate total memory after adding vectors
        total_estimated = estimate_index_memory_usage(total_vectors_after, dimension)

        # Determine if we should use GPU or CPU
        prefer_gpu = self._gpu_is_available()
        target_memory = (
            available["gpu_available"] if prefer_gpu else available["system_available"]
        )

        # Safety margin: require 20% more available memory than estimated
        safety_factor = 1.2
        required_memory = int(total_estimated["total"] * safety_factor)

        memory_check = {
            "available_memory": available,
            "estimated_usage": total_estimated,
            "required_memory": required_memory,
            "current_vectors": current_size,
            "new_vectors": num_new_vectors,
            "total_vectors_after": total_vectors_after,
            "prefer_gpu": prefer_gpu,
            "sufficient_memory": target_memory >= required_memory,
            "memory_utilization": (
                required_memory / target_memory if target_memory > 0 else float("inf")
            ),
        }

        # Log warning if memory is tight
        if not memory_check["sufficient_memory"]:
            self._logger.warning(
                f"Insufficient memory: need {required_memory // (1024**2):.1f}MB, "
                f"have {target_memory // (1024**2):.1f}MB "
                f"({'GPU' if prefer_gpu else 'CPU'})"
            )
        elif memory_check["memory_utilization"] > 0.8:
            self._logger.warning(
                f"High memory utilization: {memory_check['memory_utilization']:.1%} "
                f"of available {'GPU' if prefer_gpu else 'CPU'} memory"
            )

        return memory_check

    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory usage status."""
        available = get_available_memory()
        current_size = self.get_index_size()

        status = {
            "available_memory": available,
            "current_index_size": current_size,
            "is_gpu_enabled": self._on_gpu,
            "gpu_available": self._gpu_is_available(),
        }

        # Estimate current index memory usage if we have vectors
        if current_size > 0 and self._index is not None:
            # Estimate dimension from index if available
            try:
                dimension = (
                    self._index.d if hasattr(self._index, "d") else 768
                )  # Default dimension
                estimated = estimate_index_memory_usage(current_size, dimension)
                status["estimated_index_memory"] = estimated
            except Exception as e:
                self._logger.debug(f"Could not estimate index memory usage: {e}")

        return status

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        if self._metadata_db is not None:
            self._metadata_db.close()
            self._metadata_db = None
        return False  # Don't suppress exceptions

    def __del__(self):
        """Cleanup when object is destroyed."""
        if hasattr(self, "_metadata_db") and self._metadata_db is not None:
            self._metadata_db.close()
