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

from search.chunk_id import normalize as _normalize_chunk_id
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

    def _ensure_open(self) -> None:
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
        """Get metadata for a chunk.

        Canonicalizes *chunk_id* once at the read boundary (P1b), then performs
        a single hash-cache lookup followed by a single direct DB lookup.  All
        stored keys are canonical (enforced by :meth:`set`), so no multi-variant
        fallback is needed.

        Args:
            chunk_id: Chunk identifier in format "file:lines:type:name" —
                any path-separator variant is accepted; it is canonicalized
                before lookup.

        Returns:
            Metadata dictionary with "index_id" and "metadata" keys, or None if not found

        Example:
            >>> store.get("search/indexer.py:1-10:function:foo")
            {"index_id": 0, "metadata": {"relative_path": "search/indexer.py", ...}}
        """
        self._ensure_open()
        canonical = _normalize_chunk_id(chunk_id)

        # Fast path: O(1) hash-cache lookup (canonical key always hits if stored)
        cached_chunk_id = self._symbol_cache.get_by_chunk_id(canonical)
        # pyrefly: ignore [not-iterable]
        if cached_chunk_id and cached_chunk_id in self._db:
            # pyrefly: ignore [unsupported-operation]
            return self._db[cached_chunk_id]

        # Direct DB lookup (handles the first access before cache is warm)
        # pyrefly: ignore [not-iterable]
        if canonical in self._db:
            self._symbol_cache.add(canonical)
            # pyrefly: ignore [unsupported-operation]
            return self._db[canonical]

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

        Canonicalizes *chunk_id* at write time so all stored keys are in
        consistent forward-slash form.  This is the write boundary enforced by
        the P1b architecture step — callers may pass any path-separator variant;
        only the canonical form is stored.

        Args:
            chunk_id: Chunk identifier (canonicalized before storage)
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
        canonical = _normalize_chunk_id(chunk_id)
        # pyrefly: ignore [unsupported-operation]
        self._db[canonical] = {"index_id": index_id, "metadata": metadata}

        # Add canonical form to symbol cache for O(1) lookups
        self._symbol_cache.add(canonical)

    def delete(self, chunk_id: str) -> bool:
        """Delete metadata for a chunk.

        Args:
            chunk_id: Chunk identifier to delete (canonicalized before lookup)

        Returns:
            True if chunk was deleted, False if not found
        """
        self._ensure_open()
        canonical = _normalize_chunk_id(chunk_id)
        # pyrefly: ignore [not-iterable]
        if canonical in self._db:
            # pyrefly: ignore [unsupported-operation]
            del self._db[canonical]
            # Remove from symbol cache
            self._symbol_cache.remove(canonical)
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
            chunk_id: Chunk identifier (canonicalized before lookup + write)
            new_id: New FAISS index position

        Returns:
            True if updated, False if chunk not found
        """
        self._ensure_open()
        canonical = _normalize_chunk_id(chunk_id)
        entry = self.get(canonical)
        if entry:
            entry["index_id"] = new_id
            # pyrefly: ignore [unsupported-operation]
            self._db[canonical] = entry
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
            chunk_id: Chunk identifier to check (canonicalized before lookup)

        Returns:
            True if chunk exists, False otherwise
        """
        self._ensure_open()
        # pyrefly: ignore [not-iterable]
        return _normalize_chunk_id(chunk_id) in self._db

    def __len__(self) -> int:
        """Return number of chunks in metadata store.

        Returns:
            Count of chunks
        """
        self._ensure_open()
        # pyrefly: ignore [bad-argument-type]
        return len(self._db)

    def __contains__(self, chunk_id: str) -> bool:
        """Support 'chunk_id in store' syntax.

        Args:
            chunk_id: Chunk identifier to check (canonicalized before lookup)

        Returns:
            True if chunk exists, False otherwise
        """
        self._ensure_open()
        # pyrefly: ignore [not-iterable]
        return _normalize_chunk_id(chunk_id) in self._db

    def keys(self) -> Iterator[str]:
        """Iterate over chunk IDs.

        Returns:
            Iterator over chunk_id strings
        """
        self._ensure_open()
        # pyrefly: ignore [missing-attribute]
        return iter(self._db.keys())

    def items(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Iterate over (chunk_id, metadata) pairs.

        Returns:
            Iterator over (chunk_id, metadata_entry) tuples
        """
        self._ensure_open()
        # pyrefly: ignore [missing-attribute]
        return iter(self._db.items())

    # Transaction Control

    def commit(self) -> None:
        """Commit pending changes to disk.

        Should be called after batch operations to persist changes.
        """
        self._ensure_open()
        # pyrefly: ignore [missing-attribute]
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
        return _normalize_chunk_id(chunk_id)

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
