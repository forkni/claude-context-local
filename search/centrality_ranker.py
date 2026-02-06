"""
Centrality-based result ranking for SSCG Phase 3.

Blends PageRank centrality scores with semantic similarity to boost
structurally important code in search results.
"""

import logging
import re
from typing import Optional

import networkx as nx


logger = logging.getLogger(__name__)


def _extract_name_from_chunk_id(chunk_id: str) -> str:
    """Extract name from 'file:lines:type:Name' format.

    Examples:
        "embeddings/embedder.py:276-1330:class:CodeEmbedder" -> "CodeEmbedder"
        "search/searcher.py:37-52:method:IntelligentSearcher.__init__" -> "IntelligentSearcher.__init__"
        "scripts/list_projects_display.py:24-85:function:main" -> "main"

    Returns:
        The qualified name (fourth component), or empty string if invalid format.
    """
    parts = chunk_id.split(":")
    return parts[3] if len(parts) >= 4 else ""


def _tokenize_for_matching(text: str) -> set[str]:
    """Tokenize text splitting CamelCase, snake_case, and dot-separated names.

    Filters out tokens with length <= 1 (e.g., "a", "I").

    Examples:
        "CodeEmbedder" -> {"code", "embedder"}
        "embed_chunks" -> {"embed", "chunks"}
        "IntelligentSearcher.__init__" -> {"intelligent", "searcher", "init"}
        "what does CodeEmbedder do with batch processing" -> {"what", "does", "code", "embedder", "do", "with", "batch", "processing"}

    Returns:
        Set of lowercase alphanumeric tokens (length > 1).
    """
    # Split dot-separated qualified names (e.g., "Class.method")
    text = text.replace(".", " ")
    # Split CamelCase: "CodeEmbedder" -> "Code Embedder"
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    # Split uppercase runs: "HTMLParser" -> "HTML Parser"
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", text)
    # Split snake_case and kebab-case
    text = text.replace("_", " ").replace("-", " ")
    # Extract lowercase tokens, filter single-char tokens
    tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", text.lower()) if len(t) > 1}
    return tokens


def _extract_chunk_lines(chunk_id: str) -> int:
    """Extract line count from 'file:start-end:type:name' format.

    Examples:
        "embeddings/embedder.py:276-1330:class:CodeEmbedder" -> 1054 lines
        "search/filters.py:22-31:function:normalize_path" -> 9 lines
        "invalid:format" -> 0 (fallback)

    Returns:
        Number of lines in chunk, or 0 if format is invalid.
    """
    parts = chunk_id.split(":")
    if len(parts) < 2:
        logger.warning(f"Malformed chunk_id (insufficient parts): {chunk_id}")
        return 0
    line_range = parts[1]  # "start-end" format
    if "-" not in line_range:
        logger.warning(f"Malformed chunk_id (no line range): {chunk_id}")
        return 0
    try:
        start, end = map(int, line_range.split("-"))
        return end - start + 1  # Inclusive range
    except (ValueError, IndexError):
        logger.warning(f"Malformed chunk_id (invalid line range): {chunk_id}")
        return 0


class CentralityRanker:
    """Ranks search results by blending semantic scores with centrality.

    Two modes:
    - annotate(): Add centrality field without reordering
    - rerank(): Add centrality + reorder by blended score
    """

    def __init__(
        self,
        graph_query_engine,
        method: str = "pagerank",
        alpha: float = 0.3,
        config=None,
    ):
        """Initialize centrality ranker.

        Args:
            graph_query_engine: GraphQueryEngine instance
            method: Centrality method (pagerank, degree, betweenness, closeness)
            alpha: Blending weight (0=semantic only, 1=centrality only)
            config: GraphEnhancedConfig instance for size normalization (optional)
        """
        self.graph_query_engine = graph_query_engine
        self.method = method
        self.alpha = alpha
        self.config = config

        # Cache centrality scores to avoid recomputation
        self._cache: dict[str, float] = {}
        self._cache_key = (0, 0)  # (node_count, edge_count)

    def _get_centrality_scores(self) -> dict[str, float]:
        """Compute and cache centrality scores.

        Uses node+edge count for cache invalidation (graph rebuild detection).
        Normalizes scores to [0, 1] range.

        Returns:
            dict mapping chunk_id -> normalized centrality score [0, 1]
        """
        current_key = (
            self.graph_query_engine.storage.graph.number_of_nodes(),
            self.graph_query_engine.storage.graph.number_of_edges(),
        )

        # Invalidate cache if node or edge count changed
        if current_key != self._cache_key:
            self._cache.clear()
            self._cache_key = current_key

        # Return cached scores if available
        if self._cache:
            return self._cache

        # Handle empty graph
        if current_key[0] == 0:
            logger.debug("[CENTRALITY] Empty graph, returning empty scores")
            return {}

        # Compute centrality scores
        try:
            raw_scores = self.graph_query_engine.compute_centrality(method=self.method)
        except nx.PowerIterationFailedConvergence:
            logger.warning(
                "[CENTRALITY] PageRank failed to converge, returning empty scores"
            )
            return {}
        except (nx.NetworkXError, ValueError, KeyError) as e:
            logger.error(
                f"[CENTRALITY] Failed to compute {self.method} centrality: {e}"
            )
            return {}

        # Normalize to [0, 1] range
        max_score = 0.0  # Initialize before conditional to avoid UnboundLocalError
        if raw_scores:
            max_score = max(raw_scores.values())
            if max_score > 0:
                self._cache = {
                    chunk_id: score / max_score
                    for chunk_id, score in raw_scores.items()
                }
            else:
                self._cache = dict.fromkeys(raw_scores, 0.0)
        else:
            self._cache = {}

        logger.debug(
            f"[CENTRALITY] Computed {len(self._cache)} scores "
            f"(method={self.method}, max={max_score:.4f})"
        )

        return self._cache

    def annotate(self, results: list[dict]) -> list[dict]:
        """Add centrality scores to results without reordering.

        Args:
            results: List of search result dicts

        Returns:
            Results with added "centrality" field
        """
        centrality_scores = self._get_centrality_scores()

        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                centrality = centrality_scores.get(chunk_id, 0.0)
                result["centrality"] = round(centrality, 4)

        return results

    def rerank(
        self, results: list[dict], alpha: Optional[float] = None, query: str = ""
    ) -> list[dict]:
        """Rerank results by blended semantic + centrality score.

        Args:
            results: List of search result dicts with "score" field
            alpha: Blending weight override (None = use self.alpha)
            query: Query string for query-aware boosting (optional)

        Returns:
            Reranked results with "centrality" and "blended_score" fields
        """
        # First, annotate with centrality scores
        results = self.annotate(results)

        # Use provided alpha or fall back to instance alpha
        # CRITICAL: Use `if alpha is not None` to handle alpha=0.0 correctly
        blend_alpha = alpha if alpha is not None else self.alpha

        # Compute blended scores and sort
        for result in results:
            semantic_score = result.get("score", 0.0)
            centrality = result.get("centrality", 0.0)

            # Blend: (1 - alpha) * semantic + alpha * centrality
            blended = (1 - blend_alpha) * semantic_score + blend_alpha * centrality
            result["blended_score"] = round(blended, 4)

            # Chunk-size normalization (penalize oversized chunks)
            if self.config is not None and self.config.enable_size_normalization:
                chunk_id = result.get("chunk_id", "")
                chunk_lines = _extract_chunk_lines(chunk_id)
                if chunk_lines > self.config.size_norm_target_lines:
                    import math

                    size_factor = 1.0 / (
                        1.0
                        + self.config.size_norm_alpha
                        * math.log(chunk_lines / self.config.size_norm_target_lines)
                    )
                    result["blended_score"] = round(
                        result["blended_score"] * size_factor, 4
                    )
                    logger.debug(
                        f"[CENTRALITY] Size normalization for {chunk_id}: "
                        f"{chunk_lines} lines → factor={size_factor:.3f}"
                    )

            # Query-aware boosting (ported from IntelligentSearcher)
            if query:
                chunk_type = result.get("kind", "")
                query_lower = query.lower()
                is_entity_query = any(
                    w in query_lower for w in ("class", "module", "struct", "enum")
                )
                if is_entity_query:
                    type_boosts = {
                        "class": 1.35,
                        "function": 1.15,
                        "method": 1.15,
                        "decorated_definition": 1.1,
                        "split_block": 1.1,  # Function/method fragments
                        "module": 0.85,  # File-level summaries (A2) - strengthened demotion
                        "community": 0.85,  # Community-level summaries (B1) - strengthened demotion
                    }
                else:
                    type_boosts = {
                        "function": 1.2,
                        "method": 1.2,
                        "decorated_definition": 1.0,  # Neutral — includes dataclasses, not just functions
                        "split_block": 1.1,  # Function/method fragments
                        "class": 1.35,
                        "module": 0.90,  # File-level summaries (A2) - strengthened demotion
                        "community": 0.90,  # Community-level summaries (B1) - strengthened demotion
                    }
                result["blended_score"] = round(
                    result["blended_score"] * type_boosts.get(chunk_type, 1.0), 4
                )

                # Core Logic Boost: Prioritize engine internals over glue code/tools
                chunk_id = result.get("chunk_id", "")
                core_dirs = ("embeddings/", "search/", "graph/", "chunking/", "merkle/")
                if any(chunk_id.startswith(d) for d in core_dirs):
                    result["blended_score"] = round(result["blended_score"] * 1.1, 4)

                # Test/verification code demotion (generalizable pattern)
                chunk_id = result.get("chunk_id", "")
                file_path = chunk_id.split(":")[0] if ":" in chunk_id else ""
                is_test_code = any(
                    pattern in file_path.lower()
                    for pattern in (
                        "test_",
                        "_test.",
                        "tests/",
                        "verify_",
                        "verification",
                    )
                )
                query_has_test_intent = any(
                    w in query_lower
                    for w in ("test", "testing", "verify", "verification")
                )
                if is_test_code and not query_has_test_intent:
                    result["blended_score"] = round(result["blended_score"] * 0.85, 4)

                # Config/settings file demotion (analogous to test demotion above)
                is_config_code = any(
                    pattern in file_path.lower()
                    for pattern in ("config.py", "settings.py", "constants.py")
                )
                query_has_config_intent = any(
                    w in query_lower
                    for w in ("config", "configuration", "setting", "constant")
                )
                if is_config_code and not query_has_config_intent:
                    result["blended_score"] = round(result["blended_score"] * 0.88, 4)

                # Name-match boost: extract name from chunk_id when field absent
                chunk_id = result.get("chunk_id", "")
                name = result.get("name", "") or _extract_name_from_chunk_id(chunk_id)

                # Lifecycle method demotion (e.g., __init__, __exit__)
                # Prevents boilerplate methods from displacing core logic unless specifically requested
                lifecycle_methods = {
                    "__init__",
                    "__enter__",
                    "__exit__",
                    "__del__",
                    "__repr__",
                    "__str__",
                }
                terminal_name = name.split(".")[-1] if "." in name else name
                if terminal_name in lifecycle_methods:
                    query_has_lifecycle_intent = any(
                        w in query_lower
                        for w in ("init", "enter", "exit", "del", "repr", "lifecycle")
                    )
                    if not query_has_lifecycle_intent:
                        result["blended_score"] = round(
                            result["blended_score"] * 0.85, 4
                        )

                if name and query_lower:
                    query_tokens = _tokenize_for_matching(
                        query
                    )  # Preserve CamelCase for splitting
                    name_tokens = _tokenize_for_matching(name)
                    if name_tokens:
                        # Name-centric overlap: what fraction of the NAME appears in query?
                        # This avoids penalizing name-match for long queries
                        overlap = len(query_tokens & name_tokens) / len(name_tokens)
                        pre_boost_score = result["blended_score"]
                        boost_multiplier = 1.0
                        if overlap >= 0.8:
                            result["blended_score"] = round(
                                result["blended_score"] * 1.3, 4
                            )
                            boost_multiplier = 1.3
                        elif overlap >= 0.5:
                            result["blended_score"] = round(
                                result["blended_score"] * 1.2, 4
                            )
                            boost_multiplier = 1.2
                        elif overlap >= 0.3:
                            result["blended_score"] = round(
                                result["blended_score"] * 1.1, 4
                            )
                            boost_multiplier = 1.1

                        if boost_multiplier > 1.0:
                            logger.debug(
                                f"[CENTRALITY] Name-match boost {boost_multiplier}x for '{name}': "
                                f"overlap={overlap:.2f}, tokens={query_tokens & name_tokens}, "
                                f"score {pre_boost_score:.4f} → {result['blended_score']:.4f}"
                            )

        # Sort by blended score descending
        results.sort(key=lambda r: r.get("blended_score", 0.0), reverse=True)

        logger.debug(
            f"[CENTRALITY] Reranked {len(results)} results (alpha={blend_alpha:.2f})"
        )

        return results
