#!/usr/bin/env python3
"""
CRAP / duplication gate - run unclebob's crapper and dryer on Windows and gate on the result.

crapper (CRAP = CC^2 * (1 - coverage)^3 + CC) and dryer (structural duplicate finder, Jaccard
similarity) are 0BSD tools that parse Python with tree-sitter. Their `./crapper` and `./dryer`
launchers are POSIX shell scripts that look for `.venv/bin/python` and `python3`, so they do not
start on Windows, and crapper falls back to `unittest` when it cannot find pytest settings. This
wrapper calls both as modules (`python -m crapper`, `python -m dryer`), runs coverage with the
interpreter that runs this script, and keeps every tool artifact in a temporary directory.

Stdlib-only. Same CLI shape as scan_test_smells.py: `--baseline` ratchet, `--update-baseline`,
exit 0 ok, 1 gate failed, 2 usage / tool missing / unreadable baseline.

    python crap_dry_gate.py dup  [PATH ...] [--threshold 0.82] [--json]
                                 [--baseline FILE [--update-baseline] | --base REF]
    python crap_dry_gate.py crap [--base REF] [--max-crap 30] [--lcov FILE] [--json]
                                 [-- PYTEST_ARGS ...]

dup   Lists candidate duplicate pairs under PATH (default: the repo). With --baseline it fails
      only when the pair count goes UP (Core Rule 11 ratchet; the baseline is `{"count": N}`).
      With --base REF it fails when a pair touches a line changed since REF. dryer exits 0
      even when it finds pairs, so this wrapper is the gate.
crap  Scores the functions whose lines changed since REF (default HEAD, so uncommitted and
      untracked files) and fails when one is above --max-crap. Files that coverage never saw
      score 0% coverage. Coverage comes from `coverage run -m pytest` (arguments after `--`), or
      from an existing lcov file with --lcov.

Tools: install both into one interpreter (pin the SHAs) and point UB_TOOLS_PYTHON at it, or
install them into the interpreter that runs this script:

    uv venv ~/.cache/ub-tools
    uv pip install --python ~/.cache/ub-tools/Scripts/python.exe \
        git+https://github.com/unclebob/crapper@6fd92c4c9bcc56efb64a2f8743d5a2993bcfd42d \
        git+https://github.com/unclebob/dryer@66ff6d21a42c04afcad89c78a80066176d1294b0

Nothing is installed or downloaded by this script. `crap` needs `coverage` and `pytest` in the
interpreter that runs it.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


TOOL_ENV = "UB_TOOLS_PYTHON"
INSTALL_HINT = (
    "install crapper and dryer from github.com/unclebob (pin the SHAs in this file's docstring) "
    f"into one interpreter and set {TOOL_ENV} to its python, or into the interpreter running this script"
)

_SKIP_DIRS = {
    "tests",
    "test",
    "testdata",
    ".venv",
    "venv",
    "node_modules",
    "build",
    "dist",
    "__pycache__",
    ".git",
    ".metrics",
}
_HUNK = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_CRAP_ENTRY = re.compile(
    r'\{:name "(?P<name>(?:[^"\\]|\\.)*)", :namespace "(?P<ns>(?:[^"\\]|\\.)*)", '
    r":complexity (?P<cc>\d+), :coverage (?P<cov>nil|[\d.]+), :crap (?P<crap>nil|[\d.]+)\}"
)
_DRY_LOC = re.compile(r':file "((?:[^"\\]|\\.)*)", :start-line (\d+), :end-line (\d+)')


class GateError(Exception):
    """A usage or environment problem (exit code 2)."""


# --- git ---------------------------------------------------------------------------------------


def git(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "core.quotepath=off", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise GateError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def repo_root(cwd: Path | None = None) -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise GateError("not inside a git repository")
    return Path(proc.stdout.strip())


def parse_diff_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
    """Map each changed file to its new-side line ranges from `git diff -U0` output."""
    out: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            name = line[4:].split("\t")[0]
            current = name[2:] if name.startswith("b/") else None
            if current:
                out.setdefault(current, [])
        elif line.startswith("@@") and current:
            match = _HUNK.match(line)
            if match:
                start = max(int(match.group(1)), 1)
                count = 1 if match.group(2) is None else int(match.group(2))
                out[current].append((start, start + max(count, 1) - 1))
    return out


def is_source_path(rel: str) -> bool:
    path = Path(rel)
    if path.suffix != ".py" or any(part in _SKIP_DIRS for part in path.parts[:-1]):
        return False
    name = path.name
    return not (
        name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"
    )


def changed_python(root: Path, base: str) -> dict[str, list[tuple[int, int]] | None]:
    """Changed non-test Python files since `base`. None as a value means the whole file (untracked)."""
    try:
        anchor = git(root, "merge-base", base, "HEAD").strip() or base
    except GateError:
        anchor = base
    diff = git(
        root,
        "diff",
        "-U0",
        "--no-color",
        "--no-ext-diff",
        "--diff-filter=AMR",
        anchor,
        "--",
        "*.py",
    )
    found: dict[str, list[tuple[int, int]] | None] = dict(parse_diff_ranges(diff))
    for rel in git(
        root, "ls-files", "--others", "--exclude-standard", "--", "*.py"
    ).splitlines():
        found[rel] = None
    return {
        rel: ranges
        for rel, ranges in found.items()
        if is_source_path(rel) and (root / rel).is_file()
    }


def overlaps(ranges: list[tuple[int, int]] | None, start: int, end: int) -> bool:
    return ranges is None or any(a <= end and start <= b for a, b in ranges)


# --- parsing tool output -----------------------------------------------------------------------


def function_ranges(path: Path) -> dict[str, list[tuple[int, int]]]:
    """Function name -> [(first line, last line)] for every def in the file (methods included)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return {}
    out: dict[str, list[tuple[int, int]]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(node.name, []).append(
                (node.lineno, node.end_lineno or node.lineno)
            )
    return out


def parse_crap_edn(text: str) -> list[dict]:
    entries = []
    for m in _CRAP_ENTRY.finditer(text):
        entries.append(
            {
                "name": m.group("name"),
                "namespace": m.group("ns"),
                "complexity": int(m.group("cc")),
                "coverage": None if m.group("cov") == "nil" else float(m.group("cov")),
                "crap": None if m.group("crap") == "nil" else float(m.group("crap")),
            }
        )
    return entries


def parse_dry_edn(text: str) -> list[dict]:
    """Candidate pairs: {score, left: (file, start, end), right: (file, start, end)}."""
    pairs = []
    for chunk in text.split(":score ")[1:]:
        score = re.match(r"[\d.]+", chunk)
        locs = _DRY_LOC.findall(chunk)
        if score and len(locs) >= 2:
            left, right = ((f, int(s), int(e)) for f, s, e in locs[:2])
            pairs.append({"score": float(score.group(0)), "left": left, "right": right})
    return pairs


def rel_path(root: Path, name: str) -> str:
    path = Path(name)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


# --- running the tools -------------------------------------------------------------------------


def tool_python(module: str) -> str:
    """The interpreter that can import `module`: $UB_TOOLS_PYTHON, else the current one."""
    py = os.environ.get(TOOL_ENV) or sys.executable
    try:
        probe = subprocess.run(
            [py, "-c", f"import {module}"], capture_output=True, text=True
        )
    except OSError as exc:
        raise GateError(f"cannot start {py}: {exc}. {INSTALL_HINT}") from exc
    if probe.returncode != 0:
        raise GateError(f"{module} is not importable by {py}: {INSTALL_HINT}")
    return py


def run_module(
    py: str, module: str, args: list[str], cwd: Path
) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [py, "-m", module, *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def compare_baseline(
    count: int, baseline_path: Path, update: bool, threshold: float
) -> tuple[int, dict]:
    status: dict = {"path": str(baseline_path), "action": "compare"}
    if update or not baseline_path.exists():
        payload = {"count": count, "threshold": threshold}
        baseline_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        status.update(action="written", count=count)
        return 0, status
    try:
        stored_data = json.loads(baseline_path.read_text(encoding="utf-8"))
        base = int(stored_data["count"])
        stored = stored_data.get("threshold")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        status.update(action="error", error=str(exc))
        return 2, status
    if stored is not None and stored != threshold:
        status.update(
            action="error",
            error=f"baseline was written at --threshold {stored}, this run uses "
            f"{threshold}; the counts are not comparable (rerun with --update-baseline)",
        )
        return 2, status
    status.update(baseline=base, count=count)
    return (1 if count > base else 0), status


# --- subcommands -------------------------------------------------------------------------------


def cmd_dup(args: argparse.Namespace) -> int:
    root = repo_root()
    py = tool_python("dryer")
    targets = [str((Path.cwd() / p).resolve()) for p in args.paths] or [str(root)]
    with tempfile.TemporaryDirectory() as tmp:
        proc = run_module(
            py,
            "dryer",
            [
                "--root",
                tmp,
                "--edn",
                "--threshold",
                str(args.threshold),
                *[a for t in targets for a in ("-s", t)],
            ],
            root,
        )
        if proc.returncode != 0:
            raise GateError(
                f"dryer exited {proc.returncode}: {proc.stderr.strip() or proc.stdout.strip()}"
            )
        pairs = parse_dry_edn(proc.stdout)
    for pair in pairs:
        for side in ("left", "right"):
            f, s, e = pair[side]
            pair[side] = (rel_path(root, f), s, e)
    if args.base:
        changed = changed_python(root, args.base)
        pairs = [
            p
            for p in pairs
            if any(
                p[side][0] in changed
                and overlaps(changed[p[side][0]], p[side][1], p[side][2])
                for side in ("left", "right")
            )
        ]
    code, status = 0, None
    if args.baseline:
        code, status = compare_baseline(
            len(pairs), args.baseline, args.update_baseline, args.threshold
        )
    elif args.base and pairs:
        code = 1
    report = {
        "command": "dup",
        "threshold": args.threshold,
        "count": len(pairs),
        "pairs": pairs,
        "baseline": status,
        "exit_code": code,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return code
    print(f"dup: {len(pairs)} candidate pair(s) at similarity >= {args.threshold}")
    for p in pairs:
        (lf, ls, le), (rf, rs, re_) = p["left"], p["right"]
        print(f"  {p['score']:.2f}  {lf}:{ls}-{le}  <->  {rf}:{rs}-{re_}")
    if status and status["action"] == "error":
        print(
            f"error: could not read baseline {status['path']}: {status['error']}",
            file=sys.stderr,
        )
    elif status and status["action"] == "written":
        print(f"baseline written: {status['path']} (count {status['count']})")
    elif status and code:
        print(
            f"FAIL: pair count rose from {status['baseline']} to {status['count']}. Remove the new duplicate, "
            "or rerun with --update-baseline if the increase was reviewed."
        )
    elif code:
        print("FAIL: a duplicate pair touches a line changed since " + args.base)
    return code


def source_roots(files: list[str]) -> str:
    """Top-level names for coverage --source (a top-level module is named without .py)."""
    names = set()
    for rel in files:
        parts = Path(rel).parts
        names.add(Path(rel).stem if len(parts) == 1 else parts[0])
    return ",".join(sorted(names))


def build_lcov(
    root: Path, tmp: Path, files: list[str], pytest_args: list[str], dest: Path
) -> None:
    data = tmp / ".coverage"
    cmd = [
        sys.executable,
        "-m",
        "coverage",
        "run",
        f"--data-file={data}",
        f"--source={source_roots(files)}",
        "-m",
        "pytest",
        *pytest_args,
    ]
    proc = subprocess.run(cmd, cwd=root)
    if not data.exists():
        raise GateError(
            "coverage recorded nothing; `coverage` and `pytest` must be installed in "
            f"{sys.executable}"
        )
    if proc.returncode != 0:
        raise GateError(
            f"pytest exited {proc.returncode}; fix the suite first, because partial coverage "
            "makes the CRAP scores wrong"
        )
    lcov = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "lcov",
            f"--data-file={data}",
            "-o",
            str(dest),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if lcov.returncode != 0:
        raise GateError(f"coverage lcov failed: {lcov.stderr.strip()}")


def cmd_crap(args: argparse.Namespace) -> int:
    root = repo_root()
    changed = changed_python(root, args.base)
    if not changed:
        print(f"crap: no changed Python source files since {args.base}")
        return 0
    py = tool_python("crapper")
    pytest_args = list(args.pytest_args)
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    scored: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        dest = tmp / "target" / "coverage" / "python" / "lcov.info"
        dest.parent.mkdir(parents=True)
        if args.lcov:
            shutil.copyfile(args.lcov, dest)
        else:
            build_lcov(root, tmp, list(changed), pytest_args, dest)
        edn = tmp / ".metrics" / "crap.edn"
        for rel, ranges in sorted(changed.items()):
            edn.unlink(missing_ok=True)
            proc = run_module(
                py,
                "crapper",
                ["--root", tmp_name, "--use-existing-coverage", str(root / rel)],
                root,
            )
            if proc.returncode != 0:
                raise GateError(
                    f"crapper exited {proc.returncode} on {rel}: {proc.stderr.strip() or proc.stdout.strip()}"
                )
            spans = function_ranges(root / rel)
            for entry in (
                parse_crap_edn(edn.read_text(encoding="utf-8")) if edn.exists() else []
            ):
                where = [
                    s for s in spans.get(entry["name"], []) if overlaps(ranges, *s)
                ]
                if where:
                    scored.append({**entry, "file": rel, "line": where[0][0]})
    failing = [e for e in scored if e["crap"] is not None and e["crap"] > args.max_crap]
    unscored = [e for e in scored if e["crap"] is None]
    code = 1 if failing or unscored else 0
    if args.json:
        print(
            json.dumps(
                {
                    "command": "crap",
                    "max_crap": args.max_crap,
                    "scored": scored,
                    "failing": failing,
                    "unscored": unscored,
                    "exit_code": code,
                },
                indent=2,
            )
        )
        return code
    flagged = {id(e) for e in failing} | {id(e) for e in unscored}
    print(
        f"crap: {len(scored)} changed function(s) scored in {len(changed)} file(s), max-crap {args.max_crap:g}"
    )
    for e in sorted(scored, key=lambda x: -(x["crap"] or 0)):
        cov = "n/a" if e["coverage"] is None else f"{e['coverage']:.1f}%"
        crap = "n/a" if e["crap"] is None else f"{e['crap']:.1f}"
        flag = "FAIL" if id(e) in flagged else "ok  "
        print(
            f"  {flag} {e['file']}:{e['line']} {e['name']}  CC={e['complexity']} cov={cov} CRAP={crap}"
        )
    if failing:
        print(
            "FAIL: add tests for the failing functions or split them; do not raise --max-crap to pass."
        )
    if unscored:
        print(
            "FAIL: crapper gave no score (CRAP n/a) for the functions marked above; check that the "
            "coverage input lists their file."
        )
    return code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    dup = sub.add_parser("dup", help="structural duplicate pairs (dryer)")
    dup.add_argument(
        "paths", nargs="*", help="Files or directories to compare (default: the repo)"
    )
    dup.add_argument(
        "--threshold",
        type=float,
        default=0.82,
        help="Minimum similarity (dryer default 0.82)",
    )
    dup.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    scope = dup.add_mutually_exclusive_group()
    scope.add_argument(
        "--baseline",
        type=Path,
        help='Ratchet file ({"count": N}); fail only when the count rises',
    )
    scope.add_argument(
        "--base",
        metavar="REF",
        help="Fail when a pair touches a line changed since REF",
    )
    dup.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write the current count to --baseline",
    )
    crap = sub.add_parser("crap", help="CRAP score of changed functions (crapper)")
    crap.add_argument(
        "--base",
        default="HEAD",
        metavar="REF",
        help="Compare against REF (default HEAD)",
    )
    crap.add_argument(
        "--max-crap",
        type=float,
        default=30.0,
        help="Fail above this score (default 30; use 6 for agent-authored code)",
    )
    crap.add_argument(
        "--lcov",
        type=Path,
        help="Reuse an lcov file instead of running pytest under coverage",
    )
    crap.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    crap.add_argument(
        "pytest_args", nargs=argparse.REMAINDER, help="After `--`: arguments for pytest"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "dup" and args.update_baseline and not args.baseline:
        print("error: --update-baseline needs --baseline", file=sys.stderr)
        return 2
    try:
        return cmd_dup(args) if args.command == "dup" else cmd_crap(args)
    except GateError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
