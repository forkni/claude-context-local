"""Locate a project's on-disk index (metadata.db + call graph) for evaluation.

Consolidates three ad-hoc copies of the same lookup
(``scripts/benchmark/graph_phantom_preflight.py:find_call_graph_dir``/
``load_storage``, ``audit_golden_dataset.locate_metadata_db``,
``analyze_chunking_corpus.locate_graph_storage``). Layout, as written by the
indexer::

    <storage_root>/projects/<name>_<hash>_<model-slug>_<dim>d/
        project_info.json
        index/metadata.db
        <name>_<hash>_<model-slug>_call_graph.json

``storage_root`` is ``$CODE_SEARCH_STORAGE`` or ``~/.claude_code_search``.
Errors are exceptions, not ``SystemExit``, so callers and tests can handle
them; CLI wrappers convert to exit codes.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage
    from search.metadata import MetadataStore


CALL_GRAPH_SUFFIX = "_call_graph.json"


class IndexNotFoundError(LookupError):
    """No project directory, metadata.db, or call graph matched."""


class AmbiguousIndexError(LookupError):
    """More than one project directory matched the requested name."""


@dataclass(frozen=True, slots=True)
class IndexPaths:
    project_dir: Path
    project_id: str
    metadata_db: Path
    call_graph: Path

    @property
    def project_info(self) -> Path:
        return self.project_dir / "project_info.json"

    def read_project_info(self) -> dict[str, Any]:
        if not self.project_info.exists():
            return {}
        return json.loads(self.project_info.read_text(encoding="utf-8"))


def storage_root(override: str | Path | None = None) -> Path:
    if override is not None:
        return Path(override)
    return Path(
        os.environ.get("CODE_SEARCH_STORAGE", Path.home() / ".claude_code_search")
    )


def find_index(
    project_name: str,
    *,
    storage: str | Path | None = None,
    model_slug: str | None = None,
) -> IndexPaths:
    """Resolve ``project_name`` (substring of the directory name) to its paths.

    Args:
        project_name: Substring matched against directory names under
            ``projects/`` (``"claude-context-local"`` matches
            ``claude-context-local_9e7f0a98_f2llm-v2-0.6b_1024d``).
        storage: Storage root override (defaults to env/home).
        model_slug: Optional extra substring (e.g. ``"f2llm-v2-0.6b"``) to
            disambiguate per-model directories; a full HF id is reduced to its
            last path component, lower-cased.

    Raises:
        IndexNotFoundError: no match, or a match without ``metadata.db`` or a
            single ``*_call_graph.json``.
        AmbiguousIndexError: several matches; pass a longer substring or a
            ``model_slug``.
    """
    projects_dir = storage_root(storage) / "projects"
    if not projects_dir.is_dir():
        raise IndexNotFoundError(f"No projects directory at {projects_dir}")
    slug = model_slug.split("/")[-1].lower() if model_slug else None
    matches = sorted(
        d
        for d in projects_dir.iterdir()
        if d.is_dir() and project_name in d.name and (slug is None or slug in d.name)
    )
    if not matches:
        raise IndexNotFoundError(
            f"No project directory containing {project_name!r} under {projects_dir}"
        )
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches)
        raise AmbiguousIndexError(
            f"{project_name!r} matches several project directories: {names}"
        )
    return paths_for(matches[0])


def paths_for(project_dir: Path) -> IndexPaths:
    """Build ``IndexPaths`` for a known project directory, validating contents."""
    metadata_db = project_dir / "index" / "metadata.db"
    if not metadata_db.exists():
        raise IndexNotFoundError(f"No metadata.db under {project_dir / 'index'}")
    graphs = sorted(project_dir.glob(f"*{CALL_GRAPH_SUFFIX}"))
    if len(graphs) != 1:
        found = ", ".join(g.name for g in graphs) or "none"
        raise IndexNotFoundError(
            f"Expected exactly one *{CALL_GRAPH_SUFFIX} under {project_dir}, found: {found}"
        )
    project_id = graphs[0].name[: -len(CALL_GRAPH_SUFFIX)]
    return IndexPaths(
        project_dir=project_dir,
        project_id=project_id,
        metadata_db=metadata_db,
        call_graph=graphs[0],
    )


def open_metadata_store(paths: IndexPaths) -> MetadataStore:
    """Open the SqliteDict-backed metadata store (caller closes it)."""
    from search.metadata import MetadataStore

    return MetadataStore(paths.metadata_db)


def load_call_graph(paths: IndexPaths) -> CodeGraphStorage:
    """Load the persisted NetworkX call graph for ``paths``."""
    from graph.graph_storage import CodeGraphStorage

    storage = CodeGraphStorage(paths.project_id, storage_dir=paths.project_dir)
    if not storage.load():
        raise IndexNotFoundError(f"Failed to load call graph from {paths.call_graph}")
    return storage
