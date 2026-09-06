# Python Decorated-Class Container Traversal

**Status**: planned, not implemented
**Date**: 2026-09-05
**Scope**: chunking only — canon re-pin explicitly deferred (see *Out of scope*)
**Depends on**: `721ccde` (`fix(chunking): set parent_chunk_id on decorated methods`) — already
landed on `development`
**Proposes**: ADR-0063 (Python-only container-traversal seam extension)

All measurements in this document were taken against the working tree at `721ccde` on the date
above. Re-verify before implementing if the chunking path has moved since.

## Context

`721ccde` fixed the *assignment* half of the class→method containment gap: a decorated **method**
(`@property`, `@staticmethod`) now gets a `parent_chunk_id`. It deliberately left the *chunk-shape*
half alone, and `docs/adr/0038-cpp-only-container-traversal-seam.md:83-111` records it as the third
instance of the container-traversal bug ADR-0038 fixed for C++ only — after Rust's `impl_item` and
C#'s `namespace_declaration`.

The bug: `decorated_definition` is splittable (`chunking/language_registry.py:417-425`) but is not
in `_CONTAINER_NODE_TYPES` (`chunking/languages/base.py:197-209`). Traversal chunks the outer
wrapper and `return`s at `base.py:1009` before the inner `class_definition` is ever visited. So
`@dataclass class Foo: def bar(self): ...` yields one opaque blob and `bar` never surfaces as its
own chunk.

Measured on the indexed corpus (235 files, `ast` scan):

| Symptom | Cause | Count |
|---|---|---|
| Methods of a `@dataclass`/decorated class never surface as chunks | `decorated_definition` not in `_CONTAINER_NODE_TYPES`; traversal returns at `base.py:1009` before visiting the inner class | 76 decorated classes swallowing 72 methods (34 classes have ≥1 method) |

Worst offenders:

| methods | lines | chunk |
|---|---|---|
| 12 | 194 | `mcp_server/state.py::ApplicationState` |
| 7 | 201 | `chunking/relationships/relationship_types.py::RelationshipEdge` |
| 6 | 127 | `graph/traversal_policy.py::TraversalPolicy` |
| 4 | 60 | `search/chunk_id.py::ChunkId` |

**Live-index A/B proof, same file:** `search/config.py:1975-2254:class:SearchConfig` is a *plain*
class — indexed as a 279-line chunk **and** `search/config.py:1987-2050:method:SearchConfig.__init__`
exists alongside it. Its decorated neighbour
`search/config.py:709-965:decorated_definition:RerankerConfig` (256 lines) has no member chunks at
all. Same file, same size class, different chunking — purely because one has a `@dataclass` line
above it.

**Why the naive fix is wrong** (verified in-memory, recorded at ADR-0038:93-102): simply adding
`"decorated_definition"` to `_CONTAINER_NODE_TYPES` makes traversal recurse into the wrapper's
children, where the inner `class_definition` is *itself* splittable *and already* a container —
producing a duplicate, self-parented class chunk:

```
decorated_definition  name='Decorated'     parent=None         lines=4-12
class_definition      name='Decorated'     parent='Decorated'  lines=5-12   <-- duplicate
function_definition   name='dec_cls_meth'  parent='Decorated'  lines=8-12
```

There is no dedup anywhere in `base.py` or `_convert_tree_chunks` to suppress it.

## Decisions

Four forks, resolved by measurement:

1. **The seam is a node-returning predicate, not a frozenset test.** `_container_traversal_root(node)`
   returns the node whose children are the container's members (or `None`) — for a decorated class
   that's the *inner* `class_definition`, not the wrapper. This is what lets traversal skip both the
   wrapper and the inner node without re-chunking either, avoiding the duplicate above. Overridable
   per-language exactly like `_CONTAINER_NODE_TYPES`; the base implementation is byte-identical
   behavior to today's frozenset check for every other language.
2. **The wrapper chunk is kept, unchanged.** `decorated_definition` still gets chunked (full node
   text, full span) before the container check runs — no golden-dataset id moves, no existing
   content shrinks. This change is purely additive: ~72 new `method` chunks, zero removed or
   resized chunks.
3. **The parent-registration gate widens too.** `multi_language_chunker.py:905` only registers
   `chunk_type in ("class", "struct", "union", "namespace")` into `class_chunk_map`. A decorated
   class's `chunk_type` is `"decorated_definition"`, so without widening this gate its new members
   get `parent_name` but `parent_chunk_id=None` — reproducing the exact C++ `struct_specifier`
   regression `test_chunk_cpp_struct_member_parent_chunk_id` was written to catch.
4. **Split gate must respect the new container check.** `base.py:929-934` splits large
   `decorated_definition` nodes into `split_block`s and returns before the container check ever
   runs. Add a "not a container" conjunct so a large decorated class descends instead of splitting.
   Verified no-op on today's corpus: the two largest decorated classes (194, 201 lines) are already
   single chunks, so `_split_large_node` already returns `[]` for them — this only future-proofs
   against a bigger one appearing.

## Implementation

### Phase 1 — `chunking/languages/base.py`

Add an overridable predicate next to `_CONTAINER_NODE_TYPES` (`:197-209`):

```python
def _container_traversal_root(self, node: Any) -> Any | None:
    """Return the node whose children are container members, or None.

    Default: a node is its own traversal root iff its type is in
    `_CONTAINER_NODE_TYPES`. Overriding leaves can return a *different*
    node -- see PythonChunker, which returns the inner class of a
    decorated class so neither the wrapper nor the inner node is
    re-chunked.
    """
    if node.type in self._CONTAINER_NODE_TYPES:
        return node
    return None
```

Rewrite the container gate at `:997-1009` to consult it:

```python
container_root = self._container_traversal_root(node)
if container_root is not None:
    class_info = {
        "parent_name": metadata.get("name"),
        "parent_type": (
            "namespace" if container_root.type == "namespace_definition" else "class"
        ),
    }
    for child in container_root.children:
        traverse(child, depth + 1, class_info)
return
```

The ternary now keys off `container_root.type`, not `node.type` — for a decorated class that's
`class_definition`, so `parent_type` is correctly `"class"`. `:997` is this attribute's only read
site in production, so this is a complete swap; default behavior for every non-Python language is
unchanged.

Narrow the split gate at `:929-934` with a fourth conjunct: `and self._container_traversal_root(node)
is None`.

### Phase 2 — `chunking/languages/python.py`

`PythonChunker` currently has no `_CONTAINER_NODE_TYPES` override (the base default is already
right for Python). Add the traversal-root override:

```python
def _container_traversal_root(self, node: Any) -> Any | None:
    """A decorated class is a container; a decorated function is not.

    Returns the *inner* class node so `traverse` descends straight into
    the class body: the `decorated_definition` wrapper is still chunked
    (its chunk_id is load-bearing for golden references) and the inner
    `class_definition` is skipped, which is what prevents the duplicate
    self-parented chunk recorded in ADR-0038.
    """
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in self._CONTAINER_NODE_TYPES:
                return child
        return None
    return super()._container_traversal_root(node)
```

`extract_metadata` (`python.py:107-164`) already digs through the decorator to the inner def for
`name`, so `class_info["parent_name"]` needs no further change.

### Phase 3 — `chunking/multi_language_chunker.py`

Widen the registration gate at `:905`:

```python
if (
    chunk_type in ("class", "struct", "union", "namespace", "decorated_definition")
    and name
):
```

Extend the existing comment block (`:895-904`) to explain why admitting decorated *methods* to the
same map is harmless: `_resolve_parent_chunk_id` (`:778-814`) filters to spans that *enclose* the
child, and a decorated method's span never encloses another chunk (nested functions aren't
chunked — `base.py:1009` returns unconditionally for non-containers).

*Rejected alternative:* tagging `metadata["wraps"] = "class"` in `python.py` instead of widening
the `chunk_type` tuple — more precise, but churns the `metadata` dict in the `[py]` parity snapshot
for every decorated chunk, for no benefit the span-enclosure filter doesn't already provide.

No change needed at `_map_node_type` (`:419-431`): new members arrive with `parent_name` set and
`parent_type="class"`, so the existing `function → method` promotion fires unmodified.

### Phase 4 — tests, snapshot, docs

- `tests/unit/chunking/test_parent_chunk_id.py` — six new tests (methods of a decorated class get
  the right parent; no duplicate class chunk; wrapper span/id unchanged; decorated method inside a
  decorated class; decorated function still not a container; nested plain class inside a decorated
  class). Update, don't delete, `test_decorated_class_parenting_is_container_scoped` — its docstring
  already anticipates this change.
- `tests/fixtures/chunker_corpus/sample.py` — add a minimal decorated class with one method; it has
  none today. Re-record **only** `[py].json`.
- One graph-layer test in `test_graph_integration.py::TestClassContainsMethodEdge` mirroring the
  case added in `721ccde`.
- `docs/adr/0063-python-decorated-class-container-traversal.md`, `docs/adr/README.md` (add the 0063
  row), `docs/adr/0038-...md` (mark the Python instance resolved), `CONTEXT.md` (glossary
  correction, gitignored — never staged), `CHANGELOG.md` (`### Fixed` + `### Migration`).

The full implementation-level detail for all of the above (exact test bodies, exact ADR content,
exact CHANGELOG wording) lives in the working plan file from the session that produced this
document; regenerate it fresh next session rather than relying on stale prose here — see
*Verification* and re-derive the counts in the Context table first.

## Verification

```bash
# 1. Targeted
./scripts/test/run_tests.sh tests/unit/chunking/test_parent_chunk_id.py -v
./scripts/test/run_tests.sh tests/unit/chunking/test_multi_language.py -v   # C++ container precedent

# 2. Snapshot: py re-recorded, everything else untouched
./scripts/test/run_tests.sh tests/unit/chunking/test_chunker_parity.py -k "py" --snapshot-update -q
git diff --stat tests/unit/chunking/__snapshots__/test_chunker_parity/
#    expect ONLY [py].json

# 3. Full chunking + graph suites (base.py has the widest blast radius)
./scripts/test/run_tests.sh tests/unit/chunking/ tests/unit/search/test_graph_integration.py -q

# 4. Whole unit suite
./scripts/test/run_tests.sh tests/unit/ -q
```

Ad-hoc, before committing: a read-only script over the 34 affected classes asserting, for each,
exactly one chunk carries the class name, its span is unchanged vs. HEAD, every method is present
with `chunk_type == "method"` and a non-`None` `parent_chunk_id`, and
`EmbeddingDocumentComposer.compose` on one such method contains the `class Foo` header line. Put it
in `tmp/`, never `test-results/` — that directory is indexed and pollutes the benchmark corpus.

Golden audit, only if a sanity-check reindex is run (not required for this change set):

```bash
.venv/Scripts/python.exe tools/batch_index.py --path . --mode force
.venv/Scripts/python.exe scripts/benchmark/audit_golden_dataset.py
```

`--exclude-dirs` replaces the stored list wholesale — omit it to reuse the stored one. Expect CLEAN
and roughly 2,943 chunks (2,871 + ~72).

## Out of scope (deliberate, with reopening conditions)

- **The canon re-pin.** This change lands code + tests + docs only. `721ccde` already left
  `evaluation/CANON_20260905_REBASELINE.md` stale; this change adds a second, larger perturbation
  (~72 new chunks, ~34 new `contains` edges) on top of it. Record both as one combined pending
  re-pin in `CHANGELOG.md` rather than implying either change can be attributed separately after
  the fact — measure them together in the next dedicated re-pin session.
- **Rust `impl_item`/`mod_item` and C# `namespace_declaration`.** ADR-0038's original deferrals,
  now trivially expressible through the same `_container_traversal_root` seam, but still gated on
  ADR-0038's own reopening condition (a real project in this codebase's indexing scope needing it).
- **`embeddings/document_composer.py:196`** skipping the parent-class header for
  `decorated_definition` chunks. A real, parallel gap, but fixing it changes embedding text for
  chunks this change doesn't otherwise touch, and is its own comparability break. Separate ticket.
- **Parenting `split_block` fragments; nested *plain*-class containment.** Both stay unparented by
  design, unchanged from `721ccde`'s scope decision.
- A `chunker_version` marker. ADR-0037 declined one for the two-instance C++/decorated-method
  pattern; this would be a third "chunker changed, files didn't" instance, which is ADR-0037's own
  stated reopening condition. Worth deciding explicitly in ADR-0063 rather than by silent omission,
  but not built here.
