#!/usr/bin/env python
"""Phase 2 Step 2 -- offline gate-2 truncation-policy replay (zero GPU cost).

Consumes the Step-1-extended `probe_ego_membership.py` JSON artifacts
(`evaluation/ego_membership_{63q,133q}_<date>.json`) and simulates five
alternate gate-2 truncation policies against the exact captured
pre-truncation traversal data, reproducing `EgoGraphRetriever.retrieve_ego_graph`'s
own gate-1/gate-2 sequence (`search/ego_graph_retriever.py:105-148`):

    1. neighbors = get_neighbors_ranked(anchor, ...)          -- raw BFS order
    2. valid = [n for n in neighbors if is_chunk_id(n)]        -- gate 1
    3. valid = policy(valid)[:max_total or policy's own cap]   -- gate 2 (HERE)

Policies:

    R0  no cap                                   -- replay's own ceiling
    R1  cap 30                                    -- gate-4-widening cap
    R2  centrality-sorted, cap 20                 -- QW1 repaired
    R3  confidence-sorted, cap 20                 -- A2' at the truncation boundary
    R4  hard-filter confidence >= theta, cap 20   -- theta in {0.7, 0.75, 0.9}

For each policy and dataset, counts distinct "addressable" golds (golds this
probe run classified `b2_gate2_truncated` -- i.e. reachable, symbol-filtered-in,
but cut by gate 2 under the production `base` policy) that the policy's
simulated post-gate-2 union would newly admit relative to the captured `base`
`post_gate2` union.

Pre-registered screen (plan's Step 2): carry an arm into Step 4's live A/B only
if it newly admits >= 2 addressable golds on EACH of 63q and 133q, and R0's
admission count is strictly greater than zero on both -- see `main()`'s
printed verdict table.

Stated limitation, not a defect: this replay stops at gate 2. A rescued
neighbor must still clear gate 3 (min_similarity_threshold), gate 4 (score
cap), and the listwise reranker to actually move a metric -- all four of
which are unmeasurable offline from this artifact. This screen is therefore
necessary, not sufficient; Step 4's live A/B is the actual decision.

No config writes, no production edits. Read-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from evaluation.metrics import normalize_chunk_id
from search.graph_integration import is_chunk_id


BASE_MAX_TOTAL = 20  # mnph=10 * k_hops=2, the production default (canon)
WIDE_CAP = 30  # mnph=15 * k_hops=2 -- the ego_w15 A/B arm's gate-2 cap
R4_THETAS = (0.7, 0.75, 0.9)

POLICIES = ("R0", "R1", "R2", "R3", "R4_0.7", "R4_0.75", "R4_0.9")


def _decode(table: list[str], interned: list[int]) -> list[str]:
    return [table[i] for i in interned]


def simulate_gate2(
    raw_neighbors: list[str],
    policy: str,
    *,
    centrality: dict[str, float],
    confidence: dict[str, tuple[str, float | None]],
) -> list[str]:
    """Reproduce gate 1 (`is_chunk_id`) then gate 2 under `policy`.

    `centrality` keys are RAW chunk ids (see `main()`'s decode step).
    `confidence` keys are RAW neighbor ids, values `(resolution_label, conf)`
    -- the per-anchor best-confidence map `probe_ego_membership.py`'s Step 1
    extension captured. Missing confidence sorts/filters as 0.0 (conservative:
    never over-counts a rescue for R3/R4).
    """
    valid = [n for n in raw_neighbors if is_chunk_id(n)]

    if policy == "R0":
        return valid
    if policy == "R1":
        return valid[:WIDE_CAP]
    if policy == "R2":
        ranked = sorted(valid, key=lambda n: centrality.get(n, 0.0), reverse=True)
        return ranked[:BASE_MAX_TOTAL]
    if policy == "R3":
        ranked = sorted(
            valid,
            key=lambda n: (confidence.get(n) or (None, 0.0))[1] or 0.0,
            reverse=True,
        )
        return ranked[:BASE_MAX_TOTAL]
    if policy.startswith("R4_"):
        theta = float(policy.split("_", 1)[1])
        filtered = [
            n for n in valid if ((confidence.get(n) or (None, 0.0))[1] or 0.0) >= theta
        ]
        return filtered[:BASE_MAX_TOTAL]
    raise ValueError(f"unknown policy: {policy}")


def replay_dataset(payload: dict) -> dict[str, set[str]]:
    """Return {policy: {newly-admitted addressable gold, ...}} for one probe JSON."""
    chunk_id_table: list[str] = payload["chunk_id_table"]
    global_centrality: dict[str, float] = {
        chunk_id_table[int(idx)]: score
        for idx, score in payload["global_centrality"].items()
    }

    newly_admitted: dict[str, set[str]] = {p: set() for p in POLICIES}

    for rec in payload["per_query"]:
        et = rec.get("ego_traversal")
        if not et:
            continue
        addressable = {
            g["gold"]
            for g in rec.get("golds", [])
            if g["bucket"] == "b2_gate2_truncated"
        }
        if not addressable:
            continue

        # Ground-truth base admission: the ACTUAL captured post_gate2 union,
        # not a re-simulation -- removes any dependency on this script's own
        # gate-1/gate-2 reimplementation being bug-for-bug identical to
        # production for the base case.
        base_admitted: set[str] = set()
        for neighbors_interned in et["post_gate2"].values():
            base_admitted.update(
                normalize_chunk_id(n)
                for n in _decode(chunk_id_table, neighbors_interned)
            )

        per_anchor_raw: dict[str, list[str]] = {
            anchor_idx: _decode(chunk_id_table, neighbors_interned)
            for anchor_idx, neighbors_interned in et["raw_traversal"].items()
        }
        per_anchor_conf: dict[str, dict[str, tuple[str, float | None]]] = {
            anchor_idx: {
                chunk_id_table[int(n_idx)]: tuple(v) for n_idx, v in conf_map.items()
            }
            for anchor_idx, conf_map in et.get("neighbor_confidence", {}).items()
        }

        for policy in POLICIES:
            admitted: set[str] = set()
            for anchor_idx, raw_neighbors in per_anchor_raw.items():
                selected = simulate_gate2(
                    raw_neighbors,
                    policy,
                    centrality=global_centrality,
                    confidence=per_anchor_conf.get(anchor_idx, {}),
                )
                admitted.update(normalize_chunk_id(n) for n in selected)
            rescued = (admitted & addressable) - base_admitted
            newly_admitted[policy].update(rescued)

    return newly_admitted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe-json", action="append", required=True, dest="probe_jsons"
    )
    args = parser.parse_args()

    per_dataset: dict[str, dict[str, set[str]]] = {}
    for path_str in args.probe_jsons:
        path = Path(path_str)
        payload = json.loads(path.read_text(encoding="utf-8"))
        per_dataset[path.name] = replay_dataset(payload)

    print(f"{'policy':<10}", end="")
    for name in per_dataset:
        print(f"{name[:28]:>30}", end="")
    print()
    print("-" * (10 + 30 * len(per_dataset)))

    for policy in POLICIES:
        print(f"{policy:<10}", end="")
        for name in per_dataset:
            n = len(per_dataset[name][policy])
            print(f"{n:>30}", end="")
        print()

    print(
        "\nPre-registered screen: newly-admitted addressable golds >= 2 on EACH "
        "dataset (R0 must additionally be > 0 on both)."
    )
    for policy in POLICIES:
        counts = [len(per_dataset[name][policy]) for name in per_dataset]
        if policy == "R0":
            passed = all(c > 0 for c in counts)
        else:
            passed = all(c >= 2 for c in counts)
        verdict = "CARRY to Step 4" if passed else "screen fails, do not build"
        print(f"  {policy:<10} counts={counts}  -> {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
