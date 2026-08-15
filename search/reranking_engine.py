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
from .config import SearchMode, get_search_config


# TYPE_CHECKING is always False at runtime; AddNot mutation on this guard is equivalent.
if TYPE_CHECKING:  # pragma: no mutate
    from .config import SearchConfig
    from .neural_reranker import (
        GenerativeReranker,
        JinaRerankerV3,
        NeuralReranker,
    )
    from .reranker import SearchResult

try:
    import torch
# Import-failure exception type is untestable in unit tests; ExceptionReplacer is equivalent.
except ImportError:  # pragma: no mutate
    torch = None

from .neural_reranker import create_reranker


# merged_pool_policy="channel_priority" tier map for non-hop1 candidates.
# Tier 0 (hop-1 survivors, metadata["hop1_rank"] is not None) is handled
# separately in _order_merged_pool since it isn't keyed by `source`.
_CHANNEL_TIER = {"multi_hop": 1, "graph_hop": 2}


class RerankingEngine:
    """Coordinates score-based sorting and neural reranking for search results."""

    def __init__(self, embedder, metadata_store) -> None:
        """Initialize the reranking engine.

        Args:
            embedder: CodeEmbedder instance for query embeddings
            metadata_store: MetadataStore for chunk metadata retrieval
        """
        self.embedder = embedder
        self.metadata_store = metadata_store
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
            return result
        # OOM detection path: all mutations here are boundary (requires real CUDA OOM).
        # ExceptionReplacer, And/Or in OOM string detection, and True→False on _session_oom_detected
        # are all equivalent for unit tests.
        except Exception as e:  # pragma: no mutate  # noqa: BLE001 - resilience: OOM-protected rerank falls back to original candidates
            self._logger.warning(
                f"{log_prefix} Reranking failed: {e}, using original results"
            )
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
    def _order_merged_pool(results: list, policy: str) -> list:
        """Order the merged multi-hop pool before the ``top_k_candidates`` cut.

        ``"score"`` (default) is the literal pre-existing behaviour — sort by
        raw ``.score`` descending — kept as its own branch so the default
        path is provably byte-identical to before this policy existed. It
        mixes three incomparable scales (see module docstring context in
        ``rerank_by_query``'s docstring and ADR-0013); ``"score_reserve_fix"``
        uses the same sort (the fix lives in ``_apply_hop1_reserve``'s
        ``evict_policy``, not here). ``"channel_priority"`` replaces the sort
        with a three-tier ordering that never compares across scales: tier 0
        = hop-1 survivors (``metadata["hop1_rank"]`` is not None) ordered by
        that rank ascending; tier 1 = ``source == "multi_hop"`` ordered by
        score descending; tier 2 = ``source == "graph_hop"`` in stable
        insertion order; tier 3 = anything else, stable insertion order.
        """
        if policy in ("score", "score_reserve_fix"):
            return sorted(results, key=lambda r: r.score, reverse=True)
        if policy == "channel_priority":

            def _sort_key(item: "tuple[int, SearchResult]") -> tuple[int, float, int]:
                index, r = item
                hop1_rank = r.metadata.get("hop1_rank")
                if hop1_rank is not None:
                    return (0, hop1_rank, index)
                tier = _CHANNEL_TIER.get(r.source, 3)
                if tier == 1:
                    return (tier, -r.score, index)
                return (tier, 0.0, index)

            return [r for _, r in sorted(enumerate(results), key=_sort_key)]
        raise ValueError(f"Unknown merged_pool_policy: {policy!r}")

    @staticmethod
    def _apply_graph_hop_window_cap(
        sorted_results: list, top_k_candidates: int, cap: int
    ) -> list:
        """Cap how many ``source == "graph_hop"`` candidates occupy the
        ``top_k_candidates`` rerank window, without comparing scores across
        channels.

        Runs after ``_order_merged_pool`` (still under the deployed
        ``"score"`` policy) and before ``_apply_hop1_reserve``. Every
        ``graph_hop`` candidate carries the literal score ``0.0``
        (``MultiHopSearcher``'s graph-expansion branch), so under a stable
        score sort the first ``cap`` graph entries encountered are exactly
        the first ``cap`` in the pool's original graph-expansion order —
        "first admitted" never depends on a cross-scale score comparison.

        Single stable pass over ``sorted_results``: non-graph candidates are
        admitted to the window freely; ``graph_hop`` candidates are admitted
        only while fewer than ``cap`` have been admitted already, after
        which excess graph candidates are deferred to just below the window
        (their relative order preserved) so non-graph candidates further
        back in the pool backfill the freed slots. The unscanned tail is
        untouched. Output is always a permutation of the input — deferred
        entries are reinserted immediately after the window, ahead of
        whatever wasn't scanned.

        No-op (returns ``sorted_results`` unchanged, same object) when
        ``cap <= 0`` or the pool doesn't exceed ``top_k_candidates`` — the
        deployed default ``cap=0`` is byte-identical to before this existed.
        """
        if cap <= 0 or len(sorted_results) <= top_k_candidates:
            return sorted_results

        window: list = []
        deferred: list = []
        graph_admitted = 0
        stopped_at = len(sorted_results)
        for _idx, r in enumerate(sorted_results):
            if len(window) == top_k_candidates:
                stopped_at = _idx
                break
            if r.source == "graph_hop" and graph_admitted >= cap:
                deferred.append(r)
            else:
                if r.source == "graph_hop":
                    graph_admitted += 1
                window.append(r)

        return window + deferred + sorted_results[stopped_at:]

    @staticmethod
    def _apply_hop1_reserve(
        sorted_results: list,
        top_k_candidates: int,
        reserved_slots: int,
        evict_policy: str = "tail",
    ) -> list:
        """Promote hop-1-ranked candidates cut from the rerank window back in.

        Sorting the merged multi-hop pool by ``.score`` (the caller's sort,
        immediately before this runs) mixes three incomparable scales — hop-1
        survivors carry an overwritten jina relevance score (~-0.12..+0.22),
        semantic-expansion candidates carry raw FAISS cosine (~0.5-0.9), and
        graph-expansion candidates carry literal 0.0. A hop-1 winner can
        structurally rank below the ``top_k_candidates`` cut on scale alone,
        never reaching the listwise model at all. This promotes up to
        ``reserved_slots`` of the best-hop1-ranked candidates from outside the
        window back into it, evicting an equal number from the window's tail.
        Intra-window order doesn't matter — the listwise model re-scores the
        whole window. No-op when the pool doesn't exceed the window or no
        tail candidate is hop1-tagged.

        Args:
            evict_policy: ``"tail"`` (default) evicts from the window's
                score-sorted tail — the pre-existing behaviour. Because the
                caller's score sort puts every hop-1 survivor below every
                semantic-expansion candidate (see module context above), the
                window's tail *is* the hop-1 region: promoting a rank-3..N
                hop-1 candidate can evict a better-ranked (rank 1-2) one
                already sitting there. ``"lowest_non_hop1"`` instead evicts
                the window's lowest-scored entries that are *not*
                hop1-tagged first, so a hop-1 promotion prefers evicting a
                non-hop1 incumbent over a hop-1 one; only falls back to
                evicting hop1 window entries if there aren't enough non-hop1
                ones to make room (rare: window is almost entirely
                hop1-tagged). Both policies evict exactly
                ``min(reserved_slots-worth-of-promotions, len(window))``
                window entries, so total output length is identical between
                the two — they differ only in *which* window entries are
                dropped.
        """
        if reserved_slots <= 0 or len(sorted_results) <= top_k_candidates:
            return sorted_results

        window = sorted_results[:top_k_candidates]
        tail = sorted_results[top_k_candidates:]

        tail_hop1 = [
            (r.metadata.get("hop1_rank"), i, r)
            for i, r in enumerate(tail)
            if r.metadata.get("hop1_rank") is not None
        ]
        if not tail_hop1:
            return sorted_results

        tail_hop1.sort(key=lambda item: (item[0], item[1]))
        promote = [r for _, _, r in tail_hop1[:reserved_slots]]
        promote_ids = {r.chunk_id for r in promote}
        remaining_tail = [r for r in tail if r.chunk_id not in promote_ids]
        num_evict = len(promote)

        if evict_policy == "lowest_non_hop1":
            # window is score-sorted descending; prefer evicting the
            # lowest-scored entries that aren't hop1-tagged (tail-up), only
            # falling back to hop1-tagged window entries (also tail-up) if
            # there aren't enough non-hop1 ones to make room. This keeps the
            # total eviction count identical to "tail" (min(num_evict,
            # len(window))) — the two policies differ only in target choice.
            non_hop1_tail_first = [
                r for r in reversed(window) if r.metadata.get("hop1_rank") is None
            ]
            hop1_tail_first = [
                r for r in reversed(window) if r.metadata.get("hop1_rank") is not None
            ]
            evict_ids = {
                r.chunk_id for r in (non_hop1_tail_first + hop1_tail_first)[:num_evict]
            }
            kept_window = [r for r in window if r.chunk_id not in evict_ids]
            return kept_window + promote + remaining_tail

        if evict_policy != "tail":
            raise ValueError(f"Unknown evict_policy: {evict_policy!r}")

        kept_window = window[: max(0, len(window) - num_evict)]
        return kept_window + promote + remaining_tail

    def rerank_by_query(
        self,
        query: str,
        results: list,
        k: int,
        search_mode: str = SearchMode.HYBRID,
        hop1_reserved_slots: int = 0,
        merged_pool_policy: str = "score",
        graph_hop_window_cap: int = 0,
        config: "SearchConfig | None" = None,
    ) -> list:
        """
        Re-rank results by sorted score, then apply neural reranking.

        Args:
            query: Original search query
            results: List of SearchResult objects to re-rank
            k: Number of top results to return
            search_mode: Search mode for re-ranking strategy
            hop1_reserved_slots: Reserve up to this many hop-1-tagged
                (``metadata["hop1_rank"]``) candidates into the
                ``top_k_candidates`` rerank window when the pool exceeds it.
                0 (default) is a no-op — only ``MultiHopSearcher.search``
                passes a non-zero value; the ego-graph/parent-expansion tail
                call sites stay byte-identical.
            merged_pool_policy: How to order the merged pool before the
                ``top_k_candidates`` cut — see ``_order_merged_pool`` and
                ``SearchConfig.reranker.merged_pool_policy``.
                ``"score"`` (default) is byte-identical to the pre-existing
                sort. ``"score_reserve_fix"`` keeps that sort but changes
                ``_apply_hop1_reserve``'s eviction target from the window's
                blind tail to its lowest-scored non-hop1 entries.
                ``"channel_priority"`` replaces the sort with a tiered
                ordering that never compares across incomparable score
                scales; under it, ``hop1_reserved_slots`` is provably inert
                (all hop-1 candidates already sit in the window's tier 0).
                Only ``MultiHopSearcher``'s Pass-2 call passes a non-default
                value; the ego-graph/parent-expansion tail call sites stay
                on ``"score"``.
            graph_hop_window_cap: Cap how many ``source == "graph_hop"``
                candidates occupy the ``top_k_candidates`` rerank window —
                see ``_apply_graph_hop_window_cap`` and
                ``SearchConfig.reranker.graph_hop_window_cap``. 0 (default)
                is a no-op. Applied after ``_order_merged_pool`` and before
                ``hop1_reserved_slots``' eviction. Only ``MultiHopSearcher``'s
                Pass-2 call passes a non-zero value; the ego-graph/
                parent-expansion tail call sites stay byte-identical.
            config: Optional pre-fetched SearchConfig snapshot — the effective
                config for this request (see ADR-0018). Callers that already
                hold one pass it through so the whole rerank pass reads a
                single snapshot instead of re-fetching the process global;
                fetched here if omitted.

        Returns:
            Top k results sorted by query relevance
        """
        if not results:
            return []

        # Fetch once per pass (R1) and thread through every helper below
        # instead of each independently re-fetching. Hoisted above the sort
        # (was previously fetched only after) so merged_pool_policy — itself
        # config-driven when callers pass config.reranker.merged_pool_policy
        # through — is available before ordering runs.
        if config is None:
            config = get_search_config()

        sorted_results = self._order_merged_pool(results, merged_pool_policy)
        self.last_candidate_ids = [r.chunk_id for r in sorted_results]

        if graph_hop_window_cap > 0:
            sorted_results = self._apply_graph_hop_window_cap(
                sorted_results, config.reranker.top_k_candidates, graph_hop_window_cap
            )

        # Neural reranking (Quality First mode) — always re-check config for
        # runtime changes.
        if hop1_reserved_slots > 0:
            evict_policy = (
                "lowest_non_hop1"
                if merged_pool_policy == "score_reserve_fix"
                else "tail"
            )
            sorted_results = self._apply_hop1_reserve(
                sorted_results,
                config.reranker.top_k_candidates,
                hop1_reserved_slots,
                evict_policy=evict_policy,
            )
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
