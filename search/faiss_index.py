"""FAISS vector index management.

This module provides a dedicated interface for managing FAISS vector indices
with support for saving, loading, searching, and dimension tracking.
"""

import logging
import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np
import psutil

from search.exceptions import IndexError as SearchIndexError


try:
    import faiss
except ImportError:
    faiss = None

try:
    import torch
except ImportError:
    torch = None


def get_available_memory() -> dict[str, int]:
    """Get available system and GPU memory in bytes.

    Returns:
        Dictionary with keys:
        - system_total: Total system RAM
        - system_available: Available system RAM
        - gpu_total: Total GPU VRAM (0 if no GPU)
        - gpu_available: Available GPU VRAM (0 if no GPU)
    """
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
        except RuntimeError:
            pass

    return memory_info


def estimate_index_memory_usage(
    num_vectors: int, dimension: int, index_type: str = "flat"
) -> dict[str, int]:
    """Estimate memory usage for FAISS index in bytes.

    Args:
        num_vectors: Number of vectors in the index
        dimension: Dimension of each vector
        index_type: Type of FAISS index ("flat" or "ivf")

    Returns:
        Dictionary with keys:
        - vectors: Memory for raw vectors
        - overhead: FAISS overhead
        - total: Total estimated memory
    """
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


class FaissVectorIndex:
    """Manages FAISS vector index operations.

    This class encapsulates all FAISS-specific logic including index creation,
    loading, saving, GPU management, and memory estimation. It provides a clean
    separation between vector storage and higher-level index management concerns.

    Attributes:
        index_path: Path to the FAISS index file
        chunk_id_path: Path to the chunk IDs pickle file
        _index: Underlying FAISS index instance
        _chunk_ids: List of chunk IDs corresponding to index positions
        _on_gpu: Whether the index is currently on GPU
        _logger: Logger instance

    Example:
        >>> index = FaissVectorIndex(Path("storage/code.index"))
        >>> index.create(768, "flat")
        >>> index.add(embeddings)
        >>> distances, indices = index.search(query, k=5)
        >>> index.save()
    """

    def __init__(self, index_path: Path, embedder=None):
        """Initialize FAISS vector index.

        Args:
            index_path: Path to FAISS index file
            embedder: Optional embedder for dimension validation
        """
        self.index_path = Path(index_path)
        self.chunk_id_path = self.index_path.parent / "chunk_ids.pkl"
        self.embedder = embedder

        self._index: Optional[Any] = None
        self._chunk_ids: list = []
        self._on_gpu: bool = False
        self._logger = logging.getLogger(__name__)

        # Memory-mapped vector storage (auto-enabled for >10K vectors)
        self._mmap_storage: Optional[Any] = None  # MmapVectorStorage
        self._mmap_path = (
            self.index_path.parent / f"{self.index_path.stem}_vectors.mmap"
        )

    @property
    def index(self) -> Optional[Any]:
        """Get the underlying FAISS index."""
        return self._index

    @property
    def ntotal(self) -> int:
        """Get the number of vectors in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal

    @property
    def dimension(self) -> Optional[int]:
        """Get the dimension of vectors in the index."""
        if self._index is None:
            return None
        return self._index.d

    @property
    def is_on_gpu(self) -> bool:
        """Check if the index is currently on GPU."""
        return self._on_gpu

    @property
    def chunk_ids(self) -> list:
        """Get the list of chunk IDs."""
        return self._chunk_ids

    def create(self, dimension: int, index_type: str = "flat") -> None:
        """Create a new FAISS index.

        Args:
            dimension: Embedding dimension
            index_type: Type of index to create ("flat" or "ivf")

        Raises:
            ValueError: If index_type is not supported
        """
        if faiss is None:
            raise SearchIndexError(
                "FAISS is not installed. Install with: pip install faiss-cpu"
            )

        if index_type == "flat":
            # Simple flat index for exact search
            self._index = faiss.IndexFlatIP(
                dimension
            )  # Inner product (cosine similarity)
        elif index_type == "ivf":
            # IVF index for faster approximate search on large datasets
            quantizer = faiss.IndexFlatIP(dimension)
            n_centroids = min(
                100, max(10, dimension // 8)
            )  # Adaptive number of centroids
            self._index = faiss.IndexIVFFlat(quantizer, dimension, n_centroids)
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        self._chunk_ids = []
        self._on_gpu = False
        self._logger.info(f"Created {index_type} index with dimension {dimension}")

        # Move to GPU if available
        self.move_to_gpu()

    def load(self) -> bool:
        """Load existing FAISS index from disk.

        Returns:
            True if index was loaded successfully, False otherwise
        """
        if not self.index_path.exists():
            self._logger.info("No existing index found")
            self._index = None
            self._chunk_ids = []
            return False

        try:
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
                        self._logger.error(
                            f"CRITICAL: Index dimension mismatch!\n"
                            f"  Stored index: {stored_dim} dimensions\n"
                            f"  Current embedder: {current_model_dim} dimensions\n"
                            f"  Embedder model: {self.embedder.model_name}\n"
                            f"  Index path: {self.index_path}\n"
                            f"This indicates the wrong index was loaded for this model.\n"
                            f"Clearing incompatible index to force reindex..."
                        )
                        # Clear the incompatible index
                        self._index = None
                        self._chunk_ids = []
                        return False
                except Exception as e:
                    self._logger.debug(f"Could not validate index dimension: {e}")

            # Move to GPU if available
            self.move_to_gpu()

            # Load chunk IDs
            if self.chunk_id_path.exists():
                with open(self.chunk_id_path, "rb") as f:
                    self._chunk_ids = pickle.load(f)
            else:
                self._chunk_ids = []

            # Load mmap storage if available (automatic when file exists)
            if self._mmap_path.exists():
                try:
                    from search.mmap_vectors import MmapVectorStorage

                    self._mmap_storage = MmapVectorStorage(
                        self._mmap_path, self._index.d
                    )
                    if not self._mmap_storage.load():
                        self._mmap_storage = None
                        self._logger.debug(
                            "Mmap vectors not available, using FAISS reconstruct"
                        )
                    else:
                        self._logger.info(
                            f"Loaded mmap storage: {self._mmap_storage.count} vectors "
                            f"from {self._mmap_path.name}"
                        )
                except Exception as e:
                    self._logger.debug(f"Could not load mmap storage: {e}")
                    self._mmap_storage = None

            return True

        except Exception as e:
            self._logger.error(f"Failed to load index: {e}")
            self._index = None
            self._chunk_ids = []
            return False

    def save(self) -> None:
        """Save the FAISS index and chunk IDs to disk."""
        if self._index is None:
            self._logger.warning("No index to save")
            return

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
                self._logger.info(f"Saved index to {self.index_path} (CPU fallback)")
            except Exception as e2:
                self._logger.error(f"Failed to save FAISS index: {e2}")
                raise

        # Save chunk IDs
        with open(self.chunk_id_path, "wb") as f:
            pickle.dump(self._chunk_ids, f)

        # Auto-threshold: Only use mmap for indices >10K vectors (performance benefit)
        # Fully automatic - no config needed
        MMAP_THRESHOLD = 10000
        if self._index is not None:
            vector_count = self._index.ntotal
            if vector_count >= MMAP_THRESHOLD:
                try:
                    from search.mmap_vectors import MmapVectorStorage

                    dimension = self._index.d
                    mmap_storage = MmapVectorStorage(self._mmap_path, dimension)

                    # Reconstruct all vectors
                    embeddings = np.array(
                        [self._index.reconstruct(i) for i in range(self._index.ntotal)]
                    )
                    mmap_storage.save(embeddings, self._chunk_ids)
                    self._logger.info(
                        f"Saved mmap storage: {self._index.ntotal} vectors to {self._mmap_path}"
                    )
                except Exception as e:
                    self._logger.warning(f"Failed to save mmap vectors: {e}")
            else:
                # Below threshold: delete mmap if it exists (from previous larger index)
                if self._mmap_path.exists():
                    self._mmap_path.unlink()
                    self._logger.info(
                        f"Deleted mmap file (below threshold): {vector_count} vectors < {MMAP_THRESHOLD}"
                    )
                else:
                    self._logger.info(
                        f"Skipping mmap storage: {vector_count} vectors < {MMAP_THRESHOLD} threshold "
                        f"(FAISS is faster at small scale)"
                    )

    def add(self, embeddings: np.ndarray, chunk_ids: list) -> None:
        """Add embeddings to the index.

        Args:
            embeddings: numpy array of shape (n_vectors, dimension)
            chunk_ids: List of chunk IDs corresponding to embeddings

        Raises:
            ValueError: If no index exists (call create() first)
            ValueError: If embedding dimension doesn't match index dimension
        """
        if self._index is None:
            raise ValueError("No index exists. Call create() first.")

        if len(embeddings) == 0:
            return

        # Dimension validation before FAISS operations
        if embeddings.shape[1] != self._index.d:
            raise ValueError(
                f"Embedding dimension mismatch: embeddings have {embeddings.shape[1]}d "
                f"but index expects {self._index.d}d. The index was likely created with "
                f"a different embedding model. Clear the index and re-index the project."
            )

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Train index if needed (for IVF indexes)
        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            self._index.train(embeddings)

        # Add to index
        self._index.add(embeddings)
        self._chunk_ids.extend(chunk_ids)

        self._logger.debug(f"Added {len(embeddings)} vectors to index")

    def search(self, query: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors.

        Args:
            query: Query embedding vector (1D or 2D array)
            k: Number of nearest neighbors to return

        Returns:
            Tuple of (distances, indices) arrays

        Raises:
            ValueError: If no index exists or index is empty
            ValueError: If query dimension doesn't match index dimension
        """
        if self._index is None:
            raise ValueError("No index exists")

        if self.ntotal == 0:
            raise ValueError("Index is empty")

        # Normalize query for cosine similarity
        if query.ndim == 1:
            query = query.reshape(1, -1)

        # Dimension validation before FAISS search
        query_dim = query.shape[1]
        if query_dim != self._index.d:
            raise ValueError(
                f"FATAL: Dimension mismatch between query ({query_dim}d) and "
                f"index ({self._index.d}d). The index was likely created with "
                f"a different embedding model. Clear the index and re-index the project."
            )

        faiss.normalize_L2(query)

        # Search
        distances, indices = self._index.search(query, k)
        return distances[0], indices[0]

    def reconstruct(self, idx: int) -> np.ndarray:
        """Reconstruct vector at given index position.

        Args:
            idx: Index position

        Returns:
            Reconstructed embedding vector

        Note:
            Uses memory-mapped storage for fast access (<1μs) if enabled,
            otherwise falls back to FAISS reconstruct.
        """
        if self._index is None:
            raise ValueError("No index exists")

        # Fast path: mmap access (<1μs after cache warm)
        if self._mmap_storage and self._mmap_storage.is_loaded:
            vector = self._mmap_storage.get_vector(idx)
            if vector is not None:
                return vector

        # Fallback: FAISS reconstruct
        return self._index.reconstruct(int(idx))

    def clear(self) -> None:
        """Clear the index and reset state."""
        # Explicitly delete GPU index if on GPU
        if self._index is not None and self._on_gpu:
            try:
                del self._index
                if torch and torch.cuda.is_available():
                    import gc

                    gc.collect()
                    torch.cuda.empty_cache()
            except Exception as e:
                self._logger.debug(f"GPU cache cleanup failed (non-critical): {e}")
            finally:
                self._on_gpu = False

        self._index = None
        self._chunk_ids = []

        # Remove index files
        if self.index_path.exists():
            self.index_path.unlink()
        if self.chunk_id_path.exists():
            self.chunk_id_path.unlink()

        # Remove mmap files (from before threshold implementation or old indices)
        if self._mmap_path.exists():
            self._mmap_path.unlink()
            self._logger.info(f"Removed old mmap file: {self._mmap_path.name}")

        self._logger.info("FAISS index cleared")

    # GPU Management

    @staticmethod
    def gpu_is_available() -> bool:
        """Check if GPU FAISS support is available and GPUs are present.

        Returns:
            True if GPU FAISS is available and GPUs are detected
        """
        if faiss is None:
            return False
        try:
            if not hasattr(faiss, "StandardGpuResources"):
                return False
            get_num_gpus = getattr(faiss, "get_num_gpus", None)
            if get_num_gpus is None:
                return False
            return get_num_gpus() > 0
        except (RuntimeError, AttributeError):
            return False

    def move_to_gpu(self) -> bool:
        """Move the index to GPU if supported.

        Returns:
            True if moved to GPU, False otherwise (no-op if already on GPU or unsupported)
        """
        if self._index is None or self._on_gpu:
            return False

        if not self.gpu_is_available():
            return False

        try:
            # Move index to all GPUs for faster add/search
            self._index = faiss.index_cpu_to_all_gpus(self._index)
            self._on_gpu = True
            self._logger.info("FAISS index moved to GPU(s)")
            return True
        except Exception as e:
            self._logger.warning(
                f"Failed to move FAISS index to GPU, continuing on CPU: {e}"
            )
            return False

    def move_to_cpu(self) -> bool:
        """Move the index from GPU to CPU.

        Returns:
            True if moved to CPU, False if already on CPU or failed
        """
        if self._index is None or not self._on_gpu:
            return False

        try:
            self._index = faiss.index_gpu_to_cpu(self._index)
            self._on_gpu = False
            self._logger.info("FAISS index moved to CPU")
            return True
        except Exception as e:
            self._logger.warning(f"Failed to move FAISS index to CPU: {e}")
            return False

    # Memory Management

    def check_memory_requirements(
        self, num_new_vectors: int, dimension: int
    ) -> dict[str, Any]:
        """Check if there's enough memory for adding new vectors.

        Args:
            num_new_vectors: Number of vectors to be added
            dimension: Dimension of vectors

        Returns:
            Dictionary with memory check results including:
            - available_memory: Dict of system/GPU memory
            - estimated_usage: Dict of estimated memory needed
            - sufficient_memory: Bool indicating if enough memory
            - prefer_gpu: Bool indicating if GPU should be preferred
        """
        # Get current memory status
        available = get_available_memory()

        # Check current index size
        current_size = self.ntotal
        total_vectors_after = current_size + num_new_vectors

        # Estimate total memory after adding vectors
        total_estimated = estimate_index_memory_usage(total_vectors_after, dimension)

        # Determine if we should use GPU or CPU
        prefer_gpu = self.gpu_is_available()
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

    def get_memory_status(self) -> dict[str, Any]:
        """Get current memory usage status.

        Returns:
            Dictionary with memory status including:
            - available_memory: Dict of system/GPU memory
            - index_vectors: Number of vectors in index
            - estimated_index_memory: Dict of estimated index memory
            - on_gpu: Bool indicating if index is on GPU
        """
        available = get_available_memory()
        current_size = self.ntotal

        status = {
            "available_memory": available,
            "index_vectors": current_size,
            "on_gpu": self._on_gpu,
        }

        # Add estimated memory if index exists
        if self._index is not None and current_size > 0:
            try:
                dimension = self._index.d
                estimated = estimate_index_memory_usage(current_size, dimension)
                status["estimated_index_memory"] = estimated
            except Exception as e:
                self._logger.debug(f"Could not estimate index memory: {e}")

        return status
