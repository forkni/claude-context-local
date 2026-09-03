"""Characterization tests pinning the in-progress C-family call-graph build-out.

`CppChunker.extract_metadata`/`CChunker.extract_metadata` (chunking/languages/cpp.py,
c.py) now walk `call_expression` nodes via `extract_call_sites`
(chunking/languages/_c_family.py) and `EDGE_EMISSION_SPECS` (chunking/relationships/
edge_specs.py) carries `"cpp"`/`"c"` rows, so `chunk.calls` is populated for `cpp`/`c`
function/method chunks. The walk's dispatch table now covers all four `function`-field
shapes the plan's dispatch table names: plain `identifier`, `field_expression` (method
calls, `obj.m()`/`this->m()` -- `is_method_call=True`), `qualified_identifier`
(`Foo::bar(...)`, `callee_qualified` set to the full text), and `template_function`
(`clamp<int>(...)`). `std::`-/`::std::`-qualified calls (`std::sort(...)`) are filtered
at chunk time (`_is_std_qualified`) -- the only project-context-free noise rule; a
static STL member-name blocklist for bare method calls like `.size()` needs "does the
project define its own?" context this per-file walk doesn't have, so that's Wall-2
scope (`search/graph_integration.py`'s future `_C_FAMILY_COMMON_MEMBERS`), not here --
which is why `Derived::greet`'s `items.begin()`/`items.end()` (STL container method
calls, syntactically identical to a project-defined method) still appear below.
`metadata["relationships"]` now carries IMPORTS (`#include`), INHERITS (`base_class_clause`),
and INSTANTIATES (`new_expression`) edges (`extract_include_metadata`,
`extract_inheritance_relationships`, `extract_instantiation_relationships` in
`chunking/languages/_c_family.py`), materialized via the same `EDGE_EMISSION_SPECS`/
`materialize_relationship_edges` seam GLSL's relationships flow through (see
`test_glsl_relationships.py`, whose `_rels` helper and per-edge assertion style this file
mirrors) -- so `chunk.relationships` is non-`None` for any C-family chunk carrying at least
one such edge. Chunks with no relationship of any kind (e.g. `helper_fn`, free functions with
no `new`) still have `chunk.relationships is None`, per
`materialize_relationship_edges`'s "empty list stays unassigned" contract.

`preproc_include` was also added to `LANGUAGE_SPECS["c"]`/`["cpp"]`'s `splittable_node_types`
(chunking/language_registry.py), matching GLSL's existing entry -- so `#include` lines now get
their own dedicated `chunk_type == "include"` chunk, the same as GLSL, instead of producing no
chunk at all.

This file pins the full Wall-1 walk's target shapes -- plain calls, method calls
(`->`/`this->`), `std::`-qualified calls, qualified non-`std::` calls, template calls,
inheritance, `new`, and `#include` -- with real C++/C source, so each commit in this build
showed a concrete before/after diff in this same file.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.relationships.relationship_types import RelationshipType


# Fixture exercising every call/relationship shape the future Wall-1 walk targets:
# plain call, `this->` method call, `std::`-qualified call, `#include`, inheritance, `new`.
_CPP_FIXTURE_SOURCE = """\
#include "helper.hpp"
#include <vector>
#include <algorithm>

class Base {
public:
    virtual void greet();
};

class Derived : public Base {
public:
    void greet() override {
        helper_fn(1, 2);
        this->log("hi");
        std::sort(items.begin(), items.end());
        auto* b = new Base();
    }

    void log(const char* msg);

private:
    std::vector<int> items;
};

void helper_fn(int a, int b) {
    printf("%d %d", a, b);
}

template <typename T>
T identity(T value) {
    helper_fn(1, 2);
    return value;
}

namespace ns {
void helper2(int x);
}

void mixed_dispatch_calls() {
    ns::helper2(5);
    identity<int>(5);
}
"""

# C-only call shapes: plain calls, `#include`, no methods/templates/`::`.
_C_FIXTURE_SOURCE = """\
#include "helper.h"

int helper_fn(int a, int b) {
    return a + b;
}

int main(void) {
    int result = helper_fn(1, 2);
    printf("%d", result);
    return result;
}
"""


@pytest.fixture
def cpp_chunks(tmp_path: Path):
    """Chunk `_CPP_FIXTURE_SOURCE` through the real MultiLanguageChunker -> CppChunker path."""
    file_path = tmp_path / "fixture.cpp"
    file_path.write_text(_CPP_FIXTURE_SOURCE, encoding="utf-8")

    chunker = MultiLanguageChunker(root_path=str(tmp_path))
    return chunker.chunk_file(str(file_path))


@pytest.fixture
def c_chunks(tmp_path: Path):
    """Chunk `_C_FIXTURE_SOURCE` through the real MultiLanguageChunker -> CChunker path."""
    file_path = tmp_path / "fixture.c"
    file_path.write_text(_C_FIXTURE_SOURCE, encoding="utf-8")

    chunker = MultiLanguageChunker(root_path=str(tmp_path))
    return chunker.chunk_file(str(file_path))


def _chunk(chunks, name: str, parent_name: str | None = None):
    """Find a chunk by `.name`, disambiguating same-named members (e.g. two
    classes each declaring a `greet` method) by `.parent_name`. `chunk.name`
    is the bare identifier -- the `Parent.name` qualified form only appears in
    the chunk_id, not here."""
    for c in chunks:
        if c.name == name and (parent_name is None or c.parent_name == parent_name):
            return c
    raise AssertionError(f"no chunk named {name!r} (parent_name={parent_name!r})")


def _rels(chunk, rel_type: RelationshipType):
    """Filter `chunk.relationships` to one edge type. Mirrors `test_glsl_relationships.py`."""
    return [r for r in (chunk.relationships or []) if r.relationship_type == rel_type]


# ===== C++ baseline =====


def test_cpp_function_with_plain_call_emits_calls(cpp_chunks):
    """`helper_fn` (free function, plain-identifier call site `printf(...)`) -- one call."""
    chunk = _chunk(cpp_chunks, "helper_fn")
    assert chunk.chunk_type == "function"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("printf", False, None)]
    assert not chunk.relationships


def test_cpp_method_with_mixed_call_shapes_emits_calls_and_filters_std(cpp_chunks):
    """`Derived::greet` exercises plain/`this->`/`std::`-qualified calls + `new`.

    `helper_fn(1, 2)` (plain) and `this->log("hi")` (`field_expression`, method call)
    are both recognized. `std::sort(...)` (`qualified_identifier`) is dropped by the
    `std::`-prefix noise filter -- but its own arguments, `items.begin()`/`items.end()`,
    are themselves separate `field_expression` call sites on `items` and are recognized
    as (unfiltered) method calls, per this file's module docstring. `new Base()` is a
    `new_expression`, not a `call_expression`, so it never reaches `chunk.calls` at all --
    it becomes the method's one INSTANTIATES relationship instead, asserted below.
    """
    chunk = _chunk(cpp_chunks, "greet", parent_name="Derived")
    assert chunk.chunk_type == "method"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [
        ("helper_fn", False, None),
        ("log", True, None),
        ("end", True, None),
        ("begin", True, None),
    ]
    edges = _rels(chunk, RelationshipType.INSTANTIATES)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Base"
    assert edge.line_number == 16
    assert edge.metadata == {}


def test_cpp_templated_function_emits_calls(cpp_chunks):
    """`identity<T>` chunks as `template_declaration`, not `function_definition` --
    `CppChunker.extract_metadata`'s `template_declaration` branch must propagate the
    inner `function_definition`'s `metadata["calls"]` up to the template chunk itself
    for this to be non-empty."""
    chunk = _chunk(cpp_chunks, "identity")
    assert chunk.chunk_type == "template"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("helper_fn", False, None)]


def test_cpp_function_with_qualified_and_template_calls_emits_calls(cpp_chunks):
    """`mixed_dispatch_calls` exercises non-`std::`-qualified and bare template calls.

    `ns::helper2(5)` (`qualified_identifier`, not `std::`-prefixed) is recognized with
    `callee_qualified` set to the full `"ns::helper2"` text. `identity<int>(5)` (a bare
    `template_function`, not qualified) is recognized via the same name-peeling
    `_leaf_call_name` helper the `qualified_identifier` row uses for
    `std::max<int>(...)`-shaped nesting.
    """
    chunk = _chunk(cpp_chunks, "mixed_dispatch_calls")
    assert chunk.chunk_type == "function"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [
        ("helper2", False, "ns::helper2"),
        ("identity", False, None),
    ]
    assert not chunk.relationships


def test_cpp_class_with_inheritance_emits_inherits_relationship(cpp_chunks):
    """`class Derived : public Base` -> one INHERITS edge, tagged with its access specifier."""
    chunk = _chunk(cpp_chunks, "Derived")
    edges = _rels(chunk, RelationshipType.INHERITS)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Base"
    assert edge.line_number == 10
    assert edge.metadata == {"access": "public"}


def test_cpp_quoted_include_emits_include_chunk_and_imports_edge(cpp_chunks):
    """`#include "helper.hpp"` -> its own "include"-typed chunk with a self-referential
    IMPORTS edge, mirroring `test_glsl_relationships.py`'s
    `test_include_produces_imports_edge`."""
    chunk = _chunk(cpp_chunks, "helper.hpp")
    assert chunk.chunk_type == "include"
    edges = _rels(chunk, RelationshipType.IMPORTS)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "helper.hpp"
    assert edge.line_number == 1
    assert edge.metadata == {"is_system_include": False}
    assert edge.source_id == chunk.chunk_id


def test_cpp_system_includes_emit_include_chunks_and_imports_edges(cpp_chunks):
    """`#include <vector>` / `#include <algorithm>` -> "include" chunks tagged
    `is_system_include=True`, distinguishing `<...>` from `"..."` includes."""
    vector_chunk = _chunk(cpp_chunks, "vector")
    algorithm_chunk = _chunk(cpp_chunks, "algorithm")
    for chunk, expected_line in ((vector_chunk, 2), (algorithm_chunk, 3)):
        assert chunk.chunk_type == "include"
        edges = _rels(chunk, RelationshipType.IMPORTS)
        assert len(edges) == 1
        edge = edges[0]
        assert edge.target_name == chunk.name
        assert edge.line_number == expected_line
        assert edge.metadata == {"is_system_include": True}


# ===== C baseline =====


def test_c_function_with_call_emits_calls(c_chunks):
    """`main` calls `helper_fn` and `printf`, both plain-identifier call sites."""
    chunk = _chunk(c_chunks, "main")
    assert chunk.chunk_type == "function"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [
        ("helper_fn", False, None),
        ("printf", False, None),
    ]
    assert not chunk.relationships


def test_c_include_emits_include_chunk_and_imports_edge(c_chunks):
    """`#include "helper.h"` -> its own "include"-typed chunk with a self-referential
    IMPORTS edge, same as the C++ case."""
    chunk = _chunk(c_chunks, "helper.h")
    assert chunk.chunk_type == "include"
    edges = _rels(chunk, RelationshipType.IMPORTS)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "helper.h"
    assert edge.line_number == 1
    assert edge.metadata == {"is_system_include": False}
    assert edge.source_id == chunk.chunk_id
