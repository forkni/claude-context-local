#!/usr/bin/env python3
"""BM25 path/symbol token augmentation A/B (Track D).

Compares the live whole-tokenizer BM25 corpus against the same corpus with each
document augmented by its path components and symbol name (whole + camel/snake
sub-tokens, via ``search.tokenization.build_path_symbol_text`` — the exact
helper production would use in ``HybridSearcher.add_embeddings``).

Design notes (mirrors bm25_tokenizer_ab.py):
  - Baseline tokens come straight from the on-disk ``bm25_docs.json``
    ``tokenized_docs`` (built by the production whole tokenizer at index time).
  - Augmentation tokens are produced by running the augmentation text through
    the same production ``TextPreprocessor`` (whole, stopwords on) and appending
    to the stored tokens — equivalent to appending the text to the document
    before tokenization, which is what add_embeddings would do.
  - Path/symbol come from parsing each doc_id (``path:lines:type:name``), the
    same fields add_embeddings has via chunk metadata.
  - Scoring reuses ``evaluation.metrics`` untouched; category-D queries are
    excluded (matches run_sscg_benchmark.py). BM25Okapi defaults k1=1.5 b=0.75
    (the shipped config defaults).
  - These are BM25-STANDALONE metrics — the Track D primary gate. Fused
    no-regression is a separate run_sscg_benchmark.py pass after reindex.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/bm25_path_token_ab.py \
        --golden-dataset evaluation/golden_dataset.json \
        --golden-dataset evaluation/golden_dataset_expanded.json \
        --gold-rank-ids 102 103 122
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_id,
    normalize_chunk_ids,
)
from search.bm25_index import TextPreprocessor  # noqa: E402
from search.tokenization import build_path_symbol_text  # noqa: E402


try:
    from rank_bm25 import BM25Okapi
except ImportError as e:
    raise ImportError(
        "rank_bm25 package is required for this harness. "
        "Install with: pip install rank_bm25"
    ) from e


def _find_bm25_docs_path(project_path: str) -> Path:
    from mcp_server.storage_manager import get_project_storage_dir

    storage_dir = get_project_storage_dir(project_path)
    docs_path = storage_dir / "index" / "bm25" / "bm25_docs.json"
    if not docs_path.exists():
        raise FileNotFoundError(f"BM25 docs file not found: {docs_path}")
    return docs_path


def _parse_doc_id(doc_id: str) -> tuple[str, str] | None:
    """Split ``path:lines:type:name`` into (path, name); None if malformed."""
    parts = doc_id.split(":")
    if len(parts) < 4:
        return None
    return parts[0], ":".join(parts[3:])


def _augment_tokens(
    stored_tokens: list[list[str]], doc_ids: list[str], prep: TextPreprocessor
) -> tuple[list[list[str]], int]:
    """Append path/symbol tokens to each stored token list. Returns (docs, added_total)."""
    augmented: list[list[str]] = []
    added_total = 0
    for tokens, doc_id in zip(stored_tokens, doc_ids, strict=True):
        parsed = _parse_doc_id(doc_id)
        if parsed is None:
            augmented.append(tokens)
            continue
        path, name = parsed
        extra = prep.process(build_path_symbol_text(path, name))
        added_total += len(extra)
        augmented.append(tokens + extra)
    return augmented, added_total


def _gold_ranks(
    bm25: "BM25Okapi", prep: TextPreprocessor, doc_ids: list[str], q: dict[str, Any]
) -> int | None:
    """Full-corpus rank (1-based) of the best-ranked gold chunk; None if absent."""
    query_tokens = prep.process(q["query"])
    if not query_tokens:
        return None
    scores = bm25.get_scores(query_tokens)
    order = scores.argsort()[::-1]
    expected = set(q["expected"])
    for rank, idx in enumerate(order, start=1):
        if normalize_chunk_id(doc_ids[idx]) in expected:
            return rank
    return None


def _run_variant(
    label: str,
    tokenized_docs: list[list[str]],
    doc_ids: list[str],
    queries: list[dict[str, Any]],
    prep: TextPreprocessor,
    k: int,
) -> dict[str, Any]:
    bm25 = BM25Okapi(tokenized_docs)
    per_query: list[dict[str, Any]] = []
    for q in queries:
        query_tokens = prep.process(q["query"])
        if query_tokens:
            scores = bm25.get_scores(query_tokens)
            top_indices = scores.argsort()[-k:][::-1]
            ranked = sorted(
                ((float(scores[i]), doc_ids[i]) for i in top_indices),
                key=lambda x: x[0],
                reverse=True,
            )
            retrieved = normalize_chunk_ids([cid for _, cid in ranked])
        else:
            retrieved = []
        metrics = calculate_metrics_from_results(
            retrieved, q["expected"], q.get("expected_primary", q["expected"])
        )
        metrics["query_id"] = q["id"]
        metrics["category"] = q["category"]
        metrics["query"] = q["query"]
        per_query.append(metrics)
    return {"label": label, "bm25": bm25, "per_query": per_query}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BM25 path/symbol token augmentation A/B (Track D)"
    )
    parser.add_argument("--project-path", default=str(PROJECT_ROOT))
    parser.add_argument(
        "--golden-dataset",
        action="append",
        default=None,
        help="Golden dataset path; repeatable (default: both golden sets)",
    )
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument(
        "--gold-rank-ids",
        nargs="*",
        default=["102", "103", "122"],
        help="Query IDs (expanded set) to report full-corpus gold ranks for",
    )
    args = parser.parse_args()

    datasets = args.golden_dataset or [
        str(PROJECT_ROOT / "evaluation" / "golden_dataset.json"),
        str(PROJECT_ROOT / "evaluation" / "golden_dataset_expanded.json"),
    ]

    docs_path = _find_bm25_docs_path(args.project_path)
    print(f"[INFO] Loading corpus from: {docs_path}")
    docs_data = json.loads(docs_path.read_text(encoding="utf-8"))
    doc_ids = docs_data["doc_ids"]
    stored_tokenized = docs_data["tokenized_docs"]
    print(f"[INFO] Corpus: {len(doc_ids)} documents")

    prep = TextPreprocessor(use_stopwords=True, use_stemming=False, tokenizer="whole")

    augmented_tokenized, added_total = _augment_tokens(stored_tokenized, doc_ids, prep)
    base_len = sum(len(t) for t in stored_tokenized)
    print(
        f"[INFO] Augmentation: +{added_total} tokens over {base_len} "
        f"({100.0 * added_total / base_len:.1f}% corpus growth, "
        f"avg +{added_total / len(doc_ids):.1f}/doc)"
    )

    for ds_path in datasets:
        golden = json.loads(Path(ds_path).read_text(encoding="utf-8"))
        queries = [q for q in golden["queries"] if q.get("category") != "D"]
        thresholds = golden.get("thresholds")
        print(
            f"\n{'=' * 88}\nDATASET: {Path(ds_path).name} ({len(queries)} queries, category-D excluded)\n{'=' * 88}"
        )

        results = {}
        for label, tokens in (
            ("baseline", stored_tokenized),
            ("path_aug", augmented_tokenized),
        ):
            results[label] = _run_variant(label, tokens, doc_ids, queries, prep, args.k)

        print(
            f"{'Variant':<10} {'MRR':>7} {'R@5':>7} {'R@10':>7} {'Hit@5':>7} {'NDCG@10':>8}"
        )
        print("-" * 52)
        aggs = {}
        for label in ("baseline", "path_aug"):
            agg = aggregate_metrics(results[label]["per_query"], thresholds=thresholds)
            aggs[label] = agg
            print(
                f"{label:<10} {agg['mrr']:>7.4f} {agg['recall@5']:>7.4f} "
                f"{agg['recall@10']:>7.4f} {agg['hit_rate@5']:>7.4f} {agg['ndcg@10']:>8.4f}"
            )
        d_mrr = aggs["path_aug"]["mrr"] - aggs["baseline"]["mrr"]
        d_r5 = aggs["path_aug"]["recall@5"] - aggs["baseline"]["recall@5"]
        print(f"delta      dMRR={d_mrr:+.4f}  dRecall@5={d_r5:+.4f}")

        base = {q["query_id"]: q for q in results["baseline"]["per_query"]}
        movers = []
        for q in results["path_aug"]["per_query"]:
            delta = q["recall@5"] - base[q["query_id"]]["recall@5"]
            if abs(delta) > 1e-9:
                movers.append((q["query_id"], q["category"], delta, q["query"]))
        improved = sum(1 for m in movers if m[2] > 0)
        regressed = len(movers) - improved
        print(f"\nPer-query Recall@5 movers: improved={improved} regressed={regressed}")
        for qid, cat, delta, query in sorted(movers, key=lambda r: -abs(r[2])):
            sign = "+" if delta >= 0 else ""
            print(f"  {qid:<6} {cat:<3} {sign}{delta:>6.3f}  {query[:70]}")

        wanted = {qid.lstrip("Qq") for qid in args.gold_rank_ids}
        rank_queries = [q for q in queries if str(q["id"]).lstrip("Qq") in wanted]
        if rank_queries:
            print("\nFull-corpus gold ranks (baseline -> path_aug):")
            for q in rank_queries:
                r0 = _gold_ranks(results["baseline"]["bm25"], prep, doc_ids, q)
                r1 = _gold_ranks(results["path_aug"]["bm25"], prep, doc_ids, q)
                print(f"  Q{q['id']}: {r0} -> {r1}   {q['query'][:60]}")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "benchmark_results"
    out_dir.mkdir(exist_ok=True)
    print(f"\n[INFO] Done ({timestamp}). Aggregates printed above; no JSON emitted.")


if __name__ == "__main__":
    main()
