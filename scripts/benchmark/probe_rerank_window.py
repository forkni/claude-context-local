#!/usr/bin/env python
"""Probe whether hop-1 top-10 golds survive the multi-hop rerank window cut (read-only).

Background: ``evaluation/QUERY_EXPANSION_AB_20260728.md`` (root-cause section) observed
golden-set queries Q104/Q122 ranking 1 and 6 out of hop-1 (``MultiHopSearcher``), reaching
the merged expansion pool (~66-83 chunks at k=10), yet missing the final top-10. This probe
instruments the exact boundary between "gold is in the merged pool" and "gold is in the
window the listwise reranker actually scores" to distinguish three failure modes:

- **window-cut**: gold is in the merged pool but falls outside
  ``candidates[:top_k_candidates]`` at the hard cut in ``RerankingEngine._run_rerank`` --
  the model never sees it.
- **model-demotion**: gold is inside the window but the listwise model still ranks it > k.
- **pool-loss**: gold never reached the merged pool at all (a pre-existing retrieval gap,
  out of scope for this probe).

History: the pre-ADR-0079 ``"score"`` merged-pool ordering sorted three incomparable score
scales together (jina scores, FAISS cosines, a literal 0.0) and evicted hop-1 survivors from
the window. Window membership is now decided by ``RerankingEngine._gar_interleave``
(``docs/adr/0079-gar-style-rerank-window-membership.md``); the legacy orderings, the hop-1
reserve, the graph bands and the graph_hop window cap are deleted, along with their replay
gates here. The reports in ``evaluation/`` that used them are historical records.

Instrumentation:

- ``Instrumentation.pass2_call()``/``.pass2_window()``/``.pass3_calls()`` disambiguate the
  multi-hop merge-pool rerank (Pass 2) from the ego-graph/parent-expansion tail rerank
  (Pass 3) by ``rerank_by_query`` call **ordinal**, cross-checked against
  ``is_merged_pass`` (``"window" in kwargs`` -- only Pass 2's dispatch ever passes that
  kwarg) -- *not* by list position or log prefix alone, since both passes share the
  ``"[NEURAL_RERANK]"`` prefix; only Pass 1 (``SearchExecutor.apply_neural_reranking``)
  uses the distinct ``"[NEURAL_RERANK-SEARCH]"``.
- **ADR-0077 single-block invariant**: each Pass-2 call record also captures
  ``last_block_count``/``last_doc_token_cap`` (``RerankingEngine`` attributes populated from
  ``JinaRerankerV3`` post-call). ``print_query_report()`` and
  ``summarize_listwise_invariant()`` surface these so "did the invariant hold -- exactly one
  block, on every query -- at this budget?" is answerable from one offline pass, without a
  GPU benchmark leg. See docs/adr/0077-single-block-listwise-invariant.md.
- ``simulate_windows()`` replays each query's captured Pass-2 pool (order/score/source/
  ``hop1_rank``/``anchor_rank`` snapshot, taken pre-sort) through the probe-local GAR
  orderings in ``SIMULATED_POLICIES``: ``gar_anchor_first`` (what production does) and
  ``gar_round_robin`` (the rejected alternative, kept for comparison).
- **Self-validity check**: ``simulate_windows(...)["gar_anchor_first"]`` must equal the
  observed Pass-2 window on every query. A mismatch means the captured pool snapshot is
  incomplete, or the probe's ordering has drifted from ``_gar_interleave``; it is a HALT
  condition (exit code 3) -- the simulated counterfactuals should not be trusted.
- ``--json-out PATH`` writes the full per-query + aggregate payload for offline analysis.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --query-id Q104,Q122 --dataset evaluation/golden_dataset_expanded.json --k 10

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --all --dataset evaluation/golden_dataset_expanded.json --k 10 \
        --json-out evaluation/probe_rerank_window_<date>.json

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --all --set reranker.top_k_candidates=33

Exit codes: 0 (GREEN) no window-cuts and self-validity holds everywhere; 1 (RED) at least
one grade-3 gold is window-cut; 2 on setup errors; 3 (HALT) self-validity diverged on at
least one query.
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

# GAR-style window orderings simulate_windows() replays against each query's captured Pass-2
# pool (docs/adr/0079, evaluation/GAR_WINDOW_AB_20261001.md). Both alternate 1:1 between
# hop-1 survivors (by hop1_rank) and the frontier (expansion candidates); they differ only in
# how the frontier itself is ordered. "gar_anchor_first" is the production ordering.
SIMULATED_POLICIES = ("gar_anchor_first", "gar_round_robin")
OBSERVED_POLICY = "gar_anchor_first"


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
    """Minimal stand-in for ``search.reranker.SearchResult``, sufficient for the GAR orderings
    below -- they only touch ``.chunk_id``, ``.source``, and ``.metadata['hop1_rank'/
    'anchor_rank']``. Built from the probe's captured Pass-2 pool snapshot, not the original
    live objects (which are gone by the time ``simulate_windows`` runs).
    """

    __slots__ = ("chunk_id", "score", "source", "metadata")

    def __init__(
        self,
        chunk_id: str,
        score: float,
        source: str,
        hop1_rank: int | None,
        anchor_rank: int | None = None,
    ) -> None:
        self.chunk_id = chunk_id
        self.score = score
        self.source = source
        self.metadata = {"hop1_rank": hop1_rank, "anchor_rank": anchor_rank}


def simulate_windows(pass2_call: dict, top_k_candidates: int) -> dict[str, list[str]]:
    """Offline counterfactual: replay the Pass-2 pool (captured pre-sort, original merge
    order preserved) through each ordering in ``SIMULATED_POLICIES`` and return the resulting
    rerank-window ``chunk_id`` sequence."""
    pool_objects = [
        _SimResult(
            p["chunk_id"],
            p["score"],
            p["source"],
            p["hop1_rank"],
            p.get("anchor_rank"),
        )
        for p in pass2_call["pool"]
    ]
    return {
        policy: [r.chunk_id for r in gar_order(pool_objects, policy)[:top_k_candidates]]
        for policy in SIMULATED_POLICIES
    }


def _frontier_by_anchor(frontier: list) -> dict[int, list]:
    """Group frontier candidates by ``anchor_rank`` (None -> a trailing bucket keyed past every
    real anchor), alternating the graph channel and the semantic channel inside each anchor,
    graph first (``_hybrid_expand`` runs the graph channel first). Native order within a channel
    is the captured merge order, which is already best-first per anchor."""
    groups: dict[int, list] = {}
    for r in frontier:
        key = r.metadata.get("anchor_rank")
        groups.setdefault(10**6 if key is None else key, []).append(r)
    out: dict[int, list] = {}
    for key, members in groups.items():
        graph = [m for m in members if m.source == "graph_hop"]
        other = [m for m in members if m.source != "graph_hop"]
        merged: list = []
        for i in range(max(len(graph), len(other))):
            if i < len(graph):
                merged.append(graph[i])
            if i < len(other):
                merged.append(other[i])
        out[key] = merged
    return out


def gar_order(pool: list, policy: str) -> list:
    """GAR-style ordering of a captured Pass-2 pool: 1:1 alternation, hop-1 first, between hop-1
    survivors (by ``hop1_rank``) and the frontier; when one side runs out the other fills the
    rest. Hop-1 vs frontier is decided by ``metadata['hop1_rank']`` (not ``source``: both are
    ``"multi_hop"``). ``policy`` picks only the frontier order:

    - ``gar_anchor_first``: all of anchor 1's neighbours, then anchor 2's, ...
    - ``gar_round_robin``: each anchor's best neighbour, then each anchor's second best, ...
    """
    hop1 = sorted(
        (r for r in pool if r.metadata.get("hop1_rank") is not None),
        key=lambda r: r.metadata["hop1_rank"],
    )
    frontier_raw = [r for r in pool if r.metadata.get("hop1_rank") is None]
    groups = _frontier_by_anchor(frontier_raw)
    if policy == "gar_anchor_first":
        frontier = [r for key in sorted(groups) for r in groups[key]]
    elif policy == "gar_round_robin":
        frontier = []
        depth = max((len(g) for g in groups.values()), default=0)
        for i in range(depth):
            for key in sorted(groups):
                if i < len(groups[key]):
                    frontier.append(groups[key][i])
    else:
        raise ValueError(f"unknown GAR policy {policy!r}")

    ordered: list = []
    for i in range(max(len(hop1), len(frontier))):
        if i < len(hop1):
            ordered.append(hop1[i])
        if i < len(frontier):
            ordered.append(frontier[i])
    return ordered


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
    pool (not just the window) — shows the incomparable score scales per channel, the reason
    window membership is decided by interleave rather than by comparing scores."""
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
        # log_prefix, so the prefix alone can't tell them apart.
        self._active_ordinal: int | None = None

    def install(self) -> None:
        from search.rerank_window_policy import RerankWindowPolicy

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
            window = kwargs.get("window", RerankWindowPolicy.tail())
            is_merged_pass = "window" in kwargs
            pool = [
                {
                    "chunk_id": normalize_chunk_id(r.chunk_id),
                    "score": r.score,
                    "source": getattr(r, "source", "unknown"),
                    "hop1_rank": r.metadata.get("hop1_rank"),
                    "anchor_rank": r.metadata.get("anchor_rank"),
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
                    "is_merged_pass": is_merged_pass,
                    "interleave": window.interleave,
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
            call_record = {
                "log_prefix": log_prefix,
                "rerank_by_query_ordinal": instrumentation._active_ordinal,
                "top_k_candidates": config.reranker.top_k_candidates,
                "candidate_ids": [normalize_chunk_id(c.chunk_id) for c in candidates],
                "window_ids": [normalize_chunk_id(c.chunk_id) for c in window],
                "rerank_count": rerank_count,
                "boundary_score": window[-1].score if window else None,
                # ADR-0077 single-block invariant (filled in below, after
                # orig_run_rerank runs -- these are RerankingEngine attributes
                # orig_run_rerank mutates as a side effect, not something the
                # call args expose). Placeholder None here covers the case
                # where orig_run_rerank raises: the call is still on record,
                # just without an invariant reading for it.
                "last_block_count": None,
                "last_doc_token_cap": None,
            }
            instrumentation.run_rerank_calls.append(call_record)
            result = orig_run_rerank(
                self_engine, query_or_content, candidates, k, log_prefix, config=config
            )
            # See search/reranking_engine.py's RerankingEngine.__init__ for the
            # exact "last pass wins" semantics of both attributes, and
            # JinaRerankerV3.__init__ (search/neural_reranker.py) for the one
            # documented asymmetry between them.
            call_record["last_block_count"] = self_engine.last_block_count
            call_record["last_doc_token_cap"] = getattr(
                self_engine, "last_doc_token_cap", None
            )
            return result

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
        ordinal 0 is Pass 2. Cross-checked against ``is_merged_pass`` (``"window" in
        kwargs`` — only Pass 2's dispatch ever passes that kwarg at all) — the
        cross-check only *fires* (raises) on an actual contradiction (a merged-pass call
        NOT at ordinal 0, or more than one such call).
        """
        if not self.rerank_by_query_calls:
            return None
        merged_calls = [c for c in self.rerank_by_query_calls if c["is_merged_pass"]]
        if len(merged_calls) > 1:
            raise RuntimeError(
                f"{len(merged_calls)} rerank_by_query calls passed window= "
                "in one query (expected at most 1 Pass-2 call)"
            )
        if merged_calls and merged_calls[0]["ordinal"] != 0:
            raise RuntimeError(
                "Pass-2/Pass-3 disambiguation cross-check failed: a "
                f"merged-pass call was observed at ordinal "
                f"{merged_calls[0]['ordinal']}, expected 0 (Pass 2 always runs first)"
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
                f"interleave={pass2_call['interleave']})"
            )
            # ADR-0077 single-block invariant readings, captured by
            # Instrumentation.install()'s patched_run_rerank post-call. None
            # here means _run_rerank raised (call is on record but the
            # RerankingEngine attributes never got read back).
            print(
                "  Listwise invariant: block_count="
                f"{pass2_window['last_block_count']!r} "
                f"doc_token_cap={pass2_window['last_doc_token_cap']!r}"
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
                print(f"  In window, outside Pass-2 top-k: {record['p6_hits']}")
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


def summarize_window_membership(records: list[dict]) -> dict:
    """Per simulated policy: grade-3 golds that land in the window (of those present in the
    Pass-2 pool), the median graph_hop occupancy of the window, and how many hop-1 rank-1
    survivors the window keeps."""
    out: dict[str, dict] = {}
    usable = [r for r in records if r["simulated"] is not None]
    for policy in SIMULATED_POLICIES:
        golds_in_window = 0
        golds_in_pool = 0
        graph_counts: list[int] = []
        hop1_rank1_kept = 0
        hop1_rank1_total = 0
        for r in usable:
            sources = r["pass2_call"]["sources"]
            hop1_ranks = r["pass2_call"]["hop1_ranks"]
            pool_ids = set(r["pass2_call"]["pool_ids"])
            window = r["simulated"][policy]
            window_set = set(window)
            golds = {row["gold"] for row in r["rows"]} & pool_ids
            golds_in_pool += len(golds)
            golds_in_window += len(golds & window_set)
            graph_counts.append(sum(1 for c in window if sources.get(c) == "graph_hop"))
            for cid, hr in hop1_ranks.items():
                if hr == 1:
                    hop1_rank1_total += 1
                    hop1_rank1_kept += cid in window_set
        out[policy] = {
            "golds_in_pool": golds_in_pool,
            "golds_in_window": golds_in_window,
            "graph_hop_window_median": _median_or_none(graph_counts),
            "graph_hop_window_zero_frac": (
                sum(1 for c in graph_counts if c == 0) / len(graph_counts)
                if graph_counts
                else None
            ),
            "hop1_rank1_in_window": f"{hop1_rank1_kept}/{hop1_rank1_total}",
        }
    return {"n_usable": len(usable), "by_policy": out}


def print_window_membership(summary: dict) -> None:
    print()
    print("=" * 72)
    print(f"WINDOW MEMBERSHIP by simulated policy (n_usable={summary['n_usable']})")
    print("=" * 72)
    for policy, v in summary["by_policy"].items():
        print(
            f"  {policy:<20} golds_in_window={v['golds_in_window']}/{v['golds_in_pool']}"
            f"  graph_hop_median={v['graph_hop_window_median']}"
            f"  graph_hop_zero_frac={v['graph_hop_window_zero_frac']}"
            f"  hop1_rank1_in_window={v['hop1_rank1_in_window']}"
        )


def summarize_listwise_invariant(records: list[dict]) -> dict:
    """ADR-0077 single-block invariant tally across every observed listwise rerank call
    (Pass-2's ``pass2_window`` plus any Pass-3 tail calls), offline -- Verification tier 2.
    Answers "did the invariant hold, on every query, at this budget?" without a GPU leg.

    ``last_block_count``/``last_doc_token_cap`` are read straight off each captured
    ``run_rerank_calls`` entry (see ``Instrumentation.install()``'s ``patched_run_rerank``) --
    they are ``None`` on a call that never reached a successful/attempted
    ``_fit_single_block`` solve (v3.5, no candidates, or an exception before the read-back;
    see ``JinaRerankerV3.__init__`` and ``RerankingEngine.__init__``'s ``last_doc_token_cap``
    comments for the exact per-layer semantics)."""
    calls: list[tuple[str, dict]] = []
    for r in records:
        if r["pass2_window"] is not None:
            calls.append((r["query_id"], r["pass2_window"]))
        for c in r["pass3_calls"]:
            calls.append((r["query_id"], c))

    engaged = [(qid, c) for qid, c in calls if c["last_block_count"] is not None]
    multi_block = [(qid, c) for qid, c in engaged if c["last_block_count"] > 1]
    doc_token_caps = [
        c["last_doc_token_cap"]
        for _, c in engaged
        if c["last_doc_token_cap"] is not None
    ]

    return {
        "n_calls": len(calls),
        "n_engaged": len(engaged),
        "n_multi_block": len(multi_block),
        "multi_block_query_ids": sorted({qid for qid, _ in multi_block}),
        "min_doc_token_cap": min(doc_token_caps) if doc_token_caps else None,
        "median_doc_token_cap": _median_or_none(doc_token_caps),
    }


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
            "Write the full per-query + aggregate payload as JSON to PATH "
            "(relative paths resolve against the repo root)."
        ),
    )
    args = parser.parse_args()

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
                    pass2_call, pass2_window["top_k_candidates"]
                )
                # Only a merged-pool (interleave) pass has a simulated counterpart.
                if pass2_call["interleave"]:
                    self_validity = (
                        simulated[OBSERVED_POLICY] == pass2_window["window_ids"]
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

    listwise_invariant = summarize_listwise_invariant(per_query_records)
    print(
        "Listwise invariant (ADR-0077): "
        f"{listwise_invariant['n_multi_block']}/{listwise_invariant['n_engaged']} "
        "engaged calls were multi-block "
        f"(min_doc_token_cap={listwise_invariant['min_doc_token_cap']}, "
        f"median_doc_token_cap={listwise_invariant['median_doc_token_cap']})"
    )
    if listwise_invariant["multi_block_query_ids"]:
        print(f"  Multi-block queries: {listwise_invariant['multi_block_query_ids']}")

    window_membership = summarize_window_membership(per_query_records)
    print_window_membership(window_membership)

    if args.json_out:
        out_path = Path(args.json_out)
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
        payload = {
            "k": args.k,
            "n_queries": len(items),
            "listwise_invariant_summary": listwise_invariant,
            "window_membership": window_membership,
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
            "the simulated counterfactuals cannot be trusted until this is fixed."
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
