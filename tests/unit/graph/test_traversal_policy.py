"""Unit tests for TraversalPolicy (graph traversal parameter object)."""

import dataclasses

import pytest

from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
from graph.traversal_policy import DEFAULT_RELATION_TYPES, TraversalPolicy
from search.config import EgoGraphConfig, GraphEnhancedConfig


class TestDefaults:
    def test_bare_policy_is_all_no_ops(self):
        policy = TraversalPolicy()

        assert policy.relation_types is None
        assert policy.max_depth == 1
        assert policy.exclude_import_categories is None
        assert policy.edge_weights is None
        assert policy.min_confidence == 0.0
        assert policy.confidence_weighting is False
        assert policy.drop_ambiguous is False

    def test_effective_relation_types_defaults_to_calls_both_ways(self):
        assert TraversalPolicy().effective_relation_types == list(
            DEFAULT_RELATION_TYPES
        )
        assert DEFAULT_RELATION_TYPES == ("calls", "called_by")

    def test_effective_relation_types_keeps_explicit_list(self):
        policy = TraversalPolicy(relation_types=["imports"])

        assert policy.effective_relation_types == ["imports"]

    def test_effective_relation_types_keeps_explicit_empty_list(self):
        """An explicit [] follows nothing; it is not the same as None."""
        assert TraversalPolicy(relation_types=[]).effective_relation_types == []

    def test_policy_is_frozen(self):
        policy = TraversalPolicy()

        with pytest.raises(dataclasses.FrozenInstanceError):
            policy.max_depth = 3  # type: ignore[misc]


class TestAdmits:
    @pytest.mark.parametrize(
        ("policy", "ambiguous", "confidence", "expected"),
        [
            # All gates off: everything survives.
            (TraversalPolicy(), False, 0.5, True),
            (TraversalPolicy(), True, 0.5, True),
            (TraversalPolicy(), False, 0.0, True),
            # Confidence floor only.
            (TraversalPolicy(min_confidence=0.65), False, 0.5, False),
            (TraversalPolicy(min_confidence=0.65), False, 0.65, True),
            (TraversalPolicy(min_confidence=0.65), False, 0.98, True),
            (TraversalPolicy(min_confidence=0.65), True, 0.98, True),
            # Ambiguity drop only: independent of confidence.
            (TraversalPolicy(drop_ambiguous=True), True, 0.98, False),
            (TraversalPolicy(drop_ambiguous=True), False, 0.0, True),
            # Both gates: either one can drop the edge.
            (
                TraversalPolicy(min_confidence=0.65, drop_ambiguous=True),
                True,
                0.9,
                False,
            ),
            (
                TraversalPolicy(min_confidence=0.65, drop_ambiguous=True),
                False,
                0.5,
                False,
            ),
            (
                TraversalPolicy(min_confidence=0.65, drop_ambiguous=True),
                False,
                0.7,
                True,
            ),
        ],
    )
    def test_admits_truth_table(self, policy, ambiguous, confidence, expected):
        assert policy.admits(ambiguous=ambiguous, confidence=confidence) is expected

    def test_zero_floor_admits_zero_confidence(self):
        """min_confidence=0.0 is a true no-op (0.0 < 0.0 is False)."""
        assert TraversalPolicy(min_confidence=0.0).admits(
            ambiguous=False, confidence=0.0
        )


class TestGraphHop:
    def test_no_config_is_one_weighted_hop_with_default_weights(self):
        policy = TraversalPolicy.graph_hop()

        assert policy.max_depth == 1
        assert policy.edge_weights == DEFAULT_EDGE_WEIGHTS
        assert policy.relation_types is None
        assert policy.exclude_import_categories is None
        assert policy.min_confidence == 0.0
        assert policy.confidence_weighting is False
        assert policy.drop_ambiguous is False

    def test_explicit_none_config_matches_omitted(self):
        assert TraversalPolicy.graph_hop(None) == TraversalPolicy.graph_hop()

    def test_custom_edge_weights_override_default(self):
        custom = {"calls": 0.5, "imports": 1.0}

        assert TraversalPolicy.graph_hop(edge_weights=custom).edge_weights == custom

    def test_reads_the_three_gates_off_graph_enhanced(self):
        ge = GraphEnhancedConfig(
            min_traversal_confidence=0.65,
            traversal_confidence_weighting_enabled=True,
            drop_ambiguous_traversal_edges=True,
        )

        policy = TraversalPolicy.graph_hop(ge)

        assert policy.min_confidence == 0.65
        assert policy.confidence_weighting is True
        assert policy.drop_ambiguous is True

    def test_default_graph_enhanced_matches_no_config(self):
        """A stock GraphEnhancedConfig carries no-op gates, so the policy is
        byte-identical to the no-config path."""
        assert TraversalPolicy.graph_hop(GraphEnhancedConfig()) == (
            TraversalPolicy.graph_hop()
        )


class TestEgo:
    def test_reads_depth_relations_and_weights_off_ego_config(self):
        cfg = EgoGraphConfig(
            k_hops=3, relation_types=["calls", "imports"], edge_weights=None
        )

        policy = TraversalPolicy.ego(cfg)

        assert policy.max_depth == 3
        assert policy.relation_types == ["calls", "imports"]
        assert policy.edge_weights is None

    def test_default_ego_config_uses_default_edge_weights(self):
        assert TraversalPolicy.ego(EgoGraphConfig()).edge_weights == (
            DEFAULT_EDGE_WEIGHTS
        )

    @pytest.mark.parametrize(
        ("stdlib", "third_party", "expected"),
        [
            (True, True, ["stdlib", "builtin", "third_party"]),
            (True, False, ["stdlib", "builtin"]),
            (False, True, ["third_party"]),
            (False, False, None),
        ],
    )
    def test_exclude_categories_derived_from_ego_flags(
        self, stdlib, third_party, expected
    ):
        cfg = EgoGraphConfig(
            exclude_stdlib_imports=stdlib, exclude_third_party_imports=third_party
        )

        assert TraversalPolicy.ego(cfg).exclude_import_categories == expected

    def test_no_graph_enhanced_leaves_gates_at_no_op(self):
        policy = TraversalPolicy.ego(EgoGraphConfig())

        assert policy.min_confidence == 0.0
        assert policy.confidence_weighting is False
        assert policy.drop_ambiguous is False

    def test_reads_the_three_gates_off_graph_enhanced(self):
        ge = GraphEnhancedConfig(
            min_traversal_confidence=0.8,
            traversal_confidence_weighting_enabled=True,
            drop_ambiguous_traversal_edges=True,
        )

        policy = TraversalPolicy.ego(EgoGraphConfig(), ge)

        assert policy.min_confidence == 0.8
        assert policy.confidence_weighting is True
        assert policy.drop_ambiguous is True
