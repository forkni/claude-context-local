"""Mine commit-derived hard-query candidates (categories H/I) from git history.

Stage 4b of the benchmarking-harness plan. `fix:`/`feat:` commits that touch
both production Python code and a test file are a SweRank-style proxy for
"resolves a real, test-verified issue" -- the commit subject doubles as the
issue text, so no manual authoring is needed for the query itself.

Gold extraction reads git's own hunk-header function-context. Git's *default*
xfuncname pattern only matches lines starting at column 0, which misses every
indented method inside a class -- so this script overrides
`diff.python.xfuncname` per-invocation, via `-c`, to the same pattern git
ships for its builtin "python" userdiff driver. Nothing is written to
.gitattributes or .git/config; the override is scoped to each subprocess call
via a throwaway `core.attributesFile`.

Hunk-header names are fuzzy-matched by bare symbol name against a *live*
re-chunk of HEAD (MultiLanguageChunker), so gold is always "the function
identity that exists today", never a stale historical line range. Renamed,
deleted, or ambiguous (name-collision) matches are dropped rather than
guessed, and commits with an empty resulting gold set are dropped entirely.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/mine_commit_queries.py \
        [--output evaluation/commit_mined_candidates.json] [--limit N] [--verbose]
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from chunking.multi_language_chunker import MultiLanguageChunker  # noqa: E402
from evaluation.metrics import normalize_chunk_id  # noqa: E402


OUTPUT_PATH = REPO_ROOT / "evaluation" / "commit_mined_candidates.json"

# Git's own builtin "python" userdiff xfuncname pattern (matches indented
# def/class lines). Not active by default because .gitattributes doesn't map
# *.py to diff=python; applied here via `-c` for this process only.
PY_XFUNCNAME = r"^[ \t]*((class|(async[ \t]+)?def)[ \t].*)$"

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@ ?(.*)$")
FUNC_RE = re.compile(r"^\s*(?:async\s+)?def\s+(\w+)")
CLASS_RE = re.compile(r"^\s*class\s+(\w+)")

CHUNKER = MultiLanguageChunker(str(REPO_ROOT))
_file_by_name_cache: dict[str, dict[str, list[str]]] = {}


def _git(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def _git_diff(sha: str, attrs_file: str) -> str | None:
    """Full unified=0 diff for *sha* vs its first parent, python-driver-aware.

    Returns None for a root commit (no parent) instead of raising.
    """
    result = subprocess.run(
        [
            "git",
            "-c",
            f"core.attributesFile={attrs_file}",
            "-c",
            f"diff.python.xfuncname={PY_XFUNCNAME}",
            "diff",
            "--unified=0",
            "--no-color",
            f"{sha}^",
            sha,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _iter_qualifying_commits() -> list[tuple[str, str]]:
    """(sha, subject) for every non-merge commit whose subject starts fix:/feat:."""
    log = _git(["log", "--no-merges", "--pretty=format:%H%x1f%s"])
    out = []
    for line in log.splitlines():
        if not line:
            continue
        sha, _, subject = line.partition("\x1f")
        if subject.startswith("fix: ") or subject.startswith("feat: "):
            out.append((sha, subject))
    return out


def _parse_diff(diff_text: str) -> tuple[set[str], dict[str, list[str]]]:
    """Return (all touched files, {file: [hunk-header context strings]})."""
    files_touched: set[str] = set()
    hunks_by_file: dict[str, list[str]] = defaultdict(list)
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current_file = None
        elif line.startswith("+++ "):
            path = line[len("+++ ") :]
            if path == "/dev/null":
                current_file = None
            else:
                current_file = path[2:] if path.startswith("b/") else path
                files_touched.add(current_file)
        elif line.startswith("@@") and current_file:
            m = HUNK_RE.match(line)
            if m:
                hunks_by_file[current_file].append(m.group(1))
    return files_touched, hunks_by_file


def _bare_name(context: str) -> str | None:
    m = FUNC_RE.match(context) or CLASS_RE.match(context)
    return m.group(1) if m else None


def _by_name_for_file(rel_path: str) -> dict[str, list[str]]:
    """bare tail name -> normalized chunk_ids, from a live re-chunk of HEAD."""
    if rel_path not in _file_by_name_cache:
        abs_path = REPO_ROOT / rel_path
        chunks = CHUNKER.chunk_file(str(abs_path))
        by_name: dict[str, list[str]] = defaultdict(list)
        for c in chunks:
            if not c.chunk_id:
                continue
            norm = normalize_chunk_id(c.chunk_id)
            tail = norm.rsplit(":", 1)[-1].rsplit(".", 1)[-1]
            by_name[tail].append(norm)
        _file_by_name_cache[rel_path] = dict(by_name)
    return _file_by_name_cache[rel_path]


def _extract_gold(
    non_test_py_files: set[str], hunks_by_file: dict[str, list[str]]
) -> tuple[set[str], Counter]:
    """Fuzzy-match hunk-header names to live HEAD chunk_ids.

    Returns (gold chunk_ids, drop-reason counts). A name with zero matches
    was renamed or deleted since this commit; a name with 2+ matches in the
    same file is an unresolved collision -- both are dropped rather than
    guessed.
    """
    gold: set[str] = set()
    reasons: Counter = Counter()
    for file in non_test_py_files:
        by_name = _by_name_for_file(file)
        seen_names = set()
        for context in hunks_by_file.get(file, []):
            name = _bare_name(context)
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            matches = by_name.get(name, [])
            if len(matches) == 1:
                gold.add(matches[0])
            elif not matches:
                reasons["renamed_or_deleted"] += 1
            else:
                reasons["ambiguous_name"] += 1
    return gold, reasons


# Above this, a commit's gold set stops being a "multi-evidence" query and
# becomes "half the codebase changed" (whole-subsystem deletions/renames) --
# unanswerable by any ranked search and not a useful benchmark target.
# Measured full-history distribution: a clean gap between 19 and 71 functions.
MAX_I_FUNCS = 25


def _classify(gold: set[str]) -> str | None:
    """H: <=2 functions, 1 file. I: 3-25 functions, >=2 files. Else: drop."""
    files = {g.split(":", 1)[0] for g in gold}
    if len(gold) <= 2 and len(files) == 1:
        return "H"
    if 3 <= len(gold) <= MAX_I_FUNCS and len(files) >= 2:
        return "I"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    parser.add_argument(
        "--limit", type=int, default=None, help="Cap qualifying commits (debug)"
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    commits = _iter_qualifying_commits()
    print(f"{len(commits)} commits with fix:/feat: subject (full history, no merges)")

    with tempfile.NamedTemporaryFile("w", suffix=".attributes", delete=False) as attr_f:
        attr_f.write("*.py diff=python\n")
        attrs_file = attr_f.name

    try:
        touches_both = []
        for sha, subject in commits:
            diff_text = _git_diff(sha, attrs_file)
            if diff_text is None:
                continue
            files_touched, hunks_by_file = _parse_diff(diff_text)
            non_test_py = {
                f
                for f in files_touched
                if f.endswith(".py") and not f.startswith("tests/")
            }
            has_test = any(f.startswith("tests/") for f in files_touched)
            if non_test_py and has_test:
                touches_both.append((sha, subject, non_test_py, hunks_by_file))

        print(
            f"{len(touches_both)} commits touch >=1 non-test .py file "
            "and >=1 tests/** file"
        )

        if args.limit:
            touches_both = touches_both[: args.limit]

        drop_reasons: Counter = Counter()
        candidates = []
        h_count = 0
        i_count = 0
        for sha, subject, non_test_py, hunks_by_file in touches_both:
            gold, reasons = _extract_gold(non_test_py, hunks_by_file)
            drop_reasons.update(reasons)
            if not gold:
                drop_reasons["empty_gold"] += 1
                continue
            category = _classify(gold)
            if category is None:
                if len(gold) > MAX_I_FUNCS:
                    drop_reasons["gold_set_too_large"] += 1
                else:
                    drop_reasons["ambiguous_h_i_middle"] += 1
                continue

            prefix = subject.split(":", 1)[0] + ": "
            query_text = subject[len(prefix) :].strip()

            if category == "H":
                h_count += 1
                cid = f"H{h_count:03d}"
            else:
                i_count += 1
                cid = f"I{i_count:03d}"

            candidates.append(
                {
                    "id": cid,
                    "query": query_text,
                    "category": category,
                    "intended": sorted(gold),
                    "notes": (
                        f"commit-mined from {sha[:8]} ({subject!r}); needs "
                        "paraphrase before grading -- query text is the "
                        "literal commit subject and may leak function names"
                    ),
                }
            )

        if args.verbose:
            for reason, count in drop_reasons.most_common():
                print(f"  dropped {count:4d}  {reason}")

        print(
            f"Emitting {len(candidates)} candidates (H={h_count}, I={i_count}) "
            f"after {sum(drop_reasons.values())} drops"
        )

        meta = {
            "purpose": (
                "Commit-mined candidate hard queries for categories H "
                "(bug-fix localization) and I (broader-context / "
                "multi-evidence), Stage 4 of the benchmarking-harness plan. "
                "Graded via scripts/benchmark/grade_candidate_queries.py "
                "--candidates before promotion into golden_dataset_expanded.json."
            ),
            "authored_date": "2026-07-31",
            "source": (
                "git log --no-merges, subjects starting fix:/feat:, full "
                "history, filtered to commits touching >=1 non-test .py file "
                "and >=1 tests/** file. Gold = hunk-header function/class "
                "names fuzzy-matched by bare symbol name against a live "
                "re-chunk of HEAD; renamed/deleted/ambiguous-name matches "
                "are dropped rather than guessed."
            ),
            "classification": (
                "H: <=2 matched functions, 1 file. I: >=3 matched functions, "
                ">=2 files. Commits landing in neither bucket are dropped "
                "(ambiguous middle)."
            ),
            "candidate_count": len(candidates),
            "category_counts": {"H": h_count, "I": i_count},
            "queries_need_paraphrase": True,
        }

        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(
                {"_meta": meta, "candidates": candidates}, indent=2, ensure_ascii=False
            )
            + "\n",
            encoding="utf-8",
            newline="\r\n",
        )
        print(f"Wrote {output_path}")
    finally:
        Path(attrs_file).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
