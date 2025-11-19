# Call Graph Resolution Implementation Plan

## Executive Summary

### Problem Statement

The current call graph implementation stores edges as `caller_chunk_id → bare_method_name`, causing false positives when querying callers. For example, querying callers of `ExceptionExtractor.extract` returns all callers of ANY method named `extract` across different classes.

### Solution Overview

Transform the call graph to store `chunk_id → chunk_id` edges with multi-source type resolution, achieving ~90% accuracy for method call resolution.

### Expected Outcomes

- **Before**: 67 false positive direct_callers for `ExceptionExtractor.extract`
- **After**: ~5-10 accurate direct_callers (actual tests that call this specific method)
- **Coverage**: ~90% of method calls correctly resolved

---

## Current Architecture Analysis

### Data Flow

```
1. Chunking → 2. Call Extraction → 3. Graph Storage → 4. Query
```

### Current Implementation

#### 1. Call Extraction (`graph/call_graph_extractor.py`)

```python
# Line 181-184: _get_call_name()
elif isinstance(func_node, ast.Attribute):
    return func_node.attr  # Returns "extract", not "Class.extract"
```

**Issue**: Only bare method name is captured.

#### 2. Graph Storage (`graph/graph_storage.py`)

```python
# Line 97-124: add_call_edge()
self.graph.add_edge(
    caller_id,      # "tests/test.py:50-80:function:test_foo"
    callee_name,    # "extract" (bare name)
    type="calls"
)
```

**Issue**: Target is bare name, creating ambiguous shared nodes.

#### 3. Query (`mcp_server/tools/code_relationship_analyzer.py`)

```python
# Line 335-348: analyze_impact()
symbol_name = target_id.split(":")[-1]  # Extracts "extract"
callers = self.graph.get_callers(symbol_name)  # Returns ALL "extract" callers
```

**Issue**: Query by bare name returns all methods with same name.

### Current Graph Structure

```
Graph Nodes:
  - chunk_ids (full paths)
  - symbol_names (bare names like "extract")

Graph Edges:
  caller_chunk_id → "extract" (bare name)
  caller_chunk_id → "extract" (bare name)  # Different class, same edge target!
```

---

## Target Architecture

### New Data Model

```
Graph Edges:
  caller_chunk_id → callee_chunk_id (when resolvable)
  caller_chunk_id → "bare_name" (fallback only)

Example:
  tests/test_exception.py:50-80:function:test_extract
    → graph/extractors/exception_extractor.py:92-148:method:ExceptionExtractor.extract
```

### Resolution Priority

1. **Self/super calls** (100% accurate)
2. **Type annotations** (95% accurate)
3. **Assignment tracking** (90% accurate)
4. **Import resolution** (95% accurate)
5. **Bare name fallback** (ambiguous)

---

## Implementation Phases

### Phase 1: Self/Super Calls + Qualified Chunk IDs

**Coverage**: ~70% of method calls
**Effort**: 1-2 days

#### 1.1 Modify Chunk ID Format for Methods

**File**: `chunking/tree_sitter.py`

Add parent class tracking to `TreeSitterChunk`:

```python
@dataclass
class TreeSitterChunk:
    # ... existing fields ...
    parent_class: Optional[str] = None  # NEW: Enclosing class name
```

**File**: `chunking/multi_language_chunker.py`

Modify `_convert_tree_chunks()` to build qualified names:

```python
# Current (line ~370):
name=chunk.name

# New:
name = f"{chunk.parent_class}.{chunk.name}" if chunk.parent_class else chunk.name
```

**Resulting chunk_id format**:
- Before: `file.py:1-20:method:extract`
- After: `file.py:1-20:method:ExceptionExtractor.extract`

#### 1.2 Track Parent Class During Tree-sitter Parsing

**File**: `chunking/tree_sitter.py`

Modify chunking to track enclosing class:

```python
def _extract_chunks(self, node, ...):
    # Track class context
    if node.type == 'class_definition':
        class_name = self._get_class_name(node)
        for child in node.children:
            if child.type == 'block':
                self._extract_chunks(child, parent_class=class_name, ...)

    # Use class context for methods
    if node.type in ('function_definition', 'method'):
        chunk = TreeSitterChunk(
            name=func_name,
            parent_class=parent_class,  # NEW
            ...
        )
```

#### 1.3 Resolve Self Calls to Qualified Names

**File**: `graph/call_graph_extractor.py`

Modify `_get_call_name()` to handle self calls:

```python
def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
    if isinstance(func_node, ast.Attribute):
        receiver = func_node.value
        method_name = func_node.attr

        # Self call - use enclosing class context
        if isinstance(receiver, ast.Name) and receiver.id in ('self', 'cls'):
            if self._current_class:
                return f"{self._current_class}.{method_name}"

        # Super call - resolve to parent class
        if isinstance(receiver, ast.Call):
            if isinstance(receiver.func, ast.Name) and receiver.func.id == 'super':
                parent_class = self._get_parent_class(self._current_class)
                if parent_class:
                    return f"{parent_class}.{method_name}"

        return method_name  # Fallback to bare name
```

Add class context tracking:

```python
def _extract_calls(self, node: ast.AST) -> List[CallInfo]:
    if isinstance(node, ast.ClassDef):
        self._current_class = node.name
        # ... process class body ...
        self._current_class = None
```

#### 1.4 Store Resolved Callee Chunk IDs

**File**: `graph/graph_storage.py`

Modify `add_call_edge()` to accept chunk_id or qualified name:

```python
def add_call_edge(
    self,
    caller_id: str,
    callee: str,  # Can be chunk_id or qualified name
    line_number: int = 0,
    is_resolved: bool = False,  # NEW: indicates if callee is chunk_id
    **kwargs,
) -> None:
    edge_attrs = {
        "type": "calls",
        "line": line_number,
        "is_resolved": is_resolved,
    }
    self.graph.add_edge(caller_id, callee, **edge_attrs)
```

#### 1.5 Update Query Logic

**File**: `mcp_server/tools/code_relationship_analyzer.py`

Modify `analyze_impact()` to handle resolved edges:

```python
def _get_direct_callers(self, target_id: str) -> List[str]:
    """Get callers, preferring resolved chunk_id edges."""

    # Extract qualified name from chunk_id
    # e.g., "file:lines:method:Class.method" → "Class.method"
    qualified_name = target_id.split(":")[-1]

    # Query by chunk_id first (resolved edges)
    callers_by_id = self.graph.get_callers(target_id)

    # Query by qualified name (for older edges)
    callers_by_name = self.graph.get_callers(qualified_name)

    # Combine and deduplicate
    return list(set(callers_by_id + callers_by_name))
```

---

### Phase 2: Type Annotation Resolution

**Coverage**: +10% (cumulative ~80%)
**Effort**: 1 day

#### 2.1 Extract Type Annotations

**File**: `graph/call_graph_extractor.py`

Add type annotation extraction:

```python
def _extract_type_annotations(self, func_node: ast.FunctionDef) -> Dict[str, str]:
    """Extract parameter and return type annotations."""
    annotations = {}

    for arg in func_node.args.args:
        if arg.annotation:
            param_name = arg.arg
            type_name = self._annotation_to_string(arg.annotation)
            annotations[param_name] = type_name

    return annotations

def _annotation_to_string(self, annotation: ast.AST) -> str:
    """Convert annotation AST to string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Attribute):
        return f"{self._get_full_attr(annotation)}"
    # Handle Optional, List, etc.
    return ""
```

#### 2.2 Resolve Calls Using Type Context

```python
def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
    if isinstance(func_node, ast.Attribute):
        receiver = func_node.value
        method_name = func_node.attr

        # Check if receiver has type annotation
        if isinstance(receiver, ast.Name):
            var_name = receiver.id
            if var_name in self._type_annotations:
                type_name = self._type_annotations[var_name]
                return f"{type_name}.{method_name}"

        # ... existing self/super handling ...
```

---

### Phase 3: Assignment Tracking

**Coverage**: +5-10% (cumulative ~85-90%)
**Effort**: 1-2 days

#### 3.1 Track Variable Assignments

**File**: `graph/call_graph_extractor.py`

Add assignment tracking:

```python
def _track_assignments(self, node: ast.AST):
    """Track variable assignments for type inference."""
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                assigned_type = self._infer_type(node.value)
                if assigned_type:
                    self._variable_types[var_name] = assigned_type

def _infer_type(self, value: ast.AST) -> Optional[str]:
    """Infer type from assignment value."""
    # Direct instantiation: x = MyClass()
    if isinstance(value, ast.Call):
        if isinstance(value.func, ast.Name):
            return value.func.id
        elif isinstance(value.func, ast.Attribute):
            return self._get_full_attr(value.func)

    # Factory methods, etc. - return None
    return None
```

#### 3.2 Use Tracked Types in Resolution

```python
def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
    if isinstance(func_node, ast.Attribute):
        receiver = func_node.value
        method_name = func_node.attr

        if isinstance(receiver, ast.Name):
            var_name = receiver.id

            # Priority 1: Type annotations
            if var_name in self._type_annotations:
                return f"{self._type_annotations[var_name]}.{method_name}"

            # Priority 2: Assignment tracking
            if var_name in self._variable_types:
                return f"{self._variable_types[var_name]}.{method_name}"

        # ... existing handling ...
```

---

### Phase 4: Import-Based Resolution

**Coverage**: +3-5% (cumulative ~90%)
**Effort**: 0.5 days

#### 4.1 Track Imports

**File**: `graph/call_graph_extractor.py`

```python
def _extract_imports(self, tree: ast.AST) -> Dict[str, str]:
    """Extract import mappings."""
    imports = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = alias.name

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = f"{module}.{alias.name}"

    return imports
```

#### 4.2 Resolve Imported Calls

```python
def _get_call_name(self, func_node: ast.AST) -> Optional[str]:
    # Direct function call
    if isinstance(func_node, ast.Name):
        func_name = func_node.id

        # Resolve import
        if func_name in self._imports:
            return self._imports[func_name]

        return func_name

    # ... attribute handling ...
```

---

## File-by-File Changes Summary

| File | Changes | Phase |
|------|---------|-------|
| `chunking/tree_sitter.py` | Add `parent_class` field, track during parsing | 1 |
| `chunking/multi_language_chunker.py` | Build qualified chunk_id names | 1 |
| `graph/call_graph_extractor.py` | Type resolution, assignment tracking, imports | 1-4 |
| `graph/graph_storage.py` | Support resolved chunk_id edges | 1 |
| `mcp_server/tools/code_relationship_analyzer.py` | Query by qualified name | 1 |
| `embeddings/embedder.py` | Use qualified names in metadata | 1 |

---

## Data Migration Strategy

### Backward Compatibility

1. **Graph edges**: Support both old (bare name) and new (qualified) formats
2. **Queries**: Try qualified name first, fall back to bare name
3. **Chunk IDs**: Old format still works, new format preferred

### Migration Path

```python
# Query logic handles both formats
def get_callers(self, target):
    # New format: qualified name
    callers = self._query_by_qualified_name(target)

    # Old format: bare name (for backward compatibility)
    if not callers:
        bare_name = target.split(".")[-1]
        callers = self._query_by_bare_name(bare_name)

    return callers
```

### Re-indexing Requirement

- **Phase 1**: Requires full re-index to generate qualified chunk_ids
- **Phases 2-4**: Can work incrementally on new indexes

---

## Testing Strategy

### Unit Tests

#### Phase 1 Tests

```python
def test_qualified_chunk_id_generation():
    """Test chunk_id includes class name for methods."""
    code = '''
class MyClass:
    def my_method(self):
        pass
    '''
    chunks = chunker.chunk_code(code, "test.py")
    method_chunk = [c for c in chunks if c.name == "MyClass.my_method"][0]
    assert "method:MyClass.my_method" in method_chunk.chunk_id

def test_self_call_resolution():
    """Test self.method() resolves to Class.method."""
    code = '''
class MyClass:
    def caller(self):
        self.callee()

    def callee(self):
        pass
    '''
    calls = extractor.extract_calls(code)
    assert calls[0].callee_name == "MyClass.callee"

def test_super_call_resolution():
    """Test super().method() resolves to Parent.method."""
    # ...
```

#### Phase 2 Tests

```python
def test_type_annotation_resolution():
    """Test type-annotated parameters resolve correctly."""
    code = '''
def process(extractor: ExceptionExtractor):
    extractor.extract()
    '''
    calls = extractor.extract_calls(code)
    assert calls[0].callee_name == "ExceptionExtractor.extract"
```

#### Phase 3 Tests

```python
def test_assignment_tracking():
    """Test variable assignments track types."""
    code = '''
def process():
    extractor = ExceptionExtractor()
    extractor.extract()
    '''
    calls = extractor.extract_calls(code)
    assert calls[0].callee_name == "ExceptionExtractor.extract"
```

### Integration Tests

```python
def test_find_connections_no_false_positives():
    """Test find_connections returns only actual callers."""
    # Index project with multiple extractors
    # Query ExceptionExtractor.extract
    # Verify only exception-related tests returned
    result = find_connections("...exception_extractor.py:...:method:ExceptionExtractor.extract")

    for caller in result["direct_callers"]:
        assert "exception" in caller["chunk_id"].lower() or \
               caller["file"].endswith("multi_language_chunker.py")
```

---

## Timeline and Effort Estimates

| Phase | Description | Effort | Cumulative Coverage |
|-------|-------------|--------|---------------------|
| 1 | Self/super + qualified chunk_ids | 1-2 days | ~70% |
| 2 | Type annotation resolution | 1 day | ~80% |
| 3 | Assignment tracking | 1-2 days | ~85-90% |
| 4 | Import-based resolution | 0.5 days | ~90% |
| - | Testing & documentation | 1 day | - |

**Total**: 4.5-6.5 days

---

## Version Planning

### v0.5.12: Phase 1 (Foundation)

- Qualified chunk_ids
- Self/super call resolution
- Breaking change: requires re-indexing
- Coverage: ~70%

### v0.5.13: Phases 2-4 (Enhancement)

- Type annotations
- Assignment tracking
- Import resolution
- Incremental improvement
- Coverage: ~90%

---

## Risk Assessment

### Technical Risks

| Risk | Mitigation |
|------|------------|
| Complex AST traversal | Use existing patterns from relationship extractors |
| Backward compatibility | Support both old and new formats during transition |
| Performance impact | Resolution happens at index time, not query time |

### Limitations

- Duck-typed code without annotations: ~10% unresolvable
- Dynamic method calls (`getattr`): Not resolvable
- External libraries: May fall back to bare names

---

## Success Criteria

1. **Accuracy**: find_connections returns <10% false positives (vs current ~90%)
2. **Coverage**: 90%+ of method calls correctly resolved
3. **Performance**: No regression in query time
4. **Compatibility**: Old indexes continue to work (with lower accuracy)

---

## Next Steps

1. **Commit v0.5.11** - Priority 2 relationships + path normalization
2. **Implement Phase 1** - Foundation for qualified resolution
3. **Test thoroughly** - Unit + integration tests
4. **Iterate** - Phases 2-4 based on real-world accuracy metrics

---

## References

- Current call graph extractor: `graph/call_graph_extractor.py`
- Graph storage: `graph/graph_storage.py`
- Relationship analyzer: `mcp_server/tools/code_relationship_analyzer.py`
- Tree-sitter chunker: `chunking/tree_sitter.py`
