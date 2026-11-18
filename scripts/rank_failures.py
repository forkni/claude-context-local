#!/usr/bin/env python3
"""
Rank Failures - turn N test runs into a per-test flake table.

Companion to AUDIT.md Step 4 ("Flakiness rate"). A pass/fail summary of ten runs hides which
test is the problem; this counts, per test, how often it ran and failed across many runs and
ranks them (the `collections.Counter` ranking idea from Kofler, *Scripting*, pp.261-264).

Inputs (any mix of files and directories; a directory contributes every *.xml / *.log / *.txt
inside it, sorted by modification time so "first seen" means oldest run first):
    JUnit XML     from `pytest --junitxml=run1.xml` or a CI artifact. One file = one run.
                  Test id is `classname::name`.
    pytest log    the text of `pytest -rA` (or `-rfEp`); lines `PASSED|FAILED|ERROR <nodeid>`.
                  One file = one run. Test id is the pytest node id.
Do not mix both kinds in one invocation: the two id spellings differ, so the same test would
show up twice.

Per test it reports runs, fails, flake rate, the first run it failed in, and a verdict:
    flaky      failed in some runs and passed in others (the one to root-cause)
    failing    failed in every run it appeared in (broken, not flaky)
    stable     never failed
Skipped runs do not count as runs.

    python rank_failures.py run1.xml run2.xml run3.xml
    python rank_failures.py artifacts/ --min-fails 1 --top 20 --json
    python rank_failures.py run*.xml --history .flake-history.jsonl     # append + trend
    python rank_failures.py --from-history .flake-history.jsonl         # rank the history

--history appends one record per distinct set of inputs, keyed by a digest of the file
contents (dedupe-before-append, Kofler p.320): re-running over the same artifacts never
double-counts. Rank over the whole history later with --from-history.

Exit codes (Kofler p.97): 0 no failures, 1 error (unreadable/unparsable input), 2 usage,
3 flaky tests found, 4 consistent failures only (nothing flaky).

Stdlib-only. JUnit files from CI are untrusted input: xml.etree is used as-is (expat guards
against entity-expansion blow-ups) and nothing in them is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


__version__ = "1.0.0"

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_FLAKY, EXIT_FAILING = 0, 1, 2, 3, 4

RUN_SUFFIXES = {".xml", ".log", ".txt"}
# `pytest -rA` short summary: "PASSED tests/a.py::t", "FAILED tests/a.py::t - msg". The nodeid
# runs to the first " - " (pytest's own separator) or end of line.
LOG_LINE = re.compile(
    r"^(PASSED|FAILED|ERROR|XFAIL|XPASS|SKIPPED)\s+(\S.*?)(?:\s+-\s.*)?$"
)
FAIL_OUTCOMES = {"FAILED", "ERROR"}


class InputError(Exception):
    """An input file could not be read or parsed."""


def parse_junit(path: Path) -> dict[str, bool]:
    """Return {test_id: failed} for one JUnit file. Skipped tests are omitted."""
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise InputError(f"{path}: not a readable JUnit XML file ({exc})") from exc
    results: dict[str, bool] = {}
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("skipped") is not None:
            continue
        failed = case.find("failure") is not None or case.find("error") is not None
        results[test_id] = results.get(test_id, False) or failed
    return results


def parse_log(path: Path) -> dict[str, bool]:
    """Return {test_id: failed} for one `pytest -rA` log."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise InputError(f"{path}: {exc}") from exc
    results: dict[str, bool] = {}
    for line in text.splitlines():
        match = LOG_LINE.match(line.strip())
        if not match:
            continue
        outcome, test_id = match.groups()
        if outcome in {"SKIPPED", "XFAIL"}:
            continue
        results[test_id] = results.get(test_id, False) or outcome in FAIL_OUTCOMES
    return results


def parse_run(path: Path) -> dict[str, bool]:
    return parse_junit(path) if path.suffix.lower() == ".xml" else parse_log(path)


def collect_inputs(paths: list[str]) -> list[Path]:
    """Expand directories, keep given order for files; directory members go oldest first."""
    files: list[Path] = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            members = [
                p
                for p in path.iterdir()
                if p.is_file() and p.suffix.lower() in RUN_SUFFIXES
            ]
            files.extend(sorted(members, key=lambda p: (p.stat().st_mtime, p.name)))
        elif path.is_file():
            files.append(path)
        else:
            raise InputError(f"{path}: no such file or directory")
    return files


def digest_of(files: list[Path]) -> str:
    """Order-independent digest of the inputs' contents (the dedupe key for --history)."""
    parts = sorted(hashlib.sha256(p.read_bytes()).hexdigest() for p in files)
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def tally(runs: list[tuple[str, dict[str, bool]]]) -> dict[str, dict]:
    """Aggregate [(run_label, {test: failed})] into per-test stats."""
    runs_seen: Counter[str] = Counter()
    fails: Counter[str] = Counter()
    first_failed: dict[str, str] = {}
    for label, results in runs:
        for test_id, failed in results.items():
            runs_seen[test_id] += 1
            if failed:
                fails[test_id] += 1
                first_failed.setdefault(test_id, label)
    return {
        test_id: {
            "runs": runs_seen[test_id],
            "fails": fails[test_id],
            "first_failed": first_failed.get(test_id),
        }
        for test_id in runs_seen
    }


def verdict(stats: dict) -> str:
    if stats["fails"] == 0:
        return "stable"
    return "failing" if stats["fails"] == stats["runs"] else "flaky"


def rank(stats_by_test: dict[str, dict], min_fails: int, min_runs: int) -> list[dict]:
    rows = []
    for test_id, stats in stats_by_test.items():
        if stats["fails"] < min_fails or stats["runs"] < min_runs:
            continue
        rows.append(
            {
                "test": test_id,
                "runs": stats["runs"],
                "fails": stats["fails"],
                "rate": stats["fails"] / stats["runs"],
                "first_failed": stats["first_failed"],
                "verdict": verdict(stats),
            }
        )
    # Most failures first; among equals prefer flaky over failing (flaky is the actionable one).
    rows.sort(key=lambda r: (-r["fails"], r["verdict"] != "flaky", r["test"]))
    return rows


def exit_code_for(rows: list[dict]) -> int:
    verdicts = {r["verdict"] for r in rows}
    if "flaky" in verdicts:
        return EXIT_FLAKY
    if "failing" in verdicts:
        return EXIT_FAILING
    return EXIT_OK


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{lineno}: not valid JSON ({exc})") from exc
    return records


def append_history(
    path: Path, digest: str, runs: list[tuple[str, dict[str, bool]]]
) -> bool:
    """Append one record unless this digest is already present. Returns True if appended."""
    if any(rec.get("digest") == digest for rec in load_history(path)):
        return False
    stats = tally(runs)
    record = {
        "digest": digest,
        "recorded": datetime.now(UTC).isoformat(timespec="seconds"),
        "runs": len(runs),
        "tests": {t: [s["runs"], s["fails"]] for t, s in stats.items()},
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return True


def stats_from_history(records: list[dict]) -> dict[str, dict]:
    runs_seen: Counter[str] = Counter()
    fails: Counter[str] = Counter()
    first_failed: dict[str, str] = {}
    for rec in records:
        for test_id, (n_runs, n_fails) in rec.get("tests", {}).items():
            runs_seen[test_id] += n_runs
            fails[test_id] += n_fails
            if n_fails:
                first_failed.setdefault(
                    test_id, rec.get("recorded", rec.get("digest", "?"))
                )
    return {
        t: {
            "runs": runs_seen[t],
            "fails": fails[t],
            "first_failed": first_failed.get(t),
        }
        for t in runs_seen
    }


def render_table(rows: list[dict], total_runs: int, top: int) -> str:
    if not rows:
        return f"No failing tests across {total_runs} run(s)."
    shown = rows[:top]
    width = min(max(len(r["test"]) for r in shown), 90)
    lines = [
        f"{'fails':>5} {'runs':>5} {'rate':>6}  {'verdict':<8} {'first failed in':<22} test",
        f"{'-' * 5} {'-' * 5} {'-' * 6}  {'-' * 8} {'-' * 22} {'-' * width}",
    ]
    for r in shown:
        first = (r["first_failed"] or "-")[-22:]
        lines.append(
            f"{r['fails']:>5} {r['runs']:>5} {r['rate']:>5.0%}  {r['verdict']:<8} {first:<22} {r['test']}"
        )
    if len(rows) > top:
        lines.append(f"... {len(rows) - top} more (raise --top)")
    flaky = sum(r["verdict"] == "flaky" for r in rows)
    failing = sum(r["verdict"] == "failing" for r in rows)
    lines.append(
        f"\n{flaky} flaky, {failing} consistently failing, over {total_runs} run(s)."
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rank tests by failures across several runs (JUnit XML or pytest -rA logs).",
        epilog="Exit codes: 0 no failures, 1 input error, 2 usage, 3 flaky found, 4 consistent failures only.",
    )
    parser.add_argument(
        "inputs", nargs="*", help="JUnit XML / pytest log files, or directories of them"
    )
    parser.add_argument(
        "--top", type=int, default=25, help="rows to print (default 25)"
    )
    parser.add_argument(
        "--min-fails",
        type=int,
        default=1,
        help="hide tests with fewer failures (default 1)",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=1,
        help="hide tests seen in fewer runs (default 1)",
    )
    parser.add_argument("--json", action="store_true", help="print the ranking as JSON")
    parser.add_argument(
        "--history",
        metavar="JSONL",
        help="append this batch to a history file (deduped)",
    )
    parser.add_argument(
        "--from-history", metavar="JSONL", help="rank the whole history file, no inputs"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.inputs) == bool(args.from_history):
        parser.error(
            "give run files/directories, or --from-history, but not both or neither"
        )
    if args.from_history and args.history:
        parser.error("--history and --from-history cannot be combined")

    try:
        if args.from_history:
            records = load_history(Path(args.from_history))
            if not records:
                raise InputError(f"{args.from_history}: no history records")
            stats = stats_from_history(records)
            total_runs = sum(rec.get("runs", 0) for rec in records)
        else:
            files = collect_inputs(args.inputs)
            if not files:
                raise InputError("no run files found in the given inputs")
            runs = [(f.name, parse_run(f)) for f in files]
            stats = tally(runs)
            total_runs = len(runs)
            if args.history:
                appended = append_history(Path(args.history), digest_of(files), runs)
                print(
                    f"history: {'appended' if appended else 'already recorded (same inputs), skipped'}"
                    f" -> {args.history}",
                    file=sys.stderr,
                )
    except InputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    rows = rank(stats, args.min_fails, args.min_runs)
    if args.json:
        print(json.dumps({"runs": total_runs, "tests": rows}, indent=2))
    else:
        print(render_table(rows, total_runs, args.top))
    return exit_code_for(rows)


if __name__ == "__main__":
    sys.exit(main())
