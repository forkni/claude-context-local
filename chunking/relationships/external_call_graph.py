"""pyan3-based whole-project call-graph builder.

This module uses **pyan3** (``pip install pyan3``, import ``pyan``) to
produce a whole-project static call graph and translates the resulting
``caller_fqn → callee_fqn`` edges into ``(caller_raw_id, callee_raw_id,
line_number, is_method_call)`` tuples that the :class:`IndexWriteStage` can
inject directly into the persisted code graph.

Why pyan3?
----------
The in-house ``call_graph_extractor`` only resolves bare / qualified names
*within a single file*.  It cannot follow cross-module-qualified calls such
as ``pkg.mod.func()`` where caller and callee live in different files.  pyan3
performs a whole-project AST walk and resolves module imports, closing this
gap.

Hard dependency — no import guard
----------------------------------
pyan3 is a required dependency (``install_requires``).  There is no
``try/except ImportError`` guard and no ``enabled`` config flag.  External
edges are *always* built during a full index pass.  If the pyan3 analysis
itself fails at runtime, the error is caught and logged as a warning so it
never aborts the index.

Node → chunk_id mapping
-----------------------
For each pyan node we first try ``node.filename + node.ast_node.lineno``:
convert the absolute filename to a project-relative path, then call
``find_enclosing_chunk`` on the raw-id line map.  If that yields nothing
(no ``ast_node``, missing lineno, or outside the indexed file set), we fall
back to ``chunk_id_from_fqn(node.get_name(), ...)``.

The returned chunk_ids are **raw store-key ids** (with ``:start-end:`` line
range) because the code graph keys nodes by raw ids.  The caller in
:class:`IndexWriteStage` uses ``callee_id in graph`` / ``caller_id in graph``
prechecks so any stray unmatched id silently degrades to "no edge added".
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from evaluation.chunk_mapping import chunk_id_from_fqn, find_enclosing_chunk


# Flavors that correspond to callable definitions (not modules or classes).
_CALLABLE_FLAVORS = {"FUNCTION", "METHOD", "STATICMETHOD", "CLASSMETHOD"}

# Flavors that indicate a method call (useful for ``is_method_call`` flag).
_METHOD_FLAVORS = {"METHOD", "STATICMETHOD", "CLASSMETHOD"}


def _gather_py_files(project_root: Path) -> list[str]:
    """Collect all .py files under *project_root*, excluding noise dirs.

    Excluded: test directories (``/tests/``, ``/test/``), the virtualenv
    (``.venv``), hidden directories (starting with ``.``), and ``__pycache__``.

    Returns:
        Sorted list of absolute path strings, suitable for pyan3.
    """
    excluded_segments = {".venv", "tests", "test", "__pycache__"}
    files: list[str] = []
    for p in project_root.rglob("*.py"):
        # Check any path segment matches an excluded name or starts with '.'
        skip = False
        for part in p.relative_to(project_root).parts[:-1]:  # skip file name itself
            if part in excluded_segments or part.startswith("."):
                skip = True
                break
        if not skip:
            files.append(str(p))
    return sorted(files)


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


def build_call_edges(
    project_root: Path,
    raw_line_map: dict[str, list[tuple[int, int, str]]],
    logger: logging.Logger,
) -> list[tuple[str, str, int, bool]]:
    """Run pyan3 on the project and return cross-module call edges.

    Args:
        project_root: Absolute path to the project root.
        raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list,
            built with ``normalize=False`` so ids match graph node keys.
        logger: Logger for progress and warning messages.

    Returns:
        Deduplicated list of ``(caller_raw_id, callee_raw_id, line_number,
        is_method_call)`` tuples for edges where both endpoints mapped to a
        known chunk_id.  *line_number* is the callee's definition line (0 if
        unavailable); *is_method_call* is True when the caller flavor is a
        method variant.
    """
    from pyan.analyzer import CallGraphVisitor  # hard dep — no guard

    py_files = _gather_py_files(project_root)

    # Fix 1: Scope to indexed files only — eliminates unindexed install/venv trees
    # (e.g. Scripts/, site-packages/) that can never produce injectable edges.
    if raw_line_map:
        indexed_relpaths = set(raw_line_map.keys())
        scoped: list[str] = []
        for fn in py_files:
            try:
                rel = str(Path(fn).resolve().relative_to(project_root)).replace(
                    "\\", "/"
                )
                if rel in indexed_relpaths:
                    scoped.append(fn)
            except ValueError:
                pass  # outside project_root — not in index, skip
        py_files = scoped

    if not py_files:
        logger.warning("[PYAN] No .py files found under %s — skipping", project_root)
        return []

    # Fix 2: Pre-validate with ast.parse — one malformed file must not abort the
    # whole pass (pyan's prescan raises SyntaxError on the first bad file).
    parseable: list[str] = []
    for fn in py_files:
        try:
            source = Path(fn).read_text(encoding="utf-8", errors="replace")
            ast.parse(source, filename=fn)
            parseable.append(fn)
        except SyntaxError as exc:
            logger.warning("[PYAN] Skipping unparseable file %s: %s", fn, exc)
        except (OSError, ValueError) as exc:
            logger.warning("[PYAN] Skipping unreadable file %s: %s", fn, exc)
    py_files = parseable

    if not py_files:
        logger.warning("[PYAN] No parseable .py files remain — skipping edge injection")
        return []

    logger.info("[PYAN] Analysing %d Python files with pyan3...", len(py_files))

    # Silence pyan's own verbose logging while letting warnings/errors through.
    pyan_logger = logging.getLogger("pyan")
    pyan_logger.setLevel(logging.WARNING)

    visitor = CallGraphVisitor(py_files, root=str(project_root), logger=pyan_logger)

    edges: set[tuple[str, str, int, bool]] = set()
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

            # Skip module-flavored callees (import resolutions) and anything
            # whose file is outside the project (stdlib, venv).
            if callee_flavor == "MODULE":
                skipped += 1
                continue

            callee_fn: str | None = getattr(callee_node, "filename", None)
            if callee_fn:
                try:
                    Path(callee_fn).resolve().relative_to(project_root)
                except ValueError:
                    skipped += 1
                    continue  # outside project root → stdlib / venv / external

            callee_id = _node_to_raw_chunk_id(callee_node, project_root, raw_line_map)
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

            edges.add((caller_id, callee_id, line_num, is_method_call))

    result = sorted(edges)
    logger.info(
        "[PYAN] Resolved %d cross-module call edges (%d skipped / unmappable)",
        len(result),
        skipped,
    )
    return result
