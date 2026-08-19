# Point stale ADR/README prose counts at their derived source, not a re-pinned number

Status: accepted
Date: 2026-08-19

## Context

Re-verifying `log-defects-sorted-scroll.md` against `development` @ `823d79d` (post C2/`a856781`

+ C4/`15c2429`, `6ebb69b`, `a8be927`) turned up five stale prose claims: `0014-*.md`'s inline
`FORBIDDEN_AUTO_TUNE_KEYS` listing (still named `enable_community_merge`, deleted by ADR-0020, and
missing 8 of the 19 keys live today), `0032-*.md`'s title claiming "124/124 fields live" (141
live today), `README.md:40` mirroring that count, `0030-*.md`'s "corrected 10-field set" (13 live
today), and `0022-*.md`'s "(now 15 keys)" (19 live today). None were wrong when written — each was
an accurate measurement the day it landed. They went stale because the sets they quote
(`FORBIDDEN_AUTO_TUNE_KEYS`, `_CONSTRUCTION_BAKED_FIELDS`, the total config field count) keep
growing as the codebase does, while the prose that once quoted them does not.

ADR-0042 already settled this question for the MCP tool schema: never publish a value that can
drift, publish a pointer to the code that derives it — `spec()` metadata backs `minimum`/
`maximum`/`enum`, and `default` is refused entirely because no static snapshot of it can stay
honest (a running server's effective default depends on ADR-0014's four-layer precedence, not the
dataclass). This ADR applies the same judgment to ADR/README prose, where the same drift class
surfaced independently.

## Decision

Two rules, applied to the five fixes above and to future ones shaped like them:

+ **Point-in-time measurement tables and titles stay as written.** An ADR's title and its dated
  "N fields live" results describe what was true the day that round measured it; rewriting them to
  match today's count would make the record lie about what was actually measured. `0032`'s title
  keeps "124/124 fields live, five defects fixed" verbatim.
+ **Add a pointer alongside the stale number — never a replacement number.** Each fix appends a
  short note (a blockquote under `0032`'s title, an extended Consequences bullet in `0030`, a
  parenthetical in `0022`'s sentence, an inline replacement for `0014`'s copy-pasted list) that
  names the current count for context and cites the live source: `SearchConfig._SUBCONFIG_TYPES`
  walked via `dataclasses.fields()` (total field count), `SearchConfig._CONSTRUCTION_BAKED_FIELDS`
  (construction-baked set), `search/index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS` frozenset
  (auto-tune guardrail). A future reader gets both the historical number and a pointer that cannot
  go stale, because it is not a number at all.

`0014` is the one outright deletion rather than an annotation: its inline copy of
`FORBIDDEN_AUTO_TUNE_KEYS`'s membership was never a measurement result worth preserving verbatim —
it was a convenience listing, and an actively misleading one once it named a deleted key. It is
replaced with a pointer only, matching the pattern `SearchConfig.__doc__` already uses for
`_SUBCONFIG_TYPES` (`search/config.py:1746-1749`, established by ADR-0022).

`docs/adr/README.md` also gets an unrelated sixth fix in the same commit: a missing index row for
ADR-0042 itself (42 files under `docs/adr/`, 41 index rows — the table stopped at 0041).

## Consequences

+ Five prose claims (`0014`, `0022`, `0030`, `0032`, `README.md`) no longer contradict the live
  codebase; none of their historical measurement content was altered.
+ This ADR is deliberately narrow. ADR-0042 already documents *why* this repo prefers derived
  pointers over hand-copied values and *what* the mechanism looks like for the MCP schema
  specifically; this record only extends the same judgment to ADR/README prose and does not
  restate 0042's reasoning.
+ No code changed, and no benchmark re-run is implied by this ADR on its own.

## Out of scope

+ **Auto-generating these pointers from a template or lint rule.** Five instances is not yet a
  pattern that justifies tooling; a sixth stale-count defect found the same way would be the
  trigger to build one.
+ **Pre-emptively rewriting every dated ADR's historical tables to add pointers.** Only the five
  claims found stale during this round's re-verification were touched; auditing the full ADR
  corpus for the same defect class is a separate, larger task.
