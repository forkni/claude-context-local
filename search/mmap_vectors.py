"""Memory-mapped vector storage for <1μs access.

This module provides a memory-mapped binary format for storing embedding vectors,
enabling ultra-fast vector reconstruction (<1μs after OS cache warm) without
requiring the vectors to remain in RAM.

Binary Format:
    Header (24 bytes):
        Magic: "CVEC" (4 bytes) - File identifier
        Version: u32 (4 bytes) - Format version (1)
        Dimension: u32 (4 bytes) - Embedding dimension
        Count: u32 (4 bytes) - Number of vectors
        Reserved: u64 (8 bytes) - Future use

    Data (per vector):
        Index: u32 (4 bytes) - FAISS index position
        Hash: u64 (8 bytes) - FNV-1a hash of chunk_id
        Vector: f32[dimension] (dimension * 4 bytes)

    Total size per vector: 12 + dimension * 4 bytes
    Example (1024d): 12 + 4096 = 4108 bytes per vector

Usage:
    # Save vectors to mmap file
    storage = MmapVectorStorage(Path("vectors.mmap"), dimension=1024)
    storage.save(embeddings, chunk_ids)

    # Load and access vectors
    storage = MmapVectorStorage(Path("vectors.mmap"), dimension=1024)
    if storage.load():
        vector = storage.get_vector(0)  # <1μs after cache warm

Performance:
    - Initial load: ~100-200μs (memory mapping setup)
    - First access: ~1-10μs (page fault for OS to load page)
    - Subsequent accesses: <1μs (direct memory access, no syscalls)
    - Memory overhead: Minimal (OS manages pages lazily)
"""

import logging
import mmap
import struct
from pathlib import Path

import numpy as np

from search.symbol_cache import SymbolHashCache


logger = logging.getLogger(__name__)


class MmapVectorStorage:
    """Memory-mapped vector storage for O(1) vector access.

    This class provides a binary format for storing embedding vectors that can be
    memory-mapped for ultra-fast access without loading all vectors into RAM.

    Attributes:
        MAGIC: File format identifier (b"CVEC")
        VERSION: Binary format version (1)
        HEADER_SIZE: Size of file header in bytes (24)
    """

    MAGIC = b"CVEC"
    VERSION = 1
    HEADER_SIZE = 24  # magic(4) + version(4) + dim(4) + count(4) + reserved(8)

    __slots__ = ("_path", "_dimension", "_mmap", "_file", "_count", "_entry_size")

    def __init__(self, path: Path, dimension: int):
        """Initialize MmapVectorStorage.

        Args:
            path: Path to the mmap binary file
            dimension: Embedding dimension (must match vectors)
        """
        self._path = path
        self._dimension = dimension
        self._mmap: mmap.mmap | None = None
        self._file = None
        self._count = 0
        self._entry_size = 12 + dimension * 4  # idx(4) + hash(8) + vector(dim*4)

    @property
    def is_loaded(self) -> bool:
        """Return True if mmap file is currently loaded."""
        return self._mmap is not None

    @property
    def count(self) -> int:
        """Return the number of vectors in storage."""
        return self._count

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._dimension

    def save(
        self,
        embeddings: np.ndarray,
        chunk_ids: list[str],
        indices: list[int] | None = None,
    ) -> None:
        """Save embeddings in mmap-compatible binary format.

        Args:
            embeddings: Numpy array of embeddings (n, dimension)
            chunk_ids: List of chunk IDs corresponding to embeddings
            indices: Optional list of FAISS index positions (defaults to 0..n-1)

        Raises:
            ValueError: If embeddings shape doesn't match dimension or chunk_ids length
        """
        if embeddings.shape[0] != len(chunk_ids):
            raise ValueError(
                f"Embeddings count ({embeddings.shape[0]}) doesn't match "
                f"chunk_ids count ({len(chunk_ids)})"
            )

        if embeddings.shape[1] != self._dimension:
            raise ValueError(
                f"Embeddings dimension ({embeddings.shape[1]}) doesn't match "
                f"expected dimension ({self._dimension})"
            )

        if indices is None:
            indices = list(range(len(chunk_ids)))

        if len(indices) != len(chunk_ids):
            raise ValueError(
                f"Indices count ({len(indices)}) doesn't match "
                f"chunk_ids count ({len(chunk_ids)})"
            )

        # Ensure parent directory exists
        self._path.parent.mkdir(parents=True, exist_ok=True)

        with open(self._path, "wb") as f:
            # Write header
            f.write(self.MAGIC)
            f.write(struct.pack("<III", self.VERSION, self._dimension, len(chunk_ids)))
            f.write(struct.pack("<Q", 0))  # Reserved for future use

            # Write vectors
            for i, (idx, chunk_id) in enumerate(zip(indices, chunk_ids, strict=True)):
                chunk_hash = SymbolHashCache.fnv1a_hash(chunk_id)
                f.write(struct.pack("<IQ", idx, chunk_hash))
                # Ensure float32 and write as bytes
                f.write(embeddings[i].astype(np.float32).tobytes())

        logger.debug(
            f"Saved {len(chunk_ids)} vectors ({self._dimension}d) to {self._path.name}"
        )

    def load(self) -> bool:
        """Memory-map the file for reading (lazy loading by OS).

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self._path.exists():
            logger.debug(f"Mmap file does not exist: {self._path}")
            return False

        try:
            self._file = open(self._path, "rb")  # noqa: SIM115 - file handle stored for mmap
            self._mmap = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)

            # Validate header
            if self._mmap[:4] != self.MAGIC:
                logger.warning(
                    f"Invalid magic bytes in {self._path.name}: "
                    f"{self._mmap[:4]!r} != {self.MAGIC!r}"
                )
                self.close()
                return False

            version, dim, count = struct.unpack("<III", self._mmap[4:16])

            if version != self.VERSION:
                logger.warning(
                    f"Unsupported version in {self._path.name}: "
                    f"{version} (expected {self.VERSION})"
                )
                self.close()
                return False

            if dim != self._dimension:
                logger.warning(
                    f"Dimension mismatch in {self._path.name}: "
                    f"{dim} (expected {self._dimension})"
                )
                self.close()
                return False

            self._count = count
            logger.debug(
                f"Loaded mmap storage: {count} vectors ({dim}d) from {self._path.name}"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to load mmap storage from {self._path}: {e}")
            self.close()
            return False

    def get_vector(self, index: int) -> np.ndarray | None:
        """Get vector by FAISS index position (<1μs after cache warm).

        Args:
            index: FAISS index position (0-based)

        Returns:
            Numpy array of shape (dimension,) or None if index invalid or not loaded

        Note:
            This method provides direct memory access with no syscalls after
            the initial page fault. Performance:
            - First access: ~1-10μs (OS page fault)
            - Subsequent: <1μs (direct memory read)
        """
        if self._mmap is None:
            return None

        if index < 0 or index >= self._count:
            return None

        # Calculate offset for this vector
        offset = self.HEADER_SIZE + index * self._entry_size
        vector_offset = offset + 12  # Skip idx(4) + hash(8)

        # Direct memory access - no syscalls after initial page fault
        # frombuffer creates a view, .copy() ensures we own the data
        return np.frombuffer(
            self._mmap[vector_offset : vector_offset + self._dimension * 4],
            dtype=np.float32,
        ).copy()

    def close(self) -> None:
        """Close mmap and file handles.

        Should be called when done with the storage to release resources.
        """
        if self._mmap:
            self._mmap.close()
            self._mmap = None
        if self._file:
            self._file.close()
            self._file = None
        self._count = 0

    def __enter__(self) -> "MmapVectorStorage":
        """Context manager entry - returns self for use in with statement.

        Returns:
            Self for use in with statement

        Example:
            with MmapVectorStorage(path, dimension=1024) as storage:
                if storage.load():
                    vector = storage.get_vector(0)
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - ensures resources are cleaned up.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        self.close()

    def __del__(self):
        """Ensure resources are cleaned up on deletion."""
        self.close()

    def __repr__(self) -> str:
        """Return string representation."""
        status = "loaded" if self.is_loaded else "closed"
        return (
            f"MmapVectorStorage(path={self._path.name}, "
            f"dimension={self._dimension}, count={self._count}, status={status})"
        )
