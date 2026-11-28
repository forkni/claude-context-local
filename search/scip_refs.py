"""SCIP reference table for the Rust SCIP call-edge tier (ADR-0092).

``tools/scip_index.py`` runs ``rust-analyzer scip`` outside the reindex and writes
``<storage>/scip/index.scip`` plus ``manifest.json`` (a sha256 for every ``.rs``
file). Decoding that index takes seconds and hundreds of MB, so the producer also
writes ``refs.sqlite`` (:func:`write_refs_table`), and the graph build only reads
rows from it (:class:`ScipRefs`).

Table layout (function and method symbols only; ``local`` symbols dropped)::

    symbols(id, symbol, name)          one row per symbol string
    defs(symbol_id, file, line)        every Definition occurrence; none = defined
                                       outside the indexed documents (external)
    refs(file, line, name, symbol_id)  every non-definition occurrence

A symbol string can have several definitions: rust-analyzer names items in
different targets of one package alike (each ``tests/*.rs`` file is its own
crate, so two tests' ``fn helper`` share ``<pkg> helper().``). The table keeps
them all and the graph build picks the caller's own file or declines.

Paths are project-relative with ``/``; lines are 1-based. SCIP has no call role,
so a reference is joined to a tree-sitter call site by caller file, line and
callee name.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path


SCIP_DIRNAME = "scip"
INDEX_NAME = "index.scip"
MANIFEST_NAME = "manifest.json"
REFS_NAME = "refs.sqlite"
# Directories that never hold project sources: build output and VCS data.
SKIP_DIRS = frozenset({"target", ".git", "node_modules", ".venv"})

_DEFINITION_ROLE = 0x1
_NAME_TAIL = re.compile(r"[A-Za-z0-9_$+\-]+\Z")


def hash_rust_files(root: Path) -> dict[str, str]:
    """``{relative posix path: sha256 hex}`` for every ``.rs`` file under ``root``.

    Skips build output and VCS directories (``target``, ``.git`` and similar)
    at any depth.
    """
    hashes: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if not name.endswith(".rs"):
                continue
            path = Path(dirpath) / name
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
            hashes[path.relative_to(root).as_posix()] = digest
    return hashes


def _hash_files(root: Path, relatives: frozenset[str]) -> dict[str, str]:
    """``{relative: sha256 hex}`` for each of ``relatives`` that exists under ``root``."""
    hashes: dict[str, str] = {}
    for relative in relatives:
        try:
            data = (root / relative).read_bytes()
        except OSError:
            continue
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return hashes


def descriptor_name(symbol: str) -> str | None:
    """The function or method name a SCIP symbol ends in, else None.

    A method descriptor is ``name(disambiguator).``; rust-analyzer puts impl
    blocks before it as ``impl#[Type][Trait]``, so the name is the identifier
    run just before the ``(``. Backtick-escaped names (``r#type``) are unescaped.
    """
    if symbol.startswith("local ") or not symbol.endswith(")."):
        return None
    head = symbol[: symbol.rfind("(")]
    if head.endswith("`"):
        start = head.rfind("`", 0, len(head) - 1)
        return head[start + 1 : -1].replace("``", "`") if start >= 0 else None
    match = _NAME_TAIL.search(head)
    return match.group(0) if match else None


def _varint(data: bytes, i: int) -> tuple[int, int]:
    byte = data[i]
    if byte < 0x80:
        return byte, i + 1
    value = byte & 0x7F
    shift = 7
    i += 1
    while True:
        byte = data[i]
        i += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, i
        shift += 7


def _fields(data: bytes, start: int, end: int) -> Iterator[tuple[int, int, int]]:
    """Protobuf fields in ``data[start:end]`` as ``(number, a, b)``.

    Varint fields give ``(number, value, 0)``; length-delimited fields give
    ``(number, payload_start, payload_end)``; fixed-width fields are skipped.
    """
    i = start
    while i < end:
        key, i = _varint(data, i)
        number, wire_type = key >> 3, key & 7
        if wire_type == 0:
            value, i = _varint(data, i)
            yield number, value, 0
        elif wire_type == 2:
            length, i = _varint(data, i)
            yield number, i, i + length
            i += length
        elif wire_type == 1:
            i += 8
        elif wire_type == 5:
            i += 4
        else:
            raise ValueError(f"unsupported protobuf wire type {wire_type}")


def iter_occurrences(data: bytes) -> Iterator[tuple[str, int, bytes, int]]:
    """``(path, line, symbol, roles)`` for every occurrence in a SCIP index.

    Reads only Index.documents (2); Document.relative_path (1) and occurrences
    (2); Occurrence.range (1, packed: first value = 0-based start line), symbol
    (2) and symbol_roles (3). ``\\`` in paths (rust-analyzer on Windows) becomes ``/``.
    """
    for number, start, end in _fields(data, 0, len(data)):
        if number != 2:
            continue
        path = ""
        occurrences: list[tuple[int, bytes, int]] = []
        for d_number, d_start, d_end in _fields(data, start, end):
            if d_number == 1:
                path = data[d_start:d_end].decode().replace("\\", "/")
            elif d_number == 2:
                line = -1
                symbol = b""
                roles = 0
                for o_number, o_start, o_end in _fields(data, d_start, d_end):
                    if o_number == 1:
                        line, _ = _varint(data, o_start)
                    elif o_number == 2:
                        symbol = data[o_start:o_end]
                    elif o_number == 3:
                        roles = o_start
                occurrences.append((line + 1, symbol, roles))
        for line, symbol, roles in occurrences:
            yield path, line, symbol, roles


def write_refs_table(index_path: Path, out_path: Path) -> dict[str, int]:
    """Decode ``index_path`` and write the reference table to ``out_path``.

    Written to ``<out_path>.tmp`` and renamed, so a failed run keeps the old table.

    Returns:
        ``{"symbols": n, "external": n, "multi_def": n, "refs": n}``; ``multi_def``
        counts symbols with more than one definition.
    """
    tmp = out_path.with_name(out_path.name + ".tmp")
    try:
        stats = _write_refs_table(index_path.read_bytes(), tmp)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, out_path)
    return stats


def _write_refs_table(data: bytes, tmp: Path) -> dict[str, int]:
    ids: dict[bytes, int] = {}
    names: dict[int, str] = {}
    definitions: dict[int, set[tuple[str, int]]] = {}
    refs: list[tuple[str, int, int]] = []
    for path, line, symbol, roles in iter_occurrences(data):
        if not symbol.endswith(b").") or symbol.startswith(b"local "):
            continue
        symbol_id = ids.get(symbol)
        if symbol_id is None:
            name = descriptor_name(symbol.decode())
            if name is None:
                continue
            symbol_id = len(ids) + 1
            ids[symbol] = symbol_id
            names[symbol_id] = name
        if roles & _DEFINITION_ROLE:
            definitions.setdefault(symbol_id, set()).add((path, line))
        else:
            refs.append((path, line, symbol_id))

    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.execute("PRAGMA journal_mode=OFF")
        con.execute("PRAGMA synchronous=OFF")
        con.execute(
            "CREATE TABLE symbols(id INTEGER PRIMARY KEY, symbol TEXT, name TEXT)"
        )
        con.execute("CREATE TABLE defs(symbol_id INT, file TEXT, line INT)")
        con.execute("CREATE TABLE refs(file TEXT, line INT, name TEXT, symbol_id INT)")
        con.executemany(
            "INSERT INTO symbols VALUES (?, ?, ?)",
            ((sid, sym.decode(), names[sid]) for sym, sid in ids.items()),
        )
        con.executemany(
            "INSERT INTO defs VALUES (?, ?, ?)",
            (
                (sid, path, line)
                for sid, places in definitions.items()
                for path, line in sorted(places)
            ),
        )
        con.executemany(
            "INSERT INTO refs VALUES (?, ?, ?, ?)",
            ((path, line, names[sid], sid) for path, line, sid in refs),
        )
        con.execute("CREATE INDEX refs_file_line ON refs(file, line)")
        con.execute("CREATE INDEX defs_symbol ON defs(symbol_id)")
        con.commit()
    finally:
        con.close()
    return {
        "symbols": len(ids),
        "external": sum(1 for sid in names if sid not in definitions),
        "multi_def": sum(1 for places in definitions.values() if len(places) > 1),
        "refs": len(refs),
    }


class ScipRefs:
    """Read side of the table: references by caller line, and file freshness."""

    def __init__(self, con: sqlite3.Connection, project: Path, files: dict[str, str]):
        self._con = con
        self.project = project
        self._files = files
        self._fresh: dict[str, bool] = {}
        self._relative: dict[str, str | None] = {}
        self._by_file: dict[str, dict[int, list[tuple[str, int]]]] = {}
        self._defs: dict[int, tuple[tuple[str, int], ...]] = {}
        self._with_rows: frozenset[str] | None = None
        self._project_key = os.path.normcase(os.path.normpath(str(project)))

    @classmethod
    def open(cls, scip_dir: Path) -> ScipRefs | None:
        """The table in ``scip_dir``, or None when the table or manifest is missing."""
        table = scip_dir / REFS_NAME
        manifest_path = scip_dir / MANIFEST_NAME
        if not table.is_file() or not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            project = Path(manifest["project_path"])
            files = dict(manifest["files"])
            con = sqlite3.connect(f"file:{table.as_posix()}?mode=ro", uri=True)
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            return None
        return cls(con, project, files)

    def close(self) -> None:
        self._con.close()

    def relative(self, file_path: str | Path) -> str | None:
        """``file_path`` relative to the project root (``/``), or None if outside it.

        A relative ``file_path`` is taken as relative to the project root already.
        """
        key = str(file_path)
        if key not in self._relative:
            self._relative[key] = self._relative_uncached(key)
        return self._relative[key]

    def _relative_uncached(self, file_path: str) -> str | None:
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project / path
        absolute = os.path.normcase(os.path.normpath(str(path)))
        if not absolute.startswith(self._project_key + os.sep):
            return None
        return Path(os.path.relpath(path, self.project)).as_posix()

    @property
    def hashed_files(self) -> frozenset[str]:
        """Every file the manifest has a hash for (relative, ``/``)."""
        return frozenset(self._files)

    def recorded_hash(self, relative: str) -> str | None:
        """The sha256 hex the manifest recorded for the file, or None."""
        return self._files.get(relative)

    def is_hashed(self, relative: str) -> bool:
        """True when the manifest has a hash for the file (it existed at the SCIP run)."""
        return relative in self._files

    def has_rows(self, relative: str) -> bool:
        """True when the table holds a function reference or definition in the file.

        rust-analyzer writes no document for a file outside the Cargo workspace
        (an uncovered file), so such a file has no rows. A covered file with no
        function reference or definition has none either; the table cannot
        decide its calls in both cases.
        """
        if self._with_rows is None:
            self._with_rows = frozenset(
                file
                for (file,) in self._con.execute(
                    "SELECT file FROM refs UNION SELECT file FROM defs"
                )
            )
        return relative in self._with_rows

    def is_fresh(self, relative: str) -> bool:
        """True when the file on disk still has the hash the manifest recorded."""
        fresh = self._fresh.get(relative)
        if fresh is None:
            expected = self._files.get(relative)
            fresh = False
            if expected is not None:
                try:
                    data = (self.project / relative).read_bytes()
                    fresh = hashlib.sha256(data).hexdigest() == expected
                except OSError:
                    fresh = False
            self._fresh[relative] = fresh
        return fresh

    def refs_at(
        self, relative: str, line: int, name: str
    ) -> list[tuple[int, tuple[tuple[str, int], ...]]]:
        """``(symbol_id, definitions)`` for each reference to ``name`` on ``line``.

        ``definitions`` is ``((file, line), ...)``; empty means external.
        """
        rows = self._by_file.get(relative)
        if rows is None:
            rows = {}
            for ref_line, ref_name, sid in self._con.execute(
                "SELECT line, name, symbol_id FROM refs WHERE file = ?", (relative,)
            ):
                rows.setdefault(ref_line, []).append((ref_name, sid))
            self._by_file[relative] = rows
        return [
            (sid, self.definitions(sid))
            for ref_name, sid in rows.get(line, ())
            if ref_name == name
        ]

    def definitions(self, symbol_id: int) -> tuple[tuple[str, int], ...]:
        """Every ``(file, line)`` where ``symbol_id`` is defined; empty = external."""
        found = self._defs.get(symbol_id)
        if found is None:
            found = tuple(
                self._con.execute(
                    "SELECT file, line FROM defs WHERE symbol_id = ? ORDER BY file, line",
                    (symbol_id,),
                )
            )
            self._defs[symbol_id] = found
        return found


REINDEX_HINT = " - reindex to use it"
SCIP_OFF_HINT = " - not used (call_graph.rust_scip is off)"


def _local_minute(moment: datetime) -> str:
    """``moment`` in local time as ``YYYY-MM-DD HH:MM`` (naive = already local)."""
    return moment.astimezone().strftime("%Y-%m-%d %H:%M")


def scip_status(
    scip_dir: Path,
    project: Path,
    *,
    last_indexed: datetime | None = None,
    rust_scip: bool = True,
    indexed: frozenset[str] | None = None,
) -> str | None:
    """One-line state of a project's SCIP table for the launcher's project lists.

    Classifies files with the same predicates the graph build uses
    (``_RustScipPass.decide``): a covered file (hashed, with rows) counts as
    changed when its hash differs and as removed when it is gone; a file the
    manifest does not know counts as new; an uncovered file (hashed, no rows)
    never counts, edited or not. With ``indexed``, only those files count:
    the graph never sees a file the search index leaves out (a git worktree
    under ``.claude/``, an excluded folder).

    Args:
        scip_dir: ``<storage>/scip`` of the project.
        project: Project root on disk.
        last_indexed: When the search index was last built (naive = local time).
            A table made after it gets :data:`REINDEX_HINT`: the graph reads
            the table only during a reindex. None = no hint.
        rust_scip: ``call_graph.rust_scip``. False gets :data:`SCIP_OFF_HINT`.
        indexed: The ``.rs`` files the search index holds (relative, ``/``);
            None counts every ``.rs`` file under ``project``.

    Returns:
        The status without a ``SCIP:`` label, or None when the project has no
        table and no ``Cargo.toml`` (not a Rust workspace). The text never
        holds ``|`` or ``!`` (the batch launcher splits on ``|`` and expands ``!``).
    """
    manifest_path = scip_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        return "NONE" if (project / "Cargo.toml").is_file() else None
    refs = ScipRefs.open(scip_dir)
    if refs is None:
        if not (scip_dir / REFS_NAME).is_file():
            return "INCOMPLETE (no reference table) - run Make SCIP Index"
        return "UNREADABLE - run Make SCIP Index"
    try:
        created = datetime.fromisoformat(
            json.loads(manifest_path.read_text(encoding="utf-8"))["created"]
        )
    except (OSError, ValueError, KeyError, TypeError):
        created = None
    try:
        covered = {p for p in refs.hashed_files if refs.has_rows(p)}
        if indexed is None:
            on_disk = hash_rust_files(project)
        else:
            # Hash only what the graph can see: no walk into worktrees or
            # excluded folders (hyprzero: 4,430 indexed of 32,634 .rs files).
            on_disk = _hash_files(project, indexed)
            covered &= indexed
        # Compare against the hashes just taken: no second read of each file,
        # and the project on disk is the one checked (not the manifest's path).
        changed = sum(
            1 for p in covered if p in on_disk and on_disk[p] != refs.recorded_hash(p)
        )
        removed = sum(1 for p in covered if p not in on_disk)
        new = sum(1 for p in on_disk if not refs.is_hashed(p))
        # The files the status checked: with the index filter, worktree copies
        # and excluded folders are not shown in the count either.
        hashed = len(
            refs.hashed_files if indexed is None else refs.hashed_files & indexed
        )
    finally:
        refs.close()

    made = _local_minute(created) if created is not None else "an unknown time"
    if changed or removed or new:
        text = f"STALE - {changed} changed, {new} new, {removed} removed since {made}"
    else:
        text = f"CURRENT (made {made}, {hashed} .rs files)"
    if not rust_scip:
        return text + SCIP_OFF_HINT
    if (
        created is not None
        and last_indexed is not None
        and created.astimezone() > last_indexed.astimezone()
    ):
        return text + REINDEX_HINT
    return text
