"""Characterization tests pinning the in-progress C-family call-graph build-out.

`CppChunker.extract_metadata`/`CChunker.extract_metadata` (chunking/languages/cpp.py,
c.py) now walk `call_expression` nodes via `extract_call_sites`
(chunking/languages/_c_family.py) and `EDGE_EMISSION_SPECS` (chunking/relationships/
edge_specs.py) carries `"cpp"`/`"c"` rows, so `chunk.calls` is populated for `cpp`/`c`
function/method chunks -- but the walk's *dispatch table* is still narrow: only a
`call_expression` whose `function` field is a plain `identifier` is recognized (a call
like `helper_fn(1, 2)`). `field_expression` (method calls, `obj.m()`/`this->m()`),
`qualified_identifier` (`std::sort(...)`), and `template_function` (`clamp<int>(...)`)
are not dispatched yet, so calls of those shapes are silently absent from `chunk.calls`
-- e.g. `Derived::greet`'s `this->log("hi")` and `std::sort(...)` calls do not appear
below, only its plain `helper_fn(1, 2)` call does. `metadata["relationships"]` is still
never populated (no INHERITS/INSTANTIATES/IMPORTS edges yet -- a later step), so
`chunk.relationships` stays `None` throughout this file.

This file pins that in-between state with real C++/C source containing every
call/relationship shape the full Wall-1 walk targets -- plain calls, method calls
(`->`/`this->`), `std::`-qualified calls, inheritance, and `new` -- so each subsequent
commit in this build shows a concrete before/after diff in this same file. As the
dispatch table widens (`field_expression`/`qualified_identifier`/`template_function`)
and relationship edges (`imports`/`instantiates`/`inherits`) land, the remaining
assertions below are expected to flip from "absent"/"no relationships" to real edge
assertions.

Also pins a pre-existing, Wall-1-adjacent gap: unlike GLSL, `preproc_include` is not in either
`LANGUAGE_SPECS["c"]`/`["cpp"]`'s `splittable_node_types` (chunking/language_registry.py), so
`#include` lines produce no dedicated chunk at all for C-family today -- there is nothing an
"imports" relationship edge could attach to yet without also touching the registry.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker


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


# ===== C++ baseline =====


def test_cpp_function_with_plain_call_emits_calls(cpp_chunks):
    """`helper_fn` (free function, plain-identifier call site `printf(...)`) -- one call."""
    chunk = _chunk(cpp_chunks, "helper_fn")
    assert chunk.chunk_type == "function"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("printf", False, None)]
    assert not chunk.relationships


def test_cpp_method_with_mixed_call_shapes_emits_only_identifier_call(cpp_chunks):
    """`Derived::greet` exercises plain/`this->`/`std::`-qualified calls + `new`.

    Only the plain-identifier `helper_fn(1, 2)` call is recognized yet -- `this->log("hi")`
    (`field_expression`) and `std::sort(...)` (`qualified_identifier`) are a later dispatch
    widening, see this file's module docstring.
    """
    chunk = _chunk(cpp_chunks, "greet", parent_name="Derived")
    assert chunk.chunk_type == "method"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("helper_fn", False, None)]
    assert not chunk.relationships


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


def test_cpp_class_with_inheritance_emits_no_relationships(cpp_chunks):
    """`class Derived : public Base` -- no INHERITS edge yet."""
    chunk = _chunk(cpp_chunks, "Derived")
    assert not chunk.relationships


def test_cpp_include_produces_no_dedicated_chunk(cpp_chunks):
    """`#include "helper.hpp"` produces no chunk at all (registry gap, see module docstring)."""
    assert all(c.name != "helper.hpp" for c in cpp_chunks)
    assert all(c.chunk_type != "include" for c in cpp_chunks)


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


def test_c_include_produces_no_dedicated_chunk(c_chunks):
    """`#include "helper.h"` produces no chunk at all (registry gap, see module docstring)."""
    assert all(c.name != "helper.h" for c in c_chunks)
    assert all(c.chunk_type != "include" for c in c_chunks)
