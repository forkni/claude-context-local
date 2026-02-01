"""Tests for file-level module summary generation."""

from pathlib import Path

from chunking.file_summarizer import generate_file_summaries
from chunking.python_ast_chunker import CodeChunk


class TestGenerateFileSummaries:
    def _make_chunk(
        self,
        rel_path,
        chunk_type,
        name,
        parent_name=None,
        docstring=None,
        imports=None,
    ):
        """Helper to create a CodeChunk for testing."""
        return CodeChunk(
            content=f"def {name}(): pass",
            chunk_type=chunk_type,
            start_line=1,
            end_line=5,
            file_path=f"/project/{rel_path}",
            relative_path=rel_path,
            folder_structure=list(Path(rel_path).parent.parts),
            name=name,
            parent_name=parent_name,
            docstring=docstring,
            imports=imports or [],
            language="python",
            chunk_id=f"{rel_path}:1-5:{chunk_type}:{name}",
        )

    def test_generates_summary_for_multi_chunk_file(self):
        chunks = [
            self._make_chunk("search/foo.py", "class", "Foo", docstring="Foo class."),
            self._make_chunk("search/foo.py", "method", "bar", parent_name="Foo"),
        ]
        summaries = generate_file_summaries(chunks)
        assert len(summaries) == 1
        assert summaries[0].chunk_type == "module"
        assert summaries[0].name == "foo"
        assert "Foo" in summaries[0].content

    def test_skips_single_chunk_files(self):
        chunks = [self._make_chunk("search/solo.py", "function", "solo")]
        assert generate_file_summaries(chunks) == []

    def test_chunk_id_format(self):
        chunks = [
            self._make_chunk("graph/storage.py", "class", "A"),
            self._make_chunk("graph/storage.py", "function", "b"),
        ]
        summaries = generate_file_summaries(chunks)
        assert summaries[0].chunk_id == "graph/storage.py:0-0:module:storage"

    def test_summary_contains_imports(self):
        chunks = [
            self._make_chunk("a/b.py", "class", "X", imports=["os", "sys"]),
            self._make_chunk("a/b.py", "function", "f"),
        ]
        summaries = generate_file_summaries(chunks)
        assert "os" in summaries[0].content

    def test_summary_contains_docstrings(self):
        chunks = [
            self._make_chunk(
                "a/b.py", "class", "MyClass", docstring="Does important things."
            ),
            self._make_chunk("a/b.py", "function", "helper"),
        ]
        summaries = generate_file_summaries(chunks)
        assert "Does important things" in summaries[0].content

    def test_multiple_files_produce_multiple_summaries(self):
        chunks = [
            self._make_chunk("a.py", "class", "A"),
            self._make_chunk("a.py", "function", "a_func"),
            self._make_chunk("b.py", "class", "B"),
            self._make_chunk("b.py", "function", "b_func"),
        ]
        summaries = generate_file_summaries(chunks)
        assert len(summaries) == 2

    def test_summary_has_correct_metadata(self):
        chunks = [
            self._make_chunk("search/engine.py", "class", "SearchEngine"),
            self._make_chunk("search/engine.py", "function", "search"),
        ]
        summaries = generate_file_summaries(chunks)
        summary = summaries[0]

        assert summary.chunk_type == "module"
        assert summary.name == "engine"
        assert summary.relative_path == "search/engine.py"
        assert summary.start_line == 0
        assert summary.end_line == 0
        assert summary.language == "python"

    def test_summary_includes_methods_with_parent_name(self):
        chunks = [
            self._make_chunk("a/b.py", "class", "MyClass"),
            self._make_chunk("a/b.py", "method", "my_method", parent_name="MyClass"),
        ]
        summaries = generate_file_summaries(chunks)
        assert "MyClass.my_method" in summaries[0].content

    def test_summary_caps_lists_correctly(self):
        # Test that lists are capped at documented limits
        many_classes = [
            self._make_chunk("test.py", "class", f"Class{i}") for i in range(15)
        ]
        summaries = generate_file_summaries(many_classes)
        # Classes capped at 10
        class_names = [f"Class{i}" for i in range(10)]
        for name in class_names:
            assert name in summaries[0].content
        assert "Class14" not in summaries[0].content
