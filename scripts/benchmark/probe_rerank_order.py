"""Order-sensitivity probe for the listwise reranker (deep-research candidate 3, order arm).

For each golden query, run the canon pipeline once (pin_intent_off, like
run_sscg_benchmark.py) and capture the final rerank call: the multi-hop merged
pass if one ran, else the hop-1 pass. Then re-score that call's window
(``top_k_candidates`` first candidates) with the same reranker under several
input orders: fused (identity), reversed, and N seeded shuffles. Window
membership never changes; only the order the reranker reads.

Output per arm: MRR / hit@1 of the reranker's own output against the golden
grades, plus per-query first-gold ranks. The seed spread is the reranker's
order-noise floor; an arm beating identity by >= +0.02 MRR on 133q with a
paired CI excluding 0 would justify an order change or score averaging.

Run (MCP server may stay up; nothing is written to the index):
    CLAUDE_AUTO_REINDEX=0 .venv/Scripts/python.exe scripts/benchmark/probe_rerank_order.py \
        --dataset evaluation/golden_dataset_expanded.json --json tmp/order_133q.json

Result 2026-11-22 (evaluation/CANON_20261122_LABEL_AUDIT.md): no order beats fused order;
reordering alone moves 133q reranker-output MRR by -0.004 to +0.017 over 25-35 queries.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import statistics as st
import sys
from pathlib import Path


os.environ.setdefault("CLAUDE_AUTO_REINDEX", "0")
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evaluation import probe_harness  # noqa: E402
from evaluation.metrics import normalize_chunk_id  # noqa: E402


def _first_gold(ids: list[str], gold: set[str]) -> int | None:
    for i, c in enumerate(ids, 1):
        if c in gold:
            return i
    return None


async def _run(args: argparse.Namespace) -> dict:
    from mcp_server.tools.search_orchestrator import SearchOrchestrator
    from search.config import get_search_config

    items = probe_harness.load_golden_queries(
        probe_harness.resolve_dataset_path(args.dataset), args.query_ids
    )
    orchestrator = SearchOrchestrator()
    arms = ["identity", "reverse", *[f"shuffle{s}" for s in range(args.seeds)]]
    per_query: list[dict] = []

    with probe_harness.open_probe(args) as session, session.instrument() as calls:
        engine = session.searcher.reranking_engine
        inner_run = engine._run_rerank  # instrument()'s wrapper
        captured: list[tuple[str, list, int]] = []

        def capture(query_or_content, candidates, k, log_prefix, config=None):
            captured.append((query_or_content, list(candidates), k))
            return inner_run(query_or_content, candidates, k, log_prefix, config=config)

        engine._run_rerank = capture
        try:
            for n, item in enumerate(items, 1):
                before = len(calls)
                get_search_config().intent.enabled = False  # canon methodology
                try:
                    await orchestrator.run(
                        {
                            "query": item.query,
                            "k": args.k,
                            "search_mode": "hybrid",
                            "include_context": True,
                            "max_context_tokens": 0,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - per-query resilience for a probe
                    print(f"[WARN] {item.id}: {exc}", file=sys.stderr)
                    continue
                new = list(range(before, len(calls)))
                merged = [i for i in new if calls[i]["is_merged_pass"] is True]
                hop1 = [i for i in new if calls[i]["is_merged_pass"] is None]
                pick = (merged or hop1 or [None])[-1]
                if pick is None:
                    continue
                query, cands, k = captured[pick]
                window = cands[
                    : min(session.config.reranker.top_k_candidates, len(cands))
                ]
                gold = {g for g, grade in item.grades.items() if grade > 0}
                row = {
                    "id": item.id,
                    "pass": "merged" if merged else "hop1",
                    "window": len(window),
                    "gold_in_window": any(
                        normalize_chunk_id(c.chunk_id) in gold for c in window
                    ),
                    "pipeline_first_gold": _first_gold(calls[pick]["output_ids"], gold),
                }
                for arm in arms:
                    if arm == "identity":
                        order = list(window)
                    elif arm == "reverse":
                        order = list(reversed(window))
                    else:
                        order = list(window)
                        random.Random(int(arm[7:])).shuffle(order)
                    out = engine.neural_reranker.rerank(query, order, k)
                    ids = [normalize_chunk_id(r.chunk_id) for r in out]
                    row[arm] = _first_gold(ids, gold)
                per_query.append(row)
                if n % 10 == 0:
                    print(f"[{n}/{len(items)}]", file=sys.stderr, flush=True)
        finally:
            engine._run_rerank = inner_run

    def rr(r):
        return 1.0 / r if r else 0.0

    summary = {}
    for arm in arms:
        vals = [rr(q[arm]) for q in per_query]
        summary[arm] = {
            "mrr": round(st.mean(vals), 4),
            "hit@1": round(
                sum(1 for q in per_query if q[arm] == 1) / len(per_query), 4
            ),
        }
    for arm in arms[1:]:
        d = [rr(q[arm]) - rr(q["identity"]) for q in per_query]
        sd = st.stdev(d) if len(d) > 1 else 0.0
        summary[arm]["delta_vs_identity"] = round(st.mean(d), 4)
        summary[arm]["ci95_half"] = round(1.96 * sd / len(d) ** 0.5, 4)
        summary[arm]["queries_moved"] = sum(1 for x in d if abs(x) > 1e-9)
    summary["identity_matches_pipeline"] = sum(
        1 for q in per_query if q["identity"] == q["pipeline_first_gold"]
    )
    summary["n"] = len(per_query)
    summary["gold_in_window"] = sum(q["gold_in_window"] for q in per_query)
    return {"summary": summary, "per_query": per_query}


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()
    result = asyncio.run(_run(args))
    for arm, s in result["summary"].items():
        print(arm, s)
    if args.json_out:
        probe_harness.write_probe_json(args.json_out, result)
    return 0


if __name__ == "__main__":
    probe_harness.ensure_pinned_hash_seed()
    raise SystemExit(main())
