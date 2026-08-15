#!/usr/bin/env python
"""Probe whether hop-1 top-10 golds survive the multi-hop rerank window cut (read-only).

Background: ``evaluation/QUERY_EXPANSION_AB_20260728.md`` (root-cause section) observed
golden-set queries Q104/Q122 ranking 1 and 6 out of hop-1 (``MultiHopSearcher``), reaching
the merged expansion pool (~66-83 chunks at k=10), yet missing the final top-10. This probe
instruments the exact boundary between "gold is in the merged pool" and "gold is in the
window the listwise reranker actually scores" to distinguish three failure modes:

- **window-cut**: gold is in the merged pool (``multi_hop_searcher.py:478``) but falls
  outside ``candidates[:top_k_candidates]`` at the hard cut (``reranking_engine.py:217``) —
  the model never sees it.
- **model-demotion**: gold is inside the window but the listwise model still ranks it > k.
- **pool-loss**: gold never reached the merged pool at all (a pre-existing retrieval gap,
  out of scope for this probe).

Mechanism (three incomparable score scales feed the ``:270`` sort that determines the cut):
hop-1 survivors carry a jina relevance score overwritten in place
(``neural_reranker.py:1117-1119``, range observed ~+0.22..-0.12); semantic-expansion chunks
carry raw FAISS cosine (``multi_hop_searcher.py:141``, ~0.5-0.9); graph-expansion chunks carry
literal ``0.0`` (``multi_hop_searcher.py:227``). Sorting all three together at the merge-pool
rerank means cosine-scored expansion chunks systematically outrank hop-1 winners.

**Extended instrumentation** (per ``docs/plans/humming-wondering-phoenix.md``, Phase 1),
gated behind ``search/config.py``'s ``RerankerConfig.merged_pool_policy`` field
(``"score"`` default / ``"score_reserve_fix"`` / ``"channel_priority"`` — see
``search/reranking_engine.py``'s ``_order_merged_pool``/``_apply_hop1_reserve``):

- ``Instrumentation.pass2_call()``/``.pass2_window()``/``.pass3_calls()`` disambiguate the
  multi-hop merge-pool rerank (Pass 2) from the ego-graph/parent-expansion tail rerank
  (Pass 3) by ``rerank_by_query`` call **ordinal**, cross-checked against
  ``hop1_reserved_slots > 0`` (only Pass 2's dispatch ever passes a non-zero value) — *not*
  by list position or log prefix alone, since both passes share the
  ``"[NEURAL_RERANK]"`` prefix (``reranking_engine.py:458``); only Pass 1
  (``SearchExecutor.apply_neural_reranking``) uses the distinct ``"[NEURAL_RERANK-SEARCH]"``.
- ``simulate_windows()`` replays each query's captured Pass-2 pool (order/score/source/
  ``hop1_rank`` snapshot, taken pre-sort) through the **actual production**
  ``RerankingEngine._order_merged_pool``/``._apply_hop1_reserve`` static methods for every
  policy in ``SIMULATED_POLICIES`` — an offline counterfactual, not a re-run of the search
  pipeline, so all four policies are evaluated from one live pass per query.
- **Self-validity check**: ``simulate_windows(...)[<the policy actually configured for this
  run>]`` must equal the observed Pass-2 window on every query. Because the simulator calls
  the same production functions (not a reimplementation), a mismatch means the probe's
  *pool snapshot* is incomplete or stale — not that the simulator's logic drifted. A mismatch
  is a HALT condition (exit code 3): downstream predictions/gate numbers should not be
  trusted until it is fixed.
- Six pre-registered predictions (P1-P6) and gate criteria (A1 premise, A2 headroom, A3
  self-validity) are evaluated in ``compute_predictions()``/``evaluate_gate()`` and printed
  after the per-query sweep. ``--json-out PATH`` writes the full per-query + aggregate
  payload for offline analysis.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --query-id Q104,Q122 --dataset evaluation/golden_dataset_expanded.json --k 10

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --all --dataset evaluation/golden_dataset_expanded.json --k 10 \
        --json-out evaluation/probe_rerank_window_20260815.json

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --all --set reranker.merged_pool_policy=channel_priority

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --replay evaluation/probe_rerank_window_20260815.json --caps 2,3

Exit codes: 0 (GREEN) no window-cuts and self-validity holds everywhere; 1 (RED) at least
one grade-3 gold is window-cut; 2 on setup errors; 3 (HALT) self-validity diverged on at
least one query — treat P1-P6/A1-A3 as untrustworthy until investigated. ``--replay`` mode
uses its own G1/G2/G3 exit codes 0/1/3 (see ``run_replay()``); 2 still applies to setup
errors (bad ``--caps``, unreadable JSON) via the ordinary Python traceback.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import normalize_chunk_id  # noqa: E402


MERGE_LOG_PREFIX = "[NEURAL_RERANK]"

# Policies simulate_windows() replays through the ACTUAL production static methods
# (RerankingEngine._order_merged_pool / ._apply_hop1_reserve) against each query's captured
# Pass-2 pool. "score" and "score_reserve_fix" are real SearchConfig.reranker.
# merged_pool_policy values; "channel_priority" is the third. "score_no_reserve" is a
# probe-only synthetic variant (score ordering, hop1_reserved_slots forced to 0) that
# isolates ordering from eviction for prediction P4 (finding E).
SIMULATED_POLICIES = (
    "score",
    "score_no_reserve",
    "score_reserve_fix",
    "channel_priority",
)

# Cap values simulate_cap_windows() replays for the graph_hop_window_cap probe
# (docs/plans/humming-wondering-phoenix.md follow-on, --replay mode). cap=0 is
# the no-op baseline -- byte-identical to SIMULATED_POLICIES's "score" entry --
# and is always included as the comparison point for gold rescue/eviction
# deltas (see _cap_gold_net).
SIMULATED_CAPS = (0, 2, 3, 4, 5)


def load_queries(dataset_path: Path, query_ids: list[str] | None) -> list[dict]:
    """Return golden-dataset entries, optionally filtered to ``query_ids``.

    Excludes category D (call-graph queries this probe's plain ``search()`` call cannot
    evaluate, matching the benchmark harness default) and category F (scored via
    ``find_similar_code`` anchors, a different pipeline this probe does not exercise).
    """
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = [q for q in data["queries"] if q.get("category") not in ("D", "F")]
    if query_ids:
        wanted = set(query_ids)
        items = [q for q in items if q["id"] in wanted]
        missing = wanted - {q["id"] for q in items}
        if missing:
            raise KeyError(
                f"query id(s) not found (or excluded D/F): {sorted(missing)}"
            )
    return items


class _SimResult:
    """Minimal stand-in for ``search.reranker.SearchResult``, sufficient for
    ``RerankingEngine._order_merged_pool``/``._apply_hop1_reserve`` — both only touch
    ``.chunk_id``, ``.score``, ``.source``, and ``.metadata['hop1_rank']``. Built from the
    probe's captured Pass-2 pool snapshot, not the original live objects (which are gone by
    the time ``simulate_windows`` runs) — so a self-validity mismatch means the snapshot,
    not this class or the production logic, is missing something.
    """

    __slots__ = ("chunk_id", "score", "source", "metadata")

    def __init__(
        self, chunk_id: str, score: float, source: str, hop1_rank: int | None
    ) -> None:
        self.chunk_id = chunk_id
        self.score = score
        self.source = source
        self.metadata = {"hop1_rank": hop1_rank}


def simulate_windows(
    pass2_call: dict, top_k_candidates: int, hop1_reserved_slots: int
) -> dict[str, list[str]]:
    """Offline counterfactual: replay the Pass-2 pool (captured pre-sort, original merge
    order preserved) through the ACTUAL production ordering and eviction code —
    ``RerankingEngine._order_merged_pool`` / ``._apply_hop1_reserve`` — for each policy in
    ``SIMULATED_POLICIES``, and return the resulting rerank-window ``chunk_id`` sequence.

    Reusing the production static methods (rather than re-implementing the sort/eviction
    here) means a divergence in the self-validity check
    (``simulate_windows(...)[policy] != observed window_ids``) can only mean the probe's
    *pool snapshot* — order, score, source, or hop1_rank — is incomplete or stale, never
    that this function's logic drifted from ``reranking_engine.py``.

    "score_no_reserve" is not a real ``merged_pool_policy`` value; it is "score" ordering
    with the reserve promotion forced off (``hop1_reserved_slots=0``), isolating ordering
    from eviction for prediction P4 (finding E).
    """
    from search.reranking_engine import RerankingEngine

    pool_objects = [
        _SimResult(p["chunk_id"], p["score"], p["source"], p["hop1_rank"])
        for p in pass2_call["pool"]
    ]

    windows: dict[str, list[str]] = {}
    for policy in SIMULATED_POLICIES:
        order_policy = "score" if policy == "score_no_reserve" else policy
        ordered = RerankingEngine._order_merged_pool(pool_objects, order_policy)
        reserve_slots = 0 if policy == "score_no_reserve" else hop1_reserved_slots
        evict_policy = "lowest_non_hop1" if policy == "score_reserve_fix" else "tail"
        final = RerankingEngine._apply_hop1_reserve(
            ordered, top_k_candidates, reserve_slots, evict_policy=evict_policy
        )
        windows[policy] = [r.chunk_id for r in final[:top_k_candidates]]
    return windows


def simulate_cap_windows(
    pass2_call: dict, top_k_candidates: int, hop1_reserved_slots: int
) -> dict[int, list[str]]:
    """Offline counterfactual analogous to ``simulate_windows()``, but for the
    ``graph_hop_window_cap`` probe (``--replay`` mode) instead of
    ``merged_pool_policy``: replay the Pass-2 pool through the ACTUAL
    production ``RerankingEngine._order_merged_pool("score")`` ->
    ``._apply_graph_hop_window_cap(cap)`` -> ``._apply_hop1_reserve("tail")``
    chain for every cap in ``SIMULATED_CAPS``, returning the resulting
    rerank-window ``chunk_id`` sequence keyed by cap.

    ``cap=0`` is a no-op by construction (``_apply_graph_hop_window_cap``
    returns its input unchanged when ``cap <= 0``), so ``windows[0]`` is
    byte-identical to ``simulate_windows(...)["score"]`` and to the observed
    production window whenever the deployed policy is ``"score"`` — the same
    self-validity guarantee ``simulate_windows`` relies on: a divergence can
    only mean the captured pool snapshot is stale, never that this function's
    logic drifted from ``reranking_engine.py``.

    ``graph_hop_unscored=True`` here (ADR-0039): this is what makes
    ``--replay``'s G3 self-validity check (``windows[0] == observed
    window_ids``) the empirical byte-identity gate for the provenance-band
    reformulation — a real production pool, ordered by the new banded code
    path, must still reproduce the exact window a *pre-reformulation* capture
    observed. A mismatch means the reformulation is not behaviour-preserving.
    """
    from search.reranking_engine import RerankingEngine

    pool_objects = [
        _SimResult(p["chunk_id"], p["score"], p["source"], p["hop1_rank"])
        for p in pass2_call["pool"]
    ]
    ordered = RerankingEngine._order_merged_pool(
        pool_objects, "score", graph_hop_unscored=True
    )

    windows: dict[int, list[str]] = {}
    for cap in SIMULATED_CAPS:
        capped = RerankingEngine._apply_graph_hop_window_cap(
            ordered, top_k_candidates, cap
        )
        final = RerankingEngine._apply_hop1_reserve(
            capped, top_k_candidates, hop1_reserved_slots, evict_policy="tail"
        )
        windows[cap] = [r.chunk_id for r in final[:top_k_candidates]]
    return windows


def channel_histogram(pass2_call: dict, pass2_window: dict) -> dict[str, int]:
    """Count Pass-2 rerank-window entries by channel (``source``), plus a
    ``_hop1_tagged`` sub-count (entries with ``metadata['hop1_rank']`` set — hop-1
    survivors are re-emitted into the merged pool still tagged ``source == "multi_hop"``,
    so this is a cross-cut, not an additional channel)."""
    hist: dict[str, int] = {}
    hop1_tagged = 0
    for cid in pass2_window["window_ids"]:
        src = pass2_call["sources"].get(cid, "unknown")
        hist[src] = hist.get(src, 0) + 1
        if pass2_call["hop1_ranks"].get(cid) is not None:
            hop1_tagged += 1
    hist["_hop1_tagged"] = hop1_tagged
    return hist


def score_ranges(pass2_call: dict) -> dict[str, dict[str, float]]:
    """Per-channel (source) min/median/max raw ``.score`` across the full Pass-2 merged
    pool (not just the window) — shows the incomparable-scale defect directly: channel
    score bands should not overlap under "score"/"score_reserve_fix" ordering, by
    construction of the bug."""
    by_source: dict[str, list[float]] = {}
    for cid, src in pass2_call["sources"].items():
        by_source.setdefault(src, []).append(pass2_call["scores"][cid])
    ranges: dict[str, dict[str, float]] = {}
    for src, scores in by_source.items():
        ranges[src] = {
            "min": min(scores),
            "median": statistics.median(scores),
            "max": max(scores),
            "count": len(scores),
        }
    return ranges


class Instrumentation:
    """Installs/removes monkeypatches on MultiHopSearcher and RerankingEngine classes."""

    def __init__(self, searcher) -> None:
        self._multi_hop_searcher = searcher.multi_hop_searcher
        self._engine_cls = type(searcher.reranking_engine)
        # _single_hop_search is a per-instance bound-callback attribute set in
        # MultiHopSearcher.__init__ (single_hop_callback=self._single_hop_search from
        # HybridSearcher), not a class method - must patch the instance, not the class.
        self._orig_single_hop = self._multi_hop_searcher._single_hop_search
        self._orig_rerank_by_query = self._engine_cls.rerank_by_query
        self._orig_run_rerank = self._engine_cls._run_rerank
        self.reset()

    def reset(self) -> None:
        self.hop1_ids: list[str] | None = None
        self.rerank_by_query_calls: list[dict] = []
        self.run_rerank_calls: list[dict] = []
        # Ordinal of the rerank_by_query call currently executing, so a nested
        # _run_rerank call (fired synchronously from inside it) can record which
        # rerank_by_query call it belongs to. This is the Pass-2/Pass-3
        # disambiguation: both dispatch _run_rerank under the same "[NEURAL_RERANK]"
        # log_prefix (reranking_engine.py:458), so the prefix alone can't tell them apart.
        self._active_ordinal: int | None = None

    def install(self) -> None:
        instrumentation = self
        orig_single_hop = self._orig_single_hop
        orig_rerank_by_query = self._orig_rerank_by_query
        orig_run_rerank = self._orig_run_rerank

        def patched_single_hop(*args, **kwargs):
            # orig_single_hop is already a bound method (HybridSearcher._single_hop_search
            # bound to the live searcher instance) - no self_searcher param to thread through.
            result = orig_single_hop(*args, **kwargs)
            instrumentation.hop1_ids = [normalize_chunk_id(r.chunk_id) for r in result]
            return result

        def patched_rerank_by_query(self_engine, query, results, k, *args, **kwargs):
            ordinal = len(instrumentation.rerank_by_query_calls)
            hop1_reserved_slots = kwargs.get(
                "hop1_reserved_slots", args[1] if len(args) > 1 else 0
            )
            merged_pool_policy = kwargs.get(
                "merged_pool_policy", args[2] if len(args) > 2 else "score"
            )
            pool = [
                {
                    "chunk_id": normalize_chunk_id(r.chunk_id),
                    "score": r.score,
                    "source": getattr(r, "source", "unknown"),
                    "hop1_rank": r.metadata.get("hop1_rank"),
                }
                for r in results
            ]
            instrumentation.rerank_by_query_calls.append(
                {
                    "ordinal": ordinal,
                    "pool": pool,
                    "pool_ids": [p["chunk_id"] for p in pool],
                    "pool_size": len(pool),
                    "scores": {p["chunk_id"]: p["score"] for p in pool},
                    "sources": {p["chunk_id"]: p["source"] for p in pool},
                    "hop1_ranks": {p["chunk_id"]: p["hop1_rank"] for p in pool},
                    "hop1_reserved_slots": hop1_reserved_slots,
                    "merged_pool_policy": merged_pool_policy,
                    "output_ids": None,  # filled in below once orig returns
                }
            )
            instrumentation._active_ordinal = ordinal
            try:
                output = orig_rerank_by_query(
                    self_engine, query, results, k, *args, **kwargs
                )
            finally:
                instrumentation._active_ordinal = None
            instrumentation.rerank_by_query_calls[ordinal]["output_ids"] = [
                normalize_chunk_id(r.chunk_id) for r in output
            ]
            return output

        def patched_run_rerank(
            self_engine, query_or_content, candidates, k, log_prefix, config=None
        ):
            if config is None:
                from search.config import get_search_config

                config = get_search_config()
            rerank_count = min(config.reranker.top_k_candidates, len(candidates))
            window = candidates[:rerank_count]
            instrumentation.run_rerank_calls.append(
                {
                    "log_prefix": log_prefix,
                    "rerank_by_query_ordinal": instrumentation._active_ordinal,
                    "top_k_candidates": config.reranker.top_k_candidates,
                    "candidate_ids": [
                        normalize_chunk_id(c.chunk_id) for c in candidates
                    ],
                    "window_ids": [normalize_chunk_id(c.chunk_id) for c in window],
                    "rerank_count": rerank_count,
                    "boundary_score": window[-1].score if window else None,
                }
            )
            return orig_run_rerank(
                self_engine, query_or_content, candidates, k, log_prefix, config=config
            )

        self._multi_hop_searcher._single_hop_search = patched_single_hop
        self._engine_cls.rerank_by_query = patched_rerank_by_query
        self._engine_cls._run_rerank = patched_run_rerank

    def uninstall(self) -> None:
        self._multi_hop_searcher._single_hop_search = self._orig_single_hop
        self._engine_cls.rerank_by_query = self._orig_rerank_by_query
        self._engine_cls._run_rerank = self._orig_run_rerank

    def pass2_call(self) -> dict | None:
        """The Pass-2 (multi-hop merge-pool) rerank_by_query call for the current query.

        Attribution is primarily by call **ordinal**: Pass 2 (MultiHopSearcher) always
        dispatches before Pass 3 (the ego-graph/parent-expansion tail,
        ``hybrid_searcher.py``'s two call sites) when both run in the same query, so
        ordinal 0 is Pass 2. Cross-checked against ``hop1_reserved_slots > 0`` — only
        Pass 2's dispatch ever passes a non-zero value — but the cross-check only *fires*
        (raises) on an actual contradiction (a positive-hop1_reserved_slots call NOT at
        ordinal 0, or more than one such call); it does not require ordinal 0 to itself
        have ``hop1_reserved_slots > 0``, since running this probe with
        ``--hop1-reserved-slots 0`` legitimately makes Pass 2 pass 0 too.
        """
        if not self.rerank_by_query_calls:
            return None
        positive_hop1 = [
            c for c in self.rerank_by_query_calls if c["hop1_reserved_slots"] > 0
        ]
        if len(positive_hop1) > 1:
            raise RuntimeError(
                f"{len(positive_hop1)} rerank_by_query calls with hop1_reserved_slots>0 "
                "in one query (expected at most 1 Pass-2 call)"
            )
        if positive_hop1 and positive_hop1[0]["ordinal"] != 0:
            raise RuntimeError(
                "Pass-2/Pass-3 disambiguation cross-check failed: a "
                f"hop1_reserved_slots>0 call was observed at ordinal "
                f"{positive_hop1[0]['ordinal']}, expected 0 (Pass 2 always runs first)"
            )
        return self.rerank_by_query_calls[0]

    def pass2_window(self) -> dict | None:
        """The [NEURAL_RERANK]-tagged _run_rerank call attributed to the Pass-2
        rerank_by_query call, via ``rerank_by_query_ordinal`` — NOT via list position,
        since Pass 3 shares the same log_prefix (see module docstring)."""
        call = self.pass2_call()
        if call is None:
            return None
        matches = [
            c
            for c in self.run_rerank_calls
            if c["log_prefix"] == MERGE_LOG_PREFIX
            and c["rerank_by_query_ordinal"] == call["ordinal"]
        ]
        return matches[0] if matches else None

    def pass3_calls(self) -> list[dict]:
        """[NEURAL_RERANK]-tagged _run_rerank calls NOT attributed to the Pass-2 ordinal —
        the ego-graph/parent-expansion tail rerank, if it ran for this query. Degrades to
        "every observed call" if Pass 2 never ran at all (multi_hop disabled), which is not
        a case this probe's default config exercises."""
        pass2 = self.pass2_call()
        pass2_ordinal = pass2["ordinal"] if pass2 else None
        return [
            c
            for c in self.run_rerank_calls
            if c["log_prefix"] == MERGE_LOG_PREFIX
            and c["rerank_by_query_ordinal"] != pass2_ordinal
        ]


def classify_query(
    instr: Instrumentation, gold_ids: dict[str, int], final_ids: list[str]
) -> list[dict]:
    """Per grade-3 gold: hop1_rank, in_merged_pool, in_rerank_window, final_rank, score/source."""
    hop1_ids = instr.hop1_ids or []
    merge_call = instr.pass2_call()
    window_call = instr.pass2_window()
    pool_ids = set(merge_call["pool_ids"]) if merge_call else set()
    window_ids = set(window_call["window_ids"]) if window_call else set()
    rows = []
    for gold, grade in sorted(gold_ids.items(), key=lambda kv: -kv[1]):
        if grade != 3:
            continue
        hop1_rank = hop1_ids.index(gold) + 1 if gold in hop1_ids else None
        in_pool = gold in pool_ids
        in_window = gold in window_ids
        final_rank = final_ids.index(gold) + 1 if gold in final_ids else None
        score = merge_call["scores"].get(gold) if merge_call else None
        source = merge_call["sources"].get(gold) if merge_call else None
        if hop1_rank is not None and hop1_rank <= 10 and in_pool and not in_window:
            classification = "window-cut"
        elif (
            hop1_rank is not None
            and hop1_rank <= 10
            and in_window
            and (final_rank is None or final_rank > 10)
        ):
            classification = "model-demotion"
        elif not in_pool:
            classification = "pool-loss"
        else:
            classification = "ok"
        rows.append(
            {
                "gold": gold,
                "hop1_rank": hop1_rank,
                "in_merged_pool": in_pool,
                "in_rerank_window": in_window,
                "final_rank": final_rank,
                "score": score,
                "source": source,
                "classification": classification,
            }
        )
    return rows


def print_query_report(record: dict) -> None:
    pass2_call = record["pass2_call"]
    pass2_window = record["pass2_window"]
    print(f"\nQuery {record['query_id']}: {record['query_text']!r}")
    if pass2_call is None:
        print(
            "  (no Pass-2 rerank_by_query call observed - multi_hop disabled "
            "or single_pass?)"
        )
    else:
        print(f"  Merged pool size: {pass2_call['pool_size']}")
        if pass2_window is not None:
            print(
                f"  Pass-2 rerank window: {pass2_window['rerank_count']} "
                f"(boundary score={pass2_window['boundary_score']}, "
                f"top_k_candidates={pass2_window['top_k_candidates']}, "
                f"policy={pass2_call['merged_pool_policy']!r})"
            )
            print(f"  Window channel histogram: {record['channel_histogram']}")
            print(
                "  Pool score ranges: "
                + ", ".join(
                    f"{src}=[{r['min']:.3f}..{r['max']:.3f}] (n={r['count']})"
                    for src, r in sorted(record["score_ranges"].items())
                )
            )
            validity = record["self_validity"]
            validity_s = (
                "n/a" if validity is None else ("OK" if validity else "MISMATCH")
            )
            print(f"  Self-validity (simulate == observed window): {validity_s}")
            if record["p6_hits"]:
                print(f"  P6 (in window, outside Pass-2 top-k): {record['p6_hits']}")
        else:
            print("  (no Pass-2 rerank window - reranker disabled for this call?)")
    rows = record["rows"]
    print(
        f"  {'grade':>5}  {'hop1_rank':>9}  {'in_pool':>7}  {'in_window':>9}  "
        f"{'final_rank':>10}  {'score':>8}  {'source':>10}  class"
    )
    for row in rows:
        hop1_s = str(row["hop1_rank"]) if row["hop1_rank"] is not None else "-"
        final_s = str(row["final_rank"]) if row["final_rank"] is not None else "miss"
        score_s = f"{row['score']:.3f}" if row["score"] is not None else "-"
        source_s = row["source"] or "-"
        print(
            f"  {3:>5}  {hop1_s:>9}  {str(row['in_merged_pool']):>7}  "
            f"{str(row['in_rerank_window']):>9}  {final_s:>10}  {score_s:>8}  "
            f"{source_s:>10}  {row['classification']}"
        )


def _median_or_none(xs: list[float] | list[int]) -> float | None:
    return statistics.median(xs) if xs else None


def _policy_gold_net(records: list[dict], policy: str) -> tuple[int, int, int]:
    """Grade-3 gold rescues/evictions moving from the observed "score" simulated window to
    ``policy``'s simulated window, summed over every query with a usable simulation.
    Positive net = ``policy`` nets more gold window-memberships than it costs; feeds gate
    criterion A2."""
    rescues = 0
    evictions = 0
    for r in records:
        if r["simulated"] is None:
            continue
        base = set(r["simulated"]["score"])
        variant = set(r["simulated"][policy])
        golds = {row["gold"] for row in r["rows"]}
        rescues += len((variant - base) & golds)
        evictions += len((base - variant) & golds)
    return rescues, evictions, rescues - evictions


def compute_predictions(records: list[dict]) -> dict:
    """Evaluate pre-registered predictions P1-P6 (``docs/plans/humming-wondering-phoenix.md``,
    Phase 1) against collected probe records. P1-P5 need a Pass-2 call+window (``usable``);
    P6 additionally reads grade-3 gold classification rows, present on every record."""
    usable = [
        r
        for r in records
        if r["pass2_call"] is not None and r["pass2_window"] is not None
    ]
    n = len(usable)

    # P1: Pass-2 window median multi_hop share.
    multi_hop_shares = []
    for r in usable:
        window_n = len(r["pass2_window"]["window_ids"])
        multi_hop_shares.append(
            (r["channel_histogram"].get("multi_hop", 0) / window_n) if window_n else 0.0
        )
    p1_median = _median_or_none(multi_hop_shares)

    # P2: median count of window entries with hop1_rank <= 8, and the median share of those
    # that only reached the window via the reserve promotion (absent from the pre-reserve
    # "score_no_reserve" simulated window).
    hop1_le8_counts = []
    reserve_arrival_fracs = []
    for r in usable:
        pool_by_id = {p["chunk_id"]: p for p in r["pass2_call"]["pool"]}
        le8_ids = [
            cid
            for cid in r["pass2_window"]["window_ids"]
            if (pool_by_id.get(cid, {}).get("hop1_rank") or 99) <= 8
        ]
        hop1_le8_counts.append(len(le8_ids))
        if le8_ids and r["simulated"] is not None:
            pre_reserve_ids = set(r["simulated"]["score_no_reserve"])
            arrived_via_reserve = sum(
                1 for cid in le8_ids if cid not in pre_reserve_ids
            )
            reserve_arrival_fracs.append(arrived_via_reserve / len(le8_ids))
    p2_count_median = _median_or_none(hop1_le8_counts)
    p2_reserve_share_median = _median_or_none(reserve_arrival_fracs)

    # P3: median graph_hop window count, and the fraction of queries with >=1.
    graph_hop_counts = [r["channel_histogram"].get("graph_hop", 0) for r in usable]
    p3_median = _median_or_none(graph_hop_counts)
    p3_any_frac = (sum(1 for c in graph_hop_counts if c >= 1) / n) if n else 0.0

    # P4 (finding E): fraction of queries where a pre-reserve window candidate with
    # hop1_rank in {1, 2} is absent from the post-reserve ("score") simulated window --
    # the reserve evicting a top-ranked hop-1 seed to make room for a worse-ranked one.
    p4_hits = 0
    p4_n = 0
    for r in usable:
        if r["simulated"] is None:
            continue
        p4_n += 1
        pool_by_id = {p["chunk_id"]: p for p in r["pass2_call"]["pool"]}
        pre_reserve = set(r["simulated"]["score_no_reserve"])
        post_reserve = set(r["simulated"]["score"])
        evicted_top2 = [
            cid
            for cid in pre_reserve
            if pool_by_id.get(cid, {}).get("hop1_rank") in (1, 2)
            and cid not in post_reserve
        ]
        if evicted_top2:
            p4_hits += 1
    p4_frac = (p4_hits / p4_n) if p4_n else 0.0

    # P5: Pass-3 (ego-graph/parent-expansion tail) inertness -- rerank_count should equal
    # len(candidates) on ~every query that has a Pass-3 call.
    pass3_flags = [
        c["rerank_count"] == len(c["candidate_ids"])
        for r in records
        for c in r["pass3_calls"]
    ]
    p5_frac = (sum(pass3_flags) / len(pass3_flags)) if pass3_flags else None

    # P6: grade-3 golds inside the Pass-2 window but outside Pass-2's own top-k output --
    # measures finding (D)'s ceiling independent of Pass 3.
    p6_total = sum(len(r["p6_hits"]) for r in records)
    p6_queries = sum(1 for r in records if r["p6_hits"])

    predictions = {
        "P1_multi_hop_median_share": {
            "value": p1_median,
            "target": ">= 0.60",
            "pass": p1_median is not None and p1_median >= 0.60,
        },
        "P2_hop1_le8": {
            "median_count": p2_count_median,
            "reserve_arrival_share_median": p2_reserve_share_median,
            "target": "reserve_arrival_share_median >= 0.60",
            "pass": (
                p2_reserve_share_median is not None and p2_reserve_share_median >= 0.60
            ),
        },
        "P3_graph_hop": {
            "median_count": p3_median,
            "any_frac": p3_any_frac,
            "target": "median_count == 0 and any_frac >= 0.05",
            "pass": p3_median == 0 and p3_any_frac >= 0.05,
        },
        "P4_finding_e_evicted_top2_frac": {
            "value": p4_frac,
            "n": p4_n,
            "target": ">= 0.50",
            "pass": p4_frac >= 0.50,
        },
        "P5_pass3_inert_frac": {
            "value": p5_frac,
            "n": len(pass3_flags),
            "target": ">= 0.99",
            "pass": p5_frac is not None and p5_frac >= 0.99,
        },
        "P6_window_not_top10": {
            "hit_count": p6_total,
            "query_count": p6_queries,
            "target": "informational (finding D ceiling)",
            "pass": None,
        },
    }
    return {"n_usable": n, "n_total": len(records), "predictions": predictions}


def evaluate_gate(records: list[dict], predictions: dict) -> dict:
    """A1/A2/A3 abort-criteria verdicts, per the plan's Phase 1 gate."""
    preds = predictions["predictions"]
    a1_premise_ok = (
        preds["P1_multi_hop_median_share"]["pass"] and preds["P2_hop1_le8"]["pass"]
    )

    net_by_policy = {}
    for policy in ("score_reserve_fix", "channel_priority"):
        rescues, evictions, net = _policy_gold_net(records, policy)
        net_by_policy[policy] = {"rescues": rescues, "evictions": evictions, "net": net}
    a2_headroom_ok = any(v["net"] > 0 for v in net_by_policy.values())

    validity_checked = [r for r in records if r["self_validity"] is not None]
    a3_valid = all(r["self_validity"] for r in validity_checked)

    return {
        "A1_premise_holds": a1_premise_ok,
        "A2_headroom_by_policy": net_by_policy,
        "A2_headroom_ok": a2_headroom_ok,
        "A3_self_validity_ok": a3_valid,
        "A3_checked_n": len(validity_checked),
        "abort": (not a1_premise_ok) or (not a2_headroom_ok) or (not a3_valid),
    }


def print_predictions_report(predictions: dict, gate: dict) -> None:
    preds = predictions["predictions"]
    print("\n" + "=" * 72)
    print(
        f"PREDICTIONS (n_usable={predictions['n_usable']}/{predictions['n_total']} "
        "queries with a Pass-2 window)"
    )
    print("=" * 72)
    for key, p in preds.items():
        status = p.get("pass")
        status_s = "-" if status is None else ("PASS" if status else "FAIL")
        extra = {k: v for k, v in p.items() if k != "pass"}
        print(f"  [{status_s}] {key}: {extra}")

    print("\nGATE (abort criteria)")
    print(
        f"  A1 premise (P1 & P2 hold): "
        f"{'PASS' if gate['A1_premise_holds'] else 'FAIL -> ABORT'}"
    )
    for policy, v in gate["A2_headroom_by_policy"].items():
        print(
            f"  A2 {policy}: rescues={v['rescues']} evictions={v['evictions']} net={v['net']}"
        )
    print(
        f"  A2 headroom (>=1 policy net > 0): "
        f"{'PASS' if gate['A2_headroom_ok'] else 'FAIL -> ABORT'}"
    )
    print(
        f"  A3 self-validity ({gate['A3_checked_n']} queries checked): "
        f"{'PASS' if gate['A3_self_validity_ok'] else 'FAIL -> HALT'}"
    )
    print(
        f"\n  OVERALL: "
        f"{'ABORT/HALT' if gate['abort'] else 'GATE PASSES -- proceed to Phase 4 arms'}"
    )


def _cap_gold_net(records: list[dict], cap: int) -> tuple[int, int, int]:
    """Grade-3 gold rescues/evictions moving from each record's ``cap=0``
    simulated window (byte-identical to the deployed ``"score"`` policy) to
    its ``cap`` simulated window, summed over every record with a usable cap
    simulation (``record["cap_simulated"]`` populated by ``run_replay``).
    Positive net = ``cap`` nets more gold window-memberships than it costs —
    feeds gate criterion G1. Mirrors ``_policy_gold_net``'s shape for the
    ``merged_pool_policy`` probe."""
    rescues = 0
    evictions = 0
    for r in records:
        sim = r.get("cap_simulated")
        if sim is None:
            continue
        base = set(sim[0])
        variant = set(sim[cap])
        golds = {row["gold"] for row in r["rows"]}
        rescues += len((variant - base) & golds)
        evictions += len((base - variant) & golds)
    return rescues, evictions, rescues - evictions


def evaluate_cap_gate(records: list[dict], chosen_caps: tuple[int, ...]) -> dict:
    """G1/G2/G3 abort-criteria verdicts for the ``graph_hop_window_cap``
    probe (``docs/plans/humming-wondering-phoenix.md`` follow-on Phase 1).
    Structure mirrors ``evaluate_gate()``'s A1/A2/A3 for the original
    ``merged_pool_policy`` probe.

    - G1 (headroom veto): net gold window-membership change > 0 at a cap.
    - G2 (retention): no gold in-window at cap=0 may leave the window at
      that cap -- literally ``evictions == 0`` from ``_cap_gold_net``.
    - G3 (self-validity): each record's ``cap=0`` replay window must equal
      the observed production ``pass2_window.window_ids`` exactly (set on
      ``record["g3_self_validity"]`` by ``run_replay``).
    """
    cap_stats = {}
    for cap in SIMULATED_CAPS:
        if cap == 0:
            continue
        rescues, evictions, net = _cap_gold_net(records, cap)
        cap_stats[cap] = {"rescues": rescues, "evictions": evictions, "net": net}

    g1_by_cap = {cap: v["net"] > 0 for cap, v in cap_stats.items()}
    g2_by_cap = {cap: v["evictions"] == 0 for cap, v in cap_stats.items()}

    validity_checked = [r for r in records if r.get("g3_self_validity") is not None]
    g3_valid = all(r["g3_self_validity"] for r in validity_checked)

    chosen_pass = {
        cap: (g1_by_cap.get(cap, False) and g2_by_cap.get(cap, False))
        for cap in chosen_caps
    }

    return {
        "cap_stats": cap_stats,
        "G1_by_cap": g1_by_cap,
        "G2_by_cap": g2_by_cap,
        "G3_self_validity_ok": g3_valid,
        "G3_checked_n": len(validity_checked),
        "chosen_caps": list(chosen_caps),
        "chosen_pass": chosen_pass,
        "abort": (not g3_valid) or not any(chosen_pass.values()),
    }


def print_cap_report(
    records: list[dict], gate: dict, n_usable: int, n_total: int
) -> None:
    print("\n" + "=" * 72)
    print(f"GRAPH_HOP WINDOW CAP REPLAY (n_usable={n_usable}/{n_total})")
    print("=" * 72)
    for cap in SIMULATED_CAPS:
        if cap == 0:
            continue
        changed = 0
        graph_delta = 0
        for r in records:
            sim = r.get("cap_simulated")
            if sim is None:
                continue
            base_ids = set(sim[0])
            var_ids = set(sim[cap])
            if base_ids != var_ids:
                changed += 1
            pool_source = {p["chunk_id"]: p["source"] for p in r["pass2_call"]["pool"]}
            graph_delta += sum(
                1 for c in var_ids if pool_source.get(c) == "graph_hop"
            ) - sum(1 for c in base_ids if pool_source.get(c) == "graph_hop")
        stats = gate["cap_stats"][cap]
        g1 = "PASS" if gate["G1_by_cap"][cap] else "FAIL"
        g2 = "PASS" if gate["G2_by_cap"][cap] else "FAIL"
        print(
            f"  cap={cap}: membership_changed={changed} "
            f"graph_in_window_delta={graph_delta} "
            f"gold_rescues={stats['rescues']} gold_evictions={stats['evictions']} "
            f"net={stats['net']}  G1={g1} G2={g2}"
        )

    print(
        f"\nG3 self-validity ({gate['G3_checked_n']} queries checked): "
        f"{'PASS' if gate['G3_self_validity_ok'] else 'FAIL -> HALT'}"
    )

    print("\nNamed-gold survival (Q12 / H034 / H066):")
    for qid in ("Q12", "H034", "H066"):
        rec = next((r for r in records if r["query_id"] == qid), None)
        if rec is None or rec.get("cap_simulated") is None:
            print(f"  {qid}: not found / not usable")
            continue
        golds = {row["gold"] for row in rec["rows"]}
        for cap in SIMULATED_CAPS:
            in_window = sorted(golds & set(rec["cap_simulated"][cap]))
            print(f"  {qid} cap={cap}: golds-in-window={in_window or 'none'}")

    print(
        f"\nChosen caps {gate['chosen_caps']}: "
        + ", ".join(
            f"cap={c} {'PASS' if p else 'FAIL'}" for c, p in gate["chosen_pass"].items()
        )
    )
    overall_abort = gate["abort"] or not gate["G3_self_validity_ok"]
    print(
        f"\nOVERALL: "
        f"{'ABORT/HALT' if overall_abort else 'GATE PASSES -- proceed to Phase 2b'}"
    )


def run_replay(
    json_path: Path, chosen_caps: tuple[int, ...], json_out: Path | None
) -> int:
    """``--replay`` mode: read a previously-captured probe JSON
    (``--json-out`` from a live ``--all`` run) and evaluate the
    ``graph_hop_window_cap`` gate offline -- no GPU, no live search. Reuses
    each record's captured Pass-2 pool snapshot (``pass2_call.pool``) and
    replays it through ``simulate_cap_windows`` (the ACTUAL production
    statics), so a G3 mismatch can only mean the captured snapshot is stale,
    never that this function's logic diverged from ``reranking_engine.py``.

    Exit codes: 0 (gate passes on >=1 chosen cap), 1 (no chosen cap clears
    G1+G2), 3 (G3 self-validity mismatch -- HALT, do not trust G1/G2).
    """
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    records = payload["records"]

    usable = 0
    for r in records:
        pc = r.get("pass2_call")
        pw = r.get("pass2_window")
        if pc is None or pw is None:
            r["cap_simulated"] = None
            r["g3_self_validity"] = None
            continue
        usable += 1
        sim = simulate_cap_windows(
            pc, pw["top_k_candidates"], pc["hop1_reserved_slots"]
        )
        r["cap_simulated"] = sim
        r["g3_self_validity"] = sim[0] == pw["window_ids"]

    gate = evaluate_cap_gate(records, chosen_caps)
    print_cap_report(records, gate, usable, len(records))

    if json_out is not None:
        out_payload = {
            "source": str(json_path),
            "n_usable": usable,
            "n_total": len(records),
            "simulated_caps": list(SIMULATED_CAPS),
            "chosen_caps": list(chosen_caps),
            "gate": gate,
            "per_query": [
                {
                    "query_id": r["query_id"],
                    "cap_simulated": r["cap_simulated"],
                    "g3_self_validity": r["g3_self_validity"],
                }
                for r in records
            ],
        }
        json_out.write_text(json.dumps(out_payload, indent=2), encoding="utf-8")
        print(f"\n[JSON] wrote {json_out}")

    if not gate["G3_self_validity_ok"]:
        print(
            "\nHALT: self-validity mismatch on cap replay -- G1/G2 cannot be "
            "trusted until this is fixed."
        )
        return 3
    if gate["abort"]:
        print("\nVERDICT: ABORT -- no chosen cap clears G1+G2.")
        return 1
    print("\nVERDICT: GATE PASSES")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--query-id", default="Q104,Q122", help="Comma-separated query IDs"
    )
    parser.add_argument("--all", action="store_true", help="Sweep all non-D/F queries")
    parser.add_argument("--dataset", default="evaluation/golden_dataset_expanded.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument(
        "--hop1-reserved-slots",
        type=int,
        default=None,
        help=(
            "Override reranker.hop1_reserved_slots in the in-memory config for "
            "this run (fix verification arm). Default: use config value. "
            "Sugar for --set reranker.hop1_reserved_slots=<value>."
        ),
    )
    parser.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        metavar="section.field=value",
        help=(
            "Override an arbitrary SearchConfig field for this run, e.g. "
            "'--set reranker.top_k_candidates=33'. Repeatable; later "
            "duplicates win. Routed through evaluation.arm_overrides - value "
            "is coerced to the field's declared type and validated against "
            "its spec(range=...)/choices=... before anything is mutated."
        ),
    )
    parser.add_argument(
        "--json-out",
        default=None,
        metavar="PATH",
        help=(
            "Write the full per-query + aggregate predictions/gate payload as JSON "
            "to PATH (relative paths resolve against the repo root). In --replay "
            "mode, writes the cap-gate payload instead."
        ),
    )
    parser.add_argument(
        "--replay",
        default=None,
        metavar="JSON",
        help=(
            "Offline mode: replay a previously-captured --json-out payload "
            "through the graph_hop_window_cap gate (no GPU, no live search, "
            "seconds). Ignores --query-id/--all/--dataset/--project-path/"
            "--set/--hop1-reserved-slots. See run_replay()."
        ),
    )
    parser.add_argument(
        "--caps",
        default="2,3",
        help=(
            "Comma-separated chosen caps to gate in --replay mode "
            "(default: 2,3 -- the pre-registered primary/secondary)."
        ),
    )
    args = parser.parse_args()

    if args.replay:
        replay_path = Path(args.replay)
        if not replay_path.is_absolute():
            replay_path = REPO_ROOT / replay_path
        chosen_caps = tuple(int(c.strip()) for c in args.caps.split(",") if c.strip())
        replay_json_out = None
        if args.json_out:
            replay_json_out = Path(args.json_out)
            if not replay_json_out.is_absolute():
                replay_json_out = REPO_ROOT / replay_json_out
        return run_replay(replay_path, chosen_caps, replay_json_out)

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path

    query_ids = (
        None if args.all else [q.strip() for q in args.query_id.split(",") if q.strip()]
    )
    try:
        items = load_queries(dataset_path, query_ids)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not items:
        print("ERROR: no queries selected", file=sys.stderr)
        return 2

    from evaluation.arm_overrides import (
        ArmOverrideError,
        apply_overrides,
        parse_set_flags,
    )

    try:
        overrides = parse_set_flags(args.set_overrides)
        if args.hop1_reserved_slots is not None:
            overrides["reranker.hop1_reserved_slots"] = args.hop1_reserved_slots
    except ArmOverrideError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Apply before constructing the searcher: this probe builds one searcher
    # per run (no cached-searcher reset path), so any construction_baked
    # field only takes effect if it is set first.
    if overrides:
        from search.config import get_search_config

        try:
            apply_overrides(get_search_config(), overrides)
        except ArmOverrideError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"[OVERRIDE] {overrides}")

    from mcp_server.search_factory import get_searcher

    searcher = get_searcher(project_path=args.project_path)

    instr = Instrumentation(searcher)
    instr.install()

    window_cut_count = 0
    model_demotion_count = 0
    pool_loss_count = 0
    ok_count = 0
    any_red = False
    per_query_records: list[dict] = []
    self_validity_failures: list[str] = []

    try:
        for item in items:
            query_id = item["id"]
            query_text = item["query"]
            grades = {
                normalize_chunk_id(gid): grade
                for gid, grade in (item.get("relevance_grades") or {}).items()
            }
            grade3 = {g: gr for g, gr in grades.items() if gr == 3}
            if not grade3:
                continue

            instr.reset()
            final_results = searcher.search(query_text, k=args.k)
            final_ids = [normalize_chunk_id(r.chunk_id) for r in final_results]

            rows = classify_query(instr, grades, final_ids)

            pass2_call = instr.pass2_call()
            pass2_window = instr.pass2_window()
            pass3_calls = instr.pass3_calls()

            channel_hist = None
            score_rng = None
            simulated = None
            self_validity = None
            p6_hits: list[str] = []

            if pass2_call is not None and pass2_window is not None:
                channel_hist = channel_histogram(pass2_call, pass2_window)
                score_rng = score_ranges(pass2_call)
                simulated = simulate_windows(
                    pass2_call,
                    pass2_window["top_k_candidates"],
                    pass2_call["hop1_reserved_slots"],
                )
                observed_policy = pass2_call["merged_pool_policy"]
                self_validity = (
                    simulated.get(observed_policy) == pass2_window["window_ids"]
                )
                if not self_validity:
                    self_validity_failures.append(query_id)

                if pass2_call["output_ids"] is not None:
                    pass2_top_ids = set(pass2_call["output_ids"][: args.k])
                    for row in rows:
                        if row["in_rerank_window"] and row["gold"] not in pass2_top_ids:
                            p6_hits.append(row["gold"])

            record = {
                "query_id": query_id,
                "query_text": query_text,
                "rows": rows,
                "pass2_call": pass2_call,
                "pass2_window": pass2_window,
                "pass3_calls": pass3_calls,
                "final_ids": final_ids,
                "channel_histogram": channel_hist,
                "score_ranges": score_rng,
                "simulated": simulated,
                "self_validity": self_validity,
                "p6_hits": p6_hits,
            }
            per_query_records.append(record)
            print_query_report(record)

            for row in rows:
                if row["classification"] == "window-cut":
                    window_cut_count += 1
                    any_red = True
                elif row["classification"] == "model-demotion":
                    model_demotion_count += 1
                elif row["classification"] == "pool-loss":
                    pool_loss_count += 1
                else:
                    ok_count += 1
    finally:
        instr.uninstall()

    print(
        f"\nTotals: window-cut={window_cut_count} model-demotion={model_demotion_count} "
        f"pool-loss={pool_loss_count} ok={ok_count}"
    )

    predictions = compute_predictions(per_query_records)
    gate = evaluate_gate(per_query_records, predictions)
    print_predictions_report(predictions, gate)

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        payload = {
            "k": args.k,
            "n_queries": len(items),
            "predictions": predictions,
            "gate": gate,
            "self_validity_failures": self_validity_failures,
            "records": per_query_records,
        }
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\n[JSON] wrote {out_path}")

    if self_validity_failures:
        print(
            f"\nHALT: self-validity mismatch on {len(self_validity_failures)} "
            f"quer{'y' if len(self_validity_failures) == 1 else 'ies'}: "
            f"{self_validity_failures}"
        )
        print(
            "simulate_windows() diverges from the observed production window -- "
            "P2/P4/A2 counterfactuals cannot be trusted until this is fixed."
        )
        return 3

    if any_red:
        print(
            f"VERDICT: RED - {window_cut_count} grade-3 gold(s) window-cut at k={args.k}"
        )
        return 1
    print(f"VERDICT: GREEN - no window-cuts observed at k={args.k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
