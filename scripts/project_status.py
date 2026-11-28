"""Status lines for the launcher's project lists: SCIP table and search index.

Used by ``list_projects_parseable.py`` (project pickers in ``start_mcp_server.cmd``)
and ``list_projects_display.py`` (Project Management > List Indexed Projects).

The SCIP part is stdlib only: it loads ``search/scip_refs.py`` and
``search/config_paths.py`` by file path, so ``search/__init__.py`` (which imports
torch) never runs. The index part (:func:`index_statuses`) imports
``mcp_server.index_freshness`` lazily; that import loads torch, so only the
``--freshness`` flag pays for it.
"""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import json
import os
import re
import sqlite3
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parent.parent
_OVERRIDES_NAME = "search_overrides.json"
# Fallback parse of <project>_<hash8>_<model slug>_<dim>d: the greedy prefix
# takes the last 8-hex segment that still leaves a "<slug>_<dim>d" tail.
_MODEL_DIR = re.compile(r"\A.*_([0-9a-f]{8})_(.+?_\d+d)\Z")
# Merkle file ids are 32 hex chars (merkle/snapshot_manager.py get_project_id).
_MERKLE_ID_LEN = 32
INDEX_WORKERS = 4


@functools.cache
def _load(name: str, relative: str) -> ModuleType | None:
    """Import ``REPO_ROOT/relative`` as ``name`` without its package; None on failure."""
    try:
        spec = importlib.util.spec_from_file_location(name, REPO_ROOT / relative)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    except (ImportError, OSError, SyntaxError):
        sys.modules.pop(name, None)
        return None
    return module


def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(
        os.path.normpath(b)
    )


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def rust_scip_enabled(model_dir: Path) -> bool:
    """``call_graph.rust_scip`` as the server would see it for this project.

    The base config (the file ``search/config_paths.py`` resolves), then the
    project's ``search_overrides.json`` (unless ``CLAUDE_DISABLE_PROJECT_OVERRIDES``
    is set or the base config has ``performance.enable_project_overrides`` false,
    the same gates ``SearchConfigManager.load_config`` applies). A missing file
    or key gives False, the dataclass default.
    """
    value = False
    overrides_on = True
    paths = _load("_launcher_config_paths", "search/config_paths.py")
    if paths is not None:
        config = _read_json(Path(paths.resolve_config_path())) or {}
        value = bool((config.get("call_graph") or {}).get("rust_scip", value))
        overrides_on = bool(
            (config.get("performance") or {}).get("enable_project_overrides", True)
        )
    # No strip(): SearchConfigManager._bool_from_env does not strip either.
    disabled = os.environ.get("CLAUDE_DISABLE_PROJECT_OVERRIDES", "").lower()
    if overrides_on and disabled not in ("1", "true", "yes", "on", "enabled"):
        overrides = (_read_json(model_dir / _OVERRIDES_NAME) or {}).get("overrides")
        call_graph = (overrides or {}).get("call_graph") or {}
        if "rust_scip" in call_graph:
            value = bool(call_graph["rust_scip"])
    return value


def _hash_and_model_tail(model_dir: Path) -> tuple[str, str] | None:
    """``(hash8, "<model slug>_<dim>d")`` from a ``<project>_<hash8>_<slug>_<dim>d`` folder.

    The hash comes from the folder's ``project_info.json``, so neither an 8-hex
    segment in the project name nor an ``_`` in the model slug can mislead the
    split. Without a readable hash (file missing or caught mid-rewrite), the
    folder name is parsed alone, taking the last ``_<8 hex>_`` segment.
    """
    info = _read_json(model_dir / "project_info.json") or {}
    short_hash = str(info.get("project_hash", ""))
    marker = f"_{short_hash}_"
    if short_hash and marker in model_dir.name:
        return short_hash, model_dir.name.rsplit(marker, 1)[1]
    match = _MODEL_DIR.match(model_dir.name)
    return (match.group(1), match.group(2)) if match else None


def _merkle_files(storage: Path, model_dir: Path, kind: str) -> list[Path]:
    """``<storage>/merkle/<32-hex id>_<slug>_<dim>d_<kind>.json`` files for a model folder.

    The id is matched at its exact length, so another model whose slug ends in
    this one's (``x_bge-m3`` vs ``bge-m3``) cannot match.
    """
    parts = _hash_and_model_tail(model_dir)
    if parts is None:
        return []
    short_hash, model_tail = parts
    id_pattern = short_hash + "[0-9a-f]" * (_MERKLE_ID_LEN - len(short_hash))
    return sorted((storage / "merkle").glob(f"{id_pattern}_{model_tail}_{kind}.json"))


def last_indexed(storage: Path, model_dir: Path, project_path: str) -> datetime | None:
    """``last_snapshot`` from the project's Merkle metadata (naive local time), or None."""
    for meta_file in _merkle_files(storage, model_dir, "metadata"):
        meta = _read_json(meta_file)
        if not meta or not _same_path(str(meta.get("project_path", "")), project_path):
            continue
        try:
            return datetime.fromisoformat(meta["last_snapshot"])
        except (KeyError, TypeError, ValueError):
            return None
    return None


def indexed_rust_files(
    storage: Path, model_dir: Path, project_path: str
) -> frozenset[str] | None:
    """The ``.rs`` files the next reindex will hold (relative, ``/``), from the Merkle snapshot.

    Only these files reach the call graph, so only they can make the SCIP table
    stale: a git worktree or another excluded folder inside the project holds
    ``.rs`` files that the index (and so the graph) never sees. The set is the
    snapshot's ``.rs`` files plus any ``.rs`` file now on disk directly in a
    folder the snapshot holds, so a file added after the last index counts as
    new. A file in a folder the snapshot does not hold (a new folder) is left
    out until the next reindex. None when there is no snapshot (never indexed,
    or a reindex is running).
    """
    for snap_file in _merkle_files(storage, model_dir, "snapshot"):
        dag = (_read_json(snap_file) or {}).get("dag")
        if not isinstance(dag, dict) or not _same_path(
            str(dag.get("root_path", "")), project_path
        ):
            continue
        found: set[str] = set()
        folders: list[str] = []
        stack = [dag.get("root_node")]
        while stack:
            node = stack.pop()
            if not isinstance(node, dict):
                continue
            path = str(node.get("path", "")).replace("\\", "/")
            if node.get("is_file"):
                if path.endswith(".rs"):
                    found.add(path)
            else:
                folders.append(path)
            children = node.get("children")
            if isinstance(children, list):
                stack.extend(children)
        root = Path(project_path)
        for folder in folders:
            prefix = "" if folder in ("", ".") else folder + "/"
            try:
                with os.scandir(root / folder) as entries:
                    found.update(
                        prefix + e.name
                        for e in entries
                        if e.name.endswith(".rs") and e.is_file()
                    )
            except OSError:
                continue
        return frozenset(found)
    return None


def _manifest_created(model_dir: Path, scip_refs: ModuleType) -> str:
    manifest = _read_json(model_dir / scip_refs.SCIP_DIRNAME / scip_refs.MANIFEST_NAME)
    return str((manifest or {}).get("created", ""))


def scip_text(
    storage: Path, project_path: str, model_dirs: Iterable[Path]
) -> str | None:
    """SCIP status for a project (no ``SCIP:`` label), or None for a non-Rust project.

    With several model folders, the one holding the latest manifest wins.
    """
    dirs = list(model_dirs)
    if not dirs or not os.path.isdir(project_path):
        return None
    scip_refs = _load("_launcher_scip_refs", "search/scip_refs.py")
    if scip_refs is None:
        return None
    chosen = max(dirs, key=lambda d: _manifest_created(d, scip_refs))
    try:
        return scip_refs.scip_status(
            chosen / scip_refs.SCIP_DIRNAME,
            Path(project_path),
            last_indexed=last_indexed(storage, chosen, project_path),
            rust_scip=rust_scip_enabled(chosen),
            indexed=indexed_rust_files(storage, chosen, project_path),
        )
    except (OSError, ValueError, sqlite3.Error):
        return "unreadable - run Make SCIP Index"


def _index_text(result: dict | None) -> str:
    if result is None:
        return "unknown"
    if result["index_is_current"]:
        return "up to date"
    pending = result["pending_changes"]
    return (
        f"stale - {pending['added']} added, {pending['modified']} modified, "
        f"{pending['removed']} removed"
    )


def index_statuses(
    projects: list[tuple[str, list[tuple[str, int]]]],
) -> list[list[tuple[str, str]]]:
    """Index freshness per model, for each ``(project_path, [(model, dim), ...])``.

    Returns, in the same order, ``[(model short name, status text), ...]`` per
    project. Uses the server's Merkle check (``compute_index_freshness``,
    ADR-0058) in ``INDEX_WORKERS`` threads. Anything the import or the check
    prints goes to stderr, so stdout keeps only the caller's lines.
    """
    with contextlib.redirect_stdout(sys.stderr):
        try:
            if str(REPO_ROOT) not in sys.path:
                sys.path.insert(0, str(REPO_ROOT))
            from mcp_server.index_freshness import compute_index_freshness
            from search.config import get_model_slug
        except Exception as exc:  # noqa: BLE001 - optional display: any import failure -> "unknown"
            print(f"[WARN] Index freshness unavailable: {exc}", file=sys.stderr)
            return [
                [(model.split("/")[-1], "unknown") for model, _dim in models]
                for _path, models in projects
            ]

        def check(path: str, model: str, dim: int) -> str:
            if not os.path.isdir(path):
                return "path not found"
            try:
                return _index_text(
                    compute_index_freshness(
                        path, model_slug=get_model_slug(model), dimension=dim
                    )
                )
            except Exception as exc:  # noqa: BLE001 - one project's failure must not hide the others
                print(f"[WARN] Index check failed for {path}: {exc}", file=sys.stderr)
                return "unknown"

        with ThreadPoolExecutor(max_workers=INDEX_WORKERS) as pool:
            futures = [
                [
                    (model.split("/")[-1], pool.submit(check, path, model, dim))
                    for model, dim in models
                ]
                for path, models in projects
            ]
            return [[(name, f.result()) for name, f in row] for row in futures]


def index_field(statuses: list[tuple[str, str]]) -> str:
    """One picker field: the status alone for one model, else ``model status; ...``."""
    if len(statuses) == 1:
        return statuses[0][1]
    return "; ".join(f"{name} {text}" for name, text in statuses)
