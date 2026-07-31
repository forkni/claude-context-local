"""Unit tests for search/summary_stage.py.

Verifies:
- generate_module_summaries delegates correctly and returns [] on failure
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from chunking.python_ast_chunker import CodeChunk
from search.summary_stage import SummaryStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(
    rel_path: str,
    chunk_type: str,
    name: str,
    start_line: int = 1,
    end_line: int = 10,
    parent_name: str | None = None,
    docstring: str | None = None,
    imports: list | None = None,
) -> CodeChunk:
    chunk_id = f"{rel_path}:{start_line}-{end_line}:{chunk_type}:{name}"
    return CodeChunk(
        content=f"def {name}(): pass",
        chunk_type=chunk_type,
        start_line=start_line,
        end_line=end_line,
        file_path=f"/project/{rel_path}",
        relative_path=rel_path,
        folder_structure=list(Path(rel_path).parent.parts),
        name=name,
        parent_name=parent_name,
        docstring=docstring,
        imports=imports or [],
        language="python",
        chunk_id=chunk_id,
    )


# ---------------------------------------------------------------------------
# SummaryStage.generate_module_summaries
# ---------------------------------------------------------------------------


class TestGenerateModuleSummaries:
    def setup_method(self):
        self.stage = SummaryStage()

    def test_returns_module_summary_chunks(self):
        chunks = [
            _make_chunk("utils/helpers.py", "function", "helper"),
            _make_chunk("utils/helpers.py", "function", "other"),
        ]
        result = self.stage.generate_module_summaries(chunks)
        assert len(result) >= 1
        for chunk in result:
            assert chunk.chunk_type == "module"

    def test_returns_empty_on_failure(self):
        with patch(
            "chunking.file_summarizer.generate_file_summaries",
            side_effect=RuntimeError("disk error"),
        ):
            result = self.stage.generate_module_summaries([])
        assert result == []

    def test_returns_empty_list_for_empty_chunks(self):
        result = self.stage.generate_module_summaries([])
        assert isinstance(result, list)
