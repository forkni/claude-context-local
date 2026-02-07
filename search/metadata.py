"""Metadata storage layer for code search index.

This module provides a centralized interface for managing chunk metadata
stored in SQLite, with support for efficient querying and chunk ID normalization.
"""

import contextlib
import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlitedict import SqliteDict

from search.filters import normalize_path
from search.symbol_cache import SymbolHashCache


class MetadataStore:
    """Centralized metadata storage for code chunks.

    Wraps SqliteDict to provide a clean API for CRUD operations on chunk metadata.
    Handles path separator normalization and variant lookups for cross-platform
    compatibility.

    Attributes:
        _db: Underlying SqliteDict instance
        db_path: Path to the SQLite database file

    Example:
        >>> store = MetadataStore(Path("metadata.db"))
        >>> store.set("file.py:1-10:function:foo", 0, {"relative_path": "file.py"})
        >>> metadata = store.get("file.py:1-10:function:foo")
        >>> store.commit()
        >>> store.close()
    """

    def __init__(self, db_path: Path):
        """Initialize metadata store.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._db: SqliteDict | None = None

        # Symbol hash cache for O(1) chunk_id lookups
        cache_path = db_path.parent / f"{db_path.stem}_symbol_cache.json"
        self._symbol_cache = SymbolHashCache(cache_path)

    def _ensure_open(self):
        """Lazy-load database connection.

        Uses JSON serialization instead of pickle to mitigate CVE-2024-35515
        (insecure deserialization vulnerability in sqlitedict).
        """
        if self._db is None:
            self._db = SqliteDict(
                str(self.db_path),
                autocommit=False,
                journal_mode="WAL",
                encode=json.dumps,
                decode=json.loads,
            )

    # CRUD Operations

    def get(self, chunk_id: str) -> dict[str, Any] | None:
        """Get metadata for a chunk with path variant handling.

        Tries multiple chunk_id variants to handle path separator differences
        (Windows backslash vs Unix forward slash) and MCP transport escaping bugs.

        Uses symbol hash cache for O(1) lookup before falling back to variant checking.

        Args:
            chunk_id: Chunk identifier in format "file:lines:type:name"

        Returns:
            Metadata dictionary with "index_id" and "metadata" keys, or None if not found

        Example:
            >>> store.get("search/indexer.py:1-10:function:foo")
            {"index_id": 0, "metadata": {"relative_path": "search/indexer.py", ...}}
        """
        self._ensure_open()

        # Fast path: Try hash cache lookup (O(1))
        cached_chunk_id = self._symbol_cache.get_by_chunk_id(chunk_id)
        if cached_chunk_id and cached_chunk_id in self._db:
            return self._db[cached_chunk_id]

        # Slow path: Try variants (backward compatibility)
        for variant in self.get_chunk_id_variants(chunk_id):
            if variant in self._db:
                # Cache the successful variant for future lookups
                self._symbol_cache.add(variant)
                return self._db[variant]

        return None

    def get_chunk_metadata(self, chunk_id: str) -> dict[str, Any] | None:
        """Get just the metadata dict for a chunk (without index_id wrapper).

        This is a convenience method for cases where only chunk metadata is needed,
        not the FAISS index position. Used by community remerge operations.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Metadata dictionary with fields like relative_path, chunk_type, content, etc.,
            or None if chunk not found

        Example:
            >>> store.get_chunk_metadata("file.py:1-10:function:foo")
            {"relative_path": "file.py", "chunk_type": "function", "content": "...", ...}
        """
        entry = self.get(chunk_id)
        return entry["metadata"] if entry else None

    def set(self, chunk_id: str, index_id: int, metadata: dict[str, Any]) -> None:
        """Set metadata for a chunk.

        Args:
            chunk_id: Chunk identifier
            index_id: Position in FAISS index
            metadata: Chunk metadata dictionary containing relative_path, chunk_type, etc.

        Example:
            >>> store.set("file.py:1-10:function:foo", 0, {
            ...     "relative_path": "file.py",
            ...     "chunk_type": "function",
            ...     "name": "foo"
            ... })
        """
        self._ensure_open()
        self._db[chunk_id] = {"index_id": index_id, "metadata": metadata}

        # Add to symbol cache for O(1) lookups
        self._symbol_cache.add(chunk_id)

    def delete(self, chunk_id: str) -> bool:
        """Delete metadata for a chunk.

        Args:
            chunk_id: Chunk identifier to delete

        Returns:
            True if chunk was deleted, False if not found
        """
        self._ensure_open()
        if chunk_id in self._db:
            del self._db[chunk_id]
            # Remove from symbol cache
            self._symbol_cache.remove(chunk_id)
            return True
        return False

    def delete_batch(self, chunk_ids: list[str]) -> int:
        """Delete multiple chunks in batch.

        Args:
            chunk_ids: List of chunk identifiers to delete

        Returns:
            Count of chunks successfully deleted
        """
        self._ensure_open()
        count = 0
        for chunk_id in chunk_ids:
            if self.delete(chunk_id):
                count += 1
        return count

    def update_index_id(self, chunk_id: str, new_id: int) -> bool:
        """Update the FAISS index ID for a chunk.

        Args:
            chunk_id: Chunk identifier
            new_id: New FAISS index position

        Returns:
            True if updated, False if chunk not found
        """
        self._ensure_open()
        entry = self.get(chunk_id)
        if entry:
            entry["index_id"] = new_id
            self._db[chunk_id] = entry
            return True
        return False

    def update_index_ids_batch(self, updates: dict[str, int]) -> int:
        """Batch update FAISS index IDs.

        Args:
            updates: Dictionary mapping chunk_id to new index_id

        Returns:
            Count of chunks successfully updated
        """
        self._ensure_open()
        count = 0
        for chunk_id, new_id in updates.items():
            if self.update_index_id(chunk_id, new_id):
                count += 1
        return count

    # Query Operations

    def exists(self, chunk_id: str) -> bool:
        """Check if a chunk exists in metadata.

        Args:
            chunk_id: Chunk identifier to check

        Returns:
            True if chunk exists, False otherwise
        """
        self._ensure_open()
        return chunk_id in self._db

    def __len__(self) -> int:
        """Return number of chunks in metadata store.

        Returns:
            Count of chunks
        """
        self._ensure_open()
        return len(self._db)

    def __contains__(self, chunk_id: str) -> bool:
        """Support 'chunk_id in store' syntax.

        Args:
            chunk_id: Chunk identifier to check

        Returns:
            True if chunk exists, False otherwise
        """
        self._ensure_open()
        return chunk_id in self._db

    def keys(self) -> Iterator[str]:
        """Iterate over chunk IDs.

        Returns:
            Iterator over chunk_id strings
        """
        self._ensure_open()
        return iter(self._db.keys())

    def items(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Iterate over (chunk_id, metadata) pairs.

        Returns:
            Iterator over (chunk_id, metadata_entry) tuples
        """
        self._ensure_open()
        return iter(self._db.items())

    # Transaction Control

    def commit(self) -> None:
        """Commit pending changes to disk.

        Should be called after batch operations to persist changes.
        """
        self._ensure_open()
        self._db.commit()

        # Save symbol cache
        self._symbol_cache.save()

    def close(self) -> None:
        """Close database connection.

        Should be called when done with the store to release resources.
        """
        if self._db is not None:
            # Ensure WAL is checkpointed before close (prevents file handle leaks on Windows)
            with contextlib.suppress(OSError, sqlite3.Error):
                # Ignore errors during commit (db might already be closed or corrupted)
                self._db.commit()
            self._db.close()
            self._db = None

    # Utility Methods (moved from CodeIndexManager)

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
            >>> MetadataStore.normalize_chunk_id("search\\reranker.py:36-137:method:rerank")
            "search/reranker.py:36-137:method:rerank"
        """
        # Split by chunk_id structure (file:lines:type:name)
        parts = chunk_id.split(":")
        if len(parts) >= 4:
            # First part is the file path - normalize it
            file_path = normalize_path(parts[0])
            # Reconstruct chunk_id
            return f"{file_path}:{':'.join(parts[1:])}"
        # Fallback: just normalize backslashes
        return normalize_path(chunk_id)

    @staticmethod
    def get_chunk_id_variants(chunk_id: str) -> list[str]:
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

        Example:
            >>> MetadataStore.get_chunk_id_variants("search\\\\indexer.py:1-10:function:foo")
            ["search\\\\indexer.py:1-10:function:foo",
             "search\\indexer.py:1-10:function:foo",
             "search/indexer.py:1-10:function:foo",
             ...]
        """
        variants = [
            chunk_id,  # Original (exact match)
            chunk_id.replace(
                "\\\\", "\\"
            ),  # Handle double-escaped backslashes from JSON transport
            normalize_path(chunk_id),  # Normalize to forward slash
            chunk_id.replace("/", "\\"),  # Try backslash variant
            MetadataStore.normalize_chunk_id(chunk_id),  # Properly normalized
            MetadataStore.normalize_chunk_id(
                chunk_id.replace("\\\\", "\\")
            ),  # Normalized un-double-escaped
        ]

        # Remove duplicates while preserving order
        seen = set()
        unique_variants = []
        for variant in variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)

        return unique_variants

    # Context Manager Support

    def __enter__(self) -> "MetadataStore":
        """Context manager entry."""
        self._ensure_open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - commit and close."""
        if exc_type is None:
            self.commit()
        self.close()
