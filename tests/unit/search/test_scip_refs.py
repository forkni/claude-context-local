"""Unit tests for search/scip_refs.py (SCIP reference table, ADR-0092 "E" tier)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from search.scip_refs import (
    MANIFEST_NAME,
    REFS_NAME,
    ScipRefs,
    descriptor_name,
    hash_rust_files,
    iter_occurrences,
    write_refs_table,
)


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _field(number: int, payload: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(payload)) + payload


def _occurrence(line0: int, symbol: str, roles: int = 0) -> bytes:
    packed = b"".join(_varint(v) for v in (line0, 4, 9))
    body = _field(1, packed) + _field(2, symbol.encode())
    if roles:
        body += _varint(3 << 3) + _varint(roles)
    return body


def _document(path: str, occurrences: list[bytes]) -> bytes:
    body = _field(1, path.encode())
    for occ in occurrences:
        body += _field(2, occ)
    return body


PKG = "rust-analyzer cargo app 0.1.0 "
EXT = "rust-analyzer cargo core https://github.com/rust-lang/rust/library/core "
HELPER = PKG + "util/helper()."
RUN = PKG + "impl#[Engine][Runner]run()."
ESCAPED = PKG + "util/`r#type`()."
EXTERNAL = EXT + "option/impl#[`Option<T>`]map()."
TYPE_ONLY = PKG + "util/Engine#"


def _index_bytes() -> bytes:
    lib = _document(
        "src\\lib.rs",
        [
            _occurrence(1, HELPER, roles=1),  # def at line 2
            _occurrence(5, RUN, roles=1),  # def at line 6
            _occurrence(8, ESCAPED, roles=1),
            _occurrence(10, HELPER),  # ref at line 11
            _occurrence(10, TYPE_ONLY),  # not a function: dropped
            _occurrence(11, "local 3"),  # local: dropped
        ],
    )
    main = _document(
        "src/main.rs",
        [
            _occurrence(2, RUN),
            _occurrence(3, EXTERNAL),
            _occurrence(4, ESCAPED),
            # A second target defines the same symbol string (tests/*.rs crates).
            _occurrence(6, HELPER, roles=1),
        ],
    )
    metadata = _field(1, b"\x08\x01")  # Index.metadata is skipped
    return metadata + _field(2, lib) + _field(2, main)


@pytest.fixture
def scip_dir(tmp_path: Path) -> Path:
    project = tmp_path / "ws"
    (project / "src").mkdir(parents=True)
    (project / "src" / "lib.rs").write_text("// lib\n", encoding="utf-8")
    (project / "src" / "main.rs").write_text("// main\n", encoding="utf-8")
    out = tmp_path / "scip"
    out.mkdir()
    (out / "index.scip").write_bytes(_index_bytes())
    manifest = {
        "format": 1,
        "project_path": str(project),
        "files": hash_rust_files(project),
    }
    (out / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
    return out


@pytest.mark.parametrize(
    ("symbol", "name"),
    [
        (HELPER, "helper"),
        (RUN, "run"),
        (ESCAPED, "r#type"),
        (EXTERNAL, "map"),
        (PKG + "util/f(+1).", "f"),
        (TYPE_ONLY, None),
        ("local 3", None),
    ],
    ids=[
        "free",
        "impl-method",
        "escaped",
        "external",
        "disambiguator",
        "type",
        "local",
    ],
)
def test_descriptor_name(symbol: str, name: str | None) -> None:
    assert descriptor_name(symbol) == name


def test_iter_occurrences_reads_paths_lines_and_roles() -> None:
    rows = list(iter_occurrences(_index_bytes()))
    assert ("src/lib.rs", 2, HELPER.encode(), 1) in rows
    assert ("src/lib.rs", 11, HELPER.encode(), 0) in rows
    assert ("src/main.rs", 4, EXTERNAL.encode(), 0) in rows


def test_table_holds_function_symbols_and_refs(scip_dir: Path) -> None:
    stats = write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
    assert stats == {"symbols": 4, "external": 1, "multi_def": 1, "refs": 4}
    con = sqlite3.connect(scip_dir / REFS_NAME)
    try:
        names = dict(con.execute("SELECT symbol, name FROM symbols"))
        defs = sorted(
            con.execute(
                "SELECT s.symbol, d.file, d.line FROM defs d "
                "JOIN symbols s ON s.id = d.symbol_id"
            )
        )
        refs = sorted(con.execute("SELECT file, line, name FROM refs"))
    finally:
        con.close()
    assert names[RUN] == "run"
    assert names[EXTERNAL] == "map"
    assert (RUN, "src/lib.rs", 6) in defs
    assert [d for d in defs if d[0] == HELPER] == [
        (HELPER, "src/lib.rs", 2),
        (HELPER, "src/main.rs", 7),
    ]
    assert not [d for d in defs if d[0] == EXTERNAL]
    assert refs == [
        ("src/lib.rs", 11, "helper"),
        ("src/main.rs", 3, "run"),
        ("src/main.rs", 4, "map"),
        ("src/main.rs", 5, "r#type"),
    ]
    assert not list(scip_dir.glob("*.tmp"))


def test_reader_answers_refs_and_freshness(scip_dir: Path) -> None:
    write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
    refs = ScipRefs.open(scip_dir)
    assert refs is not None
    try:
        main_rs = refs.project / "src" / "main.rs"
        assert refs.relative(main_rs) == "src/main.rs"
        assert refs.is_fresh("src/main.rs")
        hits = refs.refs_at("src/main.rs", 3, "run")
        assert [hit[1] for hit in hits] == [(("src/lib.rs", 6),)]
        assert refs.refs_at("src/main.rs", 4, "map")[0][1] == ()
        helper = refs.refs_at("src/lib.rs", 11, "helper")
        assert helper[0][1] == (("src/lib.rs", 2), ("src/main.rs", 7))
        assert refs.refs_at("src/main.rs", 3, "other") == []
        main_rs.write_text("// edited\n", encoding="utf-8")
        refs_again = ScipRefs.open(scip_dir)
        assert refs_again is not None
        assert not refs_again.is_fresh("src/main.rs")
        assert not refs_again.is_fresh("src/missing.rs")
        refs_again.close()
    finally:
        refs.close()


def test_reader_needs_table_and_manifest(scip_dir: Path) -> None:
    assert ScipRefs.open(scip_dir) is None  # no table yet
    write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
    (scip_dir / MANIFEST_NAME).unlink()
    assert ScipRefs.open(scip_dir) is None


def test_hash_matches_sha256(tmp_path: Path) -> None:
    (tmp_path / "a.rs").write_bytes(b"fn a() {}\n")
    assert hash_rust_files(tmp_path) == {
        "a.rs": hashlib.sha256(b"fn a() {}\n").hexdigest()
    }
