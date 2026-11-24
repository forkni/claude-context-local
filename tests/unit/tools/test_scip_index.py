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
        workspace, out, "ra", runner=_writing_runner(), version="ra 1", decode=False
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
        workspace, tmp_path / "scip", "ra", runner=runner, version="ra 1", decode=False
    )
    assert manifest["changed_during_run"] == ["src/b.rs"]
    assert sorted(manifest["files"]) == ["src/lib.rs"]


def test_failed_run_keeps_previous_index(workspace: Path, tmp_path: Path) -> None:
    out = tmp_path / "scip"
    make_scip_index(
        workspace, out, "ra", runner=_writing_runner(), version="ra 1", decode=False
    )
    with pytest.raises(RuntimeError, match="exited 101"):
        make_scip_index(
            workspace,
            out,
            "ra",
            runner=lambda cmd, env: 101,
            version="ra 1",
            decode=False,
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
        workspace,
        tmp_path / "scip",
        "ra",
        target_dir=target,
        runner=run,
        version="v",
        decode=False,
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


def _len_field(number: int, payload: bytes) -> bytes:
    assert len(payload) < 128
    return bytes([number << 3 | 2, len(payload)]) + payload


_SYMBOL = b"rust-analyzer cargo ws 0.1.0 b()."
# One document, src/lib.rs: a definition of b() on line 1 and a reference on line 2.
_INDEX = _len_field(
    2,
    _len_field(1, b"src\\lib.rs")
    + _len_field(
        2, _len_field(1, b"\x00\x00\x01") + _len_field(2, _SYMBOL) + b"\x18\x01"
    )
    + _len_field(2, _len_field(1, b"\x01\x00\x01") + _len_field(2, _SYMBOL)),
)


def _index_runner(cmd: list[str], env: dict[str, str]) -> int:
    Path(cmd[cmd.index("--output") + 1]).write_bytes(_INDEX)
    return 0


def test_writes_reference_table(workspace: Path, tmp_path: Path) -> None:
    out = tmp_path / "scip"
    manifest = make_scip_index(workspace, out, "ra", runner=_index_runner, version="v")
    assert manifest["refs"] == {
        "symbols": 1,
        "external": 0,
        "multi_def": 0,
        "refs": 1,
    }
    assert (out / "refs.sqlite").is_file()
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_digest_only_rebuilds_the_table_and_manifest_counts(
    workspace: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    out = tmp_path / "scip"
    make_scip_index(
        workspace, out, "ra", runner=_index_runner, version="v", decode=False
    )
    assert (
        json.loads((out / "manifest.json").read_text(encoding="utf-8"))["refs"] is None
    )
    monkeypatch.setattr(scip_index, "_storage_scip_dir", lambda project: out)
    assert scip_index.main(["--path", str(workspace), "--digest-only"]) == 0
    assert (out / "refs.sqlite").is_file()
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["refs"]["refs"] == 1
    assert sorted(manifest["files"]) == ["src/b.rs", "src/lib.rs"]
    assert "1 references" in capsys.readouterr().out
    assert not list(out.glob("*.tmp"))


def test_digest_only_refuses_without_manifest(
    workspace: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    out = tmp_path / "scip"
    out.mkdir()
    (out / "index.scip").write_bytes(_INDEX)
    monkeypatch.setattr(scip_index, "_storage_scip_dir", lambda project: out)
    assert scip_index.main(["--path", str(workspace), "--digest-only"]) == 2
    assert not (out / "refs.sqlite").exists()
    assert "manifest" in capsys.readouterr().out


def test_undecodable_index_keeps_previous_output(
    workspace: Path, tmp_path: Path
) -> None:
    out = tmp_path / "scip"
    first = make_scip_index(workspace, out, "ra", runner=_index_runner, version="v")
    table = (out / "refs.sqlite").read_bytes()

    def garbage(cmd: list[str], env: dict[str, str]) -> int:
        # Field 2, length 5, but only 1 byte follows: a truncated document.
        Path(cmd[cmd.index("--output") + 1]).write_bytes(bytes([0x12, 0x05, 0x0A]))
        return 0

    with pytest.raises((ValueError, IndexError)):
        make_scip_index(workspace, out, "ra", runner=garbage, version="v")
    assert (out / "index.scip").read_bytes() == _INDEX
    assert (out / "refs.sqlite").read_bytes() == table
    assert json.loads((out / "manifest.json").read_text(encoding="utf-8")) == first
    leftovers = [p.name for p in out.iterdir() if p.suffix in {".tmp", ".new"}]
    assert leftovers == []


def test_cli_reports_a_bad_rust_analyzer_path(workspace: Path, capsys) -> None:
    bad = str(workspace / "no-such-ra.exe")
    assert scip_index.main(["--path", str(workspace), "--rust-analyzer", bad]) == 2
    out = capsys.readouterr().out
    assert "is not a file or a command" in out
    assert "rustup" not in out
