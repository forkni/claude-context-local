# Relationship Types Implementation Guide

## Overview

This document provides a comprehensive implementation plan for adding 4 new relationship types to the code search system. These additions will enhance `find_connections` with better code analysis capabilities.

**Target Version**: v0.5.11
**Estimated Time**: 16-22 hours total
**Status**: Planned (Phase 1 bug fix completed separately)

---

## Relationship Types to Implement

| Type | Forward Field | Reverse Field | Use Case |
|------|---------------|---------------|----------|
| `decorates` | `decorates` | `decorated_by` | Find decorator usage patterns |
| `raises` | `exceptions_raised` | `exception_handlers` | Error handling analysis |
| `catches` | `exceptions_caught` | - | Exception handling locations |
| `instantiates` | `instantiates` | `instantiated_by` | Find where classes are used |

---

## Current State

### Already Implemented (4/12)

- `calls` - direct/indirect callers ✅
- `inherits` - parent/child classes ✅
- `uses_type` - type annotations ✅
- `imports` - module imports ✅

### Enum Defined (All 12)

All relationship types are already defined in `graph/relationship_types.py` lines 38-62:

```python
class RelationshipType(Enum):
    CALLS = "calls"
    INHERITS = "inherits"
    USES_TYPE = "uses_type"
    IMPORTS = "imports"
    DECORATES = "decorates"
    RAISES = "raises"
    CATCHES = "catches"
    INSTANTIATES = "instantiates"
    IMPLEMENTS = "implements"
    OVERRIDES = "overrides"
    ASSIGNS_TO = "assigns_to"
    READS_FROM = "reads_from"
```

### Field Mapping Exists

`get_relationship_field_mapping()` in `graph/relationship_types.py` lines 376-389 already maps:

```python
{
    "decorates": ("decorates", "decorated_by"),
    "raises": ("exceptions_raised", "exception_handlers"),
    "catches": ("exceptions_caught", None),
    "instantiates": ("instantiates", "instantiated_by"),
}
```

---

## Implementation Tasks

### Task 1: Add ImpactReport Fields (1-2 hours)

**File**: `mcp_server/tools/code_relationship_analyzer.py`

#### 1a. Update ImpactReport Dataclass (lines 32-88)

Add 7 new fields after the existing relationship fields:

```python
@dataclass
class ImpactReport:
    # ... existing fields ...

    # Existing Phase 3 relationship fields
    parent_classes: List[Dict[str, Any]] = field(default_factory=list)
    child_classes: List[Dict[str, Any]] = field(default_factory=list)
    uses_types: List[Dict[str, Any]] = field(default_factory=list)
    used_as_type_in: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    imported_by: List[Dict[str, Any]] = field(default_factory=list)

    # NEW: Priority 2 relationship fields
    decorates: List[Dict[str, Any]] = field(default_factory=list)
    decorated_by: List[Dict[str, Any]] = field(default_factory=list)
    exceptions_raised: List[Dict[str, Any]] = field(default_factory=list)
    exception_handlers: List[Dict[str, Any]] = field(default_factory=list)
    exceptions_caught: List[Dict[str, Any]] = field(default_factory=list)
    instantiates: List[Dict[str, Any]] = field(default_factory=list)
    instantiated_by: List[Dict[str, Any]] = field(default_factory=list)

    stale_chunk_count: int = 0
```

#### 1b. Update to_dict() Method

Add new fields to the `to_dict()` method:

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        # ... existing fields ...
        "parent_classes": self.parent_classes,
        "child_classes": self.child_classes,
        "uses_types": self.uses_types,
        "used_as_type_in": self.used_as_type_in,
        "imports": self.imports,
        "imported_by": self.imported_by,
        # NEW fields
        "decorates": self.decorates,
        "decorated_by": self.decorated_by,
        "exceptions_raised": self.exceptions_raised,
        "exception_handlers": self.exception_handlers,
        "exceptions_caught": self.exceptions_caught,
        "instantiates": self.instantiates,
        "instantiated_by": self.instantiated_by,
        "stale_chunk_count": self.stale_chunk_count,
    }
```

#### 1c. Update analyze_impact() Return

Update the ImpactReport construction to include new fields from `graph_relationships`:

```python
return ImpactReport(
    # ... existing parameters ...
    decorates=graph_relationships.get("decorates", []),
    decorated_by=graph_relationships.get("decorated_by", []),
    exceptions_raised=graph_relationships.get("exceptions_raised", []),
    exception_handlers=graph_relationships.get("exception_handlers", []),
    exceptions_caught=graph_relationships.get("exceptions_caught", []),
    instantiates=graph_relationships.get("instantiates", []),
    instantiated_by=graph_relationships.get("instantiated_by", []),
    stale_chunk_count=stale_caller_count + stale_indirect_count,
)
```

---

### Task 2: DecoratorExtractor (3-4 hours)

**New File**: `graph/relationship_extractors/decorator_extractor.py`

#### AST Pattern

```python
@decorator_name          # ast.Name
@module.decorator        # ast.Attribute
@decorator(args)         # ast.Call
def func():
    pass
```

#### Implementation

```python
"""Extractor for decorator relationships."""
import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class DecoratorExtractor(BaseRelationshipExtractor):
    """Extracts decorator application relationships from Python code."""

    def __init__(self):
        super().__init__()
        self.relationship_type = RelationshipType.DECORATES

    def extract(self, code: str, chunk_metadata: Dict[str, Any]) -> List[RelationshipEdge]:
        """Extract decorator relationships from code.

        Args:
            code: Python source code
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of relationship edges for decorators
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self._extract_decorators(node, chunk_metadata)

        return self.edges

    def _extract_decorators(self, node, chunk_metadata: Dict[str, Any]):
        """Extract decorators from a function or class definition."""
        for decorator in node.decorator_list:
            decorator_name = self._get_decorator_name(decorator)
            if decorator_name:
                self._add_edge(
                    source_id=chunk_metadata.get("chunk_id", ""),
                    target_name=decorator_name,
                    line_number=decorator.lineno,
                    confidence=1.0,
                )

    def _get_decorator_name(self, decorator_node) -> str:
        """Get the full name of a decorator.

        Handles:
        - @decorator (ast.Name)
        - @module.decorator (ast.Attribute)
        - @decorator(args) (ast.Call)
        """
        if isinstance(decorator_node, ast.Name):
            return decorator_node.id
        elif isinstance(decorator_node, ast.Attribute):
            return self._get_full_attribute_name(decorator_node)
        elif isinstance(decorator_node, ast.Call):
            return self._get_decorator_name(decorator_node.func)
        return ""

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full dotted name from an Attribute node."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
```

---

### Task 3: ExceptionExtractor (4-5 hours)

**New File**: `graph/relationship_extractors/exception_extractor.py`

#### AST Patterns

```python
# raises: ast.Raise
raise ValueError("error")
raise CustomError()
raise  # bare raise

# catches: ast.Try -> ast.ExceptHandler
try:
    ...
except ValueError as e:
    ...
except (TypeError, KeyError):
    ...
except:  # bare except
    ...
```

#### Implementation

```python
"""Extractor for exception relationships (raises and catches)."""
import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class ExceptionExtractor(BaseRelationshipExtractor):
    """Extracts exception raising and catching relationships from Python code."""

    def __init__(self):
        super().__init__()
        # Will handle both RAISES and CATCHES
        self.relationship_type = None

    def extract(self, code: str, chunk_metadata: Dict[str, Any]) -> List[RelationshipEdge]:
        """Extract exception relationships from code.

        Args:
            code: Python source code
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of relationship edges for raises and catches
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                self._extract_raise(node, chunk_metadata)
            elif isinstance(node, ast.Try):
                self._extract_except_handlers(node, chunk_metadata)

        return self.edges

    def _extract_raise(self, node: ast.Raise, chunk_metadata: Dict[str, Any]):
        """Extract exception from a raise statement."""
        if node.exc is None:
            return  # bare raise

        exception_name = self._get_exception_name(node.exc)
        if exception_name:
            self.relationship_type = RelationshipType.RAISES
            self._add_edge(
                source_id=chunk_metadata.get("chunk_id", ""),
                target_name=exception_name,
                line_number=node.lineno,
                confidence=1.0,
            )

    def _extract_except_handlers(self, node: ast.Try, chunk_metadata: Dict[str, Any]):
        """Extract exceptions from except handlers."""
        for handler in node.handlers:
            if handler.type is None:
                continue  # bare except:

            exception_names = self._get_handler_exception_names(handler.type)
            for exc_name in exception_names:
                self.relationship_type = RelationshipType.CATCHES
                self._add_edge(
                    source_id=chunk_metadata.get("chunk_id", ""),
                    target_name=exc_name,
                    line_number=handler.lineno,
                    confidence=1.0,
                )

    def _get_exception_name(self, exc_node) -> str:
        """Get the name of a raised exception.

        Handles:
        - raise ValueError (ast.Name)
        - raise ValueError() (ast.Call)
        - raise module.Error (ast.Attribute)
        """
        if isinstance(exc_node, ast.Name):
            return exc_node.id
        elif isinstance(exc_node, ast.Call):
            return self._get_exception_name(exc_node.func)
        elif isinstance(exc_node, ast.Attribute):
            return self._get_full_attribute_name(exc_node)
        return ""

    def _get_handler_exception_names(self, type_node) -> List[str]:
        """Get exception names from an except handler.

        Handles:
        - except Error (ast.Name)
        - except (Error1, Error2) (ast.Tuple)
        - except module.Error (ast.Attribute)
        """
        if isinstance(type_node, ast.Name):
            return [type_node.id]
        elif isinstance(type_node, ast.Tuple):
            names = []
            for elt in type_node.elts:
                if isinstance(elt, ast.Name):
                    names.append(elt.id)
                elif isinstance(elt, ast.Attribute):
                    names.append(self._get_full_attribute_name(elt))
            return names
        elif isinstance(type_node, ast.Attribute):
            return [self._get_full_attribute_name(type_node)]
        return []

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full dotted name from an Attribute node."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
```

---

### Task 4: InstantiationExtractor (3-4 hours)

**New File**: `graph/relationship_extractors/instantiation_extractor.py`

#### AST Pattern

```python
# ast.Call where func is a class name
obj = MyClass()
result = SomeFactory.create()
data = module.DataClass(arg)
```

#### Implementation

```python
"""Extractor for class instantiation relationships."""
import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class InstantiationExtractor(BaseRelationshipExtractor):
    """Extracts class instantiation relationships from Python code."""

    def __init__(self):
        super().__init__()
        self.relationship_type = RelationshipType.INSTANTIATES

    def extract(self, code: str, chunk_metadata: Dict[str, Any]) -> List[RelationshipEdge]:
        """Extract instantiation relationships from code.

        Args:
            code: Python source code
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of relationship edges for instantiations
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._extract_instantiation(node, chunk_metadata)

        return self.edges

    def _extract_instantiation(self, node: ast.Call, chunk_metadata: Dict[str, Any]):
        """Extract class instantiation from a Call node.

        Uses heuristic: class names start with uppercase letter.
        """
        call_name = self._get_call_name(node.func)
        if not call_name:
            return

        # Heuristic: Class names start with uppercase
        # Extract just the final name for checking
        final_name = call_name.split(".")[-1]

        # Skip if it's all uppercase (likely a constant like LOGGER())
        # Skip if it doesn't start with uppercase (likely a function)
        if final_name and final_name[0].isupper() and not final_name.isupper():
            self._add_edge(
                source_id=chunk_metadata.get("chunk_id", ""),
                target_name=call_name,
                line_number=node.lineno,
                confidence=0.8,  # Lower confidence due to heuristic
            )

    def _get_call_name(self, func_node) -> str:
        """Get the name of the called function/class.

        Handles:
        - MyClass() (ast.Name)
        - module.MyClass() (ast.Attribute)
        """
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return self._get_full_attribute_name(func_node)
        return ""

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """Get the full dotted name from an Attribute node."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))
```

---

### Task 5: Integration (2-3 hours)

#### 5a. Update **init**.py Exports

**File**: `graph/relationship_extractors/__init__.py`

```python
from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_extractors.inheritance_extractor import InheritanceExtractor
from graph.relationship_extractors.type_extractor import TypeAnnotationExtractor
from graph.relationship_extractors.import_extractor import ImportExtractor
from graph.relationship_extractors.decorator_extractor import DecoratorExtractor
from graph.relationship_extractors.exception_extractor import ExceptionExtractor
from graph.relationship_extractors.instantiation_extractor import InstantiationExtractor

__all__ = [
    "BaseRelationshipExtractor",
    "InheritanceExtractor",
    "TypeAnnotationExtractor",
    "ImportExtractor",
    "DecoratorExtractor",
    "ExceptionExtractor",
    "InstantiationExtractor",
]
```

#### 5b. Register Extractors in Chunking Pipeline

The extractors need to be called during indexing. Check existing extractor integration in:

- `chunking/multi_language_chunker.py`
- `search/indexer.py` - `_add_to_graph()` method

Follow the pattern used by existing extractors (InheritanceExtractor, TypeAnnotationExtractor, ImportExtractor).

#### 5c. No Changes Needed

- `_extract_relationships()` in `code_relationship_analyzer.py` already handles the field mapping dynamically
- Field mapping already exists in `relationship_types.py`

---

### Task 6: Testing (4-5 hours)

#### 6a. Unit Tests for Each Extractor

**Location**: `tests/unit/test_relationship_extractors/`

Create test files:

- `test_decorator_extractor.py`
- `test_exception_extractor.py`
- `test_instantiation_extractor.py`

**Test Cases**:

```python
# test_decorator_extractor.py
def test_simple_decorator():
    code = '''
@decorator
def func():
    pass
'''
    # Assert edge: func -> decorator (decorated_by)

def test_decorator_with_module():
    code = '''
@module.decorator
def func():
    pass
'''
    # Assert edge target is "module.decorator"

def test_decorator_with_args():
    code = '''
@decorator(arg=value)
def func():
    pass
'''
    # Assert edge target is "decorator"

def test_class_decorator():
    code = '''
@dataclass
class MyClass:
    pass
'''
    # Assert edge: MyClass -> dataclass
```

```python
# test_exception_extractor.py
def test_raise_simple():
    code = '''
raise ValueError("error")
'''
    # Assert edge type is RAISES, target is "ValueError"

def test_raise_with_module():
    code = '''
raise custom.CustomError()
'''
    # Assert target is "custom.CustomError"

def test_catch_single():
    code = '''
try:
    pass
except ValueError:
    pass
'''
    # Assert edge type is CATCHES, target is "ValueError"

def test_catch_multiple():
    code = '''
try:
    pass
except (TypeError, KeyError):
    pass
'''
    # Assert two edges: TypeError, KeyError
```

```python
# test_instantiation_extractor.py
def test_simple_instantiation():
    code = '''
obj = MyClass()
'''
    # Assert edge target is "MyClass"

def test_module_instantiation():
    code = '''
obj = module.MyClass()
'''
    # Assert target is "module.MyClass"

def test_lowercase_not_captured():
    code = '''
result = my_function()
'''
    # Assert no edges (lowercase = function call)

def test_all_caps_not_captured():
    code = '''
LOGGER()
'''
    # Assert no edges (all caps = constant)
```

#### 6b. Integration Test

**File**: `tests/integration/test_relationship_types.py`

```python
def test_find_connections_with_decorators():
    """Test find_connections returns decorator relationships."""
    # Index a project with decorated functions
    # Call find_connections on a decorated function
    # Assert decorated_by field contains the decorator

def test_find_connections_with_exceptions():
    """Test find_connections returns exception relationships."""
    # Index a project with try/except blocks
    # Call find_connections on a function that raises
    # Assert exceptions_raised field contains the exception
    # Assert exception_handlers shows where it's caught

def test_find_connections_with_instantiation():
    """Test find_connections returns instantiation relationships."""
    # Index a project with class instantiations
    # Call find_connections on a class
    # Assert instantiated_by field shows where it's used
```

---

## Implementation Order

1. **Task 1**: Add ImpactReport fields (prerequisite)
2. **Task 2**: DecoratorExtractor (simplest, validates workflow)
3. **Task 3**: ExceptionExtractor (raises + catches together)
4. **Task 4**: InstantiationExtractor (last extractor)
5. **Task 5**: Integration (export and register)
6. **Task 6**: Testing

---

## Commit Strategy

- Single commit for all relationship types
- Version bump to 0.5.11
- Message: `feat: Add decorator/exception/instantiation relationship tracking (v0.5.11)`

---

## Notes

### BaseRelationshipExtractor Methods

Reference existing extractors for the base class interface:

```python
class BaseRelationshipExtractor:
    def __init__(self):
        self.edges = []
        self.relationship_type = None

    def _reset_state(self):
        self.edges = []

    def _add_edge(self, source_id, target_name, line_number, confidence=1.0):
        edge = RelationshipEdge(
            source_id=source_id,
            target_name=target_name,
            relationship_type=self.relationship_type,
            line_number=line_number,
            confidence=confidence,
        )
        self.edges.append(edge)

    def extract(self, code, chunk_metadata) -> List[RelationshipEdge]:
        raise NotImplementedError
```

### Edge Direction Convention

- **Source**: The code chunk that has the relationship
- **Target**: The name being referenced

For `decorates`:

- Source: The decorated function's chunk_id
- Target: The decorator name
- Query result: Function shows in `decorated_by` for the decorator

For `raises`:

- Source: The function that raises
- Target: The exception class name
- Query result: Function shows in `exception_handlers` when querying the exception

For `instantiates`:

- Source: The code that instantiates
- Target: The class name
- Query result: Code shows in `instantiated_by` when querying the class

---

## Future Enhancements

### Not Implemented (Lower Priority)

- `implements` - Protocol/ABC implementation
- `overrides` - Method overriding
- `assigns_to` - Attribute assignment
- `reads_from` - Attribute access

These can be added later following the same pattern.

---

## References

- `graph/relationship_types.py` - RelationshipType enum and field mapping
- `graph/relationship_extractors/inheritance_extractor.py` - Reference implementation
- `mcp_server/tools/code_relationship_analyzer.py` - ImpactReport and analyze_impact()
- `docs/ADVANCED_FEATURES_GUIDE.md` - Feature documentation
