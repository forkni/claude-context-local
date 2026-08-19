# Derive the MCP tool schema's bounds/enums from `spec()`; never derive `default`

Status: accepted
Date: 2026-08-19

## Context

`589f989` (2026-08-18, "close … L2a schema-honesty defects") fixed a hand-typed `"default"` in
`mcp_server/tool_registry.py` that had drifted from what the running server actually falls back
to, then appended this parenthetical to all 18 `output_format` occurrences rather than fixing the
drift class itself:

> `(schema default: 'compact'; the running server may be configured with a different effective
> default — check get_search_config_status.output_format)`

ADR-0032:200-202 had already named this exact follow-up and explicitly deferred it: *"Emitting
defaults from the dataclass into the derived schema would kill this drift class at the root — a
real follow-up, not done here."* The architecture review that produced this repo's current
candidate list (`C4`) measured the cost precisely: `tool_registry.py` carried 40 hand-typed
`"default"` entries, 23 hand-typed `"enum"` entries, 14 hand-typed `"minimum"` entries, and 18
verbatim copies of the same `output_format` block. Only 4 of the 18 tools had any parity test
(`test_tool_registry.py`'s `TestConfigToolSchemaMatchesFieldSpec`, parametrized over `(minimum,
maximum)` and `enum` — never `default`), and the four fields `589f989` had to hand-correct all
live in the 14 tools that test doesn't cover.

## Decision

Derive `minimum`/`maximum`/`enum` schema fragments from `search/config.py`'s `spec()` metadata via
a new module, `mcp_server/config_schema.py`, and **never derive `default`**.

The asymmetry is deliberate, not an oversight: `spec(range=...)`/`spec(choices=...)` are
invariants — true for every install, safe to publish in a static schema. A field's dataclass
default is not an invariant; it is the *lowest* of ADR-0014's four precedence layers (env >
per-project overrides > config file > dataclass default), so the value a specific running server
actually uses can differ from it. Publishing a derived default would still drift from the running
server the moment any higher-precedence layer overrides it — the schema-honesty parenthetical
would just move from "hand-typed and wrong" to "derived and still wrong." Removing `default`
entirely closes the drift class instead of relocating it; callers needing the live value already
have `get_search_config_status`.

Each schema property is classified into exactly one of two sets:

- **`CONFIG_BACKED`** — built by `_build()` off a `(section_cls, field_name)` pair: `type` from the
  field's real type object, `minimum`/`maximum` from `metadata["range"]`, `enum` from
  `metadata["choices"]`. Raises `ValueError` at import time (not silently guesses) when a field is
  in `_UNRESOLVABLE` (`default_factory`, `__post_init__` rewrite, or `MODEL_REGISTRY` overwrite —
  none of the three affected fields are MCP-visible today) or its type has no `_TYPE_MAP` entry.
- **`HAND_TYPED`** — every field kept out of `CONFIG_BACKED`, with a documented rationale string
  naming the exact handler line whose `arguments.get(...)` fallback proves no config field backs
  it (a per-call literal, a traversal depth, a safety confirmation — not a config value).
  Membership is decided by what the handler's fallback actually reads, not by name similarity to a
  config field.

The 18 `output_format` occurrences collapse to one shared `OUTPUT_FORMAT_PROPERTY` definition
(`CONFIG_BACKED["*.output_format"]` plus one description), since the property is identical at
every call site — `output_format` is popped centrally in `server.py`'s `handle_call_tool` before
any handler runs, so a single `(OutputConfig, "format")` mapping backs all 18. `search_mode`'s enum
generalizes the same way via `SEARCH_MODE_ENUM`, derived once instead of hand-listed at two call
sites.

The parity test widens from 4-of-18 tools to a whole-registry ratchet
(`test_every_bound_carrying_property_is_classified`, `test_config_backed_properties_spread_the_derived_fragment`,
`test_output_format_properties_match_shared_definition`), alongside — not replacing — the original
4-tool parametrized check, which verifies a different seam (`config_handlers.py`'s apply-path field
maps agree with the schema).

## Incidental fix carried by the same reconnaissance

Building `config_schema.py` required reading every `RerankerConfig` field to classify
`configure_reranking`'s three MCP-settable ones, which surfaced the field-count drift the
architecture review's candidate list had separately noted: `RerankerConfig.__doc__` said "14
fields" while `dataclasses.fields()` returned 15 (`b5bf508` added a field without bumping the
docstring count; `32b086c` then bumped a stale 13 to 14, inheriting the miss instead of fixing
it). `tests/unit/search/test_config_field_liveness.py` gained
`test_section_docstring_field_counts_match_dataclasses_fields`, a ratchet derived against
`dataclasses.fields()` (the one unambiguous source of truth for a field count) rather than a
second hand-maintained pin — comparing against a fixed snapshot would just relocate the staleness
this ADR closes elsewhere. The docstring itself was corrected to "15 fields" in the same change.

## Out of scope

- **`status_handlers.py`'s hand-listed 20-field echo** — the corrected schema descriptions now
  point at `get_search_config_status` as the source of truth for effective values, but that
  handler's own field list has no parity test of its own. Not built here.
- **The other ~10 sections' docstring counts never carrying a "(N fields)" annotation at all** —
  the new ratchet only checks sections that state a count; stating one stays optional.
- **`tool_handlers.py`'s triple-repeated tool-name list** (imports, `TOOL_DISPATCH`, `__all__`) —
  a separate Remove Dead Code candidate the architecture review named alongside this one, not
  touched here.
