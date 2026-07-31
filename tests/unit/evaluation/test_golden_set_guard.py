"""Golden-set drift guard.

`evaluation/callee_golden.json` and `evaluation/caller_golden.json` hand-curate
`target_chunk_id` / `expected_callees` / `expected_callers` (and, for callee
entries, `known_false_positives`) as literal chunk_id strings. Nothing keeps
those strings in sync with the source they describe — Step 1's investigation
found three entries (OB01, OB03, OB06) that had silently drifted after
`run_resolvers` grew past the chunk-split threshold, and the harness scored
them 0.0 without ever surfacing that the IDs themselves were stale.

`evaluation/golden_dataset.json` (77 queries, categories A-F) hand-curates the
same kind of literal chunk_id strings in `expected` / `expected_primary` /
`relevance_grades` (plus `anchor_chunk_id` for category F), and is exposed to
the same drift risk. It references ~240 distinct chunk_ids, so
`_live_normalized_ids` is memoized per source file to keep the parametrized
sweep CI-cheap.

This test re-chunks (fresh, no live index or MCP server required) every
source file referenced by a golden ID and asserts each golden ID is still
producible today. It is intentionally cheap and dependency-light so it can
run in the normal `pytest tests/unit/` sweep.
"""

import json
from functools import cache
from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from evaluation.metrics import normalize_chunk_id


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = REPO_ROOT / "evaluation"
_CHUNKER = MultiLanguageChunker(str(REPO_ROOT))


def _golden_ids(golden_path: Path) -> list[tuple[str, str]]:
    """Return (source_label, chunk_id) pairs for every chunk_id referenced.

    Covers `target_chunk_id`, every `expected_callees`/`expected_callers`
    entry, and every `known_false_positives[].chunk_id` entry.
    """
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for query in data["queries"]:
        qid = query["id"]
        pairs.append((f"{qid}.target_chunk_id", query["target_chunk_id"]))
        for expected in query.get("expected_callees", []):
            pairs.append((f"{qid}.expected_callees", expected))
        for expected in query.get("expected_callers", []):
            pairs.append((f"{qid}.expected_callers", expected))
        for fp in query.get("known_false_positives", []):
            pairs.append((f"{qid}.known_false_positives", fp["chunk_id"]))
    return pairs


def _golden_dataset_ids(golden_path: Path) -> list[tuple[str, str]]:
    """Return (source_label, chunk_id) pairs for every chunk_id in golden_dataset.json.

    Covers `expected`, `expected_primary`, every `relevance_grades` key, and
    (category F only) `anchor_chunk_id`.
    """
    data = json.loads(golden_path.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    for query in data["queries"]:
        qid = query["id"]
        for chunk_id in query.get("expected", []):
            pairs.append((f"{qid}.expected", chunk_id))
        for chunk_id in query.get("expected_primary", []):
            pairs.append((f"{qid}.expected_primary", chunk_id))
        for chunk_id in query.get("relevance_grades", {}):
            pairs.append((f"{qid}.relevance_grades", chunk_id))
        if "anchor_chunk_id" in query:
            pairs.append((f"{qid}.anchor_chunk_id", query["anchor_chunk_id"]))
    return pairs


@cache
def _live_normalized_ids(file_path: str) -> frozenset[str]:
    """Fresh-chunk *file_path* (repo-relative) and return its normalized chunk_ids.

    Memoized per file path: the 77-query golden_dataset.json alone references
    ~240 distinct chunk_ids drawn from ~70 files, so without caching this would
    re-chunk the same file hundreds of times across the parametrized sweep.
    """
    abs_path = REPO_ROOT / file_path
    chunks = _CHUNKER.chunk_file(str(abs_path))
    return frozenset(normalize_chunk_id(c.chunk_id) for c in chunks if c.chunk_id)


GOLDEN_FILES = [
    EVALUATION_DIR / "callee_golden.json",
    EVALUATION_DIR / "caller_golden.json",
]

GOLDEN_DATASET_FILE = EVALUATION_DIR / "golden_dataset.json"


def _all_golden_id_cases() -> list[tuple[str, str, str]]:
    """(golden_file_name, source_label, chunk_id) for every referenced ID."""
    cases = []
    for golden_path in GOLDEN_FILES:
        for label, chunk_id in _golden_ids(golden_path):
            cases.append((golden_path.name, label, chunk_id))
    for label, chunk_id in _golden_dataset_ids(GOLDEN_DATASET_FILE):
        cases.append((GOLDEN_DATASET_FILE.name, label, chunk_id))
    return cases


@pytest.mark.parametrize(
    "golden_file, source_label, chunk_id",
    _all_golden_id_cases(),
    ids=[f"{f}::{label}::{c}" for f, label, c in _all_golden_id_cases()],
)
def test_golden_chunk_id_exists_in_live_index(golden_file, source_label, chunk_id):
    """Every golden chunk_id must be producible by re-chunking its source file today.

    A failure here means the golden set has drifted (renamed/moved/resplit
    symbol) and needs repair — same failure mode as OB01/OB03/OB06.
    """
    file_path = chunk_id.split(":", 1)[0]
    live_ids = _live_normalized_ids(file_path)
    assert chunk_id in live_ids, (
        f"{golden_file} [{source_label}] references {chunk_id!r}, which no "
        f"longer exists among the chunks freshly produced from {file_path}. "
        "The golden set has drifted -- repair the ID (see Step 1.3)."
    )


def test_guard_detects_corrupted_id():
    """Sanity check: the guard must fail loudly on a deliberately wrong ID.

    Proves test_golden_chunk_id_exists_in_live_index is not vacuously true.
    """
    corrupted = "chunking/relationships/call_edge_resolver.py:function:this_symbol_does_not_exist"
    file_path = corrupted.split(":", 1)[0]
    live_ids = _live_normalized_ids(file_path)
    assert corrupted not in live_ids
