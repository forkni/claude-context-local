"""
Integration tests for Phase 2: Type Annotation Resolution.

Tests the end-to-end flow of type annotation resolution with indexing
and find_connections.
"""

import os
import shutil
import tempfile

from chunking.multi_language_chunker import MultiLanguageChunker
from graph.call_graph_extractor import PythonCallGraphExtractor
from graph.graph_storage import CodeGraphStorage


class TestTypeAnnotationIntegration:
    """Integration tests for type annotation resolution in the full pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.chunker = MultiLanguageChunker()
        self.extractor = PythonCallGraphExtractor()
        self.graph = CodeGraphStorage("test_project")

    def teardown_method(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_test_file(self, filename: str, content: str) -> str:
        """Create a test file with the given content."""
        filepath = os.path.join(self.test_dir, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def test_chunking_and_call_extraction_with_annotations(self):
        """Test that chunking and call extraction work together with annotations."""
        # Create test file with annotated function
        code = '''
class ExceptionExtractor:
    def extract(self):
        pass

def process_exceptions(extractor: ExceptionExtractor):
    """Process exceptions using the extractor."""
    extractor.extract()
    extractor.validate()
'''
        filepath = self._create_test_file("test_code.py", code)

        # Chunk the file
        chunks = self.chunker.chunk_file(filepath)

        # Find the process_exceptions function chunk
        func_chunk = None
        for chunk in chunks:
            if "process_exceptions" in chunk.name:
                func_chunk = chunk
                break

        assert func_chunk is not None, "Function chunk not found"

        # Extract calls from the function
        chunk_metadata = {
            "chunk_id": func_chunk.chunk_id,
            "parent_class": getattr(func_chunk, "parent_class", None),
        }

        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        # Verify calls are resolved with type annotations
        callee_names = [call.callee_name for call in calls]
        assert "ExceptionExtractor.extract" in callee_names
        assert "ExceptionExtractor.validate" in callee_names

    def test_graph_storage_with_resolved_calls(self):
        """Test that graph storage works with resolved type-annotated calls."""
        # Add nodes to graph
        self.graph.add_node(
            chunk_id="extractors.py:1-10:class:ExceptionExtractor",
            name="ExceptionExtractor",
            chunk_type="class",
            file_path="extractors.py",
        )
        self.graph.add_node(
            chunk_id="extractors.py:2-5:method:ExceptionExtractor.extract",
            name="ExceptionExtractor.extract",
            chunk_type="method",
            file_path="extractors.py",
        )
        self.graph.add_node(
            chunk_id="processor.py:1-5:function:process_exceptions",
            name="process_exceptions",
            chunk_type="function",
            file_path="processor.py",
        )

        # Add call edge with resolved type annotation
        self.graph.add_call_edge(
            caller_id="processor.py:1-5:function:process_exceptions",
            callee_name="ExceptionExtractor.extract",  # Resolved via type annotation
            line_number=3,
            is_resolved=True,
        )

        # Query callers
        callers = self.graph.get_callers("ExceptionExtractor.extract")

        assert len(callers) >= 1
        assert "processor.py:1-5:function:process_exceptions" in callers

    def test_no_false_positives_with_annotated_callers(self):
        """Test that type annotations eliminate false positives."""
        # Create multiple extractors with same method names
        code = '''
class ExceptionExtractor:
    def extract(self):
        return "exception"

class DataExtractor:
    def extract(self):
        return "data"

class LogExtractor:
    def extract(self):
        return "log"

def process_exceptions(extractor: ExceptionExtractor):
    """Should only call ExceptionExtractor.extract"""
    return extractor.extract()

def process_data(extractor: DataExtractor):
    """Should only call DataExtractor.extract"""
    return extractor.extract()

def process_logs(extractor: LogExtractor):
    """Should only call LogExtractor.extract"""
    return extractor.extract()
'''
        filepath = self._create_test_file("multi_extractor.py", code)

        chunks = self.chunker.chunk_file(filepath)

        # Extract calls from each processing function
        resolved_calls = {}
        for chunk in chunks:
            if chunk.chunk_type == "function" and "process_" in chunk.name:
                chunk_metadata = {"chunk_id": chunk.chunk_id}
                calls = self.extractor.extract_calls(chunk.content, chunk_metadata)
                resolved_calls[chunk.name] = [c.callee_name for c in calls]

        # Verify each function calls the correct extractor
        assert "ExceptionExtractor.extract" in resolved_calls.get(
            "process_exceptions", []
        )
        assert "DataExtractor.extract" in resolved_calls.get("process_data", [])
        assert "LogExtractor.extract" in resolved_calls.get("process_logs", [])

        # Verify no cross-contamination
        assert "DataExtractor.extract" not in resolved_calls.get(
            "process_exceptions", []
        )
        assert "ExceptionExtractor.extract" not in resolved_calls.get(
            "process_data", []
        )

    def test_backward_compatibility_with_unannotated_code(self):
        """Test that unannotated code still works (falls back to bare names)."""
        code = '''
def process(extractor):
    """No type annotation - should fall back to bare method name."""
    extractor.extract()
'''
        filepath = self._create_test_file("unannotated.py", code)

        chunks = self.chunker.chunk_file(filepath)

        func_chunk = [c for c in chunks if c.chunk_type == "function"][0]
        chunk_metadata = {"chunk_id": func_chunk.chunk_id}

        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        assert len(calls) == 1
        # Should fall back to bare name
        assert calls[0].callee_name == "extract"

    def test_mixed_resolution_self_and_annotation(self):
        """Test that self calls and type-annotated calls both resolve correctly."""
        code = '''
class Processor:
    def process(self, extractor: ExceptionExtractor):
        """Uses both self.helper() and extractor.extract()"""
        self.helper()
        extractor.extract()

    def helper(self):
        pass
'''
        filepath = self._create_test_file("mixed.py", code)

        chunks = self.chunker.chunk_file(filepath)

        # Find the process method
        process_chunk = None
        for chunk in chunks:
            if "process" in chunk.name and chunk.chunk_type == "method":
                process_chunk = chunk
                break

        assert process_chunk is not None

        chunk_metadata = {
            "chunk_id": process_chunk.chunk_id,
            "parent_class": "Processor",
        }

        calls = self.extractor.extract_calls(process_chunk.content, chunk_metadata)

        callee_names = {call.callee_name for call in calls}

        # Both should be resolved
        assert "Processor.helper" in callee_names
        assert "ExceptionExtractor.extract" in callee_names

    def test_optional_type_annotation_in_pipeline(self):
        """Test Optional[X] annotation works in full pipeline."""
        code = '''
from typing import Optional

class ExceptionExtractor:
    def extract(self):
        pass

def maybe_process(extractor: Optional[ExceptionExtractor]):
    """Optional parameter should still resolve to ExceptionExtractor."""
    if extractor:
        extractor.extract()
'''
        filepath = self._create_test_file("optional_test.py", code)

        chunks = self.chunker.chunk_file(filepath)

        func_chunk = [
            c
            for c in chunks
            if c.chunk_type == "function" and "maybe_process" in c.name
        ][0]
        chunk_metadata = {"chunk_id": func_chunk.chunk_id}

        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"

    def test_forward_reference_annotation_in_pipeline(self):
        """Test forward reference annotations work in full pipeline."""
        code = '''
def process(extractor: "ExceptionExtractor"):
    """Forward reference should still resolve."""
    extractor.extract()

class ExceptionExtractor:
    def extract(self):
        pass
'''
        filepath = self._create_test_file("forward_ref.py", code)

        chunks = self.chunker.chunk_file(filepath)

        func_chunk = [c for c in chunks if c.chunk_type == "function"][0]
        chunk_metadata = {"chunk_id": func_chunk.chunk_id}

        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        assert len(calls) == 1
        assert calls[0].callee_name == "ExceptionExtractor.extract"


class TestFindConnectionsWithTypeAnnotations:
    """Integration tests for find_connections with type annotation resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.graph = CodeGraphStorage("test_project")
        self.extractor = PythonCallGraphExtractor()

    def test_find_callers_with_resolved_edges(self):
        """Test that find_callers returns only resolved callers."""
        # Add target node
        self.graph.add_node(
            chunk_id="extractors.py:10-20:method:ExceptionExtractor.extract",
            name="ExceptionExtractor.extract",
            chunk_type="method",
            file_path="extractors.py",
        )

        # Add correct caller (resolved via type annotation)
        self.graph.add_node(
            chunk_id="test_exception.py:5-10:function:test_extract",
            name="test_extract",
            chunk_type="function",
            file_path="test_exception.py",
        )
        self.graph.add_call_edge(
            caller_id="test_exception.py:5-10:function:test_extract",
            callee_name="ExceptionExtractor.extract",
            is_resolved=True,
        )

        # Add different caller (different class)
        self.graph.add_node(
            chunk_id="test_data.py:5-10:function:test_data_extract",
            name="test_data_extract",
            chunk_type="function",
            file_path="test_data.py",
        )
        self.graph.add_call_edge(
            caller_id="test_data.py:5-10:function:test_data_extract",
            callee_name="DataExtractor.extract",  # Different class!
            is_resolved=True,
        )

        # Query callers of ExceptionExtractor.extract
        callers = self.graph.get_callers("ExceptionExtractor.extract")

        # Should only return the correct caller
        assert "test_exception.py:5-10:function:test_extract" in callers
        assert "test_data.py:5-10:function:test_data_extract" not in callers

    def test_end_to_end_type_resolution_accuracy(self):
        """Test end-to-end accuracy of type resolution."""
        # This tests that the full pipeline produces accurate call graphs
        # Full class structure for context (method_code extracted below):
        # class Handler:
        #     def handle(self, item): pass
        # class Processor:
        #     def process(self, handler: Handler): handler.handle("data")

        chunk_metadata = {
            "chunk_id": "processor.py:5-7:method:Processor.process",
            "parent_class": "Processor",
        }

        # Extract the method body only
        method_code = """
def process(self, handler: Handler):
    handler.handle("data")
"""

        calls = self.extractor.extract_calls(method_code, chunk_metadata)

        # Should resolve handler.handle to Handler.handle
        handler_calls = [c for c in calls if "handle" in c.callee_name]
        assert len(handler_calls) == 1
        assert handler_calls[0].callee_name == "Handler.handle"
