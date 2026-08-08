# C++ Chunking Parity

**Status**: planned, not implemented
**Date**: 2026-08-06
**Scope**: chunking only — call-graph parity explicitly deferred (see *Out of scope*)
**Proposes**: ADR-0034 (`chunker_version` over an `INDEX_VERSION` bump), ADR-0035 (C++-only
container seam)

All measurements in this document were taken against the working tree on the date above, using
the live tree-sitter grammars and the repo's own tracked fixtures. Re-verify before implementing
if the chunking path has moved since.

## Context

C++ support in this repo is nominal. The chunker registers a `cpp` grammar and eight splittable
node types, but `chunking/languages/cpp.py` is a 57-line stub and `base.py`'s traversal only
descends into Python-shaped containers. Measured on the repo's own tracked fixtures:

| File | Today | Why |
|---|---|---|
| `tests/fixtures/chunker_corpus/sample.cpp` | 4 chunks | `namespace math` → `name=None`; `square` never chunked; `Vector` ctor never chunked |
| `tests/test_data/multi_language/Calculator.cpp` | **4 chunks** for 67 lines | one 46-line `namespace_definition` with `name=None` swallows a template class, 5 methods, an enum, and a free function |
| `tests/test_data/multi_language/calculator.c` | 11 chunks, **4 with `name=None`** | `c.py` only matches a direct `function_declarator` child, so every pointer-returning function is nameless |

Root cause is one line: `base.py:975` hardcodes `["class_definition", "class_declaration"]`, and
line 983 `return`s unconditionally afterwards. Any chunked node that isn't a Python class stops
traversal dead. No header extension is registered at all, so `.h`/`.hpp` files are invisible.

Outcome: C++ reaches the same tier as Go/Rust/C#/JS/TS — correct names, member functions,
headers, templates, namespaces. Call-graph parity (Python/GLSL tier) is explicitly **not** in
scope.

## Decisions

Ten forks were resolved by measurement during design. Each is load-bearing:

1. **Header members chunk** — function-shaped `field_declaration`/`declaration` (`Foo();`,
   `~Foo();`, `int m();`, `virtual void pure() = 0;`) become chunks. Data members (`int data;`)
   do not.
2. **Templates split by what they wrap** — `template_declaration` wrapping a `function_definition`
   stays chunk-and-stop (today's behaviour, keeps the `template<…>` line, zero churn); wrapping a
   class/struct returns `False` so traversal falls through and the class chunks once with its
   members. No overlapping near-duplicate pair.
3. **Kind mapping is language-scoped** — a new `LANGUAGE_NODE_TYPE_OVERRIDES` table, consulted
   before the global `NODE_TYPE_MAP`. GLSL's `declaration` kind is untouched.
4. **Spec table holds candidates, predicate narrows** — new types go in
   `LANGUAGE_SPECS["cpp"].splittable_node_types` so `test_splittable_node_types_exist_in_grammar`
   validates them against the live grammar; `should_chunk_node` narrows to function-shaped ones.
   The ownership gate permits this — only `_load_language`/`_get_splittable_node_types` are banned.
5. **Shared C-family unwrapper** — new `chunking/languages/_c_family.py`, used by both `cpp.py`
   and `c.py`. Respects `base.py:238`/`:385` ("complex leaves keep their own name logic"), leaves
   GLSL's narrower copy alone, and fixes C's identical pointer bug.
6. **No `INDEX_VERSION` bump** — a `chunker_version` marker in snapshot metadata instead.
7. **Chunking only** — the three GLSL-only gates in `multi_language_chunker.py` (`:481`, `:612`,
   `:803`) are not touched. `calls`/`relationships` stay empty, as today.
8. **Container set is C++-only** — the seam is overridable, but the base default stays
   `{class_definition, class_declaration}`. Rust and C# have the identical bug (verified:
   `impl Point { fn new }` never chunks `new`; C# `namespace_declaration` is splittable) and are
   left as a documented follow-up so their chunk_ids and the reindex-warning scope don't move.
9. **Namespaces qualify but don't promote** — `namespace_definition` stamps
   `parent_type="namespace"`; the `function → method` promotion is gated on
   `parent_type in (None, "class")`. `math::square` keeps kind `function` and gains qualified name
   `math.square`.
10. **One benchmark round, re-pin only if it moves.**

### `.h` routing, settled by measurement

`.h` is ambiguous, and the registry is a flat `dict[str, str]` with no content-sniffing seam.
Cross-parsing both grammars:

| Input | `tree_sitter_c` | `tree_sitter_cpp` |
|---|---|---|
| C header (typedef, struct, fn-ptr, pointer return) | 0 errors | **0 errors** |
| C++ header (namespace, template class, `operator=`) | 4 errors | **0 errors** |
| C-keyword trap (`int new; int class; int this;`) | 0 errors | **0 errors** |

`.h → cpp` strictly dominates. All 7 header extensions map to `cpp`. **20 → 27 extensions.**

## Implementation

### Phase 1 — `chunking/language_registry.py`

- `EXT_TO_LANGUAGE` += `.h .hpp .hh .hxx .inl .ipp .tpp` → `"cpp"`.
- `LANGUAGE_SPECS["cpp"].splittable_node_types` += `field_declaration`, `declaration`,
  `alias_declaration`. (`namespace_definition`, `class_specifier`, `template_declaration`,
  `enum_specifier` are already present.)
- New `LANGUAGE_NODE_TYPE_OVERRIDES: dict[str, dict[str, str]]` =
  `{"cpp": {"field_declaration": "function", "declaration": "function",
  "alias_declaration": "type"}}`.

Lands standalone: the current `extract_metadata` returns `{"node_type": …}` with no name for
unhandled types and never raises, so new splittable types degrade to nameless chunks, not errors.

### Phase 2 — `chunking/languages/base.py`

Replace the hardcoded list at `:975` with an overridable class attribute:

```python
_CONTAINER_NODE_TYPES: frozenset[str] = frozenset(
    {"class_definition", "class_declaration"}
)
_CONTAINER_PARENT_TYPE: str = "class"  # overridden per node type in CppChunker
```

Traversal consults `self._CONTAINER_NODE_TYPES` and stamps `parent_type` from the container's own
node type rather than the literal `"class"`. Default value is byte-identical for every existing
language. Reuse `_extract_sibling_comment_docstring` (`:547`) as the precedent for an opt-in
shared helper.

Do **not** touch the splitting gate at `:912` — it fires only for
`("function_definition", "decorated_definition")`, so C++ classes are never split and the
"splitting swallows members" hazard does not exist.

### Phase 3 — the C family

**New `chunking/languages/_c_family.py`** — module-level `unwrap_declarator_name(node, get_text)`:

```
walk while node.type in (pointer_declarator, reference_declarator, function_declarator,
                         array_declarator, init_declarator, parenthesized_declarator):
    nxt = node.child_by_field_name("declarator")
    if nxt is None: nxt = first named declarator-ish child     # reference_declarator
    node = nxt
terminals: identifier | field_identifier | qualified_identifier
           | destructor_name | operator_name
```

The `None` fallback is required, not defensive: `reference_declarator` has **no `declarator`
field** (verified — `field_declarator=NONE, named_children=['function_declarator']`, while
`pointer_declarator` does have it). Without it every reference-returning function —
`operator=`, `operator+=`, every fluent API — silently returns `None`.

**Rewrite `chunking/languages/cpp.py`** structured like `glsl.py` minus the call/relationship
extractors:

- `should_chunk_node` override — narrows `field_declaration`/`declaration` to those whose
  declarator unwraps to a `function_declarator`; returns `False` for `template_declaration`
  wrapping a class/struct.
- `_CONTAINER_NODE_TYPES` = `{class_specifier, struct_specifier, union_specifier,
  namespace_definition}`.
- `function_node_types` override → `frozenset({"function_definition"})`, mirroring `glsl.py:380`,
  so the sizing profiler stops counting containers as functions.
- `extract_metadata` — required by `test_language_spec_ownership.py:259` (`CppChunker` is in
  `COMPLEX_LEAF_CLASSES`). Name extraction routes through `unwrap_declarator_name`.
  `namespace_definition` uses its `name` field (`namespace_identifier`); `alias_declaration` and
  `enum_specifier` (incl. `enum class`) both have `name` fields. `using Base::thing;` is
  `using_declaration` — no declarator, not chunked. `#pragma once` is `preproc_call`, absent from
  cpp's splittable set, falls through harmlessly.

**Fix `chunking/languages/c.py`** — replace the `:24-26` direct-child scan with
`unwrap_declarator_name`. Snapshot-neutral for `sample.c` (no pointer-returning function);
`calculator.c`'s 4 nameless functions gain names.

### Phase 4 — `chunking/multi_language_chunker.py`

- `_map_node_type(node_type, parent_name, parent_type, language)` — consult
  `LANGUAGE_NODE_TYPE_OVERRIDES[language]` before `NODE_TYPE_MAP`; gate the `function → method`
  promotion on `parent_type in (None, "class")`. The `None` default preserves today's behaviour
  exactly (no chunker sets `metadata["parent_name"]` directly, so `parent_type` is present
  whenever `parent_name` is).
- `:750` — register namespace chunks in `class_chunk_map` alongside classes so the `:755`
  `parent_chunk_id` lookup resolves instead of dead-ending.

### Phase 5 — reindex signal

`INDEX_VERSION` stays at **4**. It is BM25-document-format-scoped (all three prior bumps were
tokenization changes), it only logs a warning (`bm25_index.py:749` — it forces nothing), and its
message would be wrong advice for a pure-Python project. Precedent for declining: ADR-0020,
ADR-0032, `CHANGELOG.md:243`.

Instead, add `chunker_version` to snapshot metadata (`merkle/snapshot_manager.py`,
`search/incremental_indexer.py::_build_snapshot_metadata`). On load, warn **only** when it differs
*and* the snapshot's file list contains an affected extension. Pure-Python projects stay silent.

New `.h` files need no special handling — `merkle/merkle_dag.py:234` filters by
`supported_extensions`, so they read as added and chunk incrementally for free. The gap is
existing `.cpp`/`.c` files: unchanged hash → never re-chunked → stale names persist silently.

### Phase 6 — tests, snapshots, docs

- Extend `tests/fixtures/chunker_corpus/sample.cpp` to cover the decisions: a header-style
  declaration-only class, `T& operator=`, a pointer-returning out-of-class definition
  (`int* Foo::getPtr()`), `enum class`, `using X = Y;`.
- Re-record **only** `test_chunker_metadata_parity[cpp].json` and `[c].json`. That
  `[rs] [cs] [py] [glsl] [go] [js] [ts]` stay byte-identical **is the acceptance criterion** for
  decision 8.
- `test_language_spec_ownership.py` needs no relaxation — `BANNED_METHODS` is
  `{_load_language, _get_splittable_node_types}`, so a `should_chunk_node` override is already
  permitted.
- Docs: `README.md:300`, `docs/MCP_TOOLS_REFERENCE.md:1150`, `start_mcp_server.cmd:2954`
  (20 → 27, and header extensions in the language table). `CLAUDE.md:45/59/368` also carry the
  count but the file is **gitignored/local** — update it, it won't be committed.

### ADRs

`docs/adr/0033-lift-torch-ceiling.md` already exists, so the next free number is **0034**. The
README index table stops at 0032 — the missing 0033 row is a pre-existing gap; add both.

- **ADR-0034** — decline the `INDEX_VERSION` bump; introduce `chunker_version`. Future readers
  will ask why the established marker wasn't reused; the answer (wrong subsystem, warn-only,
  false-alarms every Python project) needs recording.
- **ADR-0035** — C++-only container seam. The seam is overridable yet deliberately unused by two
  languages with the identical, verified bug. Record the Rust/C# finding and the reopening
  condition, or it will read as an oversight.

### Proposed `CONTEXT.md` additions

Glossary only — no implementation detail. To be written during implementation, not now:

> **Container node**: A chunked node whose children are traversed again and chunked in their own
> right, carrying the container's name and kind down to them. Every other chunked node terminates
> descent.
> *Avoid*: parent node, wrapper node.
>
> **Transparent node**: A node deliberately left unchunked so traversal descends to what it wraps,
> which is chunked instead. The transparent node's own text is still part of the resulting chunk.
> *Avoid*: pass-through node, skipped node.

## Verification

```bash
# 1. Unit + ownership + parity
./scripts/test/run_tests.sh tests/unit/chunking/ -v

# 2. Snapshots: cpp/c re-recorded, all others must be untouched
./scripts/test/run_tests.sh tests/unit/chunking/test_chunker_parity.py --snapshot-update
git diff --stat tests/unit/chunking/__snapshots__/test_chunker_parity/
#    expect ONLY [cpp].json and [c].json

# 3. Full unit suite (base.py has the widest blast radius)
./scripts/test/run_tests.sh tests/unit/ -q
```

**Live chunker** — `Calculator.cpp` should go from 4 chunks to ~14, with `namespace Math` named,
`Calculator` and its 5 members present, `add`/`multiply` named via the `reference_declarator`
fallback, `Point` plus its ctor and `distance`, and `main`:

```bash
.venv/Scripts/python.exe -c "
from chunking.tree_sitter import TreeSitterChunker; from pathlib import Path
c=TreeSitterChunker(); ps=c.parse_file(Path('tests/test_data/multi_language/Calculator.cpp'))
for ch in c.chunk_parsed(ps): print(ch.start_line, ch.node_type, ch.metadata.get('name'), ch.parent_class)"
```

Assert no chunk has `name=None` in `calculator.c`, and that `Math::square`-style free functions
carry kind `function` (not `method`) with qualified name `Math.applyOperation`.

**End-to-end via MCP** — index a real C++ project, then confirm header and member-function
retrieval:

```
index_directory("<path to a C++ project>")
search_code("constructor initializing the vector")
search_code("operator= assignment")
```

**Benchmark** — one deterministic round, since `PYTHONHASHSEED` is pinned (ADR-0021) and a delta
is therefore real rather than noise:

```bash
./scripts/test/run_tests.sh --version >/dev/null   # venv sanity
python scripts/benchmark/run_sscg_benchmark.py --k 10   # 63q canonical
```

Diff against `evaluation/sscg_hs0_only_63q_*_20260802.json` (μ 0.7942). All four tracked C/C++
files live under `tests/`, which is in `user_excluded_dirs`, and no `.h` is tracked — so C++ adds
zero corpus chunks. The delta under test is the ~10-20 new *Python* chunks this change adds to
`chunking/` and `search/`. Identical → record "canon verified unchanged". Moved → re-pin with two
rounds and a writeup.

## Out of scope (deliberate, with reopening conditions)

- **Call/relationship parity for C++.** Requires a C++ noise model (STL, operators,
  constructor-vs-call, `std::`) plus generalizing two GLSL-justified hardcodes:
  `multi_language_chunker.py:515`'s allowlist excludes `"method"` — which is exactly what C++
  member functions map to — and `:523` hardcodes `is_method_call=False`, wrong for `obj.m()` /
  `ptr->m()` / `A::f()`. Reopen as its own campaign.
- **Rust `impl_item`/`mod_item` and C# `namespace_declaration` container swallowing.** Verified
  live. One-line spec change each once the seam exists; deferred because it moves their chunk_ids
  and widens the reindex-warning scope.
- **Pre-existing name-extraction gaps** surfaced while measuring: C# `method_declaration`
  returning `'T'` (a type parameter), and `name=None` on Go `type_declaration`/`method_declaration`
  and TS `method_definition`.
