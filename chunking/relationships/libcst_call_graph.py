"""LibCST-based call-graph resolver for the resolver pipeline.

Uses LibCST's ``FullyQualifiedNameProvider`` (FQN) and ``PositionProvider``
to resolve call-sites to fully-qualified callee names, then maps both
endpoints to graph chunk_ids via the shared helpers in
``evaluation/chunk_mapping.py``.

Why LibCST?
-----------
LibCST's ``FullRepoManager`` + ``FullyQualifiedNameProvider`` performs
cross-module import tracking and resolves qualified names with higher
precision than single-file AST inspection or pyan3's whole-project
name-matching.  As a **MIT-licensed pure-Python library**, it is the
recommended primary resolver for the ``[callgraph]`` optional extra.

Confidence: 0.90 — cross-file FQN resolution with static scope analysis.
When unavailable, only lower-confidence resolvers (pyan 0.75, AST) contribute edges.

Optional dependency
-------------------
``libcst`` is available only when the ``[callgraph]`` install extra is
present::

    pip install -e ".[callgraph]"

When absent, :class:`LibCSTResolver` logs one INFO message and returns
``[]`` — indexing continues with lower-precision resolvers.
"""

from __future__ import annotations

import logging
from pathlib import Path

from evaluation.chunk_mapping import chunk_id_from_fqn

from .call_edge_resolver import (
    ResolvedEdge,
    ResolverConfidence,
    gather_py_files,
    scope_to_indexed_files,
    validate_py_files,
)


# ---------------------------------------------------------------------------
# Optional libcst import — guarded for licence + optional-dep hygiene
# ---------------------------------------------------------------------------
try:
    import libcst as cst
    from libcst.metadata import (
        FullRepoManager,
        FullyQualifiedNameProvider,
        MetadataWrapper,
        PositionProvider,
    )

    _LIBCST_AVAILABLE = True
except ImportError:
    _LIBCST_AVAILABLE = False


def libcst_available() -> bool:
    """Return True if libcst is installed and the import succeeded."""
    return _LIBCST_AVAILABLE


# ---------------------------------------------------------------------------
# Visitor
# ---------------------------------------------------------------------------


if _LIBCST_AVAILABLE:

    class _CallVisitor(cst.CSTVisitor):  # type: ignore[misc]
        """Collect ``(caller_fqn, callee_fqn, line)`` triples from a module.

        *Caller* is identified by walking up from a ``cst.Call`` node to
        the nearest enclosing ``FunctionDef`` or ``AsyncFunctionDef``.
        *Callee* is the FQN of the outermost ``Name`` / ``Attribute``
        accessed by the call.
        """

        METADATA_DEPENDENCIES = (
            FullyQualifiedNameProvider,  # type: ignore[name-defined]
            PositionProvider,  # type: ignore[name-defined]
        )

        def __init__(self) -> None:
            self.edges: list[tuple[str, str, int]] = []
            self._fn_stack: list[str] = []

        # ------------------------------------------------------------------
        # Track enclosing function scope
        # ------------------------------------------------------------------

        def visit_FunctionDef(self, node: cst.FunctionDef) -> bool:  # noqa: N802
            fqns = self.get_metadata(FullyQualifiedNameProvider, node, set())
            # Use first FQN (there is typically exactly one for a function def)
            name = next(iter(fqns)).name if fqns else ""
            self._fn_stack.append(name)
            return True

        def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:  # noqa: N802
            self._fn_stack.pop()

        def visit_AsyncFunctionDef(self, node: cst.AsyncFunctionDef) -> bool:  # noqa: N802  # type: ignore[name-defined]
            fqns = self.get_metadata(FullyQualifiedNameProvider, node, set())
            name = next(iter(fqns)).name if fqns else ""
            self._fn_stack.append(name)
            return True

        def leave_AsyncFunctionDef(  # noqa: N802  # type: ignore[name-defined]
            self,
            original_node: cst.AsyncFunctionDef,  # type: ignore[name-defined]
        ) -> None:
            self._fn_stack.pop()

        # ------------------------------------------------------------------
        # self/cls call resolution helper
        # ------------------------------------------------------------------

        def _resolve_self_call(
            self,
            func_node: cst.BaseExpression,  # type: ignore[name-defined]
        ) -> str | None:
            """Synthesise FQN for ``self.method()`` / ``cls.method()`` calls.

            ``FullyQualifiedNameProvider`` cannot resolve attribute accesses on
            ``self`` or ``cls`` because it does not track instance-level types.
            When the callee is ``<Name("self"|"cls")>.<attr>`` and FQN resolution
            returned nothing, we derive the enclosing class FQN from the *caller's*
            FQN (already on ``_fn_stack``): ``pkg.mod.MyClass.method`` → class FQN
            is ``pkg.mod.MyClass``.  We then synthesise ``<class_fqn>.<attr>`` as
            the callee FQN.

            ``chunk_id_from_fqn`` handles ``module.Class.method`` via its
            progressive split; inherited methods safely return *None* — no
            wrong edge is emitted in that case.

            Returns the synthesised FQN string, or *None* if the call doesn't
            match the ``self.x`` / ``cls.x`` pattern or the stack has no method FQN.
            """
            if not isinstance(func_node, cst.Attribute):
                return None
            value = func_node.value
            if not isinstance(value, cst.Name):
                return None
            if value.value not in ("self", "cls"):
                return None
            if not self._fn_stack or not self._fn_stack[-1]:
                return None
            # Split "pkg.mod.MyClass.method" → class_fqn="pkg.mod.MyClass"
            parts = self._fn_stack[-1].rsplit(".", 1)
            if len(parts) < 2:
                return None  # top-level function — not a method
            class_fqn = parts[0]
            method_name: str = func_node.attr.value  # type: ignore[attr-defined]
            return f"{class_fqn}.{method_name}"

        # ------------------------------------------------------------------
        # Capture call sites
        # ------------------------------------------------------------------

        def visit_Call(self, node: cst.Call) -> None:  # noqa: N802
            if not self._fn_stack or not self._fn_stack[-1]:
                return  # module-level call — skip

            caller_fqn = self._fn_stack[-1]

            # Resolve the callee expression to a FQN set.
            # Filter out ``<locals>`` FQNs — LibCST emits these for attribute
            # accesses on local variables (e.g. ``self.helper`` →
            # ``MyClass.m.<locals>.self.helper``) which cannot be mapped to
            # indexed chunks.  Fall back to self/cls synthesis for those.
            func_node = node.func
            fqns = self.get_metadata(FullyQualifiedNameProvider, func_node, set())
            usable_fqns = {q for q in fqns if "<locals>" not in q.name}
            if usable_fqns:
                # Prefer the most-specific FQN (shortest path = fewest qualifications)
                callee_fqn: str | None = min((q.name for q in usable_fqns), key=len)
            else:
                # FQN resolution failed or yielded only <locals> FQNs —
                # try self/cls attribute call synthesis via _fn_stack.
                callee_fqn = self._resolve_self_call(func_node)
            if callee_fqn is None:
                return

            # Line number from position metadata
            # pyrefly: ignore [bad-argument-type]  # libcst stub: default typed as CodeRange, not Optional
            pos = self.get_metadata(PositionProvider, node, None)
            line = pos.start.line if pos is not None else 0

            self.edges.append((caller_fqn, callee_fqn, line))


# ---------------------------------------------------------------------------
# LibCSTResolver
# ---------------------------------------------------------------------------


class LibCSTResolver:
    """Call-edge resolver backed by LibCST ``FullyQualifiedNameProvider``.

    Implements :class:`~.call_edge_resolver.CallEdgeResolver`.

    Uses ``FullRepoManager`` to build a cross-file type environment and
    resolves every ``Call`` node in every indexed Python file to a fully-
    qualified callee name.  Both endpoints are mapped to raw graph
    chunk_ids via the shared helpers in ``evaluation/chunk_mapping.py``.

    Confidence: 0.90 — FQN-level cross-module resolution.
    """

    name: str = "libcst"
    base_confidence: float = ResolverConfidence.LIBCST

    def __init__(self, use_pyproject_toml: bool = False) -> None:
        """Initialise the resolver.

        Args:
            use_pyproject_toml: When *True*, ``FullRepoManager`` derives each
                file's module FQN from the nearest ``pyproject.toml`` package
                root instead of the bare repo root.  Enable this for
                *src-layout* projects (e.g. ``src/mypkg/``) where the default
                would produce ``src.mypkg.mod`` instead of ``mypkg.mod``.
                Default: ``False`` (flat-layout, module FQNs relative to root).
        """
        self._use_pyproject_toml = use_pyproject_toml

    def available(self) -> bool:
        """Return True if libcst was successfully imported at module load time."""
        return _LIBCST_AVAILABLE

    def resolve(
        self,
        project_root: Path,
        raw_line_map: dict[str, list[tuple[int, int, str]]],
        logger: logging.Logger,
    ) -> list[ResolvedEdge]:
        """Run LibCST on the project and return :class:`ResolvedEdge` instances.

        Args:
            project_root: Absolute path to the project root.
            raw_line_map: Per-file sorted ``(start, end, raw_chunk_id)`` list,
                built with ``normalize=False`` so ids match graph node keys.
            logger: Logger for progress and warning messages.

        Returns:
            Deduplicated list of :class:`ResolvedEdge` for edges where both
            endpoints mapped to a known chunk_id.
        """
        if not _LIBCST_AVAILABLE:
            logger.info(
                "[LIBCST] libcst not installed — skipping FQN-based call edges. "
                "Install the '[callgraph]' extra for higher-precision edges."
            )
            return []

        py_files = gather_py_files(project_root)

        # Scope to indexed files only — avoids injecting edges from venv/stdlib.
        if raw_line_map:
            py_files = scope_to_indexed_files(
                py_files, set(raw_line_map.keys()), project_root
            )

        if not py_files:
            logger.warning(
                "[LIBCST] No .py files found under %s — skipping", project_root
            )
            return []

        # Pre-validate: one syntactically broken file must not abort the pass.
        py_files = validate_py_files(py_files, logger, source_name="LIBCST")

        if not py_files:
            logger.warning(
                "[LIBCST] No parseable .py files remain — skipping edge injection"
            )
            return []

        logger.info(
            "[LIBCST] Analysing %d Python files with LibCST FQN resolver...",
            len(py_files),
        )

        # Build absolute path keys for FullRepoManager.
        # Passing relative paths triggers ValueError in
        # FullyQualifiedNameProvider.gen_cache → calculate_module_and_package
        # (PurePath(relative).relative_to(absolute_root) always fails).
        root = project_root.resolve()
        repo_root_str = str(root)
        abs_keys: list[str] = []  # absolute resolved path strings (FRM keys)
        rel_labels: list[str] = []  # forward-slash relative labels (logging only)
        for fn in py_files:
            try:
                p = Path(fn).resolve()
                rel = str(p.relative_to(root)).replace("\\", "/")
                abs_keys.append(str(p))
                rel_labels.append(rel)
            except ValueError:
                continue  # outside project root — skip

        if not abs_keys:
            logger.warning("[LIBCST] No files relative to project root — skipping")
            return []

        raw_edges: set[tuple[str, str, int, bool]] = set()
        skipped = 0

        try:
            manager = FullRepoManager(
                repo_root_str,
                abs_keys,
                {FullyQualifiedNameProvider, PositionProvider},
                use_pyproject_toml=self._use_pyproject_toml,
            )
            # Front-load the entire batch cache in one pass.
            # This resolves all cross-file FQN tables up-front so each
            # MetadataWrapper construction below hits an already-warm cache.
            manager.resolve_cache()
        except Exception as exc:
            logger.warning(
                "[LIBCST] FullRepoManager initialisation failed (%s) — skipping",
                exc,
            )
            return []

        for key, rel_label in zip(abs_keys, rel_labels, strict=False):
            try:
                # Bypass get_metadata_wrapper_for_path — it calls read_text()
                # without specifying encoding, which fails on Windows cp1252
                # locales for UTF-8 source files.  Read explicitly with utf-8.
                source = Path(key).read_text(encoding="utf-8")
                module = cst.parse_module(source)
                cache = manager.get_cache_for_path(key)
                wrapper = MetadataWrapper(module, True, cache)
            except Exception as exc:
                logger.warning(
                    "[LIBCST] Skipping %s (wrapper error: %s)", rel_label, exc
                )
                skipped += 1
                continue

            visitor = _CallVisitor()
            try:
                wrapper.visit(visitor)
            except Exception as exc:
                logger.warning(
                    "[LIBCST] Skipping %s (visitor error: %s)", rel_label, exc
                )
                skipped += 1
                continue

            for caller_fqn, callee_fqn, lineno in visitor.edges:
                caller_id = chunk_id_from_fqn(caller_fqn, raw_line_map, project_root)
                if caller_id is None:
                    skipped += 1
                    continue

                callee_id = chunk_id_from_fqn(callee_fqn, raw_line_map, project_root)
                if callee_id is None:
                    skipped += 1
                    continue

                if caller_id == callee_id:
                    skipped += 1
                    continue  # skip self-loops

                # Infer whether the caller is a method from its FQN depth.
                is_method = caller_fqn.count(".") >= 2

                raw_edges.add((caller_id, callee_id, lineno, is_method))

        result = [
            ResolvedEdge(
                caller_id=c,
                callee_id=t,
                line=ln,
                is_method=im,
                source="libcst",
                confidence=self.base_confidence,
            )
            for c, t, ln, im in sorted(raw_edges)
        ]

        logger.info(
            "[LIBCST] Resolved %d call edges (%d skipped / unmappable)",
            len(result),
            skipped,
        )
        return result
