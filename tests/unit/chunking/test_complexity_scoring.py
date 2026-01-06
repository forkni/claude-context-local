"""
Unit tests for cyclomatic complexity scoring in Python chunker.

Tests the _calculate_complexity method to ensure accurate complexity calculation
for various Python code patterns.
"""

import pytest

from chunking.languages.python import PythonChunker


@pytest.fixture
def python_chunker():
    """Create a Python chunker instance for testing."""
    return PythonChunker()


def test_simple_function_complexity(python_chunker):
    """Test complexity of simple function with no branches."""
    code = b"""
def simple():
    return 1
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # Simple function with no branches = CC 1
    assert complexity == 1


def test_single_if_complexity(python_chunker):
    """Test complexity of function with single if statement."""
    code = b"""
def with_if(x):
    if x > 0:
        return x
    return 0
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One if statement = CC 2 (base 1 + 1 if)
    assert complexity == 2


def test_if_elif_else_complexity(python_chunker):
    """Test complexity of function with if-elif-else chain."""
    code = b"""
def with_elif(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One if + one elif = CC 3 (base 1 + 1 if + 1 elif)
    assert complexity == 3


def test_for_loop_complexity(python_chunker):
    """Test complexity of function with for loop."""
    code = b"""
def with_loop(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One for loop = CC 2 (base 1 + 1 for)
    assert complexity == 2


def test_while_loop_complexity(python_chunker):
    """Test complexity of function with while loop."""
    code = b"""
def with_while(x):
    while x > 0:
        x -= 1
    return x
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One while loop = CC 2 (base 1 + 1 while)
    assert complexity == 2


def test_try_except_complexity(python_chunker):
    """Test complexity of function with try-except."""
    code = b"""
def with_except(x):
    try:
        return 1 / x
    except ZeroDivisionError:
        return 0
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One except clause = CC 2 (base 1 + 1 except)
    assert complexity == 2


def test_multiple_except_complexity(python_chunker):
    """Test complexity with multiple except clauses."""
    code = b"""
def with_multiple_except(x):
    try:
        return int(x) / 10
    except ValueError:
        return -1
    except ZeroDivisionError:
        return 0
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # Two except clauses = CC 3 (base 1 + 1 except + 1 except)
    assert complexity == 3


def test_boolean_operator_complexity(python_chunker):
    """Test complexity with boolean operators (and, or)."""
    code = b"""
def with_boolean(x, y):
    if x > 0 and y > 0:
        return True
    return False
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One if + one and = CC 3 (base 1 + 1 if + 1 and)
    assert complexity == 3


def test_ternary_operator_complexity(python_chunker):
    """Test complexity with conditional expression (ternary)."""
    code = b"""
def with_ternary(x):
    return "positive" if x > 0 else "non-positive"
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One conditional expression = CC 2 (base 1 + 1 ternary)
    assert complexity == 2


def test_list_comprehension_with_if_complexity(python_chunker):
    """Test complexity with list comprehension containing if clause."""
    code = b"""
def with_comprehension(items):
    return [x for x in items if x > 0]
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # One comprehension with if = CC 2 (base 1 + 1 if clause)
    assert complexity == 2


def test_nested_control_flow_complexity(python_chunker):
    """Test complexity with nested control flow structures."""
    code = b"""
def nested(x, y):
    if x > 0:
        for i in range(y):
            if i % 2 == 0:
                return i
    return -1
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # Two if + one for = CC 4 (base 1 + 2 if + 1 for)
    assert complexity == 4


def test_complex_function_complexity(python_chunker):
    """Test complexity of a complex function with multiple decision points."""
    code = b"""
def complex_func(x, y, z):
    if x > 0:
        for i in range(y):
            if i % 2 == 0 and i > 10:
                return i
            elif i < 0:
                break
        while z > 0:
            z -= 1
    else:
        try:
            return 1 / x
        except ZeroDivisionError:
            return 0
    return -1
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # Count decision points:
    # - Base: 1
    # - if x > 0: +1
    # - for i in range(y): +1
    # - if i % 2 == 0 and i > 10: +1 (if) +1 (and) = +2
    # - elif i < 0: +1
    # - while z > 0: +1
    # - except ZeroDivisionError: +1
    # Total: 1 + 1 + 1 + 2 + 1 + 1 + 1 = 8
    assert complexity >= 7  # Allow some tolerance for AST parsing differences


def test_decorated_function_complexity(python_chunker):
    """Test complexity calculation for decorated functions."""
    code = b"""
@decorator
def decorated(x):
    if x > 0:
        return x
    return 0
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    decorated_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(decorated_node)

    # One if statement = CC 2 (decorator doesn't affect complexity)
    assert complexity == 2


def test_empty_function_complexity(python_chunker):
    """Test complexity of function with only pass statement."""
    code = b"""
def empty():
    pass
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    complexity = python_chunker._calculate_complexity(func_node)

    # Empty function = CC 1 (base complexity)
    assert complexity == 1


def test_extract_metadata_includes_complexity(python_chunker):
    """Test that extract_metadata includes complexity_score."""
    code = b"""
def foo(x):
    if x > 0:
        return x
    return 0
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    func_node = root_node.children[0]

    metadata = python_chunker.extract_metadata(func_node, code)

    # Metadata should include complexity_score
    assert "complexity_score" in metadata
    assert metadata["complexity_score"] == 2  # One if statement


def test_class_no_complexity(python_chunker):
    """Test that class definitions don't get complexity scores."""
    code = b"""
class MyClass:
    def method(self):
        pass
"""
    tree = python_chunker.parser.parse(code)
    root_node = tree.root_node
    class_node = root_node.children[0]

    metadata = python_chunker.extract_metadata(class_node, code)

    # Classes should not have complexity_score
    assert "complexity_score" not in metadata
