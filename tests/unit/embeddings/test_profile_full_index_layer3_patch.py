"""Regression guard for profile_full_index.py's Layer 3 GPU/CPU embedding split.

``_install_layer3_embedding_split()``
(scripts/benchmark/profiling/profile_full_index.py) monkeypatches
``CodeEmbedder.create_embedding_content`` at the class level to time the
CPU-side document-composition cost separately from the GPU ``.encode()``
call. That patch target survived the embedding-document-composer extraction
(embeddings/document_composer.py, architecture-review Workstream C)
unchanged -- ``create_embedding_content`` remains a real method on
``CodeEmbedder``, now a thin delegator to
``EmbeddingDocumentComposer.compose()``.

Nothing before this test caught the failure mode described in the extraction
plan: if a future refactor rebound ``create_embedding_content`` to something
the class-level monkeypatch can no longer intercept (e.g. routing callers
through the composer directly, bypassing the patched method), the patch
would silently rebind a dead attribute and report 0ms for the CPU half with
no error. This test proves the patch still intercepts real calls.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import scripts.benchmark.profiling.profile_full_index as profile_full_index_mod
from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder
from scripts.benchmark.profiling.profile_full_index import (
    _install_layer3_embedding_split,
    _Recorder,
)
from search.config import EmbeddingConfig, SearchConfig


def _make_function_chunk(tmp_path) -> CodeChunk:
    test_file = tmp_path / "sample.py"
    test_file.write_text("def func():\n    pass\n")
    return CodeChunk(
        file_path=str(test_file),
        relative_path="sample.py",
        folder_structure=".",
        chunk_type="function",
        start_line=1,
        end_line=2,
        name="func",
        parent_name=None,
        docstring="",
        content="def func():\n    pass",
        decorators=[],
        imports=[],
        complexity_score=1.0,
        tags=[],
        calls=[],
        relationships=[],
    )


class TestLayer3EmbeddingSplitPatchPoint:
    """Installing the Layer 3 patch must actually intercept the live
    ``create_embedding_content`` method, not a stale/dead rebind."""

    @patch("embeddings.embedder.get_search_config")
    def test_patch_intercepts_the_live_create_embedding_content_method(
        self, mock_config_getter, tmp_path, monkeypatch
    ):
        mock_config_getter.return_value = SearchConfig(embedding=EmbeddingConfig())

        recorder = _Recorder()
        monkeypatch.setattr(profile_full_index_mod, "_recorder", recorder)

        original_create_content = CodeEmbedder.create_embedding_content
        original_embed_chunks = CodeEmbedder.embed_chunks
        try:
            _install_layer3_embedding_split()

            # __new__ builds the document composer -- no model, no __init__
            # side effects, matching the rest of this repo's CodeEmbedder
            # unit-test convention.
            embedder = CodeEmbedder.__new__(CodeEmbedder)
            embedder._logger = logging.getLogger("test")

            chunk = _make_function_chunk(tmp_path)
            content = embedder.create_embedding_content(chunk)

            assert "def func" in content
            assert recorder.count("embed_cpu_create_content") == 1
            assert recorder.total("embed_cpu_create_content") >= 0.0
        finally:
            # CodeEmbedder is a shared class across the whole test session --
            # undo both patches _install_layer3_embedding_split applies, or
            # every later test in this process leaks a timed wrapper.
            CodeEmbedder.create_embedding_content = original_create_content
            CodeEmbedder.embed_chunks = original_embed_chunks
