"""Unit tests for Improvement B — incremental community-summary refresh.

Tests cover:
- _chunk_from_metadata round-trips the fields generate_community_summaries reads
- Threshold routing: cumulative fraction > threshold promotes to full reindex
- Threshold routing: below threshold calls _refresh_affected_community_summaries
- _refresh_affected_community_summaries returns early when storage_dir is unavailable
- _refresh_affected_community_summaries returns early when community_map is missing
- community:N tag presence on generated community summary chunks
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from chunking.python_ast_chunker import CodeChunk
from merkle.change_detector import FileChanges
from search.incremental_indexer import IncrementalIndexer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indexer(tmp_path: Path) -> IncrementalIndexer:
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
# _chunk_from_metadata
# ---------------------------------------------------------------------------


class TestChunkFromMetadata:
    def setup_method(self):
        with tempfile.TemporaryDirectory() as d:
            self._tmp = d
        self._idx = MagicMock()
        self._idx.storage_dir = "."
        self.indexer = IncrementalIndexer(
            indexer=self._idx,
            embedder=MagicMock(),
            chunker=MagicMock(),
            snapshot_manager=MagicMock(),
        )

    def test_round_trips_basic_fields(self):
        meta = {
            "content": "def foo(): pass",
            "chunk_type": "function",
            "start_line": 5,
            "end_line": 10,
            "file_path": "/proj/a.py",
            "relative_path": "a.py",
            "folder_structure": [],
            "name": "foo",
            "parent_name": None,
            "docstring": "Foo does X.",
            "imports": ["os"],
            "language": "python",
        }
        chunk = self.indexer._chunk_from_metadata("a.py:5-10:function:foo", meta)
        assert chunk.chunk_id == "a.py:5-10:function:foo"
        assert chunk.chunk_type == "function"
        assert chunk.name == "foo"
        assert chunk.docstring == "Foo does X."
        assert chunk.imports == ["os"]
        assert chunk.start_line == 5
        assert chunk.end_line == 10
        assert chunk.language == "python"

    def test_defaults_language_to_python(self):
        meta = {"content": "", "chunk_type": "function", "start_line": 1, "end_line": 2}
        chunk = self.indexer._chunk_from_metadata("x.py:1-2:function:f", meta)
        assert chunk.language == "python"

    def test_handles_none_start_end(self):
        meta = {
            "content": "",
            "chunk_type": "class",
            "start_line": None,
            "end_line": None,
        }
        chunk = self.indexer._chunk_from_metadata("x.py:0-0:class:X", meta)
        assert chunk.start_line == 0
        assert chunk.end_line == 0


# ---------------------------------------------------------------------------
# community:N tag on generated summary chunks
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
    """Verify the drift check promotes to full reindex or calls refresh."""

    def _make_changes(self, n_added=1):
        return _changes(added=[f"file_{i}.py" for i in range(n_added)])

    def test_above_threshold_promotes_to_full_reindex(self, tmp_path):
        """When cumulative fraction exceeds threshold, _full_index is called."""
        incr = _make_indexer(tmp_path)

        # Snapshot reports 10 supported files, cumulative already 28 (28/10=2.8 + 1/10 > 0.3)
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

    def test_below_threshold_calls_refresh(self, tmp_path):
        """When fraction is below threshold, _refresh_affected_community_summaries is called."""
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
            patch.object(incr, "_refresh_affected_community_summaries") as mock_refresh,
            patch.object(incr, "detect_changes") as mock_dc,
        ):
            dag = MagicMock()
            dag.get_all_files.return_value = ["a.py"]
            mock_dc.return_value = (changes, dag)
            incr.incremental_index("/proj", "proj")

        mock_refresh.assert_called_once()

    def test_no_prior_tracking_skips_threshold_check(self, tmp_path):
        """When snapshot has no cumulative_changed_files, threshold check is skipped."""
        incr = _make_indexer(tmp_path)

        # Old-style snapshot without tracking field
        prior_meta = {"supported_files": 5}  # no cumulative_changed_files
        incr.snapshot_manager.load_metadata.return_value = prior_meta
        incr.snapshot_manager.has_snapshot.return_value = True

        changes = self._make_changes(n_added=10)  # Would be > threshold if tracked

        with (
            patch.object(incr, "_full_index") as mock_full,
            patch.object(incr, "_remove_old_chunks", return_value=0),
            patch.object(incr, "_add_new_chunks", return_value=1),
            patch.object(incr, "_refresh_affected_community_summaries"),
            patch.object(incr, "detect_changes") as mock_dc,
        ):
            dag = MagicMock()
            dag.get_all_files.return_value = ["a.py"]
            mock_dc.return_value = (changes, dag)
            incr.incremental_index("/proj", "proj")

        mock_full.assert_not_called()  # threshold check was skipped


# ---------------------------------------------------------------------------
# _refresh_affected_community_summaries early-exit paths
# ---------------------------------------------------------------------------


class TestRefreshEarlyExits:
    def test_returns_early_when_storage_dir_unavailable(self):
        """When indexer has no usable storage_dir (e.g. Mock), refresh returns silently."""
        mock_indexer = MagicMock()
        del mock_indexer.storage_dir  # Remove storage_dir attribute
        mock_indexer.dense_index = MagicMock(spec=[])  # No storage_dir either
        incr = IncrementalIndexer(
            indexer=mock_indexer,
            embedder=MagicMock(),
            chunker=MagicMock(),
            snapshot_manager=MagicMock(),
        )
        # Should not raise
        incr._refresh_affected_community_summaries(_changes(added=["a.py"]), "proj")

    def test_returns_early_when_community_map_missing(self, tmp_path):
        """When no community_map JSON exists on disk, refresh returns silently."""
        incr = _make_indexer(tmp_path)
        # tmp_path exists but has no communities JSON
        incr._refresh_affected_community_summaries(_changes(added=["a.py"]), "proj")
        # No exception raised, indexer not called for removal or add
        incr.indexer.remove_file_chunks.assert_not_called()
        incr.indexer.add_embeddings.assert_not_called()

    def test_returns_early_when_no_affected_communities(self, tmp_path):
        """When changed files are not in any community, refresh returns silently."""
        incr = _make_indexer(tmp_path)

        # Write a community_map that doesn't include the changed file
        project_id = tmp_path.parent.name.rsplit("_", 1)[0]
        community_path = tmp_path / f"{project_id}_communities.json"
        community_path.write_text(json.dumps({"other/file.py:1-5:function:foo": 0}))

        incr._refresh_affected_community_summaries(
            _changes(added=["new/file.py"]), "proj"
        )
        incr.indexer.remove_file_chunks.assert_not_called()


# ---------------------------------------------------------------------------
# Regression: FileChanges fields are lists, not sets — | operator was invalid
# ---------------------------------------------------------------------------


class TestRefreshListTypeSafety:
    """Regression for TypeError: unsupported operand type(s) for |: 'list' and 'list'.

    The bug was in _refresh_affected_community_summaries at the changed_file_set
    comprehension, which used the set-union operator | on list fields of FileChanges.
    These tests reach that line by providing a real community_map via a patched
    GraphIntegration (all early-exit guards are cleared).
    """

    def test_with_modified_files_does_not_raise(self, tmp_path):
        """Must complete without TypeError when changes.modified is a non-empty list."""
        incr = _make_indexer(tmp_path)

        community_map = {"a.py:1-5:function:foo": 7}
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map

        # Empty metadata store — no chunks to remove/rebuild, just validate no crash
        incr.indexer.metadata_store.items.return_value = []

        with patch(
            "search.incremental_indexer.GraphIntegration", return_value=mock_graph
        ):
            # Before the fix this raised TypeError on: changes.modified | changes.removed
            incr._refresh_affected_community_summaries(
                _changes(modified=["a.py"]), "proj"
            )

    def test_with_all_three_change_types_does_not_raise(self, tmp_path):
        """Must handle added, modified, and removed lists simultaneously."""
        incr = _make_indexer(tmp_path)

        community_map = {
            "a.py:1-5:function:foo": 7,
            "b.py:1-3:function:bar": 7,
            "c.py:1-2:function:baz": 7,
        }
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map

        incr.indexer.metadata_store.items.return_value = []

        with patch(
            "search.incremental_indexer.GraphIntegration", return_value=mock_graph
        ):
            incr._refresh_affected_community_summaries(
                _changes(added=["a.py"], modified=["b.py"], removed=["c.py"]),
                "proj",
            )
