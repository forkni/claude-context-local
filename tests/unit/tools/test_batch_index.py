"""Tests for tools/batch_index.py -- directory-filter list parsing."""

from __future__ import annotations

import sys
from pathlib import Path

# tools/ is on pythonpath (pyproject.toml [tool.pytest.ini_options]), so the
# standalone script is importable bare, same as when run directly.
import batch_index
import pytest


class TestSplitDirList:
    def test_comma_separated(self, tmp_path: Path) -> None:
        assert batch_index._split_dir_list("src,lib", tmp_path) == ["src", "lib"]

    def test_comma_with_spaces_after_commas(self, tmp_path: Path) -> None:
        assert batch_index._split_dir_list("src, lib ,tests", tmp_path) == [
            "src",
            "lib",
            "tests",
        ]

    def test_whitespace_separated(self, tmp_path: Path) -> None:
        raw = "pg/live_popguide pg/t7_run1 pg_live"
        assert batch_index._split_dir_list(raw, tmp_path) == [
            "pg/live_popguide",
            "pg/t7_run1",
            "pg_live",
        ]

    def test_single_entry(self, tmp_path: Path) -> None:
        assert batch_index._split_dir_list("src/core", tmp_path) == ["src/core"]

    def test_existing_path_with_space_kept_whole(self, tmp_path: Path) -> None:
        (tmp_path / "My Dir").mkdir()
        assert batch_index._split_dir_list("My Dir", tmp_path) == ["My Dir"]

    def test_comma_list_keeps_internal_spaces(self, tmp_path: Path) -> None:
        assert batch_index._split_dir_list("My Dir,src", tmp_path) == ["My Dir", "src"]

    @pytest.mark.parametrize("raw", ["", "   ", ",", " , "])
    def test_empty_inputs(self, raw: str, tmp_path: Path) -> None:
        assert batch_index._split_dir_list(raw, tmp_path) == []


class TestMainSpaceSeparatedFilters:
    """The menu passes the user's raw line as ONE quoted argv value."""

    def test_dry_run_accepts_space_separated_values(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        for name in ("a", "b"):
            (tmp_path / name).mkdir()
            (tmp_path / name / "mod.py").write_text("x = 1\n", encoding="utf-8")
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "batch_index.py",
                "--path",
                str(tmp_path),
                "--mode",
                "new",
                "--include-dirs",
                "a b",
                "--exclude-dirs",
                "zzz yyy",
                "--dry-run",
            ],
        )

        rc = batch_index.main()

        out = capsys.readouterr().out
        assert rc == 0
        assert "2 include pattern(s), 2 matched" in out
