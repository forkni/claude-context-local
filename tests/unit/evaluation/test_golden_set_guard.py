"""Golden-set drift guard.

`evaluation/callee_golden.json` and `evaluation/caller_golden.json` hand-curate
`target_chunk_id` / `expected_callees` / `expected_callers` (and, for callee
entries, `known_false_positives`) as literal chunk_id strings. Nothing keeps
those strings in sync with the source they describe — Step 1's investigation
found three entries (OB01, OB03, OB06) that had silently drifted after
`run_resolvers` grew past the chunk-split threshold, and the harness scored
them 0.0 without ever surfacing that the IDs themselves were stale.

`evaluation/golden_dataset.json` (77 queries, categories A-F) and
`evaluation/golden_dataset_expanded.json` (its superset with additional
queries) hand-curate the same kind of literal chunk_id strings in `expected` /
`expected_primary` / `relevance_grades` (plus `anchor_chunk_id` for category
F), and are exposed to the same drift risk. Together they reference several
hundred distinct chunk_ids, so `_live_normalized_ids` is memoized per source
file to keep the parametrized sweep CI-cheap.

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
    """Return (source_label, chunk_id) pairs for every chunk_id in a golden_dataset*.json file.

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
def _get_chunker() -> MultiLanguageChunker:
    """Lazily construct the shared chunker on first use.

    Previously a module-level `_CHUNKER = MultiLanguageChunker(...)` ran at
    import time as a side effect of collecting this file (Phase 13.2.b).
    `@cache` keeps it a true singleton -- one construction, reused by every
    `_live_normalized_ids` call -- while deferring that construction until a
    test actually needs it.
    """
    return MultiLanguageChunker(str(REPO_ROOT))


@cache
def _live_normalized_ids(file_path: str) -> frozenset[str]:
    """Fresh-chunk *file_path* (repo-relative) and return its normalized chunk_ids.

    Memoized per file path: the 77-query golden_dataset.json alone references
    ~240 distinct chunk_ids drawn from ~70 files, so without caching this would
    re-chunk the same file hundreds of times across the parametrized sweep.
    """
    abs_path = REPO_ROOT / file_path
    chunks = _get_chunker().chunk_file(str(abs_path))
    ids: set[str] = set()
    for c in chunks:
        if not c.chunk_id:
            continue
        ids.add(normalize_chunk_id(c.chunk_id))
        ids.update(_split_aliases(c.chunk_id))
    return frozenset(ids)


# Kinds whose oversized nodes the indexer may split into `split_block`
# fragments (chunking/languages/base.py, `node.type in ("function_definition",
# "decorated_definition")`), and the kind those fragments normalize to
# (search/chunk_id.py:dedup_key collapses `split_block` -> `method`).
_SPLIT_ELIGIBLE_KINDS = frozenset({"function", "decorated_definition", "method"})
_SPLIT_NORMALIZED_KIND = "method"


@cache
def _max_chunk_lines() -> int:
    """The line count above which the indexer considers a node for splitting."""
    from search.config import get_chunking_config

    config = get_chunking_config()
    return int(config.max_chunk_lines) if config is not None else 100


def _split_aliases(raw_chunk_id: str) -> set[str]:
    """Return the id form(s) a split-eligible chunk takes once the indexer splits it.

    Under `sizing_mode == "adaptive"` the indexer's split threshold is a
    repo-wide P75 character baseline that only exists at index time; this
    guard chunks each file alone and therefore always uses the static
    `max_split_chars`. A function longer than `max_chunk_lines` can thus
    come back unsplit here (one `decorated_definition`/`function` chunk)
    while the live index holds several `split_block` fragments that
    `normalize_chunk_id` collapses to `<file>:method:<name>` -- which is the
    form goldens must store to score against the index (Q12
    `handle_get_index_status`, 2026-09-02). Accept that alias for exactly the
    chunks the indexer could split: eligible kind AND over the line threshold.
    """
    parts = raw_chunk_id.split(":")
    if len(parts) != 4:
        return set()
    file_path, line_range, kind, name = parts
    if kind not in _SPLIT_ELIGIBLE_KINDS:
        return set()
    try:
        start, end = (int(x) for x in line_range.split("-"))
    except ValueError:
        return set()
    if end - start + 1 <= _max_chunk_lines():
        return set()
    return {f"{file_path}:{_SPLIT_NORMALIZED_KIND}:{name}"}


GOLDEN_FILES = [
    EVALUATION_DIR / "callee_golden.json",
    EVALUATION_DIR / "caller_golden.json",
]

GOLDEN_DATASET_FILES = [
    EVALUATION_DIR / "golden_dataset.json",
    EVALUATION_DIR / "golden_dataset_expanded.json",
]


ALL_GOLDEN_FILES = GOLDEN_FILES + GOLDEN_DATASET_FILES

# Computed once at collection time (Phase 13.2.b). Previously this same work
# (re-reading all 4 JSON files from disk) ran twice — once for @parametrize's
# argvalues, once for its ids= — and expanded to ~2,218 collected cases,
# ~39% of the entire unit tier, from what is really 2 def test_* functions.
# Grouping by golden file collapses that to 4 cases with identical protection:
# every drifted ID is still collected and reported, just as one aggregate
# assertion per file instead of one case per ID.
_CASES_BY_FILE: dict[Path, list[tuple[str, str]]] = {
    golden_path: _golden_ids(golden_path) for golden_path in GOLDEN_FILES
} | {
    dataset_path: _golden_dataset_ids(dataset_path)
    for dataset_path in GOLDEN_DATASET_FILES
}


@pytest.mark.parametrize(
    "golden_path", ALL_GOLDEN_FILES, ids=[p.name for p in ALL_GOLDEN_FILES]
)
def test_golden_chunk_ids_exist_in_live_index(golden_path):
    """Every golden chunk_id in *golden_path* must be producible by re-chunking
    its source file today.

    A failure here means the golden set has drifted (renamed/moved/resplit
    symbol) and needs repair — same failure mode as OB01/OB03/OB06.
    """
    drifted = []
    for source_label, chunk_id in _CASES_BY_FILE[golden_path]:
        file_path = chunk_id.split(":", 1)[0]
        live_ids = _live_normalized_ids(file_path)
        if chunk_id not in live_ids:
            drifted.append((source_label, chunk_id, file_path))

    assert not drifted, (
        f"{golden_path.name} has {len(drifted)} drifted chunk_id(s) that no "
        "longer exist among the chunks freshly produced from their source "
        "file(s). The golden set has drifted -- repair the ID(s) (see Step "
        "1.3):\n"
        + "\n".join(
            f"  [{label}] {chunk_id!r} (from {file_path})"
            for label, chunk_id, file_path in drifted
        )
    )


def test_guard_detects_corrupted_id():
    """Sanity check: the guard must fail loudly on a deliberately wrong ID.

    Proves test_golden_chunk_ids_exist_in_live_index is not vacuously true.
    """
    corrupted = "chunking/relationships/call_edge_resolver.py:function:this_symbol_does_not_exist"
    file_path = corrupted.split(":", 1)[0]
    live_ids = _live_normalized_ids(file_path)
    assert corrupted not in live_ids


@pytest.mark.parametrize(
    ("raw_chunk_id", "expected"),
    [
        # 105-line decorated def: the adaptive indexer may split it -> method alias.
        (
            "mcp_server/tools/status_handlers.py:31-135:decorated_definition:handle_get_index_status",
            {"mcp_server/tools/status_handlers.py:method:handle_get_index_status"},
        ),
        # Module-level function over the threshold: same alias.
        ("pkg/mod.py:1-140:function:big", {"pkg/mod.py:method:big"}),
        # Exactly at the threshold is NOT split-eligible (indexer uses strict >).
        ("pkg/mod.py:1-100:function:edge", set()),
        # Short node: no alias.
        ("pkg/mod.py:1-20:decorated_definition:small", set()),
        # Classes are never split by the indexer.
        ("pkg/mod.py:1-400:class:Big", set()),
        # Malformed / already-normalized ids produce nothing.
        ("pkg/mod.py:function:no_range", set()),
    ],
)
def test_split_alias_matches_indexer_eligibility(raw_chunk_id, expected):
    """`_split_aliases` mirrors base.py's split gate: eligible kind AND > max_chunk_lines."""
    assert _max_chunk_lines() == 100, "test table assumes the shipped max_chunk_lines"
    assert _split_aliases(raw_chunk_id) == expected
