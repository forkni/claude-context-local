"""Unit tests for search/scip_refs.py (SCIP reference table, ADR-0092 "E" tier)."""

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from search.graph_integration import _RustScipPass
from search.scip_refs import (
    MANIFEST_NAME,
    REFS_NAME,
    REINDEX_HINT,
    SCIP_OFF_HINT,
    ScipRefs,
    descriptor_name,
    hash_rust_files,
    iter_occurrences,
    scip_status,
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
    # Hashed, but rust-analyzer made no document for it (not a workspace member).
    (project / "src" / "extra.rs").write_text("// extra\n", encoding="utf-8")
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


def test_reader_tells_hashed_from_covered_files(scip_dir: Path) -> None:
    """A hashed file with no rows is an uncovered file (no SCIP document)."""
    write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
    refs = ScipRefs.open(scip_dir)
    assert refs is not None
    try:
        assert refs.is_hashed("src/extra.rs")
        assert not refs.has_rows("src/extra.rs")
        assert refs.has_rows("src/main.rs")  # refs and a definition
        assert refs.has_rows("src/lib.rs")
        assert not refs.is_hashed("src/missing.rs")
    finally:
        refs.close()


class TestRustScipPassUncoveredFiles:
    """`no_doc`: calls in a file that rust-analyzer made no document for."""

    @pytest.fixture
    def scip_pass(self, scip_dir: Path) -> Iterator[_RustScipPass]:
        write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
        refs = ScipRefs.open(scip_dir)
        assert refs is not None
        scip_pass = _RustScipPass(refs, {})
        yield scip_pass
        scip_pass.close()

    def test_uncovered_caller_counts_no_doc(self, scip_pass: _RustScipPass) -> None:
        assert scip_pass.decide("src/extra.rs", 1, "helper") is None
        assert scip_pass.decide("src/extra.rs", 1, "helper", in_macro=True) is None
        assert scip_pass.counts["no_doc"] == 1
        assert scip_pass.counts["no_ref"] == 0
        assert scip_pass.macro_counts["no_doc"] == 1

    def test_edited_uncovered_caller_is_not_stale(
        self, scip_pass: _RustScipPass
    ) -> None:
        """Make SCIP Index cannot cover the file, so its edits are not stale."""
        extra = scip_pass.refs.project / "src" / "extra.rs"
        extra.write_text("// edited\n", encoding="utf-8")
        assert scip_pass.decide("src/extra.rs", 1, "helper") is None
        assert scip_pass.counts["no_doc"] == 1
        assert scip_pass.counts["stale_caller"] == 0

    def test_caller_missing_from_manifest_stays_stale(
        self, scip_pass: _RustScipPass
    ) -> None:
        """A file made after the SCIP run: a new run can cover it."""
        new = scip_pass.refs.project / "src" / "new.rs"
        new.write_text("fn f() {}\n", encoding="utf-8")
        assert scip_pass.decide("src/new.rs", 1, "helper") is None
        assert scip_pass.counts["stale_caller"] == 1
        assert scip_pass.counts["no_doc"] == 0

    def test_covered_caller_without_a_ref_stays_no_ref(
        self, scip_pass: _RustScipPass
    ) -> None:
        assert scip_pass.decide("src/main.rs", 1, "helper") is None
        assert scip_pass.counts["no_ref"] == 1
        assert scip_pass.counts["no_doc"] == 0

    def test_stale_share_leaves_out_no_doc(
        self, scip_pass: _RustScipPass, caplog: pytest.LogCaptureFixture
    ) -> None:
        """1 stale call of 10 is 10% (no warning) only when no_doc counts."""
        (scip_pass.refs.project / "src" / "new.rs").write_text("\n", encoding="utf-8")
        for _ in range(9):
            scip_pass.decide("src/extra.rs", 1, "helper")
        scip_pass.decide("src/new.rs", 1, "helper")
        logger = logging.getLogger("test.scip_pass")
        with caplog.at_level(logging.INFO, logger="test.scip_pass"):
            scip_pass.log(logger)
        messages = [r.getMessage() for r in caplog.records]
        assert "no_ref=0 no_doc=9 (1 files) multi=0" in messages[0]
        assert messages[1] == (
            "[RUST_SCIP] SCIP table is stale for 1 files; run Make SCIP Index"
        )


class TestScipStatus:
    """`scip_status`: the launcher's SCIP line, on the graph build's predicates."""

    CREATED = "2026-11-24T12:05:00+00:00"

    @pytest.fixture
    def table(self, scip_dir: Path) -> Path:
        """``scip_dir`` with a reference table and a ``created`` time."""
        write_refs_table(scip_dir / "index.scip", scip_dir / REFS_NAME)
        manifest = json.loads((scip_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
        manifest["created"] = self.CREATED
        (scip_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        return scip_dir

    @staticmethod
    def _project(scip_dir: Path) -> Path:
        return scip_dir.parent / "ws"

    def _made(self) -> str:
        created = datetime.fromisoformat(self.CREATED)
        return created.astimezone().strftime("%Y-%m-%d %H:%M")

    def _status(self, table: Path, **kwargs: object) -> str:
        status = scip_status(table, self._project(table), **kwargs)  # type: ignore[arg-type]
        assert status is not None
        return status

    def test_up_to_date(self, table: Path) -> None:
        assert self._status(table) == f"CURRENT (made {self._made()}, 3 .rs files)"

    def test_changed_covered_file(self, table: Path) -> None:
        (self._project(table) / "src" / "lib.rs").write_text("// edit\n", "utf-8")
        assert self._status(table) == (
            f"STALE - 1 changed, 0 new, 0 removed since {self._made()}"
        )

    def test_new_file(self, table: Path) -> None:
        (self._project(table) / "src" / "new.rs").write_text("\n", encoding="utf-8")
        assert self._status(table).startswith("STALE - 0 changed, 1 new, 0 removed")

    def test_removed_covered_file(self, table: Path) -> None:
        (self._project(table) / "src" / "main.rs").unlink()
        assert self._status(table).startswith("STALE - 0 changed, 0 new, 1 removed")

    def test_edited_or_removed_uncovered_file_never_counts(self, table: Path) -> None:
        extra = self._project(table) / "src" / "extra.rs"
        extra.write_text("// edit\n", encoding="utf-8")
        assert self._status(table).startswith("CURRENT")
        extra.unlink()
        assert self._status(table).startswith("CURRENT")

    def test_no_reference_table(self, scip_dir: Path) -> None:
        assert self._status(scip_dir) == (
            "INCOMPLETE (no reference table) - run Make SCIP Index"
        )

    def test_no_manifest_in_cargo_workspace(self, tmp_path: Path) -> None:
        (tmp_path / "Cargo.toml").write_text("[workspace]\n", encoding="utf-8")
        assert scip_status(tmp_path / "scip", tmp_path) == "NONE"

    def test_no_manifest_outside_rust(self, tmp_path: Path) -> None:
        assert scip_status(tmp_path / "scip", tmp_path) is None

    def test_table_newer_than_index_gets_reindex_hint(self, table: Path) -> None:
        before = datetime.fromisoformat(self.CREATED) - timedelta(minutes=1)
        assert self._status(table, last_indexed=before).endswith(REINDEX_HINT)

    def test_table_older_than_index_gets_no_hint(self, table: Path) -> None:
        after = datetime.fromisoformat(self.CREATED) + timedelta(minutes=1)
        assert not self._status(table, last_indexed=after).endswith(REINDEX_HINT)

    def test_no_index_time_gets_no_hint(self, table: Path) -> None:
        assert not self._status(table, last_indexed=None).endswith(REINDEX_HINT)

    def test_naive_index_time_is_local(self, table: Path) -> None:
        """`last_snapshot` is naive local time; `created` is UTC."""
        created = datetime.fromisoformat(self.CREATED)
        after = (created + timedelta(seconds=30)).astimezone().replace(tzinfo=None)
        before = (created - timedelta(seconds=30)).astimezone().replace(tzinfo=None)
        assert not self._status(table, last_indexed=after).endswith(REINDEX_HINT)
        assert self._status(table, last_indexed=before).endswith(REINDEX_HINT)

    def test_rust_scip_off_replaces_the_hint(self, table: Path) -> None:
        before = datetime.fromisoformat(self.CREATED) - timedelta(minutes=1)
        status = self._status(table, last_indexed=before, rust_scip=False)
        assert status.endswith(SCIP_OFF_HINT)
        assert REINDEX_HINT not in status

    def test_files_outside_the_index_never_count(self, table: Path) -> None:
        """A git worktree under .claude/ holds .rs files the graph never sees."""
        project = self._project(table)
        worktree = project / ".claude" / "worktrees" / "wt" / "src"
        worktree.mkdir(parents=True)
        (worktree / "lib.rs").write_text("fn copy() {}\n", encoding="utf-8")
        (project / "src" / "main.rs").write_text("// edit\n", encoding="utf-8")
        indexed = frozenset({"src/lib.rs", "src/extra.rs"})  # main.rs excluded
        assert self._status(table, indexed=indexed) == (
            f"CURRENT (made {self._made()}, 2 .rs files)"  # count = checked files
        )
        assert self._status(table).startswith("STALE - 1 changed, 1 new, 0 removed")

    def test_text_is_safe_for_the_batch_launcher(self, table: Path) -> None:
        (self._project(table) / "src" / "new.rs").write_text("\n", encoding="utf-8")
        status = self._status(table, rust_scip=False)
        assert "|" not in status
        assert "!" not in status
