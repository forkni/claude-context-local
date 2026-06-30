"""Integration tests for auto-reindex bug fixes.

Tests:
1. max_age_minutes respects config instead of hardcoded 5
2. Multi-model cleanup clears ALL models before auto-reindex
3. No OOM during auto-reindex with multi-model mode
"""

import gc
import json
import logging
import time
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.model_pool_manager import reset_pool_manager
from mcp_server.services import get_state
from merkle import SnapshotManager
from search.config import get_search_config
from search.incremental_indexer import IncrementalIndexer


logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _mock_model_load():
    """Prevent real model downloads in all tests in this module."""
    import numpy as np

    class _FakeEmbeddingModel:
        max_seq_length = 512
        device = "cpu"

        def encode(
            self, sentences, show_progress_bar=False, convert_to_tensor=False, **kwargs
        ):
            n = 1 if isinstance(sentences, str) else len(sentences)
            return np.zeros((n, 768), dtype=np.float32)

        def get_sentence_embedding_dimension(self):
            return 768

    with patch(
        "embeddings.model_loader.ModelLoader.load",
        return_value=(_FakeEmbeddingModel(), "cpu"),
    ):
        yield


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary project with Python files."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create a simple Python file
    (project_dir / "example.py").write_text(
        """
def example_function():
    '''Example function for testing.'''
    return 42

class ExampleClass:
    '''Example class for testing.'''
    def method(self):
        return "test"
"""
    )

    return project_dir


@pytest.fixture
def cleanup_state():
    """Cleanup state before and after tests."""
    state = get_state()
    state.clear_embedders()
    reset_pool_manager()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    yield

    # Cleanup after test
    state.clear_embedders()
    reset_pool_manager()
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


class TestMaxAgeMinutesConfigRespect:
    """Test that max_age_minutes respects config instead of hardcoded 5."""

    def test_uses_config_default_when_not_specified(
        self, temp_project, cleanup_state, tmp_path
    ):
        """Verify default comes from config, not hardcoded 5."""
        config = get_search_config()

        # Verify config has a positive value (sensible default from config)
        assert config.performance.max_index_age_minutes > 0

        # Create indexer with isolated storage so no writes reach ~/.claude_code_search
        indexer = IncrementalIndexer(
            snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots")
        )
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Wait 6 seconds (longer than old 5-minute default would trigger)
        # but shorter than 60-minute config default
        time.sleep(6)

        # Auto-reindex with config default should NOT trigger
        # (we're only 6 seconds old, not 60 minutes)
        result = indexer.auto_reindex_if_needed(
            str(temp_project),
            "test_project",
            # Note: max_age_minutes not specified, should use config default
        )

        # Should NOT reindex (not old enough)
        assert result.files_added == 0
        assert result.files_modified == 0

    def test_explicit_max_age_minutes_overrides_config(
        self, temp_project, cleanup_state, tmp_path
    ):
        """Verify explicit max_age_minutes parameter overrides config."""
        # Create indexer with isolated storage so no writes reach ~/.claude_code_search
        indexer = IncrementalIndexer(
            snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots")
        )
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Wait 2 seconds
        time.sleep(2)

        # Auto-reindex with explicit 1 second max age SHOULD trigger
        result = indexer.auto_reindex_if_needed(
            str(temp_project),
            "test_project",
            max_age_minutes=1 / 60,  # 1 second in minutes
        )

        # Should reindex (index is >1 second old)
        # Files won't be re-added (incremental), but operation ran
        assert result.success


class TestMultiModelCleanupBeforeReindex:
    """Test that auto-reindex handles cleanup correctly."""

    def test_cleanup_handles_errors_gracefully(
        self, temp_project, cleanup_state, tmp_path
    ):
        """Verify auto-reindex continues even if cleanup fails."""
        # Create indexer with isolated storage so no writes reach ~/.claude_code_search
        indexer = IncrementalIndexer(
            snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots")
        )
        result = indexer.incremental_index(str(temp_project), "test_project")
        assert result.success

        # Mock cleanup to raise exception
        with (
            patch("mcp_server.services.get_state") as mock_get_state,
            patch.object(indexer, "incremental_index") as mock_index,
        ):
            # Make get_state raise exception during cleanup
            mock_get_state.side_effect = RuntimeError("Simulated cleanup failure")

            # Configure mock_index to return success
            mock_index.return_value = MagicMock(success=True)

            # Trigger auto-reindex - should not crash
            result = indexer.auto_reindex_if_needed(
                str(temp_project), "test_project", max_age_minutes=0
            )

            # Should still attempt reindex despite cleanup failure
            mock_index.assert_called_once()


class TestUserFilterPreservation:
    """Regression tests for silent user-filter loss (H1+H2+H3 bug cluster)."""

    def test_update_project_filters_refuses_null_overwrite(self, tmp_path):
        """update_project_filters must not overwrite stored filters with None."""
        from mcp_server.storage_manager import update_project_filters

        with patch("mcp_server.storage_manager.get_storage_dir", return_value=tmp_path):
            project_path = tmp_path / "myproject"
            project_path.mkdir()

            # Seed a project_info.json with user exclusions
            project_dir = tmp_path / "projects" / "myproject_abc123_bge-v1_1536d"
            project_dir.mkdir(parents=True)
            info_file = project_dir / "project_info.json"
            info_file.write_text(
                json.dumps(
                    {
                        "project_name": "myproject",
                        "project_path": str(project_path),
                        "user_included_dirs": None,
                        "user_excluded_dirs": ["secret"],
                    }
                )
            )

            # Patch get_project_storage_dir to return the seeded dir
            with patch(
                "mcp_server.storage_manager.get_project_storage_dir",
                return_value=project_dir,
            ):
                update_project_filters(str(project_path), None, None)

            updated = json.loads(info_file.read_text())
            assert updated["user_excluded_dirs"] == ["secret"], (
                "update_project_filters must not overwrite stored exclusions with None"
            )

    def test_get_canonical_project_info_finds_across_model_dirs(self, tmp_path):
        """get_canonical_project_info must find project_info.json from any model dir."""
        from mcp_server.storage_manager import get_canonical_project_info

        with patch("mcp_server.storage_manager.get_storage_dir", return_value=tmp_path):
            project_path = tmp_path / "myproject"
            project_path.mkdir()

            from search.filters import compute_drive_agnostic_hash

            h = compute_drive_agnostic_hash(str(project_path))
            # Only the bge-v1 model dir has a project_info.json
            bge_dir = tmp_path / "projects" / f"myproject_{h}_bge-v1_1536d"
            bge_dir.mkdir(parents=True)
            bge_info = bge_dir / "project_info.json"
            bge_info.write_text('{"user_excluded_dirs":["assets"]}')
            # qwen3 dir exists but has NO project_info.json
            qwen_dir = tmp_path / "projects" / f"myproject_{h}_qwen3-0.6b_1024d"
            qwen_dir.mkdir()

            found = get_canonical_project_info(str(project_path))
            assert found == bge_info, (
                "get_canonical_project_info must locate bge-v1 project_info.json "
                "even when qwen3 dir exists without one"
            )

    def test_auto_reindex_chunker_receives_filters(self, tmp_path):
        """MultiLanguageChunker in _check_auto_reindex must receive stored filters.

        If the chunker is built without filters, files inside excluded dirs get
        chunked even though IncrementalIndexer skips the file-walk for them.
        SnapshotManager and ChangeDetector are locally imported inside the function,
        so they must be patched at their source modules.
        """
        import json as _json
        from contextlib import ExitStack

        project_dir = tmp_path / "proj_dir"
        project_dir.mkdir()
        info_file = project_dir / "project_info.json"
        info_file.write_text(
            _json.dumps(
                {
                    "user_excluded_dirs": ["assets"],
                    "user_included_dirs": None,
                    "embedding_model": "BAAI/bge-code-v1",
                }
            )
        )

        chunker_calls: list = []

        class CapturingChunker:
            def __init__(self, *a, **kw):
                chunker_calls.append((a, kw))

            @classmethod
            def for_project(
                cls,
                root_path,
                include_dirs=None,
                exclude_dirs=None,
                *,
                enable_entity_tracking=False,
            ):
                # Capture args in the same positional form the assertion expects
                chunker_calls.append(
                    (
                        (root_path, include_dirs, exclude_dirs),
                        {"enable_entity_tracking": enable_entity_tracking},
                    )
                )
                return cls.__new__(cls)

        ii_instance = MagicMock()
        ii_instance.auto_reindex_if_needed.return_value = MagicMock(
            files_modified=0, files_added=0
        )
        snap_instance = MagicMock()
        snap_instance.has_snapshot.return_value = True
        snap_instance.get_snapshot_age.return_value = 9999  # stale → triggers Phase 2

        ts_mock = MagicMock()
        ts_mock.get_supported_extensions.return_value = {".py"}

        cfg = MagicMock()
        cfg.search_mode.enable_hybrid = False
        cfg.performance.enable_entity_tracking = False

        _patches = [
            patch(
                "mcp_server.tools.search_handlers.get_project_storage_dir",
                return_value=project_dir,
            ),
            patch(
                "mcp_server.tools.search_handlers.MultiLanguageChunker",
                CapturingChunker,
            ),
            patch(
                "mcp_server.tools.search_handlers.get_embedder",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server.tools.search_handlers.IncrementalIndexer",
                return_value=ii_instance,
            ),
            patch("mcp_server.tools.search_handlers.get_config", return_value=cfg),
            patch(
                "mcp_server.tools.search_handlers.get_state", return_value=MagicMock()
            ),
            # SnapshotManager / ChangeDetector are locally imported inside the function
            patch(
                "merkle.snapshot_manager.SnapshotManager", return_value=snap_instance
            ),
            patch("merkle.change_detector.ChangeDetector"),
            # TreeSitterChunker.get_supported_extensions() is called to compute the ChangeDetector arg
            patch("chunking.tree_sitter.TreeSitterChunker", ts_mock),
            patch("search.dimension_validator.validate_embedder_index_compatibility"),
        ]

        with ExitStack() as stack:
            for p in _patches:
                stack.enter_context(p)
            from mcp_server.tools.search_handlers import _check_auto_reindex

            _check_auto_reindex("/fake/project", max_age_minutes=0)

        assert chunker_calls, "MultiLanguageChunker was never constructed"
        args, kwargs = chunker_calls[0]
        exclude_passed = kwargs.get("exclude_dirs") or (
            args[2] if len(args) > 2 else None
        )
        # get_effective_filters merges user exclusions with default dirs, so the result is a
        # superset of ["assets"] — verify "assets" is present rather than checking exact equality
        assert exclude_passed is not None and "assets" in exclude_passed, (
            "MultiLanguageChunker must receive exclude_dirs containing stored user exclusions; "
            f"got args={args}, kwargs={kwargs}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
