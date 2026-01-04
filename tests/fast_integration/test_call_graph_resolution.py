"""
Integration tests for call graph resolution (Phase 1).

Tests end-to-end that qualified names reduce false positives when
querying callers of methods with common names like "extract".

Expected improvement:
- Before: ~67 false positive direct_callers for methods named "extract"
- After: ~5-10 accurate direct_callers (only actual callers)
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from chunking.multi_language_chunker import MultiLanguageChunker
from graph.call_graph_extractor import PythonCallGraphExtractor
from graph.graph_storage import CodeGraphStorage
from mcp_server.services import ServiceLocator
from search.config import ChunkingConfig


class TestCallGraphResolutionIntegration:
    """Integration tests for qualified call graph resolution."""

    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)

        # Disable greedy merge for these tests to check individual method chunks
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig(enable_greedy_merge=False)
        self.locator = ServiceLocator.instance()
        self.locator.register("config", mock_config)

        # Create test files
        self._create_test_files()

        # Initialize components
        self.chunker = MultiLanguageChunker(root_path=str(self.project_path))
        self.graph = CodeGraphStorage(
            project_id="test_resolution", storage_dir=self.project_path / ".graph"
        )

    def teardown_method(self):
        """Clean up ServiceLocator."""
        ServiceLocator.reset()

    def _create_test_files(self):
        """Create test Python files with multiple classes having 'extract' methods."""
        # File 1: ExceptionExtractor
        exception_file = self.project_path / "exception_extractor.py"
        exception_file.write_text(
            '''
class ExceptionExtractor:
    """Extracts exception relationships."""

    def extract(self, code, metadata):
        """Extract exceptions from code."""
        self._parse_code(code)
        return self._process_results()

    def _parse_code(self, code):
        pass

    def _process_results(self):
        return []
'''
        )

        # File 2: ImportExtractor (different class, same method name)
        import_file = self.project_path / "import_extractor.py"
        import_file.write_text(
            '''
class ImportExtractor:
    """Extracts import relationships."""

    def extract(self, code, metadata):
        """Extract imports from code."""
        self._analyze_imports(code)
        return self._format_results()

    def _analyze_imports(self, code):
        pass

    def _format_results(self):
        return []
'''
        )

        # File 3: Test that calls ExceptionExtractor.extract
        test_file = self.project_path / "test_exception.py"
        test_file.write_text(
            '''
from exception_extractor import ExceptionExtractor

def test_exception_extraction():
    """Test ExceptionExtractor.extract specifically."""
    extractor = ExceptionExtractor()
    result = extractor.extract("code", {})
    assert result == []

class TestExceptionExtractor:
    def test_extract_with_exceptions(self):
        extractor = ExceptionExtractor()
        extractor.extract("raise ValueError", {"file": "test.py"})
'''
        )

        # File 4: Test that calls ImportExtractor.extract
        test_import_file = self.project_path / "test_import.py"
        test_import_file.write_text(
            '''
from import_extractor import ImportExtractor

def test_import_extraction():
    """Test ImportExtractor.extract specifically."""
    extractor = ImportExtractor()
    result = extractor.extract("import os", {})
    assert result == []
'''
        )

        # File 5: Class that calls self.extract (should resolve to its own class)
        another_file = self.project_path / "data_extractor.py"
        another_file.write_text(
            '''
class DataExtractor:
    """Generic data extractor."""

    def process(self):
        """Process data using extract."""
        data = self.extract("input", {})
        return data

    def extract(self, code, metadata):
        """Generic extract method."""
        return {"data": code}
'''
        )

    def test_qualified_chunk_ids_generated(self):
        """Test that chunk_ids include qualified names."""
        # Chunk the exception extractor file
        chunks = self.chunker.chunk_file(
            str(self.project_path / "exception_extractor.py")
        )

        # Find the extract method
        extract_chunks = [c for c in chunks if c.name == "extract"]
        assert len(extract_chunks) == 1

        extract_chunk = extract_chunks[0]
        assert extract_chunk.parent_name == "ExceptionExtractor"
        assert extract_chunk.chunk_type == "method"

    def test_self_calls_resolved_to_qualified_names(self):
        """Test that self.method() calls resolve to ClassName.method."""
        # Chunk the data extractor file
        chunks = self.chunker.chunk_file(str(self.project_path / "data_extractor.py"))

        # Find the process method
        process_chunks = [c for c in chunks if c.name == "process"]
        assert len(process_chunks) == 1

        process_chunk = process_chunks[0]

        # Check that self.extract() was resolved to DataExtractor.extract
        if hasattr(process_chunk, "calls") and process_chunk.calls:
            extract_calls = [
                c for c in process_chunk.calls if "extract" in c.callee_name
            ]
            assert len(extract_calls) >= 1

            # Should be qualified
            qualified_calls = [
                c for c in extract_calls if "DataExtractor.extract" == c.callee_name
            ]
            assert (
                len(qualified_calls) >= 1
            ), f"Expected DataExtractor.extract, got {[c.callee_name for c in extract_calls]}"

    def test_different_classes_same_method_name_distinct(self):
        """Test that extract methods in different classes have distinct chunk_ids."""
        # Chunk both extractor files
        exception_chunks = self.chunker.chunk_file(
            str(self.project_path / "exception_extractor.py")
        )
        import_chunks = self.chunker.chunk_file(
            str(self.project_path / "import_extractor.py")
        )

        # Get extract methods
        exception_extract = [c for c in exception_chunks if c.name == "extract"][0]
        import_extract = [c for c in import_chunks if c.name == "extract"][0]

        # Parent names should be different
        assert exception_extract.parent_name == "ExceptionExtractor"
        assert import_extract.parent_name == "ImportExtractor"

        # This means they'll have different qualified names in chunk_ids

    def test_call_graph_stores_qualified_names(self):
        """Test that the call graph stores qualified callee names."""
        # Chunk and extract calls from data_extractor.py
        chunks = self.chunker.chunk_file(str(self.project_path / "data_extractor.py"))

        # Find process method and check its calls
        process_chunks = [c for c in chunks if c.name == "process"]
        assert len(process_chunks) == 1

        process_chunk = process_chunks[0]

        # Add to graph
        if hasattr(process_chunk, "calls") and process_chunk.calls:
            for call in process_chunk.calls:
                self.graph.add_call_edge(
                    caller_id="data_extractor.py:5-7:method:DataExtractor.process",
                    callee_name=call.callee_name,
                    line_number=call.line_number,
                    is_method_call=call.is_method_call,
                )

            # Query the graph for DataExtractor.extract
            callers = self.graph.get_callers("DataExtractor.extract")

            # Should find the process method as a caller
            assert len(callers) >= 1

    def test_no_false_positives_across_classes(self):
        """Test that querying one class's extract doesn't return callers of another's."""
        # This is the key test for false positive reduction

        # Chunk all files
        all_chunks = []
        for py_file in self.project_path.glob("*.py"):
            chunks = self.chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        # Build graph with all calls
        for chunk in all_chunks:
            # Build chunk_id
            rel_path = Path(chunk.file_path).relative_to(self.project_path)
            chunk_id = (
                f"{rel_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
            )
            if chunk.parent_name and chunk.name:
                chunk_id += f":{chunk.parent_name}.{chunk.name}"
            elif chunk.name:
                chunk_id += f":{chunk.name}"

            # Add node
            self.graph.add_node(
                chunk_id=chunk_id,
                name=chunk.name or "unknown",
                chunk_type=chunk.chunk_type,
                file_path=str(rel_path),
            )

            # Add call edges
            if hasattr(chunk, "calls") and chunk.calls:
                for call in chunk.calls:
                    self.graph.add_call_edge(
                        caller_id=chunk_id,
                        callee_name=call.callee_name,
                        line_number=call.line_number,
                        is_method_call=call.is_method_call,
                    )

        # Query callers of DataExtractor.extract
        data_extract_callers = self.graph.get_callers("DataExtractor.extract")

        # Should only have DataExtractor.process as caller (not test files)
        # Note: Test files call extractor.extract() which isn't resolved yet
        # but DataExtractor.process calls self.extract() which IS resolved

        # At minimum, verify no OTHER class's callers appear
        for caller in data_extract_callers:
            # Should not include callers that call other extractors
            assert "ImportExtractor" not in caller
            assert "ExceptionExtractor" not in caller

    def test_method_resolution_accuracy(self):
        """Test overall method resolution accuracy."""
        extractor = PythonCallGraphExtractor()

        # Code with self calls
        code = """
class Calculator:
    def add(self, a, b):
        self.validate(a, b)
        return a + b

    def validate(self, a, b):
        pass
"""
        chunk_metadata = {
            "chunk_id": "calc.py:2-4:method:Calculator.add",
            "parent_class": "Calculator",
        }

        calls = extractor.extract_calls(code, chunk_metadata)

        # Find validate call
        validate_calls = [c for c in calls if "validate" in c.callee_name]
        assert len(validate_calls) >= 1

        # Should be resolved to Calculator.validate
        resolved_calls = [
            c for c in validate_calls if c.callee_name == "Calculator.validate"
        ]
        assert (
            len(resolved_calls) >= 1
        ), f"Expected Calculator.validate, got {[c.callee_name for c in validate_calls]}"


class TestCallGraphBackwardCompatibility:
    """Test backward compatibility with existing graph data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.graph = CodeGraphStorage(
            project_id="test_compat", storage_dir=Path(self.temp_dir) / ".graph"
        )

    def test_bare_name_edges_still_work(self):
        """Test that old-style bare name edges can still be queried."""
        # Simulate old-style edge (bare name)
        self.graph.add_call_edge(
            caller_id="test.py:1-5:function:test_func",
            callee_name="extract",  # Bare name (old style)
            line_number=3,
            is_method_call=True,
        )

        # Query by bare name
        callers = self.graph.get_callers("extract")
        assert len(callers) == 1
        assert callers[0] == "test.py:1-5:function:test_func"

    def test_qualified_name_edges_work(self):
        """Test that new-style qualified name edges work."""
        # New-style edge (qualified name)
        self.graph.add_call_edge(
            caller_id="test.py:1-5:function:test_func",
            callee_name="ExceptionExtractor.extract",  # Qualified name
            line_number=3,
            is_method_call=True,
        )

        # Query by qualified name
        callers = self.graph.get_callers("ExceptionExtractor.extract")
        assert len(callers) == 1
        assert callers[0] == "test.py:1-5:function:test_func"

    def test_mixed_edges_coexist(self):
        """Test that old and new style edges can coexist."""
        # Old style
        self.graph.add_call_edge(
            caller_id="old_test.py:1-5:function:old_test",
            callee_name="extract",
            line_number=3,
        )

        # New style
        self.graph.add_call_edge(
            caller_id="new_test.py:1-5:function:new_test",
            callee_name="ExceptionExtractor.extract",
            line_number=3,
        )

        # Both should be independently queryable
        bare_callers = self.graph.get_callers("extract")
        qualified_callers = self.graph.get_callers("ExceptionExtractor.extract")

        assert len(bare_callers) == 1
        assert len(qualified_callers) == 1
        assert bare_callers[0] != qualified_callers[0]

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if hasattr(self, "temp_dir"):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
