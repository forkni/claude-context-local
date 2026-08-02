# Architecture Decision Records

Index of all ADRs for claude-context-local. Each record captures a decision, its context, and
the alternatives considered — including declined options, which are as valuable as accepted ones
for avoiding re-litigating settled questions.

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-faiss-as-vector-index-backend.md) | Use FAISS as the vector index backend; do not migrate to turbovec | accepted | 2026-05-15 |
| [0002](0002-pyrefly-over-pyright.md) | Use Pyrefly as the type checker; do not adopt Pyright or Mypy | accepted | 2026-05-15 |
| [0003](0003-decline-llm-hierarchical-summaries.md) | Decline LLM-generated hierarchical summaries from NVIDIA/context-aware-rag | accepted | 2026-05-23 |
| [0004](0004-scoped-tracing-only-observability.md) | Scoped tracing-only OTel observability; rejected full OTel + metrics | accepted | 2026-05-23 |
| [0005](0005-no-di-container-module-singleton-state.md) | Prefer module singletons over DI containers for process-global state | accepted | 2026-05-29 |
| [0006](0006-thread-safety-of-module-singletons.md) | Thread-safety of module singletons via coarse locks | accepted | 2026-06-11 |
| [0007](0007-onnx-token-contract-and-activation-floors.md) | 2048-token ONNX contract and `max()` activation-cost floors | superseded (`72b6881`) | 2026-06-12 |
| [0008](0008-reindex-search-rwlock.md) | Reader-writer lock for auto-reindex vs. in-flight searches | accepted (amended 2026-07-27) | 2026-07-12 |
| [0009](0009-decline-parse-once-profile-chunk.md) | Decline parse-once tree reuse between the profile and chunk passes | accepted | 2026-07-20 |
| [0010](0010-centrality-memo-invalidation.md) | Centrality memo invalidation: version counter, not node/edge counts | accepted | 2026-07-27 |
| [0011](0011-listwise-reranker-doc-cap.md) | Cap JinaRerankerV3's listwise document budget at 1000 chars | accepted | 2026-07-28 |
| [0012](0012-curated-vocabulary-query-expansion.md) | Curated-vocabulary query expansion over PRF or LLM query rewriting | accepted | 2026-07-28 |
| [0013](0013-hop1-reserve-at-final-pool.md) | Reserve hop-1 winners at the multi-hop rerank window, not at hop-1 fusion | accepted | 2026-07-28 |
| [0014](0014-per-project-search-config-overrides.md) | Per-project search config overrides via `search_overrides.json` | accepted | 2026-07-29 |
| [0015](0015-remove-community-subsystem.md) | Remove the community-detection subsystem; cancel the Leiden migration | accepted | 2026-07-30 |
| [0016](0016-remove-dspy-eval-subsystem.md) | Remove the DSPy eval subsystem | accepted | 2026-08-01 |
| [0017](0017-adopt-mcp-sdk-v2.md) | Adopt MCP Python SDK v2 | accepted | 2026-08-01 |
| [0018](0018-retrieval-request-carries-effective-config.md) | `RetrievalRequest` carries the effective config; per-layer re-fetch removed | accepted | 2026-08-01 |
| [0019](0019-reject-intent-adaptive-fusion-weights.md) | Reject intent-adaptive fusion weights (measured, replicated, removed) | accepted | 2026-08-01 |
| [0020](0020-config-field-liveness-audit.md) | Config field liveness audit: wire the hardcoded, delete the orphaned | accepted | 2026-08-02 |

## Adding a new ADR

1. Copy the format of a recent record (title as H1 — no `ADR-NNNN:` prefix — then plain
   `Status:` / `Date:` lines, `## Context`, `## Decision`, `## Reasons` or `## Consequences`).
2. Number sequentially, zero-padded to 4 digits: `00NN-kebab-case-title.md`.
3. Add a row to the table above.
4. Link the ADR from `CHANGELOG.md` and/or `docs/VERSION_HISTORY.md` when the decision ships.
