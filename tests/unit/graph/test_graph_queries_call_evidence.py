"""Tests for GraphQueryEngine.score_call_evidence (A1 call-evidence scoring).

The score is query-conditioned: lambda * log2(1 + number of distinct
reference ids the candidate shares a calls-edge with, either direction).
Non-calls edges never count, and any degenerate input returns 0.0.
"""

import math

import pytest

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage


CANDIDATE = "src/mod.py:10-20:function:candidate"
REF_CALLEE = "src/mod.py:30-40:function:ref_callee"
REF_CALLER = "src/other.py:5-15:function:ref_caller"
UNRELATED = "src/other.py:50-60:function:unrelated"
IMPORT_ONLY = "src/imports.py:1-5:function:import_target"


@pytest.fixture
def storage(tmp_path):
    """Real CodeGraphStorage with a small call graph around CANDIDATE."""
    storage = CodeGraphStorage(project_id="test_call_evidence", storage_dir=tmp_path)
    # candidate calls REF_CALLEE; REF_CALLER calls candidate
    storage.add_call_edge(CANDIDATE, REF_CALLEE, line_number=12)
    storage.add_call_edge(REF_CALLER, CANDIDATE, line_number=7)
    # A non-calls parallel edge to IMPORT_ONLY must never count as evidence
    storage.graph.add_edge(CANDIDATE, IMPORT_ONLY, key="imports", type="imports")
    # UNRELATED exists in the graph but has no edge to candidate
    storage.graph.add_node(UNRELATED)
    return storage


@pytest.fixture
def engine(storage):
    return GraphQueryEngine(storage)


class TestScoreCallEvidence:
    def test_single_shared_reference(self, engine):
        """One call link to the reference set -> lambda * log2(2) == lambda."""
        score = engine.score_call_evidence(
            CANDIDATE, frozenset({REF_CALLEE}), lambda_weight=0.05
        )
        assert score == pytest.approx(0.05)

    def test_counts_both_directions(self, engine):
        """Caller and callee links both count as distinct shared references."""
        score = engine.score_call_evidence(
            CANDIDATE, frozenset({REF_CALLEE, REF_CALLER}), lambda_weight=0.05
        )
        assert score == pytest.approx(0.05 * math.log2(3))

    def test_no_shared_reference_returns_zero(self, engine):
        score = engine.score_call_evidence(
            CANDIDATE, frozenset({UNRELATED}), lambda_weight=0.05
        )
        assert score == 0.0

    def test_non_calls_edge_never_counts(self, engine):
        """An imports-keyed edge to a reference id contributes no evidence."""
        score = engine.score_call_evidence(
            CANDIDATE, frozenset({IMPORT_ONLY}), lambda_weight=0.05
        )
        assert score == 0.0

    def test_chunk_not_in_graph_returns_zero(self, engine):
        score = engine.score_call_evidence(
            "src/ghost.py:1-2:function:ghost",
            frozenset({REF_CALLEE}),
            lambda_weight=0.05,
        )
        assert score == 0.0

    def test_empty_reference_set_returns_zero(self, engine):
        assert engine.score_call_evidence(CANDIDATE, frozenset(), 0.05) == 0.0

    def test_zero_lambda_returns_zero(self, engine):
        assert (
            engine.score_call_evidence(CANDIDATE, frozenset({REF_CALLEE}), 0.0) == 0.0
        )

    def test_accepts_plain_set(self, engine):
        """reference_ids may be a plain set, not only a frozenset."""
        score = engine.score_call_evidence(CANDIDATE, {REF_CALLEE}, lambda_weight=0.1)
        assert score == pytest.approx(0.1)
