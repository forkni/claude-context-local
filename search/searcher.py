"""Intelligent search functionality with query optimization."""

import logging
from typing import TYPE_CHECKING, Any, Optional

from embeddings.embedder import CodeEmbedder

from .base_searcher import BaseSearcher
from .config import SearchMode
from .indexer import CodeIndexManager
from .ranking_heuristics import RankingHeuristics
from .reranker import SearchResult


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage


class IntelligentSearcher(BaseSearcher):
    """Intelligent code search with query optimization and context awareness."""

    def __init__(
        self, index_manager: CodeIndexManager, embedder: CodeEmbedder, config=None
    ):
        # Initialize base searcher (cache management, dimension validation)
        super().__init__()

        self.index_manager = index_manager
        self.embedder = embedder

        # Override logger with module-specific logger (set by BaseSearcher)
        self._logger = logging.getLogger(__name__)

        # Dimension validation (safety check)
        self._validate_dimensions(self.index_manager.index, self.embedder)

        self._ranking = RankingHeuristics()

    @property
    def graph_storage(self) -> Optional["CodeGraphStorage"]:
        """Access graph storage from index manager."""
        return getattr(self.index_manager, "graph_storage", None)

    @property
    def is_ready(self) -> bool:
        """Check if searcher is ready for queries.

        Returns:
            bool: True if index is loaded and searcher is operational
        """
        return (
            self.index_manager.index is not None and self.index_manager.index.ntotal > 0
        )

    # pyrefly: ignore [bad-override]
    def search(
        self,
        query: str,
        k: int = 4,
        search_mode: str = SearchMode.SEMANTIC,
        context_depth: int = 1,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Semantic search for code understanding.

        This provides semantic search capabilities. For complete search coverage:
        - Use this tool for conceptual/functionality queries
        - Use Claude Code's Grep for exact term matching
        - Combine both for comprehensive results

        Args:
            query: Natural language query
            k: Number of results
            search_mode: Currently "semantic" only
            context_depth: Include related chunks
            filters: Optional filters
        """

        # Focus on semantic search - our specialty
        return self._semantic_search(query, k, context_depth, filters)

    def _semantic_search(
        self,
        query: str,
        k: int = 4,
        context_depth: int = 1,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Pure semantic search implementation."""

        # Optimize query
        optimized_query = self._optimize_query(query)

        self._logger.info(f"Searching for: '{optimized_query}'")

        # Generate query embedding
        query_embedding = self.embedder.embed_query(optimized_query)

        # Search with expanded result set for better filtering and recall
        search_k = min(k * 10, 200)  # Increased from k*3 to k*10 for better recall
        self._logger.info(
            f"Query embedding shape: {query_embedding.shape if hasattr(query_embedding, 'shape') else 'unknown'}"
        )
        self._logger.info(f"Using original filters: {filters}")
        self._logger.info(f"Calling index_manager.search with k={search_k}")

        raw_results = self.index_manager.search(query_embedding, search_k, filters)
        self._logger.info(f"Index manager returned {len(raw_results)} raw results")

        # Build thin (unenriched) results for all candidates. Enrichment
        # (get_similar_chunks: a metadata lookup + FAISS reconstruct + nested
        # FAISS search) is deferred until after ranking + truncation so it's
        # only paid for the results actually returned, not all ~search_k of them.
        search_results = [
            self._create_search_result(chunk_id, similarity, metadata, context_depth=0)
            for chunk_id, similarity, metadata in raw_results
        ]

        # Post-process and rank results, then truncate before enriching survivors
        ranked_results = self._ranking.rank(search_results, query)
        top_results = ranked_results[:k]

        for result in top_results:
            self._enrich_result(result, context_depth)

        return top_results

    def _optimize_query(self, query: str) -> str:
        """Optimize query for better embedding generation."""
        # Basic query cleaning only - avoid expanding technical terms
        # that might distort code-specific queries
        return query.strip()

    def _create_search_result(
        self,
        chunk_id: str,
        similarity: float,
        metadata: dict[str, Any],
        context_depth: int,
    ) -> SearchResult:
        """Create a thin search result, enriching metadata with context information."""
        result = SearchResult(
            chunk_id=chunk_id,
            score=similarity,
            metadata={**metadata, "context_info": {}},
            source="semantic",
        )
        self._enrich_result(result, context_depth)
        return result

    def _enrich_result(self, result: SearchResult, context_depth: int) -> None:
        """Enrich a search result's metadata with context information, in place.

        Extracted from `_create_search_result` so `_semantic_search` can defer
        this — `get_similar_chunks` costs a metadata lookup + FAISS reconstruct
        + a nested FAISS search — until after ranking and truncation, instead of
        paying it for every raw candidate that ranking then discards.
        """
        if context_depth <= 0:
            return

        metadata = result.metadata

        # Add related chunks context
        similar_chunks = self.index_manager.get_similar_chunks(result.chunk_id, k=3)
        context_info: dict[str, Any] = {
            "similar_chunks": [
                {
                    "chunk_id": cid,
                    "similarity": sim,
                    "name": meta.get("name"),
                    "chunk_type": meta.get("chunk_type"),
                }
                for cid, sim, meta in similar_chunks[:2]  # Top 2 similar
            ]
        }

        # Add file context (folder_path only — total_chunks_in_file was
        # returning the project-wide file count, not the per-file chunk count,
        # and was read nowhere downstream so it has been removed (#45))
        folder_structure = metadata.get("folder_structure", [])
        # pyrefly: ignore [unsupported-operation]
        context_info["file_context"] = {
            "folder_path": "/".join(folder_structure) if folder_structure else None,
        }

        metadata["context_info"] = context_info

    def search_by_file_pattern(
        self,
        query: str,
        file_patterns: list[str],
        k: int = 4,
    ) -> list[SearchResult]:
        """Search within a set of file path patterns.

        Args:
            query: Natural-language search query.
            file_patterns: Glob-style patterns (e.g., ``["**/*.py", "src/**"]``)
                used to restrict results to matching files.
            k: Number of results to return (default: 4).

        Returns:
            Ranked list of ``SearchResult``, filtered to chunks whose source
            file matches at least one of ``file_patterns``.
        """
        filters = {"file_pattern": file_patterns}
        return self.search(query, k=k, filters=filters)

    def search_by_chunk_type(
        self, query: str, chunk_type: str, k: int = 4
    ) -> list[SearchResult]:
        """Search restricted to a specific chunk type.

        Args:
            query: Natural-language search query.
            chunk_type: Chunk kind to match (e.g., ``"function"``, ``"class"``,
                ``"method"``, ``"module"``).
            k: Number of results to return (default: 4).

        Returns:
            Ranked list of ``SearchResult`` filtered to the requested chunk type.
        """
        filters = {"chunk_type": chunk_type}
        return self.search(query, k=k, filters=filters)

    def find_similar_to_chunk(self, chunk_id: str, k: int = 4) -> list[SearchResult]:
        """Find chunks functionally similar to a given chunk.

        Args:
            chunk_id: Chunk ID in the form ``"file.py:start-end:type:name"``.
            k: Number of similar chunks to return (default: 4).

        Returns:
            Ranked list of ``SearchResult`` ordered by similarity (descending).
            Each result is enriched with ``context_depth=1`` neighbor context.
        """
        similar_chunks = self.index_manager.get_similar_chunks(chunk_id, k)

        results = []
        for chunk_id, similarity, metadata in similar_chunks:
            result = self._create_search_result(
                chunk_id, similarity, metadata, context_depth=1
            )
            results.append(result)

        return results

    def get_by_chunk_id(self, chunk_id: str) -> SearchResult | None:
        """
        Direct lookup by chunk_id (unambiguous, no search needed).

        Uses in-memory cache to avoid repeated SQLite lookups during
        multi-hop operations like find_connections (2-5x speedup).

        Args:
            chunk_id: Format "file.py:10-20:function:name"

        Returns:
            SearchResult if found, None otherwise
        """
        # Fast path: Check in-memory cache first
        if chunk_id in self._metadata_cache:
            self._cache_hits += 1
            # pyrefly: ignore [bad-return]
            return self._metadata_cache[chunk_id]

        # Slow path: Load from SQLite
        self._cache_misses += 1
        metadata = self.index_manager.get_chunk_by_id(chunk_id)
        if not metadata:
            # Cache None results to avoid repeated failed lookups
            self._metadata_cache[chunk_id] = None
            self._evict_cache_if_needed()
            return None

        # Create SearchResult with score 1.0 (exact match)
        result = self._create_search_result(
            chunk_id,
            similarity=1.0,
            metadata=metadata,
            context_depth=2,  # Include full context for direct lookups
        )

        # Store in cache for future lookups
        # pyrefly: ignore [unsupported-operation]
        self._metadata_cache[chunk_id] = result
        self._evict_cache_if_needed()

        return result

    def get_search_suggestions(self, partial_query: str) -> list[str]:
        """Generate search suggestions from indexed content.

        Uses the index's aggregate statistics (top tags, chunk types) to
        propose candidate query completions that match ``partial_query``.

        Args:
            partial_query: Partial user query used as a substring filter.

        Returns:
            List of suggestion strings (may be empty if nothing matches).
        """
        # This is a simplified implementation
        # In a full system, you might maintain a separate suggestions index

        suggestions = []
        stats = self.index_manager.get_stats()

        # Suggest based on top tags
        top_tags = stats.get("top_tags", {})
        for tag in top_tags:
            if partial_query.lower() in tag.lower():
                suggestions.append(f"Find {tag} related code")

        # Suggest based on chunk types
        chunk_types = stats.get("chunk_types", {})
        for chunk_type in chunk_types:
            if partial_query.lower() in chunk_type.lower():
                suggestions.append(f"Show all {chunk_type}s")

        return suggestions[:5]
