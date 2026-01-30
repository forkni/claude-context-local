"""Unit tests for structural header context injection in embeddings (v0.9.0)."""

import pytest

from chunking.python_ast_chunker import CodeChunk
from embeddings.embedder import CodeEmbedder


class TestStructuralHeaderContextInjection:
    """Test suite for structural header feature in create_embedding_content()."""

    @pytest.fixture
    def embedder(self):
        """Create CodeEmbedder instance with minimal config."""
        return CodeEmbedder(model_name="google/embeddinggemma-300m")

    def test_structural_header_method_chunk(self, embedder):
        """Verify structural header for method chunks includes parent class."""
        chunk = CodeChunk(
            content="def search(self, query: str) -> list:\n    return []",
            chunk_type="method",
            start_line=10,
            end_line=11,
            file_path="/project/search/searcher.py",
            relative_path="search/searcher.py",
            folder_structure=["search"],
            name="search",
            parent_name="Searcher",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Should start with structural header
        assert result.startswith("# search/searcher.py | method Searcher.search")
        # Should still include the actual code
        assert "def search(self, query: str)" in result

    def test_structural_header_function_chunk(self, embedder):
        """Verify structural header for function chunks (no parent class)."""
        chunk = CodeChunk(
            content="def validate_input(data):\n    pass",
            chunk_type="function",
            start_line=5,
            end_line=6,
            file_path="/project/utils/helpers.py",
            relative_path="utils/helpers.py",
            folder_structure=["utils"],
            name="validate_input",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        assert result.startswith("# utils/helpers.py | function validate_input")
        assert "def validate_input(data):" in result

    def test_structural_header_class_chunk(self, embedder):
        """Verify structural header for class chunks."""
        chunk = CodeChunk(
            content="class UserModel:\n    pass",
            chunk_type="class",
            start_line=1,
            end_line=2,
            file_path="/project/models/user.py",
            relative_path="models/user.py",
            folder_structure=["models"],
            name="UserModel",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        assert result.startswith("# models/user.py | class UserModel")
        assert "class UserModel:" in result

    def test_structural_header_disabled(self, embedder, monkeypatch):
        """Verify structural header is skipped when disabled via config."""
        # Mock config to disable structural header
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.embedding.enable_import_context = False
        mock_config.embedding.enable_class_context = False
        mock_config.embedding.max_import_lines = 10
        mock_config.embedding.max_class_signature_lines = 5
        mock_config.embedding.enable_structural_header = False  # KEY: disabled

        def mock_get_config():
            return mock_config

        monkeypatch.setattr(
            "embeddings.embedder._get_config_via_service_locator", mock_get_config
        )

        chunk = CodeChunk(
            content="def test():\n    pass",
            chunk_type="function",
            start_line=1,
            end_line=2,
            file_path="/project/test.py",
            relative_path="test.py",
            folder_structure=[],
            name="test",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Should NOT start with structural header
        assert not result.startswith("# test.py")
        # Should directly start with the code
        assert result.strip().startswith("def test():")

    def test_structural_header_missing_fields(self, embedder):
        """Verify graceful fallback when chunk lacks relative_path or name."""
        # Chunk with no relative_path or name
        chunk = CodeChunk(
            content="x = 42",
            chunk_type="module_level",
            start_line=1,
            end_line=1,
            file_path="/project/config.py",
            relative_path="",  # Empty
            folder_structure=[],
            name=None,  # No name
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Should not crash; should include chunk type if available
        assert "# module_level" in result or result.strip().startswith("x = 42")

    def test_structural_header_partial_fields(self, embedder):
        """Verify header with only some fields available."""
        # Chunk with path but no name
        chunk = CodeChunk(
            content="CONST = 123",
            chunk_type="module_level",
            start_line=1,
            end_line=1,
            file_path="/project/constants.py",
            relative_path="constants.py",
            folder_structure=[],
            name=None,
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Should have path + type but no qualified name
        assert "# constants.py | module_level" in result

    def test_structural_header_token_budget_respected(self, embedder):
        """Verify structural header respects the max_chars=6000 budget."""
        # Create a very large chunk
        large_code = "def big_function():\n" + ("    x = 1\n" * 2000)
        chunk = CodeChunk(
            content=large_code,
            chunk_type="function",
            start_line=1,
            end_line=2001,
            file_path="/project/large.py",
            relative_path="large.py",
            folder_structure=[],
            name="big_function",
            language="python",
        )

        result = embedder.create_embedding_content(chunk, max_chars=6000)

        # Should have structural header
        assert result.startswith("# large.py | function big_function")
        # Total length should not exceed max_chars significantly
        # (allow small buffer for line separators)
        assert len(result) <= 6100

    def test_structural_header_order(self, embedder, monkeypatch):
        """Verify structural header appears BEFORE import/class context."""
        # Mock config to enable all context features
        from unittest.mock import MagicMock

        mock_config = MagicMock()
        mock_config.embedding.enable_import_context = True
        mock_config.embedding.enable_class_context = True
        mock_config.embedding.max_import_lines = 10
        mock_config.embedding.max_class_signature_lines = 5
        mock_config.embedding.enable_structural_header = True

        def mock_get_config():
            return mock_config

        monkeypatch.setattr(
            "embeddings.embedder._get_config_via_service_locator", mock_get_config
        )

        chunk = CodeChunk(
            content="def process(self):\n    pass",
            chunk_type="method",
            start_line=10,
            end_line=11,
            file_path="/project/service/handler.py",
            relative_path="service/handler.py",
            folder_structure=["service"],
            name="process",
            parent_name="Handler",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Find positions of each context block
        header_pos = result.find("# service/handler.py")
        imports_pos = result.find("# Imports:")
        class_pos = result.find("# Parent class:")

        # Structural header should come first
        assert header_pos == 0, "Structural header should be at position 0"

        # Order should be: structural header -> imports -> class context -> code
        # (imports might not exist if file has no imports, but if present, should be after header)
        if imports_pos != -1:
            assert header_pos < imports_pos
        if class_pos != -1:
            assert header_pos < class_pos

    def test_structural_header_with_docstring(self, embedder):
        """Verify structural header works with docstring context."""
        chunk = CodeChunk(
            content='def api_call(self):\n    """Make API request."""\n    return {}',
            chunk_type="method",
            start_line=5,
            end_line=7,
            file_path="/project/client/api.py",
            relative_path="client/api.py",
            folder_structure=["client"],
            name="api_call",
            parent_name="APIClient",
            docstring="Make API request.",
            language="python",
        )

        result = embedder.create_embedding_content(chunk)

        # Should have structural header
        assert result.startswith("# client/api.py | method APIClient.api_call")
        # Should include docstring
        assert '"""Make API request."""' in result
        # Should include code
        assert "def api_call(self):" in result

    def test_structural_header_namespace_collision(self, embedder):
        """Verify header disambiguates methods with same name in different classes."""
        chunk1 = CodeChunk(
            content="def run(self):\n    pass",
            chunk_type="method",
            start_line=5,
            end_line=6,
            file_path="/project/engine/simulation.py",
            relative_path="engine/simulation.py",
            folder_structure=["engine"],
            name="run",
            parent_name="SimulationEngine",
            language="python",
        )

        chunk2 = CodeChunk(
            content="def run(self):\n    pass",
            chunk_type="method",
            start_line=10,
            end_line=11,
            file_path="/project/tests/runner.py",
            relative_path="tests/runner.py",
            folder_structure=["tests"],
            name="run",
            parent_name="TestRunner",
            language="python",
        )

        result1 = embedder.create_embedding_content(chunk1)
        result2 = embedder.create_embedding_content(chunk2)

        # Headers should be distinct despite same method name
        assert "# engine/simulation.py | method SimulationEngine.run" in result1
        assert "# tests/runner.py | method TestRunner.run" in result2
        # Actual code is identical, but embedding vectors will differ due to headers
        assert "def run(self):" in result1
        assert "def run(self):" in result2
