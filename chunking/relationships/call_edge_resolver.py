"""Resolver protocol, ResolvedEdge, and shared helpers for the call-graph pipeline.

Architecture — two namespaces
------------------------------
The resolver pipeline chains multiple static-analysis backends at increasing accuracy.
There are **two distinct confidence namespaces** that must not be conflated:

``confidence`` (tag attribute on graph edges)
    Qualitative label produced by the AST chunking pass: ``"exact"``,
    ``"recovered"``, or ``"ambiguous"``.  Written via
    ``graph_storage.add_call_edge`` during chunking.  These are *not* numeric
    scores and are *not* compared against :class:`ResolverConfidence` thresholds.

``resolver_confidence`` (numeric score on graph edges)
    Numeric precedence written by the resolver pipeline (Stage 1–3 below).
    Edges without this attribute default to ``0.0``, so *every* resolver reliably
    upgrades them via the keep-max merge in :func:`run_resolvers`.

Resolver ladder (``resolver_confidence`` values; see :class:`ResolverConfidence`)::

    pyan wildcard (0.60)  →  pyan (0.75)  →  libcst (0.90)  →  lsp (0.98)

*AST edges* ride a separate ``add_call_edge`` / ``extract_calls`` rail and are
written during chunking — they are not :class:`CallEdgeResolver` instances and
do not participate in the keep-max merge.  The pipeline only manages the
*additional* resolvers that run at full-index time:

- **PyanResolver** (Stage 1)  — whole-project name resolution; GPL-2.0 optional extra.
  Wildcard fan-out edges (``expand_unknowns``) get :attr:`ResolverConfidence.PYAN_WILDCARD`.
- **LibCSTResolver** (Stage 2) — ``FullyQualifiedNameProvider``; MIT, permissive.
- **LSPResolver** (Stage 3)   — basedpyright JSON-RPC call hierarchy; opt-in.

Each resolver emits :class:`ResolvedEdge` instances.  :func:`run_resolvers` merges all
edges from all available resolvers by ``(caller_id, callee_id)`` key, keeping the
highest-confidence version of each edge.

Shared file-collection helpers (previously duplicated in ``external_call_graph.py``)
are also here so that Stage 2/3 resolvers can reuse them without import cycles.
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable


if TYPE_CHECKING:
    pass  # mypy/pyright stubs only


# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedEdge:
    """A call-graph edge with provenance metadata.

    Attributes:
        caller_id: Raw store-key chunk_id of the caller
            (e.g. ``"pkg/mod.py:10-20:function:fn"``).
        callee_id: Raw store-key chunk_id of the callee.
        line: Line number of the callee's *definition* (0 if unknown).
        is_method: True if the caller is a method variant
            (METHOD / STATICMETHOD / CLASSMETHOD).
        source: Resolver that produced this edge:
            ``"ast"`` | ``"pyan"`` | ``"libcst"`` | ``"lsp"``.
        confidence: Numeric precedence for this resolver (higher = more trusted).
            Used by :func:`run_resolvers` to pick the authoritative version when
            multiple resolvers produce an edge for the same (caller, callee) pair.
    """

    caller_id: str
    callee_id: str
    line: int
    is_method: bool
    source: str
    confidence: float


# ---------------------------------------------------------------------------
# Confidence constants — single source of truth for all resolvers
# ---------------------------------------------------------------------------


class ResolverConfidence:
    """Numeric ``resolver_confidence`` values for each resolver stage.

    These are the authoritative constants; each resolver imports the
    appropriate value rather than hard-coding a float literal.

    Ladder (ascending precision)::

        PYAN_WILDCARD (0.60) — pyan ``expand_unknowns`` fan-out edges
        PYAN          (0.75) — pyan whole-project name resolution
        LIBCST        (0.90) — LibCST ``FullyQualifiedNameProvider``
        LSP           (0.98) — basedpyright type-inference call hierarchy
    """

    PYAN_WILDCARD: float = 0.60
    """pyan ``expand_unknowns`` wildcard fan-out: lower-confidence speculative edges."""

    PYAN: float = 0.75
    """pyan whole-project name resolution."""

    LIBCST: float = 0.90
    """LibCST ``FullyQualifiedNameProvider`` cross-module resolution."""

    LSP: float = 0.98
    """basedpyright type-inference–level call hierarchy."""


# ---------------------------------------------------------------------------
# Resolver protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class CallEdgeResolver(Protocol):
    """Protocol that all call-edge resolvers must satisfy.

    The injection seam (:class:`~search.index_write_stage.IndexWriteStage`)
    only depends on this protocol — it never imports resolver internals.
    Concrete implementations: ``PyanResolver``, ``LibCSTResolver``,
    ``LSPResolver``.
    """

    name: str
    """Short resolver name: ``"ast"`` | ``"pyan"`` | ``"libcst"`` | ``"lsp"``."""

    base_confidence: float
    """Default precedence weight for edges produced by this resolver."""

    def available(self) -> bool:
        """Return True if the resolver's optional dependency is present.

        Must not raise — on import error or missing binary, return False
        and log once at INFO level.
        """
        ...

    def resolve(
        self,
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Run the resolver and return call edges.

        Args:
            project_root: Absolute path to the project root.
            raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list,
                built with ``normalize=False`` so ids match graph node keys.
            logger: Logger for progress and warning messages.

        Returns:
            List of :class:`ResolvedEdge`.  The injection seam filters edges
            whose endpoints are not in the graph; this method need not do so.

        Contract:
            Must never raise — catch all resolver errors and log them.
            Return an empty list on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Shared file-collection helpers (reused by all resolvers)
# ---------------------------------------------------------------------------


def gather_py_files(project_root: Path) -> list[str]:
    """Collect .py files under *project_root*, excluding noise directories.

    Excluded: virtualenv (``.venv``), test directories (``tests/``, ``test/``),
    hidden directories (starting with ``"."``), and ``__pycache__``.

    Args:
        project_root: Absolute path to the project root.

    Returns:
        Sorted list of absolute path strings.
    """
    excluded_segments = {".venv", "tests", "test", "__pycache__"}
    files: list[str] = []
    for p in project_root.rglob("*.py"):
        skip = False
        for part in p.relative_to(project_root).parts[:-1]:  # skip file name itself
            if part in excluded_segments or part.startswith("."):
                skip = True
                break
        if not skip:
            files.append(str(p))
    return sorted(files)


def scope_to_indexed_files(
    py_files: list[str],
    indexed_relpaths: set[str],
    project_root: Path,
) -> list[str]:
    """Filter *py_files* to those that appear in *indexed_relpaths*.

    Prevents injection of edges for files outside the index (install trees,
    ``Scripts/``, ``site-packages/``).

    Args:
        py_files: Absolute .py file paths to filter.
        indexed_relpaths: Relative paths (forward-slash, project-relative) of
            files present in the metadata index.
        project_root: Project root for computing relative paths.

    Returns:
        Filtered list of absolute paths — same relative order as *py_files*.
    """
    scoped: list[str] = []
    for fn in py_files:
        try:
            rel = str(Path(fn).resolve().relative_to(project_root)).replace("\\", "/")
            if rel in indexed_relpaths:
                scoped.append(fn)
        except ValueError:
            pass  # outside project_root — skip silently
    return scoped


def validate_py_files(
    py_files: list[str],
    logger: logging.Logger,
    source_name: str = "RESOLVER",
) -> list[str]:
    """Filter *py_files* to those that pass ``ast.parse``.

    One unparseable file (e.g. a TouchDesigner YAML-in-``.py`` config) must
    not abort edge injection for the whole project.

    Args:
        py_files: Absolute .py file paths to validate.
        logger: Logger for warning messages about skipped files.
        source_name: Upper-cased resolver name used in log prefixes.

    Returns:
        Subset of *py_files* that are syntactically valid Python.
    """
    parseable: list[str] = []
    for fn in py_files:
        try:
            source = Path(fn).read_text(encoding="utf-8", errors="replace")
            ast.parse(source, filename=fn)
            parseable.append(fn)
        except SyntaxError as exc:
            logger.warning(
                "[%s] Skipping unparseable file %s: %s", source_name, fn, exc
            )
        except (OSError, ValueError) as exc:
            logger.warning("[%s] Skipping unreadable file %s: %s", source_name, fn, exc)
    return parseable


# ---------------------------------------------------------------------------
# Merge / orchestration
# ---------------------------------------------------------------------------


def run_resolvers(
    resolvers: list[CallEdgeResolver],
    project_root: Path,
    raw_line_map: dict[str, list[tuple[int, int, str]]],
    logger: logging.Logger,
) -> dict[tuple[str, str], ResolvedEdge]:
    """Run each available resolver and merge edges by maximum confidence.

    Resolvers are run in *ascending* ``base_confidence`` order so that
    higher-confidence resolvers overwrite lower-confidence entries for the same
    ``(caller_id, callee_id)`` pair.

    Args:
        resolvers: Resolver instances in any order; sorted internally by
            ``base_confidence`` before execution.
        project_root: Passed through to each resolver's ``resolve()`` call.
        raw_line_map: Passed through to each resolver's ``resolve()`` call.
        logger: Logger for per-resolver progress messages.

    Returns:
        Dict keyed by ``(caller_id, callee_id)`` → highest-confidence
        :class:`ResolvedEdge`.  When two resolvers produce equal confidence for
        the same pair, the first (lower-precedence) value is kept.
    """
    import traceback

    merged: dict[tuple[str, str], ResolvedEdge] = {}

    # Sort ascending so higher-confidence resolvers overwrite lower-confidence ones.
    for resolver in sorted(resolvers, key=lambda r: r.base_confidence):
        if not resolver.available():
            logger.info(
                "[RESOLVERS] %s resolver unavailable (optional dep missing) — "
                "install '[callgraph]' extra for higher-recall cross-module edges",
                resolver.name,
            )
            continue

        try:
            edges = resolver.resolve(project_root, raw_line_map, logger)
        except Exception:
            logger.warning(
                "[RESOLVERS] %s resolver failed (non-fatal):\n%s",
                resolver.name,
                traceback.format_exc(),
            )
            continue

        added = upgraded = 0
        for edge in edges:
            key = (edge.caller_id, edge.callee_id)
            existing = merged.get(key)
            if existing is None:
                merged[key] = edge
                added += 1
            elif edge.confidence > existing.confidence:
                merged[key] = edge
                upgraded += 1

        logger.info(
            "[RESOLVERS] %s: %d edges → added=%d, upgraded=%d (total merged so far: %d)",
            resolver.name,
            len(edges),
            added,
            upgraded,
            len(merged),
        )

    return merged
