"""Tests for tools/batch_index.py's --dry-run filter preview.

_dry_run() walks a project directory applying the same PathFilter precedence
resolver the real indexing path uses, then prints a root-file listing and a
per-directory rollup (file count + size) of everything that would be indexed,
without touching hashing/chunking/embedding. These tests exercise the
listing/rollup rendering added on top of the existing per-pattern preview:
counts reconciling with the walk, the row cap + --dry-run-full escape hatch,
exclude/include filtering reflected in the listing, and the ASCII-safety
fallback that keeps a non-ASCII filename from crashing the preview under a
Windows console codepage.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# tools/ is on pythonpath (pyproject.toml [tool.pytest.ini_options]), so the
# standalone script is importable bare, same as when run directly.
import batch_index
import pytest


def _make_file(root: Path, rel_path: str, size: int = 10) -> None:
    """Create a file at root/rel_path containing `size` bytes."""
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def _run(
    tmp_path: Path,
    *,
    include_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    include_exclusive: bool = False,
    full: bool = False,
) -> int:
    return batch_index._dry_run(
        tmp_path, include_dirs, exclude_dirs, include_exclusive, full=full
    )


class TestDryRunListing:
    """Root files + per-directory rollup rendering."""

    def test_basic_rollup(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        _make_file(tmp_path, "a.py", size=100)
        _make_file(tmp_path, "b.py", size=200)
        _make_file(tmp_path, "pkg/one.py", size=300)
        _make_file(tmp_path, "pkg/two.py", size=400)
        _make_file(tmp_path, "pkg/sub/three.py", size=500)

        rc = _run(tmp_path)
        out = capsys.readouterr().out

        assert rc == 0
        assert "Root files (2)" in out
        assert "a.py" in out
        assert "b.py" in out
        assert "Directories (2)" in out
        assert "pkg/" in out
        assert "pkg/sub/" in out
        assert "2 files" in out  # pkg/ rollup row: 2 direct files

    def test_counts_reconcile_with_totals_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "a.py")
        _make_file(tmp_path, "pkg/one.py")
        _make_file(tmp_path, "pkg/two.py")
        _make_file(tmp_path, "pkg/sub/three.py")

        rc = _run(tmp_path)
        out = capsys.readouterr().out

        assert rc == 0
        # 1 root file + 2 in pkg/ + 1 in pkg/sub/ == 4; 2 directories directly
        # contain a matched file (pkg/, pkg/sub/) -- root doesn't count as a
        # "directory" row.
        assert "4 files, 2 directories," in out

    def test_pure_container_directory_gets_no_row(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # pkg/ only contains a subfolder, no file of its own -- it should not
        # get its own rollup row, only pkg/sub/ should.
        _make_file(tmp_path, "pkg/sub/three.py")

        rc = _run(tmp_path)
        out = capsys.readouterr().out

        assert rc == 0
        assert "Directories (1)" in out
        assert "pkg/sub/" in out
        # "pkg/" alone (not followed by "sub/") should not appear as a row.
        assert "  pkg/ " not in out and "  pkg/  " not in out

    def test_cap_engages_and_reports_remainder(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(batch_index, "_DRY_RUN_MAX_ROWS", 2)
        for i in range(5):
            _make_file(tmp_path, f"dir{i}/file.py", size=10)

        rc = _run(tmp_path)
        out = capsys.readouterr().out

        assert rc == 0
        assert "dir0/" in out
        assert "dir1/" in out
        assert "dir4/" not in out
        assert "... and 3 more directories" in out
        assert "(re-run with --dry-run-full to list every directory)" in out
        # Totals stay accurate even though the listing is truncated.
        assert "5 files, 5 directories," in out

    def test_dry_run_full_lists_every_directory(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(batch_index, "_DRY_RUN_MAX_ROWS", 2)
        for i in range(5):
            _make_file(tmp_path, f"dir{i}/file.py", size=10)

        rc = _run(tmp_path, full=True)
        out = capsys.readouterr().out

        assert rc == 0
        assert "... and" not in out
        for i in range(5):
            assert f"dir{i}/" in out

    def test_include_pattern_branch_also_lists(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "pkg/one.py")
        _make_file(tmp_path, "other/two.py")

        rc = _run(tmp_path, include_dirs=["pkg"])
        out = capsys.readouterr().out

        assert rc == 0
        assert "[narrowing] pkg" in out  # existing per-pattern table untouched
        assert "Directories (1)" in out
        assert "pkg/" in out
        assert "other/" not in out  # narrowed out, must not leak into listing

    def test_excluded_dir_absent_from_listing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "keep/a.py")
        _make_file(tmp_path, "skip/b.py")

        rc = _run(tmp_path, exclude_dirs=["skip"])
        out = capsys.readouterr().out

        assert rc == 0
        assert "keep/" in out
        assert "skip/" not in out

    def test_ascii_decorations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "a.py")
        _make_file(tmp_path, "pkg/one.py")

        _run(tmp_path)
        out = capsys.readouterr().out

        # Filenames here are pure ASCII, so if any decoration (a stray
        # Unicode box-drawing char, etc.) crept in, this raises. Guards
        # against regressing the "+--"/"|--" ASCII convention.
        out.encode("ascii")


class TestDryRunAsciiFallback:
    """The Windows-console encoding fallback for non-ASCII filenames."""

    def test_non_ascii_filename_does_not_crash(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        try:
            _make_file(tmp_path, "café.py")
        except OSError:
            pytest.skip("filesystem rejects non-ASCII filenames")

        # Simulate a console codepage that can't represent the filename at
        # all -- start_mcp_server.cmd runs Python with no chcp 65001 /
        # PYTHONUTF8, so stdout's real encoding is the ambient console
        # codepage (cp1252/cp437 on this machine), not UTF-8. An "ascii"
        # stream is a strict superset of failure modes any of those codepages
        # could hit, so it's a sound stand-in for the real crash condition.
        stream = io.TextIOWrapper(
            io.BytesIO(), encoding="ascii", errors="strict", newline="\n"
        )
        monkeypatch.setattr(sys, "stdout", stream)
        try:
            rc = _run(tmp_path)
        finally:
            stream.flush()

        assert rc == 0


class TestDryRunExitCodes:
    """Presentation changes must not move the existing exit-code contract."""

    def test_zero_when_files_match(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "a.py")
        assert _run(tmp_path) == 0
        capsys.readouterr()

    def test_one_when_include_pattern_matches_nothing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        _make_file(tmp_path, "a.py")
        rc = _run(tmp_path, include_dirs=["does-not-exist"])
        out = capsys.readouterr().out
        assert rc == 1
        assert "[ERROR] Every include_dirs pattern matched 0 files" in out
