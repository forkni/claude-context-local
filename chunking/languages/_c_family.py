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
from collections.abc import Callable, Iterator
from typing import Any

from .base import LanguageChunker


#: A tree-sitter `Parser.parse`-shaped callable: bytes in, a parsed tree out.
#: `repair_macro_wrapped_declarations` only needs `.root_node`, so any
#: `tree_sitter.Parser.parse` bound method satisfies this without importing
#: the `tree_sitter` package here.
_ParseFn = Callable[[bytes], Any]


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


# ---------------------------------------------------------------------------
# Macro-wrapped return-type repair
# ---------------------------------------------------------------------------

#: Matches `MACRO_NAME(TYPE) declarator(...)` -- the macro-wrapped-return-type
#: idiom (`PyAPI_FUNC(PyObject *) f(PyObject *);`, `CVAPI(void) g(int);`) that
#: pervades C-compatible headers; neither grammar recognizes an arbitrary
#: identifier immediately followed by `(...)` in return-type position, so
#: this desyncs the parser into an ERROR node.
#:
#: Group 2 (the macro name) requires two uppercase letters in a mixed-case
#: identifier, which also matches camelCase method names like
#: `getParDouble2` -- ERROR-scoping (not this regex) is what makes rewriting
#: safe; see `repair_macro_wrapped_declarations`'s docstring.
#: Group 3 (the gap before `(`) is captured, not consumed silently: omitting
#: its length from the blank-out broke the byte-length invariant on
#: `dtype_api.h` during measurement.
_MACRO_WRAPPED_RETURN = re.compile(
    rb"(^|[\s;{}])((?=[A-Za-z_]*[A-Z][A-Za-z_]*[A-Z])[A-Za-z_][A-Za-z0-9_]*)"
    rb"([ \t]*)\(((?:[^()\n]|\([^()\n]*\))*)\)(?=[ \t]*[\*&A-Za-z_])"
)


def _blank_macro_wrapper(match: re.Match[bytes]) -> bytes:
    """Blank a macro-wrapper's name/gap/parens; keep the wrapped type.

    `MACRO_NAME(T)` -> `           T ` -- length-preserving per match, like
    `blank_preserving_layout`, but can't reuse it directly: only the
    name/gap (groups 2/3) and both parens are blanked, while the wrapped
    type (group 4) must survive verbatim.
    """
    prefix, name, gap, inner = match.groups()
    return prefix + b" " * (len(name) + len(gap) + 1) + inner + b" "


def _error_nodes(root_node: Any) -> Iterator[Any]:
    """Yield every genuine ERROR node in a parsed tree (nested included).

    Iterative (explicit stack), not recursive, for the same deep-tree
    recursion-limit reason as `unwrap_declarator_name`. Not shared with
    `chunking/tree_sitter.py`'s `_collect_error_line_ranges` -- that module
    imports the language chunkers (this module's callers), so importing
    back would be circular.

    Args:
        root_node: Root node of a parsed tree_sitter.Tree.

    Yields:
        Every node where `node.type == "ERROR"`.
    """
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type == "ERROR":
            yield node
        stack.extend(node.children)


def repair_macro_wrapped_declarations(
    source_bytes: bytes,
    parse: _ParseFn,
) -> bytes:
    """Unwrap macro-wrapped return types, scoped strictly to ERROR spans.

    Measured over 948 C++-extension files (302,095 lines) from a real
    TouchDesigner installation tree: ERROR lines 30,320 (10.04%) -> 28,030
    (9.28%), a 7.6% reduction, with definitions gained (65,277 -> 66,500,
    +1,223) and zero files regressed (107 improved / 0 regressed).

    A global (non-ERROR-scoped) version of this same rewrite was measured
    and rejected first: it regressed 82 files, because camelCase C++ method
    names (`getParDouble2`, `getParFilePath`) satisfy
    `_MACRO_WRAPPED_RETURN`'s two-uppercase-letter test just as well as a
    real macro does, and deleting a real method name to "unwrap" it breaks
    the declaration it belonged to. Scoping every rewrite to inside an
    ERROR node's byte span, and only keeping a round if the ERROR line count
    *strictly* decreases, makes this zero-regression-by-construction: a
    method name that already parses cleanly is never inside an ERROR span
    in the first place, so it is never a rewrite candidate.

    ERROR-scoping is enforced by *containment*, not by slicing the buffer to
    each span and matching within the slice: a tree-sitter ERROR node's byte
    span is an implementation detail of its error-recovery heuristics and
    can end anywhere, including mid-declaration -- e.g. right at a macro
    call's closing paren, before the wrapped function name that
    `_MACRO_WRAPPED_RETURN`'s trailing lookahead needs to see
    (`PyAPI_FUNC(PyObject *)|` with the ERROR span ending at `|`, one token
    before ` PyCell_New(...)`). Matching against a `[start:end]` slice of
    that span would put the lookahead past the end of the slice, so the
    match silently fails for that declaration while an adjacent one, whose
    ERROR span happens to run further, repairs fine -- non-deterministic
    from a caller's point of view since it depends on where the parser's
    error recovery drew the boundary. Matching against the *whole* buffer
    and then filtering matches to only those whose macro-name group starts
    inside an ERROR span gets the lookahead context right in every case
    while keeping the exact same safety property: a name that already
    parses cleanly is never inside an ERROR span, so it is still never a
    rewrite candidate.

    Bounded to two reparse-and-retry passes, since one repaired macro can
    occasionally unmask a second, previously-nested ERROR region.

    Known residual limitations, deliberately out of scope -- both share the
    same shape: the source parses *without* an ERROR node, so there is no
    span for this function to scope a rewrite to, and widening the scope
    beyond confirmed ERROR spans is exactly what caused the 82-file
    regression above.

    - Macro-wrapped *data* declarations (`PyAPI_DATA(PyTypeObject)
      PyCell_Type;`) and "stacked" macros (`Py_DEPRECATED(3.3)
      PyAPI_FUNC(PyObject *) PyCell_New(...)`) both parse without a real
      `ERROR` node -- the latter instead sets `has_error` via a synthesized
      MISSING `;` token, a different defect class this function doesn't
      target.

    Args:
        source_bytes: Source bytes, already passed through any prior,
            purely textual preprocessing (e.g.
            `neutralize_preprocessor_conditionals`) -- this function is
            parse-dependent and must run last in a chunker's
            `preprocess_source_for_parse` pipeline, after every rewrite
            that only needs the raw text.
        parse: A `tree_sitter.Parser.parse`-shaped callable used to
            (re)parse candidates and locate ERROR spans. Callers pass
            `self.parser.parse`.

    Returns:
        Source bytes with as many macro-wrapped declarations repaired as
        could be, without ever increasing the ERROR line count. Identical
        in total length and newline positions to `source_bytes`.
    """
    current = source_bytes
    tree = parse(current)
    if not tree.root_node.has_error:
        return current
    error_lines = sum(
        n.end_point[0] - n.start_point[0] + 1 for n in _error_nodes(tree.root_node)
    )

    for _ in range(2):
        spans = [(n.start_byte, n.end_byte) for n in _error_nodes(tree.root_node)]
        if not spans:
            break

        # Match against the whole buffer (not a per-span slice -- see this
        # function's docstring for why slicing can starve the trailing
        # lookahead of context) and keep only matches whose macro-name
        # group (2) starts inside one of the ERROR spans.
        matches = [
            m
            for m in _MACRO_WRAPPED_RETURN.finditer(current)
            if any(start <= m.start(2) < end for start, end in spans)
        ]
        if not matches:
            break

        # finditer matches are non-overlapping, so writing each
        # replacement at its own [start(0):end(0)] offset is safe.
        candidate = bytearray(current)
        for m in matches:
            candidate[m.start(0) : m.end(0)] = _blank_macro_wrapper(m)
        candidate_bytes = bytes(candidate)

        # Guard: length and newline-position invariant -- protects against
        # composing this with a future non-length-preserving rewrite
        # upstream.
        if len(candidate_bytes) != len(current) or candidate_bytes.count(
            b"\n"
        ) != current.count(b"\n"):
            break

        candidate_tree = parse(candidate_bytes)
        candidate_error_lines = (
            sum(
                n.end_point[0] - n.start_point[0] + 1
                for n in _error_nodes(candidate_tree.root_node)
            )
            if candidate_tree.root_node.has_error
            else 0
        )
        # Guard: only keep a round that strictly improves. Without this, a
        # global rewrite regresses real C++ method names that happen to
        # match the same shape -- see this function's docstring.
        if candidate_error_lines >= error_lines:
            break

        current, tree, error_lines = (
            candidate_bytes,
            candidate_tree,
            candidate_error_lines,
        )

    return current


# ---------------------------------------------------------------------------
# Call-expression extraction (Wall 1)
# ---------------------------------------------------------------------------


def _leaf_call_name(node: Any | None, get_text: Callable[[Any], str]) -> str | None:
    """Resolve a call-site name node to its leaf identifier text.

    Peels one level of `template_function`/`template_method` (e.g. the
    `max` in `max<int>(...)`, or the `sort` in `obj.sort<Cmp>(...)`) down to
    its own `name` field before slicing text -- tree-sitter-cpp nests the
    identifier one field deeper than a plain, non-templated call. Recursion
    is bounded to one real level (a template can't itself be templated), so
    no explicit-stack rewrite is needed here unlike the tree walks above.

    Args:
        node: The candidate name node -- a `call_expression`'s `function`
            field, a `field_expression`'s `field` field, or a
            `qualified_identifier`'s `name` field.
        get_text: Callable that slices node text from source.

    Returns:
        The leaf identifier text, or None if `node` is None, MISSING, or
        (after peeling) still not a plain name node.
    """
    if node is None or node.is_missing:
        return None
    if node.type in ("template_function", "template_method"):
        return _leaf_call_name(node.child_by_field_name("name"), get_text)
    return get_text(node)


def _is_std_qualified(qualified: str | None) -> bool:
    """True if a call's full qualified text is `std::`- or `::std::`-prefixed.

    The single biggest, cheapest noise win measured by the Phase 0 probe
    (5,679 of 33,996 call sites): nobody's project defines `std::sort`, so
    every `std::`-qualified call is unconditionally noise -- unlike a bare
    method name (`.size()`), which needs project context to judge (deferred
    to `search/graph_integration.py`'s Wall-2 "unless the project defines
    it" pattern, `_C_FAMILY_COMMON_MEMBERS` -- not duplicated here).
    """
    return qualified is not None and (
        qualified.startswith("std::") or qualified.startswith("::std::")
    )


_CAST_KEYWORDS: frozenset[str] = frozenset(
    {"static_cast", "dynamic_cast", "const_cast", "reinterpret_cast"}
)


def _is_cast_keyword(name: str) -> bool:
    """True if `name` is a C++ cast-operator keyword, not a real call.

    `static_cast<T>(x)` / `dynamic_cast<T>(x)` / `const_cast<T>(x)` /
    `reinterpret_cast<T>(x)` parse identically to an ordinary templated
    function call (`template_function` shape) in tree-sitter-cpp, so
    without this check they're indistinguishable from a real call to a
    project-defined `clamp<T>()`-style template. Measured on voro-engine's
    real `--mode force` reindex (2026-09-03): 850 of 12,968 phantom
    C-family call edges (6.6%) were exactly these four keywords --
    unconditional noise, same class as `_is_std_qualified`.
    """
    return name in _CAST_KEYWORDS


def extract_call_sites(
    node: Any,
    get_text: Callable[[Any], str],
) -> list[tuple[str, int, bool, str | None]]:
    """Walk `call_expression` nodes inside `node`, recording call sites.

    Emits plain `(name, line, is_method_call, qualified)` 4-tuples, not
    `CallSite` NamedTuples -- this module does not import
    `chunking.relationships.edge_specs`, mirroring `GLSLChunker
    ._extract_call_metadata` (glsl.py), which keeps `chunking/relationships/`
    out of every language chunker.
    `chunking.relationships.edge_specs._as_call_site` normalizes this shape
    (and GLSL's narrower 2-tuple) into a real `CallSite` downstream.

    Dispatches on the `function` field's node type, per the plan's table
    (`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`):

    - `identifier`: plain call, e.g. `helper_fn(1, 2)`.
    - `field_expression`: method call (`obj.m()` / `ptr->m()`) --
      `is_method_call=True`, name from the `field` field (itself peeled via
      `_leaf_call_name` if it's a `template_method`, e.g. `obj.sort<Cmp>()`).
    - `qualified_identifier` (C++ only): `std::sort(...)` / `Foo::bar(...)`
      -- name from the `name` field (peeled the same way for
      `std::max<int>(...)`'s `template_function` nesting), `qualified` set
      to the full text.
    - `template_function` (C++ only): a bare, unqualified templated call
      (`clamp<int>(...)`) -- name from the `name` field.
    - anything else (function-pointer calls, etc.): skipped.

    `std::`/`::std::`-qualified calls are dropped (`_is_std_qualified`), and
    bare `static_cast`/`dynamic_cast`/`const_cast`/`reinterpret_cast`
    "calls" are dropped (`_is_cast_keyword`) -- both are unconditional,
    file-local noise that belongs at chunk time. A static STL member-name
    blocklist would need "unless the project defines it" project-wide
    context this per-file walk doesn't have, so that lives at index time
    instead (Wall 2, `_C_FAMILY_COMMON_MEMBERS`).

    tree-sitter-c produces only the `identifier` shape (verified against
    the Phase 0 probe -- C's grammar has no `qualified_identifier` or
    `template_function`, and C's rare struct-function-pointer
    `field_expression` calls are covered by the same dispatch row as C++
    method calls), so this same function already covered C's call sites
    fully before this widening; only C++ gains new dispatch rows here.

    Iterative (explicit stack), not recursive -- same rationale as
    `_error_nodes` and `unwrap_declarator_name`: deep real-world trees can
    exceed Python's recursion limit.

    Args:
        node: A `function_definition` node (the chunk, or the
            `function_definition` child of a `template_declaration` chunk,
            being processed).
        get_text: Callable that slices node text from source, e.g.
            ``lambda n: self.get_node_text(n, source)``.

    Returns:
        Call sites in source-line order. Always a list (empty when the
        function body makes no recognized calls), so "no calls" and
        "language does not report calls" stay distinguishable downstream --
        mirrors `GLSLChunker._extract_call_metadata`'s contract.
    """
    calls: list[tuple[str, int, bool, str | None]] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "call_expression":
            func_node = current.child_by_field_name("function")
            entry: tuple[str, int, bool, str | None] | None = None
            if func_node is not None and not func_node.is_missing:
                line = func_node.start_point[0] + 1
                if func_node.type == "identifier":
                    entry = (get_text(func_node), line, False, None)
                elif func_node.type == "field_expression":
                    name = _leaf_call_name(
                        func_node.child_by_field_name("field"), get_text
                    )
                    if name is not None:
                        entry = (name, line, True, None)
                elif func_node.type == "qualified_identifier":
                    name = _leaf_call_name(
                        func_node.child_by_field_name("name"), get_text
                    )
                    if name is not None:
                        qualified = get_text(func_node)
                        if not _is_std_qualified(qualified):
                            entry = (name, line, False, qualified)
                elif func_node.type == "template_function":
                    name = _leaf_call_name(
                        func_node.child_by_field_name("name"), get_text
                    )
                    if name is not None and not _is_cast_keyword(name):
                        entry = (name, line, False, None)
            if entry is not None:
                calls.append(entry)
        stack.extend(current.children)
    # Stack-based traversal visits children in reverse order; sort by source
    # line so metadata["calls"] reads in document order (mirrors GLSL).
    calls.sort(key=lambda c: c[1])
    return calls


# ---------------------------------------------------------------------------
# Relationship extraction (Wall 1, step 5): imports / inherits / instantiates
# ---------------------------------------------------------------------------


def _add_relationship(
    metadata: dict[str, Any],
    rel_type: str,
    target_name: str,
    line_number: int,
    **extra: Any,
) -> None:
    """Append a plain-dict relationship edge to metadata["relationships"].

    A direct copy of `GLSLChunker`'s module-level `_add_relationship`
    (glsl.py) -- both are trivial, dependency-free dict builders with no
    `chunking/relationships/` import, so duplicating the ~10 lines here
    keeps this language chunker independent of glsl.py rather than
    introducing a cross-language-chunker import for a helper this small.
    Mirrors the `metadata["calls"]` convention (Phase 2b): this emits plain
    data only, converted into `RelationshipEdge` objects downstream by
    `materialize_relationship_edges` (chunking/relationships/edge_specs.py).

    Args:
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (set at the top of extract_metadata).
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


def _type_leaf_name(node: Any | None, get_text: Callable[[Any], str]) -> str | None:
    """Resolve a base-class or `new`-expression type node to its leaf name.

    Peels `qualified_identifier` (`ns::Base`) down to its `name` field and
    `template_type` (`Vector<int>`) down to its own `name` field, one level
    each, recursing to unwind combinations of both (`ns::Vector<int>` ->
    `qualified_identifier.name` = `template_type` -> `template_type.name` =
    `type_identifier "Vector"`). Mirrors `_leaf_call_name`'s template-peeling,
    but over the *type*-node vocabulary `base_class_clause`/`new_expression`
    actually produce (`qualified_identifier`/`template_type`) rather than the
    call-expression vocabulary (`template_function`/`template_method`)
    `_leaf_call_name` targets -- verified against the real grammar output,
    not just grammar.js (tmp/probe_cpp_grammar.py).

    Args:
        node: The candidate type node -- a `base_class_clause` entry, or a
            `new_expression`'s `type` field.
        get_text: Callable that slices node text from source.

    Returns:
        The leaf identifier text, or None if `node` is None or MISSING.
    """
    if node is None or node.is_missing:
        return None
    if node.type in ("qualified_identifier", "template_type"):
        return _type_leaf_name(node.child_by_field_name("name"), get_text)
    return get_text(node)


def extract_include_metadata(
    node: Any,
    get_text: Callable[[Any], str],
    metadata: dict[str, Any],
) -> None:
    """Populate `metadata` for a `preproc_include` chunk with an IMPORTS edge.

    A direct port of `GLSLChunker._extract_include_metadata` (glsl.py):
    tree-sitter-cpp and tree-sitter-c produce the identical
    `string_literal`/`system_lib_string` shape for `#include` that GLSL's
    (C-preprocessor-derived) grammar does -- verified empirically
    (tmp/probe_cpp_include.py), not assumed from the two grammars sharing a
    common preprocessor lineage. Shared here (unlike `extract_call_sites`,
    which has C++-only dispatch rows) since `#include` parses identically in
    both languages. Sets a self-referential relationship -- the include
    chunk's own edge describes itself as an import, same as GLSL's -- plus
    `name`/`include_path`/(for system includes) `is_system_include` on
    `metadata` directly, matching `CppChunker`/`CChunker`'s other name-
    extraction branches.

    Args:
        node: A `preproc_include` node.
        get_text: Callable that slices node text from source.
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (set at the top of extract_metadata).
    """
    line = node.start_point[0] + 1
    for child in node.children:
        if child.type == "string_literal":
            for sub in child.children:
                if sub.type == "string_content":
                    path = get_text(sub)
                    metadata["name"] = path
                    metadata["include_path"] = path
                    _add_relationship(
                        metadata, "imports", path, line, is_system_include=False
                    )
                    return
        elif child.type == "system_lib_string":
            path = get_text(child).strip("<>")
            metadata["name"] = path
            metadata["include_path"] = path
            metadata["is_system_include"] = True
            _add_relationship(metadata, "imports", path, line, is_system_include=True)
            return


def extract_inheritance_relationships(
    node: Any,
    get_text: Callable[[Any], str],
    metadata: dict[str, Any],
) -> None:
    """Walk a `class_specifier`/`struct_specifier`'s `base_class_clause`.

    Emits one INHERITS relationship per base, in declaration order, e.g.
    `class Derived : public Base, private ns::Mixin<int>` emits two edges,
    target `"Base"` then target `"Mixin"` (both peeled to their leaf name via
    `_type_leaf_name`, dropping `ns::`/`<int>` the same way the call-site
    walk peels a call's leaf name into `callee_name` while keeping the full
    text elsewhere) -- each tagged with its `access` specifier
    (`"public"`/`"private"`/`"protected"`) when the grammar carries one as an
    explicit `access_specifier` child; a base with none (rare -- every
    example in practice specifies one) is tagged `access=None`.
    `union_specifier` never has a `base_class_clause` (unions cannot inherit
    in C++), so callers only invoke this for `class_specifier`/
    `struct_specifier`. C has no `base_class_clause` at all, so `CChunker`
    never calls this.

    Args:
        node: A `class_specifier` or `struct_specifier` node.
        get_text: Callable that slices node text from source.
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (set at the top of extract_metadata).
    """
    base_clause = next(
        (child for child in node.children if child.type == "base_class_clause"), None
    )
    if base_clause is None:
        return
    access = None
    for child in base_clause.children:
        if child.type == "access_specifier":
            access = get_text(child)
        elif child.type in ("type_identifier", "qualified_identifier", "template_type"):
            name = _type_leaf_name(child, get_text)
            if name is not None:
                _add_relationship(
                    metadata,
                    "inherits",
                    name,
                    child.start_point[0] + 1,
                    access=access,
                )
            access = None


def extract_instantiation_relationships(
    node: Any,
    get_text: Callable[[Any], str],
    metadata: dict[str, Any],
) -> None:
    """Walk `new_expression` nodes inside `node`, emitting INSTANTIATES edges.

    `new_expression`'s `type` field is `type_identifier` (`new Base()`),
    `qualified_identifier` (`new ns::Base()`), or `template_type`
    (`new Vector<int>()`) -- verified against the real grammar output
    (tmp/probe_cpp_grammar.py) -- peeled to a leaf name via `_type_leaf_name`,
    same as `extract_inheritance_relationships`'s bases.

    `new_expression` is a C++-only keyword (C has no `new`), so this is only
    ever called from `CppChunker`, not `CChunker` -- mirroring the plan's
    explicit inherits/instantiates-are-C++-only scoping.

    Iterative (explicit stack) -- same rationale as `extract_call_sites`.

    Args:
        node: A `function_definition` node (the chunk, or the inner function
            of a `template_declaration` chunk) being processed.
        get_text: Callable that slices node text from source.
        metadata: Metadata dict being populated; must already have a
            "relationships" list key (set at the top of extract_metadata).
    """
    sites: list[tuple[str, int]] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if current.type == "new_expression":
            type_node = current.child_by_field_name("type")
            name = _type_leaf_name(type_node, get_text)
            if name is not None:
                sites.append((name, type_node.start_point[0] + 1))
        stack.extend(current.children)
    # Stack-based traversal visits children in reverse order; sort by source
    # line so metadata["relationships"] reads in document order (mirrors
    # extract_call_sites).
    sites.sort(key=lambda s: s[1])
    for name, line in sites:
        _add_relationship(metadata, "instantiates", name, line)


# ---------------------------------------------------------------------------
# Shared preprocess/parse composition seam
# ---------------------------------------------------------------------------


class _CFamilyChunker(LanguageChunker):
    """Shared `preprocess_source_for_parse` composition for `CChunker` and
    `CppChunker`: purely textual preprocessor-conditional neutralization,
    then the parse-dependent macro-wrapped-declaration repair, in that
    order -- the repair locates ERROR spans by parsing, so it must run
    last, after every rewrite that only needs the raw text. `_neutralize`
    is the documented override point: `CudaChunker` layers its own,
    also-textual CUDA blanking in ahead of the base's preprocessor-
    conditional rewrite by overriding this method, not
    `preprocess_source_for_parse` itself, so it still inherits the repair
    below unchanged.
    """

    def _neutralize(self, source_bytes: bytes) -> bytes:
        return neutralize_preprocessor_conditionals(source_bytes)

    def preprocess_source_for_parse(self, source_bytes: bytes) -> bytes:
        return repair_macro_wrapped_declarations(
            self._neutralize(source_bytes), self.parser.parse
        )
