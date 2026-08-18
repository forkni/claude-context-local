"""Shared interface for offline retrieval probes (``scripts/benchmark/probe_*.py``).

Before this module, every probe hand-rolled the same handful of things:
23 ``sys.path.insert`` bootstraps across ``scripts/benchmark/*.py``, 5
near-identical ``load_queries`` golden-set loaders, 25 hand-rolled
``ArgumentParser``s (14 pointing at the same
``evaluation/golden_dataset_expanded.json`` default path), 14
``get_searcher()`` constructions, unguarded ``SearchConfig`` mutations with
no script restoring the config afterward, and -- the load-bearing failure --
two live copies of the hop-1 funnel-width arithmetic
(``search_k = max(reranker_budget, k * 5)``) that had already drifted from
``search/search_executor.py`` by the time this module was written (the
production formula uses ``config.search_mode.leg_search_multiplier``, not a
hardcoded ``5``; a probe testing that knob via ``--set`` would silently
report the same ``search_k`` regardless of the override). Two independent
rerank-instrumentation adapters (``probe_final_pool_reserve.py``'s
``instrument_rerank`` and ``probe_duplicate_crowding.py``'s
``Instrumentation`` class) had also converged on the same design without
either knowing about the other.

This module is the seam that ends the hand-copying, modeled on
``evaluation/arm_overrides.py``'s shape: module-level functions plus small
data carriers, no DI container (ADR-0005). Functions built entirely from
what already exists rather than reimplemented:

- :func:`ensure_pinned_hash_seed` -- moved from
  ``scripts/benchmark/run_sscg_benchmark.py`` (ADR-0021's determinism guard).
- :class:`GoldenQuery` / :func:`load_golden_queries` -- one loader replacing
  five, grades pre-normalized via :func:`evaluation.metrics.normalize_chunk_id`.
- :func:`probe_parser` -- one parent ``ArgumentParser`` owning every probe's
  common flags.
- :func:`open_probe` / :class:`ProbeSession` -- searcher construction plus
  ``--set`` override apply/restore built on
  :mod:`evaluation.arm_overrides` (``apply_overrides``, ``requires_rebuild``,
  ``parse_set_flags``) rather than reimplementing config validation.
- :meth:`ProbeSession.replay_legs` -- hop-1 leg replay at the *actual*
  production width, via ``search.search_executor.leg_search_depth`` /
  ``fused_pool_cut`` (never a re-derived literal).
- :meth:`ProbeSession.instrument` -- the rerank-interception adapter the two
  independent originals above both reinvented.
- :func:`write_probe_json` -- the verbatim 6x-repeated JSON-output one-liner.

See ``docs/adr/0040-probe-harness-seam.md`` for the full rationale and the
evidence this was built from.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from evaluation import arm_overrides
from evaluation.metrics import normalize_chunk_id


if TYPE_CHECKING:
    from search.config import SearchConfig
    from search.hybrid_searcher import HybridSearcher


REPO_ROOT = Path(__file__).resolve().parent.parent


def ensure_pinned_hash_seed() -> None:
    """Re-exec with PYTHONHASHSEED=0 when unset (script execution only).

    Reproducibility: chunk-ID set iteration order feeds candidate-pool
    composition, so unpinned hash randomization flips ~25/131 queries between
    otherwise-identical rounds (evaluation/GPU_DETERMINISM_AB_20260802.md).
    Any explicit PYTHONHASHSEED, including "random", is respected. Must only
    run under __main__ -- at import time (tests import this module) sys.argv
    belongs to the importer and re-exec'ing it is wrong.
    """
    if os.environ.get("PYTHONHASHSEED") is None:
        print(
            "[HASHSEED] PYTHONHASHSEED unset - re-exec with PYTHONHASHSEED=0 "
            "for reproducible rounds",
            file=sys.stderr,
        )
        raise SystemExit(
            subprocess.call(
                [sys.executable, *sys.argv],
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
        )


# ---------------------------------------------------------------------------
# Golden-query loading
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class GoldenQuery:
    """One golden-dataset entry, normalized once at load time.

    ``grades`` keys are already run through :func:`normalize_chunk_id` --
    every probe was doing this inline, per-query, inside its own
    ``probe_query``; doing it once here means a probe body never touches a
    raw ``relevance_grades`` dict.
    """

    id: str
    query: str
    category: str
    grades: dict[str, int]
    anchor_chunk_id: str | None = None


def load_golden_queries(
    dataset: str | Path,
    query_ids: Sequence[str] | None = None,
    exclude_categories: Sequence[str] = ("D",),
    require_grades: bool = True,
) -> list[GoldenQuery]:
    """Load golden-dataset entries as :class:`GoldenQuery`.

    Replaces five near-identical ``load_queries`` definitions across
    ``scripts/benchmark/probe_*.py``. The two filter knobs cover every
    variant seen in that set:

    - *exclude_categories*: entries whose ``category`` is in this set are
      dropped first. Default ``("D",)`` matches every current probe except
      ``probe_stable_misses.py`` (pass ``()`` -- it diagnoses named queries
      of any category) and ``probe_leg_depth_fusion.py`` (pass
      ``("D", "F")`` -- F is scored via ``find_similar_code`` anchors, a
      pipeline plain leg replay never exercises).
    - *require_grades*: entries with no (or empty) ``relevance_grades`` are
      dropped. Default True matches every current probe except
      ``probe_stable_misses.py`` (pass False -- it diagnoses named queries
      regardless of grading status).

    *query_ids*, when given, selects exactly those ids in the given order
    (not dataset order) and raises :class:`KeyError` listing any id absent
    from the dataset or dropped by the two filters above -- matching every
    original ``load_queries``'s "not found (or excluded)" contract.
    """
    dataset_path = Path(dataset)
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    entries = [
        q
        for q in data["queries"]
        if q.get("category") not in exclude_categories
        and (not require_grades or q.get("relevance_grades"))
    ]
    if query_ids:
        by_id = {q["id"]: q for q in entries}
        missing = [qid for qid in query_ids if qid not in by_id]
        if missing:
            raise KeyError(
                f"{missing} not found (or excluded/ungraded) in {dataset_path}"
            )
        entries = [by_id[qid] for qid in query_ids]
    return [
        GoldenQuery(
            id=q["id"],
            query=q["query"],
            category=q.get("category", "?"),
            grades={
                normalize_chunk_id(gid): grade
                for gid, grade in (q.get("relevance_grades") or {}).items()
            },
            anchor_chunk_id=q.get("anchor_chunk_id"),
        )
        for q in entries
    ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def probe_parser(description: str) -> argparse.ArgumentParser:
    """Parent ``ArgumentParser`` owning every probe's common flags.

    Replaces 25 hand-rolled parsers, 14 of which respelled the same
    golden-path default. A
    probe script builds its own parser with
    ``argparse.ArgumentParser(description=..., parents=[probe_parser(...)])``
    and adds only the flags unique to it (``--probe-depth``, ``--depths``,
    ...). ``add_help=False`` is required on a parent parser -- otherwise the
    child's own ``-h/--help`` conflicts with this one's.

    ``--dataset``'s default is deliberately the same relative string every
    original probe used (``"evaluation/golden_dataset_expanded.json"``), not
    an eagerly-resolved absolute path -- callers resolve it against
    :data:`REPO_ROOT` themselves (see :func:`open_probe`), matching each
    original ``main()``'s own resolution step.
    """
    parser = argparse.ArgumentParser(description=description, add_help=False)
    parser.add_argument("--dataset", default="evaluation/golden_dataset_expanded.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--query-ids", nargs="*", default=None)
    parser.add_argument("--json", dest="json_out", default=None)
    parser.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        default=None,
        metavar="section.field=value",
        help="Override one SearchConfig field for this probe run (repeatable).",
    )
    return parser


def resolve_dataset_path(raw: str | Path) -> Path:
    """Resolve a possibly-relative ``--dataset`` value against :data:`REPO_ROOT`."""
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def write_probe_json(path: str | Path, payload: dict[str, Any] | list[Any]) -> None:
    """Write *payload* as indented JSON and announce the path.

    Replaces the 6x-repeated ``Path(args.json_out).write_text(json.dumps(...),
    encoding="utf-8")`` plus its ``"JSON written to ..."`` print at the end of
    every probe's ``main()``.
    """
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nJSON written to {path}")


# ---------------------------------------------------------------------------
# Searcher + config lifecycle
# ---------------------------------------------------------------------------


def _reset_cached_searcher() -> None:
    """Drop the cached searcher in MCP server state.

    Needed once a construction-baked field (``rrf_k``, the reranker document
    budgets, ``listwise_dtype``) has changed underneath a cached searcher --
    mirrors ``run_sscg_benchmark.py``'s identically-named helper.
    """
    try:
        from mcp_server.services import get_state

        get_state().reset_searcher()
    except Exception as e:  # noqa: BLE001 - resilience: never abort a probe over state cleanup
        print(f"[WARN] Could not reset cached searcher: {e}", file=sys.stderr)


def _snapshot_and_apply(
    cfg: SearchConfig, overrides: dict[str, Any]
) -> tuple[dict[tuple[str, str], Any], bool]:
    """Snapshot pre-override values, apply *overrides* in place, return
    ``(snapshot, requires_rebuild)``.

    Snapshotting happens *before* mutation, keyed off the same normalized
    dotted-key set :func:`evaluation.arm_overrides.apply_overrides` will
    touch, so :func:`_restore_config` can undo exactly what was changed --
    something no current probe script (or ``run_sscg_benchmark.py`` itself)
    does today.
    """
    if not overrides:
        return {}, False
    flat = arm_overrides.normalize_overrides(overrides)
    arm_overrides.validate_overrides(flat)
    snapshot: dict[tuple[str, str], Any] = {}
    for key in flat:
        section, field_name = key.split(".", 1)
        snapshot[(section, field_name)] = getattr(getattr(cfg, section), field_name)
    rebuild = arm_overrides.apply_overrides(cfg, flat)
    return snapshot, rebuild


def _restore_config(cfg: SearchConfig, snapshot: dict[tuple[str, str], Any]) -> None:
    """Undo :func:`_snapshot_and_apply`'s mutation, one field at a time."""
    for (section, field_name), value in snapshot.items():
        setattr(getattr(cfg, section), field_name, value)


@dataclasses.dataclass
class LegCapture:
    """One replayed hop-1 funnel pass: raw BM25/dense legs + the RRF-fused cut.

    ``bm25``/``dense``/``fused`` are normalized chunk-id lists (rank order
    preserved). ``raw_bm25``/``raw_dense``/``raw_fused`` are the underlying
    ``(chunk_id, score, metadata)`` tuples / ``SearchResult`` objects a probe
    needs for its own fusion experiments (e.g. TM2C2's normalized-score fuse).
    """

    bm25: list[str]
    dense: list[str]
    fused: list[str]
    search_k: int
    cut: int
    raw_bm25: list[tuple]
    raw_dense: list[tuple]
    raw_fused: list[Any]

    def rank_of(self, gold: str, leg: str = "fused") -> int | None:
        """1-based rank of *gold* within ``self.<leg>`` (bm25/dense/fused), or None."""
        ids: list[str] = getattr(self, leg)
        try:
            return ids.index(gold) + 1
        except ValueError:
            return None


class ProbeSession:
    """One probe run's searcher + live config, constructed via :func:`open_probe`.

    Not meant to be constructed directly -- :func:`open_probe` is responsible
    for building the searcher and applying/restoring any ``--set`` overrides
    around it.
    """

    def __init__(self, searcher: HybridSearcher, config: SearchConfig, k: int) -> None:
        self.searcher = searcher
        self.config = config
        self.k = k

    def replay_legs(
        self, query: str, k: int | None = None, depth: int | None = None
    ) -> LegCapture:
        """Replay the BM25/dense/fused hop-1 legs at production width.

        Widths come from ``search.search_executor.leg_search_depth`` /
        ``fused_pool_cut`` -- the single source of the hop-1 funnel-width
        arithmetic -- never a hand-copied literal (the drift that motivated
        this module: two probes hardcoded ``k * 5`` and silently stopped
        matching production once ``leg_search_multiplier`` became a live,
        unlocked knob). Pass *depth* to bypass the derived width entirely,
        for a probe sweeping leg-search depth explicitly
        (``probe_leg_depth_fusion.py``'s ``--depths``).
        """
        from search.search_executor import fused_pool_cut, leg_search_depth

        k = self.k if k is None else k
        executor = self.searcher.search_executor
        search_k = depth if depth is not None else leg_search_depth(self.config, k)
        cut = fused_pool_cut(self.config, k)
        min_score = self.config.search_mode.min_bm25_score
        raw_bm25 = executor.search_bm25(query, search_k, min_score, None)
        raw_dense = executor.search_dense(query, search_k, None, None)
        raw_fused = executor.reranker.rerank_simple(
            bm25_results=raw_bm25,
            dense_results=raw_dense,
            max_results=cut,
            bm25_weight=self.config.search_mode.bm25_weight,
            dense_weight=self.config.search_mode.dense_weight,
            reserved_slots=self.config.search_mode.bm25_reserved_slots,
        )
        return LegCapture(
            bm25=[normalize_chunk_id(c) for c, _, _ in raw_bm25],
            dense=[normalize_chunk_id(c) for c, _, _ in raw_dense],
            fused=[normalize_chunk_id(r.chunk_id) for r in raw_fused],
            search_k=search_k,
            cut=cut,
            raw_bm25=raw_bm25,
            raw_dense=raw_dense,
            raw_fused=raw_fused,
        )

    @contextmanager
    def instrument(self):
        """Intercept ``RerankingEngine._run_rerank``/``rerank_by_query`` calls.

        Yields the list of per-call records, which grows for the context
        manager's duration; patches are restored on exit even if the body
        raises. Generalizes two independent adapters that had converged on
        the same design: ``probe_final_pool_reserve.py``'s
        ``instrument_rerank`` and ``probe_duplicate_crowding.py``'s
        ``Instrumentation`` class.

        Each record: ``hop1_slots`` (the ``rerank_by_query`` call's
        ``hop1_reserved_slots`` kwarg, tagging which pass this is -- >0 is
        the multi-hop merged call, 0 is the final post-ego call, ``None`` is
        a hop-1 ``apply_neural_reranking`` pass that never went through
        ``rerank_by_query``), ``k``, ``pool_ids`` (normalized),
        ``pool_sources`` (``(chunk_id, source)`` pairs -- ``source ==
        "graph_hop"`` identifies graph-hop-expansion candidates),
        ``window_ids`` (via ``engine.last_window_ids``), ``output_ids``
        (normalized).
        """
        engine = self.searcher.reranking_engine
        calls: list[dict[str, Any]] = []
        state: dict[str, int | None] = {"hop1_slots": None}
        orig_rbq = engine.rerank_by_query
        orig_run = engine._run_rerank

        def rbq_wrap(*call_args: Any, **call_kwargs: Any) -> Any:
            state["hop1_slots"] = call_kwargs.get("hop1_reserved_slots", 0)
            try:
                return orig_rbq(*call_args, **call_kwargs)
            finally:
                state["hop1_slots"] = None

        def run_wrap(
            query_or_content: str,
            candidates: list,
            k: int,
            log_prefix: str,
            config: Any = None,
        ) -> list:
            out = orig_run(query_or_content, candidates, k, log_prefix, config=config)
            calls.append(
                {
                    "hop1_slots": state["hop1_slots"],
                    "k": k,
                    "pool_ids": [normalize_chunk_id(r.chunk_id) for r in candidates],
                    "pool_sources": [
                        (normalize_chunk_id(r.chunk_id), getattr(r, "source", None))
                        for r in candidates
                    ],
                    "window_ids": [
                        normalize_chunk_id(cid)
                        for cid in (engine.last_window_ids or [])
                    ],
                    "output_ids": [normalize_chunk_id(r.chunk_id) for r in out],
                }
            )
            return out

        engine.rerank_by_query = rbq_wrap
        engine._run_rerank = run_wrap
        try:
            yield calls
        finally:
            engine.rerank_by_query = orig_rbq
            engine._run_rerank = orig_run


@contextmanager
def open_probe(args: argparse.Namespace):
    """Context manager: build a :class:`ProbeSession` from parsed CLI ``args``.

    Applies ``--set`` overrides (via
    :func:`evaluation.arm_overrides.apply_overrides`, honouring
    ``requires_rebuild`` the same way ``run_sscg_benchmark.py``'s
    ``run_single`` does), snapshots every touched field, and restores it on
    exit -- something no current probe script does today, so repeated
    in-process probe runs (tests, a future multi-arm probe) no longer leak
    one run's overrides into the next.

    *args* must carry ``project_path``, ``k``, and (optionally)
    ``set_overrides`` -- exactly what :func:`probe_parser` produces.

    Raises ``TypeError`` if the resolved searcher isn't a
    :class:`~search.hybrid_searcher.HybridSearcher` -- every probe migrated
    onto this harness replays the BM25/dense/rerank internals that only
    ``HybridSearcher`` exposes (``search_executor``, ``reranking_engine``),
    so a config that resolves to ``IntelligentSearcher`` instead is a probe
    misuse, not something to silently paper over.
    """
    from mcp_server.search_factory import get_searcher
    from search.config import get_search_config
    from search.hybrid_searcher import HybridSearcher

    cfg = get_search_config()
    set_overrides = arm_overrides.parse_set_flags(getattr(args, "set_overrides", None))
    snapshot, rebuild = _snapshot_and_apply(cfg, set_overrides)
    if rebuild:
        _reset_cached_searcher()

    searcher = get_searcher(project_path=args.project_path)
    if not isinstance(searcher, HybridSearcher):
        raise TypeError(
            f"probe_harness requires a HybridSearcher, got {type(searcher).__name__} "
            "-- check search_mode config"
        )
    session = ProbeSession(searcher=searcher, config=cfg, k=args.k)
    try:
        yield session
    finally:
        if snapshot:
            _restore_config(cfg, snapshot)
            if rebuild:
                _reset_cached_searcher()
