"""Path normalization helpers.

Lives in `utils/` to keep `graph/` free of any `search/` dependency
(avoids a graph ↔ search import cycle).
"""


def normalize_path(path: str) -> str:
    """Normalize path separators to forward slashes for consistent matching."""
    return path.replace("\\", "/")


def path_matches(candidate_path: str, normalized_targets: set[str]) -> bool:
    """Return True if normalize_path(candidate_path) is in normalized_targets.

    Exact equality only — no bidirectional substring. Kills auth.py ⊂ oauth.py.
    """
    return normalize_path(candidate_path) in normalized_targets
