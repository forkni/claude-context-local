"""Characterization tests for the GLSL edge-emission bridges in MultiLanguageChunker.

Plan (docs/plans -- Candidate 1, "Give tree-sitter languages a relationship-extraction
seam") Step 0: these tests pin the exact current behaviour of
`_extract_glsl_call_relationships` / `_extract_glsl_phase3_relationships`
(chunking/multi_language_chunker.py) *before* that logic moves into
`chunking/relationships/edge_specs.py`. They call the stable dispatcher methods
(`_extract_call_relationships` / `_extract_phase3_relationships`), which survive the
refactor unchanged -- only their internal GLSL branch is rewired -- so this file keeps
working as a regression gate through every step of the plan, not just as a one-time
snapshot of the pre-refactor code.

Four behaviours are pinned, one class each:

1. TestSplitBlockLineWindowFilter -- every split_block fragment of one large GLSL
   function shares identical tchunk.metadata (base.py's _create_split_chunk reruns
   extract_metadata against the *original, unsplit* node for every fragment); the
   per-fragment [start_line, end_line] filter is the only thing stopping every fragment
   from reporting the whole function's calls/relationships. This is the duplicated
   logic Step 1 (Extract Function) hoists into one predicate.
2. TestChunkImportsPopulation -- multi_language_chunker.py's switch 3 (:1035-1040),
   previously zero coverage anywhere in tests/unit/chunking/.
3. TestCallsVsRelationshipsNoneEmptyAsymmetry -- chunk.calls is always assigned once
   the calls bridge's gates pass (empty list included); chunk.relationships is
   assigned ONLY when non-empty, so a fully-filtered-out GLSL chunk leaves
   chunk.relationships untouched. CodeChunk.__post_init__ (python_ast_chunker.py)
   normalizes calls=None -> [] but has no equivalent branch for relationships.
4. TestCallsGateChecksIsNoneNotFalsiness -- the calls-bridge gate is
   `raw_calls is None`, not falsiness: an empty (but present) metadata["calls"] list
   still proceeds and assigns chunk.calls = [].
"""

from __future__ import annotations

import pytest

from chunking.languages.base import TreeSitterChunk
from chunking.python_ast_chunker import CodeChunk


@pytest.fixture
def chunker():
    try:
        from chunking.multi_language_chunker import MultiLanguageChunker

        return MultiLanguageChunker()
    except Exception:
        pytest.skip("MultiLanguageChunker unavailable (missing deps)")


def _glsl_tchunk(
    metadata: dict, start_line: int = 1, end_line: int = 100
) -> TreeSitterChunk:
    """A minimal GLSL TreeSitterChunk carrying the given metadata dict."""
    return TreeSitterChunk(
        content="// glsl fixture",
        start_line=start_line,
        end_line=end_line,
        node_type="function_definition",
        language="glsl",
        metadata=metadata,
    )


def _bare_chunk(chunk_type: str, start_line: int, end_line: int) -> CodeChunk:
    """A CodeChunk built via __new__ carrying only the fields the GLSL bridges read.

    Mirrors TestSplitBlockRelationshipExtraction's helper in
    test_large_node_splitting.py -- the bridges only read chunk_type/start_line/
    end_line and write chunk.calls / chunk.relationships, so the full constructor
    (which needs relative_path, folder_structure, etc.) is unnecessary overhead here.
    """
    chunk = CodeChunk.__new__(CodeChunk)
    chunk.chunk_type = chunk_type
    chunk.start_line = start_line
    chunk.end_line = end_line
    return chunk


class TestSplitBlockLineWindowFilter:
    """Pins the shared-metadata + per-fragment [start_line, end_line] filter."""

    def test_each_split_block_fragment_reports_only_its_own_calls(self, chunker):
        raw_calls = [("alpha", 5), ("beta", 15), ("gamma", 25)]
        tchunk = _glsl_tchunk({"calls": raw_calls})

        fragment_1 = _bare_chunk("split_block", start_line=1, end_line=10)
        chunker._extract_call_relationships(fragment_1, tchunk, "chunk:1")
        assert [c.callee_name for c in fragment_1.calls] == ["alpha"]

        fragment_2 = _bare_chunk("split_block", start_line=11, end_line=20)
        chunker._extract_call_relationships(fragment_2, tchunk, "chunk:2")
        assert [c.callee_name for c in fragment_2.calls] == ["beta"]

        fragment_3 = _bare_chunk("split_block", start_line=21, end_line=30)
        chunker._extract_call_relationships(fragment_3, tchunk, "chunk:3")
        assert [c.callee_name for c in fragment_3.calls] == ["gamma"]

    def test_call_line_window_is_inclusive_at_both_ends(self, chunker):
        tchunk = _glsl_tchunk(
            {
                "calls": [
                    ("at_start", 10),
                    ("at_end", 20),
                    ("just_before", 9),
                    ("just_after", 21),
                ]
            }
        )
        fragment = _bare_chunk("split_block", start_line=10, end_line=20)

        chunker._extract_call_relationships(fragment, tchunk, "chunk:1")

        assert {c.callee_name for c in fragment.calls} == {"at_start", "at_end"}

    def test_each_split_block_fragment_reports_only_its_own_relationships(
        self, chunker
    ):
        raw_relationships = [
            {"target_name": "A", "relationship_type": "uses_type", "line_number": 5},
            {"target_name": "B", "relationship_type": "uses_type", "line_number": 15},
            {"target_name": "C", "relationship_type": "uses_type", "line_number": 25},
        ]
        tchunk = _glsl_tchunk({"relationships": raw_relationships})

        fragment_1 = _bare_chunk("split_block", start_line=1, end_line=10)
        chunker._extract_phase3_relationships(fragment_1, tchunk, "chunk:1")
        assert [r.target_name for r in fragment_1.relationships] == ["A"]

        fragment_2 = _bare_chunk("split_block", start_line=11, end_line=20)
        chunker._extract_phase3_relationships(fragment_2, tchunk, "chunk:2")
        assert [r.target_name for r in fragment_2.relationships] == ["B"]

        fragment_3 = _bare_chunk("split_block", start_line=21, end_line=30)
        chunker._extract_phase3_relationships(fragment_3, tchunk, "chunk:3")
        assert [r.target_name for r in fragment_3.relationships] == ["C"]

    def test_relationship_line_window_is_inclusive_at_both_ends(self, chunker):
        tchunk = _glsl_tchunk(
            {
                "relationships": [
                    {
                        "target_name": "at_start",
                        "relationship_type": "uses_type",
                        "line_number": 10,
                    },
                    {
                        "target_name": "at_end",
                        "relationship_type": "uses_type",
                        "line_number": 20,
                    },
                    {
                        "target_name": "just_before",
                        "relationship_type": "uses_type",
                        "line_number": 9,
                    },
                    {
                        "target_name": "just_after",
                        "relationship_type": "uses_type",
                        "line_number": 21,
                    },
                ]
            }
        )
        fragment = _bare_chunk("function", start_line=10, end_line=20)

        chunker._extract_phase3_relationships(fragment, tchunk, "chunk:1")

        assert {r.target_name for r in fragment.relationships} == {
            "at_start",
            "at_end",
        }


class TestChunkImportsPopulation:
    """Pins multi_language_chunker.py's switch 3 -- the only place any tree-sitter
    chunk's `.imports` gets populated, gated on the chunk carrying an IMPORTS
    relationship. Reached only through _convert_tree_chunks / chunk_file, since it
    lives in the caller, not in either bridge method -- so this goes through the real
    MultiLanguageChunker().chunk_file() path, mirroring test_glsl_relationships.py."""

    _FIXTURE_SOURCE = (
        '#include "common.glslinc"\n\nvoid main() {\n    vec3 color = vec3(1.0);\n}\n'
    )

    @pytest.fixture
    def glsl_chunks(self, tmp_path):
        try:
            from chunking.multi_language_chunker import MultiLanguageChunker
        except Exception:
            pytest.skip("MultiLanguageChunker unavailable (missing deps)")

        file_path = tmp_path / "imports_fixture.glsl"
        file_path.write_text(self._FIXTURE_SOURCE, encoding="utf-8")

        glsl_chunker = MultiLanguageChunker(root_path=str(tmp_path))
        chunks = glsl_chunker.chunk_file(str(file_path))
        return {c.name: c for c in chunks}

    def test_include_chunk_populates_imports_from_relationships(self, glsl_chunks):
        include_chunk = glsl_chunks["common.glslinc"]
        assert include_chunk.imports == ["common.glslinc"]

    def test_non_import_chunk_leaves_imports_empty(self, glsl_chunks):
        main_chunk = glsl_chunks["main"]
        assert main_chunk.imports == []


class TestCallsVsRelationshipsNoneEmptyAsymmetry:
    """Pins the highest-risk behaviour: CodeChunk.__post_init__ normalizes
    calls=None -> [] but has no equivalent branch for relationships. The calls
    bridge assigns unconditionally once its gates pass (empty list included); the
    relationships bridge assigns ONLY when non-empty. Nothing distinguishes these
    today -- a "cleanup" that regularized it would change persisted chunk metadata
    with no red test anywhere, which is exactly what these tests prevent."""

    def test_fresh_codechunk_relationships_defaults_to_none_while_calls_defaults_to_list(
        self,
    ):
        chunk = CodeChunk(
            content="void main() {}",
            chunk_type="function",
            start_line=1,
            end_line=1,
            file_path="shader.glsl",
            relative_path="shader.glsl",
            folder_structure=[],
        )
        assert chunk.calls == []
        assert chunk.relationships is None

    def test_calls_assigned_empty_list_when_all_filtered_out(self, chunker):
        """Every call falls outside [start_line, end_line] -> chunk.calls == [];
        never None."""
        tchunk = _glsl_tchunk({"calls": [("outside", 999)]})
        fragment = _bare_chunk("split_block", start_line=1, end_line=10)

        chunker._extract_call_relationships(fragment, tchunk, "chunk:1")

        assert fragment.calls == []

    def test_relationships_left_unassigned_when_all_filtered_out(self, chunker):
        """Every relationship falls outside [start_line, end_line] -> chunk.relationships
        is never assigned at all (stays whatever it was before the call) -- unlike
        chunk.calls, which is always (re)assigned once the bridge's gates pass."""
        tchunk = _glsl_tchunk(
            {
                "relationships": [
                    {
                        "target_name": "Foo",
                        "relationship_type": "uses_type",
                        "line_number": 999,
                    }
                ]
            }
        )
        fragment = _bare_chunk("function", start_line=1, end_line=10)
        fragment.relationships = "sentinel"  # proves assign-only-when-non-empty

        chunker._extract_phase3_relationships(fragment, tchunk, "chunk:1")

        assert fragment.relationships == "sentinel"

    def test_relationships_left_unassigned_for_empty_raw_relationships(self, chunker):
        """raw_relationships == [] is falsy -> early return, chunk.relationships
        untouched (unlike the calls bridge's `is None` gate -- see
        TestCallsGateChecksIsNoneNotFalsiness)."""
        tchunk = _glsl_tchunk({"relationships": []})
        fragment = _bare_chunk("function", start_line=1, end_line=10)
        fragment.relationships = "sentinel"

        chunker._extract_phase3_relationships(fragment, tchunk, "chunk:1")

        assert fragment.relationships == "sentinel"


class TestCallsGateChecksIsNoneNotFalsiness:
    """Pins the `raw_calls is None` gate (not a falsiness check): an empty (but
    present) metadata["calls"] list still proceeds through the gate and assigns
    chunk.calls = [], while an absent "calls" key (raw_calls is None) skips the
    assignment entirely, leaving chunk.calls untouched."""

    def test_empty_raw_calls_list_proceeds_and_assigns_empty_list(self, chunker):
        tchunk = _glsl_tchunk({"calls": []})
        fragment = _bare_chunk("function", start_line=1, end_line=10)

        chunker._extract_call_relationships(fragment, tchunk, "chunk:1")

        assert fragment.calls == []

    def test_missing_calls_key_skips_assignment_entirely(self, chunker):
        tchunk = _glsl_tchunk({})  # no "calls" key -> .get("calls") is None
        fragment = _bare_chunk("function", start_line=1, end_line=10)

        chunker._extract_call_relationships(fragment, tchunk, "chunk:1")

        # chunk.calls was never assigned by the bridge -- CodeChunk's slots have no
        # class-level default, so reading it now raises rather than returning None.
        with pytest.raises(AttributeError):
            _ = fragment.calls
