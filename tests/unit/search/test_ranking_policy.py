"""Unit tests for search.ranking_policy — shared ranking constants and factor fns."""

from search.ranking_policy import (
    ACTION_WORDS,
    LIFECYCLE_INTENT_WORDS,
    LIFECYCLE_METHODS,
    NAME_OVERLAP_TIERS,
    TYPE_BOOSTS_CLASS_KEYWORD,
    TYPE_BOOSTS_CODE,
    TYPE_BOOSTS_ENTITY,
    lifecycle_demotion,
)


# ---------------------------------------------------------------------------
# Constants: basic structure / content assertions
# ---------------------------------------------------------------------------


class TestLifecycleConstants:
    def test_lifecycle_methods_contains_dunder_init(self):
        assert "__init__" in LIFECYCLE_METHODS

    def test_lifecycle_methods_frozenset(self):
        assert isinstance(LIFECYCLE_METHODS, frozenset)

    def test_lifecycle_methods_all_six(self):
        expected = {
            "__init__",
            "__enter__",
            "__exit__",
            "__del__",
            "__repr__",
            "__str__",
        }
        assert expected == LIFECYCLE_METHODS

    def test_lifecycle_intent_words_contains_init(self):
        assert "init" in LIFECYCLE_INTENT_WORDS

    def test_lifecycle_intent_words_frozenset(self):
        assert isinstance(LIFECYCLE_INTENT_WORDS, frozenset)

    def test_lifecycle_intent_words_includes_key_words(self):
        # The four most commonly queried lifecycle methods have explicit intent words
        for word in ("init", "enter", "exit", "repr"):
            assert word in LIFECYCLE_INTENT_WORDS
        # "lifecycle" is a catch-all that covers all dunder methods
        assert "lifecycle" in LIFECYCLE_INTENT_WORDS


class TestActionWords:
    def test_action_words_frozenset(self):
        assert isinstance(ACTION_WORDS, frozenset)

    def test_common_action_words_present(self):
        for word in ("find", "search", "get", "create", "build", "implement"):
            assert word in ACTION_WORDS


# ---------------------------------------------------------------------------
# Type boost dicts
# ---------------------------------------------------------------------------


class TestTypeBoostDicts:
    def test_entity_boosts_class_gt_function(self):
        assert TYPE_BOOSTS_ENTITY["class"] > TYPE_BOOSTS_ENTITY["function"]

    def test_entity_boosts_module_lt_one(self):
        assert TYPE_BOOSTS_ENTITY["module"] < 1.0
        assert TYPE_BOOSTS_ENTITY["community"] < 1.0

    def test_code_boosts_function_equals_method(self):
        assert TYPE_BOOSTS_CODE["function"] == TYPE_BOOSTS_CODE["method"]

    def test_code_boosts_module_lt_one(self):
        assert TYPE_BOOSTS_CODE["module"] < 1.0

    def test_class_keyword_boosts_class_higher(self):
        # With explicit "class" keyword, class boost is 1.4 > entity's 1.35
        assert TYPE_BOOSTS_CLASS_KEYWORD["class"] > TYPE_BOOSTS_ENTITY["class"]

    def test_entity_and_code_share_class_boost(self):
        assert TYPE_BOOSTS_ENTITY["class"] == TYPE_BOOSTS_CODE["class"] == 1.35

    def test_dicts_are_plain_dicts(self):
        for d in (TYPE_BOOSTS_ENTITY, TYPE_BOOSTS_CODE, TYPE_BOOSTS_CLASS_KEYWORD):
            assert isinstance(d, dict)

    def test_callers_can_extend_without_mutation(self):
        """Rankers should be able to merge without mutating the shared dict."""
        extended = {**TYPE_BOOSTS_ENTITY, "decorated_definition": 1.1}
        assert "decorated_definition" not in TYPE_BOOSTS_ENTITY  # original unchanged
        assert extended["decorated_definition"] == 1.1
        assert extended["class"] == TYPE_BOOSTS_ENTITY["class"]


# ---------------------------------------------------------------------------
# Name overlap tiers
# ---------------------------------------------------------------------------


class TestNameOverlapTiers:
    def test_three_tiers(self):
        assert len(NAME_OVERLAP_TIERS) == 3

    def test_tiers_descending_threshold(self):
        thresholds = [t[0] for t in NAME_OVERLAP_TIERS]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_tiers_descending_multiplier(self):
        multipliers = [t[1] for t in NAME_OVERLAP_TIERS]
        assert multipliers == sorted(multipliers, reverse=True)

    def test_high_tier(self):
        ratio, mult = NAME_OVERLAP_TIERS[0]
        assert ratio == 0.8
        assert mult == 1.3

    def test_mid_tier(self):
        ratio, mult = NAME_OVERLAP_TIERS[1]
        assert ratio == 0.5
        assert mult == 1.2

    def test_low_tier(self):
        ratio, mult = NAME_OVERLAP_TIERS[2]
        assert ratio == 0.3
        assert mult == 1.1

    def test_tier_loop_pattern_returns_highest_match(self):
        """Verify the canonical loop usage returns the correct multiplier."""
        overlap = 0.85
        result = 1.0
        for min_ratio, multiplier in NAME_OVERLAP_TIERS:
            if overlap >= min_ratio:
                result = multiplier
                break
        assert result == 1.3

    def test_tier_loop_below_all_thresholds_leaves_one(self):
        overlap = 0.1
        result = 1.0
        for min_ratio, multiplier in NAME_OVERLAP_TIERS:
            if overlap >= min_ratio:
                result = multiplier
                break
        assert result == 1.0  # no match; callers apply their own fallback


# ---------------------------------------------------------------------------
# lifecycle_demotion pure function
# ---------------------------------------------------------------------------


class TestLifecycleDemotion:
    def test_init_no_intent_returns_085(self):
        assert lifecycle_demotion("__init__", "how does the searcher work") == 0.85

    def test_init_with_init_intent_returns_one(self):
        assert lifecycle_demotion("__init__", "what does init do") == 1.0

    def test_init_with_lifecycle_intent_returns_one(self):
        assert lifecycle_demotion("__init__", "lifecycle of the object") == 1.0

    def test_repr_no_intent_returns_085(self):
        assert lifecycle_demotion("__repr__", "find the embedder") == 0.85

    def test_repr_with_repr_intent_returns_one(self):
        assert lifecycle_demotion("__repr__", "show repr output") == 1.0

    def test_non_lifecycle_method_returns_one(self):
        assert lifecycle_demotion("search", "find the embedder") == 1.0

    def test_non_lifecycle_regular_method_returns_one(self):
        assert lifecycle_demotion("rerank", "how does reranking work") == 1.0

    def test_enter_no_intent(self):
        assert lifecycle_demotion("__enter__", "context manager usage") == 0.85

    def test_enter_with_enter_intent(self):
        assert lifecycle_demotion("__enter__", "how does enter work") == 1.0

    def test_del_no_intent(self):
        assert lifecycle_demotion("__del__", "memory cleanup") == 0.85

    def test_del_with_del_intent(self):
        assert lifecycle_demotion("__del__", "del method cleanup") == 1.0

    def test_str_no_intent(self):
        assert lifecycle_demotion("__str__", "format output") == 0.85

    def test_empty_name_returns_one(self):
        assert lifecycle_demotion("", "some query") == 1.0

    def test_empty_query_no_intent(self):
        # Empty query → no lifecycle intent words → demotion applies
        assert lifecycle_demotion("__init__", "") == 0.85
