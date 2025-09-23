"""Intelligent search functionality with query optimization."""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from embeddings.embedder import CodeEmbedder

from .indexer import CodeIndexManager


@dataclass
class SearchResult:
    """Enhanced search result with rich metadata."""

    chunk_id: str
    similarity_score: float
    content_preview: str
    file_path: str
    relative_path: str
    folder_structure: List[str]
    chunk_type: str
    name: Optional[str]
    parent_name: Optional[str]
    start_line: int
    end_line: int
    docstring: Optional[str]
    tags: List[str]
    context_info: Dict[str, Any]


class IntelligentSearcher:
    """Intelligent code search with query optimization and context awareness."""

    def __init__(self, index_manager: CodeIndexManager, embedder: CodeEmbedder):
        self.index_manager = index_manager
        self.embedder = embedder
        self._logger = logging.getLogger(__name__)

        # Query patterns for intent detection
        self.query_patterns = {
            "function_search": [
                r"\bfunction\b",
                r"\bdef\b",
                r"\bmethod\b",
                r"\bclass\b",
                r"how.*work",
                r"implement.*",
                r"algorithm.*",
            ],
            "error_handling": [
                r"\berror\b",
                r"\bexception\b",
                r"\btry\b",
                r"\bcatch\b",
                r"handle.*error",
                r"exception.*handling",
            ],
            "database": [
                r"\bdatabase\b",
                r"\bdb\b",
                r"\bquery\b",
                r"\bsql\b",
                r"\bmodel\b",
                r"\btable\b",
                r"connection",
            ],
            "api": [
                r"\bapi\b",
                r"\bendpoint\b",
                r"\broute\b",
                r"\brequest\b",
                r"\bresponse\b",
                r"\bhttp\b",
                r"rest.*api",
            ],
            "authentication": [
                r"\bauth\b",
                r"\blogin\b",
                r"\btoken\b",
                r"\bpassword\b",
                r"\bsession\b",
                r"authenticate",
                r"permission",
            ],
            "testing": [
                r"\btest\b",
                r"\bmock\b",
                r"\bassert\b",
                r"\bfixture\b",
                r"unit.*test",
                r"integration.*test",
            ],
        }

    def search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "semantic",
        context_depth: int = 1,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
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
        k: int = 5,
        context_depth: int = 1,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Pure semantic search implementation."""

        # Detect query intent and optimize
        optimized_query = self._optimize_query(query)
        intent_tags = self._detect_query_intent(query)

        self._logger.info(
            f"Searching for: '{optimized_query}' with intent: {intent_tags}"
        )

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

        # Convert to rich search results
        search_results = []
        for chunk_id, similarity, metadata in raw_results:
            result = self._create_search_result(
                chunk_id, similarity, metadata, context_depth
            )
            search_results.append(result)

        # Post-process and rank results
        ranked_results = self._rank_results(search_results, query, intent_tags)

        return ranked_results[:k]

    def _optimize_query(self, query: str) -> str:
        """Optimize query for better embedding generation."""
        # Basic query cleaning only - avoid expanding technical terms
        # that might distort code-specific queries
        return query.strip()

    def _detect_query_intent(self, query: str) -> List[str]:
        """Detect the intent/domain of the search query."""
        query_lower = query.lower()
        detected_intents = []

        for intent, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected_intents.append(intent)
                    break

        return detected_intents

    def _create_search_result(
        self,
        chunk_id: str,
        similarity: float,
        metadata: Dict[str, Any],
        context_depth: int,
    ) -> SearchResult:
        """Create a rich search result with context information."""

        # Basic metadata extraction
        content_preview = metadata.get("content_preview", "")
        file_path = metadata.get("file_path", "")
        relative_path = metadata.get("relative_path", "")
        folder_structure = metadata.get("folder_structure", [])

        # Context information
        context_info = {}

        if context_depth > 0:
            # Add related chunks context
            similar_chunks = self.index_manager.get_similar_chunks(chunk_id, k=3)
            context_info["similar_chunks"] = [
                {
                    "chunk_id": cid,
                    "similarity": sim,
                    "name": meta.get("name"),
                    "chunk_type": meta.get("chunk_type"),
                }
                for cid, sim, meta in similar_chunks[:2]  # Top 2 similar
            ]

            # Add file context
            context_info["file_context"] = {
                "total_chunks_in_file": self._count_chunks_in_file(relative_path),
                "folder_path": "/".join(folder_structure) if folder_structure else None,
            }

        return SearchResult(
            chunk_id=chunk_id,
            similarity_score=similarity,
            content_preview=content_preview,
            file_path=file_path,
            relative_path=relative_path,
            folder_structure=folder_structure,
            chunk_type=metadata.get("chunk_type", "unknown"),
            name=metadata.get("name"),
            parent_name=metadata.get("parent_name"),
            start_line=metadata.get("start_line", 0),
            end_line=metadata.get("end_line", 0),
            docstring=metadata.get("docstring"),
            tags=metadata.get("tags", []),
            context_info=context_info,
        )

    def _count_chunks_in_file(self, relative_path: str) -> int:
        """Count total chunks in a specific file."""
        count = 0
        stats = self.index_manager.get_stats()

        # This is a simplified implementation
        # In a real scenario, you might want to maintain this as a separate index
        return stats.get("files_indexed", 0)

    def _rank_results(
        self, results: List[SearchResult], original_query: str, intent_tags: List[str]
    ) -> List[SearchResult]:
        """Advanced ranking based on multiple factors."""

        def calculate_rank_score(result: SearchResult) -> float:
            score = result.similarity_score

            # Detect if query looks like an entity/class name
            query_tokens = self._normalize_to_tokens(original_query.lower())
            is_entity_query = self._is_entity_like_query(original_query, query_tokens)
            has_class_keyword = "class" in original_query.lower()

            # Dynamic chunk type boosts based on query type
            if has_class_keyword:
                # Strong preference for classes when "class" is mentioned
                type_boosts = {
                    "class": 1.3,
                    "function": 1.05,
                    "method": 1.05,
                    "module": 0.9,
                }
            elif is_entity_query:
                # Moderate preference for classes on entity-like queries
                type_boosts = {
                    "class": 1.15,
                    "function": 1.1,
                    "method": 1.1,
                    "module": 0.92,
                }
            else:
                # Default boosts for general queries
                type_boosts = {
                    "function": 1.1,
                    "method": 1.1,
                    "class": 1.05,
                    "module": 0.95,
                }

            score *= type_boosts.get(result.chunk_type, 1.0)

            # Enhanced name matching with token-based comparison
            name_boost = self._calculate_name_boost(
                result.name, original_query, query_tokens
            )
            score *= name_boost

            # Path/filename relevance boost
            path_boost = self._calculate_path_boost(result.relative_path, query_tokens)
            score *= path_boost

            # Boost based on tag matches
            if intent_tags and result.tags:
                tag_overlap = len(set(intent_tags) & set(result.tags))
                score *= 1.0 + tag_overlap * 0.1

            # Boost based on docstring presence (but less for module chunks on entity queries)
            if result.docstring:
                if is_entity_query and result.chunk_type == "module":
                    score *= (
                        1.02  # Smaller boost for module docstrings on entity queries
                    )
                else:
                    score *= 1.05

            # Slight penalty for very complex chunks (might be too specific)
            if len(result.content_preview) > 1000:
                score *= 0.98

            return score

        # Sort by calculated rank score
        ranked_results = sorted(results, key=calculate_rank_score, reverse=True)
        return ranked_results

    def _normalize_to_tokens(self, text: str) -> List[str]:
        """Convert text to normalized tokens, handling CamelCase."""
        import re

        # Split CamelCase and snake_case
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        text = text.replace("_", " ").replace("-", " ")

        # Extract alphanumeric tokens
        tokens = re.findall(r"\w+", text.lower())
        return tokens

    def _is_entity_like_query(self, query: str, query_tokens: List[str]) -> bool:
        """Detect if query looks like an entity/type name."""
        # Short queries with 1-3 tokens that don't contain action words
        if len(query_tokens) > 3:
            return False

        action_words = {
            "find",
            "search",
            "get",
            "show",
            "list",
            "how",
            "what",
            "where",
            "when",
            "create",
            "build",
            "make",
            "handle",
            "process",
            "manage",
            "implement",
        }

        # If any token is an action word, it's not an entity query
        if any(token in action_words for token in query_tokens):
            return False

        # If original query has CamelCase or looks like a class name, it's entity-like
        import re

        if re.search(r"[A-Z][a-z]+[A-Z]", query):  # CamelCase pattern
            return True

        return len(query_tokens) <= 2  # Short noun phrases

    def _calculate_name_boost(
        self, name: Optional[str], original_query: str, query_tokens: List[str]
    ) -> float:
        """Calculate boost based on name matching with robust token comparison."""
        if not name:
            return 1.0

        name_tokens = self._normalize_to_tokens(name)

        # Exact match (case insensitive)
        if original_query.lower() == name.lower():
            return 1.4

        # Token overlap calculation
        query_set = set(query_tokens)
        name_set = set(name_tokens)

        if not query_set or not name_set:
            return 1.0

        overlap = len(query_set & name_set)
        total_query_tokens = len(query_set)

        if overlap == 0:
            return 1.0

        # Strong boost for high overlap
        overlap_ratio = overlap / total_query_tokens
        if overlap_ratio >= 0.8:  # 80%+ of query tokens match
            return 1.3
        elif overlap_ratio >= 0.5:  # 50%+ match
            return 1.2
        elif overlap_ratio >= 0.3:  # 30%+ match
            return 1.1
        else:
            return 1.05

    def _calculate_path_boost(
        self, relative_path: str, query_tokens: List[str]
    ) -> float:
        """Calculate boost based on path/filename relevance."""
        if not relative_path or not query_tokens:
            return 1.0

        # Extract path components and filename
        path_parts = relative_path.lower().replace("/", " ").replace("\\", " ")
        path_tokens = self._normalize_to_tokens(path_parts)

        # Check for token overlap with path
        query_set = set(query_tokens)
        path_set = set(path_tokens)

        overlap = len(query_set & path_set)
        if overlap > 0:
            # Modest boost for path relevance
            return 1.0 + (overlap * 0.05)  # 5% boost per matching token

        return 1.0

    def search_by_file_pattern(
        self, query: str, file_patterns: List[str], k: int = 5
    ) -> List[SearchResult]:
        """Search within specific file patterns."""
        filters = {"file_pattern": file_patterns}
        return self.search(query, k=k, filters=filters)

    def search_by_chunk_type(
        self, query: str, chunk_type: str, k: int = 5
    ) -> List[SearchResult]:
        """Search for specific types of code chunks."""
        filters = {"chunk_type": chunk_type}
        return self.search(query, k=k, filters=filters)

    def find_similar_to_chunk(self, chunk_id: str, k: int = 5) -> List[SearchResult]:
        """Find chunks similar to a given chunk."""
        similar_chunks = self.index_manager.get_similar_chunks(chunk_id, k)

        results = []
        for chunk_id, similarity, metadata in similar_chunks:
            result = self._create_search_result(
                chunk_id, similarity, metadata, context_depth=1
            )
            results.append(result)

        return results

    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Generate search suggestions based on indexed content."""
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
