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
"""

from __future__ import annotations

from pathlib import Path


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
