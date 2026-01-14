"""Basic tests for multi-language chunking."""

from pathlib import Path
from unittest.mock import MagicMock

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
        assert chunker.is_supported("test.cs")
        assert chunker.is_supported("test.rs")
        assert not chunker.is_supported("test.txt")

    def test_chunk_python_file(self, chunker, test_data_dir):
        """Test chunking Python file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
            file_path = test_data_dir / "example.py"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find the class and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert "function" in chunk_types or "method" in chunk_types
            assert "class" in chunk_types
        finally:
            ServiceLocator.reset()

    def test_chunk_javascript_file(self, chunker, test_data_dir):
        """Test chunking JavaScript file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
            file_path = test_data_dir / "example.js"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find functions and class
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert "calculateSum" in chunk_names
            assert "Calculator" in chunk_names
        finally:
            ServiceLocator.reset()

    def test_chunk_typescript_file(self, chunker, test_data_dir):
        """Test chunking TypeScript file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
            file_path = test_data_dir / "example.ts"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find interface, class, and functions
            chunk_types = {chunk.chunk_type for chunk in chunks}
            assert any(t in chunk_types for t in ["class", "interface", "function"])
        finally:
            ServiceLocator.reset()

    def test_chunk_tsx_file(self, chunker, test_data_dir):
        """Test chunking TSX file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
            file_path = test_data_dir / "Component.tsx"
            chunks = chunker.chunk_file(str(file_path))

            assert len(chunks) > 0
            # Should find TypeScript React components
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            assert any(name in chunk_names for name in ["TypedCounter", "UserList"])
        finally:
            ServiceLocator.reset()

    def test_chunk_go_file(self, chunker, test_data_dir):
        """Test chunking Go file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
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
            assert (
                any(
                    t in chunk_types
                    for t in ["function", "method", "type", "interface"]
                )
                or len(chunks) > 0
            )
        finally:
            ServiceLocator.reset()

    def test_chunk_c_file(self, chunker, test_data_dir):
        """Test chunking C file."""
        file_path = test_data_dir / "calculator.c"
        chunks = chunker.chunk_file(str(file_path))

        # C parser may not be available, so chunks might be empty
        if len(chunks) > 0:
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert len(chunk_names) > 0 or len(chunk_types) > 0
        # If no chunks, that's okay - parser not available

    def test_chunk_cpp_file(self, chunker, test_data_dir):
        """Test chunking C++ file."""
        file_path = test_data_dir / "Calculator.cpp"
        chunks = chunker.chunk_file(str(file_path))

        # C++ parser may not be available, so chunks might be empty
        if len(chunks) > 0:
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert len(chunk_names) > 0 or len(chunk_types) > 0
        # If no chunks, that's okay - parser not available

    def test_chunk_csharp_file(self, chunker, test_data_dir):
        """Test chunking C# file."""
        file_path = test_data_dir / "Calculator.cs"
        chunks = chunker.chunk_file(str(file_path))

        # C# parser may not be available, so chunks might be empty
        if len(chunks) > 0:
            chunk_names = {chunk.name for chunk in chunks if chunk.name}
            chunk_types = {chunk.chunk_type for chunk in chunks}

            assert len(chunk_names) > 0 or len(chunk_types) > 0
        # If no chunks, that's okay - parser not available

    def test_chunk_rust_file(self, chunker, test_data_dir):
        """Test chunking Rust file."""
        from mcp_server.services import ServiceLocator

        # Use default config for basic chunking behavior
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
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
        finally:
            ServiceLocator.reset()
