# One spec row per request-scoped result enricher; derive schema, default, plan, and gate

Status: accepted
Date: 2026-08-20

## Context

Workstream B unified the three result enrichers behind `RESULT_ENRICHERS` +
`enrich_results(results, index_manager, gates)` in `mcp_server/tools/result_view.py`, and
ADR-0046 single-sourced every hand-typed MCP default through `config_schema.py`'s `HAND_TYPED`.
Both seams held — and yet adding one opt-in display parameter still touched four production
files, six sites, every time:

1. `tool_registry.py` — the published boolean schema property with its description,
2. `config_schema.py` — the `HAND_TYPED` default entry with its rationale,
3. `search_orchestrator.py` — a typed `SearchPlan` field,
4. `search_orchestrator.py` — the `arg()` read in `SearchPlanner.plan()`,
5. `search_orchestrator.py` — a row in `_enrichment_gates`,
6. `result_view.py` — the apply function and its `RESULT_ENRICHERS` row.

That chain executed three times in one week (`include_top_callers` a20c805,
`include_signatures` 21cd9bb, `hide_ambiguous` 63c1840) — display parameters are now the
highest-frequency change axis, since retrieval-quality levers are measured-and-exhausted per the
campaign records. Sites 1–5 restate the *same* facts (name, default, gate identity) in different
shapes; only site 6 carries behavior. Classic Shotgun Surgery over a Data Clump.

## Decision

Split the enricher concept into two registries joined on `key`, and derive everything
declarative from one row.

**`mcp_server/enricher_specs.py`** (new leaf module, stdlib-only imports) holds the **wire
interface**: `EnricherSpec(key, param, default, description, rationale)`, one frozen row per
request-scoped enricher in `ENRICHER_SPECS`. Three modules derive from it:

- `config_schema.py` builds the row's `HAND_TYPED` entry inside the dict literal
  (`**{f"search_code.{s.param}": HandTyped(default=s.default, rationale=s.rationale) ...}`),
  so the ADR-0046 ratchets keep governing the derived entries unchanged.
- `tool_registry.py` builds the row's schema property in the same slot the hand-typed literal
  occupied, still spreading `HAND_TYPED[...].schema` for the default — the ADR-0046 AST ban on
  inline `"default":` literals continues to bite.
- `search_orchestrator.py` replaces the two typed `SearchPlan` bools with one
  `display_params: Mapping[str, bool]` populated by a single loop over `ENRICHER_SPECS`
  (`{s.key: bool(arg(arguments, f"search_code.{s.param}")) ...}`); `_enrichment_gates` becomes
  `{"graph": output_cfg.include_result_graph, **plan.display_params}`.

**`result_view.py`'s `RESULT_ENRICHERS`** keeps the **application side** unchanged:
`ResultEnricher(key, field, apply)`. The spec row deliberately does *not* carry `field` or the
apply function — nothing on the wire side needs them, and pulling them into the spec would just
relocate the third edit site, not remove it. The two registries join on `key`, drift-tested in
`tests/unit/mcp_server/test_search_orchestrator.py`
(`test_enricher_specs_join_result_enrichers_on_key`: spec keys ∪ {"graph"} == enricher keys).

Adding a request-scoped enricher is now: **one spec row + the apply function and its
`RESULT_ENRICHERS` row** — two files, and every forgotten wiring step is a red test, not a
silent gap.

### The `graph` gate stays explicit

`graph` gets no spec row. Its gate is config-scoped (`OutputConfig.include_result_graph`), and
the literal field name must keep appearing in `search_orchestrator.py`: ADR-0022's
field-liveness ratchet asserts each config field's name occurs in its declared
`spec(reader=...)` file, which for `include_result_graph` is that module. Routing it through a
generic spec row would satisfy the gate map but break the liveness ratchet's reader contract.

### `SearchPlan.display_params` defaults

The field's default factory enumerates every spec row at its declared default
(`{s.key: bool(s.default) for s in ENRICHER_SPECS}`) rather than defaulting to `{}`. A bare
`SearchPlan` therefore always carries a complete gate set, which keeps the
"gates enumerate every registered enricher" invariant true by construction — the pre-existing
coverage test (`test_enrichment_gates_cover_every_registered_enricher`) now transitively enforces
the specs↔enrichers join on every constructed plan.

### Defining property

The published `search_code` schema does not move a byte — verified by diffing a full
`input_schema` + `HAND_TYPED` capture against a pre-change snapshot (property order included).
The only non-schema delta is the two `HandTyped.rationale` strings, which are internal
documentation and now name the spec row as the fallback's home. Wire-level consumers
(`scripts/benchmark/probe_context_cost.py`, docs, skill references) pass `include_top_callers`/
`include_signatures` as arguments and are untouched.

## Deliberately out of scope

- **`NEVER_DROP_EMPTY_KEYS`** (`mcp_server/output_formatter.py`) — encodes a handler contract
  out-of-band, but no enricher field appears in it (enrichers return early on empty), so folding
  it into the spec row would be speculative generality today.
- **Config-scoped display toggles** (`include_result_graph`, `hide_ambiguous`) — their defaults
  live in `search/config.py` under ADR-0022's spec table; a second declaration layer for them
  would reintroduce exactly the dual-statement drift ADR-0042/0046 closed.
