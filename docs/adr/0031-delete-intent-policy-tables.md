# Delete the two intent policy tables (QW5 + A1)

Status: accepted
Date: 2026-08-05

## Context

ADR-0030 relocated the per-request config-assembly logic into `build_effective_config` and, in its
"Out of scope" section, named two policy tables it deliberately left untouched: **QW5**
(`_intent_ego_thresholds` in `search/effective_config.py:74-93`) and **A1** (the
`INTENT_EDGE_WEIGHT_PROFILES` consumption at `:102-116`, sourced from
`graph/graph_storage.py:75-120`). Both were measured inert by ADR-0026 (bit-identical pools,
+0.0005 MRR combined), but deleting them needed "its own pre-registered gate, not proposed here."

That gate was blocked on a measurement gap: QW5 only fires when *both*
`plan.ego_graph_enabled` and `plan.intent_decision` are set, and no benchmark capture in this
repo's history had ever set the first, while production MCP callers pass it by default. A prior
round (commit `aad481f`) closed that gap: it added `--ego-per-request` to the harness, captured a
four-view matrix, and isolated QW5 as **flat** in isolation (`D − C`: MRR +0.0013 from one
already-known boundary query, recall@10 −0.0053, `pool_hit_rate` 0.0000). Full record:
`evaluation/EGO_PER_REQUEST_VIEW_20260805.md`.

**QW5's pre-registered gate read: flat ⇒ delete.** This round executes that deletion, deletes A1
alongside it (same code region, same measurement pass), and re-measures the combined result
against a same-substrate pre/post pair, judged via difference-of-differences (DiD) to cancel
substrate drift between captures.

### Verification before deletion

Confirmed by direct read and MCP `find_connections`/`search_code`:

- `find_connections` on `build_effective_config` returned exactly one direct caller
  (`SearchOrchestrator._search`, indirectly `SearchOrchestrator.run` plus two BM25 A/B scripts that
  reach it through the orchestrator). Its `imports` edge on
  `graph.graph_storage.INTENT_EDGE_WEIGHT_PROFILES` and its `uses_constant` edge on the same name
  are the two graph edges the deletion removes — `effective_config.py` ends up with no `graph`
  dependency at all.
- `find_connections` on `CodeGraphStorage.get_neighbors` returned three direct callers
  (`GraphQueryEngine.find_related_functions`, `EgoGraphRetriever.retrieve_ego_graph`,
  `MultiHopSearcher._graph_expand`), all of which pass `edge_weights` and all of which keep working
  on `DEFAULT_EDGE_WEIGHTS` alone — that table (21 entries, `graph_storage.py:49-73`) is untouched
  by this round.
- `QueryIntent` has exactly 7 members and all 7 are keys of `INTENT_EDGE_WEIGHT_PROFILES` with
  non-empty values, so `.get()` could never miss and `if edge_profile:` was truthy for every
  intent — the deepcopy fired on every intent-on request even when the write was an identity
  (`hybrid` is a bare `DEFAULT_EDGE_WEIGHTS.copy()`).
- Golden datasets store line-free `file:kind:name` chunk IDs
  (`graph/graph_storage.py:method:CodeGraphStorage.save`), and `effective_config.py` had zero gold
  references — deleting 46 lines from `graph_storage.py` could not break a gold ID.
  `audit_golden_dataset.py` ran CLEAN on both datasets, both pre- and post-deletion, confirming
  this.
- `INTENT_EDGE_WEIGHT_PROFILES` had exactly one production consumer, no `__init__.py` export, and
  no non-ADR doc references — a clean deletion.

## Decision

**Step 1 — the deletion (commit `4a93c65`, its own commit, two-hats rule).**

| File | Change |
|---|---|
| `search/effective_config.py` | Deleted the QW5 block (`:74-93`) and the A1 block (`:102-116`), including the local `from graph.graph_storage import INTENT_EDGE_WEIGHT_PROFILES`. Updated the module and function docstrings, which referenced "the two policy tables" and "intent-edge weights". |
| `graph/graph_storage.py` | Deleted `INTENT_EDGE_WEIGHT_PROFILES` (7 profiles, ~46 lines) and its header comment. `DEFAULT_EDGE_WEIGHTS` untouched. |
| `search/config.py:571` | Stale comment fix: `# Intent-specific weights (None = DEFAULT_EDGE_WEIGHTS)` → `# None = DEFAULT_EDGE_WEIGHTS`. |
| `tests/unit/search/test_intent_edge_profiles.py` | Deleted entirely — every test asserted directly on the deleted table. |
| `tests/unit/graph/test_graph_storage_weighted.py` | Widened `test_default_edge_weights_coverage`'s `expected_types` from 10 entries to all 21 `DEFAULT_EDGE_WEIGHTS` keys, recovering the coverage the deleted file provided. |
| `tests/unit/mcp_server/test_search_handlers_isolation.py` | Kept all five singleton-mutation assertions; re-framed the docstring to note three are now vacuous post-deletion and retained as reintroduction guards against any future write bypassing `build_effective_config`'s `mutable_config()` seam. |
| `tests/unit/search/test_effective_config.py` (new) | The mechanical proof: with `is_hybrid=True` and a plan carrying only `intent_decision` (no ego, no parent), `build_effective_config(plan, base, True) is base_config` — identity, not equality. |

No harness, measurement, or unrelated refactor changes went into this commit.

**Step 2 — post-side capture (`canon_j1`) and the QW5-removal proof (G2).**

MCP server restarted, then `cleanup_resources` → `batch_index.py --mode force` →
`audit_golden_dataset.py` CLEAN on both datasets against the fresh 205-file/2324-chunk index (one
chunk more than the 2323-chunk `canon_j0` substrate — both edited files are indexed, exactly as
anticipated).

G2 re-ran the 63q arm with `--ego-per-request` added
(`evaluation/sscg_canon_j1_63q_arm_ego_r1.json`). Diffed programmatically against the plain 63q
arm (`evaluation/sscg_canon_j1_63q_arm_r1.json`) on every `per_query` field except `latency_ms`:
**0 diffs across all 63 queries**, aggregate dicts matched exactly. With QW5 deleted, the only
remaining effect of `plan.ego_graph_enabled` is the no-op override write a prior round's G0 already
proved inert — this confirms nothing else was riding that flag.

## Measurement

### Capture pair

Both captures run `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, same four-view shape, control =
`intent.enabled=False` (harness default), arm = `--set intent.enabled=true` (the shipped default).

**S0 continuity check**: `canon_j0`'s 63q control/arm (0.8379/0.8524) reproduced the prior round's
`egoreq_a_63q_r1.json`/`egoreq_c_63q_r1.json` (0.8375/0.8524) within noise — substrate had not
drifted unexpectedly before this round's deletion.

| View | Dataset | MRR | Recall@10 |
|---|---|---|---|
| `canon_j0` control | 63q | 0.8379 | 0.7640 |
| `canon_j0` arm | 63q | 0.8524 | 0.7904 |
| `canon_j1` control | 63q | 0.8458 | 0.7640 |
| `canon_j1` arm | 63q | 0.8603 | 0.7864 |
| `canon_j0` control | 133q | 0.6700 | 0.7535 |
| `canon_j0` arm | 133q | 0.6841 | 0.7697 |
| `canon_j1` control | 133q | 0.6725 | 0.7541 |
| `canon_j1` arm | 133q | 0.6869 | 0.7704 |

### DiD gate (pre-registered, revert threshold: either metric < −0.02 on either dataset)

```text
DiD = (arm_post − arm_pre) − (control_post − control_pre)
```

| Dataset | Metric | DiD |
|---|---|---|
| 63q | MRR | (0.8603 − 0.8524) − (0.8458 − 0.8379) = **0.0000** |
| 63q | Recall@10 | (0.7864 − 0.7904) − (0.7640 − 0.7640) = **−0.0040** |
| 133q | MRR | (0.6869 − 0.6841) − (0.6725 − 0.6700) = **+0.0003** |
| 133q | Recall@10 | (0.7704 − 0.7697) − (0.7541 − 0.7535) = **+0.0001** |

All four values land within ±0.004 of zero — far above the −0.02 revert threshold. **The gate
passes cleanly. The deletion stands; no revert needed.**

Because a prior round already isolated QW5 as flat on a live path (`--ego-per-request`, G-series),
any movement observed here is attributable to A1 alone — the bundling of both deletions into one
commit does not muddy attribution.

### Scoping correction

ADR-0026's `+0.0005 MRR` is an upper bound on the *combined* non-redirect intent machinery, **not**
an isolation of these two tables. Deleting them removes nothing else from the intent layer: the
ADR-0029 `find_similar` redirect (+0.0999 MRR, gate-passed), CONTEXTUAL ego enablement, the GLOBAL
k-bump, and `_reorder_synthetic`'s GLOBAL check all survive. Three supporting facts, all verified:
the `hybrid` profile is a bare `DEFAULT_EDGE_WEIGHTS.copy()`, so a large share of queries provably
could not move; SIMILARITY queries **that redirect** return before `build_effective_config` runs at
all (those that don't redirect do reach it); and the deepcopy this removes fired on *every*
intent-on request because all seven `QueryIntent` members are keys of the table.

## Consequences

- Every intent-on request (the shipped default) that carries only `intent_decision` — no ego, no
  parent — now gets `base_config` back from `build_effective_config` **by identity**, not a
  `copy.deepcopy`. Pinned by `test_intent_only_plan_returns_singleton_by_identity`.
- `effective_config.py` has no import from `graph` at all.
- **Re-pin: `canon_j1`'s intent-on arm becomes the published baseline** (63q MRR 0.8603, 133q MRR
  0.6869), superseding `canon_i1`'s arm figures (0.8524/0.6879).
- Capture JSONs (`evaluation/sscg_canon_j{0,1}_*.json`) stay untracked, per every prior canon's
  precedent — this ADR is the durable record.

## Verification

`./scripts/test/run_tests.sh tests/unit/ -q` (5679 passed, 1 skipped) and
`tests/fast_integration/ -q` (102 passed) both clean. `check_lint.sh --modified-only` and
`pyrefly check` clean (0 errors). `audit_golden_dataset.py` CLEAN on both datasets, both
pre- and post-deletion.

**End-to-end MCP re-verification was blocked on an environmental issue, not a code issue** — no
listener was found on port 8765 at verification time, the same limitation ADR-0030 recorded. The
benchmark harness's own capture runs the real `search_orchestrator.py`/`HybridSearcher` path in a
fresh process per invocation and is the authoritative confirmation that the deletion is
behaviour-preserving beyond the measured DiD.

## Out of scope

- **C1** (split the index-write half out of `HybridSearcher`) and **C2** (unify retrieval funnel
  widths) — still open from ADR-0030.
- **C5** (`SearchConfig` as a `@dataclass`) — stays deferred; adds `__eq__`, changing singleton
  comparison semantics.
- Adding `--set` overrides and `--ego-per-request` to capture `config_metadata` so captures
  self-identify — a real gap, but a harness change, deferred to keep this round's hat as
  behaviour-change-only.
