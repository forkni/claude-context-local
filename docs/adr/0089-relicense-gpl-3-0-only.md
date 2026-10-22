# Relicense the project as GPL-3.0-only

Status: accepted
Date: 2026-10-22

## Context

This project is a fork of [FarhanAliRaza/claude-context-local](https://github.com/FarhanAliRaza/claude-context-local),
taken at `2299871b` (2025-09-08). At that commit, and still today, upstream declares its license
as GNU GPL v3.0: in the README "License" section and in the GPLv3 classifier in
`pyproject.toml`. Upstream never shipped a `LICENSE` file, so the GitHub API reports
`license: null` for it, but the README declaration is a license grant all the same, and it has
no "or later" clause.

The fork later removed the GPL text from its README (`606a6ac5`, 2025-11-27) and added an
Apache-2.0 `LICENSE` with "Copyright 2025 forkni" (`4ee908f2`, 2025-11-28). Releases v0.15.0
through v0.26.0 went out under that label. A GPL-3.0 licensee may not relicense the upstream
author's code under more permissive terms, so the Apache-2.0 label was never valid for the parts
derived from upstream.

How much is derived: `git blame` over the non-test Python finds about 789 of ~83k lines still
attributed to upstream commits, in 9 files (`merkle/merkle_dag.py`, `merkle/change_detector.py`,
`merkle/snapshot_manager.py`, `search/indexer.py`, `search/searcher.py`,
`chunking/multi_language_chunker.py`, `chunking/tree_sitter.py`,
`chunking/python_ast_chunker.py`, `embeddings/embedder.py`). Lines that were later rewritten
can still carry upstream structure, so this count is a floor, not a clean split.

Every human contribution since the Apache switch is the maintainer's own (forkni, Alex
Korneev); the rest are bot commits. No outside contributor has to agree to a change.

## Decision

1. **License the whole project GPL-3.0-only.** `LICENSE` holds the GPL-3.0 text,
   `pyproject.toml` declares `license = "GPL-3.0-only"`, and the README, `CONTRIBUTING.md` and
   badge say the same. "Only", not "or later", because that is the version upstream granted.
2. **NOTICE names the upstream.** It states that this is a modified version of
   claude-context-local by Farhan Ali Raza, under GPL-3.0, with the fork point, and that the
   changes are recorded in the git history and `CHANGELOG.md` (GPL-3.0 §5(a)). The holder of
   the modifications is Alexander Korneev.
3. **Record the earlier mislabel.** NOTICE, the README, this ADR and the next release notes say:
   "Releases up to v0.26.0 were labelled Apache-2.0 in error; the parts derived from
   FarhanAliRaza/claude-context-local were always GPL-3.0." Old release bodies and tags are
   not edited.
4. **Keep the pyan quarantine file as is.** `chunking/relationships/external_call_graph.py`
   keeps its `Apache-2.0 OR GPL-2.0-or-later` header from ADR-0034. pyan3's
   GPL-2.0-or-later grant combines with GPL-3.0, and pyan3 stays an optional, unbundled
   `callgraph` extra. NOTICE shrinks the pyan paragraph to one line.
5. **No upstream contact.** Relicensing to the upstream's own license needs no permission.

Alternatives considered and rejected:

- *Keep Apache-2.0 and rewrite the derived files clean-room.* The derived code is spread through
  core modules, and a rewrite done with the old code in view would not reliably be clean.
- *Ask upstream for an Apache-2.0 grant.* It would leave the project's license dependent on an
  answer that may never come, while the published label stays wrong in the meantime.
- *GPL-3.0-or-later.* Upstream granted v3 only, so the derived parts cannot go further.

## Consequences

- Supersedes ADR-0034's statement that every file outside `external_call_graph.py` is
  Apache-2.0. ADR-0034's pyan analysis and the dual-license header still stand.
- The project's own code (about 99% of the tree) stays the maintainer's to reuse elsewhere under
  any license. Only upstream-derived expression is bound by GPL-3.0, and only when it is
  distributed. Ideas and algorithms re-implemented in other projects are not affected.
- Anyone who received v0.15.0–v0.26.0 under the Apache-2.0 label holds upstream-derived parts
  under GPL-3.0 regardless; the maintainer's own additions in those releases stay usable under
  the Apache-2.0 terms they were offered with.
- The prose in `external_call_graph.py`'s module docstring still calls the project an
  "Apache-2.0 project". It is left for a follow-up, since the header itself is unchanged.

## Verification

- `gh api repos/forkni/claude-context-local/license --jq .license.spdx_id` returns
  `GPL-3.0` after the merge.
- `git grep -n 'license = ' pyproject.toml` shows `GPL-3.0-only`.
- `./scripts/test/run_tests.sh tests/unit/ -q` stays green (no runtime code touched).
