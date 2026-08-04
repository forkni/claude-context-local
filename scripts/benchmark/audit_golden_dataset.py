#!/usr/bin/env python
"""Audit golden-dataset chunk IDs against the live index (read-only).

Every golden ID (``expected``, ``expected_primary``, ``relevance_grades``) is
normalized with :func:`evaluation.metrics.normalize_chunk_id` and checked for
membership in the normalized live-index ID set. Unresolvable golds silently cap
recall (the denominator counts them but no retrieved chunk can ever match), so
this audit should be re-run after any refactor or chunker change that reshapes
the index — it exists to keep the dataset from drifting silently again.

Note on ``split_block`` golds: ``dedup_key`` rewrites ``split_block`` → the
parent-kind (``method``/``function``) only for 4-part IDs carrying a line
range. Live index IDs always carry line ranges, golden IDs never do — so a
3-part golden ``split_block:X`` can never match, even when the live index
still chunks that symbol as a split_block. Store golds in parent-kind form.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/audit_golden_dataset.py \
        [--dataset evaluation/golden_dataset.json ...] [--metadata-db PATH]

Exit code 0 when every gold resolves in every dataset, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import normalize_chunk_id  # noqa: E402
from search.metadata import MetadataStore  # noqa: E402


DEFAULT_DATASETS = [
    "evaluation/golden_dataset.json",
    "evaluation/golden_dataset_expanded.json",
]


def locate_metadata_db(project_root: Path, model_name: str) -> Path | None:
    """Find the live index metadata.db for this project + embedding model."""
    import os

    storage_root = Path(
        os.environ.get("CODE_SEARCH_STORAGE", Path.home() / ".claude_code_search")
    )
    projects_dir = storage_root / "projects"
    if not projects_dir.exists():
        return None
    slug = model_name.split("/")[-1].lower()
    candidates = sorted(
        d
        for d in projects_dir.iterdir()
        if d.is_dir() and d.name.startswith(f"{project_root.name}_") and slug in d.name
    )
    if not candidates:
        return None
    db = candidates[-1] / "index" / "metadata.db"
    return db if db.exists() else None


def gold_ids(query: dict) -> set[str]:
    """All golden chunk IDs referenced by a query entry (incl. F-anchor)."""
    ids: set[str] = set(query.get("expected", []))
    ids.update(query.get("expected_primary", []))
    ids.update((query.get("relevance_grades") or {}).keys())
    anchor = query.get("anchor_chunk_id")
    if anchor:
        ids.add(anchor)
    return ids


def audit_dataset(dataset_path: Path, index_ids: set[str], raw_ids: list[str]) -> int:
    """Report unresolvable golds for one dataset file; return their count."""
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    queries = data["queries"]
    stale_total = 0
    stale_queries = 0
    for query in queries:
        missing = sorted(
            gid for gid in gold_ids(query) if normalize_chunk_id(gid) not in index_ids
        )
        if not missing:
            continue
        stale_queries += 1
        stale_total += len(missing)
        grades = query.get("relevance_grades") or {}
        print(f"  {query['id']} [{query.get('category', '?')}] {query['query'][:70]}")
        for gid in missing:
            primary = " PRIMARY" if gid in query.get("expected_primary", []) else ""
            anchor = " ANCHOR" if gid == query.get("anchor_chunk_id") else ""
            print(f"    STALE grade={grades.get(gid)}{primary}{anchor}  {gid}")
            for candidate in suggest_candidates(gid, raw_ids):
                print(f"      -> candidate: {candidate}")
    status = (
        "CLEAN"
        if stale_total == 0
        else f"{stale_total} stale golds in {stale_queries} queries"
    )
    print(f"{dataset_path}: {len(queries)} queries — {status}")
    return stale_total


def suggest_candidates(stale_id: str, raw_ids: list[str], limit: int = 4) -> list[str]:
    """Same-file, same-trailing-symbol live chunks (normalized) as retarget hints."""
    file_part = stale_id.split(":")[0]
    symbol = stale_id.split(":")[-1].split(".")[-1]
    candidates = {
        normalize_chunk_id(rid)
        for rid in raw_ids
        if rid.split(":")[0].replace("\\", "/") == file_part
        and rid.split(":")[-1].split(".")[-1] == symbol
    }
    return sorted(candidates)[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dataset",
        action="append",
        help=f"Dataset JSON to audit (repeatable; default: {DEFAULT_DATASETS})",
    )
    parser.add_argument("--project", default=".", help="Project root (default: .)")
    parser.add_argument(
        "--metadata-db",
        help="Explicit path to the live index metadata.db (overrides auto-detect)",
    )
    args = parser.parse_args()

    project_root = Path(args.project).resolve()
    if args.metadata_db:
        db_path = Path(args.metadata_db)
    else:
        config = json.loads(
            (project_root / "search_config.json").read_text(encoding="utf-8")
        )
        model_name = config["embedding"]["model_name"]
        db_path = locate_metadata_db(project_root, model_name)
    if db_path is None or not db_path.exists():
        print(f"ERROR: metadata.db not found (looked via {project_root})")
        return 2

    store = MetadataStore(db_path)
    raw_ids = [chunk_id for chunk_id, _ in store.items()]
    index_ids = {normalize_chunk_id(chunk_id) for chunk_id in raw_ids}
    print(f"Live index: {db_path}")
    print(f"  {len(raw_ids)} chunks, {len(index_ids)} normalized IDs\n")

    datasets = args.dataset or DEFAULT_DATASETS
    total_stale = 0
    for dataset in datasets:
        dataset_path = project_root / dataset
        if not dataset_path.exists():
            print(f"ERROR: dataset not found: {dataset_path}")
            return 2
        total_stale += audit_dataset(dataset_path, index_ids, raw_ids)
        print()

    return 0 if total_stale == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
