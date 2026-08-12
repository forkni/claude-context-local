# Call-Graph Generator Research: Disposition

**Date**: 2026-08-07
**Source**: External research survey, "Robust Call-Graph Generators for Code RAG: Python,
C/C++, GLSL — Ranked Recommendations (2026)", assessed against this repo's actual
implementation (`chunking/relationships/`, `search/config.py`, `docs/CALL_GRAPH_TUNING.md`).

## Summary

The survey's architectural thesis — a layered per-edge-confidence ladder, precision-first,
don't chase whole-program soundness — is correct and already implemented. Written without
visibility into this repo, its three headline action items are either already done, rest on a
false premise, or are no-ops here. What it does surface as genuinely actionable: two
license-hygiene items (fixed, see `pyproject.toml`, `NOTICE`,
`chunking/relationships/external_call_graph.py`, ADR-0034), one un-taken but currently blocked
C/C++ tier (ADR-0035), one deferred graph-consumption idea, and five doc-drift defects (fixed
in `CLAUDE.md`, `docs/CALL_GRAPH_TUNING.md`, `docs/adr/README.md`).

**No resolver behaviour changed. No reindex required. No benchmark cycle run.**

## Disposition table

| Survey recommendation | Verdict | Evidence |
|---|---|---|
| Keep layered per-edge-confidence ladder; don't chase whole-program soundness | ✅ Already the architecture | `CallEdgeResolver` protocol + `run_resolvers()` confidence-precedence merge, `chunking/relationships/call_edge_resolver.py:355-521` |
| Python: replace the "abandoned pyan tier" with the Technologicat fork | ✅ Already on it — false premise | `.venv/.../pyan3-2.6.2.dist-info/METADATA` → `Project-URL: Homepage, https://github.com/Technologicat/pyan`, `Requires-Python: >=3.10`. The survey's "adnanshussain/pyan3 is inactive" claim describes a package we don't use. |
| Python alt: LibCST `QualifiedNameProvider` resolver at 0.75–0.80 | ❌ Reject — would lose recall | We already run `FullyQualifiedNameProvider` at **0.90** (`chunking/relationships/libcst_call_graph.py`). A second tier off the same provider only surfaces what LibCST currently *discards*, while dropping pyan's actual differentiator (whole-project import resolution + wildcard contraction). Measured: pyan = 3,594 injected edges vs LSP's 938 (v0.13.0/v0.15.0 measurements). |
| basedpyright LSP as top-confidence tier | ✅ Already the 0.98 tier, already default-on | `ResolverConfidence.LSP = 0.98`; `lsp_enabled` default flipped to `True` in commit `70c8904` (2026-08-02). Three protocol bugs fixed in v0.15.0. |
| Don't use `TypeInferenceProvider` (needs Pyre+watchman) on Windows | ✅ Already rejected + documented | `docs/CALL_GRAPH_TUNING.md` §3.6, §7 |
| Tag heuristic edges low-confidence but retain for recall | ✅ Already done | `resolver_source` / `resolver_confidence` on every injected edge, surfaced via `find_connections` |
| PageRank on a confidence-thresholded (≥0.75) subgraph | ⚠️ No-op as specified | `min_confidence=0.65` already excludes the only sub-0.75 tier (`PYAN_WILDCARD = 0.60`) at **build** time. Surviving edges are 0.75/0.90/0.98 — all already ≥ the survey's own threshold. The live version of this idea is deferred, see below. |
| GLSL: tree-sitter-glsl + name matching ≈0.9 is near-optimal | ✅ Already shipped and beyond it | `chunking/languages/glsl.py:655-707` — plus builtin filtering, type-constructor filtering, TD-prefix filtering, and struct-ctor→`INSTANTIATES` reclassification the survey doesn't contemplate |
| GLSL: shell out to glsl_analyzer (GPL-3.0) to corroborate | ❌ Decline | Survey itself rates the gain marginal; would add a GPL-3.0 binary dependency for it |
| C/C++: tree-sitter ≈0.6 → libclang ≈0.85 → clangd ≈0.97 | ⚠️ Tier 1 only | Grammars already core deps (`tree-sitter-c`, `tree-sitter-cpp`). Tiers 2–3 need `compile_commands.json`; no clangd/LLVM/cmake/ninja in this environment, and MSBuild doesn't emit one. See ADR-0035. |
| CodeQL disqualified; GitHub stack-graphs archived | ✅ Agreed, no action needed | |
| pyan is GPL — verify licence posture before shipping | ⚠️ Two real defects found and fixed | `pyproject.toml` comment said "GPL-2.0-only" (wheel METADATA says `GPL-2.0-or-later` — this inverts the Apache-2.0 compatibility analysis); `external_call_graph.py` imports pyan in-process and subclasses `CallGraphVisitor`, the strongest derivative-work posture, while carrying the repo's blanket Apache-2.0 header. Both fixed; see ADR-0034. |

## The blocker the survey couldn't know about

C/C++ call edges are not gated on picking a generator — they're gated on chunking.
`Calculator.cpp` produces 4 chunks for 67 lines because `chunking/languages/base.py:975`
hardcodes `["class_definition", "class_declaration"]` and line 983 returns unconditionally, so
traversal stops at `namespace_definition`. There are no member-function chunks to attach edges
to. `docs/plans/CPP_CHUNKING_PARITY.md` (written, unimplemented) must land first. Its
out-of-scope section already names the two follow-on hardcodes a C++ call-edge tier would need:
`chunking/multi_language_chunker.py`'s chunk-type allowlist excludes `"method"`, and
`is_method_call=False` is hardcoded there.

## Deferred, with reopening conditions

**C/C++ tiers 2–3 (libclang 0.85, clangd 0.97).** Reopen when a consumer has a real
`compile_commands.json` (CMake/ninja, or Bazel; MSBuild does not emit one). Asset when that
happens: `chunking/relationships/lsp_call_graph.py` is ~70% language-agnostic already — frame
codec, JSON-RPC ID correlation, aggregate watchdog, `_uri_to_path`, `_kill_process_tree`, and
the `prepareCallHierarchy`/`outgoingCalls` driver all generalize. Only three bits are
Python-bound: binary discovery (lines 100–118), `"languageId": "python"` (line 804), and
`_find_def_position`'s `def`/`class` regex (244–272). `gather_py_files`
(`call_edge_resolver.py:192`) hardcodes `rglob("*.py")` and would need parameterizing too.

**Confidence-weighted graph consumption.** The live version of the survey's PageRank idea is
that ego-graph expansion weights edges by relationship **type** only
(`ego_graph.edge_weights: {calls: 1.0, ...}`) and `graph_view.EdgeRecord` doesn't carry
`resolver_confidence` at all, so a 0.75 pyan guess expands identically to a 0.98 LSP
type-resolved edge. Not pursued now for two reasons: `centrality_alpha` is **0.0** in the
deployed config (PageRank reaches ranking only via the separate `centrality_bm25_boost` path),
and every config-level graph-scoring lever tried so far in this project's history has been
measured and rejected (PPR ego-graph, multi-hop expansion 0.25, `bm25_reserved_slots`,
intent-adaptive fusion weights). Reopening requires a pre-registered A/B with a declared gate,
under `PYTHONHASHSEED=0` (ADR-0021), re-baselined per the substrate-drift rule.

## Already-closed — do not re-propose

- pyan3 into core (non-optional) dependencies
- `TypeInferenceProvider` / pyre as a resolver tier (Windows-incompatible)
- Re-adding `PositionProvider` to the LibCST provider set (measured ~10% marginal cost, dropped)
- `"lsp"` as a `resolvers` config entry, i.e. gating LSP the same way as pyan/libcst (ADR-0032
  rejected this on measured behaviour-change grounds)
- Turning LSP on by default (already on, since commit `70c8904`)
- Renaming `resolver_source` back to `source` on graph edges (NetworkX node-link reserves
  `source` as a key; this was the original bug, already fixed)
