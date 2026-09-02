# Config liveness audit: 124/124 fields live, five defects fixed

Status: accepted
Date: 2026-08-06

> The 124/124 count is this round's point-in-time measurement, not a live invariant — the field
> count has grown since (config fields are added over time). Do not treat this title as the
> current count; the always-current figure is `dataclasses.fields()` walked over
> `SearchConfig._SUBCONFIG_TYPES`, ratcheted by
> `test_section_docstring_field_counts_match_dataclasses_fields`
> (`tests/unit/search/test_config_field_liveness.py`). See ADR-0042 for why this repo publishes
> pointers to derived counts rather than pinning raw numbers in prose.

## Context

Two questions were asked: (1) are `search_config.json` and `search_config.json.example` in
sync except model params, and (2) is every `search_config` field actually connected to
production code, not dead.

**Q1 was already answered by existing CI, not this round.**
`test_example_config_covers_full_dataclass_surface`
(`tests/unit/search/test_search_config.py`) already enforces bidirectional key parity across
all 124 fields *and* value equality against dataclass defaults, exempting exactly
`embedding.model_name`/`reranker.model_name` per ADR-0022's Phase 2. Verified independently
this round (line diff, semantic key-set/order comparison, dataclass-registry comparison): 124
keys on both sides, identical section/field order, zero orphans either direction, the two
sanctioned exceptions and nothing else.

**Q2 needed a real audit.** ADR-0022's `spec()` liveness ratchet is explicitly not one — its
own text states a bare-name grep finds a "hit" for all 124 fields, including the 13 fields
ADR-0020 had proved dead, so the ratchet can only freeze a result, never produce one. "A
future liveness question still needs ADR-0020's three-method audit" (semantic search +
`find_connections` zero-caller confirmation + exhaustive grep, all three agreeing). That audit
was run across all 124 fields in 14 sections, with every load-bearing claim additionally
verified against the live MCP index (`search_code`/`find_connections`) before this ADR was
written, per this repo's search-first protocol.

## Decision

### Audit result: zero dead fields

Every one of the 124 fields has a confirmed production reader at a real decision point.
ADR-0020's cleanup held, and ADR-0020 residual observation #2 (the `start_mcp_server.cmd`
community-field `AttributeError`) is independently discharged. No field was deleted, renamed,
or reclassified as dead by this round.

The audit surfaced five defects — none on the search path, so no benchmark re-pin is
required — plus verified doc drift.

### D1 — `performance.prefer_gpu` UI lie

Exactly one production read (`embeddings/embedder.py:1286`), where it co-gates *dynamic batch
sizing* only; the `else` branch falls back to static `embedding.batch_size`, and CUDA is used
regardless of this flag's value. `start_mcp_server.cmd` claimed "GPU acceleration uses CUDA
for faster embeddings and search operations" and echoed "Enabling/Disabling GPU acceleration"
— disabling it never stopped CUDA use. Fixed by rewording the `:configure_gpu_acceleration`
explanation and both enable/disable confirmation echoes to state the true effect (dynamic
batch sizing derived from measured free VRAM vs. the fixed `embedding.batch_size`). The
menu-7 label itself was left unchanged — that menu genuinely covers VRAM caps, bf16/fp16, and
dynamic batching, so "GPU acceleration" is a fair category name; only the submenu text lied.

### D2 — `reranker.batch_size`/`instruction` construction-baked but untagged

`search/reranking_engine.py`'s `create_reranker(...)` reads six config values in one call;
three (`doc_max_chars`, `listwise_doc_max_chars`, `listwise_dtype`) already carried
`spec(construction_baked=True)`, but `batch_size` and `instruction` did not, despite the
identical read site — the swap branch rebuilds only on a `model_name` change. Consequence:
`evaluation/arm_overrides.py::requires_rebuild()` returned `False` for an arm overriding
either, so the arm silently measured the un-overridden value — the exact measurement-integrity
failure class ADR-0030 added the ratchet to catch.

Confirmed by `find_connections`, not grep alone: `create_reranker` has exactly one direct
caller (`RerankingEngine._ensure_reranker`), so that site is the whole story for all six
fields. The fix propagates through a real seam: `_derive_construction_baked_fields`
(`search/config.py`) also has exactly one direct caller, `requires_rebuild`. **The fix is two
metadata kwargs in `search/config.py` — no edit to `arm_overrides.py` itself.**
`test_construction_baked_fields_are_pinned` bumped 10 → 12;
`test_requires_rebuild_true_for_construction_baked_fields` gained both keys.

`batch_size` also carries `mcp="reranker_echo"` (read-only echo, not settable via MCP), so
`test_no_mcp_settable_field_is_construction_baked` was narrowed to check only settable `mcp`
tags — echo tags cannot hit the MCP-write-then-no-op hazard the test exists to catch, since
`_RERANKER_FIELDS` (the settable set) derives from non-echo tags only.

### D3 — dead config value: `"lsp"` in `call_graph.resolvers`

`search/call_edge_injection.py` tests `enabled_names` only for `"pyan"`/`"libcst"`; LSP is
appended solely via the separate `lsp_enabled` bool, and any unrecognized name was silently
ignored. `CallGraphConfig`'s docstring tabulated `"lsp" → LSPResolver` as a resolver-list
entry and said `resolvers: []` "skips entirely" — but `[]` never affected LSP. The live config
is a three-resolver ladder that read as two. Fixed: docstrings corrected (Stage 3 governed
solely by `lsp_enabled`; `resolvers: []` does not disable it), plus a runtime warning in
`inject_call_edges` — `"lsp"` in the list gets a warning pointing at `lsp_enabled`, any other
unrecognized name gets a generic warning — purely additive, cannot alter the constructed
resolver ladder. Two new tests in `tests/unit/search/test_index_write_stage.py`
(`TestInjectCallEdgesResolverSelection`) pin both: the `"lsp"`-in-list warning fires and the
ladder stays identical to `["pyan", "libcst"]`, and a garbage name warns and is dropped.

### D4 — inert auto-tune probe rule, plus a missing guard class

`search/index_probe.py`'s `reranker.batch_size` `ProbeRule` writes 8 or 32, but
`create_reranker()` drops `batch_size` on the `JinaRerankerV3` branch — the deployed default —
so the rule is a no-op on most installs. It is genuinely live for `NeuralReranker`/
`GenerativeReranker` (both legal `reranker.model_name` values) and the probe runs on arbitrary
hardware, so the rule was not deleted or re-keyed; its `reason_fn` was made self-aware, stating
the jina-v3 no-op explicitly, matching the idiom already used six rules up
(`embedding.batch_size`'s "used when dynamic sizing disabled").

Separately: no test asserted a `RULES` entry's dotted key resolves to a real `SearchConfig`
field — `test_forbidden_keys_resolve_to_real_fields` covered only the *forbidden* set, not the
rule table itself. A typo'd rule key would write a nonsense dotted key that `_set_dotted`/
`_build_subconfig` silently drops (documented as "forward-compatible") — the same shape as the
historical `search_mode.centrality_alpha` inert-guardrail bug, on the write side instead of the
read side. Added `test_override_rules_resolve_to_real_fields` (reuses the `_SUBCONFIG_TYPES` +
`dataclasses.fields` walk from the forbidden-keys test, over all 12 `RULES` entries) and
`test_rules_pinned` (pins `{(kind, stage, key) for r in RULES}`, with an explicit reachability
caveat in its docstring: pinning proves the key is real and the shape is stable, not that the
rule fires on the shipped reranker).

### D5 — verified stale docs

- `docs/MCP_TOOLS_REFERENCE.md`: `chunking.max_split_chars` default stated 1600, actual 3000;
  `sizing_mode` default stated `"fixed"`, actual `"adaptive"` — both corrected. Every other
  stated range/default in that `configure_chunking` block was cross-checked against
  `ChunkingConfig` and found accurate.
- `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`: claimed `multi_hop.expansion`'s dataclass
  default was 0.3 versus the `.example`'s 0.5 — both are actually 0.5 (verified directly
  against the live `MultiHopConfig` dataclass); the claimed divergence was *forbidden* by the
  parity test, so left as-is it invited a "fix" that would have broken CI.
- `chunking/languages/base.py`: complexity-scoring docstring called it "inert under the
  default `sizing_mode='fixed'`" — backwards; `"adaptive"` is the current default, so the path
  is live.
- `CHANGELOG.md`'s Unreleased block described the QW5/A1 intent-policy-table deletion as "the
  pending decision" — ADR-0031 already made and executed that decision. Reworded to point at
  the Changed-section entry recording the deletion; the entry itself was not deleted, since the
  measurement it describes happened and justified the deletion.
- `search/config.py` gained five inline comments extending the existing `# GenerativeReranker
  only`-style convention to fields that had none: `prefer_gpu` (gates dynamic batch sizing
  only), `reranker.batch_size` (ignored by JinaRerankerV3), `reranker.min_vram_gb` (bypassed
  under `allow_ram_fallback`), `embedding.batch_size` (used only without dynamic sizing/CUDA),
  `embedding.dimension` (derived from `MODEL_REGISTRY`, not configurable).

### Derived figures (current, superseding ADR-0022's landing snapshot)

124 fields / 14 sections / 98 flat aliases / 43 env-settable / **18** MCP-tagged (16 settable +
2 echo-only) / 18 with validation metadata (`range` or `choices`) / **12** construction-baked
(was 10 at ADR-0030's landing; D2 added `reranker.batch_size`/`instruction`). The **15 → 18**
MCP-tagged correction belongs here, not as a retro-edit of ADR-0022 — see "Deliberately not
changing" below.

## Deliberately not changing

Recording rejections is this repo's convention (ADR-0020's residuals, ADR-0022's measured
alternatives); without it, the next audit re-derives all of these from scratch. None of these
individually clears the "surprising without context" / "result of a real trade-off" bar alone,
but the set does.

- **Renaming `prefer_gpu`, or making it gate device selection.** `CLAUDE_PREFER_GPU` and the
  `prefer_gpu` flat alias are published surfaces; a rename needs a back-compat shim plus
  lockstep edits across `spec()`, the derived env map, the tracked `.example`, the parity test,
  and the ratchet. The honest name is roughly `enable_dynamic_batch_size_on_gpu` — a near-
  duplicate of the existing `enable_dynamic_batch_size`, the exact two-switches-one-behaviour
  shape ADR-0020 rejected when it deleted `enable_result_reranking`. Making it actually gate
  the device is a feature with an index/latency story and a silent-slowdown foot-gun — the
  defect was three sentences of `.cmd` text, so the fix is three sentences.
- **Folding `lsp_enabled` into `resolvers`, or adding `choices` to it.** `resolvers` is
  `list[str] | None`, `None` meaning `["pyan", "libcst"]`; folding LSP in changes what `None`
  means for every config carrying `null` — a real indexing-behaviour change to fix a
  documentation problem. `validate_field_value` does `value not in choices`, which on a
  `list[str]` compares the whole list and always fails.
- **Deleting or re-keying the `reranker.batch_size` probe rule.** Genuinely live for
  `NeuralReranker`/`GenerativeReranker`, and the probe exists to run on arbitrary hardware.
  Re-keying to `top_k_candidates` would be a candidate-pool change — a search-path change
  requiring a full benchmark re-pin.
- **Any `reachable_when=` spec tag.** "Reachable on the current config" is a predicate over
  *other* fields' runtime values, not a static property of a field, so the tag goes stale
  exactly when it matters. ADR-0022 already rejected this class on measured grounds (a runtime
  read-tracking driver needs a curated exercise-everything harness plus an exemption list,
  naming the same population this audit found). Five fields; five inline comments beat a
  thirteenth hand-maintained representation.
- **Validation on the config-file load path.** Only 18 of 124 fields carry `range`/`choices` —
  file-load validation would gate 15% of the surface while *looking* like a full gate, worse
  than a documented absence. Every path where a bad value arrives from elsewhere is already
  validated (env, MCP handlers, benchmark arm overrides). The unvalidated path is a hand-edit
  of a gitignored, machine-local file, and gating it changes startup behaviour on every
  process including the MCP server's deliberately fail-soft stdio load. Zero evidence it has
  ever bitten.
- **Runtime enforcement of `FORBIDDEN_AUTO_TUNE_KEYS`.** Currently guarded only by static
  tests (`test_no_override_rule_touches_forbidden_keys`). Deferred as hardening, outside this
  round's scope, and would ship as a provable no-op today — no rule's key is in the forbidden
  set. Reopening condition: enforce in `run_rules` (upstream of the file, `summary()`, and the
  MCP index response, keeping `overrides`/`reasons` 1:1) the first time a rule regresses into
  the forbidden set.
- **Retro-editing ADR-0022's "15 MCP-settable"**, and `docs/VERSION_HISTORY.md`'s dated
  `default_k` entry. Both were true at landing — rewriting them breaks the convention ADR-0020
  stated explicitly, that historical records document what was true at the time. The "15 → 18"
  correction lives here instead (see Derived figures, above).
- **Realigning `query_expansion`'s section order** (7th in both JSON files, 14th in
  `_SUBCONFIG_FIELDS`). The concern was a spurious diff on a tracked file, but that cannot
  happen: `search_config.json` is gitignored and `save_config()` never writes `.example`; the
  parity test compares sets, so CI is order-indifferent. Residual cost is a noisy manual `diff`
  on one machine.
- **A prose-parsing guard for `MCP_TOOLS_REFERENCE.md` defaults.** Asserting every stated
  `default:` matches the dataclass needs a bespoke Markdown parser — precisely the thirteenth
  hand-maintained representation ADR-0022 exists to stop adding. Follow-up worth naming
  instead: the derived `configure_chunking` schema in `mcp_server/tool_registry.py` emits
  `minimum`/`maximum`/`enum` but no `default` keys, while the tool description promises each
  field's factory default is documented on its schema property. Emitting defaults from the
  dataclass into the derived schema would kill this drift class at the root — a real follow-up,
  not done here.

## Consequences

- Zero production behaviour change on the search path — nothing under
  `search/hybrid_searcher.py`, `search/search_executor.py`, or `reranking_engine.py`'s
  reranking behaviour was touched; no `INDEX_VERSION` bump; no benchmark re-pin required.
- `evaluation/arm_overrides.py::requires_rebuild()` becomes strictly more conservative (more
  rebuilds, never fewer) for `reranker.batch_size`/`instruction` overrides — it cannot silently
  change any previously-published result; worst case a future arm gets slower and correct
  instead of silently wrong. No published benchmark arm overrides either field today.
- `search/call_edge_injection.py` now warns on `call_graph.resolvers` entries other than
  `"pyan"`/`"libcst"`, purely additive — the constructed resolver ladder is unchanged for every
  existing config.
- Construction-baked field count: 10 → 12. MCP-tagged count corrected in documentation: 15 → 18
  (echo tags were always excluded from the settable count; this ADR is the first place the
  echo-inclusive total is stated).

## Verification

- `./scripts/test/run_tests.sh tests/unit/search/test_config_field_liveness.py
  tests/unit/search/test_search_config.py tests/unit/search/test_index_probe.py
  tests/unit/evaluation/test_arm_overrides.py -q` — 160 passed (baseline 55 on the first two
  files before this round's additions).
- `./scripts/test/run_tests.sh tests/unit/search/test_index_write_stage.py
  tests/unit/search/test_index_probe.py -q` — 78 passed, including the two new
  `call_edge_injection` resolver-warning tests.
- Negative controls written as permanent tests, not just run-and-discard: an embedding-
  dimension test using an unregistered `model_name` proves the registry-override test's
  effect comes from the registry lookup firing, not from `from_dict` discarding `dimension`
  unconditionally.
- Every load-bearing claim (D1 read site, D2 single-caller chain, D3 resolver ladder, D4 rule
  table, `embedding.dimension`'s derivation site) was independently confirmed via
  `search_code`/`find_connections` against the live MCP index before being written down here.

## Out of scope

- File-load-path validation, `reachable_when=` reachability tagging, and runtime
  `FORBIDDEN_AUTO_TUNE_KEYS` enforcement — see "Deliberately not changing" above for each
  rejection's reasoning and (where one exists) its reopening condition.
- Emitting dataclass defaults into `tool_registry.py`'s derived `configure_chunking` JSON
  schema, closing the `MCP_TOOLS_REFERENCE.md` prose-drift class at the root — named as a
  follow-up above, not implemented here.
