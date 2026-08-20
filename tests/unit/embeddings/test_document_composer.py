"""Tests for embeddings.document_composer — the model-free chunk-to-document seam.

Extracted from tests/unit/embeddings/test_embedder.py's TestContextExtraction
(architecture review, candidate 6). This module never imports
``embeddings.embedder.CodeEmbedder`` — that import-absence is itself the
model-freeness proof for ``EmbeddingDocumentComposer``, and it is why none of
these tests need the model-loader-patching decorators their ``TestContextExtraction``
predecessors carried.
"""

from unittest.mock import patch

from chunking.python_ast_chunker import CodeChunk
from embeddings.document_composer import (
    EmbeddingDocumentComposer,
    EmbeddingDocumentPolicy,
)


class TestContextExtraction:
    """Test context extraction features (v0.8.0+) for import and class signatures."""

    def test_extract_import_context_basic(self, tmp_path):
        """Test basic import context extraction."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\nimport sys\nfrom pathlib import Path\n\ndef func():\n    pass\n"
        )

        composer = EmbeddingDocumentComposer()

        # Extract imports
        import_context = composer._extract_import_context(
            str(test_file), max_imports=10
        )

        assert "import os" in import_context
        assert "import sys" in import_context
        assert "from pathlib import Path" in import_context
        assert "def func()" not in import_context  # Should stop at first non-import

    def test_extract_import_context_with_max_limit(self, tmp_path):
        """Test import extraction with max_imports limit."""
        test_file = tmp_path / "test.py"
        imports = "\n".join([f"import module{i}" for i in range(20)])
        test_file.write_text(f"{imports}\n\ndef func():\n    pass\n")

        composer = EmbeddingDocumentComposer()

        # Extract only 5 imports
        import_context = composer._extract_import_context(str(test_file), max_imports=5)

        lines = import_context.split("\n")
        assert len(lines) == 5
        assert all("import module" in line for line in lines)

    def test_extract_import_context_no_imports(self, tmp_path):
        """Test extraction from file with no imports."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def func():\n    pass\n")

        composer = EmbeddingDocumentComposer()

        import_context = composer._extract_import_context(
            str(test_file), max_imports=10
        )

        assert import_context == ""  # Should return empty string

    def test_get_class_signature_for_method(self, tmp_path):
        """Test class signature extraction for method chunks."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            'class MyClass:\n    """MyClass docstring."""\n\n    def method(self):\n        pass\n'
        )

        composer = EmbeddingDocumentComposer()

        # Create mock chunk for a method
        mock_chunk = CodeChunk(
            file_path=str(test_file),
            relative_path="test.py",
            folder_structure=".",
            chunk_type="method",
            start_line=4,
            end_line=5,
            name="method",
            parent_name="MyClass",
            docstring="",
            content="def method(self):\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        class_signature = composer._get_class_signature(mock_chunk, max_lines=5)

        assert "class MyClass:" in class_signature
        assert "MyClass docstring" in class_signature

    def test_get_class_signature_non_method(self):
        """Test that class signature is not extracted for non-method chunks."""
        composer = EmbeddingDocumentComposer()

        # Create mock chunk for a function (not a method)
        mock_chunk = CodeChunk(
            file_path="/fake/path.py",
            relative_path="path.py",
            folder_structure=".",
            chunk_type="function",  # Not "method"
            start_line=1,
            end_line=2,
            name="func",
            parent_name=None,
            docstring="",
            content="def func():\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        class_signature = composer._get_class_signature(mock_chunk)

        assert class_signature == ""  # Should return empty for non-methods

    def test_read_source_cached_shared_across_import_and_class_signature(
        self, tmp_path
    ):
        """I1: _extract_import_context and _get_class_signature share one cached
        read per file (#50 pattern), instead of one `open()` per call.

        A file with two method chunks previously triggered up to 3 separate
        `open()` calls (1 import-context scan + 2 class-signature reads); with
        the shared `_read_source_cached` cache they collapse to 1.
        """
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\nimport sys\n\n"
            'class MyClass:\n    """Doc."""\n\n'
            "    def method_a(self):\n        pass\n\n"
            "    def method_b(self):\n        pass\n"
        )

        composer = EmbeddingDocumentComposer()

        def make_chunk(name, start_line, end_line):
            return CodeChunk(
                file_path=str(test_file),
                relative_path="test.py",
                folder_structure=".",
                chunk_type="method",
                start_line=start_line,
                end_line=end_line,
                name=name,
                parent_name="MyClass",
                docstring="",
                content=f"def {name}(self):\n    pass",
                decorators=[],
                imports=[],
                complexity_score=1.0,
                tags=[],
                calls=[],
                relationships=[],
            )

        chunk_a = make_chunk("method_a", 7, 8)
        chunk_b = make_chunk("method_b", 10, 11)

        with patch("embeddings.document_composer.open", wraps=open) as mock_open_fn:
            import_ctx = composer._extract_import_context(str(test_file))
            sig_a = composer._get_class_signature(chunk_a)
            sig_b = composer._get_class_signature(chunk_b)

        assert mock_open_fn.call_count == 1  # one shared read across all 3 calls
        assert "import os" in import_ctx
        assert "import sys" in import_ctx
        assert "class MyClass:" in sig_a
        assert "class MyClass:" in sig_b

    def test_extract_import_context_memoized_per_file(self, tmp_path):
        """I2: repeated calls for the same file + max_imports hit the cache.

        Without memoization, `"\n".join(lines)` builds a fresh string object
        on every call. With I2, a second call for the same (file, max_imports)
        returns the exact cached object rather than re-scanning — proven here
        via object identity (`is`), not just equality.
        """
        test_file = tmp_path / "multi.py"
        test_file.write_text("import os\nimport sys\n\ndef f():\n    pass\n")

        composer = EmbeddingDocumentComposer()

        first = composer._extract_import_context(str(test_file), max_imports=10)
        second = composer._extract_import_context(str(test_file), max_imports=10)

        assert first == second
        assert first is second  # I2: cache hit, not a re-scan
        assert len(composer._import_ctx_cache) == 1

    def test_get_class_signature_memoized_across_sibling_methods(self, tmp_path):
        """I2b: sibling methods of the same class share one regex-search result.

        Without memoization, `content[start:].split("\n")[:max_lines]` (then
        joined/stripped) builds a fresh string on every call. With I2b, every
        sibling method after the first gets the exact cached object for the
        same (file, parent_name, max_lines) — proven via object identity.
        """
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "import os\nimport sys\n\n"
            'class MyClass:\n    """Doc."""\n\n'
            "    def method_a(self):\n        pass\n\n"
            "    def method_b(self):\n        pass\n"
        )

        composer = EmbeddingDocumentComposer()

        def make_chunk(name, start_line, end_line):
            return CodeChunk(
                file_path=str(test_file),
                relative_path="test.py",
                folder_structure=".",
                chunk_type="method",
                start_line=start_line,
                end_line=end_line,
                name=name,
                parent_name="MyClass",
                docstring="",
                content=f"def {name}(self):\n    pass",
                decorators=[],
                imports=[],
                complexity_score=1.0,
                tags=[],
                calls=[],
                relationships=[],
            )

        chunk_a = make_chunk("method_a", 7, 8)
        chunk_b = make_chunk("method_b", 10, 11)

        sig_a = composer._get_class_signature(chunk_a)
        sig_b = composer._get_class_signature(chunk_b)

        assert sig_a == sig_b
        assert sig_a is sig_b  # I2b: method_b's call is a cache hit
        assert len(composer._class_sig_cache) == 1


def _full_featured_chunk(tmp_path):
    """A method chunk with a real backing file exercising every optional
    ``compose()`` section: structural header, import context, parent-class
    context, and a chunk docstring."""
    test_file = tmp_path / "mod.py"
    test_file.write_text(
        "import os\nimport sys\n\n"
        'class MyClass:\n    """Class doc."""\n\n'
        "    def method(self):\n        return 1\n"
    )
    return CodeChunk(
        file_path=str(test_file),
        relative_path="mod.py",
        folder_structure=".",
        chunk_type="method",
        start_line=7,
        end_line=8,
        name="method",
        parent_name="MyClass",
        docstring="Method docstring.",
        content="def method(self):\n    return 1",
        decorators=[],
        imports=[],
        complexity_score=1.0,
        tags=[],
        calls=[],
        relationships=[],
    )


class TestComposeBranches:
    """Gate B2 (architecture-review plan, Workstream C): permanent synthetic
    characterization tests for ``EmbeddingDocumentComposer.compose()``, one
    per branch. Pinned against a synthetic ``tmp_path`` corpus rather than
    live repo files, which drift (the staleness class ADR-0043 exists to
    kill).

    Two branches this gate is meant to cover are already pinned by
    ``TestContextExtraction`` above and are not duplicated here: the import
    cap (``test_extract_import_context_with_max_limit``) and the non-method
    chunk (``test_get_class_signature_non_method``).
    """

    def test_compose_all_flags_on_includes_every_section_in_order(self, tmp_path):
        composer = EmbeddingDocumentComposer()
        chunk = _full_featured_chunk(tmp_path)
        policy = EmbeddingDocumentPolicy()  # all 5 fields default True/10/5

        result = composer.compose(chunk, policy)

        header_idx = result.index("# mod.py | method MyClass.method")
        imports_idx = result.index("# Imports:")
        class_idx = result.index("# Parent class:")
        docstring_idx = result.index('"""Method docstring."""')
        content_idx = result.index("def method(self):\n    return 1")

        assert header_idx < imports_idx < class_idx < docstring_idx < content_idx
        assert "import os" in result
        assert "class MyClass:" in result

    def test_compose_structural_header_disabled_omits_header(self, tmp_path):
        composer = EmbeddingDocumentComposer()
        chunk = _full_featured_chunk(tmp_path)
        policy = EmbeddingDocumentPolicy(enable_structural_header=False)

        result = composer.compose(chunk, policy)

        assert "# mod.py | method MyClass.method" not in result
        assert "# Imports:" in result  # sibling sections stay on

    def test_compose_import_context_disabled_omits_imports_section(self, tmp_path):
        composer = EmbeddingDocumentComposer()
        chunk = _full_featured_chunk(tmp_path)
        policy = EmbeddingDocumentPolicy(enable_import_context=False)

        result = composer.compose(chunk, policy)

        assert "# Imports:" not in result
        assert "# Parent class:" in result  # sibling section stays on

    def test_compose_class_context_disabled_omits_parent_class_section(self, tmp_path):
        composer = EmbeddingDocumentComposer()
        chunk = _full_featured_chunk(tmp_path)
        policy = EmbeddingDocumentPolicy(enable_class_context=False)

        result = composer.compose(chunk, policy)

        assert "# Parent class:" not in result
        assert "# Imports:" in result  # sibling section stays on

    def test_docstring_over_budget_is_truncated_with_ellipsis(self, tmp_path):
        composer = EmbeddingDocumentComposer()
        policy = EmbeddingDocumentPolicy(
            enable_import_context=False,
            enable_class_context=False,
            enable_structural_header=False,
        )
        long_docstring = "x" * 350
        chunk = CodeChunk(
            file_path=str(tmp_path / "f.py"),
            relative_path="f.py",
            folder_structure=".",
            chunk_type="function",
            start_line=1,
            end_line=2,
            name="f",
            parent_name=None,
            docstring=long_docstring,
            content="def f():\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        result = composer.compose(chunk, policy, max_chars=6000)

        assert f'"""{"x" * 300}..."""' in result
        assert "x" * 350 not in result

    def test_body_over_budget_with_more_than_three_lines_uses_head_tail_truncation(
        self, tmp_path
    ):
        composer = EmbeddingDocumentComposer()
        policy = EmbeddingDocumentPolicy(
            enable_import_context=False,
            enable_class_context=False,
            enable_structural_header=False,
        )
        content = "\n".join(f"line_{i}" for i in range(20))
        chunk = CodeChunk(
            file_path=str(tmp_path / "f.py"),
            relative_path="f.py",
            folder_structure=".",
            chunk_type="function",
            start_line=1,
            end_line=20,
            name="f",
            parent_name=None,
            docstring="",
            content=content,
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        # context_len=0 (all context sections off) -> remaining_budget = 60-0-10 = 50.
        result = composer.compose(chunk, policy, max_chars=60)

        assert result == (
            "line_0\nline_1\nline_2\nline_3\nline_4\n    # ... (truncated) ..."
        )
        assert "line_5" not in result
        assert "line_19" not in result

    def test_body_over_budget_with_three_or_fewer_lines_uses_character_truncation(
        self, tmp_path
    ):
        composer = EmbeddingDocumentComposer()
        policy = EmbeddingDocumentPolicy(
            enable_import_context=False,
            enable_class_context=False,
            enable_structural_header=False,
        )
        chunk = CodeChunk(
            file_path=str(tmp_path / "f.py"),
            relative_path="f.py",
            folder_structure=".",
            chunk_type="function",
            start_line=1,
            end_line=1,
            name="f",
            parent_name=None,
            docstring="",
            content="a" * 50,  # single line -> len(lines) == 1, not > 3
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        # context_len=0 -> remaining_budget = 20-0-10 = 10.
        result = composer.compose(chunk, policy, max_chars=20)

        assert result == "a" * 10 + "..."

    def test_get_class_signature_truncates_at_closing_triple_quote_within_capped_lines(
        self, tmp_path
    ):
        """Class-signature cap + quote truncation: max_lines captures a window
        that includes trailing, unrelated source (a blank line and the next
        def), but the closing `\"\"\"` truncates the signature before that
        window is exhausted."""
        test_file = tmp_path / "test.py"
        test_file.write_text(
            "class MyClass:\n"
            '    """This is\n'
            '    a docstring."""\n'
            "\n"
            "    def method(self):\n"
            "        pass\n"
        )
        composer = EmbeddingDocumentComposer()
        chunk = CodeChunk(
            file_path=str(test_file),
            relative_path="test.py",
            folder_structure=".",
            chunk_type="method",
            start_line=5,
            end_line=6,
            name="method",
            parent_name="MyClass",
            docstring="",
            content="def method(self):\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        signature = composer._get_class_signature(chunk, max_lines=5)

        assert signature == 'class MyClass:\n    """This is\n    a docstring."""'
        assert "def method(self):" not in signature

    def test_extract_import_context_missing_file_returns_empty_without_raising(
        self, tmp_path
    ):
        composer = EmbeddingDocumentComposer()
        missing = tmp_path / "does_not_exist.py"

        result = composer._extract_import_context(str(missing))

        assert result == ""

    def test_get_class_signature_missing_file_returns_empty_without_raising(
        self, tmp_path
    ):
        composer = EmbeddingDocumentComposer()
        missing = tmp_path / "does_not_exist.py"
        chunk = CodeChunk(
            file_path=str(missing),
            relative_path="does_not_exist.py",
            folder_structure=".",
            chunk_type="method",
            start_line=1,
            end_line=2,
            name="method",
            parent_name="MyClass",
            docstring="",
            content="def method(self):\n    pass",
            decorators=[],
            imports=[],
            complexity_score=1.0,
            tags=[],
            calls=[],
            relationships=[],
        )

        result = composer._get_class_signature(chunk)

        assert result == ""
