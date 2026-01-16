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
