"""Characterization tests for the Rust call-graph Wall-1 walk.

`RustChunker._extra_metadata`/`_extract_call_and_related_metadata`
(chunking/languages/rust.py) walk a `function_item`'s body via
`_dispatch_call_site`, and `EDGE_EMISSION_SPECS["rust"]`
(chunking/relationships/edge_specs.py) materializes the results into
`chunk.calls`/`chunk.relationships` -- the same `materialize_call_edges`/
`materialize_relationship_edges` seam GLSL and C-family flow through (see
`test_glsl_relationships.py`, `test_c_family_relationships.py`, whose
`_rels` helper and per-edge assertion style this file mirrors).

This file pins the full Wall-1 walk's target shapes: plain calls,
`self.`-receiver method calls (the exactness lever -- `qualified` is set to
`"ImplType::method"`, unlike C-family which has no receiver-type info at
all), other-receiver method calls (name-only, `qualified=None`),
`Type::method`/`Self::method`/`mod::fn` scoped calls, `std::`/`core::`/
`alloc::`-qualified calls (dropped), generic (turbofish) calls, struct-
literal INSTANTIATES, `impl Trait for Type` IMPLEMENTS, trait supertrait
INHERITS, and both function-nested and mod-level `use` IMPORTS (plain and
aliased; grouped/glob skipped). `macro_invocation` (e.g. `format!(...)`)
is never a `call_expression`, so it needs no explicit assertion beyond
"absent from `chunk.calls`" -- there is no code path that could add it.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.relationships.relationship_types import RelationshipType


# Fixture exercising every call/relationship shape the Rust Wall-1 walk
# targets. Line numbers below are asserted directly in relationship tests,
# so any edit to this constant must keep line numbers in sync.
_RUST_FIXTURE_SOURCE = """\
fn helper() -> i32 {
    1
}

fn identity<T>(value: T) -> T {
    value
}

fn free_function_calls() -> i32 {
    let a = helper();
    identity::<i32>(a)
}

fn drops_std_qualified_call() -> i32 {
    std::mem::drop(0);
    5
}

struct Point {
    x: f64,
    y: f64,
}

struct Helper;

impl Helper {
    fn compute(&self) -> i32 {
        1
    }
}

impl Point {
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }

    fn combined(&self) -> f64 {
        let a = self.helper_method();
        let b = Point::static_helper();
        let c = Self::other_static();
        a + b + c
    }

    fn helper_method(&self) -> f64 {
        self.x
    }

    fn static_helper() -> f64 {
        1.0
    }

    fn other_static() -> f64 {
        2.0
    }
}

fn other_receiver_call(h: &Helper) -> i32 {
    h.compute()
}

struct Circle {
    radius: f64,
}

impl Display for Circle {
    fn fmt(&self) -> String {
        format!("Circle")
    }
}

trait Shape {
    fn area(&self) -> f64;
}

trait Named: Shape + std::fmt::Display {
    fn name(&self) -> String;
}

fn uses_nested_import() -> i32 {
    use std::cmp::max;
    max(1, 2)
}

mod geometry {
    use super::Point;
    use super::Helper as H;
    use std::collections::{HashMap, HashSet};
    use std::io::*;

    pub fn unit_length() -> f64 {
        1.0
    }
}

fn mod_call() -> f64 {
    geometry::unit_length()
}
"""


@pytest.fixture
def rust_chunks(tmp_path: Path):
    """Chunk `_RUST_FIXTURE_SOURCE` through the real MultiLanguageChunker -> RustChunker path."""
    file_path = tmp_path / "fixture.rs"
    file_path.write_text(_RUST_FIXTURE_SOURCE, encoding="utf-8")

    chunker = MultiLanguageChunker(root_path=str(tmp_path))
    return chunker.chunk_file(str(file_path))


def _chunk(
    chunks, name: str, chunk_type: str | None = None, parent_name: str | None = None
):
    """Find a chunk by `.name`, disambiguating same-named nodes (a struct and
    its own `impl` block both surface a chunk named after the struct, e.g.
    `struct Point` + `impl Point`) by `.chunk_type`, and same-named members
    by `.parent_name`."""
    for c in chunks:
        if (
            c.name == name
            and (chunk_type is None or c.chunk_type == chunk_type)
            and (parent_name is None or c.parent_name == parent_name)
        ):
            return c
    raise AssertionError(
        f"no chunk named {name!r} (chunk_type={chunk_type!r}, parent_name={parent_name!r})"
    )


def _rels(chunk, rel_type: RelationshipType):
    """Filter `chunk.relationships` to one edge type. Mirrors `test_glsl_relationships.py`."""
    return [r for r in (chunk.relationships or []) if r.relationship_type == rel_type]


# ===== plain / generic / std-qualified calls =====


def test_free_function_plain_and_generic_calls(rust_chunks):
    """`helper()` (plain `identifier`) and `identity::<i32>(a)` (`generic_function`
    wrapping an `identifier`, peeled by the recursive re-dispatch) are both
    recognized as unqualified, non-method calls."""
    chunk = _chunk(rust_chunks, "free_function_calls")
    assert chunk.chunk_type == "function"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("helper", False, None), ("identity", False, None)]
    assert not chunk.relationships


def test_std_qualified_call_is_dropped(rust_chunks):
    """`std::mem::drop(0)` is a `scoped_identifier` whose full text starts with
    `std::` -- `_is_rust_std_qualified` drops it at parse time, so it never
    reaches `chunk.calls` at all (the Rust analogue of C-family's `std::sort`
    filter, checked before any `Self::` rewrite logic)."""
    chunk = _chunk(rust_chunks, "drops_std_qualified_call")
    assert chunk.calls == []


# ===== self-receiver / other-receiver / Type:: / Self:: method calls =====


def test_self_receiver_and_scoped_calls_carry_qualified_names(rust_chunks):
    """`combined` is the exactness-lever test: `self.helper_method()` (bare-`self`
    receiver) resolves `callee_qualified` to `"Point::helper_method"` --
    type-scoped at parse time, unlike C++'s receiver-blind method calls.
    `Point::static_helper()` (`scoped_identifier`, plain type path) and
    `Self::other_static()` (`scoped_identifier`, `Self` rewritten to the
    enclosing impl's type by text) both land on the identical
    `"Point::<method>"` spelling -- the key Wall-2's qualified-first lookup
    needs, whether or not the call site literally spelled out the type name.
    """
    chunk = _chunk(rust_chunks, "combined", parent_name="Point")
    assert chunk.chunk_type == "method"
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [
        ("helper_method", True, "Point::helper_method"),
        ("static_helper", False, "Point::static_helper"),
        ("other_static", False, "Point::other_static"),
    ]


def test_field_access_without_call_is_not_a_call_site(rust_chunks):
    """`self.x` (bare field access, never wrapped in a `call_expression`) must
    never appear in `chunk.calls` -- only `self.<method>()` shapes do."""
    chunk = _chunk(rust_chunks, "helper_method", parent_name="Point")
    assert chunk.calls == []


def test_other_receiver_method_call_is_unqualified(rust_chunks):
    """`h.compute()` -- receiver `h` is an ordinary identifier, not a bare `self`
    node, so this is a method call (`is_method_call=True`) but stays
    `callee_qualified=None`: the ambiguous case Wall-2 downgrades to
    `"ambiguous"` confidence, same as every C-family method call."""
    chunk = _chunk(rust_chunks, "other_receiver_call")
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("compute", True, None)]


# ===== INSTANTIATES =====


def test_struct_literal_emits_instantiates_relationship(rust_chunks):
    """`Point { x, y }` inside `Point::new` -> one INSTANTIATES edge, the struct's
    own bare type name via `_peel_type_name`."""
    chunk = _chunk(rust_chunks, "new", parent_name="Point")
    edges = _rels(chunk, RelationshipType.INSTANTIATES)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Point"
    assert edge.line_number == 34
    assert edge.metadata == {}


# ===== IMPLEMENTS =====


def test_trait_impl_emits_implements_relationship(rust_chunks):
    """`impl Display for Circle` -> one IMPLEMENTS edge naming the trait, read
    off the impl's `trait` field directly (unambiguous regardless of the
    trait-vs-Self-type document-order trap `_extra_metadata`'s docstring
    describes). `Circle::fmt`'s own `format!(...)` is a `macro_invocation`,
    never a `call_expression`, so it stays absent from `chunk.calls`."""
    impl_chunk = _chunk(rust_chunks, "Circle", chunk_type="impl")
    edges = _rels(impl_chunk, RelationshipType.IMPLEMENTS)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "Display"
    assert edge.line_number == 65
    assert edge.metadata == {}

    fmt_chunk = _chunk(rust_chunks, "fmt", parent_name="Circle")
    assert fmt_chunk.chunk_type == "method"
    assert fmt_chunk.calls == []


def test_inherent_impl_has_no_implements_relationship(rust_chunks):
    """`impl Point { ... }` (no `trait` field) must never emit an IMPLEMENTS
    edge -- distinguishes an inherent impl from a trait impl."""
    impl_chunk = _chunk(rust_chunks, "Point", chunk_type="impl")
    assert _rels(impl_chunk, RelationshipType.IMPLEMENTS) == []


# ===== INHERITS =====


def test_trait_supertrait_bounds_emit_inherits_relationships(rust_chunks):
    """`trait Named: Shape + std::fmt::Display` -> two INHERITS edges, one per
    `+`-separated bound: a plain `type_identifier` (`Shape`) and a
    `scoped_type_identifier` peeled to its last segment (`Display`), both
    read directly off the trait's own `bounds` field (never a subtree walk,
    so it can't double-count against anything nested deeper)."""
    chunk = _chunk(rust_chunks, "Named", chunk_type="trait")
    edges = _rels(chunk, RelationshipType.INHERITS)
    assert [(e.target_name, e.line_number, e.metadata) for e in edges] == [
        ("Shape", 75, {}),
        ("Display", 75, {}),
    ]


def test_trait_without_supertrait_bounds_has_no_inherits_relationship(rust_chunks):
    """`trait Shape { ... }` has no `bounds` field at all -> no INHERITS edges."""
    chunk = _chunk(rust_chunks, "Shape", chunk_type="trait")
    assert _rels(chunk, RelationshipType.INHERITS) == []


# ===== IMPORTS =====


def test_use_nested_in_function_body_emits_imports_relationship(rust_chunks):
    """`use std::cmp::max;` written inside a function body -> one IMPORTS edge,
    found by the same combined stack walk that collects calls (Rust has no
    separate relationship-extraction pass). `max(1, 2)` itself is a plain
    unqualified call, since the `use` brings the bare name into scope."""
    chunk = _chunk(rust_chunks, "uses_nested_import")
    edges = _rels(chunk, RelationshipType.IMPORTS)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.target_name == "std::cmp::max"
    assert edge.line_number == 80
    assert edge.metadata == {}
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("max", False, None)]


def test_mod_direct_use_declarations_emit_imports_and_skip_grouped_glob(rust_chunks):
    """A `mod`'s own top-level `use` statements -> IMPORTS edges for the plain
    (`use super::Point;`) and aliased (`use super::Helper as H;`, alias
    discarded) forms, scanned from `body`'s direct children only. The
    grouped (`use std::collections::{HashMap, HashSet};`) and glob
    (`use std::io::*;`) forms are skipped entirely -- neither parses as a
    bare `identifier`/`scoped_identifier`."""
    chunk = _chunk(rust_chunks, "geometry", chunk_type="module")
    edges = _rels(chunk, RelationshipType.IMPORTS)
    assert [(e.target_name, e.line_number, e.metadata) for e in edges] == [
        ("super::Point", 85, {}),
        ("super::Helper", 86, {}),
    ]


def test_mod_scoped_call_carries_qualified_name(rust_chunks):
    """`geometry::unit_length()` -- a `scoped_identifier` naming a module path,
    not a type -- is recognized the same as `Type::method`: name-only
    resolution stays available even though nothing rewrites `mod::` the way
    `Self::` is rewritten (there is no enclosing impl type to rewrite it to)."""
    chunk = _chunk(rust_chunks, "mod_call")
    assert [
        (c.callee_name, c.is_method_call, c.callee_qualified) for c in chunk.calls
    ] == [("unit_length", False, "geometry::unit_length")]
