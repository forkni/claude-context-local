"""FAISS vector index management.

This module provides a dedicated interface for managing FAISS vector indices
with support for saving, loading, searching, and dimension tracking.
"""

import logging
import math
import pickle
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import psutil

from search.exceptions import IndexError as SearchIndexError


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder


try:
    import faiss
except ImportError:
    faiss = None

try:
    import torch
except ImportError:
    torch = None


# Mmap auto-threshold: Only use mmap for indices >10K vectors (performance benefit)
MMAP_THRESHOLD = 10000

# Flat/IVF policy (ADR-0083; measured by scripts/benchmark/probe_faiss_index_params.py,
# evaluation/FAISS_INDEX_PARAMS_20261005.md). Exact search is preferred until it
# is genuinely slow: flat IndexFlatIP at 50K x 1024-d vectors is ~5 ms for one
# query and ~55 ms for a 35-query multi-hop batch; at 17K it is 3-4 ms, which
# IVF cannot beat at equal recall. Real code embeddings are far less clustered
# than synthetic data: reaching recall@210 >= 0.99 against exact search needs
# about half of the inverted lists probed (synthetic needs 3%), so the old
# fixed nlist=100 / nprobe=16 scored recall@210 = 0.94 on a real corpus.
IVF_MIN_VECTORS = 50_000

# FAISS warns below this many training points per centroid; nlist is capped
# so that every centroid has at least this many.
IVF_MIN_TRAIN_PER_CENTROID = 39

# Fraction of the inverted lists probed per query. Smallest fraction reaching
# recall@210 >= 0.99 on the 17K real corpus was 0.29-0.64 depending on nlist.
IVF_PROBE_FRACTION = 0.5

# A probe must be able to visit at least this many vectors (the leg-depth
# ceiling, search_executor.leg_search_depth at k=84), or FAISS pads with -1.
IVF_MIN_VISITED = 420


def index_kind_for(vector_count: int) -> str:
    """Index kind ("flat" or "ivf") for an index holding ``vector_count`` vectors.

    The single owner of the flat/IVF decision. Consulted wherever the dense
    index is (re)created from a known vector set: the first batch into an empty
    index and every rebuild (a removal pass), so the kind follows size rather
    than the size of whichever batch happened to arrive first.
    """
    return "ivf" if vector_count > IVF_MIN_VECTORS else "flat"


def ivf_nlist_for(vector_count: int) -> int:
    """Number of IVF centroids for ``vector_count`` vectors.

    The FAISS rule of thumb ``4 * sqrt(N)`` (the low end of its 4-16 sqrt(N)
    range: fewer, larger lists keep recall high on weakly clustered code
    embeddings), capped so every centroid has ``IVF_MIN_TRAIN_PER_CENTROID``
    training points. Always at least 1.
    """
    n = max(0, vector_count)
    by_sqrt = round(4 * math.sqrt(n))
    by_training = n // IVF_MIN_TRAIN_PER_CENTROID
    return max(1, min(by_sqrt, by_training))


def ivf_nprobe_for(nlist: int, vector_count: int) -> int:
    """Lists probed per query for ``nlist`` lists holding ``vector_count`` vectors.

    ``IVF_PROBE_FRACTION`` of the lists, raised when needed so the probe can
    visit ``IVF_MIN_VISITED`` vectors (no ``-1`` padding at the leg-depth
    ceiling), never more than ``nlist``.
    """
    nlist = max(1, nlist)
    by_fraction = math.ceil(IVF_PROBE_FRACTION * nlist)
    by_depth = math.ceil(IVF_MIN_VISITED * nlist / max(1, vector_count))
    return max(1, min(nlist, max(by_fraction, by_depth)))


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

    def __init__(self, index_path: Path, embedder: "CodeEmbedder | None" = None):
        """Initialize FAISS vector index.

        Args:
            index_path: Path to FAISS index file
            embedder: Optional embedder for dimension validation
        """
        self.index_path = Path(index_path)
        self.chunk_id_path = self.index_path.parent / "chunk_ids.pkl"
        self.embedder = embedder

        self._index: Any | None = None
        self._chunk_ids: list = []
        self._on_gpu: bool = False
        self._logger = logging.getLogger(__name__)
        # True when the loaded IVF index was built with METRIC_L2 (indexes
        # created before the metric fix); search() converts its distances.
        self._legacy_l2: bool = False
        # Lazily built chunk_id -> position map; reset whenever _chunk_ids changes.
        self._position_index: dict[str, int] | None = None

        # Memory-mapped vector storage (auto-enabled for >10K vectors)
        self._mmap_storage: Any | None = None  # MmapVectorStorage
        self._mmap_path = (
            self.index_path.parent / f"{self.index_path.stem}_vectors.mmap"
        )

    @property
    def index(self) -> Any | None:
        """Get the underlying FAISS index."""
        return self._index

    @property
    def ntotal(self) -> int:
        """Get the number of vectors in the index."""
        if self._index is None:
            return 0
        return self._index.ntotal

    @property
    def dimension(self) -> int | None:
        """Get the dimension of vectors in the index."""
        if self._index is None:
            return None
        return self._index.d

    @property
    def is_on_gpu(self) -> bool:
        """Check if the index is currently on GPU."""
        return self._on_gpu

    @property
    def chunk_ids(self) -> list[str]:
        """Get the list of chunk IDs."""
        return self._chunk_ids

    def create(
        self,
        dimension: int,
        index_type: str = "flat",
        expected_count: int | None = None,
    ) -> None:
        """Create a new FAISS index.

        Args:
            dimension: Embedding dimension
            index_type: Type of index to create ("flat" or "ivf")
            expected_count: Number of vectors the index will hold; required
                for ``"ivf"`` (sizes ``nlist``/``nprobe``, see
                ``ivf_nlist_for``/``ivf_nprobe_for``), ignored for ``"flat"``.

        Raises:
            ValueError: If index_type is not supported, or ``"ivf"`` without
                ``expected_count``
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
            if expected_count is None:
                raise ValueError("expected_count is required for an IVF index")
            quantizer = faiss.IndexFlatIP(dimension)
            n_centroids = ivf_nlist_for(expected_count)
            self._index = faiss.IndexIVFFlat(
                quantizer, dimension, n_centroids, faiss.METRIC_INNER_PRODUCT
            )
        else:
            raise ValueError(f"Unsupported index type: {index_type}")

        self._chunk_ids = []
        self._position_index = None
        self._on_gpu = False
        self._configure_ivf(expected_count)
        self._logger.info(f"Created {index_type} index with dimension {dimension}")

        # Move to GPU if available
        self.move_to_gpu()

    def _configure_ivf(self, expected_count: int | None = None) -> None:
        """Make an IVF index reconstructable and widen its search (no-op for flat).

        ``IndexIVFFlat`` cannot ``reconstruct(i)`` without a direct map, and
        defaults to ``nprobe=1``. The direct map is the FAISS-side fallback for
        ``reconstruct()`` whenever the mmap vector storage is absent or
        discarded as stale; a no-op if the loaded index already carries one.
        ``nprobe`` is set from the policy (``ivf_nprobe_for``) on every create
        and load, sized by ``ntotal`` when vectors are present, else by
        ``expected_count``; whatever was persisted on disk is ignored.
        Must run before ``move_to_gpu()`` (the GPU wrapper has no such knobs).
        """
        self._legacy_l2 = False
        if faiss is None or self._index is None:
            return
        ivf = faiss.try_extract_index_ivf(self._index)
        if ivf is None:
            return
        if ivf.direct_map.type == faiss.DirectMap.NoMap:
            ivf.make_direct_map()
        count = ivf.ntotal if ivf.ntotal > 0 else (expected_count or 0)
        ivf.nprobe = ivf_nprobe_for(ivf.nlist, count)
        if ivf.metric_type == faiss.METRIC_L2:
            # IVF indexes created before the METRIC_INNER_PRODUCT fix return
            # squared L2 distances (smaller = better). search() converts them
            # to inner products so score consumers see one convention.
            self._legacy_l2 = True
            self._logger.warning(
                "Legacy L2-metric IVF index loaded; scores are converted to "
                "inner products on search. Reindex the project to rebuild it "
                "with the inner-product metric."
            )

    def close(self) -> None:
        """Release the mmap handle without deleting any files.

        Idempotent: safe to call multiple times. Unlike ``clear()``, this
        does not touch ``index_path``/``chunk_id_path``/``_mmap_path`` on
        disk -- it only drops the in-process handle backing
        ``_mmap_storage``, so the caller can release its own mapping before
        another instance clears or rewrites the same files (WinError 32 on
        Windows otherwise: unlinking or truncating a file with a live
        mmap.mmap section fails while any handle to it stays open).
        """
        if self._mmap_storage is not None:
            self._mmap_storage.close()
            self._mmap_storage = None

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

        self._position_index = None
        try:
            self._logger.info(f"Loading existing index from {self.index_path}")
            # pyrefly: ignore [missing-attribute]
            self._index = faiss.read_index(str(self.index_path))

            # Validate index dimension matches current model (if embedder provided)
            if self.embedder is not None:
                try:
                    stored_dim = self._index.d
                    model_info = self.embedder.get_model_info()
                    current_model_dim = model_info.get("embedding_dimension")
                    if current_model_dim is None:
                        self._logger.debug(
                            "Skipping dimension validation: model not loaded yet"
                        )
                    elif stored_dim != current_model_dim:
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
                except (RuntimeError, AttributeError, KeyError) as e:
                    self._logger.debug(f"Could not validate index dimension: {e}")

            self._configure_ivf()

            # Move to GPU if available
            self.move_to_gpu()

            # Load chunk IDs
            # SECURITY: pickle.load is safe here — chunk_id_path lives under
            # ~/.claude_code_search/ which is exclusively written by this process.
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
                    elif self._mmap_storage.count != self._index.ntotal:
                        # Stale-generation guard: a residual mmap file can
                        # survive a failed delete (e.g. a foreign process
                        # held it, see save()'s below-threshold branch)
                        # while self._index above was loaded fresh from
                        # code.index. Mapping vectors from the wrong
                        # generation would silently return wrong-but-valid
                        # -looking embeddings, so refuse the mapping instead
                        # -- get_vector()/reconstruct() already fall back to
                        # FAISS reconstruct() when _mmap_storage is None.
                        self._logger.warning(
                            f"Discarding stale mmap storage: {self._mmap_storage.count} "
                            f"vectors on disk != {self._index.ntotal} in loaded index "
                            f"(likely a residual file from a failed delete); "
                            "falling back to FAISS reconstruct"
                        )
                        self._mmap_storage.close()
                        self._mmap_storage = None
                    else:
                        self._logger.info(
                            f"Loaded mmap storage: {self._mmap_storage.count} vectors "
                            f"from {self._mmap_path.name}"
                        )
                except Exception as e:  # noqa: BLE001 - resilience: mmap storage optional, fall back to FAISS reconstruct
                    self._logger.debug(f"Could not load mmap storage: {e}")
                    self._mmap_storage = None

            return True

        except (OSError, RuntimeError) as e:
            self._logger.error(f"Failed to load index: {e}", exc_info=True)
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
            # pyrefly: ignore [missing-attribute]
            faiss.write_index(index_to_write, str(self.index_path))
            self._logger.info(f"Saved index to {self.index_path}")
        except (OSError, RuntimeError) as e:
            self._logger.warning(
                f"Failed to save GPU index directly, attempting CPU fallback: {e}"
            )
            try:
                # pyrefly: ignore [missing-attribute]
                cpu_index = faiss.index_gpu_to_cpu(self._index)
                # pyrefly: ignore [missing-attribute]
                faiss.write_index(cpu_index, str(self.index_path))
                self._logger.info(f"Saved index to {self.index_path} (CPU fallback)")
            except (OSError, RuntimeError) as e2:
                self._logger.error(f"Failed to save FAISS index: {e2}")
                raise

        # Save chunk IDs
        with open(self.chunk_id_path, "wb") as f:
            pickle.dump(self._chunk_ids, f)

        # Auto-threshold: Only use mmap for indices >10K vectors (performance benefit)
        # Fully automatic - no config needed
        if self._index is not None:
            vector_count = self._index.ntotal
            if vector_count >= MMAP_THRESHOLD:
                try:
                    from search.mmap_vectors import MmapVectorStorage

                    # Release this instance's own mapping (if any) before
                    # truncating and rewriting the same file through a new
                    # MmapVectorStorage below -- a live mapping left pointing
                    # into a truncated-and-rewritten file is stale/corrupt,
                    # and on Windows a live handle blocks the rewrite outright
                    # (WinError 32).
                    self.close()

                    dimension = self._index.d
                    mmap_storage = MmapVectorStorage(self._mmap_path, dimension)

                    # Reconstruct all vectors in one C++ call (reconstruct_n
                    # is a single memcpy for IndexFlatIP vs O(N) Python↔C++
                    # crossings with per-vector reconstruct) (#19).
                    embeddings = self._index.reconstruct_n(0, self._index.ntotal)
                    mmap_storage.save(embeddings, self._chunk_ids)
                    self._logger.info(
                        f"Saved mmap storage: {self._index.ntotal} vectors to {self._mmap_path}"
                    )

                    # Re-attach: close() above dropped this instance's own
                    # mapping, and without one reconstruct() falls through to
                    # FAISS reconstruct() -- which an IVF index could not serve
                    # (direct map not initialized) until the next restart,
                    # breaking multi-hop hop-2 after every in-process reindex.
                    # Same stale-generation guard as load().
                    if mmap_storage.load() and mmap_storage.count == vector_count:
                        self._mmap_storage = mmap_storage
                    else:
                        mmap_storage.close()
                except OSError as e:
                    self._logger.warning(f"Failed to save mmap vectors: {e}")
            else:
                # Below threshold: delete mmap if it exists (from previous larger index)
                if self._mmap_path.exists():
                    # Release this instance's own mapping before unlinking --
                    # same rationale as the rewrite branch above.
                    self.close()
                    try:
                        self._mmap_path.unlink()
                        self._logger.info(
                            f"Deleted mmap file (below threshold): {vector_count} vectors < {MMAP_THRESHOLD}"
                        )
                    except OSError as e:
                        # Symmetric with the >=MMAP_THRESHOLD branch above:
                        # a residual lock here (e.g. a genuinely separate
                        # process, not just another in-process instance --
                        # those are now covered by _open_shared_delete())
                        # must not abort save_indices() mid-way through a
                        # BM25/dense write and leave the two legs desynced.
                        self._logger.warning(f"Failed to delete stale mmap file: {e}")
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

        # Normalize embeddings for cosine similarity.
        # L2-normalization invariant: all vectors in the index are unit-norm;
        # search() also normalizes the query before scoring, making IndexFlatIP
        # equivalent to cosine similarity. PyTorch embeddings
        # reach this point already approximately unit-norm; the explicit
        # normalize_L2 here is the canonical source of that guarantee (#33).
        # Copy first — normalize_L2 is in-place, and callers must not see
        # their array mutated (#29).
        embeddings = embeddings.copy()
        # pyrefly: ignore [missing-attribute]
        faiss.normalize_L2(embeddings)

        # Train index if needed (for IVF indexes)
        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            self._index.train(embeddings)

        # Add to index
        self._index.add(embeddings)
        self._chunk_ids.extend(chunk_ids)
        self._position_index = None

        self._logger.debug(f"Added {len(embeddings)} vectors to index")

    def search(self, query: np.ndarray, k: int = 5) -> tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors.

        Args:
            query: Query embedding — 1D (single query) or 2D [n, d] (batch).
            k: Number of nearest neighbors to return.

        Returns:
            Single query (1D input): (distances[k], indices[k])
            Batch (2D input [n, d]):  (distances[n, k], indices[n, k])

        Raises:
            ValueError: If no index exists or index is empty
            ValueError: If query dimension doesn't match index dimension
        """
        if self._index is None:
            raise ValueError("No index exists")

        if self.ntotal == 0:
            raise ValueError("Index is empty")

        # batched=True only when caller passes [N>1, d] — preserves existing
        # 1D return contract for single-query callers (including [1, d] inputs)
        batched = query.ndim == 2 and query.shape[0] > 1
        if query.ndim == 1:
            query = query.reshape(1, -1)

        query_dim = query.shape[1]
        if query_dim != self._index.d:
            raise ValueError(
                f"FATAL: Dimension mismatch between query ({query_dim}d) and "
                f"index ({self._index.d}d). The index was likely created with "
                f"a different embedding model. Clear the index and re-index the project."
            )

        query = query.copy()  # normalize_L2 is in-place (see add() for invariant doc)
        # pyrefly: ignore [missing-attribute]
        faiss.normalize_L2(query)

        distances, indices = self._index.search(query, k)
        if self._legacy_l2:
            # Unit-norm vectors: ||q - x||^2 = 2 - 2<q, x>  =>  <q, x> = 1 - d^2 / 2.
            distances = 1.0 - distances / 2.0
            distances[indices == -1] = -1.0
        if batched:
            return distances, indices
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

    def position_of(self, chunk_id: str) -> int | None:
        """Index position of ``chunk_id``, or None when it is not indexed.

        Backed by a lazily built dict that is invalidated by every mutation
        of the id list (create/load/add/clear), so repeated lookups cost O(1)
        instead of a linear scan or a per-call rebuild.
        """
        if self._position_index is None:
            self._position_index = {cid: pos for pos, cid in enumerate(self._chunk_ids)}
        return self._position_index.get(chunk_id)

    def reconstruct_batch(self, positions: Sequence[int]) -> np.ndarray:
        """Reconstruct the vectors at ``positions`` as one ``(n, d)`` matrix.

        Uses the mmap sidecar when every row is available there, otherwise a
        single FAISS ``reconstruct_batch`` call (direct map required for IVF,
        see ``_configure_ivf``). Returns an empty ``(0, d)`` array for no
        positions. Reconstruction errors propagate.
        """
        if self._index is None:
            raise ValueError("No index exists")
        if len(positions) == 0:
            return np.empty((0, self._index.d), dtype=np.float32)

        if self._mmap_storage and self._mmap_storage.is_loaded:
            rows = [self._mmap_storage.get_vector(int(p)) for p in positions]
            if all(r is not None for r in rows):
                return np.stack(rows).astype(np.float32, copy=False)

        ids = np.asarray(list(positions), dtype=np.int64)
        if hasattr(self._index, "reconstruct_batch"):
            return self._index.reconstruct_batch(ids)
        return np.stack([self._index.reconstruct(int(p)) for p in ids])

    def describe(self) -> dict[str, Any]:
        """Report the live index kind and IVF search parameters.

        Returns ``index_kind`` ("flat", "ivf", or None when no index exists),
        plus ``ivf_nlist``/``ivf_nprobe`` for IVF indexes (None if FAISS cannot
        expose them, e.g. a GPU-resident index).
        """
        if self._index is None:
            return {"index_kind": None}
        if "IVF" not in type(self._index).__name__:
            return {"index_kind": "flat", "metric": "ip"}
        ivf = faiss.try_extract_index_ivf(self._index) if faiss is not None else None
        return {
            "index_kind": "ivf",
            "metric": "l2" if self._legacy_l2 else "ip",
            "ivf_nlist": ivf.nlist if ivf is not None else None,
            "ivf_nprobe": ivf.nprobe if ivf is not None else None,
        }

    def remove_positions(self, positions_to_remove: set[int]) -> bool:
        """Drop the vectors at ``positions_to_remove`` by rebuilding the index.

        Reads every stored vector back in one ``reconstruct_n`` call, masks
        out the dropped positions, recreates the index and re-adds the rest,
        restoring GPU placement. The caller renumbers metadata assuming every
        kept position survives, so a reconstruction failure or an id-list /
        index size mismatch raises instead of silently skipping vectors.

        Args:
            positions_to_remove: Index positions to exclude.

        Returns:
            True if the index was rebuilt with the remaining vectors; False if
            every position was removed. On False the index is left untouched
            and the caller owns the index clear.

        Raises:
            RuntimeError: chunk-id list and FAISS index disagree on size.
        """
        if self._index is None:
            raise ValueError("No index exists")
        n = len(self._chunk_ids)
        if self._index.ntotal != n:
            raise RuntimeError(
                f"Index/id-list size mismatch: {self._index.ntotal} vectors vs "
                f"{n} chunk ids; refusing to rebuild"
            )
        keep = np.ones(n, dtype=bool)
        drop = [p for p in positions_to_remove if 0 <= p < n]
        keep[drop] = False
        if not keep.any():
            return False

        source = self._index
        if self._on_gpu and hasattr(faiss, "index_gpu_to_cpu"):
            source = faiss.index_gpu_to_cpu(self._index)
        all_vectors = source.reconstruct_n(0, n)
        embeddings_array = np.ascontiguousarray(all_vectors[keep], dtype=np.float32)
        chunk_ids_to_keep = [
            cid for cid, kept in zip(self._chunk_ids, keep, strict=True) if kept
        ]
        was_on_gpu = self._on_gpu

        self.clear()
        kept = len(embeddings_array)
        self.create(
            embeddings_array.shape[1], index_kind_for(kept), expected_count=kept
        )
        self.add(embeddings_array, chunk_ids_to_keep)

        if was_on_gpu:
            self.move_to_gpu()
        return True

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
            except Exception as e:  # noqa: BLE001 - cleanup: GPU cache release best-effort, non-critical
                self._logger.debug(f"GPU cache cleanup failed (non-critical): {e}")
            finally:
                self._on_gpu = False

        self._index = None
        self._chunk_ids = []
        self._position_index = None

        # Close and release the mmap handle, then unlink it FIRST, before
        # index_path/chunk_id_path below. A residual WinError 32 here (this
        # instance's own handle is released above, but another live
        # CodeIndexManager may still map the same file -- see
        # search.indexer.CodeIndexManager.close()) then aborts before
        # anything else is destroyed, instead of leaving a half-wiped index
        # that only "recovers" by accident on retry.
        self.close()
        if self._mmap_path.exists():
            self._mmap_path.unlink()
            self._logger.info(f"Removed old mmap file: {self._mmap_path.name}")

        # Remove index files
        if self.index_path.exists():
            self.index_path.unlink()
        if self.chunk_id_path.exists():
            self.chunk_id_path.unlink()

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
            # pyrefly: ignore [missing-attribute]
            self._index = faiss.index_cpu_to_all_gpus(self._index)
            self._on_gpu = True
            self._logger.info("FAISS index moved to GPU(s)")
            return True
        except RuntimeError as e:
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
            # pyrefly: ignore [missing-attribute]
            self._index = faiss.index_gpu_to_cpu(self._index)
            self._on_gpu = False
            self._logger.info("FAISS index moved to CPU")
            return True
        except RuntimeError as e:
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
            except Exception as e:  # noqa: BLE001 - resilience: memory estimate optional, status omits it on failure
                self._logger.debug(f"Could not estimate index memory: {e}")

        return status
