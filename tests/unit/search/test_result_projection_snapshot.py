"""Snapshot tests for RelationshipAnalyzer's three result -> display dict
adapters: _result_to_dict, _extract_result_info, _extract_symbol_info
(search/relationship_analyzer.py:938-1015).

Gate 0 for the C2 architecture-review target (unify these three near-clone
projections): pins their current, divergent behaviour BEFORE any refactor,
so a later unification step is provably byte-identical (Commit 1) or has an
explicit, reviewed diff (Commit 2 -- normalize_path uniformity).

Plain pytest module, not unittest.TestCase -- the `snapshot` fixture is not
injected into TestCase methods (this repo's own precedent,
tests/unit/mcp_server/test_search_results_snapshot.py, is plain pytest for
the same reason). The non-snapshot branch/axis assertions for these same
three adapters live in tests/unit/search/test_relationship_analyzer.py's
TestResultProjectionCharacterization; this file holds only the
snapshot-shaped centerpiece.

Run ``pytest --snapshot-update tests/unit/search/test_result_projection_snapshot.py``
once to generate JSON snapshots, then commit the ``__snapshots__/`` dir.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from search.relationship_analyzer import RelationshipAnalyzer


@pytest.fixture
def snapshot(snapshot):
    """Use diffable JSON serialisation instead of the default amber format."""
    return snapshot.use_extension(JSONSnapshotExtension)


def _bare_analyzer() -> RelationshipAnalyzer:
    """A RelationshipAnalyzer with no wired collaborators -- these three
    adapters are pure functions of (result, chunk_id) and touch no other
    instance state.
    """
    return RelationshipAnalyzer.__new__(RelationshipAnalyzer)


@dataclass
class _MetadataResult:
    """Object-with-metadata branch: hasattr(result, "metadata") is True."""

    metadata: dict[str, Any]
    score: float = 0.0


class TestResultProjectionSnapshot:
    def test_dict_input_passthrough(self, snapshot):
        """dict branch: only _result_to_dict has this branch at all; the
        other two adapters never see dict input in production.
        """
        analyzer = _bare_analyzer()
        payload = {"file": "search\\module.py", "kind": "function"}
        assert (
            analyzer._result_to_dict(payload, "search/module.py:1-2:function:f")
            == snapshot
        )

    def test_all_three_disagree_on_the_same_metadata_input(self, snapshot):
        """The centerpiece: one input, three different output shapes.

        Since Commit 2 (normalize_path uniformity), all three agree on the
        `file` string; they still disagree on key sets (score
        present/absent, name present/absent) -- that axis is untouched.
        """
        analyzer = _bare_analyzer()
        result = _MetadataResult(
            metadata={
                "file": "search\\relationship_analyzer.py",
                "start_line": 100,
                "end_line": 200,
                "chunk_type": "method",
            },
            score=0.6,
        )
        assert {
            "_result_to_dict": analyzer._result_to_dict(result, "cid"),
            "_extract_result_info": analyzer._extract_result_info(result, "cid"),
            "_extract_symbol_info": analyzer._extract_symbol_info(
                result, "pkg/mod.py:method:Foo.bar", "bar"
            ),
        } == snapshot

    def test_falsy_and_missing_file_across_all_three(self, snapshot):
        """The `file=None` axis: three different outcomes for the same
        input -- _result_to_dict's metadata branch coerces to "", the two
        non-normalizing siblings pass None straight through untouched, and
        (separately, see test_relationship_analyzer.py) the dict branch
        would raise instead of coercing. This snapshot captures the two
        non-raising outcomes side by side.
        """
        analyzer = _bare_analyzer()
        result = _MetadataResult(
            metadata={"file": None, "start_line": 1, "end_line": 2}
        )
        assert {
            "_result_to_dict": analyzer._result_to_dict(result, "cid"),
            "_extract_result_info": analyzer._extract_result_info(result, "cid"),
            "_extract_symbol_info": analyzer._extract_symbol_info(
                result, "pkg/mod.py:x", None
            ),
        } == snapshot
