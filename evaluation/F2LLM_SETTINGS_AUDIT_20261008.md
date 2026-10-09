# F2LLM-v2 settings audit and two instruction A/Bs (2026-10-08)

Sources: the paper (arXiv 2603.19223), the Hub sentence-transformers configs, the
`codefuse-ai/F2LLM` training repo, and 6 shards of the public `codefuse-ai/F2LLM-v2` training set
(cosqa, csn_ruby, csn_ccr_ruby, xcodeeval nl2code and code2code Perl, stackoverflowdupquestions).

## Part 1: settings verdict. Core settings correct

| Item | Paper / card / training data | Ours | OK |
|---|---|---|---|
| Pooling | EOS last-token | ST `1_Pooling` lasttoken as shipped | yes |
| EOS | tokenizer post-processor appends `<\|im_end\|>` | same tokenizer | yes |
| Normalize / score | Normalize, cosine | ST Normalize + `normalize_L2` + IP index | yes |
| Query template | `Instruct: {task}\nQuery: {q}` | `_format_query_text` (custom mode) | yes |
| Double prefix | n/a | `prompt_name` only in prompt_name mode | yes |
| Documents | raw; 0 of about 60K sampled code passages instructed | raw, no passage prefix | yes |
| NL to code wording | about 20 paraphrases, e.g. "Retrieve relevant code snippets for the given query" | "Retrieve source code implementations matching the query" | paraphrase, A/B D |
| Length / padding | mask-aware lasttoken; trained 1024 to 2047+EOS | composer output at most 6000 chars | yes |
| dtype | bf16 | bf16 on CUDA | yes |
| Code to code | xCodeEval Code2Code pool: query instructed ("Retrieve similar code given the following code"), passage raw. (The CodeSearchNet-CCR string "Retrieve the most relevant code snippet for the given code snippet" is a prefix-to-continuation task, not similar-code.) | stored document vector reused | deviation, A/B E |

The registry's `prompt_name: "query"` is dead in custom mode (it would select the Hub's generic prompt).

## Part 2: the two instruction A/Bs

Baseline B1 = F2LLM-v2-330M + gte reranker, 243 files / 3146 chunks, `--deterministic-gpu`, one run
per view. The harness `[CONFOUND]` flag fires only on `git_sha` (HEAD moved from 66541d06 to
2eea9bc6 for the registry entry); the index, model and corpus are identical.

### Leg D: trained NL query wording

`query_instruction` = "Instruct: Retrieve relevant code snippets for the given query\nQuery: ", all
three views, paired deltas D1 minus B1 (95% bootstrap CI):

| View | MRR | R@10 | R@20 |
|---|---|---|---|
| 63q | +0.0038 [-0.0001, +0.0102] | -0.0093 [-0.0238, +0.0000] | -0.0040 [-0.0119, +0.0000] |
| 133q | +0.0011 [-0.0028, +0.0050] | -0.0044 [-0.0113, +0.0000] | **-0.0100 [-0.0213, -0.0019]** |
| fsim | +0.0038 [-0.0001, +0.0102] | -0.0093 [-0.0238, +0.0000] | -0.0040 [-0.0119, +0.0000] |

**FAIL.** 133q R@20 has a CI that excludes 0 negatively, and MRR is a tie. The existing wording stays.
Only 5 to 12 queries moved per view, so the effect is small in both directions.

### Leg E: instructed find_similar (`EmbeddingConfig.instructed_similar`)

The anchor's composed document is re-embedded as an instructed code-to-code query instead of
reusing its stored document vector. fsim only, since the other views never call find_similar.
E1 minus B1:

| MRR | R@5 | R@10 | R@20 | Hit@5 |
|---|---|---|---|---|
| **-0.0258 [-0.0562, -0.0016]** | +0.0108 [-0.0175, +0.0428] | +0.0084 [-0.0101, +0.0335] | +0.0084 [-0.0101, +0.0335] | 0.0000 |

8 of 63 queries moved (3 lost 0.5 MRR, 1 gained 0.2). **FAIL.** The MRR CI excludes 0 negatively.
Recall rose slightly, inside its CI, so the probe changes which neighbours rank first without finding
more of them. With only 63 queries and 8 moved, this is a weak signal either way.

**E1 used the wrong instruction.** It embedded the anchor with the CodeSearchNet-CCR string, which
trains prefix-to-continuation retrieval, so the probe promoted callers and collaborators over
structural siblings (Q98 `_generate_cache_key`, Q95 `_search`, Q94 relationship-edge helpers).
The similar-code task is xCodeEval Code2Code ("Retrieve similar code given the following code"),
fixed in 30320509.

## Gate-fail diagnosis

- **D is a fragile tie, not a regression.** On 133q, R@20 moved on 4 of 133 queries (Q12, Q102, Q126,
  Q127), each by -1 gold. The bootstrap CI excludes 0 only because all four movers share a sign; the
  normal CI is [-0.020, +0.0001] and the sign test gives p about 0.125. MRR moved on 11 queries in
  mixed directions. The decision to keep the current wording stands.
- **E diluted.** Only the 9 F items call find_similar, inside a 63-item paired CI. F-only E1 vs B1:
  MRR 0.566 to 0.385 (+1/-7, sign p 0.07), R@20 0.599 to 0.658 (+2/-1).
- **Primary-MRR artifact.** MRR scores against `expected_primary` (`evaluation/metrics.py`). In Q70,
  Q71 and Q96 the new top-1 is gold but secondary; in Q70 all five top results are gold and MRR still
  halves. Against the full `expected` set, F-only MRR is 0.824 to 0.722 for E1.

## Leg E2: corrected instruction (xCodeEval Code2Code)

Same procedure as E1 (fsim only, 330M + gte, `CLAUDE_INSTRUCTED_SIMILAR=1`, one run), compared with B1.
Peak VRAM 4.24 GB, 243 files / 3146 chunks, `[CONFOUND]` on `git_sha` only, ~7.0 GB free at start.

**E2 had a bug in the probe guard, so it was re-run as E2b.** The step-1 hardening skipped the
instructed probe whenever `bm25_text == content_preview`. A chunk of 200 characters or fewer has
`content_preview` equal to its full text, so 391 of 3146 chunks (12%) were wrongly skipped. The guard
now fires only for a truncated preview (more than 200 chars). E2 and E2b agree on every headline
number (MRR +0.0025, R@10 and R@20 0.0000), so the bug did not change the verdict.

E2b minus B1 (95% bootstrap CI):

| MRR | R@5 | R@10 | R@20 | Hit@5 |
|---|---|---|---|---|
| +0.0025 [-0.0016, +0.0091] | +0.0040 [-0.0119, +0.0238] | +0.0000 [0, 0] | +0.0000 [0, 0] | 0.952 to 0.968 |

Only 2 of 63 queries moved: Q94 up (dMRR +0.190), Q97 down (dMRR -0.033). F-only (n=9): MRR 0.566 to
0.583 (+1/-1, sign p 1.00), R@10 and R@20 0.599 unchanged, nDCG@10 graded 0.509 to 0.520 (+4/-2,
p 0.69), MRR against the full `expected` set 0.824 to 0.806.

The gate is met on paper (no CI excludes 0 negatively, MRR nominally up), but the effect is null:
the corrected instruction removes E1's damage and adds no measurable benefit.

## Decision

Neither change is adopted ([ADR-0085](../docs/adr/0085-instructed-find-similar-flag-off.md)).
The E code ships flag-off (`instructed_similar=False`, env `CLAUDE_INSTRUCTED_SIMILAR`) with unit
tests, so it can be re-tested on another corpus without new plumbing. D left no code behind.
E2b does not change that: a null result does not justify an extra embedder call per find_similar.

## Follow-up (not done)

`HybridSearcher.find_similar_to_chunk(rerank=True)` reranks with the 200-char `content_preview` as the
query rather than the full persisted `bm25_text`.
