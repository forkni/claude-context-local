"""Shared declarator-unwrapping helper for the C-family chunkers (C, C++).

Both grammars wrap a declaration's name inside nested declarator nodes --
`pointer_declarator`, `reference_declarator`, `function_declarator` -- so a
bare scan of a node's direct children for an `identifier` (the pre-v0.24
approach in both `c.py` and `cpp.py`) misses the name on anything but the
simplest declarations: pointer-returning functions, reference-returning
methods (`T& operator=`), and out-of-class qualified definitions
(`int* Foo::getPtr()`) all silently returned ``name=None``.

Modeled on `GLSLChunker._unwrap_declarator_name` (chunking/languages/glsl.py)
but generalized for the C-family's wider declarator vocabulary -- GLSL's
narrower copy is intentionally left untouched since its own snapshot must
stay byte-identical. Verified against tree-sitter-cpp's and tree-sitter-c's
actual grammar output (not just their published grammar.js) -- see
`docs/adr/0037-decline-index-version-bump-for-cpp-parity.md` and
`docs/adr/0038-cpp-only-container-traversal-seam.md` for the chunking
capability this unlocked.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


#: Terminal node types that carry a declarator's name directly.
#: qualified_identifier: out-of-class definitions (`Foo::getPtr`).
#: destructor_name: `~Foo`. operator_name: `operator=`, `operator+`, etc.
_TERMINAL_DECLARATOR_TYPES = frozenset(
    {
        "identifier",
        "field_identifier",
        "qualified_identifier",
        "destructor_name",
        "operator_name",
    }
)

#: Wrapper node types this unwraps through via their `declarator` field.
#: parenthesized_declarator: the grouping parens around a function-pointer's
#: name, e.g. `void (*cb)(int);` parses as
#: `function_declarator -> parenthesized_declarator -> pointer_declarator ->
#: field_identifier "cb"`. Like `reference_declarator`, it has no
#: `declarator` *field* -- the existing None-field fallback to the first
#: named child already peels it correctly, so no fallback logic changed.
_WRAPPER_DECLARATOR_TYPES = frozenset(
    {
        "pointer_declarator",
        "reference_declarator",
        "function_declarator",
        "parenthesized_declarator",
    }
)


def _next_declarator(node: Any) -> Any | None:
    """Descend one level through a wrapper declarator to its inner declarator.

    Tries the `declarator` field first, falling back to the first named
    child when the field lookup returns None. `reference_declarator` and
    `parenthesized_declarator` have no `declarator` *field* in
    tree-sitter-cpp's grammar -- `child_by_field_name("declarator")` returns
    None for both, even though the inner declarator is present as an
    ordinary (unnamed-field) child. The fallback is load-bearing, not
    defensive: without it, `T& operator=`, reference-returning fluent-API
    methods, and function-pointer members/typedefs (`void (*cb)(int);`) all
    resolve to a dead end. Shared by `unwrap_declarator_name` (which needs
    the terminal name) and `declarator_is_function_shaped` (which only needs
    to know whether a `function_declarator` appears in the chain).

    Args:
        node: A wrapper declarator node (`pointer_declarator`,
            `reference_declarator`, `function_declarator`, or
            `parenthesized_declarator`).

    Returns:
        The inner declarator node, or None if `node` has no named children.
    """
    inner = node.child_by_field_name("declarator")
    if inner is None:
        inner = next((child for child in node.children if child.is_named), None)
    return inner


def unwrap_declarator_name(
    node: Any | None,
    get_text: Callable[[Any], str],
    extra_terminals: frozenset[str] = frozenset(),
) -> str | None:
    """Recursively unwrap a declarator to its identifier name.

    Peels `pointer_declarator` / `reference_declarator` / `function_declarator`
    / `parenthesized_declarator` wrappers via `_next_declarator` until
    reaching a terminal name node (`_TERMINAL_DECLARATOR_TYPES`, widened by
    `extra_terminals` for this call). See `_next_declarator`'s docstring for
    why the field-lookup fallback it performs is load-bearing.

    Args:
        node: The declarator node to unwrap (may itself already be terminal).
        get_text: Callable that slices node text from source, e.g.
            ``lambda n: self.get_node_text(n, source)``.
        extra_terminals: Additional terminal node types to accept for this
            call, unioned with `_TERMINAL_DECLARATOR_TYPES`. Used by typedef
            unwrapping, where the name terminal is `type_identifier` (e.g.
            `typedef void (*Callback)(int);`) -- a type not accepted as a
            terminal in the general case, since it would incorrectly treat a
            declaration's *type* as its name for shapes where `type_identifier`
            appears earlier in the chain.

    Returns:
        The unwrapped name, or None if no terminal name node is reached, or
        the terminal is a MISSING error-recovery placeholder.
    """
    terminals = (
        _TERMINAL_DECLARATOR_TYPES
        if not extra_terminals
        else _TERMINAL_DECLARATOR_TYPES | extra_terminals
    )
    while node is not None and node.type not in terminals:
        if node.type not in _WRAPPER_DECLARATOR_TYPES:
            return None
        node = _next_declarator(node)
    if node is not None and not node.is_missing:
        return get_text(node)
    return None


def declarator_is_function_shaped(node: Any | None) -> bool:
    """Return True if a declarator ultimately wraps a `function_declarator`.

    Used to narrow C++'s `field_declaration`/`declaration` splittable types
    (added for header-only method/constructor/destructor declarations) down
    to actually function-shaped ones -- a plain data member's declarator
    (`field_identifier`, `array_declarator`, ...) never reaches
    `function_declarator` and correctly returns False here.

    Args:
        node: The declarator node to inspect (e.g. a `field_declaration`'s
            `declarator` field).

    Returns:
        True if the declarator chain terminates in a `function_declarator`.
    """
    while node is not None:
        if node.type == "function_declarator":
            return True
        if node.type not in ("pointer_declarator", "reference_declarator"):
            return False
        node = _next_declarator(node)
    return False
