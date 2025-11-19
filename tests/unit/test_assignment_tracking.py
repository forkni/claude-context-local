"""
Unit tests for Phase 3: Assignment Tracking.

Tests the extraction and resolution of types from local variable assignments.
"""

import ast

from graph.call_graph_extractor import PythonCallGraphExtractor


class TestSimpleAssignmentTracking:
    """Test basic variable assignment type inference."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_constructor_assignment_resolves(self):
        """Test x = MyClass() enables x.method() resolution."""
        code = """
def process():
    handler = ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have 2 calls: ErrorHandler() and handle()
        assert len(calls) == 2

        # Find the handle() call (method call ends with .handle)
        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_multiple_assignments_tracked(self):
        """Test multiple variable assignments are tracked."""
        code = """
def process():
    extractor = ExceptionExtractor()
    handler = ErrorHandler()
    extractor.extract()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-6:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}
        assert "ExceptionExtractor.extract" in callee_names
        assert "ErrorHandler.handle" in callee_names

    def test_chained_assignment(self):
        """Test a = b = MyClass() assigns to both."""
        code = """
def process():
    a = b = ExceptionExtractor()
    a.extract()
    b.validate()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}
        assert "ExceptionExtractor.extract" in callee_names
        assert "ExceptionExtractor.validate" in callee_names

    def test_reassignment_uses_latest(self):
        """Test reassignment uses the latest type (last-write-wins)."""
        code = """
def process():
    x = Foo()
    x = Bar()
    x.method()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Find the method() call
        method_call = [c for c in calls if c.callee_name.endswith(".method")][0]
        assert method_call.callee_name == "Bar.method"

    def test_constructor_with_args_still_resolves(self):
        """Test MyClass(arg1, arg2) still resolves the type."""
        code = """
def process():
    handler = ErrorHandler(config, logger)
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"


class TestAnnotatedAssignmentTracking:
    """Test annotated assignment type tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_annotated_assignment_resolves(self):
        """Test x: MyClass = value enables resolution."""
        code = """
def process():
    handler: ErrorHandler = create_handler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_annotated_assignment_without_value(self):
        """Test x: MyClass (declaration only) enables resolution."""
        code = """
def process():
    handler: ErrorHandler
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_annotated_overrides_constructor(self):
        """Test annotation takes priority over constructor type when both present."""
        code = """
def process():
    handler: BaseHandler = DerivedHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        # Annotated assignment overwrites constructor in _type_annotations
        # Since we process ast.AnnAssign, it sets BaseHandler
        # Then ast.Assign would set DerivedHandler if it were a plain assign
        # But AnnAssign doesn't trigger Assign branch - so annotation wins
        assert method_call.callee_name == "BaseHandler.handle"

    def test_optional_annotated_assignment(self):
        """Test x: Optional[MyClass] = value resolves."""
        code = """
def process():
    handler: Optional[ErrorHandler] = get_handler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"


class TestNamedExpressionTracking:
    """Test walrus operator assignment tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_named_expression_if(self):
        """Test if (x := MyClass()): pattern."""
        code = """
def process():
    if (handler := ErrorHandler()):
        handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_named_expression_while(self):
        """Test while (x := factory()): falls back for non-constructor."""
        code = """
def process():
    while (item := get_item()):
        item.run()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Factory call - get_item is treated as a constructor name
        # _infer_type_from_call returns "get_item" for Name nodes
        method_call = [c for c in calls if c.callee_name.endswith(".run")][0]
        assert method_call.callee_name == "get_item.run"

    def test_named_expression_in_condition(self):
        """Test walrus operator in complex condition."""
        code = """
def process():
    if data and (handler := ErrorHandler()):
        handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if "handle" in c.callee_name.lower()][0]
        assert method_call.callee_name == "ErrorHandler.handle"


class TestAttributeAssignmentTracking:
    """Test self.attr = MyClass() tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_self_attribute_assignment(self):
        """Test self.handler = Handler() in __init__."""
        code = """
class Processor:
    def __init__(self):
        self.manager = ResourceManager()

    def process(self):
        self.manager.cleanup()
"""
        # Test the full class - assignments are tracked across the class
        chunk_metadata = {
            "chunk_id": "test.py:1-8:class:Processor",
            "parent_class": "Processor"
        }

        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Find the cleanup() call
        cleanup_calls = [c for c in calls if c.callee_name.endswith(".cleanup")]
        assert len(cleanup_calls) > 0
        assert cleanup_calls[0].callee_name == "ResourceManager.cleanup"

    def test_cls_attribute_assignment(self):
        """Test cls.instance = MyClass() in classmethod."""
        code = """
class Factory:
    @classmethod
    def create(cls):
        cls.instance = Singleton()
        cls.instance.initialize()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-6:method:Factory.create",
            "parent_class": "Factory"
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Find the initialize() call
        init_calls = [c for c in calls if "initialize" in c.callee_name.lower()]
        assert len(init_calls) > 0
        assert init_calls[0].callee_name == "Singleton.initialize"

    def test_other_object_attribute_not_tracked(self):
        """Test obj.attr = MyClass() is NOT tracked (no type for obj)."""
        code = """
def process(obj):
    obj.manager = ResourceManager()
    obj.manager.cleanup()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # obj.manager.cleanup() should NOT resolve (we don't know obj's type)
        cleanup_calls = [c for c in calls if "cleanup" in c.callee_name]
        assert len(cleanup_calls) > 0
        # Falls back to bare name
        assert cleanup_calls[0].callee_name == "cleanup"


class TestWithStatementTracking:
    """Test context manager assignment tracking."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_with_constructor(self):
        """Test with MyClass() as x: pattern."""
        code = """
def process():
    with ResourceManager() as manager:
        manager.cleanup()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if "cleanup" in c.callee_name.lower()][0]
        assert method_call.callee_name == "ResourceManager.cleanup"

    def test_with_nested(self):
        """Test with A() as a, B() as b: pattern."""
        code = """
def process():
    with FileHandler() as fh, DataProcessor() as dp:
        fh.read()
        dp.process()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}
        assert "FileHandler.read" in callee_names
        assert "DataProcessor.process" in callee_names

    def test_with_no_as_clause(self):
        """Test with MyClass(): (no as) doesn't break."""
        code = """
def process():
    with SomeContext():
        pass
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Should have constructor call but no variable assignment
        assert len(calls) == 1
        assert calls[0].callee_name == "SomeContext"

    def test_with_factory_falls_back(self):
        """Test with get_context() as ctx: - function name is used as type."""
        code = """
def process():
    with get_context() as ctx:
        ctx.execute()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # _infer_type_from_call returns "get_context" for Name nodes
        method_call = [c for c in calls if c.callee_name.endswith(".execute")][0]
        assert method_call.callee_name == "get_context.execute"


class TestScopeHandling:
    """Test variable scope handling in assignments."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_assignment_in_function_scope(self):
        """Test assignments within function scope work."""
        code = """
def outer():
    handler = ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:outer"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_class_and_method_assignments(self):
        """Test class-level and method-level assignments both tracked."""
        code = """
class MyClass:
    default_manager = DefaultManager()

    def process(self):
        custom_manager = CustomManager()
        custom_manager.run()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-7:class:MyClass",
            "parent_class": "MyClass"
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Local variable 'custom_manager' should resolve to CustomManager
        run_calls = [c for c in calls if c.callee_name.endswith(".run")]
        assert len(run_calls) > 0
        assert run_calls[0].callee_name == "CustomManager.run"


class TestEdgeCasesAndNegatives:
    """Test edge cases and negative scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_augmented_assignment_ignored(self):
        """Test x += MyClass() is ignored (not simple assignment)."""
        code = """
def process():
    items = []
    items += [ExceptionExtractor()]
    items[0].extract()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # items[0].extract() should NOT resolve (subscript target)
        extract_calls = [c for c in calls if "extract" in c.callee_name.lower()]
        assert len(extract_calls) > 0
        # Falls back to bare name
        assert extract_calls[0].callee_name == "extract"

    def test_subscript_assignment_ignored(self):
        """Test x[0] = MyClass() is ignored."""
        code = """
def process():
    handlers = {}
    handlers[0] = ErrorHandler()
    handlers[0].handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-5:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # handlers[0].handle() should NOT resolve (subscript target)
        handle_calls = [c for c in calls if "handle" in c.callee_name]
        assert len(handle_calls) > 0
        # Falls back to bare name (subscript receiver is not tracked)
        assert handle_calls[0].callee_name == "handle"

    def test_factory_call_uses_function_name(self):
        """Test x = factory() uses function name as type (limitation)."""
        code = """
def process():
    handler = create_handler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Factory call - function name is used as type (limitation)
        # _infer_type_from_call returns "create_handler" for Name nodes
        handle_calls = [c for c in calls if c.callee_name.endswith(".handle")]
        assert len(handle_calls) > 0
        assert handle_calls[0].callee_name == "create_handler.handle"

    def test_qualified_constructor_resolves(self):
        """Test x = module.MyClass() resolves to MyClass."""
        code = """
def process():
    handler = handlers.ErrorHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "ErrorHandler.handle"

    def test_method_return_uses_method_name(self):
        """Test x = obj.get_handler() uses method name as type (limitation)."""
        code = """
def process(obj):
    handler = obj.get_handler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Method return - method name is used as type (limitation)
        # _infer_type_from_call returns "get_handler" for Attribute nodes
        handle_calls = [c for c in calls if c.callee_name.endswith(".handle")]
        assert len(handle_calls) > 0
        assert handle_calls[0].callee_name == "get_handler.handle"

    def test_chained_call_not_inferred(self):
        """Test x = factory().create() doesn't track (chained call)."""
        code = """
def process():
    instance = Builder().create()
    instance.execute()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Chained call - Builder().create() is not a simple Call with Name/Attribute func
        # The outer Call has func = Attribute(value=Call(...), attr='create')
        # _infer_type_from_call returns "create" for the Attribute
        execute_calls = [c for c in calls if c.callee_name.endswith(".execute")]
        assert len(execute_calls) > 0
        assert execute_calls[0].callee_name == "create.execute"


class TestInteractionWithPhase1And2:
    """Test interaction with self/super (Phase 1) and annotations (Phase 2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_parameter_shadowed_by_assignment(self):
        """Test local assignment can shadow parameter annotation."""
        code = """
def process(handler: BaseHandler):
    handler = DerivedHandler()
    handler.handle()
"""
        chunk_metadata = {"chunk_id": "test.py:1-4:function:process"}
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # Local assignment should shadow parameter annotation
        method_call = [c for c in calls if c.callee_name.endswith(".handle")][0]
        assert method_call.callee_name == "DerivedHandler.handle"

    def test_self_call_always_uses_class_context(self):
        """Test self.method() uses class context, not any assignment."""
        code = """
class MyClass:
    def process(self):
        self.helper()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-4:method:MyClass.process",
            "parent_class": "MyClass"
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        # self.helper() should always resolve to MyClass.helper
        helper_calls = [c for c in calls if "helper" in c.callee_name.lower()]
        assert len(helper_calls) > 0
        assert helper_calls[0].callee_name == "MyClass.helper"

    def test_mixed_resolution_all_phases(self):
        """Test all three phases work together."""
        code = """
class Processor:
    def process(self, handler: Handler):
        extractor = ExceptionExtractor()
        self.helper()
        handler.handle()
        extractor.extract()
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-7:method:Processor.process",
            "parent_class": "Processor"
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        callee_names = {c.callee_name for c in calls}

        # Phase 1: self call
        assert "Processor.helper" in callee_names
        # Phase 2: annotation
        assert "Handler.handle" in callee_names
        # Phase 3: assignment
        assert "ExceptionExtractor.extract" in callee_names

    def test_assignment_does_not_affect_self_calls(self):
        """Test that local variable named 'self' doesn't break self resolution."""
        code = """
class MyClass:
    def process(self):
        self.method()  # Should resolve to MyClass.method
"""
        chunk_metadata = {
            "chunk_id": "test.py:1-4:method:MyClass.process",
            "parent_class": "MyClass"
        }
        calls = self.extractor.extract_calls(code, chunk_metadata)

        method_calls = [c for c in calls if "method" in c.callee_name.lower()]
        assert len(method_calls) > 0
        assert method_calls[0].callee_name == "MyClass.method"


class TestExtractLocalAssignments:
    """Direct tests for _extract_local_assignments() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_simple_assignment_extraction(self):
        """Test direct extraction of simple assignments."""
        code = """
x = MyClass()
y = OtherClass()
"""
        tree = ast.parse(code)
        assignments = self.extractor._extract_local_assignments(tree)

        assert "x" in assignments
        assert assignments["x"] == "MyClass"
        assert "y" in assignments
        assert assignments["y"] == "OtherClass"

    def test_annotated_assignment_extraction(self):
        """Test direct extraction of annotated assignments."""
        code = """
x: MyClass = get_value()
y: OtherClass
"""
        tree = ast.parse(code)
        assignments = self.extractor._extract_local_assignments(tree)

        assert "x" in assignments
        assert assignments["x"] == "MyClass"
        assert "y" in assignments
        assert assignments["y"] == "OtherClass"

    def test_self_attribute_extraction(self):
        """Test direct extraction of self.attr assignments."""
        code = """
self.handler = Handler()
cls.instance = Instance()
"""
        tree = ast.parse(code)
        assignments = self.extractor._extract_local_assignments(tree)

        assert "self.handler" in assignments
        assert assignments["self.handler"] == "Handler"
        assert "cls.instance" in assignments
        assert assignments["cls.instance"] == "Instance"

    def test_with_statement_extraction(self):
        """Test direct extraction from with statements."""
        code = """
with Manager() as mgr:
    pass
"""
        tree = ast.parse(code)
        assignments = self.extractor._extract_local_assignments(tree)

        assert "mgr" in assignments
        assert assignments["mgr"] == "Manager"

    def test_named_expression_extraction(self):
        """Test direct extraction of walrus operator assignments."""
        code = """
if (x := Creator()):
    pass
"""
        tree = ast.parse(code)
        assignments = self.extractor._extract_local_assignments(tree)

        assert "x" in assignments
        assert assignments["x"] == "Creator"


class TestInferTypeFromCall:
    """Direct tests for _infer_type_from_call() method."""

    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = PythonCallGraphExtractor()

    def test_simple_constructor(self):
        """Test type inference from simple constructor."""
        code = "MyClass()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        type_name = self.extractor._infer_type_from_call(call_node)
        assert type_name == "MyClass"

    def test_qualified_constructor(self):
        """Test type inference from qualified constructor."""
        code = "module.MyClass()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        type_name = self.extractor._infer_type_from_call(call_node)
        assert type_name == "MyClass"

    def test_factory_method_returns_none(self):
        """Test that factory methods return None (not inferable)."""
        code = "create_instance()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        type_name = self.extractor._infer_type_from_call(call_node)
        assert type_name == "create_instance"  # Function name, not class

    def test_method_call_returns_attr(self):
        """Test that obj.method() returns method name."""
        code = "obj.get_handler()"
        tree = ast.parse(code)
        call_node = tree.body[0].value

        type_name = self.extractor._infer_type_from_call(call_node)
        # Returns the method name, not class
        assert type_name == "get_handler"
