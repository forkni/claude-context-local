# Instructed find_similar ships flag-off; F2LLM query wording unchanged

Status: accepted
Date: 2026-10-08

## Context

An audit of our F2LLM-v2 settings against the paper and its public training data found the core
settings correct. Two off-distribution choices remained: (D) our NL query instruction is a paraphrase of
the trained cosqa wording, and (E) `find_similar_to_chunk` compares the anchor's stored document vector
with other document vectors, whereas training paired code to code with an instructed query and a raw
passage.

## Decision

- Keep the NL `query_instruction` ("Retrieve source code implementations matching the query").
- Ship E as `EmbeddingConfig.instructed_similar` (default `False`, env `CLAUDE_INSTRUCTED_SIMILAR`), backed
  by a `code2code_instruction` field on the three F2LLM registry entries, `CodeEmbedder.embed_code_query`,
  and a `query_embedding` parameter on `CodeIndexManager.get_similar_chunks`. Default behaviour is
  unchanged. It needs the anchor's persisted `bm25_text` (hybrid-path indexes) and falls back to the
  stored vector otherwise (missing text, a truncated preview-only text, or an embedder error).
- `code2code_instruction` is the xCodeEval Code2Code string "Retrieve similar code given the
  following code". The first E leg used the CodeSearchNet-CCR string, a prefix-to-continuation task
  that was misattributed to code2code (corrected in 30320509).

## Evidence

Same gate as ADR-0084 (no paired CI excludes 0 negatively; MRR or R@20 improves), all on
F2LLM-v2-330M + gte:

- D failed: it lowered 133q R@20 by 0.010 (CI [-0.021, -0.002]). The CI excludes 0 only because 4
  movers share a sign (sign test p about 0.125), so it is a fragile tie.
- E1 failed with the wrong (CCR) instruction: fsim MRR -0.026 (CI [-0.056, -0.002]).
- E2b, with the corrected instruction, is a null: fsim MRR +0.0025 (CI [-0.0016, +0.0091]), R@10 and
  R@20 unchanged, 2 of 63 queries moved. The gate is met on paper, but there is no measurable benefit.

Tables and the diagnosis: `evaluation/F2LLM_SETTINGS_AUDIT_20261008.md`.

## Consequences

- Matching the training distribution did not beat our retrieval-tuned wording on this corpus. The result
  is one Python-heavy repo and the 330M only; the 0.6B was not tested here.
- The flag costs one extra embedder call per find_similar when enabled; cached per anchor document.
  With no measured gain, the default stays off.
- With the flag on, `compose()` re-reads the anchor's file from disk, so the probe can drift if the
  file changed since indexing.
- Revisit E on a different corpus or the 0.6B before flipping the default.
