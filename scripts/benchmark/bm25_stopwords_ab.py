#!/usr/bin/env python3
"""BM25 stopword A/B recall harness (Dependency Optimization Plan, Phase F).

Compares ``bm25_use_stopwords`` True vs False under the production tokenizer
("whole", the shipped default per ``SearchModeConfig.bm25_tokenizer``) to
decide whether the import-time NLTK stopword-corpus download
(``search/bm25_index.py`` module load: ``nltk.data.find("corpora/stopwords")``
/ ``nltk.download("stopwords", quiet=True)``) can be removed.

Design notes (mirrors ``bm25_tokenizer_ab.py``, the Round-6/Track-A precedent):
  - No production code is monkey-patched — both arms are the real
    ``TextPreprocessor(use_stopwords=..., tokenizer="whole")`` construction,
    selected the same way the ``bm25_use_stopwords`` config knob selects it.
  - The whole corpus is re-tokenized **in memory** from the on-disk
    ``bm25_docs.json`` (raw ``documents`` + ``doc_ids``) — no reindex, no
    embedding recompute, no MCP restart; the live index files are only read.
  - Query-time tokenization reuses the *same* preprocessor instance per arm
    (mirrors ``BM25Index.search``), so index-time and query-time tokenization
    always match within an arm.
  - Scoring reuses ``evaluation.metrics`` untouched, same as the other
    benchmark harnesses, so results are comparable across runs.
  - Decision rule: recall-over-speed (project standing preference) — drop
    stopword filtering only if Recall@5/MRR do not regress with it off.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/bm25_stopwords_ab.py \
        --project-path D:/claude-context-local
    .venv/Scripts/python.exe scripts/benchmark/bm25_stopwords_ab.py \
        --golden-dataset evaluation/golden_dataset_expanded.json
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
    normalize_chunk_ids,
)
from search.bm25_index import TextPreprocessor  # noqa: E402


try:
    from rank_bm25 import BM25Okapi
except ImportError as e:
    raise ImportError(
        "rank_bm25 package is required for this harness. "
        "Install with: pip install rank_bm25"
    ) from e

VARIANTS = ("stopwords_on", "stopwords_off")


def _make_preprocessor(variant: str) -> TextPreprocessor:
    """Build a TextPreprocessor bound to `variant`.

    Tokenizer is held fixed at "whole" (the shipped production default,
    ``SearchModeConfig.bm25_tokenizer``) across both arms — this A/B isolates
    the stopword-filtering effect only. Stemming is never applied by "whole"
    (it corrupts code identifiers; see TextPreprocessor.__init__ docstring).
    """
    if variant == "stopwords_on":
        return TextPreprocessor(
            use_stopwords=True, use_stemming=False, tokenizer="whole"
        )
    if variant == "stopwords_off":
        return TextPreprocessor(
            use_stopwords=False, use_stemming=False, tokenizer="whole"
        )
    raise ValueError(f"Unknown variant: {variant!r}, expected one of {VARIANTS}")


def _find_bm25_docs_path(project_path: str) -> Path:
    """Resolve <storage>/index/bm25/bm25_docs.json for the given project."""
    from mcp_server.storage_manager import get_project_storage_dir

    storage_dir = get_project_storage_dir(project_path)
    docs_path = storage_dir / "index" / "bm25" / "bm25_docs.json"
    if not docs_path.exists():
        raise FileNotFoundError(f"BM25 docs file not found: {docs_path}")
    return docs_path


def _tokenize_corpus(
    prep: TextPreprocessor, documents: list[str]
) -> tuple[list[list[str]], float]:
    start = time.perf_counter()
    tokenized = [prep.process(doc) for doc in documents]
    elapsed = time.perf_counter() - start
    return tokenized, elapsed


def _search(
    bm25: "BM25Okapi", prep: TextPreprocessor, doc_ids: list[str], query: str, k: int
) -> list[tuple[float, str]]:
    query_tokens = prep.process(query)
    if not query_tokens:
        return []
    scores = bm25.get_scores(query_tokens)
    top_indices = scores.argsort()[-k:][::-1]
    return [(float(scores[idx]), doc_ids[idx]) for idx in top_indices]


def run_variant(
    variant: str,
    documents: list[str],
    doc_ids: list[str],
    queries: list[dict[str, Any]],
    k: int,
) -> dict[str, Any]:
    prep = _make_preprocessor(variant)
    tokenized_docs, tokenize_seconds = _tokenize_corpus(prep, documents)
    bm25 = BM25Okapi(tokenized_docs)

    distinct_stems = len({tok for doc in tokenized_docs for tok in doc})

    per_query: list[dict[str, Any]] = []
    raw_results: dict[str, list[tuple[float, str]]] = {}
    for q in queries:
        raw = _search(bm25, prep, doc_ids, q["query"], k)
        raw_results[q["id"]] = raw
        sorted_raw = sorted(raw, key=lambda x: x[0], reverse=True)
        retrieved = normalize_chunk_ids([cid for _, cid in sorted_raw])
        metrics = calculate_metrics_from_results(
            retrieved, q["expected"], q.get("expected_primary", q["expected"])
        )
        metrics["query_id"] = q["id"]
        metrics["category"] = q["category"]
        metrics["query"] = q["query"]
        per_query.append(metrics)

    return {
        "variant": variant,
        "tokenize_seconds": round(tokenize_seconds, 4),
        "distinct_stems": distinct_stems,
        "per_query": per_query,
        "raw_results": raw_results,
    }


def _print_aggregate_table(rows: list[tuple[str, dict[str, Any]]], title: str) -> None:
    print(f"\n{'=' * 88}\n{title}\n{'=' * 88}")
    print(
        f"{'Variant':<14} {'MRR':>7} {'R@5':>7} {'R@10':>7} {'Hit@5':>7} "
        f"{'NDCG@5':>8} {'NDCG@10':>8} {'Tok(s)':>8} {'Terms':>8}"
    )
    print("-" * 88)
    for variant, agg in rows:
        print(
            f"{variant:<14} {agg['mrr']:>7.4f} {agg['recall@5']:>7.4f} "
            f"{agg['recall@10']:>7.4f} {agg['hit_rate@5']:>7.4f} "
            f"{agg['ndcg@5']:>8.4f} {agg['ndcg@10']:>8.4f} "
            f"{agg.get('_tokenize_seconds', 0):>8.3f} {agg.get('_distinct_stems', 0):>8}"
        )


def _print_delta_table(
    baseline_per_query: list[dict[str, Any]],
    variant_per_query: list[dict[str, Any]],
    variant_name: str,
) -> tuple[int, int, int]:
    base = {q["query_id"]: q for q in baseline_per_query}
    improved = unchanged = regressed = 0
    rows = []
    for q in variant_per_query:
        qid = q["query_id"]
        b = base.get(qid)
        if b is None:
            continue
        delta = q["recall@5"] - b["recall@5"]
        if delta > 1e-9:
            improved += 1
        elif delta < -1e-9:
            regressed += 1
        else:
            unchanged += 1
        if abs(delta) > 1e-9:
            rows.append((qid, q["category"], delta, q["query"]))

    print(f"\n--- {variant_name} vs stopwords_on: per-query Recall@5 delta ---")
    print(f"  improved={improved}  unchanged={unchanged}  regressed={regressed}")
    if rows:
        print(f"{'ID':<6} {'Cat':<4} {'dR@5':>7}  Query")
        print("-" * 60)
        for qid, cat, delta, query in sorted(rows, key=lambda r: -abs(r[2])):
            sign = "+" if delta >= 0 else ""
            print(f"{qid:<6} {cat:<4} {sign}{delta:>6.3f}  {query}")
    return improved, unchanged, regressed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BM25 stopword A/B recall harness (Phase F)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-path",
        default=str(PROJECT_ROOT),
        help="Path to the indexed project (default: this repo)",
    )
    parser.add_argument(
        "--golden-dataset",
        default=str(PROJECT_ROOT / "evaluation" / "golden_dataset.json"),
        help="Path to golden_dataset.json",
    )
    parser.add_argument("--k", type=int, default=10, help="Top-k results per query")
    args = parser.parse_args()

    docs_path = _find_bm25_docs_path(args.project_path)
    print(f"[INFO] Loading corpus from: {docs_path}")
    docs_data = json.loads(docs_path.read_text(encoding="utf-8"))
    documents = docs_data["documents"]
    doc_ids = docs_data["doc_ids"]
    print(f"[INFO] Corpus: {len(documents)} documents")

    golden = json.loads(Path(args.golden_dataset).read_text(encoding="utf-8"))
    queries = golden["queries"]
    print(f"[INFO] Golden dataset: {len(queries)} queries")

    results: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        print(f"\n[INFO] Running variant: {variant}")
        results[variant] = run_variant(variant, documents, doc_ids, queries, args.k)

    thresholds = golden.get("thresholds")
    excl_d_aggs: dict[str, Any] = {}

    for label, filt in (
        ("all-categories", lambda q: True),
        ("excluding-D", lambda q: q["category"] != "D"),
    ):
        rows = []
        d_count = sum(1 for q in queries if not filt(q))
        subset_note = f" ({d_count} category-D queries excluded)" if d_count else ""
        print(f"\n[INFO] Aggregate scope: {label}{subset_note}")
        for variant in VARIANTS:
            r = results[variant]
            subset = [
                q
                for q in r["per_query"]
                if filt(next(qq for qq in queries if qq["id"] == q["query_id"]))
            ]
            agg = aggregate_metrics(subset, thresholds=thresholds)
            agg["_tokenize_seconds"] = r["tokenize_seconds"]
            agg["_distinct_stems"] = r["distinct_stems"]
            rows.append((variant, agg))
        _print_aggregate_table(
            rows, f"BM25 STOPWORD A/B — {label} ({len(queries) - d_count} queries)"
        )
        if label == "excluding-D":
            excl_d_aggs = dict(rows)

    on_subset = [
        q
        for q in results["stopwords_on"]["per_query"]
        if next(qq for qq in queries if qq["id"] == q["query_id"])["category"] != "D"
    ]
    off_subset = [
        q
        for q in results["stopwords_off"]["per_query"]
        if next(qq for qq in queries if qq["id"] == q["query_id"])["category"] != "D"
    ]
    _print_delta_table(on_subset, off_subset, "stopwords_off")

    # --- Decision rule (recall-over-speed) -------------------------------
    print(
        f"\n{'=' * 88}\nDECISION (excluding-D, Recall@5 / MRR, off vs on)\n{'=' * 88}"
    )
    on_agg = excl_d_aggs["stopwords_on"]
    off_agg = excl_d_aggs["stopwords_off"]
    d_r5 = off_agg["recall@5"] - on_agg["recall@5"]
    d_mrr = off_agg["mrr"] - on_agg["mrr"]
    if d_r5 >= -0.005 and d_mrr >= -0.005:
        verdict = "DROP STOPWORDS (recall holds within noise; remove NLTK stopword dep)"
    else:
        verdict = (
            "KEEP STOPWORDS (recall-over-speed: measurable regression without them)"
        )
    print(f"  dRecall@5={d_r5:+.4f}  dMRR={d_mrr:+.4f}  -> {verdict}")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "benchmark_results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"bm25_stopwords_ab_{timestamp}.json"
    save_data = {
        "timestamp": timestamp,
        "k": args.k,
        "corpus_size": len(documents),
        "query_count": len(queries),
        "variants": {
            variant: {
                "tokenize_seconds": r["tokenize_seconds"],
                "distinct_stems": r["distinct_stems"],
                "aggregate_all": aggregate_metrics(
                    r["per_query"], thresholds=thresholds
                ),
                "aggregate_excluding_d": excl_d_aggs[variant],
                "per_query": r["per_query"],
            }
            for variant, r in results.items()
        },
        "decision": {"d_recall_at_5": d_r5, "d_mrr": d_mrr, "verdict": verdict},
    }
    out_path.write_text(json.dumps(save_data, indent=2), encoding="utf-8")
    print(f"\n[INFO] Full results saved to: {out_path}")


if __name__ == "__main__":
    main()
