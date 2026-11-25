"""Integration tests for Rust call-graph resolution (openheizenberg Phase 4).

Mirrors ``tests/fast_integration/test_glsl_call_graph_resolution.py`` (the
GLSL call-graph resolution integration suite) for Rust's Wall-2 resolution
rules in ``search/graph_integration.py``: the qualified-first lookup
(``self.``/``Type::``/``Self::`` calls resolve through their ``Parent::name``
spelling ahead of bare-name matching), and the confidence-tagging divergence
from C-family (a method call that resolved through its qualified spelling
stays ``"exact"``; every other method call is downgraded to ``"ambiguous"``).

``tests/unit/chunking/test_rust_relationships.py`` already characterizes
every call-site shape and relationship type in a single file via
``MultiLanguageChunker`` output directly. This suite instead exercises the
same chunk-extract -> persist -> reload -> resolve seam
``test_glsl_call_graph_resolution.py`` uses, across **multiple files** --
none of the existing Rust fixtures (``tests/fixtures/chunker_corpus/sample.rs``,
the single-file fixture in the unit test above) exercise cross-module
resolution, since Pass-1's ``name_to_chunk_ids`` map is built globally across
every indexed chunk regardless of which file it came from.

Fixtures live in ``tests/fixtures/mini_rust_repo/`` -- three files using
Rust's normal per-file module layout (``mod geometry;`` / ``mod shapes;`` in
``main.rs``, each pointing at a same-named sibling file, not an inline
``mod { ... }`` block):

- ``geometry.rs``: ``struct Point`` + ``impl Point`` (``new``, ``magnitude``,
  private ``magnitude_sq``) and a free function ``origin()``.
- ``shapes.rs``: ``struct Circle`` + ``impl Circle`` (``new``, ``area``).
- ``main.rs``: ``describe_point(&Point)`` (calls ``p.magnitude()``, an
  "other receiver" method call) and ``run()`` (calls ``geometry::origin()``,
  ``Point::new(..)``, ``Circle::new(..)``, ``describe_point(&p)``, and
  ``c.area()``).

Four cases:
1. ``Point::new``/``Circle::new`` -- both named ``new``, defined in
   different files -- resolve to the correct file's definition via the
   qualified-first lookup, not the (ambiguous, 2-candidate) bare name.
2. ``c.area()``/``p.magnitude()`` -- "other receiver" method calls with no
   ``callee_qualified`` -- resolve cross-file via bare-name uniqueness, but
   are tagged ``"ambiguous"`` (hidden by default).
3. ``geometry::origin()`` -- a mod-qualified free-function call whose
   ``callee_qualified`` (``"geometry::origin"``) does NOT match any indexed
   key (Rust's file-based module system carries no ``parent_name``
   association back to the declaring ``mod geometry;`` statement) -- falls
   through to, and resolves via, ordinary bare-name uniqueness, tagged
   ``"exact"`` (never downgraded: it is not a method call).
4. ``self.magnitude_sq()`` inside ``Point::magnitude`` -- a same-file
   self-receiver call -- resolves through the qualified-first lookup and
   stays ``"exact"`` despite being a method call, the Wall-2 item-6
   divergence from C-family's blanket downgrade.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from graph.graph_storage import CodeGraphStorage
from search.graph_integration import GraphIntegration
from search.metadata import MetadataStore


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "mini_rust_repo"


class _ReloadedResult:
    """Minimal EmbeddingResult-shaped wrapper, mirrors test_resolution_roundtrip.py."""

    def __init__(self, chunk_id: str, metadata: dict) -> None:
        self.chunk_id = chunk_id
        self.metadata = metadata


class _RustGraphHarness:
    """Chunk real Rust files, persist through the real metadata shape,
    reload, and build the call graph from the reloaded data -- exercising
    the same extract -> persist -> reload -> resolve seam as the Python and
    GLSL roundtrip harnesses."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.chunker = MultiLanguageChunker(root_path=str(project_path))
        db_dir = project_path / ".index"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.store = MetadataStore(db_dir / "metadata.db")
        self.graph_storage = CodeGraphStorage(
            project_id="rust_resolution", storage_dir=project_path / ".graph"
        )
        self.graph = GraphIntegration.from_storage(self.graph_storage)

    def index_file(self, relative_name: str) -> None:
        chunks = self.chunker.chunk_file(str(self.project_path / relative_name))
        for i, chunk in enumerate(chunks):
            chunk_id = CodeEmbedder._build_chunk_id(chunk)
            metadata = CodeEmbedder._build_chunk_metadata(chunk)
            metadata.pop("content", None)
            self.store.set(chunk_id, i, metadata)
        self.store.commit()

    def build_graph_from_persisted(self) -> None:
        results = [
            _ReloadedResult(chunk_id, entry["metadata"])
            for chunk_id, entry in self.store.items()
        ]
        self.graph.populate_from_embeddings(results)

    def resolved_chunk_id(self, file: str, chunk_type: str, name: str) -> str:
        """Find the one node whose file portion is `file`, chunk_type
        matches, and whose trailing name segment matches `name` -- avoids
        hardcoding exact line ranges (unlike the GLSL harness), since
        disambiguating `new` across two files only needs file + type + name,
        not line numbers.

        Method chunk_ids are qualified `Parent.name` (e.g. `Point.new`, per
        the chunker's C-family-style method naming), not bare `name`, so a
        method lookup matches on the ``.name`` suffix of the trailing
        segment rather than an exact match."""
        prefix = f"{file}:"
        type_marker = f":{chunk_type}:"
        matches = []
        for node in self.graph_storage.graph.nodes:
            if not node.startswith(prefix) or type_marker not in node:
                continue
            trailing = node.rsplit(":", 1)[-1]
            if trailing == name or trailing.endswith(f".{name}"):
                matches.append(node)
        assert len(matches) == 1, (
            f"Expected exactly one graph node in {file!r} of type "
            f"{chunk_type!r} named {name!r}, got {matches}"
        )
        return matches[0]

    def callees_of(self, file: str, chunk_type: str, name: str) -> list[str]:
        caller_id = self.resolved_chunk_id(file, chunk_type, name)
        return list(self.graph_storage.get_callees(caller_id))

    def call_edge_confidence(self, caller_id: str, callee_id: str) -> str | None:
        data = self.graph_storage.graph.get_edge_data(caller_id, callee_id, key="calls")
        assert data is not None, f"no 'calls' edge from {caller_id} to {callee_id}"
        return data.get("confidence")

    def teardown(self) -> None:
        self.store.close()


def _make_harness(tmp_path: Path) -> _RustGraphHarness:
    import shutil

    project_dir = tmp_path / "mini_rust_repo"
    shutil.copytree(FIXTURES_DIR, project_dir)
    return _RustGraphHarness(project_dir)


def _index_all(h: _RustGraphHarness) -> None:
    h.index_file("geometry.rs")
    h.index_file("shapes.rs")
    h.index_file("main.rs")
    h.build_graph_from_persisted()


class TestCrossFileQualifiedFirstLookup:
    """Case 1: `Point::new`/`Circle::new` resolve to the correct file's
    definition via the qualified-first lookup (Wall-2 item 3), not the
    (ambiguous, 2-candidate) bare name `new`."""

    def test_point_new_and_circle_new_resolve_to_their_own_file(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            point_new_id = h.resolved_chunk_id("geometry.rs", "method", "new")
            circle_new_id = h.resolved_chunk_id("shapes.rs", "method", "new")
            assert point_new_id != circle_new_id

            run_callees = h.callees_of("main.rs", "function", "run")
            assert point_new_id in run_callees, (
                f"run() must resolve Point::new to geometry.rs's definition, "
                f"got {run_callees}"
            )
            assert circle_new_id in run_callees, (
                f"run() must resolve Circle::new to shapes.rs's definition, "
                f"got {run_callees}"
            )

            run_id = h.resolved_chunk_id("main.rs", "function", "run")
            assert h.call_edge_confidence(run_id, point_new_id) == "exact"
            assert h.call_edge_confidence(run_id, circle_new_id) == "exact"
        finally:
            h.teardown()


class TestCrossFileOtherReceiverMethodCalls:
    """Case 2: `c.area()`/`p.magnitude()` -- no `callee_qualified` -- resolve
    cross-file via bare-name uniqueness, but are tagged "ambiguous" (Wall-2
    item 6: they did not resolve through a qualified spelling)."""

    def test_circle_area_resolves_ambiguous(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            area_id = h.resolved_chunk_id("shapes.rs", "method", "area")
            run_id = h.resolved_chunk_id("main.rs", "function", "run")
            run_callees = h.callees_of("main.rs", "function", "run")

            assert area_id in run_callees, (
                f"run() must resolve c.area() to Circle::area, got {run_callees}"
            )
            assert h.call_edge_confidence(run_id, area_id) == "ambiguous"
        finally:
            h.teardown()

    def test_point_magnitude_resolves_ambiguous_across_files(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            magnitude_id = h.resolved_chunk_id("geometry.rs", "method", "magnitude")
            describe_id = h.resolved_chunk_id("main.rs", "function", "describe_point")
            describe_callees = h.callees_of("main.rs", "function", "describe_point")

            assert magnitude_id in describe_callees, (
                f"describe_point() must resolve p.magnitude() to Point::magnitude "
                f"across files, got {describe_callees}"
            )
            assert h.call_edge_confidence(describe_id, magnitude_id) == "ambiguous"
        finally:
            h.teardown()


class TestModQualifiedFreeFunctionFallsThroughToBareName:
    """Case 3: `geometry::origin()` -- Rust's file-based module system means
    `origin`'s chunk carries no `parent_name` tying it to "geometry", so the
    qualified-first lookup's key ("geometry::origin") is never indexed. The
    call falls through to, and resolves via, ordinary bare-name uniqueness
    -- tagged "exact" since it's a free-function call (`is_method_call`
    always False for a `scoped_identifier` call site), never subject to the
    method-call downgrade regardless of resolution path."""

    def test_mod_scoped_call_resolves_via_bare_name_fallback(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            origin_id = h.resolved_chunk_id("geometry.rs", "function", "origin")
            run_id = h.resolved_chunk_id("main.rs", "function", "run")
            run_callees = h.callees_of("main.rs", "function", "run")

            assert origin_id in run_callees, (
                f"run() must resolve geometry::origin() via bare-name "
                f"fallback, got {run_callees}"
            )
            assert h.call_edge_confidence(run_id, origin_id) == "exact"
        finally:
            h.teardown()

    def test_describe_point_call_resolves_same_file(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            describe_id = h.resolved_chunk_id("main.rs", "function", "describe_point")
            run_callees = h.callees_of("main.rs", "function", "run")

            assert describe_id in run_callees, (
                f"run() must resolve its own describe_point(&p) call, got {run_callees}"
            )
        finally:
            h.teardown()


_WS_FILES = {
    "Cargo.toml": '[workspace]\nmembers = ["lib", "app"]\n',
    "lib/Cargo.toml": '[package]\nname = "lib"\n',
    "lib/src/lib.rs": (
        "pub mod a;\npub mod b;\npub mod c;\n\n"
        "pub struct Arc;\n\nimpl Arc {\n    pub fn new() -> Self {\n        Arc\n    }\n}\n\n"
        "pub struct NodeState;\n"
    ),
    "lib/src/a.rs": "pub fn mix() {}\n",
    "lib/src/b.rs": "pub fn mix() {}\n",
    "lib/src/c.rs": "pub fn mix() {}\n\npub fn solo() {}\n",
    "app/Cargo.toml": '[package]\nname = "app"\n\n[dependencies]\nlib = { path = "../lib" }\n',
    "app/src/main.rs": (
        "use lib::b::mix;\nuse lib::NodeState;\nuse std::sync::Arc;\n\n"
        "fn run() {\n"
        "    mix();\n"
        "    Arc::new();\n"
        "    NodeState::default();\n"
        "    lib::a::solo();\n"
        "}\n\n"
        "fn main() {\n    run();\n}\n"
    ),
}


def _use_path_graph(tmp_path: Path, monkeypatch, *, enabled: bool) -> _RustGraphHarness:
    from search import graph_integration
    from search.config import SearchConfig

    config = SearchConfig()
    config.call_graph.rust_use_paths = enabled
    monkeypatch.setattr(graph_integration, "get_search_config", lambda: config)
    root = tmp_path / "ws"
    for rel, text in _WS_FILES.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    h = _RustGraphHarness(root)
    for rel in (
        "lib/src/lib.rs",
        "lib/src/a.rs",
        "lib/src/b.rs",
        "lib/src/c.rs",
        "app/src/main.rs",
    ):
        h.index_file(rel)
    h.build_graph_from_persisted()
    return h


def _calls_of(h: _RustGraphHarness, caller_id: str) -> dict[str, dict]:
    graph = h.graph_storage.graph
    return {
        target: dict(data)
        for _, target, key, data in graph.out_edges(caller_id, keys=True, data=True)
        if key == "calls"
    }


class TestRustUsePathResolution:
    """ADR-0091 "D": `use` imports and the module tree pick or refuse targets."""

    def test_imported_free_function_picks_the_imported_module(
        self, tmp_path, monkeypatch
    ):
        h = _use_path_graph(tmp_path, monkeypatch, enabled=True)
        try:
            run_id = h.resolved_chunk_id("app/src/main.rs", "function", "run")
            b_mix = h.resolved_chunk_id("lib/src/b.rs", "function", "mix")
            calls = _calls_of(h, run_id)
            mixes = sorted(t for t in calls if t.endswith(":mix"))
            assert mixes == [b_mix], f"only lib::b::mix may be linked, got {mixes}"
            assert calls[b_mix]["confidence"] == "exact"
            assert calls[b_mix]["resolution"] == "rust_use"
        finally:
            h.teardown()

    def test_std_import_gets_no_edge_to_a_project_symbol(self, tmp_path, monkeypatch):
        h = _use_path_graph(tmp_path, monkeypatch, enabled=True)
        try:
            run_id = h.resolved_chunk_id("app/src/main.rs", "function", "run")
            arc_new = h.resolved_chunk_id("lib/src/lib.rs", "method", "new")
            assert arc_new not in _calls_of(h, run_id)
        finally:
            h.teardown()

    def test_missing_module_item_links_unique_crate_match(self, tmp_path, monkeypatch):
        h = _use_path_graph(tmp_path, monkeypatch, enabled=True)
        try:
            run_id = h.resolved_chunk_id("app/src/main.rs", "function", "run")
            solo = h.resolved_chunk_id("lib/src/c.rs", "function", "solo")
            calls = _calls_of(h, run_id)
            assert calls[solo]["resolution"] == "rust_use_fallback"
        finally:
            h.teardown()

    def test_knob_off_keeps_todays_edges(self, tmp_path, monkeypatch):
        h = _use_path_graph(tmp_path, monkeypatch, enabled=False)
        try:
            run_id = h.resolved_chunk_id("app/src/main.rs", "function", "run")
            arc_new = h.resolved_chunk_id("lib/src/lib.rs", "method", "new")
            calls = _calls_of(h, run_id)
            assert arc_new in calls, "today's tier links Arc::new to the project Arc"
            assert sum(t.endswith(":mix") for t in calls) == 3
            assert not any("resolution" in d for d in calls.values())
        finally:
            h.teardown()


_SCIP_WS_FILES = {
    "Cargo.toml": '[package]\nname = "ws"\n',
    "src/lib.rs": "pub mod a;\npub mod b;\npub mod c;\npub mod d;\npub mod e;\n",
    "src/e.rs": "pub fn helper() {}\n",
    "src/a.rs": "pub struct Alpha;\n\nimpl Alpha {\n    pub fn tick(&self) {}\n}\n",
    "src/b.rs": "pub struct Beta;\n\nimpl Beta {\n    pub fn tick(&self) {}\n}\n",
    "src/c.rs": "pub struct Gamma;\n\nimpl Gamma {\n    pub fn tick(&self) {}\n}\n",
    "src/d.rs": (
        "pub struct Stack;\n\nimpl Stack {\n    pub fn push(&mut self, x: i32) {}\n}\n"
    ),
    "src/main.rs": (
        "use ws::b::Beta;\n\n"
        "fn run(b: &Beta, v: &mut Vec<i32>) {\n"
        "    b.tick();\n"
        "    v.push(1);\n"
        "}\n\n"
        "fn main() {\n"
        "    helper();\n"
        "}\n\n"
        "fn helper() {}\n"
    ),
}
_BETA_TICK = "rust-analyzer cargo ws 0.1.0 b/impl#[Beta]tick()."
_ALPHA_TICK = "rust-analyzer cargo ws 0.1.0 a/impl#[Alpha]tick()."
_VEC_PUSH = "rust-analyzer cargo alloc https://x vec/impl#[`Vec<T, A>`]push()."
# One symbol string defined twice, as rust-analyzer does across tests/*.rs crates.
_HELPER = "rust-analyzer cargo ws 0.1.0 helper()."
_SYMBOLS = {
    _BETA_TICK: ("tick", [("src/b.rs", 4)]),
    _ALPHA_TICK: ("tick", [("src/a.rs", 4)]),
    _VEC_PUSH: ("push", []),
    _HELPER: ("helper", [("src/e.rs", 1), ("src/main.rs", 12)]),
}


def _write_scip_table(
    root: Path, scip_dir: Path, refs: list[tuple], symbols: dict | None = None
) -> None:
    """A refs.sqlite + manifest as tools/scip_index.py would write them."""
    import json
    import sqlite3

    from search.scip_refs import MANIFEST_NAME, REFS_NAME, hash_rust_files

    scip_dir.mkdir(parents=True, exist_ok=True)
    symbols = symbols or _SYMBOLS
    ids = {symbol: i for i, symbol in enumerate(symbols, start=1)}
    con = sqlite3.connect(scip_dir / REFS_NAME)
    con.execute("CREATE TABLE symbols(id INTEGER PRIMARY KEY, symbol TEXT, name TEXT)")
    con.execute("CREATE TABLE defs(symbol_id INT, file TEXT, line INT)")
    con.execute("CREATE TABLE refs(file TEXT, line INT, name TEXT, symbol_id INT)")
    con.executemany(
        "INSERT INTO symbols VALUES (?, ?, ?)",
        [(ids[s], s, name) for s, (name, _) in symbols.items()],
    )
    con.executemany(
        "INSERT INTO defs VALUES (?, ?, ?)",
        [(ids[s], f, line) for s, (_, defs) in symbols.items() for f, line in defs],
    )
    con.executemany(
        "INSERT INTO refs VALUES (?, ?, ?, ?)",
        [(file, line, symbols[s][0], ids[s]) for file, line, s in refs],
    )
    con.commit()
    con.close()
    manifest = {"format": 1, "project_path": str(root), "files": hash_rust_files(root)}
    (scip_dir / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")


_MAIN_REFS = [
    ("src/main.rs", 4, _BETA_TICK),
    ("src/main.rs", 5, _VEC_PUSH),
    ("src/main.rs", 9, _HELPER),
]


def _scip_graph(
    tmp_path: Path,
    monkeypatch,
    *,
    enabled: bool = True,
    refs: list[tuple] | None = None,
    symbols: dict | None = None,
    edit: dict[str, str] | None = None,
    files: dict[str, str] | None = None,
) -> _RustGraphHarness:
    """Build the SCIP workspace graph. ``files`` replaces workspace files
    before the table is written (fresh); ``edit`` changes them after (stale)."""
    from search import graph_integration
    from search.config import SearchConfig

    config = SearchConfig()
    config.call_graph.rust_scip = enabled
    monkeypatch.setattr(graph_integration, "get_search_config", lambda: config)
    root = tmp_path / "ws"
    for rel, text in {**_SCIP_WS_FILES, **(files or {})}.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    h = _RustGraphHarness(root)
    if refs is not None:
        _write_scip_table(root, root / ".graph" / "scip", refs, symbols)
    for rel, text in (edit or {}).items():
        (root / rel).write_text(text, encoding="utf-8")
    for rel in (
        "src/a.rs",
        "src/b.rs",
        "src/c.rs",
        "src/d.rs",
        "src/e.rs",
        "src/main.rs",
    ):
        h.index_file(rel)
    h.build_graph_from_persisted()
    return h


class TestRustScipResolution:
    """ADR-0092 "E": a SCIP reference table decides receiver calls."""

    def test_receiver_call_picks_the_scip_target(self, tmp_path, monkeypatch):
        h = _scip_graph(tmp_path, monkeypatch, refs=_MAIN_REFS)
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            beta = h.resolved_chunk_id("src/b.rs", "method", "tick")
            calls = _calls_of(h, run_id)
            ticks = sorted(t for t in calls if t.endswith(".tick"))
            assert ticks == [beta], f"only Beta::tick may be linked, got {ticks}"
            assert calls[beta]["confidence"] == "exact"
            assert calls[beta]["resolver_source"] == "scip"
            assert calls[beta]["resolution"] == "scip"
        finally:
            h.teardown()

    def test_receiver_call_split_over_two_lines_resolves(self, tmp_path, monkeypatch):
        """SCIP records `tick` on the line of the name; the chunker must too."""
        main = _SCIP_WS_FILES["src/main.rs"].replace(
            "    b.tick();\n", "    b\n        .tick();\n"
        )
        refs = [("src/main.rs", 5, _BETA_TICK), ("src/main.rs", 6, _VEC_PUSH)]
        h = _scip_graph(tmp_path, monkeypatch, refs=refs, files={"src/main.rs": main})
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            beta = h.resolved_chunk_id("src/b.rs", "method", "tick")
            calls = _calls_of(h, run_id)
            ticks = sorted(t for t in calls if t.endswith(".tick"))
            assert ticks == [beta], f"only Beta::tick may be linked, got {ticks}"
            assert calls[beta]["resolver_source"] == "scip"
        finally:
            h.teardown()

    _IN_ASSERT = {
        "src/main.rs": _SCIP_WS_FILES["src/main.rs"].replace(
            "    b.tick();\n", "    assert!(b.tick());\n"
        )
    }

    def _ticks(self, h) -> dict[str, dict]:
        run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
        return {t: d for t, d in _calls_of(h, run_id).items() if t.endswith("tick")}

    def test_call_inside_a_macro_resolves_through_scip(self, tmp_path, monkeypatch):
        h = _scip_graph(tmp_path, monkeypatch, refs=_MAIN_REFS, files=self._IN_ASSERT)
        try:
            beta = h.resolved_chunk_id("src/b.rs", "method", "tick")
            ticks = self._ticks(h)
            assert list(ticks) == [beta], f"only Beta::tick may be linked, got {ticks}"
            assert ticks[beta]["confidence"] == "exact"
            assert ticks[beta]["resolver_source"] == "scip_macro"
            assert ticks[beta]["resolution"] == "scip"
        finally:
            h.teardown()

    def test_macro_candidate_without_a_reference_gets_no_edge(
        self, tmp_path, monkeypatch
    ):
        """No SCIP reference: the candidate is dropped, not linked by name."""
        refs = [r for r in _MAIN_REFS if r[2] != _BETA_TICK]
        h = _scip_graph(tmp_path, monkeypatch, refs=refs, files=self._IN_ASSERT)
        try:
            assert self._ticks(h) == {}
        finally:
            h.teardown()

    def test_macro_candidate_with_scip_off_gets_no_edge(self, tmp_path, monkeypatch):
        h = _scip_graph(
            tmp_path, monkeypatch, enabled=False, refs=_MAIN_REFS, files=self._IN_ASSERT
        )
        try:
            assert self._ticks(h) == {}
        finally:
            h.teardown()

    def test_external_symbol_gets_no_project_edge(self, tmp_path, monkeypatch):
        h = _scip_graph(tmp_path, monkeypatch, refs=_MAIN_REFS)
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            stack_push = h.resolved_chunk_id("src/d.rs", "method", "push")
            assert stack_push not in _calls_of(h, run_id)
        finally:
            h.teardown()

    def test_without_table_the_name_tier_links_all_three(self, tmp_path, monkeypatch):
        h = _scip_graph(tmp_path, monkeypatch, refs=None)
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            calls = _calls_of(h, run_id)
            assert sum(t.endswith(".tick") for t in calls) == 3
            assert not any(d.get("resolver_source") == "scip" for d in calls.values())
        finally:
            h.teardown()

    def test_knob_off_ignores_the_table(self, tmp_path, monkeypatch):
        h = _scip_graph(tmp_path, monkeypatch, enabled=False, refs=_MAIN_REFS)
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            calls = _calls_of(h, run_id)
            assert sum(t.endswith(".tick") for t in calls) == 3
            assert not any(d.get("resolver_source") == "scip" for d in calls.values())
        finally:
            h.teardown()

    def test_edited_caller_falls_through(self, tmp_path, monkeypatch):
        edited = _SCIP_WS_FILES["src/main.rs"].replace(
            "fn helper() {}", "fn helper() { }"
        )
        h = _scip_graph(
            tmp_path, monkeypatch, refs=_MAIN_REFS, edit={"src/main.rs": edited}
        )
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            calls = _calls_of(h, run_id)
            assert sum(t.endswith(".tick") for t in calls) == 3
        finally:
            h.teardown()

    def test_edited_definition_falls_through(self, tmp_path, monkeypatch):
        edited = _SCIP_WS_FILES["src/b.rs"] + "// edited\n"
        h = _scip_graph(
            tmp_path, monkeypatch, refs=_MAIN_REFS, edit={"src/b.rs": edited}
        )
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            calls = _calls_of(h, run_id)
            assert sum(t.endswith(".tick") for t in calls) == 3
        finally:
            h.teardown()

    def test_two_symbols_on_one_line_fall_through(self, tmp_path, monkeypatch):
        refs = [*_MAIN_REFS, ("src/main.rs", 4, _ALPHA_TICK)]
        h = _scip_graph(tmp_path, monkeypatch, refs=refs)
        try:
            run_id = h.resolved_chunk_id("src/main.rs", "function", "run")
            calls = _calls_of(h, run_id)
            assert sum(t.endswith(".tick") for t in calls) == 3
        finally:
            h.teardown()


class TestSelfCallStaysExactAcrossFullPipeline:
    """Case 4: `self.magnitude_sq()` inside `Point::magnitude` resolves
    through the qualified-first lookup and stays "exact" despite being a
    method call -- reconfirming the Wall-2 item-6 divergence through the
    full extract -> persist -> reload -> resolve pipeline, not just the
    mocked unit test in test_graph_integration.py."""

    def test_self_receiver_call_stays_exact(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            _index_all(h)

            magnitude_id = h.resolved_chunk_id("geometry.rs", "method", "magnitude")
            magnitude_sq_id = h.resolved_chunk_id(
                "geometry.rs", "method", "magnitude_sq"
            )
            callees = h.callees_of("geometry.rs", "method", "magnitude")

            assert magnitude_sq_id in callees, (
                f"Point::magnitude must resolve self.magnitude_sq(), got {callees}"
            )
            assert h.call_edge_confidence(magnitude_id, magnitude_sq_id) == "exact"
        finally:
            h.teardown()

    def test_duplicate_symbol_uses_the_callers_own_definition(
        self, tmp_path, monkeypatch
    ):
        h = _scip_graph(tmp_path, monkeypatch, refs=_MAIN_REFS)
        try:
            main_id = h.resolved_chunk_id("src/main.rs", "function", "main")
            own = h.resolved_chunk_id("src/main.rs", "function", "helper")
            other = h.resolved_chunk_id("src/e.rs", "function", "helper")
            calls = _calls_of(h, main_id)
            assert own in calls and other not in calls, calls
            assert calls[own]["resolver_source"] == "scip"
        finally:
            h.teardown()

    def test_duplicate_symbol_elsewhere_falls_through(self, tmp_path, monkeypatch):
        symbols = dict(_SYMBOLS)
        symbols[_HELPER] = ("helper", [("src/e.rs", 1), ("src/a.rs", 1)])
        h = _scip_graph(tmp_path, monkeypatch, refs=_MAIN_REFS, symbols=symbols)
        try:
            main_id = h.resolved_chunk_id("src/main.rs", "function", "main")
            calls = _calls_of(h, main_id)
            assert not any(d.get("resolver_source") == "scip" for d in calls.values())
        finally:
            h.teardown()
