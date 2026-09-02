# Call-Graph Generator Research: Disposition (2026-08-15)

**Date**: 2026-08-15
**Source**: External research log, "Static Call-Graph Constructors for Python in 2026: What
Actually Replaces PyCG, Jarvis, and pyan3", assessed against this repo's actual implementation
(`chunking/relationships/`, `search/config.py`, `docs/CALL_GRAPH_TUNING.md`, ADR-0034, ADR-0035).

## Summary

This log substantially overlaps a prior external survey already dispositioned on 2026-08-07
(`docs/plans/CALLGRAPH_RESEARCH_DISPOSITION.md`, → ADR-0034, ADR-0035). Its architectural
premise — a layered per-edge-confidence ladder — is correct and already implemented. Of its three
headline stages: **Stage 1 (pyan3 upgrade) is already done**; **Stage 3's Python half (LSP call
hierarchy) is already shipped and default-on**, and its cross-language half is already scoped by
ADR-0035; only **Stage 2 (HeaderGen as a new mid-tier)** is genuinely new information. Three
factual claims about this repo are wrong, all in the direction of under-crediting what is built.

**No resolver behaviour changed by this document. No reindex required.**

## Disposition table

| Log claim | Verdict | Evidence |
|---|---|---|
| Ladder = AST 0.5/0.7 → pyan 0.75 → LibCST 0.90 → LSP 0.98 | ✅ Accurate | `ResolverConfidence`, `chunking/relationships/call_edge_resolver.py:90-122` |
| "your existing 0.6/0.75 pyan tier" | ✅ Accurate | `PYAN_WILDCARD=0.60`, `PYAN=0.75` (same file) |
| TL;DR #1 / Stage 1: "upgrade to `pyan3>=2.6.2` (Technologicat fork)" | ❌ Already done | `pyproject.toml:89` pins `pyan3>=2.6.0`; installed wheel is 2.6.2 from `Technologicat/pyan`. The 2026-08-07 survey made the identical false-premise claim; already recorded there. |
| "pyan3 is GPL — verify Apache-2.0 compat; consider subprocess isolation" | ⚠️ Resolved, log is less precise than repo | ADR-0034: pyan3 is **GPL-2.0-or-later** (not bare "GPL" — decisive, since Apache-2.0 → GPLv2-only is *incompatible* while → GPLv3 is compatible). `external_call_graph.py` dual-licensed (`Apache-2.0 OR GPL-2.0-or-later`), `NOTICE` added. Subprocess isolation was considered and explicitly **rejected**: pyan's CLI exposes no hook for `_TrackedVisitor`'s wildcard-edge confidence demotion or the per-file failure isolation added in `befc65c`. |
| Stage 2: HeaderGen as a new ~0.80 flow-sensitive mid-tier | 🆕 Genuinely novel | Zero references anywhere in this repo prior to this document; absent from the 2026-08-07 disposition. |
| Nuanced / `jarviscg` archived 2026-03-05, vendor-only-if-already-depended-on | ✅ Correct, no-op | Not a dependency; zero references in repo |
| stack-graphs archived, no drop-in successor | ✅ Already agreed | 2026-08-07 disposition, "CodeQL disqualified; GitHub stack-graphs archived" row |
| Joern / `pysrc2cpg` as heavier alternative | ⚠️ Already declined | ADR-0035 declines Joern as premature — it backstops libclang/clangd tiers that don't exist here (no compile-database source on this Windows/MSBuild machine) |
| CodeQL as alternative | ✅ Already disqualified | Same 2026-08-07 disposition row |
| Stage 3: "harvest LSP call hierarchy — start with Python via basedpyright" | ❌ Already implemented, default-on | `chunking/relationships/lsp_call_graph.py` already drives `prepareCallHierarchy`/`outgoingCalls`; `lsp_enabled` defaults `True` (`search/config.py:1379-1382`, flipped in commit `70c8904`, 2026-08-02). No-ops only without the `[lsp]` extra. |
| Cross-language tree-sitter edges at ≈0.5–0.6 for the other languages | ⚠️ Already scoped, with a floor caveat | ADR-0035 already scopes exactly this for C/C++ at ≈0.6, modeled on `chunking/languages/glsl.py:655-707`. Caveat: `CallGraphConfig.min_confidence=0.65` (`search/config.py:1503`) discards sub-0.65 edges from `run_resolvers()` — a *chunking-time* extractor (the glsl.py pattern) bypasses that floor, an *injected resolver* tier would not. |
| "your 9 languages / 20 extensions" | ❌ Stale | 27 extensions since v0.25.0 — `chunking/language_registry.py:22-50` (C++ headers added: `.h .hpp .hh .hxx .inl .ipp .tpp`). `docs/MCP_TOOLS_REFERENCE.md:1214` already says "9 languages, 27 extensions" — no doc drift to fix here. |
| "~2,400-chunk corpus" | ✅ Directionally right | Recent indexes measured at 2,251–2,273 chunks |
| Apache-2.0 distribution, Windows, Python 3.11+ target | ✅ Accurate | `pyproject.toml:10-11`; pyrefly `python-platform = "win32"` |
| INDEX_VERSION + Merkle incrementality model | ✅ Accurate | `merkle/` package, `INDEX_VERSION` 4 |
| Scalpel dormant / pytype sunset / code2flow / python-graphs — none adopted | ✅ Correct, none in use | Zero references (`.pytype` in `.gitignore` is a stock ignore entry, not evidence of use) |

## The sharpest technical objection to Stage 2 (HeaderGen)

HeaderGen's claimed differentiators — flow-sensitivity and external-library return-type
resolution — are largely subsumed by the basedpyright LSP tier at 0.98, **already default-on**.
Under `run_resolvers()`'s confidence-precedence merge, a ~0.80 HeaderGen edge only survives where
pyan (0.75) misses *and* LibCST (0.90) misses *and* LSP (0.98) misses. That is a real but narrow
niche — chiefly users who never install the `[lsp]` extra. Its published 95.6%/95.3%
precision/recall figures are PyCG-lineage benchmarks (Venkatesh, Sotiropoulos & Bodden, *ESE*
2024), not independently measured on this corpus, and its Windows / Python 3.11+ support is
unverified against this project's actual target platform. See the Gate A/B probe below.

## Already-closed — do not re-propose

- Upgrading or replacing pyan3 — already on Technologicat 2.6.2 (`pyproject.toml:89`)
- pyan licence posture — settled by ADR-0034; do not re-propose subprocess isolation (rejected,
  loses `_TrackedVisitor` wildcard demotion and per-file failure isolation)
- LSP call-hierarchy harvesting for Python — shipped, default-on since `70c8904`
- Joern, CodeQL, stack-graphs — all already declined or agreed-dead (2026-08-07 disposition)
- `TypeInferenceProvider` / pyre as a resolver tier (Windows-incompatible, 2026-08-07 disposition)
- `"lsp"` as a `resolvers` config entry (ADR-0032 rejected gating LSP the same way as pyan/libcst)

## HeaderGen: staged probe — not run, dropped by decision (2026-08-15)

**Verdict: declined without reaching Gate A.** This is a schedule/priority decision, not a
technical disqualification — distinct from every other row in this document, which are all
evidence-backed declines.

What happened: `pip install headergen` into the scratch venv (`$CLAUDE_JOB_DIR/tmp/headergen_venv`,
never `.venv`) was slow because three system-level `pip.ini` files (user + global) carry a dead
`extra-index-url = https://pypi.ngc.nvidia.com` (confirmed NXDOMAIN via `nslookup`), forcing a
5x-retry-with-backoff cycle on every one of HeaderGen's transitive dependencies before falling
through to the working `pypi.org` index. The install was progressing, not hung — metadata for
`headergen` plus 7+ dependencies (`black`, `click`, `dill`, `fastapi`, `gast`, `intervaltree`,
`isort`) had already resolved. A second attempt with `PIP_EXTRA_INDEX_URL=""` /
`PIP_TRUSTED_HOST=""` set as environment variables (which override the config-file entries, unlike
the `--index-url` CLI flag) was started to work around the dead host, but the install was dropped
before completion by explicit decision — the pip.ini/NGC-mirror issue is a pre-existing local
environment defect unrelated to this repo, not worth spending more time on for a probe whose own
technical objection (§ above) already predicts a narrow marginal yield.

The pre-probe baselines were still captured and remain valid for a future attempt:
`evaluation/caller_recall_pre_headergen_20260815.json` (resolver_source: ast=25, libcst=23, lsp=6,
pyan=2) and `evaluation/callee_recall_pre_headergen_20260815.json` (ast=23, libcst=2, lsp=5,
pyan=2).

- **Gate A — platform smoke test.** Not run. Install abandoned mid-dependency-resolution.
- **Gate B — marginal unique-edge yield.** Not reached.
- **Gate C — file-incrementality + pre-registered A/B.** Not reached.

**Reopening condition:** either (a) the local pip.ini NGC extra-index-url is fixed/removed so
installs into scratch venvs aren't penalized, or (b) a future consumer never installs the `[lsp]`
extra (LSP disabled) — HeaderGen's marginal value rises without the 0.98 tier absorbing the shared
ground, which would justify the install friction. Absent either, do not re-propose HeaderGen
without first re-running this probe to completion.

## Deferred, with reopening conditions (carried from 2026-08-07, unchanged)

**C/C++ tiers 2–3 (libclang 0.85, clangd 0.97).** Reopen when a consumer has a real
`compile_commands.json` (CMake/ninja, or Bazel; MSBuild does not emit one).

**Confidence-weighted graph consumption.** Not pursued: `centrality_alpha=0.0` in the deployed
config, and every config-level graph-scoring lever tried in this project's history has been
measured and rejected. Reopening requires a pre-registered A/B under `PYTHONHASHSEED=0`
(ADR-0021), re-baselined per the substrate-drift rule.

## Verification

- `chunking/relationships/call_edge_resolver.py:90-122` (`ResolverConfidence`) — ladder confirmed
- `search/config.py:1379-1382` (`lsp_enabled` default `True`), `:1503` (`min_confidence=0.65`)
- `chunking/language_registry.py:22-50` — 27 extensions, 9 languages
- `docs/MCP_TOOLS_REFERENCE.md:1214` — already states "9 languages, 27 extensions", no edit needed
- HeaderGen probe: `scripts/benchmark/run_caller_recall.sh run --project-path <repo> --output
  evaluation/caller_recall_pre_headergen_20260815.json` (baseline capture), repeated with
  `--direction callees`; `--compare` mode against a post-HeaderGen run for Gate B
- `./scripts/test/run_tests.sh tests/unit/ -q` stays green — no runtime code touched by this
  document
