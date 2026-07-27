"""Unit tests for GLSL cyclomatic complexity scoring (Gap 1, GLSL-parity effort).

`GLSLChunker.get_node_complexity` (chunking/languages/glsl.py) computed the right
number all along, but that was never the missing piece: measured on the real
corpus, `main`/`roundedBoxSDF` both reported complexity_score=0 despite real
branching, because nothing ever wrote `get_node_complexity`'s result into chunk
metadata -- it was consumed only by adaptive sizing (inert under the default
`sizing_mode="fixed"`). The fix is `LanguageChunker._apply_complexity_score`
(chunking/languages/base.py), a base-class helper wired into both
`extract_metadata` call sites, so it closes this gap for every tree-sitter
language that overrides `get_node_complexity`, not just GLSL.

These tests operate at the `MultiLanguageChunker.chunk_file()` level -- the same
seam GLSL metadata actually flows through in production, matching
test_glsl_relationships.py's convention -- rather than calling
`get_node_complexity` directly, so they prove the wiring, not just the math.
"""

from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker


# Mirrors the real-world shape that motivated Gap 1: a `main` with if/elif/for
# branching, plus a branchless helper and a struct to confirm non-function
# chunks stay unscored.
_FIXTURE_SOURCE = """\
// Fixture exercising real branching in main(), mirroring the real-world
// shader that motivated Gap 1.
uniform float uThreshold;

struct Gain {
    float value;
};

float clampedGain(float x) {
    return x;
}

void main() {
    float g = clampedGain(uThreshold);
    if (g > 0.5) {
        g = g * 2.0;
    } else if (g > 0.0) {
        g = g + 1.0;
    }
    for (int i = 0; i < 4; i++) {
        g = g - 0.1;
    }
    gl_FragColor = vec4(g, g, g, 1.0);
}
"""


def _chunks(tmp_path: Path):
    """Chunk `_FIXTURE_SOURCE` through the real MultiLanguageChunker -> GLSLChunker path."""
    file_path = tmp_path / "complexity.frag"
    file_path.write_text(_FIXTURE_SOURCE, encoding="utf-8")

    chunker = MultiLanguageChunker(root_path=str(tmp_path))
    chunks = chunker.chunk_file(str(file_path))
    return {c.name: c for c in chunks if c.name}


def test_main_with_branching_has_complexity_greater_than_one(tmp_path):
    """`main`'s if/elif/for gives it CC > 1 -- the exact case measured at 0
    on the real corpus before the base-class `_apply_complexity_score` fix."""
    main_chunk = _chunks(tmp_path)["main"]

    assert main_chunk.complexity_score > 1


def test_branchless_function_has_complexity_exactly_one(tmp_path):
    """A branchless function still reports CC 1, not 0 or missing -- confirms
    the fix populates the field rather than merely avoiding a crash."""
    clamped_gain_chunk = _chunks(tmp_path)["clampedGain"]

    assert clamped_gain_chunk.complexity_score == 1


def test_struct_chunk_has_no_complexity_score(tmp_path):
    """Non-function chunks (structs, declarations) stay unscored, mirroring
    PythonChunker.extract_metadata: only function_definition/decorated_definition
    get scored, never classes -- `_apply_complexity_score` mirrors that same
    node-type gate for GLSL and every other tree-sitter language."""
    gain_chunk = _chunks(tmp_path)["Gain"]

    assert gain_chunk.complexity_score == 0
