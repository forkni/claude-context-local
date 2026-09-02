# Deepen the config→searcher seam (C3 + C4)

Status: accepted
Date: 2026-08-05

## Context

`/improve-codebase-architecture` surfaced five deepening candidates across the repo's hot spots;
C3 (searcher-type branching + per-request config assembly in `SearchOrchestrator._search`) and C4
(the BM25 tuning clump in `HybridSearcher.__init__`) were selected together, on the basis that
they connect. Verifying the link turned up a latent measurement-correctness defect neither card
described on its own.

`mcp_server/` hand-assembled configuration for a searcher in two places, two shapes, and neither
shape was modelled as a module.

**Construction path** — `mcp_server/search_factory.py` held a whole `SearchConfig`, then unpacked
seven fields into primitives and passed them alongside the whole config to `HybridSearcher(...)`:
`rrf_k`, `max_workers`, `bm25_use_stopwords`, `bm25_use_stemming`, `bm25_tokenizer`, `bm25_k1`,
`bm25_b`. `HybridSearcher` stored the five BM25 values on `self`, re-passed them to
`_init_search_components`, and re-passed them again into `IndexSynchronizer` — which already
received `config=self.config` on the next line and stored its own copy. Five values, five
restatements, one construction.

All ten stored fields were dead: a repo-wide grep for `.bm25_{use_stopwords,use_stemming,
tokenizer,k1,b}` found only the ten assignments, no reads. The INIT log line and the
`BM25Index(...)` construction both used the local parameters, not `self.`. The only reads
anywhere were two test assertions that existed purely to pin the storing.

**Per-request path** — `search_orchestrator.py::_search` took the same singleton, lazily
deep-copied it in a nested closure, and mutated it across four inline blocks, each guarded by a
raw `isinstance(searcher, HybridSearcher)` check — while `_view = SearcherView(searcher)` was
already constructed earlier in the same function and `SearcherView.is_hybrid` existed
specifically to isolate that check in one place. The seam was built, then bypassed 40 lines
later; `find_connections` on `is_hybrid` returned zero callers. A grep for
`isinstance(…HybridSearcher)` outside `tests/` returned exactly seven hits: five in `_search`,
one in `graph_scoring_stage.py`, one inside the seam itself.

### The defect this exposed

All seven unpacked construction-path fields reach collaborators that read them once at
construction (`RRFReranker`, `ThreadPoolExecutor`, `BM25Index`, `BM25Okapi`). A grep for
`construction_baked=True` in `config.py` returned exactly four hits — `rrf_k_parameter` and the
three reranker fields. The other six travellers were tagged `reader="search/index_sync.py"` with
no liveness flag.

That tag has exactly one consumer: `evaluation/arm_overrides.py::requires_rebuild`, reached
through `apply_overrides` from four benchmark entry points (`run_sscg_benchmark.py::run_single`,
`probe_reserve_depth.py`, `probe_weight_sensitivity.py`, `probe_rerank_window.py`). An arm
overriding `search_mode.bm25_k1` — or any of the other five — got `requires_rebuild() == False`:
`run_single` mutated the live config in place, the cached `HybridSearcher` was reused, and the arm
would silently measure the pre-override value. This is the exact failure class ADR-0022's
liveness ratchet exists to prevent.

Three supporting facts:

- **No published result is corrupted.** The one BM25 knob actually A/B'd
  (`bm25_use_stopwords`, 2026-08-01) ran through `bm25_stopwords_ab.py`, which is BM25-standalone
  and never constructs a `HybridSearcher`. The hazard was latent, not realized.
- **An adjacent guardrail partly shadows it — but not the same one, and not all six.**
  `search/index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS` already blocked `bm25_k1`, `bm25_b`,
  `bm25_use_stopwords`, `bm25_tokenizer`, and `rrf_k_parameter`, each with a cited reason. That
  frozenset governs the ADR-0014 auto-tuning probe, not benchmark arms — it stops the probe
  writing these keys into `search_overrides.json`, and does nothing about a `--set` flag or an
  arm's override dict. `bm25_use_stemming` and `max_parallel_workers` appeared in neither list —
  no guardrail of either kind.
- **A code comment stated the liveness imprecisely, in the direction that misleads.**
  `config.py` said of `bm25_k1`/`bm25_b`: "Applied at query time — changing them takes effect on
  next load, no re-index needed." The second clause is right; the first is wrong —
  `bm25_index.py` re-applies configured k1/b against the saved values when an index loads, so no
  re-index is needed, but they are not query-time: mutating them on a live singleton is a no-op
  until the index reloads or the searcher rebuilds. The comment is what made `requires_rebuild()`'s
  `False` look correct.

**Smells**: Data Clump, Long Parameter List, Feature Envy (`mcp_server` on `SearchConfig`),
Repeated Switches, Middle Man (a seam built then bypassed).

**Deletion test**: passes on both halves. Delete the seven primitives — callers pass the config
object they already hold, and the collaborators read what they need; ten of the stored fields had
no reader at all, so they left nothing behind. Delete the five `isinstance` checks —
`SearcherView.is_hybrid` already answers the question and was called by nobody. Complexity
disappeared rather than relocating.

## Decision

Four phases, two hats: phases 1–3 are pure refactors (no behaviour change, 0 benchmark flips
expected); phase 4 is a behaviour change and got its own commit.

**Phase 1 — Preserve Whole Object at the construction seam (C4).** `HybridSearcher.__init__`
dropped `rrf_k`, `max_workers`, and the five `bm25_*` params (12 params → 5), resolving
`self.config` once and reading `self.config.search_mode.*`/`self.config.performance.*` in
`_init_search_components`. `IndexSynchronizer.__init__` dropped its five `bm25_*` params and dead
`self.bm25_*` fields, reading from the `config` it already received (deleting a stale `"legacy"`
tokenizer default in the process — config ships `"whole"`, harmless only because nothing read
it). `search_factory.py`'s seven unpacked kwargs were removed; `config=config` stays. `BM25Index`
keeps its primitive interface deliberately — it is a genuine leaf with independent adapters
(`bm25_tokenizer_ab.py`, `bm25_stopwords_ab.py`, `bm25_path_token_ab.py`) that construct it
directly. Commit `0b14c1f`.

**Phase 2 — Route type checks through the seam that already exists (C3a).** The five raw
`isinstance(searcher, HybridSearcher)` checks in `_search` and the one in
`graph_scoring_stage.py` now go through `_view.is_hybrid`, consolidated into a single
conditional wrapping the whole config-assembly region. The check inside the polymorphic-dispatch
call site (`HybridSearcher.search` vs. `IntelligentSearcher.search`, different signatures) was
left as a bounded exception — replacing that one is Replace Conditional with Polymorphism on
`BaseSearcher`, unifying two search signatures, and is out of scope for this round. Commit
`e0151fb`.

**Phase 3 — Extract the per-request config assembly (C3b).** The `config_singleton`/
`mutable_config()` closure and its four mutation blocks were extracted into
`build_effective_config(plan, base_config, is_hybrid) -> SearchConfig` in a new module,
`search/effective_config.py` — next to the config it manipulates and the retrieval modules that
consume the two policy tables it writes (`_intent_ego_thresholds`,
`INTENT_EDGE_WEIGHT_PROFILES`). `_search` is left with: acquire searcher, build filters, resolve
mode, build effective config, execute. Commit `4387008`.

**Phase 4 — Correct the liveness tags (behaviour change, separate commit).** Added
`construction_baked=True` to `bm25_k1`, `bm25_b`, `bm25_use_stopwords`, `bm25_use_stemming`,
`bm25_tokenizer`, `max_parallel_workers`; updated their `reader=` tags to `search/hybrid_searcher.py`
(the post-phase-1 baking site, no longer `index_sync.py`); corrected the liveness comment in
`config.py` and the matching one in `bm25_index.py` to state a live mutation is inert until index
reload or searcher rebuild, dropping the wrong "applied at query time" clause; cross-referenced
`index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS` so the two guardrails read as answering different
questions (*may* a probe tune it, vs. *must* a collaborator be rebuilt), noting
`bm25_use_stemming` and `max_parallel_workers` were covered by neither before this fix. This
makes `arm_overrides.requires_rebuild()` return `True` for arms touching these six keys, forcing a
searcher rebuild. Blast radius is the four benchmark entry points listed above; none run in the
MCP server path, so production behaviour is unchanged. Commit `603b65b`.

## Consequences

- One named module (`search/effective_config.py`) now owns "turn a `SearchConfig` (+ a
  `SearchPlan`) into what a searcher needs." `mcp_server` hands over whole objects instead of
  hand-unpacking fields at two separate call depths.
- `SearcherView.is_hybrid` finally has callers — the seam built for this purpose is adopted
  rather than bypassed.
- Six previously-untagged config fields are now correctly marked `construction_baked=True`,
  fixing the silent measurement defect in four benchmark entry points. `ADR-0022`'s liveness
  ratchet (`test_config_field_liveness.py`) pins the corrected 10-field
  `_CONSTRUCTION_BAKED_FIELDS` set as of this round — the set has grown since (13 fields live as
  of ADR-0042's audit); treat `SearchConfig._CONSTRUCTION_BAKED_FIELDS`
  (`search/config.py`), not this number, as the current source.
- **Re-pin: `canon_i1`'s intent-on arm becomes the published baseline** (63q mrr 0.8524, 133q mrr
  0.6879), superseding `canon_h1`'s arm figures (0.8418/0.6750). See
  `evaluation/CANON_20260805_CONFIG_SEAM_REPIN.md` for the full capture, delta tables, and the
  0-flips confirmation.

## Verification

`./scripts/test/run_tests.sh tests/unit/ -q` and `tests/fast_integration/ -q` both clean after
every phase. `check_lint.sh --modified-only` and `pyrefly check` clean. Phase 4 added a red-first
test (`test_requires_rebuild_true_for_construction_baked_fields`, parametrized over all six keys)
that failed before the tag was added and passes after. `audit_golden_dataset.py` CLEAN on both
datasets against the fresh 205-file/2323-chunk index. All four `canon_i1` views (63q control,
133q control, 63q arm, 133q arm) overall PASS, 0 flips relative to `canon_h1` — the measured
deltas are attributed to substrate drift from six commits that touched indexed source between the
two captures (see the canon doc's Substrate section), not to this round's refactor.

**End-to-end MCP re-verification was blocked on an environmental issue, not a code issue.** No
listener was found on port 8765 (`get_index_status()` returned "Unable to connect"); the local
MCP HTTP server was not running at verification time. This is a known limitation of this round's
verification, not evidence against the change — the benchmark harness's own capture runs the real
`search_orchestrator.py`/`HybridSearcher` path in a fresh process per invocation and is the
authoritative confirmation that phases 1–3 are behaviour-preserving.

## Out of scope

- **C1** (split the index-write half out of `HybridSearcher`) and **C2** (unify the retrieval
  funnel widths, already approved via ADR-0023/ADR-0026 and unexecuted) — surfaced alongside C3/C4
  but not part of this round.
- **C5** (make `SearchConfig` a dataclass) — speculative; `@dataclass` adds `__eq__`, which
  changes singleton comparison semantics.
- The two policy tables phase 3 relocates (`_intent_ego_thresholds`,
  `INTENT_EDGE_WEIGHT_PROFILES`) are measured inert by ADR-0026 (bit-identical pools, +0.0005
  MRR); deleting them is a behaviour change needing its own pre-registered gate, not proposed
  here.
