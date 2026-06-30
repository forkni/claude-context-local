"""Byte-parity snapshot tests for all 9 leaf LanguageChunker implementations.

Each parametrized case serializes ``[c.to_dict() for c in chunks]`` for a
small feature-exercising fixture and pins the result with Syrupy JSON
snapshots.  These snapshots are captured on the **current** (post-Phase-A)
code and serve as the hard gate for Phase B: the refactored code must produce
byte-identical output with **no** ``--snapshot-update``.

Capturing golden baseline (run once, then commit the __snapshots__ dir):

    uv run pytest tests/unit/chunking/test_chunker_parity.py --snapshot-update -q

Verifying parity after refactor:

    uv run pytest tests/unit/chunking/test_chunker_parity.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from chunking.tree_sitter import TreeSitterChunker


# ---------------------------------------------------------------------------
# Fixtures directory
# ---------------------------------------------------------------------------

CORPUS_DIR = Path(__file__).parent.parent.parent / "fixtures" / "chunker_corpus"

# Extension → fixture filename (one per leaf chunker).
# .tsx is intentionally omitted — it uses the same TypeScriptChunker logic as
# .ts; adding it would duplicate coverage without adding signal.
CORPUS_EXTENSIONS = [
    ".py",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".cs",
    ".glsl",
]


# ---------------------------------------------------------------------------
# Snapshot extension override
# ---------------------------------------------------------------------------


@pytest.fixture
def snapshot(snapshot):
    """Use diffable JSON serialisation instead of the default amber format."""
    return snapshot.use_extension(JSONSnapshotExtension)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_fixture(ext: str) -> str:
    path = CORPUS_DIR / f"sample{ext}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ext", CORPUS_EXTENSIONS, ids=lambda e: e.lstrip("."))
def test_chunker_metadata_parity(ext: str, snapshot) -> None:
    """Chunk a fixture file and assert the result matches the golden snapshot.

    The snapshot pins *all* fields returned by ``TreeSitterChunk.to_dict()``:
    ``content``, ``start_line``, ``end_line``, ``type``, ``language``, and
    ``metadata``.  The ``metadata`` dict is what Phase B changes — if any leaf
    refactor alters its output this test will fail without ``--snapshot-update``.
    """
    src = _load_fixture(ext)
    ts = TreeSitterChunker()

    # Skip gracefully if the tree-sitter grammar isn't installed in this env
    chunker = ts.get_chunker(f"sample{ext}")
    if chunker is None:
        pytest.skip(f"No tree-sitter grammar available for {ext!r} — install first")

    chunks = ts.chunk_file(f"sample{ext}", content=src)
    result = [c.to_dict() for c in chunks]

    # Must produce at least one chunk; an empty list usually means a parse
    # error or a fixture that exercises no splittable node types.
    assert result, f"chunk_file returned no chunks for {ext!r} — check fixture content"

    assert result == snapshot
