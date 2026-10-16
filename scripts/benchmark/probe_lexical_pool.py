#!/usr/bin/env python
"""Probe BM25 analyzer and field-channel arms by fusion-cut misses, read-only.

Question: does a different BM25 analyzer (``additive``, ``case_gated``) or a
fielded symbol/path channel move gold into the fused pool on a camelCase corpus?
Every earlier tokenizer A/B ran on this repo's snake_case Python, where
arXiv 2605.18561 predicts no difference.

Gate (see CONTEXT.md, "Fusion-cut miss"): per arm, per stratum, the number of
queries whose gold is a *fusion-cut miss* under the ``whole`` baseline but in the
fused pool under the arm (rescued) minus the reverse (created). Gold absent from
both raw legs is a *leg miss*: out of reach for fusion, reported separately.
BM25 can promote a dense-deep candidate into the pool but cannot introduce a
dense-absent one (weighted RRF, k=100, 0.35/0.65), so BM25-only MRR is secondary.

Arms, all built offline from the live index's persisted BM25 documents (which
already carry the path/symbol augmentation suffix) and swapped into
``session.searcher.search_executor.bm25_index`` before ``ProbeSession.replay_legs``:

- ``whole`` / ``additive`` / ``case_gated``: the three analyzers on the full docs.
- ``moved_w<w>``: body (augmentation suffix stripped) + ``w`` * field, where the
  field index holds only the augmentation text. In-leg score sum; RRF untouched.
- ``dup_w<w>``: full docs + ``w`` * field (augmentation in both).

Fidelity (run first, always): an unswapped replay of the live index must equal
the ``whole`` arm's BM25 leg and fused cut for every query, or the verdict is RED
and no arm delta can be trusted.

No production code is touched. Set ``CLAUDE_AUTO_REINDEX=0`` (done below) so a
stale index is never rebuilt mid-run.

Usage (module form, same reason as probe_leg_depth_fusion):
    .venv/Scripts/python.exe -m scripts.benchmark.probe_lexical_pool \
        --dataset evaluation/twozero_lexical_golden.json \
        --project-path D:/Users/alexk/FORKNI/TWOZERO/twozero-dev \
        [--k 10] [--depth 100] [--min-grade 3] [--weights 0.5 1 2] \
        [--arms whole additive case_gated moved dup] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id


IN_POOL = "in_pool"
FUSION_CUT_MISS = "fusion_cut_miss"
LEG_MISS = "leg_miss"
STATUSES = (IN_POOL, FUSION_CUT_MISS, LEG_MISS)
ANALYZER_ARMS = ("whole", "additive", "case_gated")


# ---------------------------------------------------------------------------
# Arm construction
# ---------------------------------------------------------------------------


def augmentation_text(chunk_id: str) -> str:
    """Path/symbol augmentation exactly as ``augment_bm25_document`` builds it."""
    from search.tokenization import build_path_symbol_text

    parts = chunk_id.split(":")
    if len(parts) < 4:
        return ""
    return build_path_symbol_text(parts[0], ":".join(parts[3:]))


def split_body_and_field(doc_ids: list[str], docs: list[str]) -> tuple[list[str], int]:
    """Strip the augmentation suffix. Returns ``(bodies, n_unstripped)``."""
    bodies: list[str] = []
    unstripped = 0
    for chunk_id, doc in zip(doc_ids, docs, strict=True):
        aug = augmentation_text(chunk_id)
        if not aug:
            bodies.append(doc)
        elif doc == aug:
            bodies.append("")
        elif doc.endswith("\n" + aug):
            bodies.append(doc[: -(len(aug) + 1)])
        else:
            bodies.append(doc)
            unstripped += 1
    return bodies, unstripped


class ArmIndex:
    """Duck-types ``BM25Index.search`` over one or more weighted BM25 components.

    One component with weight 1 reproduces ``BM25Index.search`` exactly (same
    scoring call, same ``argsort`` tie order, same min-score skip, same metadata
    copy). Two components give the in-leg score sum of the field arms.
    """

    def __init__(self, live: Any, components: list[tuple[Any, Any, float]]) -> None:
        self._live = live
        self._components = components  # (BM25Okapi, TextPreprocessor, weight)

    def search(
        self, query: str, k: int = 5, min_score: float = 0.0
    ) -> list[tuple[str, float, dict]]:
        scores = None
        for bm25, prep, weight in self._components:
            tokens = prep.process(query)
            if not tokens:
                continue
            part = (
                bm25.get_scores(tokens) * weight
                if weight != 1
                else bm25.get_scores(tokens)
            )
            scores = part if scores is None else scores + part
        if scores is None:
            return []
        live = self._live
        results = []
        for idx in scores.argsort()[-k:][::-1]:
            score = float(scores[idx])
            if score < min_score:
                continue
            doc_id = live._doc_ids[idx]
            metadata = dict(live._metadata.get(doc_id, {}))
            if "content" not in metadata and idx < len(live._documents):
                metadata["content"] = live._documents[idx]
            results.append((doc_id, score, metadata))
        return results


def build_arms(
    live: Any, arm_names: list[str], weights: list[float]
) -> tuple[dict[str, ArmIndex], dict[str, Any]]:
    """Build every requested arm once. Returns ``(arms, build_info)``."""
    from rank_bm25 import BM25Okapi

    from search.bm25_index import TextPreprocessor

    doc_ids, docs = list(live._doc_ids), list(live._documents)
    k1, b = live.k1, live.b

    def prep(variant: str) -> Any:
        return TextPreprocessor(
            use_stopwords=live.use_stopwords, use_stemming=False, tokenizer=variant
        )

    cache: dict[tuple[str, str], tuple[Any, Any]] = {}

    def component(corpus: str, variant: str, texts: list[str]) -> tuple[Any, Any]:
        key = (corpus, variant)
        if key not in cache:
            print(f"[BUILD] {corpus}/{variant} over {len(texts)} docs", flush=True)
            p = prep(variant)
            tokenized = [p.process(t) for t in texts]
            cache[key] = (BM25Okapi(tokenized, k1=k1, b=b), p)
        return cache[key]

    need_fields = any(a in arm_names for a in ("moved", "dup"))
    info: dict[str, Any] = {"n_docs": len(docs), "live_tokenizer": live.tokenizer}
    bodies: list[str] = []
    fields: list[str] = []
    if need_fields:
        bodies, info["unstripped_docs"] = split_body_and_field(doc_ids, docs)
        fields = [augmentation_text(c) for c in doc_ids]

    arms: dict[str, ArmIndex] = {}
    for name in arm_names:
        if name in ANALYZER_ARMS:
            bm25, p = component("full", name, docs)
            arms[name] = ArmIndex(live, [(bm25, p, 1.0)])
        elif name in ("moved", "dup"):
            field_bm25, field_p = component("field", "whole", fields)
            body_bm25, body_p = (
                component("body", "whole", bodies)
                if name == "moved"
                else component("full", "whole", docs)
            )
            for w in weights:
                arms[f"{name}_w{w:g}"] = ArmIndex(
                    live, [(body_bm25, body_p, 1.0), (field_bm25, field_p, w)]
                )
        else:
            raise ValueError(f"Unknown arm {name!r}")
    return arms, info


# ---------------------------------------------------------------------------
# Per-query scoring
# ---------------------------------------------------------------------------


def is_python_chunk(chunk_id: str) -> bool:
    return chunk_id.split(":", 1)[0].endswith(".py")


def gold_set(grades: dict[str, int], min_grade: int, python_only: bool) -> set[str]:
    gold = {g for g, grade in grades.items() if grade >= min_grade}
    return {g for g in gold if is_python_chunk(g)} if python_only else gold


def classify(gold: set[str], cap: dict[str, list[str]]) -> str:
    """Query status: any gold in the fused cut / only in a raw leg / in neither."""
    if gold & set(cap["fused"]):
        return IN_POOL
    if gold & (set(cap["bm25"]) | set(cap["dense"])):
        return FUSION_CUT_MISS
    return LEG_MISS


def bm25_metrics(gold: set[str], bm25_ids: list[str]) -> tuple[float, float]:
    """``(reciprocal rank of first gold, recall@10)`` on the BM25-only leg."""
    rr = 0.0
    for rank, cid in enumerate(bm25_ids, 1):
        if cid in gold:
            rr = 1.0 / rank
            break
    r10 = len(gold & set(bm25_ids[:10])) / len(gold)
    return rr, r10


def capture(session: Any, query: str, k: int, depth: int) -> dict[str, list[str]]:
    cap = session.replay_legs(query, k=k, depth=depth)
    return {"bm25": cap.bm25, "dense": cap.dense, "fused": cap.fused}


def run_queries(
    session: Any, items: list[Any], arms: dict[str, ArmIndex], k: int, depth: int
) -> tuple[dict[str, dict[str, dict[str, list[str]]]], list[str]]:
    """Capture legs per ``arm -> query id``. Returns ``(captures, fidelity_errors)``."""
    executor = session.searcher.search_executor
    live_index = executor.bm25_index
    captures: dict[str, dict[str, dict[str, list[str]]]] = defaultdict(dict)
    errors: list[str] = []
    try:
        for i, item in enumerate(items, 1):
            print(f"[{i:3d}/{len(items)}] {item.id}", flush=True)
            live_cap = capture(session, item.query, k, depth)
            captures["live"][item.id] = live_cap
            for name, arm in arms.items():
                executor.bm25_index = arm
                captures[name][item.id] = capture(session, item.query, k, depth)
                executor.bm25_index = live_index
                if captures[name][item.id]["dense"] != live_cap["dense"]:
                    errors.append(f"{item.id}/{name}: dense leg differs from live")
            if "whole" in arms and live_index.tokenizer == "whole":
                whole = captures["whole"][item.id]
                for leg in ("bm25", "fused"):
                    if whole[leg] != live_cap[leg]:
                        errors.append(f"{item.id}: whole arm {leg} != live {leg}")
    finally:
        executor.bm25_index = live_index
    return captures, errors


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def summarize(
    items: list[Any],
    captures: dict[str, dict[str, dict[str, list[str]]]],
    min_grade: int,
) -> dict[str, Any]:
    """Per arm x slice x stratum: status counts, transitions vs whole, BM25 metrics."""
    slices = {"all": False, "python_gold": True}
    out: dict[str, Any] = {}
    for arm in captures:
        if arm == "live":
            continue
        out[arm] = {}
        for slice_name, py_only in slices.items():
            strata: dict[str, dict[str, Any]] = {}
            for item in items:
                gold = gold_set(item.grades, min_grade, py_only)
                if not gold:
                    continue
                cap = captures[arm][item.id]
                base = captures["whole"][item.id]
                status, base_status = classify(gold, cap), classify(gold, base)
                rr, r10 = bm25_metrics(gold, cap["bm25"])
                for stratum in (item.category, "ALL"):
                    row = strata.setdefault(
                        stratum,
                        {
                            "n": 0,
                            "status": Counter(),
                            "transitions": Counter(),
                            "rescued": [],
                            "created": [],
                            "mrr": 0.0,
                            "r10": 0.0,
                        },
                    )
                    row["n"] += 1
                    row["status"][status] += 1
                    row["transitions"][f"{base_status}->{status}"] += 1
                    row["mrr"] += rr
                    row["r10"] += r10
                    if base_status == FUSION_CUT_MISS and status == IN_POOL:
                        row["rescued"].append(item.id)
                    if base_status == IN_POOL and status == FUSION_CUT_MISS:
                        row["created"].append(item.id)
            for row in strata.values():
                row["net"] = len(row["rescued"]) - len(row["created"])
                row["mrr"] = round(row["mrr"] / row["n"], 4)
                row["r10"] = round(row["r10"] / row["n"], 4)
                row["status"] = dict(row["status"])
                row["transitions"] = dict(row["transitions"])
            out[arm][slice_name] = strata
    return out


def print_summary(summary: dict[str, Any]) -> None:
    for slice_name in ("all", "python_gold"):
        print(f"\n=== slice: {slice_name} (net = rescued - created vs whole) ===")
        print(
            f"{'arm':<14}{'stratum':<10}{'n':>4}{'pool':>6}{'fcm':>5}{'leg':>5}"
            f"{'resc':>6}{'crea':>6}{'net':>5}{'bm25MRR':>9}{'bm25R@10':>10}"
        )
        for arm, per_slice in summary.items():
            for stratum, row in sorted(per_slice.get(slice_name, {}).items()):
                st = row["status"]
                print(
                    f"{arm:<14}{stratum:<10}{row['n']:>4}"
                    f"{st.get(IN_POOL, 0):>6}{st.get(FUSION_CUT_MISS, 0):>5}"
                    f"{st.get(LEG_MISS, 0):>5}{len(row['rescued']):>6}"
                    f"{len(row['created']):>6}{row['net']:>5}"
                    f"{row['mrr']:>9.4f}{row['r10']:>10.4f}"
                )


def pool_candidates(
    session: Any,
    drafts: list[dict[str, Any]],
    arms: dict[str, ArmIndex],
    depth: int,
    top_n: int,
) -> list[dict[str, Any]]:
    """Grading pool: union of each arm's BM25 top-N and the dense top-N per draft.

    Pooling across arms (not just the live leg) keeps the grading set from being
    biased toward whichever analyzer happens to be the baseline.
    """
    executor = session.searcher.search_executor
    live_index = executor.bm25_index
    live = live_index
    content_of = dict(zip(live._doc_ids, live._documents, strict=True))
    norm_to_raw = {normalize_chunk_id(c): c for c in live._doc_ids}
    out: list[dict[str, Any]] = []
    try:
        for draft in drafts:
            surfaced: dict[str, dict[str, int]] = defaultdict(dict)
            dense_done = False
            for name, arm in arms.items():
                executor.bm25_index = arm
                cap = capture(session, draft["query"], 10, depth)
                executor.bm25_index = live_index
                for rank, cid in enumerate(cap["bm25"][:top_n], 1):
                    surfaced[cid][f"bm25:{name}"] = rank
                if not dense_done:
                    for rank, cid in enumerate(cap["dense"][:top_n], 1):
                        surfaced[cid]["dense"] = rank
                    dense_done = True
            intended = {normalize_chunk_id(c) for c in draft["intended_chunk_ids"]}
            for cid in intended:
                surfaced.setdefault(cid, {})
            rows = []
            for cid, ranks in surfaced.items():
                raw = norm_to_raw.get(cid)
                text = content_of.get(raw, "") if raw else ""
                rows.append(
                    {
                        "chunk_id": cid,
                        "in_index": raw is not None,
                        "intended": cid in intended,
                        "ranks": ranks,
                        "preview": text[:600],
                    }
                )
            rows.sort(
                key=lambda r: (not r["intended"], min(r["ranks"].values(), default=999))
            )
            out.append(
                {
                    "id": draft["id"],
                    "stratum": draft["stratum"],
                    "query": draft["query"],
                    "gold_note": draft.get("gold_note", ""),
                    "candidates": rows,
                }
            )
            print(f"[POOL] {draft['id']}: {len(rows)} candidates", flush=True)
    finally:
        executor.bm25_index = live_index
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    parser.add_argument("--depth", type=int, default=100)
    parser.add_argument("--min-grade", type=int, default=3)
    parser.add_argument("--weights", type=float, nargs="*", default=[0.5, 1.0, 2.0])
    parser.add_argument(
        "--arms",
        nargs="*",
        default=["whole", "additive", "case_gated", "moved", "dup"],
    )
    parser.add_argument("--exclude-categories", nargs="*", default=["D", "F"])
    parser.add_argument(
        "--pool-draft",
        default=None,
        help="Draft query JSON (id/stratum/query/intended_chunk_ids). Writes a "
        "grading pool to --json instead of scoring arms.",
    )
    parser.add_argument("--pool-top", type=int, default=20)
    args = parser.parse_args()

    arm_names = ["whole"] + [a for a in args.arms if a != "whole"]
    if args.pool_draft:
        drafts = json.loads(Path(args.pool_draft).read_text(encoding="utf-8"))
        with probe_harness.open_probe(args) as session:
            live = session.searcher.search_executor.bm25_index
            arms, info = build_arms(live, arm_names, args.weights)
            pool = pool_candidates(session, drafts, arms, args.depth, args.pool_top)
            if args.json_out:
                probe_harness.write_probe_json(
                    args.json_out, {"build_info": info, "pool": pool}
                )
        return 0
    try:
        items = probe_harness.load_golden_queries(
            probe_harness.resolve_dataset_path(args.dataset),
            args.query_ids,
            exclude_categories=tuple(args.exclude_categories),
        )
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    with probe_harness.open_probe(args) as session:
        live = session.searcher.search_executor.bm25_index
        known_norm = {normalize_chunk_id(c) for c in live.doc_ids}
        for item in items:
            missing = [g for g in item.grades if g not in known_norm]
            if missing:
                print(f"WARN {item.id}: graded chunk_ids not in index: {missing}")
        arms, info = build_arms(live, arm_names, args.weights)
        captures, errors = run_queries(session, items, arms, args.k, args.depth)

        summary = summarize(items, captures, args.min_grade)
        print_summary(summary)
        print(f"\nbuild info: {info}")

        if args.json_out:
            probe_harness.write_probe_json(
                args.json_out,
                {
                    "args": {k: v for k, v in vars(args).items() if k != "json_out"},
                    "build_info": info,
                    "fidelity_errors": errors,
                    "summary": summary,
                    "captures": captures,
                },
            )

    if errors:
        print(f"\nVERDICT: RED - {len(errors)} fidelity error(s); first 10:")
        for e in errors[:10]:
            print(f"  {e}")
        return 1
    print("\nFidelity: GREEN (whole arm == live; dense legs identical across arms)")
    return 0


if __name__ == "__main__":
    import os

    os.environ["CLAUDE_AUTO_REINDEX"] = "0"
    probe_harness.ensure_pinned_hash_seed()
    sys.exit(main())
