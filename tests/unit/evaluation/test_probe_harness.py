"""Unit tests for evaluation.probe_harness (Step 3 of the probe-harness seam).

Covers the pieces every scripts/benchmark/probe_*.py migration (Step 5)
depends on: golden-query loading with the exclude/require-grades filters
that reproduce each original load_queries's exact behavior, the
override-apply/restore round trip open_probe wraps around a probe run, and
replay_legs/instrument reusing search.search_executor's leg_search_depth /
fused_pool_cut rather than a re-derived literal -- the drift
docs/adr/0040-probe-harness-seam.md and the module docstring describe.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from evaluation.probe_harness import (
    GoldenQuery,
    LegCapture,
    ProbeSession,
    _restore_config,
    _snapshot_and_apply,
    load_golden_queries,
    probe_parser,
    resolve_dataset_path,
    write_probe_json,
)
from search.config import SearchConfig
from search.rerank_window_policy import RerankWindowPolicy


# ---------------------------------------------------------------------------
# load_golden_queries
# ---------------------------------------------------------------------------


@pytest.fixture
def dataset_path(tmp_path):
    import json

    data = {
        "queries": [
            {
                "id": "Q1",
                "query": "how does auth work",
                "category": "A",
                "relevance_grades": {"auth.py:function:login": 3},
            },
            {
                "id": "Q2",
                "query": "no grades here",
                "category": "B",
                "relevance_grades": {},
            },
            {
                "id": "Q3",
                "query": "category D excluded by default",
                "category": "D",
                "relevance_grades": {"d.py:function:d": 2},
            },
            {
                "id": "F1",
                "query": "similar to this chunk",
                "category": "F",
                "relevance_grades": {"sim.py:function:sim": 3},
                "anchor_chunk_id": "chunking/languages/python.py:method:PythonChunker.__init__",
            },
        ]
    }
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_golden_queries_excludes_category_d_by_default(dataset_path):
    queries = load_golden_queries(dataset_path)
    ids = {q.id for q in queries}
    assert "Q3" not in ids
    assert ids == {"Q1", "F1"}  # Q2 also dropped: require_grades=True default


def test_load_golden_queries_require_grades_false_keeps_ungraded(dataset_path):
    queries = load_golden_queries(dataset_path, require_grades=False)
    ids = {q.id for q in queries}
    assert "Q2" in ids


def test_load_golden_queries_exclude_categories_empty_keeps_category_d(dataset_path):
    queries = load_golden_queries(dataset_path, exclude_categories=())
    ids = {q.id for q in queries}
    assert "Q3" in ids


def test_load_golden_queries_normalizes_grade_keys(dataset_path):
    queries = load_golden_queries(dataset_path)
    q1 = next(q for q in queries if q.id == "Q1")
    # normalize_chunk_id strips any line-range suffix / split_block tag --
    # a plain chunk id with no such suffix passes through unchanged.
    assert q1.grades == {"auth.py:function:login": 3}


def test_load_golden_queries_carries_anchor_chunk_id(dataset_path):
    queries = load_golden_queries(dataset_path, exclude_categories=())
    f1 = next(q for q in queries if q.id == "F1")
    assert (
        f1.anchor_chunk_id
        == "chunking/languages/python.py:method:PythonChunker.__init__"
    )


def test_load_golden_queries_anchor_chunk_id_none_when_absent(dataset_path):
    queries = load_golden_queries(dataset_path)
    q1 = next(q for q in queries if q.id == "Q1")
    assert q1.anchor_chunk_id is None


def test_load_golden_queries_by_id_selects_and_preserves_order(dataset_path):
    queries = load_golden_queries(
        dataset_path, query_ids=["F1", "Q1"], exclude_categories=()
    )
    assert [q.id for q in queries] == ["F1", "Q1"]


def test_load_golden_queries_by_id_missing_raises_key_error(dataset_path):
    with pytest.raises(KeyError, match=r"\['NOPE'\]"):
        load_golden_queries(dataset_path, query_ids=["Q1", "NOPE"])


def test_load_golden_queries_by_id_raises_for_excluded_query(dataset_path):
    """Selecting a category-D id without also opening exclude_categories
    raises -- matches every original load_queries's "not found (or
    category-D)" contract rather than silently returning it anyway."""
    with pytest.raises(KeyError, match=r"\['Q3'\]"):
        load_golden_queries(dataset_path, query_ids=["Q3"])


# ---------------------------------------------------------------------------
# probe_parser / resolve_dataset_path
# ---------------------------------------------------------------------------


def test_probe_parser_defaults():
    parser = probe_parser("test probe")
    args = parser.parse_args([])
    assert args.dataset == "evaluation/golden_dataset_expanded.json"
    assert args.project_path == "."
    assert args.k == 10
    assert args.query_ids is None
    assert args.json_out is None
    assert args.set_overrides is None


def test_probe_parser_set_is_repeatable():
    parser = probe_parser("test probe")
    args = parser.parse_args(
        [
            "--set",
            "search_mode.bm25_weight=0.4",
            "--set",
            "reranker.top_k_candidates=20",
        ]
    )
    assert args.set_overrides == [
        "search_mode.bm25_weight=0.4",
        "reranker.top_k_candidates=20",
    ]


def test_probe_parser_composes_as_parent():
    """A concrete probe adds its own flags via parents=[probe_parser(...)] --
    add_help=False on the parent is required for this to not conflict."""
    import argparse

    child = argparse.ArgumentParser(
        description="child probe", parents=[probe_parser("parent")]
    )
    child.add_argument("--probe-depth", type=int, default=200)
    args = child.parse_args(["--probe-depth", "50"])
    assert args.probe_depth == 50
    assert args.k == 10  # inherited default


def test_resolve_dataset_path_relative_resolves_against_repo_root():
    resolved = resolve_dataset_path("evaluation/golden_dataset_expanded.json")
    assert resolved.is_absolute()
    assert resolved.name == "golden_dataset_expanded.json"


def test_resolve_dataset_path_absolute_passes_through(tmp_path):
    absolute = tmp_path / "custom.json"
    assert resolve_dataset_path(absolute) == absolute


# ---------------------------------------------------------------------------
# write_probe_json
# ---------------------------------------------------------------------------


def test_write_probe_json_round_trips(tmp_path, capsys):
    import json

    out = tmp_path / "out.json"
    write_probe_json(out, {"a": 1, "b": [1, 2, 3]})
    assert json.loads(out.read_text(encoding="utf-8")) == {"a": 1, "b": [1, 2, 3]}
    assert "JSON written to" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _snapshot_and_apply / _restore_config
# ---------------------------------------------------------------------------


def test_snapshot_and_apply_mutates_and_reports_rebuild():
    cfg = SearchConfig()
    original = cfg.search_mode.rrf_k_parameter
    snapshot, rebuild = _snapshot_and_apply(cfg, {"search_mode.rrf_k_parameter": 150})
    assert cfg.search_mode.rrf_k_parameter == 150
    assert rebuild is True
    assert snapshot == {("search_mode", "rrf_k_parameter"): original}


def test_snapshot_and_apply_empty_overrides_is_a_noop():
    cfg = SearchConfig()
    snapshot, rebuild = _snapshot_and_apply(cfg, {})
    assert snapshot == {}
    assert rebuild is False


def test_snapshot_and_apply_live_field_reports_no_rebuild():
    cfg = SearchConfig()
    _, rebuild = _snapshot_and_apply(cfg, {"search_mode.bm25_weight": 0.5})
    assert rebuild is False


def test_restore_config_undoes_snapshot_and_apply():
    cfg = SearchConfig()
    original = cfg.search_mode.bm25_weight
    snapshot, _ = _snapshot_and_apply(cfg, {"search_mode.bm25_weight": 0.9})
    assert cfg.search_mode.bm25_weight == 0.9
    _restore_config(cfg, snapshot)
    assert cfg.search_mode.bm25_weight == original


def test_snapshot_and_apply_raises_before_mutating_on_bad_override():
    """A validation failure must not leave a partial mutation -- mirrors
    arm_overrides.apply_overrides's own no-partial-application guarantee,
    which this helper builds directly on."""
    from evaluation.arm_overrides import ArmOverrideError

    cfg = SearchConfig()
    original = cfg.search_mode.bm25_weight
    with pytest.raises(ArmOverrideError):
        _snapshot_and_apply(
            cfg, {"search_mode.bm25_weight": 0.5, "search_mode.dense_weight": 5.0}
        )
    assert cfg.search_mode.bm25_weight == original


# ---------------------------------------------------------------------------
# LegCapture
# ---------------------------------------------------------------------------


def test_leg_capture_rank_of_found_and_missing():
    capture = LegCapture(
        bm25=["a", "b", "c"],
        dense=["c", "a"],
        fused=["a", "b"],
        search_k=30,
        cut=10,
        raw_bm25=[],
        raw_dense=[],
        raw_fused=[],
    )
    assert capture.rank_of("b") == 2  # default leg="fused"
    assert capture.rank_of("c", leg="dense") == 1
    assert capture.rank_of("nope") is None


# ---------------------------------------------------------------------------
# ProbeSession.replay_legs -- must call search.search_executor's helpers,
# never re-derive the funnel width inline (the drift this module fixes).
# ---------------------------------------------------------------------------


def _fake_searcher_for_replay(bm25_results, dense_results, fused_results):
    executor = MagicMock()
    executor.search_bm25.return_value = bm25_results
    executor.search_dense.return_value = dense_results
    executor.reranker.rerank_simple.return_value = fused_results
    return SimpleNamespace(search_executor=executor)


def test_replay_legs_uses_leg_search_depth_and_fused_pool_cut():
    cfg = SearchConfig()
    cfg.reranker.top_k_candidates = 30
    cfg.search_mode.leg_search_multiplier = 5
    searcher = _fake_searcher_for_replay(
        bm25_results=[("a.py:function:a", 1.0, {})],
        dense_results=[("b.py:function:b", 0.9, {})],
        fused_results=[SimpleNamespace(chunk_id="a.py:function:a")],
    )
    session = ProbeSession(searcher=searcher, config=cfg, k=10)

    capture = session.replay_legs("some query")

    from search.search_executor import fused_pool_cut, leg_search_depth

    expected_search_k = leg_search_depth(cfg, 10)
    expected_cut = fused_pool_cut(cfg, 10)
    executor = searcher.search_executor
    executor.search_bm25.assert_called_once_with(
        "some query", expected_search_k, cfg.search_mode.min_bm25_score, None
    )
    executor.search_dense.assert_called_once_with(
        "some query", expected_search_k, None, None
    )
    assert capture.search_k == expected_search_k
    assert capture.cut == expected_cut
    assert capture.bm25 == ["a.py:function:a"]
    assert capture.dense == ["b.py:function:b"]
    assert capture.fused == ["a.py:function:a"]


def test_replay_legs_leg_search_multiplier_changes_search_k():
    """The drift-closed check: two configs differing only in
    leg_search_multiplier must produce different replayed search_k, unlike
    a probe that hardcoded k * 5 inline (frozen regardless of the knob)."""
    searcher = _fake_searcher_for_replay([], [], [])

    cfg_mult_1 = SearchConfig()
    cfg_mult_1.reranker.top_k_candidates = 5  # below k*multiplier for both
    cfg_mult_1.search_mode.leg_search_multiplier = 1
    session_1 = ProbeSession(searcher=searcher, config=cfg_mult_1, k=10)
    capture_1 = session_1.replay_legs("q")

    cfg_mult_5 = SearchConfig()
    cfg_mult_5.reranker.top_k_candidates = 5
    cfg_mult_5.search_mode.leg_search_multiplier = 5
    session_5 = ProbeSession(searcher=searcher, config=cfg_mult_5, k=10)
    capture_5 = session_5.replay_legs("q")

    assert capture_1.search_k != capture_5.search_k
    assert capture_1.search_k == 10  # k * 1
    assert capture_5.search_k == 50  # k * 5


def test_replay_legs_depth_override_bypasses_derived_width():
    searcher = _fake_searcher_for_replay([], [], [])
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)

    capture = session.replay_legs("q", depth=200)

    assert capture.search_k == 200
    searcher.search_executor.search_bm25.assert_called_once_with(
        "q", 200, cfg.search_mode.min_bm25_score, None
    )


def test_replay_legs_k_override_takes_precedence_over_session_k():
    searcher = _fake_searcher_for_replay([], [], [])
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)

    from search.search_executor import leg_search_depth

    capture = session.replay_legs("q", k=4)

    assert capture.search_k == leg_search_depth(cfg, 4)


# ---------------------------------------------------------------------------
# ProbeSession.instrument
# ---------------------------------------------------------------------------


def _fake_searcher_for_instrument():
    engine = SimpleNamespace(last_window_ids=["w1", "w2"])

    def orig_run(query_or_content, candidates, k, log_prefix, config=None):
        return list(candidates[:k])

    def orig_rbq(*, candidates=(), k=0, window=None, **kwargs):
        # Real RerankingEngine.rerank_by_query delegates to _run_rerank
        # internally -- looked up via `engine.` at call time so instrument()'s
        # _run_rerank patch is visible to it, exactly like the production path.
        return engine._run_rerank("query", list(candidates), k, "log_prefix")

    engine.rerank_by_query = orig_rbq
    engine._run_rerank = orig_run
    return SimpleNamespace(reranking_engine=engine), orig_run, orig_rbq


def test_instrument_captures_run_rerank_calls():
    searcher, _, _ = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)
    candidate = SimpleNamespace(chunk_id="a.py:function:a", source="graph_hop")

    with session.instrument() as calls:
        result = searcher.reranking_engine._run_rerank(
            "query", [candidate], 1, "log_prefix"
        )

    assert result == [candidate]
    assert len(calls) == 1
    record = calls[0]
    assert record["k"] == 1
    assert record["pool_ids"] == ["a.py:function:a"]
    assert record["pool_sources"] == [("a.py:function:a", "graph_hop")]
    assert record["window_ids"] == ["w1", "w2"]
    assert record["output_ids"] == ["a.py:function:a"]


def test_instrument_captures_hop1_reserved_slots_via_rerank_by_query():
    searcher, _, _ = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)
    candidate = SimpleNamespace(chunk_id="a.py:function:a", source=None)

    with session.instrument() as calls:
        searcher.reranking_engine.rerank_by_query(
            candidates=[candidate],
            k=1,
            window=RerankWindowPolicy(hop1_reserved_slots=6),
        )

    assert calls[0]["hop1_slots"] == 6
    assert calls[0]["is_merged_pass"] is True


def test_instrument_classifies_merged_pass_with_zero_hop1_slots_as_merged():
    """D3 pin: a Pass-2 (merged-pool) call with hop1_reserved_slots explicitly
    set to 0 must still classify as a merged pass. The old classifier sniffed
    hop1_slots > 0, which silently misread this as a tail pass -- the bug
    the is_merged_pass discriminator (`"window" in kwargs`) exists to fix."""
    searcher, _, _ = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)
    candidate = SimpleNamespace(chunk_id="a.py:function:a", source=None)

    with session.instrument() as calls:
        searcher.reranking_engine.rerank_by_query(
            candidates=[candidate],
            k=1,
            window=RerankWindowPolicy(hop1_reserved_slots=0),
        )

    assert calls[0]["hop1_slots"] == 0
    assert calls[0]["is_merged_pass"] is True


def test_instrument_classifies_call_without_window_kwarg_as_not_merged():
    """The other side of the discriminator: a tail-pass call that never
    passes window= at all (production's ego/parent call shape) must not be
    classified as merged, regardless of the sentinel's own hop1_slots."""
    searcher, _, _ = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)
    candidate = SimpleNamespace(chunk_id="a.py:function:a", source=None)

    with session.instrument() as calls:
        searcher.reranking_engine.rerank_by_query(candidates=[candidate], k=1)

    assert calls[0]["is_merged_pass"] is False


def test_instrument_restores_original_methods_on_exit():
    searcher, orig_run, orig_rbq = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)

    with session.instrument():
        assert searcher.reranking_engine._run_rerank is not orig_run

    assert searcher.reranking_engine._run_rerank is orig_run
    assert searcher.reranking_engine.rerank_by_query is orig_rbq


def test_instrument_restores_original_methods_even_if_body_raises():
    searcher, orig_run, orig_rbq = _fake_searcher_for_instrument()
    cfg = SearchConfig()
    session = ProbeSession(searcher=searcher, config=cfg, k=10)

    with pytest.raises(RuntimeError), session.instrument():
        raise RuntimeError("boom")

    assert searcher.reranking_engine._run_rerank is orig_run
    assert searcher.reranking_engine.rerank_by_query is orig_rbq


# ---------------------------------------------------------------------------
# GoldenQuery is a plain frozen data carrier
# ---------------------------------------------------------------------------


def test_golden_query_is_frozen():
    import dataclasses

    query = GoldenQuery(id="Q1", query="q", category="A", grades={})
    with pytest.raises(dataclasses.FrozenInstanceError):
        query.id = "Q2"
