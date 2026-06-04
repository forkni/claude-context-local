"""pyan3-based whole-project call-graph builder.

This module uses **pyan3** (``pip install pyan3``, import ``pyan``) to
produce a whole-project static call graph and translates the resulting
``caller_fqn → callee_fqn`` edges into :class:`~.call_edge_resolver.ResolvedEdge`
instances that the resolver pipeline merges and injects into the code graph.

Why pyan3?
----------
The in-house ``call_graph_extractor`` only resolves bare / qualified names
*within a single file*.  It cannot follow cross-module-qualified calls such
as ``pkg.mod.func()`` where caller and callee live in different files.  pyan3
performs a whole-project AST walk and resolves module imports, closing this
gap.

Optional dependency — import guard
-----------------------------------
pyan3 is an **optional** dependency in the ``[callgraph]`` install extra.  A
``try/except ImportError`` guard is used so the project's Apache-2.0
distribution does not hard-depend on pyan3's GPL-2.0 licence.  Call
:func:`pyan_available` to test at runtime whether the extra is installed.

When pyan3 is absent, :class:`PyanResolver` logs one INFO message and returns
an empty edge list — indexing continues with the in-house AST edges only.

Node → chunk_id mapping
-----------------------
For each pyan node we first try ``node.filename + node.ast_node.lineno``:
convert the absolute filename to a project-relative path, then call
``find_enclosing_chunk`` on the raw-id line map.  If that yields nothing
(no ``ast_node``, missing lineno, or outside the indexed file set), we fall
back to ``chunk_id_from_fqn(node.get_name(), ...)``.

The returned chunk_ids are **raw store-key ids** (with ``:start-end:`` line
range) because the code graph keys nodes by raw ids.  The injection seam uses
``callee_id in graph`` / ``caller_id in graph`` prechecks so any stray
unmatched id silently degrades to "no edge added".
"""

from __future__ import annotations

import logging
from pathlib import Path

from evaluation.chunk_mapping import chunk_id_from_fqn, find_enclosing_chunk

from .call_edge_resolver import (
    ResolvedEdge,
    gather_py_files,
    scope_to_indexed_files,
    validate_py_files,
)


# ---------------------------------------------------------------------------
# Optional pyan3 import — guarded for GPL-2.0 licence hygiene
# ---------------------------------------------------------------------------
try:
    from pyan.analyzer import (
        CallGraphVisitor as _CallGraphVisitor,  # type: ignore[import-untyped]
    )

    class _TrackedVisitor(_CallGraphVisitor):
        """``CallGraphVisitor`` subclass that records which edges were added by
        ``expand_unknowns`` wildcard fan-out so the resolver can assign them a
        lower confidence (0.6) than directly-resolved edges (0.75).

        ``postprocess()`` is called automatically from ``__init__`` via
        ``process()``.  We override it to run each postprocessor stage
        individually, capturing a snapshot of ``uses_edges`` before
        ``expand_unknowns`` fires and diffing afterwards.  The resulting
        ``expanded_edges`` set contains only the edges that (a) were added by
        wildcard fan-out AND (b) survived the subsequent ``cull_inherited`` /
        ``collapse_inner`` passes.
        """

        expanded_edges: set[tuple[object, object]]

        def postprocess(self) -> None:  # type: ignore[override]
            from pyan.postprocessor import (  # type: ignore[import-untyped]
                collapse_inner,
                contract_nonexistents,
                cull_inherited,
                expand_unknowns,
                resolve_imports,
            )

            resolve_imports(self)
            contract_nonexistents(self)
            # Snapshot *before* wildcard fan-out.
            pre: dict[object, frozenset[object]] = {
                f: frozenset(ts) for f, ts in self.uses_edges.items()
            }
            expand_unknowns(self)
            cull_inherited(self)
            collapse_inner(self)
            # Surviving edges that were not in the pre-expansion snapshot.
            self.expanded_edges = {
                (f, t)
                for f, ts in self.uses_edges.items()
                for t in ts
                if t not in pre.get(f, frozenset())
            }

    _PYAN_AVAILABLE = True
except ImportError:
    _PYAN_AVAILABLE = False

# Flavors that correspond to callable definitions (not modules or classes).
_CALLABLE_FLAVORS = {"FUNCTION", "METHOD", "STATICMETHOD", "CLASSMETHOD"}

# Flavors accepted as callees: callables + CLASS (instantiation calls e.g.
# ``MyClass()`` resolve to the class node; pyan also emits a separate
# METHOD edge to ``MyClass.__init__`` when the class is known).
# NAME, ATTRIBUTE, UNKNOWN, IMPORTEDITEM are excluded — they produce phantom
# "call into the enclosing function" edges via filename+lineno mapping.
_CALLEE_FLAVORS = _CALLABLE_FLAVORS | {"CLASS"}

# Flavors that indicate a method call (useful for ``is_method_call`` flag).
_METHOD_FLAVORS = {"METHOD", "STATICMETHOD", "CLASSMETHOD"}


# ---------------------------------------------------------------------------
# Public availability probe
# ---------------------------------------------------------------------------


def pyan_available() -> bool:
    """Return True if pyan3 is installed and the import succeeded.

    Use this guard before calling :class:`PyanResolver` or :func:`build_call_edges`
    in tests or tooling that wants to skip the pyan pass when the ``[callgraph]``
    extra is absent.
    """
    return _PYAN_AVAILABLE


# ---------------------------------------------------------------------------
# Backward-compat alias for tests that import ``_gather_py_files`` directly
# ---------------------------------------------------------------------------
_gather_py_files = gather_py_files


def _node_to_raw_chunk_id(
    node: object,
    project_root: Path,
    raw_line_map: dict[str, list[tuple[int, int, str]]],
) -> str | None:
    """Map a pyan node to a raw graph store-key chunk_id.

    Strategy:
    1. ``node.filename + node.ast_node.lineno`` → ``find_enclosing_chunk``
    2. Fallback: ``chunk_id_from_fqn(node.get_name(), ...)``

    Returns:
        Raw chunk_id string, or *None* if unmappable.
    """
    # Attempt 1: filename + lineno
    fn: str | None = getattr(node, "filename", None)
    ast_node = getattr(node, "ast_node", None)
    if fn and ast_node is not None:
        lineno: int | None = getattr(ast_node, "lineno", None)
        if lineno is not None:
            try:
                rel = Path(fn).resolve().relative_to(project_root)
                rel_str = str(rel).replace("\\", "/")
                cid = find_enclosing_chunk(raw_line_map, rel_str, lineno)
                if cid is not None:
                    return cid
            except ValueError:
                pass  # not under project_root → fallthrough

    # Attempt 2: FQN-based lookup
    fqn: str = node.get_name()  # type: ignore[attr-defined]
    if fqn:
        return chunk_id_from_fqn(fqn, raw_line_map, project_root)
    return None


class PyanResolver:
    """Call-edge resolver backed by pyan3 whole-project static analysis.

    Implements :class:`~.call_edge_resolver.CallEdgeResolver`.

    pyan3 is a **GPL-2.0** library.  This class is only instantiated when the
    ``[callgraph]`` optional extra is installed; the Apache-2.0 core of this
    project does not hard-depend on it at import time.

    Confidence:  0.75 — whole-project name resolution is more accurate than the
    single-file in-house extractor but cannot resolve calls through return values
    or duck-typed dispatch.
    """

    name: str = "pyan"
    base_confidence: float = 0.75

    def available(self) -> bool:
        """Return True if pyan3 was successfully imported at module load time."""
        return _PYAN_AVAILABLE

    def resolve(
        self,
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Run pyan3 on the project and return :class:`ResolvedEdge` instances.

        Args:
            project_root: Absolute path to the project root.
            raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list,
                built with ``normalize=False`` so ids match graph node keys.
            logger: Logger for progress and warning messages.

        Returns:
            Deduplicated list of :class:`ResolvedEdge` for edges where both
            endpoints mapped to a known chunk_id.
        """
        if not _PYAN_AVAILABLE:
            logger.info(
                "[PYAN] pyan3 not installed — skipping cross-module edge injection. "
                "Install the '[callgraph]' extra for higher-recall call edges."
            )
            return []

        py_files = gather_py_files(project_root)

        # Scope to indexed files only — eliminates unindexed install/venv trees
        # (e.g. Scripts/, site-packages/) that can never produce injectable edges.
        if raw_line_map:
            py_files = scope_to_indexed_files(
                py_files, set(raw_line_map.keys()), project_root
            )

        if not py_files:
            logger.warning(
                "[PYAN] No .py files found under %s — skipping", project_root
            )
            return []

        # Pre-validate with ast.parse — one malformed file must not abort the
        # whole pass (pyan's prescan raises SyntaxError on the first bad file).
        py_files = validate_py_files(py_files, logger, source_name="PYAN")

        if not py_files:
            logger.warning(
                "[PYAN] No parseable .py files remain — skipping edge injection"
            )
            return []

        logger.info("[PYAN] Analysing %d Python files with pyan3...", len(py_files))

        # Silence pyan's own verbose logging while letting warnings/errors through.
        pyan_logger = logging.getLogger("pyan")
        pyan_logger.setLevel(logging.WARNING)

        # Use _TrackedVisitor to record which edges were added by expand_unknowns
        # so they can be assigned a lower confidence (0.6 vs 0.75).
        visitor = _TrackedVisitor(py_files, root=str(project_root), logger=pyan_logger)
        expanded = getattr(visitor, "expanded_edges", set())
        wildcard_confidence: float = 0.6  # expand_unknowns fan-out edges

        # 5-tuple: (caller_id, callee_id, line_num, is_method_call, confidence)
        raw_edges: set[tuple[str, str, int, bool, float]] = set()
        skipped = 0

        for caller_node, callees in visitor.uses_edges.items():
            caller_flavor: str = caller_node.flavor.name  # type: ignore[attr-defined]

            # Skip module-level "callers" — those represent import statements, not
            # real function/method call sites.
            if caller_flavor not in _CALLABLE_FLAVORS:
                skipped += len(callees)
                continue

            caller_id = _node_to_raw_chunk_id(caller_node, project_root, raw_line_map)
            if caller_id is None:
                skipped += len(callees)
                continue

            is_method_call = caller_flavor in _METHOD_FLAVORS

            for callee_node in callees:
                callee_flavor: str = callee_node.flavor.name  # type: ignore[attr-defined]

                # Only accept callable flavors + CLASS (instantiation).
                # NAME, ATTRIBUTE, UNKNOWN, IMPORTEDITEM produce phantom "call into
                # enclosing function" edges via filename+lineno mapping — drop them.
                if callee_flavor not in _CALLEE_FLAVORS:
                    skipped += 1
                    continue

                # Drop wildcard/unresolved nodes left over from expand_unknowns
                # that contract_nonexistents didn't fully eliminate.
                if not getattr(callee_node, "defined", True):
                    skipped += 1
                    continue

                callee_fn: str | None = getattr(callee_node, "filename", None)
                if callee_fn:
                    try:
                        Path(callee_fn).resolve().relative_to(project_root)
                    except ValueError:
                        skipped += 1
                        continue  # outside project root → stdlib / venv / external

                callee_id = _node_to_raw_chunk_id(
                    callee_node, project_root, raw_line_map
                )
                if callee_id is None:
                    skipped += 1
                    continue

                # Skip self-loops (recursive calls).
                if caller_id == callee_id:
                    skipped += 1
                    continue

                # Line number: callee definition line (best effort).
                callee_ast = getattr(callee_node, "ast_node", None)
                line_num: int = getattr(callee_ast, "lineno", 0) if callee_ast else 0

                # Assign lower confidence to edges added by wildcard fan-out.
                confidence = (
                    wildcard_confidence
                    if (caller_node, callee_node) in expanded
                    else self.base_confidence
                )
                raw_edges.add(
                    (caller_id, callee_id, line_num, is_method_call, confidence)
                )

        result = [
            ResolvedEdge(
                caller_id=c,
                callee_id=t,
                line=ln,
                is_method=im,
                source="pyan",
                confidence=conf,
            )
            for c, t, ln, im, conf in sorted(raw_edges)
        ]
        logger.info(
            "[PYAN] Resolved %d cross-module call edges (%d skipped / unmappable)",
            len(result),
            skipped,
        )
        return result


def build_call_edges(
    project_root: Path,
    raw_line_map: dict[str, list[tuple[int, int, str]]],
    logger: logging.Logger,
) -> list[tuple[str, str, int, bool]]:
    """Backward-compatible wrapper around :class:`PyanResolver`.

    Delegates to ``PyanResolver().resolve()`` and converts each
    :class:`~.call_edge_resolver.ResolvedEdge` back to the legacy
    ``(caller_id, callee_id, line_number, is_method_call)`` tuple format.

    New code should use the resolver pipeline (``run_resolvers``) instead of
    calling this function directly.

    Args:
        project_root: Absolute path to the project root.
        raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list.
        logger: Logger for progress and warning messages.

    Returns:
        Sorted list of ``(caller_raw_id, callee_raw_id, line_number,
        is_method_call)`` tuples.
    """
    resolver = PyanResolver()
    edges = resolver.resolve(project_root, raw_line_map, logger)
    return [(e.caller_id, e.callee_id, e.line, e.is_method) for e in edges]
