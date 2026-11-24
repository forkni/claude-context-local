"""Unit tests for tools/scip_index.py (the SCIP index producer for the planned "E" tier)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import scip_index
from tools.scip_index import hash_rust_files, make_scip_index


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "src").mkdir(parents=True)
    (root / "target" / "debug").mkdir(parents=True)
    (root / "Cargo.toml").write_text('[package]\nname = "ws"\n', encoding="utf-8")
    (root / "src" / "lib.rs").write_text("pub fn a() {}\n", encoding="utf-8")
    (root / "src" / "b.rs").write_text("pub fn b() {}\n", encoding="utf-8")
    (root / "target" / "debug" / "gen.rs").write_text(
        "// build output\n", encoding="utf-8"
    )
    return root


def _writing_runner(edit: Path | None = None):
    """A fake rust-analyzer: writes the --output file, optionally edits a source."""

    def run(cmd: list[str], env: dict[str, str]) -> int:
        Path(cmd[cmd.index("--output") + 1]).write_bytes(b"scip")
        if edit is not None:
            edit.write_text("pub fn b() { changed() }\n", encoding="utf-8")
        return 0

    return run


def test_hash_skips_build_output(workspace: Path) -> None:
    assert sorted(hash_rust_files(workspace)) == ["src/b.rs", "src/lib.rs"]


def test_writes_index_and_manifest(workspace: Path, tmp_path: Path) -> None:
    out = tmp_path / "scip"
    manifest = make_scip_index(
        workspace, out, "ra", runner=_writing_runner(), version="ra 1"
    )
    assert (out / "index.scip").read_bytes() == b"scip"
    on_disk = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert on_disk == manifest
    assert on_disk["format"] == 1
    assert on_disk["rust_analyzer"] == "ra 1"
    assert sorted(on_disk["files"]) == ["src/b.rs", "src/lib.rs"]
    assert on_disk["changed_during_run"] == []
    assert not list(out.glob("*.tmp"))


def test_file_changed_during_run_is_left_out(workspace: Path, tmp_path: Path) -> None:
    runner = _writing_runner(edit=workspace / "src" / "b.rs")
    manifest = make_scip_index(
        workspace, tmp_path / "scip", "ra", runner=runner, version="ra 1"
    )
    assert manifest["changed_during_run"] == ["src/b.rs"]
    assert sorted(manifest["files"]) == ["src/lib.rs"]


def test_failed_run_keeps_previous_index(workspace: Path, tmp_path: Path) -> None:
    out = tmp_path / "scip"
    make_scip_index(workspace, out, "ra", runner=_writing_runner(), version="ra 1")
    with pytest.raises(RuntimeError, match="exited 101"):
        make_scip_index(
            workspace, out, "ra", runner=lambda cmd, env: 101, version="ra 1"
        )
    assert (out / "index.scip").read_bytes() == b"scip"
    assert not list(out.glob("*.tmp"))


def test_target_dir_is_passed_to_the_build(workspace: Path, tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def run(cmd: list[str], env: dict[str, str]) -> int:
        seen.update(env)
        return _writing_runner()(cmd, env)

    target = tmp_path / "t"
    make_scip_index(
        workspace, tmp_path / "scip", "ra", target_dir=target, runner=run, version="v"
    )
    assert seen["CARGO_TARGET_DIR"] == str(target)


def test_missing_cargo_toml_is_refused(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Cargo.toml"):
        make_scip_index(
            tmp_path, tmp_path / "scip", "ra", runner=_writing_runner(), version="v"
        )


def test_cli_refuses_unindexed_project(workspace: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(scip_index, "find_rust_analyzer", lambda explicit=None: "ra")
    monkeypatch.setattr(scip_index, "_storage_scip_dir", lambda project: None)
    assert scip_index.main(["--path", str(workspace)]) == 2
    assert "not indexed yet" in capsys.readouterr().out
