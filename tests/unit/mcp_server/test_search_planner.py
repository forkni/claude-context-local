"""Unit tests for SearchPlanner and related types in search_orchestrator.py."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock, patch

from mcp_server.tools.search_orchestrator import PlanRedirect, SearchPlan, SearchPlanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_app_config(intent_enabled=True, semantic_enabled=False):
    cfg = MagicMock()
    cfg.intent.enabled = intent_enabled
    cfg.intent.semantic_enabled = semantic_enabled
    cfg.intent.confidence_threshold = 0.3
    cfg.intent.log_classifications = False
    cfg.intent.semantic_weight = 0.3
    cfg.performance.max_index_age_minutes = 5.0
    cfg.search_mode.default_max_context_tokens = 0
    return cfg


def _make_search_config(default_k=4, max_k=20):
    sc = MagicMock()
    sc.search_mode.default_k = default_k
    sc.search_mode.max_k = max_k
    return sc


def _make_intent_decision(intent_value, confidence=0.9, suggested_params=None):
    from search.intent_classifier import IntentDecision, QueryIntent

    return IntentDecision(
        intent=QueryIntent(intent_value),
        confidence=confidence,
        reason="test",
        scores={},
        suggested_params=suggested_params or {},
    )


def _patch_planner_deps(app_cfg=None, sc=None, intent_decision=None):
    """Return a context manager that patches all external dependencies of SearchPlanner."""
    import contextlib

    app_cfg = app_cfg or _make_app_config()
    sc = sc or _make_search_config()

    @contextlib.contextmanager
    def _ctx():
        with (
            patch(
                "mcp_server.tools.search_orchestrator.get_config", return_value=app_cfg
            ),
            patch(
                "mcp_server.tools.search_orchestrator.get_search_config",
                return_value=sc,
            ),
            patch("mcp_server.tools.search_orchestrator.get_state") as mock_state,
            patch(
                "mcp_server.tools.search_orchestrator.IntentClassifier"
            ) as mock_ic_cls,
        ):
            mock_state.return_value.searcher = None
            ic = Mock()
            ic.classify.return_value = intent_decision or _make_intent_decision(
                "hybrid"
            )
            mock_ic_cls.return_value = ic
            yield mock_ic_cls, ic

    return _ctx()


# ---------------------------------------------------------------------------
# SearchPlan field extraction
# ---------------------------------------------------------------------------


class TestSearchPlannerFieldExtraction:
    """SearchPlanner.plan() correctly maps arguments → SearchPlan fields."""

    def test_k_clamped_to_max(self):
        with _patch_planner_deps(sc=_make_search_config(default_k=4, max_k=10)):
            plan = SearchPlanner().plan({"query": "test", "k": 999})
        assert plan.k == 10

    def test_k_defaults_to_config(self):
        with _patch_planner_deps(sc=_make_search_config(default_k=7, max_k=20)):
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.k == 7

    def test_file_pattern_extracted(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test", "file_pattern": "search/"})
        assert plan.file_pattern == "search/"

    def test_include_dirs_extracted(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test", "include_dirs": ["src/"]})
        assert plan.include_dirs == ["src/"]

    def test_exclude_dirs_extracted(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test", "exclude_dirs": ["tests/"]})
        assert plan.exclude_dirs == ["tests/"]

    def test_chunk_type_extracted(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test", "chunk_type": "method"})
        assert plan.chunk_type == "method"

    def test_auto_reindex_defaults_true(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.auto_reindex is True

    def test_auto_reindex_can_be_disabled(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test", "auto_reindex": False})
        assert plan.auto_reindex is False

    def test_include_parent_defaults_false(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.include_parent is False

    def test_ego_graph_defaults_false(self):
        with _patch_planner_deps():
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.ego_graph_enabled is False
        assert plan.ego_graph_k_hops == 2
        assert plan.ego_graph_max_neighbors == 10


# ---------------------------------------------------------------------------
# Intent disabled
# ---------------------------------------------------------------------------


class TestSearchPlannerIntentDisabled:
    def test_intent_disabled_returns_no_decision(self):
        with _patch_planner_deps(app_cfg=_make_app_config(intent_enabled=False)):
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.intent_decision is None
        assert plan.redirect is None

    def test_intent_disabled_no_weight_suggestions(self):
        with _patch_planner_deps(app_cfg=_make_app_config(intent_enabled=False)):
            plan = SearchPlanner().plan({"query": "test"})
        assert plan.suggested_bm25 is None
        assert plan.suggested_dense is None


# ---------------------------------------------------------------------------
# Intent redirects
# ---------------------------------------------------------------------------


class TestSearchPlannerRedirects:
    def test_path_tracing_redirect_when_source_and_target_present(self):
        decision = _make_intent_decision(
            "path_tracing",
            confidence=0.9,
            suggested_params={"source": "FooClass", "target": "BarFunction"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "how does foo reach bar"})

        assert plan.redirect is not None
        assert plan.redirect.kind == "find_path"
        assert plan.redirect.params["source"] == "FooClass"
        assert plan.redirect.params["target"] == "BarFunction"
        assert plan.redirect.params["max_hops"] == 10
        assert plan.redirect.fallback_on_error is False

    def test_path_tracing_no_redirect_when_source_missing(self):
        decision = _make_intent_decision(
            "path_tracing",
            confidence=0.9,
            suggested_params={"target": "BarFunction"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "how does foo reach bar"})
        assert plan.redirect is None

    def test_path_tracing_no_redirect_below_threshold(self):
        decision = _make_intent_decision(
            "path_tracing",
            confidence=0.1,  # below default 0.3
            suggested_params={"source": "Foo", "target": "Bar"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "path from foo to bar"})
        assert plan.redirect is None

    def test_similarity_redirect_when_symbol_present(self):
        decision = _make_intent_decision(
            "similarity",
            confidence=0.85,
            suggested_params={"symbol_name": "CodeEmbedder"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan(
                {"query": "find code similar to CodeEmbedder", "k": 6}
            )

        assert plan.redirect is not None
        assert plan.redirect.kind == "find_similar"
        assert plan.redirect.params["symbol_name"] == "CodeEmbedder"
        assert plan.redirect.fallback_on_error is True
        assert plan.redirect.k == 6

    def test_similarity_no_redirect_when_symbol_missing(self):
        decision = _make_intent_decision(
            "similarity",
            confidence=0.85,
            suggested_params={},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "find similar patterns"})
        assert plan.redirect is None


# ---------------------------------------------------------------------------
# Intent-driven parameter adjustments
# ---------------------------------------------------------------------------


class TestSearchPlannerIntentAdjustments:
    def test_contextual_intent_enables_ego_graph(self):
        decision = _make_intent_decision(
            "contextual",
            suggested_params={"ego_graph_enabled": True, "ego_graph_k_hops": 3},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "explore context around FooBar"})
        assert plan.ego_graph_enabled is True
        assert plan.ego_graph_k_hops == 3

    def test_global_intent_bumps_k(self):
        decision = _make_intent_decision("global", suggested_params={"k": 12})
        with _patch_planner_deps(sc=_make_search_config(default_k=4, max_k=20)):
            plan = SearchPlanner().plan({"query": "how does the search pipeline work"})
            # override intent_decision after patching
            with _patch_planner_deps(
                sc=_make_search_config(default_k=4, max_k=20),
                intent_decision=decision,
            ):
                plan = SearchPlanner().plan(
                    {"query": "how does the search pipeline work"}
                )
        assert plan.k == 12

    def test_global_intent_does_not_reduce_k(self):
        decision = _make_intent_decision("global", suggested_params={"k": 2})
        with _patch_planner_deps(
            sc=_make_search_config(default_k=4, max_k=20), intent_decision=decision
        ):
            plan = SearchPlanner().plan({"query": "how does search work"})
        assert plan.k == 4  # suggested_k 2 < k 4 → unchanged

    def test_intent_weight_suggestions_extracted(self):
        decision = _make_intent_decision(
            "local", suggested_params={"bm25_weight": 0.6, "dense_weight": 0.4}
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "where is CodeEmbedder defined"})
        assert plan.suggested_bm25 == 0.6
        assert plan.suggested_dense == 0.4

    def test_intent_suggested_search_mode_applied(self):
        decision = _make_intent_decision(
            "local", suggested_params={"search_mode": "bm25"}
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan(
                {"query": "find init_model", "search_mode": "auto"}
            )
        assert plan.search_mode == "bm25"

    def test_explicit_search_mode_not_overridden_by_intent(self):
        decision = _make_intent_decision(
            "local", suggested_params={"search_mode": "bm25"}
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan(
                {"query": "find init_model", "search_mode": "hybrid"}
            )
        assert plan.search_mode == "hybrid"


# ---------------------------------------------------------------------------
# redirect field always accompanied by valid SearchPlan
# ---------------------------------------------------------------------------


class TestSearchPlannerRedirectHasFullPlan:
    """PlanRedirect is embedded in SearchPlan; normal-search params are always present."""

    def test_similarity_redirect_plan_has_k(self):
        decision = _make_intent_decision(
            "similarity",
            confidence=0.9,
            suggested_params={"symbol_name": "HybridSearcher"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan(
                {"query": "code similar to HybridSearcher", "k": 8}
            )
        assert plan.k == 8  # normal search k is set even when redirect is present
        assert plan.redirect is not None

    def test_path_tracing_redirect_plan_is_searchplan_instance(self):
        decision = _make_intent_decision(
            "path_tracing",
            confidence=0.9,
            suggested_params={"source": "A", "target": "B"},
        )
        with _patch_planner_deps(intent_decision=decision):
            plan = SearchPlanner().plan({"query": "trace path from A to B"})
        assert isinstance(plan, SearchPlan)
        assert isinstance(plan.redirect, PlanRedirect)


# ---------------------------------------------------------------------------
# model_name-keyed cache test (#5 fix verification)
# ---------------------------------------------------------------------------


class TestAnchorCacheByModelName:
    """_ANCHOR_EMBEDDINGS_CACHE is keyed by model_name, not id()."""

    def setup_method(self):
        import search.intent_classifier as _ic

        _ic._ANCHOR_EMBEDDINGS_CACHE.clear()

    def teardown_method(self):
        import search.intent_classifier as _ic

        _ic._ANCHOR_EMBEDDINGS_CACHE.clear()

    def test_same_model_name_hits_cache(self):
        import numpy as np

        from search.intent_classifier import IntentClassifier

        class _Emb1:
            model_name = "test-model"

            def embed_query(self, t):
                return np.ones(64, dtype=np.float32)

        class _Emb2:
            model_name = "test-model"

            def embed_query(self, t):
                raise AssertionError("should have hit cache, not re-embedded")

        e1 = _Emb1()
        ic1 = IntentClassifier(embedder=e1, semantic_enabled=True, enable_logging=False)
        ic1.classify("test query")  # populates cache under "test-model"

        e2 = _Emb2()
        # Creating ic2 should load from cache, not call embed_query on e2
        ic2 = IntentClassifier(embedder=e2, semantic_enabled=True, enable_logging=False)
        assert ic2._anchor_embeddings is not None  # cache hit

    def test_different_model_names_do_not_collide(self):
        import numpy as np

        import search.intent_classifier as _ic
        from search.intent_classifier import IntentClassifier

        call_counts = {"a": 0, "b": 0}

        class _EmbA:
            model_name = "model-A"

            def embed_query(self, t):
                call_counts["a"] += 1
                return np.ones(64, dtype=np.float32)

        class _EmbB:
            model_name = "model-B"

            def embed_query(self, t):
                call_counts["b"] += 1
                return np.ones(64, dtype=np.float32)

        ea, eb = _EmbA(), _EmbB()
        ic_a = IntentClassifier(
            embedder=ea, semantic_enabled=True, enable_logging=False
        )
        ic_a.classify("test")  # loads model-A anchors

        ic_b = IntentClassifier(
            embedder=eb, semantic_enabled=True, enable_logging=False
        )
        ic_b.classify("test")  # loads model-B anchors independently

        assert "model-A" in _ic._ANCHOR_EMBEDDINGS_CACHE
        assert "model-B" in _ic._ANCHOR_EMBEDDINGS_CACHE
        assert call_counts["a"] > 0
        assert call_counts["b"] > 0
