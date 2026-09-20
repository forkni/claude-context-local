# Make single-block listwise reranking an invariant

Status: accepted
Date: 2026-09-19

`JinaRerankerV3.rerank()` scored a rerank window in exactly one packed
listwise block whenever the window fit under `listwise_packed_token_budget`
(ADR-0076), and fell back to Jina's own multi-block splitting loop when it
didn't. ADR-0076 argued that split was safe because block 1 stays
near-invariant and the perturbation lands on the fusion tail. The 3-leg gate
run on the freshly-pulled ADR-0076 commits refuted that argument. This ADR
makes single-block scoring an invariant — enforced by adaptive per-document
truncation — instead of a preference, and demotes ADR-0076's splitting
machinery to a backstop.

## Context

Legs 1↔2 of the gate (default budget 8192, self-index) were bit-identical:
every metric `+0.0000`, 0 movers, both datasets — the self-index never packs
past 8192, so the pulled fix was a genuine no-op there. Leg 3 (budget forced
to the 2048 floor, engaging multi-block) told a different story on 133q:
recall@5 **−0.0485** (CI `[−0.0940, −0.0031]`, excludes 0), NDCG@5 **−0.0478**
(CI `[−0.0847, −0.0109]`, excludes 0), MRR −0.0199, recall@20 −0.0296 —
breaching ADR-0076's own ±0.02 tolerance. Movers ran both ways (H034 +1.000,
H054 −1.000): increased ranking variance, not uniform loss, and the damage
landed on recall@5/NDCG@5 — the **head** of the ranking, not the tail.

### Diagnosis — why splitting degrades ranking

Read from vendor `modeling.py`
(`~/.cache/huggingface/modules/transformers_modules/jinaai/jina_hyphen_reranker_hyphen_v3/*/`,
all four cached revisions byte-identical) plus the paper (arXiv 2509.25085v4).
Blocks are not scored independently and merged by raw sort — there is no
score-scale mismatch:

```python
247  query_embeddings.append(outputs.query_embeds[0]...)   # one per block
249  block_weights.append(((1.0 + scores) / 2.0).max())     # block's BEST doc
265  query_embeddings = np.average(query_embeddings, axis=0, weights=block_weights)
267  scores = self._calculate_cosine_scores(query_embeddings, doc_embeddings)
269  scores_argsort = np.argsort(scores[0])[::-1]           # ONE global sort
```

Per-block scores are discarded as a ranking signal. Scores land on one common
scale — numerically comparable, semantically not. Both operands of that
cosine are functions of block membership:

1. **Query-vector blur.** `<|query_emb|>` sits after all passages in a causal
   LM, so the query representation has attended over that block's documents.
   At one block it is the true whole-window vector; at five blocks it is an
   average of five vectors each conditioned on a fraction of the candidates.
2. **Adversarial averaging weights.** The weight is the block's **max**
   score, so one strong hit lets its blockmates tilt the global reference
   vector — a within-block popularity effect with no analogue at one block.
3. **Document vectors are causally block-contextualized.** Each `<|doc_emb|>`
   depends on which documents precede it *in its block*. The feed is
   score-ordered, so top candidates systematically get short weak contexts
   once split.
4. **Three existing optimizations silently lose their premise.**
   `merged_pool_policy`, `hop1_reserved_slots`, and `graph_hop_window_cap`
   (`search/rerank_window_policy.py`, applied by `RerankingEngine`) are each
   justified in-code by "the listwise model re-scores the whole window, so
   intra-window order doesn't matter." That holds only at one block. All
   three are `benchmark_locked` on A/Bs run at one block on the self-index —
   their locks stay sound, and this invariant is what keeps them sound on
   token-dense corpora going forward.

ADR-0076's "Recall risk" section claimed both *"block 1 is near-invariant"*
and *"the query vector changes globally"* — the second is correct, the first
is refuted by `modeling.py:265-267` and by Leg 3 landing its damage on
recall@5/NDCG@5. There is no "un-degraded slice" when the final sort is
global; see the correction note added to ADR-0076.

The default budget already splits the corpus that matters:
`evaluation/RERANKER_TD_TOKEN_DENSITY_20260919.md` measured TD `operator`
chunks packing to 8,948 tokens at N=30 against a default budget of 8,192 —
TD runs at roughly two blocks in production today, not the five-block stress
dose Leg 3 measured. Raising the budget instead is refuted by the incident
ADR-0076 fixed: 8,948 tokens is exactly the length that OOM'd.

## Decision

1. **One listwise block is an invariant**, not a preference. Multi-block is
   a bug, not a mode.
2. Enforce it by **adaptive per-document token truncation**
   (`derive_listwise_doc_budget`, `search/neural_reranker.py`): a uniform
   per-document token cap is solved by binary search so every document,
   clipped to that cap, still packs into one block within
   `listwise_packed_token_budget`. `top_k_candidates` — the window's
   document *count* — is never reduced; only document bodies are trimmed.
   Pure water-filling: documents shorter than the cap are untouched, only
   longer ones are cut. The search bound (`hi = max(doc_lengths)`) means the
   solver never proposes a cap larger than the longest document's own
   length — there is no reason to solve for one.
3. Below `_LISTWISE_MIN_DOC_TOKEN_ALLOWANCE = 150` tokens, that request's
   documents are rebuilt with `signature_head` representation
   (`_build_rerank_document(..., mode="signature_head")`) instead of
   truncating `full` text further — a signature_head rendering (path/parent
   line + capped docstring + 12 source lines) typically lands in the
   100–250 token range at code's measured ~3.2 chars/token density, so the
   swap engages before blind truncation would have cut deeper than
   signature_head already goes. The A4 verdict (ADR referenced in
   `search/config.py`'s `doc_representation_mode` field) rejected
   `signature_head` as a *default* on recall grounds; this is not that — it
   is a starvation fallback for the minority of requests that would
   otherwise get truncated past readability, not a blanket swap.
4. ADR-0076's splitting machinery (`derive_listwise_model_max_length`,
   Jina's own multi-block flush loop) is **demoted to a backstop**, not
   deleted: `_fit_single_block` falls through to it only when adaptive
   truncation under-shoots (decode/re-encode drift, or starvation with no
   `signature_head` fallback available), and logs a warning when it does.
5. Shipped **default-on with an escape hatch**:
   `RerankerConfig.listwise_window_fit: str = "truncate"` (default, this
   ADR) or `"split"` (ADR-0076's original behaviour, kept for rollback and
   for the decisive A/B below).
6. This ADR cross-references, does not supersede, ADR-0076 — the token
   budget, the OOM retry (Tier 2), the `RuntimeError` string contract with
   `RerankingEngine._session_oom_detected`, and the `truncation=True` guard
   test are all unchanged and still load-bearing. A correction note was
   added to ADR-0076's "Recall risk" section rather than rewriting it, so
   the historical record of what was believed at the time stays intact.

### Implementation

- **`search/neural_reranker.py`**: `derive_listwise_doc_budget` (pure,
  independently testable, no tokenizer/model dependency — same contract as
  its ADR-0076 siblings `_packed_block_length`/`_simulate_listwise_blocks`).
  `_fit_single_block` orchestrates the solve, the floor→`signature_head`
  swap, and the split-backstop degradation; called from `_attempt_rerank`
  before the vendor `model.rerank()` call, on the fully-built document with
  the `ID:` header included (token space, not char space — `_build_rerank_document`'s
  own docstring warns the header is never counted against `max_chars`).
  `JinaRerankerV3.last_block_count`/`last_doc_token_cap` record the most
  recent attempt for offline observability; see their `__init__` comments
  for the exact "last pass wins" semantics and the one documented asymmetry
  between them (`last_doc_token_cap` reflects the last *attempted* solve —
  it is set inside `_fit_single_block`, a pure CPU step that always
  completes before the GPU call that can fail — while `last_block_count`
  only reflects the last *successful* attempt).
- **`search/config.py`**: new `RerankerConfig.listwise_window_fit` field,
  `construction_baked=True` (sibling of `listwise_packed_token_budget`),
  `choices=("truncate", "split")`, `flat_alias`, `env`,
  `reader="search/neural_reranker.py"`, no `mcp=` (not caller-tunable per
  search, matching its sibling).
- **`search/reranking_engine.py`**: no behavioural change — `_run_rerank`
  already copies `last_block_count`/`last_doc_token_cap` onto itself
  (ADR-0076 plumbing), reused unchanged as this invariant's assertion
  surface. Its exception branch resets `last_doc_token_cap` to `None`
  unconditionally, so at this layer (unlike `JinaRerankerV3`) the attribute
  does carry pure "last successful pass" semantics.
- **`scripts/benchmark/probe_rerank_window.py`**: `Instrumentation`'s
  `patched_run_rerank` captures `last_block_count`/`last_doc_token_cap` per
  call (placeholder `None` before `orig_run_rerank` runs, backfilled from
  the mutated `self_engine` after — covers the case where the call raises).
  `print_query_report` surfaces both per query; a new
  `summarize_listwise_invariant(records)` helper tallies `n_engaged`,
  `n_multi_block`, `multi_block_query_ids`, `min_doc_token_cap`, and
  `median_doc_token_cap` across a probe run, printed after the `Totals:`
  line and written to `--json-out` under `"listwise_invariant_summary"`.

## Verification

Three tiers, fastest first.

1. **Structural (seconds, no GPU)** —
   `./scripts/test/run_tests.sh tests/unit/search/test_jina_reranker_v3.py -v`:
   the pure solver tested for the invariant (block count == 1 across
   densities), the floor→`signature_head` swap, header-inclusive token
   accounting, and the existing guard that the vendor call site never
   passes `truncation=True`. 56/56 passing. The fuller
   `tests/unit/search/` suite (1,899 tests,
   `PYTHONHASHSEED=0 CLAUDE_AUTO_REINDEX=0`) passes with zero regressions.
2. **Offline window replay (minutes, one live pass)** —
   `probe_rerank_window.py --all`, extended per above. Proves the invariant
   holds (or doesn't) on every query at a given budget without a GPU
   benchmark leg. Honest boundary: this replays window *composition*, not
   listwise *scoring* — it cannot predict MRR, only whether block count
   stayed at 1.
3. **Behavioural (GPU, hours)** — the gate below. The only tier that can
   answer the quality question.

## Gate

All legs: `export CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, paired
same-corpus, `--compare`'s `[CONFOUND]` guard clean.

0. **Pre-gate** — `probe_rerank_window.py --all` at budget 8192 and 7000.
   Confirms the invariant holds on every query and that the 7,000 dose lands
   above the `signature_head` floor, before spending GPU hours.
1. **Inertness control** — default budget 8192, 63q + 133q. Expected
   bit-identical to the current canon (the self-index packs to 7,484 at
   8192, so the solver must not bind).
2. **Decisive A/B** — `--set reranker.listwise_packed_token_budget=7000` on
   the self-index, 63q + 133q, `listwise_window_fit=split` (old) vs
   `=truncate` (new). At 7,484-vs-7,000 tokens, `split` produces two blocks
   — TD's production regime — while `truncate` produces one block via a
   roughly 7% per-document trim. Isolates the splitting variable at the
   dose that actually matters in production.
3. **Live TD smoke** — via the `code-search` MCP server: `get_index_status`
   first, then a token-dense query against `TD_Glossary_tox`. Confirm no
   OOM, `last_block_count == 1`, reranking stays enabled on the following
   query.

Pass criteria: leg 1 bit-identical; leg 2 shows `truncate` ≥ `split` on
recall@5/NDCG@5 with no guard-rail breach (recall@20 ≥ −0.02); leg 3 clean.
A neutral leg 2 still ships the invariant on correctness grounds (there is
no principled reading under which scoring a window in one coherent block is
worse than fragmenting it), but must be recorded honestly rather than
presented as a win.

`listwise_window_fit` gets `spec(benchmark_locked=...)` citing this gate's
report only after the gate runs — see `search/config.py` and
`tests/unit/search/test_index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS` literal.

### Gate results (2026-09-20)

Ran on the self-index at 238 files / 3,061 chunks (post `dc3c8493` +
ADR-0072 CLONES merge — newer than the 09-08 canon's 235/2,978).

- **Leg 0 (pre-gate probe)** — `probe_rerank_window.py --all` confirms the
  invariant: `n_calls == n_engaged == 248`, `n_multi_block == 0` at every
  budget tested (8192 and a 9000–16000 sweep run during triage below).
  `min_doc_token_cap`/`median_doc_token_cap` sit at ~242/278 tokens — this
  is the pre-existing, unrelated `listwise_doc_max_chars=1000`-char cap
  (`_build_rerank_document`) firing upstream of this ADR's solver, not
  evidence the solver is binding. On this substrate the solver never
  engages at any budget in that range.
- **Leg 1 (inertness, budget 8192)** — NOT bit-identical against the stale
  09-08 canon: 63q showed a real, CI-excluding-0 regression (recall@5
  −0.0236, recall@10 −0.0304, recall@20 −0.0240, NDCG@5 −0.0188); 133q
  showed the same direction but all CIs included 0. This looked like a
  gate failure and triggered an isolation check: `listwise_window_fit=split`
  (old ADR-0076 code path) vs `=truncate` (this ADR's default), both at
  budget 8192 on the *identical* current substrate. Result: **bit-identical**
  — every metric `+0.0000`, bootstrap CI `[0.0000, 0.0000]`, 0 movers, n=63.
  Since neither code path can be responsible for a difference it doesn't
  produce, leg 1's apparent regression is substrate drift between the 09-08
  pin and this substrate, not a defect introduced by this ADR. Raising
  `listwise_packed_token_budget` (9000→16000) was checked as a possible
  fix and found inert — confirms the binding cap is
  `listwise_doc_max_chars`, unrelated to this field. A canon re-pin remains
  separately owed (see Out of scope) to make future inertness checks
  comparable again.
- **Leg 2 (decisive A/B, budget 7000, split vs truncate)** — neutral on
  both datasets, no guard-rail breach: 63q mrr −0.0146, recall@5 −0.0013,
  recall@10 −0.0013, recall@20 −0.0040, ndcg@5 −0.0009 (all CIs include 0);
  133q mrr −0.0116, recall@5 +0.0038, recall@10 −0.0029, recall@20 +0.0000,
  ndcg@5 −0.0007 (all CIs include 0). Per the pass criteria above, the
  invariant ships on correctness grounds — this is recorded as a neutral
  result, not a win.
- **Determinism** — truncate-arm 63q, round 1 vs round 2: bit-identical
  (all deltas `+0.0000`, 0 movers).
- **Leg 3 (live TD smoke)** — via the `code-search` MCP server against
  `TD_Glossary_tox` (15,393 chunks). A 30-result `operator`-filtered query
  (the densest chunk kind, matching the ADR-0076 OOM profile) returned
  every result with a populated `reranker_score` distinct from its raw
  `score` — no OOM, no fallback to unreranked results. A follow-up query on
  the same connection also returned populated `reranker_score`s, confirming
  reranking stayed enabled rather than being silently disabled for the rest
  of the session (`_session_oom_detected`, the exact failure mode ADR-0076
  fixed). `last_block_count` itself isn't exposed over the MCP interface,
  so this leg verifies the externally-observable pass criteria (no OOM,
  reranking survives) rather than the internal block count directly — the
  offline probe (leg 0) is what verified block count == 1.

## Considered options

- **Raise `listwise_packed_token_budget` instead of truncating.** Rejected:
  refuted by the incident ADR-0076 fixed — 8,948 tokens (TD's measured
  density) is exactly the length that OOM'd; the window must genuinely come
  down, not just be allowed to split less often.
- **Reduce `top_k_candidates` to force everything under budget.** Rejected:
  that is a hard pool truncation (`reranking_engine.py` slices
  `candidates[:rerank_count]` and discards the tail outright), which
  destroys candidates and hits `recall@20`/`pool_hit_rate` directly — a
  different and worse failure mode than trimming document bodies.
- **Proportional scaling instead of a uniform cap.** Rejected: would trim
  short, already-concise documents along with long ones for no reason;
  `listwise_doc_max_chars` already establishes uniform-cap semantics
  elsewhere in this reranker, and matching it keeps the mental model
  consistent.
- **Delete ADR-0076's splitting machinery outright.** Rejected: kept as a
  backstop for the truncation-under-shoot case (decode/re-encode drift,
  starvation with no `signature_head` fallback) and as the `split` escape
  hatch for rollback and for the decisive A/B itself — deleting it removes
  both.
- **Binary-search `derive_listwise_model_max_length` like the doc-cap
  solver.** Not applicable: that function solves a different, genuinely
  non-monotone problem (block boundaries shift with `model_max_length`, a
  document can overshoot a flush check by one entry) — ADR-0076's
  coarse-then-fine scan there is unchanged and still correct for the
  backstop path. `derive_listwise_doc_budget`'s own problem
  (`packed(cap) = sum(min(length, cap) ...)`) *is* monotone in `cap`, which
  is exactly why it gets a plain binary search instead.

## Consequences

- The three benchmark-locked pool-ordering optimizations
  (`merged_pool_policy`, `hop1_reserved_slots`, `graph_hop_window_cap`) keep
  operating inside the regime their locks were measured in, on every corpus
  density, not just the self-index.
- A benign, bounded body truncation replaces an unbounded ranking-variance
  perturbation on token-dense corpora — measured by the gate above, not
  assumed.
- `listwise_window_fit="split"` remains available as an explicit opt-out if
  a future corpus's real content is dense enough that even
  `signature_head` starves routinely; that would be a signal to revisit
  `_LISTWISE_MIN_DOC_TOKEN_ALLOWANCE` or `listwise_packed_token_budget`
  rather than to abandon the invariant.
- Out of scope for this ADR: a canon re-pin (separately owed), a
  `TD_Glossary_tox` golden set (the real measurement gap — the existing one
  is 21 queries against a tiny synthetic fixture, not reusable here), and
  jina-reranker-v3.5 (no `max_doc_length`/`max_query_length` levers, so this
  mechanism does not apply to it — already excluded by ADR-0076's gate).

## Re-evaluation triggers

1. The vendor checkpoint republishes with a different block-averaging
   mechanism (`modeling.py:247-269`) — the diagnosis above would need
   re-verification against the new mechanism.
2. `_LISTWISE_MIN_DOC_TOKEN_ALLOWANCE` routinely triggers the
   `signature_head` swap on a corpus where that representation loses too
   much ranking signal — would indicate the floor, not the invariant
   itself, needs revisiting.
3. A corpus is found where `signature_head` documents still can't fit one
   block at the minimum `listwise_packed_token_budget` — the split backstop
   would then be firing routinely rather than as a rare degradation, which
   is the condition ADR-0076's original mechanism was built for and this
   ADR's own gate should be re-run against.
