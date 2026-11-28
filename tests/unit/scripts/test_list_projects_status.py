"""Unit tests for the launcher's project-list status lines.

Covers ``scripts/project_status.py`` and the ``--scip`` / ``--freshness`` flags of
``scripts/list_projects_parseable.py`` and ``scripts/list_projects_display.py``.
The scripts import each other by bare name (as when run from ``scripts/``), so
the tests put ``scripts/`` on ``sys.path`` the same way.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest


REPO = Path(__file__).resolve().parents[3]
SCRIPTS = REPO / "scripts"


@pytest.fixture
def scripts(monkeypatch: pytest.MonkeyPatch) -> dict[str, ModuleType]:
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import list_projects_display
    import list_projects_parseable
    import project_status

    return {
        "status": project_status,
        "parseable": list_projects_parseable,
        "display": list_projects_display,
    }


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    (root / "projects").mkdir(parents=True)
    (root / "merkle").mkdir()
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(root))
    monkeypatch.setenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", "")
    return root


def _add_project(storage: Path, project: Path, name: str = "proj") -> Path:
    model_dir = storage / "projects" / f"{name}_1a2b3c4d_test-model_8d"
    model_dir.mkdir(parents=True)
    info = {
        "project_name": name,
        "project_path": str(project),
        "project_hash": "1a2b3c4d",
        "embedding_model": "org/Test-Model",
        "model_dimension": 8,
    }
    (model_dir / "project_info.json").write_text(json.dumps(info), encoding="utf-8")
    return model_dir


def _fields(out: str) -> list[list[str]]:
    return [line.split("|") for line in out.splitlines() if line]


class TestParseableOutput:
    def test_six_fields_with_placeholders(
        self, scripts, storage: Path, tmp_path: Path, capsys
    ) -> None:
        project = tmp_path / "py_project"
        project.mkdir()
        _add_project(storage, project)
        scripts["parseable"].main([])
        assert _fields(capsys.readouterr().out) == [
            ["1", "proj", str(project), "Test-Model (8d)", "-", "-"]
        ]

    def test_scip_none_for_a_cargo_workspace_without_a_table(
        self, scripts, storage: Path, tmp_path: Path, capsys
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        _add_project(storage, project)
        scripts["parseable"].main(["--scip"])
        assert _fields(capsys.readouterr().out)[0][4:] == ["NONE", "-"]

    def test_scip_dash_for_a_non_rust_project(
        self, scripts, storage: Path, tmp_path: Path, capsys
    ) -> None:
        project = tmp_path / "py_project"
        project.mkdir()
        _add_project(storage, project)
        scripts["parseable"].main(["--scip"])
        assert _fields(capsys.readouterr().out)[0][4] == "-"

    def test_freshness_fills_field_six(
        self, scripts, storage: Path, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project = tmp_path / "py_project"
        project.mkdir()
        _add_project(storage, project)
        monkeypatch.setattr(
            scripts["status"],
            "index_statuses",
            lambda projects: [[("Test-Model", "CURRENT")] for _ in projects],
        )
        scripts["parseable"].main(["--freshness"])
        assert _fields(capsys.readouterr().out)[0][4:] == ["-", ": CURRENT"]

    def test_colour_flag_colours_both_fields(
        self, scripts, storage: Path, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        _add_project(storage, project)
        monkeypatch.setattr(
            scripts["status"],
            "index_statuses",
            lambda projects: [[("Test-Model", "CURRENT")] for _ in projects],
        )
        scripts["parseable"].main(["--scip", "--freshness", "--colour"])
        scip, index = _fields(capsys.readouterr().out)[0][4:]
        assert scip == "\x1b[93mNONE\x1b[0m"
        assert index == ": \x1b[94mCURRENT\x1b[0m"

    def test_no_colour_without_the_flag(
        self, scripts, storage: Path, tmp_path: Path, capsys
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        _add_project(storage, project)
        scripts["parseable"].main(["--scip"])
        assert "\x1b" not in capsys.readouterr().out

    def test_no_flag_run_imports_neither_torch_nor_the_index_check(
        self, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        _add_project(storage, project)
        result = subprocess.run(
            [
                sys.executable,
                "-X",
                "importtime",
                str(SCRIPTS / "list_projects_parseable.py"),
                "--scip",
            ],
            capture_output=True,
            text=True,
            env=dict(os.environ),
            check=True,
        )
        imported = {
            line.rsplit("|", 1)[-1].strip() for line in result.stderr.splitlines()
        }
        assert "torch" not in imported
        assert "mcp_server.index_freshness" not in imported
        assert result.stdout.strip().endswith("|NONE|-")


class TestIndexStatuses:
    @pytest.fixture
    def freshness(self, scripts, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
        """Results that the patched ``compute_index_freshness`` returns, by project path.

        Threads stand in for the worker processes: a patch does not reach a
        spawned process.
        """
        from concurrent.futures import ThreadPoolExecutor

        import mcp_server.index_freshness as index_freshness
        from mcp_server import freshness_batch

        monkeypatch.setattr(freshness_batch, "_make_pool", ThreadPoolExecutor)
        results: dict[str, object] = {}

        def fake(path: str, *, model_slug: str | None, dimension: int | None):
            result = results[path]
            if isinstance(result, Exception):
                raise result
            return result

        monkeypatch.setattr(index_freshness, "compute_index_freshness", fake)
        return results

    def _status(self, scripts, path: str) -> str:
        rows = scripts["status"].index_statuses([(path, [("org/Test-Model", 8)])])
        return rows[0][0][1]

    def test_up_to_date(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = {"index_is_current": True, "pending_changes": {}}
        assert self._status(scripts, str(tmp_path)) == "CURRENT"

    def test_stale_with_counts(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = {
            "index_is_current": False,
            "pending_changes": {"added": 1, "modified": 2, "removed": 0},
        }
        assert self._status(scripts, str(tmp_path)) == (
            "STALE - 1 added, 2 modified, 0 removed"
        )

    def test_no_snapshot_is_unknown(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = None
        assert self._status(scripts, str(tmp_path)) == "UNKNOWN"

    def test_failure_is_unknown(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = OSError("locked")
        assert self._status(scripts, str(tmp_path)) == "UNKNOWN"

    def test_missing_path(self, scripts, freshness, tmp_path: Path) -> None:
        assert self._status(scripts, str(tmp_path / "gone")) == "PATH NOT FOUND"

    def test_keeps_project_order(self, scripts, freshness, tmp_path: Path) -> None:
        paths = []
        for i in range(6):
            path = tmp_path / f"p{i}"
            path.mkdir()
            freshness[str(path)] = {
                "index_is_current": i % 2 == 0,
                "pending_changes": {"added": i, "modified": 0, "removed": 0},
            }
            paths.append((str(path), [("org/Test-Model", 8)]))
        rows = scripts["status"].index_statuses(paths)
        assert [row[0][1] for row in rows] == [
            "CURRENT" if i % 2 == 0 else f"STALE - {i} added, 0 modified, 0 removed"
            for i in range(6)
        ]

    def test_pool_failure_checks_one_by_one(
        self, scripts, freshness, tmp_path: Path, monkeypatch
    ) -> None:
        def no_pool(workers: int):
            raise OSError("no processes")

        from mcp_server import freshness_batch

        monkeypatch.setattr(freshness_batch, "_make_pool", no_pool)
        paths = []
        for i in range(2):
            path = tmp_path / f"p{i}"
            path.mkdir()
            freshness[str(path)] = {"index_is_current": True, "pending_changes": {}}
            paths.append((str(path), [("org/Test-Model", 8), ("org/Other", 16)]))
        rows = scripts["status"].index_statuses(paths)
        assert rows == [[("Test-Model", "CURRENT"), ("Other", "CURRENT")]] * 2

    def test_index_field_one_row_per_model(self, scripts) -> None:
        field = scripts["status"].index_field(
            [
                ("F2LLM-v2-0.6B", "CURRENT"),
                ("bge-m3", "STALE - 0 added, 2 modified, 0 removed"),
            ]
        )
        assert field.split(";;") == [
            " (F2LLM-v2-0.6B): CURRENT",
            " (bge-m3): STALE - 0 added, 2 modified, 0 removed",
        ]
        assert scripts["status"].index_field([("only", "CURRENT")]) == ": CURRENT"

    def test_index_field_colour(self, scripts) -> None:
        field = scripts["status"].index_field(
            [("A", "STALE - 1 added, 0 modified, 0 removed"), ("B", "UNKNOWN")],
            colour=True,
        )
        assert field == (
            " (A): \x1b[91mSTALE\x1b[0m - 1 added, 0 modified, 0 removed"
            ";; (B): \x1b[93mUNKNOWN\x1b[0m"
        )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("STALE - 2 changed", "\x1b[91mSTALE\x1b[0m - 2 changed"),
        ("CURRENT (made x)", "\x1b[94mCURRENT\x1b[0m (made x)"),
        ("CURRENT", "\x1b[94mCURRENT\x1b[0m"),
        ("PATH NOT FOUND", "\x1b[93mPATH NOT FOUND\x1b[0m"),
        ("INCOMPLETE (no ref)", "\x1b[93mINCOMPLETE\x1b[0m (no ref)"),
        ("NONE", "\x1b[93mNONE\x1b[0m"),
        ("CURRENTLY odd", "CURRENTLY odd"),
        ("-", "-"),
    ],
    ids=[
        "stale",
        "current-with-detail",
        "current",
        "multi-word",
        "incomplete",
        "none",
        "word-prefix-not-matched",
        "placeholder",
    ],
)
def test_colourize(text: str, expected: str) -> None:
    sys.path.insert(0, str(SCRIPTS))
    try:
        import project_status
    finally:
        sys.path.remove(str(SCRIPTS))
    assert project_status.colourize(text) == expected


class TestScipHintInputs:
    @pytest.fixture
    def base_config(
        self, scripts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> Path:
        config = tmp_path / "search_config.json"
        paths = scripts["status"]._load(
            "_launcher_config_paths", "search/config_paths.py"
        )
        monkeypatch.setattr(paths, "resolve_config_path", lambda: str(config))
        return config

    def test_rust_scip_from_the_base_config(
        self, scripts, base_config: Path, tmp_path: Path
    ) -> None:
        base_config.write_text(json.dumps({"call_graph": {"rust_scip": True}}), "utf-8")
        assert scripts["status"].rust_scip_enabled(tmp_path) is True

    def test_rust_scip_defaults_to_false(
        self, scripts, base_config: Path, tmp_path: Path
    ) -> None:
        assert scripts["status"].rust_scip_enabled(tmp_path) is False

    def test_project_override_wins(
        self, scripts, base_config: Path, tmp_path: Path, monkeypatch
    ) -> None:
        base_config.write_text(json.dumps({"call_graph": {"rust_scip": True}}), "utf-8")
        (tmp_path / "search_overrides.json").write_text(
            json.dumps({"overrides": {"call_graph": {"rust_scip": False}}}), "utf-8"
        )
        monkeypatch.delenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", raising=False)
        assert scripts["status"].rust_scip_enabled(tmp_path) is False
        monkeypatch.setenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", "1")
        assert scripts["status"].rust_scip_enabled(tmp_path) is True

    def test_last_indexed_from_merkle_metadata(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        meta = (
            storage
            / "merkle"
            / "1a2b3c4d000000000000000000000000_test-model_8d_metadata.json"
        )
        meta.write_text(
            json.dumps(
                {"project_path": str(project), "last_snapshot": "2026-11-27T15:40:00"}
            ),
            encoding="utf-8",
        )
        assert scripts["status"].last_indexed(storage, model_dir, str(project)) == (
            datetime(2026, 11, 27, 15, 40)
        )

    def test_last_indexed_skips_another_projects_metadata(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        meta = (
            storage
            / "merkle"
            / "1a2b3c4d000000000000000000000000_test-model_8d_metadata.json"
        )
        meta.write_text(
            json.dumps(
                {
                    "project_path": str(tmp_path / "other"),
                    "last_snapshot": "2026-11-27T15:40:00",
                }
            ),
            encoding="utf-8",
        )
        assert scripts["status"].last_indexed(storage, model_dir, str(project)) is None

    def test_last_indexed_uses_the_recorded_hash(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        """An 8-hex project-name segment and an ``_`` in the slug do not mislead it."""
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = storage / "projects" / "my_deadbeef_app_ab12cd34_odd_slug_8d"
        model_dir.mkdir(parents=True)
        (model_dir / "project_info.json").write_text(
            json.dumps({"project_path": str(project), "project_hash": "ab12cd34"}),
            encoding="utf-8",
        )
        meta = (
            storage
            / "merkle"
            / "ab12cd34000000000000000000000000_odd_slug_8d_metadata.json"
        )
        meta.write_text(
            json.dumps(
                {"project_path": str(project), "last_snapshot": "2026-11-27T15:40:00"}
            ),
            encoding="utf-8",
        )
        assert scripts["status"].last_indexed(storage, model_dir, str(project)) == (
            datetime(2026, 11, 27, 15, 40)
        )

    def test_indexed_rust_files_from_the_merkle_snapshot(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        tree = {
            "path": "",
            "is_file": False,
            "children": [
                {
                    "path": "src",
                    "is_file": False,
                    "children": [
                        {"path": "src\\lib.rs", "is_file": True, "children": []},
                        {"path": "src\\notes.md", "is_file": True, "children": []},
                    ],
                },
            ],
        }
        snap = (
            storage
            / "merkle"
            / "1a2b3c4d000000000000000000000000_test-model_8d_snapshot.json"
        )
        snap.write_text(
            json.dumps({"dag": {"root_path": str(project), "root_node": tree}}),
            encoding="utf-8",
        )
        assert scripts["status"].indexed_rust_files(
            storage, model_dir, str(project)
        ) == frozenset({"src/lib.rs"})

    def _snapshot(self, storage: Path, project: Path, tree: dict) -> None:
        snap = storage / "merkle" / f"1a2b3c4d{'0' * 24}_test-model_8d_snapshot.json"
        snap.write_text(
            json.dumps({"dag": {"root_path": str(project), "root_node": tree}}),
            encoding="utf-8",
        )

    def test_new_file_in_an_indexed_folder_counts(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        """Added after the last index: the next reindex sees it, so it is listed."""
        project = tmp_path / "rs_project"
        (project / "src").mkdir(parents=True)
        (project / "src" / "lib.rs").write_text("\n", encoding="utf-8")
        (project / "src" / "added.rs").write_text("\n", encoding="utf-8")
        (project / "new_dir").mkdir()
        (project / "new_dir" / "x.rs").write_text("\n", encoding="utf-8")
        model_dir = _add_project(storage, project)
        self._snapshot(
            storage,
            project,
            {
                "path": ".",
                "is_file": False,
                "children": [
                    {
                        "path": "src",
                        "is_file": False,
                        "children": [
                            {"path": "src\\lib.rs", "is_file": True, "children": []}
                        ],
                    }
                ],
            },
        )
        assert scripts["status"].indexed_rust_files(
            storage, model_dir, str(project)
        ) == frozenset({"src/lib.rs", "src/added.rs"})

    def test_merkle_lookup_ignores_a_longer_slug(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        """``x_test-model`` ends like ``test-model`` but is another model."""
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        other = storage / "merkle" / f"1a2b3c4d{'0' * 24}_x_test-model_8d_metadata.json"
        other.write_text(
            json.dumps(
                {"project_path": str(project), "last_snapshot": "2026-11-27T15:40:00"}
            ),
            encoding="utf-8",
        )
        assert scripts["status"].last_indexed(storage, model_dir, str(project)) is None

    def test_folder_name_fallback_without_project_info(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        (model_dir / "project_info.json").unlink()
        meta = storage / "merkle" / f"1a2b3c4d{'0' * 24}_test-model_8d_metadata.json"
        meta.write_text(
            json.dumps(
                {"project_path": str(project), "last_snapshot": "2026-11-27T15:40:00"}
            ),
            encoding="utf-8",
        )
        assert scripts["status"].last_indexed(storage, model_dir, str(project)) == (
            datetime(2026, 11, 27, 15, 40)
        )

    def test_padded_env_value_does_not_disable_overrides(
        self, scripts, base_config: Path, tmp_path: Path, monkeypatch
    ) -> None:
        """Same as the server's _bool_from_env, which does not strip."""
        (tmp_path / "search_overrides.json").write_text(
            json.dumps({"overrides": {"call_graph": {"rust_scip": True}}}), "utf-8"
        )
        monkeypatch.setenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", " 1")
        assert scripts["status"].rust_scip_enabled(tmp_path) is True

    def test_no_snapshot_means_no_index_filter(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        model_dir = _add_project(storage, project)
        assert (
            scripts["status"].indexed_rust_files(storage, model_dir, str(project))
            is None
        )

    def test_global_gate_turns_project_overrides_off(
        self, scripts, base_config: Path, tmp_path: Path, monkeypatch
    ) -> None:
        base_config.write_text(
            json.dumps(
                {
                    "call_graph": {"rust_scip": True},
                    "performance": {"enable_project_overrides": False},
                }
            ),
            "utf-8",
        )
        (tmp_path / "search_overrides.json").write_text(
            json.dumps({"overrides": {"call_graph": {"rust_scip": False}}}), "utf-8"
        )
        monkeypatch.delenv("CLAUDE_DISABLE_PROJECT_OVERRIDES", raising=False)
        assert scripts["status"].rust_scip_enabled(tmp_path) is True

    def test_damaged_reference_table_is_unreadable(
        self, scripts, storage: Path, tmp_path: Path
    ) -> None:
        """A corrupt refs.sqlite shows one 'unreadable' line, not a broken list."""
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        (project / "lib.rs").write_text("fn a() {}\n", encoding="utf-8")
        model_dir = _add_project(storage, project)
        scip = model_dir / "scip"
        scip.mkdir()
        (scip / "manifest.json").write_text(
            json.dumps({"project_path": str(project), "files": {"lib.rs": "0" * 64}}),
            encoding="utf-8",
        )
        (scip / "refs.sqlite").write_bytes(b"not a sqlite database" * 64)
        assert scripts["status"].scip_text(storage, str(project), [model_dir]) == (
            "UNREADABLE - run Make SCIP Index"
        )


class TestDisplay:
    def test_scip_and_index_lines(
        self, scripts, storage: Path, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project = tmp_path / "rs_project"
        project.mkdir()
        (project / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        _add_project(storage, project)
        monkeypatch.setattr(
            scripts["status"],
            "index_statuses",
            lambda projects: [
                [("Test-Model", "STALE - 1 added, 0 modified, 0 removed")]
            ],
        )
        scripts["display"].main(["--scip", "--freshness"])
        out = capsys.readouterr().out
        assert "     SCIP: NONE\n" in out  # not a console: no colour codes
        assert "     Index: STALE - 1 added, 0 modified, 0 removed\n" in out

    def test_one_line_per_model(
        self, scripts, storage: Path, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project = tmp_path / "py_project"
        project.mkdir()
        _add_project(storage, project)
        monkeypatch.setattr(
            scripts["status"],
            "index_statuses",
            lambda projects: [[("A", "CURRENT"), ("B", "UNKNOWN")]],
        )
        scripts["display"].main(["--freshness"])
        out = capsys.readouterr().out
        assert "     Index (A): CURRENT\n" in out
        assert "     Index (B): UNKNOWN\n" in out
        assert "SCIP:" not in out
