"""Tests for build_effective_config's singleton-mutation avoidance.

ADR-0031 deleted QW5 (_intent_ego_thresholds) and A1 (INTENT_EDGE_WEIGHT_PROFILES
consumption) — the two blocks that made every intent-on request pay for a
whole-SearchConfig deepcopy. This pins the resulting behavior: a plan carrying
only intent_decision (no ego, no parent) must now get the singleton back by
identity, not a copy.
"""

from search.config import SearchConfig
from search.effective_config import build_effective_config
from tests.fixtures.mcp_mocks import make_intent_decision_mock


def _make_plan(*, intent_decision, ego_graph_enabled=None, include_parent=False):
    from mcp_server.tools.search_orchestrator import SearchPlan

    return SearchPlan(
        query="find all callers of init",
        k=5,
        intent_decision=intent_decision,
        search_mode="hybrid",
        ego_graph_enabled=ego_graph_enabled,
        ego_graph_k_hops=2,
        ego_graph_max_neighbors=10,
        include_parent=include_parent,
        file_pattern=None,
        include_dirs=None,
        exclude_dirs=None,
        chunk_type=None,
        include_context=False,
        auto_reindex=False,
        max_age_minutes=5.0,
        max_context_tokens=0,
    )


def test_intent_only_plan_returns_singleton_by_identity():
    """An intent-on-only plan (no ego, no parent) must not trigger a deepcopy.

    Before ADR-0031, the A1 block always fired on this shape (every QueryIntent
    value is a key of the now-deleted INTENT_EDGE_WEIGHT_PROFILES), forcing a
    deepcopy on every intent-on request. Post-deletion, nothing in the
    is_hybrid region applies, so base_config must come back unchanged.

    ego_graph_enabled is None here (omitted), which is the tri-state gate's
    no-op case -- this is also the load-bearing regression test for that gate:
    if omitted ever regressed to coercing into False, this would start
    triggering a copy instead of returning base_config by identity.
    """
    base_config = SearchConfig()
    plan = _make_plan(intent_decision=make_intent_decision_mock("local"))

    result = build_effective_config(plan, base_config, is_hybrid=True)

    assert result is base_config


def test_intent_only_plan_returns_singleton_when_not_hybrid():
    base_config = SearchConfig()
    plan = _make_plan(intent_decision=make_intent_decision_mock("global"))

    result = build_effective_config(plan, base_config, is_hybrid=False)

    assert result is base_config


def test_ego_graph_enabled_still_triggers_copy():
    """Sanity check: the ego-graph override block is untouched by the deletion."""
    base_config = SearchConfig()
    plan = _make_plan(
        intent_decision=make_intent_decision_mock("local"),
        ego_graph_enabled=True,
    )

    result = build_effective_config(plan, base_config, is_hybrid=True)

    assert result is not base_config
    assert result.ego_graph.enabled is True


def test_ego_graph_explicit_false_disables_on_a_copy():
    """The two-way gate: an explicit False must override an on-by-default base
    config, on a copy, without touching k_hops/max_neighbors_per_hop.
    """
    base_config = SearchConfig()
    base_config.ego_graph.enabled = True
    plan = _make_plan(
        intent_decision=make_intent_decision_mock("local"),
        ego_graph_enabled=False,
    )

    result = build_effective_config(plan, base_config, is_hybrid=True)

    assert result is not base_config
    assert result.ego_graph.enabled is False
    assert base_config.ego_graph.enabled is True  # singleton untouched
    assert result.ego_graph.k_hops == base_config.ego_graph.k_hops
    assert (
        result.ego_graph.max_neighbors_per_hop
        == base_config.ego_graph.max_neighbors_per_hop
    )
