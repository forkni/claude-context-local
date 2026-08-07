# GPL-2.0-or-later quarantine for the pyan call-graph tier

Status: accepted
Date: 2026-08-07

## Context

An external research survey on call-graph generators ("Robust Call-Graph Generators for Code
RAG: Python, C/C++, GLSL — Ranked Recommendations (2026)") recommended verifying the licence
posture of the pyan-derived resolver tier before treating it as settled. Two real defects were
found during that review, both in this project's own licence bookkeeping rather than in the
architecture itself (`docs/plans/CALLGRAPH_RESEARCH_DISPOSITION.md` records the full survey
disposition; this ADR covers only the licensing decision).

**Defect 1 — wrong SPDX identifier.** `pyproject.toml`'s `[callgraph]` extra comment labeled
pyan3 "GPL-2.0-only". The installed wheel's METADATA says `License-Expression:
GPL-2.0-or-later` (verified directly, `.venv/Lib/site-packages/pyan3-2.6.2.dist-info/METADATA`).
This is not a cosmetic error: it inverts the Apache-2.0 compatibility analysis. Apache-2.0's
patent-grant and indemnity clauses count as "further restrictions" under GPLv2, making
Apache-2.0 → GPLv2-only a one-way *incompatible* combination. Apache-2.0 → GPLv3 (which
"or-later" reaches) *is* compatible one-way. The "or-later" grant is what makes any
Apache-2.0-adjacent use of pyan3 viable at all.

**Defect 2 — wrong isolation posture.** `chunking/relationships/external_call_graph.py` imports
pyan **in-process** (`from pyan.analyzer import CallGraphVisitor`) and **subclasses** it as
`_TrackedVisitor`, plus imports `pyan.anutils.Scope` and `pyan.postprocessor` directly. This is
the strongest derivative-work posture available — stronger than shelling out to pyan's CLI as a
subprocess, which the survey assumed was (or should be) the isolation model. The file carried
the project's blanket Apache-2.0 header despite this.

Neither defect was a distribution problem: pyan3 has been an optional `[callgraph]` install
extra since it was added (Apache-2.0-clean-core rationale already documented in
`pyproject.toml`), and the standard installer (`install-windows.cmd`) does not pull it — only
option [4] Developer Install/Repair does (`--all-extras`). The project ships zero lines of pyan
code either way. What needed fixing was the label on the dependency and the license on the one
file that derives from it.

## Decision

1. **Correct the SPDX label.** `pyproject.toml`'s `[callgraph]` comment now reads
   `GPL-2.0-or-later`, with a one-line note on why the distinction matters.
2. **Dual-license the one file that subclasses pyan.**
   `chunking/relationships/external_call_graph.py` carries an SPDX header
   (`Apache-2.0 OR GPL-2.0-or-later`) and is licensed GPL-2.0-or-later; every other file in the
   project remains Apache-2.0 per the top-level `LICENSE`. A `NOTICE` file at the repo root
   records the exception and the reasoning, per the standard Apache-2.0 convention for
   file-level license exceptions.
3. **Do not move to subprocess isolation.** Considered and rejected: pyan's CLI (`pyan3`
   console script / `create_callgraph()`) exposes no hook for `_TrackedVisitor`'s wildcard-edge
   confidence demotion (overriding `expand_unknowns()` to snapshot which edges were fan-out
   artifacts) or for the per-file failure isolation added in commit `befc65c`. Subprocess
   isolation would forfeit both without a clear licensing benefit — the current in-process
   approach is already a legally viable dual-license arrangement, not a stopgap.
4. **Do not remove pyan3.** It remains the highest-recall pre-LSP resolver tier (3,594 injected
   edges measured in v0.13.0 vs. LSP's 938 in v0.15.0) and stays an optional extra that a
   user installs at their own discretion, same as before this ADR.

## Consequences

- `pyproject.toml`, `NOTICE` (new), `chunking/relationships/external_call_graph.py` updated.
  No behaviour change — this is a licence-metadata and header fix only.
- Future files that import pyan in-process (rather than via `CallEdgeResolver`'s existing
  subprocess dispatch path in `run_resolvers()`) must carry the same dual-license header.
  Resolver code that stays outside `external_call_graph.py` and only consumes its output
  (e.g. `call_edge_resolver.py` itself) has no pyan import and needs no such header.
- This does not extend to other optional GPL/GPL-adjacent tooling considered and declined
  elsewhere (e.g. glsl_analyzer, GPL-3.0, declined in the same survey review for GLSL — see
  `docs/plans/CALLGRAPH_RESEARCH_DISPOSITION.md`); each such dependency needs its own review if
  ever proposed, this ADR covers pyan3 only.

## Verification

- `grep -rn "GPL-2.0-only" pyproject.toml` returns nothing.
- `chunking/relationships/external_call_graph.py` imports cleanly:
  `.venv/Scripts/python.exe -c "import chunking.relationships.external_call_graph"`.
- `./scripts/test/run_tests.sh tests/unit/ -q` stays green (no runtime code touched).
