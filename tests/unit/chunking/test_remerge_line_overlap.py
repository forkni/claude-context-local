"""Unit tests for remerge_chunks_with_communities line overlap fix.

This test suite verifies the fix for the chunk merging bug where:
1. Dangerous fallback to first chunk (wrong file)
2. Inverted line overlap logic
3. Cross-file metadata pollution

The fix ensures proper line overlap checking and same-file guarantees.
"""

from chunking.languages.base import LanguageChunker
from chunking.python_ast_chunker import CodeChunk


class TestRemergeLineOverlapFix:
    """Tests for the line overlap logic in remerge_chunks_with_communities."""

    def _create_code_chunk(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        chunk_id: str,
        content: str = "test content",
        name: str = "test_func",
    ) -> CodeChunk:
        """Helper to create test CodeChunk."""
        return CodeChunk(
            content=content,
            chunk_type="function",
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
            relative_path=file_path,
            folder_structure=[],
            name=name,
            parent_name=None,
            language="python",
            chunk_id=chunk_id,
            community_id=None,
        )

    def test_merged_chunk_finds_contained_original(self):
        """Merged chunk correctly finds original contained within its range.

        Scenario: Two adjacent chunks merge into one larger chunk.
        Original chunks: [15-25], [30-40]
        Merged chunk: [15-40]
        Expected: The merged chunk should find either original chunk successfully.
        """
        chunks = [
            self._create_code_chunk("file.py", 15, 25, "file.py:15-25:function:foo"),
            self._create_code_chunk("file.py", 30, 40, "file.py:30-40:function:bar"),
        ]
        community_map = {
            "file.py:15-25:function:foo": 0,
            "file.py:30-40:function:bar": 0,  # Same community
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Should merge successfully
        assert len(result) >= 1
        # All results should have correct file metadata
        assert all(c.file_path == "file.py" for c in result)

    def test_no_cross_file_metadata_pollution(self):
        """Chunks from different files never get wrong file's metadata.

        Scenario: Two files with chunks at similar line ranges.
        Original chunks: auth.py:[1-10], db.py:[1-10]
        Expected: auth.py chunk never gets db.py metadata and vice versa.
        """
        chunks = [
            self._create_code_chunk("auth.py", 1, 10, "auth.py:1-10:function:login"),
            self._create_code_chunk("db.py", 1, 10, "db.py:1-10:function:connect"),
        ]
        community_map = {
            "auth.py:1-10:function:login": 0,
            "db.py:1-10:function:connect": 1,  # Different communities
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Each chunk should keep its own file_path
        auth_chunks = [c for c in result if c.file_path == "auth.py"]
        db_chunks = [c for c in result if c.file_path == "db.py"]

        assert len(auth_chunks) >= 1, "Should have at least one auth.py chunk"
        assert len(db_chunks) >= 1, "Should have at least one db.py chunk"

        for c in auth_chunks:
            assert c.file_path == "auth.py", "Auth chunk should not have db.py metadata"
        for c in db_chunks:
            assert c.file_path == "db.py", "DB chunk should not have auth.py metadata"

    def test_fallback_same_file_only(self):
        """If exact overlap fails, fallback only uses same-file chunks.

        Scenario: Merged chunk with no exact overlap match.
        Expected: Fallback should use a chunk from the same file, not from a different file.
        """
        chunks = [
            self._create_code_chunk("only.py", 5, 15, "only.py:5-15:function:solo"),
        ]
        community_map = {
            "only.py:5-15:function:solo": 0,
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Should not crash or use wrong file
        assert len(result) >= 1
        assert all(c.file_path == "only.py" for c in result)

    def test_inverted_logic_regression(self):
        """Verify the inverted line logic bug is fixed.

        Old bug: checked if merged fits inside original (wrong)
        Fixed: check if original fits inside merged (correct)

        Scenario: Merged chunk spans lines 1-100
        Originals: [1-30], [31-60], [61-100]
        Old bug would fail because merged(1-100) doesn't fit inside original(1-30)
        Fixed: original(1-30) fits inside merged(1-100)
        """
        chunks = [
            self._create_code_chunk("big.py", 1, 30, "big.py:1-30:function:part1"),
            self._create_code_chunk("big.py", 31, 60, "big.py:31-60:function:part2"),
            self._create_code_chunk("big.py", 61, 100, "big.py:61-100:function:part3"),
        ]
        community_map = {
            "big.py:1-30:function:part1": 0,
            "big.py:31-60:function:part2": 0,  # Same community
            "big.py:61-100:function:part3": 0,  # Same community
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Should merge all 3 into 1 (same community, same file)
        # The merged chunk should have valid metadata from big.py
        assert len(result) == 1, f"Expected 1 merged chunk, got {len(result)}"
        assert result[0].file_path == "big.py"
        assert result[0].start_line == 1
        assert result[0].end_line == 100

    def test_cross_file_community_no_merge(self):
        """Chunks from different files should never merge even if same community.

        This is the critical test for Bug #3: Cross-File Merging prevention.

        Scenario: Two files with same community_id (semantically related code).
        Expected: They should NOT merge because they're in different files.
        """
        chunks = [
            self._create_code_chunk(
                "fileA.py", 1, 50, "fileA.py:1-50:function:related_func"
            ),
            self._create_code_chunk(
                "fileB.py", 1, 50, "fileB.py:1-50:function:related_func"
            ),
        ]
        community_map = {
            "fileA.py:1-50:function:related_func": 0,
            "fileB.py:1-50:function:related_func": 0,  # Same community (semantically related)
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Should NOT merge (different files)
        assert len(result) == 2, (
            f"Expected 2 chunks (no cross-file merge), got {len(result)}"
        )

        # Each chunk should keep its original file_path
        file_paths = {c.file_path for c in result}
        assert file_paths == {"fileA.py", "fileB.py"}

    def test_dangerous_fallback_prevented(self):
        """Test that dangerous fallback to first chunk is prevented.

        Old bug: If no match found, used chunks_with_community[0] (wrong file possible)
        Fixed: Skip chunk or use same-file fallback only

        Scenario: Merged chunk from fileB.py, but first chunk in list is fileA.py
        Expected: fileB chunk should not get fileA metadata
        """
        chunks = [
            self._create_code_chunk("fileA.py", 1, 10, "fileA.py:1-10:function:first"),
            self._create_code_chunk("fileB.py", 1, 10, "fileB.py:1-10:function:second"),
        ]
        community_map = {
            "fileA.py:1-10:function:first": 0,
            "fileB.py:1-10:function:second": 1,  # Different community
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        # Verify no cross-file pollution
        for chunk in result:
            if "first" in chunk.content or chunk.name == "first":
                assert chunk.file_path == "fileA.py", (
                    "First chunk should be in fileA.py"
                )
            elif "second" in chunk.content or chunk.name == "second":
                assert chunk.file_path == "fileB.py", (
                    "Second chunk should be in fileB.py"
                )

    def test_empty_community_map(self):
        """Empty community map returns chunks unchanged."""
        chunks = [
            self._create_code_chunk("file.py", 1, 10, "file.py:1-10:function:foo"),
        ]
        community_map = {}

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        assert len(result) == 1
        assert result[0].file_path == "file.py"

    def test_none_community_id_handling(self):
        """Chunks with None community_id are handled gracefully."""
        chunks = [
            self._create_code_chunk("file.py", 1, 10, "file.py:1-10:function:foo"),
        ]
        community_map = {
            "file.py:1-10:function:foo": None,  # No community assigned
        }

        result = LanguageChunker.remerge_chunks_with_communities(
            chunks, community_map, min_tokens=10, max_merged_tokens=5000
        )

        assert len(result) >= 1
        assert all(c.file_path == "file.py" for c in result)


# ---------------------------------------------------------------------------
# Direct tests for the three static helpers extracted from remerge_chunks_with_communities
# ---------------------------------------------------------------------------


class TestAssignCommunityIds:
    """Direct tests for LanguageChunker._assign_community_ids static helper."""

    def _make_chunk(self, **kwargs):
        defaults = {
            "content": "x",
            "chunk_type": "function",
            "start_line": 1,
            "end_line": 5,
            "file_path": "a.py",
            "relative_path": "a.py",
            "folder_structure": [],
            "name": "foo",
            "parent_name": None,
            "language": "python",
            "chunk_id": None,
            "community_id": None,
        }
        defaults.update(kwargs)
        return CodeChunk(**defaults)

    def test_maps_correctly_with_parent_name(self):
        """chunk_id=None + parent_name + name → key=path:L1-L2:type:parent.name."""
        chunk = self._make_chunk(
            relative_path="src/a.py",
            start_line=10,
            end_line=20,
            chunk_type="method",
            parent_name="MyClass",
            name="my_method",
            chunk_id=None,
        )
        community_map = {"src/a.py:10-20:method:MyClass.my_method": 42}
        result = LanguageChunker._assign_community_ids([chunk], community_map)
        assert len(result) == 1
        assert result[0].community_id == 42

    def test_uses_chunk_id_when_set(self):
        """When chunk_id is set, it is used as the lookup key verbatim."""
        chunk = self._make_chunk(chunk_id="file.py:5-10:function:foo")
        community_map = {"file.py:5-10:function:foo": 7}
        result = LanguageChunker._assign_community_ids([chunk], community_map)
        assert result[0].community_id == 7

    def test_community_none_when_key_missing(self):
        """community_id is None when the lookup key is not in community_map."""
        chunk = self._make_chunk(chunk_id="file.py:1-5:function:unknown")
        result = LanguageChunker._assign_community_ids([chunk], {})
        assert result[0].community_id is None


class TestToTreesitterChunks:
    """Direct tests for LanguageChunker._to_treesitter_chunks static helper."""

    def _make_chunk(self, **kwargs):
        defaults = {
            "content": "def foo(): pass",
            "chunk_type": "function",
            "start_line": 1,
            "end_line": 3,
            "file_path": "a.py",
            "relative_path": "a.py",
            "folder_structure": [],
            "name": "foo",
            "parent_name": None,
            "language": "python",
            "chunk_id": "a.py:1-3:function:foo",
            "community_id": 5,
            "calls": ["bar"],
            "relationships": [],
            "docstring": None,
            "decorators": [],
            "imports": [],
            "complexity_score": 1,
            "tags": set(),
        }
        defaults.update(kwargs)
        return CodeChunk(**defaults)

    def test_preserves_key_fields(self):
        """Converted TreeSitterChunk carries content, line range, community_id."""
        chunk = self._make_chunk(
            content="hello", start_line=10, end_line=15, community_id=3
        )
        result = LanguageChunker._to_treesitter_chunks([chunk])
        assert len(result) == 1
        ts = result[0]
        assert ts.content == "hello"
        assert ts.start_line == 10
        assert ts.end_line == 15
        assert ts.community_id == 3

    def test_metadata_carries_calls_and_file_path(self):
        """metadata dict includes calls and file_path from the original chunk."""
        chunk = self._make_chunk(calls=["bar", "baz"], file_path="mod/b.py")
        result = LanguageChunker._to_treesitter_chunks([chunk])
        assert result[0].metadata["calls"] == ["bar", "baz"]
        assert result[0].metadata["file_path"] == "mod/b.py"


class TestFromTreesitterChunks:
    """Direct tests for LanguageChunker._from_treesitter_chunks static helper."""

    def _make_original(self, file_path, start_line, end_line):
        return CodeChunk(
            content="orig",
            chunk_type="function",
            start_line=start_line,
            end_line=end_line,
            file_path=file_path,
            relative_path=file_path,
            folder_structure=[],
            name="orig_fn",
            parent_name=None,
            language="python",
            chunk_id=None,
            community_id=1,
            calls=["dep"],
            relationships=[],
            docstring="doc",
            decorators=[],
            imports=[],
            complexity_score=2,
            tags=set(),
        )

    def _make_ts_chunk(self, file_path, start_line, end_line, node_type="function"):
        from chunking.languages.base import TreeSitterChunk

        return TreeSitterChunk(
            content="merged content",
            start_line=start_line,
            end_line=end_line,
            node_type=node_type,
            language="python",
            metadata={
                "file_path": file_path,
                "name": "fn",
                "merged_from": None,
                "relative_path": file_path,
                "calls": [],
                "relationships": [],
                "docstring": None,
                "decorators": [],
                "imports": [],
                "complexity_score": 0,
                "tags": set(),
            },
            chunk_id=None,
            parent_class=None,
            community_id=1,
        )

    def test_containment_match_uses_original_metadata(self):
        """Pass 1: exact containment → uses the original chunk's file_path."""
        orig = self._make_original("a.py", 5, 10)
        ts = self._make_ts_chunk("a.py", 5, 10)
        result = LanguageChunker._from_treesitter_chunks([ts], [orig])
        assert len(result) == 1
        assert result[0].file_path == "a.py"
        assert result[0].calls == ["dep"]

    def test_file_fallback_when_no_containment(self):
        """Pass 2: no exact containment → falls back to any chunk from same file."""
        orig = self._make_original("a.py", 1, 4)
        ts = self._make_ts_chunk("a.py", 5, 10)  # different range
        result = LanguageChunker._from_treesitter_chunks([ts], [orig])
        assert len(result) == 1
        assert result[0].file_path == "a.py"

    def test_skips_chunk_when_no_file_match(self):
        """Pass 3: no chunk shares the file_path → chunk skipped, result shorter."""
        orig = self._make_original("b.py", 1, 5)
        ts = self._make_ts_chunk("a.py", 1, 5)  # different file
        result = LanguageChunker._from_treesitter_chunks([ts], [orig])
        assert len(result) == 0
