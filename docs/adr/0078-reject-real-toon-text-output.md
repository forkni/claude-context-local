# Reject real TOON v4.1 text output; keep the improved `ultra`

Status: accepted
Date: 2026-09-21

## Context

An uncommitted prior session built a real TOON v4.1 text encoder
(`mcp_server/toon_encoder.py`, 531 lines) and wired it as new `toon` / `toon-tab`
`output_format` values, alongside four separate, genuine improvements to the existing `ultra`
JSON-carrier format: insertion-order header fields (`sorted()` removed), nested field groups
with null-fill (e.g. `find_path`'s `path[N]{node{...},edge_to_next{...}}`), `sparse_threshold`
promoted to config, and assorted docs drift fixes. Neither piece had been committed.

The session pre-registered a gate for promoting `toon`: it must beat `ultra` in tiktoken count
on both `search_code` and `find_connections` — the two dominant tools by call volume. The full
measurement lives in `evaluation/CONTEXT_COST_TOON_PROBE_20260921.md` (133-query probe,
`golden_dataset_expanded.json`, `CLAUDE_AUTO_REINDEX=0`).

**Gate result:** `toon` beats `ultra` on `find_connections` (−28.6 tokens, −0.94%) but loses on
`search_code` (+4.5 tokens, +0.31%). The gate requires both. **FAILED.** Pooled across every
tool in the golden set (not just the two gate tools), `toon` is smaller by bytes (−3.8% mean vs
`ultra`) — the byte win doesn't survive tokenization on the two tools that matter most.
Plausible mechanism (not independently ablated): `search_code`'s dominant column is `chunk_id`
(`"file.py:10-20:function:name"`), which contains `:` — one of TOON's unconditional quoting
triggers — so it's quoted under TOON exactly as it already is under JSON, leaving only TOON's
per-row indentation/colon overhead with no offsetting unquoted-string win on that tool's largest
column.

A failed gate does not, by itself, mandate deletion — the usual next move in this project is
"ships opt-in, measured-and-rejected for default" (e.g. ADR-0034's pyan quarantine, the
`hide_ambiguous` A/B). This ADR is about why that path was rejected here specifically.

## Decision

Delete `toon` / `toon-tab` outright rather than ship them opt-in. Removed:

- `mcp_server/toon_encoder.py` (531 lines) and its `"toon"`/`"toon-tab"` dispatch branches in
  `mcp_server/output_formatter.py` and `mcp_server/server.py`.
- The `"toon"`/`"toon-tab"` `choices` on `OutputConfig.format` (`search/config.py`) and the
  corresponding `start_mcp_server.cmd` menu option.
- `tests/unit/mcp_server/test_toon_encoder.py` (513 lines, 62 tests) and
  `tests/fixtures/toon_spec/` (9 upstream spec-conformance fixtures, 45.7 KB).
- The `toon`/`toon-tab` arms and the now-vestigial `_phase2_gate_verdict()` helper in
  `scripts/benchmark/probe_context_cost.py`.
- The "Real TOON Text" section, table row, and recommendation bullet in
  `docs/MCP_TOOLS_REFERENCE.md`.

Kept — the improved `ultra`:

- Insertion-order header fields, nested field groups with null-fill, `_optimize_payload` as the
  named shared pre-pass, `sparse_threshold` promoted to config, and the docs drift fixes.
- The one piece of `toon_encoder.py` `ultra` actually depended on — the pure tabular-eligibility
  detector (`_try_tabular_field_spec` / `_try_uniform_object_group` / `_build_field_spec` /
  `_render_field_spec` / `_flatten_row` / `_all_dicts`, ~80 lines) — extracted into
  `output_formatter.py` as private module functions before the encoder was deleted, hardcoding
  the comma delimiter and dropping TOON's `fmt_key` key-quoting (the non-tabular fallback header
  already renders field names with a plain `','.join`; applying TOON-style quoting on only one of
  `_to_ultra_format`'s two branches would make them disagree on the same field name — every field
  name in this project's payloads is a Python identifier, so dropping quoting is
  behaviour-neutral, pinned by `TestUltraByteIdentityGuard`).
- The relevant detector test cases, ported from `test_toon_encoder.py` into
  `tests/unit/mcp_server/test_output_formatter.py` and retargeted at the extracted function.

## Reasons

**The measurement says it does not pay, and the miss is on the tools that matter most.**
`search_code` and `find_connections` are the two dominant tools by call volume; `toon`'s
pooled-byte advantage inverts to a net tiktoken loss on exactly the tool (`search_code`) most
callers hit most often. An opt-in format that's worse than the default on the common case is a
trap for anyone who picks it expecting the pooled number to hold.

**The name collides with this project's own retired meaning.** `CHANGELOG.md` (v0.7.0, Breaking
Changes) already documents `` `toon` → `ultra` ``, with a migration note telling callers to
change `output_format="toon"` to `output_format="ultra"`. Re-introducing `toon` as a *different*
format — real TOON text instead of the JSON-carrier tabular format that name used to mean —
would silently change what that string means to any script or memory still carrying the old
name, and makes the shipped v0.7.0 note actively misleading.

**It is dead weight with exactly one internal caller.** `find_connections` on
`toon_encoder.py:56-82:encode` showed one real caller
(`output_formatter.py:_to_toon_text`, the now-deleted text-rendering wrapper); everything else
in `direct_callers` was an unrelated `.encode()` string/bytes call misresolved by the AST
resolver tier at 0.5 confidence. The encoder's only genuine dependent was `ultra`'s detector,
which is now extracted and independent of it.

**Nothing was committed, so there is no back-compat obligation.** No deprecation shim, no alias
— the closest thing to a compatibility concern (the v0.7.0 `toon`→`ultra` rename note) argues
*for* removal, not against it.

## Considered Options

- **Ship opt-in, keep for callers with a real TOON v4.1 decoder** — rejected: the format that
  would be shipped opt-in isn't better than the default on the two dominant tools, one of them by
  a nontrivial margin; an opt-in path whose main selling point (smaller pooled bytes) doesn't
  survive tokenization on the common case isn't worth the two encoder/test files it costs to
  maintain. Also collides with the retired `toon` name (see above), which a straight "ships
  opt-in" path doesn't resolve.
- **Keep `toon_encoder.py` for the detector alone, drop the text-output formats** — rejected:
  leaves ~450 of the file's 531 lines (`encode`, `_Encoder`, `_try_keyed_tabular`, quoting,
  escapes, the JS number-format rule) permanently unreachable — exactly the dead code this ADR
  exists to remove.
- **Drop `ultra`'s nested field groups along with the encoder** — rejected: discards a verified,
  independently-useful improvement (`(2)` in the prior session's split) to fix an unrelated
  problem in `(1)`.
- **Delete the encoder, extract the shared detector into `output_formatter.py`** — accepted.

## Consequences

- `output_format` now accepts exactly `verbose` / `compact` / `ultra`; `"toon"` and `"toon-tab"`
  are rejected by every tool's schema `enum` (derived from `OutputConfig.format.choices`).
- `ultra` is the only tabular-header format the server offers; its nested-field-group and
  insertion-order improvements ship as part of this change, not as a separate follow-up.
- `pyproject.toml`'s per-file C901 allowlist comment and `docs/MCP_TOOLS_REFERENCE.md`'s example
  `chunk_id`s were updated for the `_to_toon_format` → `_to_ultra_format` rename that accompanied
  this cleanup (the retired-name credit sentence in `output_formatter.py`'s module docstring is
  the one intentional remaining `toon` mention under `mcp_server/`).
- No canon re-pin is owed: output formatting sits downstream of ranking, and no golden query
  targets the renamed symbol or the deleted encoder.
- Reopening requires re-implementing the encoder from scratch (it was deleted, not archived) —
  see the Reopening condition in `evaluation/CONTEXT_COST_TOON_PROBE_20260921.md`.
