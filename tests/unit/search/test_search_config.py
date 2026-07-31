"""Tests for search configuration system."""

import json
import os
import tempfile
from unittest.mock import patch

from search.config import (
    RerankerConfig,
    SearchConfig,
    SearchConfigManager,
    get_search_config,
)


class TestSearchConfig:
    """Test SearchConfig class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SearchConfig()

        assert config.search_mode.default_mode == "hybrid"
        assert config.search_mode.enable_hybrid is True
        assert config.search_mode.bm25_weight == 0.35  # Benchmark-verified optimal
        assert config.search_mode.dense_weight == 0.65  # Benchmark-verified optimal
        assert config.performance.use_parallel_search is True

    def test_to_dict_conversion(self):
        """Test conversion to dictionary."""
        config = SearchConfig()
        config_dict = config.to_dict()

        assert isinstance(config_dict, dict)
        # Check nested structure (v0.8.0+)
        assert "search_mode" in config_dict
        assert isinstance(config_dict["search_mode"], dict)
        assert config_dict["search_mode"]["default_mode"] == "hybrid"
        assert config_dict["search_mode"]["enable_hybrid"] is True

    def test_from_dict_creation(self):
        """Test creation from dictionary."""
        data = {
            "default_search_mode": "semantic",
            "bm25_weight": 0.3,
            "dense_weight": 0.7,
        }

        config = SearchConfig.from_dict(data)
        assert config.search_mode.default_mode == "semantic"
        assert config.search_mode.bm25_weight == 0.3
        assert config.search_mode.dense_weight == 0.7
        assert config.search_mode.enable_hybrid is True  # Default value


class TestSearchConfigManager:
    """Test SearchConfigManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")

    def test_load_default_config(self):
        """Test loading default configuration."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert isinstance(config, SearchConfig)
        assert config.search_mode.default_mode == "hybrid"

    def test_load_from_file(self):
        """Test loading configuration from file."""
        # Create test config file
        test_config = {
            "default_search_mode": "bm25",
            "bm25_weight": 0.5,
            "enable_hybrid_search": False,
        }

        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        # Load config
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert config.search_mode.default_mode == "bm25"
        assert config.search_mode.bm25_weight == 0.5
        assert config.search_mode.enable_hybrid is False

    def test_environment_overrides(self):
        """Test environment variable overrides."""
        with patch.dict(
            os.environ,
            {
                "CLAUDE_SEARCH_MODE": "semantic",
                "CLAUDE_ENABLE_HYBRID": "false",
                "CLAUDE_BM25_WEIGHT": "0.8",
            },
        ):
            manager = SearchConfigManager(self.config_file)
            config = manager.load_config()

            assert config.search_mode.default_mode == "semantic"
            assert config.search_mode.enable_hybrid is False
            assert config.search_mode.bm25_weight == 0.8

    def test_save_config(self):
        """Test saving configuration."""
        config = SearchConfig()
        config.search_mode.default_mode = "bm25"
        config.search_mode.bm25_weight = 0.7

        manager = SearchConfigManager(self.config_file)
        manager.save_config(config)

        # Verify file was created
        assert os.path.exists(self.config_file)

        # Verify content (nested structure v0.8.0+)
        with open(self.config_file) as f:
            saved_data = json.load(f)

        assert "search_mode" in saved_data
        assert isinstance(saved_data["search_mode"], dict)
        assert saved_data["search_mode"]["default_mode"] == "bm25"
        assert saved_data["search_mode"]["bm25_weight"] == 0.7

    def test_save_config_syncs_cache_mtime(self):
        """save_config must update _config_mtime so the next load_config() short-circuits."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()
        config.search_mode.bm25_weight = 0.99

        manager.save_config(config)

        # Cache mtime must match the on-disk mtime after save
        disk_mtime = os.path.getmtime(self.config_file)
        assert manager._config_mtime == disk_mtime, (
            "save_config must sync _config_mtime to the post-write disk mtime"
        )

        # And the next load_config() must return the cached object (no re-parse)
        second = manager.load_config()
        assert second is config, (
            "load_config after save_config should return the cached object, "
            "not a fresh parse from disk"
        )

    def test_auto_mode_detection(self):
        """Test automatic search mode detection."""
        # Create config with auto mode
        test_config = {"default_search_mode": "auto"}
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        manager = SearchConfigManager(self.config_file)

        # Text-heavy query should suggest BM25
        mode = manager.get_search_mode_for_query("find error message text")
        assert mode == "bm25"

        # Code structure query should suggest semantic
        mode = manager.get_search_mode_for_query("find class definition")
        assert mode == "semantic"

        # Generic query should default to hybrid
        mode = manager.get_search_mode_for_query("database connection")
        assert mode == "hybrid"

    def test_explicit_mode_override(self):
        """Test explicit mode override."""
        # Create config with auto mode
        test_config = {"default_search_mode": "auto"}
        with open(self.config_file, "w") as f:
            json.dump(test_config, f)

        manager = SearchConfigManager(self.config_file)

        # Explicit mode should override auto-detection
        mode = manager.get_search_mode_for_query(
            "find error message", explicit_mode="semantic"
        )
        assert mode == "semantic"

        # Auto mode should fall back to detection
        mode = manager.get_search_mode_for_query(
            "find error message", explicit_mode="auto"
        )
        assert mode == "bm25"


class TestDefaultConfigPath:
    """Test default config path discovery."""

    def test_default_path_uses_claude_code_search(self):
        """Test that default path uses .claude_code_search directory."""
        # Create manager without explicit config_file
        mgr = SearchConfigManager()

        # Should use .claude_code_search, not .claude-context-mcp
        assert (
            ".claude_code_search" in mgr.config_file
            or "search_config.json" in mgr.config_file
        )
        assert ".claude-context-mcp" not in mgr.config_file

    def test_config_path_fallback_order(self, monkeypatch, tmp_path):
        """Test config path discovery fallback order.

        Candidates are anchored to the repo root (not process cwd) since 2026-07-09 --
        a cwd-relative resolution let ``search_config.json`` silently miss whenever the
        MCP server or a script was launched from outside the repo root, one of the
        contributing defects behind the EmbeddingGemma-fallback incident (see
        project_search_config_guard memory note). Patch ``CONFIG_PATH_CANDIDATES``
        itself to point at an isolated tmp dir so this test doesn't depend on (or
        pollute) the real repo's search_config.json, and to prove cwd no longer
        matters.
        """
        import search.config as config_module
        import search.config_paths as config_paths_module

        fake_repo_config = str(tmp_path / "search_config.json")
        monkeypatch.setattr(
            config_paths_module,
            "CONFIG_PATH_CANDIDATES",
            [
                fake_repo_config,
                str(tmp_path / ".search_config.json"),
                str(tmp_path / "storage" / "search_config.json"),
            ],
        )

        original_dir = os.getcwd()
        other_dir = tempfile.mkdtemp()
        try:
            # Reset global config manager to ensure clean state
            config_module._config_manager = None

            # No config files exist - should return first candidate
            mgr = SearchConfigManager()
            assert mgr.config_file == fake_repo_config

            # Create the repo-root candidate - should be preferred
            with open(fake_repo_config, "w") as f:
                json.dump({"default_search_mode": "bm25"}, f)

            # Reset manager to pick up new file
            config_module._config_manager = None
            mgr2 = SearchConfigManager()
            assert mgr2.config_file == fake_repo_config

            # Changing cwd must NOT change resolution -- this is the behavior the
            # repo-root anchoring guarantees.
            os.chdir(other_dir)
            config_module._config_manager = None
            mgr3 = SearchConfigManager()
            assert mgr3.config_file == fake_repo_config
        finally:
            os.chdir(original_dir)
            # Reset global state
            config_module._config_manager = None

    def test_config_persistence_to_storage_location(self, tmp_path):
        """Test saving config to storage directory."""

        # Use temporary storage path instead of production directory
        storage_path = tmp_path / "test_search_config.json"

        mgr = SearchConfigManager(config_file=str(storage_path))
        cfg = mgr.load_config()
        cfg.embedding.model_name = "BAAI/bge-m3"
        cfg.search_mode.default_mode = "semantic"
        mgr.save_config(cfg)

        # Verify file exists
        assert storage_path.exists()

        # Load in new manager
        mgr2 = SearchConfigManager(config_file=str(storage_path))
        cfg2 = mgr2.load_config()
        assert cfg2.embedding.model_name == "BAAI/bge-m3"
        assert cfg2.search_mode.default_mode == "semantic"

        # tmp_path cleanup is automatic via pytest fixture


def test_global_config_functions():
    """Test global configuration functions."""
    config = get_search_config()
    assert isinstance(config, SearchConfig)

    # Test helper functions
    from search.config import get_default_search_mode, is_hybrid_search_enabled

    assert isinstance(is_hybrid_search_enabled(), bool)
    assert get_default_search_mode() in ["hybrid", "semantic", "bm25", "auto"]


def test_graph_enhanced_config_round_trip():
    """Test GraphEnhancedConfig serialization and deserialization."""
    from search.config import GraphEnhancedConfig, SearchConfig

    # Create config with custom graph_enhanced settings
    graph_config = GraphEnhancedConfig(
        centrality_method="betweenness",
        centrality_alpha=0.5,
        centrality_annotation=False,
        centrality_reranking=True,
    )
    config = SearchConfig(graph_enhanced=graph_config)

    # Serialize to dict
    config_dict = config.to_dict()
    assert "graph_enhanced" in config_dict
    assert config_dict["graph_enhanced"]["centrality_method"] == "betweenness"
    assert config_dict["graph_enhanced"]["centrality_alpha"] == 0.5
    assert config_dict["graph_enhanced"]["centrality_annotation"] is False
    assert config_dict["graph_enhanced"]["centrality_reranking"] is True

    # Deserialize from dict (nested format)
    config2 = SearchConfig.from_dict(config_dict)
    assert config2.graph_enhanced.centrality_method == "betweenness"
    assert config2.graph_enhanced.centrality_alpha == 0.5
    assert config2.graph_enhanced.centrality_annotation is False
    assert config2.graph_enhanced.centrality_reranking is True


def test_graph_enhanced_config_legacy_keys():
    """Test GraphEnhancedConfig with legacy flat-key format."""
    from search.config import SearchConfig

    # Legacy flat format (pre-v0.8.0)
    legacy_dict = {
        "centrality_method": "degree",
        "centrality_alpha": 0.2,
        "centrality_annotation": False,
        "centrality_reranking": True,
        "embedding_model_name": "BAAI/bge-m3",  # Other legacy keys
    }

    config = SearchConfig.from_dict(legacy_dict)
    assert config.graph_enhanced.centrality_method == "degree"
    assert config.graph_enhanced.centrality_alpha == 0.2
    assert config.graph_enhanced.centrality_annotation is False
    assert config.graph_enhanced.centrality_reranking is True


# ---------------------------------------------------------------------------
# Regression tests added to lock in the de/serialization unification:
# - no defaults drift between SearchConfig() and from_dict({})
# - lossless to_dict → from_dict round-trip
# - env-var overrides apply over a nested config file
# ---------------------------------------------------------------------------


def test_defaults_consistency():
    """SearchConfig() and from_dict({}) must produce identical field values.

    Guards against defaults drift between the dataclass defaults and the
    (now-removed) hard-coded literals that were in from_dict.
    """
    import dataclasses

    from search.config import SearchConfig

    direct = SearchConfig()
    from_empty = SearchConfig.from_dict({})

    for sub_name in SearchConfig._SUBCONFIG_FIELDS:
        direct_sub = getattr(direct, sub_name)
        loaded_sub = getattr(from_empty, sub_name)
        assert dataclasses.asdict(direct_sub) == dataclasses.asdict(loaded_sub), (
            f"Defaults mismatch in sub-config '{sub_name}': "
            f"SearchConfig() != from_dict({{}})"
        )


def test_round_trip_lossless():
    """to_dict() → from_dict() must be identity for a fully-populated config.

    Verifies that to_dict includes every field (including previously-omitted ones
    like parent_retrieval, output.source_order_output, graph_enhanced boost block).
    """
    import dataclasses

    from search.config import SearchConfig

    original = SearchConfig()
    restored = SearchConfig.from_dict(original.to_dict())

    for sub_name in SearchConfig._SUBCONFIG_FIELDS:
        orig_sub = getattr(original, sub_name)
        rest_sub = getattr(restored, sub_name)
        assert dataclasses.asdict(orig_sub) == dataclasses.asdict(rest_sub), (
            f"Round-trip mismatch in sub-config '{sub_name}': "
            f"to_dict → from_dict produced different values"
        )


def test_to_dict_includes_all_subconfigs():
    """to_dict must include every sub-config, including parent_retrieval."""
    from search.config import SearchConfig

    result = SearchConfig().to_dict()

    for sub_name in SearchConfig._SUBCONFIG_FIELDS:
        assert sub_name in result, f"to_dict missing sub-config '{sub_name}'"
        assert isinstance(result[sub_name], dict), (
            f"to_dict['{sub_name}'] should be a dict"
        )

    # Previously-omitted specific fields
    assert "source_order_output" in result["output"]
    assert "centrality_bm25_boost" in result["graph_enhanced"]
    assert "enabled" in result["parent_retrieval"]


def test_env_override_applies_over_nested_file(tmp_path):
    """CLAUDE_* env overrides must apply over a nested JSON config file.

    Previously the flat env keys were silently ignored when the config file
    was in nested format (the nested branch never read flat keys).
    """
    import json
    import os
    from unittest.mock import patch

    from search.config import SearchConfigManager

    # Write a nested config file
    config_file = tmp_path / "search_config.json"
    config_file.write_text(json.dumps({"search_mode": {"default_mode": "hybrid"}}))

    with patch.dict(os.environ, {"CLAUDE_SEARCH_MODE": "bm25"}):
        manager = SearchConfigManager(config_file=str(config_file))
        config = manager.load_config()

    # Env must have overridden the file value
    assert config.search_mode.default_mode == "bm25"


def test_reranker_dedupe_split_blocks_default_and_flat_alias():
    """Q1 toggle: defaults to True; legacy flat key maps into the nested schema."""
    assert RerankerConfig().dedupe_split_blocks is True

    config = SearchConfig.from_dict({"reranker_dedupe_split_blocks": False})
    assert config.reranker.dedupe_split_blocks is False

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.reranker.dedupe_split_blocks is False


def test_reranker_single_pass_default_and_flat_alias():
    """Q3 toggle: defaults to False; flat key maps into the nested schema."""
    assert RerankerConfig().single_pass is False

    config = SearchConfig.from_dict({"reranker_single_pass": True})
    assert config.reranker.single_pass is True

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.reranker.single_pass is True


def test_reranker_instruction_default_and_flat_alias():
    """Defaults to ''; flat key maps into the nested schema and round-trips.

    Only GenerativeReranker reads this field — see search/neural_reranker.py.
    """
    assert RerankerConfig().instruction == ""

    config = SearchConfig.from_dict({"reranker_instruction": "custom instruction"})
    assert config.reranker.instruction == "custom instruction"

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.reranker.instruction == "custom instruction"


def test_reranker_instruction_env_override(tmp_path):
    """CLAUDE_RERANKER_INSTRUCTION must override the nested config value."""
    from search.config import SearchConfigManager

    config_file = tmp_path / "search_config.json"
    config_file.write_text(json.dumps({"reranker": {"instruction": ""}}))

    with patch.dict(os.environ, {"CLAUDE_RERANKER_INSTRUCTION": "env instruction"}):
        manager = SearchConfigManager(config_file=str(config_file))
        config = manager.load_config()

    assert config.reranker.instruction == "env instruction"


def test_reranker_doc_max_chars_default_and_flat_alias():
    """Defaults to 4000 (GenerativeReranker's pointwise budget); flat key round-trips."""
    assert RerankerConfig().doc_max_chars == 4000

    config = SearchConfig.from_dict({"reranker_doc_max_chars": 2500})
    assert config.reranker.doc_max_chars == 2500

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.reranker.doc_max_chars == 2500


def test_reranker_listwise_doc_max_chars_default_and_flat_alias():
    """Defaults to 1000 (JinaRerankerV3's shared-context budget); flat key round-trips."""
    assert RerankerConfig().listwise_doc_max_chars == 1000

    config = SearchConfig.from_dict({"reranker_listwise_doc_max_chars": 500})
    assert config.reranker.listwise_doc_max_chars == 500

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.reranker.listwise_doc_max_chars == 500


def test_query_expansion_defaults():
    """QueryExpansionConfig defaults: opt-in, BM25-only, 2 concepts, 0.5 discount."""
    from search.config import QueryExpansionConfig

    cfg = QueryExpansionConfig()
    assert cfg.enabled is False
    assert cfg.variants_path == ""
    assert cfg.max_variants == 2
    assert cfg.variant_weight_discount == 0.5
    assert cfg.apply_to_bm25 is True
    assert cfg.apply_to_dense is False


def test_query_expansion_flat_aliases_and_roundtrip():
    """Flat keys map into the nested query_expansion sub-config and round-trip."""
    config = SearchConfig.from_dict(
        {
            "query_expansion_enabled": True,
            "query_expansion_max_variants": 3,
            "query_expansion_weight_discount": 0.25,
            "query_expansion_apply_to_dense": True,
        }
    )
    assert config.query_expansion.enabled is True
    assert config.query_expansion.max_variants == 3
    assert config.query_expansion.variant_weight_discount == 0.25
    assert config.query_expansion.apply_to_dense is True

    restored = SearchConfig.from_dict(config.to_dict())
    assert restored.query_expansion.enabled is True
    assert restored.query_expansion.max_variants == 3
    assert restored.query_expansion.variant_weight_discount == 0.25
    assert restored.query_expansion.apply_to_dense is True


def test_query_expansion_in_to_dict():
    """to_dict() serializes the query_expansion sub-config automatically."""
    config_dict = SearchConfig().to_dict()
    assert "query_expansion" in config_dict
    assert config_dict["query_expansion"]["enabled"] is False


def test_reranker_doc_max_chars_env_override(tmp_path):
    """CLAUDE_RERANKER_DOC_MAX_CHARS must override the nested config value."""
    from search.config import SearchConfigManager

    config_file = tmp_path / "search_config.json"
    config_file.write_text(json.dumps({"reranker": {"doc_max_chars": 4000}}))

    with patch.dict(os.environ, {"CLAUDE_RERANKER_DOC_MAX_CHARS": "3000"}):
        manager = SearchConfigManager(config_file=str(config_file))
        config = manager.load_config()

    assert config.reranker.doc_max_chars == 3000


def test_reranker_listwise_doc_max_chars_env_override(tmp_path):
    """CLAUDE_RERANKER_LISTWISE_DOC_MAX_CHARS must override the nested config value."""
    from search.config import SearchConfigManager

    config_file = tmp_path / "search_config.json"
    config_file.write_text(json.dumps({"reranker": {"listwise_doc_max_chars": 1000}}))

    with patch.dict(os.environ, {"CLAUDE_RERANKER_LISTWISE_DOC_MAX_CHARS": "750"}):
        manager = SearchConfigManager(config_file=str(config_file))
        config = manager.load_config()

    assert config.reranker.listwise_doc_max_chars == 750


# ---------------------------------------------------------------------------
# Per-project overrides layer (ADR-0014): search_overrides.json in the active
# project's storage dir is deep-merged over the global file; env still wins.
# ---------------------------------------------------------------------------


def _write_overrides(storage_dir, overrides, **extra):
    """Write a search_overrides.json into *storage_dir* and return its path."""
    from search.config import PROJECT_OVERRIDES_FILENAME

    storage_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "probe_version": "1",
        "generated_at": "2026-07-29T00:00:00",
        "overrides": overrides,
        "reasons": {},
        "observations": [],
    }
    payload.update(extra)
    path = storage_dir / PROJECT_OVERRIDES_FILENAME
    path.write_text(json.dumps(payload))
    return path


class TestProjectOverrides:
    """search_overrides.json merge layer in SearchConfigManager.load_config."""

    def _manager(self, tmp_path, global_config=None):
        config_file = tmp_path / "search_config.json"
        config_file.write_text(json.dumps(global_config or {}))
        from search.config import SearchConfigManager

        return SearchConfigManager(config_file=str(config_file))

    def test_no_active_project_is_baseline(self, tmp_path, monkeypatch):
        """With no active project dir, load_config behaves exactly as before."""
        import search.config as config_module

        monkeypatch.setattr(config_module, "_active_project_storage_dir", None)
        manager = self._manager(tmp_path, {"performance": {"max_chunking_workers": 8}})
        config = manager.load_config()

        assert config.performance.max_chunking_workers == 8
        assert manager.get_active_overrides_meta() is None

    def test_overrides_merge_over_global_file(self, tmp_path, monkeypatch):
        import search.config as config_module

        storage = tmp_path / "project_storage"
        _write_overrides(
            storage,
            {
                "performance": {"max_chunking_workers": 12},
                "reranker": {"batch_size": 8},
            },
        )
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        manager = self._manager(tmp_path, {"performance": {"max_chunking_workers": 8}})
        config = manager.load_config()

        assert config.performance.max_chunking_workers == 12
        assert config.reranker.batch_size == 8
        # Untouched sibling fields keep their global/default values
        assert config.performance.use_parallel_search is True

    def test_env_wins_over_project_overrides(self, tmp_path, monkeypatch):
        """Precedence: env > per-project overrides > global file > defaults."""
        import search.config as config_module

        storage = tmp_path / "project_storage"
        _write_overrides(storage, {"performance": {"max_chunking_workers": 12}})
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        with patch.dict(os.environ, {"CLAUDE_MAX_CHUNKING_WORKERS": "3"}):
            config = self._manager(tmp_path).load_config()

        assert config.performance.max_chunking_workers == 3

    def test_overrides_meta_provenance(self, tmp_path, monkeypatch):
        import search.config as config_module

        storage = tmp_path / "project_storage"
        path = _write_overrides(
            storage,
            {
                "performance": {"max_chunking_workers": 12},
                "reranker": {"batch_size": 8},
            },
        )
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        meta = self._manager(tmp_path).get_active_overrides_meta()

        assert meta is not None
        assert meta["path"] == str(path)
        assert meta["probe_version"] == "1"
        assert meta["generated_at"] == "2026-07-29T00:00:00"
        assert meta["keys"] == [
            "performance.max_chunking_workers",
            "reranker.batch_size",
        ]

    def test_hand_edit_hot_reloads_without_new_manager(self, tmp_path, monkeypatch):
        import search.config as config_module

        storage = tmp_path / "project_storage"
        path = _write_overrides(storage, {"performance": {"max_chunking_workers": 12}})
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        manager = self._manager(tmp_path)
        assert manager.load_config().performance.max_chunking_workers == 12

        _write_overrides(storage, {"performance": {"max_chunking_workers": 6}})
        # Force a distinct mtime — same-second writes can otherwise collide.
        os.utime(path, (os.path.getmtime(path) + 10, os.path.getmtime(path) + 10))

        assert manager.load_config().performance.max_chunking_workers == 6

    def test_project_switch_invalidates_cache(self, tmp_path, monkeypatch):
        """Changing the active storage dir applies the new project's overrides."""
        import search.config as config_module

        storage_a = tmp_path / "project_a"
        storage_b = tmp_path / "project_b"
        _write_overrides(storage_a, {"performance": {"max_chunking_workers": 12}})
        _write_overrides(storage_b, {"performance": {"max_chunking_workers": 2}})

        monkeypatch.setattr(
            config_module, "_active_project_storage_dir", str(storage_a)
        )
        manager = self._manager(tmp_path)
        assert manager.load_config().performance.max_chunking_workers == 12

        config_module.set_active_project_storage_dir(storage_b)
        assert manager.load_config().performance.max_chunking_workers == 2

        # Detaching drops the layer entirely (back to global/defaults).
        config_module.set_active_project_storage_dir(None)
        assert manager.load_config().performance.max_chunking_workers != 2

    def test_env_escape_hatch_disables_layer(self, tmp_path, monkeypatch):
        import search.config as config_module

        storage = tmp_path / "project_storage"
        _write_overrides(storage, {"performance": {"max_chunking_workers": 12}})
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        with patch.dict(os.environ, {"CLAUDE_DISABLE_PROJECT_OVERRIDES": "1"}):
            manager = self._manager(tmp_path)
            config = manager.load_config()
            meta = manager.get_active_overrides_meta()

        assert config.performance.max_chunking_workers == 4  # dataclass default
        assert meta is None

    def test_global_flag_escape_hatch_and_no_self_enable(self, tmp_path, monkeypatch):
        """performance.enable_project_overrides=false in the GLOBAL file disables
        the layer, and the overrides file cannot re-enable itself."""
        import search.config as config_module

        storage = tmp_path / "project_storage"
        _write_overrides(
            storage,
            {
                "performance": {
                    "max_chunking_workers": 12,
                    "enable_project_overrides": True,
                }
            },
        )
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        manager = self._manager(
            tmp_path, {"performance": {"enable_project_overrides": False}}
        )

        assert manager.load_config().performance.max_chunking_workers == 4
        assert manager.get_active_overrides_meta() is None

    def test_malformed_overrides_file_recovered(self, tmp_path, monkeypatch):
        """Malformed overrides JSON: warn + skip the layer, global config loads."""
        import search.config as config_module
        from search.config import PROJECT_OVERRIDES_FILENAME

        storage = tmp_path / "project_storage"
        storage.mkdir()
        (storage / PROJECT_OVERRIDES_FILENAME).write_text("{not valid json")
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        manager = self._manager(tmp_path, {"performance": {"max_chunking_workers": 8}})

        assert manager.load_config().performance.max_chunking_workers == 8
        assert manager.get_active_overrides_meta() is None

    def test_overrides_wrong_type_recovered(self, tmp_path, monkeypatch):
        """'overrides' being a non-object skips the layer instead of crashing."""
        import search.config as config_module
        from search.config import PROJECT_OVERRIDES_FILENAME

        storage = tmp_path / "project_storage"
        storage.mkdir()
        (storage / PROJECT_OVERRIDES_FILENAME).write_text(
            json.dumps({"probe_version": "1", "overrides": ["not", "a", "dict"]})
        )
        monkeypatch.setattr(config_module, "_active_project_storage_dir", str(storage))

        manager = self._manager(tmp_path)
        manager.load_config()

        assert manager.get_active_overrides_meta() is None

    def test_dotted_keys_flattening(self):
        from search.config import _dotted_keys

        assert _dotted_keys(
            {
                "performance": {"max_chunking_workers": 12, "enable_fp16": True},
                "output": {},
            }
        ) == [
            "output",
            "performance.enable_fp16",
            "performance.max_chunking_workers",
        ]


# ---------------------------------------------------------------------------
# search_config.json.example must cover the full dataclass field surface --
# commit 84046622 claimed this but nothing enforced it, which is exactly how
# the missing performance.enable_project_overrides key went unnoticed.
# ---------------------------------------------------------------------------


def test_example_config_covers_full_dataclass_surface():
    """Every SearchConfig sub-config field must appear in search_config.json.example.

    Guards against the .example template silently drifting behind the
    dataclasses it's meant to document -- the same class of gap that let
    'performance.enable_project_overrides' go missing from the shipped
    template despite being a real, load-bearing field.
    """
    import dataclasses
    import json

    from search.config import SearchConfig
    from search.config_paths import _REPO_ROOT

    example_path = _REPO_ROOT / "search_config.json.example"
    assert example_path.exists(), f"missing {example_path}"

    example = json.loads(example_path.read_text())

    # Every declared sub-config must have a top-level section in the example.
    assert set(SearchConfig._SUBCONFIG_FIELDS) == set(example.keys()), (
        "search_config.json.example top-level sections don't match "
        "SearchConfig._SUBCONFIG_FIELDS"
    )

    for section_name in SearchConfig._SUBCONFIG_FIELDS:
        subconfig_type = SearchConfig._SUBCONFIG_TYPES[section_name]
        field_names = {f.name for f in dataclasses.fields(subconfig_type)}
        example_keys = set(example[section_name].keys())

        missing = field_names - example_keys
        assert not missing, (
            f"search_config.json.example['{section_name}'] is missing fields "
            f"present on {subconfig_type.__name__}: {sorted(missing)}"
        )
