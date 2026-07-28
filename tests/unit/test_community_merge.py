"""Unit tests for community-based chunk merging (Phase 1)."""

from chunking.languages.base import TreeSitterChunk
from chunking.languages.python import PythonChunker
from search.config import ChunkingConfig


class TestCommunityMerge:
    """Tests for community-based merge functionality."""

    def create_test_chunk(
        self,
        content: str,
        start_line: int,
        end_line: int,
        parent_class: str = None,
        community_id: int = None,
    ) -> TreeSitterChunk:
        """Helper to create test chunks."""
        return TreeSitterChunk(
            content=content,
            start_line=start_line,
            end_line=end_line,
            node_type="function",
            language="python",
            metadata={},
            parent_class=parent_class,
            community_id=community_id,
        )

    def test_community_merge_same_community(self):
        """Chunks with same community_id merge together."""
        chunker = PythonChunker()

        # Three small chunks (10 tokens each) in same community
        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=0),
            self.create_test_chunk("def baz(): pass", 5, 6, community_id=0),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # All 3 should merge into 1 (same community)
        assert orig == 3
        assert final == 1
        assert len(merged) == 1

    def test_community_merge_different_communities(self):
        """Chunks with different community_id stay separate."""
        chunker = PythonChunker()

        # Three small chunks in different communities
        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=1),
            self.create_test_chunk("def baz(): pass", 5, 6, community_id=2),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # All should stay separate (different communities)
        assert orig == 3
        assert final == 3
        assert len(merged) == 3

    def test_community_merge_respects_token_limit(self):
        """Even same community splits at max_tokens.

        Note: both chunks here are >= min_tokens, so each takes the Case-3
        solo-passthrough path with an EMPTY current_group. This does not
        exercise the budget check against an already-open group — see
        test_community_merge_respects_token_limit_with_open_group for that.
        """
        chunker = PythonChunker()

        # Two chunks in same community, but large content
        chunks = [
            self.create_test_chunk(
                "def foo(): " + "x = 1\n" * 100, 1, 100, community_id=0
            ),  # ~200 tokens
            self.create_test_chunk(
                "def bar(): " + "y = 2\n" * 100, 101, 200, community_id=0
            ),  # ~200 tokens
        ]

        # Merge with max_merged_tokens=300
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=300, use_community_boundary=True
        )

        # Should stay separate (would exceed max_merged_tokens)
        assert final == 2
        assert len(merged) == 2

    def test_community_merge_disabled_uses_parent_class(self):
        """Config disable falls back to parent_class."""
        chunker = PythonChunker()

        # Two chunks: same parent_class but different community
        chunks = [
            self.create_test_chunk(
                "def foo(): pass", 1, 2, parent_class="MyClass", community_id=0
            ),
            self.create_test_chunk(
                "def bar(): pass", 3, 4, parent_class="MyClass", community_id=1
            ),
        ]

        # Merge with community boundary DISABLED (use parent_class)
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=False
        )

        # Should merge (same parent_class, community_id ignored)
        assert final == 1
        assert len(merged) == 1

    def test_community_merge_mixed_boundaries(self):
        """Complex case: some same community, some different."""
        chunker = PythonChunker()

        # 5 chunks: [0, 0, 1, 1, 2]
        chunks = [
            self.create_test_chunk("def a(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def b(): pass", 3, 4, community_id=0),
            self.create_test_chunk("def c(): pass", 5, 6, community_id=1),
            self.create_test_chunk("def d(): pass", 7, 8, community_id=1),
            self.create_test_chunk("def e(): pass", 9, 10, community_id=2),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Should merge into 3 groups: [0+0], [1+1], [2]
        assert orig == 5
        assert final == 3
        assert len(merged) == 3

    def test_community_merge_large_chunk_not_merged(self):
        """Large chunks don't merge even if same community.

        Note: the large chunk is first, so current_group is still EMPTY when
        it hits Case 3 — this does not exercise passthrough once a group is
        already open. See test_community_merge_large_chunk_passthrough_with_open_group.
        """
        chunker = PythonChunker()

        # Two chunks: one large (100 tokens), one small (10 tokens), same community
        chunks = [
            self.create_test_chunk(
                "def foo(): " + "x = 1\n" * 50, 1, 50, community_id=0
            ),  # ~100 tokens
            self.create_test_chunk(
                "def bar(): pass", 51, 52, community_id=0
            ),  # ~3 tokens
        ]

        # Merge with min_tokens=50
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Large chunk stays separate, small chunk added directly
        # Result: [large_chunk, small_chunk] (no merge because first is large)
        assert final == 2

    def test_community_merge_respects_token_limit_with_open_group(self):
        """Budget check must fire even when the community hasn't changed.

        Regression test: four 30-token chunks, all in the same community, with
        max_merged_tokens=70. The first two chunks (60 tokens) fill the budget;
        the third would push it to 90 > 70, so it must start a new group. Before
        the fix, the community-boundary elif arm consumed the chain on every
        chunk (matching whether or not the community changed), so Case 2 (the
        budget check) was unreachable once a group was open — all four chunks
        collapsed into a single oversized group.
        """
        chunker = PythonChunker()

        def make_chunk(n_words: int, start: int) -> TreeSitterChunk:
            content = " ".join(f"word{i}" for i in range(n_words))
            return self.create_test_chunk(content, start, start + 1, community_id=0)

        chunks = [make_chunk(30, i * 2 + 1) for i in range(4)]

        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=70, use_community_boundary=True
        )

        assert orig == 4
        assert final == 2
        assert len(merged) == 2

    def test_community_merge_large_chunk_passthrough_with_open_group(self):
        """A large chunk mid-stream must pass through solo, not get absorbed.

        Regression test: small (10) -> large (100) -> small (10) tokens, all
        same community, min_tokens=50. The large chunk arrives while a group
        is already open from the first small chunk. Before the fix, Case 3
        (the large-chunk passthrough) was unreachable once a group was open in
        community mode, so the large chunk got silently absorbed and all three
        chunks collapsed into a single merged blob (final == 1). After the
        fix, the large chunk flushes and passes through solo, and the
        trailing small chunk has nothing left to merge with, so all three
        chunks stay distinct (final == 3).
        """
        chunker = PythonChunker()

        def make_chunk(n_words: int, start: int) -> TreeSitterChunk:
            content = " ".join(f"word{i}" for i in range(n_words))
            return self.create_test_chunk(content, start, start + 1, community_id=0)

        small_1 = make_chunk(10, 1)
        large = make_chunk(100, 3)
        small_2 = make_chunk(10, 5)
        chunks = [small_1, large, small_2]

        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        assert orig == 3
        assert final == 3
        # The large chunk must pass through unchanged (identity, not a copy).
        assert large in merged

    def test_community_merge_none_community_id_respects_token_limit(self):
        """None community_id is a valid boundary key, not a bypass.

        Regression test: production-dominant case. community_id is only
        populated by assign_community_ids and is None whenever the Louvain
        lookup misses a chunk; all None-community chunks compare equal, so a
        file whose chunks miss the map all fall into one bucket. Four
        30-token chunks with community_id=None and max_merged_tokens=70 must
        still split at the budget, exactly like test
        test_community_merge_respects_token_limit_with_open_group.
        """
        chunker = PythonChunker()

        def make_chunk(n_words: int, start: int) -> TreeSitterChunk:
            content = " ".join(f"word{i}" for i in range(n_words))
            return self.create_test_chunk(content, start, start + 1, community_id=None)

        chunks = [make_chunk(30, i * 2 + 1) for i in range(4)]

        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=70, use_community_boundary=True
        )

        assert orig == 4
        assert final == 2
        assert len(merged) == 2

    def test_community_merge_none_community_id(self):
        """Chunks with None community_id handled gracefully."""
        chunker = PythonChunker()

        # Three chunks: [None, None, 0]
        chunks = [
            self.create_test_chunk("def a(): pass", 1, 2, community_id=None),
            self.create_test_chunk("def b(): pass", 3, 4, community_id=None),
            self.create_test_chunk("def c(): pass", 5, 6, community_id=0),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # First two should merge (both None), third separate
        assert final == 2

    def test_community_id_field_exists(self):
        """TreeSitterChunk has community_id field."""
        chunk = TreeSitterChunk(
            content="test",
            start_line=1,
            end_line=2,
            node_type="function",
            language="python",
            metadata={},
        )

        # community_id should be None by default
        assert hasattr(chunk, "community_id")
        assert chunk.community_id is None

        # Should be settable
        chunk.community_id = 5
        assert chunk.community_id == 5

    def test_community_merge_preserves_content(self):
        """Merged chunks preserve all content."""
        chunker = PythonChunker()

        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=0),
        ]

        merged, _, _ = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Merged chunk should contain both functions
        assert "def foo(): pass" in merged[0].content
        assert "def bar(): pass" in merged[0].content

    def test_config_integration(self):
        """ChunkingConfig has community_resolution field (auto-select architecture)."""
        config = ChunkingConfig()

        # community_resolution field should exist with default 1.0
        assert hasattr(config, "community_resolution")
        assert config.community_resolution == 1.0

        # Should be settable (tuning parameter for Louvain algorithm)
        config.community_resolution = 1.5
        assert config.community_resolution == 1.5

        # enable_community_merge and enable_community_detection fields restored
        assert hasattr(config, "enable_community_merge")
        assert hasattr(config, "enable_community_detection")
        # Default values should be True
        assert config.enable_community_merge is True
        assert config.enable_community_detection is True

    def test_merge_boundary_config_default(self):
        """merge_boundary defaults to "community" (pre-gate behavior)."""
        config = ChunkingConfig()
        assert config.merge_boundary == "community"


class TestRemergeBoundarySelection:
    """remerge_chunks_with_communities honors use_community_boundary."""

    @staticmethod
    def _make_code_chunk():
        from chunking.python_ast_chunker import CodeChunk

        return CodeChunk(
            file_path="/proj/a.py",
            relative_path="a.py",
            folder_structure=[],
            chunk_type="function",
            content="def foo(): pass",
            start_line=1,
            end_line=2,
            name="foo",
            chunk_id="a.py:1-2:function:foo",
        )

    def _run_with_boundary(self, **remerge_kwargs):
        """Run remerge with a spy merger; return the kwargs the merger saw."""
        from chunking.community_remerge import remerge_chunks_with_communities

        seen: dict = {}

        def spy_merger(ts_chunks, **kwargs):
            seen.update(kwargs)
            return ts_chunks, len(ts_chunks), len(ts_chunks)

        chunk = self._make_code_chunk()
        remerge_chunks_with_communities(
            chunks=[chunk],
            community_map={chunk.chunk_id: 0},
            merger=spy_merger,
            **remerge_kwargs,
        )
        return seen

    def test_default_is_community_boundary(self):
        seen = self._run_with_boundary()
        assert seen["use_community_boundary"] is True

    def test_sibling_boundary_passed_through(self):
        seen = self._run_with_boundary(use_community_boundary=False)
        assert seen["use_community_boundary"] is False
