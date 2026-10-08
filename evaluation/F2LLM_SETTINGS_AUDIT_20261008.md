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
| Code to code | query instructed ("Retrieve the most relevant code snippet for the given code snippet"), passage raw | stored document vector reused | deviation, A/B E |

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

## Decision

Neither change is adopted ([ADR-0085](../docs/adr/0085-instructed-find-similar-flag-off.md)).
The E code ships flag-off (`instructed_similar=False`, env `CLAUDE_INSTRUCTED_SIMILAR`) with unit
tests, so it can be re-tested on another corpus without new plumbing. D left no code behind.

## Follow-up (not done)

`HybridSearcher.find_similar_to_chunk(rerank=True)` reranks with the 200-char `content_preview` as the
query rather than the full persisted `bm25_text`.
