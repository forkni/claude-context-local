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
        assert _fields(capsys.readouterr().out)[0][4:] == ["none", "-"]

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
            lambda projects: [[("Test-Model", "up to date")] for _ in projects],
        )
        scripts["parseable"].main(["--freshness"])
        assert _fields(capsys.readouterr().out)[0][4:] == ["-", "up to date"]

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
        assert result.stdout.strip().endswith("|none|-")


class TestIndexStatuses:
    @pytest.fixture
    def freshness(self, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
        """Results that the patched ``compute_index_freshness`` returns, by project path."""
        import mcp_server.index_freshness as index_freshness

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
        assert self._status(scripts, str(tmp_path)) == "up to date"

    def test_stale_with_counts(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = {
            "index_is_current": False,
            "pending_changes": {"added": 1, "modified": 2, "removed": 0},
        }
        assert self._status(scripts, str(tmp_path)) == (
            "stale - 1 added, 2 modified, 0 removed"
        )

    def test_no_snapshot_is_unknown(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = None
        assert self._status(scripts, str(tmp_path)) == "unknown"

    def test_failure_is_unknown(self, scripts, freshness, tmp_path: Path) -> None:
        freshness[str(tmp_path)] = OSError("locked")
        assert self._status(scripts, str(tmp_path)) == "unknown"

    def test_missing_path(self, scripts, freshness, tmp_path: Path) -> None:
        assert self._status(scripts, str(tmp_path / "gone")) == "path not found"

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
            "up to date" if i % 2 == 0 else f"stale - {i} added, 0 modified, 0 removed"
            for i in range(6)
        ]

    def test_index_field_joins_several_models(self, scripts) -> None:
        field = scripts["status"].index_field(
            [
                ("F2LLM-v2-0.6B", "up to date"),
                ("bge-m3", "stale - 0 added, 2 modified, 0 removed"),
            ]
        )
        assert (
            field
            == "F2LLM-v2-0.6B up to date; bge-m3 stale - 0 added, 2 modified, 0 removed"
        )
        assert scripts["status"].index_field([("only", "up to date")]) == "up to date"


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
        meta = storage / "merkle" / "1a2b3c4d00000000_test-model_8d_metadata.json"
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
        meta = storage / "merkle" / "1a2b3c4d00000000_test-model_8d_metadata.json"
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
                [("Test-Model", "stale - 1 added, 0 modified, 0 removed")]
            ],
        )
        scripts["display"].main(["--scip", "--freshness"])
        out = capsys.readouterr().out
        assert "     SCIP: none\n" in out
        assert "     Index: stale - 1 added, 0 modified, 0 removed\n" in out

    def test_one_line_per_model(
        self, scripts, storage: Path, tmp_path: Path, monkeypatch, capsys
    ) -> None:
        project = tmp_path / "py_project"
        project.mkdir()
        _add_project(storage, project)
        monkeypatch.setattr(
            scripts["status"],
            "index_statuses",
            lambda projects: [[("A", "up to date"), ("B", "unknown")]],
        )
        scripts["display"].main(["--freshness"])
        out = capsys.readouterr().out
        assert "     Index (A): up to date\n" in out
        assert "     Index (B): unknown\n" in out
        assert "SCIP:" not in out
