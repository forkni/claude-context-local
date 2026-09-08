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
