"""Relevance-ranking heuristics extracted from IntelligentSearcher."""

import re
from typing import TYPE_CHECKING

from search.ranking_policy import (
    ACTION_WORDS,
    LIFECYCLE_METHODS,  # noqa: F401  (re-exported for any callers that used to import it here)
    NAME_OVERLAP_TIERS,
    TYPE_BOOSTS_CLASS_KEYWORD,
    TYPE_BOOSTS_CODE,
    TYPE_BOOSTS_ENTITY,
    lifecycle_demotion,
)


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
            type_boosts = TYPE_BOOSTS_CLASS_KEYWORD
        elif is_entity_query:
            type_boosts = TYPE_BOOSTS_ENTITY
        else:
            type_boosts = TYPE_BOOSTS_CODE

        score *= type_boosts.get(result.chunk_type, 1.0)

        score *= self._calculate_name_boost(result.name, query, query_tokens)
        score *= self._calculate_path_boost(result.relative_path, query_tokens)

        score *= lifecycle_demotion(result.name, query.lower())

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

        if any(token in ACTION_WORDS for token in query_tokens):
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
        for min_ratio, multiplier in NAME_OVERLAP_TIERS:
            if overlap_ratio >= min_ratio:
                return multiplier
        return 1.05  # below lowest tier: weak partial overlap

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
