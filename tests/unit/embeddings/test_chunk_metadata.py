"""Unit tests for embeddings.chunk_metadata.

Tests the ChunkMetadata TypedDict shape and the resolve_chunk_path() helper.
"""

from embeddings.chunk_metadata import ChunkMetadata, resolve_chunk_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_meta(**overrides: object) -> ChunkMetadata:
    """Return a minimal valid ChunkMetadata fixture dict."""
    base: ChunkMetadata = {
        "file_path": "/abs/project/src/foo.py",
        "relative_path": "src/foo.py",
        "folder_structure": ["src"],
        "chunk_type": "function",
        "start_line": 10,
        "end_line": 20,
        "name": "my_func",
        "parent_name": None,
        "parent_chunk_id": None,
        "docstring": "Does something.",
        "decorators": [],
        "imports": ["os"],
        "complexity_score": 3,
        "tags": ["utility"],
        "content_preview": "def my_func(): ...",
        "calls": [],
        "relationships": [],
        "language": "python",
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


# ---------------------------------------------------------------------------
# resolve_chunk_path
# ---------------------------------------------------------------------------


class TestResolveChunkPath:
    def test_prefers_file_path_when_both_present(self):
        meta = _make_meta(file_path="/abs/foo.py", relative_path="foo.py")
        assert resolve_chunk_path(meta) == "/abs/foo.py"

    def test_falls_back_to_relative_path_when_file_path_absent(self):
        meta = _make_meta(file_path="")
        assert resolve_chunk_path(meta) == "src/foo.py"

    def test_falls_back_to_relative_path_when_file_path_missing(self):
        meta = _make_meta()
        del meta["file_path"]  # type: ignore[misc]
        assert resolve_chunk_path(meta) == "src/foo.py"

    def test_returns_none_when_both_absent(self):
        meta = _make_meta(file_path="", relative_path="")
        assert resolve_chunk_path(meta) is None

    def test_returns_none_when_both_missing(self):
        meta = _make_meta()
        del meta["file_path"]  # type: ignore[misc]
        del meta["relative_path"]  # type: ignore[misc]
        assert resolve_chunk_path(meta) is None

    def test_returns_file_path_when_relative_is_empty(self):
        meta = _make_meta(file_path="/abs/foo.py", relative_path="")
        assert resolve_chunk_path(meta) == "/abs/foo.py"

    def test_returns_string_not_truthy_check(self):
        # A path of "0" would be falsy in some contexts — ensure we handle it
        meta = _make_meta(file_path="0", relative_path="fallback.py")
        # "0" is a non-empty string → truthy → returned
        assert resolve_chunk_path(meta) == "0"


# ---------------------------------------------------------------------------
# ChunkMetadata structural contract
# ---------------------------------------------------------------------------


class TestChunkMetadataShape:
    def test_required_keys_present(self):
        """Sanity-check that _make_meta produces all required keys."""
        meta = _make_meta()
        required = [
            "file_path",
            "relative_path",
            "folder_structure",
            "chunk_type",
            "start_line",
            "end_line",
            "name",
            "parent_name",
            "parent_chunk_id",
            "docstring",
            "decorators",
            "imports",
            "complexity_score",
            "tags",
            "content_preview",
            "calls",
            "relationships",
            "language",
        ]
        for key in required:
            assert key in meta, f"Missing required key: {key!r}"

    def test_content_not_required(self):
        """content is NotRequired — a fresh meta without it is valid."""
        meta = _make_meta()
        assert "content" not in meta  # not in the base fixture

    def test_content_can_be_added(self):
        meta = _make_meta(content="def my_func(): pass")
        assert meta["content"] == "def my_func(): pass"

    def test_project_name_not_required(self):
        meta = _make_meta()
        assert "project_name" not in meta

    def test_project_name_can_be_added(self):
        meta = _make_meta(project_name="my_project")
        assert meta["project_name"] == "my_project"

    def test_folder_structure_is_list(self):
        meta = _make_meta()
        assert isinstance(meta["folder_structure"], list)

    def test_calls_and_relationships_are_lists(self):
        meta = _make_meta()
        assert isinstance(meta["calls"], list)
        assert isinstance(meta["relationships"], list)
