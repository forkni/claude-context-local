"""Unit tests for evaluation.arm_overrides (ADR-0018 Part 2 / C1).

Covers the seam that replaced run_sscg_benchmark.py's eleven
_apply_*_override() functions: dotted-key application (flat and
nested-by-section), validate_field_value-backed rejection of a bad arm, and
the construction_baked-derived rebuild decision.
"""

from __future__ import annotations

import pytest

from evaluation.arm_overrides import (
    ArmOverrideError,
    apply_overrides,
    merge_overrides,
    normalize_overrides,
    parse_set_flag,
    parse_set_flags,
    requires_rebuild,
    validate_overrides,
)
from search.config import SearchConfig


# ---------------------------------------------------------------------------
# normalize_overrides
# ---------------------------------------------------------------------------


def test_normalize_flat_dotted_key_passes_through():
    flat = normalize_overrides({"reranker.top_k_candidates": 50})
    assert flat == {"reranker.top_k_candidates": 50}


def test_normalize_nested_by_section_flattens():
    flat = normalize_overrides({"reranker": {"top_k_candidates": 50, "enabled": True}})
    assert flat == {
        "reranker.top_k_candidates": 50,
        "reranker.enabled": True,
    }


def test_normalize_mixed_shape_in_one_dict():
    flat = normalize_overrides(
        {
            "search_mode.bm25_weight": 0.4,
            "ego_graph": {"enabled": True, "community_bounded": False},
        }
    )
    assert flat == {
        "search_mode.bm25_weight": 0.4,
        "ego_graph.enabled": True,
        "ego_graph.community_bounded": False,
    }


def test_normalize_unknown_top_level_key_raises():
    with pytest.raises(ArmOverrideError, match="Unrecognized override key"):
        normalize_overrides({"not_a_section_or_dotted_key": 1})


def test_normalize_section_key_with_non_dict_value_raises():
    with pytest.raises(ArmOverrideError, match="must map to a dict"):
        normalize_overrides({"reranker": 50})


# ---------------------------------------------------------------------------
# merge_overrides
# ---------------------------------------------------------------------------


def test_merge_overrides_later_source_wins():
    merged = merge_overrides(
        {"reranker.top_k_candidates": 10},
        {"reranker.top_k_candidates": 20},
    )
    assert merged == {"reranker.top_k_candidates": 20}


def test_merge_overrides_preserves_sibling_fields_in_same_section():
    """_deep_merge's 'don't wipe the rest' guarantee, exercised through the
    seam: a later nested-section source touching only one field must not
    erase a sibling field an earlier source set in the same section."""
    merged = merge_overrides(
        {"ego_graph": {"enabled": True, "community_bounded": False}},
        {"ego_graph": {"cross_community_penalty": 0.2}},
    )
    assert merged == {
        "ego_graph": {
            "enabled": True,
            "community_bounded": False,
            "cross_community_penalty": 0.2,
        }
    }


# ---------------------------------------------------------------------------
# validate_overrides
# ---------------------------------------------------------------------------


def test_validate_overrides_accepts_in_range_value():
    validate_overrides({"search_mode.bm25_weight": 0.5})  # no raise


def test_validate_overrides_rejects_out_of_range_value():
    with pytest.raises(ArmOverrideError, match="Invalid bm25_weight"):
        validate_overrides({"search_mode.bm25_weight": 5.0})


def test_validate_overrides_rejects_bad_choice():
    with pytest.raises(ArmOverrideError, match="Invalid"):
        validate_overrides({"reranker.listwise_dtype": "int8"})


def test_validate_overrides_rejects_unknown_field():
    with pytest.raises(ArmOverrideError, match="Unknown field"):
        validate_overrides({"search_mode.not_a_real_field": 1})


def test_validate_overrides_rejects_unknown_section():
    with pytest.raises(ArmOverrideError, match="Unrecognized override key"):
        validate_overrides({"not_a_section.field": 1})


# ---------------------------------------------------------------------------
# requires_rebuild
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "search_mode.rrf_k_parameter",
        "reranker.doc_max_chars",
        "reranker.listwise_doc_max_chars",
        "reranker.listwise_dtype",
        # C3+C4 config-seam deepening (ADR-0030): these six are read once as
        # primitive kwargs into HybridSearcher/BM25Index at construction, but
        # were untagged before this fix - an arm overriding e.g. bm25_k1 would
        # silently measure the pre-override value (requires_rebuild() was
        # False). Red before the construction_baked=True tag was added.
        "search_mode.bm25_k1",
        "search_mode.bm25_b",
        "search_mode.bm25_use_stopwords",
        "search_mode.bm25_use_stemming",
        "search_mode.bm25_tokenizer",
        "performance.max_parallel_workers",
    ],
)
def test_requires_rebuild_true_for_construction_baked_fields(key):
    assert requires_rebuild({key: "anything"}) is True


@pytest.mark.parametrize(
    "key",
    [
        "reranker.top_k_candidates",
        "search_mode.bm25_reserved_slots",
        "multi_hop.expansion",
        "reranker.hop1_reserved_slots",
        # bm25_weight/dense_weight are resolved live per search() call
        # (hybrid_searcher.py:731-739), not baked into HybridSearcher at
        # construction - see Phase 2a, ADR-0018 follow-on.
        "search_mode.bm25_weight",
        "search_mode.dense_weight",
    ],
)
def test_requires_rebuild_false_for_live_fields(key):
    assert requires_rebuild({key: "anything"}) is False


def test_requires_rebuild_true_if_any_touched_field_is_baked():
    flat = {"reranker.top_k_candidates": 10, "search_mode.rrf_k_parameter": 150}
    assert requires_rebuild(flat) is True


def test_requires_rebuild_empty_is_false():
    assert requires_rebuild({}) is False


# ---------------------------------------------------------------------------
# apply_overrides
# ---------------------------------------------------------------------------


def test_apply_overrides_mutates_in_place_same_object():
    cfg = SearchConfig()
    search_mode_before = cfg.search_mode
    apply_overrides(cfg, {"search_mode.bm25_weight": 0.5})
    assert cfg.search_mode.bm25_weight == 0.5
    assert cfg.search_mode is search_mode_before  # same object identity


def test_apply_overrides_returns_rebuild_flag():
    cfg = SearchConfig()
    assert apply_overrides(cfg, {"search_mode.rrf_k_parameter": 100}) is True
    assert apply_overrides(cfg, {"reranker.top_k_candidates": 10}) is False
    # bm25_weight/dense_weight are live-read, not construction_baked.
    assert apply_overrides(cfg, {"search_mode.bm25_weight": 0.5}) is False


def test_apply_overrides_no_sources_is_a_noop():
    cfg = SearchConfig()
    original = cfg.search_mode.bm25_weight
    assert apply_overrides(cfg) is False
    assert cfg.search_mode.bm25_weight == original


def test_apply_overrides_merges_multiple_sources():
    cfg = SearchConfig()
    apply_overrides(
        cfg,
        {"search_mode.bm25_weight": 0.4},
        {"search_mode.dense_weight": 0.6},
    )
    assert cfg.search_mode.bm25_weight == 0.4
    assert cfg.search_mode.dense_weight == 0.6


def test_apply_overrides_raises_before_mutating_anything():
    """A validation failure on any key must not leave a partial mutation -
    matches the original functions' intent (a bad arm shouldn't half-apply)."""
    cfg = SearchConfig()
    original = cfg.search_mode.bm25_weight
    with pytest.raises(ArmOverrideError):
        apply_overrides(
            cfg,
            {"search_mode.bm25_weight": 0.5, "search_mode.dense_weight": 5.0},
        )
    assert cfg.search_mode.bm25_weight == original


# ---------------------------------------------------------------------------
# parse_set_flag / parse_set_flags
# ---------------------------------------------------------------------------


def test_parse_set_flag_coerces_int():
    key, value = parse_set_flag("search_mode.rrf_k_parameter=150")
    assert key == "search_mode.rrf_k_parameter"
    assert value == 150
    assert isinstance(value, int)


def test_parse_set_flag_coerces_float():
    key, value = parse_set_flag("search_mode.bm25_weight=0.4")
    assert value == pytest.approx(0.4)
    assert isinstance(value, float)


def test_parse_set_flag_coerces_bool():
    _, value = parse_set_flag("reranker.enabled=false")
    assert value is False
    _, value = parse_set_flag("reranker.enabled=true")
    assert value is True


def test_parse_set_flag_coerces_str():
    _, value = parse_set_flag("reranker.listwise_dtype=bf16")
    assert value == "bf16"


def test_parse_set_flag_rejects_missing_equals():
    with pytest.raises(ArmOverrideError, match="section.field=value"):
        parse_set_flag("search_mode.bm25_weight")


def test_parse_set_flag_rejects_unknown_field():
    with pytest.raises(ArmOverrideError, match="Unknown field"):
        parse_set_flag("search_mode.not_a_real_field=1")


def test_parse_set_flag_rejects_bad_int_literal():
    with pytest.raises(ArmOverrideError):
        parse_set_flag("search_mode.rrf_k_parameter=not-a-number")


def test_parse_set_flags_empty_input():
    assert parse_set_flags(None) == {}
    assert parse_set_flags([]) == {}


def test_parse_set_flags_last_duplicate_wins():
    flat = parse_set_flags(
        ["search_mode.bm25_weight=0.4", "search_mode.bm25_weight=0.6"]
    )
    assert flat == {"search_mode.bm25_weight": 0.6}


def test_parse_set_flags_feeds_apply_overrides_end_to_end():
    cfg = SearchConfig()
    flat = parse_set_flags(
        ["reranker.top_k_candidates=33", "search_mode.rrf_k_parameter=150"]
    )
    rebuild = apply_overrides(cfg, flat)
    assert cfg.reranker.top_k_candidates == 33
    assert cfg.search_mode.rrf_k_parameter == 150
    assert rebuild is True  # rrf_k_parameter is construction-baked
