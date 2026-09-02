# Implementation Plan: Call-Graph Recall Improvements

**Target:** forkni/claude-context-local (`development` branch), post-v0.23.0
**Date:** 2026-09-01
**Sources studied:** LARGER (arXiv 2605.16352), TraceEval (arXiv 2605.11006, github.com/yikun-li/TraceEva), clangd (LLVM 20+)
**Deferred:** InferCG local-LLM edge verification (explicit deferral; reopening condition in §7)

---

## Status (2026-09-01, post-measurement)

Annotation pass, 2026-09-01 evening. Proposal text below is unchanged; measured outcomes are appended as **Result (2026-09-01):** blocks under each item. Only §5, §7 and §8 carry revised forward-looking prose.

| Item | State | Outcome | Evidence |
| --- | --- | --- | --- |
| P0 canon re-baseline | DONE | 219 files / 2,642 chunks / 26,606 edges; 63q MRR 0.8419, 133q 0.6378, F-via-similar 0.8843 | `evaluation/CANON_20260901_REBASELINE.md` |
| A0 ω-bucket probe | DONE, gate PASSED (degenerate form) | bucket (b) golds 47 (63q) / 83 (133q); 84.6% / 86.6% of traversed call-edge visits sit at 0.5, below the 0.65 floor | `evaluation/EGO_MEMBERSHIP_PROBE_20260901.md` |
| A1 provenance ω table | PREMISE UNDERCUT | a float `resolver_confidence` is present on 35,647 of 364,490 traversed visits (63q); nothing to index on until the tag gap is diagnosed | probe D1 |
| A2 θ filter | REJECTED (pre-plan) | `min_traversal_confidence=0.6` + weighting byte-identical, 0 movers; floor 0.8 MRR −0.0040 | `evaluation/TRACK_A_AB_20260814.md` |
| A2 per-anchor top-k | REJECTED | gate-2 cap relief w15/w50: no upside CI excludes zero, recall@20 point estimates negative on both sets, 133q latency +310.9 ms/query | `evaluation/EGO_GATE2_AB_20260901.md` |
| A2 compose_confidence | UNTESTED | only surviving A2 sub-lever; bounded by the same membership ceiling (§7) | — |
| A3 community prior | BLOCKED | ADR-0015 partitions non-reproducible across reindexes (2,145 / 2,182 assignments changed) | `docs/adr/0015-remove-community-subsystem.md` |
| A4 size-adaptive θ/k | BLOCKED BY DESIGN | `ego_graph.max_neighbors_per_hop` benchmark-locked in `FORBIDDEN_AUTO_TUNE_KEYS`; θ inherits the A2 rejection | `search/index_probe.py` |
| A5 delivery block | PARTIALLY SHIPPED | `include_top_callers` opt-in since 2026-08-14 (≤2 callers, `{name, file}`); callees and cluster not built | `mcp_server/enricher_specs.py` |
| B1–B6 traced ground truth | UNTOUCHED | — | — |
| C1–C8 clangd tier | UNTOUCHED | clangd still not installed | — |

Substrate note: two pins were used on 2026-09-01. The canon and the A0 probe ran on 2,642 chunks; the gate-2 A/B ran later the same day on 2,581 chunks (same-session bases 63q 0.8183 / 133q 0.6336). Absolute MRR is not comparable across the two pins; the A/B's paired deltas are valid within their own session.

---

## 0. What each source contributes, in one paragraph each

**LARGER** is the closest published design to SSCG: a typed multigraph (dir/file/class/func) with `contains / imports / invokes / inherits / tested_by / documents / configures` edges, a **provenance-indexed edge confidence ω(e)**, a **threshold θ** that gates K-hop expansion, a **per-anchor top-k budget**, and a **Leiden community label κ** used as a soft prior in expansion scoring. Its ablation on MuLocBench (Acc@5) is the single most useful number for you: graph expansion −13.5%, confidence scoring −4.7%, community prior −4.1%, all three removed −16.0% (stacking). Its hyperparameter sweep shows oracle θ*and k* both rise with repository size (Spearman +0.40 / +0.36), which is direct evidence for your per-codebase adaptive tuning goal. Its call-edge extraction is weak (regex import extraction, name-match 0.5) — you are already ahead there; what it wins on is *how graph evidence is scored and delivered*, not how it is extracted.

**TraceEval** replaces hand-annotated or static-tool call-graph ground truth with **execution-witnessed edges**: a tracer (`sys.settrace` for Python) records every caller→callee actually fired under a driver; a program is accepted only if it runs, yields ≥2 cross-function edges, and produces an identical edge set across 3 runs. Ground truth is the *execution-covered* call graph, not the statically reachable one. The failure taxonomy it derives for LLM predictors (untaken-branch hallucination, declared-vs-runtime dispatch, class-name-as-callee schema mismatch) is also the taxonomy your static resolver tiers will exhibit. What you take from it is a **methodology for minting golden caller edges from your own test suite** and for **empirically calibrating the 0.5/0.7/0.75/0.90/0.98 confidence ladder**, which is currently asserted, not measured.

**clangd** is the only production-grade, incremental, compiler-accurate source of C/C++ call edges that fits a local-first Windows MCP server. It gives you `callHierarchy/incomingCalls` (any modern clangd) and `callHierarchy/outgoingCalls` (landed Nov 2024, PR llvm/llvm-project#117673, so clangd 20+; index memory +2.5%). It requires a `compile_commands.json` (or `compile_flags.txt`) and a persisted `--background-index`. Its critical semantic limitation for recall: call hierarchy is reference-based, so a virtual call through a base pointer is reported as a call to `Base::f`, never to overriders — you must add class-hierarchy expansion yourself.

---

## 1. Architecture after this plan

```
                      ┌─────────────────────────────────────────────┐
                      │  Resolver ladder (per language, per edge)   │
   Python             │  AST 0.5/0.7 → LibCST 0.90 → basedpyright 0.98│
   C/C++              │  tree-sitter 0.5/0.7 → clangd 0.98 (+CHA 0.85)│
   Other tree-sitter  │  tree-sitter 0.5/0.7                         │
                      └───────────────┬─────────────────────────────┘
                                      │ edges with (source, ω)
                      ┌───────────────▼─────────────────────────────┐
                      │  SSCG graph store (SQLite)                  │
                      │  + κ community label per file (Leiden)      │
                      │  + ω calibrated by traced ground truth      │
                      └───────────────┬─────────────────────────────┘
                                      │
                      ┌───────────────▼─────────────────────────────┐
                      │  Ego-graph expansion (search stage)         │
                      │  filter ω ≥ θ(repo)  ·  top-k(repo) per     │
                      │  anchor  ·  score × (1 + λ·[κ same])        │
                      └───────────────┬─────────────────────────────┘
                                      │
                      ┌───────────────▼─────────────────────────────┐
                      │  Evaluation                                  │
                      │  63q/133q golden (unchanged)                 │
                      │  + traced_callgraph.json (new, TraceEval-   │
                      │    style) → per-tier P/R, ladder calibration │
                      └─────────────────────────────────────────────┘
```

Three workstreams, ordered by cost-to-first-signal:

| WS | Name | Side | Reindex needed | First measurable signal |
| ---- | ------ | ------ | ---------------- | ------------------------- |
| A | LARGER-style expansion scoring | search-side | no | 63q paired CI, ~1 day of work |
| B | TraceEval-style traced ground truth | eval-side | no | per-tier precision table, ~2 days |
| C | clangd C/C++ resolver tier | pool-side | yes (C/C++ only) | caller-recall on a C++ repo, ~1–2 weeks |

A and B are independent. C depends on B for validation (you need traced C++ edges or at least a clangd-vs-tree-sitter delta to gate it).

---

## 2. Workstream A — LARGER-derived expansion scoring (search-side, config-only)

### A0. Probe first (per your probe-before-build rule)

Before writing any code, dump the ω distribution of edges that currently enter ego-graph expansion on the 63q golden set:

```
for each query q in 63q:
    anchors = top-N retrieval hits
    for each anchor a:
        for each edge (a→u) used in expansion:
            log (edge_type, resolver_source, ω, u ∈ gold?)
```

Compute P(u ∈ gold | ω-bucket). If precision is flat across ω-buckets, A1–A2 will not help and you stop here. If it is monotone (LARGER's premise), proceed. This is a 2-hour script over existing benchmark infrastructure.

**Result (2026-09-01):** Ran as `scripts/benchmark/probe_ego_membership.py` (`evaluation/EGO_MEMBERSHIP_PROBE_20260901.md`) on the 2,642-chunk canon substrate. Gate PASSED, but in a degenerate form. Distinct golds reachable-but-truncated at gate 2 (bucket b): 47 on 63q, 83 on 133q. D1 confidence profile of traversed call-edge visits (63q, 364,490 visits): untagged `calls` 177,788 and AST `ambiguous` 130,582, both mapped to 0.5 by `edge_confidence()`; AST `exact` 20,473 at 0.7; a float `resolver_confidence` on only 35,647 (under 10%). 84.6% (63q) / 86.6% (133q) of visits therefore sit below the 0.65 injection floor. That is not a monotone ω-vs-gold curve; it is one dominant bucket, so the probe cannot say whether ω predicts gold membership. D2: widening `relation_types` rescues 0/13 (63q) and 0/25 (133q) unreachable golds. D3: gate-2 truncation fired on 422/630 anchors (63q) and 902/1,330 (133q); the 422 / 902 gate-2 event counts are the canon pins for this substrate. D4 found the QW1 centrality-injection defect: the comment at `search/ego_graph_retriever.py:139-140` describes a centrality ordering that did not happen.

### A1. Provenance-indexed ω for all 21 relationship types

You already have per-edge `resolver_confidence` for call edges. Extend the same field to every relationship type so the expansion filter is uniform. Seed table (LARGER's values where they map; yours where you already have them):

| Edge provenance | ω (seed) | Note |
| --- | --- | --- |
| Structural: contains, defines, same-file | 1.00 | never filtered |
| Explicit import (AST-resolved to a file) | 0.95 | |
| Resolved import (via sys.path / package heuristics) | 0.90 | |
| Inheritance (AST) | 0.90 | |
| Call: LSP (basedpyright / clangd) | 0.98 | existing |
| Call: LibCST | 0.90 | existing |
| Call: clangd + CHA override expansion | 0.85 | new (WS-C) |
| Call: pyan | 0.75 | existing; slated for removal |
| Call: AST/tree-sitter resolved-in-file | 0.70 | existing |
| Call: AST/tree-sitter name-only | 0.50 | existing |
| Decorator / context-manager / enum-member (entity tracking) | 0.80 | |
| Test linkage (tested_by, by path/name convention) | 0.75 | |
| Documentation (documents) | 0.60 | |
| Config (configures) | 0.50 | |

These are seeds. **WS-B replaces the call-edge rows with measured values.** Store in `search_config.json` under `graph_enhanced.edge_confidence` so they are tunable without reindex.

**Result (2026-09-01):** Premise undercut by A0's D1. The table above indexes ω by provenance, but on the live graph fewer than 10% of traversed call-edge visits carry a float `resolver_confidence`; the rest resolve through `edge_confidence()` (`graph/graph_storage.py:61-110`) to the 0.5 / 0.7 AST tags or to the untagged-`calls` default of 0.5, and every non-call relationship type returns `None`, which `_edge_confidence` (`graph/graph_storage.py:708-723`, ADR-0050) maps to 1.0. This is consistent with the canon resolver mix (lsp 1,356 / pyan 1,143 / libcst 474 out of 26,606 graph edges): most call edges are AST-tier only. Whether that is by design or an injection gap is the A1′ question in §5; a per-type table has nothing to act on until it is answered. Not built.

### A2. θ filter + per-anchor top-k with additive scoring

Implement LARGER Eq. 13 in the ego-graph stage:

```
N*(v) = top_k { u ∈ N_K(v) : ω(v,u) ≥ θ }  by  score(u | v, q)
score(u | v, q) = base_relevance(u, q) · ω(v,u) · (1 + λ · [κ(u) == κ(v)])
```

- `base_relevance(u, q)`: whatever the reranker/hybrid score already assigns to `u` if it is in the candidate pool, else the RRF floor. Do not invent a new relevance model.
- `θ` default 0.5, `k` default 10, `λ` default 0 until A3 lands.
- Multi-hop: ω composes multiplicatively along the path (ω(v→w→u) = ω(v,w)·ω(w,u)); filter on the composed value. This is stricter than LARGER (which filters per edge) and prevents 2-hop chains of 0.5 edges (0.25) from flooding the pool — your dominant failure mode ("merged-cut pool-flooding" in the 2026-08-14 brief).

Config:

```json
"ego_graph": {
  "theta": 0.5,
  "top_k_per_anchor": 10,
  "hops": 2,
  "compose_confidence": true,
  "community_lambda": 0.0
}
```

**Result (2026-09-01):** Three sub-levers, three different states.

- θ filter: already existed and was already rejected before this plan was written. `GraphEnhancedConfig.min_traversal_confidence` (`search/config.py:1303`) and `traversal_confidence_weighting_enabled` (`search/config.py:1313`) were A/B'd 2026-08-14 (`evaluation/TRACK_A_AB_20260814.md`): floor 0.6 and weighting on are byte-identical to base (0 movers); floor 0.8 is quality-neutral (MRR −0.0040, CI [−0.0322, +0.0243]).
- Per-anchor top-k: exists as `EgoGraphConfig.max_neighbors_per_hop` (default 10, range 1–50) and was A/B'd as gate-2 cap relief (`evaluation/EGO_GATE2_AB_20260901.md`), arms base / w15 / w50 on the 2,581-chunk substrate. REJECTED. w50 vs w15: 63q MRR −0.0079 [−0.0270, +0.0063], recall@10 +0.0078 [−0.0185, +0.0348], recall@20 −0.0343 [−0.0693, +0.0003]; 133q MRR +0.0038, recall@10 −0.0032 [−0.0383, +0.0315], recall@20 −0.0375 [−0.0775, +0.0020]. No CI excludes zero on the upside; both recall@20 point estimates are negative; the 133q latency guard-rail was breached at +310.9 ms/query. The key is now benchmark-locked (`search/index_probe.py:97`). The QW1 centrality-sort repair was screened by offline replay first (`scripts/benchmark/probe_gate2_replay.py`, policy R2): 0/0 newly-admitted addressable golds on both datasets, consistent with `centrality_alpha 0.0`.
- Multiplicative ω composition (`compose_confidence`): UNTESTED and still not built. The implementation site is `CodeGraphStorage._traverse_neighbors` (`graph/graph_storage.py:510-583`): the weighted branch filters per edge (`:572-574`) and the heap push at `:583` discards the parent's weight, so no path-ω exists today. Prior: every membership lever tried at this stage (`drop_nonpositive_output`, `graph_hop_window_cap`, `bm25_reserved_slots`, now gate-2 cap relief) cost recall@20 or was inert, so this goes behind the offline replay screen in §5 before any GPU arm.

### A3. Community prior κ — reopen ADR-0015 with a different mechanism

ADR-0015 removed community *detection/summarization*. LARGER uses community labels as a **soft scoring prior during expansion**, not as a summarization target, and measures −4.1% Acc@5 without it. This is a distinct mechanism and is a legitimate reopening condition for the rejected-catalog entry.

Implementation:

1. Project SSCG onto an undirected **file-level** graph; edge weight = count of cross-file semantic edges (calls, imports, inheritance) between the two files. Structural `contains` edges are excluded.
2. Run Leiden (`leidenalg` + `igraph`, or `networkx.community.louvain_communities` as a lighter fallback) once per full index; store `community_id` and cohesion (edge density of induced subgraph) per file in SQLite.
3. Recompute lazily: only when the Merkle diff exceeds a threshold (LARGER: "cumulative diff exceeds a configurable threshold"); otherwise carry the labels forward. Suggested trigger: >10% of files changed since last partition, or on force-reindex.
4. Expose `λ` in config. Sweep λ ∈ {0, 0.15, 0.3, 0.5} on 63q.

Cost: Leiden on a file graph of a few thousand nodes runs in well under a second; this does not touch the embedding path.

**Result (2026-09-01):** Not reopened. The reopening argument above (scoring prior vs summarization target) is a real mechanism difference, but ADR-0015 records a blocker that is independent of mechanism: seeded Louvain produced 210/237 singleton communities and 2,145 of 2,182 assignments changed across two reindexes of the same tree (`docs/adr/0015-remove-community-subsystem.md:71-79`); the Leiden migration was cancelled (`:41-42`). A soft prior keyed on labels that do not survive a reindex cannot be measured against the seed-0 deterministic canons. Prerequisite before any λ sweep: a file-level projection that yields a stable, non-degenerate partition across two reindexes, built as a probe script, not production code. Step 2's "store in SQLite" also does not match the store: the graph is a JSON-persisted NetworkX graph and chunk metadata is a `SqliteDict` keyed by chunk id.

### A4. Size-adaptive θ and k (per-project override via ADR-0014's auto-tune probe)

LARGER's sweep (k ∈ {3,5,10,20}, θ ∈ {0,0.5}) found k*rises with LOC on multi-file tasks and θ* rises with LOC on single-repo localization. Encode as a policy in the ADR-0014 auto-tune probe, keyed on `log10(LOC)` and edge density:

| Repo size (LOC) | θ | k per anchor |
| --- | --- | --- |
| < 20K | 0.30 | 5 |
| 20K – 200K | 0.50 | 10 |
| > 200K | 0.65 | 15 |

These are starting points derived from LARGER's Figure 4 trend, not from your data. The probe should sweep ±1 step around the policy pick on the project's own golden set if one exists, else fall back to the table. Write the chosen values to the per-project config override.

**Result (2026-09-01):** Blocked by design, not by data. "k per anchor" is `ego_graph.max_neighbors_per_hop`, which is in `FORBIDDEN_AUTO_TUNE_KEYS` (`search/index_probe.py:97`) with a `BENCHMARK_LOCK_CITATIONS` entry pointing at the gate-2 A/B (`search/index_probe.py:142-146`); the ADR-0014 probe refuses to tune it. The θ column inherits the Track A rejection. The size table is unfalsifiable here: one indexed repo per size bucket at best, and the 63q/133q golden sets exist for a single repo. If size-adaptivity is ever revisited, the shape is an offline sweep whose winners are written as per-project `search_overrides.json` suggestions, never a runtime policy.

### A5. (Optional, token-cost trade) Graph evidence inside `search_code` output

LARGER's ablation attributes part of the gain to *delivery*: neighbors are appended to the lexical result the agent already reads, rather than requiring a second tool call. You currently enforce a 2-step `search → find_connections` workflow. Add an opt-in `search_code` output mode that appends, per hit, a compact block:

```
callers: auth/app.py:register_blueprint [0.98], auth/scaffold.py:_endpoint_from_view_func [0.90]
callees: helpers.py:url_for [0.95]
cluster: RoutingBlueprints
```

Cap at 3+3 per hit, ω ≥ θ only. Measure on the live MCP pipeline eval (k=7) — this is where it should show, not on the bare-searcher 63q. LARGER's cost analysis: per-step overhead Δ = m·k·L_node is bounded independent of repo size; the win comes from fewer agent steps, not cheaper steps.

**Result (2026-09-01):** Partially shipped before this plan. `include_top_callers` is an opt-in `search_code` parameter (`mcp_server/enricher_specs.py:51-66`, ADR-0049 enricher rows) backed by `_enrich_results_with_top_callers` (`mcp_server/tools/result_view.py:406-506`): at most 2 callers per hit, each `{name, file}`. ω is used only as the sort key (`mcp_server/tools/result_view.py:485`, higher `resolver_confidence` first) and is not emitted, so the `[0.98]` annotations above are not in the wire format. `callees:` is not built; `cluster:` has no data source while A3 is blocked. The live MCP pipeline measurement proposed here has not been run.

### Gates for WS-A

- 63q intent-on arm, paired 95% CI on MRR / R@7 / R@20 / pool_hit; guard-rail: no CI excludes zero on the negative side.
- 133q: upside; report R@20 and pool_hit primarily (this workstream targets recall, MRR may be flat).
- Noise band ±0.02 MRR; treat anything inside as null.
- Each of A2, A3, A4 gated independently; A3 additionally requires λ>0 to beat λ=0 outside the noise band or it stays off by default.

---

## 3. Workstream B — TraceEval-style execution-witnessed ground truth (eval-side)

### B1. Python tracer as a pytest plugin

Do **not** use the TraceEval harness generator (LLM-synthesized drivers). Your repo has 5,823 unit tests; the test suite *is* the driver. Write `evaluation/tracer/pytest_callgraph.py`:

- Python 3.12+: `sys.monitoring` with `PY_START` / `PY_RETURN` events on a dedicated tool id (much lower overhead than `settrace`).
- Python 3.11: `sys.setprofile` (call/return only; cheaper than `settrace`'s line events, which TraceEval used).
- Maintain a per-thread stack of `(code.co_filename, code.co_qualname, code.co_firstlineno)`. On each call event, emit edge `(stack[-1] → new_frame)`.
- Filter: both endpoints must be under the project root and not under `.venv/`, `site-packages/`, or the test files themselves unless `--include-test-callers` is set. Keep test→src edges as a separate set (they are exactly your `tested_by` edges, and they are the ones that validate ω=0.75 for that provenance).
- Resolve qualname → chunk_id via `(file, co_firstlineno)` against the SQLite chunk table. Unmatched → log and drop.
- Output `evaluation/traced_callgraph.json` in TraceEval's unified `caller → [callees]` schema plus your chunk ids.

### B2. Acceptance checks (TraceEval §2.3, adapted)

1. **Determinism**: run 3× ; the edge set must be identical. Non-deterministic edges (thread-timing dependent) are dropped, not averaged.
2. **Density**: reject the trace if < 2 cross-function edges (trivially true for you; keep the check for other projects).
3. **Schema validity**: every caller and callee must resolve to a chunk id.

### B3. Label semantics — read this before scoring anything

Traced edges are **positive labels only**. A static edge not in the trace is *unlabeled*, not a false positive — the test suite did not cover that path. Therefore:

- **Recall** of each resolver tier against traced edges is a real number.
- **Precision** of each tier against traced edges is a *lower bound*. Report it as such.
- To get a usable precision estimate, take a stratified sample (n≈100) of static-only edges per tier and hand-label them. Your 63q golden process already does this kind of labeling.

This is the mirror of TraceEval's failure taxonomy: their "untaken-branch hallucination" is, for you, a *correct static edge* the trace didn't cover.

### B4. Ladder calibration

For each `resolver_source` tier, compute:

```
recall_tier   = |E_tier ∩ E_traced| / |E_traced ∩ dom(tier)|
prec_lb_tier  = |E_tier ∩ E_traced| / |E_tier|
prec_est_tier = from hand-labeled sample
```

Then set ω(tier) := prec_est_tier (rounded to 0.05). If the measured ordering contradicts the asserted ladder (e.g. LibCST measured 0.82 but AST-resolved-in-file measured 0.88), the measured ordering wins and the README ladder is updated. Also compute per-tier recall to answer the actual question of this research thread: **which tier is contributing recall that the tiers above it miss?** If pyan's marginal recall over LibCST is inside noise, remove pyan immediately (it is archived and GPL-isolated anyway).

Expected shape, based on PyCG-family literature: AST name-match will show high recall / low precision (it is the permissive candidate set), LSP will show high precision / recall limited by unresolved dynamic dispatch and decorators.

### B5. Caller-recall benchmark v2

Replace the current caller-recall benchmark's golden with `traced_callgraph.json`. Add a failure taxonomy column per missed edge, using TraceEval's categories plus your own:

| Category | Static resolver typically misses because |
| --- | --- |
| Dynamic dispatch (runtime type ≠ declared) | receiver type unknown without flow analysis |
| Decorator-wrapped | call goes through wrapper `__call__` |
| Callback / higher-order | function passed as value, invoked elsewhere |
| `getattr` / string dispatch | name not syntactic |
| Cross-module alias | `from x import f as g` chains |
| Class instantiation → `__init__` | schema mismatch: class name vs `__init__` |

The last row is TraceEval's "class-name-as-callee" bucket; make sure your chunker emits `Class.__init__` edges consistently so this is not scored as a miss.

### B6. C/C++ tracing (stretch, only if WS-C needs an execution oracle)

- Build the target with `clang -finstrument-functions -g` (clang-cl accepts it on Windows) and a tiny runtime that logs `(caller_addr, callee_addr)` from `__cyg_profile_func_enter`; symbolize offline with `llvm-symbolizer` against DWARF/PDB.
- Inlining must be off (`-O0` or `-fno-inline`) or edges disappear.
- Same acceptance checks as B2. Expect this to be the most fragile piece of the plan; budget it separately and do not block WS-C on it. A clangd-vs-tree-sitter delta (C8) is sufficient to gate the first release.

---

## 4. Workstream C — clangd as the 0.98 tier for C and C++ (pool-side)

### C1. Prerequisites and project detection

clangd needs a compilation database. Detection order at index time:

1. `compile_commands.json` in project root, `build/`, or any directory named in `search_config.json` → `clangd --compile-commands-dir=<dir>`.
2. `compile_flags.txt` in project root (one flag per line; adequate for header-only or single-target projects).
3. Neither → **do not start clangd**; C/C++ stays on the tree-sitter tier and the index status reports `cpp_lsp: unavailable (no compilation database)`. Do not guess flags — a clangd running with wrong include paths produces confident wrong edges.

Generating the database, documented for users:

- CMake: `-DCMAKE_EXPORT_COMPILE_COMMANDS=ON` (writes to the build dir).
- Ninja/Make without CMake: `bear -- make` (Linux), `compiledb` (cross-platform, Python).
- MSBuild/Visual Studio: `clang-cl` toolset + CMake, or Clang Power Tools export. Flag in docs that MSVC-native projects will need `--query-driver` and often a `.clangd` with `CompileFlags: { Compiler: clang-cl }`.

Version requirement: **clangd ≥ 20** for `outgoingCalls`. Detect via `clangd --version`; on 11–19, run incoming-only mode (C3 fallback). Ship no clangd binary; locate on PATH, `CLANGD_PATH` env, or the VS Code clangd extension's download dir.

### C2. Process model

- One clangd process per indexed C/C++ project, spawned lazily on first C/C++ chunk, started with `--background-index --background-index-priority=normal -j=<min(4, cores/2)> --log=error --pch-storage=memory`.
- Persisted index lives in `<project>/.cache/clangd/index/` (or `--index-file` under `~/.claude_code_search/index/<project>/clangd/` if you want it in your storage tree; clangd honors `XDG_CACHE_HOME`-style overrides only partially, so the simplest is to leave it in-project and add `.cache/clangd` to the user's `.gitignore` guidance).
- Reuse the existing LSP client you built for basedpyright (JSON-RPC over stdio, request/response correlation, timeouts). Initialize with `callHierarchy` in client capabilities.
- **Readiness**: there is no standard "index complete" notification. Subscribe to `$/progress` and watch the `backgroundIndexProgress` token; treat `end` as ready. Until ready, edges from clangd are tagged `partial=true` and the tier is not written to SQLite as authoritative. Timeout after a configurable ceiling (default 10 min for the first index; subsequent runs are incremental and fast).

### C3. Edge extraction per function chunk

For every C/C++ chunk of kind function/method/constructor with a known definition position:

```
item  = textDocument/prepareCallHierarchy(uri, position_of_name)
in    = callHierarchy/incomingCalls(item)     # callers  → edges (caller → chunk), ω=0.98
out   = callHierarchy/outgoingCalls(item)     # callees  → edges (chunk → callee), ω=0.98  [clangd ≥ 20]
```

- Map returned `CallHierarchyItem.uri + selectionRange.start` back to chunk ids via the chunk table (file, line). Items outside the project (system headers, third-party) become external-symbol nodes, same as you do for Python stdlib.
- `fromRanges` gives call-site lines; store them for `find_connections` provenance.
- On clangd < 20: callees come from tree-sitter only (existing 0.5/0.7). This is a real recall loss for outgoing analysis; surface it in `get_index_status`.
- Batch requests; clangd handles concurrent requests but serializes on the AST for a given file. Throughput on a warm index is on the order of milliseconds per request; a 10K-function project is a few minutes end-to-end, once.

### C4. Dynamic dispatch — the recall gap clangd does not close

clangd's call hierarchy is **reference-based**. For

```cpp
struct Base { virtual void f(); };
struct Derived : Base { void f() override; };
void g(Base* b) { b->f(); }
```

`incomingCalls(Derived::f)` returns nothing; `incomingCalls(Base::f)` returns `g`. TraceEval's Java tracer would record `g → Derived::f` at runtime. To recover that recall:

1. Build the override graph: for each virtual method, `textDocument/implementation` (or the `typeHierarchy` requests) returns overriders. Cache as `overrides(Base::f) = {Derived::f, …}`.
2. **CHA expansion**: for every caller edge `X → Base::f` with `Base::f` virtual, add `X → Derived::f` for each overrider, `ω = 0.85`, `resolver_source = "clangd+cha"`.
3. Bound the fan-out: if `|overrides| > 8`, cap ω at 0.70 (wide hierarchies are exactly where CHA over-approximates). This mirrors the 8.2% → 2.5% memory discussion in the outgoing-calls PR: precision is what you pay for completeness.

Function pointers and `std::function` remain unresolved by clangd; keep tree-sitter's name-match at 0.5 for those. Do not attempt points-to here (that is the SVF/CGPatch territory rejected in the 2026-08 research pass as build-coupled).

Templates: clangd resolves calls inside templates only when the callee is non-dependent or an instantiation exists in the index. Dependent calls (`T::method()`) come back empty; the tree-sitter fallback edge stays. Tag these `unresolved_reason = "dependent"` so B5's taxonomy can count them.

### C5. Incremental maintenance

- Merkle diff → for each changed C/C++ file send `textDocument/didOpen` + `didChange` (or just rely on background-index file watching; clangd re-indexes changed TUs on its own when running with `--background-index`). Deterministic path: after the Merkle pass, send `didSave` for changed files, wait for the file's `backgroundIndexProgress` to settle, then re-run C3 for chunks in changed files **and** for chunks whose callers/callees were in changed files (reverse lookup from SQLite).
- Header changes fan out: a changed `.h` invalidates every TU including it. Use clangd's own dependency tracking; do not model include graphs yourself.
- Windows: normalize `file:///C:/...` URIs and case-fold paths when matching back to chunk ids.

### C6. Storage and provenance

Extend the existing `resolver_source` enum: `clangd`, `clangd+cha`, `clangd_partial`. `find_connections` already surfaces `resolver_source`/`resolver_confidence`; nothing new in the tool surface. Add to `get_index_status`: clangd version, DB path, index readiness, functions resolved / total.

### C7. Config

```json
"callgraph": {
  "cpp": {
    "enabled": true,
    "clangd_path": null,
    "compile_commands_dir": null,
    "background_index_threads": 4,
    "first_index_timeout_s": 600,
    "cha_expansion": true,
    "cha_fanout_cap": 8,
    "cha_confidence": 0.85
  }
}
```

### C8. Validation

1. Pick a C++ project with a working `compile_commands.json`. Your own CUDA-Link TouchDesigner plugin is the obvious candidate (CMake, moderate size, virtual-heavy plugin interface).
2. Baseline: tree-sitter-only caller/callee edges.
3. Treatment: clangd + CHA.
4. Metrics: edge count delta by category; caller-recall against (a) a hand-labeled 50-edge sample, (b) B6 traced edges if built. Report the CHA edges separately so their precision is visible.
5. Gate: clangd tier must add ≥ 20% more resolved-target edges over tree-sitter with hand-labeled precision ≥ 0.9 on direct edges, or it ships opt-in only.

---

## 5. Sequencing

```
Week 1   A0 probe ─┬─ (go)  A1 ω table + A2 θ/top-k/compose  ─ gate 63q
                   └─ (stop) write ADR "expansion scoring: no signal", skip A3–A5
         B1–B2 tracer + acceptance checks (parallel, no dependency on A)

Week 2   B3–B4 per-tier P/R, ladder recalibration → update A1 table → re-gate A2
         A3 community prior sweep λ ∈ {0, .15, .3, .5} ─ gate
         A4 size-adaptive policy into ADR-0014 probe

Week 3–4 C1–C3 clangd tier, incoming+outgoing, readiness handling
         C4 CHA expansion
         C8 validation on CUDA-Link

Week 5   C5 incremental path; A5 delivery experiment on live MCP eval (k=7)
         B5 caller-recall v2 published; pyan removal decision from B4 data
```

ADRs to open: `expansion-confidence-scoring` (A1/A2), `community-prior-reopen-0015` (A3), `traced-ground-truth` (B), `clangd-cpp-resolver` (C), `cha-expansion` (C4).

**Where this actually stands (2026-09-01):** Week 1's A-branch has been walked. A0 ran and passed in degenerate form, A2's two existing sub-levers are rejected, A3/A4 are blocked. The order below replaces the sequence above.

1. **WS-B first** (B1–B3, then B5). Eval-side, no reindex, no prior negative results. Python 3.11.15 in the venv means `sys.setprofile`, not `sys.monitoring`; map frames to chunk ids with the existing `evaluation/chunk_mapping.py` helpers.
2. **A1′ diagnose the tag gap.** Why do 84.6% (63q) / 86.6% (133q) of traversed call-edge visits sit at 0.5 with no resolver-tier confidence when the canon graph carries lsp 1,356 / pyan 1,143 / libcst 474 resolver edges? Only after that is answered does an ω table have anything to index.
3. **A5 completion**: `include_top_callees`, symmetric to the shipped callers enricher, opt-in, same 2-entry `{name, file}` shape.
4. **compose_confidence** only behind an offline replay screen (the `probe_gate2_replay.py` pattern) requiring at least 2 net newly-admitted golds on each dataset before any GPU arm.
5. **A3 parked** behind a stable-partition prerequisite (see the A3 result).
6. **A4 closed** (benchmark-locked key).
7. **WS-C unchanged**, still gated on clangd being installed and a C++ validation corpus larger than cuda-link's four C++ files.

---

## 6. Risk register

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| A0 shows ω is not predictive of gold membership on your graph | medium | Stop WS-A at A0; the ladder is still worth calibrating (WS-B) for `find_connections` provenance |
| Community prior repeats ADR-0015's null result | medium | It is gated independently; λ=0 default if it fails; the ADR records the *mechanism* difference so it is not re-proposed a third time |
| Traced edges bias precision estimates downward | certain | B3: report precision as lower bound; hand-label static-only sample |
| `sys.monitoring` overhead inflates test time | low | Only run under `--callgraph-trace`; not in CI's default path |
| User projects lack `compile_commands.json` | high | C1: refuse to guess; document generation; tree-sitter fallback stays |
| clangd < 20 on user machine → no outgoing calls | medium | Detect and report; incoming-only mode |
| CHA over-approximation floods ego-graph | medium | fan-out cap, ω=0.85 (< θ=0.65 on large repos, so it is filtered exactly where it is most dangerous) |
| clangd first-index time on large C++ trees | high | timeout + partial tagging; index survives restarts |
| Windows path/URI mismatches | high | C5 normalization; add tests with mixed-case drive letters |
| MSVC-only projects | high | documented as unsupported without clang-cl toolset |

**Result (2026-09-01):** Row 1 fired, in a degenerate form: ω is not "flat across buckets", there is effectively one bucket (0.5) on the traversed edges, which is worse for A1/A2 than flat precision would have been. Row 2 understated the blocker: it is not a repeated null result but partition non-reproducibility across reindexes (ADR-0015 `:71-79`), which no λ gate can see through. One row was missing:

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Ego-graph membership levers (cap, sort key, filter) are bounded by a flat ceiling: candidates admitted at gate 2 are cut again at gate 4, so relief upstream does not reach the final pool | now observed | Measure the ceiling first with an offline replay screen. Six A/B arms on 2026-09-01 settled three levers with no upside (cap relief measured, QW1 repair screened, confidence-sort bounded by the same ceiling); no further gate-2 arm without ≥2 net replay rescues on each dataset |

---

## 7. Deferred and rejected

- **InferCG-style LLM edge verification** — deferred by decision (2026-09-01). Reopening condition: WS-B shows the AST 0.5 tier carries ≥ 15% of traced recall that no higher tier recovers *and* its hand-labeled precision is < 0.6. That is precisely the regime where a verifier pays for itself; below it, the θ filter already handles the tier.
- **Points-to / SVF / CGPatch for C++** — rejected (build-coupled, LLVM-IR, HPC-oriented); CHA at 0.85 is the ceiling this plan targets.
- **LLM-synthesized drivers (TraceEval Stage 1)** — not needed; the test suite is the driver. Reopen only for user projects with no tests.
- **LARGER's sidecar JSON storage** — not adopted; SQLite already serves the same lookups.
- **Fine-tuned resolver model (TraceEval §3.3)** — out of scope; noted that tuned Qwen2.5-Coder-1.5B reaches 65.1 F1 on TraceEval, which makes a local-model tier plausible later if InferCG is reopened.

- **Gate-2 cap relief (`ego_graph.max_neighbors_per_hop` 10 → 15 / 50)** — rejected 2026-09-01 (`evaluation/EGO_GATE2_AB_20260901.md`). No upside CI excludes zero; recall@20 −0.0343 [−0.0693, +0.0003] (63q) and −0.0375 [−0.0775, +0.0020] (133q); 133q latency +310.9 ms/query. Key benchmark-locked. Reopening condition: a design that changes what gate 4 selects on, not how many candidates reach it.
- **QW1 centrality-sort repair at gate 2** — screened by offline replay (`scripts/benchmark/probe_gate2_replay.py`, policy R2, cap 20): 0/0 newly-admitted addressable golds on both datasets, consistent with `centrality_alpha 0.0` having no ranking effect. Not built into the retriever. Reopening condition: same as above.
- **A2′ confidence-sort / path-ω at gate 2** — not measured; bounded by the same ceiling, since it re-orders the same gate-2 candidate set that gate 4 re-cuts. Reopening condition: same as above, plus an offline replay showing ≥2 net rescues on each dataset.

---

## 8. What "done" looks like

- `search_config.json` has `edge_confidence`, `ego_graph.theta`, `ego_graph.top_k_per_anchor`, `ego_graph.community_lambda`; per-project override picks θ/k by size.
- `evaluation/traced_callgraph.json` exists, is regenerated by `pytest --callgraph-trace`, and `docs/BENCHMARKS.md` has a per-tier precision/recall table replacing the asserted ladder.
- README ladder row for C/C++ reads `tree-sitter 0.5/0.7 → clangd 0.98 (+CHA 0.85)` with a measured caller-recall figure on CUDA-Link.
- pyan is either removed or its marginal recall is documented as the reason to keep it.
- 63q canonical MRR unchanged within ±0.02; 133q R@20 or pool_hit improved outside the noise band, or the negative result is filed in the rejected catalog with the exact numbers.

**Correction (2026-09-01):** The first bullet names config fields that do not exist. The real `EgoGraphConfig` fields (`search/config.py:1070-1155`) are `k_hops` (range 1–3), `max_neighbors_per_hop` (default 10, range 1–50, now benchmark-locked), `relation_types`, `min_similarity_threshold` (0.15), `expansion_mode`, and `drop_nonpositive_output`. The proposed `theta` also conflates two distinct floors: `min_similarity_threshold` is a cosine floor on neighbour similarity, while the confidence floor is `GraphEnhancedConfig.min_traversal_confidence` (`search/config.py:1303`, ADR-0050), which is the θ that Track A rejected. The last bullet's negative-result branch has been taken for the per-anchor-k lever: the numbers are filed in `evaluation/EGO_GATE2_AB_20260901.md` and the lock in `search/index_probe.py`.

Record-only, no action taken:

- `_edge_confidence` (`graph/graph_storage.py:708-723`) maps an unknown confidence to 1.0, while A0's D1 measured untagged `calls` edges at 0.5. Both are true: `edge_confidence()` returns 0.5 only when `edge_type == "calls"` and `None` otherwise. Any future ω table must not assume a single unknown default.
- Dead community vestiges survive ADR-0015: `chunking/python_ast_chunker.py:53`, `chunking/languages/base.py:99`, and the `networkx` comment at `pyproject.toml:39`.
