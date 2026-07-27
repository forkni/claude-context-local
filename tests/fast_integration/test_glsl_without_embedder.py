"""GLSL chunking works end-to-end without embedder dependencies.

Asserts the *content* of the chunker's output for every fixture in
``tests/test_data/glsl_project`` — named function chunks, builtin-filtered
call edges, and comment-docstring attachment — not just that some chunks
exist. The old ``total_chunks > 0`` assertion passed even under the
pre-parity chunker that produced unnamed blobs with no calls and no
docstrings.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker


PROJECT_PATH = Path(__file__).parent.parent / "test_data" / "glsl_project"

# Per-fixture expected function names (the parity-level contract: every
# function_definition becomes a named "function" chunk).
EXPECTED_FUNCTIONS = {
    "compute_shader.comp": {"brighten", "main"},
    "fragment_shader.frag": {"main"},
    "geometry_shader.geom": {"emitVerts", "tail", "main"},
    "simple_shader.glsl": {"hsv2rgb", "main"},
    "vertex_shader.vert": {"main"},
}

# User-function call edges expected per fixture, after GLSL builtin filtering
# (texture/imageLoad/imageStore/EmitVertex/EndPrimitive and vecN/ivecN type
# constructors must NOT survive as callees).
EXPECTED_CALLS = {
    "compute_shader.comp": {"main": ["brighten"]},
    "geometry_shader.geom": {"tail": ["emitVerts"], "main": ["tail"]},
    "simple_shader.glsl": {"main": ["hsv2rgb"]},
}

GLSL_BUILTIN_SAMPLES = {
    "texture",
    "imageLoad",
    "imageStore",
    "EmitVertex",
    "EndPrimitive",
    "vec3",
    "vec4",
    "ivec2",
    "mix",
    "clamp",
}


def _chunk_project() -> dict[str, list]:
    chunker = MultiLanguageChunker(root_path=str(PROJECT_PATH))
    by_file: dict[str, list] = {}
    for path in sorted(PROJECT_PATH.iterdir()):
        assert chunker.is_supported(str(path)), f"{path.name} should be supported"
        by_file[path.name] = chunker.chunk_file(str(path))
    return by_file


def test_all_fixture_extensions_supported():
    """All five shader-stage extensions (.comp/.frag/.geom/.glsl/.vert) index."""
    by_file = _chunk_project()
    assert set(by_file) == set(EXPECTED_FUNCTIONS)


def test_every_function_chunk_is_named():
    """Each function_definition yields a named "function" chunk (the old
    chunker emitted unnamed blobs)."""
    for filename, chunks in _chunk_project().items():
        functions = {c.name for c in chunks if c.chunk_type == "function"}
        assert None not in functions, f"{filename}: unnamed function chunk"
        assert functions == EXPECTED_FUNCTIONS[filename], (
            f"{filename}: expected functions {EXPECTED_FUNCTIONS[filename]}, "
            f"got {functions}"
        )


def test_call_edges_extracted_and_builtins_filtered():
    """User-function calls survive as CallEdge metadata; GLSL builtins and
    type constructors are filtered out before edges are built."""
    for filename, chunks in _chunk_project().items():
        for chunk in chunks:
            callees = [c.callee_name for c in (chunk.calls or [])]
            leaked = set(callees) & GLSL_BUILTIN_SAMPLES
            assert not leaked, (
                f"{filename}:{chunk.name}: builtin callees leaked: {leaked}"
            )
            expected = EXPECTED_CALLS.get(filename, {}).get(chunk.name)
            if expected is not None:
                assert callees == expected, (
                    f"{filename}:{chunk.name}: expected calls {expected}, got {callees}"
                )


def test_comment_docstring_attached():
    """A comment directly above a function becomes its docstring."""
    chunks = _chunk_project()["compute_shader.comp"]
    brighten = next(c for c in chunks if c.name == "brighten")
    assert brighten.docstring is not None
    assert "Doubles every channel" in brighten.docstring


def test_uniform_declarations_kept_as_preamble():
    """Uncommented top-level uniforms/in/out merge into a module_preamble
    chunk rather than being dropped or exploded into per-line chunks."""
    for filename in ("simple_shader.glsl", "fragment_shader.frag"):
        chunks = _chunk_project()[filename]
        preambles = [c for c in chunks if c.chunk_type == "module_preamble"]
        assert preambles, f"{filename}: no module_preamble chunk"
        assert any("uniform" in c.content for c in preambles), (
            f"{filename}: uniforms missing from preamble chunks"
        )


def test_merkle_dag_discovers_all_shaders():
    """MerkleDAG file discovery sees the same five shader files the chunker
    supports (indexer-side discovery parity)."""
    from merkle.merkle_dag import MerkleDAG

    chunker = MultiLanguageChunker(root_path=str(PROJECT_PATH))
    dag = MerkleDAG(str(PROJECT_PATH))
    dag.build()
    supported = {
        Path(f).name
        for f in dag.get_all_files()
        if chunker.is_supported(str(PROJECT_PATH / f))
    }
    assert supported == set(EXPECTED_FUNCTIONS)
