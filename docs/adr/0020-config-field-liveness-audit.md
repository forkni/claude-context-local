# Config field liveness audit: wire the hardcoded, delete the orphaned

Status: accepted
Date: 2026-08-02

We audited `search_config.json` / `search_config.json.example` against the codebase in
both directions. Schema parity was already perfect (both files carried all 129 fields of
the `SearchConfig` tree, zero stray, zero missing). Liveness parity was not: 13 of those
129 fields had no production reader. This ADR records the audit, the rule applied to
resolve it, and the resulting 7-wire / 6-delete split. A 14th, unrelated finding — an
ego-graph config reset bug — is fixed alongside it.

## Context

`to_dict()` (`search/config.py`) generates both JSON files mechanically from the
`SearchConfig` dataclass tree via `dataclasses.asdict`, so structural drift between the
schema and the shipped configs is not possible by construction. What *is* possible is a
field that round-trips cleanly — serialized, aliased in `_FLAT_KEY_ALIASES`, in some cases
settable over MCP — while no code path actually reads it. Verification for each field used
three independent methods: semantic search over the indexed codebase, `find_connections`
call-graph lookup for zero-caller confirmation, and exhaustive grep. All three had to agree
before a field was classified as dead.

The resolution rule: **if the method the field configured is actually gone from the
codebase, delete the config option; if the code path is live and merely hardcoded, wire
it.** Applied to the 13 dead fields, this produced a clean 7/6 split with no ambiguous
cases — every field mapped to exactly one of "the driver still runs, unconditionally, with
a value equal to the field's default" or "the driver was deleted in a prior refactor and
nothing calls the field's consumer."

## Decision

Wire the 7 live-but-hardcoded fields to their existing call sites, using the current
hardcoded value as the wired default so shipped behavior does not change. Delete the 6
fields whose driver is gone, plus the dead code that only they exercised. Fix the
ego-graph config reset as an adjacent, unrelated correctness bug found during the audit.

### Wired (Deliverable 1)

`embedding.query_cache_size`, `search_mode.min_bm25_score`,
`performance.max_parallel_workers`, `intent.default_intent`, `ego_graph.deduplicate`,
`parent_retrieval.include_parent_content`, `observability.capture_query_text`. Every wired
value equals the hardcode it replaces, so this shipped with zero behavior change on the
default config — confirmed by full unit suite (5,523 passed) and MCP tool-surface checks.
`capture_query_text` is the one wiring with a privacy dimension: it was **fail-closed**
before wiring (query text never emitted regardless of the setting), so wiring it turns a
false-off into a real off; default stays `false` in both JSON files, and the sink degrades
to a no-op when OTel is disabled (`_NoopSpan.set_attribute`).

### Deleted (Deliverable 2)

`chunking.min_chunk_tokens`, `chunking.max_merged_tokens`, `chunking.token_estimation`,
`chunking.size_method`, `search_mode.enable_result_reranking`,
`parent_retrieval.max_parents_per_result`.

The four chunking fields governed the greedy-merge pass and its token-budget heuristics.
The pass's driver, `_greedy_merge_small_chunks`, was already removed
(`chunking/languages/base.py` reads `# No greedy merge - raw AST chunks returned`
where it used to run); this audit found and removed its two remaining orphans:

- `estimate_tokens()` (`chunking/languages/base.py`) — zero direct callers via
  `find_connections`; its only importers were `tests/unit/chunking/test_token_estimation.py`
  and `tests/unit/chunking/test_greedy_merge.py`, both deleted with it.
- `_create_merged_chunk()` (`chunking/languages/base.py`) — zero direct callers via
  `find_connections`; survived only as a test target, hence the risk that a casual grep
  would read it as live.

`size_method` was never read by anything (a superseded name for `split_size_method`, which
stays — see the collision hazards below). `enable_result_reranking` was schema-only in
three places; RRF fusion is unconditional and neural reranking is gated by
`reranker.enabled` / `reranker.single_pass`, so wiring it would have created two switches
for one behavior. `max_parents_per_result` guarded multi-level ancestor retrieval, which
does not exist — `parent_chunk_id` is a single `str | None` linking a method to its
enclosing class, one level only; the field could never exceed 1 in practice and had no
hardcode to replace, unlike its wired sibling `include_parent_content`.

Two independent measurements had already reached this conclusion before this deliverable
acted on it: a semantic search for chunk-merging code returned only a dead benchmark
script, and `evaluation/CHUNKING_CORPUS_ANALYSIS_20260728.md` states outright that
`min_chunk_tokens`, `max_merged_tokens`, `size_method`, and `token_estimation` are inert.

**Collision hazards.** Two live neighbours sit directly beside deleted fields in every
touch point (dataclass, `_FLAT_KEY_ALIASES`, both JSON files) and were deliberately left
untouched, then re-confirmed live after the deletion:

- `split_size_method` (beside `size_method`) — still read at four sites in
  `chunking/languages/base.py` and written by both `start_mcp_server.cmd` interactive
  handlers.
- `estimate_characters()` (defined immediately after the deleted `estimate_tokens()`,
  near-identical signature and docstring shape) — still called from
  `_calculate_accumulated_size`, `chunking/repo_profiler.py`, and its unit test.

**Index probe re-key.** `search/index_probe.py` carried a `ProbeRule` keyed
`"chunking.max_merged_tokens"` — a live, useful `kind="observation"` rule that fires when
more than 15% of chunks are `split_block` fragments, whose own `reason_fn` message already
named `max_split_chars` / `max_chunk_lines`, not the key it carried. Re-keyed to
`"chunking.max_chunk_lines"` rather than deleted. Not re-keyed to
`"chunking.max_split_chars"`: that would collide with the existing rule already using that
key, and `run_rules()` writes `result.reasons[rule.key]` — a collision would silently
overwrite one rule's finding with the other's. `value_fn` is `None` on this rule, so no
auto-tune override path was affected. The corresponding test assertion in
`tests/unit/search/test_index_probe.py` moved to the new key; two unrelated occurrences of
the same string, in a synthetic `ProbeResult` fixture exercising the write-overrides
formatter, were left alone — they are arbitrary text, not references to the real rule.

**MCP tool surface.** `token_estimation` was the one dead field users could actually set —
`handle_configure_chunking` reached it via `apply_config_patch` and persisted it through
`save_config`. Removed from `_CHUNKING_FIELDS` / `_CHUNKING_ECHO`
(`mcp_server/tools/config_handlers.py`), the schema property and description text in
`mcp_server/tool_registry.py`, and the three dependent test sites in
`tests/unit/mcp_server/test_config_handlers.py`. Confirmed live post-deletion: a direct
async call to `handle_configure_chunking` with a stray `token_estimation` key present
silently ignores it (the field-map pattern never reads keys absent from its own tuple) and
still patches `max_chunk_lines` correctly.

**Dead-code and doc cleanup.** `docs/MCP_TOOLS_REFERENCE.md` (parameter list and detailed
section) and `.claude/skills/mcp-search-tool/references/advanced-features.md` had their
`token_estimation` references removed. Historical records
(`CHANGELOG.md`, `docs/VERSION_HISTORY.md`, `evaluation/*.md`, the corpus-stats JSON) were
left as-is — they document what was true at the time, not the current schema.
`config/intent_anchors.yaml`'s `"find function estimate_tokens"` local-intent anchor
phrase was deliberately left alone: the symbol name is incidental to the phrasing, editing
an anchor shifts the semantic intent classifier, and retuning the anchor set is its own
benchmarked change, not a side effect of a config cleanup.

### Ego-graph config reset (Deliverable 3)

`mcp_server/tools/search_orchestrator.py` rebuilt `EgoGraphConfig` from three fields
whenever ego-graph was switched on, discarding every other configured value — including
`expansion_mode` and `ppr_alpha`, making the Personalized-PageRank branch unreachable from
`search_code` even though the PPR implementation is real, tested, and reachable in
isolation. Fixed with `dataclasses.replace` over the per-request `mutable_config()` copy,
preserving all fields not explicitly overridden. No-op on the shipped config today (both
JSON files ship the dataclass defaults for the untouched fields); it stops future
configuration from being silently thrown away, and preserves the newly-wired
`ego_graph.deduplicate` value across ego-graph searches.

## Reasons

**Forward and backward compatibility were structural, not incidental.** `_build_subconfig`
silently drops unknown keys when constructing a dataclass from a JSON dict, so a
`search_config.json` or per-project `search_overrides.json` still carrying any of the 6
deleted keys loads with zero warnings and zero errors — verified directly by loading a
synthetic old-style config containing all 6 removed keys through `SearchConfigManager` and
confirming both a clean load and, via `hasattr()`, genuine absence of the attributes on the
resulting dataclass.

**No reindex is required.** None of the 6 deleted fields ever influenced a chunk boundary
in the current pipeline (their driver was already gone); `INDEX_VERSION` stays at 4.

**Schema parity re-verified after the cut.** `SearchConfig().to_dict()` against both JSON
files: exact match at 123 fields across 14 sections (down from 129 by exactly the 6
deleted), zero missing, zero stray, in both directions, both files.

## Corrections to the originating plan

Two things surfaced during execution that the originating plan did not anticipate.

**`tiktoken` was not removed from `pyproject.toml`.** The plan's premise was that
`estimate_tokens()` was `tiktoken`'s only importer, making the dependency droppable once
that function was deleted. A repo-wide grep found a second, independent, functioning
importer: the `TokenCounter` class in `scripts/benchmark/analyze_chunking_corpus.py`
(unrelated BPE token counting for benchmark reporting, not the deleted merge subsystem).
`tiktoken` stays a direct dependency.

**Two scope extensions, both self-identified during verification, not listed as touch
points in the plan:**

- `search/graph_integration.py`'s `SEMANTIC_TYPES` tuple carried a comment on the `"merged"`
  node type attributing it to `LanguageChunker._create_merged_chunk` — now factually wrong
  since that method was deleted. The node type itself stays (backward compatibility with
  any pre-existing indexed chunks carrying that node type from earlier merge-subsystem
  experiments); only the comment was corrected.
- `start_mcp_server.cmd`'s chunking-menu "Invalid choice" guard clause still listed
  `chunk_choice=="B"` after the `B`-choice handler (the token-estimation write) had already
  been removed — meaning selecting `B` silently no-op'd (skipped both the deleted handler
  and the invalid-choice error) instead of prompting an error. Fixed by dropping the
  dangling clause and correcting the error message and the menu prompt hint text from
  "0-9, A-F" to "0-9, A, C-F" to reflect the now-gapped letter range.

## Residual observations (not fixed here)

1. `scripts/benchmark/analyze_chunking_corpus.py`'s `simulate_merges` is already broken
   independently of this work: it raises `ImportError` importing
   `chunking.community_remerge` (deleted with the community subsystem, ADR-0015) before it
   would also hit an `AttributeError` calling `_greedy_merge_small_chunks` (deleted
   earlier still). It cannot run today. Repairing or retiring it is out of scope for this
   audit.
2. `start_mcp_server.cmd`'s "Configure Chunking Settings" menu has pre-existing, unrelated
   breakage of its own, predating this audit: both "Current Settings" status-display
   one-liners, and interactive handlers `1`–`5` (community detection, community merge,
   community resolution), reference `cfg.chunking.enable_community_detection`,
   `enable_community_merge`, `community_resolution`, and `enable_community_summaries` —
   none of which exist on `ChunkingConfig` any more. ADR-0015 removed the community
   subsystem and explicitly deferred config-surface removal to a "follow-up change"; that
   follow-up never touched this file. Selecting any of choices `1`–`5`, or reaching either
   status display, raises `AttributeError` today. Out of scope for this audit (a
   config-surface cleanup that belongs to ADR-0015's follow-up, not this one) but recorded
   here since it was directly observed while verifying the `token_estimation` removal in
   the same menu.
3. `default_k` divergence: `search_config.json` sets `search_mode.default_k: 7` and
   `search_code` honors it, but `handle_find_similar_code` hardcodes `k = arguments.get("k",
   4)` behind a comment claiming alignment with `default_k=4` — already stale before this
   audit. Not fixed here; changing `find_similar_code`'s default `k` would move the
   F-via-similar benchmark view and needs its own measurement.
4. `QueryEmbeddingCache.__init__` treats `max_size <= 0` as an explicit disable. Before
   Deliverable 1, `"query_cache_size": 0` in a config file looked like a supported
   off-switch and did nothing (the field was never read); after wiring, it works as
   documented.
5. `config/intent_anchors.yaml`'s `estimate_tokens`-naming anchor phrase now names a deleted
   symbol. Deliberately left alone (above); already flagged as a non-matching anchor in
   prior query-expansion evaluation. Retuning the anchor set is its own benchmarked change.

## Verification

- Lint/format clean (`check_lint.sh` / `fix_lint.sh --modified-only`).
- Targeted config + chunking suite: 509 passed, 1 skipped.
- Full unit suite: 5,523 passed, 2 skipped — count drop from the pre-audit baseline
  matches exactly the two deleted test files, no other regression.
- Schema parity: 123/123 fields, both JSON files, both directions.
- Backward compatibility: synthetic old-style config with all 6 deleted keys present loads
  clean, no warnings, attributes genuinely absent post-load.
- MCP tool surface: `token_estimation` absent from `configure_chunking`'s schema and echo;
  a live call with the stray key present ignores it and still patches remaining fields.
- Startup script: `start_mcp_server.cmd` chunking-menu handler letters now run
  `1`–`9`, `A`, `C`–`F` with no dangling reference to the removed `B` handler; the
  surviving `split_size_method` write handlers (`characters` / `lines`) are unaffected;
  the two pre-existing community-field crash sites are unrelated pre-existing breakage
  (residual observation 2), not a regression introduced here.

## Out of scope

`min_chunk_tokens` / `max_merged_tokens` are deleted, not reimplemented — restoring a merge
pass would reopen a decision already made on measured results (sibling merge NEUTRAL,
community merge REJECTED). No benchmark-validated value changed as part of this audit.
Both JSON files keep their two intentional `model_name` divergences (embedding/reranker
VRAM tiering), which were never part of the liveness question this ADR answers.
