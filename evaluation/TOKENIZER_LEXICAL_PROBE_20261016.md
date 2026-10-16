# Tokenizer / lexical-leg probe, 2026-10-16

Offline study of two tokenizer/code-RAG research notes against this implementation. Items 1-4 of the
ranked list were run. **Nothing here changes a default, writes an override, or reindexes anything.**

## Verdict (pre-registered)

**A twozero-dev `bm25_tokenizer = "case_gated"` override FAILS the gate: no headroom.**

The gate, fixed before any arm was scored, compared fusion-cut misses rescued minus created
against the `whole` arm:

| Criterion | Bar | twozero-dev result |
|---|---|---|
| Net, all queries | >= +2 | **0** |
| Sub-token stratum net | > 0 | **0** |
| Fusion-cut misses created, exact stratum | 0 | 0 (pass) |
| Python-gold slice net | not negative | 0 (pass) |

Two criteria fail on a technicality (0 is not >= +2 / > 0), but the cause is stronger than "no gain":
all 25 gold chunks are already in the fused pool under `whole` (0 fusion-cut misses, 0 leg misses),
so no lexical variant can rescue anything. The probe has no headroom to measure on.

## Method

- Probe `scripts/benchmark/probe_lexical_pool.py`, built on `evaluation/probe_harness.py`. Each arm is
  a BM25 index rebuilt from the project's persisted `bm25_docs.json`, swapped into
  `search_executor.bm25_index`; `ProbeSession.replay_legs` then runs the real legs at production depth
  (100) and fused-pool cut (30). Dense runs once per query and is shared. RRF is untouched.
- Arms: `whole` (live default), `additive`, `case_gated`; field arms `moved_w{0.5,1,2}` (body with the
  path/symbol augmentation stripped + w x a field-only index) and `dup_w{0.5,1,2}` (full docs + w x
  field). Field scores sum in-leg.
- **Fidelity: GREEN.** The `whole` arm through the swapped path reproduces the live BM25 and fused
  lists on all 124 queries of the 63q + 133q sets; dense legs identical across arms; 0 unstripped
  docs on every corpus.
- Gate vocabulary per `CONTEXT.md`: *fusion-cut miss* = gold in a raw leg but cut from the fused pool;
  *leg miss* = gold absent from both legs.
- Golden sets (graded 0-3 from source, pooled across arms, frozen 2026-10-16 after review, local only):
  `evaluation/twozero_lexical_golden.json` (25 queries: 10 sub-token, 10 NL, 5 exact) and
  `evaluation/voro_lexical_golden.json` (10: 4/4/2).
- Corpora: twozero-dev (32,539 chunks, 73% TouchDesigner `operator` chunks, camelCase), voro-engine
  (13,223 chunks, snake_case C++/Python control), this repo (3,187 chunks, 63q/133q sets).
  Index staleness was left as found (twozero-dev: 1 added / 40 modified files pending).

## Results

### twozero-dev (25 queries, all slice)

| Arm | in pool | fusion-cut miss | leg miss | net vs whole | BM25-only MRR | BM25 R@10 |
|---|---|---|---|---|---|---|
| whole | 25 | 0 | 0 | 0 | 0.654 | 0.947 |
| additive | 25 | 0 | 0 | 0 | 0.808 | 0.947 |
| case_gated | 25 | 0 | 0 | 0 | 0.801 | 0.907 |
| moved_w1 / w2 | 25 | 0 | 0 | 0 | 0.710 / 0.735 | 0.907 / 0.947 |
| dup_w0.5 / w1 / w2 | 25 | 0 | 0 | 0 | 0.842 / 0.841 / 0.791 | 0.907 / 0.920 / 0.920 |

Python-gold slice (18 queries): the same, every net 0. The sub-token stratum (10) sees the BM25-only
MRR rise 0.609 -> 0.770 (`additive`) and 0.752 (`case_gated`), but pool membership is unchanged. The gate
measures pool membership only; rank movement inside the pool was not gated. `moved_w0.5` is clearly worse
than `whole` on sub-tokens (0.267).

### voro-engine (10 queries, snake_case control)

Same shape: 10/10 in pool for every arm, net 0 everywhere. BM25-only MRR 0.593 (`whole`) ->
0.783 (`additive`) / 0.767 (`case_gated`); `dup_w*` 0.82-0.84; `moved_w2` 0.85.

### This repo (63q + 133q, 124 queries; informational, the default is not changing)

| Arm | in pool | fusion-cut miss | leg miss | rescued | created | net |
|---|---|---|---|---|---|---|
| whole | 114 | 9 | 1 | 0 | 0 | 0 |
| additive | 110 | 12 | 2 | 0 | 4 | **-4** |
| case_gated | 112 | 11 | 1 | 0 | 2 | **-2** |
| moved_w0.5 / w1 / w2 | 115 | 8 | 1 | 2 | 1 | +1 |
| dup_w0.5 / w1 | 115 | 8 | 1 | 2 | 1 | +1 |
| dup_w2 | 114 | 9 | 1 | 2 | 2 | 0 |

On snake_case Python, splitting identifiers hurts: `additive` loses 4 queries, `case_gated` 2
(`case_gated` is closer to `whole` because it leaves snake_case alone, exactly as designed, but the
mixed-case identifiers it does split still cost). The field arms net +1, below the +2 bar.

## Caveats

- The twozero/voro query sets are **easy**. They were drafted from identifiers in the corpus, the
  dense leg already finds every gold, and the baseline has no headroom. A negative probe on an
  easy set does not show `case_gated` cannot help on a harder, real query log.
- Small n: 25 and 10 queries; a +/-1 query difference is within noise. The repo's own sets (124)
  are the only ones large enough to see a few-query effect, and they are snake_case.
- BM25-only MRR rises sharply under sub-token splitting yet the fused outcome does not. This matches
  the structural fact that BM25 (weight 0.35, RRF k=100) can promote a dense-deep candidate but not
  introduce a dense-absent one.

## Item 3: composer truncation audit (`scripts/benchmark/probe_composer_truncation.py`)

`EmbeddingDocumentComposer.compose` bounds each document by characters (6,000), never tokens. The
probe re-chunks the indexed files (`--only-indexed`), composes each chunk at 6,000 chars and
unbounded, and counts real tokens per model tokenizer. `max_context` is the registry value;
F2LLM's live `max_seq_length` (40960) matches it.

| Corpus | chunks | truncated by 6,000-char budget |
|---|---|---|
| this repo | 2,855 | 125 (4.4%) |
| twozero-dev | 31,869 | 152 (0.5%) |

Of the truncated chunks, those that would have fit the model's full context untruncated (text lost
to a too-conservative char budget) versus those that exceed it anyway; and composed documents that
exceed `max_context` after the 6,000-char budget:

| Corpus | Model (max_context) | truncated, would fit | truncated, exceeds | composed > max_context | chars/token |
|---|---|---|---|---|---|
| repo | F2LLM (40,960) | 125 | 0 | 0 | 4.50 |
| repo | Qwen3 (32,768) | 125 | 0 | 0 | 4.50 |
| repo | BGE-M3 (8,192) | 110 | 15 | 0 | 3.52 |
| repo | EmbeddingGemma (2,048) | 39 | 86 | 1 | 3.84 |
| twozero | F2LLM (40,960) | 150 | 2 | 0 | 3.26 |
| twozero | Qwen3 (32,768) | 145 | 7 | 0 | 3.26 |
| twozero | BGE-M3 (8,192) | 116 | 36 | 0 | 2.59 |
| twozero | EmbeddingGemma (2,048) | 26 | 126 | 24 | 2.89 |

Composed-token percentiles (F2LLM): repo p50 344 / p90 954 / p99 1,386 / max 1,829; twozero p50 205 /
p90 543 / p99 1,198 / max 2,397.

Reading: for the deployed model (F2LLM-v2-0.6B) the 6,000-char budget is **conservative, never
loose**: no composed document comes near the context window (max 2,397 of 40,960 tokens), so there is
no silent model-side truncation. The cost is the other direction, but small: 0.5-4.4% of chunks lose
tail text to the char budget although they would fit. The conditional follow-up "budget =
min(token budget, model max)" would only recover that tail; it would matter for a small-context model
(EmbeddingGemma: 24 composed twozero documents exceed 2,048 tokens). It is **not** justified for the
deployed model on this evidence, and it is not built. Chars/token is 4.5 on prose/Python but only 2.6-3.3
on twozero's operator/TD-network text, which is why a fixed char budget is a weak proxy there.

Chunk-type token medians (F2LLM): repo `class` 1,148 and `split_block` 908 are the heavy types (and the
ones the budget bites); twozero `operator` p50 202, p90 520, max 1,573.

## Item 4: Recall@K-tokens and chars/token

Measured with `probe_context_cost.py` on this repo (133 queries, deployed-default routing).

- **chars/token.** `search_code` returns JSON coordinates, not code. cl100k counted **1.399x** the old
  `len(json.dumps(r)) // 4` estimate (406,263 vs 290,455 tokens; the earlier 2026-08-18 measurement
  was 1.387), i.e. about 2.86 chars/token. The `max_context_tokens` budget was therefore exceeded by
  about 40%. `_JSON_CHARS_PER_TOKEN = 2.85` (`mcp_server/tools/search_orchestrator.py`) now replaces
  the bare `// 4`, with `ceil` rounding. It is a constant, not a config knob (cl100k is only a
  proxy for the caller's tokenizer). Callers passing `max_context_tokens > 0` get fewer results; the
  budget is now honest. The probe's `production_heuristic` mirrors the constant, so
  `tiktoken_cl100k / production_heuristic` should read about 1.0 on the next run.
- **Recall@K-tokens** (gold chunk read before cumulative targeted-span cl100k tokens pass K, 133q):
  **2K = 0.752, 4K = 0.827, 8K = 0.895**, against recall@k=10 (`located_rate`) 0.940. About 4.5
  points of located golds cost more than 8K tokens to read, so a result-count metric hides a real
  cost tail. This is a new probe metric; the canon is not affected.

## Follow-ups, all gated on a user go-ahead

- **Per-project `case_gated` override on twozero-dev:** not recommended; the gate failed. If a harder
  or real query log shows sub-token queries missing at the pool cut, re-run
  `probe_lexical_pool.py` against it before any override. The override-survival fix (a `manual`
  block carried across pass 1 of `search/index_probe.py`, amending ADR-0014) is only worth building
  if that gate later passes; it is not built.
- **Field channel ("moved" doc format):** +1 net on this repo, below the +2 bar; adopting it would
  change the BM25 document format and need an `INDEX_VERSION` bump. Not recommended on this evidence.
- **Default flip, reindex of this repo, writing any override:** none done.
- **Composer budget (`min(token budget, model max)`):** not justified for the deployed model (above).
- **`CONTEXT.md`:** added "Case-gated analyzer". No ADR written (no project adopted it).

## Reproduce

```
export CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0
.venv/Scripts/python.exe -m scripts.benchmark.probe_lexical_pool --project-path <root> \
    --dataset evaluation/twozero_lexical_golden.json --json <out> --exclude-categories
.venv/Scripts/python.exe -m scripts.benchmark.probe_composer_truncation --project-path <root> \
    --only-indexed --json <out>
.venv/Scripts/python.exe -m scripts.benchmark.probe_context_cost --project-path <root> --json <out>
```

Code changes made (tested, not committed): `case_gated` analyzer in `search/bm25_index.py` +
`search/config.py` choices + `scripts/benchmark/bm25_tokenizer_ab.py` arm + unit tests;
`_JSON_CHARS_PER_TOKEN` in `mcp_server/tools/search_orchestrator.py` + boundary test; Recall@K-tokens
in `scripts/benchmark/probe_context_cost.py`; `CONTEXT.md` glossary entry.
