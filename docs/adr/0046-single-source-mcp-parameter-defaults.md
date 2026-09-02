# Single-source hand-typed MCP parameter defaults through `config_schema.py`

Status: accepted
Date: 2026-08-19

## Context

ADR-0042 stopped the MCP tool schema from deriving `default` off a `search/config.py` field —
a per-install value, the lowest of ADR-0014's four precedence layers, and therefore never safe
to bake into a static schema. It left the other kind of default alone: the ~12 MCP parameters
whose fallback is a genuine per-call *literal* (`include_parent` always falls back to `False`
regardless of install, `find_connections.max_depth` always falls back to `3`), not a config
read. Those are safe to publish — but `mcp_server/config_schema.py` only *asserted* that safety.
Its `HAND_TYPED` map was `dict[str, str]`: key → a prose rationale claiming what the handler
falls back to. Nothing executed the claim. `mcp_server/tool_registry.py` restated the same value
a second time, by hand, as a `"default"` literal in the schema.

That gap was live, not theoretical. `index_directory.include_exclusive` published
`"default": False` in the schema while `index_handlers.py`'s `arguments.get("include_exclusive")`
took **no** fallback at all — it resolves tri-state against the project's stored
`project_info.json` filter (omitted → reuse the stored value; explicit `True`/`False` → override
it). A conformant MCP client that materializes schema defaults would send `include_exclusive:
false` on every call, indistinguishable from an intentional override, silently narrowing scope
and forcing an unwanted full reindex on any project stored with `include_exclusive: true`. This
was caught by inspection, not by any test — the two statements had no mechanism connecting them
and had simply drifted apart. `docs/adr/0042-publish-invariants-not-values.md` fixed the
CONFIG_BACKED half of this problem; this ADR fixes the HAND_TYPED half the same defect exposed.

## Decision

Extend `mcp_server/config_schema.py`'s existing `CONFIG_BACKED` / `HAND_TYPED` split so a
HAND_TYPED default is stated exactly once, and both the schema and the handler read that one
statement instead of restating it.

| fallback source | set | publishes a schema `default`? |
|---|---|---|
| a `search/config.py` field, read at call time (per-install, ADR-0014's four layers) | `CONFIG_BACKED` | never (ADR-0042) |
| a literal in the handler, identical on every install (`False`, `3`, `SearchMode.AUTO`, ...) | `HandTyped(default=...)` | yes — spread from the seam, never restated |
| deliberately tri-state: omission defers to stored project state or to server config, distinguishable from an explicit value | `HandTyped(default=NO_DEFAULT)` | must stay absent |

`HAND_TYPED` becomes `dict[str, HandTyped]`. `HandTyped` is a frozen, `kw_only` dataclass:

```python
@dataclasses.dataclass(frozen=True, kw_only=True)
class HandTyped:
    default: Any = NO_DEFAULT
    rationale: str

    @property
    def schema(self) -> dict[str, Any]:
        if self.default is NO_DEFAULT:
            return {}
        value = self.default
        return {"default": value.value if isinstance(value, Enum) else value}
```

`NO_DEFAULT` is a dedicated sentinel (`_NoDefault`), not `None` — `None` is itself a legitimate
default for a real field, so it must stay distinguishable from "no default published."

`tool_registry.py` spreads `**HAND_TYPED["<tool>.<param>"].schema` into each governed property,
in the exact slot the old `"default": <literal>` occupied. Handlers read the same record back
through one accessor:

```python
def arg(arguments: dict[str, Any], key: str) -> Any:
    record = HAND_TYPED[key]
    if record.default is NO_DEFAULT:
        raise ValueError(...)  # tri-state; caller must resolve its own fallback
    _, param = key.split(".", 1)
    return arguments.get(param, record.default)
```

`arg()` lives in `config_schema.py` itself, not a new module — splitting the schema fragment
from the handler accessor into separate files would recreate the exact gap this closes. Twelve
call sites across four handler modules (`search_orchestrator.py`, `index_handlers.py`,
`search_handlers.py`, `config_handlers.py`) now call `arg(arguments, "<tool>.<param>")` instead
of restating their own `arguments.get(key, literal)`.

### The `SearchMode` wrinkle

Two governed defaults are not the same Python object on both sides of the seam.
`search_code.search_mode` and `configure_search_mode.search_mode` both fall back, in their
handlers, to a `SearchMode` enum member (`SearchMode.AUTO`, `SearchMode.HYBRID`) — but the
published JSON schema can only hold `.value`, the plain string (`"auto"`, `"hybrid"`). Storing
the plain string in `HandTyped.default` would have been behaviorally safe (`SearchMode` is a
`StrEnum`; every comparison against it holds under plain `str` equality) but would silently
change the handler's runtime value type after the redirect — a refactor that is supposed to be
byte-for-byte behavior-preserving has no business doing that. `HandTyped.default` therefore
stores the enum member itself; `.schema` normalizes `Enum → .value` only on the way out, for the
JSON-schema consumer. The handler keeps its exact pre-refactor type; the wire payload is
unaffected.

### Defining property

The published `tools/list` payload does not move a byte. Verified by diffing a full
`build_tool_list(include_advanced=True)` capture against a pre-change baseline — empty both
after the schema-side spread and again after the handler-side redirect.

## Ratchets

Four tests in `tests/unit/mcp_server/test_tool_registry.py`'s `TestHandTypedSchemaSeam`:

- `test_schema_default_matches_the_seam` — every governed property's published `default`
  matches `HAND_TYPED[key].schema["default"]` on `(value, type(value))`, not plain `==`
  (`0 == False` would let a wrong-typed default slip through undetected).
- `test_every_published_default_comes_from_hand_typed` — no property may publish a `"default"`
  whose classification key is missing from `HAND_TYPED`, or maps to a `NO_DEFAULT` entry; the
  failure message quotes that entry's own rationale (naming the `project_info.json` tri-state,
  where applicable) so a future violation explains itself.
- `test_hand_typed_defaults_are_json_scalars` — asserts on `.schema`'s *emitted* value, not
  `.default` — `.default` may legitimately hold an `Enum` member (`SearchMode`), which is not
  itself a JSON scalar.
- `test_no_inline_default_literal_in_tool_registry_source` — an AST walk over
  `tool_registry.py` banning any literal `"default": ...` dict entry outright. Supplementary to
  the three runtime checks above, not a replacement for them: detection-after-the-fact (comparing
  values once both sides already exist) is exactly the mechanism that already failed once on
  `include_exclusive`. This ratchet removes the failure mode at the syntax level — a schema
  default can only ever arrive via a `HAND_TYPED[key].schema` or `CONFIG_BACKED[key]` spread.

Verified to bite: reintroducing `include_exclusive`'s `"default": False` literal turns three
tests red (the AST ban, `test_every_published_default_comes_from_hand_typed`, and the pre-existing
D1 regression guard `TestIndexDirectoryFilterSchema::test_no_forced_schema_default`), confirming
the new ratchets and not just the old one catch the regression.

## Deliberately out of scope

- **Bounds vs. defaults.** `find_connections.max_depth` publishes `maximum: 5` but its handler
  never clamps to it (`search_handlers.py`); `find_path.max_hops` *does* clamp
  (`min(arg(...), 20)`). `search_code.k` carries three independent ceilings (schema `maximum:
  100`, the runtime `SearchModeConfig.max_k` clamp, and a "max recommended: 20" prose hint).
  Making these consistent is a behavior change — clamp vs. reject is its own decision — not a
  single-sourcing refactor. Left as-is.
- **`configure_search_mode.search_mode`'s unconditional write.** Its handler sets `SearchMode`
  from a literal `HYBRID` fallback unconditionally, never deferring to the persisted
  `default_mode` value — `default_mode` is deliberately excluded from `_SEARCH_MODE_FIELDS`'
  skip-if-absent patch. Publishing `"hybrid"` as its schema default is honest given that design;
  changing the design itself is not this ADR's concern.
- **`find_similar_code.k`.** Publishes neither a bound nor a default; its handler falls back to
  a live `get_search_config().search_mode.default_k` read — `CONFIG_BACKED` in spirit, but it
  publishes no invariant today, so there is nothing to single-source. Left unclassified in both
  maps, same as before this change.
