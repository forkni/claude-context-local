"""Tests for the quarantine-marker check in tests/conftest.py (_check_quarantine).

A quarantine is owned (reason=, issue=), time-boxed (expires=) and may be
re-dated once (redated=<the old expires date>). After that one re-date, the next
expiry means the test is deleted, with the reason written down.
"""

import datetime as dt
from types import SimpleNamespace

import pytest

import tests.conftest as conftest_module


TODAY = dt.date(2026, 11, 18)


def _item(**marker_kwargs):
    mark = pytest.mark.quarantine(**marker_kwargs).mark
    return SimpleNamespace(
        nodeid="tests/unit/test_x.py::test_flaky",
        get_closest_marker=lambda name: mark if name == "quarantine" else None,
    )


def _check(**marker_kwargs):
    conftest_module._check_quarantine([_item(**marker_kwargs)], today=TODAY)


def _error(**marker_kwargs) -> str:
    with pytest.raises(pytest.UsageError) as excinfo:
        _check(**marker_kwargs)
    return str(excinfo.value)


OWNED = {"reason": "races the index writer", "issue": "#123"}


def test_unexpired_quarantine_passes():
    _check(**OWNED, expires="2026-12-01")


def test_first_redate_within_its_new_date_passes():
    _check(**OWNED, expires="2026-12-01", redated="2026-11-10")


def test_unmarked_item_is_ignored():
    item = SimpleNamespace(nodeid="t", get_closest_marker=lambda name: None)

    conftest_module._check_quarantine([item], today=TODAY)


def test_missing_owner_fields_fail():
    assert "reason=, issue=, expires=" in _error(issue="#1", expires="2026-12-01")


def test_unknown_argument_fails_so_a_typo_cannot_hide_a_redate():
    message = _error(**OWNED, expires="2026-12-01", redate="2026-11-10")

    assert "unknown quarantine argument" in message
    assert "redate" in message


def test_expired_quarantine_offers_one_redate():
    message = _error(**OWNED, expires="2026-11-17")

    assert "expired 2026-11-17" in message
    assert "re-date once" in message


def test_expired_redated_quarantine_must_be_deleted():
    message = _error(**OWNED, expires="2026-11-17", redated="2026-10-01")

    assert "re-dated quarantine expired 2026-11-17" in message
    assert "delete the test" in message


def test_redated_must_be_the_older_date():
    message = _error(**OWNED, expires="2026-12-01", redated="2026-12-01")

    assert "redated= is the OLD expiry date" in message


def test_expiry_day_itself_still_passes():
    _check(**OWNED, expires="2026-11-18")


def test_non_iso_date_fails():
    assert "ISO date" in _error(**OWNED, expires="18/11/2026")
