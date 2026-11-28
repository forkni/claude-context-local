"""mcp_server.freshness_batch: many freshness checks, in order, never raising."""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from mcp_server import freshness_batch, index_freshness


@pytest.fixture
def verdicts(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """What the patched compute_index_freshness returns (or raises), by path.

    Threads stand in for worker processes: a patch does not reach a spawned
    process.
    """
    results: dict[str, object] = {}

    def fake(path: str, *, model_slug: str, dimension: int):
        result = results[path]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(index_freshness, "compute_index_freshness", fake)
    monkeypatch.setattr(freshness_batch, "_make_pool", ThreadPoolExecutor)
    return results


def _project(tmp_path: Path, name: str) -> str:
    path = tmp_path / name
    path.mkdir()
    return str(path)


CURRENT = {
    "index_is_current": True,
    "pending_changes": {"added": 0, "modified": 0, "removed": 0},
}


def test_check_one_states(verdicts, tmp_path: Path) -> None:
    ok, none, broken = (_project(tmp_path, n) for n in ("ok", "none", "broken"))
    verdicts.update({ok: CURRENT, none: None, broken: OSError("locked")})

    assert freshness_batch.check_one(ok, "m", 8) == {"state": "ok", "verdict": CURRENT}
    assert freshness_batch.check_one(none, "m", 8) == {"state": "ok", "verdict": None}
    assert freshness_batch.check_one(broken, "m", 8) == {
        "state": "error",
        "message": "OSError: locked",
    }
    assert freshness_batch.check_one(str(tmp_path / "gone"), "m", 8) == {
        "state": "missing"
    }


def test_check_many_keeps_job_order(verdicts, tmp_path: Path) -> None:
    jobs = []
    for i in range(6):
        path = _project(tmp_path, f"p{i}")
        verdicts[path] = {"index_is_current": i % 2 == 0, "pending_changes": {}}
        jobs.append((path, "m", 8))

    results = freshness_batch.check_many(jobs)

    assert [r["verdict"]["index_is_current"] for r in results] == [
        i % 2 == 0 for i in range(6)
    ]


def test_pool_failure_checks_one_by_one(
    verdicts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_pool(workers: int):
        raise OSError("no processes")

    monkeypatch.setattr(freshness_batch, "_make_pool", no_pool)
    jobs = []
    for i in range(3):
        path = _project(tmp_path, f"p{i}")
        verdicts[path] = CURRENT
        jobs.append((path, "m", 8))

    assert freshness_batch.check_many(jobs) == [{"state": "ok", "verdict": CURRENT}] * 3


def test_one_worker_never_starts_a_pool(
    verdicts, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_pool(workers: int):
        raise AssertionError("pool started")

    monkeypatch.setattr(freshness_batch, "_make_pool", no_pool)
    path = _project(tmp_path, "p")
    verdicts[path] = CURRENT
    assert (
        freshness_batch.check_many([(path, "m", 8)] * 2, workers=1)
        == [{"state": "ok", "verdict": CURRENT}] * 2
    )


class TestRunInSubprocess:
    def _fake_run(self, monkeypatch, *, returncode=0, stdout="", raises=None):
        calls: list[dict] = []

        def fake(cmd, **kwargs):
            calls.append({"cmd": cmd, **kwargs})
            if raises is not None:
                raise raises
            return subprocess.CompletedProcess(cmd, returncode, stdout, "boom")

        monkeypatch.setattr(freshness_batch.subprocess, "run", fake)
        return calls

    def test_sends_jobs_and_reads_results(self, monkeypatch) -> None:
        results = [{"state": "ok", "verdict": CURRENT}]
        calls = self._fake_run(monkeypatch, stdout=json.dumps(results))

        assert freshness_batch.run_in_subprocess([("p", "m", 8)]) == results
        call = calls[0]
        assert call["cmd"][1:] == ["-m", "mcp_server.freshness_batch"]
        assert json.loads(call["input"]) == [["p", "m", 8]]
        assert call["cwd"] == freshness_batch.REPO_ROOT

    @pytest.mark.parametrize(
        ("kwargs", "match"),
        [
            ({"returncode": 1}, "exited with 1"),
            ({"stdout": "not json"}, "not JSON"),
            ({"stdout": "[]"}, "0 results for 1 jobs"),
            (
                {"raises": subprocess.TimeoutExpired(["x"], 5)},
                "timed out",
            ),
        ],
        ids=["exit-code", "not-json", "wrong-count", "timeout"],
    )
    def test_failures_raise_runtime_error(self, monkeypatch, kwargs, match) -> None:
        self._fake_run(monkeypatch, **kwargs)
        with pytest.raises(RuntimeError, match=match):
            freshness_batch.run_in_subprocess([("p", "m", 8)])
