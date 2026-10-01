"""Reranking engine for result quality improvement.

Coordinates score-based sorting and neural reranking for search result
quality improvement. (The embedding-based cosine re-score this used to
also coordinate was removed — verified dead code, see rerank_by_query.)
"""

import logging
import time
from typing import TYPE_CHECKING

from utils.timing import timed

from .chunk_id import dedupe_results
from .config import get_search_config
from .rerank_window_policy import RerankWindowPolicy
from .types import ResultSource


# TYPE_CHECKING is always False at runtime; AddNot mutation on this guard is equivalent.
if TYPE_CHECKING:  # pragma: no mutate
    from .config import SearchConfig
    from .neural_reranker import (
        GenerativeReranker,
        JinaRerankerV3,
        NeuralReranker,
    )

try:
    import torch
# Import-failure exception type is untestable in unit tests; ExceptionReplacer is equivalent.
except ImportError:  # pragma: no mutate
    torch = None

from .neural_reranker import create_reranker


# RerankWindowPolicy is frozen, so one shared instance is safe as a default —
# module-level singleton instead of calling .tail() in the signature (B008).
_TAIL_WINDOW = RerankWindowPolicy.tail()


class RerankingEngine:
    """Coordinates score-based sorting and neural reranking for search results."""

    def __init__(self) -> None:
        """Initialize the reranking engine."""
        # Type annotation only; | union operators have no runtime effect.
        self.neural_reranker: (
            NeuralReranker
            | GenerativeReranker  # pragma: no mutate
            | JinaRerankerV3  # pragma: no mutate
            | None  # pragma: no mutate
        ) = None
        self._neural_reranking_enabled: bool | None = None
        self._session_oom_detected: bool = False
        # Pool-hit-rate instrumentation (R0): chunk IDs of the fused candidate
        # pool that entered the most recent rerank pass, recorded regardless of
        # whether neural reranking actually ran. Benchmarks read this to
        # distinguish retrieval misses (gold absent from pool) from ranking
        # misses (gold in pool but ranked below the cutoff). Not thread-safe —
        # meaningful only for single-threaded benchmark/diagnostic use.
        self.last_candidate_ids: list[str] | None = None
        # Chunk IDs actually handed to the listwise model (the
        # top_k_candidates-sized slice of last_candidate_ids, post hop1-reserve
        # promotion). Lets diagnostics distinguish pool membership from window
        # membership — see docs/adr/0013-hop1-reserve-at-final-pool.md.
        self.last_window_ids: list[str] | None = None
        # Reranker CUDA OOM fix (see
        # docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md):
        # recorded by _run_rerank alongside last_window_ids, same "last pass
        # wins" semantics. last_block_count is the number of packed listwise
        # blocks the most recent rerank pass split into (None when the
        # reranker isn't a JinaRerankerV3, or doesn't expose the mechanism —
        # e.g. v3.5, or no rerank has run yet). last_rerank_skipped is True
        # when that pass fell back to unreranked candidates (OOM or any
        # other rerank failure), mirroring the graceful-degradation path
        # below rather than a new failure mode.
        self.last_block_count: int | None = None
        # ADR-0077 single-block invariant: mirrors last_block_count's "last
        # pass wins" semantics for the uniform per-document token cap
        # JinaRerankerV3._fit_single_block solved (getattr'd the same way,
        # since NeuralReranker/GenerativeReranker don't set it either).
        # Offline observability only — see
        # scripts/benchmark/probe_rerank_window.py.
        self.last_doc_token_cap: int | None = None
        self.last_rerank_skipped: bool = False
        self._logger = logging.getLogger(__name__)

    def should_enable_neural_reranking(
        self, config: "SearchConfig | None" = None
    ) -> bool:
        """Check if VRAM is sufficient for neural reranking.

        Args:
            config: Optional pre-fetched SearchConfig snapshot. Callers that already
                hold one for this rerank pass (R1) pass it through to avoid a
                redundant get_search_config() call; fetched here if omitted.

        Returns:
            bool: True if VRAM is sufficient and feature is enabled
        """
        # Early exit if OOM already detected in this search session
        if self._session_oom_detected:
            self._logger.debug(
                "Neural reranking skipped: OOM detected earlier in session"
            )
            return False

        try:
            if config is None:
                config = get_search_config()
            if not hasattr(config, "reranker") or not config.reranker.enabled:
                return False

            min_vram = config.reranker.min_vram_gb
            # or→and mutation equivalent under torch mock (not torch is always False in tests).
            if not torch or not torch.cuda.is_available():  # pragma: no mutate
                self._logger.warning("Neural reranking disabled: No GPU available")
                return False

            # If RAM fallback is allowed, skip VRAM threshold check
            if hasattr(config, "performance") and config.performance.allow_ram_fallback:
                self._logger.info(
                    "Neural reranking enabled: allow_ram_fallback=True (will use system RAM if needed)"
                )
                return True

            # Get actual free memory from CUDA driver (accounts for all processes)
            free_memory, total_memory = torch.cuda.mem_get_info(0)
            # 1023/1025 NumberReplacer mutations are near-equivalent (<0.3% VRAM difference).
            free_gb = free_memory / (1024**3)  # pragma: no mutate

            # GtE→Gt mutation only differs at exact float equality — not reachable in practice.
            if free_gb >= min_vram:  # pragma: no mutate
                self._logger.info(
                    f"Neural reranking enabled: {free_gb:.1f}GB available >= {min_vram}GB required"
                )
                return True
            else:
                self._logger.warning(
                    f"Neural reranking disabled: {free_gb:.1f}GB available < {min_vram}GB required"
                )
                return False
        # VRAM-check exception path: ExceptionReplacer and ReplaceFalseWithTrue are
        # equivalent for unit tests (exception is unreachable with mocked torch).
        except Exception as e:  # pragma: no mutate  # noqa: BLE001 - resilience: VRAM check failure disables neural reranking
            self._logger.warning(f"VRAM check failed, disabling neural reranking: {e}")
            return False  # pragma: no mutate

    def _ensure_reranker(
        self, log_prefix: str, config: "SearchConfig | None" = None
    ) -> bool:
        """Lazy-init, swap, or cleanup neural reranker based on current VRAM/config state.

        Updates self._neural_reranking_enabled and self.neural_reranker.
        Returns True if reranking is available (enabled and loaded).

        Args:
            log_prefix: Prefix for log messages.
            config: Optional pre-fetched SearchConfig snapshot (R1); fetched once
                here if omitted, and passed to should_enable_neural_reranking() so
                the enable-check and this method see the same config snapshot.

        Note: like the existing create-branch, the swap-branch below has no lock around
        it. RerankingEngine is a single instance shared across concurrent
        HybridSearcher.search() calls (each offloaded via asyncio.to_thread), so two
        requests detecting a swap at the same time could each build a new reranker and
        the loser's instance would be discarded without cleanup(). Pre-existing gap,
        not introduced by the swap branch — same race already existed for the create
        branch's `self.neural_reranker is None` check.
        """
        if config is None:
            config = get_search_config()
        should_enable = self.should_enable_neural_reranking(config)

        # and/or mutations here are boundary orchestration; equivalent under the test suite's
        # mock setup (create_reranker is mocked, _ensure_reranker is not called directly).
        if should_enable and self.neural_reranker is None:  # pragma: no mutate
            self.neural_reranker = create_reranker(
                model_name=config.reranker.model_name,
                batch_size=config.reranker.batch_size,
                instruction=config.reranker.instruction or None,
                doc_max_chars=config.reranker.doc_max_chars,
                listwise_doc_max_chars=config.reranker.listwise_doc_max_chars,
                listwise_dtype=config.reranker.listwise_dtype,
                doc_representation_mode=config.reranker.doc_representation_mode,
                listwise_packed_token_budget=config.reranker.listwise_packed_token_budget,
                listwise_window_fit=config.reranker.listwise_window_fit,
            )
            self._logger.debug(f"{log_prefix} Neural reranker initialized")
        elif (
            should_enable
            and self.neural_reranker is not None
            and self.neural_reranker.model_name != config.reranker.model_name
        ):
            # configure_reranking(model_name=...) only takes effect on the next search if
            # we actually detect the change here — without this branch, a loaded reranker
            # instance is never replaced, and the config change is silently a no-op.
            self._logger.info(
                f"{log_prefix} Reranker model changed "
                f"({self.neural_reranker.model_name} -> {config.reranker.model_name}), reloading"
            )
            self.neural_reranker.cleanup()
            self.neural_reranker = create_reranker(
                model_name=config.reranker.model_name,
                batch_size=config.reranker.batch_size,
                instruction=config.reranker.instruction or None,
                doc_max_chars=config.reranker.doc_max_chars,
                listwise_doc_max_chars=config.reranker.listwise_doc_max_chars,
                listwise_dtype=config.reranker.listwise_dtype,
                doc_representation_mode=config.reranker.doc_representation_mode,
                listwise_packed_token_budget=config.reranker.listwise_packed_token_budget,
                listwise_window_fit=config.reranker.listwise_window_fit,
            )
        elif not should_enable and self.neural_reranker is not None:
            self.neural_reranker.cleanup()
            self.neural_reranker = None
            self._logger.debug(f"{log_prefix} Neural reranker disabled and cleaned up")

        self._neural_reranking_enabled = should_enable
        return bool(
            should_enable and self.neural_reranker is not None  # pragma: no mutate
        )

    def _run_rerank(
        self,
        query_or_content: str,
        candidates: list,
        k: int,
        log_prefix: str,
        config: "SearchConfig | None" = None,
    ) -> list:
        """OOM-protected timed rerank call.

        Returns reranked results on success, or candidates unchanged on failure.

        Args:
            config: Optional pre-fetched SearchConfig snapshot (R1); fetched here
                if omitted.
        """
        assert (
            self.neural_reranker is not None
        )  # guaranteed by _ensure_reranker() caller gate
        if config is None:
            config = get_search_config()
        rerank_count = min(config.reranker.top_k_candidates, len(candidates))
        self.last_window_ids = [r.chunk_id for r in candidates[:rerank_count]]
        neural_start = time.time()

        try:
            result = self.neural_reranker.rerank(
                query_or_content, candidates[:rerank_count], k
            )
            # Timing value only used in log message — arithmetic mutations are log-only.
            neural_time = time.time() - neural_start  # pragma: no mutate
            self._logger.debug(
                f"{log_prefix} Processed {rerank_count} candidates in {neural_time:.3f}s"
            )
            # See docs/adr/0076-bound-the-listwise-packed-window-by-tokens.md —
            # getattr rather than a direct read since only JinaRerankerV3 sets
            # last_block_count (NeuralReranker/GenerativeReranker don't).
            self.last_block_count = getattr(
                self.neural_reranker, "last_block_count", None
            )
            self.last_doc_token_cap = getattr(
                self.neural_reranker, "last_doc_token_cap", None
            )
            self.last_rerank_skipped = False
            # Backfill (ADR-0079): candidates past the window are never dropped.
            # The listwise pass scores only the first ``rerank_count``; the rest
            # keep their incoming order behind the reranked window. A no-op
            # whenever the candidate list fits the window.
            if len(candidates) > rerank_count:
                return [*result, *candidates[rerank_count:]]
            return result
        # OOM detection path: all mutations here are boundary (requires real CUDA OOM).
        # ExceptionReplacer, And/Or in OOM string detection, and True→False on _session_oom_detected
        # are all equivalent for unit tests.
        except Exception as e:  # pragma: no mutate  # noqa: BLE001 - resilience: OOM-protected rerank falls back to original candidates
            self._logger.warning(
                f"{log_prefix} Reranking failed: {e}, using original results"
            )
            self.last_block_count = None
            self.last_doc_token_cap = None
            self.last_rerank_skipped = True
            error_str = str(e).lower()
            if "cuda" in error_str and (  # pragma: no mutate
                "out of memory" in error_str or "oom" in error_str  # pragma: no mutate
            ):  # pragma: no mutate
                self._session_oom_detected = True  # pragma: no mutate
                self._logger.warning(
                    f"{log_prefix} CUDA OOM detected, disabling for session"
                )
            return candidates

    @staticmethod
    def _order_merged_pool(results: list, interleave: bool) -> list:
        """Order the pool before the ``top_k_candidates`` cut.

        ``interleave=True`` (MultiHopSearcher's Pass-2, ADR-0079) decides
        window membership by alternating hop-1 survivors with the expansion
        frontier (``_gar_interleave``); it never compares a score across
        channels. ``interleave=False`` (the tail pass, ``single_pass``) sorts
        by raw ``.score`` descending, which is sound there because every
        candidate carries a score from one scale.
        """
        if interleave:
            return RerankingEngine._gar_interleave(results)
        return sorted(results, key=lambda r: r.score, reverse=True)

    @staticmethod
    def _gar_interleave(results: list) -> list:
        """GAR-style window membership (ADR-0079): alternate 1:1 between hop-1
        survivors and the frontier, never comparing a score across channels.

        Hop-1 survivors (``metadata["hop1_rank"]`` is not None -- NOT
        ``source``: both hop-1 survivors and semantic expansions are
        ``"multi_hop"``) go in ``hop1_rank`` order and take the first slot.
        The frontier is every other candidate: ordered by ``anchor_rank`` (the
        best hop-1 rank among the anchors that produced it), and inside one
        anchor alternating the graph channel and the semantic channel, graph
        first (``MultiHopSearcher._hybrid_expand`` runs the graph channel
        first), each in its incoming order. A frontier candidate without an
        ``anchor_rank`` sorts after every anchored one. When one side runs
        out the other fills the rest, so the output is a permutation of the
        input. See ``evaluation/GAR_WINDOW_AB_20261001.md`` for the offline
        simulation that picked anchor-first over round-robin.
        """
        hop1 = sorted(
            (r for r in results if r.metadata.get("hop1_rank") is not None),
            key=lambda r: r.metadata["hop1_rank"],
        )
        by_anchor: dict[float, tuple[list, list]] = {}
        for r in results:
            if r.metadata.get("hop1_rank") is not None:
                continue
            anchor = r.metadata.get("anchor_rank")
            graph, other = by_anchor.setdefault(
                float("inf") if anchor is None else anchor, ([], [])
            )
            (graph if r.source == ResultSource.GRAPH_HOP else other).append(r)

        frontier: list = []
        for anchor in sorted(by_anchor):
            graph, other = by_anchor[anchor]
            for i in range(max(len(graph), len(other))):
                if i < len(graph):
                    frontier.append(graph[i])
                if i < len(other):
                    frontier.append(other[i])

        ordered: list = []
        for i in range(max(len(hop1), len(frontier))):
            if i < len(hop1):
                ordered.append(hop1[i])
            if i < len(frontier):
                ordered.append(frontier[i])
        return ordered

    def rerank_by_query(
        self,
        query: str,
        results: list,
        k: int,
        config: "SearchConfig",
        window: RerankWindowPolicy = _TAIL_WINDOW,
    ) -> list:
        """
        Re-rank results by sorted score, then apply neural reranking.

        Args:
            query: Original search query
            results: List of SearchResult objects to re-rank
            k: Number of top results to return
            config: The effective SearchConfig snapshot for this request (see
                ADR-0018). Required — callers hold one already, so the whole
                rerank pass reads a single snapshot instead of each helper
                independently re-fetching the process global.
            window: Which rerank pass this is — see CONTEXT.md's "Rerank
                pass" glossary entry and ``RerankWindowPolicy``.
                ``RerankWindowPolicy.tail()`` (default) is the post-expansion
                pass: plain score order, real scores.
                ``RerankWindowPolicy.merged_pool()`` is ``MultiHopSearcher``'s
                Pass-2 over the merged pool, with window membership decided by
                interleave (ADR-0079); the ego-graph/parent-expansion tail
                call sites always pass ``tail()``.

        Returns:
            Top k results sorted by query relevance
        """
        if not results:
            return []

        sorted_results = self._order_merged_pool(results, window.interleave)
        self.last_candidate_ids = [r.chunk_id for r in sorted_results]

        # Neural reranking (Quality First mode) — always re-check config for
        # runtime changes.
        if sorted_results and self._ensure_reranker("[RERANK]", config=config):
            sorted_results = self._run_rerank(
                query, sorted_results, k, "[NEURAL_RERANK]", config=config
            )

        # Collapse split_block fragments before truncation so freed slots
        # backfill with distinct chunks. Not applied at hop-1
        # (apply_neural_reranking) — deduping there would shrink the
        # multi-hop/ego expansion-seed pool.
        if config.reranker.dedupe_split_blocks:
            sorted_results = dedupe_results(sorted_results)

        return sorted_results[:k]

    # RemoveDecorator on @timed is equivalent — decorator adds timing metadata only.
    @timed("neural_rerank")  # pragma: no mutate
    def apply_neural_reranking(
        self,
        query_or_content: str,
        results: list,
        k: int,
        context: str = "search",
        config: "SearchConfig | None" = None,
    ) -> list:
        """
        Apply neural reranking with automatic lifecycle management.

        Consolidates duplicate lifecycle logic from HybridSearcher methods.
        Handles lazy initialization, VRAM checks, and cleanup automatically.

        Args:
            query_or_content: Query string or reference content for reranking
            results: List of SearchResult objects to rerank
            k: Number of top results to return
            context: Context identifier for logging ("search" or "similarity")
            config: Optional pre-fetched SearchConfig snapshot — the effective
                config for this request (see ADR-0018). Callers that already
                hold one pass it through so the whole rerank pass reads a
                single snapshot instead of re-fetching the process global;
                fetched here if omitted.

        Returns:
            Reranked results (or original results if neural reranking unavailable)
        """
        # not/double-not mutations on guard and _ensure_reranker are boundary orchestration.
        if not results:  # pragma: no mutate
            return []
        self.last_candidate_ids = [r.chunk_id for r in results]
        # Fetch config once per pass (R1) and thread through both helpers.
        if config is None:
            config = get_search_config()
        if not self._ensure_reranker(  # pragma: no mutate
            f"[RERANK-{context.upper()}]", config=config
        ):  # pragma: no mutate
            return results
        return self._run_rerank(
            query_or_content,
            results,
            k,
            f"[NEURAL_RERANK-{context.upper()}]",
            config=config,
        )

    def reset_session_state(self) -> None:
        """Reset session-level OOM tracking.

        Call at the start of each search request to allow reranking
        to be retried on new searches.
        """
        # False→True mutation: reset_session_state test not yet written; pragma as boundary.
        self._session_oom_detected = False  # pragma: no mutate

    def shutdown(self) -> None:
        """Cleanup neural reranker resources."""
        if self.neural_reranker:
            self.neural_reranker.cleanup()
            self.neural_reranker = None
            self._logger.debug("Neural reranker cleaned up")
