"""Basic tests for multi-language chunking."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from search.config import ChunkingConfig


class TestMultiLanguageChunker:
    """Test multi-language chunking functionality."""

    @pytest.fixture
    def chunker(self):
        """Create a chunker instance."""
        return MultiLanguageChunker()

    @pytest.fixture
    def test_data_dir(self):
        """Get test data directory."""
        return Path(__file__).parent.parent.parent / "test_data" / "multi_language"

    def test_supported_extensions(self, chunker):
        """Test that all required extensions are supported."""
        assert chunker.is_supported("test.py")
        assert chunker.is_supported("test.js")
        assert chunker.is_supported("test.ts")
        assert chunker.is_supported("test.tsx")
        assert chunker.is_supported("test.go")
        assert chunker.is_supported("test.c")
        assert chunker.is_supported("test.cpp")
        assert chunker.is_supported("test.cc")
        assert chunker.is_supported("test.cxx")
        assert chunker.is_supported("test.c++")
        assert chunker.is_supported("test.h")
        assert chunker.is_supported("test.hpp")
        assert chunker.is_supported("test.hh")
        assert chunker.is_supported("test.hxx")
        assert chunker.is_supported("test.inl")
        assert chunker.is_supported("test.ipp")
        assert chunker.is_supported("test.tpp")
        assert chunker.is_supported("test.cs")
        assert chunker.is_supported("test.rs")
        assert chunker.is_supported("test.glsl")
        assert chunker.is_supported("test.frag")
        assert chunker.is_supported("test.vert")
        assert chunker.is_supported("test.comp")
        assert chunker.is_supported("test.geom")
        assert chunker.is_supported("test.tesc")
        assert chunker.is_supported("test.tese")
        assert not chunker.is_supported("test.txt")

    def test_chunk_python_file(self, chunker, test_data_dir):
        """Test chunking Python file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.py"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find the class and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert "function" in chunk_types or "method" in chunk_types
            assert "class" in chunk_types

    def test_chunk_javascript_file(self, chunker, test_data_dir):
        """Test chunking JavaScript file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.js"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions and class
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert "calculateSum" in chunk_names
            assert "Calculator" in chunk_names

    def test_chunk_typescript_file(self, chunker, test_data_dir):
        """Test chunking TypeScript file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "example.ts"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find interface, class, and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert any(t in chunk_types for t in ["class", "interface", "function"])

    def test_chunk_tsx_file(self, chunker, test_data_dir):
        """Test chunking TSX file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "Component.tsx"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find TypeScript React components
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert any(name in chunk_names for name in ["TypedCounter", "UserList"])

    def test_chunk_go_file(self, chunker, test_data_dir):
        """Test chunking Go file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "calculator.go"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions, methods, types, and interfaces
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert any(
                name in chunk_names
                for name in ["Calculator", "CalculateSum", "NewCalculator"]
            )
            assert len(chunk_names) > 0
            # `or len(chunks) > 0` was already proven true by the assertion
            # at the top of this test, making the whole expression an
            # unconditional pass regardless of what chunk_types actually
            # contains — dropped so this checks what it claims to check.
            assert any(
                t in chunk_types for t in ["function", "method", "type", "interface"]
            ), f"Expected a Go-relevant chunk type, got {chunk_types}"

    def test_chunk_c_file(self, chunker, test_data_dir):
        """Test chunking C file."""
        file_path = test_data_dir / "calculator.c"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-c is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(
            name in chunk_names
            for name in ["calculate_sum", "get_result", "apply_operation"]
        )

    def test_chunk_c_typedef_name(self, chunker, test_data_dir):
        """Test that anonymous-struct/enum typedefs get a name.

        Regression guard: `type_definition`'s name lives on a
        `type_identifier` child (e.g. `typedef struct {...} Calculator;`),
        not a plain `identifier` -- c.py's extract_metadata only checked
        `identifier`, so every anonymous-struct/enum typedef silently
        chunked with name=None. Found via the C++ chunking parity plan's
        live gate verification, unrelated to that plan's declarator-unwrap
        fix (which only covers `function_definition`).
        """
        file_path = test_data_dir / "calculator.c"
        chunks = chunker.chunk_file(str(file_path))

        typedef_names = {
            chunk.name for chunk in chunks if chunk.chunk_type == "type_definition"
        }
        assert typedef_names == {"Calculator", "Operation"}

    def test_chunk_cpp_file(self, chunker, test_data_dir):
        """Test chunking C++ file."""
        file_path = test_data_dir / "Calculator.cpp"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-cpp is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C++ parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(name in chunk_names for name in ["Point", "main"])

    def test_chunk_cpp_header_file(self, chunker, tmp_path):
        """Test chunking a .h header file end-to-end.

        Regression guard: `.h` was added to SUPPORTED_EXTENSIONS /
        EXT_TO_LANGUAGE (Phase 1) but `TreeSitterChunker.LANGUAGE_MAP` --
        a separate suffix -> chunker-factory dict in tree_sitter.py -- was
        not updated alongside it, so `get_chunker(".h")` silently returned
        None and headers produced zero chunks despite is_supported()
        reporting True. is_supported() alone would not catch this; only an
        actual chunk_file() call does.
        """
        header = tmp_path / "widget.h"
        header.write_text(
            "class Widget {\npublic:\n    void draw();\n};\n", encoding="utf-8"
        )
        chunks = chunker.chunk_file(str(header))

        assert len(chunks) > 0, "Header parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "Widget" in chunk_names
        assert "draw" in chunk_names

    def test_chunk_csharp_file(self, chunker, test_data_dir):
        """Test chunking C# file."""
        file_path = test_data_dir / "Calculator.cs"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-c-sharp is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "C# parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert any(name in chunk_names for name in ["Math"])

    def test_chunk_glsl_file(self, chunker, test_data_dir):
        """Test chunking GLSL file."""
        file_path = test_data_dir / "example.glsl"
        chunks = chunker.chunk_file(str(file_path))

        # tree-sitter-glsl is a hard dependency (pyproject.toml), not optional --
        # the parser is always available, so this must produce real chunks.
        assert len(chunks) > 0, "GLSL parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        chunk_types = {chunk.chunk_type for chunk in chunks}

        assert any(name in chunk_names for name in ["Wave", "computeWave", "main"])
        assert any(t in chunk_types for t in ["struct", "function"])

    def test_chunk_rust_file(self, chunker, test_data_dir):
        """Test chunking Rust file."""
        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            file_path = test_data_dir / "calculator.rs"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions, structs, traits, enums, impls, macros
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert any(
                name in chunk_names
                for name in [
                    "Calculator",
                    "calculate_sum",
                    "MathOperations",
                    "Operation",
                    "Point",
                ]
            )
            assert any(
                t in chunk_types
                for t in ["function", "struct", "trait", "enum", "impl", "macro"]
            )
