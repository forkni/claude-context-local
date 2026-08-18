# Context-cost probe — full-corpus baseline (2026-08-18)

## Purpose

First corpus-wide run of `scripts/benchmark/probe_context_cost.py`. Prior to this the
context-cost axis had only ever been exercised on a single query (Q01) during the
disposition doc's static-analysis pass (`CODE_RETRIEVAL_AGENT_DISPOSITION_20260818.md`).
This run is measurement-only — no code, config, or scoring change — and was run
**before** the L5/L2a code fixes landed (`589f989`), by design: `results_vanished` is the
sizing evidence for L5, and fixing the formatter first would zero out the number that
justifies it. `format_savings` also baselines against the exact pre-fix formatter code.

Per the approved plan, this run settles sizing/gating only:

| Metric | Settles |
|---|---|
| `results_vanished_count` | Sizes L5 |
| `format_savings_mean` | Corpus-wide check of the `output_formatter.py` docstring's "30–55%" claim |
| `tokens_returned` | First real number on the token-cost axis |
| `gold_sufficiency`, `signature_view_delta_mean` | Gates L3 |
| `connections_fanout` | Gates L4 |

No re-ranking or re-opening of L3/L4 is done here — see Consequences.

## Method

```bash
.venv/Scripts/python.exe scripts/benchmark/probe_context_cost.py \
  --dataset evaluation/golden_dataset_expanded.json \
  --k 10 \
  --json evaluation/CONTEXT_COST_PROBE_20260818.json
```

Run in the background (`cleanup_resources` called first per the sequential-GPU rule; no
other GPU-loading process ran concurrently). The script re-execs itself under
`PYTHONHASHSEED=0` via `probe_harness.ensure_pinned_hash_seed()`, confirmed in the log
(`substrate.pythonhashseed: "0"` in the JSON). Wall clock ≈41 minutes (08:59:47–09:40).

Dataset: `evaluation/golden_dataset_expanded.json`, 147 queries across 7 categories (A 39,
H 39, C 19, B 18, D 14, E 9, F 9). The probe routes 133 of these (all but the 14
`D`-category, connections-shaped entries) through `search_code` at `k=10`; the 14
`D`-category entries drive `connections_fanout` (`find_connections`) instead —
`connections_fanout.primary_n=14` is exactly that count, `secondary_n=14` is the one-hop
follow-on from each primary with `secondary_skipped=0` (no primary came back empty).

## Results

### `results_vanished` — sizes L5 (corrected — see addendum below)

10 of 133 queries (7.5%) showed `results_vanished_count: 10`, **identically across all
three output formats**, in this run's original measurement. All 10 are `find_similar_code`
redirects (`redirect_kind: "find_similar"`) — 9 of the dataset's 9 total Category F queries
plus one `similarity`-classified `H` query:

| ID | Category | Query (truncated) |
|---|---|---|
| Q70 | F | find language chunker constructors similar to PythonChunker... |
| Q71 | F | find implementations similar to InheritanceExtractor._extrac... |
| Q93 | F | find detect_changes implementations similar to IncrementalIn... |
| Q94 | F | find add_chunk pattern implementations similar to GraphInteg... |
| Q95 | F | find BM25 search methods similar to BM25Index.search other... |
| Q96 | F | find search implementations similar to SearchExecutor.search... |
| Q97 | F | find FaissVectorIndex operations similar to FaissVectorIndex... |
| Q98 | F | find caching get and put implementations similar to QueryEmb... |
| Q99 | F | find save and restore implementations similar to GraphIntegr... |
| H021 | H | fix several protocol bugs in the language-server call-graph... |

**Addendum (post-fix investigation found this was a probe bug, not a live production
defect on this corpus)**: the Step 4 post-fix spot-check (below) initially still showed
`results_vanished_count: 10` after the L5 fix landed, which looked like the fix had failed.
Tracing it down found the real cause was in the **probe's own measurement code**, not
`output_formatter.py`: `_result_count`/`_results_key_present` (`probe_context_cost.py`)
only ever checked for a literal `"results"` key. `handle_find_similar_code` responses
(`search_handlers.py:351-354`) use `{"reference_chunk": ..., "similar_chunks": [...]}` —
`search_orchestrator.py`'s `"find_similar"` `PlanRedirect` returns that payload
**unmodified**, so `search_code`'s own `results` key never exists on these 10 responses in
the first place, formatter behavior aside. The module docstring (`:46-47`) already named
this "an expected outcome, not an error," but the metric functions never actually
implemented that — they misreported every redirect as a vanished-results case regardless
of the formatter.

Checking `ego_contract.ego_on_result_count` (computed straight from `response["similar_chunks"]`,
upstream of the buggy key-check) against the **original pre-fix** run confirms all 10 queries
always returned **10 non-empty `similar_chunks` matches** — never zero. Since the
formatter's empty-value guard only ever drops *empty* values, it was never triggered for
any of these 10 queries, before or after the L5/`NEVER_DROP_EMPTY_KEYS` fix. **The reported
`results_vanished_count: 10` was a probe-tooling artifact, not evidence of a live defect
firing on this corpus** — corrected here rather than left standing.

This does **not** mean the underlying contract gap was imaginary: `similar_chunks` was
genuinely missing from `NEVER_DROP_EMPTY_KEYS` (verified via a direct unit test,
`test_empty_similar_chunks_survives_all_formats`, which fails without the fix and passes
with it) — a real `find_similar_code` call that returns zero matches would still have hit
P11 pre-fix. This corpus's 9 F queries and H021 simply never exercise that path; every
`find_similar_code` redirect in the current golden dataset happens to have matches. The fix
(`similar_chunks` added to `NEVER_DROP_EMPTY_KEYS`) is closed as a preventive completeness
fix, not a corpus-confirmed rescue — see Consequences.

### `format_savings_mean` — corpus-wide check of the docstring claim

| Format | Mean bytes | Median | p90 | Savings vs verbose |
|---|---|---|---|---|
| verbose | 11,683 | 12,489 | 13,082 | — |
| compact | 7,450 | 7,978 | 8,423 | 36.7% |
| ultra | 4,743 | 5,006 | 5,449 | 59.2% |

The docstring's "30–55%" claim (`output_formatter.py:4`) holds for `compact` (36.7%) and is
**exceeded** by `ultra` (59.2%, vs. the documented ceiling of 55%) at corpus scale — Q01
alone previously gave 35.5%/58.8%, consistent with this run. No action item; recorded as
the first corpus-wide confirmation.

### `tokens_returned` — first corpus number on this axis

- Production heuristic mean: **2,252.95** tokens/query
- `tiktoken` (cl100k) mean: **3,125.14** tokens/query
- Ratio (tiktoken/production): **1.387** — the in-repo token-count heuristic under-counts
  actual tokenizer output by ~39% on this corpus, on average, for `search_code` responses
  at `k=10`.

`k_drift` (requested `k=10` vs. actual `len(results)`): mean **17.7**, median **20**, max
**20**, nonzero for 123/133 queries — the server routinely returns roughly double the
requested `k` (multi-hop/ego-graph expansion adds rows beyond the literal top-k), which is
why `tokens_returned` is measured against what's actually delivered, not the nominal `k`.

### `gold_sufficiency` / `signature_view_delta_mean` — gates L3

- `located_rate`: **0.94** (125/133 queries have their gold chunk somewhere in the
  returned set)
- `content_present_rate`: **0.0**, expected and structural — `search_code` returns
  coordinates (chunk_id/file/lines), never inlined file content, so this is not a defect,
  just confirmation of what L3 (a signature/content view) would be adding.
- `signature_view_delta_mean`: whole-file reads average **27,680** tokens/query vs. a
  targeted-span read averaging **6,086** tokens/query — a **78% reduction** (21,594
  tokens/query avoided) if an agent used a signature/targeted-span view instead of reading
  whole files to get from a located coordinate to usable content.

This is real, corpus-scale sizing evidence for L3 that did not exist before this run — the
disposition doc's original L3 estimate was static-analysis-only. Per plan scope, this
report **does not** decide to build L3; it only banks the number for later gating.

### `connections_fanout` — gates L4

| | primary (14) | secondary (14) |
|---|---|---|
| mean payload bytes | 30,148.7 | 50,513.0 |
| mean `total_impacted` | 87.5 | — |
| skipped | — | 0 |

De-conflated (not the conflation-inflated 317 figure the disposition doc's static estimate
used): mean fan-out across the 14 `D`-category `find_connections` anchors is **87.5**
impacted chunks, with one outlier (`C005`,
`search/hybrid_searcher.py:method:HybridSearcher.get_by_chunk_id`) at **577** impacted /
123 files / 183,824 payload bytes / 56,170 tiktoken tokens — a single call whose token cost
alone exceeds this probe's entire 133-query `search_code` mean by ~18x. Secondary (one-hop
follow-on) calls cost ~1.7x primary's mean payload with zero skips, i.e. every primary
anchor had at least one further edge to follow. This is the de-conflated distribution L4
would need to size a cap against; again, not decided here.

### `ego_contract` (context, not gated by this plan)

`ego_off_within_k_rate=1.0`, `ego_actually_disabled_rate=1.0`,
`truncation_semantics={interleaved_or_reranked: 121, appended_only: 12}` — recorded for
completeness; belongs to the deferred L2b A/B, not acted on here.

## Consequences

- **L5 is closed for `results`/`direct_callers`/`direct_callees`**, and separately
  extended to `similar_chunks`. The `results`/`direct_callers`/`direct_callees` fix
  (`589f989`) landed in the same session as this measurement, ordered strictly after this
  probe run; per the addendum above, this corpus provides **no** live-fire evidence for
  those three either (no query in the 133-query set returns a genuinely empty `results`,
  `direct_callers`, or `direct_callees` list) — the fix is unit-test-confirmed correct
  (`test_output_formatter.py`), not corpus-confirmed as a rescue. Same status for
  `similar_chunks`.
- **L2a's `format_savings` claim is corpus-confirmed**, no action needed.
- **L3 and L4 are gateable, not built.** Both now have real corpus-scale sizing
  (`signature_view_delta_mean`, de-conflated `connections_fanout`) instead of a
  single-query estimate; deciding whether to build either is a separate, later call, per
  the plan's explicit out-of-scope note.
- **Post-fix spot-check (Step 4 of the plan) — done, with a detour.** The first two
  spot-check attempts, run after the `589f989` fix and then again after extending
  `NEVER_DROP_EMPTY_KEYS` with `similar_chunks`, both still showed
  `results_vanished_count: 10`. That triggered the investigation recorded in the
  `results_vanished` addendum above: the probe's own `_result_count`/
  `_results_key_present` never recognized `similar_chunks` as a valid carrier key, so they
  misreported every `find_similar` redirect as vanished regardless of the actual payload.
  Fixed by threading the already-computed `redirect_kind` into both functions (a
  `_negative_evidence_key` helper picks `similar_chunks` vs `results` accordingly); no
  `find_path` case exists in the current corpus (`redirect_kind` histogram checked: zero
  entries), so that key name is left unhandled rather than guessed at. A third spot-check
  (`--query-ids Q70 Q71 Q93 Q94 Q95 Q96 Q97 Q98 Q99 H021`, `evaluation/
  CONTEXT_COST_PROBE_20260818_POSTFIX_SPOTCHECK3.json`) with the corrected probe now shows
  `results_vanished_count: {"verbose": 0, "compact": 0, "ultra": 0}` and every one of the
  10 queries reporting `result_count: 10` / `results_key_present: true` in all three
  formats — confirming the probe now measures this contract correctly. `format_savings` on
  these 10 queries is otherwise consistent with the full-corpus run.
- **Net effect on the axis this plan measures**: the true P11 defect population in the
  current 133-query corpus is **zero, not ten** — the original 7.5% figure was a
  measurement artifact of the probe script, corrected in this document rather than left
  standing. Both code fixes (`results`/`direct_callers`/`direct_callees` in `589f989`, and
  `similar_chunks` in the immediate follow-up commit) remain justified as closing a real,
  unit-test-confirmed contract gap; neither has yet been observed rescuing a real query on
  this corpus, because no query here currently exercises a genuinely empty payload on any
  of the four allowlisted keys.
