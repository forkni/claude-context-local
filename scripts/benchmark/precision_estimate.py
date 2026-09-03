#!/usr/bin/env python
"""Per-tier resolver precision estimate from hand labels (read-only, no index/GPU).

Combines the hand-labeled precision sample
(``evaluation/resolver_precision_labels.json``, produced from
``evaluation/resolver_precision_sample.json``) with the B3 calibration counts
(``evaluation/resolver_tier_scores.json`` — ``edges_cov`` / ``hits_cov`` /
``unlabeled_cov`` per tier) to produce, for every resolver tier:

    p_hat      = labeled-true / labeled           (sample true-positive rate)
    wilson     = Wilson 95% interval on p_hat
    prec_est   = (hits_cov + p_hat * unlabeled_cov) / edges_cov
    prec_range = prec_est evaluated at the Wilson bounds
    omega      = prec_est rounded to the nearest 0.05  (plan B4: ω(tier) := prec_est)

and compares each tier against the ``tag:exact`` reference precision
(``evaluation/UNTAGGED_EDGE_WITNESS_20260902.md``, 0.4228) — the comparison the
pyan-removal decision turns on. Rows that carry an ``alternative_label`` are
also reported under that reading so the rejected rule stays visible.

This script only reports. It never edits ``search/config.py``; see
``evaluation/RESOLVER_TIER_CALIBRATION_20260902.md`` §11 for what the output
licenses.

Usage (module form required -- ``scripts`` is not in the editable-install
package map, ADR-0040):
    .venv/Scripts/python.exe -m scripts.benchmark.precision_estimate \
        [--labels evaluation/resolver_precision_labels.json] \
        [--scores evaluation/resolver_tier_scores.json] \
        [--reference 0.4228] [--json]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


# No sys.path bootstrap: run in module form (``python -m
# scripts.benchmark.precision_estimate``) like the other ADR-0040 probes, so
# tests/unit/evaluation/test_probe_hygiene.py's shrink-only ratchet holds.
DEFAULT_LABELS = "evaluation/resolver_precision_labels.json"
DEFAULT_SCORES = "evaluation/resolver_tier_scores.json"
TAG_EXACT_REFERENCE = 0.4228
Z_95 = 1.959963984540054


def wilson_interval(successes: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Returns ``(0.0, 0.0)`` for ``n == 0`` so callers never divide by zero.
    """
    if n <= 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def prec_est(hits_cov: int, unlabeled_cov: int, edges_cov: int, p_hat: float) -> float:
    """``(hits_cov + p_hat * unlabeled_cov) / edges_cov`` — the plan's B4 estimator."""
    if edges_cov <= 0:
        return 0.0
    return (hits_cov + p_hat * unlabeled_cov) / edges_cov


def round_to_step(value: float, step: float = 0.05) -> float:
    """Round to the nearest multiple of ``step`` (half-up, not banker's)."""
    return round(math.floor(value / step + 0.5) * step, 2)


@dataclass(frozen=True)
class TierEstimate:
    tier: str
    labeled: int
    labeled_true: int
    p_hat: float
    p_hat_ci: tuple[float, float]
    edges_cov: int
    hits_cov: int
    unlabeled_cov: int
    prec_lb_cov: float
    prec_est: float
    prec_est_range: tuple[float, float]
    omega: float
    declared_confidence: float | None
    vs_reference: str
    alternative_true: int | None = None
    alternative_prec_est: float | None = None


def _relation(lo: float, point: float, hi: float, ref: float) -> str:
    if lo > ref:
        return "above (CI clear)"
    if hi < ref:
        return "below (CI clear)"
    return f"{'above' if point >= ref else 'below'} at point, CI straddles"


def estimate_tiers(
    labels: dict[str, Any],
    scores: dict[str, Any],
    reference: float = TAG_EXACT_REFERENCE,
    declared: dict[str, float] | None = None,
) -> list[TierEstimate]:
    """Compute one :class:`TierEstimate` per ladder tier present in ``scores``."""
    ladder = list(scores.get("ladder") or scores["tiers"].keys())
    by_tier: dict[str, list[dict[str, Any]]] = {t: [] for t in ladder}
    for row in labels["rows"]:
        if row.get("label") is None:
            continue
        by_tier.setdefault(row["tier"], []).append(row)

    out: list[TierEstimate] = []
    for tier in ladder:
        rows = by_tier.get(tier, [])
        n = len(rows)
        k = sum(1 for r in rows if r["label"] is True)
        p = k / n if n else 0.0
        lo, hi = wilson_interval(k, n)
        counts = scores["tiers"][tier]
        edges_cov = int(counts["edges_cov"])
        hits_cov = int(counts["hits_cov"])
        unlabeled_cov = int(counts["unlabeled_cov"])
        point = prec_est(hits_cov, unlabeled_cov, edges_cov, p)
        rng = (
            prec_est(hits_cov, unlabeled_cov, edges_cov, lo),
            prec_est(hits_cov, unlabeled_cov, edges_cov, hi),
        )
        alt_k = sum(1 for r in rows if r.get("alternative_label", r["label"]) is True)
        alt_point = (
            prec_est(hits_cov, unlabeled_cov, edges_cov, alt_k / n)
            if n and alt_k != k
            else None
        )
        out.append(
            TierEstimate(
                tier=tier,
                labeled=n,
                labeled_true=k,
                p_hat=round(p, 4),
                p_hat_ci=(round(lo, 4), round(hi, 4)),
                edges_cov=edges_cov,
                hits_cov=hits_cov,
                unlabeled_cov=unlabeled_cov,
                prec_lb_cov=round(hits_cov / edges_cov, 4) if edges_cov else 0.0,
                prec_est=round(point, 4),
                prec_est_range=(round(rng[0], 4), round(rng[1], 4)),
                omega=round_to_step(point),
                declared_confidence=(declared or {}).get(tier),
                vs_reference=_relation(rng[0], point, rng[1], reference),
                alternative_true=alt_k if alt_point is not None else None,
                alternative_prec_est=(
                    round(alt_point, 4) if alt_point is not None else None
                ),
            )
        )
    return out


# Declared per-tier confidences are constants in the resolver modules, not
# config knobs: lsp_call_graph.py (0.98), libcst_call_graph.py (0.90),
# external_call_graph.py (0.75; 0.6 for its recovered edges). The AST tier
# uses 0.5/0.7 by match kind and has no single figure.
DECLARED_CONFIDENCE: dict[str, float | None] = {
    "lsp": 0.98,
    "libcst": 0.90,
    "pyan": 0.75,
    "ast": None,
}


def render_table(estimates: list[TierEstimate], reference: float) -> str:
    header = (
        "| tier | n | true | p̂ | Wilson 95% | edges_cov | hits_cov | "
        "unlabeled_cov | prec_lb_cov | prec_est | range | ω | declared | "
        f"vs tag:exact {reference} |"
    )
    sep = "|" + " --- |" * 14
    lines = [header, sep]
    for e in estimates:
        declared = (
            "" if e.declared_confidence is None else f"{e.declared_confidence:.2f}"
        )
        lines.append(
            f"| {e.tier} | {e.labeled} | {e.labeled_true} | {e.p_hat:.2f} | "
            f"[{e.p_hat_ci[0]:.3f}, {e.p_hat_ci[1]:.3f}] | {e.edges_cov:,} | "
            f"{e.hits_cov:,} | {e.unlabeled_cov:,} | {e.prec_lb_cov:.4f} | "
            f"**{e.prec_est:.4f}** | [{e.prec_est_range[0]:.4f}, "
            f"{e.prec_est_range[1]:.4f}] | {e.omega:.2f} | {declared} | "
            f"{e.vs_reference} |"
        )
    alts = [e for e in estimates if e.alternative_prec_est is not None]
    if alts:
        lines.append("")
        lines.append("Alternative (rejected) readings recorded in the labels file:")
        for e in alts:
            lines.append(
                f"- {e.tier}: {e.alternative_true}/{e.labeled} true → "
                f"prec_est {e.alternative_prec_est:.4f} "
                f"(ω {round_to_step(e.alternative_prec_est):.2f})"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    parser.add_argument("--scores", default=DEFAULT_SCORES)
    parser.add_argument("--reference", type=float, default=TAG_EXACT_REFERENCE)
    parser.add_argument(
        "--json", action="store_true", help="emit JSON instead of a table"
    )
    args = parser.parse_args(argv)

    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    scores = json.loads(Path(args.scores).read_text(encoding="utf-8"))
    unlabeled = [r for r in labels["rows"] if r.get("label") is None]
    if unlabeled:
        print(f"error: {len(unlabeled)} rows still have label=null", file=sys.stderr)
        return 1

    estimates = estimate_tiers(labels, scores, args.reference, DECLARED_CONFIDENCE)
    if args.json:
        payload = {
            "schema": "resolver-precision-estimate/1",
            "labels": args.labels,
            "scores": args.scores,
            "reference_tag_exact": args.reference,
            "tiers": [asdict(e) for e in estimates],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_table(estimates, args.reference))
    return 0


if __name__ == "__main__":
    sys.exit(main())
