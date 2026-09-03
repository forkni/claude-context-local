"""Unit tests for scripts/benchmark/precision_estimate.py.

Fixture numbers are the B3 calibration counts from
``evaluation/RESOLVER_TIER_CALIBRATION_20260902.md`` §5 and the hand-computed
Wilson / prec_est figures recorded in
``evaluation/RESOLVER_PRECISION_LABELS_20260902.md`` ("Decisions").
"""

from __future__ import annotations

import json

import pytest

from scripts.benchmark.precision_estimate import (
    estimate_tiers,
    main,
    prec_est,
    render_table,
    round_to_step,
    wilson_interval,
)


PYAN_COUNTS = {"edges_cov": 723, "hits_cov": 186, "unlabeled_cov": 537}


def _scores(**tiers: dict) -> dict:
    return {"ladder": list(tiers), "tiers": tiers}


def _labels(tier: str, trues: int, falses: int, alt_true: int = 0) -> dict:
    rows = []
    for i in range(trues):
        rows.append({"tier": tier, "caller": f"c{i}", "callee": "x", "label": True})
    for i in range(falses):
        row = {"tier": tier, "caller": f"f{i}", "callee": "x", "label": False}
        if i < alt_true:
            row["alternative_label"] = True
        rows.append(row)
    return {"rows": rows}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_wilson_zero_of_ten_matches_worksheet():
    lo, hi = wilson_interval(0, 10)
    assert lo == 0.0
    assert hi == pytest.approx(0.278, abs=5e-4)


def test_wilson_three_of_ten_matches_worksheet():
    lo, hi = wilson_interval(3, 10)
    assert lo == pytest.approx(0.108, abs=5e-4)
    assert hi == pytest.approx(0.603, abs=5e-4)


def test_wilson_empty_sample_is_degenerate():
    assert wilson_interval(0, 0) == (0.0, 0.0)


def test_prec_est_pyan_stakes():
    assert prec_est(186, 537, 723, 0.0) == pytest.approx(0.2573, abs=5e-5)
    assert prec_est(186, 537, 723, 0.3) == pytest.approx(0.4801, abs=5e-5)


def test_prec_est_zero_denominator():
    assert prec_est(0, 0, 0, 0.5) == 0.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.2573, 0.25), (0.4801, 0.50), (0.874, 0.85), (0.875, 0.90), (0.0, 0.0)],
)
def test_round_to_step(value, expected):
    assert round_to_step(value) == expected


# ---------------------------------------------------------------------------
# estimate_tiers
# ---------------------------------------------------------------------------


def test_pyan_strict_reading_below_reference():
    est = estimate_tiers(_labels("pyan", 0, 10), _scores(pyan=PYAN_COUNTS))
    (e,) = est
    assert e.labeled == 10 and e.labeled_true == 0
    assert e.p_hat == 0.0
    assert e.prec_est == pytest.approx(0.2573, abs=5e-5)
    assert e.prec_est_range[0] == pytest.approx(0.2573, abs=5e-5)
    assert e.prec_est_range[1] == pytest.approx(0.464, abs=1e-3)
    assert e.omega == 0.25
    assert e.vs_reference == "below at point, CI straddles"
    assert e.alternative_prec_est is None


def test_pyan_alternative_reading_reported_but_not_adopted():
    est = estimate_tiers(_labels("pyan", 0, 10, alt_true=3), _scores(pyan=PYAN_COUNTS))
    (e,) = est
    assert e.p_hat == 0.0  # adopted labels drive the estimate
    assert e.alternative_true == 3
    assert e.alternative_prec_est == pytest.approx(0.4801, abs=5e-5)
    assert e.vs_reference.startswith("below")


def test_high_precision_tier_clears_reference():
    counts = {"edges_cov": 100, "hits_cov": 95, "unlabeled_cov": 5}
    (e,) = estimate_tiers(_labels("lsp", 10, 0), _scores(lsp=counts))
    assert e.prec_est == pytest.approx(1.0)
    assert e.vs_reference == "above (CI clear)"
    assert e.omega == 1.0


def test_ladder_order_and_declared_confidence_passthrough():
    scores = _scores(lsp=PYAN_COUNTS, pyan=PYAN_COUNTS)
    labels = {"rows": _labels("pyan", 0, 10)["rows"] + _labels("lsp", 8, 2)["rows"]}
    est = estimate_tiers(labels, scores, declared={"lsp": 0.98, "pyan": 0.75})
    assert [e.tier for e in est] == ["lsp", "pyan"]
    assert est[0].declared_confidence == 0.98
    assert est[1].declared_confidence == 0.75


def test_null_labels_are_skipped_not_counted():
    labels = _labels("pyan", 2, 2)
    labels["rows"].append({"tier": "pyan", "caller": "n", "callee": "x", "label": None})
    (e,) = estimate_tiers(labels, _scores(pyan=PYAN_COUNTS))
    assert e.labeled == 4 and e.labeled_true == 2


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write(tmp_path, name, payload):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_main_refuses_unlabeled_rows(tmp_path, capsys):
    labels = _labels("pyan", 1, 1)
    labels["rows"][0]["label"] = None
    rc = main(
        [
            "--labels",
            _write(tmp_path, "l.json", labels),
            "--scores",
            _write(tmp_path, "s.json", _scores(pyan=PYAN_COUNTS)),
        ]
    )
    assert rc == 1
    assert "label=null" in capsys.readouterr().err


def test_main_json_output(tmp_path, capsys):
    rc = main(
        [
            "--labels",
            _write(tmp_path, "l.json", _labels("pyan", 0, 10)),
            "--scores",
            _write(tmp_path, "s.json", _scores(pyan=PYAN_COUNTS)),
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "resolver-precision-estimate/1"
    assert payload["tiers"][0]["tier"] == "pyan"
    assert payload["tiers"][0]["prec_est"] == pytest.approx(0.2573, abs=5e-5)


def test_render_table_lists_alternative_reading():
    est = estimate_tiers(_labels("pyan", 0, 10, alt_true=3), _scores(pyan=PYAN_COUNTS))
    text = render_table(est, 0.4228)
    assert "| pyan | 10 | 0 | 0.00 |" in text
    assert "3/10 true" in text and "0.4801" in text
