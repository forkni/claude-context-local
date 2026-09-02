"""Paired bootstrap confidence interval for benchmark A/B deltas.

Every prior ego/pool-order disposition doc in this repo cites "paired 95% CI,
10,000-resample bootstrap, seed 0", but a repo-wide grep finds no committed
bootstrap code -- those numbers came from uncommitted ad-hoc scripts. The
committed path (`run_sscg_benchmark._paired_delta_summary`) uses a normal
approximation whose own docstring calls it "a diagnostic, not a publication
stat". This module makes the cited gate reproducible for the first time.

No scipy dependency (the harness has none) -- pure `random.Random`.
"""

from __future__ import annotations

import random


def paired_bootstrap_ci(
    deltas: list[float],
    *,
    n_resamples: int = 10000,
    seed: int = 0,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Percentile bootstrap CI for the mean of paired per-query deltas.

    Resamples `deltas` with replacement `n_resamples` times, computes the
    mean of each resample, and returns the `(observed_mean, lo, hi)`
    percentile interval at confidence `1 - alpha` (default 95%).

    Deterministic: a fixed `seed` (default 0, matching this repo's
    ADR-0021 PYTHONHASHSEED=0 determinism convention) via `random.Random`
    produces bit-identical output across calls and across processes --
    verified by the unit test.

    Args:
        deltas: paired per-query deltas (e.g. metric(arm_b) - metric(arm_a)
            for each query present in both runs). Must be non-empty.
        n_resamples: number of bootstrap resamples.
        seed: seed for the local `random.Random` instance (not global state).
        alpha: two-sided significance level; 0.05 -> 95% CI.

    Returns:
        `(observed_mean, lo, hi)`. If `deltas` has fewer than 2 elements,
        `lo == hi == observed_mean` (degenerate interval -- there is no
        resampling variance to estimate with 0 or 1 points).

    Raises:
        ValueError: if `deltas` is empty.
    """
    n = len(deltas)
    if n == 0:
        raise ValueError("paired_bootstrap_ci requires at least one delta")

    observed_mean = sum(deltas) / n
    if n < 2:
        return observed_mean, observed_mean, observed_mean

    rng = random.Random(seed)
    resample_means = []
    for _ in range(n_resamples):
        resample = [deltas[rng.randrange(n)] for _ in range(n)]
        resample_means.append(sum(resample) / n)
    resample_means.sort()

    lo_idx = int((alpha / 2) * n_resamples)
    hi_idx = int((1 - alpha / 2) * n_resamples) - 1
    lo_idx = max(0, min(lo_idx, n_resamples - 1))
    hi_idx = max(0, min(hi_idx, n_resamples - 1))

    return observed_mean, resample_means[lo_idx], resample_means[hi_idx]
