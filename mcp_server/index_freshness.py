"""Definitive index-freshness verdict: does the on-disk index match the working tree.

A snapshot timestamp (``last_indexed_at``/``last_snapshot``) only says when the
indexer last ran -- it says nothing about whether the index still matches the
project's files. An agent that infers staleness from a timestamp alone has to
reconstruct that answer from git history, which is exactly the inference that
produced a false "index is stale" report after a full reindex (see
``docs/adr/0058-index-freshness-verdict.md``).

This module is the single owner of the ``ChangeDetector`` construction used to
answer that question directly. ``ChangeDetector`` must be built with the same
``supported_extensions`` the indexer used
(``set(TreeSitterChunker.get_supported_extensions())``) or every non-code file
falls off the stat-hash fast path and the comparison reports false-positive
changes on an untouched tree -- see ``merkle.change_detector.ChangeDetector``.
Three call sites already built this construction independently
(``_is_index_stale``, ``_check_auto_reindex``,
``IncrementalIndexer.needs_reindex``); route new callers through here instead
of adding a fourth.

Lives under ``mcp_server/``, not ``search/``, because it depends on
``mcp_server.storage_manager.get_project_storage_dir`` -- ``search/`` may not
import ``mcp_server/`` at runtime (ADR-0004, enforced by
``tests/unit/search/test_layering_ownership.py``). All of this module's
callers (``search_handlers.py``, ``status_handlers.py``) already live in
``mcp_server/``, so this placement adds no new import direction.
"""

import json
import logging

from chunking.tree_sitter import TreeSitterChunker
from mcp_server.storage_manager import get_project_storage_dir
from merkle.change_detector import ChangeDetector
from merkle.snapshot_manager import SnapshotManager
from search.filters import get_effective_filters


logger = logging.getLogger(__name__)


def build_change_detector(
    project_path: str,
    *,
    model_slug: str | None = None,
    dimension: int | None = None,
    snapshot_manager: SnapshotManager | None = None,
) -> tuple[ChangeDetector, SnapshotManager]:
    """Construct a correctly-configured ``ChangeDetector`` for *project_path*.

    Loads effective include/exclude filters from ``project_info.json``
    (falling back to no filters if the file is missing or unparsable) and
    builds the detector with
    ``supported_extensions=set(TreeSitterChunker.get_supported_extensions())``
    -- the invariant documented in ``ChangeDetector.__init__``.

    Args:
        project_path: Path to the project
        model_slug: Optional explicit model slug forwarded to the detector, so
            the comparison reads the snapshot for that model rather than the
            currently configured one (e.g. when checking freshness for a
            non-active model in ``list_projects``).
        dimension: Optional explicit model dimension. Pass together with
            ``model_slug`` when checking a non-active model — passing
            ``model_slug`` alone still resolves dimension from the currently
            configured model.
        snapshot_manager: Optional pre-built ``SnapshotManager``. Defaults to
            a fresh instance.

    Returns:
        Tuple of (ChangeDetector, SnapshotManager) -- the manager is returned
        so callers can reuse it for ``has_snapshot``/``get_snapshot_age``
        without constructing a second instance.
    """
    project_storage = get_project_storage_dir(project_path)
    project_info_file = project_storage / "project_info.json"

    include_dirs = None
    exclude_dirs = None
    include_exclusive = False
    if project_info_file.exists():
        try:
            with open(project_info_file) as f:
                project_info = json.load(f)
            include_dirs, exclude_dirs, include_exclusive = get_effective_filters(
                project_info
            )
        except Exception as e:  # noqa: BLE001 - parse-recovery: project_info.json read, fall back to no filters
            logger.warning(f"[INDEX_FRESHNESS] Failed to load filters: {e}")

    snapshot_mgr = snapshot_manager or SnapshotManager()
    change_detector = ChangeDetector(
        snapshot_mgr,
        include_dirs,
        exclude_dirs,
        supported_extensions=set(TreeSitterChunker.get_supported_extensions()),
        include_exclusive=include_exclusive,
        model_slug=model_slug,
        dimension=dimension,
    )
    return change_detector, snapshot_mgr


def compute_index_freshness(
    project_path: str, *, model_slug: str | None = None, dimension: int | None = None
) -> dict | None:
    """Return the definitive, content-only freshness verdict for *project_path*.

    Unlike a snapshot-age check, this never consults *when* the index was
    built -- only whether the on-disk index still matches the working tree,
    via a full Merkle diff (``detect_changes_from_snapshot``).

    Args:
        project_path: Path to the project
        model_slug: Optional explicit model slug. If None, auto-detects from
            current config. Pass explicitly to check a specific model's index
            when a project has multiple indexed models.
        dimension: Optional explicit model dimension. Pass together with
            ``model_slug`` when checking a non-active model.

    Returns:
        None if no snapshot exists for this project/model (never indexed) --
        distinct from a "current" verdict. Otherwise::

            {
                "index_is_current": bool,
                "pending_changes": {"added": int, "modified": int, "removed": int},
            }
    """
    change_detector, snapshot_mgr = build_change_detector(
        project_path, model_slug=model_slug, dimension=dimension
    )
    if not snapshot_mgr.has_snapshot(
        project_path, dimension=dimension, model_slug=model_slug
    ):
        return None

    changes, _current_dag = change_detector.detect_changes_from_snapshot(project_path)
    return {
        "index_is_current": not changes.has_changes(),
        "pending_changes": {
            "added": len(changes.added),
            "modified": len(changes.modified),
            "removed": len(changes.removed),
        },
    }
