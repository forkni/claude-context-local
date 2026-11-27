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
import sys
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parent.parent
# <project>_<hash8>_<model slug>_<dim>d, the per-model storage folder name.
_MODEL_DIR = re.compile(r"_([0-9a-f]{8})_(.+_\d+d)\Z")
_OVERRIDES_NAME = "search_overrides.json"
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
    is set). A missing file or key gives False, the dataclass default.
    """
    value = False
    paths = _load("_launcher_config_paths", "search/config_paths.py")
    if paths is not None:
        config = _read_json(Path(paths.resolve_config_path())) or {}
        value = bool((config.get("call_graph") or {}).get("rust_scip", value))
    disabled = os.environ.get("CLAUDE_DISABLE_PROJECT_OVERRIDES", "").strip().lower()
    if disabled not in ("1", "true", "yes", "on"):
        overrides = (_read_json(model_dir / _OVERRIDES_NAME) or {}).get("overrides")
        call_graph = (overrides or {}).get("call_graph") or {}
        if "rust_scip" in call_graph:
            value = bool(call_graph["rust_scip"])
    return value


def last_indexed(storage: Path, model_dir: Path, project_path: str) -> datetime | None:
    """``last_snapshot`` from the project's Merkle metadata (naive local time), or None."""
    match = _MODEL_DIR.search(model_dir.name)
    if match is None:
        return None
    short_hash, model_tail = match.groups()
    for meta_file in (storage / "merkle").glob(
        f"{short_hash}*_{model_tail}_metadata.json"
    ):
        meta = _read_json(meta_file)
        if not meta or not _same_path(str(meta.get("project_path", "")), project_path):
            continue
        try:
            return datetime.fromisoformat(meta["last_snapshot"])
        except (KeyError, TypeError, ValueError):
            return None
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
        )
    except (OSError, ValueError):
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
