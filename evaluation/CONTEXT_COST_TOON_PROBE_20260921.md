# TOON v4.1 Context-Cost Probe (2026-09-21)

## Status: MEASURED — Phase 2 gate FAILED, real-TOON-text output REMOVED (not shipped opt-in)

Closes Phase 2 of `i-want-you-to-foamy-graham` ("Bring MCP output formatting up to TOON v4.1"):
measure real TOON v4.1 text (`toon`/`toon-tab` arms) against the existing `ultra` JSON-carrier
format before deciding whether to flip the default. Per the plan's pre-registered gate: **`toon`
must be ≤ `ultra` in tiktoken count on `search_code` AND `find_connections`** (the two dominant
tools), or `toon` ships opt-in and the finding is recorded as measured-and-rejected.

**Verdict in one line:** `toon` beats `ultra` on `find_connections` (−28.6 tokens, −0.94%) but
narrowly loses on `search_code` (+4.5 tokens, +0.31%) — the gate requires both, so it **fails**.
Since nothing had been committed, the real TOON v4.1 text encoder (`mcp_server/toon_encoder.py`,
the `toon`/`toon-tab` output formats, and its fixture/test suite) was removed outright rather than
kept opt-in — see `docs/adr/0078-reject-real-toon-text-output.md`. `ultra` remains the shipped
default in `OutputConfig.format` and is now the only tabular-header format.

## Harness

`scripts/benchmark/probe_context_cost.py --dataset evaluation/golden_dataset_expanded.json --k 10
--json evaluation/CONTEXT_COST_TOON_PROBE_20260921.json`, `CLAUDE_AUTO_REINDEX=0` exported per
this project's standing harness rule. 133 queries (`golden_dataset_expanded.json`), project
`claude-context-local` itself (self-index), `connections_max_depth=3`. Raw run log:
`/tmp/toon_probe_run.log` (not persisted — ephemeral). Full per-query JSON:
`evaluation/CONTEXT_COST_TOON_PROBE_20260921.json` (stays local per this project's `evaluation/`
convention — not staged).

## Phase 2 gate result

| tool | ultra (tiktoken mean) | toon (tiktoken mean) | Δ (toon − ultra) | toon ≤ ultra? |
|---|---|---|---|---|
| `search_code` | 1473.985 | 1478.504 | **+4.519** (+0.31%) | ❌ FAIL |
| `find_connections` | 3037.179 | 3008.607 | **−28.572** (−0.94%) | ✅ PASS |

**Gate PASSED = False** — requires both to hold; `search_code` breaks it.

## Full metrics, all formats, all tools pooled

### payload_bytes (mean / median / p90) and format_savings vs verbose

| format | mean_bytes | median | p90 | savings |
|---|---|---|---|---|
| verbose | 11156.9 | 12105 | 12638 | 0.0 |
| compact | 7061.5 | 7646 | 8045 | 0.368 |
| ultra | 4411.6 | 4665 | 5019 | 0.600 |
| **toon** | **4245.5** | 4480 | 4832 | **0.615** |
| toon-tab | 4248.0 | 4483 | 4835 | 0.615 |

Pooled across every tool in the golden set (not just the two gate tools), `toon` is the smallest
format on every statistic — 3.8% fewer bytes than `ultra` on the mean. This is the opposite
ranking from the gate-scoped result above; the two dominant tools happen to be where `toon`'s
byte advantage does not translate into tiktoken advantage (see Mechanism note).

### tiktoken_by_format, per tool (the two gate-relevant tools, full breakdown)

| format | search_code mean | find_connections mean |
|---|---|---|
| verbose | 3515.4 | 6536.4 |
| compact | 2108.8 | 3609.7 |
| ultra | 1474.0 | 3037.2 |
| **toon** | 1478.5 | **3008.6** |
| toon-tab | 1546.1 | 3090.8 |

`toon-tab` (tab delimiter) is worse than `toon` (comma) on **both** tools and on pooled bytes —
the reference implementation's note that tabs "often tokenize more efficiently"
(`docs/reference/api.md`) does not hold on this corpus/tokenizer combination. Not investigated
further; not worth a second gate leg since comma already wins the comparison that matters.

### Other probe outputs (informational, not gate-relevant)

- `k_drift`: mean 16.985, median 20, max 20 — most queries return the full requested `k`.
- `tokens_returned@k`: production heuristic mean 2167.87 vs tiktoken mean 3027.26 (ratio 1.396) —
  the in-repo token-counting heuristic undercounts by ~28% against real tiktoken on this corpus;
  unrelated to the TOON gate, noted for anyone tuning `max_context_tokens` budgets off the
  heuristic.
- `gold_sufficiency`: `located_rate=0.895`, `content_present_rate=0.0` /
  `signature_present_rate=0.0` — both expected structurally 0 since `search_code` returns
  coordinates only by default (no chunk content, no signatures) in this run.
- `redirect_histogram`: `{none: 123, find_similar: 10}`.
- `connections_fanout`: 14 primary / 14 secondary queries, 0 skipped; primary mean payload 20,106
  bytes, secondary 18,987 bytes, primary mean `total_impacted` 86.5.
- `results_vanished_count`: 0 across every format — no format is silently dropping results
  relative to `verbose`, i.e. this probe run itself found no correctness regression in any arm.

## Mechanism note (plausible, not directly measured)

Why does `toon` win on `find_connections` but lose on `search_code`? A likely explanation:
`search_code`'s dominant payload column is `chunk_id` (and `file`), formatted
`"file.py:10-20:function:name"` — every value contains `:`, one of TOON's 11 unconditional
quoting triggers. That column is therefore quoted in `toon` exactly as it already is in `ultra`'s
JSON, so the one place `ultra`'s JSON quoting genuinely costs bytes over TOON (unquoted bare
strings) never fires on `search_code`'s largest column — leaving only TOON's per-row 2-space
indentation and header-colon overhead as a net cost with no offsetting unquoted-string win.
`find_connections`' relationship-type names, confidence tags, and numeric fields are unquoted
under TOON and account for its win there. This is offered as the most plausible reading of the
gate split, not as an independently verified causal claim — no column-level ablation was run to
confirm it.

## Disposition

- `toon` / `toon-tab` were **removed**, not kept opt-in: `mcp_server/toon_encoder.py`, the
  `"toon"`/`"toon-tab"` output-format branches in `mcp_server/server.py` and `output_formatter.py`,
  the `toon`/`toon-tab` `choices` in `OutputConfig.format` (`search/config.py`), the
  `start_mcp_server.cmd` menu option, and the whole test/fixture suite
  (`tests/unit/mcp_server/test_toon_encoder.py`, `tests/fixtures/toon_spec/`) are gone. The pure
  tabular-eligibility detector `toon_encoder.py` shared with `ultra` was extracted into
  `output_formatter.py` as private helpers before deletion, so `ultra`'s nested-field-group headers
  are unaffected.
- `OutputConfig.format` default remains `"ultra"`, and `"ultra"` is now the only tabular-header
  format exposed by the server. No config-visible change for existing callers (nothing used `toon`
  — it was never committed).
- Per this project's convention: recorded here as **measured-and-rejected**, same as before, but
  the disposition is removal rather than an opt-in ship. Rationale for removing rather than keeping
  it opt-in: the gate failed on both bytes-vs-tiktoken generalization and on the two dominant
  tools, it had exactly one internal caller (the detector, now extracted), and `toon` collides with
  this project's own retired `output_format="toon"` name (renamed to `ultra` in v0.7.0 per
  `CHANGELOG.md`) — see `docs/adr/0078-reject-real-toon-text-output.md` for the full argument.

## Reopening condition

Reopen only if a future change alters the dominant tools' payload shape enough to change which
columns would require TOON quoting (e.g. a `chunk_id` format change that drops the `:`-delimited
scheme), or if a broader tool set becomes the "dominant tools" definition for the gate. Reopening
means re-implementing the encoder from scratch (it was deleted, not archived) and re-running this
probe's harness before re-wiring anything.
