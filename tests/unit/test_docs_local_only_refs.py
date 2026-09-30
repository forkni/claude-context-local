"""Guard: tracked docs must label gitignored ``scripts/git/`` as maintainer-local.

``scripts/git/`` is gitignored ("Local-only content"), so a fresh clone does not
have it. Tracked Markdown that references it without saying so reads as stale
documentation and keeps triggering docs-drift bot PRs that delete accurate
guidance. Every tracked doc that mentions the path must carry the marker phrase.
"""

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ONLY_PATH = "scripts/git/"
MARKER = "maintainer-local"
# Historical records: they describe what was true when written, not current setup.
HISTORICAL = ("docs/adr/", "CHANGELOG.md", "docs/VERSION_HISTORY.md")


def _tracked_markdown() -> list[str]:
    if shutil.which("git") is None:
        pytest.skip("git not available")
    result = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"not a git checkout: {result.stderr.strip()}")
    return result.stdout.splitlines()


def test_docs_referencing_scripts_git_are_labelled_maintainer_local():
    offenders = []
    for rel in _tracked_markdown():
        if rel.startswith(HISTORICAL[0]) or rel in HISTORICAL[1:]:
            continue
        path = REPO_ROOT / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if LOCAL_ONLY_PATH in text and MARKER not in text.lower():
            offenders.append(rel)

    assert not offenders, (
        f"{LOCAL_ONLY_PATH} is gitignored but these tracked docs reference it "
        f"without the '{MARKER}' label: {offenders}"
    )
