#!/usr/bin/env python3
"""BM25 tokenizer A/B recall harness (Round 6 → Track A, arXiv 2605.18561).

Round 6 compared word-tokenizer callables (split/nltk/wordpunct) under the
legacy destructive camel/snake preprocessing; split won and remains the
production default. Track A re-frames the question per arXiv 2605.18561
("Improving BM25 Code Retrieval Under Fixed Generic Tokenization"): the
destructive parts-only preprocessing itself is the paper's worst-case
configuration, and identifier-preserving variants should beat it.

Variants compared (all via TextPreprocessor.process, the exact production
path used by BM25Index.index_documents/search):
  - split         legacy: destructive camel/snake split + stemming (shipped default)
  - split_nostem  legacy preprocessing with stemming disabled (isolates stemming)
  - whole         T1: identifiers kept whole (lowercased), no stemming
  - additive      T2: whole identifiers + camel/snake sub-tokens, no stemming

Design notes:
  - No production code is monkey-patched for whole/additive — they are the
    real ``tokenizer=`` variants shipped in TextPreprocessor, selected the
    same way the ``bm25_tokenizer`` config knob selects them.
  - The whole corpus is re-tokenized **in memory** from the on-disk
    ``bm25_docs.json`` (raw ``documents`` + ``doc_ids``), which is exactly
    what ``BM25Index.index_documents`` does at index time. No reindex, no
    embedding recompute, no MCP restart; the live index files are only read.
  - Query-time tokenization reuses the *same* preprocessor instance per
    variant (mirrors ``BM25Index.search``), so index-time and query-time
    tokenization always match within a variant — the comparison is
    apples-to-apples.
  - Scoring reuses ``evaluation.metrics`` untouched (calculate_metrics_from_results,
    aggregate_metrics, normalize_chunk_ids) — the same functions the other
    benchmark harnesses use, so results are comparable across runs.
  - These are BM25-STANDALONE metrics — per evaluation/POOL_MISS_DIAGNOSIS.md
    this is the primary Track A gate (BM25-unique candidates cannot enter the
    fused pool under current fusion parameters, so fused pool_hit is
    insensitive to this leg by construction).

Usage:
    ./scripts/benchmark/bm25_tokenizer_ab.sh --project-path D:/claude-context-local
    ./scripts/benchmark/bm25_tokenizer_ab.sh --project-path D:/claude-context-local \
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

VARIANTS = ("split", "split_nostem", "whole", "additive")


def _make_preprocessor(variant: str) -> TextPreprocessor:
    """Build a TextPreprocessor bound to `variant`.

    Stopwords are held fixed (use_stopwords=True — production default) across
    all variants. The two legacy variants pin ``_tokenize_words`` to str.split
    (the shipped Round-6 winner) so the destructive-preprocessing pipeline is
    byte-identical to production; whole/additive are the real ``tokenizer=``
    config variants and never touch that callable.
    """
    if variant == "split":
        prep = TextPreprocessor(use_stopwords=True, use_stemming=True)
        prep._tokenize_words = str.split
    elif variant == "split_nostem":
        prep = TextPreprocessor(use_stopwords=True, use_stemming=False)
        prep._tokenize_words = str.split
    elif variant == "whole":
        prep = TextPreprocessor(
            use_stopwords=True, use_stemming=False, tokenizer="whole"
        )
    elif variant == "additive":
        prep = TextPreprocessor(
            use_stopwords=True, use_stemming=False, tokenizer="additive"
        )
    else:
        raise ValueError(f"Unknown variant: {variant!r}, expected one of {VARIANTS}")
    return prep


def _find_bm25_docs_path(project_path: str) -> Path:
    """Resolve <storage>/index/bm25/bm25_docs.json for the given project.

    Reuses the production storage-dir resolver so the path always matches
    what the live MCP server is using, including model/dimension suffixing.
    """
    from mcp_server.storage_manager import get_project_storage_dir

    storage_dir = get_project_storage_dir(project_path)
    docs_path = storage_dir / "index" / "bm25" / "bm25_docs.json"
    if not docs_path.exists():
        raise FileNotFoundError(f"BM25 docs file not found: {docs_path}")
    return docs_path


def _tokenize_corpus(
    prep: TextPreprocessor, documents: list[str]
) -> tuple[list[list[str]], float]:
    """Re-tokenize every document, mirroring BM25Index.index_documents exactly."""
    start = time.perf_counter()
    tokenized = [prep.process(doc) for doc in documents]
    elapsed = time.perf_counter() - start
    return tokenized, elapsed


def _search(
    bm25: "BM25Okapi", prep: TextPreprocessor, doc_ids: list[str], query: str, k: int
) -> list[tuple[float, str]]:
    """Score `query` against `bm25`, mirroring BM25Index.search exactly."""
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
    """Build the variant's index, run every query, and score it."""
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
        "tokenized_docs": tokenized_docs,  # only used by split for the self-check
    }


def _print_aggregate_table(rows: list[tuple[str, dict[str, Any]]], title: str) -> None:
    print(f"\n{'=' * 88}\n{title}\n{'=' * 88}")
    print(
        f"{'Variant':<11} {'MRR':>7} {'R@5':>7} {'R@10':>7} {'Hit@5':>7} "
        f"{'NDCG@5':>8} {'NDCG@10':>8} {'Tok(s)':>8} {'Stems':>8}"
    )
    print("-" * 88)
    for variant, agg in rows:
        print(
            f"{variant:<11} {agg['mrr']:>7.4f} {agg['recall@5']:>7.4f} "
            f"{agg['recall@10']:>7.4f} {agg['hit_rate@5']:>7.4f} "
            f"{agg['ndcg@5']:>8.4f} {agg['ndcg@10']:>8.4f} "
            f"{agg.get('_tokenize_seconds', 0):>8.3f} {agg.get('_distinct_stems', 0):>8}"
        )


def _print_delta_table(
    baseline_per_query: list[dict[str, Any]],
    variant_per_query: list[dict[str, Any]],
    variant_name: str,
) -> tuple[int, int, int]:
    """Print per-query recall@5 delta vs the split baseline. Returns (improved, unchanged, regressed)."""
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

    print(f"\n--- {variant_name} vs split: per-query Recall@5 delta ---")
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
        description="BM25 tokenizer A/B recall harness (Round 6)",
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
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Top-k results retrieved per query (default: 10)",
    )
    parser.add_argument(
        "--emit-raw-results",
        action="store_true",
        help=(
            "Also write the winning (or, if none wins, the split baseline) arm's "
            "raw results to evaluation/raw_mcp_results_bm25.json, refreshing the "
            "stale 13-query/2026-04-10 snapshot so mcp_eval.py --mode bm25 works again."
        ),
    )
    args = parser.parse_args()

    docs_path = _find_bm25_docs_path(args.project_path)
    print(f"[INFO] Loading corpus from: {docs_path}")
    docs_data = json.loads(docs_path.read_text(encoding="utf-8"))
    documents = docs_data["documents"]
    doc_ids = docs_data["doc_ids"]
    stored_tokenized_docs = docs_data["tokenized_docs"]
    print(f"[INFO] Corpus: {len(documents)} documents")

    golden = json.loads(Path(args.golden_dataset).read_text(encoding="utf-8"))
    queries = golden["queries"]
    print(f"[INFO] Golden dataset: {len(queries)} queries")

    results: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        print(f"\n[INFO] Running variant: {variant}")
        results[variant] = run_variant(variant, documents, doc_ids, queries, args.k)

    # --- Verification item 1: harness self-check -----------------------------
    split_tokenized = results["split"]["tokenized_docs"]
    if split_tokenized != stored_tokenized_docs:
        mismatches = sum(
            1
            for a, b in zip(split_tokenized, stored_tokenized_docs, strict=False)
            if a != b
        )
        print(
            f"[FAIL] Harness self-check: split-variant tokenization diverges from "
            f"the stored bm25_docs.json tokenized_docs on {mismatches}/{len(documents)} "
            f"documents (length {len(split_tokenized)} vs {len(stored_tokenized_docs)}). "
            f"The harness itself is suspect — do not trust the recall numbers below.",
            file=sys.stderr,
        )
    else:
        print(
            f"[OK] Harness self-check: split variant reproduces the stored "
            f"tokenized_docs byte-for-byte ({len(documents)}/{len(documents)})."
        )

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
            rows, f"BM25 TOKENIZER A/B — {label} ({len(queries) - d_count} queries)"
        )
        if label == "excluding-D":
            excl_d_aggs = dict(rows)

    split_subset = [
        q
        for q in results["split"]["per_query"]
        if next(qq for qq in queries if qq["id"] == q["query_id"])["category"] != "D"
    ]
    for variant in VARIANTS[1:]:
        variant_subset = [
            q
            for q in results[variant]["per_query"]
            if next(qq for qq in queries if qq["id"] == q["query_id"])["category"]
            != "D"
        ]
        _print_delta_table(split_subset, variant_subset, variant)

    # --- Decision rule (Phase 3) ----------------------------------------------
    print(f"\n{'=' * 88}\nDECISION (excluding-D, Recall@5 / MRR vs split)\n{'=' * 88}")
    split_agg = excl_d_aggs["split"]
    for variant in VARIANTS[1:]:
        agg = excl_d_aggs[variant]
        d_r5 = agg["recall@5"] - split_agg["recall@5"]
        d_mrr = agg["mrr"] - split_agg["mrr"]
        if d_r5 > 0.01 and d_mrr > 0.01:
            verdict = "ADOPT (beats split on both Recall@5 and MRR)"
        elif d_r5 < -0.01 and d_mrr < -0.01:
            verdict = "REJECT (worse on both)"
        elif abs(d_r5) <= 0.01 and abs(d_mrr) <= 0.01:
            verdict = "FLAT (close out, no change warranted)"
        else:
            verdict = (
                "MIXED (prefer Recall@5 winner per standing recall-over-speed rule)"
            )
        print(f"  {variant:<11} dRecall@5={d_r5:+.4f}  dMRR={d_mrr:+.4f}  -> {verdict}")

    # --- Save ------------------------------------------------------------------
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = PROJECT_ROOT / "benchmark_results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"bm25_tokenizer_ab_{timestamp}.json"
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
    }
    out_path.write_text(json.dumps(save_data, indent=2), encoding="utf-8")
    print(f"\n[INFO] Full results saved to: {out_path}")

    if args.emit_raw_results:
        # Prefer the ADOPT variant if any; otherwise refresh with the split baseline.
        chosen = "split"
        for variant in VARIANTS[1:]:
            agg = excl_d_aggs[variant]
            if (
                agg["recall@5"] - split_agg["recall@5"] > 0.01
                and agg["mrr"] - split_agg["mrr"] > 0.01
            ):
                chosen = variant
                break
        raw = results[chosen]["raw_results"]
        raw_path = PROJECT_ROOT / "evaluation" / "raw_mcp_results_bm25.json"
        payload = {
            "mode": "bm25",
            "search_mode": "bm25",
            "collected_date": time.strftime("%Y-%m-%d"),
            "k": args.k,
            "description": (
                f"BM25-index-direct (not MCP-collected) — bm25_tokenizer_ab.py, "
                f"variant={chosen}, {len(queries)}-query golden dataset. Refreshes the "
                f"stale 13-query/2026-04-10 snapshot."
            ),
            "results": {
                qid: [[score, cid] for score, cid in entries]
                for qid, entries in raw.items()
            },
        }
        raw_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[INFO] Raw results ({chosen} variant) written to: {raw_path}")


if __name__ == "__main__":
    main()
