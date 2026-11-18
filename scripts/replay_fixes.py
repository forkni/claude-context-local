#!/usr/bin/env python3
"""
Replay Fixes - do the tests catch the bugs that really happened?

Companion to AUDIT.md ("Replay past fixes"). Mutation testing plants synthetic bugs; this plants
the real ones. For each bug-fix commit F with parent P that changed both tests and source:

    1. check out F in a throwaway git worktree and run the fix's tests: this is the *control* and
       must be green (a red control is an environment or flake problem, not evidence);
    2. put the non-test files back to their state in P (the bug returns), keep the tests from F,
       and run the same tests again: a suite that guards the fix goes red.

recall = fixes whose tests went red / fixes replayed. A fix whose tests stay green with the bug
back in place is a MISS: the test added with the fix does not catch the bug it was written for.

    python replay_fixes.py --last 10
    python replay_fixes.py --fix-commit 21db852 --fix-commit 2e4de70 --json
    python replay_fixes.py --last 5 --test-command "python -m pytest -q -x {tests}"

Only commits that change at least one test module AND at least one source file (suffix in
--source-suffix, default .py) are replayed; the rest are reported as SKIP. A test file is a path
under a `tests`/`test` directory, named `test_*.py` / `*_test.py`, or `conftest.py`; only the
`test_*.py` / `*_test.py` modules become pytest targets (golden files and conftest stay as in the
fix commit, so a fix that changes only those is skipped).

The working tree is never touched: everything runs in `git worktree add --detach` copies under the
system temp directory, removed afterwards. The project's own package must be importable from the
worktree (PYTHONPATH is set to the worktree root and its `src` directory, which wins over a `.pth`-style editable install pointing at
your main checkout; a finder-based editable install, such as meson-python or scikit-build-core
can still import the main checkout, and then every fix reads MISSED: use a plain install).

Exit codes: 0 every replayed fix was caught, 1 error (not a repo, unknown commit), 2 usage,
3 at least one fix was missed, 4 nothing could be replayed.

Stdlib-only. The test command runs code from your own repository history, like a normal test run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path


__version__ = "1.0.0"

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_MISSED, EXIT_NOTHING = 0, 1, 2, 3, 4

CAUGHT, MISSED, SKIP, CONTROL_RED, ERROR = (
    "CAUGHT",
    "MISSED",
    "SKIP",
    "CONTROL-RED",
    "ERROR",
)
# pytest exit codes: 0 passed, 1 tests failed, 2 interrupted (collection error), 5 nothing collected.
PYTEST_FAILED = 1


class ReplayError(Exception):
    """A fatal problem: not a git repository, unknown commit, git missing."""


@dataclass
class Result:
    sha: str
    subject: str
    verdict: str
    detail: str = ""
    tests: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        proc = subprocess.run(
            # --literal-pathspecs: a file name with [ ? * is a name, not a glob, when it is restored
            ["git", "--literal-pathspecs", "-C", str(repo), *args],
            check=False, capture_output=True, text=True, encoding="utf-8",
        )  # fmt: skip
    except FileNotFoundError as exc:
        raise ReplayError("git is not on PATH") from exc
    if check and proc.returncode != 0:
        raise ReplayError(
            f"git {' '.join(args)}: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def is_test_path(path: str, extra_prefixes: tuple[str, ...] = ()) -> bool:
    parts = path.replace("\\", "/").split("/")
    name = parts[-1]
    if any(path.startswith(p.replace("\\", "/")) for p in extra_prefixes):
        return True
    return (
        "tests" in parts[:-1]
        or "test" in parts[:-1]
        or name == "conftest.py"
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
    )


def is_runnable_test(path: str) -> bool:
    """A test module pytest can be pointed at (not a golden file or conftest under tests/)."""
    name = path.replace("\\", "/").rsplit("/", 1)[-1]
    return (name.startswith("test_") and name.endswith(".py")) or name.endswith(
        "_test.py"
    )


def changed_files(repo: Path, parent: str, sha: str) -> list[tuple[str, str]]:
    """[(status, path)] with status A/M/D; renames are split into a delete and an add."""
    # -z: NUL-separated and never C-quoted, so a non-ASCII name arrives as itself, not as "caf\303\251.py"
    out = git(repo, "diff", "--name-status", "--no-renames", "-z", parent, sha).stdout
    tokens = out.split("\0")
    return [
        (tokens[i][0], tokens[i + 1])
        for i in range(0, len(tokens) - 1, 2)
        if tokens[i] and tokens[i + 1]
    ]


def resolve_commits(repo: Path, args: argparse.Namespace) -> list[str]:
    if args.fix_commit:
        return [
            git(repo, "rev-parse", "--verify", f"{c}^{{commit}}").stdout.strip()
            for c in args.fix_commit
        ]
    try:
        pattern = re.compile(args.grep)
    except re.error as exc:
        raise ReplayError(f"--grep is not a valid regular expression: {exc}") from exc
    # Match the SUBJECT only: `git log --grep` tests every line of the message, so a feature commit
    # whose body says "fixes #12" would be picked up.
    out = git(
        repo, "log", "--no-merges", "-n", str(args.scan), "--format=%H%x1f%s"
    ).stdout
    picked = []
    for line in out.splitlines():
        sha, _, subject = line.partition("\x1f")
        if sha and pattern.search(subject):
            picked.append(sha)
            if len(picked) == args.last:
                break
    return picked


def run_tests(cmd: list[str], cwd: Path, timeout: int) -> tuple[int | None, str]:
    env = dict(os.environ)
    # No bytecode: the control run and the bug-state run share one worktree, and a same-size edit
    # (`a - b` -> `a + b`) made inside the same second keeps its old .pyc valid, so the bug-state
    # run would import the FIXED code and report a false MISSED.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    roots = [str(cwd), str(cwd / "src")]
    env["PYTHONPATH"] = os.pathsep.join(
        roots + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else [])
    )
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, check=False, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )  # fmt: skip
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    except OSError as exc:
        return None, f"could not start the test command: {exc}"
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-1:] or [""]
    return proc.returncode, tail[0]


def build_command(
    template: str, tests: list[str], *, windows: bool | None = None
) -> list[str]:
    """Split the test command. POSIX rules eat backslashes, so a Windows path would be mangled."""
    if windows is None:
        windows = os.name == "nt"
    try:
        if windows:
            # posix=False keeps the quotes and the backslashes; drop one pair of matching outer quotes.
            words = [
                w[1:-1] if len(w) >= 2 and w[0] == w[-1] and w[0] in "\"'" else w
                for w in shlex.split(template, posix=False)
            ]
        else:
            words = shlex.split(template)
    except ValueError as exc:
        raise ReplayError(f"--test-command has unbalanced quotes: {exc}") from exc
    if "{tests}" in words:
        i = words.index("{tests}")
        return words[:i] + tests + words[i + 1 :]
    return words + tests


def replay_one(repo: Path, sha: str, args: argparse.Namespace) -> Result:
    subject = git(repo, "show", "-s", "--format=%s", sha).stdout.strip()
    res = Result(sha=sha[:7], subject=subject, verdict=SKIP)
    parents = git(repo, "rev-list", "--parents", "-n", "1", sha).stdout.split()[1:]
    if len(parents) != 1:
        res.detail = "merge or root commit"
        return res
    parent = parents[0]
    prefixes = tuple(args.test_prefix)
    suffixes = tuple(args.source_suffix)

    files = changed_files(repo, parent, sha)
    changed_tests = [p for s, p in files if s in "AM" and is_test_path(p, prefixes)]
    tests = [p for p in changed_tests if is_runnable_test(p)]
    sources = [
        (s, p)
        for s, p in files
        if not is_test_path(p, prefixes) and p.endswith(suffixes)
    ]
    res.tests, res.sources = tests, [p for _, p in sources]
    if not changed_tests:
        res.detail = "no test file added or changed"
        return res
    if not tests:
        res.detail = (
            "only fixtures, golden files or conftest changed: no test module to run"
        )
        return res
    if not sources:
        res.detail = f"no source file with suffix {'/'.join(suffixes)} changed"
        return res

    cmd = build_command(args.test_command, tests)
    tmp = Path(tempfile.mkdtemp(prefix="replay-fix-"))
    work = tmp / "wt"
    try:
        git(repo, "worktree", "add", "--detach", str(work), sha)
        code, last = run_tests(cmd, work, args.timeout)
        if code != 0:
            res.verdict = CONTROL_RED if code is not None else ERROR
            res.detail = f"control run on the fix commit: exit {code} ({last})"
            return res
        for status, path in sources:
            if status == "A":  # the fix added this file: the bug state has no such file
                (work / path).unlink(missing_ok=True)
            else:
                git(work, "checkout", parent, "--", path)
        code, last = run_tests(cmd, work, args.timeout)
        if code is None:
            res.verdict, res.detail = ERROR, last
        elif code == PYTEST_FAILED:
            res.verdict, res.detail = CAUGHT, f"red with the bug back: {last}"
        elif code == 0:
            res.verdict = MISSED
            res.detail = (
                "tests stay green with the fix reverted: they do not guard this bug"
            )
        else:
            res.verdict = ERROR
            res.detail = (
                f"exit {code}: a collection or usage error, not a test failure: {last}. "
                "Often the fix added the function the test imports; read it by hand, it is not counted"
            )
        return res
    finally:
        git(repo, "worktree", "remove", "--force", str(work), check=False)
        shutil.rmtree(tmp, ignore_errors=True)
        git(repo, "worktree", "prune", check=False)


def summarise(results: list[Result]) -> dict:
    caught = sum(r.verdict == CAUGHT for r in results)
    missed = sum(r.verdict == MISSED for r in results)
    replayed = caught + missed
    return {
        "replayed": replayed,
        "caught": caught,
        "missed": missed,
        "recall": (caught / replayed) if replayed else None,
        "skipped": sum(r.verdict == SKIP for r in results),
        "control_red": sum(r.verdict == CONTROL_RED for r in results),
        "errors": sum(r.verdict == ERROR for r in results),
    }


def exit_code_for(summary: dict) -> int:
    if summary["replayed"] == 0:
        return EXIT_NOTHING
    return EXIT_MISSED if summary["missed"] else EXIT_OK


def render(results: list[Result], summary: dict) -> str:
    lines = [
        f"{'commit':<8} {'verdict':<12} subject / detail",
        f"{'-' * 8} {'-' * 12} {'-' * 60}",
    ]
    for r in results:
        lines.append(f"{r.sha:<8} {r.verdict:<12} {r.subject[:70]}")
        if r.detail:
            lines.append(f"{'':<21}{r.detail[:110]}")
    if summary["recall"] is None:
        lines.append("\nrecall: n/a, no fix could be replayed.")
    else:
        lines.append(
            f"\nrecall: {summary['caught']}/{summary['replayed']} = {summary['recall']:.0%}"
            f" ({summary['skipped']} skipped, {summary['control_red']} control-red, {summary['errors']} errors)"
        )
    if summary["missed"]:
        lines.append(
            "Each MISSED fix names a bug the suite would let back in: strengthen its test first."
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Revert each past fix's source, keep its tests, and check that the tests go red.",
        epilog="Exit codes: 0 all caught, 1 error, 2 usage, 3 a fix was missed, 4 nothing replayable.",
    )
    parser.add_argument(
        "--repo", default=".", help="repository root (default: current directory)"
    )
    parser.add_argument(
        "--fix-commit",
        action="append",
        default=[],
        metavar="SHA",
        help="a fix commit; repeatable",
    )
    parser.add_argument(
        "--last",
        type=int,
        metavar="N",
        help="the N most recent commits whose message matches --grep",
    )
    parser.add_argument(
        "--grep",
        default="^fix",
        help="Python regex matched against the commit SUBJECT, with --last (default: ^fix)",
    )
    parser.add_argument(
        "--scan",
        type=int,
        default=5000,
        metavar="N",
        help="with --last: look back this many non-merge commits (default 5000)",
    )
    parser.add_argument(
        "--test-command",
        default=f"{shlex.quote(Path(sys.executable).as_posix())} -m pytest -q -x -p no:cacheprovider",
        help="test command; the fix's test files are appended, or put at {tests}",
    )
    parser.add_argument(
        "--source-suffix",
        action="append",
        default=None,
        metavar="EXT",
        help="suffix that counts as source (default .py). Giving it REPLACES .py, so "
        "repeat --source-suffix .py to keep Python; repeatable",
    )
    parser.add_argument(
        "--test-prefix",
        action="append",
        default=[],
        metavar="PATH",
        help="extra path prefix that counts as test code, a plain string prefix: end a "
        "directory with / (checks/ not checks); backslashes are accepted; repeatable",
    )
    parser.add_argument(
        "--timeout", type=int, default=600, help="seconds per test run (default 600)"
    )
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.fix_commit) == (args.last is not None):
        parser.error("give --fix-commit (one or more) or --last N, not both or neither")
    if args.last is not None and args.last < 1:
        parser.error("--last must be at least 1")
    if args.scan < 1:
        parser.error("--scan must be at least 1")
    args.source_suffix = tuple(args.source_suffix or [".py"])

    repo = Path(args.repo).resolve()
    try:
        git(repo, "rev-parse", "--git-dir")
        commits = resolve_commits(repo, args)
        if not commits:
            raise ReplayError(f"no commits match --grep {args.grep!r}")
        results = []
        for sha in commits:
            try:
                results.append(replay_one(repo, sha, args))
            except (
                ReplayError
            ) as exc:  # one bad commit must not lose the others' verdicts
                results.append(Result(sha[:7], "", ERROR, f"git failed: {exc}"))
    except ReplayError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    summary = summarise(results)
    if args.json:
        print(
            json.dumps(
                {"summary": summary, "results": [asdict(r) for r in results]}, indent=2
            )
        )
    else:
        print(render(results, summary))
    return exit_code_for(summary)


if __name__ == "__main__":
    sys.exit(main())
