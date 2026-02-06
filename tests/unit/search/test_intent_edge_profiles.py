"""Tests for INTENT_EDGE_WEIGHT_PROFILES structure and completeness."""

from graph.graph_storage import DEFAULT_EDGE_WEIGHTS, INTENT_EDGE_WEIGHT_PROFILES
from search.intent_classifier import QueryIntent


class TestIntentEdgeWeightProfiles:
    """Test suite for A1: Intent-adaptive edge weight profiles."""

    def test_all_intents_have_profiles(self):
        """Every QueryIntent value should have a matching profile."""
        for intent in QueryIntent:
            assert intent.value in INTENT_EDGE_WEIGHT_PROFILES, (
                f"Missing profile for {intent.value}"
            )

    def test_all_profiles_have_all_edge_types(self):
        """Each profile should contain all 21 edge types."""
        for intent_key, profile in INTENT_EDGE_WEIGHT_PROFILES.items():
            for edge_type in DEFAULT_EDGE_WEIGHTS:
                assert edge_type in profile, (
                    f"Profile '{intent_key}' missing edge type '{edge_type}'"
                )

    def test_hybrid_profile_equals_default(self):
        """Hybrid (fallback) should match DEFAULT_EDGE_WEIGHTS."""
        assert INTENT_EDGE_WEIGHT_PROFILES["hybrid"] == DEFAULT_EDGE_WEIGHTS

    def test_weights_are_valid_floats(self):
        """All weights should be floats in [0.0, 1.0]."""
        for intent_key, profile in INTENT_EDGE_WEIGHT_PROFILES.items():
            for edge_type, weight in profile.items():
                assert 0.0 <= weight <= 1.0, (
                    f"{intent_key}.{edge_type}={weight} out of range"
                )

    def test_profile_count_matches_intent_count(self):
        """Should have exactly 7 profiles for 7 QueryIntent types."""
        assert len(INTENT_EDGE_WEIGHT_PROFILES) == len(QueryIntent), (
            f"Profile count mismatch: {len(INTENT_EDGE_WEIGHT_PROFILES)} profiles vs {len(QueryIntent)} intents"
        )

    def test_local_profile_boosts_structural_edges(self):
        """LOCAL profile should boost calls/inherits/overrides/implements."""
        local = INTENT_EDGE_WEIGHT_PROFILES["local"]
        assert local["calls"] == 1.0
        assert local["inherits"] == 1.0
        assert local["overrides"] == 1.0
        assert local["implements"] == 1.0
        assert local["imports"] == 0.1  # suppressed

    def test_global_profile_boosts_module_edges(self):
        """GLOBAL profile should boost imports/uses_type/instantiates."""
        glob = INTENT_EDGE_WEIGHT_PROFILES["global"]
        assert glob["imports"] == 0.7
        assert glob["uses_type"] == 0.9
        assert glob["instantiates"] == 0.8
        assert glob["calls"] == 0.6  # reduced

    def test_navigational_profile_exists(self):
        """NAVIGATIONAL profile should exist (bug fix verification)."""
        assert "navigational" in INTENT_EDGE_WEIGHT_PROFILES
        nav = INTENT_EDGE_WEIGHT_PROFILES["navigational"]
        assert nav["calls"] == 1.0
        assert nav["inherits"] == 0.9
