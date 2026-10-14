"""Model-directory naming: the one rule six call sites used to re-derive by hand.

Each indexed project gets one storage directory *per embedding model* under
``projects/`` (see ``mcp_server.storage_manager.get_project_storage_dir``), named:

    {project_name}_{project_hash}_{model_slug}_{dimension}d

``project_id`` — the model-scoped identifier used as an on-disk filename prefix
and as a constructor kwarg on ``CodeIndexManager``, ``HybridSearcher`` and
``GraphIntegration`` — is everything before the trailing ``_{dimension}d``
suffix. Before this module existed, that suffix-strip was re-derived by string
surgery at six call sites (one of them a test reimplementing the production
rule to build its own fixture), with no single owner and no guarantee the
copies stayed in sync.

This module does not change behaviour: it names the existing rule. Callers
keep their own guards and fallbacks; nothing here raises.

It also owns the storage *root* those directories live under
(``resolve_storage_root``), so search/ and merkle/ can find it without
importing mcp_server/ (ADR-0004, ADR-0051). ``mcp_server.storage_manager.
get_storage_dir`` caches the result per process.
"""

from __future__ import annotations

import contextlib
import logging
import os
from pathlib import Path


logger = logging.getLogger(__name__)


MODEL_DIR_TEMPLATE = "{project_name}_{project_hash}_{model_slug}_{dimension}d"


def build_model_dir_name(
    project_name: str, project_hash: str, model_slug: str, dimension: int
) -> str:
    """Build a model-directory name from its components.

    Args:
        project_name: The project's directory name (e.g. ``claude-context-local``).
        project_hash: Drive-agnostic (or legacy) hash of the resolved project path.
        model_slug: Embedding model identifier slug (see ``search.config.get_model_slug``).
        dimension: Effective embedding dimension (truncate_dim if set, else native).

    Returns:
        The directory name, e.g. ``claude-context-local_caf2e75a_f2llm-v2-0.6b_1024d``.
    """
    return MODEL_DIR_TEMPLATE.format(
        project_name=project_name,
        project_hash=project_hash,
        model_slug=model_slug,
        dimension=dimension,
    )


def project_id_from_model_dir_name(name: str) -> str:
    """Derive the model-scoped ``project_id`` from a model-directory name.

    Strips the trailing ``_{dimension}d`` suffix — everything after the last
    underscore. Despite the name, ``project_id`` is model-scoped: the same
    project indexed under two models has two different ``project_id``s.

    Total function — never raises. Preserves ``str.rsplit`` semantics exactly,
    including the degenerate case: a name with no underscore is returned
    unchanged.

    Args:
        name: A model-directory name (typically ``Path.name``).

    Returns:
        The ``project_id`` (name with the trailing ``_{dimension}d`` removed).
    """
    return name.rsplit("_", 1)[0]


def project_id_from_index_dir(index_dir: Path) -> str:
    """Derive ``project_id`` from an index directory's parent (the model dir).

    Several callers hold a reference to the ``index/`` subdirectory rather
    than the model directory itself; this is the same rule as
    ``project_id_from_model_dir_name``, applied to ``index_dir.parent.name``.

    Args:
        index_dir: The ``index/`` subdirectory of a model directory.

    Returns:
        The ``project_id`` for that model directory.
    """
    return project_id_from_model_dir_name(index_dir.parent.name)


# Filename written into every legitimate storage root on first init.
# Downstream guards use its presence to verify a directory is a real
# storage root before performing destructive operations.
STORAGE_SENTINEL = ".claude_code_search_storage"

# Project-root markers — if any ancestor of the candidate path contains
# one of these (excluding the home dir itself), the path is inside a
# source tree and must be refused as storage location.
_PROJECT_MARKERS = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
)


def validate_storage_path(path: Path) -> tuple[bool, str]:
    """Check that *path* is a safe location for an index storage root.

    Refuses:
    - The user's home directory itself or a filesystem root
    - Any path whose directory tree (up to home) contains a project-root marker

    Returns ``(True, "ok")`` when safe, ``(False, reason)`` when refused.
    """
    p = path.resolve()
    home = Path.home()

    if p == home or p == Path(p.anchor):
        return False, f"refusing home dir or filesystem root: {p}"

    for ancestor in (p, *p.parents):
        if ancestor == home or ancestor == ancestor.parent:
            break
        for marker in _PROJECT_MARKERS:
            if (ancestor / marker).exists():
                return (
                    False,
                    f"path is inside a project tree ({marker} found at {ancestor})",
                )

    return True, "ok"


def resolve_storage_root() -> Path:
    """Resolve, create and mark the base storage directory (uncached).

    Reads CODE_SEARCH_STORAGE env var if set; falls back to
    ``~/.claude_code_search``.  Refuses paths that sit inside a project
    source tree (have a .git / pyproject.toml ancestor) and falls back to
    the default rather than using the unsafe path.

    Returns:
        Path to the base storage directory
    """
    env_val = os.getenv("CODE_SEARCH_STORAGE")
    if env_val:
        candidate = Path(env_val).expanduser()
        ok, reason = validate_storage_path(candidate)
        if not ok:
            logger.error(
                "CODE_SEARCH_STORAGE=%r is unsafe (%s); "
                "falling back to ~/.claude_code_search",
                env_val,
                reason,
            )
            candidate = Path.home() / ".claude_code_search"
    else:
        candidate = Path.home() / ".claude_code_search"

    candidate.mkdir(parents=True, exist_ok=True)

    sentinel = candidate / STORAGE_SENTINEL
    if not sentinel.exists():
        with contextlib.suppress(OSError):
            sentinel.write_text("claude-context-local storage root\n", encoding="utf-8")

    return candidate
