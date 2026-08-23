"""Shared parse-recovery helpers for the C-family chunkers (C, C++).

Two independent concerns live here, both scoped to the C family only:

1. Declarator-name unwrapping. Both grammars wrap a declaration's name
   inside nested declarator nodes -- `pointer_declarator`,
   `reference_declarator`, `function_declarator` -- so a bare scan of a
   node's direct children for an `identifier` (the pre-v0.24 approach in
   both `c.py` and `cpp.py`) misses the name on anything but the simplest
   declarations: pointer-returning functions, reference-returning methods
   (`T& operator=`), and out-of-class qualified definitions
   (`int* Foo::getPtr()`) all silently returned ``name=None``.

   Modeled on `GLSLChunker._unwrap_declarator_name`
   (chunking/languages/glsl.py) but generalized for the C-family's wider
   declarator vocabulary -- GLSL's narrower copy is intentionally left
   untouched since its own snapshot must stay byte-identical. Verified
   against tree-sitter-cpp's and tree-sitter-c's actual grammar output
   (not just their published grammar.js) -- see
   `docs/adr/0037-decline-index-version-bump-for-cpp-parity.md` and
   `docs/adr/0038-cpp-only-container-traversal-seam.md` for the chunking
   capability this unlocked.

2. Preprocessor-conditional neutralization. Neither grammar implements the
   preprocessor -- `#if`/`#ifdef`/.../`#endif` are parsed as literal
   tokens, and an unbalanced or macro-heavy conditional routinely desyncs
   the parser into an ERROR node that swallows every definition until the
   next recovery point. `neutralize_preprocessor_conditionals` blanks
   those directive lines before parsing, via the
   `LanguageChunker.preprocess_source_for_parse` seam GLSL already uses
   for its own, unrelated parse-error case.
"""

from __future__ import annotations

import re
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
#: pointer_type_declarator: only ever seen inside the MISSING-`::`
#: error-recovery shape handled by `_scope_is_missing` below -- an
#: unrecognized macro (e.g. an unknown export attribute) is absorbed as the
#: return type, and tree-sitter recovers by synthesizing a bogus
#: `qualified_identifier` whose tail is `pointer_type_declarator ->
#: function_declarator -> type_identifier`.
_WRAPPER_DECLARATOR_TYPES = frozenset(
    {
        "pointer_declarator",
        "reference_declarator",
        "function_declarator",
        "parenthesized_declarator",
        "pointer_type_declarator",
    }
)


def _scope_is_missing(node: Any) -> bool:
    """True if `node` (a `qualified_identifier`) has a MISSING `::` child.

    tree-sitter-cpp synthesizes this shape as error recovery when an
    unrecognized macro (e.g. an unknown export/visibility attribute like
    `CITO_PLUGIN_EXPORT`) is absorbed as the declaration's return type: the
    parser then treats what follows as a bogus namespace-qualified name,
    e.g. `AudioEnginePluginListV1*\\ncito_plugin_list_v1(void)` instead of
    the real name `cito_plugin_list_v1`. A real qualified name (`Foo::bar`)
    always has a present `::` token, so this check never fires for one.

    Args:
        node: A `qualified_identifier` node.

    Returns:
        True if `node` has a `::` child flagged `is_missing`.
    """
    return any(child.type == "::" and child.is_missing for child in node.children)


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
    if (
        node is not None
        and node.type == "qualified_identifier"
        and _scope_is_missing(node)
    ):
        # Error-recovery artifact (see `_scope_is_missing`), not a real
        # qualified name -- descend into its last named child and keep
        # unwrapping, accepting `type_identifier` as a terminal on this
        # branch only. Widening `type_identifier` globally would mistake a
        # declaration's *type* for its name (see the `extra_terminals`
        # docstring above); it's safe here because this branch only runs
        # once a MISSING `::` has already proven the parse is a recovery
        # artifact, not a genuine declaration.
        candidates = [child for child in node.children if child.is_named]
        inner = candidates[-1] if candidates else None
        return unwrap_declarator_name(
            inner, get_text, extra_terminals=extra_terminals | {"type_identifier"}
        )
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


# ---------------------------------------------------------------------------
# Preprocessor-conditional neutralization
# ---------------------------------------------------------------------------

#: Matches a preprocessor conditional directive line, including any
#: backslash-continued continuation lines (`(?:[^\n]*\\\n)*` consumes zero
#: or more `...\` + newline lines before the final, non-continued line).
#: `#include`/`#define`/`#pragma` are deliberately excluded -- they parse
#: fine as `preproc_include`/`preproc_def` nodes that
#: `chunking/language_registry.py`'s `NODE_TYPE_MAP` maps to real chunk
#: kinds, so blanking them would silently delete indexed content.
_PP_COND = re.compile(
    rb"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|elif|elifdef|elifndef|else|endif)\b"
    rb"(?:[^\n]*\\\n)*[^\n]*",
    re.M,
)


def blank_preserving_layout(match: re.Match[bytes]) -> bytes:
    """Replace every non-newline byte in a match with a space.

    Must be exactly this form, not `b" " * len(match.group(0))` -- on a
    match spanning multiple lines (a backslash-continued directive, or CUDA's
    `<<<grid, block>>>` launch syntax), the naive multiply preserves total
    length but collapses every embedded newline into spaces, silently
    shifting every downstream start_line/end_line for the rest of the file.
    `re.sub` here only touches non-newline bytes, so the line count and every
    remaining newline's byte offset are unchanged.

    Public (no leading underscore) because it's a shared `re.sub` callback,
    reused by `CudaChunker.preprocess_source_for_parse` (cpp.py) for its own,
    differently-shaped matches (`_CUDA_ATTRS`, `_LAUNCH_CFG`) -- not just
    `_PP_COND` here.

    Args:
        match: Any regex match to blank byte-for-byte.

    Returns:
        `match.group(0)` with every non-newline byte replaced by a space.
    """
    return re.sub(rb"[^\n]", b" ", match.group(0))


def neutralize_preprocessor_conditionals(source_bytes: bytes) -> bytes:
    """Blank preprocessor conditional directive lines before parsing.

    Measured over 294 real C/C++ files: ERROR lines 45,786 (23.3%) -> 3,803
    (1.9%), a 91.7% reduction, with zero definitions lost (10,217 -> 10,217).
    Both branches of a conditional keep their bodies in place -- only the
    directive lines themselves (`#if COND`, `#ifdef X`, ...) are blanked --
    so tree-sitter parses the surrounding code normally instead of
    desyncing on tokens it doesn't understand.

    Length- and newline-position-preserving per `blank_preserving_layout`,
    satisfying the contract `LanguageChunker.preprocess_source_for_parse`
    documents: the caller feeds this only to `self.parser.parse(...)` and
    keeps the original bytes for chunk text and name slicing, so byte
    offsets computed against the rewritten buffer must line up exactly with
    the original.

    Args:
        source_bytes: UTF-8-encoded original source.

    Returns:
        Source bytes with preprocessor conditional directive lines blanked.
        Identical in total length and newline positions to `source_bytes`.
    """
    return _PP_COND.sub(blank_preserving_layout, source_bytes)
