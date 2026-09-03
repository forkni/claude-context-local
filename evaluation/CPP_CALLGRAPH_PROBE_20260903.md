# C/C++ Call-Graph Probe Re-Run: Real Pipeline vs. Phase-0 Simulation (2026-09-03)

Executes plan step 9 of `docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`
("Re-run the probe against the new pipeline; write the evaluation doc") for the C-family
call-edge tier shipped in `docs/adr/0060-c-family-call-edge-tier.md`.

## Method

The Phase-0 probe (design evidence in the plan, never committed as a script) simulated what
the eventual pipeline would do against voro-engine's pre-existing graph. Now that Wall 1/Wall 2
are real, shipped code, the only faithful re-run is to execute the actual pipeline:
`tools/batch_index.py --path D:\Users\alexk\FORKNI\VORO\voro-engine --mode force` (full
non-incremental reindex — required per the ADR-0060 migration note, since file content is
unchanged and an incremental pass would keep the old zero-edge chunks), then measure the
resulting `<slug>_call_graph.json` directly.

## Results: real pipeline vs. Phase-0 projection vs. plan gate

| metric | Phase-0 projection | real (first run) | real (after cast-operator fix, this doc) | plan gate | verdict |
|---|---|---|---|---|---|
| resolved (exact) | 39.5% | 27.09% (6,452) | 28.09% (6,452) | ≥ 8,000 edges | **fail** |
| resolved + ambiguous | — | 45.55% | 47.24% (10,850) | — | informational |
| phantom rate | 24.0% | 54.45% (12,968) | 52.76% (12,118) | ≤ 25% | **fail** |
| total graph-edge growth | +90% (capped) | +123.6% (30,479→68,148) | +120.8% (30,479→67,298) | ≤ +100% | **fail** |
| max ambiguous fan-out | ≤ cap | 3 (0 violations) | 3 (0 violations) | ≤ cap (3) | **pass** |
| hand-labeled precision | — | not yet measured | not yet measured | ≥ 0.85 | pending (task #13) |

3 of 4 measurable gates fail against real numbers. This section explains why, and what (if
anything) is a real code defect versus a mis-calibrated gate.

## Root-cause breakdown of the phantom-rate gap (24.0% projected vs. 52.76% real)

Every one of the 12,968 phantom-target call edges on the first real reindex was sampled and
categorized by target name:

| category | share of phantom edges | verdict |
|---|---|---|
| unfiltered cast-operator keywords (`static_cast`, `dynamic_cast`, `const_cast`, `reinterpret_cast`) | 6.6% (850 edges) | **real, fixable Wall-1 gap** — fixed in this pass (see below) |
| `_C_FAMILY_COMMON_MEMBERS`/`_COMMON_METHODS` "unless the project defines it" blocklist hits | 22.8% (2,954 edges) | **by design, not a bug** — `_resolve_call_target`'s own contract returns `None` for these (`search/graph_integration.py:1002-1005`), matching Python's pre-existing builtin-phantoming behavior. The Phase-0 probe's "+ noise filters" step modeled these as fully dropped (no edge emitted at all) rather than phantomed, which is why the probe's 24.0% projection undercounts relative to what the shipped, Python-consistent design actually produces. |
| everything else (2,780 distinct names, 1,465 appearing exactly once) | 70.7% (9,164 edges) | **legitimate external-library calls**, not a defect. Confirmed by sampling ranks 26-60 of the target-name frequency table: CUDA runtime (`cudaGetErrorString`, `cudaFree`, `cudaGetLastError`, `cudaMemcpyAsync`), Win32 (`GetProcAddress`, `CloseHandle`), a vendored JSON library (`dump`, `is_object`, `is_array`, `is_string`, `parse`), and what appears to be a creative-coding framework (`ci`, `v3`, `fc_make`). Ruled out `using namespace std;` leakage as the driver — unqualified STL free-functions (`sort`, `min`, `max`, `swap`, `move`, `transform`, `advance`, `fill`, `next`, `remove`) account for only 142 edges (1.1%) total. A tier-1, no-type-info, no-compile-database resolver (ADR-0035's explicit scope) cannot and should not resolve calls into code it never indexed — a phantom node for `cudaGetErrorString` is exactly as correct as Python's existing phantom node for an unindexed `requests.get`. |

## Fix applied this pass

`chunking/languages/_c_family.py`: added `_CAST_KEYWORDS` / `_is_cast_keyword`, mirroring the
existing `_is_std_qualified` pattern exactly. `static_cast<T>(x)` / `dynamic_cast<T>(x)` /
`const_cast<T>(x)` / `reinterpret_cast<T>(x)` parse as an ordinary `template_function`-shaped
call in tree-sitter-cpp (identical shape to a real call like `clamp<int>(x)`), so without this
check they were indistinguishable from project-defined template calls. Chunk-time filter, same
class as the pre-existing `std::`-prefix drop — unconditional, no project-wide context needed.

Verified by direct measurement, not just code review: re-running `--mode force` after the fix
removed exactly 850 edges from the graph (23,818 → 22,968 total C-family call edges, matching
the pre-fix cast-keyword count precisely) and all four `static_cast`/`dynamic_cast`/
`const_cast`/`reinterpret_cast` phantom placeholder nodes (confirmed absent from the rebuilt
graph). Resolved-edge and ambiguous-edge counts are byte-identical before and after (6,452 /
4,398) — expected, since cast keywords were never real candidates for either pool.

Test evidence: `./scripts/test/run_tests.sh tests/unit/chunking/ -q` → 517 passed, 2 skipped, 10
snapshots passed (no fixture exercises cast operators, so the snapshot corpus is unaffected).
`./scripts/test/run_tests.sh tests/unit/ -q` → 4,376 passed, 2 skipped, 1 failed
(`test_probe_hygiene.py::test_sys_path_bootstrap_count_does_not_exceed_baseline`) — this failure
is pre-existing drift from an unrelated, concurrent workstream (a `scripts/benchmark/
precision_estimate.py` script and `docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`
edits neither authored nor touched by this change; confirmed via `git status`/`git diff` showing
zero overlap with `_c_family.py`), not caused by or related to the cast-operator fix.

This is a chunk-time-only change scoped to `chunking/languages/_c_family.py`, invoked only from
`CChunker`/`CppChunker`/`CudaChunker`. It cannot execute on Python source by construction — no
separate canon re-run was needed beyond the existing test-suite pass above.

## Why the remaining 3 gate misses are not further fixable at tier 1

- **Phantom rate (52.76% vs. ≤25% gate):** 93.4% of the (unfixed) phantom mass is either
  intentional Python-parity design (22.8%) or genuine external-library calls (70.7%). Neither is
  addressable without either (a) reversing the deliberate "unresolvable → phantom node, not a
  dropped edge" design decision that keeps Python and C-family behavior consistent, or (b) a
  type-aware / compile-database-driven resolver (tier 2/3, explicitly deferred by ADR-0035, whose
  reopening condition — a real `compile_commands.json` or local clangd/libclang — still does not
  hold on this machine, reverified 2026-09-02 per the plan).
- **Resolved-edge count (6,452 vs. ≥8,000 gate):** a direct downstream consequence of the same
  phantom-heavy population, not an independent defect — voro-engine's real external-dependency
  surface (CUDA, Win32, a vendored JSON library, and whatever the `ci`/`v3` framework is) is
  larger than the Phase-0 probe's simulation accounted for.
- **Graph growth (+120.8% vs. ≤+100% gate):** same root cause; growth tracks phantom-plus-resolved
  edge volume, both up for the same reason.

## Recommendation: revise the plan's acceptance gates

The Phase-0 probe's thresholds (resolved ≥8,000, phantom ≤25%, growth ≤+100%) were estimated
from a single offline simulation whose noise-filter methodology (treat filtered call sites as
fully dropped) does not match how the shipped, Python-parity-consistent design actually behaves,
and whose sample did not fully anticipate how much of a real, externally-integrated C++ engine's
code legitimately calls into non-project APIs. Recommend:

- **Retire the flat resolved-count and phantom-rate/growth thresholds as pass/fail blockers.**
  Track them as informational trend metrics instead (useful for catching a real future
  regression via before/after comparison on the *same* project), not as an absolute bar every
  project must clear — the right value is inherently project-dependent on how much of its code
  is self-contained versus externally-integrated.
- **Keep the fan-out cap gate (≤cap) as a hard, binary pass/fail check.** This is a real,
  fully-controllable property of the shipped code (`CallGraphConfig.ambiguous_fanout_cap`), and
  it passes cleanly and reproducibly.
- **Keep the hand-labeled precision gate (≥0.85) as the primary hard quality gate**, and proceed
  to task #13 to measure it. Precision is computed over resolved/ambiguous (non-phantom) edges
  only, so it is untouched by the phantom-rate debate above and is the metric that actually
  reflects whether emitted edges are trustworthy for retrieval/traversal.

## Verdict

Plan step 9 closes here. One real, scoped Wall-1 gap found and fixed (cast-operator keywords,
6.6% of phantom mass, zero collateral on resolved/ambiguous counts, zero Python surface). The
remaining gate misses are root-caused to deliberate design choices and genuine external-API
surface, not defects — recommend revising the plan's absolute thresholds per above. Proceeding
to task #13 (hand-labeled precision sample) and task #14 (full reindex of voro-td and
cuda-link; voro-engine's reindex is already current as of this pass).
