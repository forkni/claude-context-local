# Decline LLM-generated hierarchical summaries from NVIDIA/context-aware-rag

Status: accepted
Date: 2026-05-23

We evaluated borrowing NVIDIA's two-level map-reduce summarization pattern
(per-file LLM summary → per-Louvain-community LLM summary, written back into
the vector store as retrievable chunks). We decided not to build this feature
for this project at this time.

## Context

NVIDIA/context-aware-rag's `functions/summarization/batch.py` generates LLM
summaries at index time and surfaces them through `summary_retriever.py`.
The pattern addresses a real gap: deterministic metadata summaries miss
architectural context that a language model can infer from source text.

The question was whether this gap matters for the current system's users and
whether it is measurable by the current evaluation setup.

## Decision

Do not implement LLM hierarchical summaries. Revisit when the evaluation
dataset includes GLOBAL-intent queries and a before/after benchmark is
possible.

## Reasons

**No measurable eval gap.** The golden dataset (`evaluation/golden_dataset.json`,
13 queries) covers categories A/B/C/D — all local/structural queries
(function discovery, sibling context, class overview, connections). There are
zero GLOBAL/architectural queries, even though the system has a real
`QueryIntent.GLOBAL` path (`search/intent_classifier.py`). The feature's
entire stated payoff is improvement on GLOBAL-intent queries. There is no
benchmark that can detect a regression or improvement here, so the ±0.5%
regression bar provides no protection against breaking something while also
providing no evidence of gain.

**LLM dependency.** Adding a local LLM provider abstraction (`llm/` package,
Ollama/llama.cpp/transformers providers) is a meaningful dependency surface.
The right time to absorb that cost is when there is a measured reason to.

**Existing summaries are sufficient for the current query mix.** The deterministic
summaries in `chunking/file_summarizer.py` and `graph/community_summarizer.py`
already produce structured summaries that feed the retrieval pipeline. Hit@5
is already saturated at 100%; the remaining headroom is in MRR (0.85) and
Recall@5 (0.65), and both gaps are on local/structural queries — not the
target of LLM summaries.

## Considered Options

- **Implement as planned** — rejected; no measurable value given the eval set.
- **Add GLOBAL-intent queries to eval first, then implement** — reasonable future
  path. Build the eval coverage, establish a baseline, then decide.
- **Implement behind a feature flag, skip eval** — rejected; introducing an LLM
  dependency blind is too much risk for unmeasurable gain.

## Consequences

The `llm/` package, provider abstraction, `LLMSummaryConfig`, and four new MCP
tools (`get_file_summary`, `get_community_summary`, `regenerate_llm_summaries`,
`configure_llm_summary`) are not built. The architecture improvement candidates
surfaced during this evaluation (see ADR-0004's documented findings) remain
available for future PRs informed by OTel latency data.
