"""Unit tests for incremental community-summary refresh wiring in IncrementalIndexer.

Tests cover:
- Threshold routing: cumulative fraction > threshold promotes to full reindex
- Threshold routing: below threshold calls CommunityRefreshStage.run
- community:N tag presence on generated community summary chunks (integration smoke test)

Note: _chunk_from_metadata, early-exit paths, and list-type safety are now tested in
tests/unit/search/test_community_refresh_stage.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from chunking.python_ast_chunker import CodeChunk
from merkle.change_detector import FileChanges
from search.incremental_indexer import IncrementalIndexer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indexer(tmp_path) -> IncrementalIndexer:
    """Create a minimal IncrementalIndexer with enough real infrastructure to run."""
    mock_indexer = MagicMock()
    mock_indexer.storage_dir = str(tmp_path)
    mock_indexer.validate_index_consistency.return_value = (True, [])
    mock_embedder = MagicMock()
    mock_chunker = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.has_snapshot.return_value = True
    return IncrementalIndexer(
        indexer=mock_indexer,
        embedder=mock_embedder,
        chunker=mock_chunker,
        snapshot_manager=mock_snapshot,
    )


def _changes(added=(), modified=(), removed=()):
    return FileChanges(
        added=list(added),
        modified=list(modified),
        removed=list(removed),
        unchanged=[],
    )


# ---------------------------------------------------------------------------
# community:N tag on generated summary chunks (integration smoke test)
# ---------------------------------------------------------------------------


class TestCommunityTag:
    def test_community_summary_chunk_carries_community_id_tag(self):
        from graph.community_summarizer import generate_community_summaries

        chunks = [
            CodeChunk(
                content="class A: pass",
                chunk_type="class",
                start_line=1,
                end_line=5,
                file_path="/p/a.py",
                relative_path="a.py",
                folder_structure=[],
                name="A",
                language="python",
                chunk_id="a.py:1-5:class:A",
            ),
            CodeChunk(
                content="def b(): pass",
                chunk_type="function",
                start_line=6,
                end_line=10,
                file_path="/p/a.py",
                relative_path="a.py",
                folder_structure=[],
                name="b",
                language="python",
                chunk_id="a.py:6-10:function:b",
            ),
        ]
        community_map = {"a.py:1-5:class:A": 42, "a.py:6-10:function:b": 42}
        summaries = generate_community_summaries(chunks, community_map)
        assert len(summaries) == 1
        tags = summaries[0].tags or []
        assert "community:42" in tags, f"Expected 'community:42' in tags, got: {tags}"


# ---------------------------------------------------------------------------
# Threshold routing in incremental_index
# ---------------------------------------------------------------------------


class TestThresholdRouting:
    """Verify the drift check promotes to full reindex or delegates to the refresh stage."""

    def _make_changes(self, n_added=1):
        return _changes(added=[f"file_{i}.py" for i in range(n_added)])

    def test_above_threshold_promotes_to_full_reindex(self, tmp_path):
        """When cumulative fraction exceeds threshold, _full_index is called."""
        incr = _make_indexer(tmp_path)

        prior_meta = {
            "cumulative_changed_files": 28,
            "supported_files": 100,
        }
        incr.snapshot_manager.load_metadata.return_value = prior_meta
        incr.snapshot_manager.has_snapshot.return_value = True

        changes = self._make_changes(n_added=5)  # 5 more → 33/100 = 0.33 > 0.3

        with (
            patch.object(
                incr, "_full_index", return_value=MagicMock(success=True)
            ) as mock_full,
            patch.object(incr, "detect_changes") as mock_dc,
        ):
            mock_dc.return_value = (changes, MagicMock())
            incr.incremental_index("/proj", "proj")

        mock_full.assert_called_once()

    def test_below_threshold_calls_refresh_stage(self, tmp_path):
        """When fraction is below threshold, CommunityRefreshStage.run is called."""
        incr = _make_indexer(tmp_path)

        prior_meta = {
            "cumulative_changed_files": 0,
            "supported_files": 1000,
        }
        incr.snapshot_manager.load_metadata.return_value = prior_meta
        incr.snapshot_manager.has_snapshot.return_value = True

        changes = self._make_changes(n_added=1)  # 1/1000 = 0.001 < 0.3

        with (
            patch.object(incr, "_remove_old_chunks", return_value=0),
            patch.object(incr, "_add_new_chunks", return_value=1),
            patch.object(incr._community_refresh_stage, "run") as mock_run,
            patch.object(incr, "detect_changes") as mock_dc,
        ):
            dag = MagicMock()
            dag.get_all_files.return_value = ["a.py"]
            mock_dc.return_value = (changes, dag)
            incr.incremental_index("/proj", "proj")

        mock_run.assert_called_once()

    def test_no_prior_tracking_skips_threshold_check(self, tmp_path):
        """When snapshot has no cumulative_changed_files, threshold check is skipped."""
        incr = _make_indexer(tmp_path)

        prior_meta = {"supported_files": 5}  # no cumulative_changed_files
        incr.snapshot_manager.load_metadata.return_value = prior_meta
        incr.snapshot_manager.has_snapshot.return_value = True

        changes = self._make_changes(n_added=10)

        with (
            patch.object(incr, "_full_index") as mock_full,
            patch.object(incr, "_remove_old_chunks", return_value=0),
            patch.object(incr, "_add_new_chunks", return_value=1),
            patch.object(incr._community_refresh_stage, "run"),
            patch.object(incr, "detect_changes") as mock_dc,
        ):
            dag = MagicMock()
            dag.get_all_files.return_value = ["a.py"]
            mock_dc.return_value = (changes, dag)
            incr.incremental_index("/proj", "proj")

        mock_full.assert_not_called()
