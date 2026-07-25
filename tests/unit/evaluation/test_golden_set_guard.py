"""Golden-set drift guard.

`evaluation/callee_golden.json` and `evaluation/caller_golden.json` hand-curate
`target_chunk_id` / `expected_callees` / `expected_callers` (and, for callee
entries, `known_false_positives`) as literal chunk_id strings. Nothing keeps
those strings in sync with the source they describe — Step 1's investigation
found three entries (OB01, OB03, OB06) that had silently drifted after
`run_resolvers` grew past the chunk-split threshold, and the harness scored
them 0.0 without ever surfacing that the IDs themselves were stale.

This test re-chunks (fresh, no live index or MCP server required) every
source file referenced by a golden ID and asserts each golden ID is still
producible today. It is intentionally cheap and dependency-light so it can
run in the normal `pytest tests/unit/` sweep.
"""

import json
from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from evaluation.metrics import normalize_chunk_id


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = REPO_ROOT / "evaluation"


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


def _live_normalized_ids(file_path: str) -> set[str]:
    """Fresh-chunk *file_path* (repo-relative) and return its normalized chunk_ids."""
    abs_path = REPO_ROOT / file_path
    chunker = MultiLanguageChunker(str(REPO_ROOT))
    chunks = chunker.chunk_file(str(abs_path))
    return {normalize_chunk_id(c.chunk_id) for c in chunks if c.chunk_id}


GOLDEN_FILES = [
    EVALUATION_DIR / "callee_golden.json",
    EVALUATION_DIR / "caller_golden.json",
]


def _all_golden_id_cases() -> list[tuple[str, str, str]]:
    """(golden_file_name, source_label, chunk_id) for every referenced ID."""
    cases = []
    for golden_path in GOLDEN_FILES:
        for label, chunk_id in _golden_ids(golden_path):
            cases.append((golden_path.name, label, chunk_id))
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
