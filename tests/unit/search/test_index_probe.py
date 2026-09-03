"""Unit tests for the auto-tuning probe stage (search/index_probe.py, ADR-0014).

Covers: table-driven per-rule behaviour across hardware bands, the rule
engine's failure isolation, the create/append overrides writer, the probe
entry points (incl. escape hatches), and the guardrail static test asserting
benchmark-validated keys never appear as override rules.
"""

import json
from dataclasses import replace
from typing import Literal

import pytest

import search.index_probe as probe_module
from chunking.repo_profiler import RepoProfile
from search.config import PROJECT_OVERRIDES_FILENAME, _dotted_keys
from search.index_probe import (
    BENCHMARK_LOCK_CITATIONS,
    FORBIDDEN_AUTO_TUNE_KEYS,
    GLSL_EXTENSIONS,
    PROBE_VERSION,
    RULES,
    ProbeMeasurements,
    ProbeResult,
    ProbeRule,
    merged_probe_summary,
    probe_post_build,
    probe_pre_chunking,
    run_rules,
    write_overrides_file,
)


def make_measurements(**kwargs) -> ProbeMeasurements:
    """Baseline: 24GB workstation GPU, 24 cores, 233 Python files."""
    defaults = {
        "vram_total_gb": 24.0,
        "vram_free_gb": 20.0,
        "gpu_bf16_supported": True,
        "cpu_count": 24,
        "file_count": 233,
        "language_histogram": {".py": 233},
        "repo_profile": None,
        "embedding_model": None,
        "stats": None,
    }
    defaults.update(kwargs)
    return ProbeMeasurements(**defaults)


def make_profile(**kwargs) -> RepoProfile:
    defaults = {
        "function_count": 500,
        "p25_chars": 100,
        "p50_chars": 300,
        "p75_chars": 800,
        "p90_chars": 1500,
        "mean_chars": 500,
        "max_complexity": 12,
    }
    defaults.update(kwargs)
    return RepoProfile(**defaults)


def overrides_for(
    m: ProbeMeasurements, stage: Literal["pre_chunking", "post_build"] = "pre_chunking"
) -> dict:
    return run_rules(m, stage).overrides


def dotted_overrides(
    m: ProbeMeasurements, stage: Literal["pre_chunking", "post_build"] = "pre_chunking"
) -> set:
    return set(_dotted_keys(overrides_for(m, stage)))


# ---------------------------------------------------------------------------
# Guardrail static test — benchmark-validated keys must never be auto-tuned
# ---------------------------------------------------------------------------


class TestGuardrails:
    def test_forbidden_keys_pinned(self):
        """The forbidden set itself is pinned — removal must be a visible diff."""
        assert {
            "search_mode.bm25_weight",
            "search_mode.dense_weight",
            "search_mode.rrf_k_parameter",
            "search_mode.bm25_k1",
            "search_mode.bm25_b",
            "search_mode.bm25_use_stopwords",
            "search_mode.bm25_tokenizer",
            "search_mode.bm25_reserved_slots",
            "graph_enhanced.centrality_alpha",
            "graph_enhanced.centrality_exclude_phantoms",
            "graph_enhanced.drop_ambiguous_traversal_edges",
            "reranker.single_pass",
            "reranker.hop1_reserved_slots",
            "reranker.doc_representation_mode",
            "reranker.merged_pool_policy",
            "reranker.graph_hop_window_cap",
            "query_expansion.enabled",
            "multi_hop.expansion",
            "multi_hop.multi_hop_mode",
            "ego_graph.drop_nonpositive_output",
            "ego_graph.max_neighbors_per_hop",
            "call_graph.resolvers",
            "call_graph.ambiguous_fanout_cap",
            "call_graph.inject_on_incremental",
            "embedding.model_name",
        } == FORBIDDEN_AUTO_TUNE_KEYS

    def test_benchmark_lock_citations_match_forbidden_keys(self):
        """BENCHMARK_LOCK_CITATIONS (start_mcp_server.cmd's ADR-0022 display
        source) must cover every forbidden key except embedding.model_name,
        which is locked for index-routing safety, not a benchmark result, and
        is displayed separately. True by construction since both derive from
        spec(benchmark_locked=...); kept as a cheap invariant guard."""
        assert set(BENCHMARK_LOCK_CITATIONS) == FORBIDDEN_AUTO_TUNE_KEYS - {
            "embedding.model_name"
        }

    def test_benchmark_lock_citations_are_nonempty_strings(self):
        """Every spec(benchmark_locked=...) row must carry a real citation —
        an empty string would render a blank reason in the ':tuned_parameters'
        Benchmark-Locked panel."""
        for key, citation in BENCHMARK_LOCK_CITATIONS.items():
            assert isinstance(citation, str) and citation.strip(), key

    def test_index_routing_lock_is_not_a_benchmark_lock(self):
        """embedding.model_name is locked for index-routing safety and must
        never acquire a benchmark citation (it is displayed separately)."""
        assert "embedding.model_name" in FORBIDDEN_AUTO_TUNE_KEYS
        assert "embedding.model_name" not in BENCHMARK_LOCK_CITATIONS

    def test_no_override_rule_touches_forbidden_keys(self):
        for rule in RULES:
            if rule.kind == "override":
                assert rule.key not in FORBIDDEN_AUTO_TUNE_KEYS, (
                    f"Rule '{rule.key}' auto-tunes a benchmark-validated key"
                )

    def test_forbidden_keys_resolve_to_real_fields(self):
        """Every 'section.field' string must exist on SearchConfig.

        Catches typos like the one that made 'search_mode.centrality_alpha'
        (should be 'graph_enhanced.centrality_alpha') an inert guardrail --
        the key it named was never a real config path, so nothing it
        protected was ever actually forbidden.
        """
        import dataclasses

        from search.config import SearchConfig

        for dotted_key in FORBIDDEN_AUTO_TUNE_KEYS:
            section, _, field = dotted_key.partition(".")
            assert section in SearchConfig._SUBCONFIG_TYPES, (
                f"'{dotted_key}': '{section}' is not a SearchConfig sub-config"
            )
            subconfig_type = SearchConfig._SUBCONFIG_TYPES[section]
            field_names = {f.name for f in dataclasses.fields(subconfig_type)}
            assert field in field_names, (
                f"'{dotted_key}': '{field}' is not a field of {subconfig_type.__name__}"
            )

    def test_override_rules_resolve_to_real_fields(self):
        """Every RULES entry's 'section.field' string must exist on
        SearchConfig (2026-08-06 config-liveness audit, D4).

        Mirrors test_forbidden_keys_resolve_to_real_fields above but walks
        RULES instead of FORBIDDEN_AUTO_TUNE_KEYS: nothing previously asserted
        that a probe rule's key resolves to a real field, so a typo'd key
        would write a nonsense dotted key that _set_dotted/_build_subconfig
        silently drops as forward-compatible — the same inert-guardrail shape
        as the historical 'search_mode.centrality_alpha' bug, but on the
        write side instead of the forbidden-set read side.
        """
        import dataclasses

        from search.config import SearchConfig

        for rule in RULES:
            section, _, field = rule.key.partition(".")
            assert section in SearchConfig._SUBCONFIG_TYPES, (
                f"'{rule.key}': '{section}' is not a SearchConfig sub-config"
            )
            subconfig_type = SearchConfig._SUBCONFIG_TYPES[section]
            field_names = {f.name for f in dataclasses.fields(subconfig_type)}
            assert field in field_names, (
                f"'{rule.key}': '{field}' is not a field of {subconfig_type.__name__}"
            )

    def test_rules_pinned(self):
        """Pin the exact (kind, stage, key) set so a silent addition or
        removal of a rule shows up here as a reviewed diff.

        Reachability caveat: pinning proves a rule's key is a real
        SearchConfig field (see test_override_rules_resolve_to_real_fields)
        and its shape is stable — it does NOT prove the rule ever fires on
        the shipped code path. 'reranker.batch_size' is exactly this case:
        the rule is live for NeuralReranker/GenerativeReranker but a no-op on
        JinaRerankerV3 (the deployed default), which drops batch_size in
        create_reranker(). A rule can be correctly pinned here and still be
        inert on most installs; that is a deliberate, recorded trade-off
        (see docs/adr/0032-config-liveness-audit.md), not a gap this test
        closes.
        """
        assert {(r.kind, r.stage, r.key) for r in RULES} == {
            ("override", "pre_chunking", "embedding.batch_size"),
            ("override", "pre_chunking", "performance.dynamic_batch_max"),
            ("override", "pre_chunking", "performance.max_chunking_workers"),
            ("override", "pre_chunking", "reranker.enabled"),
            ("override", "pre_chunking", "reranker.batch_size"),
            ("override", "pre_chunking", "performance.vram_limit_fraction"),
            ("override", "pre_chunking", "performance.prefer_bf16"),
            ("override", "pre_chunking", "chunking.glsl_filter_td_prefix"),
            ("observation", "pre_chunking", "embedding.model_name"),
            ("observation", "pre_chunking", "chunking.max_split_chars"),
            ("observation", "post_build", "chunking.max_chunk_lines"),
            ("observation", "post_build", "ego_graph.max_neighbors_per_hop"),
        }

    def test_index_affecting_overrides_are_pre_chunking_only(self):
        """chunking.*/call_graph.*/embedding-context overrides may only fire at hook A."""
        index_affecting_prefixes = ("chunking.", "call_graph.")
        for rule in RULES:
            if rule.kind == "override" and rule.key.startswith(
                index_affecting_prefixes
            ):
                assert rule.stage == "pre_chunking", (
                    f"Index-affecting rule '{rule.key}' must run pre-chunking"
                )

    def test_rule_shape_invariants(self):
        """Observations have no value_fn; overrides always have one."""
        for rule in RULES:
            if rule.kind == "observation":
                assert rule.value_fn is None, rule.key
            else:
                assert rule.value_fn is not None, rule.key


# ---------------------------------------------------------------------------
# Table-driven per-rule tests: hardware bands
# ---------------------------------------------------------------------------


class TestHardwareRules:
    def test_workstation_band(self):
        result = run_rules(make_measurements(), "pre_chunking")
        assert result.overrides["embedding"]["batch_size"] == 256
        assert result.overrides["performance"]["dynamic_batch_max"] == 512
        assert result.overrides["reranker"]["batch_size"] == 32
        # Reranker stays enabled on a workstation GPU.
        assert "enabled" not in result.overrides.get("reranker", {})
        assert "vram_limit_fraction" not in result.overrides.get("performance", {})

    def test_desktop_band(self):
        m = make_measurements(vram_total_gb=12.0, vram_free_gb=10.0)
        result = run_rules(m, "pre_chunking")
        assert result.overrides["embedding"]["batch_size"] == 128
        assert result.overrides["performance"]["dynamic_batch_max"] == 384
        # Desktop is neither squeezed nor ample -> no reranker overrides.
        assert "reranker" not in result.overrides

    def test_laptop_band_squeezed(self):
        m = make_measurements(vram_total_gb=8.0, vram_free_gb=6.0)
        result = run_rules(m, "pre_chunking")
        assert result.overrides["embedding"]["batch_size"] == 64
        assert result.overrides["performance"]["dynamic_batch_max"] == 192
        assert result.overrides["reranker"]["batch_size"] == 8
        assert "enabled" not in result.overrides["reranker"]

    def test_minimal_band_disables_reranker(self):
        m = make_measurements(vram_total_gb=4.0, vram_free_gb=3.0)
        result = run_rules(m, "pre_chunking")
        assert result.overrides["reranker"]["enabled"] is False
        assert result.overrides["performance"]["vram_limit_fraction"] == 0.70
        assert result.overrides["embedding"]["batch_size"] == 32

    def test_no_gpu_disables_reranker_and_skips_batch_tuning(self):
        m = make_measurements(
            vram_total_gb=None, vram_free_gb=None, gpu_bf16_supported=None
        )
        result = run_rules(m, "pre_chunking")
        assert result.overrides["reranker"]["enabled"] is False
        assert "no CUDA GPU" in result.reasons["reranker.enabled"]
        assert "embedding" not in result.overrides
        assert "dynamic_batch_max" not in result.overrides.get("performance", {})

    def test_bf16_unsupported_gpu_prefers_fp16(self):
        m = make_measurements(gpu_bf16_supported=False)
        assert overrides_for(m)["performance"]["prefer_bf16"] is False

    def test_bf16_supported_gpu_emits_no_precision_override(self):
        assert "performance.prefer_bf16" not in dotted_overrides(make_measurements())


class TestWorkersRule:
    def test_plan_example_cpu24_files233(self):
        result = run_rules(make_measurements(), "pre_chunking")
        assert result.overrides["performance"]["max_chunking_workers"] == 12
        assert "cpu_count=24" in result.reasons["performance.max_chunking_workers"]

    @pytest.mark.parametrize(
        ("cpu_count", "file_count", "expected"),
        [
            (4, 100, 2),  # half the cores
            (64, 1000, 16),  # hard cap at 16
            (24, 3, 3),  # capped by file count
            (2, 100, 1),  # floor at 1
        ],
    )
    def test_bands(self, cpu_count, file_count, expected):
        m = make_measurements(cpu_count=cpu_count, file_count=file_count)
        assert overrides_for(m)["performance"]["max_chunking_workers"] == expected

    def test_zero_files_skips_rule(self):
        m = make_measurements(file_count=0, language_histogram={})
        assert "performance.max_chunking_workers" not in dotted_overrides(m)


class TestGlslRule:
    def test_fires_only_when_glsl_present(self):
        m = make_measurements(language_histogram={".py": 100, ".frag": 5, ".glsl": 2})
        result = run_rules(m, "pre_chunking")
        assert result.overrides["chunking"]["glsl_filter_td_prefix"] is True
        assert "7 GLSL files" in result.reasons["chunking.glsl_filter_td_prefix"]

    def test_absent_without_glsl(self):
        assert "chunking.glsl_filter_td_prefix" not in dotted_overrides(
            make_measurements()
        )

    def test_all_eight_extensions_recognized(self):
        assert {
            ".glsl",
            ".frag",
            ".vert",
            ".comp",
            ".geom",
            ".tesc",
            ".tese",
            ".glslinc",
        } == GLSL_EXTENSIONS
        for ext in GLSL_EXTENSIONS:
            m = make_measurements(language_histogram={ext: 1})
            assert "chunking.glsl_filter_td_prefix" in dotted_overrides(m), ext


class TestObservationRules:
    def test_model_tier_mismatch_is_observation_only(self):
        m = make_measurements(embedding_model="some-org/other-model")
        result = run_rules(m, "pre_chunking")
        keys = [o["key"] for o in result.observations]
        assert "embedding.model_name" in keys
        assert "embedding.model_name" not in _dotted_keys(result.overrides)
        note = next(
            o["note"] for o in result.observations if o["key"] == "embedding.model_name"
        )
        assert "never auto-applied" in note

    def test_model_tier_match_emits_nothing(self):
        m = make_measurements(embedding_model="Qwen/Qwen3-Embedding-0.6B")
        result = run_rules(m, "pre_chunking")
        assert "embedding.model_name" not in [o["key"] for o in result.observations]

    def test_none_repo_profile_tolerated(self):
        result = run_rules(make_measurements(repo_profile=None), "pre_chunking")
        assert "chunking.max_split_chars" not in [o["key"] for o in result.observations]

    def test_large_p90_emits_split_fit_note(self):
        m = make_measurements(repo_profile=make_profile(p90_chars=5000))
        result = run_rules(m, "pre_chunking")
        assert "chunking.max_split_chars" in [o["key"] for o in result.observations]

    def test_small_p90_stays_quiet(self):
        m = make_measurements(repo_profile=make_profile(p90_chars=1500))
        result = run_rules(m, "pre_chunking")
        assert "chunking.max_split_chars" not in [o["key"] for o in result.observations]


class TestPostBuildRules:
    def test_post_build_emits_no_overrides_ever(self):
        m = make_measurements(
            stats={
                "total_chunks": 100000,
                "files_indexed": 100,
                "chunk_types": {"split_block": 90000},
            }
        )
        result = run_rules(m, "post_build")
        assert result.overrides == {}
        assert result.reasons == {}

    def test_split_heavy_corpus_note(self):
        m = make_measurements(
            stats={
                "total_chunks": 1000,
                "files_indexed": 200,
                "chunk_types": {"split_block": 300},
            }
        )
        keys = [o["key"] for o in run_rules(m, "post_build").observations]
        assert "chunking.max_chunk_lines" in keys

    def test_dense_files_ego_note(self):
        m = make_measurements(stats={"total_chunks": 3000, "files_indexed": 100})
        keys = [o["key"] for o in run_rules(m, "post_build").observations]
        assert "ego_graph.max_neighbors_per_hop" in keys

    def test_modest_corpus_stays_quiet(self):
        m = make_measurements(
            stats={
                "total_chunks": 1000,
                "files_indexed": 200,
                "chunk_types": {"split_block": 50, "function": 950},
            }
        )
        assert run_rules(m, "post_build").observations == []

    def test_empty_stats_tolerated(self):
        m = make_measurements(stats={})
        assert run_rules(m, "post_build").observations == []


# ---------------------------------------------------------------------------
# Engine invariants
# ---------------------------------------------------------------------------


class TestEngine:
    @pytest.mark.parametrize(
        "m",
        [
            make_measurements(),
            make_measurements(vram_total_gb=8.0, vram_free_gb=6.0),
            make_measurements(vram_total_gb=None, vram_free_gb=None),
            make_measurements(language_histogram={".glsl": 3}),
        ],
    )
    def test_reasons_match_overrides_one_to_one(self, m):
        result = run_rules(m, "pre_chunking")
        assert set(result.reasons) == set(_dotted_keys(result.overrides))

    def test_observations_never_duplicate_override_keys(self):
        m = make_measurements(
            embedding_model="some-org/other-model",
            repo_profile=make_profile(p90_chars=9000),
        )
        result = run_rules(m, "pre_chunking")
        override_keys = set(_dotted_keys(result.overrides))
        for obs in result.observations:
            assert obs["key"] not in override_keys

    def test_raising_rule_is_isolated(self, caplog):
        def boom(_m):
            raise RuntimeError("rule exploded")

        rules = (
            ProbeRule(
                key="performance.max_parallel_workers",
                kind="override",
                stage="pre_chunking",
                condition=boom,
                value_fn=lambda m: 2,
                reason_fn=lambda m: "unreachable",
            ),
            ProbeRule(
                key="performance.dynamic_batch_max",
                kind="override",
                stage="pre_chunking",
                condition=lambda m: True,
                value_fn=lambda m: 512,
                reason_fn=lambda m: "still runs",
            ),
        )
        result = run_rules(make_measurements(), "pre_chunking", rules=rules)
        assert result.overrides == {"performance": {"dynamic_batch_max": 512}}

    def test_stage_filter(self):
        result = run_rules(make_measurements(), "post_build")
        # No pre_chunking override may leak into a post_build pass.
        assert result.overrides == {}


# ---------------------------------------------------------------------------
# Writer: create / append
# ---------------------------------------------------------------------------


def _sample_result() -> ProbeResult:
    return ProbeResult(
        overrides={"performance": {"max_chunking_workers": 12}},
        reasons={"performance.max_chunking_workers": "cpu_count=24 -> 12"},
        observations=[{"key": "embedding.model_name", "note": "tier note"}],
    )


class TestWriter:
    def test_create_writes_full_schema(self, tmp_path):
        path = write_overrides_file(tmp_path, _sample_result(), mode="create")
        assert path == tmp_path / PROJECT_OVERRIDES_FILENAME
        data = json.loads(path.read_text())
        assert data["probe_version"] == PROBE_VERSION
        assert data["generated_at"]
        assert data["overrides"] == {"performance": {"max_chunking_workers": 12}}
        assert data["reasons"] == {
            "performance.max_chunking_workers": "cpu_count=24 -> 12"
        }
        assert data["observations"] == [
            {"key": "embedding.model_name", "note": "tier note"}
        ]

    def test_create_overwrites_wholesale(self, tmp_path):
        stale = tmp_path / PROJECT_OVERRIDES_FILENAME
        stale.write_text(
            json.dumps(
                {
                    "probe_version": "0",
                    "generated_at": "old",
                    "overrides": {"reranker": {"enabled": False}},
                    "reasons": {"reranker.enabled": "stale"},
                    "observations": [{"key": "old.key", "note": "stale note"}],
                }
            )
        )
        write_overrides_file(tmp_path, _sample_result(), mode="create")
        data = json.loads(stale.read_text())
        assert data["probe_version"] == PROBE_VERSION
        assert "reranker" not in data["overrides"]
        assert data["observations"] == [
            {"key": "embedding.model_name", "note": "tier note"}
        ]

    def test_append_extends_observations_preserving_pass1(self, tmp_path):
        write_overrides_file(tmp_path, _sample_result(), mode="create")
        original = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())

        pass2 = ProbeResult(
            observations=[{"key": "chunking.max_merged_tokens", "note": "big"}]
        )
        write_overrides_file(tmp_path, pass2, mode="append")

        data = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())
        assert data["overrides"] == original["overrides"]
        assert data["reasons"] == original["reasons"]
        assert data["generated_at"] == original["generated_at"]
        assert data["observations"] == [
            {"key": "embedding.model_name", "note": "tier note"},
            {"key": "chunking.max_merged_tokens", "note": "big"},
        ]

    def test_append_dedupes_identical_observations(self, tmp_path):
        write_overrides_file(tmp_path, _sample_result(), mode="create")
        dup = ProbeResult(
            observations=[{"key": "embedding.model_name", "note": "tier note"}]
        )
        write_overrides_file(tmp_path, dup, mode="append")
        data = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())
        assert len(data["observations"]) == 1

    def test_append_onto_missing_file_creates(self, tmp_path):
        pass2 = ProbeResult(observations=[{"key": "k", "note": "n"}])
        path = write_overrides_file(tmp_path, pass2, mode="append")
        data = json.loads(path.read_text())
        assert data["probe_version"] == PROBE_VERSION
        assert data["observations"] == [{"key": "k", "note": "n"}]

    def test_append_onto_corrupt_file_recovers_fresh(self, tmp_path):
        (tmp_path / PROJECT_OVERRIDES_FILENAME).write_text("{not json")
        pass2 = ProbeResult(observations=[{"key": "k", "note": "n"}])
        path = write_overrides_file(tmp_path, pass2, mode="append")
        data = json.loads(path.read_text())
        assert data["observations"] == [{"key": "k", "note": "n"}]


# ---------------------------------------------------------------------------
# Entry points + escape hatches
# ---------------------------------------------------------------------------


class TestEntryPoints:
    @pytest.fixture(autouse=True)
    def _enabled_config(self, monkeypatch):
        """Default: probe enabled, no env escape hatch."""
        monkeypatch.delenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", raising=False)

        class _Perf:
            enable_project_overrides = True

        class _Config:
            performance = _Perf()

        self.config = _Config()
        monkeypatch.setattr(probe_module, "get_search_config", lambda: self.config)

    def test_pre_chunking_writes_file_and_returns_summary(self, tmp_path):
        summary = probe_pre_chunking(
            tmp_path,
            supported_files=["a.py", "b.py"],
            repo_profile=None,
            measurements=make_measurements(),
        )
        assert summary is not None
        assert summary["stage"] == "pre_chunking"
        assert summary["probe_version"] == PROBE_VERSION
        assert "performance.max_chunking_workers" in summary["override_keys"]
        assert set(summary["reasons"]) == set(summary["override_keys"])
        data = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())
        assert data["overrides"]["performance"]["max_chunking_workers"] == 12

    def test_pre_chunking_builds_measurements_from_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(probe_module, "_measure_gpu", lambda: (None, None, None))
        summary = probe_pre_chunking(
            tmp_path,
            supported_files=["s/x.py", "s/y.glsl"],
            repo_profile=None,
        )
        assert summary is not None
        data = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())
        # No GPU -> reranker disabled; GLSL present -> TD filter pinned.
        assert data["overrides"]["reranker"]["enabled"] is False
        assert data["overrides"]["chunking"]["glsl_filter_td_prefix"] is True

    def test_post_build_appends_observations(self, tmp_path):
        probe_pre_chunking(
            tmp_path,
            supported_files=["a.py"],
            repo_profile=None,
            measurements=make_measurements(),
        )
        summary = probe_post_build(
            tmp_path, stats={"total_chunks": 6000, "files_indexed": 100}
        )
        assert summary is not None
        assert summary["stage"] == "post_build"
        assert summary["override_keys"] == []
        assert "ego_graph.max_neighbors_per_hop" in summary["observation_keys"]
        data = json.loads((tmp_path / PROJECT_OVERRIDES_FILENAME).read_text())
        obs_keys = [o["key"] for o in data["observations"]]
        assert "ego_graph.max_neighbors_per_hop" in obs_keys
        # Pass-1 overrides survive the append.
        assert data["overrides"]["performance"]["max_chunking_workers"] == 12

    def test_post_build_quiet_corpus_returns_none_without_touching_file(self, tmp_path):
        probe_pre_chunking(
            tmp_path,
            supported_files=["a.py"],
            repo_profile=None,
            measurements=make_measurements(),
        )
        before = (tmp_path / PROJECT_OVERRIDES_FILENAME).read_text()
        summary = probe_post_build(
            tmp_path, stats={"total_chunks": 100, "files_indexed": 50}
        )
        assert summary is None
        assert (tmp_path / PROJECT_OVERRIDES_FILENAME).read_text() == before

    def test_post_build_quiet_corpus_logs_explicit_no_op(self, tmp_path, caplog):
        """Workstream C2: a quiet-corpus no-op (rules evaluated, none
        triggered) must log an explicit INFO line -- otherwise it is
        indistinguishable from pass 2 silently failing to run at all."""
        import logging

        probe_pre_chunking(
            tmp_path,
            supported_files=["a.py"],
            repo_profile=None,
            measurements=make_measurements(),
        )
        with caplog.at_level(logging.INFO, logger="search.index_probe"):
            summary = probe_post_build(
                tmp_path, stats={"total_chunks": 100, "files_indexed": 50}
            )
        assert summary is None
        messages = [rec.getMessage() for rec in caplog.records]
        assert any("Pass 2: no new observations" in m for m in messages), (
            f"Expected an explicit no-op log line; got {messages}"
        )

    def test_env_escape_hatch_skips_both_passes(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", "1")
        assert (
            probe_pre_chunking(tmp_path, [], None, measurements=make_measurements())
            is None
        )
        assert probe_post_build(tmp_path, {"total_chunks": 9999}) is None
        assert not (tmp_path / PROJECT_OVERRIDES_FILENAME).exists()

    def test_config_flag_escape_hatch_skips(self, tmp_path):
        self.config.performance.enable_project_overrides = False
        assert (
            probe_pre_chunking(tmp_path, [], None, measurements=make_measurements())
            is None
        )
        assert not (tmp_path / PROJECT_OVERRIDES_FILENAME).exists()


class TestMergedSummary:
    def test_both_none(self):
        assert merged_probe_summary(None, None) is None

    def test_merges_both_passes(self):
        m = make_measurements()
        pass1 = run_rules(m, "pre_chunking").summary("pre_chunking")
        pass2 = run_rules(
            replace(m, stats={"total_chunks": 6000, "files_indexed": 100}),
            "post_build",
        ).summary("post_build")
        merged = merged_probe_summary(pass1, pass2)
        assert merged is not None
        assert merged["probe_version"] == PROBE_VERSION
        assert "performance.max_chunking_workers" in merged["override_keys"]
        assert "ego_graph.max_neighbors_per_hop" in merged["observation_keys"]

    def test_pass1_only(self):
        pass1 = run_rules(make_measurements(), "pre_chunking").summary("pre_chunking")
        merged = merged_probe_summary(pass1, None)
        assert merged is not None
        assert merged["override_keys"] == pass1["override_keys"]
        assert merged["observation_keys"] == pass1["observation_keys"]
