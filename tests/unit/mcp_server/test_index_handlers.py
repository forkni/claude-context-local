"""Unit tests for index_handlers — file accessibility + pre-clear path guard."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCheckFileAccessibility:
    """Test _check_file_accessibility() function for pre-index file checks."""

    def test_all_files_accessible(self, tmp_path):
        """Test when all sampled files are accessible."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        # Create test files
        files = [tmp_path / f"file{i}.py" for i in range(5)]
        for f in files:
            f.write_text("pass")

        inaccessible = _check_file_accessibility(files, sample_size=5)

        assert len(inaccessible) == 0

    def test_empty_file_list(self):
        """Test with empty file list."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        inaccessible = _check_file_accessibility([], sample_size=10)

        assert inaccessible == []

    def test_permission_error_detected(self, tmp_path):
        """Test that PermissionError files are detected."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        test_file = tmp_path / "locked.py"
        test_file.write_text("pass")

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            inaccessible = _check_file_accessibility([test_file], sample_size=1)

        assert len(inaccessible) == 1
        assert test_file in inaccessible

    def test_io_error_detected(self, tmp_path):
        """Test that IOError files are detected."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        test_file = tmp_path / "broken.py"
        test_file.write_text("pass")

        with patch("builtins.open", side_effect=OSError("Read error")):
            inaccessible = _check_file_accessibility([test_file], sample_size=1)

        assert len(inaccessible) == 1

    def test_sample_size_limits_checks(self, tmp_path):
        """Test that only sample_size files are checked."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        # Create 100 test files
        files = [tmp_path / f"file{i}.py" for i in range(100)]
        for f in files:
            f.write_text("pass")

        # Track how many files are opened
        original_open = open
        open_count = [0]

        def counting_open(*args, **kwargs):
            open_count[0] += 1
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=counting_open):
            _check_file_accessibility(files, sample_size=10)


# ---------------------------------------------------------------------------
# _purge_index_dir — path-safety assertion
#
# This guard used to live only on _clear_index_files_before_create, a helper
# that had zero production callers (its sole call site was removed as
# collateral damage in an unrelated multi-model-routing refactor) and so
# never actually protected anything. It has been migrated down to
# _purge_index_dir itself — the real destructive path (shutil.rmtree of
# bm25/, unlink of a parent-directory glob) — which had no path-containment
# guard at all until now.
# ---------------------------------------------------------------------------


class TestPurgeIndexDirStorageRootGuard:
    """Verify the storage-root assertion in _purge_index_dir."""

    def test_path_inside_storage_accepted(self, tmp_path: Path) -> None:
        from mcp_server.tools.index_handlers import _purge_index_dir

        index_dir = tmp_path / "storage" / "projects" / "proj_abc_bge_512d" / "index"
        index_dir.mkdir(parents=True)

        # Patch the name as bound in index_handlers' own namespace (module-level
        # `from mcp_server.storage_manager import get_storage_dir`), not the
        # origin module — the local binding is what _purge_index_dir calls.
        with patch(
            "mcp_server.tools.index_handlers.get_storage_dir",
            return_value=tmp_path / "storage",
        ):
            _purge_index_dir(index_dir, keep_chunk_cache=True)

    def test_path_outside_storage_raises(self, tmp_path: Path) -> None:
        from mcp_server.tools.index_handlers import _purge_index_dir

        storage = tmp_path / "storage"
        storage.mkdir()
        bogus = tmp_path / "some_other_directory" / "index"
        bogus.mkdir(parents=True)

        with (
            patch(
                "mcp_server.tools.index_handlers.get_storage_dir",
                return_value=storage,
            ),
            pytest.raises(ValueError, match="_purge_index_dir refused"),
        ):
            _purge_index_dir(bogus, keep_chunk_cache=True)


class TestRunIndexingSuccessPropagation:
    """A caught indexing exception (or a zero-chunk full reindex) must surface
    as a hard failure instead of being reported as success — the exact
    "half-purged index, reported OK" defect this guards against.
    """

    @staticmethod
    def _fake_result(**overrides):
        result = MagicMock()
        result.files_added = 0
        result.files_modified = 0
        result.files_removed = 0
        result.chunks_added = 0
        result.success = True
        result.error = None
        for key, value in overrides.items():
            setattr(result, key, value)
        return result

    def test_run_indexing_propagates_success_and_error_fields(self, tmp_path):
        """_run_indexing must carry result.success/result.error into its dict
        (as indexing_succeeded/indexing_error — see the note at the call site
        on why these aren't literally named success/error), not just the
        counts (the original defect: they were dropped on the floor).
        """
        from mcp_server.tools.index_handlers import _run_indexing

        fake_indexer = MagicMock()
        fake_indexer.incremental_index.return_value = self._fake_result(
            success=False, error="PermissionError: [WinError 32]"
        )

        with patch(
            "mcp_server.tools.index_handlers.IncrementalIndexer",
            return_value=fake_indexer,
        ):
            result = _run_indexing(
                indexer=MagicMock(),
                embedder=MagicMock(),
                chunker=MagicMock(),
                directory_path=str(tmp_path),
                incremental=False,
            )

        assert result["indexing_succeeded"] is False
        assert result["indexing_error"] == "PermissionError: [WinError 32]"

    def test_build_index_response_reports_failure_on_caught_exception(self):
        """_build_index_response turns a caught-exception result into a hard
        failure response instead of the previous unconditional success=True."""
        from mcp_server.tools.index_handlers import _build_index_response

        r = {
            "files_added": 0,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 0,
            "time_taken": 0.52,
            "indexing_succeeded": False,
            "indexing_error": "PermissionError: [WinError 32]",
        }

        response = _build_index_response([r], "/some/project", incremental=False)

        assert "error" in response
        assert "PermissionError" in response["error"]
        assert response.get("success") is not True

    def test_build_index_response_reports_failure_on_zero_chunk_full_reindex(self):
        """A full (non-incremental) reindex that added 0 chunks is never a
        legitimate outcome and must be reported as a hard failure even when
        no exception was raised (success=True but chunks_added=0)."""
        from mcp_server.tools.index_handlers import _build_index_response

        r = {
            "files_added": 0,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 0,
            "time_taken": 0.52,
            "indexing_succeeded": True,
            "indexing_error": None,
        }

        response = _build_index_response([r], "/some/project", incremental=False)

        assert "error" in response
        assert response.get("success") is not True

    def test_build_index_response_incremental_zero_chunks_stays_success(self):
        """An incremental run legitimately adds 0 chunks when nothing changed —
        that must stay a success (only a *full* reindex with 0 chunks is
        suspicious)."""
        from mcp_server.tools.index_handlers import _build_index_response

        r = {
            "files_added": 0,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 0,
            "time_taken": 0.05,
            "indexing_succeeded": True,
            "indexing_error": None,
        }

        response = _build_index_response([r], "/some/project", incremental=True)

        assert response.get("success") is True
        assert "error" not in response

    def test_build_index_response_surfaces_effective_filters(self):
        """include_dirs/exclude_dirs passed through are surfaced in the
        response so an unexpected corpus size is visible without re-deriving
        which filter was actually used."""
        from mcp_server.tools.index_handlers import _build_index_response

        r = {
            "files_added": 5,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 42,
            "time_taken": 1.0,
            "indexing_succeeded": True,
            "indexing_error": None,
        }

        response = _build_index_response(
            [r],
            "/some/project",
            incremental=False,
            include_dirs=None,
            exclude_dirs=["_archive", "tests"],
        )

        assert response.get("success") is True
        assert response.get("exclude_dirs") == ["_archive", "tests"]
        assert response.get("include_dirs") is None

    def test_build_index_response_surfaces_probe_summary(self):
        """A probed full reindex threads the pass-1/pass-2 probe summary
        through to the MCP response so the caller can see what was
        auto-tuned without opening search_overrides.json."""
        from mcp_server.tools.index_handlers import _build_index_response

        probe_summary = {
            "stage": "pre_chunking",
            "probe_version": "1",
            "override_keys": ["embedding.batch_size"],
            "reasons": {"embedding.batch_size": "vram_total_gb=24.0 -> 256"},
            "observation_keys": [],
        }
        r = {
            "files_added": 5,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 42,
            "time_taken": 1.0,
            "indexing_succeeded": True,
            "indexing_error": None,
            "probe_summary": probe_summary,
        }

        response = _build_index_response([r], "/some/project", incremental=False)

        assert response.get("success") is True
        assert response.get("probe_summary") == probe_summary

    def test_build_index_response_omits_probe_summary_when_absent(self):
        """Incremental runs (and probe-disabled runs) carry no probe_summary —
        responses.ok drops the None so the field never appears at all."""
        from mcp_server.tools.index_handlers import _build_index_response

        r = {
            "files_added": 0,
            "files_modified": 0,
            "files_removed": 0,
            "chunks_added": 0,
            "time_taken": 0.05,
            "indexing_succeeded": True,
            "indexing_error": None,
            "probe_summary": None,
        }

        response = _build_index_response([r], "/some/project", incremental=True)

        assert response.get("success") is True
        assert "probe_summary" not in response


class TestPurgeIndexDirFailureReporting:
    """_purge_index_dir must report undeletable files via its return value,
    not only a log warning — callers (handle_clear_index) need this to be
    able to turn a partial purge into a hard failure response.
    """

    def test_undeletable_file_reported_in_failed(self, tmp_path):
        from mcp_server.storage_manager import get_storage_dir
        from mcp_server.tools.index_handlers import _purge_index_dir

        # _purge_index_dir now asserts index_dir is under the storage root
        # (a guard migrated in from the dead _clear_index_files_before_create),
        # so build under the session-redirected storage dir rather than a raw
        # tmp_path sibling of it.
        index_dir = get_storage_dir() / "projects" / "proj_test" / "index"
        index_dir.mkdir(parents=True)
        (index_dir / "code.index").write_text("data")
        (index_dir / "chunk_ids.pkl").write_text("data")

        original_unlink = Path.unlink

        def _flaky_unlink(self, *args, **kwargs):
            if self.name == "code.index":
                raise OSError("file in use by another process")
            return original_unlink(self, *args, **kwargs)

        with patch.object(Path, "unlink", _flaky_unlink):
            deleted, failed = _purge_index_dir(index_dir, keep_chunk_cache=True)

        assert "code.index" in failed
        assert "chunk_ids.pkl" in deleted
        assert "code.index" not in deleted

    def test_all_files_deletable_reports_empty_failed(self, tmp_path):
        from mcp_server.storage_manager import get_storage_dir
        from mcp_server.tools.index_handlers import _purge_index_dir

        index_dir = get_storage_dir() / "projects" / "proj_test2" / "index"
        index_dir.mkdir(parents=True)
        (index_dir / "code.index").write_text("data")

        deleted, failed = _purge_index_dir(index_dir, keep_chunk_cache=True)

        assert failed == []
        assert "code.index" in deleted


class TestReleaseGpuMemory:
    """Direct tests for _release_gpu_memory module-level helper."""

    def test_calls_gc_collect(self):
        """gc.collect() is always called regardless of CUDA availability."""
        from mcp_server.tools.index_handlers import _release_gpu_memory

        with patch("search.gpu_monitor.gc") as mock_gc:
            with patch("search.gpu_monitor.torch") as mock_torch:
                mock_torch.cuda.is_available.return_value = False
                _release_gpu_memory()
            mock_gc.collect.assert_called_once()

    def test_no_error_when_torch_unavailable(self):
        """Survives gracefully when torch is not installed (ImportError)."""
        from mcp_server.tools.index_handlers import _release_gpu_memory

        with patch("search.gpu_monitor.torch", None):
            _release_gpu_memory()  # Must not raise


class TestSwitchActiveModel:
    """Direct tests for _switch_active_model module-level helper."""

    def _make_config(self):
        cfg = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        cfg.embedding.model_name = "old-model"
        cfg.embedding.dimension = 768
        return cfg

    def test_saves_config_when_model_changes(self):
        """Config is saved to disk when the model name differs from current."""
        from unittest.mock import MagicMock, patch

        from mcp_server.tools.index_handlers import _switch_active_model

        mock_cfg = self._make_config()
        mock_mgr = MagicMock()
        mock_mgr.load_config.return_value = mock_cfg

        with (
            patch(
                "mcp_server.tools.index_handlers.SearchConfigManager",
                return_value=mock_mgr,
            ),
            patch(
                "mcp_server.tools.index_handlers.MODEL_REGISTRY",
                {"new-model": {"dimension": 512}},
            ),
            patch("mcp_server.tools.index_handlers.get_state"),
            patch("mcp_server.tools.index_handlers._invalidate_config_caches"),
        ):
            _switch_active_model("new-model")

        mock_mgr.save_config.assert_called_once()

    def test_invalidates_caches(self):
        """Cache invalidation helper is called after config update."""
        from unittest.mock import MagicMock, patch

        from mcp_server.tools.index_handlers import _switch_active_model

        mock_cfg = self._make_config()
        mock_mgr = MagicMock()
        mock_mgr.load_config.return_value = mock_cfg

        with (
            patch(
                "mcp_server.tools.index_handlers.SearchConfigManager",
                return_value=mock_mgr,
            ),
            patch("mcp_server.tools.index_handlers.MODEL_REGISTRY", {}),
            patch("mcp_server.tools.index_handlers.get_state"),
            patch(
                "mcp_server.tools.index_handlers._invalidate_config_caches"
            ) as mock_inv,
        ):
            _switch_active_model("old-model")

        mock_inv.assert_called_once()


class TestHandlerChunkerOwnership:
    """Both handler sites must build their chunker via MultiLanguageChunker.for_project.

    These tests lock in the import-classification fix so it cannot silently regress
    (someone replacing .for_project(...) with the bare constructor would drop
    relation_filter and re-introduce the "unknown" import-category bug).
    """

    def test_handle_index_directory_uses_for_project(self, tmp_path: Path) -> None:
        """handle_index_directory builds its chunker via MultiLanguageChunker.for_project."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with (
            patch(
                "mcp_server.tools.index_handlers.MultiLanguageChunker"
            ) as mock_chunker_cls,
            # _cleanup_previous_resources is a lazy in-function import; patch at source
            patch("mcp_server.resource_manager._cleanup_previous_resources"),
            patch("mcp_server.tools.index_handlers.get_state") as mock_state,
            patch("mcp_server.tools.index_handlers.get_config") as mock_cfg,
            patch(
                "mcp_server.tools.index_handlers.get_canonical_project_info",
                return_value=None,
            ),
            patch(
                "mcp_server.tools.index_handlers.get_project_storage_dir"
            ) as mock_psd,
            patch("mcp_server.tools.index_handlers.set_current_project"),
            patch("mcp_server.tools.index_handlers.temporary_ram_fallback_off"),
            patch(
                "mcp_server.tools.index_handlers._build_index_response", return_value={}
            ),
            # update_project_filters calls storage_manager's own get_project_storage_dir
            # (unpatched module-level reference) — mock it to prevent real-storage writes.
            patch("mcp_server.tools.index_handlers.update_project_filters"),
            # asyncio.to_thread runs _setup_and_run in a worker thread; that closure calls
            # get_embedder / get_searcher (real implementations) which trigger model loading
            # and create real project dirs.  Short-circuit the whole thread since this test
            # only verifies the chunker call-site ABOVE the to_thread dispatch.
            patch(
                "asyncio.to_thread",
                AsyncMock(
                    return_value={
                        "files_added": 0,
                        "files_modified": 0,
                        "files_removed": 0,
                        "chunks_added": 0,
                        "time_taken": 0.0,
                    }
                ),
            ),
            # TreeSitterChunker is used in the accessibility pre-check (lazy import)
            patch(
                "chunking.tree_sitter.TreeSitterChunker.get_supported_extensions",
                return_value=[],
            ),
        ):
            # Wire enough state for the handler to reach the chunker line
            mock_cfg.return_value.performance.enable_entity_tracking = False
            mock_cfg.return_value.search_mode.enable_hybrid = False
            lock_mock = AsyncMock()
            lock_mock.__aenter__ = AsyncMock(return_value=None)
            lock_mock.__aexit__ = AsyncMock(return_value=None)
            mock_state.return_value.get_reindex_rwlock.return_value.write.return_value = lock_mock
            proj_dir = tmp_path / "storage" / "proj"
            proj_dir.mkdir(parents=True)
            index_dir = proj_dir / "index"
            index_dir.mkdir()
            mock_psd.return_value = proj_dir
            mock_chunker_cls.for_project.return_value = MagicMock()

            from mcp_server.tools.index_handlers import handle_index_directory

            asyncio.run(handle_index_directory({"directory_path": str(project_dir)}))

        mock_chunker_cls.for_project.assert_called_once()
        # The bare constructor must NOT be called (that would be the regression)
        mock_chunker_cls.assert_not_called()

    def test_check_auto_reindex_uses_for_project(self, tmp_path: Path) -> None:
        """_check_auto_reindex builds its chunker via MultiLanguageChunker.for_project."""
        from unittest.mock import MagicMock, patch

        project_path = str(tmp_path / "myproject")
        Path(project_path).mkdir()

        with (
            patch(
                "mcp_server.tools.search_handlers.MultiLanguageChunker"
            ) as mock_chunker_cls,
            patch(
                "mcp_server.tools.search_handlers.get_project_storage_dir"
            ) as mock_psd,
            patch("mcp_server.tools.search_handlers.get_config") as mock_cfg,
            patch("mcp_server.tools.search_handlers.get_embedder") as mock_emb,
            patch("mcp_server.tools.search_handlers.get_index_manager"),
            patch("mcp_server.tools.search_handlers.IncrementalIndexer") as mock_ii,
            patch("mcp_server.tools.search_handlers.temporary_ram_fallback_off"),
            # validate_embedder_index_compatibility is a lazy in-function import
            patch("search.dimension_validator.validate_embedder_index_compatibility"),
            # SnapshotManager and ChangeDetector are lazy in-function imports
            patch("merkle.snapshot_manager.SnapshotManager") as mock_snap_cls,
            patch("merkle.change_detector.ChangeDetector"),
            patch(
                "chunking.tree_sitter.TreeSitterChunker.get_supported_extensions",
                return_value=[],
            ),
        ):
            storage = tmp_path / "storage"
            storage.mkdir()
            mock_psd.return_value = storage
            (storage / "project_info.json").write_text("{}")

            snap_mock = MagicMock()
            snap_mock.has_snapshot.return_value = False
            mock_snap_cls.return_value = snap_mock

            cfg = MagicMock()
            cfg.search_mode.enable_hybrid = False
            cfg.performance.enable_entity_tracking = False
            mock_cfg.return_value = cfg

            mock_emb.return_value = MagicMock()
            mock_chunker_cls.for_project.return_value = MagicMock()
            ii_inst = MagicMock()
            ii_result = MagicMock()
            ii_result.files_modified = 0
            ii_result.files_added = 0
            ii_inst.auto_reindex_if_needed.return_value = ii_result
            mock_ii.return_value = ii_inst

            from mcp_server.tools.search_handlers import _check_auto_reindex

            _check_auto_reindex(project_path, max_age_minutes=60)

        mock_chunker_cls.for_project.assert_called_once()
        mock_chunker_cls.assert_not_called()


class TestIndexDirectoryAsyncJob:
    """P2-A: index_directory(wait=False) launches a background job and returns
    a job_id immediately instead of blocking for the full indexing run.
    """

    async def test_wait_true_default_still_returns_inline_result(self, tmp_path):
        """wait defaults to True: behavior is unchanged (no job_id, inline result)."""
        from mcp_server.tools import index_handlers

        async def _fake_run(_arguments):
            return {"success": True, "files_added": 1}

        with patch.object(index_handlers, "_run_index_directory", _fake_run):
            result = await index_handlers.handle_index_directory(
                {"directory_path": str(tmp_path)}
            )

        assert result == {"success": True, "files_added": 1}
        assert "job_id" not in result

    async def test_wait_false_returns_job_id_immediately_then_completes(self, tmp_path):
        from mcp_server.tools import index_handlers
        from mcp_server.tools.job_registry import (
            JobRegistry,
            get_job_registry,
        )

        captured_tasks = []
        original_track = JobRegistry.track_background_task

        def _capture(self, task):
            captured_tasks.append(task)
            return original_track(self, task)

        async def _fake_run(_arguments):
            return {"success": True, "files_added": 1}

        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        with (
            patch.object(index_handlers, "_run_index_directory", _fake_run),
            patch.object(JobRegistry, "track_background_task", _capture),
        ):
            result = await index_handlers.handle_index_directory(
                {"directory_path": str(project_dir), "wait": False}
            )

            assert result["success"] is True
            assert result["status"] == "running"
            assert "job_id" in result

            # Await the background task while the patches are still active —
            # the task's coroutine looks up `_run_index_directory` as a module
            # global at *call* time, so it must run before the patch unwinds.
            assert captured_tasks, "background task was never tracked"
            await captured_tasks[0]

        job = await get_job_registry().get(result["job_id"])
        assert job is not None
        assert job.status == "done"
        assert job.result == {"success": True, "files_added": 1}

    async def test_wait_false_job_marks_error_on_exception(self, tmp_path):
        from mcp_server.tools import index_handlers
        from mcp_server.tools.job_registry import (
            JobRegistry,
            get_job_registry,
        )

        captured_tasks = []
        original_track = JobRegistry.track_background_task

        def _capture(self, task):
            captured_tasks.append(task)
            return original_track(self, task)

        async def _fake_run(_arguments):
            raise RuntimeError("disk full")

        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        with (
            patch.object(index_handlers, "_run_index_directory", _fake_run),
            patch.object(JobRegistry, "track_background_task", _capture),
        ):
            result = await index_handlers.handle_index_directory(
                {"directory_path": str(project_dir), "wait": False}
            )
            await captured_tasks[0]

        job = await get_job_registry().get(result["job_id"])
        assert job.status == "error"
        assert "disk full" in job.error

    async def test_wait_false_job_marks_error_on_error_response(self, tmp_path):
        """A non-raising error dict (responses.error(...)) also lands as job error."""
        from mcp_server.tools import index_handlers
        from mcp_server.tools.job_registry import (
            JobRegistry,
            get_job_registry,
        )

        captured_tasks = []
        original_track = JobRegistry.track_background_task

        def _capture(self, task):
            captured_tasks.append(task)
            return original_track(self, task)

        async def _fake_run(_arguments):
            return {"error": "Directory does not exist: /nope"}

        project_dir = tmp_path / "proj"
        project_dir.mkdir()

        with (
            patch.object(index_handlers, "_run_index_directory", _fake_run),
            patch.object(JobRegistry, "track_background_task", _capture),
        ):
            result = await index_handlers.handle_index_directory(
                {"directory_path": str(project_dir), "wait": False}
            )
            await captured_tasks[0]

        job = await get_job_registry().get(result["job_id"])
        assert job.status == "error"
        assert job.error == "Directory does not exist: /nope"
