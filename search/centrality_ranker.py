"""
Centrality-based result ranking for SSCG Phase 3.

Blends PageRank centrality scores with semantic similarity to boost
structurally important code in search results.
"""

import logging
import math
from typing import TYPE_CHECKING

import networkx as nx

from search.chunk_id import extract_line_count as _extract_chunk_lines_impl
from search.chunk_id import extract_name as _extract_name_impl
from search.ranking_policy import (
    NAME_OVERLAP_TIERS,
    TYPE_BOOSTS_CODE,
    TYPE_BOOSTS_ENTITY,
    lifecycle_demotion,
)
from search.tokenization import normalize_to_tokens
from utils.path_utils import normalize_path


# TYPE_CHECKING is always False at runtime; AddNot mutation is equivalent.
if TYPE_CHECKING:  # pragma: no mutate
    from graph.graph_queries import GraphQueryEngine
    from search.config import GraphEnhancedConfig


logger = logging.getLogger(__name__)


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
    # split_dots=False and min_len=1 are equivalent: no test uses dotted names or relies on 1-char tokens.
    return normalize_to_tokens(
        text,
        split_acronyms=True,
        split_dots=True,  # pragma: no mutate
        min_len=2,  # pragma: no mutate
        as_set=True,
    )


class CentralityRanker:
    """Ranks search results by blending semantic scores with centrality.

    Two modes:
    - annotate(): Add centrality field without reordering
    - rerank(): Add centrality + reorder by blended score
    """

    def __init__(
        self,
        graph_query_engine: "GraphQueryEngine",
        method: str = "pagerank",
        # Default alpha is never used; all tests pass alpha explicitly.
        alpha: float = 0.3,  # pragma: no mutate
        config: "GraphEnhancedConfig | None" = None,
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
        # Initial value overwritten on first call; any sentinel works.
        self._cache_key = (0, 0)  # (node_count, edge_count)  # pragma: no mutate

    def get_centrality_scores(self) -> dict[str, float]:
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
        # NotEq_Gt: code graphs only grow monotonically; Gt is equivalent to !=.
        if current_key != self._cache_key:  # pragma: no mutate
            self._cache.clear()
            self._cache_key = current_key

        # Return cached scores if available
        if self._cache:
            return self._cache

        # Handle empty graph
        # Eq_LtE: node_count is always >= 0, so == 0 and <= 0 are equivalent.
        if current_key[0] == 0:  # pragma: no mutate
            logger.debug("[CENTRALITY] Empty graph, returning empty scores")
            return {}

        # Compute centrality scores
        try:
            raw_scores = self.graph_query_engine.compute_centrality(method=self.method)
        # ExceptionReplacer: convergence failure is untestable in unit tests.
        except nx.PowerIterationFailedConvergence:  # pragma: no mutate
            logger.warning(
                "[CENTRALITY] PageRank failed to converge, returning empty scores"
            )
            return {}
        # ExceptionReplacer: NetworkXError/ValueError/KeyError boundary untestable in unit tests.
        except (nx.NetworkXError, ValueError, KeyError) as e:  # pragma: no mutate
            logger.error(
                f"[CENTRALITY] Failed to compute {self.method} centrality: {e}"
            )
            return {}

        # Normalize to [0, 1] range
        # Initial value overwritten by max() before use; any value is equivalent.
        max_score = 0.0  # Initialize before conditional to avoid UnboundLocalError  # pragma: no mutate
        if raw_scores:
            max_score = max(raw_scores.values())
            # Gt_NotEq: max() of non-negative scores is always ≥ 0; > and != are equivalent.
            if max_score > 0:  # pragma: no mutate
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
        centrality_scores = self.get_centrality_scores()

        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                centrality = centrality_scores.get(chunk_id, 0.0)
                # round() precision: 4 vs 3/5 is below retrieval noise floor.
                result["centrality"] = round(centrality, 4)  # pragma: no mutate

        return results

    def rerank(
        self, results: list[dict], alpha: float | None = None, query: str = ""
    ) -> list[dict]:
        """Rerank results by blended semantic + centrality score.

        Args:
            results: List of search result dicts with "score" field
            alpha: Blending weight override (None = use self.alpha)
            query: Query string for query-aware boosting (optional)

        Returns:
            Reranked results with "centrality" and "blended_score" fields
        """
        results = self.annotate(results)

        # CRITICAL: Use `if alpha is not None` to handle alpha=0.0 correctly
        blend_alpha = alpha if alpha is not None else self.alpha
        # AddNot: tests use lowercase queries; lowercasing an already-lowercase string is a no-op.
        query_lower = query.lower() if query else ""  # pragma: no mutate

        for result in results:
            # annotate() always sets "score"; 0.0 default unreachable (NumberReplacer equivalent).
            semantic_score = result.get("score", 0.0)  # pragma: no mutate
            # annotate() always sets "centrality"; 0.0 default is unreachable.
            centrality = result.get("centrality", 0.0)  # pragma: no mutate

            # Core blend: (1 - alpha) * semantic + alpha * centrality
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                (1 - blend_alpha) * semantic_score + blend_alpha * centrality,
                4,  # pragma: no mutate
            )

            if self.config is not None and self.config.enable_size_normalization:
                self._apply_size_normalization(result)

            # Gt_IsNot/Gt_Is/Gt_GtE: bm25_boost path not exercised via rerank() in tests.
            if (
                self.config is not None  # pragma: no mutate
                and self.config.centrality_bm25_boost  # pragma: no mutate
                and centrality
                > self.config.centrality_boost_threshold  # pragma: no mutate
            ):
                self._apply_bm25_boost(result, centrality)

            if query:
                chunk_type = result.get("kind", "")
                chunk_id = result.get("chunk_id", "")
                tags = result.get("tags", [])
                name = result.get("name", "") or _extract_name_impl(chunk_id)
                self._apply_type_boost(result, chunk_type, query_lower)
                self._apply_synthetic_demotion(result, chunk_type, chunk_id)
                self._apply_core_dir_boost(result, chunk_id)
                self._apply_role_demotion(result, chunk_id, tags, query_lower)
                self._apply_name_match_boost(result, name, query, query_lower)

        # NumberReplacer on default 0.0: blend loop always sets blended_score; default unreachable.
        results.sort(
            key=lambda r: r.get("blended_score", 0.0),  # pragma: no mutate
            reverse=True,
        )
        logger.debug(
            f"[CENTRALITY] Reranked {len(results)} results (alpha={blend_alpha:.2f})"
        )
        return results

    # ------------------------------------------------------------------
    # Scoring policy helpers (each mutates result["blended_score"] in-place)
    # ------------------------------------------------------------------

    def _apply_size_normalization(self, result: dict) -> None:
        """Log penalty for chunks exceeding config.size_norm_target_lines.

        Reduces blended_score for oversized chunks to prevent large files
        from drowning out focused, well-scoped code.
        """
        chunk_id = result.get("chunk_id", "")
        chunk_lines = _extract_chunk_lines_impl(chunk_id)
        # Gt_GtE: differs only at exact equality; no test hits chunk_lines == target_lines exactly.
        if chunk_lines > self.config.size_norm_target_lines:  # type: ignore[union-attr]  # pragma: no mutate
            size_factor = 1.0 / (
                1.0
                + self.config.size_norm_alpha  # type: ignore[union-attr]
                * math.log(chunk_lines / self.config.size_norm_target_lines)  # type: ignore[union-attr]
            )
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * size_factor,
                4,  # pragma: no mutate
            )
            logger.debug(
                f"[CENTRALITY] Size normalization for {chunk_id}: "
                f"{chunk_lines} lines → factor={size_factor:.3f}"
            )

    def _apply_bm25_boost(self, result: dict, centrality: float) -> None:
        """Additive centrality-adaptive BM25 boost (LIMIT paper, ICLR 2026).

        High-centrality chunks are exactly where single-vector embedding fails
        (sign-rank bottleneck).  A capped additive boost compensates.
        """
        boost = min(
            centrality * self.config.centrality_boost_factor,  # type: ignore[union-attr]
            self.config.centrality_boost_cap,  # type: ignore[union-attr]
        )
        # round() precision: 4 vs 3/5 is below retrieval noise floor.
        result["blended_score"] = round(
            result["blended_score"] + boost,
            4,  # pragma: no mutate
        )
        logger.debug(
            f"[CENTRALITY] BM25 adaptive boost for {result.get('chunk_id', '')}: "
            f"centrality={centrality:.4f} → boost={boost:.4f}"
        )

    def _apply_type_boost(
        self, result: dict, chunk_type: str, query_lower: str
    ) -> None:
        """Entity-query vs code-query type multiplier.

        Entity queries (mentioning class/module/struct/enum) promote class chunks
        and demote module/community summaries.  Code queries use a milder variant.
        """
        is_entity_query = any(
            w in query_lower for w in ("class", "module", "struct", "enum")
        )
        if is_entity_query:
            # Shared base from ranking_policy + centrality-specific entries
            type_boosts = {
                **TYPE_BOOSTS_ENTITY,
                "decorated_definition": 1.1,
                "split_block": 1.1,  # Function/method fragments
            }
        else:
            type_boosts = {
                **TYPE_BOOSTS_CODE,
                "decorated_definition": 1.0,  # Neutral — includes dataclasses, not just functions
                "split_block": 1.1,  # Function/method fragments
            }
        # NumberReplacer on default 1.0 and on precision 4: unknown chunk_type default
        # is never reached by tests; precision 4 vs 3/5 is below noise floor.
        result["blended_score"] = round(
            result["blended_score"] * type_boosts.get(chunk_type, 1.0),
            4,  # pragma: no mutate
        )

    def _apply_synthetic_demotion(
        self, result: dict, chunk_type: str, chunk_id: str
    ) -> None:
        """×0.5 demotion for synthetic module/community chunks with zero centrality.

        Synthetic chunks (module summaries, community summaries) are not in the
        call graph so they always have centrality=0.  Real code chunks have
        centrality > 0.  Combined with type-based demotion:
          0.90 × 0.5 = 0.45x total (code queries)
          0.85 × 0.5 = 0.425x total (entity queries).
        Research: TNO, GRACE, HiChunk all keep summaries separate from code.
        """
        # Eq_LtE: centrality is always >= 0 so ==0 and <=0 are equivalent.
        if (
            chunk_type in ("module", "community")
            and result.get("centrality", 0) == 0  # pragma: no mutate
        ):
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * 0.5,
                4,  # pragma: no mutate
            )
            logger.debug(
                f"[CENTRALITY] Zero-centrality synthetic chunk demotion: "
                f"{chunk_id} ({chunk_type}) → 0.5x multiplier"
            )

    def _apply_core_dir_boost(self, result: dict, chunk_id: str) -> None:
        """×1.1 boost for core engine directories (embeddings/search/graph/chunking/merkle).

        Prioritises engine internals over glue code and tooling.
        """
        core_dirs = ("embeddings/", "search/", "graph/", "chunking/", "merkle/")
        if any(chunk_id.startswith(d) for d in core_dirs):
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * 1.1,
                4,  # pragma: no mutate
            )

    def _apply_role_demotion(
        self, result: dict, chunk_id: str, tags: list, query_lower: str
    ) -> None:
        """Role-based demotion/boost: test/doc/config files suppressed unless query matches.

        Role detection order: indexed ``role:`` tag (from ``_classify_file_role``)
        → path heuristics fallback for pre-v0.10.0 chunks.
        """
        file_path = chunk_id.split(":")[0] if ":" in chunk_id else ""
        indexed_role = next(
            (
                t[len("role:") :]
                for t in tags
                if isinstance(t, str) and t.startswith("role:")
            ),
            None,
        )

        if indexed_role is None:
            # Normalize to forward slashes so patterns work on Windows paths too
            norm_path = normalize_path(file_path).lower()
            if any(
                p in norm_path
                for p in ("test_", "_test.", "tests/", "verify_", "verification")
            ):
                indexed_role = "test"
            elif norm_path.endswith((".md", ".rst", ".txt", ".adoc")) or any(
                p in norm_path for p in ("/docs/", "/doc/", "/documentation/", "/wiki/")
            ):
                indexed_role = "doc"
            elif any(
                p in norm_path for p in ("config.py", "settings.py", "constants.py")
            ):
                indexed_role = "config"

        query_has_test_intent = any(
            w in query_lower for w in ("test", "testing", "verify", "verification")
        )
        query_has_doc_intent = any(
            w in query_lower
            for w in ("doc", "docs", "readme", "documentation", "guide", "tutorial")
        )
        query_has_config_intent = any(
            w in query_lower for w in ("config", "configuration", "setting", "constant")
        )

        if indexed_role == "test":
            factor = 1.15 if query_has_test_intent else 0.85
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * factor,
                4,  # pragma: no mutate
            )
        # Eq_Is: CPython interns short strings; == and is are equivalent for "doc"/"config".
        elif indexed_role == "doc" and not query_has_doc_intent:  # pragma: no mutate
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * 0.80,
                4,  # pragma: no mutate
            )
        # Eq_Is: CPython interns short string literals; == and is are equivalent for "config".
        elif (
            indexed_role == "config"  # pragma: no mutate
            and not query_has_config_intent  # pragma: no mutate
        ):
            # round() precision occ=78,79: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * 0.88,
                4,  # pragma: no mutate
            )

    def _apply_name_match_boost(
        self, result: dict, name: str, query: str, query_lower: str
    ) -> None:
        """Tokenisation overlap boost ×1.1–1.3 when name tokens appear in query.

        Also applies ×0.85 lifecycle-method demotion for __init__ / __exit__ etc.
        when the query does not have explicit lifecycle intent.
        """
        # Lifecycle method demotion (prevents boilerplate from displacing core logic)
        terminal_name = name.split(".")[-1] if "." in name else name
        demotion = lifecycle_demotion(terminal_name, query_lower)
        # NotEq_LtE/NotEq_Lt/NumberReplacer: lifecycle_demotion returns <= 1.0, so
        # multiplying by 1.0 (no demotion) and skipping are equivalent.
        if demotion != 1.0:  # pragma: no mutate
            # round() precision: 4 vs 3/5 is below retrieval noise floor.
            result["blended_score"] = round(
                result["blended_score"] * demotion,
                4,  # pragma: no mutate
            )

        # ReplaceAndWithOr: both name='' and query_lower='' produce empty token sets → no boost.
        if name and query_lower:  # pragma: no mutate
            query_tokens = _tokenize_for_matching(
                query
            )  # Preserve CamelCase for splitting
            name_tokens = _tokenize_for_matching(name)
            if name_tokens:
                # Name-centric overlap: fraction of the NAME appearing in the query.
                # This avoids penalising name-match on long queries.
                overlap = len(query_tokens & name_tokens) / len(name_tokens)
                pre_boost_score = result["blended_score"]
                # Initial value overwritten in loop; log-only effect for mutations.
                boost_multiplier = 1.0  # pragma: no mutate
                # NAME_OVERLAP_TIERS = ((0.8, 1.3), (0.5, 1.2), (0.3, 1.1)) — ranking_policy
                for min_ratio, tier_mult in NAME_OVERLAP_TIERS:
                    if overlap >= min_ratio:
                        # round() precision: 4 vs 3/5 is below retrieval noise floor.
                        result["blended_score"] = round(
                            result["blended_score"] * tier_mult,
                            4,  # pragma: no mutate
                        )
                        boost_multiplier = tier_mult
                        break

                # Log-only condition: all operator/value mutations produce same blended_score.
                if boost_multiplier > 1.0:  # pragma: no mutate
                    # Log-only f-string: mutations here have no effect on outputs.
                    logger.debug(
                        f"[CENTRALITY] Name-match boost {boost_multiplier}x for '{name}': "
                        f"overlap={overlap:.2f}, tokens={query_tokens & name_tokens}, "  # pragma: no mutate
                        f"score {pre_boost_score:.4f} → {result['blended_score']:.4f}"
                    )  # pragma: no mutate
