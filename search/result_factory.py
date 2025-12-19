"""Factory methods for creating and converting SearchResult objects.

This module provides static factory methods for creating SearchResult instances
from various search result formats (BM25, dense/semantic, direct lookup).
"""

from typing import Dict, List, Tuple

from .reranker import SearchResult


class ResultFactory:
    """Factory for creating and converting search results to SearchResult format.

    This class provides static methods to convert search results from different
    sources into a standardized SearchResult format.

    Example:
        >>> bm25_results = [("chunk1", 0.85, {"file": "test.py"}), ...]
        >>> results = ResultFactory.from_bm25_results(bm25_results)
        >>> print(results[0].source)  # "bm25"
    """

    @staticmethod
    def from_bm25_results(bm25_results: List[Tuple]) -> List[SearchResult]:
        """Convert BM25 search results to SearchResult format.

        Args:
            bm25_results: List of (chunk_id, score, metadata) tuples from BM25 search

        Returns:
            List of SearchResult objects with source="bm25"

        Example:
            >>> bm25_results = [
            ...     ("file.py:1-10:function:foo", 0.85, {"file": "file.py"}),
            ...     ("file.py:20-30:class:Bar", 0.72, {"file": "file.py"}),
            ... ]
            >>> results = ResultFactory.from_bm25_results(bm25_results)
            >>> len(results)
            2
            >>> results[0].source
            'bm25'
        """
        search_results = []
        for i, (chunk_id, score, metadata) in enumerate(bm25_results):
            search_result = SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source="bm25",
                rank=i,
            )
            search_results.append(search_result)
        return search_results

    @staticmethod
    def from_dense_results(dense_results: List[Tuple]) -> List[SearchResult]:
        """Convert dense/semantic search results to SearchResult format.

        Args:
            dense_results: List of (chunk_id, score, metadata) tuples from dense search

        Returns:
            List of SearchResult objects with source="semantic"

        Example:
            >>> dense_results = [
            ...     ("file.py:1-10:function:foo", 0.92, {"file": "file.py"}),
            ...     ("file.py:20-30:class:Bar", 0.88, {"file": "file.py"}),
            ... ]
            >>> results = ResultFactory.from_dense_results(dense_results)
            >>> len(results)
            2
            >>> results[0].source
            'semantic'
        """
        search_results = []
        for i, (chunk_id, score, metadata) in enumerate(dense_results):
            search_result = SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source="semantic",
                rank=i,
            )
            search_results.append(search_result)
        return search_results

    @staticmethod
    def from_direct_lookup(chunk_id: str, metadata: Dict) -> SearchResult:
        """Create SearchResult for direct chunk ID lookup.

        Normalizes metadata to ensure the 'file' key exists (may be stored as
        'file_path' or 'relative_path' in metadata).

        Args:
            chunk_id: The chunk identifier (format: "file:lines:type:name")
            metadata: Chunk metadata dictionary

        Returns:
            SearchResult with score=1.0 and source="direct_lookup"

        Example:
            >>> metadata = {"file_path": "test.py", "content": "..."}
            >>> result = ResultFactory.from_direct_lookup("test.py:1-10:function:foo", metadata)
            >>> result.score
            1.0
            >>> result.source
            'direct_lookup'
            >>> result.metadata["file"]
            'test.py'
        """
        # Normalize metadata to ensure 'file' key exists
        # (metadata may have 'file_path' or 'relative_path' instead)
        if "file" not in metadata:
            metadata["file"] = metadata.get(
                "file_path", metadata.get("relative_path", "")
            )

        return SearchResult(
            chunk_id=chunk_id,
            score=1.0,
            metadata=metadata,
            source="direct_lookup",
            rank=0,
        )
