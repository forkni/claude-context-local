"""Tests for community-level summary generation."""

from pathlib import Path

from chunking.python_ast_chunker import CodeChunk
from graph.community_summarizer import generate_community_summaries


class TestGenerateCommunitySummaries:
    def _make_chunk(
        self,
        rel_path,
        chunk_type,
        name,
        parent_name=None,
        docstring=None,
        imports=None,
        start_line=1,
        end_line=5,
    ):
        """Helper to create a CodeChunk for testing."""
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

    def test_generates_summary_for_multi_member_community(self):
        chunks = [
            self._make_chunk("search/foo.py", "class", "Foo", docstring="Foo class."),
            self._make_chunk("search/foo.py", "method", "bar", parent_name="Foo"),
        ]
        community_map = {
            "search/foo.py:1-5:class:Foo": 0,
            "search/foo.py:1-5:method:bar": 0,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert len(summaries) == 1
        assert summaries[0].chunk_type == "community"
        assert "Foo" in summaries[0].content

    def test_skips_single_member_communities(self):
        chunks = [self._make_chunk("search/solo.py", "function", "solo")]
        community_map = {"search/solo.py:1-5:function:solo": 0}
        assert generate_community_summaries(chunks, community_map) == []

    def test_chunk_id_format(self):
        chunks = [
            self._make_chunk("graph/storage.py", "class", "A"),
            self._make_chunk("graph/storage.py", "function", "b"),
        ]
        community_map = {
            "graph/storage.py:1-5:class:A": 5,
            "graph/storage.py:1-5:function:b": 5,
        }
        summaries = generate_community_summaries(chunks, community_map)
        # Label format: {directory}_{primary_symbol}
        assert summaries[0].chunk_id.startswith("__community__/graph_")
        assert ":0-0:community:" in summaries[0].chunk_id

    def test_summary_contains_imports(self):
        chunks = [
            self._make_chunk("a/b.py", "class", "X", imports=["os", "sys"]),
            self._make_chunk("a/b.py", "function", "f"),
        ]
        community_map = {
            "a/b.py:1-5:class:X": 1,
            "a/b.py:1-5:function:f": 1,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert "os" in summaries[0].content

    def test_summary_contains_docstrings(self):
        chunks = [
            self._make_chunk(
                "a/b.py", "class", "MyClass", docstring="Does important things."
            ),
            self._make_chunk("a/b.py", "function", "helper"),
        ]
        community_map = {
            "a/b.py:1-5:class:MyClass": 2,
            "a/b.py:1-5:function:helper": 2,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert "Does important things" in summaries[0].content

    def test_multiple_communities_produce_multiple_summaries(self):
        chunks = [
            self._make_chunk("a.py", "class", "A"),
            self._make_chunk("a.py", "function", "a_func"),
            self._make_chunk("b.py", "class", "B"),
            self._make_chunk("b.py", "function", "b_func"),
        ]
        community_map = {
            "a.py:1-5:class:A": 0,
            "a.py:1-5:function:a_func": 0,
            "b.py:1-5:class:B": 1,
            "b.py:1-5:function:b_func": 1,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert len(summaries) == 2

    def test_summary_has_correct_metadata(self):
        chunks = [
            self._make_chunk("search/engine.py", "class", "SearchEngine"),
            self._make_chunk("search/engine.py", "function", "search"),
        ]
        community_map = {
            "search/engine.py:1-5:class:SearchEngine": 3,
            "search/engine.py:1-5:function:search": 3,
        }
        summaries = generate_community_summaries(chunks, community_map)
        summary = summaries[0]

        assert summary.chunk_type == "community"
        assert summary.name.startswith("search_")
        assert summary.file_path.startswith("__community__/")
        assert summary.relative_path.startswith("__community__/")
        assert summary.start_line == 0
        assert summary.end_line == 0
        assert summary.language == "python"

    def test_summary_includes_methods_with_parent_name(self):
        chunks = [
            self._make_chunk("a/b.py", "class", "MyClass"),
            self._make_chunk("a/b.py", "method", "my_method", parent_name="MyClass"),
        ]
        community_map = {
            "a/b.py:1-5:class:MyClass": 4,
            "a/b.py:1-5:method:my_method": 4,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert "MyClass.my_method" in summaries[0].content

    def test_hub_detection_uses_largest_chunk(self):
        chunks = [
            self._make_chunk(
                "test.py", "function", "small_func", start_line=1, end_line=5
            ),
            self._make_chunk(
                "test.py", "function", "large_func", start_line=10, end_line=100
            ),
        ]
        community_map = {
            "test.py:1-5:function:small_func": 7,
            "test.py:10-100:function:large_func": 7,
        }
        summaries = generate_community_summaries(chunks, community_map)
        assert "Hub function: large_func" in summaries[0].content

    def test_dominant_directory_extraction(self):
        chunks = [
            self._make_chunk("search/foo.py", "class", "Foo"),
            self._make_chunk("search/bar.py", "function", "bar"),
            self._make_chunk("utils/util.py", "function", "util"),
        ]
        community_map = {
            "search/foo.py:1-5:class:Foo": 9,
            "search/bar.py:1-5:function:bar": 9,
            "utils/util.py:1-5:function:util": 9,
        }
        summaries = generate_community_summaries(chunks, community_map)
        # Should pick "search" as dominant directory (2 chunks vs 1)
        assert "Dominant directory: search" in summaries[0].content

    def test_label_format_with_class_primary(self):
        chunks = [
            self._make_chunk("graph/storage.py", "class", "GraphStorage"),
            self._make_chunk("graph/storage.py", "method", "save"),
        ]
        community_map = {
            "graph/storage.py:1-5:class:GraphStorage": 10,
            "graph/storage.py:1-5:method:save": 10,
        }
        summaries = generate_community_summaries(chunks, community_map)
        # Label should be graph_GraphStorage
        assert "graph_GraphStorage" in summaries[0].chunk_id

    def test_label_format_with_function_primary(self):
        chunks = [
            self._make_chunk("utils/helpers.py", "function", "helper_func"),
            self._make_chunk("utils/helpers.py", "function", "other_func"),
        ]
        community_map = {
            "utils/helpers.py:1-5:function:helper_func": 11,
            "utils/helpers.py:1-5:function:other_func": 11,
        }
        summaries = generate_community_summaries(chunks, community_map)
        # Label should be utils_helper_func (first function)
        assert "utils_helper_func" in summaries[0].chunk_id

    def test_empty_community_map(self):
        chunks = [
            self._make_chunk("a.py", "function", "f1"),
            self._make_chunk("b.py", "function", "f2"),
        ]
        community_map = {}
        summaries = generate_community_summaries(chunks, community_map)
        assert summaries == []

    def test_chunks_without_chunk_id(self):
        chunks = [
            CodeChunk(
                content="",
                chunk_type="function",
                start_line=1,
                end_line=5,
                file_path="",
                relative_path="",
                folder_structure=[],
                name="func",
                language="python",
                chunk_id=None,  # Missing chunk_id
            )
        ]
        community_map = {}
        summaries = generate_community_summaries(chunks, community_map)
        assert summaries == []
