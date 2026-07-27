"""Regression tests for GLSL's anonymous layout-qualifier parse-error fix (Phase 1d).

`tree-sitter-glsl` hard-errors on the anonymous layout qualifier form used by
compute and geometry shaders (`layout(local_size_x = 16, local_size_y = 16) in;`,
`layout(triangles) in;`), and the resulting ERROR node swallows every function
defined *after* it -- verified on a real geometry shader while building this
GLSL-parity effort: only `main` survived, `emit_verts`/`tail` both vanished.

`GLSLChunker.preprocess_source_for_parse` (chunking/languages/glsl.py) neutralizes
this by rewriting the anonymous-qualifier statement into a length-preserving block
comment before parsing, so byte offsets and line numbers stay correct for every
chunk. These tests pin that fix using the two shader stages that actually trigger
it -- neither is covered by `tests/unit/chunking/test_multi_language.py`'s
`.glsl`-only smoke test.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker


TEST_DATA_DIR = Path(__file__).parent.parent.parent / "test_data" / "glsl_project"


def _function_names(chunks):
    return {c.name for c in chunks if c.chunk_type == "function" and c.name}


def test_compute_shader_recovers_functions_after_local_size_layout():
    """`layout(local_size_x = 16, local_size_y = 16) in;` must not swallow `brighten`."""
    file_path = TEST_DATA_DIR / "compute_shader.comp"
    chunker = MultiLanguageChunker(root_path=str(TEST_DATA_DIR))
    chunks = chunker.chunk_file(str(file_path))

    names = _function_names(chunks)
    assert names == {"brighten", "main"}, (
        f"expected both functions recovered after the anonymous layout "
        f"qualifier, got {names}"
    )

    # brighten() must call user code correctly (imageLoad/imageStore are
    # builtins and must not appear), confirming the function bodies parsed
    # correctly, not just their signatures.
    main_chunk = next(c for c in chunks if c.name == "main")
    callee_names = {call.callee_name for call in main_chunk.calls}
    assert callee_names == {"brighten"}, (
        f"expected only the user call to brighten(), got {callee_names}"
    )


def test_geometry_shader_recovers_functions_after_triangles_layout():
    """`layout(triangles) in;` / `layout(triangle_strip, ...) out;` must not
    swallow emitVerts/tail -- the exact regression shape measured on a real
    geometry shader (only `main` survived without the Phase 1d fix)."""
    file_path = TEST_DATA_DIR / "geometry_shader.geom"
    chunker = MultiLanguageChunker(root_path=str(TEST_DATA_DIR))
    chunks = chunker.chunk_file(str(file_path))

    names = _function_names(chunks)
    assert names == {"emitVerts", "tail", "main"}, (
        f"expected all three functions recovered after the anonymous layout "
        f"qualifiers, got {names}"
    )

    # Confirm the call chain main -> tail -> emitVerts survived intact, which
    # only holds if every function body (not just its signature) parsed
    # correctly after the neutralized layout lines.
    by_name = {c.name: c for c in chunks if c.name in names}
    assert {call.callee_name for call in by_name["main"].calls} == {"tail"}
    assert {call.callee_name for call in by_name["tail"].calls} == {"emitVerts"}
    assert by_name["emitVerts"].calls == []
