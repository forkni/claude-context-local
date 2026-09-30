# Code Style Instructions

`CLAUDE.md` and `MEMORY.md` are gitignored and maintainer-local: they are not in the repository,
so do not assume you can read them. The rules below are the project guidance available to you.

## Repository Policy

- [P1] `scripts/git/`, `CLAUDE.md`, `MEMORY.md`, and the other entries under "Local-only content"
  in `.gitignore` are intentionally absent from the repository. A doc that references them and
  labels them "maintainer-local" is correct — do not remove or rewrite those references as stale.
  If a tracked doc references one of them *without* that label, add the label instead of
  deleting the guidance.
- [P2] Open documentation PRs against `development`, not `main`. `main` lags `development` and
  PRs based on it read stale dependency pins and stale config defaults.
- [P3] Do not copy exact dependency versions or lockfile resolutions into prose. Point to
  `pyproject.toml` as the source of truth; hard-coded pins drift on every dependency audit.

## Additional Rules

- [R1] Use semantic MCP search tools before reading files
- [R2] Follow existing patterns in the codebase
- [R3] Run tests before submitting PRs
- [R4] Ensure all lint checks pass before committing
- [R5] Use type hints for all public functions
