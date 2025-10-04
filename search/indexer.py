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

    def __init__(self, storage_dir: str, embedder=None):
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
        self._on_gpu = False
        self.embedder = embedder  # Optional embedder for dimension validation

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
        if self._index is None:
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

        self._logger.info(f"Added {len(embedding_results)} embeddings to index")

        # Commit metadata in a single transaction for performance
        try:
            self.metadata_db.commit()
        except Exception:
            # If commit is unavailable for some reason, continue without failing
            pass

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
        if self._index is None or self._on_gpu:
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
            if key == "file_pattern":
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
        """Retrieve chunk metadata by ID."""
        metadata_entry = self.metadata_db.get(chunk_id)
        return metadata_entry["metadata"] if metadata_entry else None

    def get_similar_chunks(
        self, chunk_id: str, k: int = 5
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Find chunks similar to a given chunk."""
        metadata_entry = self.metadata_db.get(chunk_id)
        if not metadata_entry:
            return []

        index_id = metadata_entry["index_id"]
        if self._index is None or index_id >= self._index.ntotal:
            return []

        # Get the embedding for this chunk
        embedding = self._index.reconstruct(index_id)

        # Search for similar chunks (excluding the original)
        results = self.search(embedding, k + 1)

        # Filter out the original chunk
        return [(cid, sim, meta) for cid, sim, meta in results if cid != chunk_id][:k]

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

    def save_index(self):
        """Save the FAISS index and chunk IDs to disk."""
        if self._index is not None:
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
        if self._index is not None and len(self._chunk_ids) > 0:
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
        if self._metadata_db is not None:
            self._metadata_db.close()
