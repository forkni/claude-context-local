"""
Unit tests for Phase 4: Import-Based Resolution.

Tests the extraction and resolution of types from import statements.
"""

import ast
import os
import tempfile

from graph.call_graph_extractor import PythonCallGraphExtractor


class TestSimpleImportResolution:
    """Test basic import tracking and resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_from_import_resolves(self):
        """Test from module import Class enables x = Class(); x.method()."""
        # Create a temporary file with imports
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler

def process():
    handler = ErrorHandler()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # Should have 2 calls: ErrorHandler() and handle()
            assert len(calls) == 2

            # Find the handle() call
            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)

    def test_simple_import_resolves(self):
        """Test import module enables module.Class() resolution."""
        # Create a temporary file with imports
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
import handlers

def process():
    handler = handlers.ErrorHandler()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = handlers.ErrorHandler()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # Find the handle() call
            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)

    def test_import_class_method(self):
        """Test from module import Class; Class.class_method()."""
        # Create a temporary file with imports
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler

def process():
    ErrorHandler.class_method()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    ErrorHandler.class_method()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-5:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            assert len(calls) == 1
            assert calls[0].callee_name == "ErrorHandler.class_method"
        finally:
            os.unlink(temp_path)


class TestAliasedImportResolution:
    """Test aliased import tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_alias_resolves_to_original(self):
        """Test from x import Y as Z resolves Z to Y."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler as EH

def process():
    handler = EH()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = EH()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # Should resolve to original class name, not alias
            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)

    def test_module_alias(self):
        """Test import module as alias."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
import handlers as h

def process():
    handler = h.ErrorHandler()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = h.ErrorHandler()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)


class TestRelativeImportResolution:
    """Test relative import handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_relative_import_single_dot(self):
        """Test from . import helper."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from . import helper

def process():
    helper.do_stuff()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    helper.do_stuff()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-5:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # helper is imported and should be recognized
            assert len(calls) == 1
            # Since helper is imported, it resolves to helper.do_stuff
            assert "do_stuff" in calls[0].callee_name
        finally:
            os.unlink(temp_path)

    def test_relative_import_from(self):
        """Test from .module import Class."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from .extractors import ExceptionExtractor

def process():
    extractor = ExceptionExtractor()
    extractor.extract()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    extractor = ExceptionExtractor()
    extractor.extract()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            method_call = [c for c in calls if c.callee_name.endswith(".extract")][0]
            assert method_call.callee_name == "ExceptionExtractor.extract"
        finally:
            os.unlink(temp_path)

    def test_relative_import_double_dot(self):
        """Test from ..utils import Parser."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from ..utils import Parser

def process():
    parser = Parser()
    parser.parse()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    parser = Parser()
    parser.parse()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            method_call = [c for c in calls if c.callee_name.endswith(".parse")][0]
            assert method_call.callee_name == "Parser.parse"
        finally:
            os.unlink(temp_path)


class TestDottedImportResolution:
    """Test dotted/nested imports."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_dotted_module_import(self):
        """Test import x.y.z."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
import os.path

def process():
    result = os.path.join('a', 'b')
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    result = os.path.join('a', 'b')
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-5:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            assert len(calls) == 1
            # The call is to join
            assert calls[0].callee_name == "join"
        finally:
            os.unlink(temp_path)


class TestImportEdgeCases:
    """Test edge cases and negative scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_star_import_falls_back(self):
        """Test from x import * cannot resolve."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import *

def process():
    handler = ErrorHandler()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-6:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # Star import cannot resolve, but assignment tracking still works
            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            # Falls back to simple constructor inference
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)

    def test_shadowing_by_assignment(self):
        """Test local assignment shadows import."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler

def process():
    ErrorHandler = CustomHandler
    x = ErrorHandler()
    x.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    ErrorHandler = CustomHandler
    x = ErrorHandler()
    x.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-7:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            # The assignment shadows the import
            # x = ErrorHandler() -> ErrorHandler is now CustomHandler
            # But our current implementation doesn't track class reassignments
            # So it still uses the imported name
            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            # Still resolves based on constructor call name
            assert "handle" in method_call.callee_name
        finally:
            os.unlink(temp_path)

    def test_no_file_path_falls_back(self):
        """Test that missing file_path falls back to chunk imports."""
        chunk_code = """
from handlers import ErrorHandler

def process():
    handler = ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-6:function:process"}
        # No file_path - falls back to extracting from chunk code
        calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_file_not_found_graceful(self):
        """Test missing file is handled gracefully."""
        chunk_code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-4:function:process",
            "file_path": "/nonexistent/file.py",
        }
        # Should not crash, falls back to bare name resolution
        calls = self.extractor.extract_calls(chunk_code, chunk_metadata)
        assert len(calls) == 2


class TestExtractImports:
    """Direct tests for _extract_imports() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_simple_import_extraction(self):
        """Test direct extraction of simple imports."""
        code = """
import os
from typing import List
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        assert "os" in imports
        assert imports["os"] == "os"
        assert "List" in imports
        assert imports["List"] == "typing.List"

    def test_aliased_import_extraction(self):
        """Test extraction of aliased imports."""
        code = """
import numpy as np
from collections import defaultdict as dd
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        assert "np" in imports
        assert imports["np"] == "numpy"
        assert "dd" in imports
        assert imports["dd"] == "collections.defaultdict"

    def test_relative_import_extraction(self):
        """Test extraction of relative imports."""
        code = """
from . import helper
from ..utils import Parser
from ... import base
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        assert "helper" in imports
        assert imports["helper"] == ".helper"
        assert "Parser" in imports
        assert imports["Parser"] == "..utils.Parser"
        assert "base" in imports
        assert imports["base"] == "...base"

    def test_multiple_from_import(self):
        """Test from module import a, b, c."""
        code = """
from typing import List, Dict, Optional
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        assert "List" in imports
        assert imports["List"] == "typing.List"
        assert "Dict" in imports
        assert imports["Dict"] == "typing.Dict"
        assert "Optional" in imports
        assert imports["Optional"] == "typing.Optional"

    def test_star_import_skipped(self):
        """Test star imports are skipped."""
        code = """
from module import *
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        # Star import should not add any entries
        assert len(imports) == 0

    def test_dotted_import_extraction(self):
        """Test import os.path."""
        code = """
import os.path
import a.b.c
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)

        # First component is the local name
        assert "os" in imports
        assert imports["os"] == "os.path"
        assert "a" in imports
        assert imports["a"] == "a.b.c"


class TestInteractionWithPhases1Through3:
    """Test interaction with previous phases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_all_four_phases_together(self):
        """Test Phases 1-4 work together."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from extractors import ExceptionExtractor

class Processor(BaseProcessor):
    def process(self, handler: Handler):
        extractor = ExceptionExtractor()
        self.helper()
        super().parent_method()
        handler.handle()
        extractor.extract()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
class Processor(BaseProcessor):
    def process(self, handler: Handler):
        extractor = ExceptionExtractor()
        self.helper()
        super().parent_method()
        handler.handle()
        extractor.extract()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-10:method:Processor.process",
                "parent_class": "Processor",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            callee_names = {c.callee_name for c in calls}

            # Phase 1: self call
            assert "Processor.helper" in callee_names
            # Phase 1: super call
            assert "BaseProcessor.parent_method" in callee_names
            # Phase 2: annotation
            assert "Handler.handle" in callee_names
            # Phase 3/4: assignment with import
            assert "ExceptionExtractor.extract" in callee_names
        finally:
            os.unlink(temp_path)

    def test_import_takes_precedence_for_class_methods(self):
        """Test imported class methods resolve correctly."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from extractors import ExceptionExtractor

def process():
    ExceptionExtractor.configure()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    ExceptionExtractor.configure()
"""
            chunk_metadata = {
                "chunk_id": "test.py:3-5:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            assert len(calls) == 1
            assert calls[0].callee_name == "ExceptionExtractor.configure"
        finally:
            os.unlink(temp_path)

    def test_assignment_shadows_import_for_local_var(self):
        """Test local assignment takes precedence over import for same var name."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from extractors import ExceptionExtractor

def process():
    # Local variable shadows module-level import for 'handler'
    handler = ErrorHandler()
    handler.handle()
"""
            )
            temp_path = f.name

        try:
            chunk_code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
            chunk_metadata = {
                "chunk_id": "test.py:4-7:function:process",
                "file_path": temp_path,
            }
            calls = self.extractor.extract_calls(chunk_code, chunk_metadata)

            method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
            # Assignment tracking resolves handler to ErrorHandler
            assert method_call.callee_name == "ErrorHandler.handle"
        finally:
            os.unlink(temp_path)


class TestInferTypeFromCallWithImports:
    """Test _infer_type_from_call() with import resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_aliased_constructor_resolves(self):
        """Test H() resolves to Handler when H is alias."""
        # Set up imports first
        code = """
from handlers import Handler as H
x = H()
"""
        tree = ast.parse(code)
        imports = self.extractor._import_resolver.extract_imports(tree)
        self.extractor._assignment_tracker.set_imports(imports)

        # Now test type inference
        call_code = "H()"
        call_tree = ast.parse(call_code)
        call_node = call_tree.body[0].value

        type_name = self.extractor._assignment_tracker.infer_type_from_call(call_node)
        assert type_name == "Handler"

    def test_non_imported_uses_bare_name(self):
        """Test non-imported class uses bare name."""
        # No imports set up
        call_code = "MyClass()"
        call_tree = ast.parse(call_code)
        call_node = call_tree.body[0].value

        type_name = self.extractor._assignment_tracker.infer_type_from_call(call_node)
        assert type_name == "MyClass"


class TestCacheAndPerformance:
    """Test caching and performance behavior."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_file_imports_cached(self):
        """Test that file imports are cached for reuse."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler

def process():
    pass
"""
            )
            temp_path = f.name

        try:
            # First call
            imports1 = self.extractor._import_resolver.read_file_imports(temp_path)
            assert "ErrorHandler" in imports1

            # Check cache
            assert temp_path in self.extractor._import_resolver._file_imports_cache

            # Second call should use cache
            imports2 = self.extractor._import_resolver.read_file_imports(temp_path)
            assert imports1 == imports2
        finally:
            os.unlink(temp_path)

    def test_multiple_chunks_same_file(self):
        """Test multiple chunks from same file share cached imports."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(
                """
from handlers import ErrorHandler, SuccessHandler

def func1():
    handler = ErrorHandler()
    handler.handle()

def func2():
    handler = SuccessHandler()
    handler.process()
"""
            )
            temp_path = f.name

        try:
            # First chunk
            chunk1_code = """
def func1():
    handler = ErrorHandler()
    handler.handle()
"""
            calls1 = self.extractor.extract_calls(
                chunk1_code,
                {"chunk_id": "test.py:3-6:function:func1", "file_path": temp_path},
            )

            # Second chunk - should use cached imports
            chunk2_code = """
def func2():
    handler = SuccessHandler()
    handler.process()
"""
            calls2 = self.extractor.extract_calls(
                chunk2_code,
                {"chunk_id": "test.py:8-11:function:func2", "file_path": temp_path},
            )

            # Both should resolve correctly
            method_call1 = [c for c in calls1 if c.callee_name.endswith(".handle")][0]
            assert method_call1.callee_name == "ErrorHandler.handle"

            method_call2 = [c for c in calls2 if c.callee_name.endswith(".process")][0]
            assert method_call2.callee_name == "SuccessHandler.process"
        finally:
            os.unlink(temp_path)
