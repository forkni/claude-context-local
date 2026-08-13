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
stay byte-identical. See `docs/plans/CPP_CHUNKING_PARITY.md` for the grammar
facts this was verified against.
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
_WRAPPER_DECLARATOR_TYPES = frozenset(
    {"pointer_declarator", "reference_declarator", "function_declarator"}
)


def unwrap_declarator_name(
    node: Any | None, get_text: Callable[[Any], str]
) -> str | None:
    """Recursively unwrap a declarator to its identifier name.

    Peels `pointer_declarator` / `reference_declarator` / `function_declarator`
    wrappers via their `declarator` field until reaching a terminal name node
    (see `_TERMINAL_DECLARATOR_TYPES`).

    `reference_declarator` has no `declarator` *field* in tree-sitter-cpp's
    grammar -- `child_by_field_name("declarator")` returns None for it, even
    though the inner declarator is present as an ordinary (unnamed-field)
    child. The fallback to the first named child on a None field lookup is
    load-bearing, not defensive: without it, `T& operator=` and every
    reference-returning fluent-API method resolve to `name=None`.

    Args:
        node: The declarator node to unwrap (may itself already be terminal).
        get_text: Callable that slices node text from source, e.g.
            ``lambda n: self.get_node_text(n, source)``.

    Returns:
        The unwrapped name, or None if no terminal name node is reached, or
        the terminal is a MISSING error-recovery placeholder.
    """
    while node is not None and node.type not in _TERMINAL_DECLARATOR_TYPES:
        if node.type not in _WRAPPER_DECLARATOR_TYPES:
            return None
        inner = node.child_by_field_name("declarator")
        if inner is None:
            inner = next((child for child in node.children if child.is_named), None)
        node = inner
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
        inner = node.child_by_field_name("declarator")
        if inner is None:
            inner = next((child for child in node.children if child.is_named), None)
        node = inner
    return False
