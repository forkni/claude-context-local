"""WGSL whole-file chunks (ADR-0093).

No maintained tree-sitter grammar parses current WGSL, so each `.wgsl` file is
indexed as one `whole_file` chunk that holds the full text.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker


_SHADER = """\
@group(0) @binding(0) var<storage, read_write> data: array<f32>;

const SCALE: f32 = 2.0;

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3<u32>) {
    data[id.x] = data[id.x] * SCALE;
    workgroupBarrier();
}
"""


@pytest.fixture
def shader_chunks(tmp_path: Path):
    file_path = tmp_path / "gpu" / "scale.wgsl"
    file_path.parent.mkdir()
    file_path.write_text(_SHADER, encoding="utf-8", newline="\n")
    return MultiLanguageChunker(root_path=str(tmp_path)).chunk_file(str(file_path))


def test_one_whole_file_chunk_with_the_full_text(shader_chunks):
    assert len(shader_chunks) == 1
    chunk = shader_chunks[0]
    assert chunk.chunk_type == "whole_file"
    assert chunk.language == "wgsl"
    assert chunk.name == "scale.wgsl"
    assert chunk.content == _SHADER
    assert (chunk.start_line, chunk.end_line) == (1, 9)
    assert chunk.relative_path.replace("\\", "/") == "gpu/scale.wgsl"
    assert chunk.chunk_id == "gpu/scale.wgsl:1-9:whole_file:scale.wgsl"
    assert not chunk.calls
    assert not chunk.relationships
    assert chunk.tags == ["wgsl", "role:shader"]


def test_large_file_stays_one_chunk(tmp_path: Path):
    """An oversized shader stays one chunk; only the embedded text is cut,
    by the composer's character budget (decided 2026-11-24)."""
    body = "".join(f"fn f{i}() -> f32 {{ return {i}.0; }}\n" for i in range(1200))
    file_path = tmp_path / "big.wgsl"
    file_path.write_text(body, encoding="utf-8", newline="\n")
    assert len(body) > 34_000

    chunks = MultiLanguageChunker(root_path=str(tmp_path)).chunk_file(str(file_path))

    assert len(chunks) == 1
    assert chunks[0].content == body
    assert (chunks[0].start_line, chunks[0].end_line) == (1, 1200)


def test_empty_file_gives_no_chunk(tmp_path: Path):
    file_path = tmp_path / "empty.wgsl"
    file_path.write_text("", encoding="utf-8")
    assert (
        MultiLanguageChunker(root_path=str(tmp_path)).chunk_file(str(file_path)) == []
    )
