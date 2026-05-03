"""Path normalization helpers.

Lives in `utils/` to keep `graph/` free of any `search/` dependency
(avoids a graph ↔ search import cycle).
"""


def normalize_path(path: str) -> str:
    """Normalize path separators to forward slashes for consistent matching."""
    return path.replace("\\", "/")
