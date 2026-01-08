"""
Integration tests for Phase 4: Import-Based Resolution.

Tests the full pipeline with import-based type inference.
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock

from chunking.multi_language_chunker import MultiLanguageChunker
from graph.call_graph_extractor import PythonCallGraphExtractor
from mcp_server.services import ServiceLocator
from search.config import ChunkingConfig


class TestImportResolutionEndToEnd:
    """End-to-end tests for import resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        # Disable greedy merge for these tests to check individual method chunks
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig(enable_chunk_merging=False)
        self.locator = ServiceLocator.instance()
        self.locator.register("config", mock_config)

        self.extractor = PythonCallGraphExtractor()
        self.chunker = MultiLanguageChunker()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        ServiceLocator.reset()
        shutil.rmtree(self.temp_dir)

    def test_import_resolution_in_chunked_file(self):
        """Test imports are resolved correctly when processing chunked file."""
        # Create a test file with imports
        test_file = os.path.join(self.temp_dir, "test_module.py")
        with open(test_file, "w") as f:
            f.write(
                """
from extractors import ExceptionExtractor, TypeExtractor

class Processor:
    def process_exceptions(self):
        extractor = ExceptionExtractor()
        extractor.extract()

    def process_types(self):
        extractor = TypeExtractor()
        extractor.analyze()
"""
            )

        # Read and chunk the file
        with open(test_file, "r") as f:
            f.read()

        chunks = self.chunker.chunk_file(test_file)

        # Find method chunks
        method_chunks = [c for c in chunks if c.chunk_type == "method"]

        # Process each method chunk
        resolved_calls = {}
        for chunk in method_chunks:
            chunk_metadata = {
                "chunk_id": f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}:{chunk.name}",
                "file_path": test_file,
                "parent_class": chunk.name.split(".")[0] if "." in chunk.name else None,
            }
            calls = self.extractor.extract_calls(chunk.content, chunk_metadata)
            resolved_calls[chunk.name] = [c.callee_name for c in calls]

        # Verify resolution - chunk names may not include class prefix
        # Look for method names that contain our target names
        found_exceptions = False
        found_types = False
        for name, calls in resolved_calls.items():
            if "process_exceptions" in name:
                assert "ExceptionExtractor.extract" in calls
                found_exceptions = True
            if "process_types" in name:
                assert "TypeExtractor.analyze" in calls
                found_types = True
        assert (
            found_exceptions
        ), f"Did not find process_exceptions in {resolved_calls.keys()}"
        assert found_types, f"Did not find process_types in {resolved_calls.keys()}"

    def test_aliased_import_in_chunked_file(self):
        """Test aliased imports resolve to original class names."""
        test_file = os.path.join(self.temp_dir, "aliased_module.py")
        with open(test_file, "w") as f:
            f.write(
                """
from handlers import ErrorHandler as EH
from utils import Logger as L

def process():
    handler = EH()
    logger = L()
    handler.handle()
    logger.log("message")
"""
            )

        with open(test_file, "r") as f:
            f.read()

        chunks = self.chunker.chunk_file(test_file)

        # Find function chunk
        func_chunk = [c for c in chunks if c.chunk_type == "function"][0]

        chunk_metadata = {
            "chunk_id": f"{func_chunk.file_path}:{func_chunk.start_line}-{func_chunk.end_line}:{func_chunk.chunk_type}:{func_chunk.name}",
            "file_path": test_file,
        }
        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Should resolve to original names, not aliases
        assert "ErrorHandler.handle" in callee_names
        assert "Logger.log" in callee_names

    def test_multiple_modules_with_imports(self):
        """Test import resolution across multiple modules."""
        # Create first module
        module1 = os.path.join(self.temp_dir, "module1.py")
        with open(module1, "w") as f:
            f.write(
                """
from shared import BaseHandler

class Handler1(BaseHandler):
    def process(self):
        handler = BaseHandler()
        handler.handle()
"""
            )

        # Create second module
        module2 = os.path.join(self.temp_dir, "module2.py")
        with open(module2, "w") as f:
            f.write(
                """
from shared import BaseHandler

class Handler2(BaseHandler):
    def process(self):
        handler = BaseHandler()
        handler.handle()
"""
            )

        # Process both modules
        for module_file in [module1, module2]:
            with open(module_file, "r") as f:
                f.read()

            chunks = self.chunker.chunk_file(module_file)
            method_chunks = [c for c in chunks if c.chunk_type == "method"]

            for chunk in method_chunks:
                chunk_metadata = {
                    "chunk_id": f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}:{chunk.name}",
                    "file_path": module_file,
                    "parent_class": (
                        chunk.name.split(".")[0] if "." in chunk.name else None
                    ),
                }
                calls = self.extractor.extract_calls(chunk.content, chunk_metadata)

                # Both should resolve to BaseHandler.handle
                method_calls = [c for c in calls if c.callee_name.endswith(".handle")]
                assert len(method_calls) > 0
                assert method_calls[0].callee_name == "BaseHandler.handle"


class TestBackwardCompatibility:
    """Test backward compatibility with Phases 1-3."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_phase1_self_calls_still_work(self):
        """Test self.method() still resolves correctly."""
        code = """
class MyClass:
    def process(self):
        self.helper()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-5:method:MyClass.process",
            "parent_class": "MyClass",
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        helper_calls = [c for c in calls if "helper" in c.callee_name.lower()]
        assert len(helper_calls) > 0
        assert helper_calls[0].callee_name == "MyClass.helper"

    def test_phase1_super_calls_still_work(self):
        """Test super().method() still resolves correctly."""
        code = """
class MyClass(BaseClass):
    def process(self):
        super().parent_method()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-5:method:MyClass.process",
            "parent_class": "MyClass",
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        parent_calls = [c for c in calls if "parent_method" in c.callee_name]
        assert len(parent_calls) > 0
        assert parent_calls[0].callee_name == "BaseClass.parent_method"

    def test_phase2_type_annotations_still_work(self):
        """Test type-annotated parameters still resolve correctly."""
        code = """
def process(handler: ErrorHandler):
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-3:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_phase3_assignments_still_work(self):
        """Test local assignments still resolve correctly."""
        code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_all_phases_together_without_imports(self):
        """Test all phases work when no imports are present."""
        code = """
class Processor(BaseProcessor):
    def process(self, handler: Handler):
        extractor = ExceptionExtractor()
        self.helper()
        super().parent_method()
        handler.handle()
        extractor.extract()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-9:method:Processor.process",
            "parent_class": "Processor",
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Phase 1
        assert "Processor.helper" in callee_names
        assert "BaseProcessor.parent_method" in callee_names
        # Phase 2
        assert "Handler.handle" in callee_names
        # Phase 3
        assert "ExceptionExtractor.extract" in callee_names


class TestRealWorldPatterns:
    """Test real-world code patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def test_typical_function_with_dependencies(self):
        """Test typical function with imported dependencies."""
        test_file = os.path.join(self.temp_dir, "service.py")
        with open(test_file, "w") as f:
            f.write(
                """
from database import Connection
from cache import Cache
from logger import Logger

def process_data():
    db = Connection()
    cache = Cache()
    logger = Logger()

    logger.info("Starting")
    data = db.query("SELECT *")
    cache.set("key", data)
    return data
"""
            )

        # Chunk and analyze
        chunker = MultiLanguageChunker()
        chunks = chunker.chunk_file(test_file)

        # Find function chunk
        func_chunk = [
            c for c in chunks if c.chunk_type == "function" and c.name == "process_data"
        ][0]

        chunk_metadata = {
            "chunk_id": f"{func_chunk.file_path}:{func_chunk.start_line}-{func_chunk.end_line}:{func_chunk.chunk_type}:{func_chunk.name}",
            "file_path": test_file,
        }
        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Verify dependency calls are resolved via import + assignment tracking
        assert "Logger.info" in callee_names
        assert "Connection.query" in callee_names
        assert "Cache.set" in callee_names

    def test_factory_pattern_with_imports(self):
        """Test factory pattern with imported classes."""
        test_file = os.path.join(self.temp_dir, "factory.py")
        with open(test_file, "w") as f:
            f.write(
                """
from handlers import ErrorHandler, SuccessHandler, WarningHandler

def create_handler(handler_type):
    if handler_type == "error":
        return ErrorHandler()
    elif handler_type == "success":
        return SuccessHandler()
    else:
        return WarningHandler()
"""
            )

        chunker = MultiLanguageChunker()
        chunks = chunker.chunk_file(test_file)

        # Find create_handler function
        func_chunk = [
            c
            for c in chunks
            if c.chunk_type == "function" and c.name == "create_handler"
        ][0]

        chunk_metadata = {
            "chunk_id": f"{func_chunk.file_path}:{func_chunk.start_line}-{func_chunk.end_line}:{func_chunk.chunk_type}:{func_chunk.name}",
            "file_path": test_file,
        }
        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # All constructor calls should be present
        assert "ErrorHandler" in callee_names
        assert "SuccessHandler" in callee_names
        assert "WarningHandler" in callee_names

    def test_context_manager_with_imports(self):
        """Test context manager pattern with imported types."""
        test_file = os.path.join(self.temp_dir, "context.py")
        with open(test_file, "w") as f:
            f.write(
                """
from resources import DatabaseConnection, FileHandle

def process_data():
    with DatabaseConnection() as db:
        data = db.fetch_all()
        with FileHandle("output.txt") as f:
            f.write(data)
"""
            )

        with open(test_file, "r") as f:
            f.read()

        chunker = MultiLanguageChunker()
        chunks = chunker.chunk_file(test_file)

        func_chunk = [c for c in chunks if c.chunk_type == "function"][0]

        chunk_metadata = {
            "chunk_id": f"{func_chunk.file_path}:{func_chunk.start_line}-{func_chunk.end_line}:{func_chunk.chunk_type}:{func_chunk.name}",
            "file_path": test_file,
        }
        calls = self.extractor.extract_calls(func_chunk.content, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Both context managers should have their methods resolved
        assert "DatabaseConnection.fetch_all" in callee_names
        assert "FileHandle.write" in callee_names
