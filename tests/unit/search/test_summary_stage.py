"""Unit tests for search/summary_stage.py.

Verifies:
- generate_module_summaries delegates correctly and returns [] on failure
- generate_and_extend owns the config gate and the append-and-log idiom
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

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


# ---------------------------------------------------------------------------
# SummaryStage.generate_and_extend
# ---------------------------------------------------------------------------


class TestGenerateAndExtend:
    def setup_method(self):
        self.stage = SummaryStage()

    def _patch_config(self, enabled: bool):
        mock_config = Mock()
        mock_config.chunking.enable_file_summaries = enabled
        return patch("search.summary_stage.get_search_config", return_value=mock_config)

    def test_appends_summaries_in_place_and_returns_count(self):
        chunks = [_make_chunk("utils/helpers.py", "function", "helper")]
        sentinel = _make_chunk("utils/helpers.py", "module", "helpers")
        with (
            self._patch_config(enabled=True),
            patch.object(
                self.stage, "generate_module_summaries", return_value=[sentinel]
            ) as mock_generate,
        ):
            appended = self.stage.generate_and_extend(
                chunks, log_prefix="[FILE_SUMMARIES]", appended_noun="module summaries"
            )
        # The recorded call arg is the same (now mutated) list object, so
        # only identity — not contents — can be asserted here.
        mock_generate.assert_called_once()
        assert mock_generate.call_args.args[0] is chunks
        assert appended == 1
        assert chunks[-1] is sentinel

    def test_disabled_by_config_is_zero_work(self):
        chunks = [_make_chunk("utils/helpers.py", "function", "helper")]
        with (
            self._patch_config(enabled=False),
            patch.object(self.stage, "generate_module_summaries") as mock_generate,
        ):
            appended = self.stage.generate_and_extend(
                chunks,
                log_prefix="[INCREMENTAL]",
                appended_noun="module summary chunks",
            )
        mock_generate.assert_not_called()
        assert appended == 0
        assert len(chunks) == 1

    def test_empty_chunks_is_zero_work(self):
        with (
            self._patch_config(enabled=True),
            patch.object(self.stage, "generate_module_summaries") as mock_generate,
        ):
            appended = self.stage.generate_and_extend(
                [], log_prefix="[FILE_SUMMARIES]", appended_noun="module summaries"
            )
        mock_generate.assert_not_called()
        assert appended == 0

    def test_no_summaries_leaves_chunks_unchanged(self):
        chunks = [_make_chunk("utils/helpers.py", "function", "helper")]
        with (
            self._patch_config(enabled=True),
            patch.object(self.stage, "generate_module_summaries", return_value=[]),
        ):
            appended = self.stage.generate_and_extend(
                chunks, log_prefix="[FILE_SUMMARIES]", appended_noun="module summaries"
            )
        assert appended == 0
        assert len(chunks) == 1
