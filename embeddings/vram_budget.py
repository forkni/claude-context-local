"""VRAM budget: the per-process PyTorch cap and GPU batch sizing.

Everything that decides how much VRAM this process may hold and how many
chunks fit in one embedding batch lives here.  ``set_vram_limit`` applies the
cap; ``compute_effective_vram_cap`` is the pure measurement behind it;
``calculate_optimal_batch_size`` turns free VRAM into a batch size.
"""

import logging
from typing import NamedTuple

from search.config import (
    get_indexing_ram_fallback_override as _get_ram_fallback_override,
)
from search.config import (
    get_search_config,
)


try:
    import torch
except ImportError:
    torch = None


# ===== BATCH SIZE MEMORY ESTIMATION =====
# Empirically derived from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18% overhead
FRAGMENTATION_OVERHEAD = 0.82  # 1.0 - 0.18 = 82% usable VRAM, 18% fragmentation

# Working room the per-process VRAM cap keeps above live tensors.  Without it an
# external squeeze pins the cap at the model-weight size, where even a 2 MiB
# segment OOMs and batch halving cannot recover.
_DEFAULT_MIN_ROOM_GB = 0.25
# Measured activation items of room ``embed_chunks`` asks for on top of that.
_MIN_ROOM_ITEMS = 2


class VramCapReading(NamedTuple):
    """Result of ``compute_effective_vram_cap`` (tuple-compatible)."""

    effective_fraction: float  # value for set_per_process_memory_fraction
    cap_bytes: int
    free_gb: float
    us_gb: float
    other_gb: float
    headroom_gb: float
    room_gb: float  # cap above live tensors


def compute_effective_vram_cap(
    fraction: float, min_room_b: int = 0
) -> VramCapReading | None:
    """Compute effective VRAM cap accounting for other-process allocations.

    Pure function — reads current GPU state, does not set any limits or produce
    any side effects.  Used by the PyTorch-cap path (``set_vram_limit``).

    Formula::

        T            = total device VRAM
        F            = system-wide free VRAM (excludes ALL processes)
        A_live       = bytes of live tensors (memory_allocated)
        A_us         = bytes our allocator has reserved (memory_reserved) —
                       live tensors PLUS cached-but-unused blocks.  ``F``
                       excludes the cache, so it must count as ours, not as
                       another process's (else the cap collapses to A_live
                       right after the activation warmup).
        A_other      = T - F - A_us  (held by every other process)
        headroom     = (1 − fraction) × T   (safety reserve)
        physical_cap = A_us + F − headroom  (max we can hold without spill)
        cap          = max(min(user_cap, physical_cap), A_live)
        cap          = max(cap, A_live + min(min_room, A_us - A_live + F))
        effective_fraction = clamp(cap / T, 0.05, fraction)

    The floor is ``A_live``, not ``A_us``: the allocator frees cached blocks
    and retries when a new segment would exceed the cap, so only live tensors
    are unrecoverable.  Under external pressure the cap would sit exactly at
    ``A_live``, where even a 2 MiB segment OOMs; ``min_room`` keeps working room
    above it, bounded by memory that exists (own cache plus system free), so it
    cannot cause spillover by itself.

    Args:
        fraction: Requested fraction of total VRAM (0.05–1.0).
        min_room_b: Working room in bytes to keep above live tensors (0 = none).

    Returns:
        A ``VramCapReading`` or ``None`` if CUDA is unavailable or measurement
        fails.

        - *effective_fraction* — value for ``set_per_process_memory_fraction``
        - *cap_bytes*          — cap in bytes (diagnostic)
        - *free_gb / us_gb / other_gb / headroom_gb* — diagnostic values for logs
        - *room_gb*            — cap above live tensors (working room)
    """
    if not torch or not torch.cuda.is_available():
        return None
    try:
        free_b, total_b = torch.cuda.mem_get_info(0)
        live_b = torch.cuda.memory_allocated(0)
        us_b = max(torch.cuda.memory_reserved(0), live_b)
        other_b = max(0, total_b - free_b - us_b)

        headroom_b = int((1.0 - fraction) * total_b)
        user_cap_b = int(fraction * total_b)
        physical_cap_b = us_b + free_b - headroom_b

        cap_b = min(user_cap_b, physical_cap_b)
        cap_b = max(cap_b, live_b)  # cannot shrink below live tensors
        grantable_b = max(0, us_b - live_b + free_b)
        cap_b = max(cap_b, live_b + min(min_room_b, grantable_b))

        effective_fraction = (cap_b / total_b) if total_b > 0 else fraction
        effective_fraction = max(0.05, min(effective_fraction, fraction))

        return VramCapReading(
            effective_fraction,
            int(cap_b),
            free_b / 1024**3,
            us_b / 1024**3,
            other_b / 1024**3,
            headroom_b / 1024**3,
            (cap_b - live_b) / 1024**3,
        )
    except (RuntimeError, ValueError, AssertionError):
        return None


def set_vram_limit(
    fraction: float = 0.90, min_room_gb: float = _DEFAULT_MIN_ROOM_GB
) -> bool:
    """Set hard VRAM limit on the PyTorch CUDA allocator to prevent spillover.

    On Windows, the NVIDIA driver preemptively evicts to shared memory when
    VRAM approaches capacity. This hard limit prevents that by raising OOM
    errors instead of spilling (which is much faster than slow spillover).

    The effective fraction is computed by ``compute_effective_vram_cap`` from
    live ``mem_get_info`` readings so that memory held by other processes
    (browser, games, other ML jobs) is subtracted from our budget.

    It is safe and expected to call this function multiple times; each call
    re-measures the system state and re-applies the cap.

    **Note on `allow_ram_fallback`**: when True in config, this function
    returns without applying any cap — the PyTorch allocator is uncapped and
    the OS may spill to shared RAM.

    **FAISS**: ``set_per_process_memory_fraction`` only governs the PyTorch
    CUDA allocator.  FAISS GPU indexes use their own allocator and are not
    constrained here.

    Args:
        fraction: Requested fraction of dedicated VRAM (default: 0.90 = 90%).
            The *effective* fraction may be lower when other processes hold VRAM.
            Recommended: 0.80–0.90 depending on GPU headroom needs.
        min_room_gb: Working room to keep above live tensors, so an external
            squeeze cannot pin the cap at the model-weight size.

    Returns:
        True if limit was set (or skipped due to allow_ram_fallback), else False.
    """
    if not torch or not torch.cuda.is_available():
        return False

    # Check if RAM fallback is allowed — if so, skip the PyTorch cap only.
    # The module-level override (_indexing_ram_fallback_override in search.config) takes
    # priority over the persisted config value: it survives _config_manager = None resets
    # that happen on every model switch during multi-model indexing and would otherwise
    # silently restore allow_ram_fallback=True from disk between per-model embed passes.
    try:
        override = _get_ram_fallback_override()
        if override is not None:
            allow_fallback = override
        else:
            config = get_search_config()
            allow_fallback = bool(config and config.performance.allow_ram_fallback)
        if allow_fallback:
            logging.getLogger(__name__).info(
                "[VRAM_LIMIT] RAM fallback allowed - skipping PyTorch VRAM cap"
            )
            return True  # Don't set limit, allow PyTorch spillover
    except Exception as e:  # noqa: BLE001 - parse-recovery: config unavailable, use defaults
        logging.getLogger(__name__).debug(f"Config not available, using defaults: {e}")

    logger = logging.getLogger(__name__)
    result = compute_effective_vram_cap(fraction, min_room_b=int(min_room_gb * 1024**3))
    if result is None:
        logger.warning("[VRAM_LIMIT] Failed to measure VRAM state — cap not applied")
        return False

    effective_fraction, cap_b, free_gb, us_gb, other_gb, headroom_gb, room_gb = result

    # Warn when free memory is below the requested headroom (external GPU pressure).
    if free_gb < headroom_gb:
        logger.warning(
            f"[VRAM_LIMIT] Cannot honor requested headroom — GPU under external "
            f"pressure. Requested={fraction:.0%}, effective={effective_fraction:.0%} "
            f"(free={free_gb:.1f}GB, us={us_gb:.1f}GB, "
            f"other={other_gb:.1f}GB, headroom={headroom_gb:.1f}GB, "
            f"room={room_gb:.2f}GB)"
        )
    else:
        logger.info(
            f"[VRAM_LIMIT] Requested={fraction:.0%}, effective={effective_fraction:.0%} "
            f"(free={free_gb:.1f}GB, us={us_gb:.1f}GB, "
            f"other={other_gb:.1f}GB, headroom={headroom_gb:.1f}GB, "
            f"room={room_gb:.2f}GB)"
        )

    if room_gb + 1e-6 < min_room_gb:
        logger.warning(
            f"[VRAM_LIMIT] Only {room_gb:.2f}GB working room (wanted "
            f"{min_room_gb:.2f}GB) — GPU nearly full; expect OOM recovery"
        )

    try:
        torch.cuda.set_per_process_memory_fraction(effective_fraction, device=0)
        return True
    except (RuntimeError, ValueError, AssertionError, TypeError) as e:
        logger.warning(f"[VRAM_LIMIT] Failed to set: {e}")
        return False


def _own_cached_vram_gb() -> float:
    """GB our allocator holds reserved but unused (e.g. after the activation warmup).

    ``mem_get_info`` free excludes it, yet PyTorch reuses it for the next batch.
    """
    if not torch:
        return 0.0
    cached_b = torch.cuda.memory_reserved(0) - torch.cuda.memory_allocated(0)
    return max(0.0, cached_b / 1024**3)


def calculate_optimal_batch_size(
    embedding_dim: int = 768,
    min_batch: int = 32,
    max_batch: int = 256,  # Conservative cap to prevent spillover
    memory_fraction: float = 0.8,  # Target 80% VRAM utilization (20% headroom)
    model_vram_gb: float = 0.0,
    model_name: str | None = None,
    activation_gb_per_item: float = 0.0,
) -> int:
    """Calculate optimal batch size from architecture-derived activation memory cost.

    Uses a mathematically derived activation cost per batch item (from model
    architecture parameters via ``estimate_activation_gb_from_config()``) rather
    than hardcoded tier-based constants.  The cost is supplied by the caller so
    that both runtime-measured and formula-estimated values can be used without
    duplicating GPU probing logic here.

    Args:
        embedding_dim: Embedding output dimension (unused, kept for API compat)
        min_batch: Minimum batch size (safety floor, default: 32)
        max_batch: Maximum batch size (conservative cap, default: 256)
        memory_fraction: Target VRAM utilization (default: 0.8 = 80%)
        model_vram_gb: Model weight VRAM in GB (used only for logging)
        model_name: Model identifier (used only for logging)
        activation_gb_per_item: Pre-computed activation cost per batch item in GB.
            Pass 0.0 to signal "unknown" — a 40 MB floor will be used.

    Returns:
        Batch size clamped to [min_batch, max_batch]

    Examples:
        >>> # RTX 4090 (24GB), F2LLM-v2-0.6B, 0.855 GB/item measured
        >>> # (peak-length x32 probe, 2026-09-23 -- see embedder.py:98-101).
        >>> # Landing on min_batch here is expected: the probe is
        >>> # peak-length by design (ADR-0007 #54), not a bug.
        >>> calculate_optimal_batch_size(activation_gb_per_item=0.855, model_vram_gb=1.1)
        32  # ~(16GB free × 0.8 × 0.82) / 0.855 = 12, floored to min_batch default
    """
    if not torch or not torch.cuda.is_available():
        return min_batch  # CPU fallback

    try:
        # Get system-wide free/total GPU memory (accounts for ALL processes)
        free_memory, total_memory = torch.cuda.mem_get_info(0)
        total_gb = total_memory / (1024**3)
        free_gb = free_memory / (1024**3)

        # Free memory excludes our own reusable allocator cache; weights stay excluded.
        available_gb = free_gb + _own_cached_vram_gb()

        # Apply fragmentation factor: PyTorch caching allocator reserves ~18% extra
        # Validated from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18%
        target_activation_gb = available_gb * memory_fraction * FRAGMENTATION_OVERHEAD

        # Use provided activation cost per item (0.0 → 40 MB safety floor)
        gb_per_item = activation_gb_per_item if activation_gb_per_item > 0 else 0.04

        # Calculate optimal batch size from activation budget
        optimal_batch = int(target_activation_gb / gb_per_item)

        # Apply GPU tier limits
        if total_gb <= 6:  # minimal tier (<6GB)
            max_batch = min(max_batch, 16)
            min_batch = min(min_batch, 2)
        elif total_gb <= 10:  # laptop tier (6–10GB)
            max_batch = min(max_batch, 32)
            min_batch = min(min_batch, 4)

        # Additional cap based on actual available memory (other processes may hold VRAM)
        if available_gb < 4:
            max_batch = min(max_batch, 8)
        elif available_gb < 6:
            max_batch = min(max_batch, 16)

        # Clamp to safe bounds
        result = max(min_batch, min(optimal_batch, max_batch))

        logger = logging.getLogger(__name__)
        logger.info(
            f"[DYNAMIC_BATCH] GPU: {free_gb:.1f}GB free / {total_gb:.1f}GB total, "
            f"model: {model_vram_gb:.1f}GB ({model_name or 'unknown'}), "
            f"available: {available_gb:.1f}GB → "
            f"target: {target_activation_gb:.1f}GB "
            f"({memory_fraction:.0%} × {FRAGMENTATION_OVERHEAD:.0%} frag), "
            f"cost: {gb_per_item:.3f}GB/item → batch: {result} chunks"
        )

        return result

    except (RuntimeError, ValueError) as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[DYNAMIC_BATCH] Failed to calculate batch size: {e}, "
            f"using min_batch={min_batch}"
        )
        return min_batch  # Fallback on error
