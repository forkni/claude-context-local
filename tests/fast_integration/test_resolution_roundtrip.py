"""Fast-integration test: extract -> persist -> reload -> resolve roundtrip.

Closes the one seam no other test covers end-to-end: real AST extraction
(``PythonCallGraphExtractor``, via ``MultiLanguageChunker``) -> the real
persisted ``ChunkMetadata`` shape (``CodeEmbedder._build_chunk_metadata``) ->
a real ``MetadataStore`` (SqliteDict, JSON-encoded, ``content`` stripped like
production) -> reload -> ``GraphIntegration.populate_from_embeddings`` ->
``_two_pass_build`` -> ``_resolve_call_target``.

This is the boundary the ``callee_qualified`` schema change rides (Part 1/2
of the call-graph-resolution deepening) and where the original
``_smart_dedent`` alias-blindness bug lived. Before this deepening, a bare
name defined in more than one module fans out to *every* same-named
candidate as an ``ambiguous`` edge, because ``CallEdge.callee_name`` alone
carries no import scope. ``callee_qualified`` lets scope-aware resolution
collapse that fan-out to the one edge the caller's own imports actually
point at.

No embedding model is required -- graph build works from persisted specs,
not vectors -- so this stays in ``fast_integration``.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from graph.graph_storage import CodeGraphStorage
from search.graph_integration import GraphIntegration
from search.metadata import MetadataStore


class _ReloadedResult:
    """Minimal EmbeddingResult-shaped wrapper around a reloaded metadata dict.

    ``populate_from_embeddings`` only touches ``.chunk_id`` and ``.metadata``
    (a plain dict) -- it never reads the embedding vector -- so this is
    sufficient to drive the real graph-build pipeline from persisted-and
    -reloaded data without a model.
    """

    def __init__(self, chunk_id: str, metadata: dict) -> None:
        self.chunk_id = chunk_id
        self.metadata = metadata


class _RoundtripHarness:
    """Chunk real files on disk, persist metadata through a real
    ``MetadataStore``, reload it, and build the call graph from the reloaded
    data -- exercising the exact seam extract -> persist -> reload -> resolve.
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.chunker = MultiLanguageChunker(root_path=str(project_path))
        db_dir = project_path / ".index"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.store = MetadataStore(db_dir / "metadata.db")
        self.graph_storage = CodeGraphStorage(
            project_id="roundtrip", storage_dir=project_path / ".graph"
        )
        self.graph = GraphIntegration.from_storage(self.graph_storage)

    def index_file(self, relative_name: str) -> None:
        """Chunk one file and persist its chunks through the real metadata shape."""
        chunks = self.chunker.chunk_file(str(self.project_path / relative_name))
        for i, chunk in enumerate(chunks):
            chunk_id = CodeEmbedder._build_chunk_id(chunk)
            metadata = CodeEmbedder._build_chunk_metadata(chunk)
            # MetadataStore persistence strips full content -- only
            # content_preview survives on disk (#55). Mirror that here so the
            # reload step sees exactly what production sees.
            metadata.pop("content", None)
            self.store.set(chunk_id, i, metadata)
        self.store.commit()

    def reloaded_calls(self, chunk_id_suffix: str) -> list[dict]:
        """Return the persisted+reloaded ``calls`` list for one chunk_id,
        matched by suffix for test-fixture convenience."""
        matches = [
            chunk_id
            for chunk_id in self.store.keys()  # noqa: SIM118 -- MetadataStore has no __iter__
            if chunk_id.endswith(chunk_id_suffix)
        ]
        assert len(matches) == 1, (
            f"Expected exactly one persisted chunk ending in {chunk_id_suffix!r}, "
            f"got {matches}"
        )
        return self.store.get_chunk_metadata(matches[0])["calls"]

    def build_graph_from_persisted(self) -> None:
        """Reload every persisted chunk and rebuild the graph from it."""
        results = [
            _ReloadedResult(chunk_id, entry["metadata"])
            for chunk_id, entry in self.store.items()
        ]
        self.graph.populate_from_embeddings(results)

    def resolved_chunk_id(self, chunk_id_suffix: str) -> str:
        """Return the single node chunk_id ending in the given suffix."""
        matches = [
            node
            for node in self.graph_storage.graph.nodes
            if node.endswith(chunk_id_suffix)
        ]
        assert len(matches) == 1, (
            f"Expected exactly one graph node ending in {chunk_id_suffix!r}, "
            f"got {matches}"
        )
        return matches[0]

    def callees_of(self, chunk_id_suffix: str) -> list[str]:
        """Return callee chunk_ids/names for the caller matched by suffix."""
        caller_id = self.resolved_chunk_id(chunk_id_suffix)
        return list(self.graph_storage.get_callees(caller_id))

    def confidence(self, caller_suffix: str, callee_id: str) -> str | None:
        """Return the edge confidence tag for one resolved caller->callee pair."""
        caller_id = self.resolved_chunk_id(caller_suffix)
        data = self.graph_storage.get_edge_data(caller_id, callee_id)
        return data.get("confidence") if data else None

    def teardown(self) -> None:
        self.store.close()


def _make_harness(tmp_path: Path) -> _RoundtripHarness:
    return _RoundtripHarness(tmp_path)


class TestCrossModuleScopeDisambiguation:
    """The proof test the deepening unlocks: two same-named functions in
    different modules, imported (one aliased) into a third module, must
    resolve to the *correct* distinct definitions -- not an ambiguous
    fan-out to both.
    """

    def _write_fixtures(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def helper():\n    return 'a'\n")
        (tmp_path / "b.py").write_text("def helper():\n    return 'b'\n")
        (tmp_path / "c.py").write_text(
            "from a import helper\n"
            "from b import helper as h\n"
            "\n"
            "\n"
            "def caller():\n"
            "    helper()\n"
            "    h()\n"
        )

    def test_callee_qualified_survives_persist_reload(self, tmp_path):
        """Part 1/2: callee_qualified must round-trip through the exact
        persisted metadata shape (CallEdge.to_dict() -> MetadataStore ->
        SqliteDict/JSON -> reload) with no schema change required."""
        self._write_fixtures(tmp_path)
        h = _make_harness(tmp_path)
        try:
            h.index_file("a.py")
            h.index_file("b.py")
            h.index_file("c.py")

            calls = h.reloaded_calls(":function:caller")
            by_name_order = {c["line_number"]: c for c in calls}
            qualified_values = sorted(
                c.get("callee_qualified") for c in by_name_order.values()
            )
            assert qualified_values == ["a.helper", "b.helper"], (
                f"Expected callee_qualified for both calls, got: {calls}"
            )
        finally:
            h.teardown()

    def test_both_calls_resolve_to_correct_module_exact(self, tmp_path):
        self._write_fixtures(tmp_path)
        h = _make_harness(tmp_path)
        try:
            h.index_file("a.py")
            h.index_file("b.py")
            h.index_file("c.py")
            h.build_graph_from_persisted()

            a_helper_id = h.resolved_chunk_id("a.py:1-2:function:helper")
            b_helper_id = h.resolved_chunk_id("b.py:1-2:function:helper")

            callees = h.callees_of(":function:caller")
            assert a_helper_id in callees, (
                f"Expected {a_helper_id} among callees, got {callees}"
            )
            assert b_helper_id in callees, (
                f"Expected {b_helper_id} among callees, got {callees}"
            )

            caller_suffix = ":function:caller"
            assert h.confidence(caller_suffix, a_helper_id) == "exact"
            assert h.confidence(caller_suffix, b_helper_id) == "exact"
        finally:
            h.teardown()


class TestBareLocalSameFileResolution:
    """Regression: a bare (non-imported) call to a locally-defined function
    that shares its name with definitions in other modules must resolve via
    same-file preference, not fan out ambiguously. This is the same
    resolution machinery the `check_match` / `normalize_chunk_id` live case
    depends on (bare-local call, no import to carry a qualified name).
    """

    def test_bare_local_call_resolves_to_own_file_not_ambiguous(self, tmp_path):
        (tmp_path / "a.py").write_text("def helper():\n    return 'a'\n")
        (tmp_path / "b.py").write_text("def helper():\n    return 'b'\n")
        (tmp_path / "d.py").write_text(
            "def helper():\n"
            "    return 'd'\n"
            "\n"
            "\n"
            "def uses_local_helper():\n"
            "    helper()\n"
        )
        h = _make_harness(tmp_path)
        try:
            h.index_file("a.py")
            h.index_file("b.py")
            h.index_file("d.py")
            h.build_graph_from_persisted()

            d_helper_id = h.resolved_chunk_id("d.py:1-2:function:helper")
            callees = h.callees_of(":function:uses_local_helper")

            assert callees == [d_helper_id], (
                f"Expected bare local call to resolve only to {d_helper_id}, "
                f"got {callees}"
            )
            assert h.confidence(":function:uses_local_helper", d_helper_id) == "exact"
        finally:
            h.teardown()


class TestBuiltinFalsePositiveGuard:
    """Regression: calls to builtins/common stdlib methods must not produce a
    false 'recovered'/'ambiguous' edge to an unrelated project chunk."""

    def test_builtin_call_stays_phantom_not_ambiguous(self, tmp_path):
        (tmp_path / "e.py").write_text(
            "def uses_builtin():\n    return len([1, 2, 3])\n"
        )
        h = _make_harness(tmp_path)
        try:
            h.index_file("e.py")
            h.build_graph_from_persisted()

            callees = h.callees_of(":function:uses_builtin")
            assert callees == ["len"], (
                f"Expected only the phantom 'len' node, got {callees}"
            )
            conf = h.confidence(":function:uses_builtin", "len")
            assert conf != "ambiguous", f"builtin call falsely tagged ambiguous: {conf}"
        finally:
            h.teardown()
