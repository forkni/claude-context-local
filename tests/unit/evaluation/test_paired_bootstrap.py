"""Unit tests for evaluation.paired_bootstrap (Phase 2 Step 3, call-graph-recall plan).

Covers the seam that makes this repo's oft-cited "paired 95% CI, 10,000-resample
bootstrap, seed 0" reproducible for the first time: determinism at a fixed seed,
a known-input interval, and the n<2 / all-zero-delta edge cases.
"""

from __future__ import annotations

import pytest

from evaluation.paired_bootstrap import paired_bootstrap_ci


def test_empty_deltas_raises():
    with pytest.raises(ValueError):
        paired_bootstrap_ci([])


def test_single_delta_is_degenerate_interval():
    mean, lo, hi = paired_bootstrap_ci([0.5])
    assert mean == 0.5
    assert lo == 0.5
    assert hi == 0.5


def test_all_zero_deltas_gives_zero_width_interval():
    mean, lo, hi = paired_bootstrap_ci([0.0, 0.0, 0.0, 0.0])
    assert mean == 0.0
    assert lo == 0.0
    assert hi == 0.0


def test_seed_zero_is_bit_identical_across_calls():
    deltas = [0.1, -0.05, 0.2, 0.0, 0.15, -0.1, 0.3, 0.05]
    result_a = paired_bootstrap_ci(deltas, seed=0, n_resamples=2000)
    result_b = paired_bootstrap_ci(deltas, seed=0, n_resamples=2000)
    assert result_a == result_b


def test_different_seeds_can_differ():
    deltas = [0.1, -0.05, 0.2, 0.0, 0.15, -0.1, 0.3, 0.05]
    result_a = paired_bootstrap_ci(deltas, seed=0, n_resamples=2000)
    result_b = paired_bootstrap_ci(deltas, seed=1, n_resamples=2000)
    # The observed mean is seed-independent; only the resampled CI can move.
    assert result_a[0] == result_b[0]


def test_known_input_interval_contains_observed_mean():
    deltas = [0.1] * 20
    mean, lo, hi = paired_bootstrap_ci(deltas, n_resamples=5000)
    assert mean == pytest.approx(0.1)
    # Every resample draws only from {0.1}, so the interval collapses to the
    # observed mean exactly -- a zero-variance input is a strong invariant.
    assert lo == pytest.approx(0.1)
    assert hi == pytest.approx(0.1)


def test_ci_bounds_observed_mean_for_mixed_deltas():
    deltas = [1.0, -1.0, 1.0, -1.0, 0.5, -0.5, 1.0, -1.0]
    mean, lo, hi = paired_bootstrap_ci(deltas, n_resamples=5000)
    assert lo <= mean <= hi


def test_positive_deltas_give_positive_lower_bound():
    # Every element strictly positive -> every bootstrap resample mean is
    # strictly positive -> the CI should exclude zero on the downside.
    deltas = [0.2, 0.3, 0.25, 0.4, 0.35, 0.2, 0.3, 0.25]
    _, lo, _ = paired_bootstrap_ci(deltas, n_resamples=5000)
    assert lo > 0.0
