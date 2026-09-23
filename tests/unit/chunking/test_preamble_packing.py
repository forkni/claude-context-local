"""Unit tests for size-bounded packing of oversized `module_preamble` runs (Card B).

`_collect_module_preamble_chunks` (base.py) emits every root-level statement run
not covered by function/class chunking as one verbatim chunk, with no size check
-- unlike the function-split path. `split_oversized_preamble` (default off) packs
an oversized run into size-bounded pieces at sibling boundaries via `_pack_by_size`,
the same packer `_split_large_node` uses.
"""

import pytest

from chunking.languages.base import estimate_characters
from chunking.languages.c import CChunker
from chunking.languages.python import PythonChunker
from chunking.multi_language_chunker import MultiLanguageChunker
from search.config import ChunkingConfig


# Matches the Card B plan's worked example: static (non-adaptive) character
# packing, gated the same way the function-split path is gated.
PACK_CONFIG = ChunkingConfig(
    enable_large_node_splitting=True,
    split_oversized_preamble=True,
    max_chunk_lines=50,
    split_size_method="characters",
    max_split_chars=400,
    sizing_mode="fixed",
)


def _prose_marker_source(num_pairs: int) -> str:
    """Build a preamble run of alternating prose paragraphs and marker
    assignments.

    Em-dash-heavy prose collapses into a single ERROR node under the Python
    grammar once tree-sitter enters error recovery -- even interspersed
    comments get swallowed into the same ERROR production. A valid
    assignment statement between paragraphs acts as a circuit breaker,
    terminating error recovery and giving the run multiple distinct
    root-level siblings, which is what `_pack_by_size` needs to cut between.
    """
    blocks = []
    for i in range(num_pairs):
        blocks.append(
            f"This is paragraph {i} of the UI building guide -- it explains step {i} "
            f"in detail, covering the rationale -- and how it connects to the "
            f"previous step's output -- across several design decisions."
        )
        blocks.append(f"_marker_{i} = {i}")
    return "\n\n".join(blocks) + "\n"


@pytest.fixture
def chunker():
    try:
        return PythonChunker()
    except ValueError:
        pytest.skip("tree-sitter-python not installed")


class TestPreamblePackingGate:
    """The knob and its enable_large_node_splitting dependency."""

    def test_knob_off_stays_one_chunk(self, chunker):
        code = _prose_marker_source(40)
        chunks = chunker.chunk_code(
            code, config=ChunkingConfig(split_oversized_preamble=False)
        )
        preamble = [c for c in chunks if c.node_type == "module_preamble"]
        assert len(preamble) == 1

    def test_knob_on_short_run_stays_one_chunk(self, chunker):
        code = _prose_marker_source(5)  # well under max_chunk_lines
        chunks = chunker.chunk_code(code, config=PACK_CONFIG)
        preamble = [c for c in chunks if c.node_type == "module_preamble"]
        assert len(preamble) == 1

    def test_enable_large_node_splitting_off_overrides_knob(self, chunker):
        code = _prose_marker_source(40)
        config = ChunkingConfig(
            enable_large_node_splitting=False,
            split_oversized_preamble=True,
            max_chunk_lines=50,
            split_size_method="characters",
            max_split_chars=400,
            sizing_mode="fixed",
        )
        chunks = chunker.chunk_code(code, config=config)
        preamble = [c for c in chunks if c.node_type == "module_preamble"]
        assert len(preamble) == 1


class TestPreamblePackingSplitsOversizedRun:
    def test_long_error_prose_run_packs_into_multiple_pieces(self, chunker):
        code = _prose_marker_source(40)
        chunks = chunker.chunk_code(code, config=PACK_CONFIG)
        preamble = [c for c in chunks if c.node_type == "module_preamble"]

        assert len(preamble) > 1

        for a, b in zip(preamble, preamble[1:], strict=False):
            assert a.end_line < b.start_line

        total = sum(estimate_characters(c.content) for c in preamble)
        assert total == estimate_characters(code)

        for c in preamble:
            assert estimate_characters(c.content) < 400


class TestPreamblePackingLimitations:
    def test_single_giant_node_stays_one_chunk(self, chunker):
        """A single unsplittable node (one dict literal, no sibling
        boundaries) cannot be packed -- sibling-only packing is a known,
        deliberate limitation (Card B plan: splitting inside a giant single
        node is out of scope, deferred)."""
        entries = "\n".join(f'    "key_{i}": {i},' for i in range(150))
        code = f"DATA = {{\n{entries}\n}}\n"
        chunks = chunker.chunk_code(code, config=PACK_CONFIG)
        preamble = [c for c in chunks if c.node_type == "module_preamble"]
        assert len(preamble) == 1


class TestPreamblePackingCommentAttachment:
    def test_leading_comment_stays_with_next_statement(self, chunker):
        lines = [
            "_filler_0 = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'",
            "# leading comment directly above next stmt",
            "_marker_1 = 1",
        ]
        lines.extend(f"_marker_{i} = {i}" for i in range(2, 60))
        code = "\n".join(lines) + "\n"
        config = ChunkingConfig(
            enable_large_node_splitting=True,
            split_oversized_preamble=True,
            max_chunk_lines=10,
            split_size_method="characters",
            max_split_chars=60,
            sizing_mode="fixed",
        )
        chunks = chunker.chunk_code(code, config=config)
        preamble = [c for c in chunks if c.node_type == "module_preamble"]

        assert len(preamble) > 1
        owner = next(c for c in preamble if "leading comment" in c.content)
        assert "_marker_1 = 1" in owner.content


class TestPreamblePackingCrossLanguage:
    def test_c_oversized_preamble_packs(self):
        """The collector (`_collect_module_preamble_chunks`) and its helpers
        are defined only in base.py, never overridden per-language -- unlike
        `_split_large_node`, which is gated by `_get_block_boundary_types()`
        (unsupported for C). Preamble packing therefore works identically
        for every language."""
        try:
            chunker = CChunker()
        except ValueError:
            pytest.skip("tree-sitter-c not installed")

        lines = [f"#define MACRO_{i} ({i} * 2)" for i in range(60)]
        lines.append("")
        lines.append("int main(void) { return 0; }")
        code = "\n".join(lines) + "\n"

        chunks_off = chunker.chunk_code(
            code, config=ChunkingConfig(split_oversized_preamble=False)
        )
        preamble_off = [c for c in chunks_off if c.node_type == "module_preamble"]
        assert len(preamble_off) == 1

        chunks_on = chunker.chunk_code(code, config=PACK_CONFIG)
        preamble_on = [c for c in chunks_on if c.node_type == "module_preamble"]
        assert len(preamble_on) > 1

        # No macro definition is duplicated across pieces.
        seen = []
        for c in preamble_on:
            for i in range(60):
                if f"MACRO_{i} " in c.content:
                    seen.append(i)
        assert len(seen) == len(set(seen))


class TestPreamblePackingChunkIds:
    def test_chunk_ids_unique_through_multi_language_chunker(
        self, tmp_path, monkeypatch
    ):
        import search.config as sc

        cfg = PACK_CONFIG
        monkeypatch.setattr(sc, "get_chunking_config", lambda: cfg)

        source_path = tmp_path / "oversized_preamble.py"
        source_path.write_text(_prose_marker_source(40), encoding="utf-8")

        mc = MultiLanguageChunker(root_path=str(tmp_path))
        chunks = mc.chunk_file(str(source_path))
        preamble = [c for c in chunks if c.chunk_type == "module_preamble"]

        assert len(preamble) > 1
        ids = [c.chunk_id for c in preamble]
        assert all(ids)
        assert len(ids) == len(set(ids))
