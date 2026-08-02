"""GPU determinism pinning.

The fp32 reranker arm (evaluation/RERANKER_FP32_DETERMINISM_AB_20260802.md)
established that run-to-run MRR flips are kernel-layer noise — cuBLAS
reduction order cascading through the listwise rerank pool — not weight
precision. This module pins the deterministic kernel paths:

- ``CUBLAS_WORKSPACE_CONFIG=:4096:8`` (must be set before the FIRST cuBLAS
  call in the process, i.e. before any model load)
- ``torch.use_deterministic_algorithms(True)``
- ``torch.backends.cudnn.deterministic = True`` / ``benchmark = False``

The pinning is intentionally process-global: the embedder's dense leg feeds
the candidate pool, so whole-pipeline pinning is the point.

Gated by ``performance.deterministic_gpu`` (default False = byte-identical
behavior, no torch global touched).
"""

import logging
import os


logger = logging.getLogger(__name__)

_CUBLAS_WORKSPACE = ":4096:8"

_applied = False


def apply_gpu_determinism(warn_only: bool = False) -> bool:
    """Pin deterministic CUDA kernel paths for the whole process. Idempotent.

    Must run before the first cuBLAS call (first model load) for the
    CUBLAS_WORKSPACE_CONFIG setting to take effect.

    Args:
        warn_only: Passed to ``torch.use_deterministic_algorithms``. False
            raises RuntimeError on ops without a deterministic
            implementation; True downgrades to a warning (the op stays
            non-deterministic — record which ones).

    Returns:
        True if determinism was applied (or already active), False if torch
        is unavailable.
    """
    global _applied
    if _applied:
        return True

    # Env var first — torch reads it lazily at the first cuBLAS call, so it
    # must be in place before any model load. setdefault respects an
    # explicit user override (e.g. ":16:8" for lower memory).
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", _CUBLAS_WORKSPACE)

    try:
        import torch
    except ImportError:
        logger.warning("[DETERMINISM] torch unavailable — GPU determinism not applied")
        return False

    torch.use_deterministic_algorithms(True, warn_only=warn_only)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

    _applied = True
    logger.info(
        "[DETERMINISM] GPU determinism pinned "
        f"(CUBLAS_WORKSPACE_CONFIG={os.environ['CUBLAS_WORKSPACE_CONFIG']}, "
        f"warn_only={warn_only})"
    )
    return True


def is_applied() -> bool:
    """Whether apply_gpu_determinism() has run successfully in this process."""
    return _applied
