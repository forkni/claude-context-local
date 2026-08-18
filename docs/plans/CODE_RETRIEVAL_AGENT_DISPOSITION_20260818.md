# Code retrieval agent disposition — Jain 2025 + targeted RAG-table transfer (2026-08-18)

Status: **disposition only — no production code changed, nothing ships default-on, no search-path
commit, no benchmark re-baseline**

Source paper (in `docs/plans/`): **Jain 2025**, *An Exploratory Study of Code Retrieval Techniques
in Coding Agents*, Preprints.org, `preprints202510.0924.v1.pdf`. Cross-referenced against a ~120-row
RAG-technique table (targeted — only rows hitting an open failure class or the context-cost axis).

Companion instrument: `scripts/benchmark/probe_context_cost.py` (Deliverable 2, read-only).

## Context

The paper compares 7 coding agents on one retrieval task in a 338-file repo. Its headline is not a
ranking — **all 7 agents completed the task** — it is the spread in what completion *cost*: 8,500
tokens (Aider) to 117,000 (Claude Code), a 14× range.

That axis — **context cost per resolved query** — is the one axis this project has never measured.
Every campaign in `evaluation/` gates on rank quality (MRR, recall@k, pool_hit_rate) plus latency
and VRAM. `evaluation/metrics.py` contains zero size/length/token math, every `per_query` row across
the canonical benchmark JSONs carries no size-related key, and
`scripts/benchmark/run_sscg_benchmark.py` explicitly passes `max_context_tokens: 0`, which disables
the *only* token estimator on the live path (`mcp_server/tools/search_orchestrator.py`'s Block H,
`_apply_source_order_and_budget`, `len(json.dumps(r)) // 4` per result).

This is not an oversight — `docs/plans/RESEARCH_BRIEF_RECALL_FIDELITY_20260814.md` §7 deliberately
parked the token-efficiency levers (Roadmap Track B: tree view, signature enrichment, two-stage
budget) as out of scope for that brief's mission. They were never rejected; they were never
measurable. Meanwhile the recall axis is closed (`evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md`:
every config-level lever measured-and-rejected), so this paper arrives pointed squarely at the one
open frontier.

Two structural facts, verified live via MCP before this document was written, make the exercise
concrete rather than academic:

1. **`search_code` returns zero source code.** `mcp_server/tools/result_view.py`'s
   `_format_search_results` emits coordinates only (`file`, `lines`, `kind`, `score`, `chunk_id`,
   optionally `name`/`summary`/`reranker_score`/`complexity_score`/`source`) and never reads
   `content`, `content_preview`, or `bm25_text`. The search payload is therefore very cheap (a
   handful of fields per result) — but it **externalizes** the cost: the caller must `Read` whole
   files to confirm a hit. That is exactly the whole-file-reading pattern the paper attributes to
   Claude Code's 117k-token run, and exactly what Aider's signature map is designed to avoid.
2. **PageRank is already computed, then discarded.** `graph/graph_queries.py` runs `nx.pagerank`
   over the full graph per query, but `GraphEnhancedConfig.centrality_alpha` is `0.0`
   (`search/config.py`), so the term contributes nothing to score (`search/centrality_ranker.py`).
   Aider's entire ranking mechanism runs in this codebase and its output is thrown away.

---

## §1 Paper claims → disposition

| # | Claim (Jain 2025) | Disposition |
|---|---|---|
| P1 | Task success ≠ differentiator; context cost is (14× spread across 7 agents) | **NEW axis** — never measured before this document; Deliverable 2 makes it gateable |
| P2 | Aider repo-map: tree-sitter → graph → PageRank → budget-fit signatures | **PARTIAL**: graph ✅ (`graph/graph_storage.py`, 19 producible edge types), PageRank ✅-but-discarded (`centrality_alpha=0.0`), signature view ❌ (§3 L3), budget-fit ❌ (§3 L4/no equivalent). **Granularity note**: Aider's graph nodes are *files* (paper appendix: "NetworkX MultiDiGraph where files are nodes and symbol references create weighted edges"); this project's graph is *chunk*-level — finer-grained, not a like-for-like gap |
| P3 | Personalization multipliers (chat 50×, mentioned 10×, query-match 10×) | **PARTIAL**: PPR exists (`search/graph_view.py`, ego-graph expansion) but is **rejected for recall** (2026-08-02, `evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md`); `expansion_mode="bfs"` stays default. Never evaluated for *cost*, where it measured ~15.8% faster with a smaller final rerank pool — a latency/cost finding, not a recall one, and not reopened by this disposition. **Correction**: the paper names a fourth multiplier this row omitted — well-named `snake_case`/`camelCase` identifiers, also 10× |
| P4 | Binary-search fit to a fixed token budget | **ABSENT**: `max_context_tokens` performs greedy whole-result truncation, default `0` (unbounded) — no binary-search-to-budget mechanism exists |
| P5 | mtime-keyed cache of the repo map | **SHIPPED equivalent**: merkle-DAG incremental indexer + persistent chunk-embedding cache serve the same purpose (avoid recomputing an unchanged repo's structure) |
| P6 | Cursor: semantic precision → selective reading (agent reads ~3 files, not the whole repo) | This is the mechanism the system already optimizes *toward* — but a coordinates-only payload enables selective **locating**, not selective **reading**. The gap between the two is P6/P8's cost driver |
| P7 | ~25.5k tokens of tool-inventory overhead before any retrieval happens | **MEASURED, and not a peer comparison**: the paper's 25.5k is Claude Code's *entire* tool inventory (system tools + optional MCP integration, 12.7% of context) — this project's schema is one component of such a budget, not an equivalent whole. Exact totals: the full 18-tool schema is 33,889 chars ≈ 8.5k tokens; the default-exposed 10-tool schema (`MCP_EXPOSE_ADVANCED_TOOLS` unset) is 22,377 chars ≈ 5.6k tokens. **Duplication, corrected**: 17 byte-identical 174-char `output_format` descriptions in `mcp_server/tool_registry.py` = 2,958 chars total, **2,784 redundant** — plus an **18th, 84-char variant** at `mcp_server/tool_registry.py:782` (`find_path`) that a naive hoist-to-constant would silently overwrite |
| P8 | Whole-file reading drives cost | Direct consequence of P6 — see `downstream_read_cost` in Deliverable 2 |
| P9 | RQ2: LSP-as-agent-tool underperforms; LSP *principles* work when reimplemented server-side | **VALIDATES current design** — this system already uses LSP as an offline resolver tier (`CallEdgeResolver` confidence 0.98, basedpyright), not as an agent-facing tool. No action; cited as external corroboration of the v0.15.0 architecture choice. Primary-source confirmation: Claude Code's live LSP tool calls failed outright ("githubConnector not found", "No references found for symbol: Connector") and cost *more* tokens (117k vs 108k) for zero measurable gain, while Aider's LSP-*principles*-reimplemented approach was the cheapest run of all seven (8.5–13k tokens) |
| P10 | Table 4 transparency taxonomy (query × file visibility × duration exposed to the agent) | **PARTIAL**: `source`/`score`/`reranker_score` are exposed per result; no dense-vs-BM25 attribution beyond the `source` tag, no rank-movement signal, no duration/latency field in the payload |
| P11 | Negative evidence matters (a zero-result search should still inform the agent's understanding) | **DEFECT, independently confirmed** — worse than the paper's own framing, which attributes negative-evidence use to Codex CLI's *observed technique* (§4.2, a qualitative single-agent note, not a cross-agent finding). This codebase's version is a measured contract gap: `mcp_server/output_formatter.py`'s `_to_compact_format`/`_to_toon_format` both drop any field whose value is `[]`/`{}`/`None`/`""` — under `compact` or `ultra` (the live default), an empty `results` list **vanishes from the payload entirely**, and `mcp_server/tools/search_orchestrator.py:501`'s `_build_response` never emitted a count field to fall back on in the first place. `mcp_server/guidance.py` is static English and does not compensate. Deliverable 2's `results_vanished_count` metric measures how often this fires |

---

## §2 RAG-table cross-reference (targeted)

Only rows that hit an already-open failure class or the context-cost axis were pulled forward; the
full ~120-row table was not re-litigated end to end.

**Keep as noted / already-actioned:**

- **CatRAG** (query-aware edge weighting) → maps onto the recorded literal-`0.0` `graph_hop` score
  gap. Note only — the merged-pool ordering seam this would touch is **permanently exhausted**
  (`project_graph_band_evidence_order_rejected_20260815`, `project_graph_hop_window_cap_ab_rejected_20260815`
  memory records): both named reopening directions closed, no config knob shipped. No further
  action.
- **RAGBoost** (retrieval-overlap deduplication) → maps onto the **aborted**
  `evaluation/DUPLICATE_CROWDING_PROBE_20260817.md`/`.json` work already sitting untracked in this
  repo. Duplicates are pure token waste under the cost axis even though they were being evaluated
  for recall — the probe harness exists (`scripts/benchmark/probe_duplicate_crowding.py`) but the
  investigation was stopped short; recorded here as a candidate to resume under the cost framing,
  not reopened by this document.
- **A-RAG** (hierarchical retrieval interfaces — coarse-to-fine navigation) → informs tool-surface
  *design* thinking (distinguish from the already-rejected `get_file_tree` proposal), not a metric
  or a build item.
- **SitEmb-v1.5** (situated/context-aware embeddings) → recall-axis territory (chunk representation
  choices, §8.5-adjacent), log-only; the recall campaign is closed and this document does not
  reopen it.

**Reject with reason:**

- **RECOMP / COCOM** (LLM-in-the-retrieval-loop compression) — requires a second LLM call inside
  the retrieval path, violating the project's single-4090/no-API-LLM operating constraint.
- **G-RAG** (GNN-based reranker) — requires offline model training; no training infrastructure or
  labeled-edge corpus exists for this to be a scoped build.

**Cited as external corroboration of existing verdicts (no new action):**

- *Answer Presence Drives RAG Rewriting Gains* → corroborates the ADR-0012 query-expansion
  rejection (gains require answer-presence conditions this project's queries mostly don't meet).
- *Beyond Semantic Similarity* → corroborates RQ1-adjacent findings already banked from the recall
  campaign (semantic similarity alone is an incomplete relevance signal; this project's hybrid +
  graph + rerank stack already compensates).

---

## §3 Ranked NEW levers (proposals only — pre-registered gates, nothing built)

Ranked by (measured headroom) ÷ (cost + risk), **re-derived after verification** — three premises
moved (L1's hoist saves zero wire tokens, L2's interleaved-vs-appended question is now answered,
L3 is cheaper than assumed) and the order below reflects that, not the original draft order.

### L5 — Explicit zero-result contract *(cheapest — was ranked 5th)*

Make "no results" machine-readable under all three output formats (verbose/compact/ultra) instead
of the field silently vanishing (P11). Verified **worse** than first described:
`mcp_server/tools/search_orchestrator.py:501`'s `_build_response` emits only `{"query", "results"}`
— there is no count field anywhere to fall back on. Under `ultra` (the live default) a zero-result
payload therefore carries no `results` key and no numeric zero, only the static prose
`system_message` (`mcp_server/guidance.py:11-14`). Drop sites, all confirmed:
`mcp_server/output_formatter.py:53-55` (`_to_compact_format`), `:136-138` (`_to_toon_format`),
`:102-104` (`_compact_dict`, nested). Nearly free — a formatter-level fix, not a scoring change;
`tests/unit/mcp_server/test_output_formatter.py` (826 lines) already exists to host the contract
test. Gated by serialization survival under all three formats, not a metric threshold.

### L2a — Schema-honesty half of the `ego_graph_enabled` contract *(new: split out of the original L2)*

Live-verified: a `k=3` call returned 11–12 results (2–3 hybrid, 8–9 `source:"ego_graph"`, 1
`multi_hop`) **even when the caller explicitly passed `ego_graph_enabled=false`**. Root cause,
pinned exactly: `search/effective_config.py:57` is a bare `if plan.ego_graph_enabled:` truthiness
guard with **no `else` branch** — `False` can only ever fail to enter the block, so the per-request
flag is structurally incapable of disabling anything. The schema advertises `default: False`
(`mcp_server/tool_registry.py:157-161`) against `EgoGraphConfig.enabled=True`
(`search/config.py:1046-1051`) — the two share the identical `flat_alias="ego_graph_enabled"`
string but gate different things. A **parallel lie** exists in the same file: the schema advertises
`output_format` `default: "compact"` in all 18 tool blocks, while `search_config.json` and
`OutputConfig.format` (`search/config.py:928-931`) both say `"ultra"`, and
`mcp_server/server.py:408-415` proves the config wins whenever a caller omits the argument — the
schema default is dead code on that path. **Gate:** advertised defaults match live defaults;
documentation/schema correction only, no behaviour change, zero retrieval risk.

### L3 — `include_signatures` on `search_code`, default off *(upgraded — cheaper than first assumed)*

Derive a signature-only view at query time from the persisted `bm25_text` field. **Verified
cheaper than the original draft assumed**: `bm25_text` is persisted at 100% coverage (2,527/2,527
rows on the live self-index, median 879 chars, max 65,463), is **already read back at query time**
today by the reranker (`search/neural_reranker.py:139`), and is passed through verbatim by the
result layer with no key filtering
(`search/hybrid_searcher.py:521-560` `get_by_chunk_id` → `search/result_factory.py:36-45,124-130`).
No reindex, no `INDEX_VERSION` bump. A plain-string signature extractor already exists in-repo:
`scripts/benchmark/probe_context_cost.py`'s `_extract_signature_estimate(text, max_lines=15)`
(~20 lines) — no tree-sitter node required, unlike the production `_extract_signature` methods
(`chunking/languages/python.py:73`, `base.py:614`, `glsl.py:567`), which need a parse node and
can't take a plain string. Two corrections to the original premise: no `signature` field is
persisted anywhere (0/2,527 rows — the hoped-for even-cheaper route is refuted, but moot given
`bm25_text`), and `mcp_server/tools/result_view.py:128-131` **already** emits a `summary` field
from `metadata["docstring"]` for module chunks — "coordinates only" is slightly overstated; there
is in-repo precedent for content-derived output fields. Explicitly **not** the already-rejected A4
`doc_representation_mode=signature_head` (changed reranker *input*, recall-CI-negative both
datasets); this is display-only, orthogonal to ranking. **Gate:** `gold_sufficiency`
(content-present, not just located) increases against a pre-registered `tokens_returned@10`
ceiling, **and** ranking is proved byte-identical across the change — the field must be purely
additive, never touching which results are chosen or their order.

### L4 — `find_connections` fan-out cap *(unchanged rank, evidence now measured)*

Output is unbounded today at every layer — no `limit`/`max_results` parameter exists in
`search/relationship_analyzer.py:177-195`, `graph/graph_queries.py:585-613`, or the handler
(`mcp_server/tools/search_handlers.py:365-420`; its only post-processing is `filter_ambiguous_edges`,
a confidence filter, not a count cap). Note `find_similar_code`'s `similar_code` path *is* already
capped (`relationship_analyzer.py:816-818`, `k=10`) — "unbounded" applies specifically to the
call-edge lists. **Measured worst case on the live self-index** (5,850 nodes / 25,547 edges):
**317 direct callers on `MetadataStore.get`** → 846 nodes at `max_depth=3` (14.5% of the whole
graph) → an estimated ~260 KB ≈ 72,000 tokens from a single call. Two qualifiers before sizing a
cap off that number: the tail is driven by bare-symbol conflation — `_node_variants`
(`graph_queries.py:627-643`) merges a dotted call target with its bare symbol, so
`MetadataStore.get` absorbs every unrelated `.get()` call in the project; and the real distribution
is far tamer — median 1 caller, p95 33, p99 42. A cap sized off 317 would be sized off a known
defect, not real fan-in; size it off the de-conflated distribution instead. **Gate:**
`scripts/benchmark/run_caller_recall.py` (the only harness that scores `find_connections` output,
per `evaluation/CONFIDENCE_EGO_AB_20260816.md`) shows no recall drop at the proposed cap.

### L1 — Tool-schema diet *(demoted from 1st — hoisting alone moves nothing)*

**Correction to the original premise**: hoisting the 17×-duplicated `output_format` description
(`mcp_server/tool_registry.py`) into a shared Python constant leaves `build_tool_list()`'s emitted
JSON schema **byte-identical** — the wire payload still carries all 17 copies regardless of how the
source stores the string. Only **shortening the text itself** moves the gate. Exact figures:
17 byte-identical 174-char copies (2,958 chars total, 2,784 redundant) across
`mcp_server/tool_registry.py:155,260,304,336,361,392,422,464,488,508,565,593,617,646,726,831,914`,
plus an **18th, non-identical 84-char variant** at `:782` (`find_path`) that a naive find-replace
hoist would silently overwrite. Realistic combined trim (shortened `output_format` text + the
`index_directory` dir-pattern trio — `include_dirs.description` is 1,537 chars, not ~1,600 as
first estimated, plus `exclude_dirs` 509 and `include_exclusive` 725) is ≈3,800 chars ≈ **11%** of
the 33,889-char full-schema total — the original **≥20% gate is unreachable by this mechanism**.
**Revised gate:** ≥10% reduction on the **10-tool live-default arm** (22,377 chars,
`MCP_EXPOSE_ADVANCED_TOOLS` unset) rather than the 18-tool arm — the advanced-tools flag already
gates 8 tools behind an opt-in env var, so a 34% reduction is effectively already shipped there.
Semantic equivalence required (same tool/parameter names, types, required-ness, enum values) on a
fixed call. Note: no module-level string-constant pattern exists yet in `tool_registry.py` to hang
a hoist on (only `ADVANCED_TOOLS`, `TOOL_REGISTRY`), though a shared-*value* precedent does —
`SearchMode` enum values consumed at `:98-99`, `:538-539`.

### L2b — Truncation half of the `ego_graph_enabled` contract — DEFERRED to a recall A/B *(new)*

The original L2 gate asked whether excess ego-graph results are appended after the top-k (safe
truncation) or interleaved into it (a recall change). **Answer: INTERLEAVED, definitively.**
`search/hybrid_searcher.py:914-916` does append at merge time, but a listwise re-rank
(`:789-802`, live path since `reranker.single_pass=False`) then re-sorts the **whole** merged pool
at `k=len(results)`, so ego rows can and do outrank hybrid rows (empirically: `ego_graph` at rank 3
outranking `hybrid` at rank 4 in a live call). Bounding `len(results) ≤ k` under this path would
therefore discard reranker-preferred results — **a recall change requiring a full A/B, not a
contract fix**. The real governor today is `hybrid_searcher.py:904-906`:
`max_ego = min(max_neighbors_per_hop * k_hops, original_k * 3)`, which fully explains every
observed count as `k + min(20, 3k)` — k=3→12 (11 after `dedupe_split_blocks`), k=5→20, k=6→24. The
only caller-facing bound that actually works today is `max_context_tokens`, and it defaults to `0`
(unbounded). Deferred pending a dedicated recall A/B; not gated in this document.

### L6 — Aider-style repo map — SPEC ONLY, do not build

Its natural gate ("beats the agent's own Glob+Read baseline on real task completion") requires an
agent-in-the-loop evaluation modality this repo does not have and the project's operating
constraints (single workstation, no orchestrated multi-agent task harness) don't currently support
building. Recorded here as an ingredient inventory (graph ✅ — though file-level in Aider vs
chunk-level here, see P2 — PageRank ✅-but-discarded, budget-fit ❌, signature serialization ❌) and
the missing piece (an agent-task evaluation harness), not opened as a build item.

---

## §4 Two standing corrections this exercise surfaces

- **CLAUDE.md's "63% token reduction" claim is misattributed, not merely unreproducible.**
  `docs/BENCHMARKS.md`'s own executive-summary table reports **MCP Only = 9% reduction**;
  **63% is the *Mixed* arm** (MCP tools + traditional file-reading tools combined), from a manual,
  hand-timed study (25 hand-written queries, Test Date December 21, 2025, measured via the Claude
  Code `/cost` command) — not an automated benchmark, and no script in this repo regenerates the
  number either way. `CLAUDE.md:66` ("Token reduction: 63% vs traditional file reading") and
  `CLAUDE.md:374` both attribute the *Mixed*-approach figure to the tool itself, which is the
  stronger, more actionable defect: the document should cite 9%, not 63%, if it wants to claim
  what MCP-only search achieves. Deliverable 2's `format_savings` metric measures the actual
  verbose→compact→ultra reduction on the current payload shape as a code-backed alternative; until
  CLAUDE.md is corrected to either the 9% MCP-only figure or a script-derived number, both cited
  figures should be read as point-in-time manual measurements, not regression-tested guarantees.
- **`mcp_server/output_formatter.py`'s "30–55% token reduction" docstring claim: now
  code-backed, not merely asserted.** No test or benchmark previously asserted this range.
  Deliverable 2's `format_stats`/`format_savings` metrics answer it directly — but only after a
  bug the probe's own Verification step 4 caught was fixed: `format_stats` originally
  byte-measured all three formats with a single plain `json.dumps(formatted, default=str)`, while
  `mcp_server/server.py`'s real wire path uses `indent=2` for `verbose` (bigger) and compact
  separators `(",", ":")` for `compact`/`ultra` (smaller) — undercounting verbose and overcounting
  compact/ultra, which biased `format_savings` low. Cross-checking the probe's per-query output
  against an independent standalone reconstruction of `mcp_server/server.py`'s dispatch (calling
  `handle_search_code` + `format_response` directly, sharing no code with the probe) surfaced the
  mismatch; the probe was corrected to replicate the real serialization exactly and now matches
  the standalone reconstruction byte-for-byte. On the one query measured end-to-end so far (Q01,
  k=10): `verbose=12492B`, `compact=8053B` (35.5% reduction), `ultra=5150B` (58.8% reduction) —
  consistent with, not contradicting, the docstring's 30–55% range. This is a single-query,
  fixed-substrate data point, not a corpus-wide validation; a full-corpus probe run is the natural
  follow-up but is out of this exercise's scope (read-only instrument delivery, not a campaign).

---

## §5 Corpus-limitation caveat

Both golden sets used throughout this project's benchmark history are **100% Python** — the 63-query
set and the 133-query expanded set alike carry zero gold chunks in Go, TypeScript/JavaScript, Rust,
C, C++, C#, or GLSL, despite the indexer supporting 9 languages across 27 file extensions. Measured
exactly: `evaluation/golden_dataset.json` has 77 raw queries (63 after excluding the 14 category-D
`find_connections`-shaped queries) / 235 distinct gold chunks / **67 distinct files**, extension
histogram `{'.py': 873}`; `evaluation/golden_dataset_expanded.json` has 147 raw queries (133 after
the same exclusion) / 351 chunks / **84 distinct files**, `{'.py': 1290}`. Zero non-Python gold in
either set. The
cross-system corpus captured 2026-08-17 (`evaluation/CROSS_SYSTEM_CORPUS_20260817.md` and
associated result files) is also pure Python. Every number this document and Deliverable 2 produce
is therefore a **Python number** — the v0.22.0 GLSL and v0.25.0 C++ chunking-parity work still has
**zero** retrieval-quality or context-cost evidence behind it. This caveat applies equally to every
disposition in §1–§4: none of it has been checked against a non-Python codebase.

---

## §6 Verification provenance

This document's §1–§5 were checked against three independent sources before the 2026-08-18 amendment:
(1) three parallel codebase-search agents, one per lever cluster (L1/L5, L2, L3/L4), each tracing
claims to exact file/line locations; (2) live MCP calls against this project's own deployed index
(`search_code`, `find_connections`) to reproduce the k-drift and coordinates-only findings directly,
not just read code; (3) the primary source itself, `docs/plans/preprints202510.0924.v1.pdf`
(`pdftotext -layout`, since `Read` cannot open it — no poppler-utils installed), to check P1–P11
against the paper's actual text rather than a second-hand paraphrase.

**What changed and why**: three claims did not survive contact with the code and are corrected
above rather than silently dropped — L1's hoist-to-constant mechanism cannot reach its own ≥20%
gate (re-specified against a smaller, reachable baseline); L2's appended-vs-interleaved blocker
question is now answered (interleaved, splitting L2 into a free honesty fix and a deferred recall
question); L3's cost estimate dropped once `bm25_text`'s persistence and existing read path were
confirmed. Four P-rows were tightened against the primary source (P2 file-vs-chunk graph
granularity, P3's fourth multiplier, P7's peer-comparison caveat, P9's concrete LSP-failure quotes,
P11's Codex-CLI-specific origin). §4a was strengthened from "unreproducible" to "misattributed"
after `docs/BENCHMARKS.md`'s own table showed the cited 63% is the *Mixed* arm, not MCP-only (9%).

**Open items this document does not close**: `scripts/benchmark/probe_context_cost.py` exists and
has been exercised on at least one query end-to-end (§4b's Q01 measurement, which also caught and
fixed a serialization-fidelity bug in the probe itself — `format_stats` originally used a plain
`json.dumps` for all three formats instead of replicating `mcp_server/server.py`'s real wire
encoding), but **no full-corpus run has been performed**, so L2/L3/L4's gates remain estimates from
static analysis and single-query spot checks, not corpus-wide measurements. No lever in §3 has been
built. Running the probe corpus-wide is the natural next step, gated behind the sequential-GPU
constraint (`cleanup_resources` first) and out of scope for this doc-only amendment.

---

## Not in scope

No change to `search/`, `mcp_server/`, or config. No ADR (L1–L6 are proposals, not decisions — none
has been built). No benchmark re-baseline. No full-corpus `probe_context_cost.py` run (single-query
spot check only, see §6).
