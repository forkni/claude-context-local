"""Regression tests for the FILTER_SEMANTICS backfill bug.

Genesis: a legacy project's ``project_info.json`` — created before
``filter_semantics_version`` existed as a field — reads that field back as
``None``. The old ``semantics_stale`` check in
``mcp_server/tools/index_handlers.py`` required
``stored_filter_semantics_version is not None``, which *excluded* exactly
these legacy projects from the forced-full-reindex path meant to migrate
them: ``filters_changed`` stayed False, ``update_project_filters`` (the only
site that stamped the version) never ran, and
``check_filter_semantics_migration`` kept logging its ``[FILTER_SEMANTICS]``
warning on every single incremental run, forever, with no way to clear it.

Two independent fixes:

1. ``_is_filter_semantics_stale`` (extracted from the inline
   ``semantics_stale`` computation) now treats a missing stored version as
   ``0``, not as "exempt" — so a legacy project with dependency-tree include
   patterns correctly gets one forced full reindex.
2. The stamp itself moved from request time (``update_project_filters`` at
   the pre-reindex gate) to confirmation time
   (``stamp_filter_semantics_version``, called only after
   ``result["indexing_succeeded"]`` is True on a non-incremental run) — so a
   failed or still-incremental run can no longer permanently suppress the
   warning for an index that was never actually rebuilt under the new
   semantics.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from mcp_server.storage_manager import FILTER_SEMANTICS_VERSION
from mcp_server.tools.index_handlers import _is_filter_semantics_stale


class TestIsFilterSemanticsStale:
    def test_legacy_project_missing_version_field_is_stale(self, tmp_path: Path):
        """None (field never existed) must be treated as version 0 -- the
        exact bug: previously `is not None` excluded this case entirely."""
        assert (
            _is_filter_semantics_stale(
                None,
                False,
                ["venv/mypackage"],
                tmp_path,
            )
            is True
        )

    def test_current_version_is_not_stale(self, tmp_path: Path):
        assert (
            _is_filter_semantics_stale(
                FILTER_SEMANTICS_VERSION,
                False,
                ["venv/mypackage"],
                tmp_path,
            )
            is False
        )

    def test_old_version_without_dependency_pattern_is_not_stale(self, tmp_path: Path):
        """Scoped to the only group the migration actually affects -- a plain
        narrowing pattern is byte-identical under old and new semantics."""
        assert (
            _is_filter_semantics_stale(
                0,
                False,
                ["src/mypackage"],
                tmp_path,
            )
            is False
        )

    def test_old_version_with_include_exclusive_is_not_stale(self, tmp_path: Path):
        """include_exclusive=True is the explicit escape hatch back to
        whitelist-only (old) semantics -- must not be forced to migrate."""
        assert (
            _is_filter_semantics_stale(
                0,
                True,
                ["venv/mypackage"],
                tmp_path,
            )
            is False
        )

    def test_no_include_dirs_is_not_stale(self, tmp_path: Path):
        assert _is_filter_semantics_stale(None, False, None, tmp_path) is False


class TestStampFilterSemanticsVersion:
    def test_stamps_current_version_onto_existing_project_info(self, tmp_path: Path):
        from mcp_server.storage_manager import stamp_filter_semantics_version

        project_path = tmp_path / "myproject"
        project_path.mkdir()
        project_dir = tmp_path / "projects" / "myproject_abc123_bge-m3_1024d"
        project_dir.mkdir(parents=True)
        info_file = project_dir / "project_info.json"
        info_file.write_text(
            json.dumps({"project_name": "myproject", "filter_semantics_version": 0})
        )

        with patch(
            "mcp_server.storage_manager.get_project_storage_dir",
            return_value=project_dir,
        ):
            stamp_filter_semantics_version(str(project_path))

        updated = json.loads(info_file.read_text())
        assert updated["filter_semantics_version"] == FILTER_SEMANTICS_VERSION

    def test_noop_when_project_info_missing(self, tmp_path: Path):
        """Must not create project_info.json -- stamping only confirms an
        already-completed reindex, never originates project state."""
        from mcp_server.storage_manager import stamp_filter_semantics_version

        project_path = tmp_path / "myproject"
        project_path.mkdir()
        project_dir = tmp_path / "projects" / "myproject_abc123_bge-m3_1024d"
        project_dir.mkdir(parents=True)

        with patch(
            "mcp_server.storage_manager.get_project_storage_dir",
            return_value=project_dir,
        ):
            stamp_filter_semantics_version(str(project_path))

        assert not (project_dir / "project_info.json").exists()

    def test_silent_on_corrupt_json(self, tmp_path: Path):
        """Best-effort, matching update_project_filters's own failure mode --
        a project_info.json hiccup here must not raise."""
        from mcp_server.storage_manager import stamp_filter_semantics_version

        project_path = tmp_path / "myproject"
        project_path.mkdir()
        project_dir = tmp_path / "projects" / "myproject_abc123_bge-m3_1024d"
        project_dir.mkdir(parents=True)
        info_file = project_dir / "project_info.json"
        info_file.write_text("{not valid json")

        with patch(
            "mcp_server.storage_manager.get_project_storage_dir",
            return_value=project_dir,
        ):
            stamp_filter_semantics_version(str(project_path))  # must not raise


class TestUpdateProjectFiltersDeferredStamp:
    def test_stamp_semantics_version_false_leaves_field_untouched(self, tmp_path: Path):
        """The request-time call site (index_handlers.py) passes
        stamp_semantics_version=False so a failed/incremental reindex can't
        fake a successful migration."""
        from mcp_server.storage_manager import update_project_filters

        project_path = tmp_path / "myproject"
        project_path.mkdir()
        project_dir = tmp_path / "projects" / "myproject_abc123_bge-m3_1024d"
        project_dir.mkdir(parents=True)
        info_file = project_dir / "project_info.json"
        info_file.write_text(
            json.dumps(
                {
                    "project_name": "myproject",
                    "user_included_dirs": None,
                    "user_excluded_dirs": None,
                    "filter_semantics_version": 0,
                }
            )
        )

        with patch(
            "mcp_server.storage_manager.get_project_storage_dir",
            return_value=project_dir,
        ):
            update_project_filters(
                str(project_path),
                ["venv/mypackage"],
                None,
                stamp_semantics_version=False,
            )

        updated = json.loads(info_file.read_text())
        assert updated["filter_semantics_version"] == 0
        # The rest of the update still went through.
        assert updated["user_included_dirs"] == ["venv/mypackage"]

    def test_stamp_semantics_version_default_true_preserves_old_behavior(
        self, tmp_path: Path
    ):
        from mcp_server.storage_manager import update_project_filters

        project_path = tmp_path / "myproject"
        project_path.mkdir()
        project_dir = tmp_path / "projects" / "myproject_abc123_bge-m3_1024d"
        project_dir.mkdir(parents=True)
        info_file = project_dir / "project_info.json"
        info_file.write_text(
            json.dumps(
                {
                    "project_name": "myproject",
                    "user_included_dirs": None,
                    "user_excluded_dirs": None,
                    "filter_semantics_version": 0,
                }
            )
        )

        with patch(
            "mcp_server.storage_manager.get_project_storage_dir",
            return_value=project_dir,
        ):
            update_project_filters(str(project_path), ["venv/mypackage"], None)

        updated = json.loads(info_file.read_text())
        assert updated["filter_semantics_version"] == FILTER_SEMANTICS_VERSION
