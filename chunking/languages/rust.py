"""Rust-specific chunker using tree-sitter."""

from typing import Any

from tree_sitter import Language

from .base import LanguageChunker


#: `std::`/`core::`/`alloc::`-qualified calls are dropped at Wall 1 -- the
#: Rust analogue of `_c_family._is_std_qualified`. Unlike C++, Rust has no
#: `::`-rooted-vs-relative ambiguity worth special-casing here (`::std::` is
#: legal but vanishingly rare in practice), so both anchored and unanchored
#: forms are listed explicitly rather than stripped-and-compared.
_RUST_STD_QUALIFIED_PREFIXES: tuple[str, ...] = (
    "std::",
    "core::",
    "alloc::",
    "::std::",
    "::core::",
    "::alloc::",
)


def _is_rust_std_qualified(qualified: str) -> bool:
    """Return True if `qualified` is a `std::`/`core::`/`alloc::`-rooted path."""
    return qualified.startswith(_RUST_STD_QUALIFIED_PREFIXES)


def _add_relationship(
    metadata: dict[str, Any],
    rel_type: str,
    target_name: str,
    line_number: int,
    **extra: Any,
) -> None:
    """Append a plain-dict relationship edge to metadata["relationships"].

    A direct copy of `GLSLChunker`'s / `_c_family.py`'s module-level
    `_add_relationship` -- both are trivial, dependency-free dict builders
    with no `chunking/relationships/` import, so duplicating the ~10 lines
    here keeps this language chunker independent of those modules rather
    than introducing a cross-language-chunker import for a helper this
    small. Mirrors the `metadata["calls"]` convention: this emits plain
    data only, converted into `RelationshipEdge` objects downstream by
    `materialize_relationship_edges` (chunking/relationships/edge_specs.py).

    Args:
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (seeded at the top of
            `RustChunker._extra_metadata`).
        rel_type: RelationshipType enum value string, e.g. "imports".
        target_name: Name of the related symbol.
        line_number: 1-indexed source line the relationship was found on.
        **extra: Extra key/value pairs folded into the edge's metadata dict.
    """
    metadata["relationships"].append(
        {
            "relationship_type": rel_type,
            "target_name": target_name,
            "line_number": line_number,
            "metadata": extra,
        }
    )


class RustChunker(LanguageChunker):
    """Rust-specific chunker using tree-sitter."""

    # Rust grammars use type_identifier for struct/enum/trait names
    _NAME_ID_TYPES: tuple[str, ...] = ("identifier", "type_identifier")

    #: `impl`/`trait`/`mod` blocks are Transparent nodes under the base
    #: default (`_CONTAINER_NODE_TYPES` only matches Python's
    #: `class_definition`/`class_declaration`, neither of which Rust's
    #: grammar ever produces) -- every method inside an `impl`, every trait
    #: method, every item inside a `mod` collapsed into that one parent
    #: chunk instead of surfacing as its own named chunk. Widening this set
    #: (the seam ADR-0038 built for exactly this, see `CppChunker`'s
    #: analogous override) makes traversal continue into their children
    #: after chunking them. Discharges ADR-0038's Rust reopening condition.
    _CONTAINER_NODE_TYPES: frozenset[str] = frozenset(
        {"impl_item", "trait_item", "mod_item"}
    )

    def __init__(self, language: Language | None = None) -> None:
        super().__init__("rust", language)

    def _extra_metadata(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Add Rust-specific extras: is_async, calls/relationships for
        functions; name/impl_type/impl_trait/IMPLEMENTS for impl blocks;
        INHERITS for trait supertraits; IMPORTS for a mod's direct `use`s.

        `_extra_metadata` is the "simple leaf" hook (`LanguageChunker
        .extract_metadata`'s template method already seeded `node_type`/
        `name` before calling this) -- unlike GLSL/C-family's complex-leaf
        full `extract_metadata` override, it does not get a pre-seeded
        `metadata["relationships"]` list, so this seeds one unconditionally
        before any of the per-node-type branches below run.
        """
        metadata.setdefault("relationships", [])

        # Check for async functions, and (Wall 1) extract call sites plus
        # struct-literal/nested-use relationships from the function body.
        if node.type == "function_item":
            for child in node.children:
                if (
                    child.type == "async"
                    or self.get_node_text(child, source) == "async"
                ):
                    metadata["is_async"] = True
                    break
            impl_type = self._enclosing_impl_type(node, source)
            self._extract_call_and_related_metadata(node, source, impl_type, metadata)

        # `impl_item`'s name: the base template's `_extract_name` walk
        # (first "type_identifier"/"generic_type" child, in document order)
        # gets this wrong for a trait impl. `impl Default for Lfo` puts the
        # *trait*'s type_identifier ("Default") before the *Self* type's
        # ("Lfo") in document order, so the chunk was named after the
        # trait, not the type it implements -- measured live: a real
        # target project's `nodes/td/chop.rs` produced 14 chunks named
        # "Default" and 14 named "NodeType" instead of their real Self
        # types. Field-based lookup (`type`/`trait`, both real
        # tree-sitter-rust grammar fields) is unambiguous regardless of
        # document order, so overwrite whatever `_extract_name` set.
        if node.type == "impl_item":
            type_name = self._peel_type_name(node.child_by_field_name("type"), source)
            if type_name is not None:
                metadata["name"] = type_name
                metadata["impl_type"] = type_name
            trait_node = node.child_by_field_name("trait")
            if trait_node is not None:
                metadata["impl_trait"] = self.get_node_text(trait_node, source)
                _add_relationship(
                    metadata,
                    "implements",
                    metadata["impl_trait"],
                    trait_node.start_point[0] + 1,
                )

        # `trait Sub: Base + Clone { ... }` -- one INHERITS edge per
        # supertrait bound, read directly off the trait's own `bounds`
        # field (a `trait_bounds` node wrapping `+`-separated type nodes).
        # A direct field read, not a subtree walk, so it never risks
        # double-counting against anything else (same reasoning as
        # `_c_family.extract_inheritance_relationships`'s direct
        # `base_class_clause` child scan).
        if node.type == "trait_item":
            bounds_node = node.child_by_field_name("bounds")
            if bounds_node is not None:
                for child in bounds_node.children:
                    if child.type in (
                        "type_identifier",
                        "generic_type",
                        "scoped_type_identifier",
                    ):
                        name = self._peel_type_name(child, source)
                        if name is not None:
                            _add_relationship(
                                metadata, "inherits", name, child.start_point[0] + 1
                            )

        # A `mod`'s own top-level `use` statements -- direct children of
        # its body only (see `_extract_direct_use_declarations`), never a
        # full subtree walk.
        if node.type == "mod_item":
            self._extract_direct_use_declarations(node, source, metadata)

    def _enclosing_impl_type(self, node: Any, source: bytes) -> str | None:
        """Walk up from a `function_item` to its nearest enclosing `impl_item`.

        Returns the impl's Self type (via `_peel_type_name`) if `node` is a
        method inside a concrete `impl` block; None for a free function or
        a trait's default-body method, whose `Self` is not statically known
        (no single concrete type -- multiple implementors could exist),
        matching the plan's scope: only concrete `impl` blocks pin the type
        used for the `self.`-receiver exactness lever below.

        Args:
            node: A `function_item` node.
            source: Source code bytes.

        Returns:
            The bare Self type name, or None.
        """
        ancestor = node.parent
        while ancestor is not None:
            if ancestor.type == "impl_item":
                return self._peel_type_name(
                    ancestor.child_by_field_name("type"), source
                )
            ancestor = ancestor.parent
        return None

    def _dispatch_call_site(
        self, func_node: Any, line: int, source: bytes, impl_type: str | None
    ) -> tuple[str, int, bool, str | None] | None:
        """Resolve a `call_expression`'s `function` field to a call-site tuple.

        Dispatches per the plan's table (verified live against
        tree-sitter-rust's actual output -- no `node-types.json` ships with
        the installed grammar, tmp/rsprobe2/probe.py + probe2.py):

        - `identifier`: plain call, e.g. `helper()`.
        - `field_expression`: method call. If the receiver (`value` field)
          is itself a bare `self` node -- not merely present somewhere in a
          chained access like `self.nodes.push()`, whose outer `value` is
          another `field_expression`, not `self` -- the call is exactly
          `impl_type::name`: the one lever that makes Rust's method-call
          resolution strictly better than C++'s (ADR-0060 had no
          equivalent, since tree-sitter never carries a C++ receiver's
          static type). Any other receiver stays name-only, `qualified=None`.
        - `scoped_identifier`: qualified call (`Type::m`, `Self::m`,
          `mod::f`). `Self::` is rewritten to the enclosing impl type by
          text, matching the receiver-`self` lever above. `std::`/`core::`/
          `alloc::`-qualified calls are dropped (`_is_rust_std_qualified`,
          the Rust analogue of `_c_family._is_std_qualified`); everything
          else -- including external-crate paths -- flows through
          unfiltered, left for Wall 2's symbol-table lookup to naturally
          fail to resolve (no chunk exists with that qualified name).
        - `generic_function`: peel the `function` field and re-dispatch --
          covers both `f::<T>()` (wraps a `scoped_identifier`/`identifier`)
          and `obj.m::<T>()` (wraps a `field_expression`).
        - anything else (function-pointer calls, etc. -- `macro_invocation`
          is never reached here at all: it parses as its own top-level node
          type, never as a `call_expression`'s `function` field, so it
          needs no explicit skip branch): skipped.

        Args:
            func_node: The `call_expression`'s `function` field.
            line: 1-indexed source line, computed once from the outermost
                `function` field by the caller and threaded through every
                dispatch branch including the `generic_function` peel
                (mirrors `_c_family.extract_call_sites`'s single up-front
                `line` computation).
            source: Source code bytes.
            impl_type: The enclosing `impl` block's Self type name, or None.

        Returns:
            A plain `(name, line, is_method_call, qualified)` 4-tuple, or
            None if this shape is not a resolvable/interesting call site.
        """
        if func_node is None or func_node.is_missing:
            return None
        if func_node.type == "identifier":
            return (self.get_node_text(func_node, source), line, False, None)
        if func_node.type == "field_expression":
            field_node = func_node.child_by_field_name("field")
            if field_node is None or field_node.is_missing:
                return None
            name = self.get_node_text(field_node, source)
            value_node = func_node.child_by_field_name("value")
            if value_node is not None and value_node.type == "self" and impl_type:
                return (name, line, True, f"{impl_type}::{name}")
            return (name, line, True, None)
        if func_node.type == "scoped_identifier":
            name_node = func_node.child_by_field_name("name")
            if name_node is None or name_node.is_missing:
                return None
            name = self.get_node_text(name_node, source)
            qualified_text = self.get_node_text(func_node, source)
            if _is_rust_std_qualified(qualified_text):
                return None
            path_node = func_node.child_by_field_name("path")
            if (
                impl_type
                and path_node is not None
                and path_node.type == "identifier"
                and self.get_node_text(path_node, source) == "Self"
            ):
                qualified = f"{impl_type}::{name}"
            else:
                qualified = qualified_text
            return (name, line, False, qualified)
        if func_node.type == "generic_function":
            inner = func_node.child_by_field_name("function")
            return self._dispatch_call_site(inner, line, source, impl_type)
        return None

    def _extract_call_and_related_metadata(
        self, node: Any, source: bytes, impl_type: str | None, metadata: dict[str, Any]
    ) -> None:
        """Walk a `function_item` body once, collecting calls and
        INSTANTIATES/IMPORTS relationships.

        A single combined stack traversal, unlike `_c_family.py`'s separate
        walks (`extract_call_sites` / `extract_instantiation_relationships`)
        -- Rust has no preprocessor pass splitting those concerns, so one
        pass over the same subtree is simpler and strictly equivalent.

        Only ever called with `node.type == "function_item"` (see
        `_extra_metadata`): container chunks (`impl_item`/`trait_item`/
        `mod_item`) never get this walk, so a `struct_expression` or nested
        `use_declaration` inside a method body is never double-counted once
        against the enclosing `impl`'s own chunk (whose text includes the
        method's body verbatim, since containers emit their own full body
        *and* their children) and once against the method's own chunk --
        the same duplication trap `edge_specs.EDGE_EMISSION_SPECS["rust"]
        .call_chunk_types` guards for materializing calls (a container's
        `chunk_type` is never in `{"function","method"}`), enforced here
        instead by never walking a container's own subtree at all --
        matching `_c_family.extract_instantiation_relationships`'s
        "function_definition node being processed" contract.

        Args:
            node: A `function_item` node (the chunk being processed).
            source: Source code bytes.
            impl_type: The enclosing `impl` block's Self type, or None.
            metadata: Metadata dict being populated; must already have a
                "relationships" list key.
        """
        calls: list[tuple[str, int, bool, str | None]] = []
        instantiate_sites: list[tuple[str, int]] = []
        stack = [node]
        while stack:
            current = stack.pop()
            if current.type == "call_expression":
                func_node = current.child_by_field_name("function")
                if func_node is not None and not func_node.is_missing:
                    line = func_node.start_point[0] + 1
                    entry = self._dispatch_call_site(func_node, line, source, impl_type)
                    if entry is not None:
                        calls.append(entry)
            elif current.type == "struct_expression":
                name_node = current.child_by_field_name("name")
                name = self._peel_type_name(name_node, source)
                if name is not None:
                    instantiate_sites.append((name, name_node.start_point[0] + 1))
            elif current.type == "use_declaration":
                self._extract_use_declaration(current, source, metadata)
            stack.extend(current.children)
        # Stack-based traversal visits children in reverse order; sort by
        # source line so metadata["calls"]/relationships read in document
        # order (mirrors `_c_family.extract_call_sites`).
        calls.sort(key=lambda c: c[1])
        metadata["calls"] = calls
        instantiate_sites.sort(key=lambda s: s[1])
        for name, line in instantiate_sites:
            _add_relationship(metadata, "instantiates", name, line)

    def _extract_use_declaration(
        self, use_node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Emit one IMPORTS edge for a `use_declaration` node.

        Handles the two shapes tree-sitter-rust produces for a plain or
        aliased `use` (verified live, tmp/rsprobe2/probe.py): `use a::b::C;`
        (a bare `scoped_identifier`/`identifier` child) and
        `use a::b::C as D;` (a `use_as_clause` wrapping the same shape,
        alias discarded -- the target project has no `use ... as` per the
        plan's Absent-from-this-codebase list, so exact alias-target
        attribution is unneeded). Grouped (`use a::{b, c};`) and glob
        (`use a::*;`) imports are skipped -- deliberately out of scope, see
        the plan's Deferred section; they parse as `use_list`/
        `scoped_use_list`/`use_wildcard`, none of which is
        `identifier`/`scoped_identifier`.

        Args:
            use_node: A `use_declaration` node.
            source: Source code bytes.
            metadata: Metadata dict being populated; must already have a
                "relationships" list key.
        """
        line = use_node.start_point[0] + 1
        target_node = next((c for c in use_node.children if c.is_named), None)
        if target_node is None:
            return
        if target_node.type == "use_as_clause":
            target_node = next((c for c in target_node.children if c.is_named), None)
            if target_node is None:
                return
        if target_node.type not in ("identifier", "scoped_identifier"):
            return
        path = self.get_node_text(target_node, source)
        _add_relationship(metadata, "imports", path, line)

    def _extract_direct_use_declarations(
        self, node: Any, source: bytes, metadata: dict[str, Any]
    ) -> None:
        """Emit IMPORTS edges for a `mod_item`'s own top-level `use` statements.

        Scoped to direct children of the mod's `body` field only -- not a
        full subtree walk -- so a `use` nested inside a further-nested
        `mod`/`impl`/`fn` inside this module is never double-counted here
        as well as at its own (separately chunked) container/function.

        File-root `use` statements are structurally unreachable from any
        chunk's metadata at all: `_collect_module_preamble_chunks`
        (base.py) builds `module_preamble` chunks directly with
        `metadata={"type": "module_preamble"}`, bypassing
        `extract_metadata`/`_extra_metadata` entirely -- so this only ever
        fires for `use` statements written directly inside a `mod { ... }`
        block, not at the top of the file.

        Args:
            node: A `mod_item` node.
            source: Source code bytes.
            metadata: Metadata dict being populated; must already have a
                "relationships" list key.
        """
        body = node.child_by_field_name("body")
        if body is None:
            return
        for child in body.children:
            if child.type == "use_declaration":
                self._extract_use_declaration(child, source, metadata)

    def _peel_type_name(self, node: Any, source: bytes) -> str | None:
        """Return the bare identifier for a Rust `impl` target-type node.

        Handles the shapes an `impl` `type` (or `trait`) field can take:
        `type_identifier` directly (`Lfo`), `generic_type` (peel to its own
        `type` field -- `Container<T>` -> `Container`), and
        `scoped_type_identifier` (last segment via its `name` field --
        `std::fmt::Display` -> `Display`). Falls back to the node's raw
        text for any other shape (e.g. `reference_type`) -- unambiguous
        even without further peeling.

        Also reused (Wall 1) for `struct_expression`'s `name` field
        (`Foo { .. }` / `path::Foo { .. }`) and `trait_item`'s supertrait
        bounds (`Base` in `trait Sub: Base`) -- both take the identical
        `type_identifier`/`generic_type`/`scoped_type_identifier` shapes.

        Args:
            node: The `type` or `trait` field node of an `impl_item`, a
                `struct_expression`'s `name` field, or a `trait_bounds`
                child, or None if the field is absent.
            source: Source code bytes.

        Returns:
            The bare type name, or None if `node` is None.
        """
        if node is None:
            return None
        if node.type == "type_identifier":
            return self.get_node_text(node, source)
        if node.type == "generic_type":
            inner = node.child_by_field_name("type")
            return self._peel_type_name(inner, source) if inner is not None else None
        if node.type == "scoped_type_identifier":
            name = node.child_by_field_name("name")
            return self.get_node_text(name, source) if name is not None else None
        return self.get_node_text(node, source)
