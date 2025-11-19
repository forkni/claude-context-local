"""
Unit tests for self/super call resolution (Phase 1: Call Graph Resolution).

Tests that the PythonCallGraphExtractor correctly resolves:
- self.method() → ClassName.method
- super().method() → ParentClass.method

This enables accurate call graph construction by disambiguating
method calls within classes.
"""

from graph.call_graph_extractor import PythonCallGraphExtractor


class TestSelfCallResolution:
    """Test that self.method() calls resolve to qualified names."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_self_method_call_resolved(self):
        """Test self.method() resolves to ClassName.method."""
        code = """
class MyClass:
    def caller(self):
        self.callee()

    def callee(self):
        pass
"""
        # Parent class passed from chunker
        chunk_metadata = {
            "chunk_id": "test.py:2-3:method:MyClass.caller",
            "parent_class": "MyClass",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Find the self.callee() call
        callee_calls = [c for c in calls if "callee" in c.callee_name]
        assert len(callee_calls) >= 1

        # Should be qualified with class name
        callee_call = callee_calls[0]
        assert (
            callee_call.callee_name == "MyClass.callee"
        ), f"Expected MyClass.callee, got {callee_call.callee_name}"

    def test_cls_method_call_resolved(self):
        """Test cls.method() resolves to ClassName.method."""
        code = """
class MyClass:
    @classmethod
    def class_caller(cls):
        cls.class_callee()

    @classmethod
    def class_callee(cls):
        pass
"""
        chunk_metadata = {
            "chunk_id": "test.py:2-4:method:MyClass.class_caller",
            "parent_class": "MyClass",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Find the cls.class_callee() call
        callee_calls = [c for c in calls if "class_callee" in c.callee_name]
        assert len(callee_calls) >= 1

        # Should be qualified with class name
        callee_call = callee_calls[0]
        assert callee_call.callee_name == "MyClass.class_callee"

    def test_multiple_self_calls(self):
        """Test multiple self calls all get resolved."""
        code = """
class Calculator:
    def process(self):
        self.validate()
        self.compute()
        self.finalize()
"""
        chunk_metadata = {
            "chunk_id": "test.py:2-5:method:Calculator.process",
            "parent_class": "Calculator",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # All should be qualified
        method_names = [c.callee_name for c in calls]
        assert "Calculator.validate" in method_names
        assert "Calculator.compute" in method_names
        assert "Calculator.finalize" in method_names

    def test_self_call_without_parent_class_fallback(self):
        """Test self calls without parent_class context fall back to bare name."""
        code = """
def method_with_self(self):
    self.other()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-2:function:method_with_self",
            "parent_class": None,  # No parent class context
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Without class context, should fall back to bare name
        callee_calls = [c for c in calls if "other" in c.callee_name]
        assert len(callee_calls) >= 1
        assert callee_calls[0].callee_name == "other"


class TestSuperCallResolution:
    """Test that super().method() calls resolve to parent class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_super_method_call_resolved(self):
        """Test super().method() resolves to ParentClass.method."""
        code = """
class Parent:
    def method(self):
        pass

class Child(Parent):
    def method(self):
        super().method()
"""
        chunk_metadata = {
            "chunk_id": "test.py:6-7:method:Child.method",
            "parent_class": "Child",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have Parent.method
        parent_calls = [c for c in calls if c.callee_name == "Parent.method"]
        assert (
            len(parent_calls) >= 1
        ), f"Expected Parent.method, got {[c.callee_name for c in calls]}"

    def test_super_init_call_resolved(self):
        """Test super().__init__() resolves to ParentClass.__init__."""
        code = """
class Base:
    def __init__(self):
        pass

class Derived(Base):
    def __init__(self):
        super().__init__()
"""
        chunk_metadata = {
            "chunk_id": "test.py:6-7:method:Derived.__init__",
            "parent_class": "Derived",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have Base.__init__
        init_calls = [c for c in calls if "__init__" in c.callee_name]
        assert len(init_calls) >= 1

        base_init = [c for c in init_calls if c.callee_name == "Base.__init__"]
        assert (
            len(base_init) >= 1
        ), f"Expected Base.__init__, got {[c.callee_name for c in init_calls]}"

    def test_super_call_no_parent_class(self):
        """Test super() call when no parent class is detected."""
        code = """
class Orphan:
    def method(self):
        super().method()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-3:method:Orphan.method",
            "parent_class": "Orphan",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should fall back to super.method since no parent detected
        method_calls = [c for c in calls if "method" in c.callee_name]
        assert len(method_calls) >= 1

        # Could be super.method or just method
        super_calls = [
            c
            for c in method_calls
            if "super" in c.callee_name or c.callee_name == "method"
        ]
        assert len(super_calls) >= 1

    def test_super_with_multiple_inheritance(self):
        """Test super() with multiple base classes uses first base."""
        code = """
class A:
    def method(self):
        pass

class B:
    def method(self):
        pass

class C(A, B):
    def method(self):
        super().method()
"""
        chunk_metadata = {
            "chunk_id": "test.py:10-11:method:C.method",
            "parent_class": "C",
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # MRO means it should be A.method
        a_calls = [c for c in calls if c.callee_name == "A.method"]
        assert (
            len(a_calls) >= 1
        ), f"Expected A.method, got {[c.callee_name for c in calls]}"


class TestRegularCallsUnaffected:
    """Test that regular calls (not self/super) work as before."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_simple_function_call(self):
        """Test simple function calls return bare name."""
        code = """
def caller():
    helper()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-2:function:caller",
            "parent_class": None,
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        assert len(calls) >= 1
        helper_calls = [c for c in calls if c.callee_name == "helper"]
        assert len(helper_calls) == 1

    def test_external_method_call(self):
        """Test external method calls return bare method name."""
        code = """
def process():
    obj = get_object()
    obj.process_data()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-3:function:process",
            "parent_class": None,
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # External method call should just be method name
        process_calls = [c for c in calls if c.callee_name == "process_data"]
        assert len(process_calls) == 1

    def test_chained_method_call(self):
        """Test chained method calls return final method name."""
        code = """
def process():
    result.transform().validate().save()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-2:function:process",
            "parent_class": None,
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have all three method names
        call_names = [c.callee_name for c in calls]
        assert "transform" in call_names
        assert "validate" in call_names
        assert "save" in call_names


class TestClassHierarchyExtraction:
    """Test extraction of class hierarchy for super() resolution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_single_inheritance_extracted(self):
        """Test single inheritance is correctly extracted."""
        code = """
class Parent:
    pass

class Child(Parent):
    def method(self):
        pass
"""
        chunk_metadata = {
            "chunk_id": "test.py:5-6:method:Child.method",
            "parent_class": "Child",
        }

        # Extract calls triggers hierarchy extraction
        self.extractor.extract_calls(code, chunk_metadata)

        # Check internal state
        assert "Child" in self.extractor._class_bases
        assert "Parent" in self.extractor._class_bases["Child"]

    def test_multiple_inheritance_extracted(self):
        """Test multiple inheritance is correctly extracted."""
        code = """
class A:
    pass

class B:
    pass

class C(A, B):
    def method(self):
        pass
"""
        chunk_metadata = {
            "chunk_id": "test.py:8-9:method:C.method",
            "parent_class": "C",
        }

        self.extractor.extract_calls(code, chunk_metadata)

        assert "C" in self.extractor._class_bases
        assert self.extractor._class_bases["C"] == ["A", "B"]

    def test_get_parent_class_helper(self):
        """Test _get_parent_class returns first base class."""
        code = """
class A:
    pass

class B(A):
    pass
"""
        chunk_metadata = {"chunk_id": "test.py:4-5:class:B", "parent_class": None}

        self.extractor.extract_calls(code, chunk_metadata)

        parent = self.extractor._get_parent_class("B")
        assert parent == "A"

    def test_get_parent_class_no_bases(self):
        """Test _get_parent_class returns None for class without bases."""
        code = """
class Standalone:
    pass
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-2:class:Standalone",
            "parent_class": None,
        }

        self.extractor.extract_calls(code, chunk_metadata)

        parent = self.extractor._get_parent_class("Standalone")
        assert parent is None
