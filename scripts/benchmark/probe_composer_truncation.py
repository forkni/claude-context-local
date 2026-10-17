#!/usr/bin/env python
"""Audit the composer's 6,000-char budget against real model tokens, read-only.

``EmbeddingDocumentComposer.compose`` bounds each chunk's embedding document by
characters (``max_chars=6000``), never by tokens. This probe re-chunks a
project, composes every chunk twice (the production 6,000-char budget and an
effectively unbounded budget), and counts real tokens with each embedding
model's own tokenizer:

- how many chunks the char budget truncates;
- of those, how many would have fit inside the model's ``max_context`` untruncated
  (budget too conservative, lost text) versus genuinely exceed it;
- how many composed documents exceed ``max_context`` anyway (budget too loose);
- p50/p90/max composed tokens and chars/token, by chunk type.

It gates the conditional follow-up "budget = min(token budget, model max)": that
step is worth building only when a meaningful share of chunks is truncated while
fitting (lost text), or composed documents overflow ``max_context`` (silent
model-side truncation).

Re-chunks source files with the default chunker config, so TouchDesigner
``.tdgraph.json`` operator chunks (opt-in indexing, tiny) are not included.

Usage:
    .venv/Scripts/python.exe -m scripts.benchmark.probe_composer_truncation \
        --project-path D:/Users/alexk/FORKNI/TWOZERO/twozero-dev \
        [--max-chars 6000] [--models f2llm qwen3 bge-m3 gemma] [--json out.json]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from evaluation import probe_harness


MODELS = {
    "f2llm": "codefuse-ai/F2LLM-v2-0.6B",
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge-m3": "BAAI/bge-m3",
    "gemma": "google/embeddinggemma-300m",
}
UNBOUNDED = 10**9


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))]


def indexed_files(project_path: str) -> set[str]:
    """Relative file paths present in the project's live BM25 index."""
    args = argparse.Namespace(project_path=project_path, k=10, set_overrides=None)
    with probe_harness.open_probe(args) as session:
        live = session.searcher.search_executor.bm25_index
        return {re.split(r":\d+-\d+:", d, maxsplit=1)[0] for d in live._doc_ids}


def count_tokens(tokenizer: Any, texts: list[str]) -> list[int]:
    out: list[int] = []
    for start in range(0, len(texts), 256):
        batch = tokenizer(
            texts[start : start + 256],
            add_special_tokens=False,
            truncation=False,
            return_attention_mask=False,
        )["input_ids"]
        out.extend(len(ids) for ids in batch)
    return out


def analyse_model(
    name: str,
    model_id: str,
    max_context: int,
    chunk_types: list[str],
    budgeted: list[str],
    full: list[str],
) -> dict[str, Any]:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_id)
    tok_budgeted = count_tokens(tokenizer, budgeted)
    tok_full = count_tokens(tokenizer, full)
    truncated = [len(b) < len(f) for b, f in zip(budgeted, full, strict=True)]
    n = len(budgeted)

    n_trunc = sum(truncated)
    lost_but_fit = sum(
        1 for t, f in zip(truncated, tok_full, strict=True) if t and f <= max_context
    )
    genuinely_over = n_trunc - lost_but_fit
    composed_over = sum(1 for t in tok_budgeted if t > max_context)
    chars_per_token = sum(len(b) for b in budgeted) / max(1, sum(tok_budgeted))

    by_type: dict[str, list[int]] = defaultdict(list)
    for ct, t in zip(chunk_types, tok_budgeted, strict=True):
        by_type[ct].append(t)
    return {
        "model": model_id,
        "max_context": max_context,
        "n_chunks": n,
        "n_truncated_by_char_budget": n_trunc,
        "truncated_but_would_fit_max_context": lost_but_fit,
        "truncated_and_exceeds_max_context": genuinely_over,
        "composed_over_max_context": composed_over,
        "chars_per_token": round(chars_per_token, 3),
        "tokens_composed": {
            "p50": percentile(tok_budgeted, 0.5),
            "p90": percentile(tok_budgeted, 0.9),
            "p99": percentile(tok_budgeted, 0.99),
            "max": max(tok_budgeted, default=0),
        },
        "tokens_by_chunk_type": {
            ct: {
                "n": len(v),
                "p50": percentile(v, 0.5),
                "p90": percentile(v, 0.9),
                "max": max(v),
            }
            for ct, v in sorted(by_type.items(), key=lambda kv: -len(kv[1]))
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--max-chars", type=int, default=6000)
    parser.add_argument(
        "--models", nargs="*", default=list(MODELS), choices=list(MODELS)
    )
    parser.add_argument(
        "--only-indexed",
        action="store_true",
        help="keep only chunks from files in the live BM25 index (drops tests/, _archive/ ...)",
    )
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()

    from chunking.multi_language_chunker import MultiLanguageChunker
    from embeddings.document_composer import (
        EmbeddingDocumentComposer,
        EmbeddingDocumentPolicy,
    )
    from search.config import MODEL_REGISTRY, get_search_config

    root = str(Path(args.project_path).resolve())
    chunks = MultiLanguageChunker(root_path=root).chunk_directory(root)
    if args.only_indexed:
        keep = indexed_files(root)
        chunks = [
            c
            for c in chunks
            if os.path.relpath(c.file_path, root).replace("\\", "/") in keep
        ]
    print(f"[CHUNK] {len(chunks)} chunks from {root}", flush=True)

    composer = EmbeddingDocumentComposer()
    policy = EmbeddingDocumentPolicy.from_config(get_search_config())
    budgeted = [composer.compose(c, policy, max_chars=args.max_chars) for c in chunks]
    full = [composer.compose(c, policy, max_chars=UNBOUNDED) for c in chunks]
    chunk_types = [c.chunk_type or "?" for c in chunks]
    n_char_trunc = sum(len(b) < len(f) for b, f in zip(budgeted, full, strict=True))
    print(
        f"[COMPOSE] char budget {args.max_chars} truncates {n_char_trunc}/{len(chunks)}"
    )

    results: dict[str, Any] = {
        "project_path": root,
        "max_chars": args.max_chars,
        "n_chunks": len(chunks),
        "n_truncated_by_char_budget": n_char_trunc,
        "models": {},
    }
    for key in args.models:
        model_id = MODELS[key]
        max_context = MODEL_REGISTRY[model_id]["max_context"]
        print(f"[TOKENS] {key} ({model_id}, max_context={max_context})", flush=True)
        results["models"][key] = analyse_model(
            key, model_id, max_context, chunk_types, budgeted, full
        )

    print(f"\n=== {root} ({len(chunks)} chunks, {args.max_chars}-char budget) ===")
    print(
        f"{'model':<8}{'maxctx':>8}{'trunc':>7}{'fits':>7}{'over':>6}{'composedOver':>14}"
        f"{'ch/tok':>8}{'p50':>6}{'p90':>6}{'p99':>6}{'max':>7}"
    )
    for key, r in results["models"].items():
        t = r["tokens_composed"]
        print(
            f"{key:<8}{r['max_context']:>8}{r['n_truncated_by_char_budget']:>7}"
            f"{r['truncated_but_would_fit_max_context']:>7}"
            f"{r['truncated_and_exceeds_max_context']:>6}{r['composed_over_max_context']:>14}"
            f"{r['chars_per_token']:>8.2f}{t['p50']:>6.0f}{t['p90']:>6.0f}"
            f"{t['p99']:>6.0f}{t['max']:>7.0f}"
        )
    if args.json_out:
        probe_harness.write_probe_json(args.json_out, results)
    return 0


if __name__ == "__main__":
    os.environ.setdefault("CLAUDE_AUTO_REINDEX", "0")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    sys.exit(main())
