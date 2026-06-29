"""Unit tests for CommunityRefreshStage pipeline stage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from merkle.change_detector import FileChanges
from search.community_refresh_stage import CommunityRefreshStage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_stage(tmp_path: Path | None = None) -> CommunityRefreshStage:
    indexer = MagicMock()
    if tmp_path is not None:
        indexer.storage_dir = str(tmp_path)
    else:
        del indexer.storage_dir
        indexer.dense_index = MagicMock(spec=[])
    embedder = MagicMock()
    summary_stage = MagicMock()
    summary_stage.compute_community_summaries.return_value = []
    return CommunityRefreshStage(
        embedder=embedder, indexer=indexer, summary_stage=summary_stage
    )


def _changes(added=(), modified=(), removed=()):
    return FileChanges(
        added=list(added),
        modified=list(modified),
        removed=list(removed),
        unchanged=[],
    )


def _write_community_map(tmp_path: Path, community_map: dict) -> None:
    project_id = tmp_path.parent.name.rsplit("_", 1)[0]
    community_path = tmp_path / f"{project_id}_communities.json"
    community_path.write_text(json.dumps(community_map))


# ---------------------------------------------------------------------------
# _chunk_from_metadata (migrated from test_incremental_community_summaries.py)
# ---------------------------------------------------------------------------


class TestChunkFromMetadata:
    def _make_stage(self):
        idx = MagicMock()
        idx.storage_dir = "."
        return CommunityRefreshStage(
            embedder=MagicMock(), indexer=idx, summary_stage=MagicMock()
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
        stage = self._make_stage()
        chunk = stage._chunk_from_metadata("a.py:5-10:function:foo", meta)
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
        stage = self._make_stage()
        chunk = stage._chunk_from_metadata("x.py:1-2:function:f", meta)
        assert chunk.language == "python"

    def test_handles_none_start_end(self):
        meta = {
            "content": "",
            "chunk_type": "class",
            "start_line": None,
            "end_line": None,
        }
        stage = self._make_stage()
        chunk = stage._chunk_from_metadata("x.py:0-0:class:X", meta)
        assert chunk.start_line == 0
        assert chunk.end_line == 0


# ---------------------------------------------------------------------------
# Early exits (migrated + extended)
# ---------------------------------------------------------------------------


class TestRefreshEarlyExits:
    def test_returns_early_when_storage_dir_unavailable(self):
        """When indexer has no usable storage_dir, run() returns silently."""
        stage = _make_stage(tmp_path=None)
        stage.run(_changes(added=["a.py"]), "proj")  # must not raise

    def test_returns_early_when_community_map_missing(self, tmp_path):
        """When no community_map JSON exists on disk, run() returns silently."""
        stage = _make_stage(tmp_path)
        stage.run(_changes(added=["a.py"]), "proj")
        stage._indexer.remove_files.assert_not_called()
        stage._indexer.add_embeddings.assert_not_called()

    def test_returns_early_when_no_affected_communities(self, tmp_path):
        """When changed files are not in any community, run() returns silently."""
        _write_community_map(tmp_path, {"other/file.py:1-5:function:foo": 0})
        stage = _make_stage(tmp_path)
        stage.run(_changes(added=["new/file.py"]), "proj")
        stage._indexer.remove_files.assert_not_called()

    def test_returns_early_when_metadata_store_unavailable(self, tmp_path):
        """When MetadataStore is inaccessible, run() warns and returns silently."""
        _write_community_map(tmp_path, {"a.py:1-5:function:foo": 7})
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = {
            "a.py:1-5:function:foo": 7
        }

        stage = _make_stage(tmp_path)
        # Make _get_metadata_store return None
        del stage._indexer.metadata_store
        stage._indexer.dense_index = MagicMock(spec=[])

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(_changes(added=["a.py"]), "proj")

        stage._indexer.add_embeddings.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestRefreshHappyPath:
    def test_stale_community_summary_removed_and_new_one_indexed(self, tmp_path):
        """Stale community summary removed; new summary embedded and indexed."""
        stage = _make_stage(tmp_path)

        community_map = {"a.py:1-5:function:foo": 7}
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map

        stale_meta = {
            "chunk_type": "community",
            "tags": ["community:7"],
            "file_path": "__community_7__.py",
            "relative_path": "",
        }
        member_meta = {
            "chunk_type": "function",
            "content": "def foo(): pass",
            "start_line": 1,
            "end_line": 5,
            "file_path": "/proj/a.py",
            "relative_path": "a.py",
            "folder_structure": [],
            "name": "foo",
            "language": "python",
            "imports": [],
        }
        stage._indexer.metadata_store.items.return_value = [
            ("__community_7__.py:community", stale_meta),
            ("a.py:1-5:function:foo", member_meta),
        ]

        fake_summary = Mock()
        fake_summary.content = "summary"
        stage._summary_stage.compute_community_summaries.return_value = [fake_summary]

        fake_embed = MagicMock()
        fake_embed.metadata = {}
        stage._embedder.embed_chunks.return_value = [fake_embed]

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(_changes(added=["a.py"]), "proj")

        stage._indexer.remove_files.assert_called_once_with(
            {"__community_7__.py"}, "proj"
        )
        stage._summary_stage.compute_community_summaries.assert_called_once()
        stage._embedder.embed_chunks.assert_called_once()
        stage._indexer.add_embeddings.assert_called_once()

    def test_no_member_chunks_skips_embed(self, tmp_path):
        """When no member chunks survive, no embed or add_embeddings call is made."""
        stage = _make_stage(tmp_path)

        community_map = {"a.py:1-5:function:foo": 7}
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map

        # Only community/module chunks in store — no members for the affected community
        stage._indexer.metadata_store.items.return_value = [
            (
                "__community_7__.py:community",
                {
                    "chunk_type": "community",
                    "tags": [],
                    "file_path": "",
                    "relative_path": "",
                },
            ),
        ]

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(_changes(added=["a.py"]), "proj")

        stage._embedder.embed_chunks.assert_not_called()
        stage._indexer.add_embeddings.assert_not_called()

    def test_embed_failure_does_not_propagate(self, tmp_path):
        """Embedding failure is caught and logged; run() returns without raising."""
        stage = _make_stage(tmp_path)

        community_map = {"a.py:1-5:function:foo": 7}
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map

        member_meta = {
            "chunk_type": "function",
            "content": "def foo(): pass",
            "start_line": 1,
            "end_line": 5,
            "file_path": "/proj/a.py",
            "relative_path": "a.py",
            "folder_structure": [],
            "name": "foo",
            "language": "python",
            "imports": [],
        }
        stage._indexer.metadata_store.items.return_value = [
            ("a.py:1-5:function:foo", member_meta)
        ]

        stage._summary_stage.compute_community_summaries.return_value = [Mock()]
        stage._embedder.embed_chunks.side_effect = RuntimeError("GPU OOM")

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(_changes(added=["a.py"]), "proj")  # must not raise

        stage._indexer.add_embeddings.assert_not_called()


# ---------------------------------------------------------------------------
# List-type safety regression
# (migrated from TestRefreshListTypeSafety in test_incremental_community_summaries.py)
# ---------------------------------------------------------------------------


class TestRefreshListTypeSafety:
    """Regression for TypeError: unsupported operand type(s) for |: 'list' and 'list'."""

    def test_with_modified_files_does_not_raise(self, tmp_path):
        stage = _make_stage(tmp_path)
        community_map = {"a.py:1-5:function:foo": 7}
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map
        stage._indexer.metadata_store.items.return_value = []

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(_changes(modified=["a.py"]), "proj")

    def test_with_all_three_change_types_does_not_raise(self, tmp_path):
        stage = _make_stage(tmp_path)
        community_map = {
            "a.py:1-5:function:foo": 7,
            "b.py:1-3:function:bar": 7,
            "c.py:1-2:function:baz": 7,
        }
        mock_graph = MagicMock()
        mock_graph.storage.load_community_map.return_value = community_map
        stage._indexer.metadata_store.items.return_value = []

        with patch(
            "search.community_refresh_stage.GraphIntegration", return_value=mock_graph
        ):
            stage.run(
                _changes(added=["a.py"], modified=["b.py"], removed=["c.py"]), "proj"
            )


# ---------------------------------------------------------------------------
# Direct tests for pure-computation phase helpers
# ---------------------------------------------------------------------------


class TestMapFilesToCommunities:
    """Direct tests for _map_files_to_communities (pure computation)."""

    def _stage(self):
        idx = MagicMock()
        idx.storage_dir = "."
        return CommunityRefreshStage(
            embedder=MagicMock(), indexer=idx, summary_stage=MagicMock()
        )

    def test_single_file_single_community(self):
        stage = self._stage()
        community_map = {
            "a.py:1-5:function:foo": 3,
            "a.py:6-10:function:bar": 3,
        }
        result = stage._map_files_to_communities(community_map)
        assert result == {"a.py": 3}

    def test_primary_community_wins_by_count(self):
        """File with 2 chunks in community 5 and 1 chunk in community 9 → maps to 5."""
        stage = self._stage()
        community_map = {
            "a.py:1-5:function:foo": 5,
            "a.py:6-10:function:bar": 5,
            "a.py:11-15:function:baz": 9,
        }
        result = stage._map_files_to_communities(community_map)
        assert result["a.py"] == 5

    def test_multiple_files_mapped_independently(self):
        stage = self._stage()
        community_map = {
            "a.py:1-5:function:foo": 1,
            "b.py:1-3:function:bar": 2,
        }
        result = stage._map_files_to_communities(community_map)
        assert result == {"a.py": 1, "b.py": 2}


class TestAffectedCommunityIds:
    """Direct tests for _affected_community_ids (pure computation)."""

    def _stage(self):
        idx = MagicMock()
        idx.storage_dir = "."
        return CommunityRefreshStage(
            embedder=MagicMock(), indexer=idx, summary_stage=MagicMock()
        )

    def test_empty_when_no_overlap(self):
        stage = self._stage()
        file_to_community = {"other/file.py": 0}
        result = stage._affected_community_ids(
            file_to_community, _changes(added=["new/file.py"])
        )
        assert result == set()

    def test_finds_community_for_modified_file(self):
        stage = self._stage()
        file_to_community = {"a.py": 7}
        result = stage._affected_community_ids(
            file_to_community, _changes(modified=["a.py"])
        )
        assert result == {7}

    def test_path_normalisation_matches_forward_slash(self):
        """Windows backslash paths in changes are normalised to forward-slash keys."""
        stage = self._stage()
        file_to_community = {"src/a.py": 3}
        # Simulate a Windows path in changes
        result = stage._affected_community_ids(
            file_to_community, _changes(added=["src\\a.py"])
        )
        assert result == {3}

    def test_all_three_change_types_included(self):
        stage = self._stage()
        file_to_community = {"a.py": 1, "b.py": 2, "c.py": 3}
        result = stage._affected_community_ids(
            file_to_community,
            _changes(added=["a.py"], modified=["b.py"], removed=["c.py"]),
        )
        assert result == {1, 2, 3}
