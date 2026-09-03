# `inject_on_incremental` cost, measured on this repo (2026-09-03)

## Context

`CallGraphConfig.inject_on_incremental` (`search/config.py:1713`, default `False`) skips
resolver-pipeline call-edge injection on incremental index passes; `IndexWriteStage.run` only
injects on a full index. ADR-0044 measured the always-on-injection alternative on
`tests/fixtures/mini_repo/` (4 Python files): +1.58s latency, 5/5 resolver edges recovered, and
decided to keep the flag opt-in, default `False` — explicitly *not* extrapolating that number to
larger projects. The flag's own docstring says it "stays `False` until incremental-pass latency,
edges recovered, and the RW-lock hold time (ADR-0008) are measured" — on the project the lock
would actually apply to. This closes that measurement on `claude-context-local` itself: 233
indexed files (213 of them `.py`, the set the three resolvers scope over), 6,607 graph nodes /
28,199 edges at HEAD `268d8ea5cb0a33dc168a658328c66ee7ea6e4eb1`.

## Protocol

12-block matrix (`B0`-`B11` measurement, `B12` restore), `PYTHONHASHSEED=0` on every
`tools.batch_index` invocation, a byte-exact `search_config.json` backup + SHA-256 fingerprint
before flipping the flag, single-key surgical JSON rewrite (never `save_config()`), the flip
asserted live via `get_search_config().call_graph.inject_on_incremental`. Mutations were real
content changes (a unique trailing comment per file, per trial) — `merkle/merkle_dag.py`'s
`hash_file` is pure content SHA-256, so a bare `touch` never registers as a change and would have
produced a spurious Δ=0. Files were drawn from the 233 indexed files, excluding every file
referenced by any `evaluation/*golden*.json` golden ID. Every trial asserted `Files modified == K`
and (for the `True`-arm trials) that `lsp` appears in the resolver dispatch log, or the trial was
void. Arm-`False` is non-idempotent (a file's resolver edges can only be stripped once), so every
edges-metric trial started from a clean forced-reindex baseline; only latency replicates without a
rebuild.

| Block | Arm | K | Rebuild first | Purpose |
|---|---|---|---|---|
| B0 | — | — | force | clean `G0` baseline |
| B1-B3 | `false` | 1 | — | latency floor ×3 |
| B4 | — | — | force | reset |
| B5 | `false` | 10 | — | edge loss at K=10 |
| B6 | — | — | force | reset |
| B7-B9 | `true` | 1 | — | headline latency + edges recovered ×3 |
| B10 | — | — | force | reset |
| B11 | `true` | 10 | — | ADR-0044 reopening test: is cost flat in K? |
| B12 | — | — | force | final restore |

## Results

### Latency (`Time taken`, handler-bookend elapsed)

| Arm | K | Trials | Mean |
|---|---|---|---|
| `false` (default) | 1 | 2.11s, 4.09s, 2.08s | 2.76s |
| `false` (default) | 10 | 4.22s | 4.22s |
| `true` | 1 | 39.68s, 39.30s, 39.13s | 39.37s |
| `true` | 10 | 41.93s | 41.93s |

Δ(true − false) = **+36.61s at K=1**, **+37.71s at K=10** — a ~10-19x multiplier over the
opt-out baseline (39.68s/2.11s ≈ 18.8x at the tightest pair, 41.93s/4.22s ≈ 9.9x at K=10). The
whole pass runs under the ADR-0008 reindex-vs-search write lock, so this latency delta *is* the
RW-lock hold-time delta — no separate instrumentation was needed, closing that clause of the
docstring's condition too.

**Cost is flat in K**: +1.10s difference between K=1 and K=10 against a ~37s base, i.e. the
10x increase in changed-file count moved total latency by ~3%. Every `true`-arm trial's
`[CALL_EDGES]`/`[RESOLVERS]` log lines confirm why: `[RESOLVERS] Dispatching 3 resolver(s) over
213 file(s)` — pyan/libcst/lsp re-scan and re-resolve the *entire* 213-file `.py` corpus on every
incremental pass, not just the K changed files (`prepare_scoped_files` scopes to the indexed set,
exactly as ADR-0044 documented). The K=1 and K=10 trials' injected/added/upgraded/dropped counts
this produces are correspondingly dominated by the fixed corpus-wide resolve cost, not by K.

### Edges recovered / lost

| Arm | K | `[CALL_EDGES] Injected` | Resolver-mix vs `G0` | Total graph-link Δ vs `G0` |
|---|---|---|---|---|
| `false` | 1 | *(no `[CALL_EDGES]` line — path skipped entirely)* | lsp 1875→1872 (−3), libcst 720→713 (−7), pyan 552→547 (−5) | −13 |
| `false` | 10 | *(skipped)* | lsp 1875→1833 (−42), libcst 720→669 (−51), pyan 552→535 (−17) | −165 |
| `true` | 1 | 15 (added=12, upgraded=3, skipped=3132; floor dropped 21/3168) | fully restored (1875/720/552, byte-identical to `G0`) | −1 |
| `true` | 10 | 110 (added=86, upgraded=24, skipped=3037; floor dropped 21/3168) | fully restored (1875/720/552, byte-identical to `G0`) | −79 |

`inject_on_incremental=False` (the current default) confirms monotonic decay exactly as ADR-0044
describes: resolver-sourced edges attached to a re-chunked file's old chunk IDs are dropped and
never replaced, and the loss scales with K (13 at K=1, 165 at K=10 — order-of-magnitude
consistent, not identical, since which specific edges a given file anchors varies).
`inject_on_incremental=True` fully restores the resolver-sourced edge mix to `G0`-identical at
both K=1 and K=10 (this is the metric the flag actually manages), but a **residual shortfall in
total graph-link count persists at both K** (1 edge at K=1, 79 at K=10) — non-resolver
relationship edges (`imports`/`inherits`/`uses_type`/etc.) tied to a replaced chunk ID that
`add_embeddings` doesn't restore and that the resolver-only injection pass doesn't address either.
The flag closes the resolver-edge gap completely; it does not close this smaller, structurally
separate gap.

## ADR-0044 reopening condition: not met

ADR-0044's decision text (`docs/adr/0044-incremental-call-edge-injection-opt-in-only.md:61-83`) is
precise about what would justify flipping the default, and it is **not** "cost is flat in K":

> "Named follow-up, not built here: a *changed-file-scoped* injection — resolving edges only for
> `changes.added | changes.modified` (plus their direct neighbors) instead of the full indexed
> set. … This … is the reopening condition for flipping the default: **if a changed-file-scoped
> variant lands and its cost scales with change size rather than project size, re-measure and
> reconsider.**"

No changed-file-scoped variant exists — `prepare_scoped_files` still scopes to the whole indexed
`.py` set today, unchanged since ADR-0044. This session's measurement shows cost is flat in K
*because* the pass rescans the full 213-file corpus regardless of K — i.e. cost scales with
**project size, not change size**. That is precisely the diagnosis ADR-0044 already made on its
4-file fixture (there, too, the delta was "dominated by resolver startup cost … not by per-file
analysis work"); this session replicates it at 233-file scale with a far larger absolute number
(2.11s→39.68s here vs 0.28s→1.86s on the fixture). Flat-in-K is the *predicted signature of the
current architecture*, not evidence that the reopening condition — which requires a
changed-file-scoped implementation to exist and be re-measured — has been satisfied.

## Verdict and disposition

**Default stays `False`.** The measured cost (~37-42s per incremental pass, ~10-19x the opt-out
baseline, paid in full under the RW-lock regardless of how small the actual change is) is large in
absolute terms on this repo, and this repo runs with `performance.enable_auto_reindex: true` /
`max_index_age_minutes: 30.0` — auto-reindex passes fire routinely, so a default flip would impose
this cost automatically and repeatedly, not just on deliberate opt-in reindexes. ADR-0044's own
reopening condition is unmet (no changed-file-scoped variant exists to re-measure). This
supersedes the open item's prior "unquantified for this repo" status with a real number, and
closes the flag's docstring condition (latency measured, edges-recovered measured, RW-lock
hold-time measured — see `docs/adr/0044-incremental-call-edge-injection-opt-in-only.md`).

The residual non-resolver relationship-edge shortfall (1 edge at K=1, 79 at K=10) that
`inject_on_incremental=True` does not address is a separate, smaller gap in `add_embeddings`'s
node re-population and is out of scope for this measurement; noted here so it isn't re-discovered
as a surprise in a future incremental-injection investigation.

## Permanent timer

`search/call_edge_injection.py`'s `inject_call_edges` now records `resolve=%.1fs total=%.1fs` on
its existing `[CALL_EDGES] Injected...` log line (added around the `run_resolvers()` call and the
function's `try` block), via inline `time.perf_counter()` calls — **not** `utils.timing.timed()`,
which decorating either injection entry point would turn into a `decorated_definition:` chunk kind
and break five golden dataset entries (`golden_dataset_expanded.json`, `caller_golden.json` C007,
`callee_golden.json` OB03, `caller_golden_traced.json` TC007, `callee_golden_traced.json` TOB03—
precedent: this already happened once, from `@timed` on `IncrementalIndexer._add_new_chunks`).
This makes the latency/edges-recovered pair in this document reproducible on any future substrate
without a bespoke measurement session.

## Restore

Config restored from the pre-Item-2 backup and SHA-256-verified identical
(`226ad024edd31e796899378c6b581e8065f87129abc6d5e9feff552fcfb5ac0f`). All 10 mutated source files
reverted via `git checkout --`; `git status --short` matched the pre-capture snapshot exactly. A
final forced reindex (B12) reproduced `G0`'s graph state byte-for-byte (6,607 nodes / 28,199 edges,
resolver mix `lsp 1875 / pyan 552 / libcst 720`).
