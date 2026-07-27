"""Integration tests for GLSL call-graph resolution (Phase 2).

Mirrors ``tests/fast_integration/test_call_graph_resolution.py`` (the Python
call-graph resolution integration suite) for GLSL's much narrower call
surface: no classes, no dynamic dispatch, no recursion — calls resolve
statically by name within a translation unit, with GLSL builtins and (by
default) TouchDesigner's TD-prefixed globals filtered out in
``GLSLChunker._extract_call_metadata`` before a caller's ``calls`` list is
even built (see ``chunking/languages/glsl.py::_is_call_noise``).

Fixtures live in ``tests/fixtures/mini_shader_repo/`` — the GLSL analogue of
``tests/fixtures/mini_repo/`` (the sole existing call-edge fixture).

Five minimum cases (from the GLSL parity plan):
1. A user-defined helper (``roundedBoxSDF``-shaped) appears as a callee of
   ``main``; no builtin call (``abs``, ``length``, ``max``, the ``vec3``/
   ``vec4`` type constructors) produces an edge.
2. Two files each defining ``main`` (and a same-named local helper,
   ``process``) — each resolves to its own file's helper, not a cross-file
   ambiguity.
3. A builtin-only function body (``roundedBoxSDF`` itself) yields exactly
   zero call edges — not a crash, not a silently-missing ``calls`` key.
4. A nested call — ``helper(vec3(1.0, dot(a, b), 2.0))`` — yields exactly one
   edge (to ``helper``), with the nested ``dot``/``vec3`` builtin targets
   correctly dropped regardless of nesting depth.
5. Negative TD-filter cases: ``td_helper`` (lowercase — fails the ``TD``
   prefix match) and a bare function literally named ``TD`` (length 2 — fails
   the ``len(name) > 2`` guard) must both survive as real call edges, not be
   silently dropped as TouchDesigner builtins.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from graph.graph_storage import CodeGraphStorage
from search.graph_integration import GraphIntegration
from search.metadata import MetadataStore


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "mini_shader_repo"


class _ReloadedResult:
    """Minimal EmbeddingResult-shaped wrapper, mirrors test_resolution_roundtrip.py."""

    def __init__(self, chunk_id: str, metadata: dict) -> None:
        self.chunk_id = chunk_id
        self.metadata = metadata


class _GLSLGraphHarness:
    """Chunk real GLSL files, persist through the real metadata shape, reload,
    and build the call graph from the reloaded data — exercising the same
    extract -> persist -> reload -> resolve seam as the Python roundtrip
    harness, for GLSL's ast-only (non-resolver) edge path.
    """

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path
        self.chunker = MultiLanguageChunker(root_path=str(project_path))
        db_dir = project_path / ".index"
        db_dir.mkdir(parents=True, exist_ok=True)
        self.store = MetadataStore(db_dir / "metadata.db")
        self.graph_storage = CodeGraphStorage(
            project_id="glsl_resolution", storage_dir=project_path / ".graph"
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

    def resolved_chunk_id(self, chunk_id_suffix: str) -> str:
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
        caller_id = self.resolved_chunk_id(chunk_id_suffix)
        return list(self.graph_storage.get_callees(caller_id))

    def teardown(self) -> None:
        self.store.close()


def _make_harness(tmp_path: Path) -> _GLSLGraphHarness:
    import shutil

    project_dir = tmp_path / "mini_shader_repo"
    shutil.copytree(FIXTURES_DIR, project_dir)
    return _GLSLGraphHarness(project_dir)


class TestHelperResolutionAndBuiltinFiltering:
    """Cases 1 and 3: a user-defined helper resolves as a callee of main,
    while its own builtin-only body produces zero edges."""

    def test_main_calls_user_helper_not_builtins(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("effect_a.glsl")
            h.build_graph_from_persisted()

            sdf_id = h.resolved_chunk_id("effect_a.glsl:3-6:function:roundedBoxSDF")
            process_id = h.resolved_chunk_id("effect_a.glsl:8-10:function:process")
            callees = h.callees_of(":function:main")

            assert sdf_id in callees, f"expected roundedBoxSDF among {callees}"
            assert process_id in callees, f"expected process among {callees}"
            # No builtin (abs/length/max/vec3/vec4) may appear as a callee.
            for builtin in ("abs", "length", "max", "vec3", "vec4"):
                assert not any(c.endswith(f":{builtin}") for c in callees), (
                    f"builtin {builtin!r} leaked into main's callees: {callees}"
                )
        finally:
            h.teardown()

    def test_builtin_only_function_has_zero_callees(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("effect_a.glsl")
            h.build_graph_from_persisted()

            callees = h.callees_of("effect_a.glsl:3-6:function:roundedBoxSDF")
            assert callees == [], (
                f"roundedBoxSDF's body is builtin-only (abs/length/max) — "
                f"expected zero callees, got {callees}"
            )
        finally:
            h.teardown()


class TestTwoFileMainCollision:
    """Case 2: two files each define main() and a same-named local helper
    (process) — each main must resolve to its own file's process, not
    fan out ambiguously across files."""

    def test_each_main_resolves_to_its_own_file_process(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("effect_a.glsl")
            h.index_file("effect_b.glsl")
            h.build_graph_from_persisted()

            a_process_id = h.resolved_chunk_id("effect_a.glsl:8-10:function:process")
            b_process_id = h.resolved_chunk_id("effect_b.glsl:3-5:function:process")
            assert a_process_id != b_process_id

            a_main_callees = h.callees_of("effect_a.glsl:12-16:function:main")
            b_main_callees = h.callees_of("effect_b.glsl:7-10:function:main")

            assert a_process_id in a_main_callees, (
                f"effect_a's main must call its own process, got {a_main_callees}"
            )
            assert b_process_id not in a_main_callees, (
                f"effect_a's main must not resolve to effect_b's process, "
                f"got {a_main_callees}"
            )
            assert b_process_id in b_main_callees, (
                f"effect_b's main must call its own process, got {b_main_callees}"
            )
            assert a_process_id not in b_main_callees, (
                f"effect_b's main must not resolve to effect_a's process, "
                f"got {b_main_callees}"
            )
        finally:
            h.teardown()


class TestNestedCallExtraction:
    """Case 4: a user call nested inside another user call's argument list."""

    def test_nested_builtin_dropped_user_call_kept(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("nested.glsl")
            h.build_graph_from_persisted()

            helper_id = h.resolved_chunk_id("nested.glsl:4-6:function:helper")
            callees = h.callees_of(":function:main")

            assert callees == [helper_id], (
                f"expected exactly one edge to helper, got {callees}"
            )
        finally:
            h.teardown()


class TestTDPrefixNegativeCases:
    """Case 5: names that superficially resemble the TD-prefix pattern but
    fail the actual rule must be kept, not filtered."""

    def test_lowercase_td_and_bare_td_survive(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("td_negative.glsl")
            h.build_graph_from_persisted()

            td_helper_id = h.resolved_chunk_id(
                "td_negative.glsl:4-6:function:td_helper"
            )
            td_id = h.resolved_chunk_id("td_negative.glsl:8-10:function:TD")
            callees = h.callees_of(":function:main")

            assert td_helper_id in callees, (
                f"td_helper (lowercase) must not be filtered, got {callees}"
            )
            assert td_id in callees, (
                f"bare TD (len 2) must not be filtered, got {callees}"
            )
        finally:
            h.teardown()


class TestNonSemanticRelationshipCarriers:
    """GLSL include/macro chunks are not SEMANTIC_TYPES, but they carry
    imports/defines_constant relationship edges — those must survive the
    persisted populate_from_embeddings path via _make_spec_from_embedding's
    escape hatch (parity with add_chunk), not be dropped at spec-build time."""

    def test_include_and_macro_edges_survive_roundtrip(self, tmp_path):
        h = _make_harness(tmp_path)
        try:
            h.index_file("includes.glsl")
            h.build_graph_from_persisted()

            include_id = h.resolved_chunk_id("includes.glsl:2-3:include:common.glslinc")
            macro_id = h.resolved_chunk_id("includes.glsl:5-6:macro:GAIN")

            graph = h.graph_storage.graph
            assert graph.has_edge(include_id, "common.glslinc"), (
                "include chunk's imports edge missing after "
                "populate_from_embeddings roundtrip"
            )
            assert graph.has_edge(macro_id, "GAIN"), (
                "macro chunk's defines_constant edge missing after "
                "populate_from_embeddings roundtrip"
            )

            edge_types = {
                data.get("type")
                for _, _, data in graph.out_edges(include_id, data=True)
            }
            assert "imports" in edge_types, (
                f"expected an 'imports' edge from the include chunk, "
                f"got edge types {edge_types}"
            )

            # Semantic chunks in the same file are unaffected by the hatch:
            # main's call edge to boost still resolves.
            boost_id = h.resolved_chunk_id("includes.glsl:7-9:function:boost")
            assert boost_id in h.callees_of(":function:main")
        finally:
            h.teardown()
