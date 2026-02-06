"""Dimension validation utilities for index-embedder compatibility."""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from search.exceptions import DimensionMismatchError


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder


logger = logging.getLogger(__name__)


def read_index_metadata(storage_dir: Path) -> Optional[dict]:
    """Read index metadata from project_info.json.

    Args:
        storage_dir: Project storage directory (contains project_info.json)

    Returns:
        Dict with embedding_model and model_dimension, or None if not found
    """
    # Handle both project dir and index subdir
    if storage_dir.name == "index":
        project_info_path = storage_dir.parent / "project_info.json"
    else:
        project_info_path = storage_dir / "project_info.json"

    if not project_info_path.exists():
        return None

    try:
        with open(project_info_path) as f:
            info = json.load(f)
        return {
            "embedding_model": info.get("embedding_model"),
            "model_dimension": info.get("model_dimension"),
        }
    except Exception as e:
        logger.warning(f"Failed to read project_info.json: {e}")
        return None


def validate_embedder_index_compatibility(
    embedder: Optional["CodeEmbedder"],
    storage_dir: Path,
    raise_on_mismatch: bool = True,
) -> tuple[bool, Optional[str]]:
    """Validate that embedder dimension matches stored index dimension.

    Call BEFORE creating HybridSearcher or loading indices.

    Args:
        embedder: CodeEmbedder instance
        storage_dir: Path to project storage directory
        raise_on_mismatch: If True, raise DimensionMismatchError on mismatch

    Returns:
        Tuple of (is_compatible, error_message)

    Raises:
        DimensionMismatchError: If dimensions don't match and raise_on_mismatch=True
    """
    if embedder is None:
        return True, None

    try:
        model_info = embedder.get_model_info()
        embedder_dim = model_info.get("embedding_dimension")
        embedder_model = embedder.model_name
    except Exception as e:
        logger.debug(f"Could not get embedder info: {e}")
        return True, None

    if embedder_dim is None:
        return True, None

    metadata = read_index_metadata(storage_dir)
    if metadata is None:
        return True, None  # No existing index

    index_dim = metadata.get("model_dimension")
    index_model = metadata.get("embedding_model", "unknown")

    if index_dim is None:
        return True, None

    if embedder_dim != index_dim:
        error_msg = (
            f"DIMENSION MISMATCH DETECTED!\n"
            f"  Embedder: {embedder_model} ({embedder_dim}d)\n"
            f"  Index: {index_model} ({index_dim}d)\n"
            f"The selected embedding model is incompatible with the stored index."
        )

        logger.error(error_msg)

        if raise_on_mismatch:
            raise DimensionMismatchError(
                error_msg,
                embedder_dim=embedder_dim,
                index_dim=index_dim,
                embedder_model=embedder_model,
                index_model=index_model,
            )

        return False, error_msg

    logger.debug(
        f"Dimension validation passed: embedder={embedder_model} ({embedder_dim}d), "
        f"index={index_model} ({index_dim}d)"
    )
    return True, None
