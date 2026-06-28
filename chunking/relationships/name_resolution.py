"""Pure AST name-resolution helpers shared by relationship extractors.

All functions accept a pre-parsed ``ast`` node and return a string or
``None``.  They are stateless, import-free from project code, and safe to
call from any extractor.

Parse-once contract: these helpers never call ``ast.parse`` and operate
solely on pre-parsed trees (compatible with the parse-once optimisation, #15).
"""

import ast


def dotted_name(node: ast.expr | None) -> str | None:
    """Return the full dotted name for a ``Name`` or ``Attribute`` chain.

    Examples::

        Name('os')                               -> "os"
        Attribute(Name('a'), 'b')                -> "a.b"
        Attribute(Attribute(Name('a'), 'b'), 'c') -> "a.b.c"
        Attribute(Call(...), 'b')                -> "b"  # non-Name root: suffix only
        None / other node types                  -> None

    The non-Name-root behaviour (dotted suffix only, no root segment) matches
    the legacy iterative ``_get_full_attribute_name`` used across six extractors.
    In practice callers pre-dispatch on node type, so all real inputs have a
    ``Name`` root and the algorithms agree.
    """
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        # parts is always non-empty (we entered the Attribute branch),
        # so the join never returns an empty string.
        return ".".join(reversed(parts))
    return None


def call_target_name(node: ast.expr | None) -> str | None:
    """Resolve the callable name for a ``Call``, ``Name``, or ``Attribute`` node.

    Examples::

        Name('Foo')                       -> "Foo"
        Attribute(Name('mod'), 'Foo')     -> "mod.Foo"
        Call(func=Name('Foo'))            -> "Foo"
        Call(func=Attribute(Name('m'), 'Foo')) -> "m.Foo"
        Call(func=Call(func=...))         -> recurses into innermost callable
        None / other node types           -> None

    Used by extractors that need the callable name: instantiation, decorator,
    and exception (``raise X()``).
    """
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted_name(node)
    if isinstance(node, ast.Call):
        return call_target_name(node.func)
    return None


def base_class_name(node: ast.AST | None, *, full: bool) -> str | None:
    """Resolve a class-base AST node to a name.

    Args:
        node: AST node from ``ClassDef.bases``.
        full: If ``True``, return the full dotted name for ``Attribute``
              nodes (e.g. ``"module.Parent"``).  If ``False``, return only
              the leaf attribute (e.g. ``"Parent"``).

    Use ``full=True`` for **inheritance** edges (cross-module paths are needed
    for accurate graph edges); use ``full=False`` for **implements** edges
    (``PROTOCOL_MARKERS`` matches on the bare leaf name, not the full path).

    Examples with ``full=True``::

        Name('Parent')                      -> "Parent"
        Attribute(Name('mod'), 'Parent')    -> "mod.Parent"
        Subscript(Name('Generic'), ...)     -> "Generic"
        Call(func=Name('Meta'))             -> "Meta"

    Examples with ``full=False``::

        Attribute(Name('typing'), 'Protocol') -> "Protocol"
        Attribute(Name('abc'), 'ABC')         -> "ABC"
    """
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return dotted_name(node) if full else node.attr
    if isinstance(node, ast.Subscript):
        # Generic base: Generic[T] or Protocol[T] — extract the base type.
        return base_class_name(node.value, full=full)
    if isinstance(node, ast.Call):
        # Metaclass: class Foo(metaclass=ABCMeta) — extract the callee.
        return base_class_name(node.func, full=full)
    return None
