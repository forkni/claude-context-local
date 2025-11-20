"""
Integration tests for Phase 3: Assignment Tracking.

Tests the full pipeline with assignment-based type inference.
"""

import shutil
import tempfile
from pathlib import Path

from chunking.multi_language_chunker import MultiLanguageChunker
from graph.call_graph_extractor import PythonCallGraphExtractor
from graph.graph_storage import CodeGraphStorage


class TestAssignmentTrackingIntegration:
    """Integration tests for assignment tracking in full pipeline."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.chunker = MultiLanguageChunker()
        self.extractor = PythonCallGraphExtractor()
        self.graph = CodeGraphStorage("test_project")

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_chunking_and_call_extraction_with_assignments(self):
        """Test full pipeline with assignment-based resolution."""
        code = """
class ErrorHandler:
    def handle(self):
        return "handled"

def process_errors():
    handler = ErrorHandler()
    handler.handle()
"""
        # Write to file
        test_file = Path(self.test_dir) / "test_module.py"
        test_file.write_text(code)

        # Chunk the file
        chunks = self.chunker.chunk_file(str(test_file))

        # Find the process_errors function chunk
        func_chunk = None
        for chunk in chunks:
            if "process_errors" in chunk.name:
                func_chunk = chunk
                break

        assert func_chunk is not None, "process_errors chunk not found"

        # Extract calls from the function
        chunk_metadata = {
            "chunk_id": func_chunk.chunk_id,
            "parent_class": None,  # standalone function
        }
        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        # Verify resolution
        callee_names = {c.callee_name for c in calls}
        assert "ErrorHandler.handle" in callee_names

    def test_graph_storage_with_assignment_resolved_calls(self):
        """Test graph stores correctly resolved assignment-based calls."""
        # Add target node
        target_id = "module.py:1-10:method:ErrorHandler.handle"
        self.graph.add_node(
            chunk_id=target_id,
            name="ErrorHandler.handle",
            chunk_type="method",
            file_path="module.py",
        )

        # Add caller node
        caller_id = "module.py:20-30:function:process_errors"
        self.graph.add_node(
            chunk_id=caller_id,
            name="process_errors",
            chunk_type="function",
            file_path="module.py",
        )

        # Add call edge with qualified name (as Phase 3 would produce)
        self.graph.add_call_edge(
            caller_id,
            "ErrorHandler.handle",  # Qualified name from assignment tracking
            line_number=25,
        )

        # Query callers
        callers = self.graph.get_callers("ErrorHandler.handle")
        assert len(callers) >= 1
        assert caller_id in callers

    def test_no_false_positives_multiple_classes(self):
        """Test assignments don't create false positives."""
        code = """
class DataHandler:
    def handle(self):
        return "data"

class ErrorHandler:
    def handle(self):
        return "error"

def process_data():
    handler = DataHandler()
    return handler.handle()

def process_errors():
    handler = ErrorHandler()
    return handler.handle()
"""
        # Write to file
        test_file = Path(self.test_dir) / "handlers.py"
        test_file.write_text(code)

        # Chunk the file
        chunks = self.chunker.chunk_file(str(test_file))

        # Find function chunks
        data_func = None
        error_func = None
        for chunk in chunks:
            if "process_data" in chunk.name:
                data_func = chunk
            elif "process_errors" in chunk.name:
                error_func = chunk

        assert data_func is not None
        assert error_func is not None

        # Extract calls from process_data
        data_metadata = {
            "chunk_id": data_func.chunk_id,
            "parent_class": None,  # standalone function
        }
        data_calls = self.extractor.extract_calls(data_func.content, data_metadata)
        data_callee_names = {c.callee_name for c in data_calls}

        # Extract calls from process_errors
        error_metadata = {
            "chunk_id": error_func.chunk_id,
            "parent_class": None,  # standalone function
        }
        error_calls = self.extractor.extract_calls(error_func.content, error_metadata)
        error_callee_names = {c.callee_name for c in error_calls}

        # Verify no false positives - each function calls the correct class
        assert "DataHandler.handle" in data_callee_names
        assert "ErrorHandler.handle" not in data_callee_names

        assert "ErrorHandler.handle" in error_callee_names
        assert "DataHandler.handle" not in error_callee_names


class TestBackwardCompatibility:
    """Test backward compatibility with existing functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_unannotated_unassigned_falls_back(self):
        """Test code without annotations or assignments still works."""
        code = """
def process(obj):
    obj.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should fall back to bare name
        handle_calls = [c for c in calls if "handle" in c.callee_name]
        assert len(handle_calls) == 1
        assert handle_calls[0].callee_name == "handle"

    def test_existing_phase1_still_works(self):
        """Test self/super calls still resolve correctly."""
        code = """
class MyClass(BaseClass):
    def method(self):
        self.helper()
        super().base_method()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-5:method:MyClass.method",
            "parent_class": "MyClass",
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}
        assert "MyClass.helper" in callee_names
        assert "BaseClass.base_method" in callee_names

    def test_existing_phase2_still_works(self):
        """Test parameter annotations still resolve correctly."""
        code = """
def process(handler: ErrorHandler):
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        handle_calls = [c for c in calls if c.callee_name.endswith(".handle")]
        assert len(handle_calls) == 1
        assert handle_calls[0].callee_name == "ErrorHandler.handle"


class TestRealWorldPatterns:
    """Test real-world code patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_dependency_injection_pattern(self):
        """Test DI pattern with constructor assignments."""
        code = """
class Service:
    def __init__(self):
        self.repo = UserRepository()
        self.cache = RedisCache()

    def get_user(self, id):
        cached = self.cache.get(id)
        if cached:
            return cached
        user = self.repo.find(id)
        self.cache.set(id, user)
        return user
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-13:class:Service",
            "parent_class": "Service",
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Constructor assignments resolve self.attr.method() calls
        assert "RedisCache.get" in callee_names
        assert "UserRepository.find" in callee_names
        assert "RedisCache.set" in callee_names

    def test_factory_pattern_partial_resolution(self):
        """Test factory pattern - constructor resolves, factory result doesn't."""
        code = """
def process():
    factory = HandlerFactory()
    handler = factory.create()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # factory = HandlerFactory() resolves
        assert "HandlerFactory" in callee_names

        # factory.create() resolves using HandlerFactory as type
        assert "HandlerFactory.create" in callee_names

        # handler = factory.create() assigns "create" as type (method name)
        # So handler.handle() resolves to create.handle
        assert "create.handle" in callee_names

    def test_context_manager_pattern(self):
        """Test context manager pattern resolution."""
        code = """
def process_file():
    with DatabaseConnection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process_file"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # conn resolves to DatabaseConnection
        assert "DatabaseConnection.cursor" in callee_names

        # cursor = conn.cursor() assigns "cursor" as type (method name)
        # So cursor.execute() resolves to cursor.execute
        assert "cursor.execute" in callee_names


class TestAllPhasesCombined:
    """Test all three phases working together."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.chunker = MultiLanguageChunker()
        self.extractor = PythonCallGraphExtractor()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_phases_in_single_file(self):
        """Test Phase 1, 2, and 3 all work together in one file."""
        code = """
class BaseProcessor:
    def base_process(self):
        pass

class Processor(BaseProcessor):
    def __init__(self):
        self.handler = ErrorHandler()

    def process(self, validator: Validator):
        # Phase 1: self call
        self.helper()

        # Phase 1: super call
        super().base_process()

        # Phase 2: type annotation
        validator.validate()

        # Phase 3: constructor assignment
        formatter = DataFormatter()
        formatter.format()

        # Phase 3: self.attr assignment
        self.handler.handle()

    def helper(self):
        pass
"""
        # Write to file
        test_file = Path(self.test_dir) / "processor.py"
        test_file.write_text(code)

        # Chunk the file
        chunks = self.chunker.chunk_file(str(test_file))

        # Find the process method chunk - check for partial match
        process_chunk = None
        for chunk in chunks:
            if "process" in chunk.name and "Processor" in chunk.name:
                process_chunk = chunk
                break

        # If not found with qualified name, search by function name
        if process_chunk is None:
            for chunk in chunks:
                if chunk.name == "process" and chunk.chunk_type == "method":
                    process_chunk = chunk
                    break

        assert (
            process_chunk is not None
        ), f"process method chunk not found. Available chunks: {[c.name for c in chunks]}"

        # Extract calls
        chunk_metadata = {
            "chunk_id": process_chunk.chunk_id,
            "parent_class": "Processor",
        }
        calls = self.extractor.extract_calls(process_chunk.content, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Phase 1 checks
        assert (
            "Processor.helper" in callee_names
        ), f"self.helper() not resolved. Got: {callee_names}"
        # Note: super() without class hierarchy in chunk resolves to "super.base_process"
        assert (
            "super.base_process" in callee_names
        ), f"super().base_process() not resolved. Got: {callee_names}"

        # Phase 2 check
        assert (
            "Validator.validate" in callee_names
        ), f"validator.validate() not resolved. Got: {callee_names}"

        # Phase 3 checks
        assert (
            "DataFormatter.format" in callee_names
        ), f"formatter.format() not resolved. Got: {callee_names}"
        # Note: self.handler.handle() needs __init__ to be in same chunk
        # When extracting just the method chunk, self.handler assignment isn't visible
        # So it falls back to bare "handle"
        assert (
            "handle" in callee_names
        ), f"self.handler.handle() not resolved. Got: {callee_names}"
