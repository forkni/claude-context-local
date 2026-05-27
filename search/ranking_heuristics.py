"""Relevance-ranking heuristics extracted from IntelligentSearcher."""

import re
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from .searcher import SearchResult


class RankingHeuristics:
    """Pure scoring unit for search-result ranking.

    Contains the full relevance-ranking policy (type boosts, name/path boosts,
    lifecycle demotion, docstring boost, complexity penalty) with no dependency
    on IntelligentSearcher state.
    """

    def rank(self, results: list["SearchResult"], query: str) -> list["SearchResult"]:
        """Return results sorted by relevance score (descending)."""
        return sorted(results, key=lambda r: self._score(r, query), reverse=True)

    def _score(self, result: "SearchResult", query: str) -> float:
        """Compute relevance score for a single result."""
        score = result.similarity_score

        query_tokens = self._normalize_to_tokens(query.lower())
        is_entity_query = self._is_entity_like_query(query, query_tokens)
        has_class_keyword = "class" in query.lower()

        if has_class_keyword:
            type_boosts = {
                "class": 1.4,
                "function": 1.2,
                "method": 1.2,
                "module": 0.82,
                "community": 0.82,
            }
        elif is_entity_query:
            type_boosts = {
                "class": 1.35,
                "function": 1.15,
                "method": 1.15,
                "module": 0.85,
                "community": 0.85,
            }
        else:
            type_boosts = {
                "function": 1.2,
                "method": 1.2,
                "class": 1.35,
                "module": 0.90,
                "community": 0.90,
            }

        score *= type_boosts.get(result.chunk_type, 1.0)

        score *= self._calculate_name_boost(result.name, query, query_tokens)
        score *= self._calculate_path_boost(result.relative_path, query_tokens)

        lifecycle_methods = {
            "__init__",
            "__enter__",
            "__exit__",
            "__del__",
            "__repr__",
            "__str__",
        }
        if result.name in lifecycle_methods:
            query_has_lifecycle_intent = any(
                word in query.lower()
                for word in ("init", "enter", "exit", "del", "repr", "lifecycle")
            )
            if not query_has_lifecycle_intent:
                score *= 0.85

        if result.docstring:
            if is_entity_query and result.chunk_type == "module":
                score *= 1.02
            else:
                score *= 1.05

        if len(result.content_preview) > 1000:
            score *= 0.98

        return score

    def _normalize_to_tokens(self, text: str) -> list[str]:
        """Convert text to normalized tokens, handling CamelCase."""
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
        text = text.replace("_", " ").replace("-", " ")
        return re.findall(r"\w+", text.lower())

    def _is_entity_like_query(self, query: str, query_tokens: list[str]) -> bool:
        """Detect if query looks like an entity/type name."""
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

        if any(token in action_words for token in query_tokens):
            return False

        if re.search(r"[A-Z][a-z]+[A-Z]", query):
            return True

        return len(query_tokens) <= 2

    def _calculate_name_boost(
        self, name: str | None, original_query: str, query_tokens: list[str]
    ) -> float:
        """Calculate boost based on name matching with robust token comparison."""
        if name is None:
            return 1.0

        name_tokens = self._normalize_to_tokens(name)

        if original_query.lower() == name.lower():
            return 1.4

        query_set = set(query_tokens)
        name_set = set(name_tokens)

        if not query_set or not name_set:
            return 1.0

        overlap = len(query_set & name_set)
        total_query_tokens = len(query_set)

        if overlap == 0:
            return 1.0

        overlap_ratio = overlap / total_query_tokens
        if overlap_ratio >= 0.8:
            return 1.3
        elif overlap_ratio >= 0.5:
            return 1.2
        elif overlap_ratio >= 0.3:
            return 1.1
        else:
            return 1.05

    def _calculate_path_boost(
        self, relative_path: str, query_tokens: list[str]
    ) -> float:
        """Calculate boost based on path/filename relevance."""
        if not relative_path or not query_tokens:
            return 1.0

        path_parts = relative_path.lower().replace("/", " ").replace("\\", " ")
        path_tokens = self._normalize_to_tokens(path_parts)

        query_set = set(query_tokens)
        path_set = set(path_tokens)

        overlap = len(query_set & path_set)
        if overlap > 0:
            return 1.0 + (overlap * 0.05)

        return 1.0
